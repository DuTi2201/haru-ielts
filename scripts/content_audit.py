"""Content audit of the Haru seed against the acceptance rubric (DB-02/03, CUR-01..04).

The seed (app/seed) is the source of truth for lessons, cards and practice, so these checks read it
directly; the database-only checks (editorials, orphans, item_state) are in scripts/audit_db.sql.

usage: python -m scripts.content_audit        (exit 1 when a hard check fails)
"""
from __future__ import annotations

import re
import sys
from collections import Counter

from app.services import lesson_seed as ls

POSITION = {"앞", "뒤", "위", "아래", "밑", "옆", "오른쪽", "왼쪽", "가운데", "사이", "안", "밖"}
CONNECTORS = {"그리고", "그래서", "그렇지만", "그러나", "하지만", "그런데", "그러니까", "그러면", "그래도", "왜냐하면"}
FREQUENCY = {"항상", "언제나", "자주", "보통", "가끔", "별로", "전혀", "벌써", "아직", "먼저"}
# Korean Grammar in Use · Beginner items the rubric names explicitly (a form is found in any card pattern of 1–16)
KGIU = {
    "-(으)ㄹ 줄 알다": r"ㄹ 줄 알다",
    "A-아/어하다": r"아/어하다",
    "-아/어 있다": r"아/어 있다",
    "N처럼": r"처럼",
    "N쯤": r"쯤",
    "-지 않아도 되다": r"지 않아도 되다",
    "-(으)시겠어요": r"시겠어요",
    "-아/어 줄게요": r"줄게요",
    "-나요 / -(으)ㄴ가요": r"나요|ㄴ가요",
    "-(으)ㄴ/는데요": r"는데요",
    "ㅡ 불규칙": r"ㅡ",
    "-았/었었-": r"았/었었",
    "-대요 / -래요": r"대요|래요",
}
MAIN = set(range(2, 16)) | set(range(17, 28)) | set(range(29, 34)) | set(range(35, 42)) | set(range(51, 71))
TOPIK1 = {"listening": 30, "reading": 40}


def forms(cards) -> set[str]:
    out: set[str] = set()
    for v in cards:
        out |= ls.card_forms(v.hangul)
    return out


def main() -> int:
    b = ls.load_all()
    rows: list[tuple[str, bool, str, bool]] = []  # code, passed, detail, hard

    def add(code: str, ok: bool, detail: str, hard: bool = True) -> None:
        rows.append((code, ok, detail, hard))

    lessons = sorted(b.lessons, key=lambda r: ls.course_position(r.seed))
    add("SEED", not b.problems, f"{len(b.problems)} seed problems")

    dup = [(r.seed.slug, h) for r in lessons for h, n in Counter(v.hangul for v in r.seed.vocab).items() if n > 1]
    add("DB-02 no duplicate card in a lesson", not dup, f"{len(dup)} duplicates {dup[:5]}")
    first: dict[str, str] = {}
    cross = []
    for r in lessons:
        for v in r.seed.vocab:
            if v.hangul in first:
                cross.append((v.hangul, first[v.hangul], r.seed.slug))
            first.setdefault(v.hangul, r.seed.slug)
    add("DB-02 no word taught twice across lessons", not cross, f"{len(cross)} repeats {cross[:5]}", hard=False)

    orders = sorted(r.seed.sort_order for r in lessons)
    levels = [r.seed.level for r in lessons]
    gaps = [(a, b2) for a, b2 in zip(levels, levels[1:]) if b2 - a > 1 or b2 < a]
    add("DB-03 sort_order 1..72", orders == list(range(1, 73)), f"{orders[:3]}…{orders[-3:]} ({len(orders)})")
    add("DB-03 levels 1..6 without a gap", sorted(set(levels)) == [1, 2, 3, 4, 5, 6] and not gaps,
        f"levels {sorted(set(levels))}, jumps {gaps}")

    early = [r for r in lessons if r.seed.sort_order <= 16]
    words = forms(v for r in early for v in r.seed.vocab)
    patterns = " | ".join(g.pattern for r in early for g in r.seed.grammar)
    n16 = sum(len(r.seed.vocab) for r in early)
    add("CUR-01 words in lessons 1–16", n16 >= 1000, f"{n16} cards")
    for name, wanted in (("position nouns", POSITION), ("connectors", CONNECTORS), ("frequency/time adverbs", FREQUENCY)):
        miss = sorted(wanted - words)
        add(f"CUR-01 {name} in 1–16", not miss, f"{len(wanted) - len(miss)}/{len(wanted)} missing {miss}")
    # -(으)시겠어요 and -아/어 줄게요 need -(으)시- and -아/어 주다 (lesson 17), so they come in lesson 18
    by18 = " | ".join(g.pattern for r in lessons if r.seed.sort_order <= 18 for g in r.seed.grammar)
    late = {"-(으)시겠어요", "-아/어 줄게요"}
    miss = [k for k, rx in KGIU.items() if not re.search(rx, by18 if k in late else patterns)]
    add("CUR-01 KGIU beginner patterns in 1–16", not miss, f"{len(KGIU) - len(miss)}/{len(KGIU)} missing {miss}")
    cov, _ = ls.nikl_coverage(b.lessons)
    add("CUR-01 NIKL 초급 list", cov.get("missing", 0) <= cov.get("excused", 0), str(cov))

    cards = [v for r in lessons for v in r.seed.vocab]
    def share(pred) -> str:
        return f"{sum(1 for v in cards if pred(v)) * 100 // max(1, len(cards))}%"
    add("CUR-02 meaning + example on every card", all(v.meaning_vi and v.example_ko for v in cards),
        f"meaning {share(lambda v: v.meaning_vi)}, example {share(lambda v: v.example_ko)}, "
        f"hanja {share(lambda v: v.hanja)}, Hán–Việt {share(lambda v: v.sino_vietnamese)}, "
        f"collocations {share(lambda v: getattr(v, 'collocations', None))}", hard=False)
    gr = [g for r in lessons for g in r.seed.grammar]
    def gshare(attr) -> str:
        return f"{sum(1 for g in gr if getattr(g, attr, None)) * 100 // max(1, len(gr))}%"
    add("CUR-03 grammar richness", all(g.meaning_vi and g.example_ko for g in gr),
        ", ".join(f"{a} {gshare(a)}" for a in ("usage_context_vi", "topik_tip_vi", "contrasts", "example_ko", "example_vi")),
        hard=False)

    ex = b.exercises if hasattr(b, "exercises") else {}
    no_text = []
    for r in lessons:
        if r.seed.sort_order not in MAIN:
            continue
        items = [ex.get(i, {}) for i in r.seed.exercise_ids]
        if not any(i.get("type") == "write_essay" for i in items):
            no_text.append(r.seed.sort_order)
    add("CUR-04 a text of the learner's own in every main lesson", not no_text, f"missing in {no_text}")
    mock = next((r for r in lessons if r.seed.sort_order == 16), None)
    if mock is not None:
        items = [ex.get(i, {}) for i in mock.seed.exercise_ids]
        n = Counter(i.get("skill") for i in items)
        add("CUR-04 lesson 16 = TOPIK I (30 listening + 40 reading)",
            all(n.get(k, 0) >= v for k, v in TOPIK1.items()), f"{dict(n)}")

    width = max(len(c) for c, *_ in rows)
    failed = 0
    for code, ok, detail, hard in rows:
        mark = "PASS" if ok else ("FAIL" if hard else "INFO")
        failed += (not ok) and hard
        print(f"{mark:4}  {code:<{width}}  {detail}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

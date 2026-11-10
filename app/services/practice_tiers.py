"""Vừa sức / Thử thách: how much of a practice item a learner can already read, and the
question types they meet for the first time.

A learner who follows the course has met the words of every earlier lesson (its cards, its
examples and its practice). An item whose running text is mostly those words (plus the words of
its own lesson) is "Vừa sức"; a long item with many words not met yet is "Thử thách": an exam-
style passage the lesson keeps, shown after the rest so the learner arrives with the lesson's
words in hand. Research on reading a foreign language puts unaided comprehension at about 95–98%
of running words known; MIN_COVERAGE is lower on purpose — the lesson's own words and the
explanation after each answer carry the rest.

Measuring needs a Korean morphological analyser (kiwipiepy), which the server does not ship: the
measures are worked out once, here, and kept in app/seed/practice_tiers.json:

    python -m app.services.practice_tiers --build    # after editing lessons or exercises
    python -m app.services.practice_tiers --check    # is the file in step with the seed?

At start-up, lesson_seed only reads the file (`apply`). Each entry keeps a fingerprint of the
item's Korean text, so a stale entry is reported by --check instead of mislabelling an item.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable

from pydantic import BaseModel, ConfigDict, Field

SEED_DIR = Path(__file__).resolve().parent.parent / "seed"
TIERS_FILE = SEED_DIR / "practice_tiers.json"
TYPES_FILE = SEED_DIR / "exams" / "types.json"
TIPS_FILE = SEED_DIR / "practice_type_tips.json"
SUPPORT_FILE = SEED_DIR / "practice_support.json"

# an item is "Thử thách" when it is long enough to be a passage and too many of its words are new
MIN_WORDS = 20
MIN_COVERAGE = 85  # % of running content words already met
# "Tạo câu" is a ladder of its own (rung 1 → 4): it keeps its order and is never split
UNTIERED_SKILLS = frozenset({"build"})

_KO = re.compile("[가-힣]")
# what is NOT text the learner must understand to answer: labels, answer keys, and the help that
# comes with an item (a model answer, phrases to borrow, extra prompts for more practice)
_SKIP_KEYS = frozenset(
    {
        "id", "tags", "plan", "instruction_ko", "grammar", "focus", "answer", "answers", "number", "accepted",
        "model", "model_answer_ko", "phrases_ko", "practice", "support",
    }
)
_CONTENT_TAGS = frozenset({"NNG", "NNP", "XR", "MAG", "VV", "VA"})


def korean_strings(obj: Any) -> Iterable[str]:
    if isinstance(obj, str):
        if _KO.search(obj):
            yield obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            if k in _SKIP_KEYS or k.endswith("_vi"):
                continue
            yield from korean_strings(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from korean_strings(v)


def fingerprint(item: dict[str, Any]) -> str:
    return hashlib.sha1("\n".join(korean_strings(item)).encode()).hexdigest()[:12]


# ------------------------------------------------------------------- at start-up --
@lru_cache(maxsize=1)
def _tiers() -> dict[str, Any]:
    if not TIERS_FILE.is_file():
        return {"lessons": {}, "first_seen": {}}
    return json.loads(TIERS_FILE.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def type_guides() -> dict[str, dict[str, str]]:
    """type -> {name_vi, how_vi}: one line on how to do a question type, for its first meeting."""
    out: dict[str, dict[str, str]] = {}
    if TYPES_FILE.is_file():
        for code, t in json.loads(TYPES_FILE.read_text(encoding="utf-8")).get("types", {}).items():
            how = (t.get("tips") or t.get("steps") or [""])[0]
            out[code] = {"name_vi": t["name_vi"], "how_vi": how}
    if TIPS_FILE.is_file():
        for code, t in json.loads(TIPS_FILE.read_text(encoding="utf-8")).get("types", {}).items():
            name = t.get("name_vi") or out.get(code, {}).get("name_vi")
            if name:
                out[code] = {"name_vi": name, "how_vi": t["how_vi"]}
    return out


class SupportWord(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ko: str = Field(min_length=1)  # dictionary form
    seen: str = Field(min_length=1)  # as it appears in the item (checked)
    vi: str = Field(min_length=1)  # its meaning in THIS text


class SupportGrammar(BaseModel):
    model_config = ConfigDict(extra="forbid")
    form: str = Field(min_length=1)
    seen: str = Field(min_length=1)
    vi: str = Field(min_length=1)
    lesson: str | None  # slug of the lesson that teaches it; None: no lesson does yet


class Support(BaseModel):
    """Help before a hard item, written by hand (app/seed/practice_support.json)."""

    model_config = ConfigDict(extra="forbid")
    words: list[SupportWord] = Field(default_factory=list, max_length=12)
    grammar: list[SupportGrammar] = Field(default_factory=list, max_length=10)
    focus_vi: str = Field(min_length=1)  # hint 1: what to look for
    options_vi: dict[str, list[str]] = Field(default_factory=dict)  # hint 2: question id -> options in Vietnamese
    elim: dict[str, str] = Field(default_factory=dict)  # hint 3: question id -> one wrong option


@lru_cache(maxsize=1)
def supports() -> dict[str, dict[str, Support]]:
    """lesson slug -> exercise id -> its help in that lesson."""
    if not SUPPORT_FILE.is_file():
        return {}
    raw = json.loads(SUPPORT_FILE.read_text(encoding="utf-8")).get("lessons", {})
    return {slug: {k: Support.model_validate(v) for k, v in items.items()} for slug, items in raw.items()}


def support_problems(items: dict[tuple[str, str], dict[str, Any]], orders: dict[str, int]) -> list[str]:
    """`items`: (lesson slug, exercise id) -> the item; `orders`: slug -> sort_order."""
    out: list[str] = []
    for slug, ex_id, sup in ((s, e, x) for s, by in supports().items() for e, x in by.items()):
        it = items.get((slug, ex_id))
        if it is None:
            out.append(f"practice_support.json: {ex_id} is not in lesson {slug}")
            continue
        text = "\n".join(korean_strings(it))
        for w in sup.words:
            if w.seen not in text:
                out.append(f"practice_support.json: {ex_id}: word {w.seen!r} is not in the item")
        for g in sup.grammar:
            if g.seen not in text:
                out.append(f"practice_support.json: {ex_id}: grammar {g.seen!r} is not in the item")
            if g.lesson is not None:
                if g.lesson not in orders:
                    out.append(f"practice_support.json: {ex_id}: unknown lesson {g.lesson}")
                elif orders[g.lesson] <= orders[slug]:
                    out.append(f"practice_support.json: {ex_id}: {g.form} is taught by {g.lesson}, not ahead of {slug}")
        questions = {q["id"]: q for q in it.get("questions") or []}
        for qid, opts in sup.options_vi.items():
            q = questions.get(qid)
            if q is None:
                out.append(f"practice_support.json: {ex_id}: no question {qid}")
            elif len(opts) != len(q["options"]):
                out.append(f"practice_support.json: {ex_id}: {qid} has {len(q['options'])} options, {len(opts)} translations")
        for qid, opt in sup.elim.items():
            q = questions.get(qid)
            if q is None or opt not in {o["id"] for o in q["options"]}:
                out.append(f"practice_support.json: {ex_id}: {qid} has no option {opt}")
            elif opt == q["answer"]:
                out.append(f"practice_support.json: {ex_id}: {qid} crosses out the right answer")
    return out


def is_challenge(m: dict[str, Any]) -> bool:
    return m["n"] >= MIN_WORDS and m["cov"] < MIN_COVERAGE


def apply(slug: str, practice: dict[str, Any]) -> None:
    """Tag a lesson's practice in place: `tier` ("warm" / "challenge") and `new_words` on each
    measured item, the challenges moved after the rest of their skill (stable), and
    `type_intro` for the question types this lesson is the first to use."""
    kind = practice.get("kind")
    if kind in ("hangul", "review"):
        return  # the alphabet has its own flow; a topic review is a timed mock in its set order
    measures: dict[str, Any] = _tiers()["lessons"].get(slug, {})
    items: list[dict[str, Any]] = practice["items"]
    helps = supports().get(slug, {})
    for it in items:
        if it["id"] in helps:
            it["support"] = helps[it["id"]].model_dump(mode="json")
        m = measures.get(it["id"])
        if m is None or m["fp"] != fingerprint(it) or it["skill"] in UNTIERED_SKILLS:
            continue
        it["tier"] = "challenge" if is_challenge(m) else "warm"
        if m["new"]:
            it["new_words"] = m["new"]
    # warm first within each skill; the skills' own order is kept (the screen shows one at a time)
    items.sort(key=lambda it: it.get("tier") == "challenge")
    guides = type_guides()
    first = {t for t, s in _tiers()["first_seen"].items() if s == slug}
    intro = {t: guides[t] for t in sorted(first) if t in guides and any(it["type"] == t for it in items)}
    if intro:
        practice["type_intro"] = intro


# ---------------------------------------------------------------- building --------
def build() -> dict[str, Any]:
    from kiwipiepy import Kiwi  # noqa: PLC0415 — an editor's tool, not a server dependency

    from app.services.lesson_seed import load_all  # noqa: PLC0415

    kiwi = Kiwi()
    cache: dict[str, list[str]] = {}

    def words(text: str) -> list[str]:
        if text not in cache:
            out = []
            for t in kiwi.tokenize(text):
                tag = t.tag.split("-")[0]
                if tag in _CONTENT_TAGS:
                    out.append(t.form + ("다" if tag in ("VV", "VA") else ""))
            cache[text] = out
        return cache[text]

    def lesson_words(seed: Any) -> set[str]:
        got: set[str] = set()
        for v in seed.vocab:
            got.add(v.hangul.strip())
            got |= set(words(v.hangul))
            if v.example_ko:
                got |= set(words(v.example_ko))
        for g in seed.grammar:
            if g.example_ko:
                got |= set(words(g.example_ko))
        return got

    bundle = load_all()
    if bundle.problems:
        raise SystemExit("seed has problems; fix them first:\n" + "\n".join(bundle.problems[:20]))
    known: set[str] = set()  # met in an earlier lesson (cards, examples, practice)
    lessons: dict[str, dict[str, Any]] = {}
    first_seen: dict[str, str] = {}
    for r in sorted(bundle.lessons, key=lambda r: r.seed.sort_order):
        own = lesson_words(r.seed)
        items = (r.practice or {}).get("items") or []
        out: dict[str, Any] = {}
        # a question type is introduced where `apply` can show it: not in the alphabet's own flow,
        # not in a timed review, not on the "Tạo câu" ladder (it has its own steps)
        introduces = (r.practice or {}).get("kind") not in ("hangul", "review")
        for it in items:
            if introduces and it["skill"] not in UNTIERED_SKILLS:
                first_seen.setdefault(it["type"], r.seed.slug)
            running = [w for s in korean_strings(it) for w in words(s)]
            met = sum(1 for w in running if w in known or w in own)
            new = sorted({w for w in running if w not in known and w not in own})
            out[it["id"]] = {
                "fp": fingerprint(it),
                "n": len(running),
                "cov": round(100 * met / len(running)) if running else 100,
                "new": len(new),
            }
        lessons[r.seed.slug] = out
        known |= own
        for it in items:
            for s in korean_strings(it):
                known |= set(words(s))
    return {
        "about": "Made by `python -m app.services.practice_tiers --build`; do not edit by hand.",
        "rule": {"min_words": MIN_WORDS, "min_coverage": MIN_COVERAGE},
        "first_seen": dict(sorted(first_seen.items())),
        "lessons": lessons,
    }


def stale() -> list[str]:
    """Items whose Korean text changed (or that are new) since the file was built, and mistakes in
    practice_support.json."""
    if not TIERS_FILE.is_file():
        return []
    from app.services.lesson_seed import load_all  # noqa: PLC0415

    data = _tiers()["lessons"]
    out = []
    lessons = load_all().lessons
    items = {(r.seed.slug, it["id"]): it for r in lessons for it in (r.practice or {}).get("items") or []}
    out += support_problems(items, {r.seed.slug: r.seed.sort_order for r in lessons})
    for r in lessons:
        if (r.practice or {}).get("kind") in ("hangul", "review"):
            continue
        for it in (r.practice or {}).get("items") or []:
            m = data.get(r.seed.slug, {}).get(it["id"])
            if m is None or m["fp"] != fingerprint(it):
                out.append(f"{r.seed.slug}: {it['id']} changed since practice_tiers.json was built")
    return out


def main(argv: list[str]) -> int:
    if "--build" in argv:
        data = build()
        TIERS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        n = sum(len(v) for v in data["lessons"].values())
        hard = sum(is_challenge(m) for v in data["lessons"].values() for m in v.values())
        print(f"{TIERS_FILE.name}: {n} items, {hard} Thử thách")
        return 0
    if "--check" in argv:
        bad = stale()
        for line in bad:
            print("PROBLEM:", line)
        missing = sorted(set(_tiers()["first_seen"]) - set(type_guides()))
        for t in missing:
            print("no type guide:", t)
        return 1 if bad or missing else 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

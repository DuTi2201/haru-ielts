"""Write hand-planned sittings (`sessions`) into lesson seed files.

    python scripts/set_sessions.py plans/nen-tang-1.py ...

A plan file defines PLANS = {slug: [session, ...]}; a session is a dict with title_vi, can_do_vi,
use_vi, topik_vi, vocab, grammar, check (see app.services.lesson_seed.SessionSeed). A vocab entry
may be a `headword` or "family:<name>" (every word of that family not yet used, in lesson order).
The result is written literally into app/seed/lessons/<slug>.json and validated by LessonSeed.
"""
import json
import runpy
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

SEED = Path(__file__).resolve().parent.parent / "app" / "seed" / "lessons"


def expand(lesson: dict, sessions: list[dict]) -> list[dict]:
    used: set[str] = set()
    for s in sessions:
        for w in s.get("vocab", []):
            if not w.startswith("family:"):
                used.add(w)
    out = []
    for si, s in enumerate(sessions):
        vocab: list[str] = []
        for w in s.get("vocab", []):
            if w == "rest":
                # every word no sitting names (and none earlier took), in lesson order
                named = {x for t in sessions for x in t.get("vocab", []) if x not in ("rest",) and not x.startswith("family:")}
                done = {x for t in out for x in t["vocab"]}
                vocab += [v["headword"] for v in lesson["vocab"] if v["headword"] not in named and v["headword"] not in done and v["headword"] not in vocab]
            elif w.startswith("family:"):
                fam = w[len("family:"):]
                vocab += [v["headword"] for v in lesson["vocab"] if fam in (v.get("family") or "") and v["headword"] not in used and v["headword"] not in vocab]
            else:
                vocab.append(w)
        used.update(vocab)
        out.append({**s, "vocab": vocab})
    return out


SKILL_ORDER = ["listening", "reading", "build"]


def _stem(w: str) -> str | None:
    w = w.split("/")[0].split("(")[0].strip().split(" ")[0]
    if w.endswith("다") and len(w) > 2:
        w = w[:-1]
    return w if len(w) >= 2 else None


def _text(it: dict) -> str:
    st = it.get("stimulus") or {}
    parts = [st.get("text") or "", it.get("meaning_vi") or ""]
    parts += [t.get("text", "") for t in st.get("turns", [])]
    parts += [o.get("text", "") for q in it.get("questions") or [] for o in q.get("options", [])]
    return " ".join(parts)


def _nq(it: dict) -> int:
    return len(it.get("questions") or []) or len(it.get("blanks") or []) or 1


def pick_checks(lesson: dict, items: list[dict], sessions: list[dict]) -> None:
    """A session with "pick": N gets about N closing questions: items that test one of the session's
    own cards and no card taught after it, one skill after the other (listening, reading, build),
    never an item already given to another session."""
    own = {g["pattern"] for g in lesson["grammar"]}
    taught: set[str] = set()
    used = {i for x in sessions for i in x.get("check", [])}
    for sess in sessions:
        taught |= set(sess.get("grammar", []))
        n = sess.pop("pick", 0)
        if not n:
            continue
        mine = set(sess.get("grammar", []))
        cands = []
        for it in items:
            if it["id"] in used or it["type"] == "write_essay":
                continue
            tags = set(it.get("grammar") or [])
            for q in it.get("questions") or []:
                tags |= set(q.get("grammar") or [])
            tags &= own
            if tags & mine and tags <= taught:
                cands.append(it)
        chosen: list[dict] = []
        total = 0
        by_skill = {k: [c for c in cands if c.get("skill") == k] for k in SKILL_ORDER}
        while total < n and any(by_skill.values()):
            for k in SKILL_ORDER:
                if by_skill[k] and total < n:
                    it = by_skill[k].pop(0)
                    if total + _nq(it) > n + 1 and chosen:
                        continue
                    chosen.append(it)
                    total += _nq(it)
        # then items that USE this sitting's words (a closed item, no card taught later)
        want = sess.pop("pick_words", 0)
        if want:
            stems = [x for x in (_stem(w) for w in sess.get("vocab", [])) if x]
            got = 0
            for it in items:
                if got >= want or it["id"] in used or it in chosen:
                    continue
                if it["type"] in ("write_essay", "speak") or "stimulus" not in it and it["type"] != "build_order":
                    continue
                tags = set(it.get("grammar") or [])
                for q in it.get("questions") or []:
                    tags |= set(q.get("grammar") or [])
                if (tags & own) - taught:
                    continue
                if any(st in _text(it) for st in stems) and _nq(it) <= 3:
                    chosen.append(it)
                    got += _nq(it)
        for it in chosen:
            used.add(it["id"])
        sess["check"] = list(sess.get("check", [])) + [it["id"] for it in chosen]


def main(paths: list[str]) -> None:
    from app.services.lesson_seed import load_all

    bundle = {r.seed.slug: r for r in load_all().lessons}
    for p in paths:
        plans = runpy.run_path(p)["PLANS"]
        for slug, sessions in plans.items():
            f = SEED / f"{slug}.json"
            lesson = json.loads(f.read_text(encoding="utf-8"))
            sessions = expand(lesson, sessions)
            pick_checks(lesson, bundle[slug].practice["items"], sessions)
            lesson["sessions"] = sessions
            f.write_text(json.dumps(lesson, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print("wrote", slug, len(lesson["sessions"]), "sittings")


if __name__ == "__main__":
    main(sys.argv[1:])

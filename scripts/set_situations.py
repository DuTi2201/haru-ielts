"""Write a short dialogue situation into each hand-planned sitting of lesson seed files.

    python scripts/set_situations.py scripts/situations/so-cap-01.py ...

A situation file defines SITUATIONS = {slug: [one entry per sitting, in order, or None]} where an
entry is a dict:
    scene   : where and who (Vietnamese)
    turns   : [("A", ko, vi), ("B", ko, vi), ...]   4–6 turns, in the right order
    reply   : (prompt_en, prompt_vi, [(ko, vi, ok, why_vi) x3])  exactly one ok
    compare : (ask_vi, (ko, vi), (ko, vi), "a" or "b", why_vi)
The result is written into app/seed/lessons/<slug>.json under sessions[i].situation and validated by
LessonSeed (app.services.lesson_seed.SituationSeed). Sittings are not touched otherwise.
"""
import json
import runpy
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

SEED = Path(__file__).resolve().parent.parent / "app" / "seed" / "lessons"


def convert(e: dict) -> dict:
    ask, a, b, better, why = e["compare"]
    pk, pv, opts = e["reply"]
    return {
        "scene_vi": e["scene"],
        "turns": [{"who": w, "ko": k, "vi": v} for w, k, v in e["turns"]],
        "reply": {
            "prompt_en": pk,
            "prompt_vi": pv,
            "options": [{"ko": k, "vi": v, "ok": bool(ok), "why_vi": y} for k, v, ok, y in opts],
        },
        "compare": {
            "ask_vi": ask,
            "a": {"ko": a[0], "vi": a[1]},
            "b": {"ko": b[0], "vi": b[1]},
            "better": better,
            "why_vi": why,
        },
    }


def main(files: list[str]) -> None:
    from app.services.lesson_seed import LessonSeed

    for f in files:
        data = runpy.run_path(f)["SITUATIONS"]
        for slug, entries in data.items():
            path = SEED / f"{slug}.json"
            lesson = json.loads(path.read_text(encoding="utf8"))
            sessions = lesson.get("sessions") or []
            if len(entries) != len(sessions):
                raise SystemExit(f"{slug}: {len(entries)} situations for {len(sessions)} sittings")
            for s, e in zip(sessions, entries):
                if e is None:
                    s.pop("situation", None)
                else:
                    s["situation"] = convert(e)
            LessonSeed.model_validate(lesson)
            path.write_text(json.dumps(lesson, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
            print(f"{slug}: {sum(1 for e in entries if e)} situations")


if __name__ == "__main__":
    main(sys.argv[1:])

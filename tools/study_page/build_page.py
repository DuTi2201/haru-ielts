"""Build one self-contained HTML page of the Destination B1 course from the seed.

    python3 tools/study_page/build_page.py      # writes tools/study_page/dist/b1-study.html

A stop-gap so the course can be studied before the app is deployed. No server: cards, questions,
dictation read by the browser's own English voice, speaking prompts with a timer and a model
answer. Progress lives in the browser's localStorage (one device, may be cleared).
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SEED = ROOT / "app" / "seed"
OUT = Path(__file__).resolve().parent / "dist" / "b1-study.html"


def compact_exercise(e: dict) -> dict:
    t = e["type"]
    if t == "read_passage":
        return {"k": "p", "title": e["title_vi"], "text": e["stimulus"]["text"], "tip": e["instruction_vi"],
                "qs": [{"q": q["prompt_en"], "o": [o["text"] for o in q["options"]], "a": int(q["answer"]) - 1, "w": q["explanation_vi"]} for q in e["questions"]]}
    if t == "write_essay":
        return {"k": "w", "en": e["prompt_en"], "vi": e["instruction_vi"], "frame": e["framework_vi"], "check": e["checklist_vi"], "model": e["model_answer_en"]}
    if t in ("read_cloze", "read_match"):
        q = e["questions"][0]
        return {"k": "m", "q": (e.get("stimulus") or {}).get("text") or q.get("prompt_vi"), "h": q.get("prompt_vi") if e.get("stimulus") else None, "o": [o["text"] for o in q["options"]],
                "a": int(q["answer"]) - 1, "w": q["explanation_vi"]}
    if t == "build_order":
        return {"k": "b", "vi": e["meaning_vi"], "t": e["tiles"], "ans": e["answers"]}
    if t == "write_fill":
        b = e["blanks"][0]
        return {"k": "f", "q": e["text"], "acc": b["accepted"], "w": b.get("common_errors_vi") or ""}
    if t == "listen_dictation":
        return {"k": "d", "t": [[x["text"], x["vi"]] for x in e["stimulus"]["turns"]]}
    return {"k": "s", "en": e["prompt_en"], "vi": e.get("prompt_vi"), "model": e["model_answer_en"], "plan": [[p["when_vi"], p["do_vi"]] for p in e["plan"]]}


def main() -> None:
    ex = {}
    for f in sorted((SEED / "exercises" / "b1").glob("*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        for it in d.get("items", []):
            ex[it["id"]] = compact_exercise(it)
    lessons = []
    for f in sorted((SEED / "lessons").glob("b1-*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        lessons.append({
            "n": d["sort_order"], "t": d["title"], "en": d["title_en"],
            "notes": [[x.get("title"), x["body"]] for x in d["notes"]],
            "cards": [{"p": g["pattern"], "m": g["meaning_vi"], "u": g.get("usage_context_vi"), "e": g.get("example_en"), "ev": g.get("example_vi"),
                       "n": g.get("note_vi"), "tip": g.get("exam_tip_vi"), "vs": [[c["pattern"], c["diff_vi"]] for c in g.get("contrasts", [])]}
                      for g in d.get("grammar", [])],
            "words": [{"h": v["headword"], "m": v["meaning_vi"], "f": v.get("family"), "e": v.get("example_en"), "ev": v.get("example_vi"), "n": v.get("note_vi")}
                      for v in d["vocab"]],
            "ses": [{"t": s["title_vi"], "can": s["can_do_vi"], "v": s.get("vocab", []), "g": s.get("grammar", []), "c": s.get("check", [])} for s in d["sessions"]],
            "ex": d["exercise_ids"],
        })
    lessons.sort(key=lambda x: x["n"])
    data = json.dumps({"lessons": lessons, "ex": ex}, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    html = (Path(__file__).resolve().parent / "template.html").read_text(encoding="utf-8").replace("/*DATA*/null", data)
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(html, encoding="utf-8")
    print(OUT, len(html) // 1024, "KiB", len(lessons), "lessons", len(ex), "exercises")


if __name__ == "__main__":
    main()

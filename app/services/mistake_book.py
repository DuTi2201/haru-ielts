"""Sổ lỗi sai: the practice questions a learner currently has wrong, written out so they can be read
again away from the lesson.

`lesson_exercise_result` keeps the learner's latest answer to each practice question (right or
wrong, how many tries, what they chose or typed); the question itself, its right answer and its
explanation ship with the lesson's `practice`. This module joins the two for ONE wrong answer. It is
plain functions over plain dicts, so the rules are tested against the real seed lessons without a
database.

A mistake is a question whose *latest* answer is wrong: answering it right removes it from the book
by itself. An essay and a speaking task are scored by the learner (a number out of the points), so
there is no "wrong answer" to show for them and they are not in the book.
"""
from __future__ import annotations

from typing import Any

# scored by the learner themselves (a number out of the points), not right or wrong
SELF_SCORED_TYPES = ("write_essay", "speak")

SKILL_LABEL = {
    "listening": "Nghe",
    "reading": "Đọc",
    "writing": "Viết",
    "build": "Tạo câu",
    "speaking": "Nói",
}

MAX_CONTEXT_CHARS = 700  # a passage is shown as a reminder, not in full
MAX_CONTEXT_LINES = 12


def in_book(exercise: dict[str, Any]) -> bool:
    """Whether a wrong answer to this exercise can be shown as a mistake."""
    return exercise.get("type") not in SELF_SCORED_TYPES


def _clip(text: str) -> str:
    text = " ".join(str(text).split())
    return text if len(text) <= MAX_CONTEXT_CHARS else text[: MAX_CONTEXT_CHARS - 1].rstrip() + "…"


def _line(text: str, vi: str | None = None, speaker: str | None = None) -> dict[str, str]:
    out = {"text": _clip(text)}
    if vi:
        out["vi"] = _clip(vi)
    if speaker:
        out["speaker"] = speaker
    return out


def context_of(exercise: dict[str, Any]) -> list[dict[str, str]]:
    """What the question was about, as lines: the transcript of what was heard, the passage that was
    read, the notice. A chart is a picture, so it has no lines (the lesson shows it)."""
    st = exercise.get("stimulus") or {}
    kind = st.get("kind")
    if kind == "audio":
        return [_line(t["text"], t.get("vi"), t.get("speaker")) for t in st.get("turns", [])][:MAX_CONTEXT_LINES]
    if kind in ("cloze", "passage", "underline"):
        return [_line(st["text"])] if st.get("text") else []
    if kind == "headline":
        return [_line(st["text"], st.get("hint_vi"))] if st.get("text") else []
    if kind == "notice":
        lines = [_line(st["title"])] if st.get("title") else []
        lines += [_line(x) for x in st.get("lines", [])]
        return lines[:MAX_CONTEXT_LINES]
    if kind == "order":
        return [_line(f"{i['id']}. {i['text']}") for i in st.get("items", [])][:MAX_CONTEXT_LINES]
    if kind == "insert":
        return [_line(f"Câu cần chèn: {st['given']}")] + ([_line(st["text"])] if st.get("text") else [])
    return []


def _option_text(option: dict[str, Any]) -> str:
    if option.get("text"):
        return str(option["text"])
    scene = option.get("scene")
    if scene and scene.get("caption_vi"):
        return str(scene["caption_vi"])
    if option.get("chart"):
        return f"Biểu đồ {option['id']}"
    return f"Phương án {option['id']}"


def _joined(items: list[str]) -> str:
    return " / ".join(i for i in items if i)


def entry(exercise: dict[str, Any], question_id: str, last_answer: str | None) -> dict[str, Any] | None:
    """One wrong answer, written out; None when it cannot be (a self-scored exercise, or a question the
    lesson no longer has). `chosen` is what the learner picked or typed (an option's text, for a
    choice), `correct` the right answer(s); the rest is there to read it again."""
    if not in_book(exercise):
        return None
    out: dict[str, Any] = {
        "exercise_id": exercise["id"],
        "question_id": question_id,
        "type": exercise["type"],
        "skill": SKILL_LABEL.get(exercise.get("skill", ""), ""),
        "title": exercise.get("title_vi") or exercise["id"],
        "prompt": None,
        "context": [],
        "options": [],
        "chosen_id": None,
        "correct_id": None,
        "chosen": (last_answer or "").strip() or None,
        "correct": [],
        "explanation_vi": None,
        "notes_vi": [],
        "focus": [],
        "translation": [],
        "grammar": list(exercise.get("grammar") or []),
    }
    etype = exercise["type"]

    if etype == "build_order":
        out["prompt"] = exercise.get("meaning_vi")
        out["correct"] = list(exercise.get("answers") or [])[:2]
        out["explanation_vi"] = exercise.get("explain_vi")
        out["notes_vi"] = list(exercise.get("common_errors_vi") or [])
        return out

    if etype == "write_fill":
        blank_id = question_id.split(":", 1)[1] if ":" in question_id else question_id
        blank = next((b for b in exercise.get("blanks", []) if b["id"] == blank_id), None)
        if blank is None:
            return None
        out["prompt"] = f"Chỗ trống {blank_id}"
        out["context"] = [_line(exercise["text"])] if exercise.get("text") else []
        out["correct"] = list(blank.get("accepted") or [])[:3]
        if blank.get("common_errors_vi"):
            out["notes_vi"] = [f"Lỗi hay gặp: {blank['common_errors_vi']}"]
        return out

    if etype == "listen_dictation":
        turns = (exercise.get("stimulus") or {}).get("turns", [])
        # the typed lines were kept as one string, joined with " / "
        out["correct"] = [t["text"] for t in turns]
        out["notes_vi"] = list(exercise.get("tips_vi") or [])
        out["focus"] = list(exercise.get("focus") or [])
        out["translation"] = [t["vi"] for t in turns if t.get("vi")]
        return out

    # a multiple-choice question
    question = next((q for q in exercise.get("questions", []) if q["id"] == question_id), None)
    if question is None:
        return None
    options = [{"id": str(o["id"]), "text": _option_text(o)} for o in question.get("options", [])]
    out["prompt"] = question.get("prompt_ko") or question.get("prompt_vi") or exercise.get("instruction_vi")
    out["context"] = context_of(exercise)
    out["options"] = options
    out["correct_id"] = str(question["answer"])
    right = next((o["text"] for o in options if o["id"] == out["correct_id"]), None)
    out["correct"] = [right] if right else []
    if last_answer:
        out["chosen_id"] = str(last_answer)
        out["chosen"] = next((o["text"] for o in options if o["id"] == str(last_answer)), out["chosen"])
    out["explanation_vi"] = question.get("explanation_vi")
    out["grammar"] = list(question.get("grammar") or [])
    return out

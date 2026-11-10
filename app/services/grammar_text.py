"""The text of a grammar card, cut into the parts the app lays out separately.

The 🟣 extension cards keep their explanation in one string with a fixed shape, so the
database needs no extra columns:

    usage_context_vi:
        🟣 **Kiến thức mở rộng** · ✍ **Dùng được** …      <- the badge (see grammar_tier)
        **Cấu tạo:** …
        **Hoàn cảnh dùng:** …
        **Vì sao chọn nó thay vì X:** …
        **Trong bài này:** …
    note_vi:
        **Lỗi người Việt hay mắc:** …
        *Biên soạn bổ sung:* <where the content came from>   <- the last line

`usage_sections` returns the labelled parts (so the app can show "Cấu tạo" and "Hoàn cảnh
dùng" first and fold the longer reasoning away) and `split_source_note` takes the
provenance line out of the mistakes box (it is a footnote, not advice). Cards that do not
have this shape (the core cards) come back as one unlabelled part / unchanged — nothing is
ever dropped. Pure functions, shared by the API schema and the tests.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

SectionKey = Literal["form", "when", "why", "lesson", "level", "other"]

# **Label:** — or *Label:* with one star (the «Mức độ» line)
_LABEL = re.compile(r"^\*{1,2}(?P<label>[^*]+?):\*{1,2}\s*(?P<body>.*)$")
_EXTENSION_MARK = "🟣"
SOURCE_NOTE_PREFIX = "*Biên soạn bổ sung:*"


@dataclass(frozen=True)
class UsageSection:
    key: SectionKey
    label: str | None  # None for text that has no label
    body_vi: str


def _key_of(label: str) -> SectionKey:
    low = label.lower()
    if low.startswith("cấu tạo"):
        return "form"
    if low.startswith("hoàn cảnh"):
        return "when"
    if low.startswith("vì sao"):
        return "why"
    if low.startswith("trong bài này"):
        return "lesson"
    if low.startswith("mức độ"):
        return "level"
    return "other"


def usage_sections(usage_context_vi: str | None) -> list[UsageSection]:
    """The labelled parts of `usage_context_vi`, in order, without the badge line."""
    lines = (usage_context_vi or "").strip().split("\n")
    if lines and lines[0].lstrip().startswith(_EXTENSION_MARK):
        lines = lines[1:]  # the badge already says what this is
    sections: list[list] = []  # [key, label, [lines]]
    for line in lines:
        m = _LABEL.match(line.strip())
        if m:
            label = m.group("label").strip()
            sections.append([_key_of(label), label, [m.group("body").strip()]])
        elif line.strip():
            if not sections:
                sections.append(["other", None, []])
            sections[-1][2].append(line.strip())
    return [UsageSection(k, label, "\n".join(body).strip()) for k, label, body in sections if body]


def split_source_note(note_vi: str | None) -> tuple[str | None, str | None]:
    """(the note without its provenance line, the provenance text) — either can be None."""
    if not note_vi:
        return note_vi, None
    kept: list[str] = []
    source: str | None = None
    for line in note_vi.split("\n"):
        if line.strip().startswith(SOURCE_NOTE_PREFIX):
            source = line.strip()[len(SOURCE_NOTE_PREFIX) :].strip() or None
        else:
            kept.append(line)
    text = "\n".join(kept).strip()
    return (text or None), source

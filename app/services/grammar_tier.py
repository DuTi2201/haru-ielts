"""Which kind of knowledge a grammar card is, read from the card's own text.

Core cards come from the lesson sources. The "mở rộng" cards (👁 nhận ra / ✍ dùng
được) are authored additions that the exam sets use; their usage text opens with a
fixed marker line, so the tier needs no extra column in the database:

    🟣 **Kiến thức mở rộng** · 👁 **Nhận ra** …   -> ("extension", "recognize")
    🟣 **Kiến thức mở rộng** · ✍ **Dùng được** …  -> ("extension", "produce")
    anything else                                  -> ("core", None)

Pure functions, shared by the lesson seed, the API schemas and the tests.
"""
from __future__ import annotations

from typing import Literal

Tier = Literal["core", "extension"]
UseLevel = Literal["recognize", "produce"]

_EXTENSION_MARK = "🟣"
_RECOGNIZE_MARK = "👁"
_PRODUCE_MARK = "✍"


def grammar_tier(usage_context_vi: str | None) -> tuple[Tier, UseLevel | None]:
    text = (usage_context_vi or "").lstrip()
    if not text.startswith(_EXTENSION_MARK):
        return "core", None
    first_line = text.split("\n", 1)[0]
    if _PRODUCE_MARK in first_line and _RECOGNIZE_MARK not in first_line:
        return "extension", "produce"
    if _RECOGNIZE_MARK in first_line and _PRODUCE_MARK not in first_line:
        return "extension", "recognize"
    # an extension card must say which level it is; callers (and the tests) treat None as a bug
    return "extension", None


def effective_use_level(usage_context_vi: str | None, explicit: str | None = None) -> UseLevel:
    """How far a learner has to take a card: *recognise* it when reading or listening, or *use*
    it when writing and speaking. A level written on the card (`use_level` in the seed) wins; an
    extension card without one says it in its marker line; every other card is for use, since
    the learner's goals (TOPIK 4-5, KIIP 4-5) ask for production of the whole core.
    """
    if explicit in ("recognize", "produce"):
        return explicit  # type: ignore[return-value]
    return grammar_tier(usage_context_vi)[1] or "produce"


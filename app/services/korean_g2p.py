"""Pronunciation for the Korean voice (the "G2P" step before speech): a word whose standard
pronunciation (표준 발음) differs from its spelling is sent to the voice as it is SAID, while the
learner still sees it as written. The table is 한국어기초사전's own pronunciation of ~15,000 words
(app/seed/nikl/pronunciation.json); a word read two ways by meaning is not in it.

Only a whole word that stands alone between spaces or punctuation is replaced: a word followed by a
particle (`꽃이`) is linked differently from the word on its own (`꽃` [꼳] but `꽃이` [꼬치]), so it is
left to the voice. That is exactly the case of the alphabet lesson and of vocabulary cards (one word
said on its own), where a voice without context goes wrong most often."""
from __future__ import annotations

import json
import re
from functools import lru_cache
from html import escape
from pathlib import Path

LEXICON = Path(__file__).resolve().parents[1] / "seed" / "nikl" / "pronunciation.json"
_TOKEN = re.compile(r"[가-힣]+|[^가-힣]+")


@lru_cache(maxsize=1)
def lexicon() -> dict[str, str]:
    return json.loads(LEXICON.read_text(encoding="utf-8"))["words"]


def pronounce(word: str) -> str | None:
    """How a standalone word is said, when that differs from how it is written."""
    return lexicon().get(word)


def to_ssml_body(text: str) -> str:
    """The text as SSML body: standalone words with a different pronunciation are wrapped in
    <sub alias="said">written</sub>; everything else is escaped as it is."""
    out = []
    for tok in _TOKEN.findall(text):
        said = pronounce(tok) if re.fullmatch(r"[가-힣]+", tok) else None
        out.append(f'<sub alias="{escape(said)}">{escape(tok)}</sub>' if said else escape(tok))
    return "".join(out)

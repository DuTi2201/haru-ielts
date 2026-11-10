"""Reusing a picture that already exists instead of drawing a new one.

A picture is filed under its prompt, so the same word in two lessons is one picture for free.
Two DIFFERENT words with the same meaning (a noun and its verb: 샤워 / 샤워하다; synonyms:
일어나다 / 기상) are two prompts and, left alone, two paid drawings of nearly the same thing.
This module finds, for every word that has no picture yet, the words that already have one
and mean the same, so an editor can reuse that picture with one click (the picture is copied
under the new word's key: no Gemini call, and the two stay independent afterwards — hide or
redraw one without touching the other).

Matching is on the Vietnamese meaning, which every word has, and on the shape of the Korean
(X ↔ X하다 / X되다). Only words are matched: a lesson banner, a grammar illustration or a
scene is specific to its place, and a picture there is never offered for reuse.

Pure functions, no database: the caller passes the slots and which pictures exist."""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

MAX_CANDIDATES = 3

# "sự thức dậy" and "thức dậy" are the same thing; so are "cái bàn" and "bàn"
_LEADING_WORDS = ("sự", "việc", "cái", "con", "chiếc")
_SPLIT = re.compile(r"[/;,|]")
_NOT_WORD = re.compile(r"[^\w\s]", re.UNICODE)
_VERB_SUFFIXES = ("하다", "되다")


def senses(meaning: str | None) -> frozenset[str]:
    """The separate meanings in a gloss: "Buổi sáng / Bữa sáng" -> {"buổi sáng", "bữa sáng"};
    lower case, no punctuation, no leading "sự / việc / cái / con"."""
    out: set[str] = set()
    for part in _SPLIT.split(unicodedata.normalize("NFC", meaning or "").lower()):
        part = " ".join(_NOT_WORD.sub(" ", part).split())
        for lead in _LEADING_WORDS:
            if part.startswith(lead + " "):
                part = part[len(lead) + 1 :]
                break
        if len(part) >= 2:
            out.add(part)
    return frozenset(out)


def stem(headword: str) -> str:
    """샤워하다 -> 샤워, 완성되다 -> 완성: the noun a verb is made on."""
    text = unicodedata.normalize("NFC", headword or "").strip()
    for suffix in _VERB_SUFFIXES:
        if text.endswith(suffix) and len(text) > len(suffix):
            return text[: -len(suffix)]
    return text


@dataclass(frozen=True)
class Candidate:
    key: str  # the existing picture
    label: str  # the word it was made for
    meaning: str | None
    why: str  # one line for the editor
    confident: bool  # safe to apply without looking (offered in bulk)


def _why(target: Any, other: Any, shared: frozenset[str], same_stem: bool, same_senses: bool) -> str:
    sense = sorted(shared, key=len)[0] if shared else ""
    if same_stem and shared:
        return f'Cùng gốc với {other.label} · cùng nghĩa "{sense}"'
    if same_senses:
        return f'Cùng nghĩa với {other.label}: "{sense}"'
    if shared:
        return f'Chung nghĩa "{sense}" với {other.label}'
    return f"Cùng gốc từ với {other.label}"


def suggest(groups: Sequence[Any], stored: Mapping[str, Any]) -> dict[str, list[Candidate]]:
    """For each word slot whose picture does not exist yet: up to MAX_CANDIDATES existing,
    visible word pictures that mean the same, best first. `groups` are LessonSlots (any
    object with `.slots`), `stored` maps key -> row (anything with `.hidden`) for every
    picture in the database. A word that already has a picture, or has no match, is absent."""
    pool: dict[str, Any] = {}
    targets: dict[str, Any] = {}
    for group in groups:
        for slot in group.slots:
            if slot.kind != "vocab":
                continue
            row = stored.get(slot.key)
            if row is None:
                targets.setdefault(slot.key, slot)
            elif not getattr(row, "hidden", False):
                pool.setdefault(slot.key, slot)
    if not targets or not pool:
        return {}

    prepared = {key: (slot, senses(slot.meaning), stem(slot.label)) for key, slot in pool.items()}
    out: dict[str, list[Candidate]] = {}
    for target_key, target in targets.items():
        t_senses, t_stem = senses(target.meaning), stem(target.label)
        ranked: list[tuple[tuple, Candidate]] = []
        for key, (other, o_senses, o_stem) in prepared.items():
            shared = t_senses & o_senses
            same_stem = o_stem == t_stem and other.label != target.label
            if not shared and not same_stem:
                continue
            same_senses = bool(t_senses) and t_senses == o_senses
            # sure enough to apply unseen: a noun and its verb that also agree in meaning, or
            # two words whose every meaning is the same
            confident = (same_stem and bool(shared)) or same_senses
            candidate = Candidate(
                key=key,
                label=other.label,
                meaning=other.meaning,
                why=_why(target, other, shared, same_stem, same_senses),
                confident=confident,
            )
            ranked.append(((not confident, not same_stem, -len(shared), other.label), candidate))
        if ranked:
            ranked.sort(key=lambda pair: pair[0])
            out[target_key] = [c for _, c in ranked[:MAX_CANDIDATES]]
    return out

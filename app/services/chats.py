"""«Hội thoại»: a lesson's dialogue played as a chat. The other speaker says a line (voiced); the
learner answers by picking their line out of four. The prompt is what the line means, in
Vietnamese; the three other choices are lines that do not fit at that point: the learner's own
lines from elsewhere in the same dialogue first (same words, wrong moment), then lines of other
dialogues of the same lessons, of a similar length.

Nothing new is written: the dialogues are the lessons' own (app/seed/passages). Pure functions."""
from __future__ import annotations

import hashlib
import random
from collections.abc import Iterable
from dataclasses import dataclass

from app.services import passages

OPTIONS = 4


@dataclass(frozen=True)
class Turn:
    who: str  # F | M
    speaker: str
    ko: str
    vi: str
    mine: bool  # the learner's line: chosen out of `options`
    options: tuple[str, ...] = ()  # the line among others (shuffled), when `mine`


def learner_role(p: passages.Passage) -> str:
    """The learner answers: the speaker who does not open the dialogue."""
    first = p.lines[0].who
    return "M" if first == "F" else "F"


def _rng(*parts: str) -> random.Random:
    return random.Random(int(hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:12], 16))


def turns(p: passages.Passage, others: Iterable[passages.Passage]) -> list[Turn]:
    """The chat of dialogue `p`; `others`: dialogues whose lines may serve as wrong choices."""
    me = learner_role(p)
    own = [ln.ko.strip() for ln in p.lines if ln.who == me]
    pool = [ln.ko.strip() for o in others if o.id != p.id and o.kind == "dialogue" for ln in o.lines]
    out: list[Turn] = []
    for i, ln in enumerate(p.lines):
        line = ln.ko.strip()
        name = p.speakers.get(ln.who, "")
        if ln.who != me:
            out.append(Turn(ln.who, name, line, ln.vi, False))
            continue
        rng = _rng(p.id, str(i))
        wrong: list[str] = []
        same = [x for x in own if x != line]
        rng.shuffle(same)
        wrong += same[: OPTIONS - 2]  # at most two from the same dialogue: one at least from elsewhere
        near = sorted({x for x in pool if x != line and x not in wrong}, key=lambda x: (abs(len(x) - len(line)), x))
        near = near[:12]
        rng.shuffle(near)
        for x in near:
            if len(wrong) >= OPTIONS - 1:
                break
            wrong.append(x)
        options = [line, *wrong[: OPTIONS - 1]]
        rng.shuffle(options)
        out.append(Turn(ln.who, name, line, ln.vi, True, tuple(options)))
    return out

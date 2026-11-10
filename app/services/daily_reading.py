"""Which reading and which dialogue to offer a learner today — the rules, with no database.

The bank (app.services.passages) holds short texts, each built on named grammar cards and key
words. A text is offered to a learner only when they have MET every card it is built on (the card
has a study record). Among the texts that are open to them, the ones that rest on what they are
about to forget come up more often: a weak or due card raises a text's chance, a text offered in
the last two weeks is less likely to come back (and not at all within three days while another is
open), and the draw is seeded by (learner, day, kind), so the same learner sees the same pick all
day however often the screen is opened, while the next day is a fresh draw.

The reading does not touch the review schedule: it is a way to meet the cards in use, not another
round of grading them.
"""
from __future__ import annotations

import random
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone, tzinfo
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.services import passages

Key = tuple[str, int]  # ("grammar_point" | "vocab_item", id) — the same keys as ItemState

DUE_BONUS = 0.5  # a card that is due counts as this much weaker
GRAMMAR_SHARE = 0.65  # of a text's score: the cards it practises; the rest is its words
FLOOR = 0.05  # a text whose cards are all strong still has a chance
MIN_GAP_DAYS = 3  # a text offered within this many days is not offered again while another is open
COOLDOWN_DAYS = 14  # a text offered fewer days ago than this is less likely to come back
RECENT_WEIGHT = 0.1  # how likely, against a text not offered for a long while, one offered yesterday is
_FIXED_ZONES = {"Asia/Seoul": timezone(timedelta(hours=9))}  # when the host has no tz database


@dataclass(frozen=True)
class Card:
    """What a learner's study record says about one card."""

    strength: float
    due: bool


def need(card: Card) -> float:
    """How much a card could use another sight: 0 (solid) … 1 (new, unremembered), plus a bonus when due."""
    return 1.0 - max(0.0, min(1.0, card.strength)) + (DUE_BONUS if card.due else 0.0)


# ------------------------------------------------------------------- the day --
def zone(name: str) -> tzinfo:
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError, OSError):
        return _FIXED_ZONES.get(name, timezone.utc)


def local_day(now: datetime, tz_name: str) -> date:
    """The learner's calendar day. Everyone shares one zone (the app is used in Korea)."""
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    return now.astimezone(zone(tz_name)).date()


# ------------------------------------------------------------- what a text rests on --
@dataclass(frozen=True)
class Refs:
    """The card ids behind a text. One group per grammar use / key word: the ids are those of every
    lesson the text may draw on that holds the card (a pattern can sit in two lessons)."""

    grammar: tuple[tuple[Key, ...], ...]
    words: tuple[tuple[Key, ...], ...]


def resolve(
    p: passages.Passage,
    slugs: Iterable[str],
    grammar_index: Mapping[tuple[str, str], int],
    vocab_index: Mapping[tuple[str, str], int],
) -> Refs:
    """Look the text's patterns and words up in the lessons it may draw on.
    `*_index`: (lesson slug, pattern | headword) -> id."""
    allowed = sorted(passages.allowed_slugs(p.lesson, slugs))
    grammar = tuple(
        tuple(("grammar_point", grammar_index[(s, u.pattern)]) for s in allowed if (s, u.pattern) in grammar_index)
        for u in p.uses
    )
    words = tuple(
        tuple(("vocab_item", vocab_index[(s, k.word)]) for s in allowed if (s, k.word) in vocab_index)
        for k in p.keywords
    )
    return Refs(grammar=grammar, words=words)


def _met(group: Iterable[Key], cards: Mapping[Key, Card]) -> list[Card]:
    return [cards[k] for k in group if k in cards]


def unlocked(refs: Refs, cards: Mapping[Key, Card]) -> bool:
    """Every grammar card the text is built on has been met (a card that is not in the database
    at all keeps the text shut)."""
    return bool(refs.grammar) and all(_met(group, cards) for group in refs.grammar)


def score(refs: Refs, cards: Mapping[Key, Card]) -> float | None:
    """How well the text fits what this learner should see again; None while it is still locked.
    The score is the mean `need` of the cards it practises (the better-remembered copy of a card
    that sits in two lessons), blended with the words of the text the learner has met."""
    if not unlocked(refs, cards):
        return None
    grammar = [min(need(c) for c in _met(group, cards)) for group in refs.grammar]
    words = [min(need(c) for c in met) for group in refs.words if (met := _met(group, cards))]
    g = sum(grammar) / len(grammar)
    if not words:
        return g
    return GRAMMAR_SHARE * g + (1 - GRAMMAR_SHARE) * (sum(words) / len(words))


def weakest(p: passages.Passage, refs: Refs, cards: Mapping[Key, Card], n: int = 2) -> list[tuple[str, bool]]:
    """The `n` grammar patterns of the text this learner most needs to see again: (pattern, due)."""
    rows = []
    for use, group in zip(p.uses, refs.grammar):
        met = _met(group, cards)
        if met:
            best = min(met, key=need)
            rows.append((use.pattern, need(best), best.due))
    rows.sort(key=lambda r: (-r[1], r[0]))
    return [(pattern, due) for pattern, _need, due in rows[:n]]


def new_words(refs: Refs, p: passages.Passage, cards: Mapping[Key, Card]) -> list[str]:
    """Key words of the text that the learner has not met yet (shown to them with their meaning)."""
    return [k.word for k, group in zip(p.keywords, refs.words) if not _met(group, cards)]


# ------------------------------------------------------------------- the draw --
@dataclass(frozen=True)
class Candidate:
    passage: passages.Passage
    refs: Refs
    score: float


def candidates(
    texts: Iterable[passages.Passage],
    slugs: Sequence[str],
    grammar_index: Mapping[tuple[str, str], int],
    vocab_index: Mapping[tuple[str, str], int],
    cards: Mapping[Key, Card],
) -> list[Candidate]:
    """The texts open to this learner, with their score."""
    out: list[Candidate] = []
    for p in texts:
        refs = resolve(p, slugs, grammar_index, vocab_index)
        s = score(refs, cards)
        if s is not None:
            out.append(Candidate(p, refs, s))
    return out


def weight(score_: float, days_since_offered: int | None) -> float:
    """A text's chance in the draw: the square of its score (so a weak card pulls clearly) times a
    cool-down for a text offered recently."""
    if days_since_offered is None:
        fresh = 1.0
    else:
        fresh = min(1.0, max(days_since_offered, 0) / COOLDOWN_DAYS)
    return (FLOOR + score_) ** 2 * (RECENT_WEIGHT + (1 - RECENT_WEIGHT) * fresh)


def seed_of(learner: object, day: date, kind: str) -> str:
    return f"{learner}:{day.isoformat()}:{kind}"


def pick(
    pool: Sequence[Candidate],
    learner: object,
    day: date,
    kind: str,
    offered: Mapping[str, date],
) -> Candidate | None:
    """One text of `kind` for `day`. `offered`: passage id -> the last day it was offered.
    The same inputs always give the same text."""
    ordered = sorted((c for c in pool if c.passage.kind == kind), key=lambda c: c.passage.id)
    if not ordered:
        return None

    def ago(c: Candidate) -> int | None:
        return (day - offered[c.passage.id]).days if c.passage.id in offered else None

    # the same text does not come two days running: leave out the ones seen in the last few days,
    # unless nothing else is open (a learner with a single dialogue still gets it)
    rested = [c for c in ordered if (ago(c) is None or ago(c) >= MIN_GAP_DAYS)]
    ordered = rested or ordered
    weights = [weight(c.score, ago(c)) for c in ordered]
    return random.Random(seed_of(learner, day, kind)).choices(ordered, weights=weights, k=1)[0]


def pick_day(
    pool: Sequence[Candidate], learner: object, day: date, offered: Mapping[str, date]
) -> list[Candidate]:
    """Today's sitting: a dialogue to listen to and a reading, whichever are open."""
    chosen = (pick(pool, learner, day, kind, offered) for kind in passages.KINDS)
    return [c for c in chosen if c is not None]


# ---------------------------------------------------------------------- why --
def why_vi(p: passages.Passage, refs: Refs, cards: Mapping[Key, Card]) -> str:
    """One line for the learner: why this text today."""
    rows = weakest(p, refs, cards)
    if not rows:
        return "Bài này dùng lại những gì bạn đã học trong một tình huống thật."
    # the list is plain names; a due card changes the sentence, not the names (a bracket after a
    # grammar pattern reads as part of the pattern)
    names = " · ".join(pattern for pattern, _ in rows)
    lead = "Bài này giúp bạn ôn lại mẫu sắp quên" if any(due for _, due in rows) else "Bài này giúp bạn gặp lại"
    return f"{lead}: {names}"


# ------------------------------------------------------------------- grading --
@dataclass(frozen=True)
class Graded:
    answer: int | None
    correct: int
    is_right: bool
    explain_vi: str


def grade(p: passages.Passage, answers: Sequence[int | None]) -> list[Graded]:
    """Mark the learner's answers (one per question, None = left blank). Raises ValueError when the
    number of answers is not the number of questions."""
    if len(answers) != len(p.questions):
        raise ValueError(f"{len(p.questions)} answers wanted, got {len(answers)}")
    out = []
    for q, a in zip(p.questions, answers):
        valid = a is not None and 0 <= a < len(q.options)
        out.append(Graded(a if valid else None, q.answer, bool(valid and a == q.answer), q.explain_vi))
    return out

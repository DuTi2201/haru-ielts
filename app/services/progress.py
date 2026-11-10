"""Per-learner progress helpers that need no schema of their own.

`ItemState.strength` (0..1, nudged +/-0.2 by /progress/reviews) is the only
per-learner memory signal the spec defines (SRS §5 ITEM_STATE) — this module
only *reads* it. It is deliberately pure (plain dicts in, a small dataclass
out, no DB session) so the selection rule can be unit-tested without
Postgres; the router does the two bulk queries and hands the rows over.

Two different things are tracked and kept apart:
  * **studied** — the learner has been through the lesson: every word and card was
    marked at least once (it has an ItemState) and every practice question was answered.
    This is what moves "the next lesson" on.
  * **mastered** — memory strength >= 0.8 (about four right answers per card, spread
    over days by the spaced review). That is the job of "Ôn tập hôm nay", not of the
    lesson picker: waiting for it would keep a finished lesson in the plan for days.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

# An item counts as "learned" once four correct nudges in a row have lifted it
# to 0.8. Compared with a small epsilon: 0.2 steps accumulate float noise.
MASTERY_THRESHOLD = 0.8
_EPS = 1e-9

ItemKey = tuple[str, int]  # ("vocab_item" | "grammar_point", content id)


def is_mastered(strength: float | None) -> bool:
    return strength is not None and strength >= MASTERY_THRESHOLD - _EPS


@dataclass(frozen=True)
class LessonProgress:
    lesson_id: int
    total: int
    mastered: int
    met: int = 0  # words / cards marked at least once (they have an ItemState)
    practice_answered: int = 0
    practice_total: int = 0

    @property
    def complete(self) -> bool:
        """Every item is mastered (memory)."""
        return self.total > 0 and self.mastered >= self.total

    @property
    def studied(self) -> bool:
        """The learner has been through the lesson: every item marked once, every question answered."""
        return (self.total > 0 or self.practice_total > 0) and self.met >= self.total and self.practice_answered >= self.practice_total


def count_mastered(items: Sequence[ItemKey], states: Mapping[ItemKey, tuple[float, datetime]]) -> int:
    """How many of `items` the learner has mastered (items never reviewed count as not)."""
    return sum(1 for key in items if (state := states.get(key)) is not None and is_mastered(state[0]))


def pick_next_lesson(
    lessons: Mapping[int, Sequence[ItemKey]],
    states: Mapping[ItemKey, tuple[float, datetime]],
    order: Sequence[int] | None = None,
    practice: Mapping[int, tuple[int, int]] | None = None,
) -> LessonProgress | None:
    """Which lesson should this learner see next?

    * `lessons`: lesson id -> the vocab/grammar items that belong to it.
      Lessons without any item are skipped (nothing to study in them).
    * `states`: this learner's ItemState rows as (strength, last_seen),
      keyed by (item_type, item_id). Items with no row are simply "not
      started yet".
    * `order`: the curriculum order (lesson ids, first = earliest). Seeded lessons
      are ordered by track (sơ → trung → cao) and their position in it, not by
      id; without it the lowest id comes first. Lessons missing from `order`
      come after the listed ones, by id.
    * `practice`: lesson id -> (questions answered, questions in the lesson). Without it
      no practice is required.

    Rule: the first lesson in that order the learner has not **studied** yet (see the module
    doc) — so one who has been through lesson 1 is moved on to lesson 2 the same day, and one
    who is halfway through lesson 2 resumes there. Words that have not stuck yet come back
    through the daily review, not by keeping the lesson here. If every lesson is studied,
    return the one whose least-recently-seen item is oldest (the one most due for a refresher).
    Returns None when there is no lesson with any item at all.
    """
    progress: list[tuple[LessonProgress, datetime | None]] = []
    if order is None:
        sequence: list[int] = sorted(lessons)
    else:
        listed = [i for i in order if i in lessons]
        sequence = listed + sorted(set(lessons) - set(listed))
    for lesson_id in sequence:
        items = lessons[lesson_id]
        if not items and not (practice or {}).get(lesson_id, (0, 0))[1]:
            continue  # nothing to study in it (a lesson with practice only, like Bảng chữ cái, stays)
        mastered = 0
        met = 0
        oldest: datetime | None = None
        for key in items:
            state = states.get(key)
            if state is None:
                continue
            strength, last_seen = state
            met += 1
            if is_mastered(strength):
                mastered += 1
            if oldest is None or last_seen < oldest:
                oldest = last_seen
        answered, questions = (practice or {}).get(lesson_id, (0, 0))
        progress.append((LessonProgress(lesson_id, len(items), mastered, met, answered, questions), oldest))

    if not progress:
        return None
    for entry, _ in progress:
        if not entry.studied:
            return entry

    # Everything studied: refresh the lesson that has gone longest unseen.
    # `oldest` is never None here — a studied lesson has a state row for every item.
    return min(progress, key=lambda p: (p[1], p[0].lesson_id))[0]


Step = Literal["listen", "vocab", "grammar", "practice"]


def resume_step(
    vocab_met: int,
    vocab_total: int,
    grammar_met: int,
    grammar_total: int,
    practice_answered: int,
    practice_total: int,
) -> Step | None:
    """The part of a lesson to open: the first one with something left, in the order the lesson
    screen shows them. Listening leaves no trace on the server, so it is only named for a lesson
    the learner has not touched at all (the screen skips it when this device remembers it was played).
    None when everything is done."""
    if vocab_met == 0 and grammar_met == 0 and practice_answered == 0:
        return "listen"
    if vocab_met < vocab_total:
        return "vocab"
    if grammar_met < grammar_total:
        return "grammar"
    if practice_answered < practice_total:
        return "practice"
    return None

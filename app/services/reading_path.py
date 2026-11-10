"""Which news article to offer a learner today — the rules, with no database.

An article is placed on the course path by `related_lesson_ids` (the lessons whose topic and words it
reinforces, closest first). It is offered once the learner has been through its closest lesson, so
a learner who has just finished "Việc nhà" is sent to the housework article, never to a text far above
them. Among the articles within reach, one not yet read comes first, then the one that follows the
lesson studied most recently, then the easier one. An article that is not placed on the path (an older
import) is only offered to a learner who aims at TOPIK II, as before.
"""
from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class Candidate:
    id: str
    level: int | None
    related: Sequence[int]  # course lesson ids, closest first
    created_ts: float = 0.0


def studied_lessons(order: Sequence[int], next_lesson: int | None) -> list[int]:
    """The lessons before the learner's next one, in course order: the ones they have been through.
    `next_lesson` None means every lesson with content has been studied."""
    if next_lesson is None:
        return list(order)
    return list(order[: order.index(next_lesson)]) if next_lesson in order else []


def pick(
    candidates: Iterable[Candidate],
    studied: Sequence[int],
    done: set[str],
    *,
    editorial_goal: bool,
) -> Candidate | None:
    """The article to offer today, or None. `studied` is in course order; `done` the articles already
    worked through (their outline was submitted)."""
    place = {lid: i for i, lid in enumerate(studied)}
    placed: list[tuple[tuple, Candidate]] = []
    legacy: list[Candidate] = []
    for c in candidates:
        if not c.related:
            if editorial_goal:
                legacy.append(c)
            continue
        if c.related[0] not in place:
            continue  # its closest lesson has not been studied yet
        recent = max((place[r] for r in c.related if r in place), default=-1)
        # not yet read first, then following the lesson studied most recently, then the easier one
        placed.append(((c.id in done, -recent, c.level or 9, -c.created_ts), c))
    if placed:
        return min(placed, key=lambda p: p[0])[1]
    if legacy:
        fresh = [c for c in legacy if c.id not in done] or legacy
        return max(fresh, key=lambda c: c.created_ts)
    return None

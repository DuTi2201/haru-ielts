"""Which grammar cards are made of which: the "xây trên" links between cards.

A card lists, in `builds_on`, the `pattern` of the earlier cards it is made of or rests on
(-(으)ㄹ 수 있겠습니까? = -(으)ㄹ 수 있다 + -겠- + -습니까?). Intermediate grammar is mostly
primary grammar put together, so the learner is shown the parts, and which later cards use the
one in front of them. Patterns are the keys; where one pattern is taught twice (a later card
that revisits it) a link goes to its earliest card, and a card never links to itself.

Pure functions, shared by the seed validator, the API and the tests.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Hashable, Sequence


@dataclass(frozen=True)
class GraphCard:
    key: Hashable  # whatever identifies the card to the caller
    lesson: int  # the lesson's place in the curriculum (equal for cards of one lesson)
    pattern: str
    builds_on: tuple[str, ...] = ()


def resolve(
    cards: Sequence[GraphCard], *, strict_order: bool = True
) -> tuple[dict[Hashable, list[Hashable]], list[str]]:
    """`cards` in curriculum order -> (card key -> keys of the cards it builds on, problems).

    A link must lead to a card of an earlier lesson, or of the same lesson (before it, when
    `strict_order`): the learner has met every part before the whole."""
    by_pattern: dict[str, list[int]] = defaultdict(list)
    for i, c in enumerate(cards):
        by_pattern[c.pattern].append(i)
    edges: dict[Hashable, list[Hashable]] = {}
    problems: list[str] = []
    for i, c in enumerate(cards):
        targets: list[Hashable] = []
        for n, p in enumerate(c.builds_on):
            if p in c.builds_on[:n]:
                problems.append(f"{c.pattern!r}: builds_on lists {p!r} twice")
                continue
            found = [
                j
                for j in by_pattern.get(p, [])
                if j != i
                and (cards[j].lesson < c.lesson or (cards[j].lesson == c.lesson and (j < i or not strict_order)))
            ]
            if not found:
                later = [j for j in by_pattern.get(p, []) if j != i]
                why = "is only taught later" if later else "is not a card of any lesson"
                problems.append(f"{c.pattern!r}: builds_on {p!r} {why}")
                continue
            if cards[found[0]].key not in targets:
                targets.append(cards[found[0]].key)
        edges[c.key] = targets
    return edges, problems


def invert(edges: dict[Hashable, list[Hashable]]) -> dict[Hashable, list[Hashable]]:
    """card key -> the keys of the cards that build on it, in the order of `edges`."""
    used: dict[Hashable, list[Hashable]] = defaultdict(list)
    for key, targets in edges.items():
        for t in targets:
            used[t].append(key)
    return dict(used)

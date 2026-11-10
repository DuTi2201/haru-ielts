"""The entry diagnostic: ~16 short questions on the core patterns of the beginner course.

`app/seed/placement/diagnostic.json` holds the items. Each is an ordinary exercise (a multiple
choice question, a sentence to build, a blank to fill — the shapes of the lesson practice, so the
same screens grade them in the browser) plus the grammar card it is evidence for. A right answer
is evidence that the learner can do that much with the card; a wrong or skipped answer says nothing
about the card (no penalty: the diagnostic must never make the learner look worse than they are).

This module is pure: it loads and checks the file and turns a set of answers into a summary.
The database side (record the evidence, schedule the known cards, store the attempt) is in
`app.api.routers.competency`."""
from __future__ import annotations

import json
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from app.services import competency
from app.services import lesson_seed as seed

PLACEMENT_DIR = seed.SEED_DIR / "placement"
DIAGNOSTIC_FILE = PLACEMENT_DIR / "diagnostic.json"
REACHED = 2 / 3  # a rung is "reached" when at least this share of its items was right
NO_RUNG_LABEL = "Bắt đầu từ nhận ra"
_KINDS = ("read_cloze", "read_meaning", "build_order", "write_fill")


class CardRef(seed._M):
    lesson: str  # slug of the lesson that teaches the card
    pattern: str


class Item(seed._M):
    card: CardRef
    exercise: dict[str, Any]  # as validated and served (the lesson-seed shape)


class Diagnostic(seed._M):
    title_vi: str
    intro_vi: str
    minutes: int
    items: list[Item]


@dataclass(frozen=True)
class DiagItem:
    id: str  # the exercise id (also its question id for a build / MCQ item)
    question_id: str
    rung: int
    lesson: str
    pattern: str
    exercise: dict[str, Any]


@dataclass(frozen=True)
class Loaded:
    title_vi: str
    intro_vi: str
    minutes: int
    items: tuple[DiagItem, ...]


def load(path: Path = DIAGNOSTIC_FILE) -> tuple[Loaded | None, list[str]]:
    """The diagnostic and the problems found in the file (no diagnostic when it cannot be read)."""
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return None, [f"{path.name}: {exc}"]
    problems: list[str] = []
    try:
        doc = Diagnostic.model_validate(
            {**raw, "items": [{"card": it.get("card"), "exercise": it.get("exercise")} for it in raw.get("items", [])]}
        )
    except ValidationError as exc:
        return None, [f"{path.name}: {exc}"]
    items: list[DiagItem] = []
    seen_ids: set[str] = set()
    seen_cards: set[tuple[str, str]] = set()
    for n, it in enumerate(doc.items, 1):
        label = f"{path.name} item {n}"
        try:
            ex = seed._validate_exercise(it.exercise, str(it.exercise.get("skill")))
        except (ValidationError, ValueError) as exc:
            problems.append(f"{label}: {exc}")
            continue
        if ex.get("type") not in _KINDS:
            problems.append(f"{label}: type {ex.get('type')!r} cannot be graded in the diagnostic")
            continue
        qids = seed.question_ids(ex)
        if len(qids) != 1:
            problems.append(f"{label}: an item asks exactly one question, {ex['id']} asks {len(qids)}")
            continue
        if ex["id"] in seen_ids or qids[0] in seen_ids:
            problems.append(f"{label}: id {ex['id']} is used twice")
            continue
        seen_ids.update({ex["id"], qids[0]})
        key = (it.card.lesson, it.card.pattern)
        if key in seen_cards:
            problems.append(f"{label}: the card {key} has two items (one item per card)")
        seen_cards.add(key)
        rung = competency.rung_of(ex)
        if rung is None or rung > 2:
            problems.append(f"{label}: this item does not sit on a rung the diagnostic can grade")
            continue
        items.append(DiagItem(ex["id"], qids[0], rung, it.card.lesson, it.card.pattern, ex))
    if not items:
        problems.append(f"{path.name}: no items")
        return None, problems
    return Loaded(doc.title_vi, doc.intro_vi, doc.minutes, tuple(items)), problems


@lru_cache(maxsize=1)
def diagnostic() -> Loaded | None:
    return load()[0]


def check(loaded: Loaded | None, cards: Iterable[tuple[str, str]]) -> list[str]:
    """Problems that need the lessons: every item must point at a card that exists, and the three
    rungs must all be asked (otherwise "where to start" has nothing to say about a rung)."""
    if loaded is None:
        return ["the diagnostic could not be loaded"]
    have = set(cards)
    problems = [f"{i.id}: no card {i.pattern!r} in lesson {i.lesson!r}" for i in loaded.items if (i.lesson, i.pattern) not in have]
    asked = {i.rung for i in loaded.items}
    problems += [f"no item on rung {r}" for r in (0, 1, 2) if r not in asked]
    return problems


# ------------------------------------------------------------------ the answers --
@dataclass(frozen=True)
class Answer:
    exercise_id: str
    question_id: str
    correct: bool
    answer: str = ""


def resolve(loaded: Loaded, answers: Sequence[Answer]) -> tuple[dict[str, Answer], list[str]]:
    """The answer to each item (the last one when an item was sent twice) and what is wrong with the
    set: an item or question the diagnostic does not have."""
    by_id = {i.id: i for i in loaded.items}
    out: dict[str, Answer] = {}
    problems: list[str] = []
    for a in answers:
        item = by_id.get(a.exercise_id)
        if item is None:
            problems.append(f"{a.exercise_id}: not an item of the diagnostic")
        elif a.question_id != item.question_id:
            problems.append(f"{a.exercise_id}: not its question ({a.question_id})")
        else:
            out[item.id] = a
    return out, problems


def summarize(
    loaded: Loaded,
    given: Mapping[str, Answer],
    *,
    gid_of: Mapping[tuple[str, str], int],
    lesson_id_of: Mapping[str, int],
    lesson_pos: Mapping[str, int],
) -> dict[str, Any]:
    """What the attempt says. An item that was skipped counts as not known. `gid_of` maps
    (lesson slug, pattern) to the card's id; `lesson_pos` is the lesson's place in the curriculum."""
    right: dict[int, list[DiagItem]] = {0: [], 1: [], 2: []}
    wrong: dict[int, list[DiagItem]] = {0: [], 1: [], 2: []}
    for item in loaded.items:
        a = given.get(item.id)
        (right if a is not None and a.correct else wrong)[item.rung].append(item)
    by_rung = {
        str(r): {"right": len(right[r]), "total": len(right[r]) + len(wrong[r])}
        for r in (0, 1, 2)
        if right[r] or wrong[r]
    }
    reached = [r for r in (0, 1, 2) if (right[r] or wrong[r]) and len(right[r]) / (len(right[r]) + len(wrong[r])) >= REACHED - 1e-9]
    start = max(reached) if reached else -1

    known = [i for r in (0, 1, 2) for i in right[r]]
    unknown = [i for r in (0, 1, 2) for i in wrong[r]]
    known_ids = sorted({gid_of[(i.lesson, i.pattern)] for i in known if (i.lesson, i.pattern) in gid_of})
    # right on a sentence to build or a blank to fill: not a lucky guess, so the card may be tucked away
    solid_ids = sorted({gid_of[(i.lesson, i.pattern)] for i in known if i.rung >= 1 and (i.lesson, i.pattern) in gid_of})
    start_lesson = None
    candidates = [i.lesson for i in unknown if i.lesson in lesson_pos and i.lesson in lesson_id_of]
    if candidates:
        start_lesson = lesson_id_of[min(candidates, key=lambda slug: lesson_pos[slug])]
    return {
        "score": len(known),
        "total": len(loaded.items),
        "known": [i.pattern for i in known],
        "unknown": [i.pattern for i in unknown],
        "known_ids": known_ids,
        "solid_ids": solid_ids,
        "start_rung": start,
        "start_label": competency.RUNG_LABEL[start] if start >= 0 else NO_RUNG_LABEL,
        "start_lesson_id": start_lesson,
        "by_rung": by_rung,
    }


def evidence(loaded: Loaded, given: Mapping[str, Answer], gid_of: Mapping[tuple[str, str], int]) -> list[tuple[int, int]]:
    """(card id, rung) for each item answered right: what to write to the competency record."""
    return [
        (gid_of[(i.lesson, i.pattern)], i.rung)
        for i in loaded.items
        if given.get(i.id) is not None and given[i.id].correct and (i.lesson, i.pattern) in gid_of
    ]

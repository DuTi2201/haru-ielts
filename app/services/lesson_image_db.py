"""Lesson pictures and the database: which ones exist, which a learner may see, and what
a drawing run still has to draw (see app.services.lesson_image for what a picture is)."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Iterable

from sqlalchemy import select

from app.models import GrammarPoint, Lesson, SceneImage, VocabItem
from app.services import lesson_image
from app.services.lesson_image import Slot

IMAGE_URL = "/api/v1/lessons/scene-image/"


def url_for(key: str, made_at: datetime | None) -> str:
    """The picture's URL. The `v` follows the moment it was drawn, so a picture drawn
    again (the URL's key is the same) is fetched afresh although the file itself is cached
    for a year."""
    return f"{IMAGE_URL}{key}?v={int(made_at.timestamp()) if made_at else 0}"


async def visible_urls(db: Any, prompts: Iterable[str | None]) -> dict[str, str]:
    """prompt -> URL of its picture, for the pictures that exist and are not hidden.
    Empty (and no query) while the feature is off or when there is nothing to look up."""
    if not lesson_image.enabled():
        return {}
    keys = {lesson_image.scene_key(p): p.strip() for p in prompts if p and p.strip()}
    if not keys:
        return {}
    rows = (
        await db.execute(
            select(SceneImage.cache_key, SceneImage.created_at).where(
                SceneImage.cache_key.in_(list(keys)), SceneImage.hidden.is_(False)
            )
        )
    ).all()
    return {keys[key]: url_for(key, made_at) for key, made_at in rows}


@dataclass
class LessonSlots:
    lesson_id: int
    slug: str | None
    title: str
    slots: list[Slot]


def _assemble(
    lessons: list[tuple[int, str | None, str, dict | None]],
    vocab: dict[int, list[str]],
    grammar: dict[int, list[str]],
    meanings: dict[int, dict[str, str]],
) -> list[LessonSlots]:
    return [
        LessonSlots(
            lesson_id=lid,
            slug=slug,
            title=title,
            slots=lesson_image.lesson_slots(
                slug, vocab.get(lid, []), grammar.get(lid, []), practice, meanings.get(lid)
            ),
        )
        for lid, slug, title, practice in lessons
    ]


def _lessons_query(lesson_ids: list[int] | None, order: tuple):
    query = select(Lesson.id, Lesson.slug, Lesson.title, Lesson.practice)
    if lesson_ids is not None:
        query = query.where(Lesson.id.in_(lesson_ids))
    if order:
        query = query.order_by(*order)
    return query


def _vocab_query(ids: list[int]):
    return (
        select(VocabItem.lesson_id, VocabItem.headword, VocabItem.meaning_vi)
        .where(VocabItem.lesson_id.in_(ids))
        .order_by(VocabItem.id)
    )


def _grammar_query(ids: list[int]):
    return (
        select(GrammarPoint.lesson_id, GrammarPoint.pattern)
        .where(GrammarPoint.lesson_id.in_(ids))
        .order_by(GrammarPoint.position, GrammarPoint.id)
    )


def _collect(vocab_rows, grammar_rows):
    vocab: dict[int, list[str]] = defaultdict(list)
    meanings: dict[int, dict[str, str]] = defaultdict(dict)
    grammar: dict[int, list[str]] = defaultdict(list)
    for lid, headword, meaning in vocab_rows:
        vocab[lid].append(headword)
        if meaning:
            meanings[lid].setdefault(headword, meaning)
    for lid, pattern in grammar_rows:
        grammar[lid].append(pattern)
    return vocab, grammar, meanings


async def lesson_slots_async(db: Any, lesson_ids: list[int] | None = None, order: tuple = ()) -> list[LessonSlots]:
    """The picture slots of the given lessons (all when None), in `order`."""
    lessons = [(r[0], r[1], r[2], r[3]) for r in (await db.execute(_lessons_query(lesson_ids, order))).all()]
    ids = [row[0] for row in lessons]
    vocab_rows: list = []
    grammar_rows: list = []
    if ids:
        vocab_rows = (await db.execute(_vocab_query(ids))).all()
        grammar_rows = (await db.execute(_grammar_query(ids))).all()
    return _assemble(lessons, *_collect(vocab_rows, grammar_rows))


def lesson_slots_sync(db: Any, lesson_ids: list[int] | None = None, order: tuple = ()) -> list[LessonSlots]:
    """Same as lesson_slots_async, for the worker's sync Session."""
    lessons = [(r[0], r[1], r[2], r[3]) for r in db.execute(_lessons_query(lesson_ids, order)).all()]
    ids = [row[0] for row in lessons]
    vocab_rows: list = []
    grammar_rows: list = []
    if ids:
        vocab_rows = db.execute(_vocab_query(ids)).all()
        grammar_rows = db.execute(_grammar_query(ids)).all()
    return _assemble(lessons, *_collect(vocab_rows, grammar_rows))


def pick_work(
    groups: list[LessonSlots],
    existing: set[str],
    keys: list[str] | None = None,
    force: bool = False,
) -> list[Slot]:
    """What a drawing run has to draw: every slot of the chosen lessons that has no picture
    (hidden or not — a hidden picture is an editor's decision, not a gap), each picture
    once even when several lessons share it. `keys` narrows it to those pictures, and with
    `force` they are drawn again although they exist."""
    wanted = set(keys) if keys else None
    out: list[Slot] = []
    seen: set[str] = set()
    for group in groups:
        for slot in group.slots:
            key = slot.key
            if key in seen or (wanted is not None and key not in wanted):
                continue
            seen.add(key)
            if force or key not in existing:
                out.append(slot)
    return out

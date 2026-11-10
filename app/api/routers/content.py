"""Learner-facing read endpoints: content (topics/lessons/vocab/grammar),
corpus (listening sentences), progress (item-state check-ins), curriculum
(goal/placement/plan) and practice (quick-checks). Grouped in one router
for the scaffold; split into content.py/curriculum.py/practice.py once
each grows past a handful of routes.
"""
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Annotated, Literal, Sequence

from fastapi import APIRouter, Depends, Query, Response, status
from starlette.concurrency import run_in_threadpool
from sqlalchemy import and_, case, func, literal_column, or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    _problem,
    get_current_profile,
    ensure_lesson_open,
    get_optional_profile,
    require_private_source,
    require_role,
    study_day,
)
from app.core.config import settings
from app.db import get_db
from app.models import (
    CorpusItem,
    EditorialArticle,
    EditorialOutlineSubmission,
    EditorialRead,
    ErrorLog,
    Film,
    GrammarPoint,
    ItemState,
    Lesson,
    LessonExerciseResult,
    LearnerBankDeck,
    LessonPartDone,
    LessonTopic,
    PlacementAttempt,
    Profile,
    SceneImage,
    Topic,
    VocabItem,
)
from app.schemas import (
    ConstellationOut,
    FeatherOut,
    JourneyChapterOut,
    StarOut,
    ClozeOut,
    CoachOut,
    SessionOut,
    CorpusFacetsOut,
    CorpusFilmCount,
    CorpusGrammarCount,
    CorpusItemOut,
    CorpusLevelCount,
    CorpusPageOut,
    CorpusRegisterCount,
    CorpusSimilarOut,
    CorpusTopicCount,
    GrammarPointOut,
    GrammarRefOut,
    ItemStateOut,
    ItemStateReviewRequest,
    ExerciseAnswerRequest,
    ExerciseResultOut,
    LessonOut,
    LessonTotalsOut,
    LessonPracticeOut,
    CardStudyOut,
    LessonProgressOut,
    LessonStudyOut,
    KiipCountsOut,
    LessonSummaryOut,
    NoteOut,
    PracticeCountsOut,
    ProfileOut,
    ReviewOnlyOut,
    ReviewOnlyRequest,
    ReviewQueueItem,
    ReviewQueueOut,
    JourneyOut,
    TodayPlanOut,
    TodayPlanTask,
    TopicOut,
    VocabItemOut,
)
from app.services import audio_store, competency, topik_bank, feathers, competency_db, corpus_browse, corpus_enrich, daily_reading_db, journey, lesson_image, lesson_image_db, lesson_seed, placement, reading_path, srs, weakness
from app.services.corpus_browse import Sentence
from app.services.exercises import build_cloze
from app.services.grammar_graph import GraphCard, invert as invert_graph, resolve as resolve_graph
from app.services.billing import access as billing_access
from app.services.billing import catalog as billing_catalog
from app.services.progress import ItemKey, count_mastered, pick_next_lesson, resume_step

router = APIRouter(tags=["content"])

EDITORIAL_GOALS = ("topik4", "topik5", "topik6")  # who gets the daily editorial in the plan


@router.get("/topics")
async def list_topics(db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(select(Topic).order_by(Topic.name))
    topics = result.scalars().all()
    return [{"id": t.id, "name": t.name, "quizlet_url": t.quizlet_url} for t in topics]


async def _recognize_only(db: AsyncSession) -> set[ItemKey]:
    """The words that only need recognising (`priority` = "recognize"): the queue offers them
    after the words to learn now of the same lesson."""
    rows = await db.execute(select(VocabItem.id).where(VocabItem.priority == "recognize", VocabItem.lesson_id.isnot(None)))
    return {("vocab_item", item_id) for (item_id,) in rows.all()}


async def _grammar_links(
    db: AsyncSession, wanted: Sequence[GrammarPoint]
) -> dict[int, tuple[list[GrammarRefOut], list[GrammarRefOut]]]:
    """card id -> (the earlier cards it is built from, the later cards built on it) for the cards of
    one lesson, read from every card's `builds_on` (app.services.grammar_graph)."""
    if not wanted:
        return {}
    rows = (
        await db.execute(
            select(
                GrammarPoint.id, GrammarPoint.pattern, GrammarPoint.builds_on, GrammarPoint.importance,
                GrammarPoint.lesson_id, Lesson.title,
            )
            .join(Lesson, Lesson.id == GrammarPoint.lesson_id)
            .order_by(*_LESSON_ORDER, GrammarPoint.id)
        )
    ).all()
    place: dict[int, int] = {}
    for r in rows:
        place.setdefault(r.lesson_id, len(place))
    cards = [GraphCard(r.id, place[r.lesson_id], r.pattern, tuple(r.builds_on or ())) for r in rows]
    edges, _ = resolve_graph(cards, strict_order=False)
    used = invert_graph(edges)
    info = {r.id: GrammarRefOut(pattern=r.pattern, lesson_id=r.lesson_id, lesson_title=r.title, importance=r.importance) for r in rows}
    return {
        g.id: ([info[i] for i in edges.get(g.id, [])], [info[i] for i in used.get(g.id, [])])  # type: ignore[index]
        for g in wanted
    }


async def _revisit_refs(db: AsyncSession, wanted: Sequence[GrammarPoint]) -> dict[int, GrammarRefOut]:
    """card id -> the earliest card it teaches again (spaced review), for the cards that say so."""
    targets = {g.pattern: g.revisits for g in wanted if g.revisits}
    if not targets:
        return {}
    rows = (
        await db.execute(
            select(GrammarPoint.pattern, GrammarPoint.lesson_id, GrammarPoint.importance, Lesson.title)
            .join(Lesson, Lesson.id == GrammarPoint.lesson_id)
            .where(GrammarPoint.pattern.in_(set(targets.values())))
            .order_by(*_LESSON_ORDER, GrammarPoint.id)
        )
    ).all()
    first: dict[str, GrammarRefOut] = {}
    for r in rows:
        first.setdefault(r.pattern, GrammarRefOut(pattern=r.pattern, lesson_id=r.lesson_id, lesson_title=r.title, importance=r.importance))
    return {g.id: first[g.revisits] for g in wanted if g.revisits and g.revisits in first}


async def _lesson_item_keys(db: AsyncSession) -> dict[int, list[ItemKey]]:
    """lesson id -> the (type, id) of every vocab/grammar item in it. Two
    narrow bulk queries (ids only); items that belong to no lesson
    (editorial-article imports) are left out — they are not lesson content."""
    lesson_items: dict[int, list[ItemKey]] = defaultdict(list)
    for lesson_id, item_id in (await db.execute(select(VocabItem.lesson_id, VocabItem.id))).all():
        if lesson_id is not None:
            lesson_items[lesson_id].append(("vocab_item", item_id))
    for lesson_id, item_id in (await db.execute(select(GrammarPoint.lesson_id, GrammarPoint.id))).all():
        if lesson_id is not None:
            lesson_items[lesson_id].append(("grammar_point", item_id))
    # Bảng chữ cái has no words or cards of its own, only its end check: it is still a lesson to study
    for lesson_id in (await db.execute(select(Lesson.id).where(Lesson.practice["kind"].astext == "hangul"))).scalars().all():
        lesson_items.setdefault(lesson_id, [])
    return lesson_items


async def _kiip_tallies(db: AsyncSession) -> dict[int, tuple[list[ItemKey], int, int, int, dict[str, int]]]:
    """lesson id -> (the tagged words and cards, #words, #cards, #notes, count by stage) for every
    lesson with something tagged for an exam course (`exam`: "kiip-3" …). Three narrow queries."""
    keys: dict[int, list[ItemKey]] = defaultdict(list)
    vocab_n: dict[int, int] = defaultdict(int)
    grammar_n: dict[int, int] = defaultdict(int)
    note_n: dict[int, int] = defaultdict(int)
    stages: dict[int, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for lesson_id, item_id, exam in (
        await db.execute(select(VocabItem.lesson_id, VocabItem.id, VocabItem.exam).where(VocabItem.exam.isnot(None)))
    ).all():
        if lesson_id is not None:
            keys[lesson_id].append(("vocab_item", item_id))
            vocab_n[lesson_id] += 1
            stages[lesson_id][exam] += 1
    for lesson_id, item_id, exam in (
        await db.execute(
            select(GrammarPoint.lesson_id, GrammarPoint.id, GrammarPoint.exam).where(GrammarPoint.exam.isnot(None))
        )
    ).all():
        if lesson_id is not None:
            keys[lesson_id].append(("grammar_point", item_id))
            grammar_n[lesson_id] += 1
            stages[lesson_id][exam] += 1
    # the notes' tags live inside the lesson's JSON: ask the database for just the tags
    note_tags = func.jsonb_path_query_array(Lesson.notes, literal_column("'$[*].exam'::jsonpath"))
    for lesson_id, tags in (await db.execute(select(Lesson.id, note_tags).where(Lesson.notes.isnot(None)))).all():
        for tag in tags or []:
            note_n[lesson_id] += 1
            stages[lesson_id][tag] += 1
    out: dict[int, tuple[list[ItemKey], int, int, int, dict[str, int]]] = {}
    for lesson_id in set(vocab_n) | set(grammar_n) | set(note_n):
        out[lesson_id] = (
            keys.get(lesson_id, []),
            vocab_n.get(lesson_id, 0),
            grammar_n.get(lesson_id, 0),
            note_n.get(lesson_id, 0),
            dict(sorted(stages[lesson_id].items())),
        )
    return out


@dataclass
class ArticleWords:
    """The vocabulary of the confirmed news articles, newest article first.
    `keys` is every word that exists; `hold` the ones above the learner's level
    (not started as new cards), `title_of` / `article_of` say where a word came from."""

    keys: dict[str, list[ItemKey]] = field(default_factory=dict)
    hold: set[ItemKey] = field(default_factory=set)
    title_of: dict[str, str] = field(default_factory=dict)
    article_of: dict[int, str] = field(default_factory=dict)


async def _article_words(db: AsyncSession, level_cap: int) -> ArticleWords:
    """Words of the articles a human has confirmed. A word that was rolled back is
    left out (it no longer exists); a word shared by two articles belongs to the
    newer one. Words above `level_cap` stay in `keys` but are listed in `hold`."""
    out = ArticleWords()
    rows = (
        await db.execute(
            select(
                EditorialArticle.id,
                EditorialArticle.title_ko,
                EditorialArticle.source_name,
                EditorialArticle.vocab_ids,
            )
            .where(func.length(func.btrim(EditorialArticle.body_ko)) > 0, func.cardinality(EditorialArticle.vocab_ids) > 0)
            .order_by(EditorialArticle.created_at.desc())
        )
    ).all()
    if not rows:
        return out
    wanted = {vid for _, _, _, vocab_ids in rows for vid in vocab_ids}
    # a course word an article also lists is started by its lesson, in course order — not
    # pulled forward as an "article word" (the reader still shows it with the article)
    level_of = dict(
        (
            await db.execute(
                select(VocabItem.id, VocabItem.level).where(VocabItem.id.in_(wanted), VocabItem.lesson_id.is_(None))
            )
        ).all()
    )
    for article_id, title, source_name, vocab_ids in rows:
        key = str(article_id)
        words = [vid for vid in vocab_ids if vid in level_of and vid not in out.article_of]
        if not words:
            continue
        out.keys[key] = [("vocab_item", vid) for vid in words]
        out.title_of[key] = title or source_name
        for vid in words:
            out.article_of[vid] = key
            if level_of[vid] > level_cap:
                out.hold.add(("vocab_item", vid))
    return out


async def _word_sources(db: AsyncSession, profile) -> ArticleWords:
    """The words that come into the daily new cards from outside the lessons: the decks of the
    TOPIK word bank the learner added (first: the learner chose them), then the news articles.
    A bank deck is keyed "bank:<deck key>"."""
    out = await _article_words(db, srs.article_level_cap(profile.goal))
    chosen = list(
        (
            await db.execute(
                select(LearnerBankDeck.deck_key).where(LearnerBankDeck.learner_id == profile.id).order_by(LearnerBankDeck.added_at)
            )
        ).scalars()
    )
    by_entry = dict(
        (await db.execute(select(VocabItem.bank_key, VocabItem.id).where(VocabItem.bank_key.isnot(None)))).all()
    )
    # a deck the learner took away again brings no new words, but the words already started
    # stay in their reviews
    started = set(
        (
            await db.execute(
                select(ItemState.item_id).where(
                    ItemState.learner_id == profile.id,
                    ItemState.item_type == "vocab_item",
                    ItemState.item_id.in_(select(VocabItem.id).where(VocabItem.bank_key.isnot(None))),
                )
            )
        ).scalars()
    )
    if not chosen and not started:
        return out
    entry_of = {vid: e for e, vid in by_entry.items()}
    for vid in started:
        w = topik_bank.words().get(entry_of.get(vid, -1))
        if w and w["deck"] not in chosen:
            chosen = [*chosen, w["deck"]]
    bank_keys: dict[str, list[ItemKey]] = {}
    added = set((await db.execute(select(LearnerBankDeck.deck_key).where(LearnerBankDeck.learner_id == profile.id))).scalars())
    for deck_key in chosen:
        deck = topik_bank.decks().get(deck_key)
        if deck is None:  # a deck the bank no longer has
            continue
        key = f"bank:{deck_key}"
        ids = [by_entry[e] for e in deck.words if e in by_entry and by_entry[e] not in out.article_of]
        if deck_key not in added:
            ids = [vid for vid in ids if vid in started]
        if not ids:
            continue
        bank_keys[key] = [("vocab_item", vid) for vid in ids]
        out.title_of[key] = topik_bank.deck_title(deck_key) or deck_key
        for vid in ids:
            out.article_of[vid] = key
    out.keys = {**bank_keys, **out.keys}
    return out


# lesson-v5: lessons are shown by track (sơ → trung → cao) and by their position in it,
# not by the order they happened to be inserted.
_TRACK_RANK = case({"beginner": 0, "intermediate": 1, "advanced": 2}, value=Lesson.track, else_=3)
_LESSON_ORDER = (_TRACK_RANK, Lesson.sort_order, Lesson.level, Lesson.id)

# practice question id -> skill name the error log (and the weakness report) uses
# ("build" = sentence building, "Tạo câu": it is writing practice, so its mistakes count as writing)
_ERROR_SKILL = {"listening": "nghe", "reading": "đọc", "build": "viết", "writing": "viết", "speaking": "nói"}


async def _lesson_order(db: AsyncSession, learner_id: uuid.UUID | None = None) -> list[int]:
    """Lesson ids in curriculum order. For a learner placed by the entry check, the lessons from
    their start come first and the ones before it last: the plan and the new cards begin where the
    check put them, and what they skipped is still there, after."""
    start = await _placed_at(db, learner_id) if learner_id is not None else None
    if not start:
        return list((await db.execute(select(Lesson.id).order_by(*_LESSON_ORDER))).scalars().all())
    rows = (await db.execute(select(Lesson.id, Lesson.sort_order).order_by(*_LESSON_ORDER))).all()
    return [lid for lid, so in rows if (so or 0) >= start] + [lid for lid, so in rows if (so or 0) < start]


async def _placed_at(db: AsyncSession, learner_id: uuid.UUID) -> int | None:
    """The lesson position the latest adaptive entry check started this learner at."""
    summaries = (
        await db.execute(
            select(PlacementAttempt.summary)
            .where(PlacementAttempt.learner_id == learner_id)
            .order_by(PlacementAttempt.taken_at.desc())
            .limit(5)
        )
    ).scalars().all()
    for s in summaries:
        if (s or {}).get("kind") == "adaptive":
            return int(s.get("start_sort") or 0) or None
    return None


async def _practice_by_lesson(db: AsyncSession, learner_id: uuid.UUID) -> dict[int, tuple[int, int]]:
    """lesson id -> (practice questions this learner has answered, questions in the lesson), for the
    lessons that have any. What "studied" needs besides the cards (app.services.progress)."""
    totals = {
        lid: int((counts or {}).get("questions", 0))
        for lid, counts in (await db.execute(select(Lesson.id, Lesson.practice["counts"]))).all()
    }
    answered = dict(
        (
            await db.execute(
                select(LessonExerciseResult.lesson_id, func.count())
                .where(LessonExerciseResult.learner_id == learner_id)
                .group_by(LessonExerciseResult.lesson_id)
            )
        ).all()
    )
    return {lid: (int(answered.get(lid, 0)), n) for lid, n in totals.items() if n or answered.get(lid)}


def _counts(practice_counts: dict | None) -> PracticeCountsOut | None:
    return PracticeCountsOut.model_validate(practice_counts) if practice_counts else None


def _kiip_out(
    tally: tuple[list[ItemKey], int, int, int, dict[str, int]] | None,
    states: dict[ItemKey, tuple[float, datetime]] | None,
) -> KiipCountsOut | None:
    if tally is None:
        return None
    keys, vocab_n, grammar_n, note_n, stages = tally
    return KiipCountsOut(
        vocab=vocab_n,
        grammar=grammar_n,
        notes=note_n,
        stages=stages,
        mastered=count_mastered(keys, states) if states is not None else None,
    )


async def _require_open(db: AsyncSession, profile, lesson: Lesson) -> None:
    await ensure_lesson_open(db, profile, lesson)


async def _open_lesson_items(db: AsyncSession, profile, lesson_items: dict[int, list[ItemKey]]) -> dict[int, list[ItemKey]]:
    """The review queue and the plan only draw cards from lessons the learner may open."""
    held = await billing_access.load_access(db, profile)
    if not held.enforced or held.everything:
        return lesson_items
    sorts = dict((await db.execute(select(Lesson.id, Lesson.sort_order))).all())
    return {lid: keys for lid, keys in lesson_items.items() if held.can_open(sorts.get(lid))}


def _vocab_preview(v: VocabItemOut) -> VocabItemOut:
    """What a locked lesson shows of a word: the word, its meaning and one example."""
    return v.model_copy(
        update={
            "definition_ko": None,
            "hanja": None,
            "sino_vietnamese": None,
            "family": None,
            "node_word": None,
            "usage_note_vi": None,
            "collocations": None,
            "distractors": None,
        }
    )


@router.get("/lessons", response_model=list[LessonSummaryOut])
async def list_lessons(
    db: Annotated[AsyncSession, Depends(get_db)],
    profile: Annotated[Profile | None, Depends(get_optional_profile)],
):
    """The lesson picker: every lesson that has something to study, by track
    (sơ → trung → cao) and position in it. Public; when the caller is signed in each
    row also carries how many of its items they have mastered and how much of its
    practice they have answered, and `is_next` marks the lesson /me/plan would hand
    them (same rule — app.services.progress)."""
    lessons = (
        await db.execute(
            select(
                Lesson.id,
                Lesson.title,
                Lesson.level,
                Lesson.slug,
                Lesson.title_ko,
                Lesson.summary,
                Lesson.track,
                Lesson.sort_order,
                Lesson.practice["counts"],
                Lesson.practice["kind"],
            ).order_by(*_LESSON_ORDER)
        )
    ).all()
    order = [row[0] for row in lessons]
    lesson_items = await _lesson_item_keys(db)
    kiip = await _kiip_tallies(db)

    topics: dict[int, list[str]] = defaultdict(list)
    topic_rows = (
        await db.execute(
            select(LessonTopic.lesson_id, Topic.name)
            .join(Topic, Topic.id == LessonTopic.topic_id)
            .order_by(Topic.name)
        )
    ).all()
    for lesson_id, name in topic_rows:
        topics[lesson_id].append(name)

    states: dict[ItemKey, tuple[float, datetime]] | None = None
    next_id: int | None = None
    answered: dict[int, tuple[int, int]] = {}
    if profile is not None:
        rows = (await db.execute(select(ItemState).where(ItemState.learner_id == profile.id))).scalars().all()
        states = {(s.item_type, s.item_id): (s.strength, s.last_seen) for s in rows}
        # never hand out a lesson the learner cannot open yet (a locked one is only a preview)
        picked = pick_next_lesson(
            await _open_lesson_items(db, profile, lesson_items),
            states,
            await _lesson_order(db, profile.id) if await _placed_at(db, profile.id) else order,
            await _practice_by_lesson(db, profile.id),
        )
        next_id = picked.lesson_id if picked is not None else None
        for lid, n_all, n_right in (
            await db.execute(
                select(
                    LessonExerciseResult.lesson_id,
                    func.count(),
                    func.count().filter(LessonExerciseResult.correct.is_(True)),
                )
                .where(LessonExerciseResult.learner_id == profile.id)
                .group_by(LessonExerciseResult.lesson_id)
            )
        ).all():
            answered[lid] = (n_all, n_right)

    by_course = {c.id: c for c in await feathers.course(db)}
    feather_rec = await feathers.record(db, profile.id) if profile is not None else None

    plan = lesson_image.load_plan()
    banners = await lesson_image_db.visible_urls(
        db,
        [plan.lessons.get(row[3] or "") for row in lessons]
        + [plan.topics.get(t) for ts in topics.values() for t in ts[:1]],
    )
    held = await billing_access.load_access(db, profile)
    out: list[LessonSummaryOut] = []
    for lesson_id, title, level, slug, title_ko, summary, track, sort_order, counts, kind in lessons:
        keys = lesson_items.get(lesson_id, [])
        is_review = kind == "review"  # the topic review: practice only, no words or cards of its own
        if not keys and kind not in ("review", "hangul"):  # nothing to study yet: not a choice worth offering
            continue
        vocab_count = sum(1 for kind_, _ in keys if kind_ == "vocab_item")
        access = held.label_for(sort_order)
        entry = by_course.get(lesson_id)
        out.append(
            LessonSummaryOut(
                id=lesson_id,
                title=title,
                level=level,
                topics=topics.get(lesson_id, []),
                vocab_count=vocab_count,
                grammar_count=len(keys) - vocab_count,
                kind=kind if kind in ("review", "hangul") else "lesson",
                mastered=count_mastered(keys, states) if states is not None and kind not in ("review", "hangul") else None,
                is_next=lesson_id == next_id,
                slug=slug,
                title_ko=title_ko,
                summary=summary,
                track=track,
                sort_order=sort_order,
                practice=_counts(counts),
                practice_correct=answered.get(lesson_id, (0, 0))[1] if profile is not None else None,
                practice_answered=answered.get(lesson_id, (0, 0))[0] if profile is not None else None,
                image_url=banners.get(plan.lessons.get(slug or "", "")),
                topic_image_url=banners.get(plan.topics.get((topics.get(lesson_id) or [""])[0], "")),
                kiip=_kiip_out(kiip.get(lesson_id), states),
                access=access,
                unlock_with=billing_catalog.unlock_products(sort_order) if access == "locked" else [],
                chapter=entry.chapter if entry else None,
                support=entry.support if entry else None,
                feathers_total=len(entry.feathers) if entry else 0,
                feathers_earned=sum(feathers.lesson_status(entry, feather_rec)) if entry and feather_rec else None,
            )
        )
    return out


async def _find_lesson(db: AsyncSession, lesson_id: str) -> Lesson:
    """`lesson_id="today"` is the anonymous fallback (the first lesson of the curriculum)."""
    if lesson_id == "today":
        lesson = (await db.execute(select(Lesson).order_by(*_LESSON_ORDER).limit(1))).scalars().first()
    else:
        try:
            lid = int(lesson_id)
        except ValueError as exc:
            raise _problem(status.HTTP_404_NOT_FOUND, "Lesson not found", "not_found") from exc
        lesson = await db.get(Lesson, lid)
    if lesson is None:
        raise _problem(status.HTTP_404_NOT_FOUND, "Lesson not found", "not_found")
    return lesson


@router.get("/lessons/{lesson_id}", response_model=LessonOut)
async def get_lesson(
    lesson_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    response: Response,
    profile: Annotated[Profile | None, Depends(get_optional_profile)] = None,
):
    """`lesson_id="today"` is the anonymous fallback (the first lesson) —
    this route is public, so it cannot know who is asking. The learner-aware
    "next lesson" is chosen by /me/plan (see app.services.progress), which
    hands the frontend a concrete numeric `lesson_id`; a numeric id fetches
    that exact lesson. The practice set is not in here (it is large): see
    GET /lessons/{id}/practice.

    Paid access (BILLING_ENABLED): a lesson the caller has not unlocked answers with a PREVIEW —
    the goal, the first three words, the totals — and `access: "locked"`; never its content."""
    lesson = await _find_lesson(db, lesson_id)
    held = await billing_access.load_access(db, profile)
    access = held.label_for(lesson.sort_order)
    if held.enforced and access != "free":
        response.headers["Cache-Control"] = "private, no-store"  # the answer depends on who asks

    topics = (
        (
            await db.execute(
                select(Topic).join(LessonTopic, LessonTopic.topic_id == Topic.id).where(LessonTopic.lesson_id == lesson.id)
            )
        )
        .scalars()
        .all()
    )
    vocab = (
        (await db.execute(select(VocabItem).where(VocabItem.lesson_id == lesson.id).order_by(VocabItem.id)))
        .scalars()
        .all()
    )
    grammar = (
        (await db.execute(select(GrammarPoint).where(GrammarPoint.lesson_id == lesson.id).order_by(GrammarPoint.id)))
        .scalars()
        .all()
    )
    links = await _grammar_links(db, grammar)
    revisit_refs = await _revisit_refs(db, grammar)
    plan = lesson_image.load_plan()
    banner_prompt = plan.lessons.get(lesson.slug or "")
    pictures = await lesson_image_db.visible_urls(
        db,
        [banner_prompt]
        + [plan.vocab.get(v.hangul) for v in vocab]
        + [plan.grammar.get(g.pattern) for g in grammar],
    )

    def picture(prompt: str | None) -> str | None:
        return pictures.get(prompt) if prompt else None

    full = LessonOut(
        id=lesson.id,
        title=lesson.title,
        level=lesson.level,
        content=lesson.content,
        created_at=lesson.created_at,
        topics=[TopicOut.model_validate(t) for t in topics],
        vocab=[
            VocabItemOut.model_validate(v).model_copy(update={"image_url": picture(plan.vocab.get(v.hangul))})
            for v in vocab
        ],
        grammar=[
            GrammarPointOut.model_validate(g).model_copy(
                update={
                    "image_url": picture(plan.grammar.get(g.pattern)),
                    "built_from": links[g.id][0],
                    "built_into": links[g.id][1],
                    "revisit_of": revisit_refs.get(g.id),
                }
            )
            for g in grammar
        ],
        image_url=picture(banner_prompt),
        slug=lesson.slug,
        title_ko=lesson.title_ko,
        summary=lesson.summary,
        track=lesson.track,
        sort_order=lesson.sort_order or 0,
        kind=_kind_of(lesson.practice),
        notes=[NoteOut.model_validate(n) for n in (lesson.notes or [])],
        coach=CoachOut.model_validate(lesson.coach) if lesson.coach else None,
        sessions=[SessionOut.model_validate(x) for x in (lesson.sessions or [])],
        practice=_counts((lesson.practice or {}).get("counts")),
        access=access,
    )
    if access != "locked":
        return full
    return full.model_copy(
        update={
            "content": "",
            "vocab": [_vocab_preview(v) for v in full.vocab[:3]],
            "grammar": [],
            "notes": [n for n in full.notes if n.kind == "goal"][:1],
            "coach": None,
            "sessions": [],
            "unlock_with": billing_catalog.unlock_products(lesson.sort_order),
            "totals": LessonTotalsOut(vocab=len(full.vocab), grammar=len(full.grammar), notes=len(full.notes)),
        }
    )


# ------------------------------------------------------------ lesson practice --
@router.get("/lessons/{lesson_id}/practice", response_model=LessonPracticeOut)
async def get_lesson_practice(
    lesson_id: int,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
    profile: Annotated[Profile | None, Depends(get_optional_profile)] = None,
):
    """The lesson's whole practice set (listening, reading, writing, speaking), with
    the answers and explanations: the browser grades each question the moment it is
    answered. Public — it is the same material the repository holds."""
    lesson = await db.get(Lesson, lesson_id)
    if lesson is None or not lesson.practice or not lesson.practice.get("items"):
        raise _problem(status.HTTP_404_NOT_FOUND, "This lesson has no practice set", "not_found")
    practice = lesson.practice
    held = await billing_access.load_access(db, profile)
    if held.enforced and not billing_catalog.is_free(lesson.sort_order):
        # the answers ship with the questions: a paid lesson's set goes only to someone who holds it
        await _require_open(db, profile, lesson)  # 401 not signed in, 402 not unlocked
        response.headers["Cache-Control"] = "private, no-store"
    else:
        response.headers["Cache-Control"] = "public, max-age=60"
    return LessonPracticeOut(
        lesson_id=lesson.id,
        items=await _support_links(db, practice["items"]),
        guides=practice.get("guides") or {},
        type_intro=practice.get("type_intro") or {},
        overview=practice.get("overview"),
        extension=practice.get("extension"),
        grammar=await _linked_cards(db, practice.get("grammar") or {}),
        kind=_kind_of(practice),
        review=await _review_payload(db, practice.get("review")),
        hangul=practice.get("hangul"),
        scene_images=await lesson_image_db.visible_urls(db, lesson_image.scene_prompts(practice)),
    )


async def _support_links(db: AsyncSession, items: list[dict]) -> list[dict]:
    """The items, with the id and title of the lesson that teaches each "grammar not met yet" of an
    item's `support` (the seed names it by slug), so the client can open it."""
    slugs = {g["lesson"] for it in items for g in (it.get("support") or {}).get("grammar", []) if g.get("lesson")}
    if not slugs:
        return items
    rows = {slug: (lid, title) for slug, lid, title in (await db.execute(select(Lesson.slug, Lesson.id, Lesson.title).where(Lesson.slug.in_(slugs)))).all()}
    out = []
    for it in items:
        sup = it.get("support")
        if not sup:
            out.append(it)
            continue
        grammar = [
            {**g, "lesson_id": rows.get(g["lesson"], (None, None))[0], "lesson_title": rows.get(g["lesson"], (None, None))[1]}
            if g.get("lesson")
            else {**g, "lesson_id": None, "lesson_title": None}
            for g in sup.get("grammar", [])
        ]
        out.append({**it, "support": {**sup, "grammar": grammar}})
    return out


def _kind_of(practice: dict | None) -> str:
    kind = (practice or {}).get("kind")
    return kind if kind in ("review", "hangul") else "lesson"


async def _linked_cards(db: AsyncSession, cards: dict[str, dict]) -> dict[str, dict]:
    """The practice set's `grammar` (pattern -> card info, see lesson_seed.card_info) with the
    id of the lesson that teaches each card, so the client can open it."""
    if not cards:
        return {}
    slugs = {c["lesson_slug"] for c in cards.values()}
    ids = dict((await db.execute(select(Lesson.slug, Lesson.id).where(Lesson.slug.in_(slugs)))).all())
    out: dict[str, dict] = {}
    for pattern, card in cards.items():
        info = {k: v for k, v in card.items() if k != "lesson_order"}
        info["lesson_id"] = ids.get(card["lesson_slug"])
        out[pattern] = info
    return out


async def _review_payload(db: AsyncSession, review: dict | None) -> dict | None:
    """The review lesson's map, mock and capstone, with the id of the lesson that teaches each
    card of the map (so the client can open the card)."""
    if not review:
        return None
    return {**review, "cards": await _linked_cards(db, review.get("cards") or {})}


# ------------------------------------------------------------ lesson pictures --
@router.get("/lessons/scene-image/{key}")
async def get_scene_image(key: str, db: Annotated[AsyncSession, Depends(get_db)]):
    """The bytes of one lesson picture (a small WebP). The URL carries `?v=` of the moment it
    was drawn, so the file can be cached for good. Making, listing and hiding them is
    editors' work: see app.api.routers.lesson_images."""
    row = await db.get(SceneImage, key)
    if row is None:
        raise _problem(status.HTTP_404_NOT_FOUND, "Picture not found", "not_found")
    try:
        data = await run_in_threadpool(audio_store.read_image, row)
    except audio_store.StoreError:
        raise _problem(
            status.HTTP_503_SERVICE_UNAVAILABLE, "Picture storage unreachable", "storage_unavailable"
        ) from None
    if not data:
        raise _problem(status.HTTP_404_NOT_FOUND, "Picture not found", "not_found")
    return Response(
        content=data, media_type=row.mime_type, headers={"Cache-Control": "public, max-age=31536000, immutable"}
    )


async def _lesson_results(db: AsyncSession, learner_id: uuid.UUID, lesson_id: int) -> list[LessonExerciseResult]:
    return list(
        (
            await db.execute(
                select(LessonExerciseResult)
                .where(LessonExerciseResult.learner_id == learner_id, LessonExerciseResult.lesson_id == lesson_id)
                .order_by(LessonExerciseResult.updated_at)
            )
        )
        .scalars()
        .all()
    )


def _progress_out(lesson: Lesson, rows: list[LessonExerciseResult]) -> LessonProgressOut:
    counts = (lesson.practice or {}).get("counts") or {}
    return LessonProgressOut(
        lesson_id=lesson.id,
        total=int(counts.get("questions", 0)),
        answered=len(rows),
        correct=sum(1 for r in rows if r.correct),
        results=[
            ExerciseResultOut(
                exercise_id=r.exercise_id, question_id=r.question_id, correct=r.correct, attempts=r.attempts, answer=r.last_answer
            )
            for r in rows
        ],
    )


@router.get("/lessons/{lesson_id}/progress", response_model=LessonProgressOut)
async def get_lesson_progress(
    lesson_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    profile: Annotated[Profile, Depends(get_current_profile)],
):
    """The signed-in learner's latest answer to each practice question of this lesson."""
    lesson = await db.get(Lesson, lesson_id)
    if lesson is None:
        raise _problem(status.HTTP_404_NOT_FOUND, "Lesson not found", "not_found")
    await _require_open(db, profile, lesson)
    return _progress_out(lesson, await _lesson_results(db, profile.id, lesson.id))


@router.get("/lessons/{lesson_id}/study", response_model=LessonStudyOut)
async def get_lesson_study(
    lesson_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    profile: Annotated[Profile, Depends(get_current_profile)],
):
    """Where the signed-in learner stands in this lesson, so the lesson screen can open on the part
    that is left and show the words and cards already marked (also on another phone): which of its
    words / cards have a record (and the last answer to each), and the practice answered. The same
    rule as the plan's next lesson (app.services.progress)."""
    lesson = await db.get(Lesson, lesson_id)
    if lesson is None:
        raise _problem(status.HTTP_404_NOT_FOUND, "Lesson not found", "not_found")
    await _require_open(db, profile, lesson)
    vocab_ids = set((await db.execute(select(VocabItem.id).where(VocabItem.lesson_id == lesson_id))).scalars().all())
    grammar_ids = set((await db.execute(select(GrammarPoint.id).where(GrammarPoint.lesson_id == lesson_id))).scalars().all())
    states = (
        (
            await db.execute(
                select(ItemState).where(
                    ItemState.learner_id == profile.id,
                    or_(
                        and_(ItemState.item_type == "vocab_item", ItemState.item_id.in_(vocab_ids)),
                        and_(ItemState.item_type == "grammar_point", ItemState.item_id.in_(grammar_ids)),
                    ),
                )
            )
        )
        .scalars()
        .all()
    )
    cards = [
        CardStudyOut(
            item_type=st.item_type,
            item_id=st.item_id,
            # rows from before the column existed: a card answered right at least once in a row counts as understood
            last_correct=st.last_correct if st.last_correct is not None else (st.reps or 0) >= 1,
            strength=st.strength,
        )
        for st in states
    ]
    vocab_met = sum(1 for c in cards if c.item_type == "vocab_item")
    grammar_met = len(cards) - vocab_met
    progress = _progress_out(lesson, await _lesson_results(db, profile.id, lesson.id))
    return LessonStudyOut(
        lesson_id=lesson.id,
        vocab_total=len(vocab_ids),
        vocab_met=vocab_met,
        grammar_total=len(grammar_ids),
        grammar_met=grammar_met,
        practice_total=progress.total,
        practice_answered=progress.answered,
        resume_step=resume_step(vocab_met, len(vocab_ids), grammar_met, len(grammar_ids), progress.answered, progress.total),
        cards=cards,
        **await _lesson_feathers(db, profile.id, lesson.id),
    )


async def _lesson_feathers(db: AsyncSession, learner_id: uuid.UUID, lesson_id: int) -> dict:
    """One lesson's feathers and where it sits in the journey."""
    entry = next((c for c in await feathers.course(db) if c.id == lesson_id), None)
    if entry is None:
        return {}
    rec = await feathers.record(db, learner_id, lesson_id)
    return {
        "feathers": [FeatherOut(**f) for f in feathers.feathers_out(entry, rec)],
        "chapter": entry.chapter,
        "support": entry.support,
    }


@router.post("/lessons/{lesson_id}/parts/{part_id}", response_model=list[FeatherOut], dependencies=[Depends(study_day)])
async def finish_lesson_part(
    lesson_id: int,
    part_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    profile: Annotated[Profile, Depends(get_current_profile)],
):
    """The learner finished a part of a lesson that leaves no other record (the alphabet lesson's
    five parts): its feather is earned. Saying it twice changes nothing."""
    lesson = await db.get(Lesson, lesson_id)
    if lesson is None:
        raise _problem(status.HTTP_404_NOT_FOUND, "Lesson not found", "not_found")
    await _require_open(db, profile, lesson)
    parts = {str(p.get("id")) for p in ((lesson.practice or {}).get("hangul") or {}).get("parts") or []}
    if part_id not in parts:
        raise _problem(status.HTTP_404_NOT_FOUND, "Part not found", "not_found")
    await db.execute(
        pg_insert(LessonPartDone).values(learner_id=profile.id, lesson_id=lesson_id, part_id=part_id).on_conflict_do_nothing()
    )
    await db.commit()
    return (await _lesson_feathers(db, profile.id, lesson_id)).get("feathers", [])


def _error_example(exercise: dict, question_id: str) -> str:
    """A short Korean line that says which question it was (for the error log)."""
    if exercise.get("type") == "build_order" and exercise.get("answers"):
        return str(exercise["answers"][0])[:300]  # the sentence the learner was asked to build
    for q in exercise.get("questions") or []:
        if q["id"] == question_id:
            for text in (q.get("prompt_ko"), (exercise.get("stimulus") or {}).get("text"), exercise.get("instruction_ko")):
                if text:
                    return str(text)[:300]
    return str(exercise.get("instruction_ko") or exercise.get("title_vi") or exercise["id"])[:300]


@router.post("/lessons/{lesson_id}/answers", response_model=LessonProgressOut, dependencies=[Depends(study_day)])
async def answer_lesson_question(
    lesson_id: int,
    body: ExerciseAnswerRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    profile: Annotated[Profile, Depends(get_current_profile)],
):
    """Record one practice question the learner has just answered. The browser did
    the grading (the answer ships with the lesson), so this stores the outcome: the
    latest answer per question, a try counter, and — when it was wrong — a line in
    the error log, where the weak-spot report reads it. Returns the lesson's progress."""
    lesson = await db.get(Lesson, lesson_id)
    if lesson is None:
        raise _problem(status.HTTP_404_NOT_FOUND, "Lesson not found", "not_found")
    await _require_open(db, profile, lesson)
    exercise = lesson_seed.question_index(lesson.practice).get(body.question_id)
    if exercise is None or exercise["id"] != body.exercise_id:
        raise _problem(status.HTTP_422_UNPROCESSABLE_ENTITY, "That question is not in this lesson", "unknown_question")

    row = (
        await db.execute(
            select(LessonExerciseResult).where(
                LessonExerciseResult.learner_id == profile.id,
                LessonExerciseResult.lesson_id == lesson.id,
                LessonExerciseResult.question_id == body.question_id,
            )
        )
    ).scalar_one_or_none()
    first_miss = not body.correct and (row is None or row.correct)  # a new mistake, not a retry of one
    linked = await _linked_grammar_ids(db, lesson, exercise, body.question_id)
    cards = linked if not body.correct else []
    if row is None:
        db.add(
            LessonExerciseResult(
                learner_id=profile.id,
                lesson_id=lesson.id,
                exercise_id=body.exercise_id,
                question_id=body.question_id,
                correct=body.correct,
                attempts=1,
                last_answer=body.answer,
            )
        )
    else:
        row.correct = body.correct
        row.attempts = (row.attempts or 0) + 1
        row.last_answer = body.answer
        row.updated_at = datetime.now(timezone.utc)
        if not body.correct:
            row.understood_at = None  # a new wrong answer is a new thing to read in the mistake book
    if not body.correct:
        main = cards[0] if cards else None
        db.add(
            ErrorLog(
                learner_id=profile.id,
                skill=_ERROR_SKILL.get(exercise["skill"], exercise["skill"]),
                error_type=exercise["type"],
                example_ko=_error_example(exercise, body.question_id),
                # the main linked grammar card, so "hay sai" lists it by name
                item_type="grammar_point" if main else None,
                item_id=main[0] if main else None,
                mode="writing" if exercise["skill"] in ("writing", "build") else "exam",
                detail={
                    "lesson_id": lesson.id,
                    "exercise": exercise["id"],
                    "question": body.question_id,
                    **({"chosen": body.answer} if body.answer else {}),
                    **({"grammar": [pattern for _, pattern in cards]} if cards else {}),
                },
            )
        )
        if first_miss and cards:
            await _lapse_cards(db, profile.id, [gid for gid, _ in cards], datetime.now(timezone.utc))
    # what the learner can DO with the linked cards: one more outcome on this exercise's rung
    rung = competency.rung_of(exercise)
    if linked and rung is not None:
        await competency_db.record_outcomes(db, profile.id, [gid for gid, _ in linked], rung, body.correct)
    await db.commit()
    return _progress_out(lesson, await _lesson_results(db, profile.id, lesson.id))


async def _linked_grammar_ids(
    db: AsyncSession, lesson: Lesson, exercise: dict, question_id: str
) -> list[tuple[int, str]]:
    """(grammar_point id, pattern) of the cards a practice question is linked to, main one first
    (the links are written in grammar_links.json and carried by the lesson's practice set)."""
    patterns = lesson_seed.question_grammar(exercise, question_id)
    info = (lesson.practice or {}).get("grammar") or {}
    wanted = [(info[p]["lesson_slug"], p) for p in patterns if p in info]
    if not wanted:
        return []
    rows = (
        await db.execute(
            select(GrammarPoint.id, GrammarPoint.pattern, Lesson.slug)
            .join(Lesson, Lesson.id == GrammarPoint.lesson_id)
            .where(Lesson.slug.in_({slug for slug, _ in wanted}), GrammarPoint.pattern.in_({p for _, p in wanted}))
        )
    ).all()
    found = {(slug, pattern): gid for gid, pattern, slug in rows}
    return [(found[key], key[1]) for key in wanted if key in found]


async def _lapse_cards(db: AsyncSession, learner_id: uuid.UUID, grammar_ids: list[int], now: datetime) -> None:
    """A grammar card the learner just got wrong in a practice question goes back to their
    review queue: it is forgotten once more (app.services.srs.review), so it is due again in
    ten minutes and, forgotten twice, is listed first as a leech. Several questions of one
    sitting that miss the same card count once (the second lapse needs the ten minutes to pass,
    i.e. a real second forgetting, not a second blank of the same exercise). A card they had never
    studied is not "new" any more (`introduced_at` stays empty, so the day's new-card budget is
    not spent on it): it simply comes back as due."""
    states = {
        s.item_id: s
        for s in (
            await db.execute(
                select(ItemState).where(
                    ItemState.learner_id == learner_id,
                    ItemState.item_type == "grammar_point",
                    ItemState.item_id.in_(grammar_ids),
                )
            )
        )
        .scalars()
        .all()
    }
    for gid in grammar_ids:
        state = states.get(gid)
        if (
            state is not None
            and (state.lapses or 0) >= 1
            and (state.reps or 0) == 0
            and state.last_seen is not None
            and now - state.last_seen < srs.RELEARN_DELAY
        ):
            continue  # it was sent back a moment ago (another question of the same sitting): once is enough
        after = srs.review(_schedule_of(state) if state is not None else None, False, now)
        if state is None:
            state = ItemState(learner_id=learner_id, item_type="grammar_point", item_id=gid, last_seen=now)
            db.add(state)
            introduced = None
        else:
            introduced = after.introduced_at
        state.strength = after.strength
        state.reps = after.reps
        state.lapses = after.lapses
        state.ease = after.ease
        state.interval_days = after.interval_days
        state.due_at = after.due_at
        state.introduced_at = introduced
        state.known_at = None  # answered wrong: not known after all, back in the queue
        state.last_seen = now


@router.get("/corpus/items", response_model=list[CorpusItemOut], dependencies=[Depends(require_private_source)])
async def list_corpus_items(
    db: Annotated[AsyncSession, Depends(get_db)],
    level: Annotated[int | None, Query(ge=1, le=6)] = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
):
    """Random sample of corpus.corpus_item for listening practice. No SQL
    JOIN across corpus/content (SDD module-boundary principle) — film/
    topic/grammar names are resolved via separate bulk queries and zipped
    together in application code instead."""
    query = select(CorpusItem).where(CorpusItem.kind == "câu", _visible_to_learners())
    if level is not None:
        query = query.where(CorpusItem.level == level)
    items = (await db.execute(query.order_by(func.random()).limit(limit))).scalars().all()

    film_ids = {i.film_id for i in items}
    films = dict((await db.execute(select(Film.id, Film.title).where(Film.id.in_(film_ids)))).all()) if film_ids else {}

    topic_ids = {tid for i in items for tid in i.topic_ids}
    topics = dict((await db.execute(select(Topic.id, Topic.name).where(Topic.id.in_(topic_ids)))).all()) if topic_ids else {}

    grammar_ids = {gid for i in items for gid in i.grammar_point_ids}
    grammar = (
        dict((await db.execute(select(GrammarPoint.id, GrammarPoint.pattern).where(GrammarPoint.id.in_(grammar_ids)))).all())
        if grammar_ids
        else {}
    )

    return [
        CorpusItemOut(
            id=i.id,
            film_id=i.film_id,
            film_title=films.get(i.film_id, ""),
            text_ko=i.text_ko,
            kind=i.kind,
            level=i.level,
            register=i.register,
            topics=[topics[t] for t in i.topic_ids if t in topics],
            grammar_patterns=[grammar[g] for g in i.grammar_point_ids if g in grammar],
            meaning_vi=i.meaning_vi,
            usage_note_vi=i.usage_note_vi,
        )
        for i in items
    ]


# --------------------------------------------------------- corpus browsing --
# A light copy of corpus.corpus_item (no embedding, de-duplicated, register
# corrected — see app/services/corpus_browse.py). Three endpoints and every
# page of a listening session read from it, so it is kept for a short while
# per process instead of being rebuilt on each request; a freshly confirmed
# import shows up within _SNAPSHOT_TTL_SECONDS.
_SNAPSHOT_TTL_SECONDS = 30.0
_snapshot: tuple[float, list[Sentence]] | None = None


def reset_corpus_snapshot() -> None:
    global _snapshot
    _snapshot = None


def _visible_to_learners():
    """Lines the enrichment step judged unnatural or awkward (corpus_enrich.HIDDEN) are kept in
    the table but never offered; not-yet-judged lines (NULL) are."""
    return or_(CorpusItem.naturalness.is_(None), CorpusItem.naturalness.notin_(corpus_enrich.HIDDEN))


async def _corpus_sentences(db: AsyncSession) -> list[Sentence]:
    global _snapshot
    now = time.monotonic()
    if _snapshot is not None and now - _snapshot[0] < _SNAPSHOT_TTL_SECONDS:
        return _snapshot[1]
    rows = (
        await db.execute(
            select(
                CorpusItem.id,
                CorpusItem.film_id,
                CorpusItem.text_ko,
                CorpusItem.kind,
                CorpusItem.level,
                CorpusItem.register,
                CorpusItem.topic_ids,
                CorpusItem.grammar_point_ids,
                CorpusItem.meaning_vi,
                CorpusItem.usage_note_vi,
            ).where(CorpusItem.kind == "câu", _visible_to_learners())
        )
    ).all()
    sentences = corpus_browse.dedupe(
        [
            corpus_browse.with_effective_register(
                Sentence(
                    id=r[0],
                    film_id=r[1],
                    text_ko=r[2],
                    kind=r[3],
                    level=r[4],
                    register=r[5],
                    topic_ids=tuple(r[6] or ()),
                    grammar_ids=tuple(r[7] or ()),
                    meaning_vi=r[8],
                    usage_note_vi=r[9],
                )
            )
            for r in rows
        ]
    )
    _snapshot = (now, sentences)
    return sentences


async def _id_names(db: AsyncSession, id_col, name_col, ids: set[int]) -> dict[int, str]:
    if not ids:
        return {}
    return dict((await db.execute(select(id_col, name_col).where(id_col.in_(ids)))).all())


async def _corpus_out(db: AsyncSession, sentences: list[Sentence]) -> list[CorpusItemOut]:
    """Names for the ids a page of sentences refers to — separate bulk queries
    zipped in code, never a JOIN across corpus/content (module boundary)."""
    films = await _id_names(db, Film.id, Film.title, {s.film_id for s in sentences})
    topics = await _id_names(db, Topic.id, Topic.name, {t for s in sentences for t in s.topic_ids})
    grammar = await _id_names(db, GrammarPoint.id, GrammarPoint.pattern, {g for s in sentences for g in s.grammar_ids})
    return [
        CorpusItemOut(
            id=s.id,
            film_id=s.film_id,
            film_title=films.get(s.film_id, ""),
            text_ko=s.text_ko,
            kind=s.kind,
            level=s.level,
            register=s.register,
            topics=[topics[t] for t in s.topic_ids if t in topics],
            grammar_patterns=[grammar[g] for g in s.grammar_ids if g in grammar],
            meaning_vi=s.meaning_vi,
            usage_note_vi=s.usage_note_vi,
        )
        for s in sentences
    ]


@router.get("/corpus/facets", response_model=CorpusFacetsOut, dependencies=[Depends(require_private_source)])
async def corpus_facets(db: Annotated[AsyncSession, Depends(get_db)]):
    """What the listening picker can filter by (level, speech level, topic,
    grammar pattern, source film) and how many distinct sentences each holds.
    Public, like the sentences themselves."""
    counts = corpus_browse.count_facets(await _corpus_sentences(db))
    films = await _id_names(db, Film.id, Film.title, {i for i, _ in counts.films})
    topics = await _id_names(db, Topic.id, Topic.name, {i for i, _ in counts.topics})
    grammar = await _id_names(db, GrammarPoint.id, GrammarPoint.pattern, {i for i, _ in counts.grammar})
    return CorpusFacetsOut(
        total=counts.total,
        levels=[CorpusLevelCount(level=lv, count=n) for lv, n in counts.levels],
        registers=[CorpusRegisterCount(register=r, count=n) for r, n in counts.registers],
        topics=[CorpusTopicCount(id=i, name=topics[i], count=n) for i, n in counts.topics if i in topics],
        grammar=[CorpusGrammarCount(id=i, pattern=grammar[i], count=n) for i, n in counts.grammar if i in grammar],
        films=[CorpusFilmCount(id=i, title=films[i], count=n) for i, n in counts.films if i in films],
    )


@router.get("/corpus/browse", response_model=CorpusPageOut, dependencies=[Depends(require_private_source)])
async def browse_corpus(
    db: Annotated[AsyncSession, Depends(get_db)],
    level: Annotated[int | None, Query(ge=1, le=6)] = None,
    topic_id: Annotated[int | None, Query(ge=1)] = None,
    register: Annotated[Literal["존댓말", "반말", "hỗn hợp"] | None, Query()] = None,
    grammar_id: Annotated[int | None, Query(ge=1)] = None,
    film_id: Annotated[int | None, Query(ge=1)] = None,
    seed: Annotated[str, Query(max_length=40)] = "",
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
):
    """A page of distinct sentences matching the filters, in an order fixed by
    `seed`: ask for offset 0, 10, 20… with the same seed and every sentence
    comes up exactly once (a fresh random sample per request cannot promise
    that). The client picks a new random seed for each listening session."""
    matching = [
        s
        for s in await _corpus_sentences(db)
        if corpus_browse.matches(
            s, level=level, topic_id=topic_id, register=register, grammar_id=grammar_id, film_id=film_id
        )
    ]
    page = corpus_browse.seeded_order(matching, seed)[offset : offset + limit]
    return CorpusPageOut(total=len(matching), offset=offset, items=await _corpus_out(db, page))


@router.get("/corpus/items/{item_id}/similar", response_model=list[CorpusSimilarOut], dependencies=[Depends(require_private_source)])
async def similar_corpus_items(
    item_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=10)] = 3,
    max_distance: Annotated[float, Query(ge=0, le=2)] = 0.4,
):
    """Sentences close in meaning to this one — the same idea said another way
    (a politer or plainer ending, other word forms) — nearest first. Uses the
    embedding stored when the sentence was imported; word-for-word repeats are
    never offered as "similar"."""
    target = await db.get(CorpusItem, item_id)
    if target is None:
        raise _problem(status.HTTP_404_NOT_FOUND, "Corpus item not found", "not_found")
    if target.embedding is None:
        return []

    distance = CorpusItem.embedding.cosine_distance(target.embedding)
    rows = (
        await db.execute(
            select(CorpusItem.id, distance.label("distance"))
            .where(
                CorpusItem.id != item_id,
                CorpusItem.kind == "câu",
                CorpusItem.embedding.is_not(None),
                distance <= max_distance,
            )
            .order_by(distance)
            .limit(limit * 6)  # headroom: copies and repeats are filtered out below
        )
    ).all()

    by_id = {s.id: s for s in await _corpus_sentences(db)}
    own_key = corpus_browse.normalize_key(target.text_ko)
    picked: list[tuple[Sentence, float]] = []
    seen_keys = {own_key}
    for near_id, dist in rows:
        sentence = by_id.get(near_id)  # absent = a repeat of a sentence kept elsewhere
        if sentence is None:
            continue
        key = corpus_browse.normalize_key(sentence.text_ko)
        if key in seen_keys:
            continue
        seen_keys.add(key)
        picked.append((sentence, float(dist)))
        if len(picked) == limit:
            break

    outs = await _corpus_out(db, [s for s, _ in picked])
    return [CorpusSimilarOut(**o.model_dump(), distance=round(d, 3)) for o, (_, d) in zip(outs, picked)]


@router.post("/progress/reviews", response_model=ItemStateOut, dependencies=[Depends(study_day)])
async def record_item_review(
    body: ItemStateReviewRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    profile: Annotated[Profile, Depends(get_current_profile)],
):
    """A learner's quick in-app check. It nudges ItemState.strength (SRS §5
    ITEM_STATE's decay-style nudge, the readiness signal) and moves the item's
    review schedule (app.services.srs: when it is due again, how often it was
    forgotten). A wrong answer is also written to the error log, so the same
    mistake can be found again (app.services.weakness). The item must exist:
    item_id has no FK (content lives in another schema), so without this check a
    typo'd or made-up id would quietly become a phantom ItemState row that skews
    the learner's streak and readiness."""
    content_model = VocabItem if body.item_type == "vocab_item" else GrammarPoint
    row = (await db.execute(select(content_model).where(content_model.id == body.item_id))).scalar_one_or_none()
    if row is None:
        raise _problem(status.HTTP_404_NOT_FOUND, "Item not found", "not_found")
    if settings.BILLING_ENABLED and row.lesson_id is not None:  # a card of a lesson the learner has not unlocked
        owner = await db.get(Lesson, row.lesson_id)
        if owner is not None:
            await _require_open(db, profile, owner)

    existing = await db.execute(
        select(ItemState).where(
            ItemState.learner_id == profile.id,
            ItemState.item_type == body.item_type,
            ItemState.item_id == body.item_id,
        )
    )
    state = existing.scalar_one_or_none()
    now = datetime.now(timezone.utc)
    hard = body.correct and srs.is_hard(body.hard, body.response_ms)
    after = srs.review(_schedule_of(state) if state is not None else None, body.correct, now, hard=hard)
    if state is None:
        state = ItemState(learner_id=profile.id, item_type=body.item_type, item_id=body.item_id, last_seen=now)
        db.add(state)
    state.strength = after.strength
    state.reps = after.reps
    state.lapses = after.lapses
    state.ease = after.ease
    state.interval_days = after.interval_days
    state.due_at = after.due_at
    state.introduced_at = after.introduced_at
    state.last_seen = now
    state.last_correct = body.correct
    if not body.correct:
        state.known_at = None  # marked "Đã biết" but forgotten: it goes back into the queue
        db.add(_error_for(profile.id, body, row))
    if body.item_type == "grammar_point":  # the flip-card review is "nhận ra", rung 0 of the ladder
        await competency_db.record_outcomes(db, profile.id, [body.item_id], 0, body.correct)
    await db.commit()
    await db.refresh(state)
    return state


def _error_for(learner_id: uuid.UUID, body: ItemStateReviewRequest, row: VocabItem | GrammarPoint) -> ErrorLog:
    """The error-log row for a wrong review answer."""
    mode = body.mode or "recognize"
    is_vocab = isinstance(row, VocabItem)
    detail: dict[str, str] = {}
    if body.chosen:
        detail["chosen"] = body.chosen
    family = getattr(row, "family", None)
    if family:
        detail["family"] = family
    return ErrorLog(
        learner_id=learner_id,
        skill="vocab" if is_vocab else "grammar",
        error_type=weakness.error_type_for_review(body.item_type, mode, bool(getattr(row, "node_word", None))),
        example_ko=row.hangul if is_vocab else row.pattern,
        item_type=body.item_type,
        item_id=body.item_id,
        mode=mode,
        detail=detail or None,
    )


def _schedule_of(state: ItemState) -> srs.Schedule:
    return srs.Schedule(
        strength=state.strength,
        reps=state.reps or 0,
        lapses=state.lapses or 0,
        ease=state.ease or srs.START_EASE,
        interval_days=state.interval_days or 0.0,
        due_at=state.due_at,
        introduced_at=state.introduced_at,
        known=getattr(state, "known_at", None) is not None,
    )


def _new_limit(profile: Profile, requested: int, now: datetime) -> int:
    """The day's new-card cap, or none on a "Hôm nay bận — chỉ ôn" day."""
    return srs.new_limit_for(requested, getattr(profile, "review_only_on", None), journey.today_vn(now))


async def _content_row(db: AsyncSession, profile: Profile, item_type: str, item_id: int) -> VocabItem | GrammarPoint:
    """The card behind a learner's mark: it must exist, in a lesson they may open."""
    content_model = VocabItem if item_type == "vocab_item" else GrammarPoint
    row = (await db.execute(select(content_model).where(content_model.id == item_id))).scalar_one_or_none()
    if row is None:
        raise _problem(status.HTTP_404_NOT_FOUND, "Item not found", "not_found")
    if settings.BILLING_ENABLED and row.lesson_id is not None:
        owner = await db.get(Lesson, row.lesson_id)
        if owner is not None:
            await _require_open(db, profile, owner)
    return row


async def _state_of(db: AsyncSession, learner_id: uuid.UUID, item_type: str, item_id: int) -> ItemState | None:
    return (
        await db.execute(
            select(ItemState).where(
                ItemState.learner_id == learner_id,
                ItemState.item_type == item_type,
                ItemState.item_id == item_id,
            )
        )
    ).scalar_one_or_none()


@router.post("/srs/items/{item_type}/{item_id}/known", response_model=ItemStateOut)
async def mark_known(
    item_type: Literal["vocab_item", "grammar_point"],
    item_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    profile: Annotated[Profile, Depends(get_current_profile)],
):
    """"Đã biết": the learner already knows this card. It leaves the review queue — never offered
    as new, never due, and it does not use up the day's new cards (app.services.srs) — until it is
    undone (DELETE) or answered wrong somewhere. A card never studied before counts as mastered
    (strength srs.KNOWN_STRENGTH); one with a history keeps its strength and schedule, so undoing
    the mark puts it back exactly where it was."""
    await _content_row(db, profile, item_type, item_id)
    now = datetime.now(timezone.utc)
    state = await _state_of(db, profile.id, item_type, item_id)
    if state is None:
        state = ItemState(
            learner_id=profile.id, item_type=item_type, item_id=item_id, strength=srs.KNOWN_STRENGTH,
            last_seen=now, reps=0, lapses=0, ease=srs.START_EASE, interval_days=0.0, due_at=None, introduced_at=None,
        )
        db.add(state)
    if state.known_at is None:
        state.known_at = now
    await db.commit()
    await db.refresh(state)
    return state


@router.delete("/srs/items/{item_type}/{item_id}/known", status_code=status.HTTP_204_NO_CONTENT)
async def unmark_known(
    item_type: Literal["vocab_item", "grammar_point"],
    item_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    profile: Annotated[Profile, Depends(get_current_profile)],
):
    """Undo "Đã biết". A row that exists only because of the mark is removed, so the card is new
    again; otherwise the card goes back to its own schedule."""
    state = await _state_of(db, profile.id, item_type, item_id)
    if state is None or state.known_at is None:
        return None
    if srs.only_marked_known(_schedule_of(state)) and state.last_correct is None:
        await db.delete(state)
    else:
        state.known_at = None
    await db.commit()
    return None


@router.put("/me/review-only", response_model=ReviewOnlyOut)
async def set_review_only(
    body: ReviewOnlyRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    profile: Annotated[Profile, Depends(get_current_profile)],
):
    """"Hôm nay bận — chỉ ôn": today (Vietnam time) the review queue offers only the due cards, no
    new ones. It lapses on its own tomorrow; `on: false` undoes it for today."""
    today = journey.today_vn(datetime.now(timezone.utc))
    profile.review_only_on = today if body.on else None
    db.add(profile)
    await db.commit()
    return ReviewOnlyOut(review_only=body.on, day=today if body.on else None)


@router.get("/me/review-queue", response_model=ReviewQueueOut)
async def get_review_queue(
    db: Annotated[AsyncSession, Depends(get_db)],
    profile: Annotated[Profile, Depends(get_current_profile)],
    limit: Annotated[int, Query(ge=1, le=60)] = srs.DEFAULT_REVIEW_LIMIT,
    new: Annotated[int, Query(ge=0, le=30)] = srs.DEFAULT_NEW_PER_DAY,
    focus: Annotated[Literal["due", "weak"], Query()] = "due",
):
    """Today's sitting: the cards that are due (cards the learner keeps forgetting
    first, then the most overdue), then new ones — from the earliest lessons that
    still have unseen cards, plus words from the confirmed news articles that fit
    the learner's goal level — at most `new` per rolling 24 hours (about one
    grammar point and one article word in four). A due vocabulary card that has
    been answered right before is asked as a fill-in-the-blank when one can be
    built from it (app.services.exercises); a new, forgotten or grammar card is
    shown for the ordinary flip-and-judge review.

    `focus=weak` is practice on demand instead: the cards the learner keeps
    forgetting, due or not (an answer before the due time still counts for
    strength and the error log, but does not push the schedule out)."""
    now = datetime.now(timezone.utc)
    states = (await db.execute(select(ItemState).where(ItemState.learner_id == profile.id))).scalars().all()
    lesson_items = await _open_lesson_items(db, profile, await _lesson_item_keys(db))
    articles = await _word_sources(db, profile)
    schedules = {(s.item_type, s.item_id): _schedule_of(s) for s in states}
    if focus == "weak":
        existing = {key for keys in lesson_items.values() for key in keys}
        existing |= {key for keys in articles.keys.values() for key in keys}
        weak = srs.weak_keys(schedules, existing, limit=limit)
        queue = srs.Queue(due=weak, due_total=len(srs.weak_keys(schedules, existing, limit=10_000)))
    else:
        queue = srs.build_queue(
            schedules,
            lesson_items,
            now,
            limit=limit,
            new_limit=_new_limit(profile, new, now),
            articles=articles.keys,
            hold=articles.hold,
            order=await _lesson_order(db, profile.id),
            later=await _recognize_only(db),
        )

    keys = [*queue.due, *queue.new]
    vocab_ids = [i for t, i in keys if t == "vocab_item"]
    grammar_ids = [i for t, i in keys if t == "grammar_point"]
    vocab = {}
    if vocab_ids:
        vocab = {v.id: v for v in (await db.execute(select(VocabItem).where(VocabItem.id.in_(vocab_ids)))).scalars().all()}
    grammar = {}
    if grammar_ids:
        grammar = {
            g.id: g for g in (await db.execute(select(GrammarPoint).where(GrammarPoint.id.in_(grammar_ids)))).scalars().all()
        }
    lesson_ids = {v.lesson_id for v in vocab.values() if v.lesson_id} | {g.lesson_id for g in grammar.values() if g.lesson_id}
    titles: dict[int, str] = {}
    mates: dict[int, list[VocabItem]] = defaultdict(list)
    if lesson_ids:
        titles = dict((await db.execute(select(Lesson.id, Lesson.title).where(Lesson.id.in_(lesson_ids)))).all())
        for v in (await db.execute(select(VocabItem).where(VocabItem.lesson_id.in_(lesson_ids)))).scalars().all():
            mates[v.lesson_id].append(v)
    # an article word's mates, for the fill-in-the-blank, are the other words of its article
    article_mates: dict[str, list[VocabItem]] = defaultdict(list)
    article_ids = {articles.article_of[v.id] for v in vocab.values() if v.id in articles.article_of}
    if article_ids:
        wanted = [vid for aid in article_ids for _, vid in articles.keys.get(aid, [])]
        for v in (await db.execute(select(VocabItem).where(VocabItem.id.in_(wanted)))).scalars().all():
            article_mates[articles.article_of[v.id]].append(v)

    items: list[ReviewQueueItem] = []
    due_keys = set(queue.due)
    for item_type, item_id in keys:
        row = vocab.get(item_id) if item_type == "vocab_item" else grammar.get(item_id)
        if row is None:  # deleted between the two queries
            continue
        schedule = schedules.get((item_type, item_id))
        is_new = (item_type, item_id) not in due_keys
        source = articles.article_of.get(item_id) if item_type == "vocab_item" and row.lesson_id is None else None
        article_id = source if source and not source.startswith("bank:") else None
        bank_deck = source[5:] if source and source.startswith("bank:") else None
        cloze = None
        if item_type == "vocab_item" and not is_new and schedule is not None and schedule.reps >= 1:
            pool = article_mates.get(source, []) if source else mates.get(row.lesson_id, [])
            built = build_cloze(row, pool, seed=f"{profile.id}:{item_id}:{schedule.reps}")
            if built is not None:
                cloze = ClozeOut(prompt_ko=built.prompt_ko, answer=built.answer, choices=list(built.choices))
        items.append(
            ReviewQueueItem(
                item_type=item_type,  # type: ignore[arg-type]
                item_id=item_id,
                is_new=is_new,
                mode="cloze" if cloze is not None else "recognize",
                reps=schedule.reps if schedule else 0,
                lapses=schedule.lapses if schedule else 0,
                leech=bool(schedule and srs.is_leech(schedule)),
                due_at=schedule.due_at if schedule else None,
                lesson_title=titles.get(row.lesson_id) if row.lesson_id else None,
                article_id=uuid.UUID(article_id) if article_id else None,
                article_title=articles.title_of.get(article_id) if article_id else None,
                bank_deck=bank_deck,
                bank_title=articles.title_of.get(source) if bank_deck else None,
                vocab=VocabItemOut.model_validate(row) if item_type == "vocab_item" else None,
                grammar=GrammarPointOut.model_validate(row) if item_type == "grammar_point" else None,
                cloze=cloze,
            )
        )
    return ReviewQueueOut(
        due_total=queue.due_total,
        new_available=queue.new_budget,
        new_today=queue.new_today,
        items=items,
        focus=focus,
        article_waiting=queue.article_waiting,
        article_above_level=sum(
            1 for key in articles.hold if key not in schedules
        ),
        review_only=_new_limit(profile, 1, now) == 0,
    )


async def _topic_review_task(
    db: AsyncSession, learner_id: uuid.UUID, lesson_items: dict[int, list[ItemKey]], studied: set[ItemKey]
) -> TodayPlanTask | None:
    """"Ôn tập chủ đề": once the learner has met every grammar card of a topic (each has an
    ItemState, i.e. was introduced in their reviews), the topic's review lesson is offered until
    they have answered all of its timed mixed set. One topic at a time, the earliest first.
    Words are not required: a topic holds hundreds and the review is about choosing between
    the patterns, which is what a learner is ready for after the last lesson's cards."""
    reviews = list(
        (
            await db.execute(
                select(Lesson.id, Lesson.title, Lesson.practice["review"]["mock"]["question_ids"])
                .where(Lesson.practice["kind"].as_string() == "review")
                .order_by(*_LESSON_ORDER)
            )
        ).all()
    )
    if not reviews:
        return None
    links = (
        await db.execute(
            select(LessonTopic.lesson_id, LessonTopic.topic_id, Topic.name).join(Topic, Topic.id == LessonTopic.topic_id)
        )
    ).all()
    lessons_of: dict[int, set[int]] = defaultdict(set)
    topic_name: dict[int, str] = {}
    topics_of: dict[int, set[int]] = defaultdict(set)
    for lesson_id, topic_id, name in links:
        lessons_of[topic_id].add(lesson_id)
        topic_name[topic_id] = name
        topics_of[lesson_id].add(topic_id)
    review_ids = {rid for rid, _, _ in reviews}
    answered_rows = (
        await db.execute(
            select(LessonExerciseResult.lesson_id, LessonExerciseResult.question_id).where(
                LessonExerciseResult.learner_id == learner_id, LessonExerciseResult.lesson_id.in_(review_ids)
            )
        )
    ).all()
    answered: dict[int, set[str]] = defaultdict(set)
    for lesson_id, question_id in answered_rows:
        answered[lesson_id].add(question_id)
    for review_id, title, question_ids in reviews:
        mock = list(question_ids or [])
        for topic_id in sorted(topics_of.get(review_id, ())):
            cards = [
                key
                for lid in lessons_of[topic_id]
                if lid not in review_ids
                for key in lesson_items.get(lid, [])
                if key[0] == "grammar_point"
            ]
            if not cards or any(key not in studied for key in cards):
                continue  # the topic is not finished yet
            done = len(answered.get(review_id, set()) & set(mock))
            if mock and done >= len(mock):
                continue  # the timed set has been answered: nothing to remind about
            return TodayPlanTask(
                kind="topic_review",
                title=f"Ôn tập chủ đề: {topic_name[topic_id]}",
                subtitle=f"Bạn đã gặp hết ngữ pháp của chủ đề · bản đồ ngữ pháp + thi thử {len(mock)} câu",
                status="in_progress" if done else "todo",
                lesson_id=review_id,
            )
    return None


async def _daily_reading_task(
    db: AsyncSession, learner_id: uuid.UUID, states: list[ItemState], now: datetime
) -> TodayPlanTask | None:
    """The plan line for /daily. Reads today's picks (or previews them) — it writes nothing."""
    cards = daily_reading_db.cards_of(states, now)
    if not cards:
        return None
    ctx = await daily_reading_db.load_context(db)
    today = await daily_reading_db.sitting(db, learner_id, cards, ctx, now, persist=False)
    if not today.picks:
        return None
    done = sum(1 for p in today.picks if p.done)
    parts = {"dialogue": "hội thoại", "reading": "bài đọc"}
    what = " + ".join(f"1 {parts[p.passage.kind]}" for p in today.picks)
    return TodayPlanTask(
        kind="daily_reading",
        title="Đọc & nghe hôm nay",
        subtitle=f"{what} · chọn theo những gì bạn đã học, giọng Chirp",
        status="done" if done == len(today.picks) else ("in_progress" if done else "todo"),
    )


@router.get("/me/plan", response_model=TodayPlanOut)
async def get_my_plan(
    db: Annotated[AsyncSession, Depends(get_db)],
    profile: Annotated[Profile, Depends(get_current_profile)],
):
    """Real /today data — every field here comes from a query, never a
    hardcoded placeholder. `streak_days`/`readiness_pct` are derived from
    ItemState (the only per-learner history table that exists so far —
    see its docstring), so a brand-new learner honestly gets 0/None
    rather than fake numbers; the frontend renders that as a first-run
    empty state instead of a lie. Each task is only included when there
    is real content behind it (a lesson/corpus item/confirmed article
    actually exists) and `status` is only ever "done"/"in_progress" when
    that is something this endpoint can actually verify — no fabricated
    checkmarks like the old Lovable mock had."""
    states = (
        (await db.execute(select(ItemState).where(ItemState.learner_id == profile.id))).scalars().all()
    )
    today = datetime.now(timezone.utc).date()
    readiness_pct = round(sum(s.strength for s in states) / len(states) * 100, 1) if states else None

    # the streak and Hành trình Thiên Nga read the days studied (Vietnam time); the item states'
    # last-seen days are added for anything recorded before learner_day existed
    # the chapters finished (feathers) decide the stage; the support topics give relics and sparkle
    course = await feathers.course(db)
    feather_tally = feathers.tally(course, await feathers.record(db, profile.id), await _placed_at(db, profile.id))
    relics_now = [c.code for c in feather_tally.constellations if c.done and c.relic]
    trip = await journey.compute(
        db,
        profile.id,
        feather_tally.stage,
        len(states),
        extra_days={journey.day_of(s.last_seen) for s in states},
        relics=relics_now,
        sparkle=feather_tally.sparkle,
    )
    streak_days = trip.streak
    if trip.changed:
        await db.commit()

    tasks: list[TodayPlanTask] = []

    # -- vocab/grammar review: the first lesson this learner has not yet
    # mastered (see app.services.progress.pick_next_lesson), so finishing
    # lesson 1 moves them on to lesson 2 instead of showing lesson 1 forever.
    # Two narrow bulk queries (ids only) — vocab/grammar that belong to no
    # lesson (editorial-article imports) are left out, they are not lesson
    # content.
    lesson_items = await _open_lesson_items(db, profile, await _lesson_item_keys(db))
    lesson_order = await _lesson_order(db, profile.id)

    # -- today's review sitting (the /review screen): cards that are due plus the
    # day's new ones, counted by the same rule that builds the queue itself.
    now = datetime.now(timezone.utc)
    articles = await _word_sources(db, profile)
    queue = srs.build_queue(
        {(s.item_type, s.item_id): _schedule_of(s) for s in states},
        lesson_items,
        now,
        new_limit=_new_limit(profile, srs.DEFAULT_NEW_PER_DAY, now),
        articles=articles.keys,
        hold=articles.hold,
        order=lesson_order,
        later=await _recognize_only(db),
    )
    lesson_keys_all = {key for keys in lesson_items.values() for key in keys}
    lesson_keys_all |= {key for keys in articles.keys.values() for key in keys}
    studied_today = sum(
        1
        for s in states
        if (s.item_type, s.item_id) in lesson_keys_all and s.last_seen.astimezone(timezone.utc).date() == today
    )
    waiting = queue.due_total + len(queue.new)
    if waiting > 0:
        parts = [f"{queue.due_total} thẻ đến hạn"] if queue.due_total else []
        if queue.new:
            parts.append(f"{len(queue.new)} thẻ mới")
        tasks.append(
            TodayPlanTask(
                kind="review",
                title="Ôn tập hôm nay",
                subtitle=" · ".join(parts),
                status="in_progress" if studied_today else "todo",
            )
        )
    elif studied_today:
        tasks.append(
            TodayPlanTask(
                kind="review",
                title="Ôn tập hôm nay",
                subtitle="Đã ôn hết thẻ đến hạn, hẹn lần sau",
                status="done",
            )
        )

    practice = await _practice_by_lesson(db, profile.id)
    picked = pick_next_lesson(
        lesson_items, {(s.item_type, s.item_id): (s.strength, s.last_seen) for s in states}, lesson_order, practice
    )
    lesson = await db.get(Lesson, picked.lesson_id) if picked is not None else None
    placed = await _placed_at(db, profile.id)
    if placed and (lesson is None or (lesson.sort_order or 0) < placed):
        # the entry check put this learner further on than the lessons they can open: show where
        # they start (its preview offers the packs), not Nền tảng 1 again
        start = (
            await db.execute(select(Lesson).where(Lesson.sort_order >= placed).order_by(*_LESSON_ORDER).limit(1))
        ).scalars().first()
        if start is not None and start.id not in lesson_items:
            tasks.append(
                TodayPlanTask(
                    kind="vocab_review",
                    title=start.title,
                    subtitle="Bài bắt đầu theo kiểm tra đầu vào · cần mở gói",
                    status="todo",
                    lesson_id=start.id,
                    step="listen",
                )
            )
            picked = None
    if picked is not None and lesson is not None:
        keys = lesson_items[picked.lesson_id]
        seen_keys = {(s.item_type, s.item_id) for s in states}
        vocab_keys = [k for k in keys if k[0] == "vocab_item"]
        grammar_keys = [k for k in keys if k[0] == "grammar_point"]
        step = resume_step(
            sum(1 for k in vocab_keys if k in seen_keys),
            len(vocab_keys),
            sum(1 for k in grammar_keys if k in seen_keys),
            len(grammar_keys),
            picked.practice_answered,
            picked.practice_total,
        )
        # what is left, in the words the lesson screen uses; "đã thuộc" is memory, kept apart from "đã học"
        subtitle = f"Đã học {picked.met}/{picked.total} từ và mẫu"
        if picked.total == 0:  # Bảng chữ cái: only its end check is counted here
            subtitle = f"5 phần ngắn · kiểm tra cuối bài {picked.practice_answered}/{picked.practice_total} câu"
        elif picked.practice_total:
            subtitle += f" · luyện tập {picked.practice_answered}/{picked.practice_total} câu"
        if picked.mastered:
            subtitle += f" · đã thuộc {picked.mastered}"
        tasks.append(
            TodayPlanTask(
                kind="vocab_review",
                title=lesson.title,
                subtitle=subtitle,
                status="done" if picked.studied else ("in_progress" if step != "listen" else "todo"),
                lesson_id=lesson.id,
                step=step,
            )
        )

    # -- the topic review ("Ôn tập chủ đề"): offered once every grammar card of a topic was met
    topic_review = await _topic_review_task(db, profile.id, lesson_items, {(s.item_type, s.item_id) for s in states})
    if topic_review is not None:
        tasks.append(topic_review)

    # -- the day's reading and dialogue (the /daily screen): offered once the learner has met the
    # grammar of some text; "done" when both of today's texts have been answered.
    daily = await _daily_reading_task(db, profile.id, states, now)
    if daily is not None:
        tasks.append(daily)

    # -- listening: no per-item completion is tracked yet for corpus
    # items (only lesson vocab/grammar go through /progress/reviews), so
    # this is honestly always "todo" rather than a faked checkmark.
    corpus_count = (
        await db.execute(select(func.count()).select_from(CorpusItem).where(CorpusItem.kind == "câu"))
    ).scalar_one()
    # the corpus and the editorials are closed to learners while their copyright is not settled
    # (deps.require_private_source): a learner is never sent to a door that says "Chưa mở"
    closed = _sources_closed_to(profile)
    if corpus_count > 0 and not closed:
        tasks.append(
            TodayPlanTask(
                kind="listening",
                title="Luyện nghe câu mẫu từ phim",
                subtitle=f"{corpus_count} câu có sẵn, giọng đọc chuẩn Seoul",
                status="todo",
            )
        )

    # -- reading: a confirmed article that follows the lessons this learner has been through (see
    # app.services.reading_path); an article not placed on the course path (an older import) is TOPIK II
    # level 5-6 reading for the essay (câu 54), offered only to a learner who aims at TOPIK II.
    article = None
    submission = None
    if not closed:
        rows = (
            await db.execute(
                select(
                    EditorialArticle.id,
                    EditorialArticle.level_estimate,
                    EditorialArticle.related_lesson_ids,
                    EditorialArticle.created_at,
                ).where(func.length(func.btrim(EditorialArticle.body_ko)) > 0)
            )
        ).all()
        finished = {
            str(aid)
            for aid in (
                await db.execute(
                    select(EditorialOutlineSubmission.editorial_article_id).where(
                        EditorialOutlineSubmission.learner_id == profile.id,
                        EditorialOutlineSubmission.revision_count > 0,
                    )
                )
            ).scalars()
        } | {
            str(aid)
            for aid in (
                await db.execute(select(EditorialRead.editorial_article_id).where(EditorialRead.learner_id == profile.id))
            ).scalars()
        }
        chosen = reading_path.pick(
            [
                reading_path.Candidate(str(aid), level, list(related or []), created.timestamp())
                for aid, level, related, created in rows
            ],
            reading_path.studied_lessons(lesson_order, picked.lesson_id if picked is not None else None),
            finished,
            editorial_goal=profile.goal in EDITORIAL_GOALS,
        )
        if chosen is not None:
            article = await db.get(EditorialArticle, uuid.UUID(chosen.id))
            submission = chosen.id in finished
    if article is not None:
        tasks.append(
            TodayPlanTask(
                kind="reading",
                title=article.title_ko or article.source_name,
                subtitle=(
                    "Đọc báo · hợp với bài bạn vừa học"
                    if article.related_lesson_ids
                    else "Đọc xã luận · luyện dàn ý câu 54"
                ),
                status="done" if submission else "todo",
                article_id=article.id,
            )
        )

    # -- the entry diagnostic, offered until it has been taken once (it follows the review, which stays first)
    taken = (
        await db.execute(select(PlacementAttempt.id).where(PlacementAttempt.learner_id == profile.id).limit(1))
    ).first()
    if taken is None and placement.DIAGNOSTIC_FILE.is_file():
        task = TodayPlanTask(
            kind="placement",
            title="Tìm bài bắt đầu",
            subtitle="Khoảng 2 phút · không bắt buộc",
            status="todo",
        )
        # a learner who has studied nothing yet sees it first: it decides what the rest should be
        tasks.insert(1 if states and tasks and tasks[0].kind == "review" else 0, task)

    return TodayPlanOut(
        streak_days=streak_days,
        readiness_pct=readiness_pct,
        goal=profile.goal,
        exam_date=profile.exam_date,
        tasks=tasks,
        journey=JourneyOut(
            stage=trip.stage,
            shown_stage=trip.shown_stage,
            missed_days=trip.missed_days,
            cursed=trip.cursed,
            studied_today=trip.studied_today,
            items=trip.items,
            name=trip.name,
            card=trip.card,
            shield_ready=trip.shield_ready,
            shield_day=trip.shield_day,
            **_feather_fields(feather_tally, trip.relics, trip.sparkle),
        ),
    )


def _sources_closed_to(profile: Profile) -> bool:
    """True when the corpus, editorials and real past papers are closed to this account (see
    deps.require_private_source)."""
    return bool(settings.BILLING_ENABLED and settings.BILLING_PRIVATE_SOURCES) and getattr(profile, "role", None) not in billing_access.STAFF_ROLES


def _feather_fields(t: feathers.Tally, relics: list[str], sparkle: int) -> dict:
    """The feather side of the journey: the chapters, the station, the starlight and the sky."""
    return {
        "chapters": [
            JourneyChapterOut(
                n=c.n,
                name=feathers.CHAPTERS[c.n].name,
                level=feathers.CHAPTERS[c.n].level,
                becomes=feathers.CHAPTERS[c.n].becomes,
                earned=c.earned,
                credited=c.credited,
                total=c.total,
                lessons=c.lessons,
                lessons_done=c.lessons_done,
                done=c.done,
            )
            for c in t.chapters.values()
        ],
        "station": t.station,
        "starlight": t.starlight,
        "starlight_total": t.starlight_total,
        "sparkle": sparkle,
        "next_sparkle_at": next((at for at in feathers.SPARKLE_AT if t.starlight < at), None) if sparkle < 3 else None,
        "relics": relics,
        "constellations": [
            ConstellationOut(
                code=c.code,
                name=c.name,
                topic=c.topic,
                relic=c.relic,
                relic_earned=c.code in relics,
                stars=[StarOut(lesson_id=x.lesson_id, title=x.title, earned=x.earned, total=x.total, lit=x.lit) for x in c.stars],
            )
            for c in t.constellations
        ],
    }


@router.patch("/me/goal", response_model=ProfileOut)
async def set_my_goal(
    goal: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    profile: Annotated[Profile, Depends(get_current_profile)],
):
    profile.goal = goal
    await db.commit()
    await db.refresh(profile)
    return profile

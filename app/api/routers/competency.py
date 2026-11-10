"""What the learner can do, and a review that mixes what they have learned.

* GET /lessons/{id}/mix     — the mixed review at the end of a lesson (app.services.competency)
* GET /me/competency        — the competency report by topic: coverage, memory, use, weak spots, next steps
* GET /placement            — the entry diagnostic (app.services.placement)
* POST /me/placement        — its answers: evidence for the cards, a first review for the known ones
* GET /me/placement         — the latest result

Both read the same three things: the practice sets (what can be asked), `grammar_competency` (what the
learner has been able to do) and `item_state` (what they still remember).
"""
from collections import defaultdict
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import _problem, ensure_lesson_open, get_current_profile, study_day
from app.api.routers.content import _LESSON_ORDER
from app.db import get_db
from app.models import GrammarPoint, ItemState, Lesson, LessonExerciseResult, LessonTopic, PlacementAttempt, Profile, Topic
from app.schemas import (
    CompetencyLessonOut,
    CompetencyNextOut,
    CompetencyOut,
    CompetencySummaryOut,
    CompetencyTopicOut,
    CompetencyWeakOut,
    MixItemOut,
    MixOut,
    PlacementItemOut,
    PlacementOut,
    PlacementSubmit,
    PlacementSummaryOut,
)
from app.services import competency, competency_db, placement, srs
from app.services.billing import access as billing_access

router = APIRouter(tags=["competency"])


# ----------------------------------------------------------------- mixed review --
@router.get("/lessons/{lesson_id}/mix", response_model=MixOut)
async def get_mix(
    lesson_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    profile: Annotated[Profile, Depends(get_current_profile)],
    limit: Annotated[int, Query(ge=1, le=competency.MAX_MIX)] = competency.DEFAULT_MIX,
):
    """The mixed review for the end of a lesson: exercises of this and EARLIER lessons about the
    grammar cards the learner has already met — cards due for review first (at the rung their
    recent answers call for), then questions they got wrong, then ones they have not done yet.
    Each item is graded in the browser and answered through its own lesson's answers endpoint,
    so it feeds the progress, the error log, the review schedule and the competency record."""
    lesson = await db.get(Lesson, lesson_id)
    if lesson is None:
        raise _problem(404, "Lesson not found", "not_found")
    order = list((await db.execute(select(Lesson.id).order_by(*_LESSON_ORDER))).scalars().all())
    if lesson_id not in order:
        raise _problem(404, "Lesson not found", "not_found")
    pool_ids = order[: order.index(lesson_id) + 1]
    await ensure_lesson_open(db, profile, lesson)
    held = await billing_access.load_access(db, profile)
    if held.enforced and not held.everything:
        # earlier lessons the learner has not unlocked must not leak their questions into this mix
        sorts = dict((await db.execute(select(Lesson.id, Lesson.sort_order))).all())
        pool_ids = [i for i in pool_ids if held.can_open(sorts.get(i))]
    position = {lid: i for i, lid in enumerate(order)}

    rows = (
        await db.execute(
            select(
                Lesson.id,
                Lesson.title,
                Lesson.practice["kind"].as_string(),
                Lesson.practice["items"],
                Lesson.practice["grammar"],
            ).where(Lesson.id.in_(pool_ids))
        )
    ).all()
    titles = {lid: title for lid, title, *_ in rows}
    exercises: dict[tuple[int, str], dict] = {}
    sets: list[competency.PracticeSet] = []
    grammar_info: dict[int, dict] = {}
    for lid, _title, kind, items, grammar in rows:
        if kind == "review" or not items:
            continue
        for ex in items:
            exercises[(lid, ex["id"])] = ex
        grammar_info[lid] = grammar or {}
        sets.append(competency.PracticeSet(lid, position[lid], items, grammar or {}))

    gid_of = {
        (slug, pattern): gid
        for gid, pattern, slug in (
            await db.execute(select(GrammarPoint.id, GrammarPoint.pattern, Lesson.slug).join(Lesson, Lesson.id == GrammarPoint.lesson_id))
        ).all()
    }
    candidates = competency.build_candidates(sets, gid_of)
    now = datetime.now(timezone.utc)
    cards = await competency_db.card_states(db, profile.id, now)
    results = {
        (lid, qid): bool(ok)
        for lid, qid, ok in (
            await db.execute(
                select(LessonExerciseResult.lesson_id, LessonExerciseResult.question_id, LessonExerciseResult.correct).where(
                    LessonExerciseResult.learner_id == profile.id, LessonExerciseResult.lesson_id.in_(pool_ids)
                )
            )
        ).all()
    }
    picks = competency.select_mix(candidates, cards, results, lesson_id, limit=limit)

    slug_to_id: dict[str, int] = {}
    wanted = {info["lesson_slug"] for p in picks for info in grammar_info[p.candidate.lesson_id].values()}
    if wanted:
        slug_to_id = dict((await db.execute(select(Lesson.slug, Lesson.id).where(Lesson.slug.in_(wanted)))).all())

    items: list[MixItemOut] = []
    for pick in picks:
        c = pick.candidate
        ex = exercises[c.key]
        info = grammar_info[c.lesson_id]
        card_map = {}
        for pattern in competency.exercise_patterns(ex):
            if pattern in info:
                card = {k: v for k, v in info[pattern].items() if k != "lesson_order"}
                card["lesson_id"] = slug_to_id.get(card["lesson_slug"])
                card_map[pattern] = card
        items.append(MixItemOut(lesson_id=c.lesson_id, lesson_title=titles[c.lesson_id], reason=pick.reason, rung=c.rung, exercise=ex, grammar=card_map))  # type: ignore[arg-type]
    by_reason: dict[str, int] = defaultdict(int)
    for item in items:
        by_reason[item.reason] += 1
    return MixOut(lesson_id=lesson_id, items=items, by_reason=dict(by_reason), pool=len(candidates))


# ------------------------------------------------------------------ the report --
def _summary(cards: list[competency.CardState]) -> CompetencySummaryOut:
    return CompetencySummaryOut(**competency.summarize(cards))


async def latest_placement(db: AsyncSession, learner_id) -> PlacementSummaryOut | None:
    row = (
        await db.execute(
            select(PlacementAttempt).where(PlacementAttempt.learner_id == learner_id).order_by(PlacementAttempt.taken_at.desc()).limit(1)
        )
    ).scalar_one_or_none()
    if row is None:
        return None
    s = row.summary or {}
    if s.get("kind") == "adaptive":  # the adaptive check (app.api.routers.onboarding), told the same way
        return PlacementSummaryOut(
            taken_at=row.taken_at,
            score=s.get("right", 0),
            total=s.get("asked", 0),
            known=[],
            unknown=[],
            start_rung=-1,
            start_label=s.get("level_label", ""),
            start_lesson_id=s.get("start_lesson_id"),
        )
    return PlacementSummaryOut(taken_at=row.taken_at, **s)


@router.get("/me/competency", response_model=CompetencyOut)
async def get_my_competency(
    db: Annotated[AsyncSession, Depends(get_db)],
    profile: Annotated[Profile, Depends(get_current_profile)],
):
    """Per topic: how many grammar cards the learner has met, at which rung of the ladder they can
    use them, how many they still remember, which are weak, and what to do next (at most three
    things). Counting only — no prediction of an exam score."""
    now = datetime.now(timezone.utc)
    lessons = (
        await db.execute(select(Lesson.id, Lesson.title, Lesson.practice["kind"].as_string()).order_by(*_LESSON_ORDER))
    ).all()
    topic_rows = (
        await db.execute(
            select(LessonTopic.lesson_id, Topic.id, Topic.name).join(Topic, Topic.id == LessonTopic.topic_id).order_by(Topic.id)
        )
    ).all()
    topic_of: dict[int, str] = {}
    for lid, _tid, name in topic_rows:
        topic_of.setdefault(lid, name)  # the first topic, as the lesson list does

    cards = await competency_db.card_states(db, profile.id, now)
    by_lesson: dict[int, list[competency.CardState]] = defaultdict(list)
    for card in cards.values():
        by_lesson[card.lesson_id].append(card)

    groups: dict[str, list[competency.LessonCards]] = {}
    for lid, title, kind in lessons:  # curriculum order, so topics come in the order they start
        if kind == "review" or not by_lesson.get(lid):
            continue
        groups.setdefault(topic_of.get(lid, "Khác"), []).append(
            competency.LessonCards(lid, title, sorted(by_lesson[lid], key=lambda c: c.id))
        )

    topics: list[CompetencyTopicOut] = []
    for name, group in groups.items():
        every = [c for lc in group for c in lc.cards]
        topics.append(
            CompetencyTopicOut(
                topic=name,
                summary=_summary(every),
                lessons=[CompetencyLessonOut(lesson_id=lc.lesson_id, title=lc.title, summary=_summary(list(lc.cards))) for lc in group],
                weakest=[CompetencyWeakOut(**w) for w in competency.weakest(every)],
                next=[CompetencyNextOut(**r) for r in competency.recommend(group)],
            )
        )
    return CompetencyOut(
        rungs={str(r): label for r, label in competency.RUNG_LABEL.items()},
        topics=topics,
        placement=await latest_placement(db, profile.id),
    )


# ------------------------------------------------------------------ the diagnostic --
def _diagnostic() -> placement.Loaded:
    loaded = placement.diagnostic()
    if loaded is None:
        raise _problem(status.HTTP_503_SERVICE_UNAVAILABLE, "The entry diagnostic is not available", "unavailable")
    return loaded


@router.get("/placement", response_model=PlacementOut)
async def get_placement(
    db: Annotated[AsyncSession, Depends(get_db)],
    profile: Annotated[Profile, Depends(get_current_profile)],
):
    """The entry diagnostic: ~16 short questions on the core patterns of the beginner course, in the
    shapes of the lesson practice. Graded in the browser (like the practice) and sent back whole to
    POST /me/placement. The cards they are about are not named here: that would give the answer."""
    loaded = _diagnostic()
    return PlacementOut(
        title_vi=loaded.title_vi,
        intro_vi=loaded.intro_vi,
        minutes=loaded.minutes,
        items=[PlacementItemOut(id=i.id, rung=i.rung, exercise=i.exercise) for i in loaded.items],
        last=await latest_placement(db, profile.id),
    )


@router.get("/me/placement", response_model=PlacementSummaryOut | None)
async def get_my_placement(
    db: Annotated[AsyncSession, Depends(get_db)],
    profile: Annotated[Profile, Depends(get_current_profile)],
):
    """The latest result of the entry diagnostic, or null when it was never taken."""
    return await latest_placement(db, profile.id)


@router.post("/me/placement", response_model=PlacementSummaryOut, dependencies=[Depends(study_day)])
async def submit_placement(
    body: PlacementSubmit,
    db: Annotated[AsyncSession, Depends(get_db)],
    profile: Annotated[Profile, Depends(get_current_profile)],
):
    """Store one sitting of the diagnostic. What follows from it:

    * every item answered right is one outcome on its rung for its card (competency record);
    * a known card that has no review schedule yet gets its first (right) review, so it comes back
      after a day instead of being forgotten;
    * a wrong or skipped item changes nothing about its card — the diagnostic never takes anything
      away from the learner.
    Items sent twice count once (the last answer); an item the diagnostic does not have is a 422."""
    loaded = _diagnostic()
    given, problems = placement.resolve(
        loaded, [placement.Answer(a.exercise_id, a.question_id, a.correct, a.answer) for a in body.answers]
    )
    if problems:
        raise _problem(status.HTTP_422_UNPROCESSABLE_ENTITY, "; ".join(problems[:3]), "unknown_question")
    if not given:
        raise _problem(status.HTTP_422_UNPROCESSABLE_ENTITY, "No answers", "empty")

    gid_of = {
        (slug, pattern): gid
        for gid, pattern, slug in (
            await db.execute(select(GrammarPoint.id, GrammarPoint.pattern, Lesson.slug).join(Lesson, Lesson.id == GrammarPoint.lesson_id))
        ).all()
    }
    lessons = (await db.execute(select(Lesson.slug, Lesson.id).order_by(*_LESSON_ORDER))).all()
    summary = placement.summarize(
        loaded,
        given,
        gid_of=gid_of,
        lesson_id_of={slug: lid for slug, lid in lessons},
        lesson_pos={slug: pos for pos, (slug, _lid) in enumerate(lessons)},
    )

    by_rung: dict[int, list[int]] = defaultdict(list)
    for gid, rung in placement.evidence(loaded, given, gid_of):
        by_rung[rung].append(gid)
    for rung, gids in by_rung.items():
        await competency_db.record_outcomes(db, profile.id, gids, rung, True)

    known = summary["known_ids"]
    if known:
        have = set(
            (
                await db.execute(
                    select(ItemState.item_id).where(
                        ItemState.learner_id == profile.id,
                        ItemState.item_type == "grammar_point",
                        ItemState.item_id.in_(known),
                    )
                )
            )
            .scalars()
            .all()
        )
        now = datetime.now(timezone.utc)
        for gid in known:
            if gid in have:
                continue
            after = srs.review(None, True, now)
            db.add(
                ItemState(
                    learner_id=profile.id,
                    item_type="grammar_point",
                    item_id=gid,
                    last_seen=now,
                    strength=after.strength,
                    reps=after.reps,
                    lapses=after.lapses,
                    ease=after.ease,
                    interval_days=after.interval_days,
                    due_at=after.due_at,
                    introduced_at=after.introduced_at,
                )
            )

    taken_at = datetime.now(timezone.utc)
    db.add(
        PlacementAttempt(
            learner_id=profile.id,
            taken_at=taken_at,
            answers=[{"exercise_id": a.exercise_id, "correct": a.correct, "answer": a.answer[:200]} for a in given.values()],
            summary=summary,
        )
    )
    await db.commit()
    return PlacementSummaryOut(taken_at=taken_at, **summary)

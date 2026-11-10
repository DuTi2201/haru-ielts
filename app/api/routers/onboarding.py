"""Kiểm tra đầu vào thích ứng: the survey, the questions one at a time, the result and the road.

* POST /me/placement/next      — the answers so far -> the next question, or done
* POST /me/placement/adaptive  — the survey + the answers -> the result, stored; the plan starts there
* GET  /me/placement/adaptive  — the latest result (null before the first)

The estimate is app.services.placement_cat (pure); the road is app.services.roadmap: its numbers are
computed, Gemini only words them (with a plain fallback). Answers are graded here: the questions
sent to the browser carry no answer."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import _problem, get_current_profile
from app.core.config import settings
from app.db import get_db
from app.models import Lesson, PlacementAttempt, Profile
from app.schemas import (
    AdaptiveFinishIn,
    AdaptiveItemOut,
    AdaptiveResultOut,
    AdaptiveStepIn,
    AdaptiveStepOut,
    GapOut,
    RoadLessonOut,
)
from app.services import gemini_client, placement_cat, roadmap
from app.services.billing import catalog as billing_catalog

log = logging.getLogger(__name__)
router = APIRouter(tags=["onboarding"])

KIND = "adaptive"
PROFILE_GOAL = {"talk": "talk", "work": "talk", "topik1": "topik1", "topik4": "topik4", "topik5": "topik5"}


def _answers(body_answers) -> list[placement_cat.Answer]:
    b = placement_cat.bank()
    unknown = [a.ref for a in body_answers if a.ref not in b.by_ref]
    if unknown:
        raise _problem(status.HTTP_422_UNPROCESSABLE_ENTITY, f"Unknown question {unknown[0]}", "unknown_question")
    seen: set[str] = set()
    out = []
    for a in body_answers:
        if a.ref in seen:
            continue
        seen.add(a.ref)
        out.append(placement_cat.Answer(a.ref, a.choice))
    return out


def _progress(p: list[float], asked: int) -> float:
    """How settled the estimate is, for the light bar: the share of the probability near the
    median, stretched so the bar grows with each answer and is full when the test stops."""
    m = placement_cat.median(p)
    near = sum(p[max(0, m - placement_cat.WINDOW): m + placement_cat.WINDOW + 1])
    by_count = asked / placement_cat.MAX_ITEMS
    return round(min(0.95, max(by_count, near / placement_cat.TIGHT * 0.9)), 2)


@router.post("/me/placement/next", response_model=AdaptiveStepOut)
async def next_item(body: AdaptiveStepIn, _: Annotated[Profile, Depends(get_current_profile)]):
    if body.self_level == "new":
        return AdaptiveStepOut(done=True, asked=0, progress=1.0)
    b = placement_cat.bank()
    answers = _answers(body.answers)
    p = placement_cat.posterior(b, answers, body.self_level)
    last = None
    if answers:
        q = b.by_ref[answers[-1].ref]
        last = placement_cat.outcome_of(q, answers[-1].choice) == "right"
    if placement_cat.done(p, len(answers), placement_cat.skipped_at_start(b, answers)):
        return AdaptiveStepOut(done=True, asked=len(answers), progress=1.0, last_right=last)
    q = placement_cat.next_question(b, answers, p)
    return AdaptiveStepOut(
        done=False,
        item=AdaptiveItemOut(ref=q.ref, exercise=q.exercise),
        asked=len(answers),
        progress=_progress(p, len(answers)),
        last_right=last,
    )


async def _course(db: AsyncSession) -> list[roadmap.CourseLesson]:
    ids = dict((await db.execute(select(Lesson.slug, Lesson.id).where(Lesson.slug.isnot(None)))).all())
    return [
        roadmap.CourseLesson(ids[c["slug"]], c["sort_order"], c["slug"], c["title"], c["kind"], c["vocab"], c["grammar"], c["questions"])
        for c in placement_cat.course()
        if c["slug"] in ids
    ]


async def _words(f: dict) -> dict:
    if not settings.GEMINI_API_KEY:
        return roadmap.fallback(f)
    try:
        out = await run_in_threadpool(
            gemini_client.generate_structured,
            model=settings.GEMINI_MODEL_STUDY,
            prompt=roadmap.prompt(f),
            response_schema=roadmap.SCHEMA,
            prompt_version="roadmap-v1",
        )
        return roadmap.parse(out["text"]) or roadmap.fallback(f)
    except Exception as exc:  # the road is there either way, in plain words
        log.warning("[onboarding] roadmap words failed: %s", exc.__class__.__name__)
        return roadmap.fallback(f)


@router.post("/me/placement/adaptive", response_model=AdaptiveResultOut)
async def finish(
    body: AdaptiveFinishIn,
    db: Annotated[AsyncSession, Depends(get_db)],
    profile: Annotated[Profile, Depends(get_current_profile)],
):
    """The result of the survey and the questions. The learner's goal and daily minutes are kept on
    the profile; the start lesson moves the daily plan there (content.get_my_plan)."""
    s = body.survey
    b = placement_cat.bank()
    tested = s.self_level != "new"
    answers = _answers(body.answers) if tested else []
    res = placement_cat.conclude(b, answers, s.self_level if tested else None) if tested else None
    course = await _course(db)
    by_slug = {c.slug: c for c in course}

    if res is None:  # new: the first lesson of the course, no test
        first = min(course, key=lambda c: c.sort_order) if course else None
        start_sort, start, label, advice, gaps_raw, restart = (first.sort_order if first else 1), first, placement_cat.NEW_LABEL, "start_here", (), None
    else:
        start = by_slug.get(res.start.slug) if res.start else None
        restart = by_slug.get(res.restart.slug) if res.restart else None
        go = restart or start
        start_sort = go.sort_order if go else max((c.sort_order for c in course), default=1) + 1
        label, advice, gaps_raw = res.level_label, res.advice, res.gaps

    gaps = [
        {"lesson_id": by_slug[r.slug].id if r.slug in by_slug else None, "title": r.title, "patterns": list(ps)}
        for r, ps in gaps_raw
    ]
    now = datetime.now(timezone.utc)
    p = roadmap.plan(course, start_sort, s.purpose, s.daily_minutes, profile.exam_date, now, billing_catalog.FREE_LESSON_MAX)
    f = roadmap.facts(
        label,
        (restart or start).title if (restart or start) else None,
        advice,
        restart.title if restart else None,
        gaps,
        p,
        s.purpose,
        res.asked if res else 0,
        res.right if res else 0,
    )
    words = await _words(f) if tested else roadmap.fallback(f)

    profile.goal = PROFILE_GOAL[s.purpose]
    profile.daily_minutes = s.daily_minutes
    go = restart or start
    summary = {
        "kind": KIND,
        "tested": tested,
        "survey": s.model_dump(),
        "level_label": label,
        "asked": res.asked if res else 0,
        "right": res.right if res else 0,
        "frontier": res.frontier if res else 0,
        "range": [res.low, res.high] if res else [0, 0],
        "start_sort": start_sort,
        "start_lesson_id": go.id if go else None,
        "start_title": go.title if go else None,
        "advice": advice,
        "gaps": gaps,
        "plan": {
            "lessons": p.lessons, "minutes": p.minutes, "weeks": p.weeks, "daily_minutes": p.daily_minutes,
            "exam_weeks": p.exam_weeks, "need_daily": p.need_daily, "first": p.first,
        },
        "words": words,
    }
    row = PlacementAttempt(
        learner_id=profile.id,
        taken_at=now,
        answers=[{"ref": a.ref, "choice": a.choice} for a in answers],
        summary=summary,
    )
    db.add(row)
    await db.commit()
    return result_out(now, summary)


def result_out(taken_at: datetime, s: dict) -> AdaptiveResultOut:
    plan = s["plan"]
    survey = s["survey"]
    return AdaptiveResultOut(
        taken_at=taken_at,
        tested=s["tested"],
        level_label=s["level_label"],
        asked=s["asked"],
        right=s["right"],
        start_lesson_id=s["start_lesson_id"],
        start_title=s["start_title"],
        advice=s["advice"],
        gaps=[GapOut(**g) for g in s["gaps"]],
        purpose=survey["purpose"],
        goal_label=roadmap.GOAL_LABEL.get(survey["purpose"], ""),
        lessons_to_goal=plan["lessons"],
        minutes_to_goal=plan["minutes"],
        weeks=plan["weeks"],
        daily_minutes=plan["daily_minutes"],
        exam_weeks=plan["exam_weeks"],
        need_daily=plan["need_daily"],
        next_lessons=[RoadLessonOut(**l) for l in plan["first"]],
        headline=s["words"]["headline"],
        tips=s["words"]["tips"],
        words_by=s["words"]["by"],
    )


async def latest_adaptive(db: AsyncSession, learner_id) -> PlacementAttempt | None:
    rows = (
        await db.execute(
            select(PlacementAttempt)
            .where(PlacementAttempt.learner_id == learner_id)
            .order_by(PlacementAttempt.taken_at.desc())
            .limit(5)
        )
    ).scalars().all()
    return next((r for r in rows if (r.summary or {}).get("kind") == KIND), None)


@router.get("/me/placement/adaptive", response_model=AdaptiveResultOut | None)
async def latest(
    db: Annotated[AsyncSession, Depends(get_db)],
    profile: Annotated[Profile, Depends(get_current_profile)],
):
    row = await latest_adaptive(db, profile.id)
    return result_out(row.taken_at, row.summary) if row is not None else None

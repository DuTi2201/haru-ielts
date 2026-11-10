"""The database side of app.services.competency: writing an outcome, loading a learner's cards.

Kept apart from the pure rules so the routers (content answers, the daily review, the mixed review
and the competency report) share one way to read and write the same two tables."""
from __future__ import annotations

import uuid
from collections.abc import Iterable
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import GrammarCompetency, GrammarPoint, ItemState
from app.services import competency, srs
from app.services.grammar_tier import effective_use_level


def schedule_of(state: ItemState) -> srs.Schedule:
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


async def record_outcomes(
    db: AsyncSession, learner_id: uuid.UUID, grammar_ids: Iterable[int], rung: int, correct: bool
) -> None:
    """One more outcome on `rung` for each card (nothing is committed: the caller does)."""
    ids = sorted(set(grammar_ids))
    if not ids:
        return
    rows = {
        row.grammar_id: row
        for row in (
            await db.execute(
                select(GrammarCompetency).where(
                    GrammarCompetency.learner_id == learner_id, GrammarCompetency.grammar_id.in_(ids)
                )
            )
        )
        .scalars()
        .all()
    }
    now = datetime.now(timezone.utc)
    for gid in ids:
        row = rows.get(gid)
        if row is None:
            db.add(GrammarCompetency(learner_id=learner_id, grammar_id=gid, history=competency.record(None, rung, correct), updated_at=now))
        else:
            row.history = competency.record(row.history, rung, correct)  # a new dict: the change is seen
            row.updated_at = now


async def card_states(
    db: AsyncSession, learner_id: uuid.UUID, now: datetime, lesson_ids: Iterable[int] | None = None
) -> dict[int, competency.CardState]:
    """Every grammar card of the given lessons (all lessons when None) as this learner stands
    with it: what they have done with it (competency) and how well it is remembered (ItemState)."""
    query = select(
        GrammarPoint.id,
        GrammarPoint.pattern,
        GrammarPoint.lesson_id,
        GrammarPoint.exam,
        GrammarPoint.use_level,
        GrammarPoint.usage_context_vi,
    ).where(GrammarPoint.lesson_id.isnot(None))
    if lesson_ids is not None:
        query = query.where(GrammarPoint.lesson_id.in_(list(lesson_ids)))
    rows = (await db.execute(query)).all()
    if not rows:
        return {}
    ids = [r[0] for r in rows]
    states = {
        s.item_id: s
        for s in (
            await db.execute(
                select(ItemState).where(
                    ItemState.learner_id == learner_id,
                    ItemState.item_type == "grammar_point",
                    ItemState.item_id.in_(ids),
                )
            )
        )
        .scalars()
        .all()
    }
    history = {
        c.grammar_id: c.history or {}
        for c in (
            await db.execute(
                select(GrammarCompetency).where(
                    GrammarCompetency.learner_id == learner_id, GrammarCompetency.grammar_id.in_(ids)
                )
            )
        )
        .scalars()
        .all()
    }
    out: dict[int, competency.CardState] = {}
    for gid, pattern, lesson_id, exam, use_level, usage in rows:
        state = states.get(gid)
        sched = schedule_of(state) if state is not None else None
        due = bool(sched and srs.is_due(sched, now))
        out[gid] = competency.CardState(
            id=gid,
            pattern=pattern,
            lesson_id=lesson_id,
            use_level=effective_use_level(usage, use_level),
            difficulty=int(exam[-1]) if exam and exam[-1].isdigit() else 3,
            history=history.get(gid, {}),
            in_srs=state is not None,
            strength=state.strength if state is not None else 0.0,
            due=due,
            leech=bool(sched and srs.is_leech(sched)),
            shaky=bool(sched and srs.is_shaky(sched)),
            overdue_since=state.due_at if (state is not None and due) else None,
        )
    return out

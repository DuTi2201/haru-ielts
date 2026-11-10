"""The daily reading and dialogue.

* GET  /me/daily-reading                      — today's dialogue and reading, drawn from what the learner has studied
* POST /me/daily-reading/{passage_id}/finish  — grade the comprehension questions of one of them

Each text (app/seed/passages) is built on named grammar cards and key words. It opens when the
learner has met all of its cards; among the open ones the draw favours what they are about to
forget (app.services.daily_reading). The text is voiced line by line (a dialogue, two Chirp voices)
or as one clip (a reading) through POST /audio/text — the answers to the questions never leave the
server before the learner has submitted theirs.
"""
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import _problem, get_current_profile, study_day
from app.db import get_db
from app.models import ItemState, Profile
from app.schemas import DailyFinishIn, DailyFinishOut, DailyReadingOut
from app.services import daily_reading_db as store

router = APIRouter(tags=["daily-reading"])


async def _states(db: AsyncSession, profile: Profile) -> list[ItemState]:
    return list((await db.execute(select(ItemState).where(ItemState.learner_id == profile.id))).scalars().all())


@router.get("/me/daily-reading", response_model=DailyReadingOut)
async def get_daily_reading(
    db: Annotated[AsyncSession, Depends(get_db)],
    profile: Annotated[Profile, Depends(get_current_profile)],
):
    """Today's two texts (a dialogue to listen to and a reading), or none while the learner has not
    met the grammar of any text yet. The same two all day; a new draw tomorrow."""
    now = datetime.now(timezone.utc)
    cards = store.cards_of(await _states(db, profile), now)
    ctx = await store.load_context(db)
    today = await store.sitting(db, profile.id, cards, ctx, now, persist=True)
    return store.reading_out(today, [store.passage_out(pick, ctx, cards) for pick in today.picks])


@router.post("/me/daily-reading/{passage_id}/finish", response_model=DailyFinishOut, dependencies=[Depends(study_day)])
async def finish_daily_reading(
    passage_id: str,
    body: DailyFinishIn,
    db: Annotated[AsyncSession, Depends(get_db)],
    profile: Annotated[Profile, Depends(get_current_profile)],
):
    """Grade the answers (one per question, null = blank) and explain each one. Only one of today's
    texts can be finished. This reading does not change the review schedule."""
    try:
        return await store.finish(db, profile.id, passage_id, body.answers, datetime.now(timezone.utc))
    except store.NotToday:
        raise _problem(404, "That text is not one of today's readings", "not_found")
    except ValueError as exc:
        raise _problem(422, str(exc), "invalid_answers")

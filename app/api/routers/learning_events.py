"""What learners do inside a lesson, for decisions made on data (analytics.learning_event).

The app sends a few kinds of event, in small batches:

- ``session_start`` / ``session_complete``: a ~15-minute sitting of a lesson was opened / finished
  (payload: lesson_id, session, of; value = minutes it took, on complete)
- ``step_abandon``: the learner left a sitting part-way (payload: lesson_id, session, step;
  value = seconds spent in that step)
- ``audio_seek``: the lecture was moved back or forward (payload: lesson_id, from_s, to_s,
  chapter; value = seconds moved, negative = back)
- ``audio_rate``: the lecture speed was changed (value = the new rate)
- ``first_try``: a practice question answered for the first time (payload: lesson_id,
  question_id; value 1 = right, 0 = wrong)
- ``lecture_complete``: a sitting's lecture was heard to its last slide (payload: lesson_id,
  session; value = seconds of the recording)
- ``lecture_replay``: something on a slide was tapped to hear it again (payload: lesson_id,
  session, step = the slide's kind)
- ``say_score``: a read-aloud sentence was scored (payload: lesson_id, session, step = which
  sentence; value = the accuracy score, 0-100)

Nothing typed by the learner is kept: payloads carry ids and numbers only. Admins read the
totals per lesson at GET /admin/learning-events/summary.
"""
from datetime import datetime, timedelta, timezone
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_profile, require_role
from app.db import get_db
from app.models import LearningEvent, Profile

router = APIRouter(tags=["learning-events"])

EventType = Literal["session_start", "session_complete", "step_abandon", "audio_seek", "audio_rate", "first_try", "lecture_complete", "lecture_replay", "say_score"]  # "chat_done" is filed by /me/chats
SKILL_OF: dict[str, str] = {
    "session_start": "lesson",
    "session_complete": "lesson",
    "step_abandon": "lesson",
    "audio_seek": "lecture",
    "audio_rate": "lecture",
    "first_try": "practice",
    "lecture_complete": "lecture",
    "lecture_replay": "lecture",
    "say_score": "speaking",
}
# payload keys kept, and how long a text value may be (ids only: nothing the learner wrote)
PAYLOAD_KEYS = {"lesson_id", "session", "of", "step", "from_s", "to_s", "chapter", "question_id", "mode"}
MAX_TEXT = 64
MAX_PER_DAY = 2000


class EventIn(BaseModel):
    type: EventType
    value: float = 0.0
    payload: dict[str, Any] = Field(default_factory=dict)
    at: datetime | None = None

    @field_validator("payload")
    @classmethod
    def _ids_only(cls, v: dict[str, Any]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for k, val in v.items():
            if k not in PAYLOAD_KEYS:
                continue
            if isinstance(val, bool) or val is None:
                continue
            if isinstance(val, (int, float)):
                out[k] = val
            elif isinstance(val, str):
                out[k] = val[:MAX_TEXT]
        return out


class EventBatchIn(BaseModel):
    events: list[EventIn] = Field(min_length=1, max_length=50)


@router.post("/me/events", status_code=status.HTTP_202_ACCEPTED)
async def record_events(
    body: EventBatchIn,
    db: Annotated[AsyncSession, Depends(get_db)],
    profile: Annotated[Profile, Depends(get_current_profile)],
) -> dict[str, int]:
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=1)
    sent_today = (
        await db.execute(
            select(func.count())
            .select_from(LearningEvent)
            .where(LearningEvent.learner_id == profile.id, LearningEvent.occurred_at >= since)
        )
    ).scalar_one()
    room = max(0, MAX_PER_DAY - sent_today)
    kept = 0
    for e in body.events[:room]:
        at = e.at if e.at is not None else now
        if at.tzinfo is None:
            at = at.replace(tzinfo=timezone.utc)
        # a device clock far off is not trusted: the event is filed at arrival
        if abs((now - at).total_seconds()) > 7 * 86400:
            at = now
        db.add(
            LearningEvent(
                learner_id=profile.id,
                occurred_at=at,
                event_type=e.type,
                skill=SKILL_OF[e.type],
                value=float(e.value),
                payload=e.payload,
            )
        )
        kept += 1
    await db.commit()
    return {"kept": kept}


class LessonSummaryRow(BaseModel):
    lesson_id: int
    learners: int
    sessions_started: int
    sessions_completed: int
    completion_pct: float | None
    median_minutes: float | None
    abandons_by_step: dict[str, int]
    first_try_answers: int
    first_try_correct_pct: float | None
    lecture_seeks_back: int


class EventSummaryOut(BaseModel):
    days: int
    lessons: list[LessonSummaryRow]


@router.get("/admin/learning-events/summary", response_model=EventSummaryOut)
async def summary(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[Profile, Depends(require_role("admin"))],
    days: Annotated[int, Query(ge=1, le=180)] = 30,
) -> EventSummaryOut:
    since = datetime.now(timezone.utc) - timedelta(days=days)
    lesson = LearningEvent.payload["lesson_id"].as_integer()
    rows = (
        await db.execute(
            select(LearningEvent.event_type, lesson, LearningEvent.learner_id, LearningEvent.value, LearningEvent.payload)
            .where(LearningEvent.occurred_at >= since, lesson.is_not(None))
        )
    ).all()
    by: dict[int, dict[str, Any]] = {}
    for kind, lid, learner, value, payload in rows:
        s = by.setdefault(
            int(lid),
            {"learners": set(), "start": 0, "done": 0, "minutes": [], "abandon": {}, "ft": 0, "ft_ok": 0, "back": 0},
        )
        s["learners"].add(learner)
        if kind == "session_start":
            s["start"] += 1
        elif kind == "session_complete":
            s["done"] += 1
            if value > 0:
                s["minutes"].append(value)
        elif kind == "step_abandon":
            step = str((payload or {}).get("step") or "?")
            s["abandon"][step] = s["abandon"].get(step, 0) + 1
        elif kind == "first_try":
            s["ft"] += 1
            s["ft_ok"] += 1 if value >= 1 else 0
        elif kind == "audio_seek" and value < 0:
            s["back"] += 1

    def median(xs: list[float]) -> float | None:
        if not xs:
            return None
        xs = sorted(xs)
        m = len(xs) // 2
        return round(xs[m] if len(xs) % 2 else (xs[m - 1] + xs[m]) / 2, 1)

    out = [
        LessonSummaryRow(
            lesson_id=lid,
            learners=len(s["learners"]),
            sessions_started=s["start"],
            sessions_completed=s["done"],
            completion_pct=round(100 * s["done"] / s["start"], 1) if s["start"] else None,
            median_minutes=median(s["minutes"]),
            abandons_by_step=s["abandon"],
            first_try_answers=s["ft"],
            first_try_correct_pct=round(100 * s["ft_ok"] / s["ft"], 1) if s["ft"] else None,
            lecture_seeks_back=s["back"],
        )
        for lid, s in sorted(by.items())
    ]
    return EventSummaryOut(days=days, lessons=out)

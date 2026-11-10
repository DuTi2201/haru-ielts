"""«Nhờ Haru chấm»: the AI check of a paragraph the learner wrote for a lesson's `write_essay`
item (app/services/essay_check.py). The text is kept with its result, so the learner sees the
last check again when they come back to the lesson."""
import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import _problem, ensure_daily_cap, ensure_lesson_open, get_current_profile, study_day
from app.core.config import settings
from app.db import get_db
from app.models import Job, Lesson, LessonEssayCheck, Profile
from app.schemas import EssayCheckOut, EssayCheckRequest, EssayResultOut
from app.services import essay_check
from app.services.billing import access as billing_access
from app.services.billing import catalog as billing_catalog
from app.workers.tasks import check_lesson_essay

router = APIRouter(tags=["lesson-essays"])

JOB_TYPE = "check_lesson_essay"
STALE_AFTER = timedelta(minutes=10)


def _out(row: LessonEssayCheck) -> EssayCheckOut:
    return EssayCheckOut(
        id=row.id,
        lesson_id=row.lesson_id,
        exercise_id=row.exercise_id,
        status=row.status,  # type: ignore[arg-type]
        job_id=row.job_id,
        text=row.text,
        result=EssayResultOut(**row.result) if row.status == "ready" and row.result else None,
        created_at=row.created_at,
    )


def _expire_if_stale(row: LessonEssayCheck, now: datetime) -> bool:
    """A check whose worker died must not keep the learner waiting forever."""
    if row.status == "pending" and now - (row.updated_at or row.created_at) > STALE_AFTER:
        row.status = "failed"
        return True
    return False


async def _lesson_and_item(db: AsyncSession, profile: Profile, lesson_id: int, exercise_id: str) -> tuple[Lesson, dict]:
    lesson = await db.get(Lesson, lesson_id)
    if lesson is None:
        raise _problem(status.HTTP_404_NOT_FOUND, "Lesson not found", "not_found")
    held = await billing_access.load_access(db, profile)
    if held.enforced and not billing_catalog.is_free(lesson.sort_order):
        await ensure_lesson_open(db, profile, lesson)
    item = essay_check.find_item(lesson.practice, exercise_id)
    if item is None:
        raise _problem(status.HTTP_404_NOT_FOUND, "Bài này không có phần viết đoạn để chấm.", "not_found")
    return lesson, item


@router.post(
    "/lessons/{lesson_id}/essays/{exercise_id}/checks",
    response_model=EssayCheckOut,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(study_day)],
)
async def start_essay_check(
    lesson_id: int,
    exercise_id: str,
    body: EssayCheckRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    profile: Annotated[Profile, Depends(get_current_profile)],
):
    """Send a paragraph to be checked. The same text already checked (or being checked) is not
    sent to the model again: its check is returned."""
    lesson, _item = await _lesson_and_item(db, profile, lesson_id, exercise_id)
    text = body.text.strip()
    if len(text) > essay_check.MAX_TEXT_CHARS:
        raise _problem(status.HTTP_422_UNPROCESSABLE_ENTITY, f"Bài dài quá {essay_check.MAX_TEXT_CHARS} ký tự.", "text_too_long")
    if essay_check.count_words(text) < essay_check.MIN_WORDS and len(essay_check._HANGUL_RE.findall(text)) < essay_check.MIN_HANGUL:
        raise _problem(status.HTTP_422_UNPROCESSABLE_ENTITY, "Hãy viết vài câu tiếng Anh rồi mới gửi chấm.", "too_short")

    now = datetime.now(timezone.utc)
    last = (
        await db.execute(
            select(LessonEssayCheck)
            .where(LessonEssayCheck.learner_id == profile.id, LessonEssayCheck.lesson_id == lesson.id, LessonEssayCheck.exercise_id == exercise_id)
            .order_by(LessonEssayCheck.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if last is not None:
        if _expire_if_stale(last, now):
            db.add(last)
        if last.text == text and last.status in ("pending", "ready"):
            await db.commit()
            return _out(last)

    await ensure_daily_cap(db, profile.id, JOB_TYPE, settings.LESSON_ESSAY_CHECKS_PER_DAY, "bài viết")
    row = LessonEssayCheck(learner_id=profile.id, lesson_id=lesson.id, exercise_id=exercise_id, text=text, status="pending")
    db.add(row)
    job = Job(type=JOB_TYPE, owner_id=profile.id, status="queued")
    db.add(job)
    await db.flush()
    row.job_id = job.id
    await db.commit()
    await db.refresh(row)
    try:
        check_lesson_essay.delay(str(job.id), str(row.id))
    except Exception:  # noqa: BLE001 — the queue is down: the check fails, the text is kept
        row.status = "failed"
        db.add(row)
        await db.commit()
        await db.refresh(row)
    return _out(row)


@router.get("/lessons/{lesson_id}/essays/{exercise_id}/checks/latest", response_model=EssayCheckOut | None)
async def latest_essay_check(
    lesson_id: int,
    exercise_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    profile: Annotated[Profile, Depends(get_current_profile)],
):
    row = (
        await db.execute(
            select(LessonEssayCheck)
            .where(LessonEssayCheck.learner_id == profile.id, LessonEssayCheck.lesson_id == lesson_id, LessonEssayCheck.exercise_id == exercise_id)
            .order_by(LessonEssayCheck.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if row is None:
        return None
    if _expire_if_stale(row, datetime.now(timezone.utc)):
        db.add(row)
        await db.commit()
        await db.refresh(row)
    return _out(row)


@router.get("/essay-checks/{check_id}", response_model=EssayCheckOut)
async def get_essay_check(
    check_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    profile: Annotated[Profile, Depends(get_current_profile)],
):
    row = await db.get(LessonEssayCheck, check_id)
    if row is None or row.learner_id != profile.id:
        raise _problem(status.HTTP_404_NOT_FOUND, "Check not found", "not_found")
    if _expire_if_stale(row, datetime.now(timezone.utc)):
        db.add(row)
        await db.commit()
        await db.refresh(row)
    return _out(row)

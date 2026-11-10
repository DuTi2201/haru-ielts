"""Practice on real TOPIK II papers ("Luyện đề thi thật").

* GET  /me/real-exam                          — where the learner stands, by cụm and dạng; today's suggestion
* GET  /me/real-exam/types/{code}             — one question type: its guide, its questions, what it keeps asking
* GET  /me/real-exam/exams/{exam}             — a whole paper question by question (free browsing)
* GET  /me/real-exam/lessons/{lesson_id}      — the real questions a lesson offers ("Thử sức TOPIK II"), each with a primer
* POST /me/real-exam/sets                     — a sitting of a few questions chosen for this learner and scope
* GET  /me/real-exam/sets/{id}                — the sitting again (to pick it up); /answers for those already answered
* POST /me/real-exam/sets/{id}/hint           — open hint 1, 2 or 3 of a question (what to look for / in Vietnamese / cross one out)
* POST /me/real-exam/sets/{id}/answer         — answer; the reply is the whole explanation
* POST /me/real-exam/attempts/{id}/self-check — the learner judges a written answer the program cannot
* GET  /me/real-exam/sets/{id}/summary        — "Bạn thu được gì"; POST …/finish closes the sitting
* GET  /me/real-exam/assets/{name}            — a picture of a question, behind login

The papers are for the owner's own study: every route needs a login and the answer of a question never
leaves the server before it has been answered. Listening questions are voiced by the client through POST
/audio/text, line by line, like the daily dialogue."""
import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import _problem, get_current_profile, require_private_source, study_day
from app.db import get_db
from app.models import Profile
from app.schemas import (
    RxAnswerIn,
    RxAnswerOut,
    RxExamDetailOut,
    RxHintIn,
    RxHintOut,
    RxLessonOut,
    RxOverviewOut,
    RxScopeIn,
    RxSelfCheckIn,
    RxSelfCheckOut,
    RxSetOut,
    RxSummaryOut,
    RxTypeDetailOut,
)
from app.services import real_exam as rx
from app.services import real_exam_db as store

router = APIRouter(prefix="/me/real-exam", tags=["real-exam"], dependencies=[Depends(require_private_source)])

DbDep = Annotated[AsyncSession, Depends(get_db)]
ProfileDep = Annotated[Profile, Depends(get_current_profile)]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _not_found(what: str):
    return _problem(404, "Không tìm thấy", "not_found", what)


@router.get("", response_model=RxOverviewOut)
async def get_overview(db: DbDep, profile: ProfileDep):
    return await store.overview(db, profile, _now())


@router.get("/types/{code}", response_model=RxTypeDetailOut)
async def get_type(code: str, db: DbDep, profile: ProfileDep):
    try:
        return await store.type_detail(db, profile, code, _now())
    except store.NotFound as exc:
        raise _not_found(str(exc)) from exc


@router.get("/exams/{exam}", response_model=RxExamDetailOut)
async def get_exam(exam: str, db: DbDep, profile: ProfileDep):
    try:
        return await store.exam_detail(db, profile, exam, _now())
    except store.NotFound as exc:
        raise _not_found(str(exc)) from exc


@router.get("/lessons/{lesson_id}", response_model=RxLessonOut)
async def get_lesson_picks(lesson_id: int, db: DbDep, profile: ProfileDep):
    try:
        return await store.lesson_picks(db, profile, lesson_id, _now())
    except store.NotFound as exc:
        raise _not_found(str(exc)) from exc


@router.post("/sets", response_model=RxSetOut, status_code=201)
async def create_set(body: RxScopeIn, db: DbDep, profile: ProfileDep):
    """A sitting for this scope (a type, a cụm, a section of a paper, chosen questions, or nothing —
    then the app chooses). 409 `nothing_to_practice` when every question in the scope is resting."""
    now = _now()
    try:
        row = await store.make_set(db, profile, body, now)
    except store.NotFound as exc:
        raise _not_found(str(exc)) from exc
    except store.NothingToPractice as exc:
        raise _problem(
            409,
            "Các câu trong phạm vi này đang nghỉ",
            "nothing_to_practice",
            "Bạn đã làm hết các câu có thể làm lúc này. Câu sai quay lại sau 12 giờ, câu đúng nhờ gợi ý sau 3 ngày, "
            "câu đã vững sau 7 ngày — hoặc chọn một dạng khác.",
        ) from exc
    return await store.set_out(db, profile, row, now)


async def _own_set(db: AsyncSession, profile: Profile, set_id: uuid.UUID):
    try:
        return await store.get_set(db, profile, set_id)
    except store.NotFound as exc:
        raise _not_found("sitting") from exc


@router.get("/sets/{set_id}", response_model=RxSetOut)
async def get_set(set_id: uuid.UUID, db: DbDep, profile: ProfileDep):
    row = await _own_set(db, profile, set_id)
    return await store.set_out(db, profile, row, _now())


@router.get("/sets/{set_id}/answers", response_model=list[RxAnswerOut])
async def get_set_answers(set_id: uuid.UUID, db: DbDep, profile: ProfileDep):
    row = await _own_set(db, profile, set_id)
    return await store.set_answers(db, profile, row, _now())


@router.post("/sets/{set_id}/hint", response_model=RxHintOut)
async def open_hint(set_id: uuid.UUID, body: RxHintIn, db: DbDep, profile: ProfileDep):
    row = await _own_set(db, profile, set_id)
    try:
        return await store.open_hint(db, profile, row, body.qid, body.level)
    except store.NotFound as exc:
        raise _not_found(str(exc)) from exc
    except store.Conflict as exc:
        raise _problem(409, str(exc), "already_answered") from exc


@router.post("/sets/{set_id}/answer", response_model=RxAnswerOut, dependencies=[Depends(study_day)])
async def answer(set_id: uuid.UUID, body: RxAnswerIn, db: DbDep, profile: ProfileDep):
    row = await _own_set(db, profile, set_id)
    try:
        return await store.answer(db, profile, row, body, _now())
    except store.NotFound as exc:
        raise _not_found(str(exc)) from exc


@router.post("/attempts/{attempt_id}/self-check", response_model=RxSelfCheckOut)
async def self_check(attempt_id: uuid.UUID, body: RxSelfCheckIn, db: DbDep, profile: ProfileDep):
    try:
        return await store.self_check(db, profile, attempt_id, body, _now())
    except store.NotFound as exc:
        raise _not_found("attempt") from exc
    except store.Conflict as exc:
        raise _problem(409, str(exc), "cannot_check") from exc


@router.get("/sets/{set_id}/summary", response_model=RxSummaryOut)
async def get_summary(set_id: uuid.UUID, db: DbDep, profile: ProfileDep):
    row = await _own_set(db, profile, set_id)
    return await store.summary(db, profile, row, _now())


@router.post("/sets/{set_id}/finish", response_model=RxSummaryOut, dependencies=[Depends(study_day)])
async def finish(set_id: uuid.UUID, db: DbDep, profile: ProfileDep):
    row = await _own_set(db, profile, set_id)
    now = _now()
    await store.finish_set(db, row, now)
    return await store.summary(db, profile, row, now)


@router.get("/assets/{name}")
async def get_asset(name: str, profile: ProfileDep):
    """A picture a question is printed with. Only the files the papers name are served."""
    known = {i.img for i in rx.load().items.values() if i.img}
    if name not in known:
        raise _not_found(name)
    return Response(
        content=(rx.IMG_DIR / name).read_bytes(),
        media_type="image/png",
        headers={"Cache-Control": "private, max-age=86400"},
    )

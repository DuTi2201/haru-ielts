"""Looking back at the talks with Haru (app.services.talk_history).

GET    /me/conversations                    finished sessions, newest first (?limit, ?before)
GET    /me/conversations/insights           the trend: pronunciation, band, recurring mistakes
GET    /me/conversations/notes              Sổ trò chuyện: words / sentences kept from talks
PATCH  /me/conversations/notes/{id}         tick one off (or back on)
DELETE /me/conversations/notes/{id}
GET    /me/conversations/{id}               one session: report, pronunciation, transcript
POST   /me/conversations/{id}/save          "Đưa vào ôn tập": the session's suggested words and
                                            corrected sentences go to the notebook; words that are vocabulary cards
                                            (same headword, a lesson card first) are linked and go due in the review queue.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import _problem, get_current_profile
from app.db import get_db
from app.models import ConversationSession, Lesson, Profile, TalkNote
from app.schemas import (
    ConversationReportOut,
    PronunciationOut,
    TalkInsightsOut,
    TalkNoteOut,
    TalkNoteUpdate,
    TalkSaveOut,
    TalkSessionDetailOut,
    TalkSessionRowOut,
)
from app.services import talk_history, talk_notes_db, talk_profile

router = APIRouter(prefix="/me/conversations", tags=["conversation"])


async def _lesson_titles(db: AsyncSession, ids: set[int]) -> dict[int, str]:
    if not ids:
        return {}
    return {i: t for i, t in (await db.execute(select(Lesson.id, Lesson.title).where(Lesson.id.in_(ids)))).all()}


def _note_out(n: TalkNote) -> TalkNoteOut:
    return TalkNoteOut(
        id=n.id,
        kind=n.kind,
        ko=n.ko,
        vi=n.vi or "",
        in_review=n.vocab_item_id is not None,
        done=n.done_at is not None,
        created_at=n.created_at or datetime.now(timezone.utc),
    )


async def _notes(db: AsyncSession, learner_id: uuid.UUID) -> list[TalkNote]:
    return list(
        (
            await db.execute(
                select(TalkNote)
                .where(TalkNote.learner_id == learner_id)
                .order_by(TalkNote.done_at.is_not(None), TalkNote.created_at.desc())
                .limit(200)
            )
        )
        .scalars()
        .all()
    )


async def _own_session(db: AsyncSession, session_id: uuid.UUID, profile: Profile) -> ConversationSession:
    row = await db.get(ConversationSession, session_id)
    if row is None or row.learner_id != profile.id or getattr(row, "kind", "talk") != "talk":
        raise _problem(status.HTTP_404_NOT_FOUND, "Không tìm thấy buổi trò chuyện này.", "not_found")
    return row


@router.get("", response_model=list[TalkSessionRowOut])
async def list_sessions(
    db: Annotated[AsyncSession, Depends(get_db)],
    profile: Annotated[Profile, Depends(get_current_profile)],
    limit: Annotated[int, Query(ge=1, le=100)] = 30,
    before: datetime | None = None,
):
    q = select(ConversationSession).where(
        ConversationSession.learner_id == profile.id,
        ConversationSession.ended_at.is_not(None),
        ConversationSession.kind == "talk",
    )
    if before is not None:
        q = q.where(ConversationSession.started_at < before)
    rows = (await db.execute(q.order_by(ConversationSession.started_at.desc()).limit(limit))).scalars().all()
    titles = await _lesson_titles(db, {r.lesson_id for r in rows if r.lesson_id})
    return [talk_history.summary_row(r, titles.get(r.lesson_id)) for r in rows]


@router.get("/insights", response_model=TalkInsightsOut)
async def get_insights(
    db: Annotated[AsyncSession, Depends(get_db)],
    profile: Annotated[Profile, Depends(get_current_profile)],
):
    rows = (
        await db.execute(
            select(ConversationSession)
            .where(
                ConversationSession.learner_id == profile.id,
                ConversationSession.ended_at.is_not(None),
                ConversationSession.kind == "talk",
            )
            .order_by(ConversationSession.started_at.desc())
            .limit(30)
        )
    ).scalars().all()
    return talk_history.insights(list(rows))


@router.get("/notes", response_model=list[TalkNoteOut])
async def list_notes(
    db: Annotated[AsyncSession, Depends(get_db)],
    profile: Annotated[Profile, Depends(get_current_profile)],
):
    return [_note_out(n) for n in await _notes(db, profile.id)]


async def _own_note(db: AsyncSession, note_id: uuid.UUID, profile: Profile) -> TalkNote:
    note = await db.get(TalkNote, note_id)
    if note is None or note.learner_id != profile.id:
        raise _problem(status.HTTP_404_NOT_FOUND, "Không tìm thấy mục này.", "not_found")
    return note


@router.patch("/notes/{note_id}", response_model=TalkNoteOut)
async def update_note(
    note_id: uuid.UUID,
    body: TalkNoteUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    profile: Annotated[Profile, Depends(get_current_profile)],
):
    note = await _own_note(db, note_id, profile)
    note.done_at = datetime.now(timezone.utc) if body.done else None
    await db.commit()
    return _note_out(note)


@router.delete("/notes/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_note(
    note_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    profile: Annotated[Profile, Depends(get_current_profile)],
):
    note = await _own_note(db, note_id, profile)
    await db.delete(note)
    await db.commit()


@router.get("/{session_id}", response_model=TalkSessionDetailOut)
async def get_session(
    session_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    profile: Annotated[Profile, Depends(get_current_profile)],
):
    row = await _own_session(db, session_id, profile)
    titles = await _lesson_titles(db, {row.lesson_id} if row.lesson_id else set())
    base = talk_history.summary_row(row, titles.get(row.lesson_id))
    m = row.metrics or {}
    return TalkSessionDetailOut(
        **base,
        report=ConversationReportOut(**row.report) if isinstance(row.report, dict) and row.report else None,
        pronunciation=PronunciationOut(**row.pronunciation) if isinstance(row.pronunciation, dict) and row.pronunciation else None,
        turns=[t for t in (row.turns or []) if t.get("role") in ("learner", "haru")],
        band_note_vi=talk_profile.band_change_note(m["band_before"], m["band_after"])
        if m.get("band_before") and m.get("band_after")
        else None,
    )


@router.post("/{session_id}/save", response_model=TalkSaveOut)
async def save_to_review(
    session_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    profile: Annotated[Profile, Depends(get_current_profile)],
):
    row = await _own_session(db, session_id, profile)
    if not isinstance(row.report, dict) or not row.report:
        raise _problem(status.HTTP_409_CONFLICT, "Buổi này chưa có nhận xét để đưa vào ôn tập.", "no_report")
    now = datetime.now(timezone.utc)
    wanted = talk_history.notes_from_report(row.report)

    # words that are vocabulary cards (a lesson card first, else a news-article card): due now in
    # the review queue. A word with no card stays a note only.
    words = [n["ko"] for n in wanted if n["kind"] == "word"]
    card_of = await talk_notes_db.cards_by_hangul(db, words)
    await talk_notes_db.put_in_review(db, profile.id, card_of.values(), now)
    added_to_review = list(card_of)

    existing = {(n.kind, n.ko): n for n in await _notes(db, profile.id)}
    added = 0
    for n in wanted:
        old = existing.get((n["kind"], n["ko"]))
        if old is not None:
            old.done_at = None  # it came back: open it again
            if n["kind"] == "word" and old.vocab_item_id is None:
                old.vocab_item_id = card_of.get(n["ko"])  # saved before it had a card
            continue
        db.add(
            TalkNote(
                learner_id=profile.id, session_id=row.id, kind=n["kind"], ko=n["ko"], vi=n["vi"],
                vocab_item_id=card_of.get(n["ko"]) if n["kind"] == "word" else None, created_at=now,
            )
        )
        added += 1
    row.saved_at = now
    await db.commit()
    return TalkSaveOut(
        notes_added=added,
        added_to_review=added_to_review,
        notes=[_note_out(n) for n in await _notes(db, profile.id)],
    )

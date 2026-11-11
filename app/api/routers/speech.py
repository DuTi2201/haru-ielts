"""POST /me/speech/assess — score one read-aloud sentence (the lesson's "Nói thử" step).

The sentence must be one the lesson teaches (an example of one of its words or cards, or a line of
a sitting's lecture): the endpoint is not a general speech service. Signed-in learners who hold the
lesson only; a per-learner hourly allowance (each call is a paid Azure request)."""
from __future__ import annotations

import base64
import logging
import re
from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import _problem, ensure_lesson_open, get_current_profile
from app.core import ratelimit
from app.core.config import settings
from app.db import get_db
from app.models import GrammarPoint, Lesson, Profile, VocabItem
from app.services import azure_pron, pronunciation

log = logging.getLogger("haru.speech")
router = APIRouter(prefix="/me/speech", tags=["speech"])


class AssessIn(BaseModel):
    lesson_id: int
    text: str = Field(min_length=1, max_length=300)
    wav_b64: str = Field(min_length=100, max_length=1_400_000)  # 30 s of 16 kHz 16-bit mono is ~960 kB, base64 ~1.28 MB


def _norm(s: str) -> str:
    return re.sub(r"[^a-z']+", " ", s.lower().replace("’", "'")).strip()


async def lesson_sentences(db: AsyncSession, lesson: Lesson) -> set[str]:
    """Every English sentence the lesson teaches, normalised: its words' and cards' examples and
    the English lines of its sittings' lectures."""
    out: set[str] = set()
    vocab = (await db.execute(select(VocabItem.headword, VocabItem.example_en).where(VocabItem.lesson_id == lesson.id))).all()
    cards = (await db.execute(select(GrammarPoint.example_en).where(GrammarPoint.lesson_id == lesson.id))).all()
    for head, ex in vocab:
        out.add(_norm(head))
        out.update(_norm(x) for x in (ex or "").split("\n") if x.strip())
    for (ex,) in cards:
        out.update(_norm(x) for x in (ex or "").split("\n") if x.strip())
    for ses in lesson.sessions or []:
        for slide in ses.get("lecture") or []:
            out.update(_norm(str(ln["en"])) for ln in slide.get("lines") or [] if ln.get("en"))
    out.discard("")
    return out


@router.post("/assess")
async def assess(
    body: AssessIn,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    profile: Annotated[Profile, Depends(get_current_profile)],
) -> dict:
    lesson = await db.get(Lesson, body.lesson_id)
    if lesson is None:
        raise _problem(status.HTTP_404_NOT_FOUND, "Không tìm thấy bài học.", "not_found")
    await ensure_lesson_open(db, profile, lesson)
    if not azure_pron.is_configured():
        raise _problem(status.HTTP_503_SERVICE_UNAVAILABLE, "Chấm phát âm chưa được bật trên máy chủ.", "pron_off")
    try:
        reference = azure_pron.check_reference(body.text)
    except ValueError:
        raise _problem(status.HTTP_422_UNPROCESSABLE_ENTITY, "Câu cần đọc không hợp lệ.", "bad_reference") from None
    if _norm(reference) not in await lesson_sentences(db, lesson):
        raise _problem(status.HTTP_422_UNPROCESSABLE_ENTITY, "Câu này không thuộc bài học.", "not_in_lesson")
    try:
        wav = base64.b64decode(body.wav_b64, validate=True)
        azure_pron.check_wav(wav)
    except (ValueError, pronunciation.ClipError):
        raise _problem(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "Bản ghi âm chưa dùng được (cần từ nửa giây đến 30 giây).", "bad_audio"
        ) from None
    await ratelimit.spend(request, "pron", per_client=settings.PRON_PER_CLIENT_HOURLY, overall=settings.PRON_ALL_HOURLY)
    try:
        return await azure_pron.assess(wav, reference)
    except azure_pron.PronTransient as exc:
        log.warning("[speech] transient: %s", exc)
        raise _problem(status.HTTP_503_SERVICE_UNAVAILABLE, "Máy chấm đang bận, bạn thử lại sau ít phút.", "pron_busy") from None
    except azure_pron.PronError as exc:
        log.warning("[speech] failed: %s", exc)
        raise _problem(status.HTTP_502_BAD_GATEWAY, "Chưa chấm được lần này.", "pron_failed") from None

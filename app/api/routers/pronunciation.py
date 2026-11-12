"""Pronunciation course: GET /pronunciation (public, the videos and practice texts) and
POST /me/pronunciation/assess (signed in; score the learner's recording of one practice text of one
sound with Azure, en-GB). A per-learner hourly allowance applies (each call is a paid Azure request).
Scores are read-aloud scores for the text, not IELTS bands."""
from __future__ import annotations

import base64
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from pydantic import BaseModel, Field

from app.api.deps import _problem, get_current_profile
from app.core import ratelimit
from app.core.config import settings
from app.models import Profile
from app.services import azure_pron, pron_sounds, pronunciation

log = logging.getLogger("haru.pronunciation")
router = APIRouter(tags=["pronunciation"])


class PronAssessIn(BaseModel):
    sound: str = Field(min_length=1, max_length=8)
    text: str = Field(min_length=1, max_length=300)
    wav_b64: str = Field(min_length=100, max_length=1_400_000)


@router.get("/pronunciation")
async def course() -> dict:
    return pron_sounds.load()


@router.post("/me/pronunciation/assess")
async def assess(
    body: PronAssessIn,
    request: Request,
    profile: Annotated[Profile, Depends(get_current_profile)],
) -> dict:
    sound = pron_sounds.get_sound(body.sound)
    if sound is None:
        raise _problem(status.HTTP_404_NOT_FOUND, "Không tìm thấy âm này.", "not_found")
    if not azure_pron.is_configured():
        raise _problem(status.HTTP_503_SERVICE_UNAVAILABLE, "Chấm phát âm chưa được bật trên máy chủ.", "pron_off")
    try:
        reference = azure_pron.check_reference(body.text)
    except ValueError:
        raise _problem(status.HTTP_422_UNPROCESSABLE_ENTITY, "Văn bản cần đọc không hợp lệ.", "bad_reference") from None
    if not pron_sounds.allowed(sound, reference):
        raise _problem(status.HTTP_422_UNPROCESSABLE_ENTITY, "Văn bản này không thuộc bài luyện của âm.", "not_in_sound")
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
        log.warning("[pron] transient: %s", exc)
        raise _problem(status.HTTP_503_SERVICE_UNAVAILABLE, "Máy chấm đang bận, bạn thử lại sau ít phút.", "pron_busy") from None
    except azure_pron.PronError as exc:
        log.warning("[pron] failed: %s", exc)
        raise _problem(status.HTTP_502_BAD_GATEWAY, "Chưa chấm được lần này.", "pron_failed") from None

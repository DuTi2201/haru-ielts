"""Audio caching for any Korean text: ask for a text to be read aloud; if its recording is already
filed it is played at once, otherwise Google Chirp voices it ONCE and it is filed for every later
play, by any learner or device.

    text ──► key = hash(text, voice, pace, version)
              │
              ├─ a row `audio.text_audio` with that key ─────────► play it (no Google call)
              └─ none ─► Chirp 3 HD ─► Base64 `audioContent` decoded (google_tts.synthesize_pcm)
                         ─► ffmpeg ─► opus + aac ─► file (Postgres row, or a private GCS bucket)
                         + the row that links the text to its file

The route (app/api/routers/audio.py) and the task (app/workers/tasks.py) are thin; the rules live
here so they can be tested without a network."""
from __future__ import annotations

import logging
import re

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import TextAudio
from app.services import audio_keys, audio_store, azure_tts, tts

log = logging.getLogger(__name__)

VOICES = ("en-female-1", "en-female-2", "en-male-1", "en-male-2", "ko-female-1", "ko-female-2", "ko-male-1", "ko-male-2")
PROMPT_VERSION = "v1"
_ASCII_LETTER = re.compile(r"[A-Za-z]")
_VIET_DIACRITIC = re.compile(
    r"[ÀÁÂÃÈÉÊÌÍÒÓÔÕÙÚÝàáâãèéêìíòóôõùúýĂăĐđĨĩŨũƠơƯưẠ-ỹ]"
)
_LETTER = re.compile(r"[^\W\d_]", re.UNICODE)


class TextNotSpeakable(ValueError):
    """The text cannot be voiced here (empty, too long, or not English)."""


def check_text(text: str | None) -> str:
    """The text to voice: normalised, and only English. This door turns text into paid speech, so it
    voices English only (an en-GB/en-US voice cannot read Vietnamese or Korean) and not at any length."""
    spoken = audio_keys.speakable(text)
    if not spoken:
        raise TextNotSpeakable("Văn bản trống.")
    if len(spoken) > settings.TEXT_AUDIO_MAX_CHARS:
        raise TextNotSpeakable(f"Văn bản dài quá {settings.TEXT_AUDIO_MAX_CHARS} ký tự.")
    letters = _LETTER.findall(spoken)
    en_letters = _ASCII_LETTER.findall(spoken)
    if _VIET_DIACRITIC.search(spoken) or not en_letters or len(en_letters) * 2 < len(letters):
        raise TextNotSpeakable("Chỉ đọc được văn bản tiếng Anh.")
    return spoken


def voice_spec() -> str:
    """The voice + pace in use, part of every key: change the Chirp voice or rate on Railway and the
    texts are voiced again in the new voice. Without Chirp the recordings are Gemini's."""
    if azure_tts.is_configured():
        return azure_tts.spec()
    return tts.chirp_spec() if tts.chirp_enabled() else "gemini"


def cache_key(text: str, voice: str, prompt_version: str = PROMPT_VERSION) -> str:
    return audio_keys.text_audio_key(text, voice, voice_spec(), prompt_version)


def paths(key: str) -> dict[str, str]:
    base = f"/api/v1/audio/text/{key}"
    return {"opus_path": f"{base}.opus", "aac_path": f"{base}.aac"}


def is_usable(row: TextAudio | None) -> bool:
    """A recording that can be played as it is. One that Gemini made because Chirp failed is not,
    while Chirp is configured: it is made again (and replaced) the next time it is asked for."""
    if row is None:
        return False
    return row.provider == _best_provider() or (_best_provider() == "chirp" and not tts.chirp_enabled())


def _best_provider() -> str:
    """The voice that should have made a recording: Azure when configured, else Chirp."""
    return "azure" if azure_tts.is_configured() else "chirp"


def _file_away(key: str, opus: bytes, aac: bytes) -> dict:
    """File the bytes where `AUDIO_STORAGE` says; if the bucket fails, in the row (never lose the audio)."""
    if audio_store.backend() == "gcs":
        opus_key, aac_key = audio_store.object_key(key, "opus"), audio_store.object_key(key, "aac")
        try:
            audio_store.gcs_put(opus_key, opus, "audio/ogg")
            audio_store.gcs_put(aac_key, aac, "audio/aac")
            return {"storage": "gcs", "opus_key": opus_key, "aac_key": aac_key, "opus_data": None, "aac_data": None}
        except audio_store.StoreError as exc:
            log.warning("[text_audio] bucket write failed (%s); keeping %s in the database", exc, key)
    return {"storage": "db", "opus_key": None, "aac_key": None, "opus_data": opus, "aac_data": aac}


def synthesize(text: str, voice: str) -> tuple[bytes, bytes, int, str]:
    """(opus, aac, seconds, provider) — Chirp 3 HD first, Gemini if Chirp fails."""
    return tts.synthesize_korean_with_provider(text, voice)


def save(db: Session, key: str, text: str, voice: str, prompt_version: str, produced: tuple[bytes, bytes, int, str]) -> TextAudio:
    """File a recording and the row that links it to its text. A row of the same key already there
    (a Gemini fallback being replaced, or another worker that got there first) is reused: the Chirp
    recording replaces the fallback; a fallback never replaces anything."""
    opus, aac, duration, provider = produced
    existing = db.execute(select(TextAudio).where(TextAudio.cache_key == key)).scalar_one_or_none()
    if existing is not None:
        if provider != _best_provider() or existing.provider == provider:
            return existing
        fields = _file_away(key, opus, aac)
        for name, value in fields.items():
            setattr(existing, name, value)
        existing.provider, existing.duration_sec = provider, duration
        existing.opus_bytes, existing.aac_bytes = len(opus), len(aac)
        db.commit()
        return existing
    row = TextAudio(
        cache_key=key, text_en=text, voice=voice, prompt_version=prompt_version, provider=provider,
        duration_sec=duration, opus_bytes=len(opus), aac_bytes=len(aac), **_file_away(key, opus, aac),
    )
    db.add(row)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        winner = db.execute(select(TextAudio).where(TextAudio.cache_key == key)).scalar_one_or_none()
        if winner is None:
            raise
        return winner
    return row


def read(row: TextAudio, ext: str) -> bytes | None:
    """The bytes of one container ("opus" | "aac") of a filed recording, from wherever it is kept."""
    if row.storage == "gcs":
        key = row.opus_key if ext == "opus" else row.aac_key
        return audio_store.gcs_get(key) if key else None
    return row.opus_data if ext == "opus" else row.aac_data

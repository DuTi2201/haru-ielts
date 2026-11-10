"""Cache keys of the word and sentence recordings.

A recording is filed under what it SAYS, not under the row that asked for it: the same word
in two lessons (or in a lesson and an article) is one recording, made once and played for
everyone. The text always comes from the database, never from the request — a caller can
neither make the server voice something else nor file it under a word's key."""
from __future__ import annotations

import hashlib
import unicodedata


def speakable(text: str | None) -> str:
    """The text a recording is made from: NFC, no surrounding space, one space between words."""
    return " ".join(unicodedata.normalize("NFC", text or "").split())


def vocab_audio_key(text: str, voice: str, prompt_version: str) -> str:
    """Key of a word's recording: the same word, voice and version give the same key in every
    lesson. (Recordings made before this carry the old `{vocab_item_id}:{voice}:{version}`
    key and are still found under it — see `vocab_legacy_key`.)"""
    digest = hashlib.sha256(f"{speakable(text)}|{voice}|{prompt_version}".encode("utf-8")).hexdigest()[:24]
    return f"vt:{digest}"


def vocab_legacy_key(vocab_item_id: int, voice: str, prompt_version: str) -> str:
    return f"{vocab_item_id}:{voice}:{prompt_version}"


def text_audio_key(text: str, voice: str, spec: str, prompt_version: str) -> str:
    """Key of the recording of a TEXT: the same text, voice, pace (`spec`, the Chirp voice + rate in
    use, or "gemini") and version give the same key for every learner and device. Changing the Chirp
    voice or pace on Railway changes `spec`, so the texts are voiced again in the new voice."""
    digest = hashlib.sha256(f"{speakable(text)}|{voice}|{spec}|{prompt_version}".encode("utf-8")).hexdigest()[:32]
    return f"tx:{digest}"

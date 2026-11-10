"""Azure Neural TTS for Korean (ko-KR-SunHiNeural / ko-KR-InJoonNeural): the voice for every short
Korean text Haru plays — a letter, a word card, a sentence, a dialogue line. Words are sent through
app/services/korean_g2p.py first, so a word on its own is read with its standard pronunciation.
Long mixed Vietnamese–Korean lectures and article read-alongs stay on Google Chirp.

The key lives only in the server environment (AZURE_SPEECH_KEY, AZURE_SPEECH_REGION); it travels in
a request header and never appears in an error message or a log line."""
from __future__ import annotations

import re

import httpx

from app.core.config import settings
from app.services import korean_g2p

FORMAT = "raw-24khz-16bit-mono-pcm"
SAMPLE_RATE = 24000
G2P_VERSION = "g2p1"  # bump when the pronunciation table or its rules change: texts are voiced again
_TIMEOUT = httpx.Timeout(30.0, connect=10.0)
_VOICE_RE = re.compile(r"^ko-KR-[A-Za-z]+Neural$")


class AzureTTSError(RuntimeError):
    pass


class AzureTTSTransient(AzureTTSError):
    pass


def is_configured() -> bool:
    return bool(settings.AZURE_SPEECH_KEY and settings.AZURE_SPEECH_REGION)


def voice_for(voice: str) -> str:
    """Haru's voice ids ("ko-female-1", "ko-male-2" …) onto Azure voices."""
    name = settings.AZURE_TTS_VOICE_MALE if voice.startswith("ko-male") else settings.AZURE_TTS_VOICE
    if not _VOICE_RE.match(name):
        raise AzureTTSError(f"'{name}' không phải tên giọng Azure tiếng Hàn")
    return name


def spec() -> str:
    """Voice + pace + pronunciation table, part of every cache key: change one and texts are voiced again."""
    v = settings.AZURE_TTS_VOICE.replace("ko-KR-", "").replace("Neural", "").lower()
    return f"az-{v}-r{round(settings.AZURE_TTS_RATE * 100)}-{G2P_VERSION}"


def dialogue_spec() -> str:
    """The two voices + pace a practice dialogue is recorded with (part of its cache key)."""

    def short(name: str) -> str:
        return name.replace("ko-KR-", "").replace("Neural", "").lower()

    return f"az-{short(settings.AZURE_TTS_VOICE)}-{short(settings.AZURE_TTS_VOICE_MALE)}-r{round(settings.AZURE_TTS_RATE * 100)}-{G2P_VERSION}"


def ssml(text: str, voice: str) -> str:
    rate = f"{round((settings.AZURE_TTS_RATE - 1) * 100):+d}%"
    return (
        '<speak version="1.0" xml:lang="ko-KR" xmlns="http://www.w3.org/2001/10/synthesis">'
        f'<voice name="{voice_for(voice)}"><prosody rate="{rate}">{korean_g2p.to_ssml_body(text)}</prosody></voice></speak>'
    )


def synthesize_pcm(text: str, voice: str = "ko-female-1") -> tuple[bytes, int]:
    """One request -> (pcm, sample_rate). AzureTTSTransient for a failure worth retrying."""
    text = text.strip()
    if not text:
        raise AzureTTSError("empty text")
    if not is_configured():
        raise AzureTTSError("Azure Speech is not configured")
    url = f"https://{settings.AZURE_SPEECH_REGION}.tts.speech.microsoft.com/cognitiveservices/v1"
    headers = {
        "Ocp-Apim-Subscription-Key": settings.AZURE_SPEECH_KEY,
        "Content-Type": "application/ssml+xml",
        "X-Microsoft-OutputFormat": FORMAT,
        "User-Agent": "haru-tts",
    }
    try:
        resp = httpx.post(url, content=ssml(text, voice).encode("utf-8"), headers=headers, timeout=_TIMEOUT)
    except (httpx.TimeoutException, httpx.TransportError) as exc:
        raise AzureTTSTransient(f"Azure TTS unreachable: {type(exc).__name__}") from exc
    if resp.status_code == 200 and resp.content:
        return resp.content, SAMPLE_RATE
    if resp.status_code in (429, 500, 502, 503, 504):
        raise AzureTTSTransient(f"Azure TTS HTTP {resp.status_code}")
    raise AzureTTSError(f"Azure TTS HTTP {resp.status_code}")

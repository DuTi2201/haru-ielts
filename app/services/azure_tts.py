"""Azure Neural TTS for English (en-GB / en-US Neural) and Korean (ko-KR Neural): the voice for
every short text Haru plays — a word card, a sentence, a dialogue line. Korean voices still run
through app/services/korean_g2p.py; English voices skip the Korean pronunciation step.
Long mixed Vietnamese–target lectures and article read-alongs stay on Google Chirp.

The key lives only in the server environment (AZURE_SPEECH_KEY, AZURE_SPEECH_REGION); it travels in
a request header and never appears in an error message or a log line."""
from __future__ import annotations

import html
import re

import httpx

from app.core.config import settings
from app.services import korean_g2p

FORMAT = "raw-24khz-16bit-mono-pcm"
SAMPLE_RATE = 24000
G2P_VERSION = "g2p1"  # bump when the pronunciation table or its rules change: texts are voiced again
_TIMEOUT = httpx.Timeout(30.0, connect=10.0)
_VOICE_RE = re.compile(r"^(?:en-(?:GB|US|AU)|ko-KR)-[A-Za-z]+Neural$")
_LOCALE_PREFIX_RE = re.compile(r"^(?:en-(?:GB|US|AU)|ko-KR)-")


class AzureTTSError(RuntimeError):
    pass


class AzureTTSTransient(AzureTTSError):
    pass


def is_configured() -> bool:
    return bool(settings.AZURE_SPEECH_KEY and settings.AZURE_SPEECH_REGION)


def _short(name: str) -> str:
    return _LOCALE_PREFIX_RE.sub("", name).replace("Neural", "").lower()


def voice_for(voice: str) -> str:
    """Haru's voice ids ("en-female-1", "en-male-1", "ko-female-1", "ko-male-2" …) onto Azure voices."""
    is_male = voice.startswith(("en-male", "ko-male"))
    name = settings.AZURE_TTS_VOICE_MALE if is_male else settings.AZURE_TTS_VOICE
    if not _VOICE_RE.match(name):
        raise AzureTTSError(f"'{name}' không phải tên giọng Azure hợp lệ")
    return name


def spec() -> str:
    """Voice + pace + pronunciation table, part of every cache key: change one and texts are voiced again."""
    v = _short(settings.AZURE_TTS_VOICE)
    return f"az-{v}-r{round(settings.AZURE_TTS_RATE * 100)}-{G2P_VERSION}"


def dialogue_spec() -> str:
    """The two voices + pace a practice dialogue is recorded with (part of its cache key)."""
    return f"az-{_short(settings.AZURE_TTS_VOICE)}-{_short(settings.AZURE_TTS_VOICE_MALE)}-r{round(settings.AZURE_TTS_RATE * 100)}-{G2P_VERSION}"


def ssml(text: str, voice: str) -> str:
    v = voice_for(voice)
    lang = "-".join(v.split("-")[:2])
    rate = f"{round((settings.AZURE_TTS_RATE - 1) * 100):+d}%"
    body = korean_g2p.to_ssml_body(text) if lang == "ko-KR" else html.escape(text, quote=False)
    return (
        f'<speak version="1.0" xml:lang="{lang}" xmlns="http://www.w3.org/2001/10/synthesis">'
        f'<voice name="{v}"><prosody rate="{rate}">{body}</prosody></voice></speak>'
    )


def synthesize_pcm(text: str, voice: str = "en-female-1") -> tuple[bytes, int]:
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

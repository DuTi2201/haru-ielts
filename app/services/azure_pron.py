"""Pronunciation assessment of ONE read-aloud sentence with Azure Speech (the "Nói thử" step).

The learner hears a sentence, records it, and the recording is scored against that sentence
(scripted assessment) by Azure's pronunciation-assessment model through the speech-to-text REST
API for short audio: an acoustic measurement, not a language model's impression. One request per
sentence; the audio is 16 kHz 16-bit mono WAV, at most 30 seconds (the API's own limit for
assessment), and is not stored.

What comes back, all 0-100 (Azure's HundredMark scale):
  accuracy      how close the sounds are to a native speaker's
  fluency       how natural the pauses between words are
  completeness  share of the sentence's words that were said
  pron          Azure's overall score from the three above
and per word: its accuracy and whether it was left out, put in, or mispronounced.

The scores are NOT IELTS bands. IELTS marks pronunciation in free speech on intelligibility,
stress, rhythm and intonation; a read-aloud score says how clearly THIS sentence was produced.
The app says so next to the number.

The key lives only in the server environment and travels in a request header.
"""
from __future__ import annotations

import base64
import json
import re
from typing import Any

import httpx

from app.core.config import settings
from app.services import pronunciation

LOCALE = "en-GB"
MAX_SECONDS = 30.0  # Azure: "for pronunciation assessment, the audio duration should be no more than 30 seconds"
MIN_SECONDS = 0.5
MAX_REFERENCE_WORDS = 40
_TIMEOUT = httpx.Timeout(25.0, connect=8.0)
_WORD_RE = re.compile(r"[A-Za-z]+(?:['’][A-Za-z]+)?")

# Bands of the accuracy score a learner can act on. The cut-offs are Haru's reading of the scale
# (Azure publishes none); they are shown as words, with the number beside them, and are to be
# re-set from learners' data (docs/QUALITY_LESSON44.md, "Ngưỡng điểm phát âm").
GOOD, FAIR = 80, 60


class PronError(RuntimeError):
    pass


class PronTransient(PronError):
    pass


def is_configured() -> bool:
    return bool(settings.AZURE_SPEECH_KEY and settings.AZURE_SPEECH_REGION)


def reference_words(text: str) -> list[str]:
    return _WORD_RE.findall(text)


def check_reference(text: str) -> str:
    """The sentence to be read: English words only, short enough to say in one breath or two."""
    text = re.sub(r"\s+", " ", text).strip()
    n = len(reference_words(text))
    if not 1 <= n <= MAX_REFERENCE_WORDS:
        raise ValueError(f"the sentence must have 1-{MAX_REFERENCE_WORDS} English words")
    return text


def check_wav(wav: bytes) -> float:
    seconds = pronunciation.wav_seconds(wav)  # raises ClipError unless 16 kHz 16-bit mono PCM
    if not MIN_SECONDS <= seconds <= MAX_SECONDS:
        raise pronunciation.ClipError(f"{seconds:.1f}s is outside {MIN_SECONDS}-{MAX_SECONDS:.0f}s")
    return seconds


def assessment_header(reference: str) -> str:
    """The Pronunciation-Assessment header: base64 of the parameters, as Azure's REST reference gives them."""
    params = {
        "ReferenceText": reference,
        "GradingSystem": "HundredMark",
        "Granularity": "Phoneme",
        "Dimension": "Comprehensive",
        "EnableMiscue": True,
    }
    return base64.b64encode(json.dumps(params).encode("utf-8")).decode("ascii")


def _num(v: Any) -> float | None:
    try:
        return round(float(v), 1)
    except (TypeError, ValueError):
        return None


def parse(body: dict[str, Any], reference: str) -> dict[str, Any]:
    """Azure's detailed answer -> what the screen shows. With format=detailed the scores sit on the
    best hypothesis (NBest[0]), either directly or under "PronunciationAssessment" depending on the
    API version: both shapes are read."""
    status = body.get("RecognitionStatus")
    best = (body.get("NBest") or [{}])[0] if status == "Success" else {}
    pa = best.get("PronunciationAssessment") or best
    words = []
    for w in best.get("Words") or []:
        wpa = w.get("PronunciationAssessment") or w
        err = str(wpa.get("ErrorType") or "None")
        words.append({
            "word": str(w.get("Word") or ""),
            "accuracy": _num(wpa.get("AccuracyScore")),
            "error": {"None": "ok", "Omission": "omitted", "Insertion": "inserted", "Mispronunciation": "mispronounced"}.get(err, "ok"),
        })
    accuracy = _num(pa.get("AccuracyScore"))
    heard = str(best.get("Display") or best.get("Lexical") or body.get("DisplayText") or "").strip()
    if accuracy is None:
        return {"ok": False, "heard": heard, "reason": "no_speech" if status in ("NoMatch", "InitialSilenceTimeout") else "not_scored"}
    weak = [w["word"] for w in words if w["error"] in ("mispronounced", "omitted") or (w["accuracy"] is not None and w["accuracy"] < FAIR)]
    return {
        "ok": True,
        "reference": reference,
        "heard": heard,
        "accuracy": accuracy,
        "fluency": _num(pa.get("FluencyScore")),
        "completeness": _num(pa.get("CompletenessScore")),
        "pron": _num(pa.get("PronScore")),
        # a sentence with a word left out is said again, however clear the rest was
        "level": "retry" if accuracy < FAIR or (_num(pa.get("CompletenessScore")) or 0) < 99 else "good" if accuracy >= GOOD else "fair",
        "words": words,
        "weak": weak[:6],
    }


async def assess(wav: bytes, reference: str, client: httpx.AsyncClient | None = None) -> dict[str, Any]:
    """Score one recording against one sentence. Raises PronTransient for a retryable failure."""
    if not is_configured():
        raise PronError("Azure Speech is not configured")
    url = f"https://{settings.AZURE_SPEECH_REGION}.stt.speech.microsoft.com/speech/recognition/conversation/cognitiveservices/v1"
    headers = {
        "Ocp-Apim-Subscription-Key": settings.AZURE_SPEECH_KEY,
        "Content-Type": "audio/wav; codecs=audio/pcm; samplerate=16000",
        "Accept": "application/json",
        "Pronunciation-Assessment": assessment_header(reference),
    }
    own = client is None
    client = client or httpx.AsyncClient(timeout=_TIMEOUT)
    try:
        r = await client.post(url, params={"language": LOCALE, "format": "detailed"}, headers=headers, content=wav)
    except httpx.HTTPError as exc:
        raise PronTransient(exc.__class__.__name__) from None  # never the URL or a header in a message
    finally:
        if own:
            await client.aclose()
    if r.status_code in (429, 500, 502, 503, 504):
        raise PronTransient(f"Azure {r.status_code}")
    if r.status_code != 200:
        raise PronError(f"Azure {r.status_code}")
    return parse(r.json(), reference)

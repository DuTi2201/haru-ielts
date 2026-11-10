"""Text-to-speech + ffmpeg transcode — the real implementation behind
`audio.lecture_audio` (whole-lesson narration), `audio.corpus_item_audio`
(single-sentence listening clips) and the article read-aloud.

Voices: Google Chirp 3 HD (app/services/google_tts.py) is the PRIMARY voice
for Korean-only text whenever the `TTS_GG_Chirp` credential is configured
(`synthesize_article_chirp`, `synthesize_korean_tts_chirp_first`); Gemini TTS
below is the fallback. The podcast script mixes Vietnamese with Korean, and a
Chirp voice speaks one language only, so `synthesize_lecture_chirp` voices it
run by run (Hangul with the ko-KR voice, Vietnamese with the vi-VN one). One call
here == one TTS request, so every caller MUST go through the
content-addressed cache (cache_key = f"{content_id}:{voice}:{prompt_version}",
already the pattern audio.py's lecture-audio route uses) rather than
calling this on every playback — that's what keeps repeat listens free.

Gemini's TTS models return headerless 16-bit signed little-endian PCM
(default 24kHz mono for a unary/non-streaming request); ffmpeg transcodes
that once into two containers so the frontend can always play something:
Opus/Ogg (small, good quality, Chrome/Firefox/Android) and AAC/ADTS
(larger, but the one that also plays on Safari/iOS, since Ogg-Opus
support there is inconsistent).
"""
from __future__ import annotations

import re
import subprocess
import tempfile
import threading
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed

from google import genai
from google.genai import errors as genai_errors

from app.core.config import settings
from app.services import azure_tts, google_tts, lecture_voice, read_along

# Friendly ids (already the shape of LectureAudioRequest.voice's default,
# "ko-female-1") mapped to one of Gemini's prebuilt voice names. Kept as a
# small indirection layer (SDD §5 "cấu hình thay cho hard-code") so the
# API contract doesn't have to change if Gemini's voice catalog does.
VOICE_MAP: dict[str, str] = {
    "en-female-1": "Kore",
    "en-female-2": "Leda",
    "en-male-1": "Charon",
    "en-male-2": "Orus",
    "ko-female-1": "Kore",
    "ko-female-2": "Leda",
    "ko-male-1": "Charon",
    "ko-male-2": "Orus",
}
DEFAULT_GEMINI_VOICE = "Kore"

_RATE_RE = re.compile(r"rate=(\d+)")


class TransientTTSError(RuntimeError):
    """A failure that is worth retrying (Gemini 5xx / empty audio) — as
    opposed to quota exhaustion or a content rejection, where a retry only
    burns more quota. Still a RuntimeError, so every existing caller that
    catches RuntimeError is unaffected."""

class TranscodeError(RuntimeError):
    """ffmpeg could not turn a finished recording into opus / aac (too slow, or it failed). The voice
    work was done and is fine, so redoing it with another voice engine cannot help — the caller must
    not fall back to one."""


class TTSContentShapeError(RuntimeError):
    """Gemini TTS refused a chunk because it read like a task to perform (an
    order, an exam question, a stack of questions) instead of a transcript to
    voice — 400 "Model tried to generate text, but it should only be used for
    TTS". Not transient and not a quota problem: the same text fails again, so
    `_synthesize_chunk_pcm` changes how the text is presented instead of
    repeating it. Still a RuntimeError for every caller that catches that."""


# Said in front of a chunk the voice has refused once. It is the documented way
# to steer Gemini TTS ("Say cheerfully: ..."): a style instruction followed by
# a colon, then the transcript. It makes "read this out" unmistakable without a
# system_instruction (which broke every podcast request, see _tts_config).
_TRANSCRIPT_FRAME = "Say slowly and warmly, like a friendly teacher talking to a student: "

# The actual cause of the podcast 500s turned out to be the (now-removed)
# system_instruction field, not length — a ~1600-char chunk reproduced the
# same 500 regardless. Kept as a defensive ceiling anyway: Google doesn't
# document a hard input limit for native TTS, and a whole-lesson script
# can run to several thousand characters, so this keeps each request to
# roughly a minute of speech. Below this, text is sent as one chunk
# exactly like before (so short callers are unaffected); above it, text is
# split at sentence boundaries and synthesized as multiple chunks whose
# raw PCM gets concatenated before a single transcode.
_MAX_TTS_CHARS = 1600
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?…])\s+")

_client: genai.Client | None = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=settings.GEMINI_API_KEY)
    return _client


def _resolve_voice(voice: str) -> str:
    return VOICE_MAP.get(voice) or (voice if voice in VOICE_MAP.values() else DEFAULT_GEMINI_VOICE)


def _split_for_tts(text: str, max_chars: int) -> list[str]:
    """Greedily pack sentence-like pieces into chunks no larger than
    max_chars, splitting only at a sentence boundary (a punctuation mark
    the podcast script already uses for pauses) so a chunk edge never
    lands mid-clause. Falls back to a hard split for the rare single
    "sentence" that alone exceeds max_chars (e.g. a long compound example
    with no terminal punctuation)."""
    sentences = [s.strip() for s in _SENTENCE_SPLIT_RE.split(text.strip()) if s.strip()]
    chunks: list[str] = []
    current = ""
    for sentence in sentences:
        candidate = f"{current} {sentence}".strip() if current else sentence
        if len(candidate) <= max_chars:
            current = candidate
            continue
        if current:
            chunks.append(current)
            current = ""
        if len(sentence) <= max_chars:
            current = sentence
        else:
            for start in range(0, len(sentence), max_chars):
                chunks.append(sentence[start : start + max_chars])
    if current:
        chunks.append(current)
    return chunks or [text.strip()]


# ffmpeg turns a minute of speech into opus / aac in a second or two on an ordinary CPU. The machine
# that runs the worker is a small shared-core VM that also runs Postgres, the API and the Chirp
# threads, so on a busy moment the same job can run many times slower. A flat 60 s made a long lecture
# fail then (and put the raw command line in the error the learner saw). The limit grows with the
# length of the recording instead; it only has to catch an ffmpeg that is truly stuck.
_FFMPEG_MIN_TIMEOUT_S = 120.0
_FFMPEG_PER_AUDIO_SECOND = 1.0


def _ffmpeg_timeout(pcm_len: int, sample_rate: int) -> float:
    audio_seconds = pcm_len / (sample_rate * 2)  # 16-bit mono PCM: 2 bytes/sample
    return max(_FFMPEG_MIN_TIMEOUT_S, 30.0 + audio_seconds * _FFMPEG_PER_AUDIO_SECOND)


def _run_ffmpeg(pcm, sample_rate: int, *, codec_args: list[str], size: int | None = None) -> bytes:
    """Encode raw PCM. `pcm` is the bytes, or an open file holding them (then `size` is its length in
    bytes): a long lecture is read from disk by ffmpeg instead of being held in this process too."""
    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-f", "s16le", "-ar", str(sample_rate), "-ac", "1", "-i", "pipe:0",
        *codec_args, "pipe:1",
    ]
    codec = codec_args[codec_args.index("-c:a") + 1] if "-c:a" in codec_args else "?"
    if isinstance(pcm, (bytes, bytearray)):
        size, feed = len(pcm), {"input": pcm}
    else:
        pcm.seek(0)
        feed = {"stdin": pcm}
    limit = _ffmpeg_timeout(size or 0, sample_rate)
    started = time.monotonic()
    try:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=limit, **feed)
    except subprocess.TimeoutExpired as exc:
        print(f"[tts] ffmpeg {codec} gave up after {limit:.0f}s on {(size or 0) / 1e6:.1f} MB of PCM", flush=True)
        raise TranscodeError(
            "Máy chủ đang quá tải nên chưa mã hoá xong âm thanh (ffmpeg quá thời gian). Thử tạo lại sau ít phút."
        ) from exc
    took = time.monotonic() - started
    if took > 15:  # slow enough to matter: leave a trace in the worker log
        print(f"[tts] ffmpeg {codec} took {took:.0f}s for {(size or 0) / 1e6:.1f} MB of PCM", flush=True)
    if proc.returncode != 0:
        raise TranscodeError(f"ffmpeg failed ({' '.join(codec_args)}): {proc.stderr.decode('utf-8', errors='replace')[:500]}")
    return proc.stdout


_OPUS_ARGS = ["-c:a", "libopus", "-b:a", "48k", "-f", "ogg"]
# Speech at 24 kHz mono: 64 kbit/s AAC-LC is plenty (it was 96) and makes a 30-minute lecture ~16 MB, not ~24.
_AAC_ARGS = ["-c:a", "aac", "-b:a", "64k", "-f", "adts"]


def transcode_pcm(pcm_bytes: bytes, sample_rate: int = 24000) -> tuple[bytes, bytes, int]:
    """Pure transcode step, split out from `synthesize_korean_tts` so it can
    be exercised in tests without a live Gemini call (feed it synthetic PCM
    instead). Returns (opus_bytes, aac_bytes, duration_sec)."""
    if not pcm_bytes:
        raise RuntimeError("empty pcm_bytes")
    opus_bytes = _run_ffmpeg(pcm_bytes, sample_rate, codec_args=_OPUS_ARGS)
    aac_bytes = _run_ffmpeg(pcm_bytes, sample_rate, codec_args=_AAC_ARGS)
    duration_sec = round(len(pcm_bytes) / (sample_rate * 2))  # 16-bit mono PCM: 2 bytes/sample
    return opus_bytes, aac_bytes, duration_sec


def transcode_pcm_file(pcm_file, size: int, sample_rate: int = 24000) -> tuple[bytes, bytes, int]:
    """Same as `transcode_pcm`, for PCM that sits in a file (`size` bytes long): the long lecture."""
    if size <= 0:
        raise RuntimeError("empty pcm file")
    opus_bytes = _run_ffmpeg(pcm_file, sample_rate, codec_args=_OPUS_ARGS, size=size)
    aac_bytes = _run_ffmpeg(pcm_file, sample_rate, codec_args=_AAC_ARGS, size=size)
    return opus_bytes, aac_bytes, round(size / (sample_rate * 2))


def _synthesize_once(client: genai.Client, text: str, config: dict, models_to_try: list[str]) -> tuple[bytes, int]:
    """One request -> (pcm_bytes, sample_rate), trying each model in order and
    falling through to the next only on a quota (429) error. Raises
    RuntimeError with a clean, user-facing message otherwise
    (TTSContentShapeError when the text read like a task)."""
    response = None
    for i, model_name in enumerate(models_to_try):
        try:
            response = client.models.generate_content(model=model_name, contents=text, config=config)
            break
        except genai_errors.APIError as exc:
            is_quota = exc.status == "RESOURCE_EXHAUSTED" or exc.code == 429
            if is_quota and i < len(models_to_try) - 1:
                continue
            if is_quota:
                # Surface a clean, actionable message instead of the raw SDK
                # repr (a huge nested-dict string) — this is what ends up
                # verbatim in job.error.message and is shown to the user.
                print("[tts] Gemini TTS free quota exhausted (fallback model tried too); enable billing on the key", flush=True)
                raise RuntimeError(
                    "Giọng đọc của Haru đã hết lượt trong hôm nay. Bạn thử lại vào ngày mai nhé."
                ) from exc
            if exc.code == 400 and "tried to generate text" in (exc.message or ""):
                # Content-shape rejection, not a transient failure: some
                # phrasing in this particular chunk (imperative/exam-style
                # wording like "hãy chọn đáp án...") reads to the TTS model
                # like a task to perform rather than a transcript to voice.
                # Confirmed in production against a TOPIK-tip sentence
                # phrased as a command. _synthesize_chunk_pcm recovers.
                raise TTSContentShapeError(
                    "Một đoạn trong kịch bản bị hiểu nhầm là câu lệnh thay vì lời thoại cần "
                    "đọc, dù đã thử đọc lại theo cách khác. Thử lại để kịch bản được viết lại."
                ) from exc
            raise TransientTTSError(
                f"Giọng đọc tạm thời gặp lỗi ({exc.code} {exc.status or 'unknown'}), thử lại sau ít phút."
            ) from exc
    assert response is not None  # loop always either returns via break or raises

    candidates = response.candidates or []
    parts = candidates[0].content.parts if candidates and candidates[0].content else None
    inline = parts[0].inline_data if parts else None
    if inline is None or not inline.data:
        raise TransientTTSError("Gemini TTS returned no inline audio data")

    match = _RATE_RE.search(inline.mime_type or "")
    sample_rate = int(match.group(1)) if match else 24000
    return inline.data, sample_rate


def _synthesize_chunk_pcm(client: genai.Client, text: str, config: dict, models_to_try: list[str]) -> tuple[bytes, int]:
    """One chunk of text -> (pcm_bytes, sample_rate). When the voice treats the
    chunk as a task it is not given up on (that used to fail the whole lecture,
    throw away the chunks already voiced and, on retry, regenerate the script
    and spend the daily TTS quota again). Instead, in order:

    1. the chunk as it is (the normal case — nothing changes for chunks that
       work);
    2. the same text introduced as a transcript to say aloud;
    3. the chunk cut in two at a sentence boundary, each half introduced the
       same way — a long chunk with a few command-like sentences usually has
       halves that read as plain speech.

    Only then does the error reach the caller. Each step is logged, so the logs
    show which one finally worked."""
    try:
        return _synthesize_once(client, text, config, models_to_try)
    except TTSContentShapeError as first:
        print(f"[tts] chunk of {len(text)} chars read as a task; retrying framed as a transcript", flush=True)
        failure = first
    try:
        return _synthesize_once(client, _TRANSCRIPT_FRAME + text, config, models_to_try)
    except TTSContentShapeError as second:
        failure = second

    halves = _split_for_tts(text, max(len(text) // 2 + 1, 80))
    if len(halves) < 2:
        raise failure
    print(f"[tts] still refused; voicing it as {len(halves)} smaller parts", flush=True)
    parts: list[bytes] = []
    sample_rate = 24000
    for half in halves:
        pcm, sample_rate = _synthesize_once(client, _TRANSCRIPT_FRAME + half, config, models_to_try)
        parts.append(pcm)
    return b"".join(parts), sample_rate


def _tts_config(voice: str) -> tuple[dict, str]:
    """(request config, resolved Gemini voice name). Plain dict config (not
    typed types.GenerateContentConfig(...)) to match this pinned SDK's
    proven-working style in gemini_client.py — the SDK's dict->proto
    conversion accepts snake_case keys here.

    NOTE: no `system_instruction`. It was once added to stop a long
    conversational script from being *answered* instead of voiced (400
    "Model tried to generate text, but it should only be used for TTS") and
    turned out to be the wrong fix: Gemini's native TTS documents only
    response_modalities/speech_config, and every podcast call started
    failing with a generic 500 the moment it was added. The 400 is
    prevented at the source instead — script prompts forbid instruction-like
    phrasing, and article audio voices real news prose."""
    voice_name = _resolve_voice(voice)
    config = {
        "response_modalities": ["AUDIO"],
        "speech_config": {
            "voice_config": {"prebuilt_voice_config": {"voice_name": voice_name}},
        },
    }
    return config, voice_name


def _tts_models() -> list[str]:
    """Gemini's free-tier TTS quota is a hard per-model daily cap (observed:
    10 requests/day for gemini-2.5-flash-tts) shared by every TTS caller
    (lecture/corpus/vocab/podcast/article audio). The quota is tracked per
    model, so a same-shape fallback model is a genuinely separate bucket.
    Only a RESOURCE_EXHAUSTED (429) falls through to the next model — any
    other APIError is the same regardless of model, so it is raised
    immediately instead of burning a second call."""
    models = [settings.GEMINI_MODEL_TTS]
    if settings.GEMINI_MODEL_TTS_FALLBACK and settings.GEMINI_MODEL_TTS_FALLBACK not in models:
        models.append(settings.GEMINI_MODEL_TTS_FALLBACK)
    return models


def synthesize_korean_tts(text_en: str, voice: str = "ko-female-1") -> tuple[bytes, bytes, int]:
    """Returns (opus_bytes, aac_bytes, duration_sec). Raises RuntimeError on
    any failure (missing key, empty/blocked response, ffmpeg error) — the
    caller (a Celery task) turns that into a job.failed row, same as every
    other AI-backed task in this codebase.

    A long single-shot input (the podcast script — a whole lesson's
    vocab+grammar, easily several thousand characters) reliably 500s the
    native TTS endpoint; short callers (one word/sentence) never do. Text is
    chunked at sentence boundaries and the raw PCM concatenated before ONE
    transcode, so long scripts get the same reliability short callers have.
    For real article text (paragraph pauses, retries, progress) use
    synthesize_article_tts instead."""
    if not settings.GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is not set")
    text_en = text_en.strip()
    if not text_en:
        raise RuntimeError("empty text_en")

    client = _get_client()
    config, voice_name = _tts_config(voice)
    models_to_try = _tts_models()
    chunks = _split_for_tts(text_en, _MAX_TTS_CHARS)
    pcm_parts: list[bytes] = []
    sample_rate = 24000
    print(f"[tts] chars={len(text_en)} chunks={len(chunks)} voice={voice_name}", flush=True)
    for chunk in chunks:
        pcm, sample_rate = _synthesize_chunk_pcm(client, chunk, config, models_to_try)
        pcm_parts.append(pcm)

    return transcode_pcm(b"".join(pcm_parts), sample_rate)


# ------------------------------------------------------ article read-aloud --
# Paragraph-aligned chunks of ~1200 chars: small enough that one bad
# request costs little and the voice does not drift over a very long input,
# large enough to keep the request count (= quota) low.
_ARTICLE_CHUNK_CHARS = 1200
_ARTICLE_MAX_CHARS = 8000  # ~ a 20-minute read; beyond this the tail is not voiced
_PAUSE_AFTER_PARAGRAPH_MS = 700
_PAUSE_AFTER_SENTENCE_MS = 250
_CHUNK_RETRY_DELAYS_SEC = (2.0, 6.0)


def plan_article_chunks(
    text: str, max_chars: int = _ARTICLE_CHUNK_CHARS, max_total: int = _ARTICLE_MAX_CHARS
) -> list[tuple[str, int]]:
    """text (one paragraph per line) -> [(chunk_text, pause_after_ms)].

    Chunks end on a paragraph boundary whenever possible, so the silence
    inserted between chunks is a real paragraph pause; paragraphs inside one
    chunk are separated by a blank line (the model's own pacing). A single
    paragraph longer than max_chars is split at sentence boundaries and
    gets the shorter sentence pause between its pieces. `max_total` caps the
    characters voiced (the tail of a very long text is dropped)."""
    paragraphs = [p.strip() for p in text.splitlines() if p.strip()]
    chunks: list[tuple[str, int]] = []
    current: list[str] = []
    size = 0
    total = 0

    def flush(pause_ms: int) -> None:
        nonlocal current, size
        if current:
            chunks.append(("\n\n".join(current), pause_ms))
            current, size = [], 0

    for para in paragraphs:
        if total + len(para) > max_total and chunks:
            break
        total += len(para)
        if len(para) > max_chars:
            flush(_PAUSE_AFTER_PARAGRAPH_MS)
            pieces = _split_for_tts(para, max_chars)
            for i, piece in enumerate(pieces):
                last = i == len(pieces) - 1
                chunks.append((piece, _PAUSE_AFTER_PARAGRAPH_MS if last else _PAUSE_AFTER_SENTENCE_MS))
            continue
        if current and size + len(para) + 2 > max_chars:
            flush(_PAUSE_AFTER_PARAGRAPH_MS)
        current.append(para)
        size += len(para) + 2
    flush(0)
    if chunks:
        chunks[-1] = (chunks[-1][0], 0)
    return chunks


def _silence_pcm(ms: int, sample_rate: int) -> bytes:
    return b"\x00" * (int(sample_rate * ms / 1000) * 2)  # 16-bit mono


def synthesize_article_tts(
    text: str,
    voice: str = "ko-female-1",
    on_progress: Callable[[int, int], None] | None = None,
) -> tuple[bytes, bytes, int]:
    """Read a whole news article aloud. Differences from synthesize_korean_tts:
    paragraph-aligned chunking, real silence between chunks (so paragraph
    breaks are audible instead of being flattened into one run-on blob),
    per-chunk retry on transient Gemini errors (a 5xx on chunk 4 used to
    throw away chunks 1-3 and their quota), and an `on_progress(done,
    total)` callback so the UI can show "2/4" instead of a bare spinner.
    Returns (opus_bytes, aac_bytes, duration_sec)."""
    if not settings.GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is not set")
    plan = plan_article_chunks(text)
    if not plan:
        raise RuntimeError("empty text_en")

    client = _get_client()
    config, voice_name = _tts_config(voice)
    models_to_try = _tts_models()
    print(
        f"[tts] article chars={len(text)} chunks={len(plan)} chunk_lens={[len(c) for c, _ in plan]} voice={voice_name}",
        flush=True,
    )
    if on_progress:
        on_progress(0, len(plan))

    pcm_parts: list[bytes] = []
    sample_rate = 24000
    for idx, (chunk, pause_ms) in enumerate(plan):
        attempt = 0
        while True:
            try:
                pcm, sample_rate = _synthesize_chunk_pcm(client, chunk, config, models_to_try)
                break
            except TransientTTSError:
                if attempt >= len(_CHUNK_RETRY_DELAYS_SEC):
                    raise
                time.sleep(_CHUNK_RETRY_DELAYS_SEC[attempt])
                attempt += 1
        pcm_parts.append(pcm)
        if pause_ms:
            pcm_parts.append(_silence_pcm(pause_ms, sample_rate))
        if on_progress:
            on_progress(idx + 1, len(plan))

    return transcode_pcm(b"".join(pcm_parts), sample_rate)


# ------------------------------------------------- Google Chirp 3 HD (primary)
# Chirp is cheap per character and its request limit (5,000 bytes) is enforced
# by google_tts.CHUNK_CHARS, so a longer read-aloud cap than Gemini's is fine.
_CHIRP_ARTICLE_MAX_CHARS = 12000


def chirp_enabled() -> bool:
    """True when the TTS_GG_Chirp credential is present in the environment."""
    return google_tts.is_configured()


def chirp_spec() -> str:
    """Voice + pace id (e.g. "gc3-iapetus-r85") for cache keys."""
    return google_tts.spec()


def describe_error(exc: BaseException) -> str:
    """One-line, log-safe description of a failure. Never includes the
    credential: it travels in a request header, not in any exception text."""
    text = str(exc).strip()
    return f"{type(exc).__name__}: {text}"[:400] if text else type(exc).__name__


def _chirp_chunk_pcm(text: str) -> tuple[bytes, int]:
    """One Chirp request; a retryable failure is mapped onto TransientTTSError
    so the same retry loop as the Gemini path applies. A non-retryable
    GoogleTTSError is already a RuntimeError and simply propagates."""
    try:
        return google_tts.synthesize_pcm(text)
    except google_tts.GoogleTTSTransient as exc:
        raise TransientTTSError(str(exc)) from exc


def _retry_transient(
    fn: Callable[[str], tuple[bytes, int]], text: str, delays: tuple[float, ...] | None = None
) -> tuple[bytes, int]:
    delays = _CHUNK_RETRY_DELAYS_SEC if delays is None else delays
    attempt = 0
    while True:
        try:
            return fn(text)
        except TransientTTSError:
            if attempt >= len(delays):
                raise
            time.sleep(delays[attempt])
            attempt += 1


def _join_pcm(parts: list[tuple[bytes, int, int]]) -> tuple[bytes, int]:
    """[(pcm, sample_rate, pause_after_ms)] -> one PCM stream with the pauses
    inserted as silence. All chunks come from one voice, so one sample rate;
    a mismatch would garble the join, so it is an error, not a shrug."""
    rates = {rate for _, rate, _ in parts}
    if len(rates) != 1:
        raise RuntimeError(f"Google TTS returned mixed sample rates {sorted(rates)}")
    rate = rates.pop()
    out: list[bytes] = []
    for pcm, _rate, pause_ms in parts:
        out.append(pcm)
        if pause_ms:
            out.append(_silence_pcm(pause_ms, rate))
    return b"".join(out), rate


def synthesize_article_chirp(
    text: str, on_progress: Callable[[int, int], None] | None = None
) -> tuple[bytes, bytes, int]:
    """Read a whole article aloud with Google Chirp 3 HD: same paragraph-aligned
    plan, real silence between chunks, per-chunk retry of transient errors and
    progress callback as the Gemini path, but ~900-character chunks (the
    request limit is in bytes). Raises RuntimeError on any failure — the
    caller (the Celery task) decides whether to fall back to Gemini; this never
    mixes two voices inside one recording."""
    if not google_tts.is_configured():
        raise RuntimeError("TTS_GG_Chirp is not set")
    plan = plan_article_chunks(text, google_tts.CHUNK_CHARS, _CHIRP_ARTICLE_MAX_CHARS)
    if not plan:
        raise RuntimeError("empty text_en")
    print(
        f"[tts] article provider=google-chirp spec={google_tts.spec()} chars={len(text)} chunks={len(plan)}",
        flush=True,
    )
    if on_progress:
        on_progress(0, len(plan))

    parts: list[tuple[bytes, int, int]] = []
    for idx, (chunk, pause_ms) in enumerate(plan):
        pcm, rate = _retry_transient(_chirp_chunk_pcm, chunk)
        parts.append((pcm, rate, pause_ms))
        if on_progress:
            on_progress(idx + 1, len(plan))

    pcm_all, rate = _join_pcm(parts)
    return transcode_pcm(pcm_all, rate)


# ------------------------------------------- read-along (timed) article audio --
# The same two voices, but planned sentence by sentence so the reader can
# highlight what is being said (see app/services/read_along.py). The clip
# length of every request is known exactly, which is where the timeline gets
# its accuracy. Nothing here changes how a single request is made or retried.
_CHIRP_PACK_CHARS = 240  # ~2-3 news sentences per Chirp request
_CHIRP_SENTENCE_GAP_MS = 150  # extra silence between requests inside a paragraph


def _synthesize_timed(
    chunks: list[read_along.Chunk],
    synth_one: Callable[[str], tuple[bytes, int]],
    on_progress: Callable[[int, int], None] | None,
) -> tuple[bytes, int, list[float], list[float]]:
    """Run the planned chunks one after the other. Returns (pcm of the whole
    article with the planned silences in it, sample rate, start time of every
    chunk in ms, length of every chunk's speech in ms) — the last two measured
    from the samples, so they are exact."""
    if on_progress:
        on_progress(0, len(chunks))
    parts: list[bytes] = []
    starts: list[float] = []
    speech: list[float] = []
    rate = 0
    samples = 0
    for idx, chunk in enumerate(chunks):
        pcm, chunk_rate = synth_one(chunk.text)
        if not rate:
            rate = chunk_rate
        elif chunk_rate != rate:
            raise RuntimeError(f"TTS returned mixed sample rates {sorted({rate, chunk_rate})}")
        n = len(pcm) // 2  # 16-bit mono
        starts.append(samples * 1000.0 / rate)
        speech.append(n * 1000.0 / rate)
        parts.append(pcm[: n * 2])
        samples += n
        if chunk.pause_after_ms:
            silence = int(rate * chunk.pause_after_ms / 1000)
            parts.append(b"\x00" * (silence * 2))
            samples += silence
        if on_progress:
            on_progress(idx + 1, len(chunks))
    return b"".join(parts), rate, starts, speech


def synthesize_article_chirp_timed(
    units: list[read_along.Unit], on_progress: Callable[[int, int], None] | None = None
) -> tuple[bytes, bytes, int, dict]:
    """synthesize_article_chirp, planned per sentence. Returns (opus, aac,
    duration_sec, timings). Raises RuntimeError on any failure; the caller
    decides whether to fall back (never mixes two voices in one recording)."""
    if not google_tts.is_configured():
        raise RuntimeError("TTS_GG_Chirp is not set")
    chunks = read_along.plan_chunks(
        units,
        pack_to=_CHIRP_PACK_CHARS,
        split_over=google_tts.CHUNK_CHARS,
        max_total=_CHIRP_ARTICLE_MAX_CHARS,
        sentence_gap_ms=_CHIRP_SENTENCE_GAP_MS,
        paragraph_gap_ms=_PAUSE_AFTER_PARAGRAPH_MS,
        cross_paragraph=False,
    )
    if not chunks:
        raise RuntimeError("empty text_en")
    print(
        f"[tts] article provider=google-chirp spec={google_tts.spec()} units={len(units)} chunks={len(chunks)} timed=1",
        flush=True,
    )
    pcm, rate, starts, speech = _synthesize_timed(
        chunks, lambda text: _retry_transient(_chirp_chunk_pcm, text), on_progress
    )
    timings = read_along.build_timeline(units, chunks, starts, speech)
    opus, aac, dur = transcode_pcm(pcm, rate)
    return opus, aac, dur, timings


def synthesize_article_tts_timed(
    units: list[read_along.Unit],
    voice: str = "ko-female-1",
    on_progress: Callable[[int, int], None] | None = None,
) -> tuple[bytes, bytes, int, dict]:
    """synthesize_article_tts (Gemini), planned per sentence but packed into
    the same large paragraph-aligned chunks as before — Gemini's daily quota is
    small, so its request count must not grow. Timing is therefore coarser
    here (anchored every ~1,200 characters) than with Chirp."""
    if not settings.GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is not set")
    chunks = read_along.plan_chunks(
        units,
        pack_to=_ARTICLE_CHUNK_CHARS,
        split_over=_ARTICLE_CHUNK_CHARS,
        max_total=_ARTICLE_MAX_CHARS,
        sentence_gap_ms=_PAUSE_AFTER_SENTENCE_MS,
        paragraph_gap_ms=_PAUSE_AFTER_PARAGRAPH_MS,
        cross_paragraph=True,
    )
    if not chunks:
        raise RuntimeError("empty text_en")
    client = _get_client()
    config, voice_name = _tts_config(voice)
    models_to_try = _tts_models()
    print(
        f"[tts] article chars={sum(len(c.text) for c in chunks)} chunks={len(chunks)} "
        f"chunk_lens={[len(c.text) for c in chunks]} voice={voice_name} timed=1",
        flush=True,
    )
    pcm, rate, starts, speech = _synthesize_timed(
        chunks,
        lambda text: _retry_transient(lambda t: _synthesize_chunk_pcm(client, t, config, models_to_try), text),
        on_progress,
    )
    timings = read_along.build_timeline(units, chunks, starts, speech)
    opus, aac, dur = transcode_pcm(pcm, rate)
    return opus, aac, dur, timings


def _synthesize_korean_chirp(text: str) -> tuple[bytes, bytes, int]:
    chunks = _split_for_tts(text, google_tts.CHUNK_CHARS)
    parts = []
    for chunk in chunks:
        pcm, rate = _retry_transient(_chirp_chunk_pcm, chunk)
        parts.append((pcm, rate, 0))
    print(f"[tts] chars={len(text)} chunks={len(chunks)} provider=google-chirp spec={google_tts.spec()}", flush=True)
    pcm_all, rate = _join_pcm(parts)
    return transcode_pcm(pcm_all, rate)


# ------------------------------------------ bilingual lecture (Chirp, primary)
_LECTURE_MAX_CHARS = 9000  # the script lint's own ceiling (podcast_script.script_problems)
_LECTURE_SPLIT_GAP_MS = 200  # between two requests of one long run


def lecture_spec() -> str:
    """Id of the two voices + paces a lecture is voiced with (cache keys)."""
    return google_tts.lecture_spec()


def plan_lecture(script: str, max_chars: int = _LECTURE_MAX_CHARS) -> list[tuple[str, str, int]]:
    """script -> [(language, text, silence_after_ms)], one entry per Chirp
    request: the script cut where the language changes, long runs cut again at
    sentence boundaries so every request stays inside the byte limit. Text past
    `max_chars` is not voiced (a story lecture of several parts asks for more)."""
    return [(lang, text, pause) for lang, text, pause, _where in _plan_lecture_at(script, max_chars)]


def _plan_lecture_at(script: str, max_chars: int = _LECTURE_MAX_CHARS) -> list[tuple[str, str, int, tuple[int, int]]]:
    """`plan_lecture`, each entry with (line, run) of the script it comes from."""
    plan: list[tuple[str, str, int, tuple[int, int]]] = []
    for run in lecture_voice.split_runs(script[:max_chars]):
        where = (run.line, run.run)
        if len(run.text) <= google_tts.CHUNK_CHARS:
            plan.append((run.lang, run.text, run.pause_after_ms, where))
            continue
        pieces = _split_for_tts(run.text, google_tts.CHUNK_CHARS)
        for i, piece in enumerate(pieces):
            last = i == len(pieces) - 1
            plan.append((run.lang, piece, run.pause_after_ms if last else _LECTURE_SPLIT_GAP_MS, where))
    return plan


# One slot every `gap` seconds, counted across every worker process and every lecture at
# once (Redis keeps the time of the next free slot). Returns how long the caller waits.
_SLOT_LUA = """
local t = redis.call('TIME')
local now = tonumber(t[1]) + tonumber(t[2]) / 1000000
local nxt = tonumber(redis.call('GET', KEYS[1]) or '0')
local start = now
if nxt > now then start = nxt end
redis.call('SET', KEYS[1], tostring(start + tonumber(ARGV[1])), 'EX', 300)
return tostring(start - now)
"""
_SLOT_KEY = "tts:chirp:next-slot"
_slot_script = None


def _shared_slot(gap: float) -> float:
    """Seconds to wait for the next free Chirp slot in the whole app. Raises when Redis cannot be reached."""
    global _slot_script
    if _slot_script is None:
        from app.core.redis_client import sync_redis

        _slot_script = sync_redis.register_script(_SLOT_LUA)
    return float(_slot_script(keys=[_SLOT_KEY], args=[gap]))


class _Pacer:
    """Keeps Chirp requests at least 60/per_minute seconds apart. Google lets a project send 200
    Chirp 3 HD requests a minute, so two lectures voiced at the same time (two worker processes)
    share one allowance through Redis (`shared`); when Redis cannot be reached each job paces
    itself, and the words and passages other learners ask for in the meantime still fit."""

    def __init__(self, per_minute: float, shared: Callable[[float], float] | None = None):
        self._gap = 60.0 / per_minute if per_minute and per_minute > 0 else 0.0
        self._shared = shared
        self._lock = threading.Lock()
        self._next = 0.0

    def wait(self) -> None:
        if not self._gap:
            return
        delay = None
        if self._shared is not None:
            try:
                delay = self._shared(self._gap)
            except Exception:  # noqa: BLE001 - no Redis is not a reason to lose the lecture
                print("[tts] lecture: shared pacing unavailable; pacing this job alone", flush=True)
                self._shared = None
        if delay is None:
            with self._lock:
                now = time.monotonic()
                start = max(now, self._next)
                self._next = start + self._gap
            delay = start - now
        if delay > 0:
            time.sleep(delay)


def _lecture_request(
    lang: str, voices: dict[str, str], client=None, pacer: _Pacer | None = None
) -> Callable[[str], tuple[bytes, int]]:
    """The one-request function for a language, so the shared retry loop can
    drive it (from several threads at once: `voices` is only changed under a lock).
    The Vietnamese voice is derived (same persona in vi-VN) unless configured,
    so it is the one that can turn out not to exist: when Google refuses it,
    a Vietnamese Chirp voice that does exist is picked once and used for the
    rest of the lecture."""
    rate = google_tts.speaking_rate() if lang == lecture_voice.KO else google_tts.vi_speaking_rate()
    swap = threading.Lock()

    def send(text: str, voice: str) -> tuple[bytes, int]:
        if pacer is not None:
            pacer.wait()  # every attempt counts, a retry too
        return google_tts.synthesize_pcm(text, client=client, voice=voice, rate=rate)

    def one(text: str) -> tuple[bytes, int]:
        used = voices[lang]
        try:
            return send(text, used)
        except google_tts.GoogleTTSTransient as exc:
            raise TransientTTSError(str(exc)) from exc
        except google_tts.GoogleTTSError as exc:
            if lang != lecture_voice.VI:
                raise
            with swap:
                if voices[lang] == used:  # nobody has replaced it yet
                    replacement = google_tts.pick_vi_voice(used)
                    if not replacement:
                        raise
                    print(f"[tts] vi voice {used} refused ({describe_error(exc)}); using {replacement}", flush=True)
                    voices[lang] = replacement
                replacement = voices[lang]
            try:
                return send(text, replacement)
            except google_tts.GoogleTTSTransient as again:
                raise TransientTTSError(str(again)) from again

    return one


# a 429 from Google means the minute's allowance is spent: wait for part of the next minute
_LECTURE_RETRY_DELAYS_SEC = (2.0, 6.0, 15.0, 30.0)


def synthesize_lecture_chirp(
    script: str,
    on_progress: Callable[[int, int], None] | None = None,
    max_chars: int = _LECTURE_MAX_CHARS,
    timeline_out: list[list[int]] | None = None,
) -> tuple[bytes, bytes, int]:
    """Voice a Vietnamese+Korean lecture with Google Chirp 3 HD: Hangul with
    the Korean voice (slow, for shadowing), everything else with the
    Vietnamese voice, silence between runs, one transcode at the end. Chirp
    is a plain text-to-speech engine, so — unlike Gemini's — it never mistakes
    a line of the lecture for a task to answer. Raises RuntimeError on any
    failure; the Celery task decides about the Gemini fallback, and the two
    engines are never mixed inside one recording.

    A lecture is hundreds of short phrases. Each distinct phrase is voiced once, a few at a
    time over kept-open connections (settings.TTS_LECTURE_WORKERS), but never faster than
    settings.TTS_LECTURE_RPM a minute; the pieces are joined in the script's order.
    `on_progress(done, total)` counts distinct phrases and is only called from the calling
    thread (it may use a database session)."""
    if not google_tts.is_configured():
        raise RuntimeError("TTS_GG_Chirp is not set")
    placed = _plan_lecture_at(script, max_chars)
    plan = [(lang, text, pause) for lang, text, pause, _where in placed]
    if not plan:
        raise RuntimeError("empty lecture script")
    voices = {lecture_voice.KO: google_tts.voice_name(), lecture_voice.VI: google_tts.vi_voice_name()}
    phrases = list(dict.fromkeys((lang, text) for lang, text, _pause in plan))  # a repeated phrase is voiced once
    n_ko = sum(1 for lang, _t in phrases if lang == lecture_voice.KO)
    workers = max(1, min(int(settings.TTS_LECTURE_WORKERS), len(phrases)))
    print(
        f"[tts] lecture provider=google-chirp spec={google_tts.lecture_spec()} chars={len(script)} "
        f"requests={len(plan)} distinct={len(phrases)} (ko={n_ko} vi={len(phrases) - n_ko}) "
        f"workers={workers} max_per_minute={settings.TTS_LECTURE_RPM}",
        flush=True,
    )
    if on_progress:
        on_progress(0, len(phrases))

    pacer = _Pacer(settings.TTS_LECTURE_RPM, _shared_slot)
    # Each distinct phrase's PCM goes straight into a temporary file, as (offset, length, rate): a
    # 30-minute lecture is ~95 MB of PCM, which must not sit in this process (nor be joined into a
    # second copy) inside a 700 MB worker.
    spool = tempfile.TemporaryFile()
    heard: dict[tuple[str, str], tuple[int, int, int]] = {}
    with google_tts.new_client(workers) as client:
        senders = {lang: _lecture_request(lang, voices, client, pacer) for lang in voices}

        def voice_phrase(key: tuple[str, str]) -> tuple[bytes, int]:
            lang, text = key
            return _retry_transient(senders[lang], text, _LECTURE_RETRY_DELAYS_SEC)

        with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="lecture-tts") as pool:
            futures = {pool.submit(voice_phrase, key): key for key in phrases}
            try:
                for future in as_completed(futures):
                    pcm, phrase_rate = future.result()
                    # pop: a finished Future keeps its result alive for as long as `futures` holds it
                    heard[futures.pop(future)] = (spool.tell(), len(pcm), phrase_rate)
                    spool.write(pcm)
                    del pcm, future
                    if on_progress:
                        on_progress(len(heard), len(phrases))
            except BaseException:
                pool.shutdown(wait=True, cancel_futures=True)  # the phrases not started are dropped
                spool.close()
                raise

    try:
        rates = {phrase_rate for _offset, _length, phrase_rate in heard.values()}
        if len(rates) != 1:
            raise RuntimeError(f"Google TTS returned mixed sample rates {sorted(rates)}")
        rate = rates.pop()
        with tempfile.TemporaryFile() as joined:
            starts: list[list[int]] = []  # [line, run, ms]: when each run of the script starts
            for (lang, text, pause_ms), (_l, _t, _p, (line, run)) in zip(plan, placed):
                if not starts or starts[-1][:2] != [line, run]:
                    starts.append([line, run, (joined.tell() // 2) * 1000 // rate])  # 16-bit mono
                offset, length, _rate = heard[(lang, text)]
                spool.seek(offset)
                joined.write(spool.read(length))
                if pause_ms:
                    joined.write(_silence_pcm(pause_ms, rate))
            size = joined.tell()
            joined.flush()
            if timeline_out is not None:
                timeline_out.extend(starts)
            return transcode_pcm_file(joined, size, rate)
    finally:
        spool.close()


# ------------------------------------------------ recorded dialogues (Chirp, two voices)
_DIALOGUE_GAP_MS = 650  # between two speakers
_DIALOGUE_SPLIT_GAP_MS = 150


def dialogue_spec() -> str:
    """Id of the two voices + pace a dialogue is recorded with (cache keys)."""
    return google_tts.dialogue_spec()


def synthesize_dialogue_azure(
    turns: list[tuple[str, str]], on_progress: Callable[[int, int], None] | None = None
) -> tuple[bytes, bytes, int]:
    """The same listening dialogue as `synthesize_dialogue_chirp`, voiced by Azure: speaker "F" is
    the female voice, "M" / "N" the male one. One request per turn (cut at sentence ends when a
    turn is long), a short silence between speakers, one transcode at the end. Raises on any
    failure: the caller falls back to Chirp, then Gemini."""
    if not azure_tts.is_configured():
        raise RuntimeError("Azure Speech is not configured")
    turns = [(who, text.strip()) for who, text in turns if text.strip()]
    if not turns:
        raise RuntimeError("empty dialogue")
    print(f"[tts] dialogue provider=azure spec={azure_tts.dialogue_spec()} turns={len(turns)}", flush=True)
    if on_progress:
        on_progress(0, len(turns))
    parts: list[tuple[bytes, int, int]] = []
    for idx, (who, text) in enumerate(turns):
        voice = "ko-female-1" if who == "F" else "ko-male-1"
        pieces = _split_for_tts(text, 400) if len(text) > 400 else [text]
        for j, piece in enumerate(pieces):
            pcm, hz = _retry_transient(lambda t, v=voice: _azure_chunk_pcm(t, v), piece)
            last_piece = j == len(pieces) - 1
            pause = (_DIALOGUE_GAP_MS if idx < len(turns) - 1 else 0) if last_piece else _DIALOGUE_SPLIT_GAP_MS
            parts.append((pcm, hz, pause))
        if on_progress:
            on_progress(idx + 1, len(turns))
    pcm_all, hz = _join_pcm(parts)
    return transcode_pcm(pcm_all, hz)


def synthesize_dialogue_chirp(
    turns: list[tuple[str, str]], on_progress: Callable[[int, int], None] | None = None
) -> tuple[bytes, bytes, int]:
    """A listening-exam dialogue: `turns` is [(speaker, text)], speaker "F" (female
    voice), "M" or "N" (the Korean male voice; N is the narrator). One request per turn,
    natural pace, a short silence between speakers, one transcode at the end. Raises
    RuntimeError on any failure — the caller decides about the Gemini fallback."""
    if not google_tts.is_configured():
        raise RuntimeError("TTS_GG_Chirp is not set")
    turns = [(who, text.strip()) for who, text in turns if text.strip()]
    if not turns:
        raise RuntimeError("empty dialogue")
    voices = {"M": google_tts.voice_name(), "N": google_tts.voice_name(), "F": google_tts.female_voice_name()}
    rate = google_tts.exam_rate()

    def sender(who: str) -> Callable[[str], tuple[bytes, int]]:
        def one(text: str) -> tuple[bytes, int]:
            try:
                return google_tts.synthesize_pcm(text, voice=voices[who], rate=rate)
            except google_tts.GoogleTTSTransient as exc:
                raise TransientTTSError(str(exc)) from exc
            except google_tts.GoogleTTSError as exc:
                replacement = google_tts.pick_ko_voice(voices[who], "FEMALE" if who == "F" else "MALE")
                if not replacement:
                    raise
                print(f"[tts] dialogue voice {voices[who]} refused ({describe_error(exc)}); using {replacement}", flush=True)
                voices[who] = replacement
                try:
                    return google_tts.synthesize_pcm(text, voice=replacement, rate=rate)
                except google_tts.GoogleTTSTransient as again:
                    raise TransientTTSError(str(again)) from again

        return one

    print(f"[tts] dialogue provider=google-chirp spec={google_tts.dialogue_spec()} turns={len(turns)}", flush=True)
    if on_progress:
        on_progress(0, len(turns))
    parts: list[tuple[bytes, int, int]] = []
    for idx, (who, text) in enumerate(turns):
        pieces = _split_for_tts(text, google_tts.CHUNK_CHARS) if len(text) > google_tts.CHUNK_CHARS else [text]
        for j, piece in enumerate(pieces):
            pcm, hz = _retry_transient(sender(who if who in voices else "N"), piece)
            last_piece = j == len(pieces) - 1
            pause = (_DIALOGUE_GAP_MS if idx < len(turns) - 1 else 0) if last_piece else _DIALOGUE_SPLIT_GAP_MS
            parts.append((pcm, hz, pause))
        if on_progress:
            on_progress(idx + 1, len(turns))
    pcm_all, hz = _join_pcm(parts)
    return transcode_pcm(pcm_all, hz)


def _azure_chunk_pcm(text: str, voice: str) -> tuple[bytes, int]:
    try:
        return azure_tts.synthesize_pcm(text, voice)
    except azure_tts.AzureTTSTransient as exc:
        raise TransientTTSError(str(exc)) from exc


def synthesize_korean_with_provider(text_en: str, voice: str = "ko-female-1") -> tuple[bytes, bytes, int, str]:
    """Same as `synthesize_korean_tts_chirp_first`, and also says who voiced it: "azure" (when
    configured, the Korean voice with the NIKL pronunciation table), "chirp" or "gemini"
    (the fallback). A caller that files the recording keeps this, so a fallback one is replaced by
    a Chirp one the next time the text is asked for."""
    text = text_en.strip()
    if not text:
        raise RuntimeError("empty text_en")
    if azure_tts.is_configured():
        try:
            pcm, rate = _retry_transient(lambda t: _azure_chunk_pcm(t, voice), text)
            print(f"[tts] chars={len(text)} provider=azure spec={azure_tts.spec()}", flush=True)
            return (*transcode_pcm(pcm, rate), "azure")
        except Exception as exc:  # noqa: BLE001 - Azure down: Chirp, so the learner still hears it
            print(f"[tts] azure failed ({describe_error(exc)}); falling back to Chirp", flush=True)
    if not google_tts.is_configured():
        return (*synthesize_korean_tts(text, voice), "gemini")
    try:
        return (*_synthesize_korean_chirp(text), "chirp")
    except Exception as exc:  # noqa: BLE001 - any Chirp failure falls back rather than losing the audio
        reason = describe_error(exc)
        print(f"[tts] google-chirp failed ({reason}); falling back to Gemini", flush=True)
        try:
            return (*synthesize_korean_tts(text, voice), "gemini")
        except RuntimeError as gem_exc:
            raise RuntimeError(f"Giọng đọc gặp lỗi ({reason}); giọng dự phòng cũng lỗi: {gem_exc}") from gem_exc


def synthesize_korean_tts_chirp_first(text_en: str, voice: str = "ko-female-1") -> tuple[bytes, bytes, int]:
    """Korean-ONLY text (a lesson passage, one listening sentence, one word):
    Google Chirp 3 HD when configured, Gemini when it is not or when Chirp
    fails. Not for the podcast script — that mixes in Vietnamese, which a
    ko-KR voice cannot read; it uses synthesize_lecture_chirp."""
    return synthesize_korean_with_provider(text_en, voice)[:3]

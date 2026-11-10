"""Audio module — the ONE fully-wired example of the SDD's async-job
pattern end to end: client POSTs -> 202 + job_id -> Celery task runs ->
Redis publishes progress -> SSE streams it -> row lands in
audio.lecture_audio (or audio.corpus_item_audio). Every other AI-backed
endpoint (writing grading, exam ingestion, placement scoring) should
follow this exact shape.

Two resources share this pattern:
- lecture audio: whole-lesson narration, gated behind login (Job.owner_id
  is required) — matches the existing /lessons/{id} learner-progress flow.
- corpus-item audio: one listening-screen sentence. Playback itself needs
  no account, same as GET /corpus/items — only the "đã nhớ/chưa nhớ"
  progress buttons require login, not hearing a sentence read aloud.

Both are content-addressed (`cache_key = f"{id}:{voice}:{prompt_version}"`)
so a repeat request short-circuits to the already-succeeded job instead of
re-billing Gemini, and both are served back out through the GET streaming
routes below — the frontend just points an <audio> tag at `opus_path`/
`aac_path`, no separate fetch-then-blob dance needed.
"""
import hashlib
import logging
import re
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from starlette.concurrency import run_in_threadpool
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import _problem, ensure_lesson_open, get_current_profile, get_optional_profile
from app.core import ratelimit
from app.core.config import settings
from app.db import get_db
from app.models import (
    CorpusItem,
    CorpusItemAudio,
    GrammarPoint,
    Job,
    LectureAudio,
    Lesson,
    Profile,
    TextAudio,
    VocabItem,
    VocabItemAudio,
)
from app.schemas import (
    CorpusAudioRequest,
    JobAccepted,
    LectureAudioRequest,
    PodcastRequest,
    TextAudioRequest,
    VocabAudioRequest,
)
from app.services import azure_tts, audio_keys, audio_store, job_events, landing_audio, lesson_audio, podcast_script, text_audio, tts
from app.workers.tasks import (
    generate_content_podcast,
    generate_corpus_audio,
    generate_exercise_audio,
    generate_lecture_audio,
    generate_text_audio,
    generate_vocab_audio,
)

router = APIRouter(prefix="/lessons", tags=["audio"])
corpus_router = APIRouter(prefix="/corpus", tags=["audio"])
vocab_router = APIRouter(prefix="/vocab-items", tags=["audio"])
text_router = APIRouter(prefix="/audio", tags=["audio"])
log = logging.getLogger(__name__)

_CACHE_CONTROL = "public, max-age=31536000, immutable"  # cache_key is content-addressed — never changes once written


_RANGE_RE = re.compile(r"bytes=(\d*)-(\d*)")


def _audio_response(request: Request, data: bytes, media_type: str) -> Response:
    """200 with the whole body, or 206 for a `Range: bytes=a-b` request.
    Browsers (iOS/macOS Safari above all) only report a duration, allow
    seeking, and in the worst case only PLAY media from a server that
    answers byte-range requests — without Accept-Ranges a minutes-long
    article recording could not be scrubbed on the iPhone."""
    total = len(data)
    headers = {"Cache-Control": _CACHE_CONTROL, "Accept-Ranges": "bytes"}
    match = _RANGE_RE.fullmatch((request.headers.get("range") or "").strip())
    if match and (match.group(1) or match.group(2)):
        if match.group(1):
            start = int(match.group(1))
            end = int(match.group(2)) if match.group(2) else total - 1
        else:  # "bytes=-N": the last N bytes
            start = max(total - int(match.group(2)), 0)
            end = total - 1
        end = min(end, total - 1)
        if start >= total or start > end:
            return Response(status_code=416, headers={"Content-Range": f"bytes */{total}", "Accept-Ranges": "bytes"})
        headers["Content-Range"] = f"bytes {start}-{end}/{total}"
        return Response(content=data[start : end + 1], status_code=206, media_type=media_type, headers=headers)
    return Response(content=data, media_type=media_type, headers=headers)


async def _spend_word(request: Request) -> None:
    """A new word or sentence recording is about to be made: spend from the allowance."""
    await ratelimit.spend(
        request,
        "word",
        per_client=settings.AUDIO_WORD_PER_CLIENT_HOURLY,
        overall=settings.AUDIO_WORD_ALL_HOURLY,
    )


async def _spend_lecture(request: Request) -> None:
    """A new lecture or dialogue recording is about to be made (Gemini + several TTS calls)."""
    await ratelimit.spend(
        request,
        "lecture",
        per_client=settings.AUDIO_LECTURE_PER_CLIENT_HOURLY,
        overall=settings.AUDIO_LECTURE_ALL_HOURLY,
    )


async def _podcast_cache_key(
    db: AsyncSession,
    owner_kind: str,
    owner_id: str,
    voice: str,
    prompt_version: str,
    vocab_ids: list[int],
    grammar_ids: list[int],
    content_sig: str | None = None,
) -> str:
    """Includes a short hash of the CURRENT vocab/grammar id set so the
    cache naturally busts if an admin adds/removes a word later — unlike
    plain lecture/corpus/vocab audio, a podcast's content can change out
    from under a stable owner id (a lesson/article gets edited in Studio),
    so `{owner_id}:{voice}:{prompt_version}` alone would keep serving a
    stale recording forever.

    A seeded lesson keeps the same ids when its text is edited, so it also passes
    `content_sig` (the seed's content hash): an edited lesson is recorded again."""
    sig_src = "v:" + ",".join(str(i) for i in sorted(vocab_ids)) + "|g:" + ",".join(str(i) for i in sorted(grammar_ids))
    if content_sig:
        sig_src += "|c:" + content_sig
    content_sig = hashlib.sha256(sig_src.encode("utf-8")).hexdigest()[:16]
    return f"podcast:{owner_kind}:{owner_id}:{voice}:{prompt_version}:{content_sig}"


async def _podcast_keys(
    db: AsyncSession,
    owner_kind: str,
    owner_id: str,
    body: PodcastRequest,
    vocab_ids: list[int],
    grammar_ids: list[int],
    content_sig: str | None = None,
) -> tuple[str, str | None, str, str]:
    """(cache_key, fallback_cache_key, prompt_version, mode) of a lecture: the one place its keys are
    built, so asking for a recording and asking whether it exists can never disagree."""
    # The prompt version belongs to the server: bumping podcast_script.PODCAST_VERSION
    # makes every lecture regenerate with the new prompt, whatever an older
    # client still sends in the request body. A lesson (lesson-v5) is voiced from the
    # fixed template script by default, or from Gemini's story on request: each has
    # its own version, so each is stored and reused on its own. Articles are always Gemini.
    if owner_kind == "lesson":
        mode = body.mode
        prompt_version = lesson_audio.TEMPLATE_VERSION if mode == "template" else lesson_audio.STORY_VERSION
    else:
        mode = "story"
        prompt_version = podcast_script.PODCAST_VERSION
    base_key = await _podcast_cache_key(
        db, owner_kind, owner_id, body.voice, prompt_version, vocab_ids, grammar_ids, content_sig
    )
    # With Google Chirp on, the key also carries the two voices' spec: lectures
    # recorded earlier by Gemini do not match and are redone in the Chirp voice,
    # and changing a voice or pace on Railway redoes them again. The plain key is
    # where the worker files a Gemini FALLBACK recording (Chirp failed), so a
    # later play retries Chirp instead of staying on the fallback voice.
    if tts.chirp_enabled():
        return f"{base_key}:{tts.lecture_spec()}", base_key, prompt_version, mode
    return base_key, None, prompt_version, mode


async def _request_podcast(
    db: AsyncSession,
    owner_kind: str,
    owner_id: str,
    body: PodcastRequest,
    request: Request,
    vocab_ids: list[int],
    grammar_ids: list[int],
    content_sig: str | None = None,
    allow_new: bool = True,
) -> JobAccepted:
    """`allow_new` False: only a recording that already exists (or a job already queued or running)
    is handed out; a new recording is refused with 409 before it spends anything."""
    cache_key, fallback_cache_key, prompt_version, mode = await _podcast_keys(
        db, owner_kind, owner_id, body, vocab_ids, grammar_ids, content_sig
    )

    cached = await db.execute(select(LectureAudio).where(LectureAudio.cache_key == cache_key))
    hit = cached.scalar_one_or_none()

    # The recording's own key IS the idempotency key (a header would let a caller queue the
    # same missing recording again and again, each run paying for it).
    idempotency_key = cache_key
    existing_job = await db.execute(
        select(Job).where(Job.type == "generate_content_podcast", Job.idempotency_key == idempotency_key)
    )
    job = existing_job.scalar_one_or_none()
    if job is not None and (
        (job.status not in ("queued", "running", "succeeded") or job_events.abandoned(job))
        # A "succeeded" job whose recording is not in the cache under the key we
        # want NOW: the Gemini fallback was used (Chirp failed), or a voice or
        # pace changed. Run again so Chirp gets another chance — the worker
        # reuses the fallback lecture's script and recording while Chirp is down.
        or (job.status == "succeeded" and hit is None)
    ):
        # A prior attempt with this exact idempotency key ended in "failed"
        # (or another terminal-but-not-usable state). `idempotency_key` has
        # a DB-level unique constraint per job type, so leaving that row in
        # place would permanently wedge every future retry behind an
        # unrelated 500 (IntegrityError on insert) instead of ever trying
        # Gemini again — clear it out so a retry actually retries.
        await db.delete(job)
        await db.flush()
        job = None

    if job is None:
        if not hit and not allow_new:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                detail={"code": "whole_not_recorded", "message": "Bài giảng cả bài chưa có sẵn. Hãy nghe theo từng buổi."},
            )
        if not hit:
            await _spend_lecture(request)
        job = Job(
            type="generate_content_podcast",
            owner_id=None,
            idempotency_key=idempotency_key,
            status="succeeded" if hit else "queued",
            progress=1.0 if hit else 0.0,
            result={
                "cache_key": hit.cache_key,
                "opus_path": hit.opus_path,
                "aac_path": hit.aac_path,
                "duration_sec": hit.duration_sec,
                "script_text": hit.script_text,
                "timeline": hit.timeline,
            }
            if hit
            else None,
        )
        db.add(job)
        await db.commit()
        await db.refresh(job)

        if not hit:
            try:
                generate_content_podcast.delay(
                    str(job.id), owner_kind, owner_id, body.voice, prompt_version, cache_key, fallback_cache_key, mode
                )
            except Exception as exc:  # noqa: BLE001 - the queue (Redis) is unreachable
                # Leave no "queued" job behind that nothing will ever run, and say plainly that
                # the audio queue is down rather than failing with a bare 500.
                logging.getLogger("haru.api").exception("podcast: cannot enqueue job %s", job.id)
                job.status = "failed"
                job.result = {"error": "queue_unavailable"}
                await db.commit()
                raise HTTPException(
                    status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Hàng đợi âm thanh đang tạm ngưng. Thử lại sau ít phút.",
                    headers={"Retry-After": "30"},
                ) from exc

    return JobAccepted(
        job_id=job.id,
        status=job.status,
        poll_url=f"/api/v1/jobs/{job.id}",
        events_url=f"/api/v1/jobs/{job.id}/events",
    )


def _split_cache_filename(filename: str) -> tuple[str, str]:
    """"{cache_key}.opus" / "{cache_key}.aac" -> (cache_key, media_type)."""
    if filename.endswith(".opus"):
        return filename[: -len(".opus")], "audio/ogg; codecs=opus"
    if filename.endswith(".aac"):
        return filename[: -len(".aac")], "audio/aac"
    raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Unsupported audio format")


@router.post("/{lesson_id}/lecture", response_model=JobAccepted, status_code=status.HTTP_202_ACCEPTED)
async def request_lecture_audio(
    lesson_id: str,
    body: LectureAudioRequest,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    profile: Annotated[Profile, Depends(get_current_profile)],
):
    """Content-addressed cache: `cache_key` = f(lesson_id, voice,
    prompt_version). If audio already exists, return it as an
    already-succeeded job instead of re-running Gemini+ffmpeg
    (SDD: "bất biến theo nội dung: khóa cache là hash").
    """
    cache_key = f"{lesson_id}:{body.voice}:{body.prompt_version}"

    cached = await db.execute(select(LectureAudio).where(LectureAudio.cache_key == cache_key))
    hit = cached.scalar_one_or_none()

    idempotency_key = request.headers.get("Idempotency-Key", cache_key)

    existing_job = await db.execute(
        select(Job).where(Job.type == "generate_lecture_audio", Job.idempotency_key == idempotency_key)
    )
    job = existing_job.scalar_one_or_none()
    if job is not None and (job.status not in ("queued", "running", "succeeded") or job_events.abandoned(job)):
        # See _request_podcast's identical comment: a failed row would
        # otherwise permanently block retries behind a unique-constraint 500.
        await db.delete(job)
        await db.flush()
        job = None

    if job is None:
        job = Job(
            type="generate_lecture_audio",
            owner_id=profile.id,
            idempotency_key=idempotency_key,
            status="succeeded" if hit else "queued",
            progress=1.0 if hit else 0.0,
            result={"cache_key": hit.cache_key, "opus_path": hit.opus_path, "duration_sec": hit.duration_sec}
            if hit
            else None,
        )
        db.add(job)
        await db.commit()
        await db.refresh(job)

        if not hit:
            generate_lecture_audio.delay(
                str(job.id), lesson_id, body.text_ko, body.voice, body.prompt_version
            )

    return JobAccepted(
        job_id=job.id,
        status=job.status,
        poll_url=f"/api/v1/jobs/{job.id}",
        events_url=f"/api/v1/jobs/{job.id}/events",
    )


@router.get("/{lesson_id}/lecture-slides")
async def lesson_lecture_slides(
    lesson_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    sitting: Annotated[int | None, Query(ge=1, le=40)] = None,
    profile: Annotated[Profile | None, Depends(get_optional_profile)] = None,
) -> dict:
    """The slides of a lesson's lecture (lesson_audio.build_template_lecture): what each slide holds,
    and for every line of the script the slide it is on and what it brings onto it. With the
    recording's `timeline` ([line, run, ms]) the screen shows each thing when the voice says it.
    `script` is the text the slides were built for: a recording whose script differs (an older
    template) is played without them."""
    lesson = await db.get(Lesson, lesson_id)
    if lesson is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Lesson not found")
    await ensure_lesson_open(db, profile, lesson)
    vocab_rows = (
        (await db.execute(select(VocabItem).where(VocabItem.lesson_id == lesson_id).order_by(VocabItem.id))).scalars().all()
    )
    grammar_rows = (
        (await db.execute(select(GrammarPoint).where(GrammarPoint.lesson_id == lesson_id).order_by(GrammarPoint.id)))
        .scalars()
        .all()
    )
    if not vocab_rows and not grammar_rows:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="This lesson has no lecture")
    if sitting is not None:
        cut = lesson_audio.sitting_source(lesson, vocab_rows, grammar_rows, sitting)
        if cut is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="This lesson has no such sitting")
        source = cut[0]
    else:
        source = lesson_audio.source_from_rows(lesson, vocab_rows, grammar_rows)
    lecture = lesson_audio.build_template_lecture(source)
    return {
        "script": lecture.script,
        "lines": [[ln.slide, ln.show] for ln in lecture.lines],
        "slides": lecture.slides,
    }


@router.post("/{lesson_id}/podcast", response_model=JobAccepted, status_code=status.HTTP_202_ACCEPTED)
async def request_lesson_podcast(
    lesson_id: int,
    body: PodcastRequest,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    profile: Annotated[Profile | None, Depends(get_optional_profile)] = None,
):
    """The lecture of a lesson: by default a fixed script built from the lesson
    (every word and pattern, lesson_audio.build_template_script), or — with
    mode="story" — Gemini's retelling, written in parts when the lesson is long. Either
    way it is voiced by Chirp, stored once and replayed; see
    app.workers.tasks.generate_content_podcast. No login required, same rationale as
    vocab/corpus audio (hearing content is a public read)."""
    lesson = await db.get(Lesson, lesson_id)
    if lesson is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Lesson not found")
    await ensure_lesson_open(db, profile, lesson)  # a paid lesson's lecture costs TTS: only for who holds it
    vocab_rows = (
        (await db.execute(select(VocabItem).where(VocabItem.lesson_id == lesson_id).order_by(VocabItem.id))).scalars().all()
    )
    grammar_rows = (
        (await db.execute(select(GrammarPoint).where(GrammarPoint.lesson_id == lesson_id).order_by(GrammarPoint.id)))
        .scalars()
        .all()
    )
    if not vocab_rows and not grammar_rows:  # the topic review lesson: nothing of its own to read out
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="This lesson has no lecture")
    # The recording is keyed by what the lecture is made of (words, patterns, notes, title),
    # not by the lesson's whole content hash: editing a lesson's exercises or links must not
    # make every lecture be recorded (and paid for) again.
    owner_id = str(lesson_id)
    if body.sitting is not None:
        cut = lesson_audio.sitting_source(lesson, vocab_rows, grammar_rows, body.sitting)
        if cut is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="This lesson has no such sitting")
        source, vocab_rows, grammar_rows = cut
        owner_id = f"{lesson_id}:s{body.sitting}"
    else:
        source = lesson_audio.source_from_rows(lesson, vocab_rows, grammar_rows)
    signature = lesson_audio.source_signature(source)
    return await _request_podcast(
        db,
        "lesson",
        owner_id,
        body,
        request,
        [v.id for v in vocab_rows],
        [g.id for g in grammar_rows],
        content_sig=signature,
        # a whole-lesson lecture is long (a 44-word lesson is ~440 Chirp requests): it is only
        # played when it already exists; a new recording is made per sitting
        allow_new=body.sitting is not None,
    )


@router.get("/{lesson_id}/lecture-status")
async def lesson_lecture_status(
    lesson_id: int,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
    profile: Annotated[Profile | None, Depends(get_optional_profile)] = None,
    voice: str = "ko-female-1",
    mode: str = "template",
):
    """Which lecture recordings of a lesson exist: the whole lesson's, and each sitting's. Looks keys
    up only: no job is made and nothing is spent, so a page can ask before it offers a play button."""
    lesson = await db.get(Lesson, lesson_id)
    if lesson is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Lesson not found")
    await ensure_lesson_open(db, profile, lesson)
    vocab_rows = (
        (await db.execute(select(VocabItem).where(VocabItem.lesson_id == lesson_id).order_by(VocabItem.id))).scalars().all()
    )
    grammar_rows = (
        (await db.execute(select(GrammarPoint).where(GrammarPoint.lesson_id == lesson_id).order_by(GrammarPoint.id)))
        .scalars()
        .all()
    )
    if not vocab_rows and not grammar_rows:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="This lesson has no lecture")

    async def ready(sitting: int | None) -> dict:
        body = PodcastRequest(voice=voice, mode="story" if mode == "story" else "template", sitting=sitting)
        if sitting is None:
            source = lesson_audio.source_from_rows(lesson, vocab_rows, grammar_rows)
            vids, gids, owner = [v.id for v in vocab_rows], [g.id for g in grammar_rows], str(lesson_id)
        else:
            cut = lesson_audio.sitting_source(lesson, vocab_rows, grammar_rows, sitting)
            if cut is None:
                return {}
            source, vr, gr = cut
            vids, gids, owner = [v.id for v in vr], [g.id for g in gr], f"{lesson_id}:s{sitting}"
        key, _fallback, _version, _mode = await _podcast_keys(
            db, "lesson", owner, body, vids, gids, lesson_audio.source_signature(source)
        )
        row = (await db.execute(select(LectureAudio).where(LectureAudio.cache_key == key))).scalar_one_or_none()
        return {"ready": row is not None, "duration_sec": row.duration_sec if row is not None else None}

    sittings = []
    for n in range(1, min(len(getattr(lesson, "sessions", None) or []), 40) + 1):
        info = await ready(n)
        if info:
            sittings.append({"n": n, **info})
    response.headers["Cache-Control"] = "private, max-age=30"
    return {"whole": await ready(None), "sittings": sittings}


@router.post(
    "/{lesson_id}/exercises/{exercise_id}/audio", response_model=JobAccepted, status_code=status.HTTP_202_ACCEPTED
)
async def request_exercise_audio(
    lesson_id: int,
    exercise_id: str,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    profile: Annotated[Profile | None, Depends(get_optional_profile)] = None,
):
    """The recorded dialogue of one listening exercise (or speaking task S4) of a lesson's
    practice set, spoken by a female and a male Chirp voice at a natural pace. Recorded
    the first time it is asked for, then stored and replayed; the recording is shared by
    every lesson that holds the same exercise. No login required (hearing is a public read)."""
    lesson = await db.get(Lesson, lesson_id)
    if lesson is not None:
        await ensure_lesson_open(db, profile, lesson)
    exercise = next((e for e in (lesson.practice or {}).get("items", []) if e.get("id") == exercise_id), None) if lesson else None
    turns = lesson_audio.exercise_turns(exercise) if exercise else None
    if not turns:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="This exercise has no recording")

    base_key = lesson_audio.dialogue_cache_key(exercise_id, turns, "gemini")
    if azure_tts.is_configured():
        # Azure's two voices are the recording; the Chirp one (found under its own old key) is only
        # what plays while Azure is down, and Azure is tried again the next time
        cache_key = lesson_audio.dialogue_cache_key(exercise_id, turns, azure_tts.dialogue_spec())
        fallback_cache_key: str | None = (
            lesson_audio.dialogue_cache_key(exercise_id, turns, tts.dialogue_spec()) if tts.chirp_enabled() else base_key
        )
    elif tts.chirp_enabled():
        cache_key = lesson_audio.dialogue_cache_key(exercise_id, turns, tts.dialogue_spec())
        fallback_cache_key = base_key
    else:
        cache_key, fallback_cache_key = base_key, None

    hit = (await db.execute(select(LectureAudio).where(LectureAudio.cache_key == cache_key))).scalar_one_or_none()
    idempotency_key = cache_key  # see _request_podcast: the recording's key, not a caller's header
    job = (
        await db.execute(select(Job).where(Job.type == "generate_exercise_audio", Job.idempotency_key == idempotency_key))
    ).scalar_one_or_none()
    if job is not None and ((job.status not in ("queued", "running", "succeeded") or job_events.abandoned(job)) or (job.status == "succeeded" and hit is None)):
        await db.delete(job)  # see _request_podcast: a failed or fallback-only job must not wedge the retry
        await db.flush()
        job = None

    if job is None:
        if not hit:
            await _spend_lecture(request)
        job = Job(
            type="generate_exercise_audio",
            owner_id=None,
            idempotency_key=idempotency_key,
            status="succeeded" if hit else "queued",
            progress=1.0 if hit else 0.0,
            result={
                "cache_key": hit.cache_key,
                "opus_path": hit.opus_path,
                "aac_path": hit.aac_path,
                "duration_sec": hit.duration_sec,
            }
            if hit
            else None,
        )
        db.add(job)
        await db.commit()
        await db.refresh(job)
        if not hit:
            generate_exercise_audio.delay(str(job.id), exercise_id, [list(t) for t in turns], cache_key, fallback_cache_key)

    return JobAccepted(
        job_id=job.id,
        status=job.status,
        poll_url=f"/api/v1/jobs/{job.id}",
        events_url=f"/api/v1/jobs/{job.id}/events",
    )


@router.get("/audio/{filename}")
async def stream_lecture_audio(filename: str, request: Request, db: Annotated[AsyncSession, Depends(get_db)]):
    """Serves the bytes behind `LectureAudio.opus_path`/`aac_path` — those
    columns are set to exactly this route at write time (see
    app/workers/tasks.py generate_lecture_audio), so the frontend just
    plays `<audio src={opus_path}>` with no separate fetch-then-blob step.
    """
    cache_key, media_type = _split_cache_filename(filename)
    row = (
        await db.execute(select(LectureAudio).where(LectureAudio.cache_key == cache_key))
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Audio not found")
    ext = "opus" if media_type.startswith("audio/ogg") else "aac"
    # a lecture is tens of MB: the player takes it (and its byte ranges) from the bucket, not through us
    link = await run_in_threadpool(audio_store.signed_redirect_url, row, ext)
    if link:
        return RedirectResponse(link, status_code=status.HTTP_302_FOUND, headers={"Cache-Control": "private, max-age=600"})
    try:
        data = await run_in_threadpool(audio_store.read_row, row, ext)
    except audio_store.StoreError:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail="Audio storage is not reachable; try again") from None
    if not data:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Audio not yet generated")
    return _audio_response(request, data, media_type)


@corpus_router.post("/{corpus_item_id}/audio", response_model=JobAccepted, status_code=status.HTTP_202_ACCEPTED)
async def request_corpus_audio(
    corpus_item_id: str,
    body: CorpusAudioRequest,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Same content-addressed cache-hit-shortcut as lecture audio, but for
    one /listening sentence. No login required — hearing a sentence read
    aloud is a public read like GET /corpus/items; only progress (đã nhớ/
    chưa nhớ) needs an account, so `Job.owner_id` stays null here.

    The sentence that is voiced is the one in the database, whatever `text_ko` says; a new
    recording spends from the hourly allowance (an existing one is free).
    """
    try:
        item_id = uuid.UUID(corpus_item_id)
    except ValueError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Sentence not found") from None
    item = await db.get(CorpusItem, item_id)
    text_ko = audio_keys.speakable(item.text_ko) if item is not None else ""
    if not text_ko:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Sentence not found")
    # with Azure on, a sentence is voiced again once by the Korean voice (its own key), like a word
    version = f"{body.prompt_version}+{azure_tts.spec()}" if azure_tts.is_configured() else body.prompt_version
    cache_key = f"{corpus_item_id}:{body.voice}:{version}"

    cached = await db.execute(select(CorpusItemAudio).where(CorpusItemAudio.cache_key == cache_key))
    hit = cached.scalar_one_or_none()

    idempotency_key = cache_key  # see _request_podcast: the recording's key, not a caller's header

    existing_job = await db.execute(
        select(Job).where(Job.type == "generate_corpus_audio", Job.idempotency_key == idempotency_key)
    )
    job = existing_job.scalar_one_or_none()
    if job is not None and ((job.status not in ("queued", "running", "succeeded") or job_events.abandoned(job)) or (job.status == "succeeded" and hit is None)):
        # See _request_podcast's identical comment: a failed row would
        # otherwise permanently block retries behind a unique-constraint 500.
        await db.delete(job)
        await db.flush()
        job = None

    if job is None:
        if not hit:
            await _spend_word(request)
        job = Job(
            type="generate_corpus_audio",
            owner_id=None,
            idempotency_key=idempotency_key,
            status="succeeded" if hit else "queued",
            progress=1.0 if hit else 0.0,
            result={
                "cache_key": hit.cache_key,
                "opus_path": f"/api/v1/corpus/audio/{hit.cache_key}.opus",
                "aac_path": f"/api/v1/corpus/audio/{hit.cache_key}.aac",
                "duration_sec": hit.duration_sec,
            }
            if hit
            else None,
        )
        db.add(job)
        await db.commit()
        await db.refresh(job)

        if not hit:
            generate_corpus_audio.delay(str(job.id), corpus_item_id, text_ko, body.voice, body.prompt_version, cache_key)

    return JobAccepted(
        job_id=job.id,
        status=job.status,
        poll_url=f"/api/v1/jobs/{job.id}",
        events_url=f"/api/v1/jobs/{job.id}/events",
    )


@corpus_router.get("/audio/{filename}")
async def stream_corpus_audio(filename: str, request: Request, db: Annotated[AsyncSession, Depends(get_db)]):
    """Serves audio.corpus_item_audio bytes — same shape as
    stream_lecture_audio, keyed by the corpus item's own cache_key."""
    cache_key, media_type = _split_cache_filename(filename)
    row = (
        await db.execute(select(CorpusItemAudio).where(CorpusItemAudio.cache_key == cache_key))
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Audio not found")
    ext = "opus" if media_type.startswith("audio/ogg") else "aac"
    try:
        data = await run_in_threadpool(audio_store.read_row, row, ext)
    except audio_store.StoreError:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail="Audio storage is not reachable; try again") from None
    if not data:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Audio not yet generated")
    return _audio_response(request, data, media_type)


@vocab_router.post("/{vocab_item_id}/audio", response_model=JobAccepted, status_code=status.HTTP_202_ACCEPTED)
async def request_vocab_audio(
    vocab_item_id: int,
    body: VocabAudioRequest,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """The recording of one word, for the "nghe" button of a flashcard or a word list. No
    login required — hearing a word read aloud is a public read, only the "đã nhớ/chưa
    nhớ" progress needs an account. Covers lessons and editorial articles alike, since both
    read the same content.vocab_item rows.

    The recording is filed under the WORD (text + voice + version), not under the row: the
    same word in another lesson or topic is found already recorded and plays at once, for
    every learner and device. The word voiced is the one in the database, whatever `text_ko`
    says. A recording made before this (filed under the row's id) is still found. Only a
    word nobody has had recorded spends from the hourly allowance."""
    item = await db.get(VocabItem, vocab_item_id)
    text_ko = audio_keys.speakable(item.hangul) if item is not None else ""
    if not text_ko:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Word not found")
    # with Azure on, a word is voiced again once by the Korean voice (its own key); the Chirp
    # recordings stay under theirs, so turning Azure off finds them again
    version = f"{body.prompt_version}+{azure_tts.spec()}" if azure_tts.is_configured() else body.prompt_version
    cache_key = audio_keys.vocab_audio_key(text_ko, body.voice, version)

    hit = (
        await db.execute(select(VocabItemAudio).where(VocabItemAudio.cache_key == cache_key))
    ).scalar_one_or_none()
    if hit is None and not azure_tts.is_configured():
        hit = (
            await db.execute(
                select(VocabItemAudio).where(
                    VocabItemAudio.cache_key
                    == audio_keys.vocab_legacy_key(vocab_item_id, body.voice, body.prompt_version)
                )
            )
        ).scalar_one_or_none()

    idempotency_key = cache_key  # see _request_podcast: the recording's key, not a caller's header

    existing_job = await db.execute(
        select(Job).where(Job.type == "generate_vocab_audio", Job.idempotency_key == idempotency_key)
    )
    job = existing_job.scalar_one_or_none()
    if job is not None and ((job.status not in ("queued", "running", "succeeded") or job_events.abandoned(job)) or (job.status == "succeeded" and hit is None)):
        # See _request_podcast's identical comment: a failed row would
        # otherwise permanently block retries behind a unique-constraint 500.
        await db.delete(job)
        await db.flush()
        job = None

    if job is None:
        if hit is None:
            await _spend_word(request)
        job = Job(
            type="generate_vocab_audio",
            owner_id=None,
            idempotency_key=idempotency_key,
            status="succeeded" if hit else "queued",
            progress=1.0 if hit else 0.0,
            result={
                "cache_key": hit.cache_key,
                "opus_path": f"/api/v1/vocab-items/audio/{hit.cache_key}.opus",
                "aac_path": f"/api/v1/vocab-items/audio/{hit.cache_key}.aac",
                "duration_sec": hit.duration_sec,
            }
            if hit
            else None,
        )
        db.add(job)
        await db.commit()
        await db.refresh(job)

        if not hit:
            generate_vocab_audio.delay(
                str(job.id), str(vocab_item_id), text_ko, body.voice, body.prompt_version, cache_key
            )

    return JobAccepted(
        job_id=job.id,
        status=job.status,
        poll_url=f"/api/v1/jobs/{job.id}",
        events_url=f"/api/v1/jobs/{job.id}/events",
    )


@vocab_router.get("/audio/{filename}")
async def stream_vocab_audio(filename: str, request: Request, db: Annotated[AsyncSession, Depends(get_db)]):
    """Serves audio.vocab_item_audio bytes — same shape as
    stream_corpus_audio, keyed by the vocab item's own cache_key."""
    cache_key, media_type = _split_cache_filename(filename)
    row = (
        await db.execute(select(VocabItemAudio).where(VocabItemAudio.cache_key == cache_key))
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Audio not found")
    ext = "opus" if media_type.startswith("audio/ogg") else "aac"
    try:
        data = await run_in_threadpool(audio_store.read_row, row, ext)
    except audio_store.StoreError:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail="Audio storage is not reachable; try again") from None
    if not data:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Audio not yet generated")
    return _audio_response(request, data, media_type)


@text_router.post("/text", response_model=JobAccepted, status_code=status.HTTP_202_ACCEPTED)
async def request_text_audio(
    body: TextAudioRequest,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    profile: Annotated[Profile, Depends(get_current_profile)],
):
    """Read this Korean text aloud — checked first in the store, Google called only if it is not there.

    The recording is filed under a hash of what the text says (+ voice, pace, version), so the same
    sentence asked for again, from any device, is found and plays at once: the job comes back
    already succeeded with its paths, and nothing is spent. Only a text nobody has had voiced goes
    to the queue (Chirp 3 HD, then stored: services/text_audio) and spends from the hourly allowance.
    Login is required because this door turns the caller's text into paid speech; it voices Korean
    only and up to TEXT_AUDIO_MAX_CHARS."""
    try:
        text = text_audio.check_text(body.text)
    except text_audio.TextNotSpeakable as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    cache_key = text_audio.cache_key(text, body.voice, body.prompt_version)

    hit = (await db.execute(select(TextAudio).where(TextAudio.cache_key == cache_key))).scalar_one_or_none()
    usable = text_audio.is_usable(hit)

    idempotency_key = cache_key  # the recording's own key: see _request_podcast
    existing_job = await db.execute(
        select(Job).where(Job.type == "generate_text_audio", Job.idempotency_key == idempotency_key)
    )
    job = existing_job.scalar_one_or_none()
    if job is not None and ((job.status not in ("queued", "running", "succeeded") or job_events.abandoned(job)) or (job.status == "succeeded" and not usable)):
        # See _request_podcast: a failed row would wedge every retry behind the unique key; a
        # "succeeded" job whose recording is a Gemini fallback is run again so Chirp gets another go.
        await db.delete(job)
        await db.flush()
        job = None

    if job is None:
        if not usable:
            await _spend_word(request)
        job = Job(
            type="generate_text_audio",
            owner_id=None,
            idempotency_key=idempotency_key,
            status="succeeded" if usable else "queued",
            progress=1.0 if usable else 0.0,
            result={"cache_key": hit.cache_key, **text_audio.paths(hit.cache_key), "duration_sec": hit.duration_sec}
            if usable
            else None,
        )
        db.add(job)
        await db.commit()
        await db.refresh(job)

        if not usable:
            generate_text_audio.delay(str(job.id), text, body.voice, body.prompt_version, cache_key)

    return JobAccepted(
        job_id=job.id,
        status=job.status,
        poll_url=f"/api/v1/jobs/{job.id}",
        events_url=f"/api/v1/jobs/{job.id}/events",
    )


@text_router.get("/landing")
async def landing_audio_paths(response: Response, db: Annotated[AsyncSession, Depends(get_db)]):
    """The home page's demo cards (services/landing_audio): for each text, where its recording is,
    or "pending" while it is being made. Public and free to call: a recording is made once, by the
    first visit after a deploy (or a voice change), and every later visit only reads it; the files
    themselves are served immutable. A text still pending plays with the device's own voice."""
    items = []
    pending = False
    keys = {text: text_audio.cache_key(text, landing_audio.VOICE) for text in landing_audio.LANDING_TEXTS}
    rows = {
        r.cache_key: r
        for r in (await db.execute(select(TextAudio).where(TextAudio.cache_key.in_(list(keys.values()))))).scalars().all()
    }
    for text, key in keys.items():
        hit = rows.get(key)
        if text_audio.is_usable(hit):
            items.append({"text": text, "status": "ready", **text_audio.paths(key)})
            continue
        pending = True
        items.append({"text": text, "status": "pending"})
        await _ensure_landing_job(db, text, key)
    response.headers["Cache-Control"] = "no-store" if pending else "public, max-age=3600"
    return {"items": items}


async def _ensure_landing_job(db: AsyncSession, text: str, key: str) -> None:
    """One job per recording, however many visitors arrive at once: the job's idempotency key is the
    recording's key, so a second insert fails on the unique index and is simply dropped."""
    job = (
        await db.execute(select(Job).where(Job.type == "generate_text_audio", Job.idempotency_key == key))
    ).scalar_one_or_none()
    if job is not None and job.status in ("queued", "running") and not job_events.abandoned(job):
        return
    if job is not None:
        await db.delete(job)  # failed, abandoned, or "succeeded" with a fallback recording: try again
        await db.flush()
    job = Job(type="generate_text_audio", owner_id=None, idempotency_key=key, status="queued", progress=0.0)
    db.add(job)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()  # another visitor's request queued it first
        return
    await db.refresh(job)
    try:
        generate_text_audio.delay(str(job.id), text, landing_audio.VOICE, text_audio.PROMPT_VERSION, key)
    except Exception:  # noqa: BLE001 — the queue is down: the page still works (device voice); the
        # job is left queued, counts as abandoned after a while, and a later visit queues it again
        log.warning("[landing_audio] could not queue %s", key, exc_info=True)


@text_router.get("/text/{filename}")
async def stream_text_audio(filename: str, request: Request, db: Annotated[AsyncSession, Depends(get_db)]):
    """Serves a filed text recording — from its row, or from the private bucket when the row only
    holds the link. Same shape as the word and sentence routes, so an <audio> tag plays `opus_path`."""
    cache_key, media_type = _split_cache_filename(filename)
    row = (await db.execute(select(TextAudio).where(TextAudio.cache_key == cache_key))).scalar_one_or_none()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Audio not found")
    ext = "opus" if media_type.startswith("audio/ogg") else "aac"
    try:
        data = await run_in_threadpool(text_audio.read, row, ext)
    except audio_store.StoreError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail="Audio store unavailable") from exc
    if not data:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Audio not yet generated")
    return _audio_response(request, data, media_type)

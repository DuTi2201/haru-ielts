"""Celery tasks — where every AI call and heavy transform actually runs.
Sync SQLAlchemy session (Celery workers are sync by default); the API
process uses the async session instead (see app/db.py AsyncSessionLocal).
"""
import base64
import logging
import uuid
from dataclasses import asdict
from datetime import datetime, timezone

from sqlalchemy import create_engine, func
from sqlalchemy.orm import Session

from sqlalchemy import inspect as sa_inspect, or_, select

from app.core.celery_app import celery_app
from app.core.config import settings
from app.models import (
    CorpusItem,
    CorpusItemAudio,
    EditorialArticle,
    EditorialOutlineSubmission,
    ExamPaper,
    GrammarPoint,
    ImportBatch,
    ImportItem,
    Job,
    LectureAudio,
    Lesson,
    Profile,
    SceneImage,
    TextAudio,
    VocabItem,
    VocabItemAudio,
    LessonEssayCheck,
    WritingDrill,
)
from app.models import ErrorLog
from app.services import (
    article_extract,
    audio_store,
    azure_tts,
    corpus_enrich,
    db_backup,
    exam_extract,
    heavy_slot,
    ingestion,
    lesson_audio,
    lesson_image,
    lesson_image_db,
    read_along,
    srs,
    study_pack,
    text_audio,
    tts,
    writing_drill,
    essay_check,
)
from app.services import gemini_client
from app.services.job_events import publish_job_event

log = logging.getLogger(__name__)

# Separate sync engine for worker-side DB access.
_sync_engine = create_engine(settings.SYNC_DATABASE_URL, pool_pre_ping=True)


@celery_app.task(name="app.workers.tasks.generate_lecture_audio", bind=True, max_retries=3)
def generate_lecture_audio(self, job_id: str, lesson_id: str, text_ko: str, voice: str, prompt_version: str):
    """text -> Gemini TTS -> ffmpeg transcode to opus+aac -> row in
    audio.lecture_audio -> job.succeeded. Real pipeline (app/services/tts.py);
    this task is now just the job/cache bookkeeping around it — the ONE
    fully-wired example of the SDD's async-job pattern end to end, for
    real this time."""
    jid = uuid.UUID(job_id)
    cache_key = f"{lesson_id}:{voice}:{prompt_version}"
    with Session(_sync_engine) as db:
        try:
            publish_job_event(db, jid, status="running", progress=0.1, step="Đang tạo giọng đọc")
            opus_bytes, aac_bytes, duration_sec = tts.synthesize_korean_tts_chirp_first(text_ko, voice)

            publish_job_event(db, jid, progress=0.8, step="Đang lưu âm thanh")
            row = LectureAudio(
                cache_key=cache_key,
                opus_path=f"/api/v1/lessons/audio/{cache_key}.opus",
                aac_path=f"/api/v1/lessons/audio/{cache_key}.aac",
                **audio_store.file_away("lecture", cache_key, opus_bytes, aac_bytes),
                prompt_version=prompt_version,
                voice=voice,
                duration_sec=duration_sec,
            )
            db.add(row)
            db.commit()

            publish_job_event(
                db,
                jid,
                status="succeeded",
                progress=1.0,
                step="Hoàn tất",
                result={"cache_key": cache_key, "opus_path": row.opus_path, "duration_sec": duration_sec},
            )
        except Exception as exc:  # noqa: BLE001 — report to job row, then re-raise for Celery retry bookkeeping
            db.rollback()
            publish_job_event(
                db, jid, status="failed", error={"code": "internal_error", "message": str(exc), "retryable": True}
            )
            raise


def _store_word_audio(
    db: Session, model, jid: uuid.UUID, cache_key: str, text_ko: str, voice: str, make_row, path_prefix: str
):
    """Shared body of the word / sentence recordings: reuse the recording if one is already
    filed under `cache_key` (another lesson, device or a queued duplicate got there first),
    otherwise voice `text_ko`, store it and report the paths. Losing a race to a second
    worker on the unique key is a success too — the recording exists, which is all anyone
    wanted."""
    from sqlalchemy.exc import IntegrityError

    def done(duration_sec: int, stored_key: str):
        publish_job_event(
            db,
            jid,
            status="succeeded",
            progress=1.0,
            step="Hoàn tất",
            result={
                "cache_key": stored_key,
                "opus_path": f"{path_prefix}/{stored_key}.opus",
                "aac_path": f"{path_prefix}/{stored_key}.aac",
                "duration_sec": duration_sec,
            },
        )

    publish_job_event(db, jid, status="running", progress=0.1, step="Đang tạo giọng đọc")
    existing = db.execute(select(model).where(model.cache_key == cache_key)).scalar_one_or_none()
    if existing is not None:
        done(existing.duration_sec, existing.cache_key)
        return

    opus_bytes, aac_bytes, duration_sec = tts.synthesize_korean_tts_chirp_first(text_ko, voice)

    publish_job_event(db, jid, progress=0.8, step="Đang lưu âm thanh")
    db.add(make_row(opus_bytes, aac_bytes, duration_sec))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        winner = db.execute(select(model).where(model.cache_key == cache_key)).scalar_one_or_none()
        if winner is None:
            raise
        done(winner.duration_sec, winner.cache_key)
        return
    done(duration_sec, cache_key)


@celery_app.task(name="app.workers.tasks.generate_corpus_audio", bind=True, max_retries=3)
def generate_corpus_audio(
    self, job_id: str, corpus_item_id: str, text_ko: str, voice: str, prompt_version: str, cache_key: str | None = None
):
    """Same pattern as generate_lecture_audio, keyed to one corpus_item
    (a single listening sentence) instead of a whole lesson — backs the
    /listening screen's playback button."""
    jid = uuid.UUID(job_id)
    cache_key = cache_key or f"{corpus_item_id}:{voice}:{prompt_version}"  # a message queued before Azure carries none
    with Session(_sync_engine) as db:
        try:
            _store_word_audio(
                db,
                CorpusItemAudio,
                jid,
                cache_key,
                text_ko,
                voice,
                lambda opus, aac, dur: CorpusItemAudio(
                    corpus_item_id=uuid.UUID(corpus_item_id),
                    cache_key=cache_key,
                    **audio_store.file_away("word", cache_key, opus, aac),
                    prompt_version=prompt_version,
                    voice=voice,
                    duration_sec=dur,
                ),
                "/api/v1/corpus/audio",
            )
        except Exception as exc:  # noqa: BLE001
            db.rollback()
            publish_job_event(
                db, jid, status="failed", error={"code": "internal_error", "message": str(exc), "retryable": True}
            )
            raise


@celery_app.task(name="app.workers.tasks.generate_vocab_audio", bind=True, max_retries=3)
def generate_vocab_audio(
    self,
    job_id: str,
    vocab_item_id: str,
    text_ko: str,
    voice: str,
    prompt_version: str,
    cache_key: str | None = None,
):
    """Same pattern as generate_corpus_audio, but for one word's hangul — backs the "nghe"
    (listen) button on the vocab-study screen (the lesson flashcards and an editorial
    article's vocab list read the same VocabItem rows, so this one task covers both).

    `cache_key` is the recording's key (filed under the word, see services/audio_keys);
    a message queued before that change carries none, and gets the old per-row key."""
    jid = uuid.UUID(job_id)
    cache_key = cache_key or f"{vocab_item_id}:{voice}:{prompt_version}"
    with Session(_sync_engine) as db:
        try:
            _store_word_audio(
                db,
                VocabItemAudio,
                jid,
                cache_key,
                text_ko,
                voice,
                lambda opus, aac, dur: VocabItemAudio(
                    vocab_item_id=int(vocab_item_id),
                    cache_key=cache_key,
                    **audio_store.file_away("word", cache_key, opus, aac),
                    prompt_version=prompt_version,
                    voice=voice,
                    duration_sec=dur,
                ),
                "/api/v1/vocab-items/audio",
            )
        except Exception as exc:  # noqa: BLE001
            db.rollback()
            publish_job_event(
                db, jid, status="failed", error={"code": "internal_error", "message": str(exc), "retryable": True}
            )
            raise


@celery_app.task(name="app.workers.tasks.generate_text_audio", bind=True, max_retries=3)
def generate_text_audio(self, job_id: str, text_ko: str, voice: str, prompt_version: str, cache_key: str):
    """The recording of one text (a sentence, a dialogue line, a passage): if a recording is
    already filed under `cache_key` it is reported as it is (another device or a queued duplicate
    got there first); otherwise Chirp voices the text once (the Base64 reply is decoded in
    services/google_tts), it is filed (services/text_audio: Postgres row or the private bucket) and
    the row that links the text to its file is written. The text is the one the route checked."""
    jid = uuid.UUID(job_id)
    with Session(_sync_engine) as db:
        try:
            publish_job_event(db, jid, status="running", progress=0.1, step="Đang tạo giọng đọc")
            row = db.execute(select(TextAudio).where(TextAudio.cache_key == cache_key)).scalar_one_or_none()
            if not text_audio.is_usable(row):
                produced = text_audio.synthesize(text_ko, voice)
                publish_job_event(db, jid, progress=0.8, step="Đang lưu âm thanh")
                row = text_audio.save(db, cache_key, text_ko, voice, prompt_version, produced)
            publish_job_event(
                db,
                jid,
                status="succeeded",
                progress=1.0,
                step="Hoàn tất",
                result={"cache_key": row.cache_key, **text_audio.paths(row.cache_key), "duration_sec": row.duration_sec},
            )
        except Exception as exc:  # noqa: BLE001
            db.rollback()
            publish_job_event(
                db, jid, status="failed", error={"code": "internal_error", "message": str(exc), "retryable": True}
            )
            raise


def _voice_podcast(
    db: Session,
    script: str,
    voice: str,
    cache_key: str,
    fallback_cache_key: str | None,
    on_progress,
    max_chars: int | None = None,
    timeline_out: list | None = None,
):
    """Voice a lecture script. Returns (reuse_row, opus, aac, duration_sec,
    stored_key). `max_chars` raises the length the Chirp voice reads (a lesson's story
    of several parts is longer than the single-answer lecture).

    `fallback_cache_key` None: Gemini only, stored under `cache_key`.

    Otherwise Chirp 3 HD first (stored under `cache_key`, which embeds the voice
    spec). If Chirp fails, the WHOLE lecture is redone with Gemini (never two
    engines in one recording) and stored under `fallback_cache_key`, so a later
    play retries Chirp instead of being stuck with the fallback voice. A fallback
    recording that already exists is reused while Chirp is still down, rather
    than spending Gemini's small daily quota again."""
    if fallback_cache_key is None:
        opus, aac, dur = tts.synthesize_korean_tts(script, voice)
        return None, opus, aac, dur, cache_key

    try:
        if not tts.chirp_enabled():
            raise RuntimeError("TTS_GG_Chirp is not set on the worker service")
        if max_chars:
            opus, aac, dur = tts.synthesize_lecture_chirp(script, on_progress, max_chars, timeline_out=timeline_out)
        else:
            opus, aac, dur = tts.synthesize_lecture_chirp(script, on_progress, timeline_out=timeline_out)
        return None, opus, aac, dur, cache_key
    except tts.TranscodeError:
        # Chirp voiced the whole lecture; it is the encoding that failed. A second engine would only
        # spend another ~10 minutes (and Gemini's small quota) to meet the same encoder.
        raise
    except Exception as chirp_exc:  # noqa: BLE001 - ANY Chirp failure must fall back, not lose the lecture
        reason = tts.describe_error(chirp_exc)
        print(f"[tts] lecture: Google Chirp failed ({reason}); using Gemini fallback", flush=True)
        existing = db.execute(select(LectureAudio).where(LectureAudio.cache_key == fallback_cache_key)).scalar_one_or_none()
        if existing is not None:
            return existing, b"", b"", existing.duration_sec, fallback_cache_key
        try:
            opus, aac, dur = tts.synthesize_korean_tts(script, voice)
        except RuntimeError as gemini_exc:
            raise RuntimeError(f"Google Chirp lỗi ({reason}); Gemini dự phòng cũng lỗi: {gemini_exc}") from gemini_exc
        return None, opus, aac, dur, fallback_cache_key


@celery_app.task(name="app.workers.tasks.generate_content_podcast", bind=True, max_retries=3)
def generate_content_podcast(
    self,
    job_id: str,
    owner_kind: str,
    owner_id: str,
    voice: str,
    prompt_version: str,
    cache_key: str,
    fallback_cache_key: str | None = None,
    mode: str = "story",
):
    """Lesson-v5: for a lesson `mode` "template" (the default the API sends) builds the
    fixed script from the lesson (lesson_audio.build_template_script, no model), and
    "story" has Gemini write it in parts (ingestion.generate_lesson_story); both are then
    voiced by Chirp. Articles, and an old queued task that carries no mode, are always
    "story" in the original single-answer form.

    Gemini synthesizes a lesson's/article's ENTIRE vocab+grammar into
    one consolidated "bài giảng" script (ingestion.generate_podcast_script)
    -> TTS -> row in audio.lecture_audio (script_text set, cache_key
    prefixed "podcast:lesson:..."/"podcast:article:..." so it shares that
    table/route instead of a parallel one — see LectureAudio's docstring).
    Reuses the SAME "content-addressed job" pattern as generate_lecture_audio,
    except the cache_key here is computed by the API route from a hash of
    the owner's CURRENT vocab/grammar ids (see app/api/routers/audio.py and
    editorial.py), so adding a word later naturally busts the cache instead
    of serving a stale lecture.

    `owner_kind` is "lesson" or "article" — re-queries vocab/grammar fresh
    from the DB rather than trusting caller-supplied payloads, same as
    every other extraction task here.

    Voice: Google Chirp 3 HD first — Korean runs with the Korean voice and
    Vietnamese runs with the Vietnamese one (tts.synthesize_lecture_chirp) —
    and Gemini TTS as the fallback; see _voice_podcast. `fallback_cache_key`
    is None when the API did not have Chirp on: Gemini only, stored under
    `cache_key`, as before."""
    jid = uuid.UUID(job_id)
    with Session(_sync_engine) as db:
        try:
            publish_job_event(db, jid, status="running", progress=0.1, step="Đang tổng hợp nội dung bài giảng")

            lesson_source = None
            if owner_kind == "lesson":
                lesson_key, _, sitting_tag = owner_id.partition(":s")
                lesson = db.get(Lesson, int(lesson_key))
                if lesson is None:
                    raise RuntimeError(f"lesson {owner_id} not found")
                title = lesson.title
                vocab_rows = (
                    db.execute(select(VocabItem).where(VocabItem.lesson_id == lesson.id).order_by(VocabItem.id))
                    .scalars()
                    .all()
                )
                grammar_rows = (
                    db.execute(select(GrammarPoint).where(GrammarPoint.lesson_id == lesson.id).order_by(GrammarPoint.id))
                    .scalars()
                    .all()
                )
                lesson_source = lesson_audio.source_from_rows(lesson, vocab_rows, grammar_rows)
                if sitting_tag:  # "<lesson id>:s<n>": the lecture of one sitting
                    cut = lesson_audio.sitting_source(lesson, vocab_rows, grammar_rows, int(sitting_tag))
                    if cut is None:
                        raise RuntimeError(f"lesson {owner_id} has no such sitting")
                    lesson_source, vocab_rows, grammar_rows = cut
            else:
                article = db.get(EditorialArticle, uuid.UUID(owner_id))
                if article is None:
                    raise RuntimeError(f"editorial_article {owner_id} not found")
                title = article.title_ko or article.source_name
                vocab_rows = (
                    db.execute(select(VocabItem).where(VocabItem.id.in_(article.vocab_ids))).scalars().all()
                    if article.vocab_ids
                    else []
                )
                grammar_rows = (
                    db.execute(select(GrammarPoint).where(GrammarPoint.id.in_(article.grammar_ids))).scalars().all()
                    if article.grammar_ids
                    else []
                )

            vocab = [(v.hangul, v.pos, v.meaning_vi, v.example_ko, v.hanja, v.sino_vietnamese) for v in vocab_rows]
            grammar = [
                (g.pattern, g.meaning_vi, g.example_ko, g.usage_context_vi, g.topik_tip_vi) for g in grammar_rows
            ]

            if lesson_source is not None and mode == "template":
                # the same lesson always gives the same script: nothing to write, nothing to reuse
                publish_job_event(db, jid, progress=0.3, step="Đang soạn kịch bản bài học")
                script = lesson_audio.build_template_script(lesson_source)
            else:
                # A lecture already voiced by the Gemini fallback has its script on the
                # row: when only the voice is being redone, the same lecture is kept
                # instead of paying for (and getting) a different one.
                earlier = (
                    db.execute(select(LectureAudio).where(LectureAudio.cache_key == fallback_cache_key)).scalar_one_or_none()
                    if fallback_cache_key
                    else None
                )
                if earlier is not None and (earlier.script_text or "").strip():
                    script = earlier.script_text
                elif lesson_source is not None:

                    def on_part(done: int, total: int) -> None:
                        publish_job_event(
                            db,
                            jid,
                            progress=round(0.1 + 0.4 * done / max(total, 1), 3),
                            step=f"Đang viết kịch bản với Gemini (phần {min(done + 1, total)}/{total})",
                        )

                    publish_job_event(db, jid, progress=0.1, step="Đang viết kịch bản với Gemini")
                    script = ingestion.generate_lesson_story(lesson_source, on_part)
                else:
                    publish_job_event(db, jid, progress=0.3, step="Đang viết kịch bản với Gemini")
                    script = ingestion.generate_podcast_script(title, vocab, grammar)

            def on_progress(done: int, total: int) -> None:
                if total <= 0:
                    return
                publish_job_event(
                    db,
                    jid,
                    progress=round(0.5 + 0.4 * done / total, 3),
                    step=f"Đang tạo giọng đọc ({done}/{total})" if done < total else "Đang ghép âm thanh",
                )

            publish_job_event(db, jid, progress=0.5, step="Đang tạo giọng đọc")
            # the one heavy stretch of the job (recording, encoding): long ones take turns
            with heavy_slot.heavy_voicing_slot(
                lambda: publish_job_event(db, jid, progress=0.5, step="Đang chờ một bài giảng khác tạo xong")
            ):
                publish_job_event(db, jid, progress=0.5, step="Đang tạo giọng đọc")
                timeline: list[list[int]] = []
                reuse, opus_bytes, aac_bytes, duration_sec, stored_key = _voice_podcast(
                    db,
                    script,
                    voice,
                    cache_key,
                    fallback_cache_key,
                    on_progress,
                    lesson_audio.MAX_SCRIPT_CHARS if lesson_source is not None else None,
                    timeline,
                )

            if reuse is not None:
                row = reuse
            else:
                publish_job_event(db, jid, progress=0.95, step="Đang lưu bài giảng")
                row = LectureAudio(
                    cache_key=stored_key,
                    opus_path=f"/api/v1/lessons/audio/{stored_key}.opus",
                    aac_path=f"/api/v1/lessons/audio/{stored_key}.aac",
                    **audio_store.file_away("lecture", stored_key, opus_bytes, aac_bytes),
                    prompt_version=prompt_version,
                    voice=voice,
                    duration_sec=duration_sec,
                    script_text=script,
                    timeline=timeline or None,
                )
                db.add(row)
                db.commit()

            publish_job_event(
                db,
                jid,
                status="succeeded",
                progress=1.0,
                step="Hoàn tất",
                result={
                    "cache_key": stored_key,
                    "opus_path": row.opus_path,
                    "aac_path": row.aac_path,
                    "duration_sec": row.duration_sec,
                    "script_text": script,
                    "timeline": row.timeline,
                },
            )
        except Exception as exc:  # noqa: BLE001
            db.rollback()
            publish_job_event(
                db, jid, status="failed", error={"code": "internal_error", "message": str(exc), "retryable": True}
            )
            raise


def _voice_dialogue(
    db: Session,
    turns: list[tuple[str, str]],
    cache_key: str,
    fallback_cache_key: str | None,
    on_progress,
    gemini_key: str | None = None,
):
    """Voice a practice dialogue. Returns (reuse_row, opus, aac, duration_sec, stored_key).
    With Azure configured its two voices (female, male) record it under `cache_key`; if Azure
    fails, the Chirp recording (or Gemini when Chirp is not set) is filed under
    `fallback_cache_key` and Azure is tried again the next time. Without Azure: Chirp with two
    voices first; if it fails, ONE Gemini voice reads the whole thing and is filed under
    `fallback_cache_key` (so a later play tries Chirp again). With Chirp not configured at all
    it is Gemini only, filed under `cache_key`."""
    if azure_tts.is_configured():
        try:
            opus, aac, dur = tts.synthesize_dialogue_azure(turns, on_progress)
            return None, opus, aac, dur, cache_key
        except Exception as az_exc:  # noqa: BLE001 - Azure down: the learner still hears it
            print(f"[tts] dialogue: Azure failed ({tts.describe_error(az_exc)}); using the fallback voice", flush=True)
            if fallback_cache_key is None:
                raise
            existing = db.execute(select(LectureAudio).where(LectureAudio.cache_key == fallback_cache_key)).scalar_one_or_none()
            if existing is not None:
                return existing, b"", b"", existing.duration_sec, fallback_cache_key
            key = fallback_cache_key
            if tts.chirp_enabled():
                try:
                    opus, aac, dur = tts.synthesize_dialogue_chirp(turns, on_progress)
                    return None, opus, aac, dur, fallback_cache_key
                except Exception as chirp_exc:  # noqa: BLE001
                    print(f"[tts] dialogue: Google Chirp failed ({tts.describe_error(chirp_exc)}); using Gemini", flush=True)
                    key = gemini_key or fallback_cache_key
            opus, aac, dur = tts.synthesize_korean_tts("\n".join(text for _who, text in turns))
            return None, opus, aac, dur, key
    if fallback_cache_key is None:
        opus, aac, dur = tts.synthesize_korean_tts("\n".join(text for _who, text in turns))
        return None, opus, aac, dur, cache_key
    try:
        if not tts.chirp_enabled():
            raise RuntimeError("TTS_GG_Chirp is not set on the worker service")
        opus, aac, dur = tts.synthesize_dialogue_chirp(turns, on_progress)
        return None, opus, aac, dur, cache_key
    except Exception as chirp_exc:  # noqa: BLE001 - any Chirp failure falls back, the audio is not lost
        reason = tts.describe_error(chirp_exc)
        print(f"[tts] dialogue: Google Chirp failed ({reason}); using Gemini fallback", flush=True)
        existing = db.execute(select(LectureAudio).where(LectureAudio.cache_key == fallback_cache_key)).scalar_one_or_none()
        if existing is not None:
            return existing, b"", b"", existing.duration_sec, fallback_cache_key
        try:
            opus, aac, dur = tts.synthesize_korean_tts("\n".join(text for _who, text in turns))
        except RuntimeError as gemini_exc:
            raise RuntimeError(f"Google Chirp lỗi ({reason}); Gemini dự phòng cũng lỗi: {gemini_exc}") from gemini_exc
        return None, opus, aac, dur, fallback_cache_key


@celery_app.task(name="app.workers.tasks.generate_exercise_audio", bind=True, max_retries=3)
def generate_exercise_audio(
    self,
    job_id: str,
    exercise_id: str,
    turns: list,
    cache_key: str,
    fallback_cache_key: str | None = None,
):
    """The recording of one practice dialogue (listening exam question, speaking S4): a
    female and a male Chirp voice at a natural pace -> row in audio.lecture_audio, served by
    the same /lessons/audio route. `turns` is [[speaker, text], ...], built by the API from
    the lesson's own practice set."""
    jid = uuid.UUID(job_id)
    pairs = [(str(who), str(text)) for who, text in turns]
    with Session(_sync_engine) as db:
        try:
            publish_job_event(db, jid, status="running", progress=0.1, step="Đang tạo giọng đọc")

            def on_progress(done: int, total: int) -> None:
                if total > 0:
                    publish_job_event(db, jid, progress=round(0.1 + 0.8 * done / total, 3), step=f"Đang tạo giọng đọc ({done}/{total})")

            reuse, opus_bytes, aac_bytes, duration_sec, stored_key = _voice_dialogue(
                db,
                pairs,
                cache_key,
                fallback_cache_key,
                on_progress,
                lesson_audio.dialogue_cache_key(exercise_id, pairs, "gemini"),
            )
            if reuse is not None:
                row = reuse
            else:
                row = LectureAudio(
                    cache_key=stored_key,
                    opus_path=f"/api/v1/lessons/audio/{stored_key}.opus",
                    aac_path=f"/api/v1/lessons/audio/{stored_key}.aac",
                    **audio_store.file_away("lecture", stored_key, opus_bytes, aac_bytes),
                    prompt_version="lex-v1",
                    voice="dialogue",
                    duration_sec=duration_sec,
                    script_text="\n".join(f"{who}: {text}" for who, text in pairs),
                )
                db.add(row)
                db.commit()
            publish_job_event(
                db,
                jid,
                status="succeeded",
                progress=1.0,
                step="Hoàn tất",
                result={
                    "cache_key": stored_key,
                    "opus_path": row.opus_path,
                    "aac_path": row.aac_path,
                    "duration_sec": row.duration_sec,
                },
            )
        except Exception as exc:  # noqa: BLE001
            db.rollback()
            publish_job_event(
                db, jid, status="failed", error={"code": "internal_error", "message": str(exc), "retryable": True}
            )
            raise


def _timings_for_key(db: Session, cache_key: str) -> dict | None:
    """The read-along timeline of an earlier recording, taken from the result of
    the job that made it (the timeline is stored with the job result — there is
    no column for it on the audio row). None when that job is gone or predates
    read-along."""
    result = db.execute(
        select(Job.result)
        .where(
            Job.type == "generate_article_audio",
            Job.status == "succeeded",
            Job.result["cache_key"].astext == cache_key,
        )
        .order_by(Job.created_at.desc())
        .limit(1)
    ).scalar_one_or_none()
    timings = (result or {}).get("timings")
    return timings if isinstance(timings, dict) else None


def _voice_article(
    db: Session,
    tts_text: str,
    voice: str,
    cache_key: str,
    fallback_cache_key: str | None,
    on_progress,
    units: list | None = None,
):
    """Voice an article. Returns (reuse_row, opus, aac, duration_sec,
    stored_key, timings).

    `units` (read_along.Unit tuples) turns on read-along: the article is voiced
    sentence by sentence and `timings` says when each one starts. Without it
    (an old queued task) the article is voiced as before and `timings` is None.

    `fallback_cache_key` is None when the API did not have Google Chirp on:
    plain Gemini, stored under `cache_key`, exactly as before.

    Otherwise Chirp 3 HD is tried first and its recording is stored under
    `cache_key` (which embeds the voice+pace spec). If Chirp fails, the
    WHOLE article is redone with Gemini (never two voices in one recording)
    and stored under `fallback_cache_key`, so a later play retries Chirp
    instead of being stuck with the fallback voice forever. A fallback
    recording that already exists is reused rather than spending Gemini's
    small daily quota again while Chirp is still down."""
    timed = [read_along.Unit(*u) for u in units] if units else None

    def gemini():
        if timed:
            return tts.synthesize_article_tts_timed(timed, voice, on_progress)
        opus, aac, dur = tts.synthesize_article_tts(tts_text, voice, on_progress)
        return opus, aac, dur, None

    def chirp():
        if timed:
            return tts.synthesize_article_chirp_timed(timed, on_progress)
        opus, aac, dur = tts.synthesize_article_chirp(tts_text, on_progress)
        return opus, aac, dur, None

    if fallback_cache_key is None:
        opus, aac, dur, timings = gemini()
        return None, opus, aac, dur, cache_key, timings

    try:
        if not tts.chirp_enabled():
            raise RuntimeError("TTS_GG_Chirp is not set on the worker service")
        opus, aac, dur, timings = chirp()
        return None, opus, aac, dur, cache_key, timings
    except Exception as chirp_exc:  # noqa: BLE001 - ANY Chirp failure (incl. an unexpected client error) must fall back, not lose the audio
        chirp_exc = RuntimeError(tts.describe_error(chirp_exc))
        print(f"[tts] article: Google Chirp failed ({chirp_exc}); using Gemini fallback", flush=True)
        existing = db.execute(select(LectureAudio).where(LectureAudio.cache_key == fallback_cache_key)).scalar_one_or_none()
        if existing is not None:
            return existing, b"", b"", existing.duration_sec, fallback_cache_key, _timings_for_key(db, fallback_cache_key)
        try:
            opus, aac, dur, timings = gemini()
        except RuntimeError as gemini_exc:
            raise RuntimeError(f"Google Chirp lỗi ({chirp_exc}); Gemini dự phòng cũng lỗi: {gemini_exc}") from gemini_exc
        return None, opus, aac, dur, fallback_cache_key, timings


@celery_app.task(name="app.workers.tasks.generate_article_audio", bind=True, max_retries=3)
def generate_article_audio(
    self,
    job_id: str,
    tts_text: str,
    voice: str,
    prompt_version: str,
    cache_key: str,
    fallback_cache_key: str | None = None,
    units: list | None = None,
):
    """Reads an editorial article's OWN cleaned text aloud verbatim —
    deliberately independent of generate_content_podcast (which has Gemini
    WRITE a teaching script about the article's vocab/grammar, never the
    article's actual words). `tts_text` is built by the API route
    (article_extract.article_tts_text: cleaned title + body, one paragraph
    per line) and is exactly what the cache key hashes.

    Voice: Google Chirp 3 HD first, Gemini as the fallback (see _voice_article).
    Both paths use paragraph-aligned chunks with real silence between them,
    per-chunk retry on transient errors, and a progress callback so the client
    can show "2/4" during the (long) first generation. Every later play of
    the same text is a cache hit and never reaches this task."""
    jid = uuid.UUID(job_id)
    with Session(_sync_engine) as db:
        try:
            publish_job_event(db, jid, status="running", progress=0.05, step="Đang chuẩn bị giọng đọc")

            def on_progress(done: int, total: int) -> None:
                if total <= 0:
                    return
                publish_job_event(
                    db,
                    jid,
                    progress=round(0.05 + 0.85 * done / total, 3),
                    step=f"Đang tạo giọng đọc ({done}/{total})" if done < total else "Đang ghép âm thanh",
                )

            reuse, opus_bytes, aac_bytes, duration_sec, stored_key, timings = _voice_article(
                db, tts_text, voice, cache_key, fallback_cache_key, on_progress, units
            )

            if reuse is not None:
                row = reuse
            else:
                publish_job_event(db, jid, progress=0.95, step="Đang lưu âm thanh")
                row = LectureAudio(
                    cache_key=stored_key,
                    opus_path=f"/api/v1/lessons/audio/{stored_key}.opus",
                    aac_path=f"/api/v1/lessons/audio/{stored_key}.aac",
                    **audio_store.file_away("lecture", stored_key, opus_bytes, aac_bytes),
                    prompt_version=prompt_version,
                    voice=voice,
                    duration_sec=duration_sec,
                )
                db.add(row)
                db.commit()

            publish_job_event(
                db,
                jid,
                status="succeeded",
                progress=1.0,
                step="Hoàn tất",
                result={
                    "cache_key": stored_key,
                    "opus_path": row.opus_path,
                    "aac_path": row.aac_path,
                    "duration_sec": duration_sec,
                    # read-along: when each sentence starts (None for a
                    # recording made without it)
                    "timings": timings,
                },
            )
        except Exception as exc:  # noqa: BLE001
            db.rollback()
            publish_job_event(
                db, jid, status="failed", error={"code": "internal_error", "message": str(exc), "retryable": True}
            )
            raise


@celery_app.task(name="app.workers.tasks.grade_editorial_outline", bind=True, max_retries=3)
def grade_editorial_outline(self, job_id: str, submission_id: str):
    """Real Gemini feedback on the learner's OWN "luyện dàn ý" attempt —
    previously POST /editorials/{id}/outline only ever persisted the text
    and returned the static, ingestion-time model_outline (a reference
    answer, not feedback on what the learner actually wrote). Runs after
    every save (see app/api/routers/editorial.py submit_editorial_outline).
    """
    jid, sid = uuid.UUID(job_id), uuid.UUID(submission_id)
    with Session(_sync_engine) as db:
        submission = db.get(EditorialOutlineSubmission, sid)
        if submission is None:
            publish_job_event(db, jid, status="failed", error={"code": "not_found", "message": "submission not found"})
            return
        try:
            article = db.get(EditorialArticle, submission.editorial_article_id)
            if article is None:
                raise RuntimeError(f"editorial_article {submission.editorial_article_id} not found")

            publish_job_event(db, jid, status="running", progress=0.2, step="Đang phân tích dàn ý với Gemini")
            feedback = ingestion.generate_outline_feedback(
                article_title=article.title_ko or article.source_name,
                article_body=article_extract.clean_article_text(article.body_ko or ""),
                reference_outline=article.model_outline or {},
                learner_outline={
                    "phenomenon_text": submission.phenomenon_text,
                    "cause_text": submission.cause_text,
                    "consequence_text": submission.consequence_text,
                    "solution_text": submission.solution_text,
                },
            )

            submission.feedback_status = "ready"
            submission.feedback_text = feedback
            db.add(submission)
            db.commit()

            publish_job_event(
                db, jid, status="succeeded", progress=1.0, step="Hoàn tất",
                result={"submission_id": submission_id, "feedback_text": feedback},
            )
        except Exception as exc:  # noqa: BLE001
            db.rollback()
            submission.feedback_status = "failed"
            db.add(submission)
            db.commit()
            publish_job_event(
                db, jid, status="failed", error={"code": "internal_error", "message": str(exc), "retryable": True}
            )
            raise


@celery_app.task(name="app.workers.tasks.generate_writing_drill", bind=True, max_retries=0)
def generate_writing_drill(self, job_id: str, drill_id: str):
    """Builds one "viết câu 51–52" exercise from the learner's own cards:
    generate, check with code, check with a second model call (see
    app/services/writing_drill.py). No retry on purpose — a failed exercise
    costs the learner one tap to ask for another, while a retry would double
    the spend on a model that just refused to give a reliable one."""
    jid, did = uuid.UUID(job_id), uuid.UUID(drill_id)
    with Session(_sync_engine) as db:
        drill = db.get(WritingDrill, did)
        if drill is None:
            publish_job_event(db, jid, status="failed", error={"code": "not_found", "message": "drill not found"})
            return
        try:
            publish_job_event(db, jid, status="running", progress=0.2, step="Đang soạn đề từ các cụm bạn đang học")
            ids = [s["item_id"] for s in drill.source_items]
            rows = {v.id: v for v in db.execute(select(VocabItem).where(VocabItem.id.in_(ids))).scalars().all()}
            targets = [
                writing_drill.SourceCard(
                    item_id=v.id,
                    hangul=v.hangul,
                    meaning_vi=v.meaning_vi,
                    node_word=v.node_word,
                    family=v.family,
                    register=v.register,
                    example_ko=v.example_ko,
                )
                for i in ids
                if (v := rows.get(i)) is not None
            ]
            if not targets:
                raise ValueError("Các thẻ nguồn của đề không còn nữa. Hãy tạo đề mới.")
            profile = db.get(Profile, drill.learner_id)
            level = srs.article_level_cap(profile.goal if profile else None)
            exercise = writing_drill.build_exercise(
                targets, level, gemini_client.generate_structured, exam_extract.analysis_model()
            )
            drill.prompt = exercise
            drill.status = "ready"
            db.add(drill)
            db.commit()
            publish_job_event(
                db, jid, status="succeeded", progress=1.0, step="Đề đã sẵn sàng", result={"drill_id": drill_id}
            )
        except Exception as exc:  # noqa: BLE001 — recorded on the drill and the job
            db.rollback()
            drill = db.get(WritingDrill, did)
            drill.status = "failed"
            db.add(drill)
            db.commit()
            friendly = isinstance(exc, ValueError)
            print(f"[writing-drill] generate {did}: {exc!r}", flush=True)
            publish_job_event(
                db,
                jid,
                status="failed",
                error={
                    "code": "drill_failed",
                    "message": str(exc) if friendly else "Không tạo được đề lúc này. Hãy thử lại sau.",
                    "retryable": True,
                },
            )


@celery_app.task(name="app.workers.tasks.grade_writing_drill", bind=True, max_retries=0)
def grade_writing_drill(self, job_id: str, drill_id: str):
    """Checks the learner's two sentences (code first, then the model) and writes
    each slip to the error log so it shows up in "điểm yếu". If the model cannot
    be reached the check fails and the answers are kept, so the learner can send
    them again (an exercise is graded once)."""
    jid, did = uuid.UUID(job_id), uuid.UUID(drill_id)
    with Session(_sync_engine) as db:
        drill = db.get(WritingDrill, did)
        if drill is None or drill.prompt is None or drill.answers is None:
            publish_job_event(db, jid, status="failed", error={"code": "not_found", "message": "drill not ready"})
            return
        try:
            publish_job_event(db, jid, status="running", progress=0.3, step="Đang chấm bài viết")
            result = writing_drill.grade_answers(
                drill.prompt, drill.answers, gemini_client.generate_structured, exam_extract.analysis_model()
            )
            drill.result = result
            drill.grade_status = "ready"
            single = drill.source_items[0] if len(drill.source_items) == 1 else None
            for row in writing_drill.error_rows(result):
                db.add(
                    ErrorLog(
                        learner_id=drill.learner_id,
                        skill="viết",
                        error_type=row["error_type"],
                        example_ko=row["example_ko"],
                        item_type=single["item_type"] if single else None,
                        item_id=single["item_id"] if single else None,
                        mode="writing",
                        detail={**row["detail"], "drill_id": drill_id},
                    )
                )
            db.add(drill)
            db.commit()
            publish_job_event(
                db, jid, status="succeeded", progress=1.0, step="Đã chấm xong", result={"drill_id": drill_id}
            )
        except Exception as exc:  # noqa: BLE001
            db.rollback()
            drill = db.get(WritingDrill, did)
            drill.grade_status = "failed"
            db.add(drill)
            db.commit()
            print(f"[writing-drill] grade {did}: {exc!r}", flush=True)
            publish_job_event(
                db,
                jid,
                status="failed",
                error={"code": "grade_failed", "message": "Chưa chấm được lúc này. Bài của bạn vẫn được giữ, hãy thử gửi lại.", "retryable": True},
            )


@celery_app.task(name="app.workers.tasks.check_lesson_essay", bind=True, max_retries=0)
def check_lesson_essay(self, job_id: str, check_id: str):
    """Checks a paragraph written for a lesson (app/services/essay_check.py) and writes each kind
    of slip to the error log. If the model cannot be reached the check fails and the text is kept,
    so the learner can send it again."""
    jid, cid = uuid.UUID(job_id), uuid.UUID(check_id)
    with Session(_sync_engine) as db:
        row = db.get(LessonEssayCheck, cid)
        if row is None:
            publish_job_event(db, jid, status="failed", error={"code": "not_found", "message": "check not found"})
            return
        lesson = db.get(Lesson, row.lesson_id)
        item = essay_check.find_item(lesson.practice if lesson else None, row.exercise_id)
        if item is None:
            row.status = "failed"
            db.add(row)
            db.commit()
            publish_job_event(db, jid, status="failed", error={"code": "not_found", "message": "exercise not found"})
            return
        try:
            publish_job_event(db, jid, status="running", progress=0.3, step="Đang chấm bài viết")
            result = essay_check.check(item, row.text, gemini_client.generate_structured, exam_extract.analysis_model())
            row.result = result
            row.status = "ready"
            for err in essay_check.error_rows(result):
                db.add(
                    ErrorLog(
                        learner_id=row.learner_id,
                        skill="viết",
                        error_type=err["error_type"],
                        example_ko=err["example_ko"],
                        mode="writing",
                        detail={**err["detail"], "lesson_id": row.lesson_id, "exercise_id": row.exercise_id, "check_id": check_id},
                    )
                )
            db.add(row)
            db.commit()
            publish_job_event(db, jid, status="succeeded", progress=1.0, step="Đã chấm xong", result={"check_id": check_id})
        except Exception as exc:  # noqa: BLE001
            db.rollback()
            row = db.get(LessonEssayCheck, cid)
            row.status = "failed"
            db.add(row)
            db.commit()
            print(f"[essay-check] {cid}: {exc!r}", flush=True)
            publish_job_event(
                db,
                jid,
                status="failed",
                error={"code": "check_failed", "message": "Chưa chấm được lúc này. Bài của bạn vẫn được giữ, hãy thử gửi lại.", "retryable": True},
            )


@celery_app.task(name="app.workers.tasks.grade_writing_submission")
def grade_writing_submission(job_id: str, submission_id: str):
    """Stub for the Xưởng viết grading step (OCR transcript already
    confirmed by the learner -> Gemini grading -> writing_score row)."""
    jid = uuid.UUID(job_id)
    with Session(_sync_engine) as db:
        publish_job_event(db, jid, status="running", progress=0.3, step="Đang chấm điểm")
        publish_job_event(
            db,
            jid,
            status="succeeded",
            progress=1.0,
            step="Hoàn tất chấm điểm",
            result={"submission_id": submission_id},
        )


@celery_app.task(name="app.workers.tasks.extract_lesson_import", bind=True, max_retries=2)
def extract_lesson_import(self, job_id: str, batch_id: str, file_b64: str, mime_type: str):
    """Bài học ảnh/PDF -> Gemini (đa phương thức) -> đề xuất lesson/vocab/
    grammar vào khu chờ duyệt (import_item). Không ghi bảng chính ở đây —
    chỉ POST /imports/{id}/confirm mới ghi (SDD: "khu chờ duyệt")."""
    jid, bid = uuid.UUID(job_id), uuid.UUID(batch_id)
    with Session(_sync_engine) as db:
        batch = db.get(ImportBatch, bid)
        if batch is None:
            publish_job_event(db, jid, status="failed", error={"code": "not_found", "message": "batch not found"})
            return
        try:
            # A file read again (re-uploaded after the extraction improved) lands on
            # the same batch: its old, unreviewed proposals are replaced.
            cleared = ingestion.clear_staged_items(db, batch)
            if cleared:
                print(f"[lesson] re-reading batch {bid}: dropped {cleared} earlier proposal(s)", flush=True)
            batch.status = "extracting"
            db.add(batch)
            db.commit()
            publish_job_event(db, jid, status="running", progress=0.2, step="Đang đọc tài liệu với Gemini")

            file_bytes = base64.b64decode(file_b64)

            def on_progress(done: int, total: int, step: str) -> None:
                publish_job_event(db, jid, progress=round(0.2 + 0.7 * done / max(total, 1), 3), step=step)

            staged, flagged = ingestion.run_lesson_extraction(db, batch, file_bytes, mime_type, on_progress)

            batch.status = "awaiting_review"
            batch.flagged_count = flagged
            db.add(batch)
            db.commit()
            publish_job_event(
                db,
                jid,
                status="succeeded",
                progress=1.0,
                step="Hoàn tất trích xuất",
                result={"import_batch_id": str(bid), "staged": staged, "flagged": flagged},
            )
        except Exception as exc:  # noqa: BLE001
            batch.status = "failed"
            db.add(batch)
            db.commit()
            publish_job_event(
                db, jid, status="failed", error={"code": "internal_error", "message": str(exc), "retryable": True}
            )
            raise


@celery_app.task(name="app.workers.tasks.extract_corpus_import", bind=True, max_retries=2)
def extract_corpus_import(self, job_id: str, batch_id: str, file_b64: str, film_title: str, mime_type: str | None = None):
    """Phụ đề phim -> phân đoạn theo lô cố định (chunk_cues) -> mỗi lô gọi
    Gemini phân loại câu/cụm/mẫu ngữ pháp riêng, KHÔNG dồn cả kịch bản vào
    một prompt (FR-19, Gate G6: kích thước prompt không phình theo độ dài
    kịch bản) -> đề xuất corpus_item vào khu chờ duyệt.

    `mime_type` decides how the raw bytes become text: a real .srt/.vtt file
    or plain text is just decoded, but an image/PDF (a photographed or
    screenshotted subtitle list) goes through a Gemini-vision OCR pass first
    — see ingestion.extract_corpus_source_text. `mime_type=None` (older
    enqueued jobs / callers that don't pass it) falls back to the previous
    plain-decode-only behavior, so this stays backward compatible."""
    jid, bid = uuid.UUID(job_id), uuid.UUID(batch_id)
    with Session(_sync_engine) as db:
        batch = db.get(ImportBatch, bid)
        if batch is None:
            publish_job_event(db, jid, status="failed", error={"code": "not_found", "message": "batch not found"})
            return
        try:
            film = ingestion.find_or_create_film(db, film_title)
            batch.film_id = film.id
            batch.status = "extracting"
            db.add(batch)
            db.commit()
            is_image = bool(mime_type) and (mime_type.startswith("image/") or mime_type == "application/pdf")
            publish_job_event(
                db, jid, status="running", progress=0.1,
                step="Đang nhận diện văn bản từ ảnh" if is_image else "Đang tách câu thoại",
            )

            file_bytes = base64.b64decode(file_b64)
            raw_text = ingestion.extract_corpus_source_text(file_bytes, mime_type)
            if is_image:
                publish_job_event(db, jid, progress=0.4, step="Đang tách câu thoại")
            publish_job_event(db, jid, progress=0.5, step="Đang phân loại, lọc câu thiếu tự nhiên và dịch nghĩa")
            stats = ingestion.run_corpus_extraction(db, batch, raw_text)

            batch.status = "awaiting_review"
            batch.flagged_count = stats.flagged
            db.add(batch)
            db.commit()
            publish_job_event(
                db,
                jid,
                status="succeeded",
                progress=1.0,
                step="Hoàn tất phân loại kho câu",
                result={
                    "import_batch_id": str(bid),
                    "film_id": film.id,
                    "staged": stats.staged,
                    "flagged": stats.flagged,
                    "duplicates_skipped": stats.duplicates,
                    # lines judged unnatural/garbled: never staged (a few shown
                    # so the reviewer can tell if the filter is too strict)
                    "unnatural_skipped": stats.unnatural,
                    "unnatural_samples": stats.unnatural_samples,
                    # staged without a meaning/usage note (enrichment call failed)
                    "unenriched": stats.unenriched,
                },
            )
        except Exception as exc:  # noqa: BLE001
            batch.status = "failed"
            db.add(batch)
            db.commit()
            publish_job_event(
                db, jid, status="failed", error={"code": "internal_error", "message": str(exc), "retryable": True}
            )
            raise


@celery_app.task(name="app.workers.tasks.enrich_corpus_items", bind=True, max_retries=0)
def enrich_corpus_items(self, job_id: str):
    """Điền bù nghĩa tiếng Việt, ghi chú cách dùng, nhận định "có tự nhiên không"
    và chủ đề cho các câu trong kho câu chưa được xử lý (câu import trước khi có
    tính năng này, hoặc câu mà lần làm giàu lúc import bị lỗi). Chạy theo lô,
    COMMIT sau mỗi lô nên chạy lại được: lần sau chỉ làm tiếp phần còn thiếu.
    Dừng sớm nếu nhiều lô liên tiếp lỗi (hết hạn mức Gemini, sự cố) thay vì đốt
    cả kho vào những lần gọi chắc chắn hỏng."""
    jid = uuid.UUID(job_id)
    with Session(_sync_engine) as db:
        try:
            publish_job_event(db, jid, status="running", progress=0.02, step="Đang chuẩn bị làm giàu kho câu")
            generate = corpus_enrich.make_generate(
                settings.GEMINI_MODEL_CORPUS_INGEST, gemini_client.generate_structured
            )

            def progress(done: int, total: int) -> None:
                publish_job_event(
                    db, jid, status="running", progress=0.05 + 0.9 * done / max(total, 1),
                    step=f"Đã xử lý {done}/{total} câu",
                )

            stats = ingestion.run_corpus_enrichment(db, generate, on_progress=progress)
            remaining = db.scalar(
                select(func.count()).select_from(CorpusItem).where(ingestion.corpus_enrichment_pending_filter())
            )
            result = {**asdict(stats), "remaining": remaining}
            if stats.stopped_early:
                publish_job_event(
                    db, jid, status="failed", step="Dừng sớm vì Gemini liên tục lỗi", result=result,
                    error={
                        "code": "gemini_unavailable",
                        "message": stats.error or "Gemini liên tục lỗi",
                        "retryable": True,
                    },
                )
            else:
                publish_job_event(
                    db, jid, status="succeeded", progress=1.0, step="Hoàn tất làm giàu kho câu", result=result
                )
        except Exception as exc:  # noqa: BLE001
            db.rollback()
            publish_job_event(
                db, jid, status="failed", error={"code": "internal_error", "message": str(exc)[:300], "retryable": True}
            )
            raise


@celery_app.task(name="app.workers.tasks.generate_lesson_images", bind=True, max_retries=0)
def generate_lesson_images(self, job_id: str, lesson_id: int | None, keys: list[str] | None, force: bool):
    """Vẽ ảnh minh hoạ còn thiếu (của một bài, hoặc của mọi bài). Ba ảnh được vẽ cùng lúc;
    mỗi ảnh được nén thành WebP nhỏ rồi COMMIT ngay, nên chạy lại được: lần sau chỉ vẽ phần
    còn thiếu. Ảnh bị mô hình từ chối (an toàn) chỉ bị bỏ qua và ghi vào kết quả; lỗi khoá /
    hạn mức / mô hình sai làm dừng cả lượt thay vì đốt thêm những lần gọi chắc chắn hỏng."""
    from concurrent.futures import ThreadPoolExecutor, as_completed

    jid = uuid.UUID(job_id)
    with Session(_sync_engine) as db:
        try:
            publish_job_event(db, jid, status="running", progress=0.02, step="Đang chuẩn bị vẽ ảnh")
            groups = lesson_image_db.lesson_slots_sync(
                db, [lesson_id] if lesson_id is not None else None, (Lesson.sort_order, Lesson.id)
            )
            wanted = [s.key for g in groups for s in g.slots]
            existing = set(db.scalars(select(SceneImage.cache_key).where(SceneImage.cache_key.in_(wanted or [""]))).all())
            todo = lesson_image_db.pick_work(groups, existing, keys, force)
            model = (settings.GEMINI_MODEL_IMAGE or "").strip()[:64]
            created = 0
            failed: list[dict] = []
            fatal: str | None = None

            with ThreadPoolExecutor(max_workers=3) as pool:
                futures = {pool.submit(lesson_image.generate_image, slot.prompt, slot.kind): slot for slot in todo}
                for future in as_completed(futures):
                    slot = futures[future]
                    if future.cancelled():  # a fatal error already stopped the run
                        continue
                    try:
                        data, mime = future.result()
                    except lesson_image.ImageGenError as exc:
                        failed.append({"key": slot.key, "label": slot.label, "error": str(exc)[:200]})
                        if exc.fatal and fatal is None:
                            fatal = str(exc)[:300]
                            for pending in futures:
                                pending.cancel()
                    except Exception as exc:  # noqa: BLE001
                        failed.append({"key": slot.key, "label": slot.label, "error": str(exc)[:200]})
                    else:
                        row = db.get(SceneImage, slot.key)
                        if row is None:
                            row = SceneImage(cache_key=slot.key)
                            db.add(row)
                        row.mime_type = mime[:32]
                        for column, value in audio_store.file_image(slot.key, data, row.mime_type).items():
                            setattr(row, column, value)  # storage, object_key, data
                        row.prompt = slot.prompt
                        row.model = model
                        row.kind = slot.kind
                        row.hidden = False
                        row.created_at = datetime.now(timezone.utc)
                        db.commit()
                        created += 1
                    done = created + len(failed)
                    publish_job_event(
                        db, jid, status="running", progress=0.05 + 0.9 * done / max(len(todo), 1),
                        step=f"Đã vẽ {created}/{len(todo)} ảnh" + (f", {len(failed)} lỗi" if failed else ""),
                    )

            remaining = len(lesson_image_db.pick_work(
                groups, set(db.scalars(select(SceneImage.cache_key).where(SceneImage.cache_key.in_(wanted or [""]))).all()), keys, False
            ))
            result = {"lesson_id": lesson_id, "created": created, "failed": failed, "remaining": remaining, "total": len(todo)}
            if fatal is not None or (created == 0 and failed):
                publish_job_event(
                    db, jid, status="failed", step="Dừng vì Gemini không vẽ được", result=result,
                    error={"code": "image_failed", "message": fatal or failed[0]["error"], "retryable": True},
                )
            else:
                publish_job_event(
                    db, jid, status="succeeded", progress=1.0,
                    step=f"Đã vẽ {created} ảnh" + (f", {len(failed)} ảnh bị bỏ qua" if failed else ""), result=result,
                )
        except Exception as exc:  # noqa: BLE001
            db.rollback()
            publish_job_event(
                db, jid, status="failed", error={"code": "internal_error", "message": str(exc)[:300], "retryable": True}
            )
            raise


@celery_app.task(name="app.workers.tasks.extract_exam_paper_import", bind=True, max_retries=2)
def extract_exam_paper_import(
    self, job_id: str, batch_id: str, files_b64: list[dict], exam_kind: str, session_label: str
):
    """Đề thi ảnh/PDF -> Gemini (đa phương thức) -> đề xuất exam_passage/
    exam_item vào khu chờ duyệt. exam_paper được tạo ngay (giống film,
    exam_kind/session_label do admin gõ chứ không phải AI suy ra) trước khi
    trích xuất; không ghi content.exam_passage/exam_item ở đây — chỉ POST
    /imports/{id}/confirm mới ghi.

    `files_b64` are the pages of ONE paper, each `{"data": <base64>, "mime_type":
    <str>}` (a paper may arrive as several files). exam_extract cuts a PDF into
    pages and reads them a few at a time, twice, so a file's size never decides
    how much of the paper Gemini sees at once."""
    jid, bid = uuid.UUID(job_id), uuid.UUID(batch_id)
    with Session(_sync_engine) as db:
        batch = db.get(ImportBatch, bid)
        if batch is None:
            publish_job_event(db, jid, status="failed", error={"code": "not_found", "message": "batch not found"})
            return
        try:
            paper = ingestion.find_or_create_exam_paper(db, batch.owner_id, batch.file_hash, exam_kind, session_label)
            batch.exam_paper_id = paper.id
            # A paper read again (re-uploaded after the extraction improved) lands on
            # the same batch: its old, unreviewed proposals are replaced.
            cleared = ingestion.clear_staged_items(db, batch)
            if cleared:
                print(f"[exam] re-reading batch {bid}: dropped {cleared} earlier proposal(s)", flush=True)
            batch.status = "extracting"
            db.add(batch)
            db.commit()
            publish_job_event(db, jid, status="running", progress=0.1, step="Đang tách các trang của đề")

            files = [(base64.b64decode(f["data"]), f["mime_type"]) for f in files_b64]

            def on_progress(done: int, total: int, step: str) -> None:
                publish_job_event(db, jid, progress=round(0.1 + 0.8 * done / max(total, 1), 3), step=step)

            staged, flagged = ingestion.run_exam_extraction(
                db, batch, files, session_label=session_label, on_progress=on_progress
            )

            batch.status = "awaiting_review"
            batch.flagged_count = flagged
            db.add(batch)
            db.commit()
            publish_job_event(
                db,
                jid,
                status="succeeded",
                progress=1.0,
                step="Hoàn tất trích xuất đề thi",
                result={"import_batch_id": str(bid), "exam_paper_id": str(paper.id), "staged": staged, "flagged": flagged},
            )
        except Exception as exc:  # noqa: BLE001
            db.rollback()
            batch.status = "failed"
            db.add(batch)
            db.commit()
            publish_job_event(
                db, jid, status="failed", error={"code": "internal_error", "message": str(exc)[:300], "retryable": True}
            )
            raise


@celery_app.task(name="app.workers.tasks.extract_answer_key_import", bind=True, max_retries=1)
def extract_answer_key_import(self, job_id: str, batch_id: str, files_b64: list[dict], skill: str | None):
    """Bảng đáp án (정답표) tải lên riêng -> Gemini đọc hai lượt -> đáp án chỉ được
    dùng khi hai lượt khớp nhau -> ghi vào các câu của lô đề thi `batch_id` (kể cả
    những câu đã xác nhận vào thư viện). Không có AI nào đoán đáp án ở đây: chỉ
    chép bảng in sẵn. `skill` (đọc/nghe) chọn bảng nào của đáp án nhiều phần thuộc
    về đề này; để trống thì suy ra từ nhãn phiên thi và nội dung đề."""
    jid, bid = uuid.UUID(job_id), uuid.UUID(batch_id)
    with Session(_sync_engine) as db:
        batch = db.get(ImportBatch, bid)
        if batch is None or batch.kind != "exam_paper":
            publish_job_event(db, jid, status="failed", error={"code": "not_found", "message": "exam batch not found"})
            return
        try:
            publish_job_event(db, jid, status="running", progress=0.1, step="Đang đọc bảng đáp án")

            def on_progress(done: int, total: int, step: str) -> None:
                publish_job_event(db, jid, progress=round(0.1 + 0.8 * done / max(total, 1), 3), step=step)

            read = exam_extract.extract_key([(base64.b64decode(f["data"]), f["mime_type"]) for f in files_b64], on_progress=on_progress)

            paper = db.get(ExamPaper, batch.exam_paper_id) if batch.exam_paper_id else None
            items = db.execute(select(ImportItem).where(ImportItem.import_batch_id == bid)).scalars().all()
            target = skill or ingestion.paper_skill(list(items), paper.session_label if paper else None)
            chosen = exam_extract.choose_key_section(read.sections, target)
            if chosen is None:
                found = ", ".join(sorted(read.sections)) or "không có bảng nào"
                raise RuntimeError(
                    f"Không biết bảng đáp án nào thuộc đề này (đọc được: {found}). "
                    "Hãy ghi rõ đề đọc/nghe ở nhãn phiên thi hoặc chọn phần thi khi tải đáp án."
                )
            report = ingestion.apply_answers(
                db,
                batch,
                read.sections[chosen],
                skill=chosen,
                source="file",
                conflicts=read.conflicts.get(chosen, []),
            )
            db.commit()
            publish_job_event(
                db,
                jid,
                status="succeeded",
                progress=1.0,
                step=f"Đã áp {len(report.applied)} đáp án",
                result={"import_batch_id": str(bid), **report.as_dict()},
            )
        except Exception as exc:  # noqa: BLE001
            db.rollback()
            publish_job_event(
                db, jid, status="failed", error={"code": "internal_error", "message": str(exc)[:300], "retryable": True}
            )
            raise


@celery_app.task(name="app.workers.tasks.extract_editorial_import", bind=True, max_retries=2)
def extract_editorial_import(
    self,
    job_id: str,
    batch_id: str,
    source_url: str,
    source_name: str,
    title_ko: str | None,
    published_date_iso: str | None = None,
):
    """URL bài xã luận/chuyên mục -> tải + làm sạch HTML (không gọi AI ở
    bước này) -> Gemini phân loại từ vựng/ngữ pháp/cấp độ + soạn dàn ý mẫu
    -> đề xuất vào khu chờ duyệt (import_item, kind=editorial_meta/
    vocab_item/grammar_point). editorial_article được tạo ngay (giống
    film/exam_paper — source_url/source_name do admin/candidate cung cấp
    chứ không phải AI suy ra); body_ko/level_estimate/... vẫn NULL cho
    tới khi POST /imports/{id}/confirm ghi vào (app/services/ingestion.py
    apply_editorial_batch)."""
    jid, bid = uuid.UUID(job_id), uuid.UUID(batch_id)
    with Session(_sync_engine) as db:
        batch = db.get(ImportBatch, bid)
        if batch is None:
            publish_job_event(db, jid, status="failed", error={"code": "not_found", "message": "batch not found"})
            return
        try:
            publish_job_event(db, jid, status="running", progress=0.1, step="Đang tải bài viết")
            fetched = ingestion.fetch_article(source_url)
            body_ko, parsed_title, suggested_source_name = fetched.body, fetched.title, fetched.site_name
            resolved_title = title_ko or parsed_title
            published_date = datetime.fromisoformat(published_date_iso) if published_date_iso else None

            article = ingestion.find_or_create_editorial_article(
                db,
                source_url=source_url,
                source_name=source_name,
                title_ko=resolved_title,
                published_date=published_date,
            )
            batch.editorial_article_id = article.id
            batch.status = "extracting"
            db.add(batch)
            db.commit()
            publish_job_event(db, jid, progress=0.4, step="Đang phân tích với Gemini")

            staged, flagged = ingestion.run_editorial_extraction(
                db, batch, body_ko, resolved_title, suggested_source_name, fetched.images
            )

            batch.status = "awaiting_review"
            batch.flagged_count = flagged
            db.add(batch)
            db.commit()
            publish_job_event(
                db,
                jid,
                status="succeeded",
                progress=1.0,
                step="Hoàn tất phân tích bài xã luận",
                result={
                    "import_batch_id": str(bid),
                    "editorial_article_id": str(article.id),
                    "staged": staged,
                    "flagged": flagged,
                },
            )
        except Exception as exc:  # noqa: BLE001
            batch.status = "failed"
            db.add(batch)
            db.commit()
            publish_job_event(
                db, jid, status="failed", error={"code": "internal_error", "message": str(exc), "retryable": True}
            )
            raise


@celery_app.task(name="app.workers.tasks.refresh_editorial_images", bind=True, max_retries=1)
def refresh_editorial_images(self, article_id: str):
    """Re-fetches one already-published article's source page and stores ONLY
    its photos (+captions). Never touches body_ko/vocab/grammar — those were
    reviewed by an admin. Queued lazily by GET /editorials/{id} the first
    time an article imported before the `images` column existed is read
    (images_fetched_at IS NULL). images_fetched_at is stamped even when the
    fetch fails or finds no photo, so a broken source page is tried once, not
    on every page view; an admin can still force a full re-import."""
    aid = uuid.UUID(article_id)
    with Session(_sync_engine) as db:
        article = db.get(EditorialArticle, aid)
        if article is None:
            return {"ok": False, "reason": "not_found"}
        images: list[dict] = []
        try:
            images = ingestion.fetch_article(article.source_url).images
        except Exception as exc:  # noqa: BLE001 — a dead source page must not retry-loop
            print(f"[refresh-images] {article.source_url}: {exc}", flush=True)
        article.images = images
        article.images_fetched_at = datetime.now(timezone.utc)
        db.add(article)
        db.commit()
        return {"ok": True, "images": len(images)}


@celery_app.task(name="app.workers.tasks.generate_study_pack", bind=True, max_retries=0)
def generate_study_pack(self, article_id: str):
    """Builds the beginner study pack (summary, per-sentence translation +
    word breakdown, simplified-Korean paragraphs) for one article and stores
    it on the row. Queued lazily by GET /editorials/{id} (and after an
    import is applied); runs ONCE per (article text, prompt version) —
    every reader afterwards just reads the stored JSON, so Gemini is never
    called per view. `study_updated_at` is touched after every Gemini batch:
    the API treats a 'pending' pack with no heartbeat for a while as dead
    (worker killed by a redeploy) and re-queues it."""
    aid = uuid.UUID(article_id)
    with Session(_sync_engine) as db:
        article = db.get(EditorialArticle, aid)
        if article is None or not (article.body_ko or "").strip():
            return {"ok": False, "reason": "not_found"}

        cleaned = article_extract.clean_article_text(article.body_ko)
        paragraphs = article_extract.split_paragraphs(cleaned)
        if not paragraphs:
            article.study_status = "failed"
            article.study_updated_at = datetime.now(timezone.utc)
            db.add(article)
            db.commit()
            return {"ok": False, "reason": "no_body"}

        article.study_status = "pending"
        article.study_updated_at = datetime.now(timezone.utc)
        db.add(article)
        db.commit()

        def heartbeat(done: int, total: int) -> None:
            article.study_updated_at = datetime.now(timezone.utc)
            db.add(article)
            db.commit()

        try:
            pack = study_pack.build_study_pack(
                article.title_ko,
                paragraphs,
                study_pack.make_gemini_generate(settings.GEMINI_MODEL_STUDY, gemini_client.generate_structured),
                text_sig=study_pack.study_text_sig(cleaned),
                on_progress=heartbeat,
            )
            article.study_pack = pack
            article.study_status = "ready"
        except Exception as exc:  # noqa: BLE001 — recorded, retried later by the API
            print(f"[study-pack] {article.source_url}: {exc}", flush=True)
            db.rollback()
            article = db.get(EditorialArticle, aid)
            article.study_status = "failed"
        article.study_updated_at = datetime.now(timezone.utc)
        db.add(article)
        db.commit()
        return {"ok": article.study_status == "ready", "status": article.study_status}


@celery_app.task(name="app.workers.tasks.apply_import_batch", bind=True, max_retries=2)
def apply_import_batch_task(self, job_id: str, batch_id: str):
    """Ghi các import_item đã confirmed vào bảng chính (content.lesson/
    vocab_item/grammar_point, hoặc corpus.corpus_item kèm embedding —
    lệnh gọi AI duy nhất ở bước confirm, nên bước này chạy qua Celery chứ
    không ghi trực tiếp trong handler FastAPI)."""
    jid, bid = uuid.UUID(job_id), uuid.UUID(batch_id)
    with Session(_sync_engine) as db:
        batch = db.get(ImportBatch, bid)
        if batch is None:
            publish_job_event(db, jid, status="failed", error={"code": "not_found", "message": "batch not found"})
            return
        try:
            publish_job_event(db, jid, status="running", progress=0.3, step="Đang ghi dữ liệu đã duyệt")
            outcome = ingestion.apply_import_batch(db, batch)
            db.commit()
            publish_job_event(
                db, jid, status="succeeded", progress=1.0, step="Hoàn tất xác nhận", result=outcome
            )
            # Prepare the beginner study pack right away, so the first learner
            # to open a freshly published article doesn't wait for it.
            if batch.kind == "editorial_article" and batch.editorial_article_id is not None:
                try:
                    generate_study_pack.delay(str(batch.editorial_article_id))
                except Exception as exc:  # noqa: BLE001 — the API also queues it lazily on first read
                    print(f"[study-pack] could not queue after import: {exc}", flush=True)
        except Exception as exc:  # noqa: BLE001
            db.rollback()
            publish_job_event(
                db, jid, status="failed", error={"code": "internal_error", "message": str(exc), "retryable": True}
            )
            raise


@celery_app.task(name="app.workers.tasks.discover_editorial_candidates")
def discover_editorial_candidates():
    """Celery-beat periodic task (Phase 2 của tính năng đọc xã luận): kéo
    RSS của các nguồn đã đăng ký (editorial.editorial_source), lọc theo
    từ khóa chủ đề, và tạo sẵn editorial_candidate ở trạng thái "new" để
    admin duyệt trong Studio — không bao giờ tự động publish, chỉ tự động
    hoá bước tìm kiếm (xem app/services/ingestion.py discover_editorial_
    candidates). Không có Job/job_id — cùng dạng "chạy nền, không ai chờ
    kết quả trực tiếp" như reset_daily_ai_quota, vì không gọi Gemini."""
    with Session(_sync_engine) as db:
        return ingestion.discover_editorial_candidates(db)


@celery_app.task(name="app.workers.tasks.reset_daily_ai_quota")
def reset_daily_ai_quota():
    """pg_cron-equivalent scheduled task (Celery beat), replaces the
    SDD's Redis TTL-based daily quota reset. No-op scaffold: wire up the
    actual per-learner counter reset once the quota table is added.
    """
    return {"ok": True}


# ------------------------------------------------------------------ paid access --
@celery_app.task(name="app.workers.tasks.reconcile_billing_orders")
def reconcile_billing_orders():
    """Every few minutes: ask payOS about each order of the last 24 hours that is not paid yet and
    unlock the ones whose money arrived (a webhook can fall while the API is being deployed).
    Does nothing while billing is off or payOS is not configured."""
    if not settings.billing_configured:
        return {"skipped": True}
    import asyncio

    from app.services.billing import orders as billing_orders

    return asyncio.run(billing_orders.reconcile_pending_standalone())


# ------------------------------------------------------------ database backup (bucket) --
@celery_app.task(name="app.workers.tasks.backup_database")
def backup_database():
    """Every night: copy every table to the private bucket (services/db_backup) and keep the last
    14 days. Does nothing without the bucket."""
    if audio_store.backend() != "gcs":
        log.info("[backup] the bucket is not configured; nothing to do")
        return {"skipped": True}
    return db_backup.run_backup(_sync_engine, db_backup.GcsStore())


# ---------------------------------------------------------------- audio in the bucket --
@celery_app.task(name="app.workers.tasks.offload_audio_to_gcs")
def offload_audio_to_gcs():
    """Move the files that are still stored in Postgres (a lesson's podcast and narration, the
    recording of a text, a sentence or a word, a lesson picture) to the private bucket, one row at a
    time, then give the freed space back with VACUUM FULL. Started by the worker when it boots with AUDIO_STORAGE=gcs; safe to run again
    (it only touches rows still in the database) and nothing is deleted before its upload succeeded."""
    if audio_store.backend() != "gcs":
        log.info("[offload_audio] the bucket is not configured; nothing to do")
        return {"skipped": True}
    moved_rows = moved_bytes = failed = 0
    audio_has_bytes = lambda m: or_(m.opus_data.isnot(None), m.aac_data.isnot(None))  # noqa: E731
    for model, prefix, table, move, has_bytes in (
        (LectureAudio, "lecture", "audio.lecture_audio", audio_store.offload_row, audio_has_bytes(LectureAudio)),
        (TextAudio, "tts", "audio.text_audio", audio_store.offload_row, audio_has_bytes(TextAudio)),
        (CorpusItemAudio, "word", "audio.corpus_item_audio", audio_store.offload_row, audio_has_bytes(CorpusItemAudio)),
        (VocabItemAudio, "word", "audio.vocab_item_audio", audio_store.offload_row, audio_has_bytes(VocabItemAudio)),
        (SceneImage, "img", "content.scene_image", audio_store.offload_image, SceneImage.data.isnot(None)),
    ):
        with Session(_sync_engine) as db:
            ids = db.execute(
                select(*sa_inspect(model).primary_key)
                .where(model.storage == "db", has_bytes)
                .order_by(model.created_at)
            ).scalars().all()
        in_a_row = 0
        done_here = 0
        for row_id in ids:
            with Session(_sync_engine) as db:
                try:
                    row = db.get(model, row_id)
                    moved = move(row, prefix) if row is not None else 0
                    db.commit()
                except audio_store.StoreError as exc:
                    db.rollback()
                    failed += 1
                    in_a_row += 1
                    log.warning("[offload_audio] %s %s kept in the database: %s", table, row_id, exc)
                    if in_a_row >= 3:  # the bucket or its key is wrong: stop instead of trying them all
                        break
                    continue
                except Exception:  # noqa: BLE001 - one bad row must not stop the rest
                    db.rollback()
                    failed += 1
                    log.exception("[offload_audio] %s %s failed", table, row_id)
                    continue
            in_a_row = 0
            if moved:
                moved_rows += 1
                done_here += 1
                moved_bytes += moved
        if done_here:
            try:  # return the space to the volume: the emptied rows leave dead pages behind
                with _sync_engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
                    conn.exec_driver_sql(f"VACUUM FULL {table}")
            except Exception:  # noqa: BLE001 - not enough room yet: autovacuum will still reuse the space
                log.exception("[offload_audio] VACUUM FULL %s failed", table)
    log.info("[offload_audio] moved %s files (%.1f MB), %s kept in the database", moved_rows, moved_bytes / 1e6, failed)
    return {"moved": moved_rows, "mb": round(moved_bytes / 1e6, 1), "failed": failed}

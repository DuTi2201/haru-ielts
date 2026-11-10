"""Trò chuyện với Haru — a spoken conversation with Gemini Live (app.services.conversation).

POST   /me/conversations                     builds the learner's context, mints a single-use Live
                                              token locked to Haru's setup, opens a session row; the
                                              browser then talks to Gemini directly with that token
                                              (the audio never passes through here).
POST   /me/conversations/{id}/finish         the transcript and duration the browser saw; returns the
                                              report and moves the learner's conversation band.
POST   /me/conversations/{id}/pronunciation  a few of the learner's own sentences (WAV, recorded on
                                              the device) checked by a model that listens; not stored.
GET    /me/conversations/profile             band, what Haru remembers about the learner, time left.
DELETE /me/conversations/profile/facts       forget one remembered fact (?index=) or all of them.
"""
from __future__ import annotations

import base64
import binascii
import logging
import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.api.deps import _problem, ensure_feature, feature_seconds_left, get_current_profile, study_day
from app.core.config import settings
from app.db import get_db
from app.models import ConversationSession, LearnerTalkProfile, Profile
from app.schemas import (
    ConversationFinishOut,
    ConversationFinishRequest,
    ConversationProfileOut,
    ConversationReplyOut,
    ConversationReplyRequest,
    ConversationReportOut,
    ConversationStartOut,
    ConversationStartRequest,
    PronunciationOut,
    PronunciationRequest,
)
from app.services import conversation, conversation_db, gemini_client, pronunciation, talk_profile

log = logging.getLogger(__name__)
router = APIRouter(prefix="/me/conversations", tags=["conversation"])

# below this the session is too short to say anything useful about it
MIN_LEARNER_CHARS = 4


def _session_seconds() -> int:
    return max(60, settings.CONVERSATION_SESSION_SECONDS)


async def _seconds_left(db: AsyncSession, learner_id: uuid.UUID, now: datetime) -> int:
    cap = settings.CONVERSATION_DAILY_MINUTES * 60
    if cap <= 0:
        return _session_seconds()
    used = await conversation_db.seconds_used_today(db, learner_id, session_seconds=_session_seconds(), now=now)
    return max(0, cap - used)


async def seconds_to_show(db: AsyncSession, profile: Profile, feature: str, now: datetime) -> int:
    """What a screen may promise: the day's cap, or less when the pass's minutes or the trial run
    out sooner."""
    left = await _seconds_left(db, profile.id, now)
    allowed = await feature_seconds_left(db, profile, feature)
    return left if allowed is None else min(left, allowed)


def _verdict_ints(entries: list) -> list[int]:
    return [int(e["v"]) for e in entries if isinstance(e, dict) and "v" in e]


async def _talk_row(db: AsyncSession, learner_id: uuid.UUID) -> LearnerTalkProfile:
    row = await conversation_db.get_talk_profile(db, learner_id)
    if row is None:
        row = LearnerTalkProfile(learner_id=learner_id, verdicts=[], facts=[], last_topics=[], sessions=0)
        db.add(row)
    return row


@router.post("", response_model=ConversationStartOut, status_code=status.HTTP_201_CREATED)
async def start_conversation(
    body: ConversationStartRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    profile: Annotated[Profile, Depends(get_current_profile)],
    request: Request = None,  # type: ignore[assignment]  # FastAPI fills it; direct calls in tests may omit it
):
    now = datetime.now(timezone.utc)
    capped = settings.CONVERSATION_DAILY_MINUTES > 0
    left = await _seconds_left(db, profile.id, now)
    if capped and left < 60:
        raise _problem(
            status.HTTP_429_TOO_MANY_REQUESTS,
            f"Hôm nay bạn đã trò chuyện đủ {settings.CONVERSATION_DAILY_MINUTES} phút rồi, mai mình nói tiếp nhé!",
            "daily_limit",
        )
    max_seconds = min(_session_seconds(), left)
    # without a Haru Nói pass: the one-time trial, cut to the minutes left (402 when none are)
    trial = await ensure_feature(db, profile, "talk", request)
    if trial is not None:
        max_seconds = min(max_seconds, trial)

    talk = await conversation_db.get_talk_profile(db, profile.id)
    chosen = await conversation_db.lesson_they_may_open(db, profile, body.lesson_id)
    ctx = await conversation_db.load_context(
        db, profile, remember=body.remember, talk=talk, now=now, lesson_id=chosen
    )
    setup = conversation.live_setup(
        ctx, model=settings.CONVERSATION_LIVE_MODEL, voice=settings.CONVERSATION_VOICE or None
    )
    token = ""
    try:
        if not body.typing:
            token = await run_in_threadpool(
                gemini_client.mint_live_token,
                conversation.token_request(
                    setup, now, session_seconds=max_seconds, slack_seconds=60 if trial is not None else 300
                ),
            )
    except gemini_client.LiveTokenError as exc:
        log.warning("[conversation] live token refused: %s %s", exc.status, exc)
        raise _problem(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Haru chưa kết nối được giọng nói lúc này. Thử lại sau ít phút nhé.",
            "live_unavailable",
        ) from exc

    band = ctx.band or talk_profile.initial_band(ctx.level)
    row = ConversationSession(
        learner_id=profile.id,
        lesson_id=ctx.current.id if ctx.current else None,
        model=settings.CONVERSATION_LIVE_MODEL,
        remember=body.remember,
        band=band,
        allowed_seconds=max_seconds,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)

    return ConversationStartOut(
        session_id=row.id,
        token=token,
        ws_url="" if body.typing else gemini_client.LIVE_WS_URL,
        setup=setup,
        nudges=conversation.NUDGES,
        max_seconds=max_seconds,
        seconds_left_today=left if capped else max_seconds,
        lesson={"id": ctx.current.id, "title": ctx.current.title} if ctx.current else None,
        topic=ctx.topic,
        earlier_lessons=[b.title for b in ctx.earlier],
        hints=conversation.hint_cards(ctx),
        band=band,
        band_label_vi=talk_profile.BANDS[band]["label_vi"],
        answer_goal_vi=talk_profile.answer_step(band)["goal_vi"],
        band_note_vi=talk_profile.BANDS[band]["note_vi"],
    )


# how Haru answers when the learner types: the same teacher, in writing
_TEXT_MODE = (
    "\n\nLúc này người học GÕ chữ, không nói. Bạn trả lời bằng chữ: tối đa 2 câu tiếng Hàn ngắn đúng "
    "trình độ của họ, rồi một câu hỏi. Không dùng markdown, không dịch trừ khi họ nhờ."
)


@router.post("/{session_id}/reply", response_model=ConversationReplyOut)
async def reply_conversation(
    session_id: uuid.UUID,
    body: ConversationReplyRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    profile: Annotated[Profile, Depends(get_current_profile)],
):
    """Haru's next line in a typed chat (the session was started with typing=true)."""
    row = await db.get(ConversationSession, session_id)
    if row is None or row.learner_id != profile.id or getattr(row, "kind", "talk") != "talk":
        raise _problem(status.HTTP_404_NOT_FOUND, "Không tìm thấy buổi trò chuyện này.", "not_found")
    if row.ended_at is not None:
        raise _problem(status.HTTP_409_CONFLICT, "Buổi trò chuyện này đã kết thúc.", "ended")
    turns = conversation.clean_turns([t.model_dump() for t in body.turns])
    ctx = await conversation_db.load_context(
        db, profile, remember=row.remember, now=datetime.now(timezone.utc), lesson_id=row.lesson_id
    )
    system = conversation.build_system_instruction(ctx) + _TEXT_MODE
    try:
        text = await run_in_threadpool(
            gemini_client.generate_chat,
            model=settings.GEMINI_MODEL_STUDY,
            system=system,
            turns=turns[-40:],
        )
    except Exception as exc:  # noqa: BLE001 - any upstream failure is the same to the learner
        log.warning("[conversation] text reply failed: %s", exc)
        raise _problem(
            status.HTTP_503_SERVICE_UNAVAILABLE, "Haru chưa trả lời được. Thử gõ lại nhé.", "reply_unavailable"
        ) from exc
    if not text:
        raise _problem(status.HTTP_503_SERVICE_UNAVAILABLE, "Haru chưa trả lời được. Thử gõ lại nhé.", "reply_unavailable")
    return ConversationReplyOut(text=text)


@router.post("/{session_id}/finish", response_model=ConversationFinishOut, dependencies=[Depends(study_day)])
async def finish_conversation(
    session_id: uuid.UUID,
    body: ConversationFinishRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    profile: Annotated[Profile, Depends(get_current_profile)],
):
    row = await db.get(ConversationSession, session_id)
    if row is None or row.learner_id != profile.id or getattr(row, "kind", "talk") != "talk":
        raise _problem(status.HTTP_404_NOT_FOUND, "Không tìm thấy buổi trò chuyện này.", "not_found")

    turns = conversation.clean_turns([t.model_dump() for t in body.turns])
    learner_chars = sum(len(t["text"]) for t in turns if t["role"] == "learner")
    learner_turns = sum(1 for t in turns if t["role"] == "learner")

    # finishing twice (a retry) returns what was made the first time
    if row.ended_at is not None:
        m = row.metrics or {}
        return ConversationFinishOut(
            session_id=row.id,
            seconds=row.seconds,
            learner_turns=learner_turns,
            report=ConversationReportOut(**row.report) if row.report else None,
            band_before=m.get("band_before"),
            band_after=m.get("band_after"),
            band_note_vi=talk_profile.band_change_note(m["band_before"], m["band_after"])
            if m.get("band_before") and m.get("band_after")
            else None,
        )

    row.ended_at = datetime.now(timezone.utc)
    # the browser's clock, but never more than the session could have run
    row.seconds = min(body.seconds, _session_seconds() + 120)
    row.nudges = body.nudges
    row.turns = turns

    report: dict | None = None
    error_vi: str | None = None
    if learner_chars < MIN_LEARNER_CHARS:
        error_vi = "Buổi này bạn chưa nói gì nhiều nên Haru chưa có gì để nhận xét. Lần sau thử trả lời vài câu nhé!"
    else:
        ctx = await conversation_db.load_context(db, profile, remember=False)
        try:
            out = await run_in_threadpool(
                gemini_client.generate_structured,
                model=settings.CONVERSATION_REPORT_MODEL or settings.GEMINI_MODEL_STUDY,
                prompt=conversation.build_report_prompt(ctx, turns),
                response_schema=conversation.REPORT_SCHEMA,
                prompt_version="conversation-report-v2",
            )
            report = conversation.parse_report(out["text"])
            if not row.remember:
                report["learner_facts"] = []
        except Exception as exc:  # the transcript is kept either way; the report can fail alone
            log.warning("[conversation] report failed for %s: %s", row.id, exc.__class__.__name__)
            error_vi = "Chưa làm được nhận xét cho buổi này. Bản ghi vẫn được lưu."
    row.report = report

    # -- phase 3: measure the session and move the band (two agreeing sessions in a row)
    talk = await _talk_row(db, profile.id)
    band_before = talk_profile.clamp_band(talk.band, row.band or 1)
    metrics = talk_profile.measure(turns, row.seconds, row.nudges)
    v = talk_profile.verdict(metrics, band_before)
    entries = list(talk.verdicts or [])
    if v is not None:
        entries = [*entries, {"s": str(row.id), "v": v}][-talk_profile.KEEP_VERDICTS :]
    band_after = talk_profile.next_band(band_before, _verdict_ints(entries)) if v is not None else band_before
    talk.verdicts = entries
    talk.band = band_after
    talk.sessions = (talk.sessions or 0) + 1
    if report:
        talk.last_topics = report.get("topics_vi") or talk.last_topics or []
        talk.follow_up = report.get("next_time_vi") or talk.follow_up
        if row.remember and report.get("learner_facts"):
            talk.facts = talk_profile.add_facts(list(talk.facts or []), report["learner_facts"], row.ended_at.date().isoformat())
    row.metrics = {**metrics.as_dict(), "verdict": v, "band_before": band_before, "band_after": band_after}
    await db.commit()

    return ConversationFinishOut(
        session_id=row.id,
        seconds=row.seconds,
        learner_turns=learner_turns,
        report=ConversationReportOut(**report) if report else None,
        report_error_vi=error_vi,
        band_before=band_before,
        band_after=band_after,
        band_note_vi=talk_profile.band_change_note(band_before, band_after),
    )


@router.post("/{session_id}/pronunciation", response_model=PronunciationOut, dependencies=[Depends(study_day)])
async def check_pronunciation(
    session_id: uuid.UUID,
    body: PronunciationRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    profile: Annotated[Profile, Depends(get_current_profile)],
):
    row = await db.get(ConversationSession, session_id)
    if row is None or row.learner_id != profile.id or getattr(row, "kind", "talk") != "talk":
        raise _problem(status.HTTP_404_NOT_FOUND, "Không tìm thấy buổi trò chuyện này.", "not_found")
    if row.pronunciation:  # once per session; a retry gets the same answer
        return PronunciationOut(**row.pronunciation)

    clips: list[pronunciation.Clip] = []
    try:
        for c in body.clips:
            try:
                wav = base64.b64decode(c.wav_b64, validate=True)
            except (binascii.Error, ValueError) as exc:
                raise pronunciation.ClipError("bad base64") from exc
            clips.append(pronunciation.Clip(c.index, c.heard.strip(), wav, pronunciation.wav_seconds(wav)))
        pronunciation.check_clips(clips)
    except pronunciation.ClipError as exc:
        raise _problem(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Đoạn ghi âm gửi lên không đúng định dạng hoặc quá dài.",
            "bad_audio",
            str(exc),
        ) from exc

    ctx = await conversation_db.load_context(db, profile, remember=False)
    parts: list = [gemini_client.part_from_bytes(c.wav, "audio/wav") for c in clips]
    parts.append(pronunciation.build_prompt(clips, conversation._level_rules(ctx.level)))
    try:
        out = await run_in_threadpool(
            gemini_client.generate_structured,
            model=settings.CONVERSATION_PRONUNCIATION_MODEL or settings.GEMINI_MODEL_STUDY,
            prompt=parts,
            response_schema=pronunciation.SCHEMA,
            prompt_version="pronunciation-v1",
        )
    except Exception as exc:
        log.warning("[conversation] pronunciation failed for %s: %s", row.id, exc.__class__.__name__)
        raise _problem(
            status.HTTP_502_BAD_GATEWAY,
            "Haru chưa nghe lại được giọng bạn lúc này. Thử lại sau nhé.",
            "pronunciation_failed",
        ) from exc
    result = pronunciation.parse(out["text"], clips)
    row.pronunciation = result

    # a clearly unclear session counts in the band too: re-judge it if it is still the latest verdict
    m = dict(row.metrics or {})
    talk = await conversation_db.get_talk_profile(db, profile.id)
    if result["average"] is not None and m and talk is not None:
        m["pron_avg"] = result["average"]
        entries = list(talk.verdicts or [])
        if entries and entries[-1].get("s") == str(row.id) and m.get("band_before"):
            metrics = talk_profile.TalkMetrics(
                learner_turns=int(m.get("learner_turns", 0)),
                ko_words_per_turn=float(m.get("ko_words_per_turn", 0)),
                vi_share=float(m.get("vi_share", 0)),
                nudges_per_min=float(m.get("nudges_per_min", 0)),
                pron_avg=result["average"],
            )
            v = talk_profile.verdict(metrics, int(m["band_before"]))
            if v is not None and v != entries[-1]["v"]:
                entries[-1] = {"s": str(row.id), "v": v}
                talk.verdicts = entries
                talk.band = talk_profile.next_band(int(m["band_before"]), _verdict_ints(entries))
                m["verdict"] = v
                m["band_after"] = talk.band
        row.metrics = m
    await db.commit()
    return PronunciationOut(**result)


async def _profile_out(db: AsyncSession, profile: Profile, talk: LearnerTalkProfile | None) -> ConversationProfileOut:
    now = datetime.now(timezone.utc)
    if talk is not None and talk.band:
        band = talk_profile.clamp_band(talk.band)
    else:
        band = (await conversation_db.load_context(db, profile, remember=False, talk=talk, now=now)).band or 1
    return ConversationProfileOut(
        band=band,
        band_label_vi=talk_profile.BANDS[band]["label_vi"],
        band_note_vi=talk_profile.BANDS[band]["note_vi"],
        facts=[{"text": str(f.get("text", "")), "at": str(f.get("at", ""))} for f in (talk.facts if talk else []) if f.get("text")],
        sessions=talk.sessions if talk else 0,
        seconds_left_today=await seconds_to_show(db, profile, "talk", now),
        daily_minutes=settings.CONVERSATION_DAILY_MINUTES,
    )


@router.get("/profile", response_model=ConversationProfileOut)
async def get_profile(
    db: Annotated[AsyncSession, Depends(get_db)],
    profile: Annotated[Profile, Depends(get_current_profile)],
):
    return await _profile_out(db, profile, await conversation_db.get_talk_profile(db, profile.id))


@router.delete("/profile/facts", response_model=ConversationProfileOut)
async def forget_facts(
    db: Annotated[AsyncSession, Depends(get_db)],
    profile: Annotated[Profile, Depends(get_current_profile)],
    index: Annotated[int | None, Query(ge=0)] = None,
):
    """Forget one thing Haru remembers (`index` in the list GET /profile returns) or, without
    `index`, all of them. Past session reports keep their own text; only the memory Haru carries
    into the next sessions is cleared."""
    talk = await conversation_db.get_talk_profile(db, profile.id)
    if talk is not None and talk.facts:
        facts = list(talk.facts)
        if index is None:
            facts = []
        elif index < len(facts):
            facts.pop(index)
        talk.facts = facts
        await db.commit()
    return await _profile_out(db, profile, talk)

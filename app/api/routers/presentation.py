"""Trình bày với Haru — say a structured answer in one go and get it marked (app.services.presentation),
fitted to each learner (app.services.present_profile).

POST /me/presentations                         a new round: mode "topic" (a question from the lesson)
                                                or "defense" (the learner's own talk: title + material);
                                                band_shift -1/0/+1 makes this round easier / harder
                                                (a round about a news article is started from
                                                POST /editorials/{id}/presentation, same path: create_round)
GET  /me/presentations                         past rounds that were tried, newest first
GET  /me/presentations/insights                presentation band, focus, the trend of first tries,
                                                studied items used correctly when presenting
GET  /me/presentations/{id}                    the round as it stands
POST /me/presentations/{id}/ideas              "Không biết nói gì?": three idea seeds
POST /me/presentations/{id}/outline            the learner's notes (Vietnamese) -> a keyword outline
POST /me/presentations/{id}/attempts           one try (WAV recorded on the device) -> measured and
                                                marked; up to three per round, audio not kept
POST /me/presentations/{id}/attempts/{i}/answers/{q}
                                                "Hỏi vặn": the spoken answer to follow-up question q
"""
from __future__ import annotations

import base64
import binascii
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Path, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.api.deps import _problem, ensure_feature, get_current_profile, study_day
from app.core.config import settings
from app.db import get_db
from app.models import LearnerTalkProfile, Lesson, PresentationSession, Profile
from app.schemas import (
    PresentAttemptRequest,
    PresentIdeaOut,
    PresentInsightsOut,
    PresentOutlineRequest,
    PresentRowOut,
    PresentSessionOut,
    PresentStartRequest,
)
from app.services import (
    conversation,
    conversation_db,
    gemini_client,
    present_profile,
    presentation,
    presentation_db,
    talk_profile,
)
from app.services.pronunciation import ClipError, wav_seconds

log = logging.getLogger(__name__)
router = APIRouter(prefix="/me/presentations", tags=["presentation"])

ANSWER_TRIES = 2


def _text_model() -> str:
    return settings.PRESENT_TEXT_MODEL or settings.GEMINI_MODEL_STUDY


def _eval_model() -> str:
    return settings.PRESENT_EVAL_MODEL or settings.CONVERSATION_PRONUNCIATION_MODEL or settings.GEMINI_MODEL_STUDY


async def _attempts_today(db: AsyncSession, learner_id: uuid.UUID, now: datetime) -> int:
    since = now - timedelta(hours=24)
    rows = (
        await db.execute(
            select(PresentationSession.attempts).where(
                PresentationSession.learner_id == learner_id,
                PresentationSession.created_at >= now - timedelta(hours=48),
            )
        )
    ).scalars().all()
    n = 0
    for attempts in rows:
        for a in attempts or []:
            try:
                if datetime.fromisoformat(str(a.get("at"))) >= since:
                    n += 1
            except (TypeError, ValueError):
                continue
    return n


async def _left_today(db: AsyncSession, learner_id: uuid.UUID, now: datetime) -> int | None:
    cap = settings.PRESENT_DAILY_ATTEMPTS
    if cap <= 0:
        return None
    return max(0, cap - await _attempts_today(db, learner_id, now))


def _frame(row: PresentationSession) -> presentation.Frame:
    return presentation.frame_for(row.band, row.mode or "topic")


def _plan(row: PresentationSession) -> dict[str, Any]:
    return row.plan if isinstance(row.plan, dict) else {}


async def _out(db: AsyncSession, row: PresentationSession, now: datetime) -> PresentSessionOut:
    frame = _frame(row)
    plan = _plan(row)
    lesson = None
    if row.lesson_id:
        title = (await db.execute(select(Lesson.title).where(Lesson.id == row.lesson_id))).scalar_one_or_none()
        if title:
            lesson = {"id": row.lesson_id, "title": title}
    attempts = list(row.attempts or [])
    focus = plan.get("focus")
    return PresentSessionOut(
        id=row.id,
        mode=row.mode or "topic",
        title=row.title or "",
        material=row.material or "",
        band=frame.band,
        band_label_vi=talk_profile.BANDS[frame.band]["label_vi"],
        base_band=plan.get("base_band"),
        shift=int(plan.get("shift") or 0),
        focus=focus,
        focus_label_vi=presentation.CRITERIA.get(focus) if focus else None,
        targets=plan.get("targets") or [],
        answer_criteria=presentation.ANSWER_CRITERIA,
        frame=frame.as_dict(),
        topic=row.topic,
        lesson=lesson,
        outline=row.outline,
        notes_vi=row.notes_vi or "",
        attempts=attempts,
        attempts_left=max(0, presentation.MAX_ATTEMPTS - len(attempts)),
        attempts_left_today=await _left_today(db, row.learner_id, now),
        criteria=presentation.CRITERIA,
    )


async def _own(db: AsyncSession, session_id: uuid.UUID, profile: Profile) -> PresentationSession:
    row = await db.get(PresentationSession, session_id)
    if row is None or row.learner_id != profile.id:
        raise _problem(status.HTTP_404_NOT_FOUND, "Không tìm thấy lượt trình bày này.", "not_found")
    return row


def _present_base(talk: LearnerTalkProfile | None, ctx_band: int | None, level: int) -> int:
    if talk is not None and talk.present_band:
        return talk_profile.clamp_band(talk.present_band)
    return talk_profile.clamp_band(ctx_band or talk_profile.initial_band(level))


def _wav(b64: str, lo: float, hi: float) -> bytes:
    try:
        try:
            wav = base64.b64decode(b64, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise ClipError("bad base64") from exc
        seconds = wav_seconds(wav)
        if not (lo <= seconds <= hi):
            raise ClipError(f"{seconds:.1f}s is outside {lo}-{hi}s")
    except ClipError as exc:
        raise _problem(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Bản ghi âm không đúng định dạng, quá ngắn hoặc quá dài.",
            "bad_audio",
        ) from exc
    return wav


async def _measure_voiced(wav: bytes, min_voiced: float) -> presentation.AudioMeasure:
    measure = await run_in_threadpool(presentation.measure_audio, wav)
    if measure.voiced_seconds < min_voiced:
        raise _problem(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Haru chưa nghe thấy giọng bạn. Kiểm tra micro rồi nói lại nhé.",
            "no_voice",
        )
    return measure


# ---------------------------------------------------------------- start


@router.post("", response_model=PresentSessionOut, status_code=status.HTTP_201_CREATED)
async def start_presentation(
    db: Annotated[AsyncSession, Depends(get_db)],
    profile: Annotated[Profile, Depends(get_current_profile)],
    body: PresentStartRequest | None = None,
):
    return await create_round(db, profile, body or PresentStartRequest())


async def create_round(
    db: AsyncSession,
    profile: Profile,
    body: PresentStartRequest,
    *,
    first_targets: list[dict[str, Any]] | None = None,
    source: dict[str, Any] | None = None,
) -> PresentSessionOut:
    """A new round, saved. `first_targets` come before the learner's usual studied items (a news
    article's grammar and key terms, app.services.presentation.editorial_handoff); `source` says
    where the round came from (kept in the plan)."""
    now = datetime.now(timezone.utc)
    mode = body.mode
    if mode == "defense" and not body.title.strip():
        raise _problem(status.HTTP_422_UNPROCESSABLE_ENTITY, "Nhập tên đề tài bạn muốn thuyết trình nhé.", "no_title")

    talk = await conversation_db.get_talk_profile(db, profile.id)
    chosen = await conversation_db.lesson_they_may_open(db, profile, body.lesson_id) if mode == "topic" else None
    ctx = await conversation_db.load_context(db, profile, remember=False, talk=talk, now=now, lesson_id=chosen)
    base = _present_base(talk, ctx.band, ctx.level)
    band = talk_profile.clamp_band(base + body.band_shift)
    frame = presentation.frame_for(band, mode)

    knowledge = await presentation_db.load_knowledge(db, profile.id)
    usage = dict(talk.present_usage or {}) if talk is not None else {}
    focus = present_profile.focus_of(await presentation_db.recent_first_tries(db, profile.id))
    round_id = uuid.uuid4()
    targets = present_profile.choose_targets(
        knowledge, usage, band=band, level=ctx.level, mode=mode, seed=str(round_id), now=now
    )
    if first_targets:
        targets = presentation.merge_targets(first_targets, targets)
    plan = {
        "base_band": base,
        "shift": band - base,
        "focus": focus,
        "targets": targets,
        "known": presentation_db.known_patterns(knowledge),
    }
    if source:
        plan["source"] = source

    seen = [
        str((t or {}).get("question_ko") or "")
        for t in (
            await db.execute(
                select(PresentationSession.topic)
                .where(PresentationSession.learner_id == profile.id)
                .order_by(PresentationSession.created_at.desc())
                .limit(15)
            )
        ).scalars().all()
    ]
    level_rules = conversation._level_rules(ctx.level)
    topic: dict[str, Any] | None = None
    try:
        if mode == "defense":
            prompt = presentation.build_defense_prompt(
                level_rules=level_rules, frame=frame, title=body.title, material=body.material, targets=targets
            )
        else:
            prompt = presentation.build_topic_prompt(
                level_rules=level_rules,
                frame=frame,
                topic=ctx.topic,
                lesson_title=ctx.current.title if ctx.current else None,
                words=[(w.ko, w.vi) for w in ctx.words],
                patterns=[p.pattern for p in ctx.patterns],
                seen=seen,
                focus_hint=present_profile.FOCUS_TOPIC_HINT.get(focus) if focus else None,
                targets=targets,
            )
        out = await run_in_threadpool(
            gemini_client.generate_structured,
            model=_text_model(),
            prompt=prompt,
            response_schema=presentation.TOPIC_SCHEMA,
            prompt_version="present-topic-v2",
        )
        topic = presentation.parse_topic(out["text"], max_words=8 if mode == "defense" else 6)
    except Exception as exc:  # a topic from the bank (or the learner's own title) is fine
        log.warning("[presentation] topic failed: %s", exc.__class__.__name__)
    if mode == "defense":
        if topic is None:
            title = body.title.strip()
            topic = {"question_ko": title, "question_vi": title, "angle_vi": "", "words": [], "source": "title"}
    elif topic is None or topic["question_ko"] in seen:
        topic = presentation.fallback_topic(band, seen, seed=len(seen))

    row = PresentationSession(
        id=round_id,
        learner_id=profile.id,
        lesson_id=ctx.current.id if ctx.current and mode == "topic" else None,
        band=band,
        level=ctx.level,
        topic=topic,
        attempts=[],
        mode=mode,
        title=body.title.strip()[:200],
        material=body.material.strip()[:6000],
        plan=plan,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return await _out(db, row, now)


# ---------------------------------------------------------------- looking back


@router.get("", response_model=list[PresentRowOut])
async def list_presentations(
    db: Annotated[AsyncSession, Depends(get_db)],
    profile: Annotated[Profile, Depends(get_current_profile)],
    limit: Annotated[int, Query(ge=1, le=100)] = 30,
):
    rows = (
        await db.execute(
            select(PresentationSession)
            .where(PresentationSession.learner_id == profile.id)
            .order_by(PresentationSession.created_at.desc())
            .limit(limit * 3)
        )
    ).scalars().all()
    out = []
    for r in rows:
        attempts = list(r.attempts or [])
        if not attempts:
            continue
        overalls = [float((a.get("eval") or {}).get("overall") or 0) for a in attempts]
        out.append(
            PresentRowOut(
                id=r.id,
                created_at=r.created_at,
                mode=r.mode or "topic",
                title_ko=str((r.topic or {}).get("question_ko") or r.title or ""),
                band=r.band,
                tries=len(attempts),
                first_overall=overalls[0],
                best_overall=max(overalls),
                answers=sum(len(a.get("answers") or {}) for a in attempts),
            )
        )
        if len(out) >= limit:
            break
    return out


@router.get("/insights", response_model=PresentInsightsOut)
async def get_insights(
    db: Annotated[AsyncSession, Depends(get_db)],
    profile: Annotated[Profile, Depends(get_current_profile)],
):
    talk = await conversation_db.get_talk_profile(db, profile.id)
    rows = (
        await db.execute(
            select(PresentationSession)
            .where(PresentationSession.learner_id == profile.id)
            .order_by(PresentationSession.created_at.desc())
            .limit(60)
        )
    ).scalars().all()
    tried = [r for r in rows if r.attempts]
    points = []
    answer_scores: list[float] = []
    for r in reversed(tried[:20]):
        first = r.attempts[0] or {}
        ev = first.get("eval") or {}
        points.append({"at": first.get("at"), "overall": ev.get("overall"), "scores": ev.get("scores") or {}, "band": r.band, "mode": r.mode})
    for r in tried:
        for a in r.attempts:
            answer_scores += [float(x.get("overall") or 0) for x in (a.get("answers") or {}).values()]
    if talk is not None and talk.present_band:
        band = talk_profile.clamp_band(talk.present_band)
    else:
        ctx = await conversation_db.load_context(db, profile, remember=False, talk=talk)
        band = _present_base(talk, ctx.band, ctx.level)
    focus = present_profile.focus_of([((r.attempts[0] or {}).get("eval") or {}).get("scores") or {} for r in tried[:8]])
    m = present_profile.mastery(dict(talk.present_usage or {}) if talk is not None else {})
    bests = [max(float((a.get("eval") or {}).get("overall") or 0) for a in r.attempts) for r in tried]
    return PresentInsightsOut(
        rounds=len(tried),
        present_band=band,
        band_label_vi=talk_profile.BANDS[band]["label_vi"],
        band_rubric_vi={presentation.CRITERIA[k]: v for k, v in present_profile.BAND_RUBRIC[band].items()},
        focus=focus,
        focus_label_vi=presentation.CRITERIA.get(focus) if focus else None,
        points=points,
        best_overall=max(bests) if bests else None,
        mastered=m["mastered"],
        practicing=m["practicing"],
        answer_avg=round(sum(answer_scores) / len(answer_scores), 1) if answer_scores else None,
    )


@router.get("/{session_id}", response_model=PresentSessionOut)
async def get_presentation(
    session_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    profile: Annotated[Profile, Depends(get_current_profile)],
):
    return await _out(db, await _own(db, session_id, profile), datetime.now(timezone.utc))


# ---------------------------------------------------------------- preparing


@router.post("/{session_id}/ideas", response_model=list[PresentIdeaOut])
async def idea_seeds(
    session_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    profile: Annotated[Profile, Depends(get_current_profile)],
):
    row = await _own(db, session_id, profile)
    try:
        out = await run_in_threadpool(
            gemini_client.generate_structured,
            model=_text_model(),
            prompt=presentation.build_ideas_prompt(
                level_rules=conversation._level_rules(row.level),
                frame=_frame(row),
                question_ko=row.topic["question_ko"],
                material=row.material or "",
            ),
            response_schema=presentation.IDEAS_SCHEMA,
            prompt_version="present-ideas-v1",
        )
        seeds = presentation.parse_ideas(out["text"])
    except Exception as exc:
        log.warning("[presentation] ideas failed for %s: %s", row.id, exc.__class__.__name__)
        seeds = []
    if not seeds:
        raise _problem(status.HTTP_502_BAD_GATEWAY, "Haru chưa nghĩ ra gợi ý lúc này. Thử lại sau nhé.", "ideas_failed")
    return seeds


@router.post("/{session_id}/outline", response_model=PresentSessionOut)
async def make_outline(
    session_id: uuid.UUID,
    body: PresentOutlineRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    profile: Annotated[Profile, Depends(get_current_profile)],
):
    row = await _own(db, session_id, profile)
    frame = _frame(row)
    targets = _plan(row).get("targets") or []
    try:
        out = await run_in_threadpool(
            gemini_client.generate_structured,
            model=_text_model(),
            prompt=presentation.build_outline_prompt(
                level_rules=conversation._level_rules(row.level),
                frame=frame,
                question_ko=row.topic["question_ko"],
                notes_vi=body.notes_vi,
                targets=targets,
                material=row.material or "",
            ),
            response_schema=presentation.OUTLINE_SCHEMA,
            prompt_version="present-outline-v2",
        )
    except Exception as exc:
        log.warning("[presentation] outline failed for %s: %s", row.id, exc.__class__.__name__)
        raise _problem(status.HTTP_502_BAD_GATEWAY, "Haru chưa làm được dàn ý lúc này. Thử lại sau nhé.", "outline_failed") from exc
    row.notes_vi = body.notes_vi.strip()
    row.outline = presentation.parse_outline(out["text"], frame, targets)
    await db.commit()
    return await _out(db, row, datetime.now(timezone.utc))


# ---------------------------------------------------------------- speaking


async def _after_marking(db: AsyncSession, row: PresentationSession, attempt: dict[str, Any], learner_id: uuid.UUID) -> None:
    """Move the presentation band on a round's first try (not on an eased / harder round), and
    record which studied items were used correctly."""
    plan = _plan(row)
    talk = await conversation_db.get_talk_profile(db, learner_id)
    if talk is None:
        talk = LearnerTalkProfile(learner_id=learner_id, verdicts=[], facts=[], last_topics=[], sessions=0,
                                  present_verdicts=[], present_usage={})
        db.add(talk)
    targets = plan.get("targets") or []
    if targets:
        talk.present_usage = present_profile.update_usage(
            dict(talk.present_usage or {}), targets, attempt["eval"].get("targets_used") or [], str(row.id), attempt["at"]
        )
    if attempt["index"] == 0 and not plan.get("shift"):
        base = talk_profile.clamp_band(plan.get("base_band") or row.band)
        v = present_profile.verdict(attempt["eval"], attempt["metrics"], parts_total=len(_frame(row).parts))
        if v is not None:
            entries = [*(talk.present_verdicts or []), {"s": str(row.id), "v": v}][-present_profile.KEEP_VERDICTS :]
            talk.present_verdicts = entries
            talk.present_band = present_profile.next_present_band(base, [int(e["v"]) for e in entries if "v" in e])
            attempt["verdict"] = v
            attempt["band_after"] = talk.present_band
        elif not talk.present_band:
            talk.present_band = base


@router.post("/{session_id}/attempts", response_model=PresentSessionOut, dependencies=[Depends(study_day)])
async def add_attempt(
    session_id: uuid.UUID,
    body: PresentAttemptRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    profile: Annotated[Profile, Depends(get_current_profile)],
    request: Request = None,  # type: ignore[assignment]  # FastAPI fills it; direct calls in tests may omit it
):
    now = datetime.now(timezone.utc)
    row = await _own(db, session_id, profile)
    attempts = list(row.attempts or [])
    if len(attempts) >= presentation.MAX_ATTEMPTS:
        raise _problem(
            status.HTTP_409_CONFLICT,
            f"Mỗi đề nói tối đa {presentation.MAX_ATTEMPTS} lần. Lấy đề mới để luyện tiếp nhé!",
            "attempts_used",
        )
    left = await _left_today(db, profile.id, now)
    if left is not None and left <= 0:
        raise _problem(
            status.HTTP_429_TOO_MANY_REQUESTS,
            f"Hôm nay bạn đã trình bày đủ {settings.PRESENT_DAILY_ATTEMPTS} lần rồi, mai luyện tiếp nhé!",
            "daily_limit",
        )
    await ensure_feature(db, profile, "present", request)
    frame = _frame(row)
    plan = _plan(row)
    wav = _wav(body.wav_b64, presentation.MIN_SECONDS, frame.max_seconds + 5)
    measure = await _measure_voiced(wav, 2.0)

    targets = plan.get("targets") or []
    prompt = presentation.build_eval_prompt(
        level_rules=conversation._level_rules(row.level),
        frame=frame,
        question_ko=row.topic["question_ko"],
        measure=measure,
        outline=row.outline,
        previous=attempts[-1] if attempts else None,
        targets=targets,
        known=plan.get("known") or [],
        focus=plan.get("focus"),
        material=row.material or "",
    )
    try:
        out = await run_in_threadpool(
            gemini_client.generate_structured,
            model=_eval_model(),
            prompt=[gemini_client.part_from_bytes(wav, "audio/wav"), prompt],
            response_schema=presentation.EVAL_SCHEMA,
            prompt_version="present-eval-v2",
        )
        marked = presentation.parse_eval(out["text"], frame, measure, targets)
    except Exception as exc:
        log.warning("[presentation] marking failed for %s: %s", row.id, exc.__class__.__name__)
        raise _problem(
            status.HTTP_502_BAD_GATEWAY,
            "Haru chưa chấm được bài nói lúc này. Thử nói lại sau ít phút nhé.",
            "eval_failed",
        ) from exc
    attempt = {"index": len(attempts), "at": now.isoformat(), **marked, "answers": {}}
    await _after_marking(db, row, attempt, profile.id)
    row.attempts = [*attempts, attempt]
    await db.commit()
    return await _out(db, row, now)


@router.post("/{session_id}/attempts/{index}/answers/{q}", response_model=PresentSessionOut)
async def answer_follow_up(
    session_id: uuid.UUID,
    index: Annotated[int, Path(ge=0, le=presentation.MAX_ATTEMPTS - 1)],
    q: Annotated[int, Path(ge=0, le=4)],
    body: PresentAttemptRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    profile: Annotated[Profile, Depends(get_current_profile)],
):
    now = datetime.now(timezone.utc)
    row = await _own(db, session_id, profile)
    attempts = list(row.attempts or [])
    if index >= len(attempts):
        raise _problem(status.HTTP_404_NOT_FOUND, "Không tìm thấy lần nói này.", "not_found")
    attempt = dict(attempts[index])
    questions = (attempt.get("eval") or {}).get("follow_ups") or []
    if q >= len(questions):
        raise _problem(status.HTTP_404_NOT_FOUND, "Không tìm thấy câu hỏi này.", "not_found")
    answers = dict(attempt.get("answers") or {})
    tries = int((answers.get(str(q)) or {}).get("tries") or 0)
    if tries >= ANSWER_TRIES:
        raise _problem(status.HTTP_409_CONFLICT, f"Mỗi câu hỏi trả lời tối đa {ANSWER_TRIES} lần.", "answers_used")

    wav = _wav(body.wav_b64, presentation.ANSWER_MIN_SECONDS, presentation.ANSWER_MAX_SECONDS + 5)
    measure = await _measure_voiced(wav, 1.0)
    try:
        out = await run_in_threadpool(
            gemini_client.generate_structured,
            model=_eval_model(),
            prompt=[
                gemini_client.part_from_bytes(wav, "audio/wav"),
                presentation.build_answer_prompt(
                    level_rules=conversation._level_rules(row.level),
                    band=row.band,
                    question_ko=questions[q]["q_ko"],
                    talk_ko=(attempt.get("eval") or {}).get("transcript_ko") or "",
                    measure=measure,
                    known=_plan(row).get("known") or [],
                ),
            ],
            response_schema=presentation.ANSWER_SCHEMA,
            prompt_version="present-answer-v1",
        )
        result = presentation.parse_answer(out["text"], measure)
    except Exception as exc:
        log.warning("[presentation] answer marking failed for %s: %s", row.id, exc.__class__.__name__)
        raise _problem(
            status.HTTP_502_BAD_GATEWAY,
            "Haru chưa chấm được câu trả lời lúc này. Thử lại sau nhé.",
            "eval_failed",
        ) from exc
    answers[str(q)] = {**result, "tries": tries + 1, "at": now.isoformat()}
    attempt["answers"] = answers
    attempts[index] = attempt
    row.attempts = attempts
    await db.commit()
    return await _out(db, row, now)

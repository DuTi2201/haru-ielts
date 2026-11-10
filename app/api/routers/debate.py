"""Tranh luận · Đàm phán · Phản biện with Haru (app.services.debate) — Gemini Live role-plays.

GET  /me/debates/options       the learner's debate band and tier, the scenarios for it, phrases,
                                criteria and what a 4 means; time left today (shared with the talks)
POST /me/debates               start: a scenario (or the learner's own motion) -> a single-use Live
                                token locked to Haru's role; the browser talks to Gemini directly
POST /me/debates/{id}/finish   the transcript the browser saw -> the report; moves the debate band
GET  /me/debates               past sessions, newest first
GET  /me/debates/{id}          one session: report and transcript
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.api.deps import _problem, ensure_feature, get_current_profile, study_day
from app.core.config import settings
from app.db import get_db
from app.models import ConversationSession, LearnerTalkProfile, Profile
from app.schemas import (
    ConversationFinishRequest,
    DebateDetailOut,
    DebateFinishOut,
    DebateOptionsOut,
    DebateReportOut,
    DebateRowOut,
    DebateStartOut,
    DebateStartRequest,
)
from app.services import conversation, conversation_db, debate, gemini_client, presentation_db, talk_profile
from app.api.routers.conversation import _seconds_left, seconds_to_show

log = logging.getLogger(__name__)
router = APIRouter(prefix="/me/debates", tags=["debate"])


def _base_band(talk: LearnerTalkProfile | None, ctx_band: int | None, level: int) -> int:
    """The debate band; before any debate, the presentation band, then the talk band, then the level."""
    if talk is not None and talk.debate_band:
        return talk_profile.clamp_band(talk.debate_band)
    if talk is not None and talk.present_band:
        return talk_profile.clamp_band(talk.present_band)
    return talk_profile.clamp_band(ctx_band or talk_profile.initial_band(level))


def _scenario_of(row: ConversationSession) -> debate.Scenario | None:
    sc = row.scenario if isinstance(row.scenario, dict) else {}
    if sc.get("id") == "custom":
        return debate.custom_debate(str(sc.get("motion") or ""), row.band)
    return debate.BY_ID.get(str(sc.get("id")))


def _phrases(kind: str, band: int) -> list[dict[str, str]]:
    return [{"ko": k, "vi": v} for k, v in debate.PHRASES[kind][debate.tier_of(band)]]


@router.get("/options", response_model=DebateOptionsOut)
async def options(
    db: Annotated[AsyncSession, Depends(get_db)],
    profile: Annotated[Profile, Depends(get_current_profile)],
):
    now = datetime.now(timezone.utc)
    talk = await conversation_db.get_talk_profile(db, profile.id)
    ctx = await conversation_db.load_context(db, profile, remember=False, talk=talk, now=now)
    band = _base_band(talk, ctx.band, ctx.level)
    tier = debate.tier_of(band)
    return DebateOptionsOut(
        band=band,
        band_label_vi=talk_profile.BANDS[band]["label_vi"],
        tier=tier,
        kinds=debate.KINDS,
        scenarios=[s.public() for s in debate.SCENARIOS if s.tier == tier],
        phrases={k: _phrases(k, band) for k in debate.KINDS},
        criteria=debate.CRITERIA,
        rubric={k: debate.RUBRIC[k][tier] for k in debate.KINDS},
        seconds_left_today=await seconds_to_show(db, profile, "debate", now),
        daily_minutes=settings.CONVERSATION_DAILY_MINUTES,
    )


@router.post("", response_model=DebateStartOut, status_code=status.HTTP_201_CREATED)
async def start_debate(
    body: DebateStartRequest,
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
            f"Hôm nay bạn đã nói với Haru đủ {settings.CONVERSATION_DAILY_MINUTES} phút rồi, mai luyện tiếp nhé!",
            "daily_limit",
        )
    trial = await ensure_feature(db, profile, "debate", request)  # the one-time trial's seconds left, or None
    talk = await conversation_db.get_talk_profile(db, profile.id)
    ctx = await conversation_db.load_context(db, profile, remember=False, talk=talk, now=now)
    band = talk_profile.clamp_band(_base_band(talk, ctx.band, ctx.level) + body.band_shift)

    if body.kind == "debate" and body.motion.strip():
        sc = debate.custom_debate(body.motion, band)
    else:
        sc = debate.BY_ID.get(body.scenario_id or "")
        if sc is None or sc.kind != body.kind:
            raise _problem(status.HTTP_422_UNPROCESSABLE_ENTITY, "Chọn một tình huống nhé.", "no_scenario")
    side = body.side if sc.kind == "debate" else None
    knowledge = await presentation_db.load_knowledge(db, profile.id)
    setup_in = debate.Setup(
        scenario=sc, band=band, level_rules=conversation._level_rules(ctx.level), side_en=side,
        known=presentation_db.known_patterns(knowledge),
    )
    max_seconds = min(debate.MAX_SECONDS, settings.CONVERSATION_SESSION_SECONDS, left if capped else debate.MAX_SECONDS)
    if trial is not None:
        max_seconds = min(max_seconds, trial)
    setup = conversation.live_setup(
        None,
        model=settings.CONVERSATION_LIVE_MODEL,
        voice=settings.CONVERSATION_VOICE or None,
        instruction=debate.build_system_instruction(setup_in),
    )
    try:
        token = await run_in_threadpool(
            gemini_client.mint_live_token,
            conversation.token_request(
                setup, now, session_seconds=max_seconds, slack_seconds=60 if trial is not None else 300
            ),
        )
    except gemini_client.LiveTokenError as exc:
        log.warning("[debate] live token refused: %s %s", exc.status, exc)
        raise _problem(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Haru chưa kết nối được giọng nói lúc này. Thử lại sau ít phút nhé.",
            "live_unavailable",
        ) from exc

    row = ConversationSession(
        id=uuid.uuid4(),
        learner_id=profile.id,
        lesson_id=None,
        model=settings.CONVERSATION_LIVE_MODEL,
        remember=False,
        band=band,
        kind="debate",
        allowed_seconds=max_seconds,
        scenario={"id": sc.id, "kind": sc.kind, "side": side, "motion": sc.opener_en if sc.id == "custom" else None,
                  "shift": body.band_shift},
    )
    db.add(row)
    await db.commit()
    return DebateStartOut(
        session_id=row.id,
        token=token,
        ws_url=gemini_client.LIVE_WS_URL,
        setup=setup,
        nudges=debate.nudges(sc),
        max_seconds=max_seconds,
        seconds_left_today=left if capped else max_seconds,
        band=band,
        band_label_vi=talk_profile.BANDS[band]["label_vi"],
        scenario=sc.public(),
        side=side,
        phrases=_phrases(sc.kind, band),
        criteria=debate.CRITERIA[sc.kind],
    )


async def _own(db: AsyncSession, session_id: uuid.UUID, profile: Profile) -> ConversationSession:
    row = await db.get(ConversationSession, session_id)
    if row is None or row.learner_id != profile.id or getattr(row, "kind", "talk") != "debate":
        raise _problem(status.HTTP_404_NOT_FOUND, "Không tìm thấy buổi này.", "not_found")
    return row


def _report_out(row: ConversationSession, sc: debate.Scenario | None) -> DebateReportOut | None:
    if not isinstance(row.report, dict) or not row.report:
        return None
    return DebateReportOut(**row.report, flaw_vi=sc.flaw_vi if sc and sc.kind == "critique" else "")


@router.post("/{session_id}/finish", response_model=DebateFinishOut, dependencies=[Depends(study_day)])
async def finish_debate(
    session_id: uuid.UUID,
    body: ConversationFinishRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    profile: Annotated[Profile, Depends(get_current_profile)],
):
    row = await _own(db, session_id, profile)
    sc = _scenario_of(row)
    kind = sc.kind if sc else "debate"
    turns = conversation.clean_turns([t.model_dump() for t in body.turns])
    learner_turns = sum(1 for t in turns if t["role"] == "learner")
    m = row.metrics or {}
    if row.ended_at is not None:  # a retry gets what was made the first time
        return DebateFinishOut(
            session_id=row.id, seconds=row.seconds, learner_turns=learner_turns, report=_report_out(row, sc),
            band_before=m.get("band_before"), band_after=m.get("band_after"), criteria=debate.CRITERIA[kind],
        )
    row.ended_at = datetime.now(timezone.utc)
    row.seconds = min(body.seconds, debate.MAX_SECONDS + 120)
    row.nudges = body.nudges
    row.turns = turns

    report: dict[str, Any] | None = None
    error_vi: str | None = None
    learner_chars = sum(len(t["text"]) for t in turns if t["role"] == "learner")
    if sc is None or learner_chars < debate.MIN_LEARNER_CHARS:
        error_vi = "Buổi này bạn chưa nói gì nhiều nên Haru chưa có gì để nhận xét. Lần sau thử nói vài lượt nhé!"
    else:
        ctx = await conversation_db.load_context(db, profile, remember=False)
        setup_in = debate.Setup(
            scenario=sc, band=row.band or 1, level_rules=conversation._level_rules(ctx.level),
            side_en=(row.scenario or {}).get("side"),
        )
        try:
            out = await run_in_threadpool(
                gemini_client.generate_structured,
                model=settings.CONVERSATION_REPORT_MODEL or settings.GEMINI_MODEL_STUDY,
                prompt=debate.build_report_prompt(setup_in, turns),
                response_schema=debate.report_schema(kind),
                prompt_version="debate-report-v1",
            )
            report = debate.parse_report(out["text"], kind)
        except Exception as exc:  # the transcript is kept either way
            log.warning("[debate] report failed for %s: %s", row.id, exc.__class__.__name__)
            error_vi = "Chưa làm được nhận xét cho buổi này. Bản ghi vẫn được lưu."
    row.report = report

    # the debate band moves after two agreeing sessions (eased / harder ones don't count)
    talk = await conversation_db.get_talk_profile(db, profile.id)
    if talk is None:
        talk = LearnerTalkProfile(learner_id=profile.id, verdicts=[], facts=[], last_topics=[], sessions=0,
                                  present_verdicts=[], present_usage={}, debate_verdicts=[])
        db.add(talk)
    shift = int((row.scenario or {}).get("shift") or 0)
    before = talk_profile.clamp_band(talk.debate_band or (row.band or 1) - shift)
    after = before
    v = debate.verdict(report, learner_turns) if report and not shift else None
    if v is not None:
        entries = [*(talk.debate_verdicts or []), {"s": str(row.id), "v": v}][-6:]
        talk.debate_verdicts = entries
        after = talk_profile.next_band(before, [int(e["v"]) for e in entries if "v" in e])
    talk.debate_band = after
    row.metrics = {"learner_turns": learner_turns, "verdict": v, "band_before": before, "band_after": after}
    await db.commit()
    return DebateFinishOut(
        session_id=row.id, seconds=row.seconds, learner_turns=learner_turns, report=_report_out(row, sc),
        report_error_vi=error_vi, band_before=before, band_after=after, criteria=debate.CRITERIA[kind],
    )


@router.get("", response_model=list[DebateRowOut])
async def list_debates(
    db: Annotated[AsyncSession, Depends(get_db)],
    profile: Annotated[Profile, Depends(get_current_profile)],
    limit: Annotated[int, Query(ge=1, le=100)] = 30,
):
    rows = (
        await db.execute(
            select(ConversationSession)
            .where(
                ConversationSession.learner_id == profile.id,
                ConversationSession.kind == "debate",
                ConversationSession.ended_at.is_not(None),
            )
            .order_by(ConversationSession.started_at.desc())
            .limit(limit)
        )
    ).scalars().all()
    out = []
    for r in rows:
        sc = _scenario_of(r)
        rep = r.report if isinstance(r.report, dict) else {}
        out.append(
            DebateRowOut(
                id=r.id, started_at=r.started_at, seconds=r.seconds, kind=sc.kind if sc else "debate",
                title_vi=sc.title_vi if sc else "", band=r.band, overall=rep.get("overall"),
                goal_reached=bool(rep.get("goal_reached")),
            )
        )
    return out


@router.get("/{session_id}", response_model=DebateDetailOut)
async def get_debate(
    session_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    profile: Annotated[Profile, Depends(get_current_profile)],
):
    row = await _own(db, session_id, profile)
    sc = _scenario_of(row)
    kind = sc.kind if sc else "debate"
    m = row.metrics or {}
    return DebateDetailOut(
        session_id=row.id, seconds=row.seconds, learner_turns=int(m.get("learner_turns") or 0),
        report=_report_out(row, sc), band_before=m.get("band_before"), band_after=m.get("band_after"),
        criteria=debate.CRITERIA[kind], started_at=row.started_at, kind=kind, title_vi=sc.title_vi if sc else "",
        side=(row.scenario or {}).get("side"), turns=[t for t in (row.turns or []) if t.get("role") in ("learner", "haru")],
    )

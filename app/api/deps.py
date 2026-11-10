import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import Depends, HTTPException, Query, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import decode_token, issued_before
from app.db import get_db
from app.models import ConversationSession, Entitlement, Job, PresentationSession, Profile
from app.services import abuse
from app.services.billing import access as billing_access
from app.services.billing import catalog as billing_catalog
from app.services.billing import features as billing_features
from app.services.billing import settings_db as billing_settings

bearer_scheme = HTTPBearer(auto_error=False)


def _problem(status_code: int, title: str, code: str, detail: str | None = None) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"type": "about:blank", "title": title, "status": status_code, "code": code, "detail": detail},
    )


async def get_current_claims(
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> dict:
    if creds is None:
        raise _problem(status.HTTP_401_UNAUTHORIZED, "Missing bearer token", "unauthenticated")
    try:
        return decode_token(creds.credentials)
    except ValueError as exc:
        raise _problem(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token", "invalid_token") from exc


def account_disabled() -> HTTPException:
    return _problem(
        status.HTTP_401_UNAUTHORIZED, "Tài khoản đã bị khoá", "account_disabled", "Liên hệ người quản trị để mở lại."
    )


async def profile_for_claims(db: AsyncSession, claims: dict) -> Profile:
    """The account a verified token speaks for, if it may still act: the account exists, is not
    locked, and the token was not issued before the last password reset / change."""
    profile = await db.get(Profile, uuid.UUID(claims["sub"]))
    if profile is None:
        raise _problem(status.HTTP_401_UNAUTHORIZED, "Profile not found", "unauthenticated")
    if profile.disabled:
        raise account_disabled()
    if issued_before(claims, profile.tokens_valid_after):
        raise _problem(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token", "invalid_token")
    return profile


async def get_current_profile(
    claims: Annotated[dict, Depends(get_current_claims)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Profile:
    return await profile_for_claims(db, claims)


async def get_optional_profile(
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Profile | None:
    """Like get_current_profile, but a caller with no (or an expired) token is
    simply anonymous — None, never a 401. For public routes that only
    personalise the answer when they know who is asking."""
    if creds is None:
        return None
    try:
        claims = decode_token(creds.credentials)
        return await profile_for_claims(db, claims)
    except (ValueError, KeyError, HTTPException):  # a locked account or a stale token is anonymous here
        return None


async def get_current_profile_sse(
    db: Annotated[AsyncSession, Depends(get_db)],
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)] = None,
    token: Annotated[str | None, Query()] = None,
) -> Profile:
    """Same as get_current_profile, but ALSO accepts the JWT as a `?token=`
    query param. Only use this on the SSE events route: the browser's
    native EventSource cannot set an Authorization header, so this is the
    one endpoint where a token-in-URL is the pragmatic trade-off (short-
    lived access token, HTTPS-only, not logged server-side by this app).
    """
    raw = creds.credentials if creds else token
    if not raw:
        raise _problem(status.HTTP_401_UNAUTHORIZED, "Missing bearer token", "unauthenticated")
    try:
        claims = decode_token(raw)
    except ValueError as exc:
        raise _problem(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token", "invalid_token") from exc
    return await profile_for_claims(db, claims)


def require_role(*roles: str):
    async def _dep(profile: Annotated[Profile, Depends(get_current_profile)]) -> Profile:
        if profile.role not in roles:
            raise _problem(
                status.HTTP_403_FORBIDDEN, "Insufficient role", "forbidden", f"requires one of {roles}"
            )
        return profile

    return _dep


# ------------------------------------------------------------- paid access --
def payment_required(needs: str, detail: str, unlock_with: list[str] | None = None) -> HTTPException:
    """402: the caller is signed in but has not bought this. `needs` is "lesson_pack" or
    "exam_pass"; `unlock_with` lists the product codes that open it (see GET /billing/catalog)."""
    return HTTPException(
        status_code=status.HTTP_402_PAYMENT_REQUIRED,
        detail={
            "type": "about:blank",
            "title": "Cần mở khoá để dùng phần này",
            "status": status.HTTP_402_PAYMENT_REQUIRED,
            "code": "payment_required",
            "detail": detail,
            "needs": needs,
            "unlock_with": unlock_with or [],
        },
    )


async def get_access(
    db: Annotated[AsyncSession, Depends(get_db)],
    profile: Annotated[Profile | None, Depends(get_optional_profile)],
) -> billing_access.Access:
    """What the caller may open (everything while billing is off)."""
    return await billing_access.load_access(db, profile)


async def require_exam_pass(
    db: Annotated[AsyncSession, Depends(get_db)],
    profile: Annotated[Profile, Depends(get_current_profile)],
) -> Profile:
    """The model-marked practice (writing drills, exam drill) belongs to the exam pass."""
    held = await billing_access.load_access(db, profile)
    if not held.can_use_exam_pass():
        raise payment_required(
            billing_catalog.EXAM_PASS,
            "Phần luyện thi có AI chấm thuộc Pass Luyện thi.",
            [p.code for p in billing_catalog.listed() if p.kind == billing_catalog.EXAM_PASS],
        )
    return profile


async def trial_used(db: AsyncSession, profile_id: uuid.UUID, feature: str) -> int:
    """How much of the one-time trial is used, for life: live SECONDS (Trò chuyện + Tranh luận
    together; a session never finished counts as all it was allowed), or presentation tries marked."""
    if feature in billing_features.LIVE_FEATURES:
        rows = (
            await db.execute(
                select(ConversationSession.seconds, ConversationSession.allowed_seconds, ConversationSession.ended_at).where(
                    ConversationSession.learner_id == profile_id,
                    ConversationSession.kind.in_(billing_features.LIVE_FEATURES),
                )
            )
        ).all()
        used = 0
        for seconds, allowed, ended in rows:
            if ended is not None:
                used += min(int(seconds or 0), int(allowed)) if allowed else int(seconds or 0)
            else:
                used += int(allowed or 0)
        return used
    if feature == "present":
        rows = (
            await db.execute(select(PresentationSession.attempts).where(PresentationSession.learner_id == profile_id))
        ).scalars().all()
        return sum(len(a or []) for a in rows)
    return 0


async def live_seconds_since(db: AsyncSession, profile_id: uuid.UUID, since: datetime) -> int:
    """Live seconds (Trò chuyện + Tranh luận) used since `since`, counted like the trial: a session
    never finished counts as all it was allowed."""
    rows = (
        await db.execute(
            select(ConversationSession.seconds, ConversationSession.allowed_seconds, ConversationSession.ended_at).where(
                ConversationSession.learner_id == profile_id,
                ConversationSession.kind.in_(billing_features.LIVE_FEATURES),
                ConversationSession.started_at >= since,
            )
        )
    ).all()
    used = 0
    for seconds, allowed, ended in rows:
        if ended is not None:
            used += min(int(seconds or 0), int(allowed)) if allowed else int(seconds or 0)
        else:
            used += int(allowed or 0)
    return used


async def pass_minutes(db: AsyncSession, profile_id: uuid.UUID) -> tuple[int, int] | None:
    """(seconds used, minutes included) of the Haru Nói passes held now when they are sold by the
    minute; None when one has no minute total (an older pass, a grant). A pass bought while another
    runs is queued after it (its days follow on) but its minutes can be used at once: the minutes
    of the running pass and of those queued after it add up, counted from the running one's start;
    minutes left when a pass ends do not carry over."""
    now = datetime.now(timezone.utc)
    rows = (
        await db.execute(
            select(Entitlement).where(
                Entitlement.profile_id == profile_id,
                Entitlement.kind == billing_catalog.FEATURE_PASS,
                Entitlement.revoked_at.is_(None),
                (Entitlement.ends_at.is_(None)) | (Entitlement.ends_at > now),
            )
        )
    ).scalars().all()
    running = [r for r in rows if r.starts_at <= now]
    if not running:
        return None
    total = 0
    for r in rows:
        product = billing_catalog.get(r.product_code)
        if product is None or product.minutes is None:
            return None  # an unlimited pass is running: no minute total
        total += product.minutes
    since = min(r.starts_at for r in running)
    return await live_seconds_since(db, profile_id, since), total


async def pass_seconds_left(db: AsyncSession, profile_id: uuid.UUID) -> int | None:
    m = await pass_minutes(db, profile_id)
    if m is None:
        return None
    used, total = m
    return max(0, total * 60 - used)


def trial_left_of(feature: str, used: int) -> int | None:
    """What is left of the trial in the feature's unit (minutes / tries); None = no billing limit."""
    if feature in billing_features.LIVE_FEATURES:
        r = billing_features.rule(feature)
        if r.mode == "free":
            return None
        if r.mode == "paid":
            return 0
        minutes, _ = billing_features.trial_size(feature)
        return max(0, (minutes * 60 - used) // 60)
    return billing_features.trial_left(feature, used)


async def ensure_feature(
    db: AsyncSession, profile: Profile, feature: str, request: Request | None = None
) -> int | None:
    """The AI speaking features: open with a Haru Nói pass; without one, the one-time trial of the
    feature's rule (billing.features), then 402. Returns, for a live feature on the trial, how many
    SECONDS the session may run (None = no billing limit). Does nothing while billing is off.

    A start on the trial also passes the anti-abuse gate (app/services/abuse.py: one trial per
    browser, a soft cap per network, the day's budget, the pause switch) and is recorded there."""
    if not settings.BILLING_ENABLED:
        return None
    held = await billing_access.load_access(db, profile)
    if held.has_feature(feature):
        if feature not in billing_features.LIVE_FEATURES or held.everything or not held.enforced:
            return None
        # a Haru Nói pass sold by the minute: the session is cut to what is left of its minutes
        left = await pass_seconds_left(db, profile.id)
        if left is None or left >= 60:
            return left
        raise payment_required(
            billing_catalog.FEATURE_PASS,
            "Bạn đã dùng hết số phút nói của gói Haru Nói. Mua thêm gói để nói tiếp (thời hạn và số phút được cộng thêm).",
            billing_catalog.feature_passes(feature),
        )
    await billing_settings.refresh(db)
    rule = billing_features.rule(feature)
    if rule.mode == "free":
        return None
    if rule.mode == "trial":
        used = await trial_used(db, profile.id, feature)
        if feature in billing_features.LIVE_FEATURES:
            minutes, _ = billing_features.trial_size(feature)
            left = minutes * 60 - used
            if left >= 60:
                return await abuse.gate_trial(db, profile, feature, request, left)
        elif used < billing_features.trial_size(feature)[0]:
            await abuse.gate_trial(db, profile, feature, request, 1)
            return None
    raise payment_required(
        billing_catalog.FEATURE_PASS, billing_features.refusal_vi(feature), billing_catalog.feature_passes(feature)
    )


async def feature_seconds_left(db: AsyncSession, profile: Profile, feature: str) -> int | None:
    """How many seconds of a live feature this learner may still use, as `ensure_feature` would
    allow them, without starting anything: what is left of the Haru Nói pass's minutes or of the
    one-time trial; 0 when neither is left; None when billing sets no limit. The screens show the
    smaller of this and the daily cap, so they never promise 20 minutes to someone with 5."""
    if not settings.BILLING_ENABLED or feature not in billing_features.LIVE_FEATURES:
        return None
    held = await billing_access.load_access(db, profile)
    if held.has_feature(feature):
        if held.everything or not held.enforced:
            return None
        return await pass_seconds_left(db, profile.id)
    await billing_settings.refresh(db)
    rule = billing_features.rule(feature)
    if rule.mode == "free":
        return None
    if rule.mode == "trial":
        minutes, _ = billing_features.trial_size(feature)
        return max(0, minutes * 60 - await trial_used(db, profile.id, feature))
    return 0


async def require_private_source(
    profile: Annotated[Profile | None, Depends(get_optional_profile)],
) -> Profile | None:
    """The corpus, the editorial commentaries and the real past papers: with billing on they are
    for editors and admins only (settings.BILLING_PRIVATE_SOURCES), because their copyright is
    not settled. With billing off nothing changes."""
    if not (settings.BILLING_ENABLED and settings.BILLING_PRIVATE_SOURCES):
        return profile
    if profile is None:
        raise _problem(status.HTTP_401_UNAUTHORIZED, "Missing bearer token", "unauthenticated")
    if profile.role not in billing_access.STAFF_ROLES:
        raise _problem(
            status.HTTP_403_FORBIDDEN, "Tài liệu này hiện chỉ dành cho người biên tập", "closed_source", "Chưa mở cho người học."
        )
    return profile


async def ensure_lesson_open(db: AsyncSession, profile: Profile | None, lesson) -> None:
    """Paid lessons: 401 for someone not signed in, 402 for someone who has not unlocked the
    lesson. Does nothing while billing is off, and nothing for a free lesson."""
    held = await billing_access.load_access(db, profile)
    if not held.enforced or held.can_open(lesson.sort_order):
        return
    if profile is None:
        raise _problem(status.HTTP_401_UNAUTHORIZED, "Missing bearer token", "unauthenticated")
    raise payment_required(
        billing_catalog.LESSON_PACK,
        "Bài này thuộc một gói cần mở khoá.",
        billing_catalog.unlock_products(lesson.sort_order),
    )


async def ensure_daily_cap(db: AsyncSession, profile_id: uuid.UUID, job_type: str, cap: int, what_vi: str) -> None:
    """Each of these jobs is a paid model call, so one learner gets only `cap` of them in a
    rolling 24 hours (counted from the jobs table). 429 beyond that. cap <= 0 switches the limit off."""
    if cap <= 0:
        return
    since = datetime.now(timezone.utc) - timedelta(hours=24)
    used = (
        await db.execute(
            select(func.count()).select_from(Job).where(Job.owner_id == profile_id, Job.type == job_type, Job.created_at > since)
        )
    ).scalar_one()
    if used >= cap:
        raise _problem(
            status.HTTP_429_TOO_MANY_REQUESTS,
            f"Hôm nay bạn đã nhờ chấm {what_vi} nhiều rồi (tối đa {cap} lần mỗi ngày), mai làm tiếp nhé.",
            "daily_limit",
        )


async def study_day(
    db: Annotated[AsyncSession, Depends(get_db)],
    profile: Annotated[Profile, Depends(get_current_profile)],
) -> None:
    """A route a learner studies through (an answer, a review, a talk, a reading): today counts as
    a day studied (app/services/journey.py). Shares the route's session, so the route's commit keeps it."""
    from app.services import journey  # late: keeps deps light to import

    await journey.mark(db, profile.id)

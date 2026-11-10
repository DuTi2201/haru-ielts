"""The admin page's accounts side: a summary, the learner list, one learner in full, and the role
of an account. The money side (orders, claims, grants, revokes, reconcile) is in billing.py under
/admin/billing; this file only reads it together per learner. Every route is admin-only."""
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import _problem, require_role
from app.api.routers.billing import AdminClaimOut, AdminOrderOut, EntitlementRowOut, _admin_order, claim_out
from app.core.config import settings
from app.core.security import hash_password, make_temporary_password
from app.db import get_db
from app.models import Profile
from app.schemas import Role
from app.services import admin_accounts as accounts

log = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["admin-accounts"])

_admin = require_role("admin")


# ----------------------------------------------------------------- shapes --
class AccessOut(BaseModel):
    staff: bool  # editors and admins open everything by their role
    everything: bool
    lesson_packs: list[str]
    exam_pass: bool
    exam_pass_until: datetime | None = None


class LearnerRowOut(BaseModel):
    id: uuid.UUID
    email: str
    display_name: str | None = None
    role: Role
    goal: str | None = None
    created_at: datetime
    last_active_at: datetime | None = None
    disabled_at: datetime | None = None
    disabled_reason: str | None = None
    # set while the password is a temporary one an admin made (it stops working at this time)
    temp_password_expires_at: datetime | None = None
    exercises_answered: int
    paid_orders: int
    paid_total: int
    open_claims: int
    access: AccessOut


class LearnerPageOut(BaseModel):
    total: int
    items: list[LearnerRowOut]


class ProgressOut(BaseModel):
    exercises_answered: int
    exercises_correct: int
    lessons_touched: int
    words_tracked: int
    mistakes_logged: int
    last_active_at: datetime | None = None


class LearnerDetailOut(LearnerRowOut):
    exam_date: datetime | None = None
    daily_minutes: int
    progress: ProgressOut
    entitlements: list[EntitlementRowOut]
    orders: list[AdminOrderOut]
    claims: list[AdminClaimOut]


class RoleIn(BaseModel):
    role: Role


class LockIn(BaseModel):
    reason: str | None = Field(default=None, max_length=255)


class TemporaryPasswordOut(BaseModel):
    """Shown once, to the admin. Only its hash is stored; it is not in any log."""

    temporary_password: str
    expires_at: datetime


class LearnerCountsOut(BaseModel):
    total: int
    learner: int
    editor: int
    admin: int
    new_7d: int
    new_30d: int
    active_7d: int
    active_30d: int
    paying: int
    locked: int = 0


class ProductMoneyOut(BaseModel):
    product_code: str
    title: str
    orders: int
    revenue: int


class MoneyOut(BaseModel):
    paid_total: int
    paid_7d: int
    paid_30d: int
    paid_orders: int
    by_product: list[ProductMoneyOut]


class QueueOut(BaseModel):
    open_claims: int
    needs_review: int
    waiting_orders: int
    underpaid: int


class OverviewOut(BaseModel):
    billing_enabled: bool
    billing_configured: bool
    learners: LearnerCountsOut
    money: MoneyOut
    queue: QueueOut
    orders_by_status: dict[str, int] = Field(default_factory=dict)


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def _learner(db: AsyncSession, profile_id: uuid.UUID) -> Profile:
    profile = await db.get(Profile, profile_id)
    if profile is None:
        raise _problem(status.HTTP_404_NOT_FOUND, "Learner not found", "not_found")
    return profile


# ------------------------------------------------------------------ routes --
@router.get("/overview", response_model=OverviewOut)
async def admin_overview(db: Annotated[AsyncSession, Depends(get_db)], _: Annotated[Profile, Depends(_admin)]):
    """People, money and what waits for you, in one call."""
    data = await accounts.overview(db, _now())
    return OverviewOut(
        billing_enabled=settings.BILLING_ENABLED,
        billing_configured=settings.billing_configured,
        **data,
    )


@router.get("/learners", response_model=LearnerPageOut)
async def admin_learners(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[Profile, Depends(_admin)],
    q: Annotated[str | None, Query(max_length=100, description="part of the e-mail or the name")] = None,
    role: Annotated[Role | None, Query()] = None,
    paying: Annotated[bool | None, Query(description="true: has a paid order; false: has none")] = None,
    locked: Annotated[bool | None, Query(description="true: only locked accounts")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 30,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    """Accounts, newest first, each with what it holds, what it paid and when it was last active."""
    total, items = await accounts.learner_page(db, now=_now(), q=q, role=role, paying=paying, locked=locked, limit=limit, offset=offset)
    return LearnerPageOut(total=total, items=[LearnerRowOut(**i) for i in items])


@router.get("/learners/{profile_id}", response_model=LearnerDetailOut)
async def admin_learner(
    profile_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[Profile, Depends(_admin)],
):
    """One account in full: progress, every entitlement (revoked ones too), orders and claims."""
    profile = await _learner(db, profile_id)
    d = await accounts.learner_detail(db, profile, _now())
    email = profile.email
    return LearnerDetailOut(
        **{k: v for k, v in d.items() if k not in ("entitlements", "orders", "claims")},
        entitlements=[EntitlementRowOut.model_validate(r, from_attributes=True) for r in d["entitlements"]],
        orders=[_admin_order(o, email) for o in d["orders"]],
        claims=[AdminClaimOut(**claim_out(c).model_dump(), email=email, profile_id=c.profile_id) for c in d["claims"]],
    )


@router.post("/learners/{profile_id}/role", response_model=LearnerRowOut)
async def admin_set_role(
    profile_id: uuid.UUID,
    body: RoleIn,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin_profile: Annotated[Profile, Depends(_admin)],
):
    """Make an account a learner, an editor (Studio, no billing tools) or an admin. You cannot change
    your own role, so there is always at least one admin left."""
    if profile_id == admin_profile.id:
        raise _problem(
            status.HTTP_409_CONFLICT, "Không đổi được vai trò của chính bạn", "cannot_change_self",
            "Nhờ một admin khác đổi, để luôn còn ít nhất một admin.",
        )
    profile = await _learner(db, profile_id)
    if profile.role != body.role:
        log.info("[admin] %s: role %s -> %s (by %s)", profile.id, profile.role, body.role, admin_profile.id)
        profile.role = body.role
        await db.commit()
        await db.refresh(profile)
    return LearnerRowOut(**(await accounts.learner_rows(db, [profile], _now()))[0])


TEMP_PASSWORD_HOURS = 72


async def _other_managed_account(db: AsyncSession, profile_id: uuid.UUID, admin_profile: Profile) -> Profile:
    """The account an admin may lock or reset: not yourself (use the app's own screens), and not
    another admin (change their role first, so taking over an admin is never one click)."""
    if profile_id == admin_profile.id:
        raise _problem(
            status.HTTP_409_CONFLICT, "Không làm việc này với chính bạn", "cannot_change_self",
            "Tự đổi mật khẩu ở mục Tài khoản; không ai khoá được chính mình.",
        )
    profile = await _learner(db, profile_id)
    if profile.role == "admin":
        raise _problem(
            status.HTTP_409_CONFLICT, "Đây là tài khoản admin", "admin_protected",
            "Muốn khoá hoặc đặt lại mật khẩu cho admin, hãy đổi vai trò của họ trước.",
        )
    return profile


@router.post("/learners/{profile_id}/lock", response_model=LearnerRowOut)
async def admin_lock(
    profile_id: uuid.UUID,
    body: LockIn,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin_profile: Annotated[Profile, Depends(_admin)],
):
    """Lock an account: it cannot log in, and every token it holds stops working at once. Nothing is
    deleted (progress, orders, entitlements stay) and unlocking brings it all back."""
    profile = await _other_managed_account(db, profile_id, admin_profile)
    if profile.disabled_at is None:
        profile.disabled_at = _now()
        profile.disabled_reason = (body.reason or "").strip() or None
        log.info("[admin] %s: locked by %s", profile.id, admin_profile.id)
        await db.commit()
        await db.refresh(profile)
    return LearnerRowOut(**(await accounts.learner_rows(db, [profile], _now()))[0])


@router.post("/learners/{profile_id}/unlock", response_model=LearnerRowOut)
async def admin_unlock(
    profile_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin_profile: Annotated[Profile, Depends(_admin)],
):
    profile = await _learner(db, profile_id)
    if profile.disabled_at is not None:
        profile.disabled_at = None
        profile.disabled_reason = None
        log.info("[admin] %s: unlocked by %s", profile.id, admin_profile.id)
        await db.commit()
        await db.refresh(profile)
    return LearnerRowOut(**(await accounts.learner_rows(db, [profile], _now()))[0])


@router.post("/learners/{profile_id}/reset-password", response_model=TemporaryPasswordOut)
async def admin_reset_password(
    profile_id: uuid.UUID,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin_profile: Annotated[Profile, Depends(_admin)],
):
    """Give the learner a new temporary password (for someone who forgot theirs). It is shown here
    once, for the admin to pass on privately; the learner must change it within 72 hours, and every
    older session of the account ends now."""
    profile = await _other_managed_account(db, profile_id, admin_profile)
    password = make_temporary_password()
    now = _now()
    profile.hashed_password = hash_password(password)
    profile.temp_password_expires_at = now + timedelta(hours=TEMP_PASSWORD_HOURS)
    profile.tokens_valid_after = now
    await db.commit()
    log.info("[admin] %s: password reset by %s", profile.id, admin_profile.id)  # never the password
    response.headers["Cache-Control"] = "no-store"
    return TemporaryPasswordOut(temporary_password=password, expires_at=profile.temp_password_expires_at)

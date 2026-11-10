"""The admin's anti-abuse page (app/services/abuse.py): the guard's numbers, what the free trial
gave away today, accounts that share a browser or a network, locking several at once, and the
throwaway-mail domains added by hand. Every route is admin-only."""
from __future__ import annotations

import logging
import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import distinct, func, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import _problem, require_role
from app.db import get_db
from app.models import AccountSignal, BillingOrder, BillingSetting, BlockedEmailDomain, Profile, TrialUse
from app.services import abuse
from app.services.billing import settings_db

log = logging.getLogger(__name__)
router = APIRouter(prefix="/admin/abuse", tags=["admin-abuse"])
_admin = require_role("admin")

DEFAULT_LOCK_REASON = "Vi phạm điều khoản: tạo nhiều tài khoản để dùng thử lại"


class GuardOut(BaseModel):
    trial_enabled: bool
    trial_daily_minutes: int  # 0 = no cap
    trial_daily_present_tries: int  # 0 = no cap
    trial_accounts_per_device: int
    trial_accounts_per_ip_daily: int
    signup_per_ip_daily: int


class GuardIn(BaseModel):
    trial_enabled: bool | None = None
    trial_daily_minutes: int | None = Field(default=None, ge=0, le=100_000)
    trial_daily_present_tries: int | None = Field(default=None, ge=0, le=100_000)
    trial_accounts_per_device: int | None = Field(default=None, ge=1, le=10)
    trial_accounts_per_ip_daily: int | None = Field(default=None, ge=1, le=1000)
    signup_per_ip_daily: int | None = Field(default=None, ge=1, le=1000)


class TodayOut(BaseModel):
    live_minutes: int  # trial minutes granted since midnight (Vietnam time)
    live_cap: int  # 0 = no cap
    present_tries: int
    present_cap: int
    trial_accounts: int  # accounts that started on the trial today
    new_accounts: int


class DomainOut(BaseModel):
    domain: str
    created_at: datetime


class OverviewOut(BaseModel):
    guard: GuardOut
    today: TodayOut
    domains: list[DomainOut]
    bundled_domains: int


class ClusterAccountOut(BaseModel):
    id: uuid.UUID
    email: str
    display_name: str | None = None
    role: str
    created_at: datetime
    disabled_at: datetime | None = None
    last_seen: datetime
    trial_live_minutes: int
    trial_present_tries: int
    paid_orders: int


class ClusterOut(BaseModel):
    kind: Literal["device", "ip"]
    key: str  # a short tag of the hash, to tell clusters apart
    accounts: list[ClusterAccountOut]
    trial_accounts: int
    last_seen: datetime


class LockManyIn(BaseModel):
    profile_ids: list[uuid.UUID] = Field(min_length=1, max_length=200)
    reason: str | None = Field(default=None, max_length=255)


class LockManyOut(BaseModel):
    locked: int
    already: int
    skipped: int  # staff, yourself, or not found


class DomainIn(BaseModel):
    domain: str = Field(min_length=3, max_length=253)


def _guard_out() -> GuardOut:
    g = abuse.guard()
    return GuardOut(**{**g, "trial_enabled": bool(g["trial_enabled"])})


async def _domains(db: AsyncSession) -> list[DomainOut]:
    rows = (await db.execute(select(BlockedEmailDomain).order_by(BlockedEmailDomain.domain))).scalars().all()
    return [DomainOut(domain=r.domain, created_at=r.created_at) for r in rows]


@router.get("", response_model=OverviewOut)
async def overview(db: Annotated[AsyncSession, Depends(get_db)], _: Annotated[Profile, Depends(_admin)]):
    await settings_db.refresh(db, force=True)
    live, present = await abuse.used_today(db)
    since = abuse.day_start()
    trial_accounts = await db.scalar(
        select(func.count(distinct(TrialUse.profile_id))).where(TrialUse.created_at >= since)
    )
    new_accounts = await db.scalar(select(func.count(Profile.id)).where(Profile.created_at >= since))
    g = abuse.guard()
    return OverviewOut(
        guard=_guard_out(),
        today=TodayOut(
            live_minutes=live // 60,
            live_cap=g["trial_daily_minutes"],
            present_tries=present,
            present_cap=g["trial_daily_present_tries"],
            trial_accounts=int(trial_accounts or 0),
            new_accounts=int(new_accounts or 0),
        ),
        domains=await _domains(db),
        bundled_domains=len(abuse._BUNDLED),
    )


@router.put("/guard", response_model=GuardOut)
async def set_guard(
    body: GuardIn,
    db: Annotated[AsyncSession, Depends(get_db)],
    who: Annotated[Profile, Depends(_admin)],
):
    for key, value in body.model_dump(exclude_none=True).items():
        row = await db.get(BillingSetting, key) or BillingSetting(key=key)
        row.value = int(value)
        row.updated_by = who.id
        db.add(row)
    await db.commit()
    await settings_db.refresh(db, force=True)
    log.info("[admin] %s changed the trial guard: %s", who.id, body.model_dump(exclude_none=True))
    return _guard_out()


@router.get("/clusters", response_model=list[ClusterOut])
async def clusters(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[Profile, Depends(_admin)],
    days: int = Query(default=30, ge=1, le=365),
    kind: Literal["all", "device", "ip"] = "all",
    trial_only: bool = True,
):
    """Browsers and networks shared by two accounts or more, seen in the last `days`. With
    `trial_only`, only those where two accounts or more used the free trial. A shared network is
    often innocent (a dorm, a school, one mobile carrier): look at the browser clusters first."""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    q = (
        select(AccountSignal.kind, AccountSignal.value)
        .where(AccountSignal.last_seen >= since)
        .group_by(AccountSignal.kind, AccountSignal.value)
        .having(func.count(distinct(AccountSignal.profile_id)) >= 2)
        .order_by(func.count(distinct(AccountSignal.profile_id)).desc())
        .limit(500)
    )
    if kind != "all":
        q = q.where(AccountSignal.kind == kind)
    groups = (await db.execute(q)).all()
    if not groups:
        return []
    signals = (
        await db.execute(
            select(AccountSignal).where(tuple_(AccountSignal.kind, AccountSignal.value).in_([tuple(g) for g in groups]))
        )
    ).scalars().all()
    ids = {s.profile_id for s in signals}
    profiles = {p.id: p for p in (await db.execute(select(Profile).where(Profile.id.in_(ids)))).scalars().all()}
    trial: dict[uuid.UUID, tuple[int, int]] = defaultdict(lambda: (0, 0))
    for pid, feature, amount in (
        await db.execute(
            select(TrialUse.profile_id, TrialUse.feature, func.sum(TrialUse.amount))
            .where(TrialUse.profile_id.in_(ids))
            .group_by(TrialUse.profile_id, TrialUse.feature)
        )
    ).all():
        live, present = trial[pid]
        if feature in abuse.LIVE:
            live += int(amount)
        else:
            present += int(amount)
        trial[pid] = (live, present)
    paid = dict(
        (
            await db.execute(
                select(BillingOrder.profile_id, func.count(BillingOrder.id))
                .where(BillingOrder.profile_id.in_(ids), BillingOrder.status == "PAID")
                .group_by(BillingOrder.profile_id)
            )
        ).all()
    )
    by_group: dict[tuple[str, str], list[AccountSignal]] = defaultdict(list)
    for s in signals:
        by_group[(s.kind, s.value)].append(s)
    out: list[ClusterOut] = []
    for (k, v), rows in by_group.items():
        accounts = []
        for s in sorted(rows, key=lambda r: r.last_seen, reverse=True):
            p = profiles.get(s.profile_id)
            if p is None:
                continue
            live, present = trial[p.id]
            accounts.append(
                ClusterAccountOut(
                    id=p.id,
                    email=p.email,
                    display_name=p.display_name,
                    role=p.role,
                    created_at=p.created_at,
                    disabled_at=p.disabled_at,
                    last_seen=s.last_seen,
                    trial_live_minutes=(live + 59) // 60,
                    trial_present_tries=present,
                    paid_orders=int(paid.get(p.id, 0)),
                )
            )
        used = sum(1 for a in accounts if a.trial_live_minutes or a.trial_present_tries)
        if len(accounts) < 2 or (trial_only and used < 2):
            continue
        out.append(
            ClusterOut(
                kind=k,  # type: ignore[arg-type]
                key=v[:8],
                accounts=accounts,
                trial_accounts=used,
                last_seen=max(a.last_seen for a in accounts),
            )
        )
    # a shared browser says more than a shared network
    out.sort(key=lambda c: (c.kind != "device", -c.trial_accounts, -len(c.accounts)))
    return out[:100]


@router.post("/lock", response_model=LockManyOut)
async def lock_many(
    body: LockManyIn,
    db: Annotated[AsyncSession, Depends(get_db)],
    who: Annotated[Profile, Depends(_admin)],
):
    """Lock several learner accounts at once (the terms forbid extra accounts for another trial).
    Staff accounts and your own are skipped; nothing is deleted and each can be unlocked later."""
    reason = (body.reason or "").strip() or DEFAULT_LOCK_REASON
    rows = (await db.execute(select(Profile).where(Profile.id.in_(set(body.profile_ids))))).scalars().all()
    now = datetime.now(timezone.utc)
    locked = already = 0
    for p in rows:
        if p.id == who.id or p.role != "learner":
            continue
        if p.disabled_at is not None:
            already += 1
            continue
        p.disabled_at = now
        p.disabled_reason = reason
        locked += 1
    await db.commit()
    skipped = len(set(body.profile_ids)) - locked - already
    log.info("[admin] %s locked %s accounts for abuse (%s already, %s skipped)", who.id, locked, already, skipped)
    return LockManyOut(locked=locked, already=already, skipped=skipped)


@router.post("/domains", response_model=list[DomainOut], status_code=status.HTTP_201_CREATED)
async def add_domain(
    body: DomainIn,
    db: Annotated[AsyncSession, Depends(get_db)],
    who: Annotated[Profile, Depends(_admin)],
):
    """Refuse sign-ups from one more throwaway-mail domain (and its subdomains)."""
    domain = abuse.normalize_domain(body.domain)
    if domain is None:
        raise _problem(status.HTTP_422_UNPROCESSABLE_ENTITY, "Tên miền chưa hợp lệ", "bad_domain")
    if domain in abuse.PROTECTED_DOMAINS:
        raise _problem(
            status.HTTP_409_CONFLICT, "Không chặn được tên miền email phổ biến", "protected_domain",
            "Chặn tên miền này sẽ chặn cả người học thật.",
        )
    if await db.get(BlockedEmailDomain, domain) is None:
        db.add(BlockedEmailDomain(domain=domain, created_by=who.id))
        await db.commit()
    return await _domains(db)


@router.delete("/domains/{domain}", response_model=list[DomainOut])
async def remove_domain(
    domain: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[Profile, Depends(_admin)],
):
    row = await db.get(BlockedEmailDomain, (domain or "").strip().lower())
    if row is not None:
        await db.delete(row)
        await db.commit()
    return await _domains(db)

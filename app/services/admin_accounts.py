"""What the admin page shows about accounts and money: the learner list, one learner in full, and the
summary at the top. Read-only queries (the writes are the billing admin routes and the role change);
the rules for what a learner holds are the same ones the lesson gate uses (billing.access.build_access).

Everything here takes the ids of one page of learners and asks the database once per kind of fact, so a
page of 50 costs a handful of queries, not 50 x a handful."""
import uuid
from datetime import datetime, timedelta
from typing import Any, Iterable

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    BillingClaim,
    BillingOrder,
    Entitlement,
    ErrorLog,
    ItemState,
    LessonExerciseResult,
    Profile,
)
from app.services.billing import access as billing_access
from app.services.billing import catalog

PAID = "PAID"
ROLES = ("learner", "editor", "admin")


def like_pattern(text: str) -> str:
    """`%text%` for ILIKE, with the characters that mean something to LIKE taken literally."""
    t = text.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{t}%"


def access_of(profile: Profile, rows: Iterable[Entitlement], now: datetime) -> dict[str, Any]:
    """What this account holds, whatever the billing switch says (the page shows rights, not the gate)."""
    held = billing_access.build_access(rows, now)
    staff = profile.role in billing_access.STAFF_ROLES
    return {
        "staff": staff,
        "everything": staff or held.everything,
        "lesson_packs": sorted(held.packs),
        "exam_pass": held.exam_pass,
        "exam_pass_until": held.exam_pass_until,
    }


async def _learner_facts(db: AsyncSession, ids: list[uuid.UUID]) -> dict[uuid.UUID, dict[str, Any]]:
    """Per learner: how much they practised and when, what they paid, how many claims wait."""
    facts: dict[uuid.UUID, dict[str, Any]] = {
        i: {"exercises_answered": 0, "last_active_at": None, "paid_orders": 0, "paid_total": 0, "open_claims": 0}
        for i in ids
    }
    if not ids:
        return facts
    for pid, n, last in (
        await db.execute(
            select(LessonExerciseResult.learner_id, func.count(), func.max(LessonExerciseResult.updated_at))
            .where(LessonExerciseResult.learner_id.in_(ids))
            .group_by(LessonExerciseResult.learner_id)
        )
    ).all():
        facts[pid]["exercises_answered"] = n
        facts[pid]["last_active_at"] = last
    for pid, last in (
        await db.execute(
            select(ItemState.learner_id, func.max(ItemState.last_seen))
            .where(ItemState.learner_id.in_(ids))
            .group_by(ItemState.learner_id)
        )
    ).all():
        mine = facts[pid]["last_active_at"]
        facts[pid]["last_active_at"] = last if mine is None or (last is not None and last > mine) else mine
    for pid, n, total in (
        await db.execute(
            select(BillingOrder.profile_id, func.count(), func.coalesce(func.sum(BillingOrder.paid_amount), 0))
            .where(BillingOrder.profile_id.in_(ids), BillingOrder.status == PAID)
            .group_by(BillingOrder.profile_id)
        )
    ).all():
        facts[pid]["paid_orders"], facts[pid]["paid_total"] = n, int(total)
    for pid, n in (
        await db.execute(
            select(BillingClaim.profile_id, func.count())
            .where(BillingClaim.profile_id.in_(ids), BillingClaim.status == "open")
            .group_by(BillingClaim.profile_id)
        )
    ).all():
        facts[pid]["open_claims"] = n
    return facts


async def _entitlements(db: AsyncSession, ids: list[uuid.UUID]) -> dict[uuid.UUID, list[Entitlement]]:
    held: dict[uuid.UUID, list[Entitlement]] = {i: [] for i in ids}
    if ids:
        rows = (
            (await db.execute(select(Entitlement).where(Entitlement.profile_id.in_(ids)).order_by(Entitlement.created_at.desc())))
            .scalars()
            .all()
        )
        for r in rows:
            held[r.profile_id].append(r)
    return held


def _row(profile: Profile, facts: dict[str, Any], rows: list[Entitlement], now: datetime) -> dict[str, Any]:
    return {
        "id": profile.id,
        "email": profile.email,
        "display_name": profile.display_name,
        "role": profile.role,
        "goal": profile.goal,
        "created_at": profile.created_at,
        "disabled_at": profile.disabled_at,
        "disabled_reason": profile.disabled_reason,
        "temp_password_expires_at": profile.temp_password_expires_at,
        **facts,
        "access": access_of(profile, rows, now),
    }


async def learner_rows(db: AsyncSession, profiles: list[Profile], now: datetime) -> list[dict[str, Any]]:
    ids = [p.id for p in profiles]
    facts, held = await _learner_facts(db, ids), await _entitlements(db, ids)
    return [_row(p, facts[p.id], held[p.id], now) for p in profiles]


async def learner_page(
    db: AsyncSession,
    *,
    now: datetime,
    q: str | None = None,
    role: str | None = None,
    paying: bool | None = None,
    locked: bool | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[int, list[dict[str, Any]]]:
    """Newest accounts first. `q` matches the e-mail or the name; `paying` keeps those who have (or
    have not) a paid order; `locked` keeps the locked (or the not locked) accounts."""
    where = []
    if q and q.strip():
        pattern = like_pattern(q)
        where.append(or_(Profile.email.ilike(pattern, escape="\\"), Profile.display_name.ilike(pattern, escape="\\")))
    if role:
        where.append(Profile.role == role)
    if locked is not None:
        where.append(Profile.disabled_at.isnot(None) if locked else Profile.disabled_at.is_(None))
    if paying is not None:
        has_paid = Profile.id.in_(select(BillingOrder.profile_id).where(BillingOrder.status == PAID))
        where.append(has_paid if paying else ~has_paid)
    total = (await db.execute(select(func.count()).select_from(Profile).where(*where))).scalar_one()
    profiles = (
        (await db.execute(select(Profile).where(*where).order_by(Profile.created_at.desc(), Profile.id).limit(limit).offset(offset)))
        .scalars()
        .all()
    )
    return total, await learner_rows(db, list(profiles), now)


async def progress_of(db: AsyncSession, profile_id: uuid.UUID) -> dict[str, Any]:
    """How far the learner has got, in numbers an admin can read at a glance."""
    answered, correct, lessons = (
        await db.execute(
            select(
                func.count(),
                func.count().filter(LessonExerciseResult.correct.is_(True)),
                func.count(func.distinct(LessonExerciseResult.lesson_id)),
            ).where(LessonExerciseResult.learner_id == profile_id)
        )
    ).one()
    words = (await db.execute(select(func.count()).select_from(ItemState).where(ItemState.learner_id == profile_id))).scalar_one()
    mistakes = (await db.execute(select(func.count()).select_from(ErrorLog).where(ErrorLog.learner_id == profile_id))).scalar_one()
    facts = (await _learner_facts(db, [profile_id]))[profile_id]
    return {
        "exercises_answered": answered,
        "exercises_correct": correct,
        "lessons_touched": lessons,
        "words_tracked": words,
        "mistakes_logged": mistakes,
        "last_active_at": facts["last_active_at"],
    }


async def learner_detail(db: AsyncSession, profile: Profile, now: datetime) -> dict[str, Any]:
    """The row, plus the whole entitlement list (revoked ones too), the orders and the claims."""
    facts, held = (await _learner_facts(db, [profile.id]))[profile.id], (await _entitlements(db, [profile.id]))[profile.id]
    orders = (
        (await db.execute(select(BillingOrder).where(BillingOrder.profile_id == profile.id).order_by(BillingOrder.created_at.desc()).limit(50)))
        .scalars()
        .all()
    )
    claims = (
        (await db.execute(select(BillingClaim).where(BillingClaim.profile_id == profile.id).order_by(BillingClaim.created_at.desc()).limit(50)))
        .scalars()
        .all()
    )
    return {
        **_row(profile, facts, held, now),
        "exam_date": profile.exam_date,
        "daily_minutes": profile.daily_minutes,
        "progress": await progress_of(db, profile.id),
        "entitlements": held,
        "orders": list(orders),
        "claims": list(claims),
    }


async def overview(db: AsyncSession, now: datetime) -> dict[str, Any]:
    """The summary line at the top of the page: people, money, and what waits for the admin."""
    d7, d30 = now - timedelta(days=7), now - timedelta(days=30)

    by_role = dict((await db.execute(select(Profile.role, func.count()).group_by(Profile.role))).all())
    locked = (await db.execute(select(func.count()).select_from(Profile).where(Profile.disabled_at.isnot(None)))).scalar_one()
    new_7d, new_30d = (
        await db.execute(
            select(
                func.count().filter(Profile.created_at >= d7),
                func.count().filter(Profile.created_at >= d30),
            )
        )
    ).one()

    def active(since: datetime):
        a = select(LessonExerciseResult.learner_id).where(LessonExerciseResult.updated_at >= since)
        b = select(ItemState.learner_id).where(ItemState.last_seen >= since)
        return select(func.count()).select_from(a.union(b).subquery())

    active_7d = (await db.execute(active(d7))).scalar_one()
    active_30d = (await db.execute(active(d30))).scalar_one()

    by_status = dict((await db.execute(select(BillingOrder.status, func.count()).group_by(BillingOrder.status))).all())
    paid_all, paid_7d, paid_30d, paying = (
        await db.execute(
            select(
                func.coalesce(func.sum(BillingOrder.paid_amount), 0),
                func.coalesce(func.sum(BillingOrder.paid_amount).filter(BillingOrder.paid_at >= d7), 0),
                func.coalesce(func.sum(BillingOrder.paid_amount).filter(BillingOrder.paid_at >= d30), 0),
                func.count(func.distinct(BillingOrder.profile_id)),
            ).where(BillingOrder.status == PAID)
        )
    ).one()
    products = (
        await db.execute(
            select(BillingOrder.product_code, func.count(), func.coalesce(func.sum(BillingOrder.paid_amount), 0))
            .where(BillingOrder.status == PAID)
            .group_by(BillingOrder.product_code)
            .order_by(func.coalesce(func.sum(BillingOrder.paid_amount), 0).desc())
        )
    ).all()
    needs_review = (
        await db.execute(select(func.count()).select_from(BillingOrder).where(BillingOrder.needs_review.is_(True)))
    ).scalar_one()
    open_claims = (
        await db.execute(select(func.count()).select_from(BillingClaim).where(BillingClaim.status == "open"))
    ).scalar_one()

    def title(code: str) -> str:
        p = catalog.get(code)
        return p.title_vi if p else code

    return {
        "learners": {
            "total": sum(by_role.values()),
            "learner": by_role.get("learner", 0),
            "editor": by_role.get("editor", 0),
            "admin": by_role.get("admin", 0),
            "new_7d": new_7d,
            "new_30d": new_30d,
            "active_7d": active_7d,
            "active_30d": active_30d,
            "paying": paying,
            "locked": locked,
        },
        "money": {
            "paid_total": int(paid_all),
            "paid_7d": int(paid_7d),
            "paid_30d": int(paid_30d),
            "paid_orders": by_status.get(PAID, 0),
            "by_product": [
                {"product_code": c, "title": title(c), "orders": n, "revenue": int(r)} for c, n, r in products
            ],
        },
        "queue": {
            "open_claims": open_claims,
            "needs_review": needs_review,
            "waiting_orders": by_status.get("PENDING", 0),
            "underpaid": by_status.get("UNDERPAID", 0),
        },
        "orders_by_status": by_status,
    }

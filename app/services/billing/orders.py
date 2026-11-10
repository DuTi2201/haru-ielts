"""Orders, payments and entitlements.

One rule keeps this safe: a payment is counted ONCE, under a lock on its order row, and the order
turning PAID and its entitlement appearing happen in the same database transaction. The webhook,
the order screen's polling and the reconcile job all go through `apply_payment`, so a payment seen
by all three still unlocks exactly once (the bank reference is UNIQUE, and so is the entitlement's
order).
"""
import asyncio
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.models import BillingOrder, Coupon, Entitlement, PaymentEvent, Profile
from app.services.billing import access as access_mod
from app.services.billing import catalog, coupons, settings_db
from app.services.billing.payos_client import PayosClient, PayosError, Transaction, make_client, new_order_code

log = logging.getLogger(__name__)

PENDING, PAID, EXPIRED, CANCELLED, UNDERPAID, NEEDS_REVIEW = (
    "PENDING",
    "PAID",
    "EXPIRED",
    "CANCELLED",
    "UNDERPAID",
    "NEEDS_REVIEW",
)
REFRESH_EVERY = timedelta(seconds=20)  # the order screen asks often; payOS is asked at most this often
RECONCILE_WINDOW = timedelta(hours=24)


class BillingError(Exception):
    """A refusal the API turns into an HTTP problem."""

    def __init__(self, status: int, code: str, message: str):
        super().__init__(message)
        self.status, self.code, self.message = status, code, message


# ------------------------------------------------------------ the pure rules --
@dataclass
class Settlement:
    granted: bool  # this payment completed the order: make the entitlement now
    outcome: str


def _note(order: BillingOrder, text: str) -> None:
    order.note = f"{order.note}\n{text}" if order.note else text


def settle(order: BillingOrder, now: datetime) -> Settlement:
    """Decide what the order's money so far means (`order.paid_amount` already counts the new
    payment). Mutates the order; never creates the entitlement itself."""
    price = order.amount
    paid = order.paid_amount
    if paid >= price:
        if order.status == PAID:
            order.needs_review = True
            _note(order, f"Nhận thêm tiền sau khi đơn đã thanh toán: tổng {paid}đ, giá {price}đ.")
            return Settlement(False, "extra")
        if order.status in (EXPIRED, CANCELLED):
            _note(order, "Tiền về sau khi link thanh toán đã hết hạn / bị huỷ; vẫn mở khoá.")
        order.status = PAID
        order.paid_at = now
        over = paid - price
        order.needs_review = over > 0
        if over > 0:
            _note(order, f"Chuyển dư {over}đ (giá {price}đ): hoàn phần dư thủ công.")
        return Settlement(True, "granted" if over == 0 else "granted_over")
    if order.status != PAID:
        order.status = UNDERPAID
        order.needs_review = True
        _note(order, f"Mới nhận {paid}đ trên giá {price}đ: chưa mở khoá.")
    return Settlement(False, "underpaid")


def entitlement_window(product: catalog.Product, now: datetime, pass_ends: datetime | None, days: int | None = None):
    """(starts_at, ends_at). A pack is for life; a second pass starts when the first one ends."""
    if product.kind == catalog.LESSON_PACK:
        return now, None
    start = max(now, pass_ends) if pass_ends else now
    return start, start + timedelta(days=days or product.days or 30)


async def _active_pass_end(
    db: AsyncSession, profile_id: uuid.UUID, now: datetime, kind: str = catalog.EXAM_PASS
) -> datetime | None:
    """When the learner's current pass of this kind ends (a new one is added after it)."""
    ends = (
        await db.execute(
            select(Entitlement.ends_at).where(
                Entitlement.profile_id == profile_id,
                Entitlement.kind == kind,
                Entitlement.revoked_at.is_(None),
                Entitlement.ends_at.isnot(None),
                Entitlement.ends_at > now,
            )
        )
    ).scalars().all()
    return max(ends) if ends else None


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ------------------------------------------------------------------ creating --
async def resolve_coupon(
    db: AsyncSession, code: str | None, product: catalog.Product, profile_id: uuid.UUID, now: datetime
) -> Coupon | None:
    """The discount code for this learner and product, or None for no code. Refuses (422
    bad_coupon) a code that does not exist, is off, out of its dates, not for this product, used up
    (paid uses + pending orders holding a place) or already used by this learner."""
    code = coupons.normalize(code)
    if not code:
        return None
    c = await db.get(Coupon, code) if coupons.CODE_RE.match(code) else None
    why = coupons.check(c, product, now)
    if why:
        raise BillingError(422, "bad_coupon", why)
    assert c is not None
    if c.max_uses is not None:
        holding = (
            await db.execute(
                select(func.count())
                .select_from(BillingOrder)
                .where(
                    BillingOrder.coupon_code == c.code,
                    BillingOrder.status == PENDING,
                    BillingOrder.expires_at > now,
                    BillingOrder.profile_id != profile_id,
                )
            )
        ).scalar_one()
        if c.used + holding >= c.max_uses:
            raise BillingError(422, "bad_coupon", "Mã giảm giá đã hết lượt dùng.")
    if c.once_per_learner:
        before = (
            await db.execute(
                select(BillingOrder.id).where(
                    BillingOrder.coupon_code == c.code,
                    BillingOrder.profile_id == profile_id,
                    BillingOrder.status == PAID,
                )
            )
        ).first()
        if before:
            raise BillingError(422, "bad_coupon", "Bạn đã dùng mã giảm giá này rồi.")
    return c


async def upgrade_credit(db: AsyncSession, profile_id: uuid.UUID, product: catalog.Product) -> int:
    """Nâng cấp chỉ trả phần chênh: what the learner paid for the smaller lesson packs that lie
    wholly inside this one (Sinh hoạt 2 inside Trung cấp, both inside Trọn bộ; a combo's lessons
    count as the combo's lessons, and a pack bought in a combo counts for its share). Only paid
    orders count (a granted pack cost nothing), each pack once, a revoked one not at all."""
    if product.kind not in (catalog.LESSON_PACK, catalog.COMBO) or not product.lessons:
        return 0
    rows = (
        await db.execute(
            select(Entitlement.product_code, BillingOrder.product_code, BillingOrder.amount)
            .join(Entitlement, Entitlement.order_id == BillingOrder.id)
            .where(
                BillingOrder.profile_id == profile_id,
                BillingOrder.status == PAID,
                Entitlement.revoked_at.is_(None),
                Entitlement.kind == catalog.LESSON_PACK,
            )
        )
    ).all()
    inside = lambda p: all(product.covers(n) for lo, hi in p.lessons for n in range(lo, hi + 1))  # noqa: E731
    paid: dict[str, int] = {}
    for code, bought, amount in rows:
        p = catalog.get(code)
        if p is None or p.code == product.code or not p.lessons or not inside(p):
            continue
        share = int(amount or 0)
        combo = catalog.get(bought)
        if combo is not None and combo.kind == catalog.COMBO:
            # a pack bought in a combo: its share of what the combo cost, by today's prices
            share = share * p.amount // max(1, catalog.list_total(combo))
        paid[code] = max(paid.get(code, 0), share)
    return sum(paid.values())


async def quote(
    db: AsyncSession, profile: Profile, product_code: str, coupon_code: str | None
) -> tuple[catalog.Product, coupons.Quote, str | None]:
    """What this learner would pay for this product with this code (the checkout summary). A bad
    code does not fail the quote: it comes back as the reason, with the price without it."""
    await settings_db.refresh(db, force=True)
    product = catalog.get(product_code)
    if product is None or not product.active:
        raise BillingError(404, "unknown_product", "Gói này hiện không bán.")
    credit = await upgrade_credit(db, profile.id, product)
    try:
        c = await resolve_coupon(db, coupon_code, product, profile.id, _now())
    except BillingError as exc:
        return product, coupons.price(product, None, credit), exc.message
    return product, coupons.price(product, c, credit), None


async def create_order(
    db: AsyncSession,
    profile: Profile,
    product_code: str,
    payos: PayosClient | None = None,
    coupon_code: str | None = None,
) -> BillingOrder:
    await settings_db.refresh(db, force=True)
    product = catalog.get(product_code)
    if product is None or not product.active:
        raise BillingError(404, "unknown_product", "Sản phẩm này không có.")
    origin = settings.frontend_origin
    if not settings.billing_configured or not origin:
        raise BillingError(503, "billing_unavailable", "Thanh toán chưa được bật.")
    now = _now()
    profile_id = profile.id

    held = await access_mod.load_access(db, profile)
    if held.owns(product):
        raise BillingError(409, "already_owned", "Bạn đã có gói này rồi.")
    coupon = await resolve_coupon(db, coupon_code, product, profile_id, now)
    q = coupons.price(product, coupon, await upgrade_credit(db, profile_id, product))

    await db.execute(
        update(BillingOrder)
        .where(
            BillingOrder.profile_id == profile_id,
            BillingOrder.status == PENDING,
            BillingOrder.paid_amount == 0,
            BillingOrder.expires_at < now,
        )
        .values(status=EXPIRED)
    )
    open_orders = (
        (await db.execute(select(BillingOrder).where(BillingOrder.profile_id == profile_id, BillingOrder.status == PENDING)))
        .scalars()
        .all()
    )
    for existing in open_orders:  # the same thing asked twice (a double click): same order
        if (
            existing.product_code == product.code
            and existing.coupon_code == q.coupon_code
            and existing.amount == q.total
            and existing.expires_at > now
            and existing.checkout_url
        ):
            await db.commit()
            return existing
    if len(open_orders) >= settings.BILLING_MAX_PENDING_ORDERS:
        raise BillingError(429, "too_many_pending", "Bạn đang có quá nhiều đơn chờ thanh toán. Huỷ bớt hoặc chờ chúng hết hạn.")

    recent = (
        await db.execute(
            select(func.count())
            .select_from(BillingOrder)
            .where(BillingOrder.profile_id == profile_id, BillingOrder.created_at > now - timedelta(hours=1))
        )
    ).scalar_one()
    if recent >= settings.BILLING_MAX_ORDERS_PER_HOUR:  # each order is a call to payOS
        raise BillingError(429, "too_many_orders", "Bạn tạo đơn hơi nhiều, thử lại sau ít phút.")

    expires_at = now + timedelta(minutes=settings.BILLING_ORDER_TTL_MIN)
    order = None
    for _ in range(3):  # an order code that is already taken is a one-in-a-million; try again
        order = BillingOrder(
            id=uuid.uuid4(),
            order_code=new_order_code(),
            profile_id=profile_id,
            product_code=product.code,
            amount=q.total,  # from the catalogue (and the code), never from the request
            list_amount=q.list_amount,
            discount=q.discount + q.credit,
            coupon_code=q.coupon_code,
            status=PENDING,
            expires_at=expires_at,
        )
        db.add(order)
        try:
            await db.flush()
            break
        except IntegrityError:
            await db.rollback()
            order = None
    if order is None:
        raise BillingError(503, "billing_unavailable", "Chưa tạo được đơn, thử lại sau ít phút.")

    payos = payos or make_client()
    back = f"{origin}/pricing?order={order.id}"
    try:
        link = await asyncio.to_thread(
            payos.create_payment,
            order_code=order.order_code,
            amount=order.amount,
            # payOS allows only 9 characters here when the shop's bank account is not one linked
            # through payOS (a longer one is refused and no link is made); the order code, not
            # this text, is what matches a payment to its order
            description=f"HR{order.order_code % 10**7:07d}",
            return_url=back,
            cancel_url=back,
            expired_at=int(expires_at.timestamp()),
        )
    except PayosError as exc:
        await db.rollback()
        log.warning("[billing] payOS refused to make a payment link: code=%s %s", exc.code, exc)
        raise BillingError(502, "payos_error", "Cổng thanh toán đang không phản hồi, thử lại sau ít phút.") from None
    order.payment_link_id = link.payment_link_id
    order.checkout_url = link.checkout_url
    order.payment_info = {
        "qr_code": link.qr_code,
        "bank_bin": link.bin,
        "account_number": link.account_number,
        "account_name": link.account_name,
        "description": link.description,
    }
    await db.commit()
    return order


async def cancel_order(db: AsyncSession, order: BillingOrder, payos: PayosClient | None = None) -> BillingOrder:
    """The learner gives up on a pending order. Refused once money has arrived."""
    if order.status != PENDING or order.paid_amount:
        raise BillingError(409, "not_cancellable", "Đơn này không huỷ được nữa.")
    changed = (
        await db.execute(
            update(BillingOrder)
            .where(BillingOrder.id == order.id, BillingOrder.status == PENDING, BillingOrder.paid_amount == 0)
            .values(status=CANCELLED)
        )
    ).rowcount
    await db.commit()
    if changed and settings.billing_configured:
        try:
            await asyncio.to_thread((payos or make_client()).cancel_payment, order.order_code, "Người học huỷ đơn")
        except PayosError:
            pass  # the link will expire by itself; a late payment is still caught by the reconcile job
    await db.refresh(order)
    return order


# -------------------------------------------------------------- the payments --
async def apply_payment(
    db: AsyncSession, *, order_code: int, amount: int, reference: str, source: str, raw: dict | None = None
) -> str:
    """Count one bank payment for an order, once. Returns what happened: granted, granted_over,
    underpaid, extra, unknown_order, repeat. Always ends the transaction."""
    now = _now()
    try:
        order = (
            await db.execute(select(BillingOrder).where(BillingOrder.order_code == order_code).with_for_update())
        ).scalar_one_or_none()
        if (await db.execute(select(PaymentEvent.id).where(PaymentEvent.reference == reference))).first():
            await db.rollback()
            return "repeat"
        if order is None:
            db.add(PaymentEvent(reference=reference, order_code=order_code, amount=amount, source=source, outcome="unknown_order", raw=raw))
            await db.commit()
            log.warning("[billing] a payment for an unknown order code")
            return "unknown_order"

        order.paid_amount = (order.paid_amount or 0) + amount
        if not order.provider_ref:
            order.provider_ref = reference
        settlement = settle(order, now)
        product = catalog.get(order.product_code)
        if settlement.granted:
            if product is None:  # the catalogue changed under a pending order
                order.status = NEEDS_REVIEW
                order.needs_review = True
                _note(order, f"Sản phẩm {order.product_code} không còn trong danh mục: cấp quyền tay.")
                settlement = Settlement(False, "needs_review")
            else:
                for part in catalog.parts(product):  # a combo: each of its products, as if bought alone
                    starts, ends = entitlement_window(
                        part, now, await _active_pass_end(db, order.profile_id, now, part.kind)
                    )
                    db.add(
                        Entitlement(
                            profile_id=order.profile_id,
                            kind=part.kind,
                            product_code=part.code,
                            starts_at=starts,
                            ends_at=ends,
                            source="order",
                            order_id=order.id,
                        )
                    )
                if order.coupon_code:  # a code is used when its order is paid, once
                    await db.execute(update(Coupon).where(Coupon.code == order.coupon_code).values(used=Coupon.used + 1))
        db.add(
            PaymentEvent(
                reference=reference, order_code=order_code, order_id=order.id, amount=amount, source=source, outcome=settlement.outcome, raw=raw
            )
        )
        await db.commit()
        return settlement.outcome
    except IntegrityError:
        # the same payment (or the same order's entitlement) arrived on another connection first
        await db.rollback()
        return "repeat"


async def refresh_order(db: AsyncSession, order: BillingOrder, payos: PayosClient | None = None, force: bool = False) -> BillingOrder:
    """Ask payOS what became of an order that is not settled, and apply what it says. The order
    screen calls this on every poll (throttled); the reconcile job calls it for every open order;
    "I paid but nothing unlocked" calls it with force."""
    now = _now()
    if order.status not in (PENDING, UNDERPAID, EXPIRED, CANCELLED) or not settings.billing_configured:
        return order
    if not force and order.last_checked_at and now - order.last_checked_at < REFRESH_EVERY:
        return order
    # read what is needed now: a rollback inside apply_payment expires the object
    order_id, order_code, expires_at = order.id, order.order_code, order.expires_at
    await db.execute(update(BillingOrder).where(BillingOrder.id == order_id).values(last_checked_at=now))
    await db.commit()
    try:
        info = await asyncio.to_thread((payos or make_client()).get_payment, order_code)
    except PayosError as exc:
        log.warning("[billing] could not ask payOS about an order: %s", exc)
        await db.refresh(order)
        return order
    transactions = list(info.transactions)
    if not transactions and info.status == "PAID" and info.amount_paid:
        transactions = [Transaction(reference=f"link:{info.id}", amount=info.amount_paid)]
    for t in transactions:
        await apply_payment(
            db, order_code=order_code, amount=t.amount, reference=t.reference, source="reconcile", raw={"status": info.status}
        )
    # nothing paid, and the link is dead: say so (a conditional update, so a payment that landed a
    # moment ago through the webhook is never overwritten)
    if info.status in ("CANCELLED", "EXPIRED") or (info.status == "PENDING" and expires_at < now - timedelta(minutes=5)):
        await db.execute(
            update(BillingOrder)
            .where(BillingOrder.id == order_id, BillingOrder.status == PENDING, BillingOrder.paid_amount == 0)
            .values(status=CANCELLED if info.status == "CANCELLED" else EXPIRED)
        )
        await db.commit()
    await db.refresh(order)
    return order


async def reconcile_pending(factory: async_sessionmaker[AsyncSession], payos: PayosClient | None = None) -> dict:
    """Every order that could still receive money (made in the last 24 hours and not PAID): ask
    payOS. Rescues a webhook that fell while the API was being deployed."""
    since = _now() - RECONCILE_WINDOW
    async with factory() as db:
        ids = (
            (
                await db.execute(
                    select(BillingOrder.id)
                    .where(BillingOrder.status.in_((PENDING, UNDERPAID, EXPIRED)), BillingOrder.created_at > since)
                    .order_by(BillingOrder.created_at)
                    .limit(100)
                )
            )
            .scalars()
            .all()
        )
    checked = unlocked = failed = 0
    payos = payos or make_client()
    for order_id in ids:
        try:
            async with factory() as db:
                order = await db.get(BillingOrder, order_id)
                if order is None:
                    continue
                before = order.status
                order = await refresh_order(db, order, payos, force=True)
                checked += 1
                unlocked += int(before != PAID and order.status == PAID)
        except Exception:  # one bad order must not stop the others
            failed += 1
            log.exception("[billing] reconcile failed for one order")
    return {"checked": checked, "unlocked": unlocked, "failed": failed}


async def reconcile_pending_standalone() -> dict:
    """The Celery task's entry: its own short-lived engine (a worker has no event loop of its own)."""
    engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
    try:
        return await reconcile_pending(async_sessionmaker(engine, expire_on_commit=False))
    finally:
        await engine.dispose()


# ----------------------------------------------------------- admin's hand --
async def grant_entitlement(
    db: AsyncSession,
    *,
    profile_id: uuid.UUID,
    product_code: str,
    granted_by: uuid.UUID,
    note: str | None,
    days: int | None = None,
    order_id: uuid.UUID | None = None,
) -> Entitlement:
    """An admin gives a right by hand (a short payment accepted, a gift, a refund undone). With
    `order_id` the order is closed as PAID by the admin and the grant is its entitlement. A combo
    grants each of its products (the first row is returned)."""
    now = _now()
    windows: list[tuple[str, str, datetime, datetime | None]] = []  # kind, code, starts, ends
    if product_code == catalog.ALL:
        windows.append(("grant", catalog.ALL, now, (now + timedelta(days=days) if days else None)))
    else:
        product = catalog.get(product_code)
        if product is None:
            raise BillingError(404, "unknown_product", "Sản phẩm này không có.")
        for part in catalog.parts(product):
            starts, ends = entitlement_window(part, now, await _active_pass_end(db, profile_id, now, part.kind), days)
            windows.append((part.kind, part.code, starts, ends))
    order = None
    if order_id is not None:
        order = (await db.execute(select(BillingOrder).where(BillingOrder.id == order_id).with_for_update())).scalar_one_or_none()
        if order is None or order.profile_id != profile_id:
            raise BillingError(404, "not_found", "Không thấy đơn này của người học.")
        if (await db.execute(select(Entitlement.id).where(Entitlement.order_id == order.id))).first():
            raise BillingError(409, "already_granted", "Đơn này đã mở khoá rồi.")
        order.status = PAID
        order.paid_at = order.paid_at or now
        order.needs_review = False
        _note(order, f"Admin cấp quyền tay. {note or ''}".strip())
    rows = [
        Entitlement(
            profile_id=profile_id,
            kind=kind,
            product_code=code,
            starts_at=starts,
            ends_at=ends,
            source="admin",
            order_id=order.id if order else None,
            granted_by=granted_by,
            note=note,
        )
        for kind, code, starts, ends in windows
    ]
    db.add_all(rows)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise BillingError(409, "already_granted", "Đơn này đã mở khoá rồi.") from None
    return rows[0]

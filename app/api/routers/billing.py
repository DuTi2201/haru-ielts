"""Paid access: the price list, orders (payOS), the payOS webhook, "I paid but nothing unlocked",
and the admin's tools. See app/services/billing. With BILLING_ENABLED off the list still answers
(enabled: false) and nothing can be bought."""
import logging
import uuid
from datetime import datetime, timezone
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import _problem, get_current_profile, pass_minutes, require_role, trial_left_of, trial_used
from app.core.config import settings
from app.db import get_db
from app.models import (
    BillingClaim,
    BillingOrder,
    BillingSetting,
    Coupon,
    Entitlement,
    FeatureRule,
    PaymentEvent,
    Profile,
    ProductSetting,
    SiteSetting,
)
from app.services.billing import access as billing_access
from app.services.billing import catalog, coupons, features, orders, merchant, settings_db, support
from app.services.billing.payos_client import PayosError, make_client

log = logging.getLogger(__name__)
router = APIRouter(tags=["billing"])


# ----------------------------------------------------------------- shapes --
class ProductOut(BaseModel):
    code: str
    kind: Literal["lesson_pack", "exam_pass", "feature_pass", "combo"]
    title_vi: str
    blurb_vi: str
    amount: int
    compare_at: int | None = None  # a "was" price, struck through
    days: int | None = None
    lessons: list[list[int]] = []
    lesson_count: int = 0
    features: list[str] = []
    minutes: int | None = None  # a Haru Nói pass: live minutes included (None = no total)
    includes: list[str] = []  # a combo: the products it grants
    list_total: int | None = None  # a combo: its products bought one by one, at today's prices


class FeatureRuleOut(BaseModel):
    feature: str
    label_vi: str
    mode: Literal["free", "trial", "paid"]
    trial_amount: int  # the one-time trial: minutes (Trò chuyện + Tranh luận share them) or tries
    trial_unit: Literal["phút", "lượt"]
    trial_shared: bool  # the minutes are one pool for every live feature


class MerchantOut(BaseModel):
    """Who sells (the terms, refund and contact pages)."""

    name: str | None = None
    tax_id: str | None = None
    address: str | None = None
    email: str | None = None
    phone: str | None = None


class MerchantIn(BaseModel):
    name: str | None = Field(default=None, max_length=300)
    tax_id: str | None = Field(default=None, max_length=300)
    address: str | None = Field(default=None, max_length=300)
    email: str | None = Field(default=None, max_length=300)
    phone: str | None = Field(default=None, max_length=300)


class MerchantAdminOut(MerchantIn):
    """What is saved (an empty field: the server's MERCHANT_* setting) and what every page shows."""

    shown: MerchantOut


class TrialOut(BaseModel):
    """The one-time free trial of the AI speaking features (per account, never renewed)."""

    live_trial_minutes: int
    present_trial_tries: int


class SupportLinkOut(BaseModel):
    kind: Literal["zalo", "telegram", "messenger", "facebook", "email", "phone"]
    label: str
    value: str  # as the admin typed it (shown)
    url: str  # what it opens: https://zalo.me/…, mailto:…, tel:…


class SupportOut(BaseModel):
    """Where a learner gets help (set by an admin on the admin page)."""

    links: list[SupportLinkOut] = []
    hours: str | None = None
    note: str | None = None


class SupportIn(BaseModel):
    zalo: str | None = Field(default=None, max_length=200)
    telegram: str | None = Field(default=None, max_length=200)
    messenger: str | None = Field(default=None, max_length=200)
    facebook: str | None = Field(default=None, max_length=200)
    email: str | None = Field(default=None, max_length=200)
    phone: str | None = Field(default=None, max_length=200)
    hours: str | None = Field(default=None, max_length=300)
    note: str | None = Field(default=None, max_length=300)


class SupportAdminOut(SupportIn):
    """What is saved (empty: the server's BILLING_SUPPORT_URL / MERCHANT_* are used) and what learners see."""

    shown: SupportOut


def support_out() -> SupportOut:
    c = support.current()
    return SupportOut(
        links=[SupportLinkOut(kind=l.kind, label=l.label, value=l.value, url=l.url) for l in support.links()],  # type: ignore[arg-type]
        hours=c.get("hours"),
        note=c.get("note"),
    )


class CatalogOut(BaseModel):
    enabled: bool  # false: everything is open, nothing is sold yet
    purchasable: bool  # payOS is configured
    free_lesson_max: int
    support_url: str | None = None  # one link (the first channel), for a single button
    support: SupportOut | None = None
    products: list[ProductOut]
    feature_rules: list[FeatureRuleOut] = []
    trial: TrialOut | None = None
    merchant: MerchantOut = MerchantOut()
    # the corpus (Luyện nghe), the editorials (Đọc xã luận) and the real past papers are for the
    # team only (settings.BILLING_PRIVATE_SOURCES): the app does not offer them to learners
    private_sources: bool = False


class ExamPassOut(BaseModel):
    active: bool
    ends_at: datetime | None = None


class FeaturePassOut(BaseModel):
    active: bool
    ends_at: datetime | None = None
    features: list[str] = []
    minutes_total: int | None = None  # live minutes of the passes held (None = no total)
    minutes_left: int | None = None


class FeatureTrialOut(BaseModel):
    unlimited: bool  # a pass, a free feature or billing off: no trial limit
    left: int | None = None  # what is left of the trial (minutes / tries); None = unlimited
    total: int | None = None
    unit: str | None = None


class EntitlementsOut(BaseModel):
    billing_enabled: bool
    everything: bool
    lesson_packs: list[str]
    exam_pass: ExamPassOut
    feature_pass: FeaturePassOut = FeaturePassOut(active=False)
    features_trial: dict[str, FeatureTrialOut] = {}


class TransferOut(BaseModel):
    qr_code: str | None = None
    bank_bin: str | None = None
    account_number: str | None = None
    account_name: str | None = None
    description: str | None = None


class OrderOut(BaseModel):
    id: uuid.UUID
    order_code: int
    product_code: str
    product_title: str
    amount: int  # what is paid
    list_amount: int | None = None  # the price before the discount code
    discount: int = 0
    coupon_code: str | None = None
    status: str
    paid_amount: int
    expires_at: datetime
    paid_at: datetime | None = None
    created_at: datetime
    checkout_url: str | None = None
    transfer: TransferOut | None = None
    unlocked: bool
    message_vi: str


class OrderCreate(BaseModel):
    product_code: str = Field(min_length=1, max_length=40)
    coupon_code: str | None = Field(default=None, max_length=40)


class QuoteIn(BaseModel):
    product_code: str = Field(min_length=1, max_length=40)
    coupon_code: str | None = Field(default=None, max_length=40)


class QuoteOut(BaseModel):
    """The checkout summary: what this learner pays for this product with this code."""

    product: ProductOut
    list_amount: int
    discount: int
    total: int
    coupon_code: str | None = None
    coupon_label_vi: str | None = None
    coupon_error_vi: str | None = None
    credit: int = 0  # paid before for smaller packs inside this one, taken off (orders.upgrade_credit)
    owned: bool
    purchasable: bool


class ClaimCreate(BaseModel):
    order_id: uuid.UUID | None = None
    note: str = Field(min_length=1, max_length=500)
    bank_ref: str | None = Field(default=None, max_length=80)


class ClaimOut(BaseModel):
    id: uuid.UUID
    order_id: uuid.UUID | None = None
    note: str
    bank_ref: str | None = None
    status: str
    resolution: str | None = None
    created_at: datetime


class ClaimResultOut(BaseModel):
    unlocked: bool  # the check found the payment and opened it
    claim: ClaimOut | None = None
    order: OrderOut | None = None
    support_url: str | None = None


def _message(order: BillingOrder) -> str:
    s = order.status
    if s == "PAID":
        return "Đã thanh toán, đã mở khoá."
    if s == "UNDERPAID":
        return f"Đã nhận {order.paid_amount:,}đ, còn thiếu {order.amount - order.paid_amount:,}đ. Chuyển bù đúng số còn thiếu hoặc liên hệ hỗ trợ.".replace(",", ".")
    if s == "EXPIRED":
        return "Đơn đã hết hạn. Nếu bạn đã chuyển tiền, hãy bấm “Tôi đã thanh toán nhưng chưa mở khoá”."
    if s == "CANCELLED":
        return "Đơn đã huỷ."
    if s == "NEEDS_REVIEW":
        return "Đơn đang được kiểm tra thủ công, bạn sẽ được mở khoá sớm."
    return "Đang chờ thanh toán. Đừng sửa nội dung chuyển khoản."


def order_out(order: BillingOrder) -> OrderOut:
    product = catalog.get(order.product_code)
    info = order.payment_info or {}
    pending = order.status == "PENDING"
    return OrderOut(
        id=order.id,
        order_code=order.order_code,
        product_code=order.product_code,
        product_title=product.title_vi if product else order.product_code,
        amount=order.amount,
        list_amount=order.list_amount,
        discount=order.discount or 0,
        coupon_code=order.coupon_code,
        status=order.status,
        paid_amount=order.paid_amount or 0,
        expires_at=order.expires_at,
        paid_at=order.paid_at,
        created_at=order.created_at,
        checkout_url=order.checkout_url if pending else None,
        transfer=(
            TransferOut(
                qr_code=info.get("qr_code"),
                bank_bin=info.get("bank_bin"),
                account_number=info.get("account_number"),
                account_name=info.get("account_name"),
                description=info.get("description"),
            )
            if pending and info
            else None
        ),
        unlocked=order.status == "PAID",
        message_vi=_message(order),
    )


def claim_out(claim: BillingClaim) -> ClaimOut:
    return ClaimOut(
        id=claim.id,
        order_id=claim.order_id,
        note=claim.note,
        bank_ref=claim.bank_ref,
        status=claim.status,
        resolution=claim.resolution,
        created_at=claim.created_at,
    )


def _refused(exc: orders.BillingError):
    return _problem(exc.status, exc.message, exc.code)


def product_out(p: catalog.Product) -> ProductOut:
    return ProductOut(
        code=p.code,
        kind=p.kind,
        title_vi=p.title_vi,
        blurb_vi=p.blurb_vi,
        amount=p.amount,
        compare_at=p.compare_at,
        days=p.days,
        lessons=[list(r) for r in p.lessons],
        lesson_count=p.lesson_count,
        features=list(p.features),
        minutes=p.minutes,
        includes=list(p.includes),
        list_total=catalog.list_total(p) if p.kind == catalog.COMBO else None,
    )


def feature_rules_out() -> list[FeatureRuleOut]:
    return [
        FeatureRuleOut(
            feature=k,
            label_vi=catalog.FEATURES[k],
            mode=r.mode,
            trial_amount=features.trial_size(k)[0],
            trial_unit=features.trial_size(k)[1],  # type: ignore[arg-type]
            trial_shared=k in features.LIVE_FEATURES,
        )
        for k, r in features.rules().items()
        if k in catalog.FEATURES
    ]


def trial_out() -> TrialOut:
    return TrialOut(**features.trial())


def merchant_out() -> MerchantOut:
    return MerchantOut(**merchant.current())


def _purchasable() -> bool:
    return settings.billing_configured and bool(settings.frontend_origin)


# ------------------------------------------------------------------ public --
@router.get("/billing/catalog", response_model=CatalogOut)
async def get_catalog(db: Annotated[AsyncSession, Depends(get_db)]):
    """The price list. Public: the pricing page, the landing page and the locked-lesson cards read it."""
    await settings_db.refresh(db)
    return CatalogOut(
        enabled=settings.BILLING_ENABLED,
        purchasable=_purchasable(),
        free_lesson_max=catalog.FREE_LESSON_MAX,
        support_url=support.primary_url(),
        support=support_out(),
        products=[product_out(p) for p in catalog.listed()],
        feature_rules=feature_rules_out(),
        trial=trial_out(),
        merchant=merchant_out(),
        private_sources=bool(settings.BILLING_ENABLED and settings.BILLING_PRIVATE_SOURCES),
    )


@router.post("/billing/payos/webhook")
async def payos_webhook(request: Request, db: Annotated[AsyncSession, Depends(get_db)]):
    """payOS tells us a payment arrived. Public, so the signature is checked FIRST and an unsigned
    or altered body does nothing. A signed one is counted once (orders.apply_payment) and answered
    200 at once, whatever it concerned (an order we do not know is recorded and still answered 200,
    so payOS's own test call of this URL succeeds)."""
    if not settings.billing_configured:
        raise _problem(status.HTTP_503_SERVICE_UNAVAILABLE, "Billing is not configured", "billing_unavailable")
    try:
        body = await request.json()
    except ValueError:
        raise _problem(status.HTTP_400_BAD_REQUEST, "Invalid body", "bad_request") from None
    try:
        payment = make_client().verify_webhook(body)
    except PayosError:
        log.warning("[billing] a webhook with a bad signature was ignored")
        raise _problem(status.HTTP_400_BAD_REQUEST, "Invalid signature", "bad_signature") from None
    if not payment.paid:
        return {"ok": True, "outcome": "ignored"}
    outcome = await orders.apply_payment(
        db,
        order_code=payment.order_code,
        amount=payment.amount,
        reference=payment.reference,
        source="webhook",
        # what is kept of the body: the money facts only (no payer's name or account number)
        raw={
            k: body["data"].get(k)
            for k in ("orderCode", "amount", "reference", "description", "paymentLinkId", "transactionDateTime", "code")
        },
    )
    return {"ok": True, "outcome": outcome}


# ----------------------------------------------------------------- learner --
@router.get("/me/entitlements", response_model=EntitlementsOut)
async def my_entitlements(
    db: Annotated[AsyncSession, Depends(get_db)], profile: Annotated[Profile, Depends(get_current_profile)]
):
    held = await billing_access.load_access(db, profile)
    await settings_db.refresh(db)
    trial: dict[str, FeatureTrialOut] = {}
    for key in catalog.FEATURES:
        if held.has_feature(key) or features.rule(key).mode == "free":
            trial[key] = FeatureTrialOut(unlimited=True)
        else:
            amount, unit = features.trial_size(key)
            trial[key] = FeatureTrialOut(
                unlimited=False,
                left=trial_left_of(key, await trial_used(db, profile.id, key)),
                total=amount if features.rule(key).mode == "trial" else 0,
                unit=unit,
            )
    minutes = await pass_minutes(db, profile.id) if held.features and not held.everything and held.enforced else None
    return EntitlementsOut(
        billing_enabled=settings.BILLING_ENABLED,
        everything=held.everything,
        lesson_packs=sorted(held.packs),
        exam_pass=ExamPassOut(active=held.can_use_exam_pass(), ends_at=held.exam_pass_until),
        feature_pass=FeaturePassOut(
            active=bool(held.features) or held.everything or not held.enforced,
            ends_at=held.features_until,
            features=sorted(held.features),
            minutes_total=minutes[1] if minutes else None,
            minutes_left=max(0, minutes[1] * 60 - minutes[0]) // 60 if minutes else None,
        ),
        features_trial=trial,
    )


@router.post("/billing/quote", response_model=QuoteOut)
async def quote(
    body: QuoteIn,
    db: Annotated[AsyncSession, Depends(get_db)],
    profile: Annotated[Profile, Depends(get_current_profile)],
):
    """The checkout summary before paying: list price, the discount code checked, the total."""
    try:
        product, q, coupon_error = await orders.quote(db, profile, body.product_code, body.coupon_code)
    except orders.BillingError as exc:
        raise _refused(exc) from None
    held = await billing_access.load_access(db, profile)
    return QuoteOut(
        product=product_out(product),
        list_amount=q.list_amount,
        discount=q.discount,
        total=q.total,
        coupon_code=q.coupon_code,
        coupon_label_vi=q.coupon_label_vi,
        coupon_error_vi=coupon_error,
        credit=q.credit,
        owned=held.owns(product),
        purchasable=_purchasable(),
    )


@router.post("/billing/orders", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
async def create_order(
    body: OrderCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    profile: Annotated[Profile, Depends(get_current_profile)],
):
    """Buy a product: makes a pending order (price from the catalogue) and a payOS payment link."""
    try:
        order = await orders.create_order(db, profile, body.product_code, coupon_code=body.coupon_code)
    except orders.BillingError as exc:
        raise _refused(exc) from None
    return order_out(order)


@router.get("/billing/orders", response_model=list[OrderOut])
async def my_orders(
    db: Annotated[AsyncSession, Depends(get_db)], profile: Annotated[Profile, Depends(get_current_profile)]
):
    rows = (
        (await db.execute(select(BillingOrder).where(BillingOrder.profile_id == profile.id).order_by(BillingOrder.created_at.desc()).limit(30)))
        .scalars()
        .all()
    )
    return [order_out(o) for o in rows]


async def _own_order(db: AsyncSession, order_id: uuid.UUID, profile: Profile) -> BillingOrder:
    order = await db.get(BillingOrder, order_id)
    if order is None or order.profile_id != profile.id:  # someone else's order looks like no order
        raise _problem(status.HTTP_404_NOT_FOUND, "Order not found", "not_found")
    return order


@router.get("/billing/orders/{order_id}", response_model=OrderOut)
async def get_order(
    order_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    profile: Annotated[Profile, Depends(get_current_profile)],
):
    """The paying screen polls this every few seconds. While the order waits, payOS is asked too
    (at most every 20 s), so a slow webhook does not leave the learner looking at a QR."""
    order = await _own_order(db, order_id, profile)
    return order_out(await orders.refresh_order(db, order))


@router.post("/billing/orders/{order_id}/cancel", response_model=OrderOut)
async def cancel_order(
    order_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    profile: Annotated[Profile, Depends(get_current_profile)],
):
    order = await _own_order(db, order_id, profile)
    try:
        return order_out(await orders.cancel_order(db, order))
    except orders.BillingError as exc:
        raise _refused(exc) from None


MAX_OPEN_CLAIMS = 5


@router.post("/billing/claims", response_model=ClaimResultOut, status_code=status.HTTP_201_CREATED)
async def create_claim(
    body: ClaimCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    profile: Annotated[Profile, Depends(get_current_profile)],
):
    """"Tôi đã thanh toán nhưng chưa mở khoá." First ask payOS again about that order; if the money
    is found it unlocks and no claim is needed. Only then is a claim opened for an admin."""
    profile_id = profile.id
    order = await _own_order(db, body.order_id, profile) if body.order_id else None
    if order is not None:
        order = await orders.refresh_order(db, order, force=True)
        if order.status == "PAID":
            return ClaimResultOut(unlocked=True, order=order_out(order))
    open_claims = (
        (await db.execute(select(BillingClaim.id).where(BillingClaim.profile_id == profile_id, BillingClaim.status == "open")))
        .scalars()
        .all()
    )
    if len(open_claims) >= MAX_OPEN_CLAIMS:
        raise _problem(status.HTTP_429_TOO_MANY_REQUESTS, "Bạn đang có nhiều yêu cầu chưa xử lý", "too_many_claims")
    claim = BillingClaim(
        profile_id=profile_id,
        order_id=order.id if order else None,
        note=body.note.strip(),
        bank_ref=(body.bank_ref or "").strip() or None,
    )
    db.add(claim)
    await db.commit()
    await db.refresh(claim)
    return ClaimResultOut(
        unlocked=False,
        claim=claim_out(claim),
        order=order_out(order) if order else None,
        support_url=support.primary_url(),
    )


@router.get("/billing/claims", response_model=list[ClaimOut])
async def my_claims(
    db: Annotated[AsyncSession, Depends(get_db)], profile: Annotated[Profile, Depends(get_current_profile)]
):
    rows = (
        (await db.execute(select(BillingClaim).where(BillingClaim.profile_id == profile.id).order_by(BillingClaim.created_at.desc()).limit(30)))
        .scalars()
        .all()
    )
    return [claim_out(c) for c in rows]


# ------------------------------------------------------------------- admin --
admin = APIRouter(prefix="/admin/billing", tags=["billing-admin"])


class AdminOrderOut(OrderOut):
    email: str
    profile_id: uuid.UUID
    needs_review: bool
    note: str | None = None
    provider_ref: str | None = None


class AdminClaimOut(ClaimOut):
    email: str
    profile_id: uuid.UUID


class GrantIn(BaseModel):
    email: str | None = Field(default=None, max_length=255)
    profile_id: uuid.UUID | None = None
    product_code: str = Field(min_length=1, max_length=40)  # a catalogue code, or "all"
    days: int | None = Field(default=None, ge=1, le=3650)
    note: str | None = Field(default=None, max_length=500)
    order_id: uuid.UUID | None = None  # close this order as paid by hand


class EntitlementRowOut(BaseModel):
    id: uuid.UUID
    profile_id: uuid.UUID
    kind: str
    product_code: str
    starts_at: datetime
    ends_at: datetime | None = None
    source: str
    order_id: uuid.UUID | None = None
    note: str | None = None
    revoked_at: datetime | None = None


class ResolveIn(BaseModel):
    status: Literal["resolved", "rejected"]
    resolution: str | None = Field(default=None, max_length=500)


class ReviewDoneIn(BaseModel):
    note: str | None = Field(default=None, max_length=500)


class PaymentEventOut(BaseModel):
    """One payment payOS reported for an order (the money facts only)."""

    id: uuid.UUID
    reference: str
    amount: int
    source: str
    outcome: str
    created_at: datetime


def _admin_order(order: BillingOrder, email: str) -> AdminOrderOut:
    base = order_out(order)
    return AdminOrderOut(
        **base.model_dump(),
        email=email,
        profile_id=order.profile_id,
        needs_review=bool(order.needs_review),
        note=order.note,
        provider_ref=order.provider_ref,
    )


@admin.get("/orders", response_model=list[AdminOrderOut])
async def admin_orders(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[Profile, Depends(require_role("admin"))],
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    needs_review: bool | None = None,
    email: str | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
):
    query = select(BillingOrder, Profile.email).join(Profile, Profile.id == BillingOrder.profile_id)
    if status_filter:
        query = query.where(BillingOrder.status == status_filter.upper())
    if needs_review is not None:
        query = query.where(BillingOrder.needs_review == needs_review)
    if email:
        query = query.where(Profile.email.ilike(f"%{email.strip()}%"))
    rows = (await db.execute(query.order_by(BillingOrder.created_at.desc()).limit(limit))).all()
    return [_admin_order(o, e) for o, e in rows]


async def _order_with_email(db: AsyncSession, order_id: uuid.UUID) -> tuple[BillingOrder, str]:
    row = (
        await db.execute(select(BillingOrder, Profile.email).join(Profile, Profile.id == BillingOrder.profile_id).where(BillingOrder.id == order_id))
    ).first()
    if row is None:
        raise _problem(status.HTTP_404_NOT_FOUND, "Order not found", "not_found")
    return row[0], row[1]


@admin.get("/orders/{order_id}/events", response_model=list[PaymentEventOut])
async def admin_order_events(
    order_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[Profile, Depends(require_role("admin"))],
):
    """The payments payOS reported for this order, oldest first: what a short / extra / late payment was."""
    order, _email = await _order_with_email(db, order_id)
    rows = (
        (await db.execute(select(PaymentEvent).where(PaymentEvent.order_code == order.order_code).order_by(PaymentEvent.created_at)))
        .scalars()
        .all()
    )
    return [
        PaymentEventOut(id=r.id, reference=r.reference, amount=r.amount, source=r.source, outcome=r.outcome, created_at=r.created_at)
        for r in rows
    ]


@admin.post("/orders/{order_id}/review-done", response_model=AdminOrderOut)
async def admin_review_done(
    order_id: uuid.UUID,
    body: ReviewDoneIn,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin_profile: Annotated[Profile, Depends(require_role("admin"))],
):
    """"I looked at it" (a refund of the extra paid on the payOS side, a short payment left as it is):
    takes the order off the review queue and writes who did it into its note. Opens nothing."""
    order, email = await _order_with_email(db, order_id)
    if order.needs_review:
        line = f"Admin {admin_profile.id} đã xem xong. {body.note or ''}".strip()
        order.note = f"{order.note}\n{line}" if order.note else line
        order.needs_review = False
        await db.commit()
        await db.refresh(order)
    return _admin_order(order, email)


@admin.get("/claims", response_model=list[AdminClaimOut])
async def admin_claims(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[Profile, Depends(require_role("admin"))],
    status_filter: Annotated[str, Query(alias="status")] = "open",
):
    rows = (
        await db.execute(
            select(BillingClaim, Profile.email)
            .join(Profile, Profile.id == BillingClaim.profile_id)
            .where(BillingClaim.status == status_filter)
            .order_by(BillingClaim.created_at)
            .limit(100)
        )
    ).all()
    return [AdminClaimOut(**claim_out(c).model_dump(), email=e, profile_id=c.profile_id) for c, e in rows]


@admin.post("/claims/{claim_id}/resolve", response_model=ClaimOut)
async def admin_resolve_claim(
    claim_id: uuid.UUID,
    body: ResolveIn,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin_profile: Annotated[Profile, Depends(require_role("admin"))],
):
    claim = await db.get(BillingClaim, claim_id)
    if claim is None:
        raise _problem(status.HTTP_404_NOT_FOUND, "Claim not found", "not_found")
    claim.status = body.status
    claim.resolution = body.resolution
    claim.resolved_by = admin_profile.id
    claim.resolved_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(claim)
    return claim_out(claim)


@admin.post("/grants", response_model=EntitlementRowOut, status_code=status.HTTP_201_CREATED)
async def admin_grant(
    body: GrantIn,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin_profile: Annotated[Profile, Depends(require_role("admin"))],
):
    """Give a learner a right by hand and leave a trace (who, why). Name the learner by e-mail or id."""
    if body.profile_id is None and not body.email:
        raise _problem(status.HTTP_422_UNPROCESSABLE_ENTITY, "Name the learner by email or id", "bad_request")
    target_id = body.profile_id
    if target_id is None:
        target_id = (
            await db.execute(select(Profile.id).where(Profile.email == (body.email or "").strip().lower()))
        ).scalar_one_or_none()
    if target_id is None or await db.get(Profile, target_id) is None:
        raise _problem(status.HTTP_404_NOT_FOUND, "Learner not found", "not_found")
    try:
        row = await orders.grant_entitlement(
            db,
            profile_id=target_id,
            product_code=body.product_code,
            granted_by=admin_profile.id,
            note=body.note,
            days=body.days,
            order_id=body.order_id,
        )
    except orders.BillingError as exc:
        raise _refused(exc) from None
    return row


@admin.get("/entitlements", response_model=list[EntitlementRowOut])
async def admin_entitlements(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[Profile, Depends(require_role("admin"))],
    email: str,
):
    """Everything one learner holds, revoked rows included."""
    rows = (
        (
            await db.execute(
                select(Entitlement)
                .join(Profile, Profile.id == Entitlement.profile_id)
                .where(Profile.email == email.strip().lower())
                .order_by(Entitlement.created_at.desc())
            )
        )
        .scalars()
        .all()
    )
    return rows


@admin.post("/entitlements/{entitlement_id}/revoke", response_model=EntitlementRowOut)
async def admin_revoke(
    entitlement_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin_profile: Annotated[Profile, Depends(require_role("admin"))],
):
    row = await db.get(Entitlement, entitlement_id)
    if row is None:
        raise _problem(status.HTTP_404_NOT_FOUND, "Entitlement not found", "not_found")
    if row.revoked_at is None:
        row.revoked_at = datetime.now(timezone.utc)
        row.note = f"{row.note + ' | ' if row.note else ''}revoked by admin {admin_profile.id}"
        await db.commit()
        await db.refresh(row)
    return row


@admin.post("/reconcile")
async def admin_reconcile(_: Annotated[Profile, Depends(require_role("admin"))]):
    """Ask payOS now about every order of the last 24 hours that is not paid (the job does this every 5 minutes)."""
    if not settings.billing_configured:
        raise _problem(status.HTTP_503_SERVICE_UNAVAILABLE, "Billing is not configured", "billing_unavailable")
    return await orders.reconcile_pending_standalone()




# ------------------------------------------------- admin: prices, rules, codes --
class AdminProductOut(ProductOut):
    active: bool
    default_amount: int
    default_title_vi: str
    overridden: bool  # an admin setting is applied


class ProductSettingIn(BaseModel):
    amount: int = Field(ge=catalog.MIN_AMOUNT, le=catalog.MAX_AMOUNT)
    compare_at: int | None = Field(default=None, ge=0, le=catalog.MAX_AMOUNT)
    title_vi: str | None = Field(default=None, max_length=120)
    blurb_vi: str | None = Field(default=None, max_length=1000)
    active: bool = True


class FeatureRuleIn(BaseModel):
    mode: Literal["free", "trial", "paid"]


class TrialIn(BaseModel):
    live_trial_minutes: int = Field(ge=5, le=60)
    present_trial_tries: int = Field(ge=0, le=20)


class CouponIn(BaseModel):
    code: str = Field(min_length=3, max_length=32)
    percent_off: int | None = Field(default=None, ge=1, le=90)
    amount_off: int | None = Field(default=None, ge=1000, le=catalog.MAX_AMOUNT)
    product_codes: list[str] | None = None
    max_uses: int | None = Field(default=None, ge=1, le=1_000_000)
    once_per_learner: bool = True
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    note: str | None = Field(default=None, max_length=500)


class CouponPatch(BaseModel):
    active: bool | None = None
    max_uses: int | None = Field(default=None, ge=1, le=1_000_000)
    ends_at: datetime | None = None
    note: str | None = Field(default=None, max_length=500)


class CouponOut(BaseModel):
    code: str
    label_vi: str
    percent_off: int | None = None
    amount_off: int | None = None
    product_codes: list[str] | None = None
    max_uses: int | None = None
    once_per_learner: bool
    used: int
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    active: bool
    note: str | None = None
    created_at: datetime


def _admin_product(p: catalog.Product, overridden: bool) -> AdminProductOut:
    d = catalog.default(p.code) or p
    return AdminProductOut(
        **product_out(p).model_dump(), active=p.active, default_amount=d.amount, default_title_vi=d.title_vi, overridden=overridden
    )


async def _admin_products(db: AsyncSession) -> list[AdminProductOut]:
    await settings_db.refresh(db, force=True)
    set_codes = set((await db.execute(select(ProductSetting.product_code))).scalars().all())
    return [_admin_product(p, p.code in set_codes) for p in sorted(catalog.PRODUCTS, key=lambda p: p.order)]


def coupon_out(c: Coupon) -> CouponOut:
    return CouponOut(
        code=c.code, label_vi=coupons.label_vi(c), percent_off=c.percent_off, amount_off=c.amount_off,
        product_codes=c.product_codes, max_uses=c.max_uses, once_per_learner=c.once_per_learner, used=c.used,
        starts_at=c.starts_at, ends_at=c.ends_at, active=c.active, note=c.note, created_at=c.created_at,
    )


@admin.get("/products", response_model=list[AdminProductOut])
async def admin_products(
    db: Annotated[AsyncSession, Depends(get_db)], _: Annotated[Profile, Depends(require_role("admin"))]
):
    """Every product, on sale or not, with its default and current price."""
    return await _admin_products(db)


@admin.put("/products/{code}", response_model=list[AdminProductOut])
async def admin_set_product(
    code: str,
    body: ProductSettingIn,
    db: Annotated[AsyncSession, Depends(get_db)],
    who: Annotated[Profile, Depends(require_role("admin"))],
):
    """Set a product's price, "was" price, name, blurb and whether it is on sale. Orders already
    made keep their price; rights already bought are not touched."""
    if catalog.default(code) is None:
        raise _problem(status.HTTP_404_NOT_FOUND, "Không có sản phẩm này.", "unknown_product")
    if body.compare_at is not None and body.compare_at and body.compare_at <= body.amount:
        raise _problem(status.HTTP_422_UNPROCESSABLE_ENTITY, "Giá gốc phải cao hơn giá bán.", "bad_compare_at")
    row = await db.get(ProductSetting, code) or ProductSetting(product_code=code)
    row.amount = body.amount
    row.compare_at = body.compare_at or None
    row.title_vi = (body.title_vi or "").strip() or None
    row.blurb_vi = (body.blurb_vi or "").strip() or None
    row.active = body.active
    row.updated_by = who.id
    db.add(row)
    await db.commit()
    log.info("[billing] admin set product %s to %s", code, body.amount)
    return await _admin_products(db)


@admin.delete("/products/{code}", response_model=list[AdminProductOut])
async def admin_reset_product(
    code: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[Profile, Depends(require_role("admin"))],
):
    """Back to the default price, name and blurb, on sale."""
    row = await db.get(ProductSetting, code)
    if row is not None:
        await db.delete(row)
        await db.commit()
    return await _admin_products(db)


@admin.get("/features", response_model=list[FeatureRuleOut])
async def admin_features(
    db: Annotated[AsyncSession, Depends(get_db)], _: Annotated[Profile, Depends(require_role("admin"))]
):
    await settings_db.refresh(db, force=True)
    return feature_rules_out()


@admin.put("/features/{feature}", response_model=list[FeatureRuleOut])
async def admin_set_feature(
    feature: str,
    body: FeatureRuleIn,
    db: Annotated[AsyncSession, Depends(get_db)],
    who: Annotated[Profile, Depends(require_role("admin"))],
):
    """How a feature is sold: free, a one-time trial then a pass, or pass only."""
    if feature not in catalog.FEATURES:
        raise _problem(status.HTTP_404_NOT_FOUND, "Không có tính năng này.", "unknown_feature")
    row = await db.get(FeatureRule, feature) or FeatureRule(feature=feature)
    row.mode = body.mode
    row.updated_by = who.id
    db.add(row)
    await db.commit()
    await settings_db.refresh(db, force=True)
    return feature_rules_out()


@admin.get("/trial", response_model=TrialOut)
async def admin_trial(
    db: Annotated[AsyncSession, Depends(get_db)], _: Annotated[Profile, Depends(require_role("admin"))]
):
    await settings_db.refresh(db, force=True)
    return trial_out()


@admin.put("/trial", response_model=TrialOut)
async def admin_set_trial(
    body: TrialIn,
    db: Annotated[AsyncSession, Depends(get_db)],
    who: Annotated[Profile, Depends(require_role("admin"))],
):
    """The one-time trial's size: minutes of live speaking (Trò chuyện + Tranh luận together) and
    marked presentation tries, per account, for life. Lowering it never takes back what was used."""
    for key, value in body.model_dump().items():
        row = await db.get(BillingSetting, key) or BillingSetting(key=key)
        row.value = value
        row.updated_by = who.id
        db.add(row)
    await db.commit()
    await settings_db.refresh(db, force=True)
    return trial_out()


@admin.get("/coupons", response_model=list[CouponOut])
async def admin_coupons(
    db: Annotated[AsyncSession, Depends(get_db)], _: Annotated[Profile, Depends(require_role("admin"))]
):
    rows = (await db.execute(select(Coupon).order_by(Coupon.created_at.desc()).limit(200))).scalars().all()
    return [coupon_out(c) for c in rows]


@admin.post("/coupons", response_model=CouponOut, status_code=status.HTTP_201_CREATED)
async def admin_create_coupon(
    body: CouponIn,
    db: Annotated[AsyncSession, Depends(get_db)],
    who: Annotated[Profile, Depends(require_role("admin"))],
):
    code = coupons.normalize(body.code)
    if not coupons.CODE_RE.match(code):
        raise _problem(status.HTTP_422_UNPROCESSABLE_ENTITY, "Mã chỉ gồm chữ, số, - và _ (3–32 ký tự).", "bad_code")
    if (body.percent_off is None) == (body.amount_off is None):
        raise _problem(status.HTTP_422_UNPROCESSABLE_ENTITY, "Chọn giảm theo % hoặc theo số tiền.", "bad_discount")
    if body.product_codes:
        unknown = [c for c in body.product_codes if catalog.default(c) is None]
        if unknown:
            raise _problem(status.HTTP_422_UNPROCESSABLE_ENTITY, f"Không có sản phẩm: {', '.join(unknown)}", "unknown_product")
    if body.starts_at and body.ends_at and body.ends_at <= body.starts_at:
        raise _problem(status.HTTP_422_UNPROCESSABLE_ENTITY, "Ngày kết thúc phải sau ngày bắt đầu.", "bad_dates")
    if await db.get(Coupon, code) is not None:
        raise _problem(status.HTTP_409_CONFLICT, "Mã này đã có.", "duplicate")
    c = Coupon(
        code=code, percent_off=body.percent_off, amount_off=body.amount_off, product_codes=body.product_codes or None,
        max_uses=body.max_uses, once_per_learner=body.once_per_learner, used=0, starts_at=body.starts_at,
        ends_at=body.ends_at, active=True, note=body.note, created_by=who.id, created_at=datetime.now(timezone.utc),
    )
    db.add(c)
    await db.commit()
    return coupon_out(c)


@admin.patch("/coupons/{code}", response_model=CouponOut)
async def admin_update_coupon(
    code: str,
    body: CouponPatch,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[Profile, Depends(require_role("admin"))],
):
    """Switch a code off or on, change its limit, end date or note. A code is never deleted: past
    orders name it."""
    c = await db.get(Coupon, coupons.normalize(code))
    if c is None:
        raise _problem(status.HTTP_404_NOT_FOUND, "Không có mã này.", "not_found")
    for k in ("active", "max_uses", "ends_at", "note"):
        if k in body.model_fields_set:
            setattr(c, k, getattr(body, k))
    await db.commit()
    return coupon_out(c)


@admin.get("/support", response_model=SupportAdminOut)
async def admin_support(
    db: Annotated[AsyncSession, Depends(get_db)], _: Annotated[Profile, Depends(require_role("admin"))]
):
    await settings_db.refresh(db, force=True)
    return SupportAdminOut(**support.saved(), shown=support_out())


@admin.put("/support", response_model=SupportAdminOut)
async def admin_set_support(
    body: SupportIn,
    db: Annotated[AsyncSession, Depends(get_db)],
    who: Annotated[Profile, Depends(require_role("admin"))],
):
    """The help channels learners see (the "Hỗ trợ" button, the contact page, the payment dialog).
    Each is checked to make a safe link; leaving every channel empty falls back to the server's
    BILLING_SUPPORT_URL / MERCHANT_EMAIL / MERCHANT_PHONE."""
    try:
        value = support.clean(body.model_dump())
    except support.SupportError as exc:
        raise _problem(status.HTTP_422_UNPROCESSABLE_ENTITY, "Thông tin hỗ trợ chưa đúng", "bad_support_contact", str(exc)) from None
    row = await db.get(SiteSetting, "support") or SiteSetting(key="support")
    row.value = value
    row.updated_by = who.id
    db.add(row)
    await db.commit()
    await settings_db.refresh(db, force=True)
    return SupportAdminOut(**support.saved(), shown=support_out())


@admin.get("/merchant", response_model=MerchantAdminOut)
async def admin_merchant(
    db: Annotated[AsyncSession, Depends(get_db)], _: Annotated[Profile, Depends(require_role("admin"))]
):
    await settings_db.refresh(db, force=True)
    return MerchantAdminOut(**merchant.saved(), shown=merchant_out())


@admin.put("/merchant", response_model=MerchantAdminOut)
async def admin_set_merchant(
    body: MerchantIn,
    db: Annotated[AsyncSession, Depends(get_db)],
    who: Annotated[Profile, Depends(require_role("admin"))],
):
    """Thông tin vận hành: saved once, shown by the footer, /contact and /terms (all read
    /billing/catalog). An empty field falls back to the server's MERCHANT_* setting."""
    try:
        value = merchant.clean(body.model_dump())
    except merchant.MerchantError as exc:
        raise _problem(status.HTTP_422_UNPROCESSABLE_ENTITY, "Thông tin vận hành chưa đúng", "bad_merchant", str(exc)) from None
    row = await db.get(SiteSetting, "merchant") or SiteSetting(key="merchant")
    row.value = value
    row.updated_by = who.id
    db.add(row)
    await db.commit()
    await settings_db.refresh(db, force=True)
    return MerchantAdminOut(**merchant.saved(), shown=merchant_out())


# the admin routes above join the billing router last, so every one of them is included
router.include_router(admin)

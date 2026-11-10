"""Shared parts of the billing tests that use a real Postgres: a fake payOS (httpx MockTransport,
fake keys only) and a base class that opens its own engine, patches the billing settings and cleans
up the rows it made."""
import unittest
import uuid
from unittest import mock

import httpx
from sqlalchemy import create_engine, delete, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.models import (
    BillingClaim,
    BillingOrder,
    Entitlement,
    ErrorLog,
    ItemState,
    Job,
    LessonExerciseResult,
    PaymentEvent,
    PlacementAttempt,
    Profile,
)
from app.services.billing import access as acc
from app.services.billing import orders
from app.services.billing import payos_client as px

KEY = "fake-test-checksum-key"


def _db_ready() -> bool:
    try:
        engine = create_engine(settings.SYNC_DATABASE_URL, connect_args={"connect_timeout": 2})
        with engine.connect() as conn:
            return conn.execute(text("select to_regclass('billing.orders')")).scalar() is not None
    except Exception:
        return False


DB_READY = _db_ready()


class FakePayos:
    """A payOS that signs what it answers; `links` maps order code -> the link state it reports."""

    def __init__(self):
        self.created: list[dict] = []
        self.links: dict[int, dict] = {}
        self.fail_create = False
        self.get_calls = 0
        self.client = px.PayosClient(
            "fake-test-client-id", "fake-test-api-key", KEY, base_url="https://payos.test",
            http=httpx.Client(transport=httpx.MockTransport(self._handle)),
        )

    def _signed(self, data):
        return httpx.Response(200, json={"code": "00", "desc": "success", "data": data, "signature": px.signature_of(data, KEY)})

    def _handle(self, request: httpx.Request):
        import json

        if request.method == "POST" and request.url.path == "/v2/payment-requests":
            if self.fail_create:
                return httpx.Response(200, json={"code": "20", "desc": "boom", "data": None, "signature": None})
            body = json.loads(request.content)
            self.created.append(body)
            return self._signed({
                "bin": "970415", "accountNumber": "111", "accountName": "HARU", "amount": body["amount"],
                "description": body["description"], "orderCode": body["orderCode"], "currency": "VND",
                "paymentLinkId": f"pl-{body['orderCode']}", "status": "PENDING", "expiredAt": body.get("expiredAt"),
                "checkoutUrl": f"https://pay.payos.test/{body['orderCode']}", "qrCode": "000201-fake-qr",
            })
        if request.method == "GET":
            self.get_calls += 1
            code = int(request.url.path.rsplit("/", 1)[1])
            state = self.links.get(code, {})
            paid = state.get("paid", [])
            return self._signed({
                "id": f"pl-{code}", "orderCode": code, "amount": state.get("amount", 29000),
                "amountPaid": state.get("amount_paid", sum(a for _, a in paid)), "amountRemaining": 0, "status": state.get("status", "PENDING"),
                "createdAt": "2026-10-14T10:00:00+07:00",
                "transactions": [{"reference": r, "amount": a, "accountNumber": "1", "description": "d",
                                  "transactionDateTime": "2026-10-14 10:01:00"} for r, a in paid],
            })
        return httpx.Response(404)


# The price list these tests were written against (before October 2026): they test how orders,
# payments, rights and trials WORK, not today's prices, so they keep a fixed catalogue. Today's
# catalogue has its own tests (test_billing_rules.CatalogTests, NewCatalogueTests below it).
LEGACY_PRICES = {"pack_sinh_hoat_2": 29_000, "pack_viet_54": 29_000, "exam_pass_30": 49_000, "exam_pass_90": 119_000}
LEGACY_CODES = ("pack_sinh_hoat_2", "pack_quan_he", "pack_nhap_canh", "pack_cong_so", "pack_viet_54", "pack_xa_hoi",
                "combo_3_packs", "exam_pass_30", "exam_pass_90", "speak_pass_30", "speak_pass_90")


def legacy_catalogue():
    from dataclasses import replace

    from app.services.billing import catalog as cat

    out = []
    for n, code in enumerate(LEGACY_CODES):
        p = cat.default(code)
        out.append(replace(p, active=True, retired=False, order=n + 1, amount=LEGACY_PRICES.get(code, p.amount)))
    return tuple(out)


@unittest.skipUnless(DB_READY, "no Postgres with the billing schema")
class BillingDbCase(unittest.IsolatedAsyncioTestCase):
    LEGACY_CATALOG = True  # False: today's catalogue and trial sizes

    async def asyncSetUp(self):
        from app.services.billing import catalog as cat
        from app.services.billing import features as feat

        if self.LEGACY_CATALOG:
            # cleanups run last-first: these two run after the patches are undone
            self.addCleanup(cat.apply_settings, {})
            self.addCleanup(feat.apply_rules, {}, {})
            for target, name, value in (
                (cat, "DEFAULTS", legacy_catalogue()),
                (feat, "TRIAL_DEFAULTS", {"live_trial_minutes": 20, "present_trial_tries": 3}),
            ):
                p = mock.patch.object(target, name, value)
                p.start()
                self.addCleanup(p.stop)
            cat.apply_settings({})
            feat.apply_rules({}, {})
        self.engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
        self.factory = async_sessionmaker(self.engine, expire_on_commit=False)
        patches = {
            "BILLING_ENABLED": True,
            "PAYOS_CLIENT_ID": "fake-test-client-id",
            "PAYOS_API_KEY": "fake-test-api-key",
            "PAYOS_CHECKSUM_KEY": KEY,
            "FRONTEND_URL": "https://haru.test",
            "BILLING_MAX_PENDING_ORDERS": 3,
        }
        for name, value in patches.items():
            p = mock.patch.object(settings, name, value)
            p.start()
            self.addCleanup(p.stop)
        self.profile_ids: list[uuid.UUID] = []
        self.payos = FakePayos()

    async def asyncTearDown(self):
        async with self.factory() as db:
            ids = self.profile_ids
            order_ids = select(BillingOrder.id).where(BillingOrder.profile_id.in_(ids))
            codes = select(BillingOrder.order_code).where(BillingOrder.profile_id.in_(ids))
            # what the learners did while the test ran (reviews, answers, jobs) refers to them too
            for model, column in (
                (ItemState, ItemState.learner_id),
                (ErrorLog, ErrorLog.learner_id),
                (LessonExerciseResult, LessonExerciseResult.learner_id),
                (Job, Job.owner_id),
                (PlacementAttempt, PlacementAttempt.learner_id),
            ):
                await db.execute(delete(model).where(column.in_(ids)))
            await db.execute(delete(BillingClaim).where(BillingClaim.profile_id.in_(ids)))
            await db.execute(delete(PaymentEvent).where(PaymentEvent.order_code.in_(codes)))
            await db.execute(delete(PaymentEvent).where(PaymentEvent.order_code < 1000))
            await db.execute(delete(Entitlement).where(Entitlement.profile_id.in_(ids)))
            await db.execute(delete(BillingOrder).where(BillingOrder.id.in_(order_ids)))
            await db.execute(delete(Profile).where(Profile.id.in_(ids)))
            await db.commit()
        await self.engine.dispose()

    async def new_profile(self, role="learner") -> Profile:
        async with self.factory() as db:
            p = Profile(email=f"billing-test-{uuid.uuid4().hex}@example.invalid", hashed_password="x", role=role)
            db.add(p)
            await db.commit()
        self.profile_ids.append(p.id)
        return p

    async def buy(self, profile, product="pack_quan_he") -> BillingOrder:
        async with self.factory() as db:
            return await orders.create_order(db, profile, product, payos=self.payos.client)

    async def pay(self, order, amount, reference, source="webhook"):
        async with self.factory() as db:
            return await orders.apply_payment(db, order_code=order.order_code, amount=amount, reference=reference, source=source)

    async def state(self, order):
        async with self.factory() as db:
            row = await db.get(BillingOrder, order.id)
            ents = (await db.execute(select(Entitlement).where(Entitlement.profile_id == order.profile_id))).scalars().all()
            events = (await db.execute(select(PaymentEvent).where(PaymentEvent.order_code == order.order_code))).scalars().all()
            return row, ents, events

    async def access_of(self, profile):
        async with self.factory() as db:
            return await acc.load_access(db, profile)

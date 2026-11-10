"""Admin prices, feature rules, discount codes and the Haru Nói pass, against a real Postgres
(skipped without one). Every key is an obviously fake test value."""
import unittest
import uuid
from datetime import datetime, timedelta, timezone
from unittest import mock

import httpx
from fastapi import HTTPException
from sqlalchemy import delete

from app.api import deps
from app.core.security import create_access_token
from app.db import get_db
from app.main import app
from app.models import BillingSetting, ConversationSession, Coupon, FeatureRule, PresentationSession, ProductSetting
from app.services.billing import catalog, coupons, features, orders, settings_db
from tests.billing_support import BillingDbCase

API = "/api/v1"
NOW = datetime.now(timezone.utc)


class SettingsCase(BillingDbCase):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        settings_db.forget()
        self.coupon_codes: list[str] = []

        async def get_db_override():
            async with self.factory() as session:
                yield session

        app.dependency_overrides[get_db] = get_db_override
        self.addCleanup(app.dependency_overrides.pop, get_db, None)
        p = mock.patch("app.services.billing.orders.make_client", return_value=self.payos.client)
        p.start()
        self.addCleanup(p.stop)
        self.http = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")
        self.addAsyncCleanup(self.http.aclose)

    async def asyncTearDown(self):
        async with self.factory() as db:
            await db.execute(delete(ConversationSession).where(ConversationSession.learner_id.in_(self.profile_ids)))
            await db.execute(delete(PresentationSession).where(PresentationSession.learner_id.in_(self.profile_ids)))
            await db.execute(delete(ProductSetting))
            await db.execute(delete(FeatureRule))
            await db.execute(delete(BillingSetting))
            await db.commit()
        await super().asyncTearDown()
        async with self.factory() as db:  # orders that name the codes are gone now
            await db.execute(delete(Coupon).where(Coupon.code.in_(self.coupon_codes)))
            await db.commit()
        catalog.apply_settings({})
        features.apply_rules({})
        settings_db.forget()

    def auth(self, profile) -> dict:
        return {"Authorization": f"Bearer {create_access_token(str(profile.id), profile.role)}"}

    async def coupon(self, code=None, **kw) -> str:
        code = code or f"T{uuid.uuid4().hex[:8].upper()}"
        async with self.factory() as db:
            db.add(Coupon(code=code, **(kw if ("percent_off" in kw or "amount_off" in kw) else {"percent_off": 20} | kw)))
            await db.commit()
        self.coupon_codes.append(code)
        return code

    async def set_price(self, code, **fields):
        async with self.factory() as db:
            db.add(ProductSetting(product_code=code, **fields))
            await db.commit()
        settings_db.forget()


class PriceTests(SettingsCase):
    async def test_an_admin_price_is_what_an_order_costs(self):
        await self.set_price("pack_quan_he", amount=45_000, compare_at=59_000, title_vi="Quan hệ (mới)")
        learner = await self.new_profile()
        order = await self.buy(learner)
        self.assertEqual(order.amount, 45_000)
        r = await self.http.get(API + "/billing/catalog")
        p = next(x for x in r.json()["products"] if x["code"] == "pack_quan_he")
        self.assertEqual((p["amount"], p["compare_at"], p["title_vi"]), (45_000, 59_000, "Quan hệ (mới)"))

    async def test_a_product_off_sale_cannot_be_bought_but_what_was_bought_still_opens(self):
        learner = await self.new_profile()
        order = await self.buy(learner, "pack_nhap_canh")
        await self.pay(order, 29_000, "REF-OFF-1")
        await self.set_price("pack_nhap_canh", amount=29_000, active=False)
        other = await self.new_profile()
        with self.assertRaises(orders.BillingError) as cm:
            await self.buy(other, "pack_nhap_canh")
        self.assertEqual(cm.exception.code, "unknown_product")
        r = await self.http.get(API + "/billing/catalog")
        self.assertNotIn("pack_nhap_canh", [x["code"] for x in r.json()["products"]])
        self.assertTrue((await self.access_of(learner)).can_open(41))

    async def test_the_payment_description_fits_payos_shortest_limit(self):
        # payOS refuses more than 9 characters for a bank account not linked through payOS
        order = await self.buy(await self.new_profile())
        sent = self.payos.created[-1]["description"]
        self.assertLessEqual(len(sent), 9)
        self.assertEqual(sent, f"HR{order.order_code % 10**7:07d}")

    async def test_a_bad_setting_never_makes_a_product_free(self):
        catalog.apply_settings({"pack_quan_he": {"amount": 0, "compare_at": 10}})
        self.assertEqual(catalog.get("pack_quan_he").amount, 39_000)
        self.assertIsNone(catalog.get("pack_quan_he").compare_at)


class CouponTests(SettingsCase):
    async def test_a_percentage_code_lowers_the_order_and_is_counted_when_paid(self):
        code = await self.coupon(percent_off=20)
        learner = await self.new_profile()
        async with self.factory() as db:
            order = await orders.create_order(db, learner, "pack_quan_he", payos=self.payos.client, coupon_code=code.lower())
        self.assertEqual((order.list_amount, order.discount, order.amount, order.coupon_code), (39_000, 7_000, 32_000, code))
        self.assertEqual(self.payos.created[-1]["amount"], 32_000)
        await self.pay(order, 32_000, "REF-CP-1")
        async with self.factory() as db:
            self.assertEqual((await db.get(Coupon, code)).used, 1)
        # once per learner
        async with self.factory() as db:
            with self.assertRaises(orders.BillingError) as cm:
                await orders.create_order(db, learner, "exam_pass_30", payos=self.payos.client, coupon_code=code)
        self.assertEqual(cm.exception.code, "bad_coupon")

    async def test_the_quote_explains_a_bad_code_and_keeps_the_price(self):
        learner = await self.new_profile()
        only_exam = await self.coupon(amount_off=10_000, product_codes=["exam_pass_30"])
        expired = await self.coupon(ends_at=NOW - timedelta(days=1))
        async with self.factory() as db:
            _, q, err = await orders.quote(db, learner, "pack_quan_he", only_exam)
            self.assertEqual((q.total, err), (39_000, "Mã giảm giá không áp dụng cho gói này."))
            _, q, err = await orders.quote(db, learner, "exam_pass_30", only_exam)
            self.assertEqual((q.total, q.discount, err), (39_000, 10_000, None))
            _, q, err = await orders.quote(db, learner, "exam_pass_30", expired)
            self.assertIn("hết hạn", err)
            _, q, err = await orders.quote(db, learner, "exam_pass_30", "NOPE-NOPE")
            self.assertIn("không đúng", err)
        r = await self.http.post(API + "/billing/quote", headers=self.auth(learner), json={"product_code": "exam_pass_30", "coupon_code": only_exam})
        self.assertEqual(r.status_code, 200)
        self.assertEqual((r.json()["total"], r.json()["coupon_label_vi"]), (39_000, "Giảm 10.000đ"))

    async def test_a_limited_code_counts_pending_orders_of_others(self):
        code = await self.coupon(max_uses=1, once_per_learner=False)
        a, b = await self.new_profile(), await self.new_profile()
        async with self.factory() as db:
            await orders.create_order(db, a, "pack_quan_he", payos=self.payos.client, coupon_code=code)
        async with self.factory() as db:
            with self.assertRaises(orders.BillingError) as cm:
                await orders.create_order(db, b, "pack_quan_he", payos=self.payos.client, coupon_code=code)
        self.assertIn("hết lượt", cm.exception.message)

    def test_the_total_never_drops_below_the_floor_and_rounds_to_the_thousand(self):
        p = catalog.get("pack_sinh_hoat_2")
        big = Coupon(code="X", amount_off=50_000)
        self.assertEqual(coupons.price(p, big).total, coupons.MIN_TOTAL)
        odd = Coupon(code="Y", percent_off=15)  # 15% of 29.000 = 4.350 -> 4.000
        self.assertEqual((coupons.price(p, odd).discount, coupons.price(p, odd).total), (4_000, 25_000))


class FeatureTests(SettingsCase):
    async def live(self, learner, kind="talk", seconds=0, allowed=None, ended=True):
        async with self.factory() as db:
            db.add(ConversationSession(learner_id=learner.id, model="m", kind=kind, band=1, seconds=seconds,
                                       allowed_seconds=allowed, ended_at=NOW if ended else None))
            await db.commit()

    async def ensure(self, learner, feature):
        async with self.factory() as db:
            return await deps.ensure_feature(db, learner, feature)

    async def test_the_live_trial_is_one_pool_of_minutes_for_life(self):
        learner = await self.new_profile()
        self.assertEqual(await self.ensure(learner, "talk"), 20 * 60)  # the default: 20 minutes, once
        await self.live(learner, "talk", seconds=8 * 60, allowed=20 * 60)
        self.assertEqual(await self.ensure(learner, "debate"), 12 * 60)  # talk and debate share it
        await self.live(learner, "debate", seconds=0, allowed=11 * 60 + 30, ended=False)  # never finished: all of it
        with self.assertRaises(HTTPException) as cm:
            await self.ensure(learner, "talk")
        self.assertEqual(cm.exception.status_code, 402)
        self.assertEqual(cm.exception.detail["unlock_with"], ["speak_pass_30", "speak_pass_90"])
        self.assertIn("một lần cho mỗi tài khoản", cm.exception.detail["detail"])

    async def test_a_session_counts_no_more_than_it_was_allowed(self):
        learner = await self.new_profile()
        await self.live(learner, seconds=25 * 60, allowed=5 * 60)  # the client ran over: 5 minutes counted
        self.assertEqual(await self.ensure(learner, "talk"), 15 * 60)

    async def test_the_presentation_trial_counts_tries_for_life(self):
        learner = await self.new_profile()
        async with self.factory() as db:
            db.add(PresentationSession(learner_id=learner.id, band=1, topic={"question_en": "q"},
                                       attempts=[{"at": (NOW - timedelta(days=40)).isoformat()}] * 2))
            await db.commit()
        self.assertIsNone(await self.ensure(learner, "present"))  # 2 of 3 used, a month ago still counts
        async with self.factory() as db:
            db.add(PresentationSession(learner_id=learner.id, band=1, topic={"question_en": "q"}, attempts=[{"at": NOW.isoformat()}]))
            await db.commit()
        with self.assertRaises(HTTPException):
            await self.ensure(learner, "present")

    async def test_the_pass_opens_every_speaking_feature_and_a_second_one_stacks(self):
        learner = await self.new_profile()
        await self.live(learner, seconds=30 * 60, allowed=30 * 60)
        first = await self.buy(learner, "speak_pass_30")
        await self.pay(first, 79_000, "REF-SP-1")
        self.assertIsNone(await self.ensure(learner, "talk"))
        held = await self.access_of(learner)
        self.assertTrue(all(held.has_feature(f) for f in ("talk", "present", "debate")))
        second = await self.buy(learner, "speak_pass_30")
        await self.pay(second, 79_000, "REF-SP-2")
        _, ents, _ = await self.state(second)
        passes = sorted((e for e in ents if e.kind == "feature_pass"), key=lambda e: e.starts_at)
        self.assertEqual(passes[1].starts_at, passes[0].ends_at)

    async def test_admin_modes_and_trial_size(self):
        admin = await self.new_profile("admin")
        learner = await self.new_profile()
        r = await self.http.put(API + "/admin/billing/features/talk", headers=self.auth(admin), json={"mode": "paid"})
        self.assertEqual(r.status_code, 200)
        with self.assertRaises(HTTPException):
            await self.ensure(learner, "talk")
        await self.http.put(API + "/admin/billing/features/talk", headers=self.auth(admin), json={"mode": "free"})
        self.assertIsNone(await self.ensure(learner, "talk"))
        r = await self.http.put(API + "/admin/billing/trial", headers=self.auth(admin), json={"live_trial_minutes": 15, "present_trial_tries": 2})
        self.assertEqual(r.json(), {"live_trial_minutes": 15, "present_trial_tries": 2})
        self.assertEqual(await self.ensure(learner, "debate"), 15 * 60)
        bad = await self.http.put(API + "/admin/billing/trial", headers=self.auth(admin), json={"live_trial_minutes": 120, "present_trial_tries": 2})
        self.assertEqual(bad.status_code, 422)
        r = await self.http.put(API + "/admin/billing/trial", headers=self.auth(learner), json={"live_trial_minutes": 30, "present_trial_tries": 2})
        self.assertEqual(r.status_code, 403)
        cat = (await self.http.get(API + "/billing/catalog")).json()
        self.assertEqual(cat["trial"], {"live_trial_minutes": 15, "present_trial_tries": 2})
        debate_rule = next(x for x in cat["feature_rules"] if x["feature"] == "debate")
        self.assertEqual((debate_rule["trial_amount"], debate_rule["trial_unit"], debate_rule["trial_shared"]), (15, "phút", True))

    async def test_the_learner_sees_what_is_left(self):
        learner = await self.new_profile()
        await self.live(learner, seconds=5 * 60 + 20, allowed=20 * 60)
        r = await self.http.get(API + "/me/entitlements", headers=self.auth(learner))
        t = r.json()["features_trial"]
        self.assertEqual(t["talk"], {"unlimited": False, "left": 14, "total": 20, "unit": "phút"})
        self.assertEqual(t["present"], {"unlimited": False, "left": 3, "total": 3, "unit": "lượt"})

    async def test_with_billing_off_nothing_is_counted(self):
        learner = await self.new_profile()
        await self.live(learner, seconds=60 * 60, allowed=60 * 60)
        with mock.patch.object(deps.settings, "BILLING_ENABLED", False):
            self.assertIsNone(await self.ensure(learner, "talk"))


class MinutePassTests(FeatureTests):
    """Today's catalogue: Haru Nói sold by the minute (catalog.speak_30 / speak_90)."""

    LEGACY_CATALOG = False

    # the trial tests above are written for the legacy sizes; this class is about the passes
    test_the_live_trial_is_one_pool_of_minutes_for_life = None
    test_a_session_counts_no_more_than_it_was_allowed = None
    test_the_presentation_trial_counts_tries_for_life = None
    test_the_pass_opens_every_speaking_feature_and_a_second_one_stacks = None
    test_admin_modes_and_trial_size = None
    test_the_learner_sees_what_is_left = None
    test_with_billing_off_nothing_is_counted = None

    async def test_the_trial_is_five_minutes_and_one_presentation(self):
        learner = await self.new_profile()
        self.assertEqual(await self.ensure(learner, "talk"), 5 * 60)
        self.assertIsNone(await self.ensure(learner, "present"))
        cat = (await self.http.get(API + "/billing/catalog")).json()
        self.assertEqual(cat["trial"], {"live_trial_minutes": 5, "present_trial_tries": 1})

    async def test_a_pass_carries_its_minutes_and_a_second_one_adds_at_once(self):
        learner = await self.new_profile()
        await self.live(learner, seconds=5 * 60, allowed=5 * 60)  # the trial, before the pass: not counted
        first = await self.buy(learner, "speak_30")
        self.assertEqual(first.amount, 229_000)
        await self.pay(first, 229_000, "REF-MIN-1")
        self.assertEqual(await self.ensure(learner, "talk"), 100 * 60)
        await self.live(learner, "debate", seconds=40 * 60, allowed=40 * 60)
        await self.live(learner, "talk", seconds=0, allowed=10 * 60, ended=False)  # running: counts as allowed
        self.assertEqual(await self.ensure(learner, "talk"), 50 * 60)
        r = (await self.http.get(API + "/me/entitlements", headers=self.auth(learner))).json()["feature_pass"]
        self.assertEqual((r["minutes_total"], r["minutes_left"]), (100, 50))
        await self.live(learner, "talk", seconds=49 * 60 + 30, allowed=50 * 60)
        with self.assertRaises(HTTPException) as cm:  # under a minute left
            await self.ensure(learner, "talk")
        self.assertEqual(cm.exception.status_code, 402)
        self.assertEqual(cm.exception.detail["unlock_with"], ["speak_30", "speak_90"])
        self.assertIsNone(await self.ensure(learner, "present"))  # presentations are not counted in minutes
        second = await self.buy(learner, "speak_90")
        await self.pay(second, 599_000, "REF-MIN-2")
        # the days of the second pass follow the first, its minutes are there now
        self.assertEqual(await self.ensure(learner, "talk"), 300 * 60 + 30)

    async def test_the_screens_promise_no_more_than_the_trial_or_the_pass_holds(self):
        learner = await self.new_profile()
        async with self.factory() as db:
            self.assertEqual(await deps.feature_seconds_left(db, learner, "debate"), 5 * 60)
            self.assertIsNone(await deps.feature_seconds_left(db, learner, "present"))  # counted in tries
        r = (await self.http.get(API + "/me/debates/options", headers=self.auth(learner))).json()
        self.assertEqual(r["seconds_left_today"], 5 * 60)  # not the day's 20 minutes
        await self.live(learner, "talk", seconds=2 * 60, allowed=5 * 60)
        async with self.factory() as db:
            self.assertEqual(await deps.feature_seconds_left(db, learner, "debate"), 3 * 60)  # one pool
        await self.live(learner, "talk", seconds=3 * 60, allowed=3 * 60)
        async with self.factory() as db:
            self.assertEqual(await deps.feature_seconds_left(db, learner, "talk"), 0)
        await self.pay(await self.buy(learner, "speak_30"), 229_000, "REF-MIN-SHOW")
        async with self.factory() as db:
            self.assertEqual(await deps.feature_seconds_left(db, learner, "talk"), 100 * 60)

    async def test_a_bigger_pack_costs_only_the_difference(self):
        learner = await self.new_profile()
        h = self.auth(learner)
        await self.pay(await self.buy(learner, "pack_sinh_hoat_2"), 49_000, "REF-UP-1")
        q = (await self.http.post(API + "/billing/quote", headers=h, json={"product_code": "pack_9_41"})).json()
        self.assertEqual((q["credit"], q["total"]), (49_000, 199_000 - 49_000))
        q = (await self.http.post(API + "/billing/quote", headers=h, json={"product_code": "pack_viet_54"})).json()
        self.assertEqual(q["credit"], 0)  # Sinh hoạt 2 is not inside Viết câu 54
        order = await self.buy(learner, "pack_all")
        self.assertEqual(order.amount, 349_000 - 49_000)
        await self.pay(order, 300_000, "REF-UP-2")

    async def test_an_old_pass_keeps_no_minute_total(self):
        learner = await self.new_profile()
        async with self.factory() as db:
            from app.models import Entitlement

            db.add(Entitlement(profile_id=learner.id, kind="feature_pass", product_code="speak_pass_30", source="admin",
                               starts_at=NOW - timedelta(days=1), ends_at=NOW + timedelta(days=29)))
            await db.commit()
        await self.live(learner, seconds=500 * 60, allowed=500 * 60)
        self.assertIsNone(await self.ensure(learner, "talk"))
        with self.assertRaises(orders.BillingError):  # retired: no longer sold
            await self.buy(learner, "speak_pass_30")


class AdminTests(SettingsCase):
    async def test_prices_codes_and_rules_from_the_admin_screen(self):
        admin = await self.new_profile("admin")
        h = self.auth(admin)
        r = await self.http.put(API + "/admin/billing/products/speak_pass_30", headers=h,
                                json={"amount": 69_000, "compare_at": 79_000, "active": True})
        self.assertEqual(r.status_code, 200)
        row = next(p for p in r.json() if p["code"] == "speak_pass_30")
        self.assertEqual((row["amount"], row["default_amount"], row["overridden"]), (69_000, 79_000, True))
        bad = await self.http.put(API + "/admin/billing/products/speak_pass_30", headers=h, json={"amount": 69_000, "compare_at": 60_000})
        self.assertEqual(bad.status_code, 422)
        r = await self.http.delete(API + "/admin/billing/products/speak_pass_30", headers=h)
        self.assertEqual(next(p for p in r.json() if p["code"] == "speak_pass_30")["amount"], 79_000)

        code = f"ADM{uuid.uuid4().hex[:6].upper()}"
        self.coupon_codes.append(code)
        r = await self.http.post(API + "/admin/billing/coupons", headers=h, json={"code": code.lower(), "percent_off": 30, "max_uses": 10})
        self.assertEqual((r.status_code, r.json()["code"], r.json()["label_vi"]), (201, code, "Giảm 30%"))
        dup = await self.http.post(API + "/admin/billing/coupons", headers=h, json={"code": code, "amount_off": 5000})
        self.assertEqual(dup.status_code, 409)
        both = await self.http.post(API + "/admin/billing/coupons", headers=h, json={"code": "BOTH1", "percent_off": 5, "amount_off": 5000})
        self.assertEqual(both.status_code, 422)
        r = await self.http.patch(API + f"/admin/billing/coupons/{code}", headers=h, json={"active": False})
        self.assertFalse(r.json()["active"])
        r = await self.http.get(API + "/admin/billing/coupons", headers=self.auth(await self.new_profile()))
        self.assertEqual(r.status_code, 403)


if __name__ == "__main__":
    unittest.main()

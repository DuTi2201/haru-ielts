"""Orders and payments against a REAL Postgres (the locking, the UNIQUE keys and the single
transaction are what keep a payment from being counted twice, and a mock cannot show that).
Skipped when no database with the billing schema is reachable. payOS is a fake over httpx's
MockTransport; every key is an obviously fake test value."""
import asyncio
import unittest
from datetime import datetime, timedelta, timezone
from unittest import mock

from sqlalchemy import func, select

from app.core.config import settings
from app.models import BillingOrder, Entitlement, PaymentEvent
from app.services.billing import orders
from tests.billing_support import BillingDbCase


class CreateOrderTests(BillingDbCase):
    async def test_an_order_takes_its_price_from_the_catalogue_and_makes_a_payos_link(self):
        profile = await self.new_profile()
        order = await self.buy(profile, "pack_quan_he")
        self.assertEqual((order.amount, order.status, order.product_code), (39_000, "PENDING", "pack_quan_he"))
        self.assertTrue(order.checkout_url.startswith("https://pay.payos.test/"))
        self.assertEqual(order.payment_info["qr_code"], "000201-fake-qr")
        sent = self.payos.created[0]
        self.assertEqual((sent["amount"], sent["orderCode"]), (39_000, order.order_code))
        self.assertTrue(sent["returnUrl"].startswith("https://haru.test/pricing?order="))
        self.assertLess(abs(sent["expiredAt"] - (datetime.now(timezone.utc) + timedelta(minutes=15)).timestamp()), 30)

    async def test_the_same_product_asked_twice_gives_the_same_order(self):
        profile = await self.new_profile()
        a, b = await self.buy(profile), await self.buy(profile)
        self.assertEqual(a.id, b.id)
        self.assertEqual(len(self.payos.created), 1)

    async def test_no_more_than_three_orders_wait_at_once(self):
        profile = await self.new_profile()
        for product in ("pack_quan_he", "pack_nhap_canh", "pack_sinh_hoat_2"):
            await self.buy(profile, product)
        with self.assertRaises(orders.BillingError) as caught:
            await self.buy(profile, "combo_3_packs")
        self.assertEqual((caught.exception.status, caught.exception.code), (429, "too_many_pending"))

    async def test_orders_are_limited_per_hour(self):
        profile = await self.new_profile()
        with mock.patch.object(settings, "BILLING_MAX_ORDERS_PER_HOUR", 2):
            first = await self.buy(profile, "pack_quan_he")
            async with self.factory() as db:
                await orders.cancel_order(db, await db.get(BillingOrder, first.id), self.payos.client)
            second = await self.buy(profile, "pack_quan_he")
            async with self.factory() as db:
                await orders.cancel_order(db, await db.get(BillingOrder, second.id), self.payos.client)
            with self.assertRaises(orders.BillingError) as caught:
                await self.buy(profile, "pack_quan_he")
        self.assertEqual((caught.exception.status, caught.exception.code), (429, "too_many_orders"))

    async def test_an_unknown_product_is_refused(self):
        profile = await self.new_profile()
        with self.assertRaises(orders.BillingError) as caught:
            await self.buy(profile, "free_money")
        self.assertEqual(caught.exception.code, "unknown_product")

    async def test_a_pack_already_held_is_not_sold_again(self):
        profile = await self.new_profile()
        order = await self.buy(profile, "pack_nhap_canh")
        await self.pay(order, 29_000, "REF-HELD")
        with self.assertRaises(orders.BillingError) as caught:
            await self.buy(profile, "pack_nhap_canh")
        self.assertEqual(caught.exception.code, "already_owned")

    async def test_when_payos_refuses_no_order_is_left_behind(self):
        profile = await self.new_profile()
        self.payos.fail_create = True
        with self.assertRaises(orders.BillingError) as caught:
            await self.buy(profile)
        self.assertEqual(caught.exception.status, 502)
        async with self.factory() as db:
            n = (await db.execute(select(func.count()).select_from(BillingOrder).where(BillingOrder.profile_id == profile.id))).scalar_one()
        self.assertEqual(n, 0)

    async def test_nothing_is_sold_while_payos_is_not_configured(self):
        profile = await self.new_profile()
        with mock.patch.object(settings, "PAYOS_API_KEY", ""):
            with self.assertRaises(orders.BillingError) as caught:
                await self.buy(profile)
        self.assertEqual(caught.exception.code, "billing_unavailable")

    async def test_a_stale_pending_order_expires_and_a_new_one_is_made(self):
        profile = await self.new_profile()
        old = await self.buy(profile)
        async with self.factory() as db:
            row = await db.get(BillingOrder, old.id)
            row.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
            await db.commit()
        fresh = await self.buy(profile)
        self.assertNotEqual(old.id, fresh.id)
        row, _, _ = await self.state(old)
        self.assertEqual(row.status, "EXPIRED")


class PaymentTests(BillingDbCase):
    async def test_the_full_amount_pays_the_order_and_unlocks_in_one_go(self):
        profile = await self.new_profile()
        order = await self.buy(profile, "pack_quan_he")
        self.assertFalse((await self.access_of(profile)).can_open(31))
        self.assertEqual(await self.pay(order, 39_000, "REF-1"), "granted")
        row, ents, events = await self.state(order)
        self.assertEqual((row.status, row.paid_amount, row.provider_ref, row.needs_review), ("PAID", 39_000, "REF-1", False))
        self.assertIsNotNone(row.paid_at)
        self.assertEqual([(e.product_code, e.kind, e.ends_at, e.source) for e in ents], [("pack_quan_he", "lesson_pack", None, "order")])
        self.assertEqual([(e.reference, e.outcome) for e in events], [("REF-1", "granted")])
        self.assertTrue((await self.access_of(profile)).can_open(31))

    async def test_the_same_payment_twice_counts_once(self):
        profile = await self.new_profile()
        order = await self.buy(profile)
        self.assertEqual(await self.pay(order, 39_000, "REF-2"), "granted")
        self.assertEqual(await self.pay(order, 39_000, "REF-2"), "repeat")
        self.assertEqual(await self.pay(order, 39_000, "REF-2", source="reconcile"), "repeat")
        row, ents, events = await self.state(order)
        self.assertEqual((row.paid_amount, len(ents), len(events)), (39_000, 1, 1))

    async def test_two_deliveries_at_the_same_moment_still_unlock_once(self):
        profile = await self.new_profile()
        order = await self.buy(profile)
        results = await asyncio.gather(*(self.pay(order, 39_000, "REF-RACE", source=s) for s in ("webhook", "reconcile", "webhook", "reconcile")))
        self.assertEqual(sorted(results), ["granted", "repeat", "repeat", "repeat"])
        row, ents, events = await self.state(order)
        self.assertEqual((row.status, row.paid_amount, len(ents), len(events)), ("PAID", 39_000, 1, 1))

    async def test_two_different_payments_at_the_same_moment_unlock_once_and_flag_the_extra(self):
        profile = await self.new_profile()
        order = await self.buy(profile)
        results = await asyncio.gather(self.pay(order, 39_000, "REF-A"), self.pay(order, 39_000, "REF-B"))
        self.assertEqual(sorted(results), ["extra", "granted"])
        row, ents, _ = await self.state(order)
        self.assertEqual((row.status, row.paid_amount, len(ents), row.needs_review), ("PAID", 78_000, 1, True))

    async def test_a_short_payment_unlocks_nothing_until_the_rest_arrives(self):
        profile = await self.new_profile()
        order = await self.buy(profile)
        self.assertEqual(await self.pay(order, 30_000, "REF-S1"), "underpaid")
        row, ents, _ = await self.state(order)
        self.assertEqual((row.status, row.paid_amount, row.needs_review, ents), ("UNDERPAID", 30_000, True, []))
        self.assertFalse((await self.access_of(profile)).can_open(31))
        self.assertEqual(await self.pay(order, 9_000, "REF-S2"), "granted")
        row, ents, _ = await self.state(order)
        self.assertEqual((row.status, row.paid_amount, row.needs_review, len(ents)), ("PAID", 39_000, False, 1))

    async def test_too_much_money_unlocks_and_is_flagged_for_a_refund(self):
        profile = await self.new_profile()
        order = await self.buy(profile)
        self.assertEqual(await self.pay(order, 50_000, "REF-OVER"), "granted_over")
        row, ents, _ = await self.state(order)
        self.assertEqual((row.status, row.needs_review, len(ents)), ("PAID", True, 1))
        self.assertIn("11000", row.note)

    async def test_money_for_an_order_we_do_not_know_is_recorded_and_unlocks_nothing(self):
        async with self.factory() as db:
            self.assertEqual(
                await orders.apply_payment(db, order_code=123, amount=3000, reference="TF-TEST-PAYOS", source="webhook"), "unknown_order"
            )
        async with self.factory() as db:
            self.assertEqual(await orders.apply_payment(db, order_code=123, amount=3000, reference="TF-TEST-PAYOS", source="webhook"), "repeat")

    async def test_a_payment_after_the_order_expired_still_unlocks(self):
        profile = await self.new_profile()
        order = await self.buy(profile)
        async with self.factory() as db:
            row = await db.get(BillingOrder, order.id)
            row.status = "EXPIRED"
            await db.commit()
        self.assertEqual(await self.pay(order, 39_000, "REF-LATE"), "granted")
        self.assertTrue((await self.access_of(profile)).can_open(31))

    async def test_a_second_exam_pass_starts_when_the_first_ends(self):
        profile = await self.new_profile()
        first = await self.buy(profile, "exam_pass_30")
        await self.pay(first, 49_000, "REF-P1")
        second = await self.buy(profile, "exam_pass_30")
        await self.pay(second, 49_000, "REF-P2")
        async with self.factory() as db:
            rows = (await db.execute(select(Entitlement).where(Entitlement.profile_id == profile.id).order_by(Entitlement.starts_at))).scalars().all()
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[1].starts_at, rows[0].ends_at)
        self.assertEqual(rows[1].ends_at - rows[1].starts_at, timedelta(days=30))
        held = await self.access_of(profile)
        self.assertTrue(held.can_use_exam_pass())

    async def test_a_learner_cannot_cancel_after_money_arrived(self):
        profile = await self.new_profile()
        order = await self.buy(profile)
        await self.pay(order, 10_000, "REF-C1")
        async with self.factory() as db:
            row = await db.get(BillingOrder, order.id)
            with self.assertRaises(orders.BillingError):
                await orders.cancel_order(db, row, self.payos.client)

    async def test_a_pending_order_can_be_cancelled(self):
        profile = await self.new_profile()
        order = await self.buy(profile)
        async with self.factory() as db:
            row = await db.get(BillingOrder, order.id)
            row = await orders.cancel_order(db, row, self.payos.client)
        self.assertEqual(row.status, "CANCELLED")


class ReconcileTests(BillingDbCase):
    async def refresh(self, order, force=False):
        async with self.factory() as db:
            row = await db.get(BillingOrder, order.id)
            return await orders.refresh_order(db, row, self.payos.client, force=force)

    async def test_a_payment_payos_reports_unlocks_the_order(self):
        profile = await self.new_profile()
        order = await self.buy(profile)
        self.payos.links[order.order_code] = {"status": "PAID", "amount": 39_000, "paid": [("REF-R1", 39_000)]}
        row = await self.refresh(order)
        self.assertEqual(row.status, "PAID")
        self.assertTrue((await self.access_of(profile)).can_open(31))
        # asking again changes nothing (and the webhook arriving later is a repeat)
        await self.refresh(order, force=True)
        self.assertEqual(await self.pay(order, 39_000, "REF-R1"), "repeat")
        _, ents, _ = await self.state(order)
        self.assertEqual(len(ents), 1)

    async def test_payos_is_not_asked_more_than_once_every_twenty_seconds(self):
        profile = await self.new_profile()
        order = await self.buy(profile)
        await self.refresh(order)
        await self.refresh(order)
        self.assertEqual(self.payos.get_calls, 1)
        await self.refresh(order, force=True)
        self.assertEqual(self.payos.get_calls, 2)

    async def test_a_dead_link_with_no_money_marks_the_order(self):
        profile = await self.new_profile()
        order = await self.buy(profile)
        self.payos.links[order.order_code] = {"status": "CANCELLED", "paid": []}
        self.assertEqual((await self.refresh(order)).status, "CANCELLED")

    async def test_a_paid_link_that_lists_no_transaction_is_still_counted_once(self):
        profile = await self.new_profile()
        order = await self.buy(profile)
        self.payos.links[order.order_code] = {"status": "PAID", "amount": 39_000, "amount_paid": 39_000, "paid": []}
        self.assertEqual((await self.refresh(order)).status, "PAID")
        await self.refresh(order, force=True)
        _, ents, events = await self.state(order)
        self.assertEqual((len(ents), len(events)), (1, 1))

    async def test_a_pending_link_that_lists_nothing_changes_nothing(self):
        profile = await self.new_profile()
        order = await self.buy(profile)
        self.payos.links[order.order_code] = {"status": "PENDING", "paid": []}
        self.assertEqual((await self.refresh(order)).status, "PENDING")

    async def test_the_job_checks_every_open_order(self):
        learner = await self.new_profile()
        paid, waiting = await self.buy(learner, "pack_quan_he"), await self.buy(learner, "pack_nhap_canh")
        self.payos.links[paid.order_code] = {"status": "PAID", "amount": 39_000, "paid": [("REF-JOB", 39_000)]}
        result = await orders.reconcile_pending(self.factory, self.payos.client)
        self.assertGreaterEqual(result["checked"], 2)
        self.assertEqual(result["failed"], 0)
        self.assertEqual((await self.state(paid))[0].status, "PAID")
        self.assertEqual((await self.state(waiting))[0].status, "PENDING")


class AdminGrantTests(BillingDbCase):
    async def grant(self, profile, product, **kw):
        admin = await self.new_profile("admin")
        async with self.factory() as db:
            return await orders.grant_entitlement(db, profile_id=profile.id, product_code=product, granted_by=admin.id, note="test", **kw)

    async def test_an_admin_grant_opens_what_it_names(self):
        profile = await self.new_profile()
        row = await self.grant(profile, "pack_sinh_hoat_2")
        self.assertEqual((row.source, row.kind, row.ends_at), ("admin", "lesson_pack", None))
        self.assertTrue((await self.access_of(profile)).can_open(21))

    async def test_an_all_grant_opens_everything(self):
        profile = await self.new_profile()
        await self.grant(profile, "all")
        held = await self.access_of(profile)
        self.assertTrue(held.can_open(33) and held.can_use_exam_pass())

    async def test_an_unknown_product_cannot_be_granted(self):
        profile = await self.new_profile()
        with self.assertRaises(orders.BillingError):
            await self.grant(profile, "nonsense")

    async def test_a_short_order_can_be_accepted_by_hand_once(self):
        profile = await self.new_profile()
        order = await self.buy(profile)
        await self.pay(order, 30_000, "REF-HAND")
        row = await self.grant(profile, "pack_quan_he", order_id=order.id)
        self.assertEqual(row.order_id, order.id)
        stored, ents, _ = await self.state(order)
        self.assertEqual((stored.status, stored.needs_review, len(ents)), ("PAID", False, 1))
        with self.assertRaises(orders.BillingError) as caught:
            await self.grant(profile, "pack_quan_he", order_id=order.id)
        self.assertEqual(caught.exception.code, "already_granted")

    async def test_staff_open_everything_without_any_row(self):
        for role in ("admin", "editor"):
            held = await self.access_of(await self.new_profile(role))
            self.assertTrue(held.can_open(33) and held.can_use_exam_pass(), role)

    async def test_with_billing_off_a_learner_with_nothing_still_opens_everything(self):
        profile = await self.new_profile()
        with mock.patch.object(settings, "BILLING_ENABLED", False):
            held = await self.access_of(profile)
        self.assertTrue(held.can_open(33))


if __name__ == "__main__":
    unittest.main()


class ComboTests(BillingDbCase):
    """A combo: several products in one order. Paying it grants each of them, once."""

    LEGACY_CATALOG = False

    async def grant(self, profile, code, **kw):
        admin = await self.new_profile("admin")
        async with self.factory() as db:
            return await orders.grant_entitlement(db, profile_id=profile.id, product_code=code, granted_by=admin.id, note="test", **kw)

    async def test_paying_a_combo_grants_each_of_its_products_once(self):
        learner = await self.new_profile()
        order = await self.buy(learner, "combo_giao_tiep")
        self.assertEqual(order.amount, 379_000)
        self.assertEqual(await self.pay(order, 379_000, "REF-COMBO"), "granted")
        self.assertEqual(await self.pay(order, 379_000, "REF-COMBO"), "repeat")
        _, ents, _ = await self.state(order)
        self.assertEqual(sorted((e.product_code, e.kind) for e in ents), [("pack_9_41", "lesson_pack"), ("speak_30", "feature_pass")])
        self.assertTrue(all(e.order_id == order.id for e in ents))
        held = await self.access_of(learner)
        self.assertTrue(held.can_open(31) and held.has_feature("talk"))
        self.assertFalse(held.can_open(71))
        speak = next(e for e in ents if e.product_code == "speak_30")
        self.assertEqual((speak.ends_at - speak.starts_at).days, 30)

    async def test_a_pass_in_a_combo_extends_the_pass_held(self):
        learner = await self.new_profile()
        first = await self.buy(learner, "exam_pass_30")
        await self.pay(first, 99_000, "REF-PASS")
        combo = await self.buy(learner, "combo_topik2")
        await self.pay(combo, 429_000, "REF-TOPIK2")
        _, ents, _ = await self.state(combo)
        passes = sorted((e for e in ents if e.kind == "exam_pass"), key=lambda e: e.starts_at)
        self.assertEqual(len(passes), 2)
        self.assertEqual(passes[1].starts_at, passes[0].ends_at)  # the combo's pass starts when the first ends

    async def test_packs_already_paid_for_are_taken_off_a_combo_and_a_combo_pack_off_a_bigger_pack(self):
        learner = await self.new_profile()
        small = await self.buy(learner, "pack_sinh_hoat_2")
        await self.pay(small, 49_000, "REF-SMALL")
        async with self.factory() as db:
            _, q, _ = await orders.quote(db, learner, "combo_giao_tiep", None)
        self.assertEqual((q.credit, q.total), (49_000, 330_000))
        combo = await self.buy(learner, "combo_giao_tiep")
        await self.pay(combo, combo.amount, "REF-COMBO2")
        # Trọn bộ later: the Trung cấp pack counts for its share of the combo (by today's prices)
        async with self.factory() as db:
            _, q, _ = await orders.quote(db, learner, "pack_all", None)
        share = 330_000 * 199_000 // 428_000
        self.assertEqual(q.credit, (49_000 + share) - (49_000 + share) % 1000)

    async def test_an_admin_grant_of_a_combo_gives_each_product_and_can_close_its_order(self):
        learner = await self.new_profile()
        row = await self.grant(learner, "combo_tron_goi")
        self.assertEqual(row.product_code, "pack_all")
        held = await self.access_of(learner)
        self.assertTrue(held.can_open(70) and held.can_use_exam_pass() and held.has_feature("debate"))
        other = await self.new_profile()
        order = await self.buy(other, "combo_topik2")
        await self.pay(order, 100_000, "REF-SHORT")
        await self.grant(other, "combo_topik2", order_id=order.id)
        stored, ents, _ = await self.state(order)
        self.assertEqual((stored.status, sorted(e.product_code for e in ents)), ("PAID", ["exam_pass_90", "pack_42_71"]))

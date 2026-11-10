"""Paid access over HTTP, against the real routes and a real Postgres holding the 49 seeded lessons:
what a learner who has bought nothing can and cannot reach, what a purchase opens, the payOS webhook,
the order screen, "I paid but nothing unlocked", the admin's grant, the exam pass and the closed
sources. Skipped when the database or its lessons are missing. Every key is an obviously fake test value."""
import unittest
import uuid
from unittest import mock

import httpx
from sqlalchemy import select

from app.api.deps import ensure_daily_cap
from app.core.config import settings
from app.core.security import create_access_token
from app.db import get_db
from app.main import app
from app.models import BillingClaim, BillingOrder, Entitlement, Job, Lesson, PaymentEvent
from app.services.billing import payos_client as px
from tests.billing_support import DB_READY, KEY, BillingDbCase

API = "/api/v1"




class ApiCase(BillingDbCase):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        async with self.factory() as db:
            self.by_sort = dict((await db.execute(select(Lesson.sort_order, Lesson.id))).all())
        if len(self.by_sort) < 49:
            self.skipTest("the seeded lessons are not in this database")

        async def get_db_override():
            async with self.factory() as session:
                yield session

        app.dependency_overrides[get_db] = get_db_override
        self.addCleanup(app.dependency_overrides.pop, get_db, None)
        patch = mock.patch("app.services.billing.orders.make_client", return_value=self.payos.client)
        patch.start()
        self.addCleanup(patch.stop)
        self.http = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")
        self.addAsyncCleanup(self.http.aclose)

    def auth(self, profile) -> dict:
        return {"Authorization": f"Bearer {create_access_token(str(profile.id), profile.role)}"}

    async def get(self, path, profile=None, **kw):
        return await self.http.get(API + path, headers=self.auth(profile) if profile else None, **kw)

    async def post(self, path, profile=None, json=None):
        return await self.http.post(API + path, headers=self.auth(profile) if profile else None, json=json)

    def lesson(self, sort_order: int) -> int:
        return self.by_sort[sort_order]

    def webhook_body(self, order, amount, reference, key=KEY, **over):
        data = {
            "orderCode": order.order_code, "amount": amount, "description": "HARU", "accountNumber": "111",
            "reference": reference, "transactionDateTime": "2026-10-14 10:01:00", "currency": "VND",
            "paymentLinkId": f"pl-{order.order_code}", "code": "00", "desc": "Thành công",
            "counterAccountBankId": None, "counterAccountBankName": None, "counterAccountName": "NGUYEN VAN A",
            "counterAccountNumber": None, "virtualAccountName": None, "virtualAccountNumber": None, **over,
        }
        return {"code": "00", "desc": "success", "success": True, "data": data, "signature": px.signature_of(data, key)}


@unittest.skipUnless(DB_READY, "no Postgres with the billing schema")
class LockedLessonTests(ApiCase):
    async def test_the_list_marks_each_lesson_free_or_locked(self):
        rows = {r["sort_order"]: r for r in (await self.get("/lessons")).json()}
        self.assertTrue(all(rows[n]["access"] == "free" and rows[n]["unlock_with"] == [] for n in range(1, 20)))
        self.assertTrue(all(rows[n]["access"] == "locked" for n in range(20, max(rows) + 1)))
        self.assertEqual(rows[56]["unlock_with"], ["pack_viet_54"])
        self.assertEqual(rows[21]["unlock_with"], ["pack_sinh_hoat_2", "combo_3_packs"])
        self.assertEqual(rows[41]["unlock_with"], ["pack_nhap_canh", "combo_3_packs"])
        self.assertEqual(rows[47]["unlock_with"], ["pack_cong_so"])
        self.assertIn("title", rows[21])  # the card still has something to show

    async def test_the_list_shows_what_a_learner_owns(self):
        profile = await self.new_profile()
        await self.pay(await self.buy(profile, "pack_quan_he"), 39_000, "REF-LIST")
        rows = {r["sort_order"]: r["access"] for r in (await self.get("/lessons", profile)).json()}
        self.assertEqual(rows[3], "free")
        self.assertTrue(all(rows[n] == "owned" for n in range(28, 40)))
        self.assertTrue(all(rows[n] == "locked" for n in (20, 27, 40, 45)))

    async def test_a_locked_lesson_is_only_a_preview(self):
        out = await self.get(f"/lessons/{self.lesson(21)}")
        self.assertEqual(out.status_code, 200)
        body = out.json()
        self.assertEqual(body["access"], "locked")
        self.assertEqual((body["content"], body["grammar"], body["coach"]), ("", [], None))
        self.assertLessEqual(len(body["vocab"]), 3)
        self.assertGreater(body["totals"]["vocab"], 3)
        self.assertGreater(body["totals"]["grammar"], 0)
        self.assertLessEqual(len(body["notes"]), 1)
        self.assertTrue(all(n["kind"] == "goal" for n in body["notes"]))
        self.assertTrue(all(v["usage_note_vi"] is None and v["collocations"] is None for v in body["vocab"]))
        self.assertEqual(body["unlock_with"], ["pack_sinh_hoat_2", "combo_3_packs"])
        self.assertIn("no-store", out.headers["cache-control"])

    async def test_a_free_lesson_is_whole_for_everyone(self):
        body = (await self.get(f"/lessons/{self.lesson(7)}")).json()
        self.assertEqual(body["access"], "free")
        self.assertGreater(len(body["grammar"]), 0)
        self.assertIsNone(body.get("totals"))

    async def test_an_owned_lesson_is_whole(self):
        profile = await self.new_profile()
        await self.pay(await self.buy(profile, "pack_sinh_hoat_2"), 29_000, "REF-OWN")
        body = (await self.get(f"/lessons/{self.lesson(21)}", profile)).json()
        self.assertEqual(body["access"], "owned")
        self.assertGreater(len(body["grammar"]), 0)
        self.assertNotEqual(body["content"], "")

    async def test_the_practice_set_of_a_paid_lesson_needs_a_login_and_the_pack(self):
        path = f"/lessons/{self.lesson(23)}/practice"
        self.assertEqual((await self.get(path)).status_code, 401)
        learner = await self.new_profile()
        denied = await self.get(path, learner)
        self.assertEqual(denied.status_code, 402)
        detail = denied.json()
        self.assertEqual((detail["code"], detail["needs"]), ("payment_required", "lesson_pack"))
        self.assertEqual(detail["unlock_with"], ["pack_sinh_hoat_2", "combo_3_packs"])
        self.assertNotIn("items", denied.text)  # not a single answer in the refusal
        await self.pay(await self.buy(learner, "combo_3_packs"), 79_000, "REF-COMBO")
        ok = await self.get(path, learner)
        self.assertEqual(ok.status_code, 200)
        self.assertGreater(len(ok.json()["items"]), 0)
        self.assertIn("no-store", ok.headers["cache-control"])

    async def test_a_pack_does_not_open_another_packs_practice(self):
        learner = await self.new_profile()
        await self.pay(await self.buy(learner, "pack_nhap_canh"), 29_000, "REF-OTHER")
        self.assertEqual((await self.get(f"/lessons/{self.lesson(31)}/practice", learner)).status_code, 402)
        self.assertEqual((await self.get(f"/lessons/{self.lesson(41)}/practice", learner)).status_code, 200)

    async def test_the_practice_set_of_a_free_lesson_stays_public(self):
        out = await self.get(f"/lessons/{self.lesson(3)}/practice")
        self.assertEqual(out.status_code, 200)
        self.assertIn("public", out.headers["cache-control"])

    async def test_answering_a_locked_lesson_is_refused(self):
        learner = await self.new_profile()
        out = await self.post(f"/lessons/{self.lesson(21)}/answers", learner, {"exercise_id": "L1", "question_id": "Q1", "correct": True})
        self.assertEqual(out.status_code, 402)
        self.assertEqual((await self.get(f"/lessons/{self.lesson(21)}/progress", learner)).status_code, 402)

    async def test_the_review_queue_draws_new_cards_only_from_lessons_the_learner_may_open(self):
        learner = await self.new_profile()
        body = (await self.get("/me/review-queue?new=30&limit=60", learner)).json()
        titles = {i["lesson_title"] for i in body["items"] if i["lesson_title"]}
        async with self.factory() as db:
            free_titles = set((await db.execute(select(Lesson.title).where(Lesson.sort_order <= 19))).scalars().all())
        self.assertTrue(body["items"])
        self.assertTrue(titles <= free_titles, titles - free_titles)

    async def test_a_card_of_a_locked_lesson_cannot_be_reviewed(self):
        learner = await self.new_profile()
        async with self.factory() as db:
            from app.models import VocabItem

            locked = (await db.execute(select(VocabItem.id).where(VocabItem.lesson_id == self.lesson(23)).limit(1))).scalar_one()
            free = (await db.execute(select(VocabItem.id).where(VocabItem.lesson_id == self.lesson(3)).limit(1))).scalar_one()
        refused = await self.post("/progress/reviews", learner, {"item_type": "vocab_item", "item_id": locked, "correct": True})
        self.assertEqual(refused.status_code, 402)
        allowed = await self.post("/progress/reviews", learner, {"item_type": "vocab_item", "item_id": free, "correct": True})
        self.assertEqual(allowed.status_code, 200)

    async def test_staff_open_everything(self):
        admin = await self.new_profile("admin")
        self.assertEqual((await self.get(f"/lessons/{self.lesson(41)}/practice", admin)).status_code, 200)
        self.assertEqual((await self.get(f"/lessons/{self.lesson(41)}", admin)).json()["access"], "owned")

    async def test_with_billing_off_nothing_is_locked(self):
        with mock.patch.object(settings, "BILLING_ENABLED", False):
            self.assertEqual((await self.get(f"/lessons/{self.lesson(41)}/practice")).status_code, 200)
            rows = (await self.get("/lessons")).json()
            self.assertTrue(all(r["access"] == "free" for r in rows))
            self.assertEqual((await self.get(f"/lessons/{self.lesson(41)}")).json()["access"], "free")


@unittest.skipUnless(DB_READY, "no Postgres with the billing schema")
class ClosedSourceAndPassTests(ApiCase):
    def setUp(self):
        super().setUp()
        # closing is a switch (off by default: the app is used inside a small group)
        patcher = mock.patch.object(settings, "BILLING_PRIVATE_SOURCES", True)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_open_by_default(self):
        from app.core.config import Settings

        self.assertFalse(Settings.model_fields["BILLING_PRIVATE_SOURCES"].default)

    async def test_the_corpus_the_editorials_and_the_real_papers_close_for_learners(self):
        learner = await self.new_profile()
        for path in ("/corpus/facets", "/corpus/browse", "/editorials", "/me/real-exam"):
            anonymous = await self.get(path)
            self.assertEqual(anonymous.status_code, 401, path)
            refused = await self.get(path, learner)
            self.assertEqual(refused.status_code, 403, path)
            self.assertEqual(refused.json()["code"], "closed_source", path)

    async def test_editors_still_reach_them(self):
        editor = await self.new_profile("editor")
        for path in ("/corpus/facets", "/editorials", "/me/real-exam"):
            self.assertNotIn((await self.get(path, editor)).status_code, (401, 402, 403), path)

    async def test_switching_the_closing_off_opens_them_again(self):
        learner = await self.new_profile()
        with mock.patch.object(settings, "BILLING_PRIVATE_SOURCES", False):
            self.assertNotIn((await self.get("/corpus/facets", learner)).status_code, (401, 403))
            self.assertNotIn((await self.get("/editorials")).status_code, (401, 403))

    async def test_with_billing_off_they_are_open_as_before(self):
        with mock.patch.object(settings, "BILLING_ENABLED", False):
            self.assertNotIn((await self.get("/corpus/facets")).status_code, (401, 403))
            self.assertNotIn((await self.get("/editorials")).status_code, (401, 403))

    async def test_the_marked_practice_needs_the_exam_pass(self):
        learner = await self.new_profile()
        for method, path in (("get", "/me/exam-drill"), ("post", "/me/writing-drills")):
            out = await (self.get(path, learner) if method == "get" else self.post(path, learner))
            self.assertEqual(out.status_code, 402, path)
            detail = out.json()
            self.assertEqual((detail["code"], detail["needs"]), ("payment_required", "exam_pass"))
            self.assertEqual(detail["unlock_with"], ["exam_pass_30", "exam_pass_90"])

    async def test_a_pass_lets_the_learner_in(self):
        learner = await self.new_profile()
        await self.pay(await self.buy(learner, "exam_pass_30"), 49_000, "REF-PASS")
        self.assertNotEqual((await self.get("/me/exam-drill", learner)).status_code, 402)
        me = (await self.get("/me/entitlements", learner)).json()
        self.assertTrue(me["exam_pass"]["active"])
        self.assertIsNotNone(me["exam_pass"]["ends_at"])

    async def test_with_billing_off_the_marked_practice_is_open(self):
        learner = await self.new_profile()
        with mock.patch.object(settings, "BILLING_ENABLED", False):
            self.assertNotEqual((await self.get("/me/exam-drill", learner)).status_code, 402)


@unittest.skipUnless(DB_READY, "no Postgres with the billing schema")
class DailyCapTests(ApiCase):
    async def add_jobs(self, profile, job_type, n):
        async with self.factory() as db:
            for _ in range(n):
                db.add(Job(type=job_type, owner_id=profile.id, status="succeeded"))
            await db.commit()

    async def tearDownJobs(self):
        async with self.factory() as db:
            from sqlalchemy import delete

            await db.execute(delete(Job).where(Job.owner_id.in_(self.profile_ids)))
            await db.commit()

    async def asyncTearDown(self):
        await self.tearDownJobs()
        await super().asyncTearDown()

    async def test_the_cap_stops_the_next_marking_but_not_the_ones_before_it(self):
        profile = await self.new_profile()
        await self.add_jobs(profile, "grade_writing_submission", 2)
        async with self.factory() as db:
            await ensure_daily_cap(db, profile.id, "grade_writing_submission", 3, "bài viết")  # 2 of 3 used: fine
        await self.add_jobs(profile, "grade_writing_submission", 1)
        async with self.factory() as db:
            with self.assertRaises(Exception) as caught:
                await ensure_daily_cap(db, profile.id, "grade_writing_submission", 3, "bài viết")
        self.assertEqual(caught.exception.status_code, 429)
        self.assertEqual(caught.exception.detail["code"], "daily_limit")

    async def test_another_learner_and_another_kind_are_not_counted(self):
        a, b = await self.new_profile(), await self.new_profile()
        await self.add_jobs(a, "grade_writing_submission", 5)
        await self.add_jobs(b, "grade_editorial_outline", 5)
        async with self.factory() as db:
            await ensure_daily_cap(db, b.id, "grade_writing_submission", 3, "bài viết")
            await ensure_daily_cap(db, a.id, "grade_editorial_outline", 3, "dàn ý")

    async def test_a_cap_of_zero_switches_it_off(self):
        profile = await self.new_profile()
        await self.add_jobs(profile, "grade_writing_submission", 5)
        async with self.factory() as db:
            await ensure_daily_cap(db, profile.id, "grade_writing_submission", 0, "bài viết")

    async def test_the_default_caps_are_set(self):
        self.assertEqual((settings.WRITING_GRADES_PER_DAY, settings.EDITORIAL_OUTLINES_PER_DAY), (10, 10))


@unittest.skipUnless(DB_READY, "no Postgres with the billing schema")
class OrderApiTests(ApiCase):
    async def test_the_catalogue_is_public(self):
        body = (await self.get("/billing/catalog")).json()
        self.assertEqual((body["enabled"], body["purchasable"], body["free_lesson_max"]), (True, True, 19))
        self.assertEqual([p["code"] for p in body["products"]],
                         ["pack_sinh_hoat_2", "pack_quan_he", "pack_nhap_canh", "pack_cong_so", "pack_viet_54", "pack_xa_hoi", "combo_3_packs", "exam_pass_30", "exam_pass_90", "speak_pass_30", "speak_pass_90"])
        self.assertEqual(next(p for p in body["products"] if p["code"] == "pack_quan_he")["amount"], 39_000)

    async def test_the_catalogue_says_when_nothing_is_sold_yet(self):
        with mock.patch.object(settings, "BILLING_ENABLED", False):
            body = (await self.get("/billing/catalog")).json()
        self.assertEqual((body["enabled"], body["purchasable"]), (False, False))

    async def test_buying_needs_a_login_and_the_price_cannot_be_named_by_the_client(self):
        self.assertEqual((await self.post("/billing/orders", json={"product_code": "pack_quan_he"})).status_code, 401)
        learner = await self.new_profile()
        out = await self.post("/billing/orders", learner, {"product_code": "pack_quan_he", "amount": 1})
        self.assertEqual(out.status_code, 201)
        body = out.json()
        self.assertEqual((body["amount"], body["status"], body["unlocked"]), (39_000, "PENDING", False))
        self.assertEqual(body["transfer"]["qr_code"], "000201-fake-qr")
        self.assertTrue(body["checkout_url"])
        self.assertNotIn("payment_link_id", body)

    async def test_the_order_screen_is_private_to_its_owner(self):
        owner, other = await self.new_profile(), await self.new_profile()
        order = (await self.post("/billing/orders", owner, {"product_code": "pack_nhap_canh"})).json()
        self.assertEqual((await self.get(f"/billing/orders/{order['id']}", owner)).status_code, 200)
        self.assertEqual((await self.get(f"/billing/orders/{order['id']}", other)).status_code, 404)
        self.assertEqual((await self.get(f"/billing/orders/{order['id']}")).status_code, 401)
        self.assertEqual((await self.post(f"/billing/orders/{order['id']}/cancel", other)).status_code, 404)
        self.assertEqual([o["id"] for o in (await self.get("/billing/orders", other)).json()], [])
        self.assertEqual([o["id"] for o in (await self.get("/billing/orders", owner)).json()], [order["id"]])

    async def test_an_unknown_product_and_a_repeat_purchase_are_refused(self):
        learner = await self.new_profile()
        self.assertEqual((await self.post("/billing/orders", learner, {"product_code": "free_money"})).status_code, 404)
        await self.pay(await self.buy(learner, "pack_nhap_canh"), 29_000, "REF-DUP-BUY")
        again = await self.post("/billing/orders", learner, {"product_code": "pack_nhap_canh"})
        self.assertEqual((again.status_code, again.json()["code"]), (409, "already_owned"))

    async def test_polling_unlocks_when_payos_reports_the_payment(self):
        learner = await self.new_profile()
        order = (await self.post("/billing/orders", learner, {"product_code": "pack_quan_he"})).json()
        code = order["order_code"]
        self.assertEqual((await self.get(f"/billing/orders/{order['id']}", learner)).json()["status"], "PENDING")
        self.payos.links[code] = {"status": "PAID", "amount": 39_000, "paid": [("REF-POLL", 39_000)]}
        async with self.factory() as db:  # the screen polls every few seconds; let the 20 s throttle pass
            from sqlalchemy import update

            await db.execute(update(BillingOrder).where(BillingOrder.order_code == code).values(last_checked_at=None))
            await db.commit()
        done = (await self.get(f"/billing/orders/{order['id']}", learner)).json()
        self.assertEqual((done["status"], done["unlocked"], done["transfer"]), ("PAID", True, None))
        self.assertEqual((await self.get(f"/lessons/{self.lesson(31)}/practice", learner)).status_code, 200)

    async def test_cancelling_a_waiting_order(self):
        learner = await self.new_profile()
        order = (await self.post("/billing/orders", learner, {"product_code": "pack_quan_he"})).json()
        out = await self.post(f"/billing/orders/{order['id']}/cancel", learner)
        self.assertEqual((out.status_code, out.json()["status"]), (200, "CANCELLED"))


@unittest.skipUnless(DB_READY, "no Postgres with the billing schema")
class WebhookApiTests(ApiCase):
    async def post_webhook(self, body):
        return await self.http.post(API + "/billing/payos/webhook", json=body)

    async def test_a_signed_payment_unlocks_the_order_once(self):
        learner = await self.new_profile()
        order = await self.buy(learner, "pack_quan_he")
        body = self.webhook_body(order, 39_000, "REF-HOOK")
        first = await self.post_webhook(body)
        self.assertEqual((first.status_code, first.json()), (200, {"ok": True, "outcome": "granted"}))
        again = await self.post_webhook(body)
        self.assertEqual((again.status_code, again.json()["outcome"]), (200, "repeat"))
        row, ents, events = await self.state(order)
        self.assertEqual((row.status, len(ents), len(events)), ("PAID", 1, 1))
        self.assertEqual((await self.get(f"/lessons/{self.lesson(31)}/practice", learner)).status_code, 200)
        # only the money facts are kept of the body: not the payer's name
        self.assertNotIn("counterAccountName", events[0].raw)
        self.assertNotIn("NGUYEN", str(events[0].raw))
        self.assertEqual(events[0].raw["reference"], "REF-HOOK")

    async def test_an_unsigned_or_altered_body_does_nothing(self):
        learner = await self.new_profile()
        order = await self.buy(learner, "pack_quan_he")
        forged = self.webhook_body(order, 39_000, "REF-FORGED", key="a-key-the-attacker-guessed")
        self.assertEqual((await self.post_webhook(forged)).status_code, 400)
        altered = self.webhook_body(order, 1_000, "REF-ALTERED")
        altered["data"]["amount"] = 39_000
        self.assertEqual((await self.post_webhook(altered)).status_code, 400)
        self.assertEqual((await self.http.post(API + "/billing/payos/webhook", content=b"not json")).status_code, 400)
        self.assertEqual((await self.post_webhook({"data": {"orderCode": order.order_code}})).status_code, 400)
        row, ents, events = await self.state(order)
        self.assertEqual((row.status, row.paid_amount, ents, events), ("PENDING", 0, [], []))

    async def test_a_short_payment_by_webhook_waits_for_an_admin(self):
        learner = await self.new_profile()
        order = await self.buy(learner, "pack_quan_he")
        out = await self.post_webhook(self.webhook_body(order, 20_000, "REF-HOOK-SHORT"))
        self.assertEqual(out.json()["outcome"], "underpaid")
        shown = (await self.get(f"/billing/orders/{order.id}", learner)).json()
        self.assertEqual((shown["status"], shown["unlocked"]), ("UNDERPAID", False))
        self.assertIn("19.000", shown["message_vi"])

    async def test_payos_own_test_call_for_an_unknown_order_gets_a_200(self):
        test_order = type("O", (), {"order_code": 123})()
        out = await self.post_webhook(self.webhook_body(test_order, 3_000, "TF-PAYOS-TEST"))
        self.assertEqual((out.status_code, out.json()["outcome"]), (200, "unknown_order"))

    async def test_a_failed_transaction_is_ignored(self):
        learner = await self.new_profile()
        order = await self.buy(learner, "pack_quan_he")
        out = await self.post_webhook(self.webhook_body(order, 39_000, "REF-FAILED", code="01"))
        self.assertEqual(out.json()["outcome"], "ignored")
        self.assertEqual((await self.state(order))[0].status, "PENDING")

    async def test_without_payos_configured_the_webhook_is_unavailable(self):
        with mock.patch.object(settings, "PAYOS_CHECKSUM_KEY", ""):
            self.assertEqual((await self.post_webhook({"data": {}, "signature": "x"})).status_code, 503)


@unittest.skipUnless(DB_READY, "no Postgres with the billing schema")
class ClaimAndAdminApiTests(ApiCase):
    async def test_a_claim_first_asks_payos_and_unlocks_when_the_money_is_found(self):
        learner = await self.new_profile()
        order = await self.buy(learner, "pack_quan_he")
        self.payos.links[order.order_code] = {"status": "PAID", "amount": 39_000, "paid": [("REF-CLAIM-FOUND", 39_000)]}
        out = await self.post("/billing/claims", learner, {"order_id": str(order.id), "note": "đã chuyển khoản"})
        body = out.json()
        self.assertEqual((out.status_code, body["unlocked"], body["claim"], body["order"]["status"]), (201, True, None, "PAID"))
        async with self.factory() as db:
            self.assertEqual((await db.execute(select(BillingClaim).where(BillingClaim.profile_id == learner.id))).scalars().all(), [])

    async def test_a_claim_is_opened_when_the_money_is_not_found(self):
        learner = await self.new_profile()
        order = await self.buy(learner, "pack_quan_he")
        out = await self.post("/billing/claims", learner, {"order_id": str(order.id), "note": "sửa nội dung CK", "bank_ref": "FT123"})
        body = out.json()
        self.assertEqual((body["unlocked"], body["claim"]["status"], body["claim"]["bank_ref"]), (False, "open", "FT123"))
        mine = (await self.get("/billing/claims", learner)).json()
        self.assertEqual(len(mine), 1)

    async def test_nobody_can_claim_on_another_learners_order(self):
        owner, other = await self.new_profile(), await self.new_profile()
        order = await self.buy(owner, "pack_quan_he")
        out = await self.post("/billing/claims", other, {"order_id": str(order.id), "note": "x"})
        self.assertEqual(out.status_code, 404)

    async def test_the_admin_sees_the_queue_and_grants_by_email(self):
        admin, learner = await self.new_profile("admin"), await self.new_profile()
        order = await self.buy(learner, "pack_quan_he")
        await self.pay(order, 30_000, "REF-ADMIN-SHORT")
        await self.post("/billing/claims", learner, {"order_id": str(order.id), "note": "thiếu 9k"})

        orders_view = (await self.get("/admin/billing/orders?needs_review=true", admin)).json()
        mine = next(o for o in orders_view if o["id"] == str(order.id))
        self.assertEqual((mine["status"], mine["email"], mine["paid_amount"]), ("UNDERPAID", learner.email, 30_000))
        claims = (await self.get("/admin/billing/claims", admin)).json()
        claim = next(c for c in claims if c["profile_id"] == str(learner.id))

        grant = await self.post("/admin/billing/grants", admin, {"email": learner.email, "product_code": "pack_quan_he", "order_id": str(order.id), "note": "nhận thiếu 9k"})
        self.assertEqual((grant.status_code, grant.json()["source"]), (201, "admin"))
        self.assertEqual((await self.get(f"/lessons/{self.lesson(31)}/practice", learner)).status_code, 200)
        resolved = await self.post(f"/admin/billing/claims/{claim['id']}/resolve", admin, {"status": "resolved", "resolution": "đã cấp"})
        self.assertEqual(resolved.json()["status"], "resolved")

        rows = (await self.get(f"/admin/billing/entitlements?email={learner.email}", admin)).json()
        self.assertEqual(len(rows), 1)
        revoked = await self.post(f"/admin/billing/entitlements/{rows[0]['id']}/revoke", admin)
        self.assertIsNotNone(revoked.json()["revoked_at"])
        self.assertEqual((await self.get(f"/lessons/{self.lesson(31)}/practice", learner)).status_code, 402)

    async def test_only_an_admin_may_use_the_admin_tools(self):
        learner, editor = await self.new_profile(), await self.new_profile("editor")
        for who in (learner, editor):
            self.assertEqual((await self.get("/admin/billing/orders", who)).status_code, 403)
            self.assertEqual((await self.post("/admin/billing/grants", who, {"email": learner.email, "product_code": "all"})).status_code, 403)
        self.assertEqual((await self.get("/admin/billing/orders")).status_code, 401)

    async def test_a_grant_names_a_learner_that_exists(self):
        admin = await self.new_profile("admin")
        out = await self.post("/admin/billing/grants", admin, {"email": "nobody-here@example.invalid", "product_code": "all"})
        self.assertEqual(out.status_code, 404)
        out = await self.post("/admin/billing/grants", admin, {"product_code": "all"})
        self.assertEqual(out.status_code, 422)


if __name__ == "__main__":
    unittest.main()

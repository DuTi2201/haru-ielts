"""The admin page's data over HTTP, against the real routes and a real Postgres: who may use it, the
learner list (search, role, paying, paging), one learner in full, the role of an account, the summary,
and the two order tools (its payments; "I looked at it"). Skipped without the database. Every key and
e-mail is an obviously fake test value."""
import unittest
import uuid

from sqlalchemy import select

from app.models import LessonExerciseResult, Profile
from app.services.billing import catalog
from tests.billing_support import DB_READY
from tests.test_billing_api import ApiCase


@unittest.skipUnless(DB_READY, "no Postgres with the billing schema")
class AccessTests(ApiCase):
    async def test_only_an_admin_may_open_any_of_it(self):
        learner, editor, admin = await self.new_profile(), await self.new_profile("editor"), await self.new_profile("admin")
        paths = ["/admin/overview", "/admin/learners", f"/admin/learners/{learner.id}"]
        for who in (learner, editor):
            for path in paths:
                self.assertEqual((await self.get(path, who)).status_code, 403, path)
            self.assertEqual((await self.post(f"/admin/learners/{learner.id}/role", who, {"role": "admin"})).status_code, 403)
        for path in paths:
            self.assertEqual((await self.get(path)).status_code, 401, path)
            self.assertEqual((await self.get(path, admin)).status_code, 200, path)
        # asking to become admin did nothing
        async with self.factory() as db:
            self.assertEqual((await db.get(Profile, learner.id)).role, "learner")


@unittest.skipUnless(DB_READY, "no Postgres with the billing schema")
class LearnerListTests(ApiCase):
    def token(self, profile) -> str:
        return profile.email.split("billing-test-")[1].split("@")[0]

    async def test_search_by_email_or_name_finds_the_account_and_shows_what_it_holds(self):
        admin, learner, other = await self.new_profile("admin"), await self.new_profile(), await self.new_profile()
        async with self.factory() as db:
            (await db.get(Profile, learner.id)).display_name = "Bạn Học Viên 100%"
            await db.commit()
        rows = (await self.get(f"/admin/learners?q={self.token(learner)}", admin)).json()
        self.assertEqual((rows["total"], [r["id"] for r in rows["items"]]), (1, [str(learner.id)]))
        row = rows["items"][0]
        self.assertEqual((row["role"], row["paid_orders"], row["paid_total"], row["open_claims"], row["exercises_answered"]), ("learner", 0, 0, 0, 0))
        self.assertEqual(row["access"], {"staff": False, "everything": False, "lesson_packs": [], "exam_pass": False, "exam_pass_until": None})
        self.assertIsNone(row["last_active_at"])

        # the name, and a "%" in it that means itself and not "anything"
        by_name = (await self.get("/admin/learners?q=Học Viên 100%25", admin)).json()
        self.assertEqual([r["id"] for r in by_name["items"]], [str(learner.id)])
        self.assertEqual((await self.get("/admin/learners?q=Viên 1%250", admin)).json()["total"], 0)
        self.assertNotIn(str(other.id), [r["id"] for r in by_name["items"]])

    async def test_money_rights_and_activity_show_on_the_row(self):
        admin, learner = await self.new_profile("admin"), await self.new_profile()
        order = await self.buy(learner, "pack_quan_he")
        await self.pay(order, 39_000, "REF-ADMIN-LIST-FULL")
        await self.post("/billing/claims", learner, {"note": "hỏi thử"})
        async with self.factory() as db:
            for n, ok in enumerate((True, False, True)):
                db.add(LessonExerciseResult(learner_id=learner.id, lesson_id=self.lesson(10), exercise_id="e1", question_id=f"q{n}", correct=ok))
            await db.commit()

        row = (await self.get(f"/admin/learners?q={self.token(learner)}", admin)).json()["items"][0]
        self.assertEqual((row["paid_orders"], row["paid_total"], row["open_claims"], row["exercises_answered"]), (1, 39_000, 1, 3))
        self.assertEqual(row["access"]["lesson_packs"], ["pack_quan_he"])
        self.assertFalse(row["access"]["everything"])
        self.assertIsNotNone(row["last_active_at"])

    async def test_filters_by_role_and_by_whether_the_account_paid(self):
        admin, payer, free, editor = (await self.new_profile("admin"), await self.new_profile(), await self.new_profile(), await self.new_profile("editor"))
        await self.pay(await self.buy(payer, "pack_quan_he"), 39_000, "REF-ADMIN-FILTER")
        mine = {str(p.id) for p in (admin, payer, free, editor)}

        def ids(data):
            return {r["id"] for r in data["items"]} & mine

        everyone = (await self.get("/admin/learners?limit=100", admin)).json()
        self.assertTrue(mine <= {r["id"] for r in everyone["items"]} or everyone["total"] > 100)
        editors = (await self.get("/admin/learners?role=editor&limit=100", admin)).json()
        self.assertEqual(ids(editors), {str(editor.id)})
        self.assertTrue(all(r["role"] == "editor" for r in editors["items"]))
        paying = (await self.get("/admin/learners?paying=true&limit=100", admin)).json()
        self.assertEqual(ids(paying), {str(payer.id)})
        not_paying = (await self.get("/admin/learners?paying=false&limit=100", admin)).json()
        self.assertEqual(ids(not_paying), {str(admin.id), str(free.id), str(editor.id)})
        self.assertEqual((await self.get("/admin/learners?role=owner", admin)).status_code, 422)

    async def test_a_page_is_newest_first_and_total_counts_all_matches(self):
        admin = await self.new_profile("admin")
        made = [await self.new_profile() for _ in range(3)]
        first = (await self.get("/admin/learners?role=learner&limit=2", admin)).json()
        second = (await self.get("/admin/learners?role=learner&limit=2&offset=2", admin)).json()
        self.assertEqual((len(first["items"]), first["total"] >= 3), (2, True))
        self.assertEqual(first["total"], second["total"])
        newest_first = [r["created_at"] for r in first["items"] + second["items"]]
        self.assertEqual(newest_first, sorted(newest_first, reverse=True))
        self.assertTrue({str(made[-1].id)} & {r["id"] for r in first["items"]} or first["total"] > 3)
        self.assertEqual((await self.get("/admin/learners?limit=0", admin)).status_code, 422)
        self.assertEqual((await self.get("/admin/learners?limit=101", admin)).status_code, 422)

    async def test_staff_and_an_all_grant_open_everything(self):
        admin, editor, gifted = await self.new_profile("admin"), await self.new_profile("editor"), await self.new_profile()
        await self.post("/admin/billing/grants", admin, {"email": gifted.email, "product_code": "all", "note": "tặng"})
        for who, staff in ((admin, True), (editor, True), (gifted, False)):
            row = (await self.get(f"/admin/learners?q={self.token(who)}", admin)).json()["items"][0]
            self.assertEqual((row["access"]["everything"], row["access"]["staff"]), (True, staff), row["role"])


@unittest.skipUnless(DB_READY, "no Postgres with the billing schema")
class LearnerDetailTests(ApiCase):
    async def test_one_learner_in_full(self):
        admin, learner = await self.new_profile("admin"), await self.new_profile()
        order = await self.buy(learner, "pack_quan_he")
        await self.pay(order, 39_000, "REF-ADMIN-DETAIL")
        pending = await self.buy(learner, "exam_pass_30")
        await self.post("/billing/claims", learner, {"order_id": str(pending.id), "note": "chưa mở"})
        g = (await self.post("/admin/billing/grants", admin, {"email": learner.email, "product_code": "exam_pass_30", "days": 7, "note": "dùng thử"})).json()
        await self.post(f"/admin/billing/entitlements/{g['id']}/revoke", admin)
        async with self.factory() as db:
            for n, ok in enumerate((True, True, False)):
                db.add(LessonExerciseResult(learner_id=learner.id, lesson_id=self.lesson(10 + (n % 2)), exercise_id="e1", question_id=f"q{n}", correct=ok))
            await db.commit()

        d = (await self.get(f"/admin/learners/{learner.id}", admin)).json()
        self.assertEqual((d["email"], d["role"]), (learner.email, "learner"))
        self.assertEqual(d["progress"]["exercises_answered"], 3)
        self.assertEqual((d["progress"]["exercises_correct"], d["progress"]["lessons_touched"]), (2, 2))
        self.assertEqual({o["product_code"]: o["status"] for o in d["orders"]}, {"pack_quan_he": "PAID", "exam_pass_30": "PENDING"})
        self.assertTrue(all(o["email"] == learner.email for o in d["orders"]))
        # the pack from the order and the revoked pass, both listed
        self.assertEqual(sorted((e["product_code"], e["revoked_at"] is not None) for e in d["entitlements"]), [("exam_pass_30", True), ("pack_quan_he", False)])
        self.assertEqual([(c["status"], c["email"]) for c in d["claims"]], [("open", learner.email)])
        self.assertEqual(d["access"]["lesson_packs"], ["pack_quan_he"])
        self.assertFalse(d["access"]["exam_pass"])  # the only pass was revoked
        self.assertEqual((d["paid_orders"], d["paid_total"], d["open_claims"]), (1, 39_000, 1))

    async def test_an_unknown_learner_is_not_found(self):
        admin = await self.new_profile("admin")
        self.assertEqual((await self.get(f"/admin/learners/{uuid.uuid4()}", admin)).status_code, 404)
        self.assertEqual((await self.get("/admin/learners/not-an-id", admin)).status_code, 422)


@unittest.skipUnless(DB_READY, "no Postgres with the billing schema")
class RoleTests(ApiCase):
    async def test_an_admin_can_make_an_editor_and_take_it_back(self):
        admin, learner = await self.new_profile("admin"), await self.new_profile()
        out = await self.post(f"/admin/learners/{learner.id}/role", admin, {"role": "editor"})
        self.assertEqual((out.status_code, out.json()["role"], out.json()["access"]["staff"]), (200, "editor", True))
        # the editor works at once (the role is read from the database, not from the old token)
        self.assertEqual((await self.get("/admin/billing/orders", learner)).status_code, 403)
        out = await self.post(f"/admin/learners/{learner.id}/role", admin, {"role": "learner"})
        self.assertEqual((out.json()["role"], out.json()["access"]["staff"]), ("learner", False))
        async with self.factory() as db:
            self.assertEqual((await db.get(Profile, learner.id)).role, "learner")

    async def test_a_new_admin_can_use_the_admin_page_with_the_token_they_already_had(self):
        admin, learner = await self.new_profile("admin"), await self.new_profile()
        headers = self.auth(learner)
        before = await self.http.get("/api/v1/admin/overview", headers=headers)
        self.assertEqual(before.status_code, 403)
        await self.post(f"/admin/learners/{learner.id}/role", admin, {"role": "admin"})
        after = await self.http.get("/api/v1/admin/overview", headers=headers)
        self.assertEqual(after.status_code, 200)

    async def test_nobody_changes_their_own_role(self):
        admin = await self.new_profile("admin")
        out = await self.post(f"/admin/learners/{admin.id}/role", admin, {"role": "learner"})
        self.assertEqual((out.status_code, out.json()["code"]), (409, "cannot_change_self"))
        async with self.factory() as db:
            self.assertEqual((await db.get(Profile, admin.id)).role, "admin")

    async def test_only_the_three_roles_exist_and_the_account_must_exist(self):
        admin, learner = await self.new_profile("admin"), await self.new_profile()
        self.assertEqual((await self.post(f"/admin/learners/{learner.id}/role", admin, {"role": "owner"})).status_code, 422)
        self.assertEqual((await self.post(f"/admin/learners/{uuid.uuid4()}/role", admin, {"role": "editor"})).status_code, 404)
        self.assertEqual((await self.post(f"/admin/learners/{learner.id}/role", admin, {})).status_code, 422)


@unittest.skipUnless(DB_READY, "no Postgres with the billing schema")
class OverviewAndOrderToolTests(ApiCase):
    async def overview(self, admin) -> dict:
        out = await self.get("/admin/overview", admin)
        self.assertEqual(out.status_code, 200)
        return out.json()

    async def test_the_summary_moves_with_signups_money_and_the_queue(self):
        admin = await self.new_profile("admin")
        before = await self.overview(admin)
        self.assertTrue(before["billing_enabled"])
        self.assertTrue(before["billing_configured"])

        learner = await self.new_profile()
        order = await self.buy(learner, "pack_quan_he")
        await self.pay(order, 39_000, "REF-ADMIN-OV-FULL")
        short = await self.buy(await self.new_profile(), "pack_sinh_hoat_2")
        await self.pay(short, 20_000, "REF-ADMIN-OV-SHORT")
        await self.post("/billing/claims", learner, {"note": "hỏi"})

        after = await self.overview(admin)
        self.assertEqual(after["learners"]["total"] - before["learners"]["total"], 2)
        self.assertEqual(after["learners"]["new_7d"] - before["learners"]["new_7d"], 2)
        self.assertEqual(after["learners"]["paying"] - before["learners"]["paying"], 1)
        self.assertEqual(after["money"]["paid_total"] - before["money"]["paid_total"], 39_000)
        self.assertEqual(after["money"]["paid_7d"] - before["money"]["paid_7d"], 39_000)
        self.assertEqual(after["money"]["paid_orders"] - before["money"]["paid_orders"], 1)
        self.assertEqual(after["queue"]["needs_review"] - before["queue"]["needs_review"], 1)
        self.assertEqual(after["queue"]["underpaid"] - before["queue"]["underpaid"], 1)
        self.assertEqual(after["queue"]["open_claims"] - before["queue"]["open_claims"], 1)
        product = next(p for p in after["money"]["by_product"] if p["product_code"] == "pack_quan_he")
        self.assertEqual(product["title"], catalog.get("pack_quan_he").title_vi)
        self.assertGreaterEqual(product["revenue"], 39_000)

    async def test_the_payments_of_an_order_are_listed(self):
        admin, learner = await self.new_profile("admin"), await self.new_profile()
        order = await self.buy(learner, "pack_quan_he")
        await self.pay(order, 30_000, "REF-ADMIN-EV-1")
        await self.pay(order, 9_000, "REF-ADMIN-EV-2", source="reconcile")
        events = (await self.get(f"/admin/billing/orders/{order.id}/events", admin)).json()
        self.assertEqual([(e["reference"], e["amount"], e["source"]) for e in events], [("REF-ADMIN-EV-1", 30_000, "webhook"), ("REF-ADMIN-EV-2", 9_000, "reconcile")])
        self.assertEqual(set(events[0]), {"id", "reference", "amount", "source", "outcome", "created_at"})  # no raw body
        self.assertEqual((await self.get(f"/admin/billing/orders/{uuid.uuid4()}/events", admin)).status_code, 404)
        self.assertEqual((await self.get(f"/admin/billing/orders/{order.id}/events", learner)).status_code, 403)

    async def test_looking_at_an_order_takes_it_off_the_queue_and_opens_nothing(self):
        admin, learner = await self.new_profile("admin"), await self.new_profile()
        order = await self.buy(learner, "pack_quan_he")
        await self.pay(order, 30_000, "REF-ADMIN-REVIEW")
        queue = lambda: self.get("/admin/billing/orders?needs_review=true&limit=200", admin)  # noqa: E731
        self.assertIn(str(order.id), [o["id"] for o in (await queue()).json()])

        done = await self.post(f"/admin/billing/orders/{order.id}/review-done", admin, {"note": "để nguyên, đợi họ chuyển bù"})
        body = done.json()
        self.assertEqual((done.status_code, body["needs_review"], body["status"], body["email"]), (200, False, "UNDERPAID", learner.email))
        self.assertIn(str(admin.id), body["note"])
        self.assertIn("đợi họ chuyển bù", body["note"])
        self.assertNotIn(str(order.id), [o["id"] for o in (await queue()).json()])
        # still short, still locked
        self.assertEqual((await self.get(f"/lessons/{self.lesson(20)}/practice", learner)).status_code, 402)
        # a second press changes nothing
        again = (await self.post(f"/admin/billing/orders/{order.id}/review-done", admin, {})).json()
        self.assertEqual(again["note"], body["note"])

    async def test_review_done_needs_an_admin_and_an_order(self):
        admin, learner = await self.new_profile("admin"), await self.new_profile()
        order = await self.buy(learner, "pack_quan_he")
        self.assertEqual((await self.post(f"/admin/billing/orders/{order.id}/review-done", learner, {})).status_code, 403)
        self.assertEqual((await self.post(f"/admin/billing/orders/{uuid.uuid4()}/review-done", admin, {})).status_code, 404)


if __name__ == "__main__":
    unittest.main()

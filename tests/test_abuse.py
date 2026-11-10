"""Keeping the free trial to one per person (app/services/abuse.py, routers/admin_abuse.py), against
a real Postgres (skipped without one)."""
import uuid

from fastapi import HTTPException
from sqlalchemy import delete, select
from starlette.requests import Request

from app.api import deps
from app.models import AccountSignal, BlockedEmailDomain, Profile, TrialUse
from app.services import abuse
from app.services.billing import settings_db
from app.models import BillingSetting
from tests.test_billing_settings import API, SettingsCase


def req(device: str | None = None, ip: str | None = None) -> Request:
    headers = []
    if device:
        headers.append((b"x-haru-device", device.encode()))
    if ip:
        headers.append((b"x-forwarded-for", ip.encode()))
    return Request({"type": "http", "method": "POST", "path": "/", "headers": headers, "client": ("172.18.0.5", 5000)})


def dev() -> str:
    return uuid.uuid4().hex


class Unit(SettingsCase):
    async def test_one_inbox_has_one_key(self):
        self.assertEqual(abuse.email_key("An.Nguyen+haru2@GMail.com"), "annguyen@gmail.com")
        self.assertEqual(abuse.email_key("an.nguyen@googlemail.com"), "annguyen@gmail.com")
        self.assertEqual(abuse.email_key("an.nguyen+x@outlook.com"), "an.nguyen@outlook.com")

    async def test_throwaway_domains_and_their_subdomains(self):
        async with self.factory() as db:
            self.assertTrue(await abuse.is_throwaway(db, "x@mailinator.com"))
            self.assertTrue(await abuse.is_throwaway(db, "x@yopmail.com"))
            self.assertFalse(await abuse.is_throwaway(db, "x@gmail.com"))
            self.assertFalse(await abuse.is_throwaway(db, "x@hust.edu.vn"))

    async def test_only_a_public_address_counts_as_a_network(self):
        self.assertIsNone(abuse.ip_of(req()))  # a private peer, nothing forwarded
        self.assertIsNotNone(abuse.ip_of(req(ip="8.8.8.8")))
        self.assertIsNone(abuse.device_of(req(device="short")))
        self.assertNotEqual(abuse.device_of(req(device="a" * 20)), "a" * 20)  # stored hashed


class AbuseCase(SettingsCase):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        async with self.factory() as db:  # the day's budget must start from nothing here
            await db.execute(delete(TrialUse))
            await db.commit()

    async def asyncTearDown(self):
        async with self.factory() as db:
            ids = (await db.execute(select(Profile.id).where(Profile.email.like("abuse-test-%")))).scalars().all()
            self.profile_ids.extend(ids)
            await db.execute(delete(BlockedEmailDomain).where(BlockedEmailDomain.domain.like("%.abuse-test.dev")))
            await db.commit()
        await super().asyncTearDown()
        abuse.apply({})

    async def setting(self, **values):
        async with self.factory() as db:
            for k, v in values.items():
                db.add(BillingSetting(key=k, value=v))
            await db.commit()
        settings_db.forget()

    async def start(self, learner, feature="talk", **kw):
        async with self.factory() as db:
            granted = await deps.ensure_feature(db, learner, feature, req(**kw))
            await db.commit()
            return granted

    async def refused(self, learner, feature="talk", **kw) -> dict:
        with self.assertRaises(HTTPException) as cm:
            await self.start(learner, feature, **kw)
        return cm.exception.detail

    def email(self, local="abuse-test-") -> str:
        return f"{local}{uuid.uuid4().hex[:10]}@gmail.com"


class SignupTests(AbuseCase):
    async def test_a_throwaway_inbox_cannot_sign_up(self):
        r = await self.http.post(API + "/auth/signup", json={"email": "abuse-test-x@mailinator.com", "password": "password123"})
        self.assertEqual((r.status_code, r.json()["code"]), (422, "disposable_email"))

    async def test_an_admin_domain_is_refused_too(self):
        async with self.factory() as db:
            db.add(BlockedEmailDomain(domain="trash.abuse-test.dev"))
            await db.commit()
        r = await self.http.post(API + "/auth/signup", json={"email": "abuse-test-y@mx.trash.abuse-test.dev", "password": "password123"})
        self.assertEqual(r.json()["code"], "disposable_email")

    async def test_the_same_gmail_inbox_cannot_sign_up_twice(self):
        local = f"abuse.test.{uuid.uuid4().hex[:8]}"
        r = await self.http.post(API + "/auth/signup", json={"email": f"{local}@gmail.com", "password": "password123"})
        self.assertEqual(r.status_code, 201)
        twin = local.replace(".", "") + "+2@gmail.com"
        r = await self.http.post(API + "/auth/signup", json={"email": twin, "password": "password123"})
        self.assertEqual((r.status_code, r.json()["code"]), (409, "email_taken"))
        async with self.factory() as db:
            p = (await db.execute(select(Profile).where(Profile.email == f"{local}@gmail.com"))).scalar_one()
            self.profile_ids.append(p.id)

    async def test_one_network_makes_a_few_accounts_a_day(self):
        await self.setting(signup_per_ip_daily=2)
        codes = []
        for _ in range(3):
            r = await self.http.post(
                API + "/auth/signup",
                json={"email": self.email(), "password": "password123"},
                headers={"X-Forwarded-For": "203.0.113.77, 8.8.4.4", "X-Haru-Device": dev()},
            )
            codes.append(r.status_code)
        self.assertEqual(codes, [201, 201, 429])
        r = await self.http.post(
            API + "/auth/signup", json={"email": self.email(), "password": "password123"}, headers={"X-Forwarded-For": "1.1.1.1"}
        )
        self.assertEqual(r.status_code, 201)  # another network is not affected

    async def test_signup_and_login_leave_traces(self):
        email, device = self.email(), dev()
        h = {"X-Forwarded-For": "8.8.8.8", "X-Haru-Device": device}
        await self.http.post(API + "/auth/signup", json={"email": email, "password": "password123"}, headers=h)
        r = await self.http.post(API + "/auth/login", json={"email": email, "password": "password123"}, headers=h)
        self.assertEqual(r.status_code, 200)
        async with self.factory() as db:
            rows = (await db.execute(select(AccountSignal).join(Profile).where(Profile.email == email))).scalars().all()
        self.assertEqual(sorted(r.kind for r in rows), ["device", "ip"])
        self.assertEqual({r.seen_count for r in rows}, {2})
        self.assertNotIn(device, [r.value for r in rows])


class TrialGateTests(AbuseCase):
    async def test_one_trial_per_browser(self):
        a, b = await self.new_profile(), await self.new_profile()
        d = dev()
        self.assertEqual(await self.start(a, device=d), 20 * 60)
        detail = await self.refused(b, device=d)
        self.assertEqual((detail["status"], detail["reason"]), (402, "trial_device"))
        self.assertEqual(await self.start(b, device=dev()), 20 * 60)  # another browser (soft, by design)
        self.assertIsNotNone(await self.start(a, device=d))  # A keeps what is left of its own trial

    async def test_a_browser_where_a_trial_account_signed_in_is_spent_too(self):
        a, b = await self.new_profile(), await self.new_profile()
        phone, laptop = dev(), dev()
        await self.start(a, device=phone)
        async with self.factory() as db:  # A signs in on the laptop later
            await abuse.remember(db, a.id, req(device=laptop))
            await db.commit()
        self.assertEqual((await self.refused(b, device=laptop))["reason"], "trial_device")

    async def test_a_family_browser_can_be_allowed_more_accounts(self):
        await self.setting(trial_accounts_per_device=2)
        d = dev()
        for p in [await self.new_profile(), await self.new_profile()]:
            self.assertIsNotNone(await self.start(p, device=d))
        self.assertEqual((await self.refused(await self.new_profile(), device=d))["reason"], "trial_device")

    async def test_a_trial_needs_the_browser_id(self):
        detail = await self.refused(await self.new_profile())
        self.assertEqual((detail["status"], detail["code"]), (400, "device_missing"))

    async def test_a_soft_cap_of_new_trials_per_network(self):
        await self.setting(trial_accounts_per_ip_daily=2)
        ip = "198.51.100.23, 9.9.9.9"
        for _ in range(2):
            await self.start(await self.new_profile(), device=dev(), ip=ip)
        self.assertEqual((await self.refused(await self.new_profile(), device=dev(), ip=ip))["reason"], "trial_network")
        self.assertIsNotNone(await self.start(await self.new_profile(), device=dev(), ip="1.0.0.1"))

    async def test_the_days_budget_cuts_then_refuses(self):
        await self.setting(trial_daily_minutes=25)
        self.assertEqual(await self.start(await self.new_profile(), device=dev()), 20 * 60)
        self.assertEqual(await self.start(await self.new_profile(), device=dev()), 5 * 60)
        self.assertEqual((await self.refused(await self.new_profile(), device=dev()))["reason"], "trial_budget")

    async def test_the_presentation_budget(self):
        await self.setting(trial_daily_present_tries=1)
        self.assertIsNone(await self.start(await self.new_profile(), "present", device=dev()))
        self.assertEqual((await self.refused(await self.new_profile(), "present", device=dev()))["reason"], "trial_budget")

    async def test_the_pause_switch(self):
        await self.setting(trial_enabled=0)
        detail = await self.refused(await self.new_profile(), device=dev())
        self.assertEqual(detail["reason"], "trial_paused")
        self.assertEqual(detail["unlock_with"], ["speak_pass_30", "speak_pass_90"])

    async def test_a_failed_start_is_not_counted(self):
        a = await self.new_profile()
        async with self.factory() as db:
            await deps.ensure_feature(db, a, "talk", req(device=dev()))
            await db.rollback()  # e.g. the live token could not be made
        async with self.factory() as db:
            self.assertEqual(await abuse.used_today(db), (0, 0))


class RouteTests(AbuseCase):
    async def test_the_speaking_routes_take_the_request_not_a_query_param(self):
        from app.main import app

        seen = set()
        for route in app.routes:
            name = getattr(getattr(route, "endpoint", None), "__name__", "")
            if name in ("start_conversation", "start_debate", "add_attempt"):
                seen.add(name)
                self.assertNotIn("request", [p.name for p in route.dependant.query_params], route.path)
                self.assertEqual(route.dependant.request_param_name, "request", route.path)
        self.assertEqual(seen, {"start_conversation", "start_debate", "add_attempt"})


class AdminTests(AbuseCase):
    async def test_shared_browsers_are_listed_and_locked_together(self):
        admin = await self.new_profile("admin")
        a, b, solo = await self.new_profile(), await self.new_profile(), await self.new_profile()
        d = dev()
        await self.setting(trial_accounts_per_device=2)
        await self.start(a, device=d)
        await self.start(b, device=d)
        await self.start(solo, device=dev())
        r = await self.http.get(API + "/admin/abuse/clusters", headers=self.auth(admin))
        self.assertEqual(r.status_code, 200)
        mine = [c for c in r.json() if {x["id"] for x in c["accounts"]} == {str(a.id), str(b.id)}]
        self.assertEqual(len(mine), 1)
        self.assertEqual((mine[0]["kind"], mine[0]["trial_accounts"]), ("device", 2))
        self.assertEqual({x["trial_live_minutes"] for x in mine[0]["accounts"]}, {20})

        r = await self.http.post(
            API + "/admin/abuse/lock", headers=self.auth(admin), json={"profile_ids": [str(a.id), str(b.id), str(admin.id)]}
        )
        self.assertEqual(r.json(), {"locked": 2, "already": 0, "skipped": 1})
        async with self.factory() as db:
            locked = await db.get(Profile, a.id)
            self.assertIsNotNone(locked.disabled_at)
            self.assertIn("điều khoản", locked.disabled_reason)
        r = await self.http.get(API + "/auth/me", headers=self.auth(a))
        self.assertIn(r.status_code, (401, 403))

    async def test_the_guard_and_the_overview(self):
        admin = await self.new_profile("admin")
        h = self.auth(admin)
        r = await self.http.put(API + "/admin/abuse/guard", headers=h, json={"trial_enabled": False, "trial_daily_minutes": 90})
        self.assertEqual((r.json()["trial_enabled"], r.json()["trial_daily_minutes"], r.json()["signup_per_ip_daily"]), (False, 90, 5))
        r = await self.http.put(API + "/admin/abuse/guard", headers=h, json={"trial_accounts_per_device": 0})
        self.assertEqual(r.status_code, 422)
        r = await self.http.get(API + "/admin/abuse", headers=h)
        body = r.json()
        self.assertFalse(body["guard"]["trial_enabled"])
        self.assertEqual(body["today"]["live_cap"], 90)
        self.assertGreater(body["bundled_domains"], 1000)
        learner = await self.new_profile()
        self.assertEqual((await self.http.get(API + "/admin/abuse", headers=self.auth(learner))).status_code, 403)

    async def test_admin_domains(self):
        h = self.auth(await self.new_profile("admin"))
        r = await self.http.post(API + "/admin/abuse/domains", headers=h, json={"domain": "@Spam.Abuse-Test.dev"})
        self.assertEqual((r.status_code, [d["domain"] for d in r.json()]), (201, ["spam.abuse-test.dev"]))
        r = await self.http.post(API + "/admin/abuse/domains", headers=h, json={"domain": "gmail.com"})
        self.assertEqual(r.json()["code"], "protected_domain")
        r = await self.http.post(API + "/admin/abuse/domains", headers=h, json={"domain": "not a domain"})
        self.assertEqual(r.status_code, 422)
        r = await self.http.delete(API + "/admin/abuse/domains/spam.abuse-test.dev", headers=h)
        self.assertEqual(r.json(), [])

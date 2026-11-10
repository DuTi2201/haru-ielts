"""The help channels an admin sets (app/services/billing/support.py), against a real Postgres."""
from unittest import mock

from sqlalchemy import delete

from app.models import SiteSetting
from app.services.billing import settings_db, support
from tests.test_billing_settings import API, SettingsCase


class LinkTests(SettingsCase):
    async def test_each_channel_becomes_a_safe_link(self):
        self.assertEqual(support.link_of("email", "hotro@haru.vn"), "mailto:hotro@haru.vn")
        self.assertEqual(support.link_of("phone", "0912 345 678"), "tel:0912345678")
        self.assertEqual(support.link_of("phone", "+84 912 345 678"), "tel:+84912345678")
        self.assertEqual(support.link_of("zalo", "0912.345.678"), "https://zalo.me/0912345678")
        self.assertEqual(support.link_of("zalo", "+84912345678"), "https://zalo.me/0912345678")
        self.assertEqual(support.link_of("zalo", "https://zalo.me/g/abcdef"), "https://zalo.me/g/abcdef")
        self.assertEqual(support.link_of("telegram", "@haru_help"), "https://t.me/haru_help")
        self.assertEqual(support.link_of("messenger", "haru.korean"), "https://m.me/haru.korean")
        self.assertEqual(support.link_of("facebook", "https://www.facebook.com/haru"), "https://www.facebook.com/haru")
        for channel, bad in [
            ("email", "min220115"),
            ("zalo", "javascript:alert(1)"),
            ("telegram", "https://evil.example/t"),
            ("facebook", "http://facebook.com/x"),
            ("phone", "12"),
        ]:
            self.assertIsNone(support.link_of(channel, bad), (channel, bad))

    async def test_an_email_in_the_old_setting_is_a_mailto_not_a_page(self):
        support.apply(None)
        with mock.patch.object(support.settings, "BILLING_SUPPORT_URL", "min220115@gmail.com"), mock.patch.object(
            support.settings, "MERCHANT_PHONE", ""
        ):
            self.assertEqual(support.primary_url(), "mailto:min220115@gmail.com")


class AdminTests(SettingsCase):
    async def asyncTearDown(self):
        async with self.factory() as db:
            await db.execute(delete(SiteSetting))
            await db.commit()
        support.apply(None)
        await super().asyncTearDown()

    async def test_the_admin_sets_what_learners_see(self):
        h = self.auth(await self.new_profile("admin"))
        r = await self.http.put(
            API + "/admin/billing/support",
            headers=h,
            json={"zalo": "0912345678", "email": "hotro@haru.vn", "telegram": "@haru_help", "hours": "8:00–22:00 mỗi ngày"},
        )
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual([x["kind"] for x in r.json()["shown"]["links"]], ["zalo", "telegram", "email"])
        settings_db.forget()
        r = await self.http.get(API + "/billing/catalog")
        body = r.json()
        self.assertEqual(body["support_url"], "https://zalo.me/0912345678")
        self.assertEqual(body["support"]["hours"], "8:00–22:00 mỗi ngày")
        self.assertEqual(body["support"]["links"][2]["url"], "mailto:hotro@haru.vn")

    async def test_a_bad_value_is_refused_and_learners_cannot_set_it(self):
        h = self.auth(await self.new_profile("admin"))
        r = await self.http.put(API + "/admin/billing/support", headers=h, json={"telegram": "https://evil.example"})
        self.assertEqual((r.status_code, r.json()["code"]), (422, "bad_support_contact"))
        self.assertIn("Telegram", r.json()["detail"])
        learner = self.auth(await self.new_profile())
        self.assertEqual((await self.http.put(API + "/admin/billing/support", headers=learner, json={})).status_code, 403)

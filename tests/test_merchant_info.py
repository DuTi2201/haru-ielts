"""Thông tin vận hành an admin sets once (app/services/billing/merchant.py), against a real Postgres."""
from unittest import mock

from sqlalchemy import delete

from app.models import SiteSetting
from app.services.billing import merchant, settings_db
from tests.test_billing_settings import API, SettingsCase


class MerchantTests(SettingsCase):
    async def asyncTearDown(self):
        async with self.factory() as db:
            await db.execute(delete(SiteSetting).where(SiteSetting.key == "merchant"))
            await db.commit()
        merchant.apply(None)
        await super().asyncTearDown()

    async def test_saved_once_every_page_reads_it_and_empty_fields_fall_back(self):
        h = self.auth(await self.new_profile("admin"))
        with mock.patch.object(merchant.settings, "MERCHANT_EMAIL", "env@haru.vn"):
            r = await self.http.put(
                API + "/admin/billing/merchant",
                headers=h,
                json={"name": "  Hộ kinh doanh   Haru ", "tax_id": "0123456789", "address": "Hải Phòng", "phone": ""},
            )
            self.assertEqual(r.status_code, 200, r.text)
            self.assertEqual(r.json()["name"], "Hộ kinh doanh Haru")
            settings_db.forget()
            shown = (await self.http.get(API + "/billing/catalog")).json()["merchant"]
        self.assertEqual(
            (shown["name"], shown["tax_id"], shown["address"], shown["email"]),
            ("Hộ kinh doanh Haru", "0123456789", "Hải Phòng", "env@haru.vn"),
        )

    async def test_a_bad_value_is_refused_and_learners_cannot_set_it(self):
        h = self.auth(await self.new_profile("admin"))
        for body, field in (({"email": "abc"}, "Email"), ({"tax_id": "12"}, "Mã số thuế"), ({"phone": "gọi tôi"}, "điện thoại")):
            r = await self.http.put(API + "/admin/billing/merchant", headers=h, json=body)
            self.assertEqual((r.status_code, r.json()["code"]), (422, "bad_merchant"))
            self.assertIn(field, r.json()["detail"])
        learner = self.auth(await self.new_profile())
        self.assertEqual((await self.http.put(API + "/admin/billing/merchant", headers=learner, json={})).status_code, 403)
        self.assertEqual((await self.http.get(API + "/admin/billing/merchant", headers=learner)).status_code, 403)

"""Locking an account, an admin's temporary password, and the learner's own password change, over
HTTP against the real routes and a real Postgres. What must hold: a locked account is shut out
everywhere at once (login, every token, refresh) and gets everything back on unlock; a reset
password ends the old sessions and the old password; a temporary password works only until it
expires and must be replaced; an admin cannot lock or reset themselves or another admin.
Skipped without the database. Every password is an obviously fake test value."""
import asyncio
import unittest
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.core.security import create_access_token, create_refresh_token, hash_password, verify_password
from app.models import Profile
from tests.billing_support import DB_READY
from tests.test_billing_api import ApiCase

API = "/api/v1"
OLD = "fake-test-old-password"


@unittest.skipUnless(DB_READY, "no Postgres with the billing schema")
class SecurityCase(ApiCase):
    async def new_profile(self, role="learner") -> Profile:
        """The login and /auth/me routes validate the e-mail, which refuses the `.invalid` domain
        the other billing tests use, so these accounts are on example.com (a reserved name too)."""
        async with self.factory() as db:
            p = Profile(email=f"billing-test-{uuid.uuid4().hex}@example.com", hashed_password="x", role=role)
            db.add(p)
            await db.commit()
        self.profile_ids.append(p.id)
        return p

    async def with_password(self, role="learner", password=OLD) -> Profile:
        """A learner whose password really is `password` (new_profile stores a placeholder)."""
        p = await self.new_profile(role)
        async with self.factory() as db:
            (await db.get(Profile, p.id)).hashed_password = hash_password(password)
            await db.commit()
        return p

    async def login(self, profile, password=OLD):
        return await self.http.post(API + "/auth/login", json={"email": profile.email, "password": password})

    def bearer(self, token: str) -> dict:
        return {"Authorization": f"Bearer {token}"}

    async def me(self, token: str):
        return await self.http.get(API + "/auth/me", headers=self.bearer(token))

    async def reload(self, profile) -> Profile:
        async with self.factory() as db:
            return await db.get(Profile, profile.id)


class LockTests(SecurityCase):
    async def test_a_locked_account_is_shut_out_everywhere_and_comes_back_on_unlock(self):
        admin, learner = await self.new_profile("admin"), await self.with_password()
        tokens = (await self.login(learner)).json()
        self.assertEqual((await self.me(tokens["access_token"])).status_code, 200)

        out = await self.post(f"/admin/learners/{learner.id}/lock", admin, {"reason": "chia sẻ tài khoản"})
        row = out.json()
        self.assertEqual((out.status_code, row["disabled_reason"]), (200, "chia sẻ tài khoản"))
        self.assertIsNotNone(row["disabled_at"])

        # the token it already held stops working at once
        gone = await self.me(tokens["access_token"])
        self.assertEqual((gone.status_code, gone.json()["code"]), (401, "account_disabled"))
        self.assertEqual((await self.get("/me/entitlements", learner)).json()["code"], "account_disabled")
        # it cannot log in, and cannot trade its refresh token for a new pair
        blocked = await self.login(learner)
        self.assertEqual((blocked.status_code, blocked.json()["code"]), (403, "account_disabled"))
        refreshed = await self.http.post(API + "/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
        self.assertEqual((refreshed.status_code, refreshed.json()["code"]), (401, "account_disabled"))
        # a public page still answers it, as if it were anonymous
        self.assertEqual((await self.get("/lessons", learner)).status_code, 200)

        out = await self.post(f"/admin/learners/{learner.id}/unlock", admin)
        self.assertEqual((out.status_code, out.json()["disabled_at"], out.json()["disabled_reason"]), (200, None, None))
        self.assertEqual((await self.me(tokens["access_token"])).status_code, 200)
        self.assertEqual((await self.login(learner)).status_code, 200)

    async def test_a_wrong_password_never_reveals_that_the_account_is_locked(self):
        admin, learner = await self.new_profile("admin"), await self.with_password()
        await self.post(f"/admin/learners/{learner.id}/lock", admin, {})
        out = await self.login(learner, "not-the-password")
        self.assertEqual((out.status_code, out.json()["code"]), (401, "invalid_credentials"))

    async def test_locking_twice_changes_nothing_and_what_is_kept_stays(self):
        admin, learner = await self.new_profile("admin"), await self.with_password()
        order = await self.buy(learner, "pack_quan_he")
        await self.pay(order, 39_000, "REF-LOCK-KEEP")
        first = (await self.post(f"/admin/learners/{learner.id}/lock", admin, {"reason": "một"})).json()
        second = (await self.post(f"/admin/learners/{learner.id}/lock", admin, {"reason": "hai"})).json()
        self.assertEqual((second["disabled_at"], second["disabled_reason"]), (first["disabled_at"], "một"))
        # the money and the rights are untouched
        self.assertEqual((second["paid_orders"], second["access"]["lesson_packs"]), (1, ["pack_quan_he"]))

    async def test_the_list_filters_locked_accounts_and_the_summary_counts_them(self):
        admin, learner, other = await self.new_profile("admin"), await self.new_profile(), await self.new_profile()
        before = (await self.get("/admin/overview", admin)).json()["learners"]["locked"]
        await self.post(f"/admin/learners/{learner.id}/lock", admin, {})
        ids = lambda data: {r["id"] for r in data["items"]}  # noqa: E731
        locked = (await self.get("/admin/learners?locked=true&limit=100", admin)).json()
        self.assertIn(str(learner.id), ids(locked))
        self.assertNotIn(str(other.id), ids(locked))
        self.assertTrue(all(r["disabled_at"] for r in locked["items"]))
        open_ = (await self.get("/admin/learners?locked=false&limit=100", admin)).json()
        self.assertNotIn(str(learner.id), ids(open_))
        self.assertEqual((await self.get("/admin/overview", admin)).json()["learners"]["locked"] - before, 1)

    async def test_an_admin_cannot_lock_themselves_or_another_admin(self):
        admin, other_admin, learner = await self.new_profile("admin"), await self.new_profile("admin"), await self.new_profile()
        out = await self.post(f"/admin/learners/{admin.id}/lock", admin, {})
        self.assertEqual((out.status_code, out.json()["code"]), (409, "cannot_change_self"))
        out = await self.post(f"/admin/learners/{other_admin.id}/lock", admin, {})
        self.assertEqual((out.status_code, out.json()["code"]), (409, "admin_protected"))
        # change the role first, then it can be locked
        await self.post(f"/admin/learners/{other_admin.id}/role", admin, {"role": "editor"})
        self.assertEqual((await self.post(f"/admin/learners/{other_admin.id}/lock", admin, {})).status_code, 200)
        self.assertEqual((await self.post(f"/admin/learners/{uuid.uuid4()}/lock", admin, {})).status_code, 404)
        self.assertEqual((await self.post(f"/admin/learners/{learner.id}/lock", learner, {})).status_code, 403)
        self.assertEqual((await self.post(f"/admin/learners/{learner.id}/lock", None, {})).status_code, 401)

    async def test_a_reason_is_short_and_optional(self):
        admin, learner = await self.new_profile("admin"), await self.new_profile()
        self.assertEqual((await self.post(f"/admin/learners/{learner.id}/lock", admin, {"reason": "x" * 256})).status_code, 422)
        out = await self.post(f"/admin/learners/{learner.id}/lock", admin, {"reason": "   "})
        self.assertEqual((out.status_code, out.json()["disabled_reason"]), (200, None))


class ResetTests(SecurityCase):
    async def test_a_reset_gives_a_temporary_password_and_ends_the_old_password_and_sessions(self):
        admin, learner = await self.new_profile("admin"), await self.with_password()
        old = (await self.login(learner)).json()

        out = await self.post(f"/admin/learners/{learner.id}/reset-password", admin)
        body = out.json()
        self.assertEqual(out.status_code, 200)
        self.assertEqual(out.headers.get("cache-control"), "no-store")
        temp = body["temporary_password"]
        self.assertEqual(len(temp), 12)
        self.assertFalse(set(temp) & set("0O1lI"))  # nothing to misread when it is read out
        left = datetime.fromisoformat(body["expires_at"]) - datetime.now(timezone.utc)
        self.assertTrue(timedelta(hours=71) < left <= timedelta(hours=72), left)

        stored = await self.reload(learner)
        self.assertNotEqual(stored.hashed_password, temp)  # only a hash is kept
        self.assertTrue(verify_password(temp, stored.hashed_password))

        # the old password and every old session are over
        self.assertEqual((await self.login(learner, OLD)).status_code, 401)
        self.assertEqual((await self.me(old["access_token"])).json()["code"], "invalid_token")
        stale = await self.http.post(API + "/auth/refresh", json={"refresh_token": old["refresh_token"]})
        self.assertEqual((stale.status_code, stale.json()["code"]), (401, "invalid_token"))

        # the temporary password works, and the app is told to ask for a new one
        fresh = await self.login(learner, temp)
        self.assertEqual(fresh.status_code, 200)
        me = (await self.me(fresh.json()["access_token"])).json()
        self.assertTrue(me["must_change_password"])
        again = await self.http.post(API + "/auth/refresh", json={"refresh_token": fresh.json()["refresh_token"]})
        self.assertEqual(again.status_code, 200)  # a session started after the reset is fine

    async def test_two_resets_give_different_passwords_and_the_first_stops_working(self):
        admin, learner = await self.new_profile("admin"), await self.with_password()
        first = (await self.post(f"/admin/learners/{learner.id}/reset-password", admin)).json()["temporary_password"]
        second = (await self.post(f"/admin/learners/{learner.id}/reset-password", admin)).json()["temporary_password"]
        self.assertNotEqual(first, second)
        self.assertEqual((await self.login(learner, first)).status_code, 401)
        self.assertEqual((await self.login(learner, second)).status_code, 200)

    async def test_an_expired_temporary_password_no_longer_logs_in(self):
        admin, learner = await self.new_profile("admin"), await self.with_password()
        temp = (await self.post(f"/admin/learners/{learner.id}/reset-password", admin)).json()["temporary_password"]
        async with self.factory() as db:
            (await db.get(Profile, learner.id)).temp_password_expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
            await db.commit()
        out = await self.login(learner, temp)
        self.assertEqual((out.status_code, out.json()["code"]), (403, "temp_password_expired"))
        # the admin can simply reset again
        again = (await self.post(f"/admin/learners/{learner.id}/reset-password", admin)).json()["temporary_password"]
        self.assertEqual((await self.login(learner, again)).status_code, 200)

    async def test_the_list_shows_who_still_has_a_temporary_password(self):
        admin, learner = await self.new_profile("admin"), await self.with_password()
        row = lambda: self.get(f"/admin/learners/{learner.id}", admin)  # noqa: E731
        self.assertIsNone((await row()).json()["temp_password_expires_at"])
        await self.post(f"/admin/learners/{learner.id}/reset-password", admin)
        self.assertIsNotNone((await row()).json()["temp_password_expires_at"])

    async def test_a_locked_account_can_be_reset_and_stays_locked(self):
        admin, learner = await self.new_profile("admin"), await self.with_password()
        await self.post(f"/admin/learners/{learner.id}/lock", admin, {})
        temp = (await self.post(f"/admin/learners/{learner.id}/reset-password", admin)).json()["temporary_password"]
        self.assertEqual((await self.login(learner, temp)).json()["code"], "account_disabled")

    async def test_nobody_resets_their_own_or_another_admins_password_here(self):
        admin, other_admin, learner = await self.new_profile("admin"), await self.new_profile("admin"), await self.new_profile()
        out = await self.post(f"/admin/learners/{admin.id}/reset-password", admin)
        self.assertEqual((out.status_code, out.json()["code"]), (409, "cannot_change_self"))
        out = await self.post(f"/admin/learners/{other_admin.id}/reset-password", admin)
        self.assertEqual((out.status_code, out.json()["code"]), (409, "admin_protected"))
        self.assertEqual((await self.post(f"/admin/learners/{uuid.uuid4()}/reset-password", admin)).status_code, 404)
        for who in (learner, await self.new_profile("editor")):
            self.assertEqual((await self.post(f"/admin/learners/{learner.id}/reset-password", who)).status_code, 403)
        self.assertEqual((await self.post(f"/admin/learners/{learner.id}/reset-password")).status_code, 401)
        # the refused attempts changed nothing
        async with self.factory() as db:
            kept = (await db.execute(select(Profile.temp_password_expires_at).where(Profile.id.in_([admin.id, other_admin.id])))).scalars().all()
        self.assertEqual(kept, [None, None])


class ChangePasswordTests(SecurityCase):
    async def change(self, token, current, new):
        return await self.http.post(
            API + "/auth/change-password", headers=self.bearer(token), json={"current_password": current, "new_password": new}
        )

    async def test_the_learner_changes_their_own_password_and_other_sessions_end(self):
        learner = await self.with_password()
        here, elsewhere = (await self.login(learner)).json(), (await self.login(learner)).json()
        await asyncio.sleep(0.01)
        out = await self.change(here["access_token"], OLD, "fake-test-new-password")
        self.assertEqual(out.status_code, 200)
        new = out.json()
        self.assertEqual((await self.me(new["access_token"])).status_code, 200)  # this session carries on
        self.assertEqual((await self.me(elsewhere["access_token"])).status_code, 401)
        self.assertEqual((await self.me(here["access_token"])).status_code, 401)  # the pair it asked with is spent too
        self.assertEqual((await self.login(learner, OLD)).status_code, 401)
        self.assertEqual((await self.login(learner, "fake-test-new-password")).status_code, 200)

    async def test_replacing_a_temporary_password_clears_the_demand(self):
        admin, learner = await self.new_profile("admin"), await self.with_password()
        temp = (await self.post(f"/admin/learners/{learner.id}/reset-password", admin)).json()["temporary_password"]
        token = (await self.login(learner, temp)).json()["access_token"]
        self.assertTrue((await self.me(token)).json()["must_change_password"])
        new = (await self.change(token, temp, "fake-test-own-password")).json()
        self.assertFalse((await self.me(new["access_token"])).json()["must_change_password"])
        self.assertIsNone((await self.reload(learner)).temp_password_expires_at)
        # and it is a login that works again after the temporary period would have ended
        self.assertEqual((await self.login(learner, "fake-test-own-password")).status_code, 200)

    async def test_a_wrong_current_password_a_repeat_or_a_weak_one_is_refused(self):
        learner = await self.with_password()
        token = (await self.login(learner)).json()["access_token"]
        out = await self.change(token, "not-it", "fake-test-new-password")
        self.assertEqual((out.status_code, out.json()["code"]), (400, "wrong_password"))
        out = await self.change(token, OLD, OLD)
        self.assertEqual((out.status_code, out.json()["code"]), (400, "same_password"))
        self.assertEqual((await self.change(token, OLD, "short")).status_code, 422)
        self.assertEqual((await self.change(token, OLD, "ế" * 40)).status_code, 422)  # 120 bytes: bcrypt would cut it
        self.assertEqual((await self.me(token)).status_code, 200)  # nothing changed
        self.assertEqual((await self.login(learner)).status_code, 200)

    async def test_it_needs_a_signed_in_account(self):
        self.assertEqual(
            (await self.http.post(API + "/auth/change-password", json={"current_password": "a", "new_password": "bbbbbbbb"})).status_code, 401
        )


class TokenTests(SecurityCase):
    async def test_a_token_carries_its_issue_time_and_tokens_without_one_are_refused_after_a_reset(self):
        admin, learner = await self.new_profile("admin"), await self.new_profile()
        self.assertEqual((await self.get("/me/entitlements", learner)).status_code, 200)
        await self.post(f"/admin/learners/{learner.id}/reset-password", admin)
        # a token made after the reset is fine; one made before it (here: signed by hand with no `ts`) is not
        self.assertEqual((await self.get("/me/entitlements", learner)).status_code, 200)
        from jose import jwt

        from app.core.config import settings

        bare = jwt.encode({"sub": str(learner.id), "role": "learner", "type": "access", "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
                          settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
        self.assertEqual((await self.me(bare)).json()["code"], "invalid_token")

    async def test_an_account_nobody_has_touched_still_accepts_every_token_it_ever_had(self):
        learner = await self.new_profile()
        bare_refresh = create_refresh_token(str(learner.id), "learner")
        self.assertEqual((await self.http.post(API + "/auth/refresh", json={"refresh_token": bare_refresh})).status_code, 200)
        self.assertEqual((await self.me(create_access_token(str(learner.id), "learner"))).status_code, 200)


if __name__ == "__main__":
    unittest.main()

"""Security fixes of the November 2026 audit, checked without a database: only access tokens call
the API, a refresh token is redeemed once, sign-in is throttled, lesson content and new recordings
need a signed-in caller, and production publishes no route list."""
import asyncio
import unittest
from types import SimpleNamespace
from unittest import mock

from fastapi import HTTPException

from app.api import deps
from app.api.routers import audio
from app.core import ratelimit, security


class FakeRedis:
    def __init__(self):
        self.data: dict[str, int | str] = {}

    async def get(self, key):
        v = self.data.get(key)
        return None if v is None else str(v)

    async def ttl(self, key):
        return 600

    async def incr(self, key):
        self.data[key] = int(self.data.get(key, 0)) + 1
        return self.data[key]

    async def expire(self, key, seconds):
        return True

    async def delete(self, key):
        self.data.pop(key, None)

    async def set(self, key, value, nx=False, ex=None):
        if nx and key in self.data:
            return None
        self.data[key] = value
        return True


class BrokenRedis:
    def __getattr__(self, name):
        async def boom(*a, **k):
            raise ConnectionError("redis is down")

        return boom


def request(ip="8.8.8.8", authorization=None):
    headers = {"x-forwarded-for": ip}
    if authorization:
        headers["authorization"] = authorization
    return SimpleNamespace(headers=headers, client=None)


def run(coro):
    return asyncio.run(coro)


class TokenKindTests(unittest.TestCase):
    def test_only_an_access_token_calls_the_api(self):
        access = security.create_access_token("11111111-1111-1111-1111-111111111111", "learner")
        refresh = security.create_refresh_token("11111111-1111-1111-1111-111111111111", "learner")
        self.assertEqual(security.decode_access_token(access)["type"], "access")
        with self.assertRaises(ValueError):
            security.decode_access_token(refresh)
        creds = SimpleNamespace(credentials=refresh)
        with self.assertRaises(HTTPException) as ctx:
            run(deps.get_current_claims(creds))
        self.assertEqual((ctx.exception.status_code, ctx.exception.detail["code"]), (401, "invalid_token"))

    def test_a_refresh_token_has_its_own_id_and_tampering_is_refused(self):
        a = security.decode_token(security.create_refresh_token("x", "learner"))
        b = security.decode_token(security.create_refresh_token("x", "learner"))
        self.assertTrue(a["jti"] and b["jti"] and a["jti"] != b["jti"])
        token = security.create_access_token("x", "learner")
        with self.assertRaises(ValueError):
            security.decode_token(token[:-2] + ("aa" if not token.endswith("aa") else "bb"))
        with self.assertRaises(ValueError):
            security.decode_token("not-a-token")

    def test_a_token_signed_with_no_algorithm_is_refused(self):
        import base64
        import json

        def part(d):
            return base64.urlsafe_b64encode(json.dumps(d).encode()).rstrip(b"=").decode()

        forged = part({"alg": "none", "typ": "JWT"}) + "." + part({"sub": "x", "type": "access", "exp": 9999999999}) + "."
        with self.assertRaises(ValueError):
            security.decode_token(forged)


class RefreshOnceTests(unittest.TestCase):
    def test_the_second_use_of_a_refresh_token_is_refused(self):
        with mock.patch.object(ratelimit, "async_redis", FakeRedis()):
            self.assertTrue(run(ratelimit.refresh_token_unused("abc", 60)))
            self.assertFalse(run(ratelimit.refresh_token_unused("abc", 60)))
            self.assertTrue(run(ratelimit.refresh_token_unused("other", 60)))


class LoginGuardTests(unittest.TestCase):
    def test_five_wrong_passwords_lock_the_account_for_a_while_and_the_right_one_clears_the_count(self):
        fake = FakeRedis()
        with mock.patch.object(ratelimit, "async_redis", fake):
            for _ in range(ratelimit.LOGIN_PER_EMAIL):
                run(ratelimit.login_check(request(), "A@example.com"))
                run(ratelimit.login_failed(request(), "A@example.com"))
            with self.assertRaises(HTTPException) as ctx:
                run(ratelimit.login_check(request("9.9.9.9"), "a@example.com"))  # another address, same account
            self.assertEqual(ctx.exception.status_code, 429)
            self.assertIn("Retry-After", ctx.exception.headers)
            run(ratelimit.login_check(request(), "b@example.com"))  # another account is not affected yet
            run(ratelimit.login_succeeded(request(), "a@example.com"))
            run(ratelimit.login_check(request("9.9.9.9"), "a@example.com"))

    def test_one_address_trying_many_accounts_is_stopped(self):
        with mock.patch.object(ratelimit, "async_redis", FakeRedis()):
            for i in range(ratelimit.LOGIN_PER_IP):
                run(ratelimit.login_failed(request("7.7.7.7"), f"u{i}@example.com"))
            with self.assertRaises(HTTPException) as ctx:
                run(ratelimit.login_check(request("7.7.7.7"), "fresh@example.com"))
            self.assertEqual(ctx.exception.status_code, 429)

    def test_with_redis_down_sign_in_is_refused_not_left_unguarded(self):
        with mock.patch.object(ratelimit, "async_redis", BrokenRedis()):
            with self.assertRaises(HTTPException) as ctx:
                run(ratelimit.login_check(request(), "a@example.com"))
            self.assertEqual(ctx.exception.status_code, 503)
            self.assertTrue(run(ratelimit.refresh_token_unused("abc", 60)))  # a session in use keeps working


class SignedInOnlyTests(unittest.TestCase):
    def test_lesson_content_is_refused_to_an_anonymous_caller(self):
        with self.assertRaises(HTTPException) as ctx:
            run(deps.ensure_lesson_open(None, None, SimpleNamespace(sort_order=1)))
        self.assertEqual((ctx.exception.status_code, ctx.exception.detail["code"]), (401, "unauthenticated"))
        run(deps.ensure_lesson_open(None, SimpleNamespace(role="learner"), SimpleNamespace(sort_order=1)))

    def test_a_new_recording_needs_an_access_token(self):
        spend = mock.AsyncMock()
        with mock.patch.object(audio.ratelimit, "spend", spend):
            for bad in (None, "Basic abc", "Bearer ", "Bearer " + security.create_refresh_token("x", "learner")):
                with self.assertRaises(HTTPException) as ctx:
                    run(audio._spend_word(request(authorization=bad)))
                self.assertEqual(ctx.exception.status_code, 401)
                with self.assertRaises(HTTPException):
                    run(audio._spend_lecture(request(authorization=bad)))
            spend.assert_not_awaited()
            run(audio._spend_lecture(request(authorization="Bearer " + security.create_access_token("x", "learner"))))
            spend.assert_awaited_once()


class PublishedSurfaceTests(unittest.TestCase):
    def test_production_publishes_no_route_list_and_cors_has_no_wildcard_pattern(self):
        import importlib

        from app import main
        from app.core.config import Settings, settings

        self.assertEqual(Settings.model_fields["CORS_ORIGIN_REGEX"].default, "")
        with mock.patch.object(settings, "ENVIRONMENT", "production"):
            prod = importlib.reload(main).app
            self.assertIsNone(prod.docs_url)
            self.assertIsNone(prod.openapi_url)
            self.assertIsNone(prod.redoc_url)
        importlib.reload(main)

    def test_the_refresh_cookie_is_httponly_strict_and_scoped_to_the_auth_routes(self):
        from fastapi import Response

        from app.api.routers import auth
        from app.core.config import settings

        profile = SimpleNamespace(id="11111111-1111-1111-1111-111111111111", role="learner")
        with mock.patch.object(settings, "ENVIRONMENT", "production"):
            response = Response()
            pair = auth._issue(response, profile)
        cookie = response.headers["set-cookie"].lower()
        self.assertIsNone(pair.refresh_token)  # never in the body in production
        for part in ("haru_rt=", "httponly", "secure", "samesite=strict", "path=/api/v1/auth"):
            self.assertIn(part, cookie)
        self.assertEqual(security.decode_access_token(pair.access_token)["sub"], profile.id)


if __name__ == "__main__":
    unittest.main()


class JourneySeenTests(unittest.TestCase):
    """What a learner was last shown of the journey is kept per account; the newer snapshot wins."""

    def test_a_snapshot_is_checked_and_an_older_one_does_not_replace_a_newer_one(self):
        from pydantic import ValidationError

        from app.models import Journey
        from app.schemas import JourneySeen
        from app.services import journey

        ok = JourneySeen(stage=2, missed=0, relics=["compass"], at=2000)
        self.assertEqual(ok.model_dump(mode="json")["stage"], 2)
        for bad in ({"stage": 9, "missed": 0}, {"stage": 1, "missed": 0, "note": "x"}, {"stage": 1, "missed": -1}):
            with self.assertRaises(ValidationError):
                JourneySeen(**bad)

        row = Journey(learner_id="11111111-1111-1111-1111-111111111111", stage=1, relics=[], sparkle=0)

        class Db:
            async def get(self, model, key):
                return row

            def add(self, obj):
                raise AssertionError("the row exists")

        run(journey.keep_seen(Db(), row.learner_id, {"stage": 2, "missed": 0, "at": 2000}))
        self.assertEqual(row.seen["stage"], 2)
        run(journey.keep_seen(Db(), row.learner_id, {"stage": 1, "missed": 3, "at": 1000}))  # an older device
        self.assertEqual(row.seen["stage"], 2)
        run(journey.keep_seen(Db(), row.learner_id, {"stage": 3, "missed": 0, "at": 3000}))
        self.assertEqual(row.seen["stage"], 3)

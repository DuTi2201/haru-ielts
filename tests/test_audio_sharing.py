"""Word / sentence recordings are shared and guarded.

- a word is filed under WHAT it says (text + voice + version), so the same word in another
  lesson or topic is one recording; the text voiced comes from the database, never the request;
- the public endpoints that start a paid generation spend from an hourly allowance (an existing
  recording is free), and a caller can no longer queue the same recording twice with its own
  Idempotency-Key.

No network, no Redis, no database: the allowance is checked against an in-memory Redis stand-in."""
import unicodedata
import unittest
import uuid
from types import SimpleNamespace
from unittest import mock

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

from app.api.routers import audio
from app.core import ratelimit
from app.schemas import CorpusAudioRequest, VocabAudioRequest
from app.services import audio_keys
from app.workers import tasks


def results(*values):
    out = []
    for v in values:
        res = mock.MagicMock()
        res.scalar_one_or_none.return_value = v
        out.append(res)
    return out


# ----------------------------------------------------------------- the keys --
class AudioKeyTests(unittest.TestCase):
    def test_the_same_word_has_the_same_key_whichever_lesson_asks(self):
        a = audio_keys.vocab_audio_key("학교", "ko-female-1", "v1")
        b = audio_keys.vocab_audio_key("학교", "ko-female-1", "v1")
        self.assertEqual(a, b)
        self.assertTrue(a.startswith("vt:"))

    def test_another_voice_or_version_is_another_recording(self):
        base = audio_keys.vocab_audio_key("학교", "ko-female-1", "v1")
        self.assertNotEqual(base, audio_keys.vocab_audio_key("학교", "ko-male-1", "v1"))
        self.assertNotEqual(base, audio_keys.vocab_audio_key("학교", "ko-female-1", "v2"))
        self.assertNotEqual(base, audio_keys.vocab_audio_key("학원", "ko-female-1", "v1"))

    def test_spelling_variants_of_one_word_share_a_key(self):
        composed = "한국어  "
        decomposed = unicodedata.normalize("NFD", "한국어")
        self.assertNotEqual(composed.strip(), decomposed)
        self.assertEqual(
            audio_keys.vocab_audio_key(composed, "ko-female-1", "v1"),
            audio_keys.vocab_audio_key(decomposed, "ko-female-1", "v1"),
        )
        self.assertEqual(audio_keys.speakable(" 안녕   하세요 "), "안녕 하세요")
        self.assertEqual(audio_keys.speakable(None), "")

    def test_the_old_key_is_still_known(self):
        self.assertEqual(audio_keys.vocab_legacy_key(12, "ko-female-1", "v1"), "12:ko-female-1:v1")


class RequestSchemaTests(unittest.TestCase):
    def test_the_client_need_not_send_the_text(self):
        self.assertIsNone(VocabAudioRequest().text_ko)
        self.assertEqual(VocabAudioRequest().voice, "en-female-1")
        self.assertEqual(VocabAudioRequest(text_ko="x", voice="ko-male-2").voice, "ko-male-2")
        self.assertEqual(CorpusAudioRequest().prompt_version, "v2")

    def test_only_known_voices_and_versions_are_accepted(self):
        with self.assertRaises(ValidationError):
            VocabAudioRequest(voice="anything-else")
        with self.assertRaises(ValidationError):
            VocabAudioRequest(prompt_version="v99")  # a new version string would dodge the cache
        with self.assertRaises(ValidationError):
            CorpusAudioRequest(prompt_version="v1")
        with self.assertRaises(ValidationError):
            CorpusAudioRequest(voice="ko-evil")


# ------------------------------------------------------------- the allowance --
class FakeRedis:
    """INCR / TTL / EXPIRE, enough for the fixed-window counters."""

    def __init__(self, fail=False):
        self.counts, self.ttls, self.fail = {}, {}, fail

    def pipeline(self):
        outer = self
        ops = []

        class Pipe:
            def incr(self, key):
                ops.append(("incr", key))

            def ttl(self, key):
                ops.append(("ttl", key))

            async def execute(self):
                if outer.fail:
                    raise ConnectionError("redis down")
                out = []
                for op, key in ops:
                    if op == "incr":
                        outer.counts[key] = outer.counts.get(key, 0) + 1
                        out.append(outer.counts[key])
                    else:
                        out.append(outer.ttls.get(key, -1))
                return out

        return Pipe()

    async def expire(self, key, seconds):
        self.ttls[key] = seconds


def req(forwarded=None, peer="10.0.0.9"):
    headers = {"x-forwarded-for": forwarded} if forwarded else {}
    return SimpleNamespace(headers=headers, client=SimpleNamespace(host=peer) if peer else None)


class ClientIpTests(unittest.TestCase):
    def test_the_address_our_proxy_saw_is_the_last_public_one(self):
        self.assertEqual(ratelimit.client_ip(req("8.8.4.4")), "8.8.4.4")
        # a caller can prepend addresses of its own; the proxy appends the real one
        self.assertEqual(ratelimit.client_ip(req("6.6.6.6, 8.8.4.4")), "8.8.4.4")

    def test_private_hops_and_garbage_are_skipped(self):
        self.assertEqual(ratelimit.client_ip(req("8.8.4.4, 10.1.2.3, not-an-ip")), "8.8.4.4")

    def test_without_a_forwarded_address_the_peer_is_used(self):
        self.assertEqual(ratelimit.client_ip(req(None, peer="203.0.113.7")), "203.0.113.7")
        self.assertEqual(ratelimit.client_ip(req("10.0.0.2", peer="203.0.113.7")), "203.0.113.7")
        self.assertEqual(ratelimit.client_ip(req(None, peer=None)), "unknown")


class SpendTests(unittest.IsolatedAsyncioTestCase):
    def use(self, fake):
        patcher = mock.patch.object(ratelimit, "async_redis", fake)
        patcher.start()
        self.addCleanup(patcher.stop)
        return fake

    async def test_a_client_can_spend_up_to_its_allowance_then_gets_429(self):
        fake = self.use(FakeRedis())
        for _ in range(3):
            await ratelimit.spend(req("8.8.4.4"), "word", per_client=3, overall=100)
        with self.assertRaises(HTTPException) as caught:
            await ratelimit.spend(req("8.8.4.4"), "word", per_client=3, overall=100)
        exc = caught.exception
        self.assertEqual(exc.status_code, 429)
        self.assertEqual(exc.detail["code"], "rate_limited")
        self.assertEqual(exc.headers["Retry-After"], str(ratelimit.WINDOW_SECONDS))
        self.assertEqual(fake.ttls["rl:word:ip:8.8.4.4"], ratelimit.WINDOW_SECONDS)

    async def test_another_client_has_an_allowance_of_its_own(self):
        self.use(FakeRedis())
        for _ in range(2):
            await ratelimit.spend(req("8.8.4.4"), "word", per_client=2, overall=100)
        await ratelimit.spend(req("1.1.1.1"), "word", per_client=2, overall=100)

    async def test_kinds_are_counted_apart(self):
        self.use(FakeRedis())
        await ratelimit.spend(req("8.8.4.4"), "word", per_client=1, overall=100)
        await ratelimit.spend(req("8.8.4.4"), "lecture", per_client=1, overall=100)

    async def test_everyone_together_has_a_ceiling_too(self):
        self.use(FakeRedis())
        await ratelimit.spend(req("8.8.4.4"), "word", per_client=5, overall=2)
        await ratelimit.spend(req("1.1.1.1"), "word", per_client=5, overall=2)
        with self.assertRaises(HTTPException) as caught:
            await ratelimit.spend(req("9.9.9.9"), "word", per_client=5, overall=2)
        self.assertEqual(caught.exception.status_code, 429)

    async def test_when_redis_is_down_listening_carries_on(self):
        self.use(FakeRedis(fail=True))
        await ratelimit.spend(req("8.8.4.4"), "word", per_client=1, overall=1)  # no exception


class OverTheWireTests(unittest.TestCase):
    """What the browser gets when the allowance is spent: a problem+json 429 that carries
    Retry-After (the shared exception handler used to drop the headers)."""

    def test_the_429_carries_retry_after_and_the_vietnamese_message(self):
        from fastapi import FastAPI
        from starlette.exceptions import HTTPException as StarletteHTTPException
        from starlette.testclient import TestClient

        from app.main import problem_json_handler

        app = FastAPI()
        app.add_exception_handler(StarletteHTTPException, problem_json_handler)

        @app.post("/spend")
        async def spend():
            fake = FakeRedis()
            fake.counts["rl:word:ip:8.8.4.4"] = 99
            with mock.patch.object(ratelimit, "async_redis", fake):
                await ratelimit.spend(req("8.8.4.4"), "word", per_client=1, overall=100)

        res = TestClient(app).post("/spend")
        self.assertEqual(res.status_code, 429)
        self.assertEqual(res.headers["content-type"], "application/problem+json")
        self.assertEqual(res.headers["retry-after"], str(ratelimit.WINDOW_SECONDS))
        self.assertEqual(res.json()["code"], "rate_limited")
        self.assertIn("audio", res.json()["detail"])


# ---------------------------------------------------------------- endpoints --
class WordEndpointBase(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        patcher = mock.patch.object(audio.ratelimit, "spend", mock.AsyncMock())
        self.spend = patcher.start()
        self.addCleanup(patcher.stop)

    def make_db(self, item, *executed):
        db = mock.MagicMock()
        db.get = mock.AsyncMock(return_value=item)
        db.execute = mock.AsyncMock(side_effect=results(*executed))
        db.add = mock.MagicMock()
        db.commit = mock.AsyncMock()
        db.flush = mock.AsyncMock()
        db.delete = mock.AsyncMock()

        async def refresh(j):
            j.id = uuid.UUID(int=9)
            j.status = j.status or "queued"

        db.refresh = mock.AsyncMock(side_effect=refresh)
        self.db = db
        return db

    def added_job(self):
        return self.db.add.call_args.args[0]


class VocabAudioEndpointTests(WordEndpointBase):
    WORD = SimpleNamespace(id=5, hangul="  학교 ")

    async def ask(self, item, *executed, body=None, vocab_id=5, headers=None):
        db = self.make_db(item, *executed)
        request = SimpleNamespace(headers=headers or {}, client=SimpleNamespace(host="8.8.4.4"))
        with mock.patch.object(audio.generate_vocab_audio, "delay") as delay:
            out = await audio.request_vocab_audio(vocab_id, body or VocabAudioRequest(), request, db)
        return out, delay

    async def test_a_new_word_is_voiced_from_the_database_under_the_words_key(self):
        out, delay = await self.ask(self.WORD, None, None, None, body=VocabAudioRequest(text_ko="무료 광고"))
        job_id, vid, text, voice, version, key = delay.call_args.args
        self.assertEqual(text, "학교")  # the stored word, not what the client sent
        self.assertEqual(key, audio_keys.vocab_audio_key("학교", "en-female-1", "v1"))
        self.assertEqual((vid, voice, version), ("5", "en-female-1", "v1"))
        self.spend.assert_awaited_once()
        self.assertEqual(out.status, "queued")

    async def test_the_same_word_in_another_lesson_asks_for_the_same_recording(self):
        _, first = await self.ask(self.WORD, None, None, None)
        _, second = await self.ask(SimpleNamespace(id=777, hangul="학교"), None, None, None, vocab_id=777)
        self.assertEqual(first.call_args.args[5], second.call_args.args[5])

    async def test_a_recording_that_exists_is_free_and_not_made_again(self):
        hit = SimpleNamespace(cache_key="vt:abc", duration_sec=2)
        out, delay = await self.ask(self.WORD, hit, None)
        delay.assert_not_called()
        self.spend.assert_not_awaited()
        job = self.added_job()
        self.assertEqual(job.status, "succeeded")
        self.assertEqual(job.result["opus_path"], "/api/v1/vocab-items/audio/vt:abc.opus")

    async def test_a_recording_made_before_the_change_is_still_found(self):
        legacy = SimpleNamespace(cache_key="5:ko-female-1:v1", duration_sec=3)
        out, delay = await self.ask(self.WORD, None, legacy, None)
        delay.assert_not_called()
        self.spend.assert_not_awaited()
        self.assertEqual(self.added_job().result["cache_key"], "5:ko-female-1:v1")

    async def test_a_callers_idempotency_key_cannot_queue_the_recording_again(self):
        await self.ask(self.WORD, None, None, None, headers={"Idempotency-Key": "fresh-every-time"})
        self.assertEqual(
            self.added_job().idempotency_key, audio_keys.vocab_audio_key("학교", "en-female-1", "v1")
        )

    async def test_a_finished_job_whose_recording_is_gone_is_made_again(self):
        stale = SimpleNamespace(status="succeeded")
        out, delay = await self.ask(self.WORD, None, None, stale)
        self.db.delete.assert_awaited_once_with(stale)
        delay.assert_called_once()

    async def test_an_unknown_word_is_404(self):
        with self.assertRaises(HTTPException) as caught:
            await self.ask(None, vocab_id=404)
        self.assertEqual(caught.exception.status_code, 404)
        self.spend.assert_not_awaited()

    async def test_a_word_with_no_text_is_404(self):
        with self.assertRaises(HTTPException) as caught:
            await self.ask(SimpleNamespace(id=1, hangul="   "))
        self.assertEqual(caught.exception.status_code, 404)

    async def test_when_the_allowance_is_spent_nothing_is_queued(self):
        self.spend.side_effect = HTTPException(429, detail="slow down")
        with self.assertRaises(HTTPException) as caught:
            await self.ask(self.WORD, None, None, None)
        self.assertEqual(caught.exception.status_code, 429)
        self.db.add.assert_not_called()


class CorpusAudioEndpointTests(WordEndpointBase):
    ITEM = SimpleNamespace(text_ko="  오늘 날씨가 좋아요 ")
    ID = str(uuid.UUID(int=1))

    async def ask(self, item, *executed, body=None, corpus_id=None):
        db = self.make_db(item, *executed)
        request = SimpleNamespace(headers={}, client=SimpleNamespace(host="8.8.4.4"))
        with mock.patch.object(audio.generate_corpus_audio, "delay") as delay:
            out = await audio.request_corpus_audio(corpus_id or self.ID, body or CorpusAudioRequest(), request, db)
        return out, delay

    async def test_the_sentence_voiced_is_the_stored_one(self):
        _, delay = await self.ask(self.ITEM, None, None, body=CorpusAudioRequest(text_ko="something else"))
        args = delay.call_args.args
        self.assertEqual(args[2], "오늘 날씨가 좋아요")
        self.assertEqual(self.added_job().idempotency_key, f"{self.ID}:en-female-1:v2")
        self.spend.assert_awaited_once()

    async def test_an_existing_recording_is_free(self):
        hit = SimpleNamespace(cache_key="k", duration_sec=1)
        _, delay = await self.ask(self.ITEM, hit, None)
        delay.assert_not_called()
        self.spend.assert_not_awaited()

    async def test_a_bad_or_unknown_sentence_id_is_404(self):
        for item, cid in ((None, self.ID), (self.ITEM, "not-a-uuid"), (SimpleNamespace(text_ko=""), self.ID)):
            with self.assertRaises(HTTPException) as caught:
                await self.ask(item, corpus_id=cid)
            self.assertEqual(caught.exception.status_code, 404)


class LectureAllowanceTests(unittest.IsolatedAsyncioTestCase):
    """A new lecture / dialogue spends from the (smaller) lecture allowance; a recording that
    exists does not."""

    async def test_only_a_missing_recording_spends(self):
        existing = SimpleNamespace(
            cache_key="k", opus_path="/o", aac_path="/a", duration_sec=1, script_text="t", timeline=None
        )
        for hit, expected in ((None, 1), (existing, 0)):
            db = mock.MagicMock()
            db.execute = mock.AsyncMock(side_effect=results(hit, None))
            db.add = mock.MagicMock()
            db.commit = mock.AsyncMock()
            db.flush = mock.AsyncMock()
            db.delete = mock.AsyncMock()

            async def refresh(j):
                j.id = uuid.UUID(int=4)
                j.status = j.status or "queued"

            db.refresh = mock.AsyncMock(side_effect=refresh)
            with mock.patch.object(audio.ratelimit, "spend", mock.AsyncMock()) as spend, mock.patch.object(
                audio.tts, "chirp_enabled", return_value=False
            ), mock.patch.object(audio.generate_content_podcast, "delay"):
                request = SimpleNamespace(headers={"Idempotency-Key": "mine"}, client=SimpleNamespace(host="8.8.4.4"))
                from app.schemas import PodcastRequest

                await audio._request_podcast(db, "lesson", "5", PodcastRequest(), request, [1], [2])
            self.assertEqual(spend.await_count, expected)
            self.assertNotEqual(db.add.call_args.args[0].idempotency_key, "mine")


# ------------------------------------------------------------------ worker --
class StoreWordAudioTests(unittest.TestCase):
    def setUp(self):
        for target in ("publish_job_event",):
            patcher = mock.patch.object(tasks, target)
            setattr(self, target, patcher.start())
            self.addCleanup(patcher.stop)
        self.jid = uuid.UUID(int=2)

    def run_store(self, db, make_row=None):
        tasks._store_word_audio(
            db,
            tasks.VocabItemAudio,
            self.jid,
            "vt:key",
            "학교",
            "ko-female-1",
            make_row or (lambda o, a, d: SimpleNamespace(opus=o, aac=a, dur=d)),
            "/api/v1/vocab-items/audio",
        )

    def db_with(self, *found):
        db = mock.MagicMock()
        res = []
        for f in found:
            r = mock.MagicMock()
            r.scalar_one_or_none.return_value = f
            res.append(r)
        db.execute.side_effect = res
        return db

    def final_event(self):
        return self.publish_job_event.call_args_list[-1].kwargs

    def test_a_recording_that_exists_is_reported_without_a_text_to_speech_call(self):
        existing = SimpleNamespace(duration_sec=4, cache_key="vt:key")
        with mock.patch.object(tasks.tts, "synthesize_korean_tts_chirp_first") as tts_call:
            self.run_store(self.db_with(existing))
        tts_call.assert_not_called()
        event = self.final_event()
        self.assertEqual(event["status"], "succeeded")
        self.assertEqual(event["result"]["opus_path"], "/api/v1/vocab-items/audio/vt:key.opus")

    def test_a_new_word_is_voiced_stored_and_reported(self):
        db = self.db_with(None)
        with mock.patch.object(tasks.tts, "synthesize_korean_tts_chirp_first", return_value=(b"o", b"a", 3)) as tts_call:
            self.run_store(db)
        tts_call.assert_called_once_with("학교", "ko-female-1")
        db.add.assert_called_once()
        db.commit.assert_called_once()
        self.assertEqual(self.final_event()["result"]["duration_sec"], 3)

    def test_losing_the_race_to_another_worker_is_still_a_success(self):
        winner = SimpleNamespace(duration_sec=5, cache_key="vt:key")
        db = self.db_with(None, winner)
        db.commit.side_effect = IntegrityError("insert", {}, Exception("duplicate key"))
        with mock.patch.object(tasks.tts, "synthesize_korean_tts_chirp_first", return_value=(b"o", b"a", 3)):
            self.run_store(db)
        db.rollback.assert_called_once()
        self.assertEqual(self.final_event()["status"], "succeeded")
        self.assertEqual(self.final_event()["result"]["duration_sec"], 5)

    def test_an_integrity_error_with_no_winner_is_a_real_failure(self):
        db = self.db_with(None, None)
        db.commit.side_effect = IntegrityError("insert", {}, Exception("other"))
        with mock.patch.object(tasks.tts, "synthesize_korean_tts_chirp_first", return_value=(b"o", b"a", 3)):
            with self.assertRaises(IntegrityError):
                self.run_store(db)


class VocabTaskKeyTests(unittest.TestCase):
    """The Celery task files the recording under the key the API gave it; a message queued
    before the change (no key) gets the old per-row key."""

    def run_task(self, *extra):
        captured = {}

        def fake_store(db, model, jid, cache_key, text, voice, make_row, prefix):
            captured["key"] = cache_key
            captured["row"] = make_row(b"o", b"a", 2)

        with mock.patch.object(tasks, "_store_word_audio", fake_store), mock.patch.object(
            tasks, "Session"
        ) as session, mock.patch.object(tasks, "publish_job_event"):
            session.return_value.__enter__.return_value = mock.MagicMock()
            tasks.generate_vocab_audio.run(str(uuid.UUID(int=1)), "5", "학교", "ko-female-1", "v1", *extra)
        return captured

    def test_the_key_from_the_api_is_used(self):
        got = self.run_task("vt:abc")
        self.assertEqual(got["key"], "vt:abc")
        self.assertEqual(got["row"].cache_key, "vt:abc")
        self.assertEqual(got["row"].vocab_item_id, 5)

    def test_an_old_queued_message_gets_the_old_key(self):
        self.assertEqual(self.run_task()["key"], "5:ko-female-1:v1")


if __name__ == "__main__":
    unittest.main()

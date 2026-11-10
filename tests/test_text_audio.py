"""Audio caching for any Korean text: check the store first, call Chirp only for a text nobody has
had voiced, decode the Base64 reply, file the bytes (Postgres row or a private bucket) and the row
that links the text to its file.

No network, no Redis, no database: Google, the bucket and the session are stand-ins, and the
credential used anywhere here is an obviously fake one."""
import base64
import io
import unittest
import unicodedata
import uuid
import wave
from types import SimpleNamespace
from unittest import mock

import httpx
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

from app.api.routers import audio
from app.models import TextAudio
from app.schemas import TextAudioRequest
from app.services import audio_keys, audio_store, google_tts, text_audio, tts
from app.workers import tasks

REAL_TOKEN = audio_store._token  # the tests below replace it on the module; this keeps the real one

FAKE_CRED = "fake-test-credential"


def results(*values):
    out = []
    for v in values:
        res = mock.MagicMock()
        res.scalar_one_or_none.return_value = v
        out.append(res)
    return out


def chirp_row(**changes):
    base = dict(
        cache_key="tx:abc", text_ko="안녕하세요", voice="ko-female-1", prompt_version="v1", provider="chirp",
        duration_sec=2, storage="db", opus_key=None, aac_key=None, opus_data=b"OPUS", aac_data=b"AAC",
    )
    return SimpleNamespace(**{**base, **changes})


# ------------------------------------------------------------------ the text --
class CheckTextTests(unittest.TestCase):
    def test_a_korean_sentence_is_cleaned_and_accepted(self):
        self.assertEqual(text_audio.check_text("  The weather   is nice today.  "), "The weather is nice today.")
        self.assertEqual(text_audio.check_text("Meet me at 3 pm!"), "Meet me at 3 pm!")

    def test_empty_text_is_refused(self):
        for bad in ("", "   ", None):
            with self.assertRaises(text_audio.TextNotSpeakable):
                text_audio.check_text(bad)

    def test_text_that_is_not_korean_is_refused(self):
        for bad in ("오늘 날씨가 좋아요.", "Hôm nay trời đẹp quá", "12345"):
            with self.assertRaises(text_audio.TextNotSpeakable, msg=bad):
                text_audio.check_text(bad)

    def test_a_text_over_the_cap_is_refused(self):
        with mock.patch.object(text_audio.settings, "TEXT_AUDIO_MAX_CHARS", 10):
            self.assertEqual(text_audio.check_text("abcdefghij"), "abcdefghij")
            with self.assertRaises(text_audio.TextNotSpeakable):
                text_audio.check_text("abcdefghijk")

    def test_the_request_accepts_only_the_known_voices_and_version(self):
        self.assertEqual(TextAudioRequest(text="Hello").voice, "en-female-1")
        with self.assertRaises(ValidationError):
            TextAudioRequest(text="Hello", voice="ko-evil")
        with self.assertRaises(ValidationError):
            TextAudioRequest(text="Hello", prompt_version="v99")  # a new version string would dodge the cache
        with self.assertRaises(ValidationError):
            TextAudioRequest(text="")


class KeyTests(unittest.TestCase):
    def test_the_same_text_voice_and_pace_have_the_same_key(self):
        a = audio_keys.text_audio_key("오늘 날씨가 좋아요", "ko-female-1", "gc3-iapetus-r85", "v1")
        self.assertEqual(a, audio_keys.text_audio_key("  오늘  날씨가 좋아요 ", "ko-female-1", "gc3-iapetus-r85", "v1"))
        self.assertTrue(a.startswith("tx:"))

    def test_spelling_variants_share_a_key(self):
        composed = "한국어를 공부해요"
        decomposed = unicodedata.normalize("NFD", composed)
        self.assertNotEqual(composed, decomposed)
        self.assertEqual(
            audio_keys.text_audio_key(composed, "ko-female-1", "s", "v1"),
            audio_keys.text_audio_key(decomposed, "ko-female-1", "s", "v1"),
        )

    def test_another_text_voice_pace_or_version_is_another_recording(self):
        base = audio_keys.text_audio_key("안녕", "ko-female-1", "gc3-iapetus-r85", "v1")
        for other in (
            audio_keys.text_audio_key("안녕!", "ko-female-1", "gc3-iapetus-r85", "v1"),
            audio_keys.text_audio_key("안녕", "ko-male-1", "gc3-iapetus-r85", "v1"),
            audio_keys.text_audio_key("안녕", "ko-female-1", "gc3-iapetus-r100", "v1"),
            audio_keys.text_audio_key("안녕", "ko-female-1", "gc3-iapetus-r85", "v2"),
        ):
            self.assertNotEqual(base, other)

    def test_the_pace_in_use_is_part_of_the_key_so_a_new_voice_is_recorded_again(self):
        with mock.patch.object(tts, "chirp_enabled", return_value=True), mock.patch.object(tts, "chirp_spec", return_value="gc3-a-r85"):
            first = text_audio.cache_key("안녕", "ko-female-1")
        with mock.patch.object(tts, "chirp_enabled", return_value=True), mock.patch.object(tts, "chirp_spec", return_value="gc3-b-r85"):
            second = text_audio.cache_key("안녕", "ko-female-1")
        with mock.patch.object(tts, "chirp_enabled", return_value=False):
            gemini = text_audio.cache_key("안녕", "ko-female-1")
        self.assertEqual(len({first, second, gemini}), 3)

    def test_the_paths_are_the_streaming_route(self):
        self.assertEqual(
            text_audio.paths("tx:abc"),
            {"opus_path": "/api/v1/audio/text/tx:abc.opus", "aac_path": "/api/v1/audio/text/tx:abc.aac"},
        )


class UsableTests(unittest.TestCase):
    def test_a_chirp_recording_plays_as_it_is(self):
        with mock.patch.object(tts, "chirp_enabled", return_value=True):
            self.assertTrue(text_audio.is_usable(chirp_row()))

    def test_no_row_is_not_usable(self):
        self.assertFalse(text_audio.is_usable(None))

    def test_a_gemini_fallback_is_made_again_while_chirp_is_configured(self):
        fallback = chirp_row(provider="gemini")
        with mock.patch.object(tts, "chirp_enabled", return_value=True):
            self.assertFalse(text_audio.is_usable(fallback))
        with mock.patch.object(tts, "chirp_enabled", return_value=False):
            self.assertTrue(text_audio.is_usable(fallback))


# ------------------------------------------------------------------- Google --
def wav_bytes(seconds=1, rate=24000):
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(b"\x00\x01" * rate * seconds)
    return buf.getvalue()


class ChirpBase64Tests(unittest.TestCase):
    def test_the_base64_audio_content_is_decoded_to_pcm(self):
        body = {"audioContent": base64.b64encode(wav_bytes()).decode("ascii")}
        resp = mock.MagicMock(status_code=200)
        resp.json.return_value = body
        with mock.patch.object(google_tts, "_auth_headers", return_value={"x": "y"}), mock.patch.object(
            google_tts.httpx, "post", return_value=resp
        ) as post:
            pcm, rate = google_tts.synthesize_pcm("안녕하세요")
        self.assertEqual(rate, 24000)
        self.assertEqual(len(pcm), 2 * 24000)
        sent = post.call_args.kwargs["json"]
        self.assertEqual(sent["input"], {"text": "안녕하세요"})
        self.assertEqual(sent["audioConfig"]["audioEncoding"], "LINEAR16")


class ProviderTests(unittest.TestCase):
    def test_chirp_is_named_when_it_voices_the_text(self):
        with mock.patch.object(google_tts, "is_configured", return_value=True), mock.patch.object(
            tts, "_synthesize_korean_chirp", return_value=(b"o", b"a", 3)
        ):
            self.assertEqual(tts.synthesize_korean_with_provider("안녕"), (b"o", b"a", 3, "chirp"))
            self.assertEqual(tts.synthesize_korean_tts_chirp_first("안녕"), (b"o", b"a", 3))

    def test_gemini_is_named_when_chirp_is_off_or_fails(self):
        with mock.patch.object(google_tts, "is_configured", return_value=False), mock.patch.object(
            tts, "synthesize_korean_tts", return_value=(b"g", b"h", 2)
        ):
            self.assertEqual(tts.synthesize_korean_with_provider("안녕"), (b"g", b"h", 2, "gemini"))
        with mock.patch.object(google_tts, "is_configured", return_value=True), mock.patch.object(
            tts, "_synthesize_korean_chirp", side_effect=RuntimeError("boom")
        ), mock.patch.object(tts, "synthesize_korean_tts", return_value=(b"g", b"h", 2)):
            self.assertEqual(tts.synthesize_korean_with_provider("안녕"), (b"g", b"h", 2, "gemini"))

    def test_when_both_fail_the_error_says_so(self):
        with mock.patch.object(google_tts, "is_configured", return_value=True), mock.patch.object(
            tts, "_synthesize_korean_chirp", side_effect=RuntimeError("chirp down")
        ), mock.patch.object(tts, "synthesize_korean_tts", side_effect=RuntimeError("gemini down")):
            with self.assertRaisesRegex(RuntimeError, "giọng dự phòng cũng lỗi"):
                tts.synthesize_korean_with_provider("안녕")


# --------------------------------------------------------------------- store --
class StoreSettingsTests(unittest.TestCase):
    def use(self, **values):
        for name, value in values.items():
            p = mock.patch.object(audio_store.settings, name, value)
            p.start()
            self.addCleanup(p.stop)

    def test_the_database_is_the_default(self):
        self.use(AUDIO_STORAGE="db", AUDIO_GCS_BUCKET="b", AUDIO_GCS_CREDENTIALS=FAKE_CRED)
        self.assertEqual(audio_store.backend(), "db")

    def test_gcs_needs_the_bucket_and_the_credential_as_well_as_the_switch(self):
        self.use(AUDIO_STORAGE="gcs", AUDIO_GCS_BUCKET="", AUDIO_GCS_CREDENTIALS=FAKE_CRED)
        self.assertEqual(audio_store.backend(), "db")
        self.use(AUDIO_STORAGE="gcs", AUDIO_GCS_BUCKET="haru-audio", AUDIO_GCS_CREDENTIALS="")
        self.assertEqual(audio_store.backend(), "db")
        self.use(AUDIO_STORAGE=" GCS ", AUDIO_GCS_BUCKET="haru-audio", AUDIO_GCS_CREDENTIALS=FAKE_CRED)
        self.assertEqual(audio_store.backend(), "gcs")

    def test_the_object_is_named_after_the_recordings_key(self):
        self.assertEqual(audio_store.object_key("tx:abc123", "opus"), "tts/tx/abc123.opus")


class GcsCallTests(unittest.TestCase):
    def setUp(self):
        for name, value in (("AUDIO_GCS_BUCKET", "haru-audio"), ("AUDIO_GCS_CREDENTIALS", FAKE_CRED)):
            p = mock.patch.object(audio_store.settings, name, value)
            p.start()
            self.addCleanup(p.stop)
        p = mock.patch.object(audio_store, "_token", return_value="fake-test-token")
        p.start()
        self.addCleanup(p.stop)

    def test_an_upload_is_a_media_upload_of_the_named_object(self):
        with mock.patch.object(audio_store.httpx, "post", return_value=mock.MagicMock(status_code=200)) as post:
            audio_store.gcs_put("tts/tx/abc.opus", b"DATA", "audio/ogg")
        url = post.call_args.args[0]
        self.assertEqual(url, "https://storage.googleapis.com/upload/storage/v1/b/haru-audio/o")
        self.assertEqual(post.call_args.kwargs["params"], {"uploadType": "media", "name": "tts/tx/abc.opus"})
        self.assertEqual(post.call_args.kwargs["content"], b"DATA")
        self.assertEqual(post.call_args.kwargs["headers"]["Content-Type"], "audio/ogg")
        self.assertEqual(post.call_args.kwargs["headers"]["Authorization"], "Bearer fake-test-token")

    def test_a_refused_upload_is_an_error_that_does_not_carry_the_token(self):
        bad = mock.MagicMock(status_code=403)
        bad.json.return_value = {"error": {"status": "PERMISSION_DENIED", "message": "caller does not have access"}}
        with mock.patch.object(audio_store.httpx, "post", return_value=bad):
            with self.assertRaises(audio_store.StoreError) as caught:
                audio_store.gcs_put("k", b"x", "audio/ogg")
        self.assertIn("PERMISSION_DENIED", str(caught.exception))
        self.assertNotIn("fake-test-token", str(caught.exception))

    def test_a_network_failure_is_a_store_error(self):
        with mock.patch.object(audio_store.httpx, "post", side_effect=httpx.ConnectTimeout("slow")):
            with self.assertRaises(audio_store.StoreError):
                audio_store.gcs_put("k", b"x", "audio/ogg")

    def test_a_download_asks_for_the_media_of_the_encoded_object_name(self):
        ok = mock.MagicMock(status_code=200, content=b"BYTES")
        with mock.patch.object(audio_store.httpx, "get", return_value=ok) as get:
            self.assertEqual(audio_store.gcs_get("tts/tx/abc.opus"), b"BYTES")
        self.assertEqual(
            get.call_args.args[0], "https://storage.googleapis.com/storage/v1/b/haru-audio/o/tts%2Ftx%2Fabc.opus"
        )
        self.assertEqual(get.call_args.kwargs["params"], {"alt": "media"})

    def test_a_missing_object_is_none_and_another_failure_is_an_error(self):
        with mock.patch.object(audio_store.httpx, "get", return_value=mock.MagicMock(status_code=404)):
            self.assertIsNone(audio_store.gcs_get("k"))
        with mock.patch.object(audio_store.httpx, "get", return_value=mock.MagicMock(status_code=500)):
            with self.assertRaises(audio_store.StoreError):
                audio_store.gcs_get("k")

    def test_a_credential_that_is_not_json_is_refused_without_echoing_it(self):
        self.assert_refused(FAKE_CRED)

    def test_json_that_is_not_a_service_account_is_refused_without_echoing_it(self):
        self.assert_refused('{"hello": "fake-test-secret"}')

    def assert_refused(self, credential):
        saved = audio_store._credentials, audio_store._credentials_raw
        self.addCleanup(lambda: setattr(audio_store, "_credentials", saved[0]))
        self.addCleanup(lambda: setattr(audio_store, "_credentials_raw", saved[1]))
        audio_store._credentials, audio_store._credentials_raw = None, ""
        with mock.patch.object(audio_store, "_token", REAL_TOKEN):
            with mock.patch.object(audio_store.settings, "AUDIO_GCS_CREDENTIALS", credential):
                with self.assertRaises(audio_store.StoreError) as caught:
                    audio_store._token()
        self.assertNotIn(credential, str(caught.exception))
        self.assertNotIn("fake-test-secret", str(caught.exception))


# ---------------------------------------------------------------- the filing --
class SaveTests(unittest.TestCase):
    PRODUCED = (b"OPUS", b"AAC", 4, "chirp")

    def db(self, *existing):
        db = mock.MagicMock()
        db.execute.side_effect = results(*existing)
        return db

    def test_in_the_database_the_row_holds_the_bytes(self):
        db = self.db(None)
        with mock.patch.object(audio_store, "backend", return_value="db"):
            row = text_audio.save(db, "tx:k", "안녕하세요", "ko-female-1", "v1", self.PRODUCED)
        db.add.assert_called_once_with(row)
        db.commit.assert_called_once()
        self.assertEqual((row.storage, row.opus_data, row.aac_data, row.opus_key), ("db", b"OPUS", b"AAC", None))
        self.assertEqual((row.text_ko, row.provider, row.duration_sec, row.opus_bytes, row.aac_bytes), ("안녕하세요", "chirp", 4, 4, 3))

    def test_in_the_bucket_the_row_holds_only_the_link(self):
        db = self.db(None)
        with mock.patch.object(audio_store, "backend", return_value="gcs"), mock.patch.object(audio_store, "gcs_put") as put:
            row = text_audio.save(db, "tx:k", "안녕하세요", "ko-female-1", "v1", self.PRODUCED)
        self.assertEqual(
            [c.args for c in put.call_args_list],
            [("tts/tx/k.opus", b"OPUS", "audio/ogg"), ("tts/tx/k.aac", b"AAC", "audio/aac")],
        )
        self.assertEqual((row.storage, row.opus_key, row.aac_key), ("gcs", "tts/tx/k.opus", "tts/tx/k.aac"))
        self.assertIsNone(row.opus_data)
        self.assertIsNone(row.aac_data)

    def test_when_the_bucket_fails_the_audio_is_kept_in_the_row(self):
        db = self.db(None)
        with mock.patch.object(audio_store, "backend", return_value="gcs"), mock.patch.object(
            audio_store, "gcs_put", side_effect=audio_store.StoreError("403")
        ):
            row = text_audio.save(db, "tx:k", "안녕", "ko-female-1", "v1", self.PRODUCED)
        self.assertEqual((row.storage, row.opus_data, row.opus_key), ("db", b"OPUS", None))

    def test_a_chirp_recording_replaces_a_gemini_fallback_in_place(self):
        old = chirp_row(provider="gemini", opus_data=b"OLD", aac_data=b"OLD")
        db = self.db(old)
        with mock.patch.object(audio_store, "backend", return_value="db"):
            row = text_audio.save(db, "tx:abc", "안녕하세요", "ko-female-1", "v1", self.PRODUCED)
        self.assertIs(row, old)
        db.add.assert_not_called()
        self.assertEqual((old.provider, old.opus_data, old.duration_sec), ("chirp", b"OPUS", 4))

    def test_a_fallback_never_replaces_anything(self):
        for existing in (chirp_row(), chirp_row(provider="gemini")):
            db = self.db(existing)
            row = text_audio.save(db, "tx:abc", "안녕", "ko-female-1", "v1", (b"G", b"H", 2, "gemini"))
            self.assertIs(row, existing)
            self.assertEqual(existing.opus_data, b"OPUS")
            db.commit.assert_not_called()

    def test_losing_the_race_to_a_second_worker_returns_its_row(self):
        winner = chirp_row()
        db = self.db(None, winner)
        db.commit.side_effect = IntegrityError("insert", {}, Exception("duplicate key"))
        with mock.patch.object(audio_store, "backend", return_value="db"):
            row = text_audio.save(db, "tx:abc", "안녕", "ko-female-1", "v1", self.PRODUCED)
        self.assertIs(row, winner)
        db.rollback.assert_called_once()

    def test_read_gets_the_bytes_from_the_row_or_from_the_bucket(self):
        self.assertEqual(text_audio.read(chirp_row(), "opus"), b"OPUS")
        self.assertEqual(text_audio.read(chirp_row(), "aac"), b"AAC")
        linked = chirp_row(storage="gcs", opus_key="o", aac_key="a", opus_data=None, aac_data=None)
        with mock.patch.object(audio_store, "gcs_get", return_value=b"FROM-BUCKET") as get:
            self.assertEqual(text_audio.read(linked, "aac"), b"FROM-BUCKET")
        get.assert_called_once_with("a")
        self.assertIsNone(text_audio.read(chirp_row(storage="gcs", opus_key=None, opus_data=None), "opus"))


# -------------------------------------------------------------------- worker --
class WorkerTests(unittest.TestCase):
    def run_task(self, existing, produced=None, usable=None):
        events = []
        session = mock.MagicMock()
        session.__enter__.return_value = session
        session.execute.side_effect = results(existing)
        saved = chirp_row(cache_key="tx:abc", duration_sec=4)
        with mock.patch.object(tasks, "Session", return_value=session), mock.patch.object(
            tasks, "publish_job_event", side_effect=lambda *a, **k: events.append(k)
        ), mock.patch.object(tasks.text_audio, "is_usable", return_value=usable), mock.patch.object(
            tasks.text_audio, "synthesize", return_value=produced or (b"O", b"A", 4, "chirp")
        ) as synth, mock.patch.object(tasks.text_audio, "save", return_value=saved) as save:
            tasks.generate_text_audio.run(str(uuid.UUID(int=3)), "안녕하세요", "ko-female-1", "v1", "tx:abc")
        return events, synth, save

    def test_a_recording_already_filed_is_reported_without_calling_google(self):
        events, synth, save = self.run_task(chirp_row(), usable=True)
        synth.assert_not_called()
        save.assert_not_called()
        self.assertEqual(events[-1]["status"], "succeeded")

    def test_a_new_text_is_voiced_once_filed_and_reported_with_its_paths(self):
        events, synth, save = self.run_task(None, usable=False)
        synth.assert_called_once_with("안녕하세요", "ko-female-1")
        save.assert_called_once()
        self.assertEqual(save.call_args.args[1:5], ("tx:abc", "안녕하세요", "ko-female-1", "v1"))
        done = events[-1]
        self.assertEqual(done["status"], "succeeded")
        self.assertEqual(done["result"]["opus_path"], "/api/v1/audio/text/tx:abc.opus")
        self.assertEqual(done["result"]["aac_path"], "/api/v1/audio/text/tx:abc.aac")
        self.assertEqual(done["result"]["duration_sec"], 4)

    def test_a_failure_is_published_as_retryable_and_raised(self):
        session = mock.MagicMock()
        session.__enter__.return_value = session
        session.execute.side_effect = results(None)
        events = []
        with mock.patch.object(tasks, "Session", return_value=session), mock.patch.object(
            tasks, "publish_job_event", side_effect=lambda *a, **k: events.append(k)
        ), mock.patch.object(tasks.text_audio, "is_usable", return_value=False), mock.patch.object(
            tasks.text_audio, "synthesize", side_effect=RuntimeError("both voices failed")
        ):
            with self.assertRaises(RuntimeError):
                tasks.generate_text_audio.run(str(uuid.UUID(int=3)), "안녕", "ko-female-1", "v1", "tx:abc")
        self.assertEqual(events[-1]["status"], "failed")
        self.assertTrue(events[-1]["error"]["retryable"])


# ---------------------------------------------------------------- endpoints --
class TextEndpointBase(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        patcher = mock.patch.object(audio.ratelimit, "spend", mock.AsyncMock())
        self.spend = patcher.start()
        self.addCleanup(patcher.stop)
        patcher = mock.patch.object(text_audio, "cache_key", side_effect=lambda t, v, ver="v1": audio_keys.text_audio_key(t, v, "spec", ver))
        patcher.start()
        self.addCleanup(patcher.stop)
        patcher = mock.patch.object(tts, "chirp_enabled", return_value=True)
        patcher.start()
        self.addCleanup(patcher.stop)

    def make_db(self, *executed):
        db = mock.MagicMock()
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


class RequestTextAudioTests(TextEndpointBase):
    PROFILE = SimpleNamespace(id=uuid.UUID(int=1))

    async def ask(self, *executed, body=None):
        db = self.make_db(*executed)
        request = SimpleNamespace(headers={}, client=SimpleNamespace(host="8.8.4.4"))
        with mock.patch.object(audio.generate_text_audio, "delay") as delay:
            out = await audio.request_text_audio(body or TextAudioRequest(text="  The weather  is nice today. "), request, db, self.PROFILE)
        return out, delay

    def key(self):
        return audio_keys.text_audio_key("The weather is nice today.", "en-female-1", "spec", "v1")

    async def test_a_new_text_is_queued_with_its_cleaned_text_and_spends_from_the_allowance(self):
        out, delay = await self.ask(None, None)
        job_id, text, voice, version, key = delay.call_args.args
        self.assertEqual((text, voice, version, key), ("The weather is nice today.", "en-female-1", "v1", self.key()))
        self.spend.assert_awaited_once()
        self.assertEqual(out.status, "queued")
        self.assertEqual(self.db.add.call_args.args[0].idempotency_key, self.key())

    async def test_a_text_already_filed_plays_at_once_for_free(self):
        hit = chirp_row(cache_key=self.key(), duration_sec=3)
        out, delay = await self.ask(hit, None)
        delay.assert_not_called()
        self.spend.assert_not_awaited()
        job = self.db.add.call_args.args[0]
        self.assertEqual(job.status, "succeeded")
        self.assertEqual(job.result["opus_path"], f"/api/v1/audio/text/{self.key()}.opus")
        self.assertEqual(job.result["duration_sec"], 3)

    async def test_the_same_text_from_another_device_asks_for_the_same_recording(self):
        _, first = await self.ask(None, None)
        _, second = await self.ask(None, None, body=TextAudioRequest(text="The weather is nice today."))
        self.assertEqual(first.call_args.args[4], second.call_args.args[4])

    async def test_a_gemini_fallback_is_voiced_again_while_chirp_is_on(self):
        fallback = chirp_row(cache_key=self.key(), provider="gemini")
        out, delay = await self.ask(fallback, None)
        delay.assert_called_once()
        self.spend.assert_awaited_once()

    async def test_a_finished_job_whose_recording_is_gone_is_made_again(self):
        stale = SimpleNamespace(status="succeeded")
        out, delay = await self.ask(None, stale)
        self.db.delete.assert_awaited_once_with(stale)
        delay.assert_called_once()

    async def test_a_text_that_is_not_korean_is_422_and_nothing_is_queued(self):
        for bad in ("오늘 날씨가 좋아요", "Xin chào các bạn"):
            with self.assertRaises(HTTPException) as caught:
                await self.ask(body=TextAudioRequest(text=bad))
            self.assertEqual(caught.exception.status_code, 422)
        self.spend.assert_not_awaited()

    async def test_when_the_allowance_is_spent_nothing_is_queued(self):
        self.spend.side_effect = HTTPException(429, detail="slow down")
        with self.assertRaises(HTTPException) as caught:
            await self.ask(None, None)
        self.assertEqual(caught.exception.status_code, 429)
        self.db.add.assert_not_called()


class StreamTextAudioTests(unittest.IsolatedAsyncioTestCase):
    def request(self, range_header=None):
        return SimpleNamespace(headers={"range": range_header} if range_header else {})

    def db(self, row):
        db = mock.MagicMock()
        db.execute = mock.AsyncMock(side_effect=results(row))
        return db

    async def test_a_recording_in_the_row_is_served_whole_or_by_range(self):
        row = chirp_row()
        res = await audio.stream_text_audio("tx:abc.opus", self.request(), self.db(row))
        self.assertEqual((res.status_code, res.body, res.media_type), (200, b"OPUS", "audio/ogg; codecs=opus"))
        self.assertIn("immutable", res.headers["cache-control"])
        res = await audio.stream_text_audio("tx:abc.aac", self.request("bytes=1-2"), self.db(row))
        self.assertEqual((res.status_code, res.body), (206, b"AC"))

    async def test_a_recording_in_the_bucket_is_fetched_when_played(self):
        row = chirp_row(storage="gcs", opus_key="o", aac_key="a", opus_data=None, aac_data=None)
        with mock.patch.object(audio_store, "gcs_get", return_value=b"FROM-BUCKET"):
            res = await audio.stream_text_audio("tx:abc.aac", self.request(), self.db(row))
        self.assertEqual(res.body, b"FROM-BUCKET")

    async def test_a_bucket_that_cannot_be_reached_is_503_not_a_wrong_answer(self):
        row = chirp_row(storage="gcs", opus_key="o", aac_key="a", opus_data=None, aac_data=None)
        with mock.patch.object(audio_store, "gcs_get", side_effect=audio_store.StoreError("down")):
            with self.assertRaises(HTTPException) as caught:
                await audio.stream_text_audio("tx:abc.opus", self.request(), self.db(row))
        self.assertEqual(caught.exception.status_code, 503)

    async def test_an_unknown_key_or_format_is_404(self):
        with self.assertRaises(HTTPException) as caught:
            await audio.stream_text_audio("tx:none.opus", self.request(), self.db(None))
        self.assertEqual(caught.exception.status_code, 404)
        with self.assertRaises(HTTPException) as caught:
            await audio.stream_text_audio("tx:abc.mp3", self.request(), self.db(None))
        self.assertEqual(caught.exception.status_code, 404)

    async def test_an_object_that_is_not_there_is_404(self):
        row = chirp_row(storage="gcs", opus_key="o", aac_key="a", opus_data=None, aac_data=None)
        with mock.patch.object(audio_store, "gcs_get", return_value=None):
            with self.assertRaises(HTTPException) as caught:
                await audio.stream_text_audio("tx:abc.opus", self.request(), self.db(row))
        self.assertEqual(caught.exception.status_code, 404)


class ModelTests(unittest.TestCase):
    def test_the_table_links_a_text_to_its_file(self):
        cols = TextAudio.__table__.c
        for name in ("cache_key", "text_ko", "provider", "storage", "opus_key", "aac_key", "opus_data", "aac_data"):
            self.assertIn(name, cols)
        self.assertEqual(TextAudio.__table__.schema, "audio")
        self.assertTrue(cols.cache_key.unique)


if __name__ == "__main__":
    unittest.main()

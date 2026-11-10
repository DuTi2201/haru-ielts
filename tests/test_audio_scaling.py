"""What keeps the VM small when many learners listen at once: long recordings go to the player as a
signed link into the bucket (not through this process), long voicing jobs take turns, and a lecture's
PCM is read from disk by ffmpeg.

No network and no database: the bucket, Redis and the sessions are stand-ins; the key is generated here."""
import json
import shutil
import subprocess
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest import mock
from urllib.parse import parse_qs, urlparse

import httpx
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from app.api.routers import audio
from app.services import audio_store, heavy_slot, tts

BUCKET = "haru-audio"


def service_account_json() -> str:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = key.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
    ).decode()
    return json.dumps(
        {
            "type": "service_account",
            "project_id": "p",
            "private_key_id": "k1",
            "private_key": pem,
            "client_email": "haru@p.iam.gserviceaccount.com",
            "client_id": "1",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    )


CREDENTIAL = service_account_json()  # one key for the module: generating one per test is slow


def bucket_on(test, *, redirect=True):
    for name, value in (
        ("AUDIO_STORAGE", "gcs"),
        ("AUDIO_GCS_BUCKET", BUCKET),
        ("AUDIO_GCS_CREDENTIALS", CREDENTIAL),
        ("AUDIO_REDIRECT_TO_GCS", redirect),
    ):
        p = mock.patch.object(audio_store.settings, name, value)
        p.start()
        test.addCleanup(p.stop)
    audio_store._check.update(ok=False, at=-1e9)  # no verdict yet
    test.addCleanup(lambda: audio_store._check.update(ok=False, at=-1e9))


def lecture_row(**changes):
    base = dict(
        id="r1", cache_key="podcast:lesson:33", storage="gcs", opus_key="lecture/podcast/lesson/33.opus",
        aac_key="lecture/podcast/lesson/33.aac", opus_data=None, aac_data=None, created_at=1,
    )
    return SimpleNamespace(**{**base, **changes})


class SignedUrlTests(unittest.TestCase):
    NOW = datetime(2026, 10, 26, 17, 12, 34, tzinfo=timezone.utc)

    def setUp(self):
        bucket_on(self)

    def test_the_link_names_the_object_and_is_aligned_to_the_half_hour(self):
        url = audio_store.gcs_signed_url("lecture/podcast/lesson/33.aac", now=self.NOW)
        parsed = urlparse(url)
        self.assertEqual((parsed.scheme, parsed.netloc), ("https", "storage.googleapis.com"))
        self.assertEqual(parsed.path, f"/{BUCKET}/lecture/podcast/lesson/33.aac")
        q = parse_qs(parsed.query)
        self.assertEqual(q["X-Goog-Date"], ["20261026T170000Z"])
        self.assertEqual(q["X-Goog-Expires"], ["7200"])
        self.assertEqual(q["X-Goog-Credential"], ["haru@p.iam.gserviceaccount.com/20261026/auto/storage/goog4_request"])
        # the same half hour, the same link (so a browser or proxy can reuse it)
        later = datetime(2026, 10, 26, 17, 29, 59, tzinfo=timezone.utc)
        self.assertEqual(url, audio_store.gcs_signed_url("lecture/podcast/lesson/33.aac", now=later))
        self.assertNotEqual(url, audio_store.gcs_signed_url("lecture/podcast/lesson/33.aac", now=later.replace(minute=31)))

    def test_it_is_exactly_what_googles_own_library_signs(self):
        try:
            from google.cloud.storage import _signing
            from google.oauth2 import service_account
        except ImportError:
            self.skipTest("google-cloud-storage is not installed (it is not a dependency of the app)")
        creds = service_account.Credentials.from_service_account_info(json.loads(CREDENTIAL))
        for key in ("lecture/podcast/lesson/33.aac", "lecture/podcast/lesson/35/ko-female-1/tpl-v2/5be2/gc3bi-iapetus-r85.opus"):
            reference = _signing.generate_signed_url_v4(
                creds,
                f"/{BUCKET}/{key}",
                expiration=7200,
                api_access_endpoint="https://storage.googleapis.com",
                method="GET",
                _request_timestamp="20261026T170000Z",
            )
            self.assertEqual(audio_store.gcs_signed_url(key, now=self.NOW), reference)

    def test_a_credential_that_cannot_sign_is_a_store_error(self):
        with mock.patch.object(audio_store.settings, "AUDIO_GCS_CREDENTIALS", "not json"):
            with self.assertRaises(audio_store.StoreError):
                audio_store.gcs_signed_url("k")


class SignedLinksWorkTests(unittest.TestCase):
    def setUp(self):
        bucket_on(self)

    def reply(self, status):
        return httpx.Response(status, request=httpx.Request("GET", "https://storage.googleapis.com/x"))

    def test_served_or_missing_object_proves_the_signing_is_right(self):
        for status in (200, 206, 404):
            audio_store._check.update(ok=False, at=-1e9)
            with mock.patch.object(audio_store.httpx, "get", return_value=self.reply(status)):
                self.assertTrue(audio_store._signed_links_work("u"), status)

    def test_a_refused_link_or_a_dead_network_means_serve_it_here(self):
        for outcome in (self.reply(403), self.reply(400), httpx.ConnectError("down")):
            audio_store._check.update(ok=False, at=-1e9)
            side = {"side_effect": outcome} if isinstance(outcome, Exception) else {"return_value": outcome}
            with mock.patch.object(audio_store.httpx, "get", **side):
                self.assertFalse(audio_store._signed_links_work("u"))

    def test_the_verdict_is_kept_for_a_while_not_asked_on_every_play(self):
        with mock.patch.object(audio_store.httpx, "get", return_value=self.reply(206)) as get:
            for _ in range(5):
                self.assertTrue(audio_store._signed_links_work("u"))
        self.assertEqual(get.call_count, 1)

    def test_a_failed_check_is_retried_soon_and_a_good_one_much_later(self):
        clock = [1000.0]
        with mock.patch.object(audio_store.time, "monotonic", lambda: clock[0]):
            with mock.patch.object(audio_store.httpx, "get", return_value=self.reply(403)) as get:
                self.assertFalse(audio_store._signed_links_work("u"))
                clock[0] += 60
                self.assertFalse(audio_store._signed_links_work("u"))
                self.assertEqual(get.call_count, 1)  # still inside the 2 minutes
                clock[0] += 70
            with mock.patch.object(audio_store.httpx, "get", return_value=self.reply(206)) as get:
                self.assertTrue(audio_store._signed_links_work("u"))
                self.assertEqual(get.call_count, 1)
                clock[0] += 10 * 60
                self.assertTrue(audio_store._signed_links_work("u"))
                self.assertEqual(get.call_count, 1)  # a good verdict lasts 15 minutes
                clock[0] += 6 * 60
                audio_store._signed_links_work("u")
                self.assertEqual(get.call_count, 2)


class RedirectDecisionTests(unittest.TestCase):
    def setUp(self):
        bucket_on(self)

    def test_a_recording_in_the_bucket_gets_a_link_when_the_bucket_accepts_it(self):
        with mock.patch.object(audio_store, "_signed_links_work", return_value=True):
            url = audio_store.signed_redirect_url(lecture_row(), "aac")
        self.assertIn("/lecture/podcast/lesson/33.aac?", url)
        with mock.patch.object(audio_store, "_signed_links_work", return_value=True):
            self.assertIn("/lecture/podcast/lesson/33.opus?", audio_store.signed_redirect_url(lecture_row(), "opus"))

    def test_otherwise_none_so_the_bytes_are_served_here(self):
        with mock.patch.object(audio_store, "_signed_links_work", return_value=False):
            self.assertIsNone(audio_store.signed_redirect_url(lecture_row(), "aac"))
        with mock.patch.object(audio_store, "_signed_links_work", return_value=True):
            self.assertIsNone(audio_store.signed_redirect_url(lecture_row(storage="db"), "aac"))
            self.assertIsNone(audio_store.signed_redirect_url(lecture_row(aac_key=None), "aac"))
            with mock.patch.object(audio_store.settings, "AUDIO_REDIRECT_TO_GCS", False):
                self.assertIsNone(audio_store.signed_redirect_url(lecture_row(), "aac"))
            with mock.patch.object(audio_store.settings, "AUDIO_GCS_CREDENTIALS", "not json"):
                self.assertIsNone(audio_store.signed_redirect_url(lecture_row(), "aac"))


class StreamLectureRedirectTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        bucket_on(self)

    def db(self, row):
        res = mock.MagicMock()
        res.scalar_one_or_none.return_value = row
        db = mock.MagicMock()
        db.execute = mock.AsyncMock(return_value=res)
        return db

    def request(self, range_header=None):
        return SimpleNamespace(headers={"range": range_header} if range_header else {})

    async def test_the_player_is_sent_to_the_bucket_and_the_bytes_are_never_read_here(self):
        with mock.patch.object(audio_store, "_signed_links_work", return_value=True), mock.patch.object(
            audio_store, "gcs_get"
        ) as read:
            res = await audio.stream_lecture_audio("podcast:lesson:33.aac", self.request("bytes=0-1"), self.db(lecture_row()))
        self.assertEqual(res.status_code, 302)
        self.assertTrue(res.headers["location"].startswith(f"https://storage.googleapis.com/{BUCKET}/lecture/podcast/lesson/33.aac?"))
        self.assertEqual(res.headers["cache-control"], "private, max-age=600")
        read.assert_not_called()

    async def test_when_the_bucket_refuses_the_link_the_bytes_are_served_as_before(self):
        audio_store._cache.clear()
        with mock.patch.object(audio_store, "_signed_links_work", return_value=False), mock.patch.object(
            audio_store, "gcs_get", return_value=b"0123456789"
        ):
            res = await audio.stream_lecture_audio("podcast:lesson:33.aac", self.request("bytes=2-4"), self.db(lecture_row()))
        self.assertEqual((res.status_code, res.body), (206, b"234"))

    async def test_a_recording_still_in_its_row_is_served_from_the_row(self):
        row = lecture_row(storage="db", opus_key=None, aac_key=None, opus_data=b"OPUS", aac_data=b"AAC")
        with mock.patch.object(audio_store, "_signed_links_work", return_value=True):
            res = await audio.stream_lecture_audio("podcast:lesson:33.opus", self.request(), self.db(row))
        self.assertEqual((res.status_code, res.body), (200, b"OPUS"))


class HeavySlotTests(unittest.TestCase):
    def lock(self, *, first, then=True):
        lock = mock.MagicMock()
        lock.acquire.side_effect = [first, then]
        return lock

    def test_a_free_slot_is_taken_and_given_back(self):
        lock = self.lock(first=True)
        waited = []
        with mock.patch.object(heavy_slot.sync_redis, "lock", return_value=lock):
            with heavy_slot.heavy_voicing_slot(lambda: waited.append(1)):
                pass
        self.assertEqual(waited, [])
        lock.release.assert_called_once()

    def test_a_busy_slot_tells_the_learner_once_then_waits_its_turn(self):
        lock = self.lock(first=False, then=True)
        waited = []
        with mock.patch.object(heavy_slot.sync_redis, "lock", return_value=lock):
            with heavy_slot.heavy_voicing_slot(lambda: waited.append(1)):
                pass
        self.assertEqual(waited, [1])
        self.assertEqual([c.kwargs.get("blocking") for c in lock.acquire.call_args_list], [False, True])
        lock.release.assert_called_once()

    def test_a_wait_that_runs_out_goes_ahead_and_does_not_release_a_lock_it_never_held(self):
        lock = self.lock(first=False, then=False)
        ran = []
        with mock.patch.object(heavy_slot.sync_redis, "lock", return_value=lock):
            with heavy_slot.heavy_voicing_slot():
                ran.append(1)
        self.assertEqual(ran, [1])
        lock.release.assert_not_called()

    def test_redis_being_down_never_stops_the_job(self):
        ran = []
        with mock.patch.object(heavy_slot.sync_redis, "lock", side_effect=ConnectionError("redis down")):
            with heavy_slot.heavy_voicing_slot():
                ran.append(1)
        self.assertEqual(ran, [1])

    def test_the_slot_is_released_when_the_job_fails_and_the_error_is_not_swallowed(self):
        lock = self.lock(first=True)
        with mock.patch.object(heavy_slot.sync_redis, "lock", return_value=lock):
            with self.assertRaises(ValueError):
                with heavy_slot.heavy_voicing_slot():
                    raise ValueError("boom")
        lock.release.assert_called_once()

    def test_a_lock_that_expired_meanwhile_does_not_hide_the_result(self):
        lock = self.lock(first=True)
        lock.release.side_effect = RuntimeError("lock no longer owned")
        with mock.patch.object(heavy_slot.sync_redis, "lock", return_value=lock):
            with heavy_slot.heavy_voicing_slot():
                pass


@unittest.skipUnless(shutil.which("ffmpeg"), "ffmpeg is not installed")
class TranscodeFromFileTests(unittest.TestCase):
    RATE = 24000

    def tone(self, seconds):
        cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i", f"sine=frequency=440:duration={seconds}:sample_rate={self.RATE}",
               "-f", "s16le", "-ac", "1", "-"]
        return subprocess.run(cmd, capture_output=True, check=True).stdout

    def test_a_file_gives_the_same_recordings_as_the_bytes(self):
        import tempfile

        pcm = self.tone(3)
        opus_b, aac_b, dur_b = tts.transcode_pcm(pcm, self.RATE)
        with tempfile.TemporaryFile() as f:
            f.write(pcm)
            f.flush()
            opus_f, aac_f, dur_f = tts.transcode_pcm_file(f, len(pcm), self.RATE)
        self.assertEqual((dur_f, opus_f[:4], aac_f[:2]), (dur_b, b"OggS", aac_b[:2]))
        self.assertEqual((len(opus_f), len(aac_f)), (len(opus_b), len(aac_b)))

    def test_an_empty_file_is_refused(self):
        import tempfile

        with tempfile.TemporaryFile() as f:
            with self.assertRaises(RuntimeError):
                tts.transcode_pcm_file(f, 0, self.RATE)

    def speechlike(self, seconds):
        """Pink noise with a syllable-rate tremolo: a pure tone is too easy for the encoder to show a
        difference between bitrates."""
        cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i",
               f"anoisesrc=d={seconds}:c=pink:r={self.RATE}:a=0.5,tremolo=f=4:d=0.9,lowpass=f=4000",
               "-f", "s16le", "-ac", "1", "-"]
        return subprocess.run(cmd, capture_output=True, check=True).stdout

    def test_aac_is_64k_which_is_smaller_than_the_old_96k(self):
        pcm = self.speechlike(20)
        _o, aac, _d = tts.transcode_pcm(pcm, self.RATE)
        old = tts._run_ffmpeg(pcm, self.RATE, codec_args=["-c:a", "aac", "-b:a", "96k", "-f", "adts"])
        self.assertLess(len(aac), len(old) * 0.75)

    def test_a_stuck_ffmpeg_is_a_transcode_error_with_a_clean_message(self):
        pcm = self.tone(1)

        def stuck(*args, **kwargs):
            raise subprocess.TimeoutExpired(args[0], kwargs["timeout"])

        with mock.patch.object(tts.subprocess, "run", stuck):
            with self.assertRaises(tts.TranscodeError) as caught:
                tts.transcode_pcm(pcm, self.RATE)
        self.assertNotIn("ffmpeg', '-hide_banner", str(caught.exception))

    def test_the_time_allowed_grows_with_the_recording(self):
        self.assertEqual(tts._ffmpeg_timeout(self.RATE * 2 * 5, self.RATE), 120.0)
        self.assertAlmostEqual(tts._ffmpeg_timeout(self.RATE * 2 * 1800, self.RATE), 1830.0)


if __name__ == "__main__":
    unittest.main()

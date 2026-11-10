"""The home page's Korean lines: recorded once, then only read back (app/api/routers/audio.py
landing_audio_paths, app/services/landing_audio.py)."""
import unittest
from types import SimpleNamespace
from unittest import mock

from sqlalchemy.exc import IntegrityError

from app.api.routers import audio
from app.services import landing_audio, text_audio

TEXTS = landing_audio.LANDING_TEXTS


def recorded(*texts):
    """The first query: the recordings already filed (one SELECT ... IN for every text)."""
    r = mock.MagicMock()
    r.scalars.return_value.all.return_value = [
        SimpleNamespace(cache_key=text_audio.cache_key(t, landing_audio.VOICE), provider="chirp") for t in texts
    ]
    return r


def job(value):
    r = mock.MagicMock()
    r.scalar_one_or_none.return_value = value
    return r


class LandingAudioTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        patcher = mock.patch.object(audio, "generate_text_audio")
        self.task = patcher.start()
        self.addCleanup(patcher.stop)

    def db(self, *results, commit_error=None):
        db = mock.MagicMock()
        db.execute = mock.AsyncMock(side_effect=list(results))
        db.add = mock.MagicMock()
        db.delete = mock.AsyncMock()
        db.flush = mock.AsyncMock()
        db.commit = mock.AsyncMock(side_effect=commit_error)
        db.rollback = mock.AsyncMock()
        db.refresh = mock.AsyncMock()
        return db

    async def test_every_text_is_korean_unique_and_within_the_cap(self):
        self.assertEqual(len(set(TEXTS)), len(TEXTS))
        for t in TEXTS:
            self.assertEqual(text_audio.check_text(t), t)
            self.assertNotRegex(t, "[㉠㉡]")  # a voice cannot read a blank

    async def test_recorded_texts_are_only_read_and_cached(self):
        db = self.db(recorded(*TEXTS))
        response = SimpleNamespace(headers={})
        out = await audio.landing_audio_paths(response, db)
        self.assertEqual([i["status"] for i in out["items"]], ["ready"] * len(TEXTS))
        self.assertEqual([i["text"] for i in out["items"]], list(TEXTS))
        key = text_audio.cache_key(TEXTS[0], landing_audio.VOICE)
        self.assertEqual(out["items"][0]["aac_path"], f"/api/v1/audio/text/{key}.aac")
        self.assertIn("max-age", response.headers["Cache-Control"])
        self.assertEqual(db.execute.await_count, 1)  # one query, whatever the number of texts
        self.task.delay.assert_not_called()
        db.add.assert_not_called()

    async def test_a_missing_recording_is_queued_once(self):
        db = self.db(recorded(*TEXTS[1:]), job(None))
        response = SimpleNamespace(headers={})
        out = await audio.landing_audio_paths(response, db)
        self.assertEqual(out["items"][0], {"text": TEXTS[0], "status": "pending"})
        self.assertEqual(response.headers["Cache-Control"], "no-store")
        self.task.delay.assert_called_once()
        self.assertEqual(self.task.delay.call_args.args[1], TEXTS[0])

    async def test_a_job_already_running_is_not_queued_again(self):
        running = SimpleNamespace(status="running", updated_at=None, created_at=None)
        with mock.patch.object(audio.job_events, "abandoned", return_value=False):
            db = self.db(recorded(*TEXTS[1:]), job(running))
            await audio.landing_audio_paths(SimpleNamespace(headers={}), db)
        self.task.delay.assert_not_called()
        db.add.assert_not_called()

    async def test_two_visitors_at_once_make_one_job(self):
        db = self.db(recorded(*TEXTS[1:]), job(None), commit_error=IntegrityError("x", {}, Exception()))
        out = await audio.landing_audio_paths(SimpleNamespace(headers={}), db)
        self.assertEqual(out["items"][0]["status"], "pending")
        db.rollback.assert_awaited_once()
        self.task.delay.assert_not_called()

    async def test_a_queue_that_is_down_does_not_break_the_page(self):
        self.task.delay.side_effect = ConnectionError("redis down")
        db = self.db(recorded(*TEXTS[1:]), job(None))
        out = await audio.landing_audio_paths(SimpleNamespace(headers={}), db)
        self.assertEqual(out["items"][0]["status"], "pending")


if __name__ == "__main__":
    unittest.main()

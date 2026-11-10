"""Learning events: ids and numbers only, a daily cap, clocks far off filed at arrival."""
import asyncio
import unittest
import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest import mock

from pydantic import ValidationError

from app.api.routers import learning_events as le


def _db(sent_today: int):
    db = mock.MagicMock()
    res = mock.MagicMock()
    res.scalar_one.return_value = sent_today
    db.execute = mock.AsyncMock(return_value=res)
    db.commit = mock.AsyncMock()
    return db


class EventInTests(unittest.TestCase):
    def test_only_known_keys_and_plain_values_are_kept(self):
        e = le.EventIn(
            type="step_abandon",
            value=42,
            payload={"lesson_id": 32, "step": "grammar", "answer_text": "제가 쓴 문장", "nested": {"a": 1}, "ok": True},
        )
        self.assertEqual(e.payload, {"lesson_id": 32, "step": "grammar"})

    def test_long_text_is_cut(self):
        e = le.EventIn(type="first_try", value=1, payload={"question_id": "x" * 500})
        self.assertEqual(len(e.payload["question_id"]), le.MAX_TEXT)

    def test_an_unknown_type_is_refused(self):
        with self.assertRaises(ValidationError):
            le.EventIn(type="keystroke", value=1)

    def test_a_batch_is_one_to_fifty(self):
        with self.assertRaises(ValidationError):
            le.EventBatchIn(events=[])
        with self.assertRaises(ValidationError):
            le.EventBatchIn(events=[le.EventIn(type="audio_rate", value=1)] * 51)


class RecordTests(unittest.TestCase):
    def run_record(self, events, sent_today=0):
        db = _db(sent_today)
        profile = SimpleNamespace(id=uuid.uuid4())
        out = asyncio.run(le.record_events(le.EventBatchIn(events=events), db, profile))
        return out, [c.args[0] for c in db.add.call_args_list]

    def test_events_are_filed_with_their_skill(self):
        out, rows = self.run_record(
            [le.EventIn(type="session_start", payload={"lesson_id": 3}), le.EventIn(type="audio_seek", value=-10)]
        )
        self.assertEqual(out, {"kept": 2})
        self.assertEqual([r.skill for r in rows], ["lesson", "lecture"])

    def test_the_daily_cap_drops_the_rest(self):
        out, rows = self.run_record([le.EventIn(type="first_try", value=1)] * 5, sent_today=le.MAX_PER_DAY - 2)
        self.assertEqual(out, {"kept": 2})
        self.assertEqual(len(rows), 2)

    def test_a_clock_far_off_is_filed_at_arrival(self):
        far = datetime.now(timezone.utc) - timedelta(days=30)
        _, rows = self.run_record([le.EventIn(type="audio_rate", value=0.8, at=far)])
        self.assertLess(abs((datetime.now(timezone.utc) - rows[0].occurred_at).total_seconds()), 60)


if __name__ == "__main__":
    unittest.main()

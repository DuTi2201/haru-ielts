"""The database side of the competency record, the mixed review and the competency report
(app.services.competency_db, app.api.routers.competency) — against mocked sessions."""
import unittest
import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest import mock

from fastapi import HTTPException

from app.api.routers import competency as router
from app.models import GrammarCompetency
from app.services import competency, competency_db

NOW = datetime(2026, 10, 9, 12, 0, tzinfo=timezone.utc)
LEARNER = uuid.uuid4()


def rows(value, *, scalars=False):
    res = mock.MagicMock()
    if scalars:
        res.scalars.return_value.all.return_value = value
    else:
        res.all.return_value = value
    return res


def db_with(*executes):
    db = mock.MagicMock()
    db.execute = mock.AsyncMock(side_effect=list(executes))
    db.add = mock.MagicMock()
    db.get = mock.AsyncMock()
    return db


class RecordOutcomesTests(unittest.IsolatedAsyncioTestCase):
    async def test_a_new_card_gets_a_row_with_the_first_outcome(self):
        db = db_with(rows([], scalars=True))
        await competency_db.record_outcomes(db, LEARNER, [5, 5, 3], 1, True)
        added = [c.args[0] for c in db.add.call_args_list]
        self.assertEqual(sorted(a.grammar_id for a in added), [3, 5])  # one row per card, not per mention
        self.assertTrue(all(isinstance(a, GrammarCompetency) and a.history == {"1": [1]} for a in added))

    async def test_an_existing_row_keeps_its_history_and_gains_the_outcome(self):
        row = SimpleNamespace(grammar_id=5, history={"0": [1], "1": [1]}, updated_at=None)
        db = db_with(rows([row], scalars=True))
        await competency_db.record_outcomes(db, LEARNER, [5], 1, False)
        db.add.assert_not_called()
        self.assertEqual(row.history, {"0": [1], "1": [1, 0]})
        self.assertIsNotNone(row.updated_at)

    async def test_nothing_is_read_or_written_without_cards(self):
        db = db_with()
        await competency_db.record_outcomes(db, LEARNER, [], 0, True)
        db.execute.assert_not_called()
        db.add.assert_not_called()


class CardStatesTests(unittest.IsolatedAsyncioTestCase):
    async def test_cards_carry_level_difficulty_memory_and_history(self):
        due_at = NOW - timedelta(days=2)
        state = SimpleNamespace(
            item_id=11, strength=0.3, reps=1, lapses=0, ease=2.3, interval_days=1.0, due_at=due_at, introduced_at=NOW - timedelta(days=5)
        )
        comp = SimpleNamespace(grammar_id=11, history={"0": [1], "1": [0, 0]})
        db = db_with(
            rows([(11, "V + -고 싶다", 1, "kiip-2", None, None), (12, "A + -네요", 2, None, "recognize", None)]),
            rows([state], scalars=True),
            rows([comp], scalars=True),
        )
        out = await competency_db.card_states(db, LEARNER, NOW)
        a, b = out[11], out[12]
        self.assertEqual((a.difficulty, a.use_level, a.in_srs, a.due), (2, "produce", True, True))
        self.assertEqual(a.overdue_since, due_at)
        self.assertEqual(a.history, {"0": [1], "1": [0, 0]})
        self.assertEqual((b.difficulty, b.use_level, b.in_srs, b.history), (3, "recognize", False, {}))  # the card's own level wins
        self.assertIsNone(b.overdue_since)

    async def test_no_cards_means_no_further_queries(self):
        db = db_with(rows([]))
        self.assertEqual(await competency_db.card_states(db, LEARNER, NOW), {})
        self.assertEqual(db.execute.await_count, 1)


GRAMMAR = {
    "V + -고 싶다": {"pattern": "V + -고 싶다", "lesson_slug": "bai-a", "lesson_order": 1, "tier": "core", "use_level": "produce"},
}
BUILD = {"id": "BO1", "type": "build_order", "rung": 1, "tiles": ["a", "b"], "answers": ["a b"], "grammar": ["V + -고 싶다"]}
FILL = {"id": "BF1", "type": "write_fill", "rung": 2, "grammar": ["V + -고 싶다"], "blanks": [{"id": "a"}]}


class MixEndpointTests(unittest.IsolatedAsyncioTestCase):
    def db(self, cards_results=(), lesson_exists=True, order=(1, 2)):
        db = db_with(
            rows(list(order), scalars=True),
            rows(
                [
                    (1, "Bài A", "lesson", [BUILD, FILL], GRAMMAR),
                    (2, "Bài B", "lesson", [], {}),
                    (3, "Ôn tập", "review", [BUILD], GRAMMAR),
                ]
            ),
            rows([(100, "V + -고 싶다", "bai-a")]),
            rows(list(cards_results)),
            rows([("bai-a", 1)]),
        )
        db.get.return_value = SimpleNamespace(id=2) if lesson_exists else None
        return db

    async def call(self, db, cards, **kw):
        with mock.patch.object(router.competency_db, "card_states", mock.AsyncMock(return_value=cards)):
            return await router.get_mix(2, db, SimpleNamespace(id=LEARNER), **{"limit": 8, **kw})

    async def test_an_unknown_lesson_is_a_404(self):
        db = self.db(lesson_exists=False)
        with self.assertRaises(HTTPException) as ctx:
            await self.call(db, {})
        self.assertEqual(ctx.exception.status_code, 404)

    async def test_a_lesson_outside_the_curriculum_order_is_a_404(self):
        with self.assertRaises(HTTPException) as ctx:
            await self.call(self.db(order=(1, 3)), {})
        self.assertEqual(ctx.exception.status_code, 404)

    async def test_a_due_card_brings_its_exercise_with_the_card_info_and_the_lesson_to_answer_in(self):
        card = competency.CardState(
            id=100, pattern="V + -고 싶다", lesson_id=1, in_srs=True, due=True, overdue_since=NOW - timedelta(days=1),
            history={"1": [1, 1]},
        )
        out = await self.call(self.db(), {100: card})
        self.assertEqual(out.lesson_id, 2)
        self.assertEqual(out.pool, 2)  # the review lesson and the empty one add nothing
        self.assertEqual(out.by_reason, {"due": 1, "new": 1})  # the rest is filled with a question not done yet
        item = out.items[0]
        self.assertEqual((item.lesson_id, item.lesson_title, item.reason, item.rung), (1, "Bài A", "due", 2))  # level 1 is solid: one rung up
        self.assertEqual(item.exercise["id"], "BF1")
        self.assertEqual(item.grammar["V + -고 싶다"]["lesson_id"], 1)
        self.assertNotIn("lesson_order", item.grammar["V + -고 싶다"])

    async def test_a_card_the_learner_has_not_met_gives_an_empty_review(self):
        card = competency.CardState(id=100, pattern="V + -고 싶다", lesson_id=1)
        out = await self.call(self.db(), {100: card})
        self.assertEqual((out.items, out.by_reason), ([], {}))

    async def test_a_wrong_answer_comes_back_when_the_card_is_not_due(self):
        card = competency.CardState(id=100, pattern="V + -고 싶다", lesson_id=1, in_srs=True)
        out = await self.call(self.db(cards_results=[(1, "BO1", False)]), {100: card})
        self.assertEqual([(i.reason, i.exercise["id"]) for i in out.items], [("wrong", "BO1"), ("new", "BF1")])


class ReportEndpointTests(unittest.IsolatedAsyncioTestCase):
    def db(self, placement=None):
        return db_with(
            rows([(1, "Bài A", "lesson"), (2, "Bài B", "lesson"), (3, "Ôn tập", "review"), (4, "Bài chưa học", "lesson")]),
            rows([(1, 10, "Sinh hoạt"), (2, 10, "Sinh hoạt"), (3, 10, "Sinh hoạt"), (1, 11, "Quan hệ")]),
            mock.MagicMock(**{"scalar_one_or_none.return_value": placement}),
        )

    async def call(self, db, cards):
        with mock.patch.object(router.competency_db, "card_states", mock.AsyncMock(return_value=cards)):
            return await router.get_my_competency(db, SimpleNamespace(id=LEARNER))

    async def test_topics_list_lessons_in_curriculum_order_and_skip_review_lessons(self):
        cards = {
            1: competency.CardState(id=1, pattern="A", lesson_id=1, in_srs=True, history={"0": [1], "1": [1]}),
            2: competency.CardState(id=2, pattern="B", lesson_id=2),
            3: competency.CardState(id=3, pattern="C", lesson_id=3, in_srs=True),
        }
        out = await self.call(self.db(), cards)
        self.assertEqual([t.topic for t in out.topics], ["Sinh hoạt"])  # lesson 3 is a review lesson, 4 has no topic row but no cards either
        topic = out.topics[0]
        self.assertEqual([(lc.lesson_id, lc.summary.unseen) for lc in topic.lessons], [(1, 0), (2, 1)])
        self.assertEqual((topic.summary.cards, topic.summary.studying, topic.summary.unseen), (2, 0, 1))  # card 1 is at level 1, so not merely "studying"
        self.assertEqual(topic.summary.by_level["1"], 1)
        self.assertEqual(out.rungs["0"], "Nhận ra")
        self.assertIsNone(out.placement)

    async def test_no_progress_gives_an_empty_report(self):
        out = await self.call(self.db(), {})
        self.assertEqual(out.topics, [])

    async def test_the_latest_placement_is_included(self):
        placement = SimpleNamespace(
            taken_at=NOW,
            summary={
                "score": 9, "total": 12, "known": ["A", "B"], "unknown": ["C"], "start_rung": 1, "start_label": "Xếp câu",
                "start_lesson_id": 1, "by_rung": {"0": {"right": 3, "total": 3}},
            },
        )
        out = await self.call(self.db(placement=placement), {})
        self.assertEqual((out.placement.score, out.placement.total, out.placement.start_rung), (9, 12, 1))


if __name__ == "__main__":
    unittest.main()

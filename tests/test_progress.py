"""Progress logic: which lesson a learner sees next (pure function), and the
routes that use it — /progress/reviews rejects unknown items, /me/plan and the
lesson picker (/lessons) follow the learner's own progress. DB session is
faked (no Postgres)."""
import re
import unittest
import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest import mock

from fastapi import HTTPException

from app.api import deps
from app.api.routers import content
from app.models import ErrorLog, GrammarPoint, ItemState, VocabItem
from app.schemas import ItemStateReviewRequest
from app.services.progress import MASTERY_THRESHOLD, count_mastered, is_mastered, pick_next_lesson, resume_step

NOW = datetime(2026, 9, 30, 12, 0, tzinfo=timezone.utc)


def lessons():
    return {
        1: [("vocab_item", 1), ("vocab_item", 2), ("grammar_point", 1)],
        2: [("vocab_item", 3), ("vocab_item", 4)],
        3: [("vocab_item", 5)],
    }


class MasteryTests(unittest.TestCase):
    def test_threshold_tolerates_float_accumulation(self):
        strength = 0.0
        for _ in range(4):  # four correct nudges of +0.2
            strength += 0.2
        self.assertTrue(is_mastered(strength))
        self.assertTrue(is_mastered(MASTERY_THRESHOLD))
        self.assertFalse(is_mastered(0.6))
        self.assertFalse(is_mastered(None))


class PickNextLessonTests(unittest.TestCase):
    def test_new_learner_starts_at_first_lesson(self):
        got = pick_next_lesson(lessons(), {})
        self.assertEqual((got.lesson_id, got.total, got.mastered), (1, 3, 0))

    def test_a_lesson_of_practice_only_comes_first_until_its_check_is_answered(self):
        # Bảng chữ cái (id 0): no words or cards, only its end check of 20 questions
        with_hangul = {0: [], **lessons()}
        got = pick_next_lesson(with_hangul, {}, order=[0, 1, 2], practice={0: (0, 20)})
        self.assertEqual((got.lesson_id, got.total, got.practice_total), (0, 0, 20))
        got = pick_next_lesson(with_hangul, {}, order=[0, 1, 2], practice={0: (20, 20)})
        self.assertEqual(got.lesson_id, 1)
        # a lesson with nothing at all is still skipped
        self.assertEqual(pick_next_lesson({0: [], **lessons()}, {}, order=[0, 1, 2]).lesson_id, 1)

    def test_finished_lesson_moves_learner_on(self):
        states = {k: (0.8, NOW) for k in lessons()[1]}
        got = pick_next_lesson(lessons(), states)
        self.assertEqual(got.lesson_id, 2)

    def test_resumes_a_half_done_lesson_and_counts_mastered(self):
        # the grammar card was never marked: the lesson is not studied yet
        states = {("vocab_item", 1): (1.0, NOW), ("vocab_item", 2): (0.4, NOW)}
        got = pick_next_lesson(lessons(), states)
        self.assertEqual((got.lesson_id, got.mastered, got.met, got.total), (1, 1, 2, 3))

    def test_a_lesson_gone_through_once_moves_the_learner_on_before_it_is_mastered(self):
        # every word and card marked once (strength 0.2): studied, though far from mastered. Memory is the
        # daily review's job; keeping the lesson here would show it for days after it was done.
        states = {k: (0.2, NOW) for k in lessons()[1]}
        got = pick_next_lesson(lessons(), states)
        self.assertEqual(got.lesson_id, 2)

    def test_a_forgotten_item_does_not_pull_the_learner_back(self):
        # lesson 1 was mastered, then a wrong answer dropped one item below 0.8: it comes back in the review
        states = {k: (0.8, NOW) for k in lessons()[1]}
        states[("vocab_item", 2)] = (0.6, NOW)
        self.assertEqual(pick_next_lesson(lessons(), states).lesson_id, 2)

    def test_unanswered_practice_keeps_the_lesson_until_it_is_answered(self):
        states = {k: (0.2, NOW) for k in lessons()[1]}
        got = pick_next_lesson(lessons(), states, practice={1: (3, 5)})
        self.assertEqual((got.lesson_id, got.practice_answered, got.practice_total), (1, 3, 5))
        self.assertEqual(pick_next_lesson(lessons(), states, practice={1: (5, 5)}).lesson_id, 2)

    def test_practice_of_other_lessons_does_not_matter(self):
        states = {k: (0.2, NOW) for k in lessons()[1]}
        self.assertEqual(pick_next_lesson(lessons(), states, practice={2: (0, 9)}).lesson_id, 2)

    def test_lessons_without_items_are_skipped(self):
        got = pick_next_lesson({1: [], 2: [("vocab_item", 3)]}, {})
        self.assertEqual(got.lesson_id, 2)

    def test_no_content_returns_none(self):
        self.assertIsNone(pick_next_lesson({}, {}))
        self.assertIsNone(pick_next_lesson({1: []}, {}))

    def test_states_for_unrelated_items_are_ignored(self):
        # e.g. article vocab (no lesson) that the learner reviewed
        got = pick_next_lesson(lessons(), {("vocab_item", 999): (1.0, NOW)})
        self.assertEqual((got.lesson_id, got.mastered), (1, 0))

    def test_everything_studied_refreshes_the_stalest_lesson(self):
        states = {}
        for lid, days_ago in ((1, 1), (2, 9), (3, 4)):
            for key in lessons()[lid]:
                states[key] = (1.0, NOW - timedelta(days=days_ago))
        got = pick_next_lesson(lessons(), states)
        self.assertEqual(got.lesson_id, 2)
        self.assertTrue(got.complete and got.studied)


class ResumeStepTests(unittest.TestCase):
    def test_an_untouched_lesson_opens_on_listening(self):
        self.assertEqual(resume_step(0, 30, 0, 5, 0, 20), "listen")

    def test_it_opens_on_the_first_part_with_something_left(self):
        self.assertEqual(resume_step(10, 30, 0, 5, 0, 20), "vocab")
        self.assertEqual(resume_step(30, 30, 2, 5, 0, 20), "grammar")
        self.assertEqual(resume_step(30, 30, 5, 5, 7, 20), "practice")

    def test_a_part_the_lesson_does_not_have_is_skipped(self):
        self.assertEqual(resume_step(30, 30, 0, 0, 0, 20), "practice")
        self.assertEqual(resume_step(0, 0, 5, 5, 0, 0), None)

    def test_a_finished_lesson_has_nothing_left(self):
        self.assertIsNone(resume_step(30, 30, 5, 5, 20, 20))

    def test_practice_alone_counts_as_a_start(self):
        self.assertEqual(resume_step(0, 30, 0, 5, 4, 20), "vocab")


def _rows(rows):
    res = mock.MagicMock()
    res.all.return_value = rows
    return res


class RecordReviewTests(unittest.IsolatedAsyncioTestCase):
    def _db(self, *, item_exists, row=None):
        row = row or SimpleNamespace(id=1)
        db = mock.MagicMock()
        db.add = mock.MagicMock()
        db.commit = mock.AsyncMock()
        db.refresh = mock.AsyncMock()

        async def execute(stmt):
            text = str(stmt)
            res = mock.MagicMock()
            if "item_state" in text:
                res.scalar_one_or_none.return_value = None
            else:  # the vocab/grammar row itself
                res.scalar_one_or_none.return_value = row if item_exists else None
            return res

        db.execute = execute
        return db

    async def test_unknown_item_is_404_and_writes_nothing(self):
        db = self._db(item_exists=False)
        body = ItemStateReviewRequest(item_type="vocab_item", item_id=999999, correct=True)
        with self.assertRaises(HTTPException) as ctx:
            await content.record_item_review(body, db, SimpleNamespace(id=uuid.uuid4()))
        self.assertEqual(ctx.exception.status_code, 404)
        db.add.assert_not_called()
        db.commit.assert_not_awaited()

    async def test_known_item_records_a_nudge(self):
        db = self._db(item_exists=True)
        body = ItemStateReviewRequest(item_type="grammar_point", item_id=7, correct=True)
        learner = uuid.uuid4()
        with mock.patch.object(content.competency_db, "record_outcomes", mock.AsyncMock()) as recorded:
            await content.record_item_review(body, db, SimpleNamespace(id=learner))
        (created,) = db.add.call_args.args
        self.assertEqual((created.item_type, created.item_id), ("grammar_point", 7))
        self.assertAlmostEqual(created.strength, 0.2)
        db.commit.assert_awaited_once()
        # the flip-card review of a grammar card is "nhận ra": one outcome on rung 0
        recorded.assert_awaited_once()
        self.assertEqual(recorded.await_args.args[1:], (learner, [7], 0, True))

    async def test_the_last_answer_is_stored_for_the_lesson_screen(self):
        for correct in (True, False):
            db = self._db(item_exists=True, row=VocabItem(id=1, hangul="날씨", meaning_vi="m", level=1))
            body = ItemStateReviewRequest(item_type="vocab_item", item_id=1, correct=correct)
            await content.record_item_review(body, db, SimpleNamespace(id=uuid.uuid4()))
            self.assertIs(self._added(db)[0].last_correct, correct)

    async def test_a_vocabulary_review_writes_no_competency(self):
        db = self._db(item_exists=True)
        body = ItemStateReviewRequest(item_type="vocab_item", item_id=7, correct=True)
        with mock.patch.object(content.competency_db, "record_outcomes", mock.AsyncMock()) as recorded:
            await content.record_item_review(body, db, SimpleNamespace(id=uuid.uuid4()))
        recorded.assert_not_awaited()

    def _added(self, db):
        return [c.args[0] for c in db.add.call_args_list]

    async def test_a_right_answer_writes_no_error(self):
        db = self._db(item_exists=True, row=VocabItem(id=1, hangul="비가 오다", meaning_vi="m", level=1))
        body = ItemStateReviewRequest(item_type="vocab_item", item_id=1, correct=True, mode="cloze")
        await content.record_item_review(body, db, SimpleNamespace(id=uuid.uuid4()))
        self.assertEqual([type(x) for x in self._added(db)], [ItemState])

    async def test_a_wrong_blank_on_a_chunk_is_logged_as_a_collocation_mistake(self):
        row = VocabItem(id=1, hangul="비가 오다", meaning_vi="m", level=1, node_word="오다", family="Động từ đi với thời tiết")
        db = self._db(item_exists=True, row=row)
        learner = uuid.uuid4()
        body = ItemStateReviewRequest(item_type="vocab_item", item_id=1, correct=False, mode="cloze", chosen="불다")
        await content.record_item_review(body, db, SimpleNamespace(id=learner))
        state, error = self._added(db)
        self.assertIsInstance(state, ItemState)
        self.assertIsInstance(error, ErrorLog)
        self.assertEqual(
            (error.learner_id, error.skill, error.error_type, error.example_ko, error.item_type, error.item_id, error.mode),
            (learner, "vocab", "collocation", "비가 오다", "vocab_item", 1, "cloze"),
        )
        self.assertEqual(error.detail, {"chosen": "불다", "family": "Động từ đi với thời tiết"})

    async def test_a_forgotten_card_is_a_recall_failure_and_an_old_client_without_a_mode_still_logs(self):
        row = VocabItem(id=2, hangul="날씨", meaning_vi="m", level=1)
        db = self._db(item_exists=True, row=row)
        body = ItemStateReviewRequest(item_type="vocab_item", item_id=2, correct=False)
        await content.record_item_review(body, db, SimpleNamespace(id=uuid.uuid4()))
        error = self._added(db)[1]
        self.assertEqual((error.error_type, error.mode, error.detail), ("vocab_recall", "recognize", None))

    async def test_a_forgotten_grammar_point_is_logged_under_grammar(self):
        row = GrammarPoint(id=3, pattern="V + -(으)ㄹ 것 같다", meaning_vi="m", level=2)
        db = self._db(item_exists=True, row=row)
        body = ItemStateReviewRequest(item_type="grammar_point", item_id=3, correct=False, mode="recognize")
        await content.record_item_review(body, db, SimpleNamespace(id=uuid.uuid4()))
        error = self._added(db)[1]
        self.assertEqual((error.skill, error.error_type, error.example_ko), ("grammar", "grammar_recall", "V + -(으)ㄹ 것 같다"))

    async def test_a_wrong_answer_to_an_unknown_item_writes_no_error(self):
        db = self._db(item_exists=False)
        body = ItemStateReviewRequest(item_type="vocab_item", item_id=999, correct=False)
        with self.assertRaises(HTTPException):
            await content.record_item_review(body, db, SimpleNamespace(id=uuid.uuid4()))
        db.add.assert_not_called()


class PlanTests(unittest.IsolatedAsyncioTestCase):
    def _db(self, states, *, vocab, grammar, lessons_by_id, totals=(), answered=(), article=None):
        db = mock.MagicMock()

        async def get(model, pk):
            if model is content.EditorialArticle:
                return article
            return lessons_by_id.get(pk)

        db.get = get

        async def execute(stmt):
            text = str(stmt)
            res = mock.MagicMock()
            if "FROM item_state" in text:
                res.scalars.return_value.all.return_value = states
            elif "content.lesson.slug" in text:
                res.all.return_value = []  # the daily reading's lookup of seeded lessons: none here
            elif "FROM lesson_exercise_result" in text and "GROUP BY" in text:  # answers per lesson
                res.all.return_value = list(answered)
            elif "FROM content.lesson" in text and "WHERE" not in text:  # practice questions per lesson
                res.all.return_value = [(lid, {"questions": n}) for lid, n in totals]
            elif "FROM reading_log" in text:
                res.scalars.return_value.all.return_value = []
                res.all.return_value = []
            elif "content.vocab_item.priority" in text:  # the words that only need recognising: none here
                res.all.return_value = []
            elif "FROM content.vocab_item" in text:
                res.all.return_value = vocab
            elif "FROM content.grammar_point" in text:
                res.all.return_value = grammar
            elif "cardinality(" in text:
                res.all.return_value = []  # no article has words
            elif "count(" in text:
                res.scalar_one.return_value = 0
            elif "FROM editorial.editorial_article" in text:  # the articles to pick from (not placed on the path)
                res.all.return_value = (
                    [(article.id, 5, [], datetime(2026, 10, 1, tzinfo=timezone.utc))] if article is not None else []
                )
            else:  # editorial submission: none
                res.scalars.return_value.first.return_value = None
                res.scalar_one_or_none.return_value = None
            return res

        db.execute = execute
        return db

    def _state(self, item_type, item_id, strength, when=NOW, **schedule):
        fields = dict(reps=0, lapses=0, ease=2.2, interval_days=0.0, due_at=None, introduced_at=when)
        return SimpleNamespace(item_type=item_type, item_id=item_id, strength=strength, last_seen=when, **{**fields, **schedule})

    def _lesson_task(self, plan):
        (task,) = [t for t in plan.tasks if t.kind == "vocab_review"]
        return task

    async def _plan(self, states, goal="topik4", **practice):
        db = self._db(
            states,
            vocab=[(1, 1), (1, 2), (2, 3), (None, 50)],  # 50 = article vocab, no lesson
            grammar=[(1, 1)],
            lessons_by_id={
                1: SimpleNamespace(id=1, title="Bài 1"),
                2: SimpleNamespace(id=2, title="Bài 2"),
            },
            **practice,
        )
        profile = SimpleNamespace(id=uuid.uuid4(), goal=goal, exam_date=None, role="learner")
        with mock.patch.object(content, "datetime", wraps=datetime) as dt:
            dt.now.return_value = NOW
            return await content.get_my_plan(db, profile)

    async def test_the_editorial_is_offered_only_to_a_topik_ii_goal(self):
        article = SimpleNamespace(id=uuid.uuid4(), title_ko="[기고] 서·논술형 수능", source_name="x", related_lesson_ids=[])
        reading = lambda plan: [t for t in plan.tasks if t.kind == "reading"]  # noqa: E731
        self.assertEqual(len(reading(await self._plan([], article=article))), 1)
        for goal in (None, "talk", "topik1"):
            self.assertEqual(reading(await self._plan([], goal=goal, article=article)), [], goal)

    async def test_closed_sources_are_not_offered_to_a_learner(self):
        article = SimpleNamespace(id=uuid.uuid4(), title_ko="[기고] 서·논술형 수능", source_name="x", related_lesson_ids=[])
        with mock.patch.object(content.settings, "BILLING_ENABLED", True), mock.patch.object(
            content.settings, "BILLING_PRIVATE_SOURCES", True
        ):
            plan = await self._plan([], article=article)
        self.assertEqual([t for t in plan.tasks if t.kind in ("reading", "listening")], [])

    async def test_new_learner_gets_first_lesson(self):
        plan = await self._plan([])
        task = self._lesson_task(plan)
        self.assertEqual((task.kind, task.lesson_id, task.status), ("vocab_review", 1, "todo"))
        self.assertEqual(task.subtitle, "Đã học 0/3 từ và mẫu")
        self.assertEqual(task.step, "listen")

    async def test_a_lesson_gone_through_once_leaves_the_plan_before_it_is_mastered(self):
        # the reported case: every card marked once and the practice answered, yet far from "thuộc"
        states = [self._state(t, i, 0.2) for t, i in (("vocab_item", 1), ("vocab_item", 2), ("grammar_point", 1))]
        plan = await self._plan(states, totals=[(1, 4), (2, 6)], answered=[(1, 4)])
        task = self._lesson_task(plan)
        self.assertEqual(task.lesson_id, 2)
        self.assertEqual(task.step, "listen")  # nothing of lesson 2 has been touched

    async def test_the_plan_says_what_is_left_and_where_to_open_the_lesson(self):
        states = [self._state("vocab_item", 1, 0.2), self._state("vocab_item", 2, 0.2)]
        plan = await self._plan(states, totals=[(1, 4)], answered=[])
        task = self._lesson_task(plan)
        self.assertEqual((task.lesson_id, task.step, task.status), (1, "grammar", "in_progress"))
        self.assertEqual(task.subtitle, "Đã học 2/3 từ và mẫu · luyện tập 0/4 câu")
        plan = await self._plan(states + [self._state("grammar_point", 1, 0.2)], totals=[(1, 4)], answered=[(1, 3)])
        task = self._lesson_task(plan)
        self.assertEqual((task.lesson_id, task.step), (1, "practice"))
        self.assertEqual(task.subtitle, "Đã học 3/3 từ và mẫu · luyện tập 3/4 câu")

    async def test_mastering_lesson_one_moves_plan_to_lesson_two(self):
        old = NOW - timedelta(days=2)
        states = [self._state(t, i, 0.8, old) for t, i in (("vocab_item", 1), ("vocab_item", 2), ("grammar_point", 1))]
        # article vocab reviewed today must not count toward any lesson
        states.append(self._state("vocab_item", 50, 1.0))
        plan = await self._plan(states)
        task = self._lesson_task(plan)
        self.assertEqual((task.lesson_id, task.title, task.status), (2, "Bài 2", "todo"))

    async def test_half_done_lesson_reports_what_was_learned_and_what_is_mastered(self):
        states = [self._state("vocab_item", 1, 1.0), self._state("vocab_item", 2, 0.2)]
        plan = await self._plan(states)
        task = self._lesson_task(plan)
        self.assertEqual((task.lesson_id, task.status, task.step), (1, "in_progress", "grammar"))
        self.assertEqual(task.subtitle, "Đã học 2/3 từ và mẫu · đã thuộc 1")


class LessonStudyTests(unittest.IsolatedAsyncioTestCase):
    """GET /lessons/{id}/study: where the learner stands in one lesson (fake session, no Postgres)."""

    def _db(self, *, vocab_ids, grammar_ids, states, answers=0, questions=4):
        lesson = SimpleNamespace(id=7, practice={"counts": {"questions": questions}})
        db = mock.MagicMock()
        db.get = mock.AsyncMock(return_value=lesson)

        async def execute(stmt):
            text = str(stmt)
            res = mock.MagicMock()
            if "FROM content.vocab_item" in text:
                res.scalars.return_value.all.return_value = vocab_ids
            elif "FROM content.grammar_point" in text:
                res.scalars.return_value.all.return_value = grammar_ids
            elif "FROM item_state" in text:
                res.scalars.return_value.all.return_value = states
            else:  # the lesson's answered practice questions
                rows = [
                    SimpleNamespace(exercise_id="e", question_id=f"q{i}", correct=True, attempts=1, last_answer="a")
                    for i in range(answers)
                ]
                res.scalars.return_value.all.return_value = rows
            return res

        db.execute = execute
        return db

    def _state(self, item_type, item_id, strength, last_correct, reps=0):
        return SimpleNamespace(item_type=item_type, item_id=item_id, strength=strength, last_correct=last_correct, reps=reps)

    async def _study(self, db):
        with mock.patch.object(content, "_require_open", mock.AsyncMock()):
            return await content.get_lesson_study(7, db, SimpleNamespace(id=uuid.uuid4()))

    async def test_an_untouched_lesson_opens_on_listening(self):
        out = await self._study(self._db(vocab_ids=[1, 2], grammar_ids=[1], states=[]))
        self.assertEqual((out.vocab_total, out.vocab_met, out.grammar_total, out.grammar_met), (2, 0, 1, 0))
        self.assertEqual((out.practice_total, out.practice_answered, out.resume_step, out.cards), (4, 0, "listen", []))

    async def test_it_reports_the_marked_cards_with_their_last_answer_and_opens_on_what_is_left(self):
        states = [
            self._state("vocab_item", 1, 0.2, True),
            self._state("vocab_item", 2, 0.0, False),
            self._state("grammar_point", 1, 0.2, True),
        ]
        out = await self._study(self._db(vocab_ids=[1, 2], grammar_ids=[1, 2], states=states, answers=1))
        self.assertEqual((out.vocab_met, out.grammar_met, out.practice_answered), (2, 1, 1))
        self.assertEqual(out.resume_step, "grammar")
        by_key = {(c.item_type, c.item_id): c.last_correct for c in out.cards}
        self.assertEqual(by_key, {("vocab_item", 1): True, ("vocab_item", 2): False, ("grammar_point", 1): True})

    async def test_a_card_from_before_the_column_existed_counts_as_understood_when_it_was_right_in_a_row(self):
        states = [self._state("vocab_item", 1, 0.2, None, reps=1), self._state("vocab_item", 2, 0.0, None, reps=0)]
        out = await self._study(self._db(vocab_ids=[1, 2], grammar_ids=[], states=states))
        self.assertEqual({c.item_id: c.last_correct for c in out.cards}, {1: True, 2: False})

    async def test_a_lesson_gone_through_has_nothing_left(self):
        states = [self._state("vocab_item", 1, 0.2, True), self._state("grammar_point", 1, 0.2, True)]
        out = await self._study(self._db(vocab_ids=[1], grammar_ids=[1], states=states, answers=4))
        self.assertIsNone(out.resume_step)

    async def test_an_unknown_lesson_is_404(self):
        db = mock.MagicMock()
        db.get = mock.AsyncMock(return_value=None)
        with self.assertRaises(HTTPException) as ctx:
            await content.get_lesson_study(7, db, SimpleNamespace(id=uuid.uuid4()))
        self.assertEqual(ctx.exception.status_code, 404)


class CountMasteredTests(unittest.TestCase):
    def test_counts_only_mastered_items_of_the_given_lesson(self):
        states = {
            ("vocab_item", 1): (1.0, NOW),
            ("vocab_item", 2): (0.4, NOW),
            ("vocab_item", 99): (1.0, NOW),  # not in this lesson
        }
        items = [("vocab_item", 1), ("vocab_item", 2), ("grammar_point", 1)]
        self.assertEqual(count_mastered(items, states), 1)
        self.assertEqual(count_mastered(items, {}), 0)


class LessonListTests(unittest.IsolatedAsyncioTestCase):
    # id, title, level, slug, title_ko, summary, track, sort_order, practice counts, practice kind
    LESSONS = [
        (1, "Gia đình", 1, None, None, None, None, 0, None, None),
        (2, "Công việc", 1, None, None, None, None, 0, None, None),
        (3, "Bài trống", 2, None, None, None, None, 0, None, None),
        (4, "Du lịch", 3, None, None, None, None, 0, None, None),
    ]
    VOCAB = [(1, 1), (1, 2), (2, 3), (4, 4), (None, 50)]  # 50: article vocab, no lesson
    GRAMMAR = [(1, 1), (4, 2)]
    TOPICS = [(1, "Gia đình"), (1, "Xã hội"), (4, "Du lịch")]

    def _db(self, states, answered=()):
        db = mock.MagicMock()

        async def execute(stmt):
            text = str(stmt)
            res = mock.MagicMock()
            if "FROM lesson_exercise_result" in text and "GROUP BY" in text:  # (lesson id, answers) per lesson
                res.all.return_value = [(lid, n, n) for lid, n in answered] if "filter" in text.lower() else list(answered)
            elif "FROM content.lesson" in text and "WHERE" not in text and "ORDER BY" not in text:
                res.all.return_value = []  # the practice totals: none in these fixtures
            elif re.search(r"\bexam\b", text):  # the exam-tag tallies: nothing is tagged in these fixtures
                res.all.return_value = []
            elif "lesson_topic" in text:
                res.all.return_value = self.TOPICS
            elif "FROM content.vocab_item" in text:
                res.all.return_value = self.VOCAB
            elif "FROM content.grammar_point" in text:
                res.all.return_value = self.GRAMMAR
            elif text.startswith("SELECT item_state.item_id, item_state.item_type"):  # the feathers' record
                res.all.return_value = [(st.item_id, st.item_type) for st in states]
            elif "FROM item_state" in text:
                res.scalars.return_value.all.return_value = states
            elif "lesson_exercise_result" in text or "lesson_part_done" in text:
                res.all.return_value = []
            else:  # the lessons themselves
                res.all.return_value = self.LESSONS
            return res

        db.execute = execute
        return db

    def _state(self, item_type, item_id, strength):
        return SimpleNamespace(item_type=item_type, item_id=item_id, strength=strength, last_seen=NOW)

    async def test_anonymous_gets_the_list_without_personal_fields(self):
        rows = await content.list_lessons(self._db([]), None)
        self.assertEqual([r.id for r in rows], [1, 2, 4])  # lesson 3 has nothing to study
        first = rows[0]
        self.assertEqual((first.title, first.vocab_count, first.grammar_count), ("Gia đình", 2, 1))
        self.assertEqual(first.topics, ["Gia đình", "Xã hội"])
        self.assertEqual(rows[1].topics, [])
        self.assertTrue(all(r.mastered is None and r.is_next is False for r in rows))

    async def test_new_learner_is_pointed_at_the_first_lesson(self):
        rows = await content.list_lessons(self._db([]), SimpleNamespace(id=uuid.uuid4()))
        self.assertEqual([(r.id, r.mastered, r.is_next) for r in rows], [(1, 0, True), (2, 0, False), (4, 0, False)])

    async def test_finished_lesson_moves_the_marker_on_and_counts_mastered(self):
        states = [
            self._state("vocab_item", 1, 0.8),
            self._state("vocab_item", 2, 1.0),
            self._state("grammar_point", 1, 0.8),
        ]
        rows = await content.list_lessons(self._db(states), SimpleNamespace(id=uuid.uuid4()))
        by_id = {r.id: r for r in rows}
        self.assertEqual(by_id[1].mastered, 3)
        self.assertEqual(by_id[2].mastered, 0)
        self.assertEqual([r.id for r in rows if r.is_next], [2])

    async def test_a_lesson_gone_through_once_is_no_longer_the_next_one_though_not_mastered(self):
        states = [
            self._state("vocab_item", 1, 0.2),
            self._state("vocab_item", 2, 0.2),
            self._state("grammar_point", 1, 0.2),
        ]
        rows = await content.list_lessons(self._db(states), SimpleNamespace(id=uuid.uuid4()))
        by_id = {r.id: r for r in rows}
        self.assertEqual(by_id[1].mastered, 0)  # the memory count is kept apart
        self.assertEqual([r.id for r in rows if r.is_next], [2])

    async def test_the_marker_never_lands_on_a_lesson_the_learner_cannot_open(self):
        async def only_lesson_2_is_open(db, profile, items):
            return {2: items[2]}

        with mock.patch.object(content, "_open_lesson_items", only_lesson_2_is_open):
            rows = await content.list_lessons(self._db([]), SimpleNamespace(id=uuid.uuid4()))
        self.assertEqual([r.id for r in rows if r.is_next], [2])


class OptionalProfileTests(unittest.IsolatedAsyncioTestCase):
    async def test_no_token_is_anonymous(self):
        self.assertIsNone(await deps.get_optional_profile(None, mock.MagicMock()))

    async def test_bad_token_is_anonymous_not_a_401(self):
        creds = SimpleNamespace(credentials="junk")
        with mock.patch.object(deps, "decode_token", side_effect=ValueError("bad")):
            self.assertIsNone(await deps.get_optional_profile(creds, mock.MagicMock()))

    async def test_valid_token_loads_the_profile(self):
        pid = uuid.uuid4()
        profile = SimpleNamespace(id=pid, disabled=False, tokens_valid_after=None)
        db = mock.MagicMock()
        db.get = mock.AsyncMock(return_value=profile)
        with mock.patch.object(deps, "decode_token", return_value={"sub": str(pid)}):
            got = await deps.get_optional_profile(SimpleNamespace(credentials="ok"), db)
        self.assertIs(got, profile)

    async def test_locked_account_is_anonymous(self):
        pid = uuid.uuid4()
        profile = SimpleNamespace(id=pid, disabled=True, tokens_valid_after=None)
        db = mock.MagicMock()
        db.get = mock.AsyncMock(return_value=profile)
        with mock.patch.object(deps, "decode_token", return_value={"sub": str(pid)}):
            self.assertIsNone(await deps.get_optional_profile(SimpleNamespace(credentials="ok"), db))


if __name__ == "__main__":
    unittest.main()

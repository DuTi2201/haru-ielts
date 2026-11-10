"""The lesson endpoints of lesson-v5: ordering, the practice set, answers and progress,
the audio requests (template by default, Gemini story on request) (the lesson
pictures have their own tests: test_lesson_images.py)."""
import unittest
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest import mock

from fastapi import HTTPException
from sqlalchemy.dialects import postgresql

from app.api.routers import audio, content
from app.models import ErrorLog, LessonExerciseResult
from app.schemas import ExerciseAnswerRequest, PodcastRequest
from app.services import lesson_audio, lesson_seed, progress, srs, tts

NOW = datetime(2026, 10, 5, tzinfo=timezone.utc)
BUNDLE = lesson_seed.load_all()
# the first lesson with every skill (the foundation lessons before it have reading and building only)
LESSON = next(r for r in BUNDLE.lessons if r.seed.slug == "sinh-hoat-01-buoi-sang")


def fake_lesson(resolved=LESSON, lesson_id=7):
    return SimpleNamespace(
        id=lesson_id,
        content_hash=resolved.content_hash,
        practice=resolved.practice,
        title=resolved.seed.title,
    )


def results(*values):
    out = []
    for v in values:
        res = mock.MagicMock()
        res.scalar_one_or_none.return_value = v
        res.scalars.return_value.all.return_value = v if isinstance(v, list) else []
        out.append(res)
    return out


class CurriculumOrderTests(unittest.TestCase):
    def test_the_next_lesson_follows_the_curriculum_not_the_id(self):
        lessons = {1: [("vocab_item", 1)], 2: [("vocab_item", 2)], 3: [("vocab_item", 3)]}
        self.assertEqual(progress.pick_next_lesson(lessons, {}).lesson_id, 1)
        self.assertEqual(progress.pick_next_lesson(lessons, {}, [3, 1, 2]).lesson_id, 3)
        done = {("vocab_item", 3): (1.0, NOW)}
        self.assertEqual(progress.pick_next_lesson(lessons, done, [3, 1, 2]).lesson_id, 1)

    def test_a_lesson_missing_from_the_order_comes_last(self):
        lessons = {1: [("vocab_item", 1)], 2: [("vocab_item", 2)], 9: [("vocab_item", 9)]}
        done = {("vocab_item", 2): (1.0, NOW)}
        self.assertEqual(progress.pick_next_lesson(lessons, done, [2]).lesson_id, 1)

    def test_new_cards_come_from_the_first_lesson_of_the_curriculum(self):
        lessons = {1: [("vocab_item", 1)], 2: [("vocab_item", 2)]}
        queue = srs.build_queue({}, lessons, NOW, new_limit=1, order=[2, 1])
        self.assertEqual(queue.new, [("vocab_item", 2)])
        self.assertEqual(srs.build_queue({}, lessons, NOW, new_limit=1).new, [("vocab_item", 1)])

    def test_the_list_is_ordered_by_track_then_position(self):
        sql = str(select_order()).lower()
        order_by = sql[sql.index("order by"):]
        self.assertIn("case", order_by)
        self.assertLess(order_by.index("case"), order_by.index("sort_order"))
        self.assertLess(order_by.index("sort_order"), order_by.rindex("content.lesson.id"))


def select_order():
    from sqlalchemy import select

    from app.models import Lesson

    return select(Lesson.id).order_by(*content._LESSON_ORDER).compile(dialect=postgresql.dialect())


class PracticeEndpointTests(unittest.IsolatedAsyncioTestCase):
    async def test_the_practice_set_is_returned_with_its_answers(self):
        db = mock.MagicMock()
        db.get = mock.AsyncMock(return_value=fake_lesson())
        no_pictures = mock.MagicMock()
        no_pictures.all.return_value = []
        db.execute = mock.AsyncMock(return_value=no_pictures)
        response = SimpleNamespace(headers={})
        out = await content.get_lesson_practice(7, response, db)
        self.assertEqual(len(out.items), len(LESSON.seed.exercise_ids))
        self.assertIn("answer", out.items[0]["questions"][0])
        self.assertIn("listening", out.guides)
        self.assertEqual(out.scene_images, {})  # none drawn yet: the browser keeps its icons
        self.assertIn("max-age", response.headers["Cache-Control"])

    async def test_a_lesson_without_practice_is_a_404(self):
        db = mock.MagicMock()
        db.get = mock.AsyncMock(return_value=SimpleNamespace(id=1, practice=None))
        with self.assertRaises(HTTPException) as caught:
            await content.get_lesson_practice(1, SimpleNamespace(headers={}), db)
        self.assertEqual(caught.exception.status_code, 404)


class AnswerTests(unittest.IsolatedAsyncioTestCase):
    PROFILE = SimpleNamespace(id=uuid.UUID(int=5))

    def db(self, existing=None, rows=None):
        db = mock.MagicMock()
        db.get = mock.AsyncMock(return_value=fake_lesson())
        db.execute = mock.AsyncMock(side_effect=results(existing, rows or []))
        db.add = mock.MagicMock()
        db.commit = mock.AsyncMock()
        return db

    def first_question(self):
        # a question with no linked grammar card (those take more queries, tested elsewhere)
        ex = next(e for e in LESSON.practice["items"] if e["skill"] == "listening" and not e["questions"][0].get("grammar"))
        return ex, ex["questions"][0]

    async def answer(self, db, **body):
        return await content.answer_lesson_question(7, ExerciseAnswerRequest(**body), db, self.PROFILE)

    async def test_a_right_answer_is_recorded_without_an_error_line(self):
        ex, q = self.first_question()
        db = self.db()
        await self.answer(db, exercise_id=ex["id"], question_id=q["id"], correct=True, answer=q["answer"])
        added = [c.args[0] for c in db.add.call_args_list]
        self.assertEqual([type(a) for a in added], [LessonExerciseResult])
        self.assertEqual((added[0].correct, added[0].attempts, added[0].learner_id), (True, 1, self.PROFILE.id))
        db.commit.assert_awaited_once()

    async def test_a_wrong_answer_also_goes_to_the_error_log_under_the_skill(self):
        ex, q = self.first_question()
        db = self.db()
        await self.answer(db, exercise_id=ex["id"], question_id=q["id"], correct=False, answer="9")
        log = next(c.args[0] for c in db.add.call_args_list if isinstance(c.args[0], ErrorLog))
        self.assertEqual((log.skill, log.error_type, log.mode), ("nghe", ex["type"], "exam"))
        self.assertEqual(log.detail["question"], q["id"])
        self.assertEqual(log.detail["chosen"], "9")
        self.assertEqual(log.learner_id, self.PROFILE.id)

    async def test_answering_again_updates_the_row_and_counts_the_try(self):
        ex, q = self.first_question()
        row = SimpleNamespace(correct=False, attempts=1, last_answer="2", updated_at=None, exercise_id=ex["id"], question_id=q["id"])
        db = self.db(existing=row, rows=[row])
        out = await self.answer(db, exercise_id=ex["id"], question_id=q["id"], correct=True, answer=q["answer"])
        self.assertEqual((row.correct, row.attempts, row.last_answer), (True, 2, q["answer"]))
        self.assertEqual(db.add.call_count, 0)
        self.assertEqual((out.answered, out.correct), (1, 1))
        self.assertEqual(out.total, LESSON.practice["counts"]["questions"])

    async def test_a_question_that_is_not_in_the_lesson_is_refused(self):
        ex, q = self.first_question()
        for body in (
            dict(exercise_id=ex["id"], question_id="NOPE", correct=True),
            dict(exercise_id="L99", question_id=q["id"], correct=True),
        ):
            db = self.db()
            with self.assertRaises(HTTPException) as caught:
                await self.answer(db, **body)
            self.assertEqual(caught.exception.status_code, 422)
            db.commit.assert_not_awaited()

    async def test_a_writing_blank_is_filed_under_viet(self):
        plain = [e for e in LESSON.practice["items"] if e["type"] == "write_fill" and not e.get("grammar")]
        ex = plain[0] if plain else None
        if ex is None:  # the first lesson has none: use a lesson that does
            resolved = next(r for r in BUNDLE.lessons if any(e["type"] == "write_fill" and not e.get("grammar") for e in r.practice["items"]))
            ex = next(e for e in resolved.practice["items"] if e["type"] == "write_fill" and not e.get("grammar"))
            lesson = fake_lesson(resolved)
        else:
            lesson = fake_lesson()
        db = self.db()
        db.get = mock.AsyncMock(return_value=lesson)
        qid = f"{ex['id']}:{ex['blanks'][0]['id']}"
        await content.answer_lesson_question(
            7, ExerciseAnswerRequest(exercise_id=ex["id"], question_id=qid, correct=False, answer="x"), db, self.PROFILE
        )
        log = next(c.args[0] for c in db.add.call_args_list if isinstance(c.args[0], ErrorLog))
        self.assertEqual((log.skill, log.error_type, log.mode), ("viết", "write_fill", "writing"))

    async def test_progress_totals_come_from_the_lesson(self):
        db = mock.MagicMock()
        db.get = mock.AsyncMock(return_value=fake_lesson())
        rows = [SimpleNamespace(exercise_id="L1", question_id="L1", correct=True, attempts=2, last_answer="1")]
        db.execute = mock.AsyncMock(side_effect=results(rows))
        out = await content.get_lesson_progress(7, db, self.PROFILE)
        self.assertEqual((out.answered, out.correct, out.attempts if hasattr(out, "attempts") else 0), (1, 1, 0))
        self.assertEqual(out.results[0].attempts, 2)
        self.assertEqual(out.total, LESSON.practice["counts"]["questions"])


class LinkedGrammarTests(unittest.IsolatedAsyncioTestCase):
    """A wrong answer to a question that is linked to a grammar card sends the card back to
    the learner's review queue and names it in the error log; a right one touches neither."""

    PROFILE = SimpleNamespace(id=uuid.UUID(int=5))

    def setUp(self):
        self.resolved = next(r for r in BUNDLE.lessons if r.seed.slug == "sinh-hoat-06-hoc-lam")
        ex = next(e for e in self.resolved.practice["items"] if e["id"] == "E01a")
        self.ex, self.q = ex, ex["questions"][0]

    def db(self, *results_):
        db = mock.MagicMock()
        db.get = mock.AsyncMock(return_value=fake_lesson(self.resolved))
        db.execute = mock.AsyncMock(side_effect=results(*results_))
        db.add = mock.MagicMock()
        db.commit = mock.AsyncMock()
        return db

    async def answer(self, db, correct, qid=None, exercise=None):
        ex = exercise or self.ex
        body = ExerciseAnswerRequest(
            exercise_id=ex["id"], question_id=qid or self.q["id"], correct=correct, answer="1"
        )
        self.recorded = mock.AsyncMock()
        with mock.patch.object(content, "_linked_grammar_ids", mock.AsyncMock(return_value=[(42, "V + -(으)면서")])) as lookup:
            with mock.patch.object(content.competency_db, "record_outcomes", self.recorded):
                await content.answer_lesson_question(7, body, db, self.PROFILE)
        return lookup

    def added(self, db, kind):
        return [c.args[0] for c in db.add.call_args_list if isinstance(c.args[0], kind)]

    async def test_a_wrong_answer_names_the_card_and_brings_it_back(self):
        from app.models import ItemState

        db = self.db(None, [], [])  # no earlier result, no schedule yet, progress rows
        before = datetime.now(timezone.utc)
        await self.answer(db, correct=False)
        log = self.added(db, ErrorLog)[0]
        self.assertEqual((log.item_type, log.item_id), ("grammar_point", 42))
        self.assertEqual(log.detail["grammar"], ["V + -(으)면서"])
        state = self.added(db, ItemState)[0]
        self.assertEqual((state.item_type, state.item_id, state.learner_id), ("grammar_point", 42, self.PROFILE.id))
        self.assertEqual((state.lapses, state.reps), (1, 0))
        self.assertGreater(state.due_at, before)
        self.assertLess(state.due_at - before, srs.RELEARN_DELAY + srs.DUE_GRACE)
        self.assertIsNone(state.introduced_at)  # it is not a "new" card: the day's budget is untouched

    async def test_a_card_the_learner_already_has_is_forgotten_once_more(self):
        existing = SimpleNamespace(
            item_id=42, strength=0.6, reps=2, lapses=0, ease=2.2, interval_days=3.0,
            due_at=NOW, introduced_at=NOW, last_seen=NOW,
        )
        db = self.db(None, [existing], [])
        await self.answer(db, correct=False)
        self.assertEqual((existing.lapses, existing.reps), (1, 0))
        self.assertAlmostEqual(existing.strength, 0.4)
        self.assertAlmostEqual(existing.ease, 2.0)
        self.assertEqual(existing.introduced_at, NOW)  # when it was first studied stays
        self.assertEqual(db.add.call_count, 2)  # the result and the error line, no second state

    async def test_two_misses_of_one_card_in_one_sitting_count_once(self):
        just_now = datetime.now(timezone.utc)
        existing = SimpleNamespace(
            item_id=42, strength=0.4, reps=0, lapses=1, ease=2.0, interval_days=0.0,
            due_at=just_now, introduced_at=None, last_seen=just_now,
        )
        db = self.db(None, [existing], [])
        await self.answer(db, correct=False)
        self.assertEqual(existing.lapses, 1)  # a second blank of the same exercise is not a second forgetting
        later = SimpleNamespace(
            item_id=42, strength=0.4, reps=0, lapses=1, ease=2.0, interval_days=0.0,
            due_at=NOW, introduced_at=None, last_seen=NOW,
        )
        db = self.db(None, [later], [])
        await self.answer(db, correct=False)
        self.assertEqual(later.lapses, 2)  # ...but a miss after the card was due again is

    async def test_trying_a_missed_question_again_does_not_forget_the_card_again(self):
        from app.models import ItemState

        previous = SimpleNamespace(
            correct=False, attempts=1, last_answer="2", updated_at=None, exercise_id="E01a", question_id="E01a"
        )
        db = self.db(previous, [previous])
        await self.answer(db, correct=False)
        self.assertEqual(self.added(db, ItemState), [])
        self.assertEqual(len(self.added(db, ErrorLog)), 1)  # the mistake is still logged

    async def test_a_question_that_was_right_before_and_is_wrong_now_counts_again(self):
        from app.models import ItemState

        previous = SimpleNamespace(
            correct=True, attempts=1, last_answer="4", updated_at=None, exercise_id="E01a", question_id="E01a"
        )
        db = self.db(previous, [], [previous])
        await self.answer(db, correct=False)
        self.assertEqual(len(self.added(db, ItemState)), 1)

    async def test_a_right_answer_leaves_the_card_alone(self):
        from app.models import ItemState

        db = self.db(None, [])
        await self.answer(db, correct=True)
        self.assertEqual(self.added(db, ItemState), [])  # the card is not sent back for review
        self.assertEqual(self.added(db, ErrorLog), [])

    async def test_every_answer_is_one_more_outcome_for_the_linked_cards_on_the_exercises_rung(self):
        for correct in (True, False):
            db = self.db(None, [], []) if not correct else self.db(None, [])
            await self.answer(db, correct=correct)
            self.recorded.assert_awaited_once()
            args = self.recorded.await_args.args
            self.assertEqual((args[1], args[2], args[3], args[4]), (self.PROFILE.id, [42], 0, correct))  # E01a is a reading question: rung 0

    async def test_the_links_are_looked_up_through_the_lessons_own_cards(self):
        db = mock.MagicMock()
        row = SimpleNamespace(id=42)
        found = mock.MagicMock()
        found.all.return_value = [(42, "V + -(으)면서", "sinh-hoat-06-hoc-lam")]
        db.execute = mock.AsyncMock(return_value=found)
        lesson = fake_lesson(self.resolved)
        got = await content._linked_grammar_ids(db, lesson, self.ex, "E01a")
        self.assertEqual(got, [(42, "V + -(으)면서")])
        # a question with no link costs no query
        db.execute.reset_mock()
        other = next(e for e in self.resolved.practice["items"] if e["type"] == "listen_dialogue")
        self.assertEqual(await content._linked_grammar_ids(db, lesson, other, other["questions"][0]["id"]), [])
        db.execute.assert_not_awaited()
        del row

    async def test_the_practice_set_tells_each_card_and_the_lesson_that_teaches_it(self):
        db = mock.MagicMock()
        db.get = mock.AsyncMock(return_value=fake_lesson(self.resolved))
        ids = mock.MagicMock()
        ids.all.return_value = [("sinh-hoat-06-hoc-lam", 66)]
        titled = mock.MagicMock()
        titled.all.return_value = []  # the lessons named by a hard item's help (tested in test_practice_tiers)

        async def execute(stmt):
            return titled if "content.lesson.title" in str(stmt) else ids

        db.execute = mock.AsyncMock(side_effect=execute)
        with mock.patch.object(content.lesson_image_db, "visible_urls", mock.AsyncMock(return_value={})):
            out = await content.get_lesson_practice(7, SimpleNamespace(headers={}), db)
        card = out.grammar["V + -(으)면서"]
        self.assertEqual((card["lesson_id"], card["tier"], card["use_level"]), (66, "extension", "produce"))
        self.assertNotIn("lesson_order", card)
        first = next(e for e in out.items if e["id"] == "E01a")
        self.assertEqual(first["questions"][0]["grammar"], ["V + -(으)면서"])


class LessonAudioRequestTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        # no Redis here: spending from the allowance is checked in test_audio_sharing.py
        patcher = mock.patch.object(audio.ratelimit, "spend", mock.AsyncMock())
        self.spend = patcher.start()
        self.addCleanup(patcher.stop)

    def make_db(self, hit=None, job=None):
        db = mock.MagicMock()
        db.execute = mock.AsyncMock(side_effect=results(hit, job))
        db.add = mock.MagicMock()
        db.commit = mock.AsyncMock()
        db.flush = mock.AsyncMock()
        db.delete = mock.AsyncMock()

        async def refresh(j):
            j.id = uuid.UUID(int=4)
            j.status = j.status or "queued"

        db.refresh = mock.AsyncMock(side_effect=refresh)
        return db

    async def podcast(self, owner, mode="template", sig="hash-a"):
        with mock.patch.object(tts, "chirp_enabled", return_value=True), mock.patch.object(
            audio.generate_content_podcast, "delay"
        ) as delay:
            await audio._request_podcast(
                self.make_db(), owner, "5", PodcastRequest(mode=mode), SimpleNamespace(headers={}), [1], [2],
                content_sig=sig if owner == "lesson" else None,
            )
        return delay.call_args.args

    async def test_a_lesson_is_voiced_from_the_template_by_default(self):
        args = await self.podcast("lesson")
        self.assertEqual(args[4], lesson_audio.TEMPLATE_VERSION)
        self.assertEqual(args[7], "template")
        self.assertIn(f":{lesson_audio.TEMPLATE_VERSION}:", args[5])
        self.assertTrue(args[5].endswith(tts.lecture_spec()))  # Chirp, with the voice spec in the key

    async def test_the_story_is_a_separate_recording_with_its_own_key(self):
        template, story = await self.podcast("lesson"), await self.podcast("lesson", "story")
        self.assertEqual((story[4], story[7]), (lesson_audio.STORY_VERSION, "story"))
        self.assertNotEqual(template[5], story[5])  # both are kept, neither overwrites the other

    async def test_an_edited_lesson_is_recorded_again(self):
        self.assertNotEqual((await self.podcast("lesson", sig="hash-a"))[5], (await self.podcast("lesson", sig="hash-b"))[5])
        self.assertEqual((await self.podcast("lesson", sig="hash-a"))[5], (await self.podcast("lesson", sig="hash-a"))[5])

    async def test_an_article_keeps_the_original_lecture(self):
        args = await self.podcast("article")
        self.assertEqual((args[4], args[7]), ("podcast-v2", "story"))

    async def test_a_stored_recording_is_replayed_without_a_new_job(self):
        hit = SimpleNamespace(cache_key="k", opus_path="/o", aac_path="/a", duration_sec=60, script_text="s")
        with mock.patch.object(tts, "chirp_enabled", return_value=True), mock.patch.object(
            audio.generate_content_podcast, "delay"
        ) as delay:
            out = await audio._request_podcast(
                self.make_db(hit=hit), "lesson", "5", PodcastRequest(), SimpleNamespace(headers={}), [1], [2], content_sig="x"
            )
        delay.assert_not_called()
        self.assertEqual(out.status, "succeeded")


class ExerciseAudioRequestTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        # no Redis here: spending from the allowance is checked in test_audio_sharing.py
        patcher = mock.patch.object(audio.ratelimit, "spend", mock.AsyncMock())
        self.spend = patcher.start()
        self.addCleanup(patcher.stop)

    def db(self, lesson, hit=None, job=None):
        db = mock.MagicMock()
        db.get = mock.AsyncMock(return_value=lesson)
        db.execute = mock.AsyncMock(side_effect=results(hit, job))
        db.add = mock.MagicMock()
        db.commit = mock.AsyncMock()
        db.flush = mock.AsyncMock()
        db.delete = mock.AsyncMock()

        async def refresh(j):
            j.id = uuid.UUID(int=6)
            j.status = j.status or "queued"

        db.refresh = mock.AsyncMock(side_effect=refresh)
        return db

    def lesson_with(self, exercise_id):
        return next(r for r in BUNDLE.lessons if exercise_id in r.seed.exercise_ids)

    async def ask(self, lesson, exercise_id, **kw):
        with mock.patch.object(tts, "chirp_enabled", return_value=True), mock.patch.object(
            audio.generate_exercise_audio, "delay"
        ) as delay:
            out = await audio.request_exercise_audio(7, exercise_id, SimpleNamespace(headers={}), self.db(lesson, **kw))
        return out, delay

    async def test_a_listening_exercise_is_recorded_with_its_turns(self):
        resolved = self.lesson_with("L1")
        out, delay = await self.ask(fake_lesson(resolved), "L1")
        job_id, ex_id, turns, key, fallback = delay.call_args.args
        self.assertEqual(ex_id, "L1")
        self.assertEqual([t[0] for t in turns], ["F", "M", "F", "M"])
        self.assertTrue(key.startswith("lex:L1:") and key.endswith(tts.dialogue_spec()))
        self.assertTrue(fallback.startswith("lex:L1:") and fallback != key)
        self.assertEqual(out.status, "queued")

    async def test_the_recording_is_stored_once_and_replayed(self):
        resolved = self.lesson_with("L1")
        hit = SimpleNamespace(cache_key="k", opus_path="/o", aac_path="/a", duration_sec=9)
        out, delay = await self.ask(fake_lesson(resolved), "L1", hit=hit)
        delay.assert_not_called()
        self.assertEqual(out.status, "succeeded")

    async def test_an_exercise_without_a_recording_is_a_404(self):
        resolved = self.lesson_with("R1")
        with self.assertRaises(HTTPException) as caught:
            await self.ask(fake_lesson(resolved), "R1")
        self.assertEqual(caught.exception.status_code, 404)
        with self.assertRaises(HTTPException) as caught:
            await self.ask(None, "L1")
        self.assertEqual(caught.exception.status_code, 404)

    async def test_the_speaking_task_with_a_dialogue_has_one_too(self):
        resolved = self.lesson_with("S4")
        _out, delay = await self.ask(fake_lesson(resolved), "S4")
        delay.assert_called_once()


if __name__ == "__main__":
    unittest.main()

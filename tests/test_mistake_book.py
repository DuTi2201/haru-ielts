"""Sổ lỗi sai: a wrong practice answer written out from the lesson's own question (what was chosen, the
right answer, the explanation, the cards it is about), the endpoint that lists a learner's mistakes by
lesson and the "Đã hiểu" mark."""
import unittest
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest import mock

from fastapi import HTTPException

from app.api.routers import content, practice
from app.schemas import ExerciseAnswerRequest, MistakeUnderstoodRequest
from app.services import lesson_seed, mistake_book

BUNDLE = lesson_seed.load_all()
GUIDED = BUNDLE.lessons
LESSON = BUNDLE.lessons[0]
NOW = datetime(2026, 10, 11, 10, 0, tzinfo=timezone.utc)


def items(resolved=LESSON, **where):
    return [e for e in resolved.practice["items"] if all(e.get(k) == v for k, v in where.items())]


class EntryTests(unittest.TestCase):
    def test_every_question_of_the_guided_lessons_can_be_written_out(self):
        # whatever the learner got wrong, the book can say what the right answer was and why
        self.assertEqual(len(GUIDED), 42)
        for r in GUIDED:
            for ex in r.practice["items"]:
                for qid in lesson_seed.question_ids(ex):
                    e = mistake_book.entry(ex, qid, None)
                    if ex["type"] in mistake_book.SELF_SCORED_TYPES:
                        self.assertIsNone(e, (r.seed.slug, qid))
                        continue
                    self.assertIsNotNone(e, (r.seed.slug, qid))
                    self.assertTrue(e["correct"], (r.seed.slug, qid))
                    self.assertTrue(e["title"], (r.seed.slug, qid))
                    if e["options"]:
                        self.assertIn(e["correct_id"], [o["id"] for o in e["options"]], qid)
                        self.assertTrue(e["explanation_vi"], (r.seed.slug, qid))

    def test_a_choice_shows_the_text_of_what_was_picked_and_of_the_right_option(self):
        ex = items(type="read_cloze")[0]
        q = ex["questions"][0]
        wrong = next(o for o in q["options"] if o["id"] != q["answer"])
        e = mistake_book.entry(ex, q["id"], wrong["id"])
        self.assertEqual((e["chosen_id"], e["chosen"]), (wrong["id"], wrong["text"]))
        right = next(o for o in q["options"] if o["id"] == q["answer"])
        self.assertEqual((e["correct_id"], e["correct"]), (q["answer"], [right["text"]]))
        self.assertEqual(e["skill"], "Đọc")
        self.assertEqual(e["explanation_vi"], q["explanation_vi"])
        self.assertEqual(e["grammar"], q["grammar"])

    def test_what_was_heard_is_shown_as_the_transcript_with_its_meaning(self):
        ex = {
            "id": "L1",
            "skill": "listening",
            "type": "listen_reply",
            "title_vi": "Nghe",
            "stimulus": {"kind": "audio", "turns": [{"speaker": "F", "text": "Hello", "vi": "Xin chào"}]},
            "questions": [
                {"id": "L1", "options": [{"id": "1", "text": "a"}, {"id": "2", "text": "b"}], "answer": "2", "explanation_vi": "e"}
            ],
        }
        e = mistake_book.entry(ex, "L1", "1")
        self.assertEqual([c["text"] for c in e["context"]], [t["text"] for t in ex["stimulus"]["turns"]])
        self.assertTrue(all(c.get("vi") for c in e["context"]))

    def test_a_reading_passage_is_shown_but_kept_short(self):
        ex = items(type="read_passage")[0]
        e = mistake_book.entry(ex, ex["questions"][0]["id"], "2")
        self.assertEqual(len(e["context"]), 1)
        self.assertLessEqual(len(e["context"][0]["text"]), mistake_book.MAX_CONTEXT_CHARS)
        self.assertEqual(e["skill"], "Đọc")

    def test_an_answer_that_is_not_an_option_is_kept_as_it_was(self):
        ex = items(type="read_cloze")[0]
        e = mistake_book.entry(ex, ex["questions"][0]["id"], "9")
        self.assertEqual((e["chosen_id"], e["chosen"]), ("9", "9"))

    def test_building_a_sentence_shows_the_meaning_what_was_built_and_the_right_sentences(self):
        ex = items(type="build_order")[0]
        e = mistake_book.entry(ex, ex["id"], "저는 어제 일찍 일어나요.")
        self.assertEqual(e["prompt"], ex["meaning_vi"])
        self.assertEqual(e["chosen"], "저는 어제 일찍 일어나요.")
        self.assertEqual(e["correct"], ex["answers"][:2])
        self.assertEqual(e["explanation_vi"], ex["explain_vi"])
        self.assertEqual(e["skill"], "Tạo câu")

    def test_a_writing_blank_is_one_entry_per_blank(self):
        ex = items(type="write_fill")[0]
        blank = ex["blanks"][0]
        e = mistake_book.entry(ex, f"{ex['id']}:{blank['id']}", "과식해요")
        self.assertEqual(e["prompt"], f"Chỗ trống {blank['id']}")
        self.assertEqual(e["correct"], blank["accepted"][:3])
        self.assertEqual(e["chosen"], "과식해요")
        self.assertEqual([c["text"] for c in e["context"]], [ex["text"]][: len(e["context"])])
        self.assertIsNone(mistake_book.entry(ex, f"{ex['id']}:nope", "x"))

    def test_a_dictation_shows_the_script_and_the_words_to_learn(self):
        ex = items(type="listen_dictation")[0]
        e = mistake_book.entry(ex, ex["id"], "저는 / 세수를")
        self.assertEqual(e["correct"], [t["text"] for t in ex["stimulus"]["turns"]])
        self.assertEqual(e["chosen"], "저는 / 세수를")
        self.assertEqual(e["focus"], ex["focus"])
        self.assertTrue(e["translation"])

    def test_an_essay_and_a_speaking_task_are_not_mistakes(self):
        for t in ("write_essay", "speak"):
            ex = items(type=t)[0]
            self.assertIsNone(mistake_book.entry(ex, ex["id"], "5/10"), t)
            self.assertFalse(mistake_book.in_book(ex))

    def test_a_question_the_lesson_does_not_have_is_none(self):
        ex = items(type="read_cloze")[0]
        self.assertIsNone(mistake_book.entry(ex, "NOPE", "1"))


def lesson_row(resolved=LESSON, lesson_id=7):
    return SimpleNamespace(
        id=lesson_id,
        slug=resolved.seed.slug,
        title=resolved.seed.title,
        sort_order=resolved.seed.sort_order,
        practice=resolved.practice,
        coach={"focus_vi": ["x"]},
    )


def result_row(ex, qid, answer, understood=None, attempts=1, correct=False, lesson_id=7, when=NOW):
    return SimpleNamespace(
        lesson_id=lesson_id,
        exercise_id=ex["id"],
        question_id=qid,
        correct=correct,
        attempts=attempts,
        last_answer=answer,
        updated_at=when,
        understood_at=understood,
    )


def execute_results(*payloads):
    """db.execute() answers, in order: each payload serves .all(), .scalars().all() and .scalar_one_or_none()."""
    out = []
    for p in payloads:
        res = mock.MagicMock()
        res.all.return_value = p
        res.scalars.return_value.all.return_value = p
        res.scalar_one_or_none.return_value = p
        out.append(res)
    return out


class BookEndpointTests(unittest.IsolatedAsyncioTestCase):
    PROFILE = SimpleNamespace(id=uuid.UUID(int=5))

    def slug_of(self, ex, qid):
        info = LESSON.practice["grammar"]
        patterns = lesson_seed.question_grammar(ex, qid)
        return {info[p]["lesson_slug"] for p in patterns if p in info}

    def db(self, rows, order=(7,)):
        # queries in order: the wrong answers, the lessons that teach the cards, the curriculum order
        slugs = set()
        for r, _ in rows:
            ex = lesson_seed.question_index(LESSON.practice).get(r.question_id)
            if ex is not None and mistake_book.in_book(ex):
                slugs |= self.slug_of(ex, r.question_id)
        payloads = [rows]
        if slugs:
            payloads.append([(s, 70 + i) for i, s in enumerate(sorted(slugs))])
        payloads.append(list(order))
        db = mock.MagicMock()
        db.execute = mock.AsyncMock(side_effect=execute_results(*payloads))
        db.commit = mock.AsyncMock()
        return db

    def reply(self):
        ex = items(type="read_cloze")[0]
        return ex, ex["questions"][0]["id"]

    async def test_a_wrong_answer_is_listed_under_its_lesson_with_the_cards_and_where_they_are_taught(self):
        ex, qid = self.reply()
        db = self.db([(result_row(ex, qid, "2", attempts=2), lesson_row())])
        book = await practice.get_mistake_book(db, self.PROFILE)
        self.assertEqual((book.open, book.understood), (1, 0))
        (lesson,) = book.lessons
        self.assertEqual((lesson.lesson_id, lesson.title), (7, LESSON.seed.title))
        (m,) = lesson.mistakes
        self.assertEqual((m.question_id, m.chosen_id, m.attempts, m.understood), (qid, "2", 2, False))
        self.assertTrue(m.explanation_vi)
        self.assertTrue(m.grammar)
        self.assertTrue(all(g.lesson_id is not None and g.pattern for g in m.grammar))

    async def test_a_mistake_marked_understood_goes_after_the_open_ones(self):
        replies = items(type="read_cloze")
        a, b = replies[0], replies[1]
        qa, qb = a["questions"][0]["id"], b["questions"][0]["id"]
        rows = [
            (result_row(a, qa, "2", understood=NOW, when=NOW), lesson_row()),
            (result_row(b, qb, "2", when=datetime(2026, 10, 1, tzinfo=timezone.utc)), lesson_row()),
        ]
        book = await practice.get_mistake_book(self.db(rows), self.PROFILE)
        self.assertEqual([m.question_id for m in book.lessons[0].mistakes], [qb, qa])
        self.assertEqual((book.open, book.understood), (1, 1))

    async def test_the_lessons_come_in_curriculum_order(self):
        ex, qid = self.reply()
        rows = [
            (result_row(ex, qid, "2", lesson_id=9), lesson_row(lesson_id=9)),
            (result_row(ex, qid, "2", lesson_id=7), lesson_row(lesson_id=7)),
        ]
        book = await practice.get_mistake_book(self.db(rows, order=(7, 9)), self.PROFILE)
        self.assertEqual([l.lesson_id for l in book.lessons], [7, 9])

    async def test_self_scored_and_vanished_questions_are_left_out(self):
        essay = items(type="write_essay")[0]
        rows = [
            (result_row(essay, essay["id"], "3/10"), lesson_row()),
            (result_row(essay, "GONE", "1"), lesson_row()),
        ]
        book = await practice.get_mistake_book(self.db(rows), self.PROFILE)
        self.assertEqual((book.lessons, book.open, book.understood), ([], 0, 0))

    async def test_an_empty_book_is_an_empty_list(self):
        db = mock.MagicMock()
        db.execute = mock.AsyncMock(side_effect=execute_results([], []))
        book = await practice.get_mistake_book(db, self.PROFILE)
        self.assertEqual((book.lessons, book.open, book.understood), ([], 0, 0))

    async def test_the_book_only_asks_for_wrong_answers_of_lessons_with_the_study_guide(self):
        db = mock.MagicMock()
        db.execute = mock.AsyncMock(side_effect=execute_results([], []))
        await practice.get_mistake_book(db, self.PROFILE)
        sql = str(db.execute.await_args_list[0].args[0].compile(compile_kwargs={"literal_binds": False})).lower()
        self.assertIn("lesson_exercise_result.correct is false", sql)
        self.assertIn("lesson.coach is not null", sql)
        self.assertIn("lesson_exercise_result.learner_id", sql)


class UnderstoodTests(unittest.IsolatedAsyncioTestCase):
    PROFILE = SimpleNamespace(id=uuid.UUID(int=5))

    async def test_marking_a_mistake_understood_sets_the_time_and_returns_the_book(self):
        ex = items(type="read_cloze")[0]
        qid = ex["questions"][0]["id"]
        row = result_row(ex, qid, "2")
        book_rows = [(row, lesson_row())]
        info = LESSON.practice["grammar"]
        slugs = {info[p]["lesson_slug"] for p in lesson_seed.question_grammar(ex, qid) if p in info}
        payloads = [row, book_rows] + ([[(s, 70) for s in slugs]] if slugs else []) + [[7]]
        db = mock.MagicMock()
        db.execute = mock.AsyncMock(side_effect=execute_results(*payloads))
        db.commit = mock.AsyncMock()
        out = await practice.mark_mistake_understood(
            MistakeUnderstoodRequest(lesson_id=7, question_id=qid), db, self.PROFILE
        )
        self.assertIsNotNone(row.understood_at)
        db.commit.assert_awaited_once()
        self.assertEqual((out.open, out.understood), (0, 1))

    async def test_taking_it_back_clears_the_time(self):
        ex = items(type="listen_reply")[0]
        qid = ex["questions"][0]["id"]
        row = result_row(ex, qid, "2", understood=NOW)
        db = mock.MagicMock()
        db.execute = mock.AsyncMock(side_effect=execute_results(row, [], []))
        db.commit = mock.AsyncMock()
        await practice.mark_mistake_understood(
            MistakeUnderstoodRequest(lesson_id=7, question_id=qid, understood=False), db, self.PROFILE
        )
        self.assertIsNone(row.understood_at)

    async def test_a_question_that_is_not_a_mistake_is_a_404(self):
        db = mock.MagicMock()
        db.execute = mock.AsyncMock(side_effect=execute_results(None))
        db.commit = mock.AsyncMock()
        with self.assertRaises(HTTPException) as cm:
            await practice.mark_mistake_understood(
                MistakeUnderstoodRequest(lesson_id=7, question_id="L1"), db, self.PROFILE
            )
        self.assertEqual(cm.exception.status_code, 404)
        db.commit.assert_not_awaited()

    async def test_the_request_takes_a_short_question_id(self):
        with self.assertRaises(Exception):
            MistakeUnderstoodRequest(lesson_id=7, question_id="x" * 33)


class AnswerClearsTheMarkTests(unittest.IsolatedAsyncioTestCase):
    PROFILE = SimpleNamespace(id=uuid.UUID(int=5))

    def db(self, row):
        db = mock.MagicMock()
        lesson = SimpleNamespace(id=7, content_hash=LESSON.content_hash, practice=LESSON.practice, title=LESSON.seed.title)
        db.get = mock.AsyncMock(return_value=lesson)
        db.execute = mock.AsyncMock(side_effect=execute_results(row, []))
        db.add = mock.MagicMock()
        db.commit = mock.AsyncMock()
        return db

    async def answer(self, row, correct):
        ex = items(type="listen_main_idea")[0]  # no grammar link: one query fewer to mock
        qid = ex["questions"][0]["id"]
        row.exercise_id, row.question_id = ex["id"], qid
        db = self.db(row)
        await content.answer_lesson_question(
            7, ExerciseAnswerRequest(exercise_id=ex["id"], question_id=qid, correct=correct, answer="2"), db, self.PROFILE
        )

    async def test_a_new_wrong_answer_puts_an_understood_mistake_back(self):
        row = result_row({"id": "x"}, "q", "1", understood=NOW)
        await self.answer(row, correct=False)
        self.assertIsNone(row.understood_at)

    async def test_a_right_answer_leaves_the_mark_alone(self):
        row = result_row({"id": "x"}, "q", "1", understood=NOW)
        await self.answer(row, correct=True)
        self.assertEqual(row.understood_at, NOW)
        self.assertTrue(row.correct)


if __name__ == "__main__":
    unittest.main()

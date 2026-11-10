"""The "Tạo câu" (sentence building) skill of the practice screen: a ladder of four rungs
(order the tiles → fill the frame → join two sentences → write a short paragraph) that sits between
reading and writing, and the foundation cards it practises. The pilot was topic 1, lessons 1–3; it now
covers every lesson of topic 1 (lessons 1–9) and of topic 2 (lessons 1–11)."""
import re
import unittest
import uuid
from types import SimpleNamespace
from unittest import mock

from pydantic import ValidationError

from app.api.routers import content
from app.models import ErrorLog
from app.schemas import ExerciseAnswerRequest
from app.services import lesson_seed as seed
from app.services import weakness

BUNDLE = seed.load_all()
LESSONS = {r.seed.slug: r for r in BUNDLE.lessons}
PILOT = ("sinh-hoat-01-buoi-sang", "sinh-hoat-02-viec-nha", "sinh-hoat-03-an-uong")
SCALED = (
    "sinh-hoat-04-mua-sam", "sinh-hoat-05-di-lai", "sinh-hoat-06-hoc-lam",
    "sinh-hoat-07-giai-tri", "sinh-hoat-08-suc-khoe", "sinh-hoat-09-nhat-ky",
)
T1 = PILOT + SCALED  # the practice lessons of topic 1; lesson 10 is its review
# The practice lessons of topic 2 (Quan hệ): lesson 12 is its review.
T2 = tuple(sorted(s for s in LESSONS if re.match(r"quan-he-(0[1-9]|1[01])-", s)))
# The practice lessons of topic 4 (Công sở): lesson 41 is its review. They build on two rungs (word order and
# joining two sentences); the Viết 53 warm-ups and the chart-description essay take the place of the upper rungs.
T4 = tuple(sorted(s for s in LESSONS if re.match(r"cong-so-0[1-7]-", s)))
TW54 = tuple(sorted(s for s in LESSONS if s.startswith("viet-nghi-luan-")))  # the Viết 54 course builds sentences too
# How many foundation cards each lesson leads with (the pilot wrote four, the scale-up two).
FOUNDATION = {**{s: 4 for s in PILOT}, **{s: 2 for s in SCALED}}

GOOD = {
    "id": "BX1", "skill": "build", "type": "build_order", "rung": 1, "title_vi": "t", "meaning_vi": "m",
    "tiles": ["어제", "일어났어요.", "저는", "일어나요."],
    "answers": ["저는 어제 일어났어요.", "어제 저는 일어났어요."],
}


def build(**changes):
    return seed.BuildOrder.model_validate({**GOOD, **changes})


class BuildOrderSchemaTests(unittest.TestCase):
    def test_a_good_one_validates(self):
        self.assertEqual(build().answers[0], "저는 어제 일어났어요.")

    def test_every_word_of_the_answer_must_be_a_tile(self):
        with self.assertRaisesRegex(ValidationError, "do not contain every word"):
            build(tiles=["어제", "일어났어요.", "일어나요."])

    def test_all_answers_use_the_same_tiles(self):
        with self.assertRaisesRegex(ValidationError, "does not use the same tiles"):
            build(answers=["저는 어제 일어났어요.", "저는 일어났어요."])

    def test_answers_are_tiles_joined_by_single_spaces(self):
        with self.assertRaisesRegex(ValidationError, "single spaces"):
            build(answers=["저는  어제 일어났어요."])

    def test_the_same_answer_twice_is_refused(self):
        with self.assertRaisesRegex(ValidationError, "the same answer twice"):
            build(answers=["저는 어제 일어났어요.", "저는 어제 일어났어요."])

    def test_tiles_shown_already_in_order_are_refused(self):
        with self.assertRaisesRegex(ValidationError, "already in an accepted order"):
            build(tiles=["저는", "어제", "일어났어요."])

    def test_more_than_ten_tiles_do_not_fit_a_phone(self):
        words = [f"단어{i}" for i in range(11)]
        with self.assertRaisesRegex(ValidationError, "more than 10 tiles"):
            build(tiles=words[::-1], answers=[" ".join(words)])

    def test_the_rung_goes_with_the_build_skill_only(self):
        fill = {
            "id": "BX2", "skill": "build", "type": "write_fill", "number": "Bước 2", "title_vi": "t", "points": 2,
            "text": "( ㉠ )", "blanks": [{"id": "㉠", "points": 2, "accepted": ["x"]}],
        }
        with self.assertRaisesRegex(ValidationError, "rung"):
            seed.WriteFill.model_validate(fill)  # build without a rung
        seed.WriteFill.model_validate({**fill, "rung": 2})
        with self.assertRaisesRegex(ValidationError, "rung"):
            seed.WriteFill.model_validate({**fill, "skill": "writing", "rung": 2})  # a rung on plain writing
        essay = {
            "id": "BX3", "skill": "build", "type": "write_essay", "number": "Bước 4", "title_vi": "t", "points": 10,
            "limits": {"min": 10, "max": 50},
        }
        with self.assertRaisesRegex(ValidationError, "rung"):
            seed.WriteEssay.model_validate(essay)
        seed.WriteEssay.model_validate({**essay, "rung": 4})

    def test_question_ids_and_the_skill_order(self):
        self.assertEqual(seed._question_ids({"id": "BO01", "type": "build_order"}), ["BO01"])
        self.assertIn("build_order", seed.NON_MCQ_TYPES)
        self.assertEqual(seed.SKILL_ORDER, ["listening", "reading", "build", "writing", "speaking"])
        self.assertIn("build_order", weakness.ERROR_LABELS)


class B1BuildContentTests(unittest.TestCase):
    def test_the_seed_has_no_problems(self):
        self.assertEqual(BUNDLE.problems, [])

    def test_every_grammar_unit_has_sentence_building_tile_exercises(self):
        grammar_units = [r for r in BUNDLE.lessons if r.seed.grammar]
        self.assertEqual(len(grammar_units), 28)
        for r in grammar_units:
            built = [e for e in r.practice["items"] if e["type"] == "build_order"]
            self.assertGreaterEqual(len(built), 2, r.seed.slug)
            for e in built:
                self.assertEqual(e["skill"], "build")
                self.assertEqual(e["rung"], 1)
                self.assertTrue(e["tiles"] and e["answers"], e["id"])


class BuildAnswerTests(unittest.IsolatedAsyncioTestCase):
    PROFILE = SimpleNamespace(id=uuid.UUID(int=9))

    def db(self, lesson):
        db = mock.MagicMock()
        db.get = mock.AsyncMock(return_value=lesson)
        row = mock.MagicMock()
        row.scalar_one_or_none.return_value = None
        row.scalars.return_value.all.return_value = []
        db.execute = mock.AsyncMock(return_value=row)
        db.add = mock.MagicMock()
        db.commit = mock.AsyncMock()
        return db

    async def test_a_wrong_tile_order_is_filed_under_viet_with_the_sentence_it_wanted(self):
        r = BUNDLE.lessons[0]
        lesson = SimpleNamespace(id=7, content_hash=r.content_hash, practice=r.practice, title=r.seed.title)
        ex = next(e for e in r.practice["items"] if e["type"] == "build_order")
        db = self.db(lesson)
        body = ExerciseAnswerRequest(exercise_id=ex["id"], question_id=ex["id"], correct=False, answer="Wrong tile order.")
        with mock.patch.object(content, "_linked_grammar_ids", mock.AsyncMock(return_value=[(42, r.seed.grammar[0].pattern)])):
            await content.answer_lesson_question(7, body, db, self.PROFILE)
        log = next(c.args[0] for c in db.add.call_args_list if isinstance(c.args[0], ErrorLog))
        self.assertEqual((log.skill, log.error_type, log.mode), ("viết", "build_order", "writing"))
        self.assertEqual(log.example_ko, ex["answers"][0])

    async def test_a_tile_exercise_is_one_question(self):
        r = BUNDLE.lessons[0]
        index = seed.question_index(r.practice)
        self.assertEqual(index["B1U01B1"]["id"], "B1U01B1")
        self.assertEqual(index["B1U01F1:㉠"]["id"], "B1U01F1")


if __name__ == "__main__":
    unittest.main()

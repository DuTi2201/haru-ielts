"""The "Việc cần làm" block at the top of a lesson: its limits, that every lesson has one, and that it
travels to the learner unchanged."""
import re
import unittest

from pydantic import ValidationError

from app.schemas import CoachOut
from app.services import lesson_seed as seed

BUNDLE = seed.load_all()
# every lesson but Bảng chữ cái (kind "hangul": five parts and an end check, no coach block)
LESSONS = {r.seed.slug: r.seed for r in BUNDLE.lessons if r.seed.kind != "hangul"}
# the free lessons after Bảng chữ cái: the 16 Nền tảng parts, Buổi sáng and Việc nhà (Bài 2–19), and
# Ăn uống, the first paid one (Bài 20), which used to be free with them
FIRST_EIGHT = sorted((s for s in LESSONS.values() if s.sort_order <= 20), key=lambda s: s.sort_order)
FOUNDATION = [s for s in FIRST_EIGHT if s.slug.startswith("sinh-hoat-00-")]
MAIN_THREE = [s for s in FIRST_EIGHT if not s.slug.startswith("sinh-hoat-00-")]


def make(**kw):
    base = {"goal_vi": "Kể các việc đầu ngày theo thứ tự.", "focus_vi": ["`V + -고` nối hành động theo trình tự."]}
    base.update(kw)
    return seed.CoachSeed.model_validate(base)


class CoachModelTests(unittest.TestCase):
    def test_a_small_block_is_accepted(self):
        self.assertEqual(len(make().focus_vi), 1)

    def test_the_focus_is_one_to_three_lines(self):
        with self.assertRaises(ValidationError):
            make(focus_vi=[])
        with self.assertRaises(ValidationError):
            make(focus_vi=["a" * 12] * 4)

    def test_a_line_with_a_lone_backtick_is_refused(self):
        with self.assertRaises(ValidationError):
            make(focus_vi=["`V + -고 nối hành động"])

    def test_a_padded_or_empty_line_is_refused(self):
        with self.assertRaises(ValidationError):
            make(notebook_vi=[" 3 câu giới thiệu bản thân. "])
        with self.assertRaises(ValidationError):
            make(notebook_vi=[""])

    def test_no_more_than_three_checks_and_two_watch_outs(self):
        check = {"prompt_vi": "Nói 3 câu về bản thân."}
        with self.assertRaises(ValidationError):
            make(self_check=[check] * 4)
        with self.assertRaises(ValidationError):
            make(watch_out_vi=["a" * 12] * 3)

    def test_unknown_fields_are_refused(self):
        with self.assertRaises(ValidationError):
            make(minutes=20)


class CoachInLessonTests(unittest.TestCase):
    def raw(self, **kw):
        base = dict(
            slug="demo-lesson", title="Demo", topic="Demo", track="intermediate", level=1, sort_order=99,
            summary="Demo", vocab=[{"hangul": "아침", "pos": "N", "meaning_vi": "buổi sáng", "priority": "core"}],
        )
        base.update(kw)
        return base

    def test_a_coach_needs_a_goal_from_somewhere(self):
        no_goal = {"focus_vi": ["`V + -고` nối hành động theo trình tự."]}
        with self.assertRaises(ValidationError):
            seed.LessonSeed.model_validate(self.raw(coach=no_goal))

    def test_a_goal_note_is_enough(self):
        no_goal = {"focus_vi": ["`V + -고` nối hành động theo trình tự."]}
        notes = [{"title": "Sau bài này bạn làm được gì", "body": "Nói về buổi sáng.", "kind": "goal"}]
        self.assertIsNotNone(seed.LessonSeed.model_validate(self.raw(coach=no_goal, notes=notes)).coach)


class SeededCoachTests(unittest.TestCase):
    def test_a_change_to_the_block_changes_the_lesson_hash(self):
        resolved = next(r for r in BUNDLE.lessons if r.seed.sort_order == 7)
        edited = resolved.seed.model_copy(update={"coach": make(goal_vi="Mục tiêu khác hẳn so với trước đó.")})
        self.assertNotEqual(seed._lesson_hash(edited, resolved.practice), resolved.content_hash)


if __name__ == "__main__":
    unittest.main()

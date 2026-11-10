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
    def test_every_lesson_has_a_coach_block(self):
        self.assertEqual(len(LESSONS), 82)
        for s in LESSONS.values():
            self.assertIsNotNone(s.coach, s.slug)

    def test_the_first_eight_lessons_are_the_free_ones(self):
        self.assertEqual(len(FIRST_EIGHT), 19)
        self.assertEqual(len(FOUNDATION), 16)
        self.assertEqual(len(MAIN_THREE), 3)

    def test_a_lesson_with_a_goal_note_does_not_repeat_it_in_the_block(self):
        # many lessons already open with «Sau bài này bạn làm được gì» / «Mục tiêu của bài»: the block
        # then holds no goal of its own; a lesson without such a note states its goal in the block
        for s in LESSONS.values():
            if any(n.kind == "goal" for n in s.notes):
                self.assertIsNone(s.coach.goal_vi, s.slug)
            else:
                self.assertTrue(s.coach.goal_vi, s.slug)

    def test_the_foundation_lessons_keep_their_own_goal_note(self):
        for s in FOUNDATION:
            self.assertIsNone(s.coach.goal_vi, s.slug)
            self.assertTrue(any(n.kind == "goal" for n in s.notes), s.slug)

    def test_the_block_holds_no_counts(self):
        # "bài này có N từ / mẫu / câu": the screen counts the lesson's words, cards and questions itself,
        # so the text can never disagree with it (a task such as "viết 5 câu" is not a count)
        for s in LESSONS.values():
            lines = [s.coach.goal_vi or "", s.coach.tip_vi or "", *s.coach.focus_vi, *s.coach.watch_out_vi, *s.coach.notebook_vi]
            for line in lines:
                self.assertNotRegex(line, r"(?i)\b(bài này )?có \d+ (từ|mẫu|câu)\b", s.slug)

    def test_a_focus_line_names_a_form_of_the_lesson(self):
        # the block points at the lesson's own cards: every non-review lesson names at least one of its
        # grammar patterns (or a piece of one) between backticks in the focus lines
        for s in LESSONS.values():
            if s.kind == "review" or not s.grammar:
                continue
            focus = " ".join(s.coach.focus_vi)
            pieces = set()
            for g in s.grammar:
                for part in re.split(r"\s*[·+]\s*|\s+", g.pattern):
                    part = part.strip("() ")
                    if len(part) >= 2 and not part.isascii():
                        pieces.add(part)
            self.assertTrue(any(p in focus for p in pieces), s.slug)

    def test_the_block_reaches_the_learner_unchanged(self):
        for s in LESSONS.values():
            dumped = s.coach.model_dump(mode="json", exclude_none=True)
            out = CoachOut.model_validate(dumped)
            self.assertEqual(out.focus_vi, s.coach.focus_vi)
            self.assertEqual([c.prompt_vi for c in out.self_check], [c.prompt_vi for c in s.coach.self_check])

    def test_a_change_to_the_block_changes_the_lesson_hash(self):
        resolved = next(r for r in BUNDLE.lessons if r.seed.sort_order == 7)
        edited = resolved.seed.model_copy(update={"coach": make(goal_vi="Mục tiêu khác hẳn so với trước đó.")})
        self.assertNotEqual(seed._lesson_hash(edited, resolved.practice), resolved.content_hash)


if __name__ == "__main__":
    unittest.main()

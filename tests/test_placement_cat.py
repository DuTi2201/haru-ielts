"""The adaptive entry check (app.services.placement_cat) and its routes (app.api.routers.onboarding)."""
import random
import unittest
from unittest import mock

from app.services import placement_cat as cat
from app.services import roadmap
from tests.test_billing_settings import API, SettingsCase


def take(bank, frontier, self_level, rng, skip=0.5):
    """A simulated learner who can do the lessons before `frontier` (with slips) and guesses or
    skips the others."""
    answers = []
    while True:
        p = cat.posterior(bank, answers, self_level)
        if cat.done(p, len(answers), cat.skipped_at_start(bank, answers)):
            return answers
        q = cat.next_question(bank, answers, p)
        if q.rung < frontier:
            choice = q.answer if rng.random() < 0.85 else "x"
        else:
            choice = "" if rng.random() < skip else (q.answer if rng.random() < 0.25 else "x")
        answers.append(cat.Answer(q.ref, choice))


class EngineTests(unittest.TestCase):
    def setUp(self):
        self.bank = cat.bank()

    def test_the_bank_is_the_lessons_own_questions_and_shows_no_answer(self):
        self.assertGreater(len(self.bank.ladder), 40)
        self.assertGreater(len(self.bank.by_ref), 300)
        self.assertFalse(any(r.slug.startswith("viet-nghi-luan-") for r in self.bank.ladder))
        for q in list(self.bank.by_ref.values())[:200]:
            shown = q.exercise["questions"][0]
            self.assertNotIn("answer", shown)
            self.assertNotIn("explanation_vi", shown)
            self.assertEqual(len(shown["options"]), 4)
            self.assertNotIn("title_vi", q.exercise)

    def test_a_beginner_who_skips_is_done_in_a_few_questions_and_starts_at_the_first_lesson(self):
        answers = []
        for _ in range(cat.MAX_ITEMS):
            p = cat.posterior(self.bank, answers, "basic")
            if cat.done(p, len(answers), cat.skipped_at_start(self.bank, answers)):
                break
            answers.append(cat.Answer(cat.next_question(self.bank, answers, p).ref, ""))
        self.assertLessEqual(len(answers), 5)
        res = cat.conclude(self.bank, answers, "basic")
        self.assertEqual((res.frontier, res.level_label), (0, cat.NEW_LABEL))
        self.assertEqual(res.start, self.bank.ladder[0])

    def test_it_is_short_and_lands_near_the_truth_across_levels(self):
        rng = random.Random(7)
        n, near = [], []
        top = len(self.bank.ladder)
        for t in range(0, top + 1, 4):
            for s in ("basic", "elementary", "intermediate", "advanced"):
                answers = take(self.bank, t, s, rng)
                n.append(len(answers))
                near.append(abs(cat.conclude(self.bank, answers, s).frontier - t) <= 4)
        self.assertLessEqual(max(n), cat.MAX_ITEMS)
        self.assertLess(sum(n) / len(n), 10.5)
        self.assertGreater(sum(near) / len(near), 0.7)

    def test_no_question_is_asked_twice(self):
        answers = take(self.bank, 20, "elementary", random.Random(3))
        self.assertEqual(len({a.ref for a in answers}), len(answers))

    def test_misses_below_the_start_are_named_as_gaps(self):
        b = self.bank
        # right on everything up to rung 12, except two misses on rungs 3 and 6
        answers = []
        for r in (10, 3, 6, 11, 8, 12, 9):
            q = b.by_rung[r][0]
            answers.append(cat.Answer(q.ref, "x" if r in (3, 6) else q.answer))
        res = cat.conclude(b, answers, "elementary")
        self.assertIn(res.advice, ("fill_gaps", "restart_from"))
        self.assertTrue({b.ladder[3].slug, b.ladder[6].slug} & {g.slug for g, _ in res.gaps})


class RoadmapTests(unittest.TestCase):
    def test_weeks_and_the_exam_follow_from_the_minutes(self):
        course = [roadmap.CourseLesson(i, i, f"sinh-hoat-{i:02d}", f"Bài {i}", "lesson", 30, 6, 40) for i in range(1, 11)]
        from datetime import datetime, timedelta, timezone

        now = datetime(2026, 10, 30, tzinfo=timezone.utc)
        p = roadmap.plan(course, 3, "topik5", 15, now + timedelta(weeks=2), now, free_max=8)
        self.assertEqual(p.lessons, 8)
        per = roadmap.lesson_minutes(course[0])
        self.assertEqual(p.minutes, 8 * per)
        self.assertGreater(p.weeks, 2)
        self.assertIsNotNone(p.need_daily)
        self.assertGreater(p.need_daily, 15)
        self.assertEqual([x["free"] for x in p.first], [True, True, True])

    def test_gemini_words_that_run_long_fall_back_to_plain_ones(self):
        self.assertIsNone(roadmap.parse('{"headline": "' + "x" * 300 + '", "tips": []}'))
        self.assertIsNone(roadmap.parse("not json"))
        ok = roadmap.parse('{"headline": "Bạn ở mức Sơ cấp.", "tips": ["Học 15 phút mỗi ngày."]}')
        self.assertEqual(ok["by"], "gemini")


class RouteTests(SettingsCase):
    async def test_survey_questions_result_and_the_plan_starts_there(self):
        learner = await self.new_profile()
        h = self.auth(learner)
        rng = random.Random(11)
        answers = []
        b = cat.bank()
        frontier = 30
        while True:
            r = await self.http.post(API + "/me/placement/next", headers=h, json={"self_level": "intermediate", "answers": answers})
            self.assertEqual(r.status_code, 200, r.text)
            step = r.json()
            if step["done"]:
                break
            self.assertNotIn("answer", step["item"]["exercise"]["questions"][0])
            q = b.by_ref[step["item"]["ref"]]
            right = q.rung < frontier and rng.random() < 0.9
            answers.append({"ref": q.ref, "choice": q.answer if right else ""})
        self.assertLessEqual(len(answers), cat.MAX_ITEMS)
        body = {"survey": {"purpose": "topik4", "self_level": "intermediate", "daily_minutes": 30}, "answers": answers}
        with mock.patch.object(roadmap, "prompt", side_effect=AssertionError("no model in tests")), mock.patch(
            "app.api.routers.onboarding.settings.GEMINI_API_KEY", ""
        ):
            r = await self.http.post(API + "/me/placement/adaptive", headers=h, json=body)
        self.assertEqual(r.status_code, 200, r.text)
        out = r.json()
        self.assertTrue(out["tested"])
        self.assertEqual(out["words_by"], "rules")
        self.assertIsNotNone(out["start_lesson_id"])
        self.assertGreater(out["lessons_to_goal"], 0)
        self.assertEqual(out["daily_minutes"], 30)
        latest = (await self.http.get(API + "/me/placement/adaptive", headers=h)).json()
        self.assertEqual(latest["start_lesson_id"], out["start_lesson_id"])
        old = (await self.http.get(API + "/me/placement", headers=h)).json()
        self.assertEqual(old["start_label"], out["level_label"])

    async def test_a_new_learner_is_not_tested_and_a_made_up_question_is_refused(self):
        h = self.auth(await self.new_profile())
        r = await self.http.post(API + "/me/placement/next", headers=h, json={"self_level": "new", "answers": []})
        self.assertTrue(r.json()["done"])
        r = await self.http.post(API + "/me/placement/adaptive", headers=h,
                                 json={"survey": {"purpose": "talk", "self_level": "new", "daily_minutes": 15}, "answers": []})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual((r.json()["tested"], r.json()["level_label"]), (False, cat.NEW_LABEL))
        bad = await self.http.post(API + "/me/placement/next", headers=h, json={"self_level": "basic", "answers": [{"ref": "x/y", "choice": "1"}]})
        self.assertEqual(bad.status_code, 422)

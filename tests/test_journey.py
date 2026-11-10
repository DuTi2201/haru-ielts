"""Hành trình Thiên Nga (app/services/journey.py): days studied, stages, the curse."""
import unittest
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import delete, select

from app.models import Journey, LearnerDay, Lesson, LessonPartDone
from app.services import journey
from tests.test_billing_settings import API, SettingsCase

T = date(2026, 10, 29)


def days(*ago: int) -> set[date]:
    return {T - timedelta(days=n) for n in ago}


class Rules(unittest.TestCase):
    def test_days_away(self):
        self.assertEqual(journey.missed_days(days(0, 1), T), 0)
        self.assertEqual(journey.missed_days(days(1, 2), T), 0)  # yesterday: today is still open
        self.assertEqual(journey.missed_days(days(2), T), 1)
        self.assertEqual(journey.missed_days(days(5, 6), T), 4)
        self.assertEqual(journey.missed_days(set(), T), 0)  # a new learner is not punished

    def test_streak(self):
        self.assertEqual(journey.streak(days(0, 1, 2, 4), T), 3)
        self.assertEqual(journey.streak(days(1, 2), T), 2)
        self.assertEqual(journey.streak(days(2, 3), T), 0)

    def test_the_curse_falls_after_four_days_and_lifts_after_two(self):
        self.assertFalse(journey.is_cursed(days(4), T))  # 3 days away
        self.assertTrue(journey.is_cursed(days(5), T))  # 4 days away
        self.assertTrue(journey.is_cursed(days(0, 6), T))  # back today after 5 days: not yet
        self.assertFalse(journey.is_cursed(days(0, 1, 7), T))  # two days in a row: lifted
        self.assertFalse(journey.is_cursed(days(0, 2), T))  # a 1-day gap never curses

    def test_the_shield_forgives_one_day_off_a_week(self):
        # T is a Thursday. Studied Mon-Tue, off Wednesday: shielded, so nothing is missed
        study = days(3, 2)
        self.assertEqual(journey.shielded_days(study, T), days(1))
        covered = study | journey.shielded_days(study, T)
        self.assertEqual(journey.missed_days(covered, T), 0)
        self.assertEqual(journey.kept_streak(study, covered, T), 2)  # bridged, not counted
        # studied today too: the run goes on through the shielded day
        study = days(3, 2, 0)
        covered = study | journey.shielded_days(study, T)
        self.assertEqual(journey.kept_streak(study, covered, T), 3)

    def test_the_shield_is_once_a_week_and_never_hides_an_absence(self):
        # off Tuesday (shielded) and Wednesday (counts): one day missed
        study = days(3)
        shields = journey.shielded_days(study, T)
        self.assertEqual(shields, days(2))
        self.assertEqual(journey.missed_days(study | shields, T), 1)
        # Sun, Tue, Thu studied: off Monday (shielded) and Wednesday (the week's shield is gone)
        self.assertEqual(journey.shielded_days(days(4, 2, 0), T), days(3))
        # Sat, Mon, Tue, Thu studied: off Sunday (last week's shield) and Wednesday (this week's)
        self.assertEqual(journey.shielded_days(days(5, 3, 2, 0), T), days(4, 1))
        # today is never shielded
        self.assertEqual(journey.shielded_days(days(1), T), set())



class JourneyDb(SettingsCase):
    async def asyncTearDown(self):
        async with self.factory() as db:
            await db.execute(delete(LearnerDay).where(LearnerDay.learner_id.in_(self.profile_ids)))
            await db.execute(delete(Journey).where(Journey.learner_id.in_(self.profile_ids)))
            await db.execute(delete(LessonPartDone).where(LessonPartDone.learner_id.in_(self.profile_ids)))
            await db.commit()
        await super().asyncTearDown()

    async def test_a_stage_reached_is_kept(self):
        p = await self.new_profile()
        async with self.factory() as db:
            st = await journey.compute(db, p.id, 3, 130)
            await db.commit()
        self.assertEqual((st.stage, st.raised), (3, True))
        async with self.factory() as db:
            st = await journey.compute(db, p.id, 2, 130)  # lessons were added to a chapter: the stage stays
        self.assertEqual((st.stage, st.raised, st.name), (3, False, "Vượt hồ đêm"))

    async def test_relics_and_sparkle_are_kept_for_good(self):
        p = await self.new_profile()
        async with self.factory() as db:
            st = await journey.compute(db, p.id, 1, 0, relics=["mirror"], sparkle=2)
            await db.commit()
        self.assertEqual((st.stage, st.relics, st.sparkle), (1, ["mirror"], 2))
        async with self.factory() as db:
            # a reading lesson was added: the topic is no longer finished, the starlight share fell
            st = await journey.compute(db, p.id, 1, 0, relics=[], sparkle=1)
            await db.commit()
        self.assertEqual((st.relics, st.sparkle), (["mirror"], 2))

    async def test_away_too_long_the_swan_shows_a_stage_back(self):
        p = await self.new_profile()
        now = datetime(2026, 10, 29, 5, tzinfo=timezone.utc)
        async with self.factory() as db:
            db.add(Journey(learner_id=p.id, stage=4))
            db.add(LearnerDay(learner_id=p.id, day=date(2026, 10, 23)))
            await db.commit()
        async with self.factory() as db:
            st = await journey.compute(db, p.id, 1, 0, now=now)
        # away since the 23rd: the shield forgives the 24th, the next four days count
        self.assertEqual((st.stage, st.shown_stage, st.missed_days, st.cursed), (4, 3, 4, True))

    async def test_studying_marks_the_day_once_and_the_plan_shows_it(self):
        p = await self.new_profile()
        async with self.factory() as db:
            await journey.mark(db, p.id)
            await journey.mark(db, p.id)
            await db.commit()
            n = (await db.execute(select(LearnerDay).where(LearnerDay.learner_id == p.id))).scalars().all()
        self.assertEqual(len(n), 1)
        r = await self.http.get(API + "/me/plan", headers=self.auth(p))
        self.assertEqual(r.status_code, 200, r.text)
        j = r.json()["journey"]
        self.assertEqual((j["stage"], j["studied_today"], j["missed_days"], j["next_readiness"]), (1, True, 0, None))
        self.assertEqual([c["n"] for c in j["chapters"]], [1, 2, 3, 4])
        self.assertEqual((j["chapters"][0]["earned"], j["chapters"][0]["lessons"], j["sparkle"]), (0, 19, 0))  # chapter I: Bảng chữ cái, the 16 Nền tảng parts, Buổi sáng, Việc nhà
        self.assertEqual({c["code"] for c in j["constellations"]}, {"compass", "quill", "mirror"})
        self.assertEqual(r.json()["streak_days"], 1)

    async def test_a_part_of_the_alphabet_lesson_gives_its_feather(self):
        p = await self.new_profile()
        async with self.factory() as db:
            lid = (await db.execute(select(Lesson.id).where(Lesson.slug == "hangul-00-bang-chu-cai"))).scalar_one()
        r = await self.http.get(f"{API}/lessons/{lid}/study", headers=self.auth(p))
        self.assertEqual(r.status_code, 200, r.text)
        before = r.json()
        self.assertEqual((before["chapter"], [f["earned"] for f in before["feathers"]]), (1, [False] * 6))
        for _ in range(2):  # twice changes nothing
            r = await self.http.post(f"{API}/lessons/{lid}/parts/p1", headers=self.auth(p))
            self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual([f["earned"] for f in r.json()], [True] + [False] * 5)
        r = await self.http.post(f"{API}/lessons/{lid}/parts/p9", headers=self.auth(p))
        self.assertEqual(r.status_code, 404)
        r = await self.http.get(API + "/me/plan", headers=self.auth(p))
        self.assertEqual(r.json()["journey"]["chapters"][0]["earned"], 1)

    async def test_the_study_routes_count_the_day(self):
        from app.api.deps import study_day
        from app.main import app

        want = {
            "answer_lesson_question", "record_item_review", "answer_exam_drill", "answer_writing_drill",
            "finish_daily_reading", "answer", "finish", "finish_conversation", "check_pronunciation",
            "add_attempt", "finish_debate", "submit_placement", "finish_lesson_part",
        }
        found = set()
        for route in app.routes:
            name = getattr(getattr(route, "endpoint", None), "__name__", "")
            dep = getattr(route, "dependant", None)
            if dep and any(d.call is study_day for d in dep.dependencies):
                found.add(name)
        self.assertTrue(want <= found, want - found)

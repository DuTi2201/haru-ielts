"""Vừa sức / Thử thách, the first meeting of a question type, and the help before a hard item
(app/services/practice_tiers.py) — on the real seed, so a stale measure fails here."""
import unittest
from types import SimpleNamespace
from unittest import mock

from app.api.routers import content
from app.services import feathers, practice_tiers as pt
from app.services.lesson_seed import load_all

BUNDLE = load_all()
BY_SLUG = {r.seed.slug: r for r in BUNDLE.lessons}
L01 = BY_SLUG["sinh-hoat-01-buoi-sang"]


def items_of(slug):
    return BY_SLUG[slug].practice["items"]


class SeedTests(unittest.TestCase):
    def test_the_measures_and_the_support_are_in_step_with_the_seed(self):
        self.assertEqual(pt.stale(), [])

    def test_every_type_met_first_has_a_one_line_guide(self):
        guides = pt.type_guides()
        for t in pt._tiers()["first_seen"]:
            self.assertIn(t, guides)
            self.assertTrue(guides[t]["how_vi"])

    def test_the_hard_passages_of_lesson_01_come_last_in_their_skill(self):
        items = items_of("sinh-hoat-01-buoi-sang")
        tier = {it["id"]: it.get("tier") for it in items}
        for hard in ("L16-17", "R14", "R16", "W52"):
            self.assertEqual(tier[hard], "challenge", hard)
        for easy in ("L12", "LN01", "LN03", "D04", "R10", "E05a", "KR01"):
            self.assertEqual(tier[easy], "warm", easy)
        for skill in ("listening", "reading", "writing"):
            tiers = [it.get("tier") for it in items if it["skill"] == skill]
            self.assertEqual(tiers, sorted(tiers, key=lambda t: t == "challenge"), skill)

    def test_sentence_building_keeps_its_ladder(self):
        built = [it for it in items_of("sinh-hoat-01-buoi-sang") if it["skill"] == "build"]
        self.assertTrue(built)
        self.assertTrue(all("tier" not in it for it in built))
        self.assertEqual([it["id"] for it in built], [i for i in L01.seed.exercise_ids if BUNDLE.exercises[i]["skill"] == "build"])

    def test_reviews_and_the_alphabet_are_left_as_written(self):
        for r in BUNDLE.lessons:
            if (r.practice or {}).get("kind") in ("review", "hangul"):
                self.assertEqual([it["id"] for it in r.practice["items"]], r.seed.exercise_ids, r.seed.slug)
                self.assertNotIn("type_intro", r.practice)

    def test_lesson_01_introduces_the_types_it_brings_in(self):
        intro = L01.practice["type_intro"]
        for t in ("read_main_idea", "read_mood", "listen_interview", "listen_dictation"):
            self.assertIn(t, intro)
        self.assertNotIn("read_cloze", intro)  # met in the foundation lessons
        # each type is introduced once in the whole course
        seen: dict[str, str] = {}
        for r in BUNDLE.lessons:
            for t in (r.practice or {}).get("type_intro", {}):
                self.assertNotIn(t, seen, f"{t} introduced by {seen.get(t)} and {r.seed.slug}")
                seen[t] = r.seed.slug

    def test_feathers_follow_the_new_order(self):
        qs = [q for f in feathers.partition([], [], L01.practice) if f.kind == "practice" for q in f.questions]
        listening = [q for it in items_of("sinh-hoat-01-buoi-sang") if it["skill"] == "listening" for q in content.lesson_seed.question_ids(it)]
        self.assertEqual(qs[: len(listening)], listening)

    def test_support_rides_only_in_its_own_lesson(self):
        r10 = {r.seed.slug: next(it for it in r.practice["items"] if it["id"] == "R10") for r in BUNDLE.lessons if "R10" in r.seed.exercise_ids}
        self.assertIn("support", r10["sinh-hoat-01-buoi-sang"])
        self.assertNotIn("support", r10["sinh-hoat-03-an-uong"])  # there -(으)면 is not "ahead" any more
        sup = r10["sinh-hoat-01-buoi-sang"]["support"]
        self.assertEqual(sup["elim"], {"R10": "1"})
        self.assertEqual(len(sup["options_vi"]["R10"]), 4)


class SupportCheckTests(unittest.TestCase):
    def check(self, sup, item=None):
        item = item or {
            "id": "X1", "skill": "reading", "type": "read_cloze",
            "stimulus": {"kind": "cloze", "text": "아침을 먹지 않으면 점심에 ( ) 쉽다."},
            "questions": [{"id": "X1", "options": [{"id": "1", "text": "가"}, {"id": "2", "text": "나"}], "answer": "2"}],
        }
        with mock.patch.object(pt, "supports", return_value={"b": {"X1": pt.Support.model_validate(sup)}}):
            return pt.support_problems({("b", "X1"): item}, {"a": 1, "b": 2, "c": 3})

    def test_a_clean_entry(self):
        sup = {
            "words": [{"ko": "점심", "seen": "점심에", "vi": "bữa trưa"}],
            "grammar": [{"form": "-(으)면", "seen": "않으면", "vi": "nếu", "lesson": "c"}],
            "focus_vi": "…", "options_vi": {"X1": ["a", "b"]}, "elim": {"X1": "1"},
        }
        self.assertEqual(self.check(sup), [])

    def test_mistakes_are_caught(self):
        sup = {
            "words": [{"ko": "저녁", "seen": "저녁에", "vi": "bữa tối"}],
            "grammar": [{"form": "-(으)면", "seen": "않으면", "vi": "nếu", "lesson": "a"}, {"form": "-고", "seen": "x", "vi": "và", "lesson": "zz"}],
            "focus_vi": "…", "options_vi": {"X1": ["a"]}, "elim": {"X1": "2"},
        }
        problems = "\n".join(self.check(sup))
        for needle in ("word '저녁에'", "not ahead", "unknown lesson zz", "grammar 'x'", "2 options, 1 translations", "crosses out the right answer"):
            self.assertIn(needle, problems)


class EndpointTests(unittest.IsolatedAsyncioTestCase):
    async def test_the_practice_carries_tiers_intros_and_the_lessons_that_teach_the_grammar(self):
        db = mock.MagicMock()
        db.get = mock.AsyncMock(return_value=SimpleNamespace(id=7, practice=L01.practice, sort_order=L01.seed.sort_order))
        lessons = mock.MagicMock()
        lessons.all.return_value = [("sinh-hoat-02-viec-nha", 12, "Việc nhà")]
        none = mock.MagicMock()
        none.all.return_value = []

        async def execute(stmt):
            return lessons if "content.lesson.title" in str(stmt) else none

        db.execute = mock.AsyncMock(side_effect=execute)
        out = await content.get_lesson_practice(7, SimpleNamespace(headers={}), db)
        self.assertIn("read_main_idea", out.type_intro)
        r10 = next(it for it in out.items if it["id"] == "R10")
        g = next(g for g in r10["support"]["grammar"] if g["lesson"] == "sinh-hoat-02-viec-nha")
        self.assertEqual((g["lesson_id"], g["lesson_title"]), (12, "Việc nhà"))
        ahead = next(g for g in r10["support"]["grammar"] if g["lesson"] is None)
        self.assertIsNone(ahead["lesson_id"])
        self.assertNotIn("lesson_id", L01.practice["items"][0].get("support", {}).get("grammar", [{}])[0])  # the seed is not changed


if __name__ == "__main__":
    unittest.main()

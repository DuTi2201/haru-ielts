"""The topic review lesson ("Ôn tập chủ đề"): the seed hangs together with the topic's cards,
a broken review is rejected by the loader, the Today reminder appears once a topic's grammar
has been met, and the picker / lecture treat the lesson as the special case it is."""
import copy
import json
import re
import shutil
import tempfile
import unittest
import uuid
from collections import Counter
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from fastapi import HTTPException
from pydantic import ValidationError

from app.api.routers import audio, content
from app.schemas import PodcastRequest
from app.services import lesson_seed as seed

BUNDLE = seed.load_all()
REVIEWS = [r for r in BUNDLE.lessons if r.seed.kind == "review"]


def _supplement_patterns() -> set[str]:
    """The 🟣 cards added from the TOPIK II grammar list: each has its own question in its lesson."""
    return {g.pattern for r in BUNDLE.lessons for g in r.seed.grammar if (g.source or "").startswith("EXT-SUP-")}


def _lesson_cards(slug_prefix_of_review):
    """Grammar cards of the lessons of the same topic and bank as a review lesson."""
    review = next(r for r in REVIEWS if r.seed.slug == slug_prefix_of_review)
    return [
        g
        for r in BUNDLE.lessons
        if r.seed.kind == "lesson" and r.seed.topic == review.seed.topic and r.seed.bank == review.seed.bank
        for g in r.seed.grammar
    ]


class ReviewSeedTests(unittest.TestCase):
    def test_each_topic_has_one_review_lesson_that_is_last(self):
        self.assertEqual(len(REVIEWS), 5)
        for review in REVIEWS:
            siblings = [r.seed for r in BUNDLE.lessons if r.seed.topic == review.seed.topic]
            self.assertEqual(max(s.sort_order for s in siblings), review.seed.sort_order)
            self.assertEqual([s.kind for s in siblings].count("review"), 1)
            self.assertEqual((review.seed.vocab, review.seed.grammar), ([], []))

    def test_the_map_names_every_card_of_the_topic_exactly_once(self):
        for review in REVIEWS:
            cards = [g.pattern for g in _lesson_cards(review.seed.slug)]
            mapped = [p for f in review.seed.review.functions for p in f.patterns]
            self.assertEqual(sorted(mapped), sorted(cards), review.seed.slug)
            self.assertEqual(len(mapped), len(set(mapped)))

    # the mock is every multiple-choice question of the review. Topics 1 and 2 are built like a
    # TOPIK I paper (30 listening + 40 reading); topics 3, 4 and 5 are shorter sets (10 + 16, 10 + 20, 12 + 28)
    MOCK_SHAPE = {
        "sinh-hoat-10-on-tap-chu-de": (30, 40),
        "quan-he-12-on-tap-chu-de": (30, 40),
        "nhap-canh-06-on-tap-chu-de": (10, 16),
        "cong-so-08-on-tap-chu-de": (10, 20),
        "xa-hoi-21-on-tap-chu-de": (12, 28),
    }

    def test_the_mock_is_listening_then_reading_with_spread_answers(self):
        for review in REVIEWS:
            mock_ids = review.practice["review"]["mock"]["question_ids"]
            listening, reading = self.MOCK_SHAPE[review.seed.slug]
            self.assertEqual(len(mock_ids), listening + reading, review.seed.slug)
            by_id = {q["id"]: it["skill"] for it in review.practice["items"] for q in it.get("questions", [])}
            self.assertEqual([by_id[i] for i in mock_ids], ["listening"] * listening + ["reading"] * reading)  # listening first
            answers = Counter(
                q["answer"]
                for it in review.practice["items"]
                if it["type"] not in seed.NON_MCQ_TYPES
                for q in it["questions"]
            )
            self.assertEqual(set(answers), {"1", "2", "3", "4"})
            fair = -(-len(mock_ids) // 4)  # the share of an even spread
            self.assertTrue(all(max(3, fair - 2) <= n <= max(7, fair + 2) for n in answers.values()), answers)

    def test_every_mock_question_is_tagged_with_its_cards(self):
        for review in REVIEWS:
            cards = review.practice["review"]["cards"]
            for it in review.practice["items"]:
                if it["type"] in seed.NON_MCQ_TYPES:
                    continue
                for q in it["questions"]:
                    self.assertTrue(q.get("grammar"), q["id"])
                    self.assertTrue(all(p in cards or p in review.practice["grammar"] for p in q["grammar"]))

    def test_each_function_is_tested_and_every_extension_card_is_tested_or_required(self):
        for review in REVIEWS:
            tested = Counter(
                p
                for it in review.practice["items"]
                if it["type"] not in seed.NON_MCQ_TYPES
                for q in it["questions"]
                for p in q.get("grammar", [])
            )
            for f in review.seed.review.functions:
                if f.id == "mo-rong-bo-sung":  # the TOPIK II supplement: tested in the lessons (see below)
                    continue
                self.assertGreaterEqual(sum(tested[p] for p in f.patterns), 2, f"{review.seed.slug}: {f.id}")
            required = {d.pattern for d in review.seed.review.capstone.required}
            # the cards added from the TOPIK II grammar list (EXT-SUP-…) are practised by a question in
            # their own lesson and grouped on the map; the review's mock keeps the shape of a real paper
            added = _supplement_patterns()
            for p, card in review.practice["review"]["cards"].items():
                if card["tier"] == "extension" and p not in added:
                    self.assertTrue(tested[p] or p in required, f"{review.seed.slug}: {p}")

    def test_the_capstone_needs_extension_cards_and_the_model_answers_meet_it(self):
        for review in REVIEWS:
            cap = review.seed.review.capstone
            cards = review.practice["review"]["cards"]
            # a topic with extension cards asks for them; one without asks for a wider set of detectors
            extension = [p for p, c in cards.items() if c["tier"] == "extension" and p not in _supplement_patterns()]
            if extension:  # all of them when the topic has fewer than four
                self.assertGreaterEqual(sum(cards[d.pattern]["tier"] == "extension" for d in cap.required), min(4, len(extension)))
            else:
                self.assertGreaterEqual(len(cap.required), 5, review.seed.slug)
            by_id = {it["id"]: it for it in review.practice["items"]}
            for ex_id in (cap.essay_id, cap.speak_id):
                text = by_id[ex_id]["model_answer_ko"]
                self.assertGreaterEqual(sum(bool(re.search(d.regex, text)) for d in cap.required), cap.min_required)
            essay = by_id[cap.essay_id]["model_answer_ko"]
            self.assertTrue(600 <= len(essay) <= 700, len(essay))

    def test_the_detectors_ignore_words_that_only_look_like_the_pattern(self):
        def hits(slug, pattern_start, text):
            review = next(r for r in REVIEWS if r.seed.slug == slug)
            d = next(d for d in review.seed.review.capstone.required if d.pattern.startswith(pattern_start))
            return bool(re.search(d.regex, text))

        t1, t2 = "sinh-hoat-10-on-tap-chu-de", "quan-he-12-on-tap-chu-de"
        self.assertFalse(hits(t2, "A/V + -기 때문에", "쓰레기 때문에 힘들다"))
        self.assertTrue(hits(t2, "A/V + -기 때문에", "시간이 없기 때문에 힘들다"))
        self.assertFalse(hits(t1, "V/A + -는데도", "습관을 만드는 데도 시간이 필요하다"))
        self.assertTrue(hits(t1, "V/A + -는데도", "충분히 잤는데도 피곤하다"))
        self.assertFalse(hits(t1, "V + -(으)면서", "그렇다면서 웃었다"))
        self.assertFalse(hits(t1, "V + -기로 하다", "여기로 한 번 오세요"))
        self.assertTrue(hits(t1, "V + -기로 하다", "걷기로 했다"))
        t3 = "nhap-canh-06-on-tap-chu-de"
        self.assertTrue(hits(t3, "V + -(으)면 되다", "서류는 내일 내면 됩니다"))
        self.assertFalse(hits(t3, "V + -(으)면 되다", "여기에서 사진을 찍으면 안 됩니다"))
        self.assertTrue(hits(t3, "V + -아/어 두다", "서류를 미리 준비해 두었다"))
        self.assertFalse(hits(t3, "V + -아/어 두다", "이 두 가지를 준비한다"))
        self.assertTrue(hits(t3, "V + -는 게 좋다", "미리 알아 두는 것이 좋다"))
        self.assertFalse(hits(t3, "V + -는 게 좋다", "가는 게 많다"))

    def test_topics_one_and_two_are_scored_like_a_topik_one_paper(self):
        for review in REVIEWS:
            mock = review.practice["review"]["mock"]
            if review.seed.slug.startswith(("nhap-canh", "cong-so", "xa-hoi")):  # TOPIK II topics are not scored like a TOPIK I paper
                self.assertNotIn("score", mock)
                continue
            scale = mock["score"]
            self.assertEqual((scale["listening"], scale["reading"]), (30, 40))
            self.assertEqual(mock["minutes"], 100)  # 40 min listening + 60 min reading in the real paper
            cuts = [b["min_score"] for b in scale["bands"]]
            self.assertEqual(cuts[:3], [0, 80, 140])  # the official cut-offs of level 1 and level 2 (out of 200)
            self.assertIn("ước lượng", scale["note_vi"])
            self.assertIn("TOPIK II", scale["note_vi"])  # says plainly that the real sets of the app are TOPIK II

    def test_the_review_payload_carries_the_map_the_mock_and_the_cards(self):
        for review in REVIEWS:
            payload = review.practice["review"]
            self.assertEqual(review.practice["kind"], "review")
            self.assertEqual(set(payload), {"functions", "mock", "capstone", "cards"})
            self.assertEqual(payload["mock"]["bands"][0]["min_correct"], 0)
            self.assertTrue(all(c["lesson_slug"] for c in payload["cards"].values()))


class ReviewLoaderTests(unittest.TestCase):
    """Edits to a copy of the seed that the loader has to refuse."""

    SLUG = "sinh-hoat-10-on-tap-chu-de"

    def problems_with(self, edit_lesson=None, edit_exercises=None):
        with tempfile.TemporaryDirectory() as tmp:
            copy_dir = Path(tmp) / "seed"
            shutil.copytree(seed.SEED_DIR, copy_dir)
            if edit_lesson:
                path = copy_dir / "lessons" / f"{self.SLUG}.json"
                data = json.loads(path.read_text(encoding="utf-8"))
                edit_lesson(data)
                path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            if edit_exercises:
                path = copy_dir / "exercises" / "reading.json"
                data = json.loads(path.read_text(encoding="utf-8"))
                edit_exercises(data)
                path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            return "\n".join(seed.load_all(copy_dir).problems)

    def test_the_untouched_copy_is_clean(self):
        self.assertEqual(self.problems_with(lambda d: None), "")

    def test_a_card_in_no_function_is_a_problem(self):
        def edit(d):
            d["review"]["functions"][0]["patterns"].pop()

        self.assertIn("cards that are in no function", self.problems_with(edit))

    def test_a_card_in_two_functions_is_a_problem(self):
        def edit(d):
            d["review"]["functions"][1]["patterns"].append(d["review"]["functions"][0]["patterns"][0])

        self.assertIn("a card belongs to one function", self.problems_with(edit))

    def test_a_rule_naming_a_pattern_the_topic_does_not_teach_is_a_problem(self):
        def edit(d):
            d["review"]["functions"][0]["rules"][0]["use"] = ["V + -없는-패턴"]

        self.assertIn("is not a grammar card of the bank", self.problems_with(edit))

    def test_a_capstone_the_model_answer_cannot_meet_is_a_problem(self):
        def edit(d):
            d["review"]["capstone"]["min_required"] = 7
            for r in d["review"]["capstone"]["required"][:4]:
                r["regex"] = "절대로-없는-문장"

        self.assertIn("model answer", self.problems_with(edit))

    def test_a_capstone_pointing_at_the_wrong_exercise_is_a_problem(self):
        def edit(d):
            d["review"]["capstone"]["essay_id"] = "VR01"

        self.assertIn("is not a write_essay", self.problems_with(edit))

    def test_bands_must_start_at_zero_and_ascend(self):
        def edit(d):
            d["review"]["mock"]["bands"][0]["min_correct"] = 2

        self.assertIn("mock bands must start at 0", self.problems_with(edit))

    def test_a_score_scale_that_miscounts_the_skills_is_a_problem(self):
        def edit(d):
            d["review"]["mock"]["score"]["listening"] = 25

        self.assertIn("mock.score says 25 listening", self.problems_with(edit))

    def test_score_bands_must_start_at_zero_and_ascend(self):
        def edit(d):
            d["review"]["mock"]["score"]["bands"][0]["min_score"] = 10

        self.assertIn("score bands must start at 0", self.problems_with(edit))

    def test_duplicate_tags_in_a_question_are_a_problem(self):
        def edit(data):
            q = data["items"][0]["questions"][0]
            q["tags"] = ["-고", "-고"]

        self.assertIn("duplicate tags", self.problems_with(edit_exercises=edit))

    def test_the_two_kinds_are_told_apart(self):
        review = copy.deepcopy(next(r for r in REVIEWS if r.seed.slug == self.SLUG).seed.model_dump(mode="json"))
        lesson = copy.deepcopy(next(r for r in BUNDLE.lessons if r.seed.kind == "lesson").seed.model_dump(mode="json"))
        seed.LessonSeed.model_validate(review)
        no_review = {**review, "review": None}
        with self.assertRaises(ValidationError):
            seed.LessonSeed.model_validate(no_review)
        with self.assertRaises(ValidationError):
            seed.LessonSeed.model_validate({**review, "vocab": lesson["vocab"]})
        with self.assertRaises(ValidationError):
            seed.LessonSeed.model_validate({**lesson, "review": review["review"]})


class TopicReviewTaskTests(unittest.IsolatedAsyncioTestCase):
    """/me/plan offers the review once the learner has met every grammar card of a topic."""

    LEARNER = uuid.uuid4()
    LESSON_ITEMS = {1: [("vocab_item", 1), ("grammar_point", 10)], 2: [("grammar_point", 11)], 9: []}

    def _db(self, reviews, answered):
        db = mock.MagicMock()

        async def execute(stmt):
            text = str(stmt)
            res = mock.MagicMock()
            if "lesson_exercise_result" in text:
                res.all.return_value = answered
            elif "lesson_topic" in text:
                res.all.return_value = [(1, 5, "Chủ đề A"), (2, 5, "Chủ đề A"), (9, 5, "Chủ đề A")]
            else:
                res.all.return_value = reviews
            return res

        db.execute = execute
        return db

    REVIEWS = [(9, "Ôn tập", [f"VL0{i}" for i in range(1, 5)])]

    async def task(self, studied, answered=(), reviews=None):
        reviews = self.REVIEWS if reviews is None else reviews
        return await content._topic_review_task(self._db(reviews, list(answered)), self.LEARNER, self.LESSON_ITEMS, studied)

    async def test_nothing_without_a_review_lesson(self):
        self.assertIsNone(await self.task({("grammar_point", 10), ("grammar_point", 11)}, reviews=[]))

    async def test_not_offered_while_a_card_of_the_topic_is_unmet(self):
        self.assertIsNone(await self.task({("grammar_point", 10)}))

    async def test_offered_when_every_grammar_card_was_met_words_do_not_matter(self):
        t = await self.task({("grammar_point", 10), ("grammar_point", 11)})
        self.assertEqual((t.kind, t.lesson_id, t.status), ("topic_review", 9, "todo"))
        self.assertIn("Chủ đề A", t.title)

    async def test_partly_answered_is_in_progress_and_fully_answered_is_not_offered(self):
        studied = {("grammar_point", 10), ("grammar_point", 11)}
        partial = [(9, "VL01"), (9, "VL02")]
        self.assertEqual((await self.task(studied, partial)).status, "in_progress")
        full = [(9, q) for q in ("VL01", "VL02", "VL03", "VL04")]
        self.assertIsNone(await self.task(studied, full))


class ReviewListAndLectureTests(unittest.IsolatedAsyncioTestCase):
    async def test_the_picker_keeps_the_review_row_and_does_not_track_mastery_for_it(self):
        from tests.test_progress import LessonListTests

        base = LessonListTests("test_anonymous_gets_the_list_without_personal_fields")
        counts = {"items": 22, "questions": 22, "by_skill": {"listening": 4, "reading": 16, "writing": 1, "speaking": 1}}
        review_row = (5, "Ôn tập chủ đề: Du lịch", 3, "du-lich-ontap", None, None, "intermediate", 9, counts, "review")
        with mock.patch.object(LessonListTests, "LESSONS", LessonListTests.LESSONS + [review_row]):
            rows = await content.list_lessons(base._db([]), SimpleNamespace(id=uuid.uuid4()))
        review = next(r for r in rows if r.id == 5)
        self.assertEqual((review.kind, review.mastered, review.vocab_count, review.grammar_count), ("review", None, 0, 0))
        self.assertTrue(all(r.kind == "lesson" for r in rows if r.id != 5))
        self.assertFalse(review.is_next)

    async def test_a_review_lesson_has_no_lecture(self):
        db = mock.MagicMock()
        db.get = mock.AsyncMock(return_value=SimpleNamespace(id=21))
        res = mock.MagicMock()
        res.scalars.return_value.all.return_value = []
        db.execute = mock.AsyncMock(return_value=res)
        with self.assertRaises(HTTPException) as ctx:
            await audio.request_lesson_podcast(21, PodcastRequest(), mock.MagicMock(), db)
        self.assertEqual(ctx.exception.status_code, 404)
        self.assertIn("no lecture", ctx.exception.detail)


if __name__ == "__main__":
    unittest.main()

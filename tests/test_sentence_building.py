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


class PilotContentTests(unittest.TestCase):
    def items(self, slug):
        return LESSONS[slug].practice["items"]

    def test_the_seed_has_no_problems(self):
        self.assertEqual(BUNDLE.problems, [])

    def test_each_lesson_has_all_four_rungs_between_reading_and_writing(self):
        for slug in T1:
            built = [e for e in self.items(slug) if e["skill"] == "build"]
            self.assertEqual({e.get("rung") for e in built}, {1, 2, 3, 4}, slug)
            self.assertGreaterEqual(sum(e["rung"] == 1 for e in built), 5, slug)
            by_skill = LESSONS[slug].practice["counts"]["by_skill"]
            keys = list(by_skill)
            self.assertLess(keys.index("reading"), keys.index("build"), slug)
            self.assertLess(keys.index("build"), keys.index("writing"), slug)
            self.assertEqual(by_skill["build"], sum(len(seed._question_ids(e)) for e in built), slug)

    def test_other_lessons_have_no_build_skill_yet(self):
        for slug, r in LESSONS.items():
            if slug not in T1 and slug not in T2 and slug not in T4 and slug not in TW54 and not slug.startswith(("sinh-hoat-00-", "xa-hoi-")):  # the foundation lessons and the topic-5 lessons build too
                self.assertNotIn("build", r.practice["counts"]["by_skill"], slug)

    def test_every_build_exercise_is_linked_to_a_card_of_its_own_lesson_or_before(self):
        for slug in T1:
            r = LESSONS[slug]
            cards = r.practice["grammar"]
            for e in self.items(slug):
                if e["skill"] != "build":
                    continue
                self.assertTrue(e.get("grammar"), e["id"])
                for p in e["grammar"]:
                    self.assertLessEqual(cards[p]["lesson_order"], r.seed.sort_order, e["id"])

    def test_the_foundation_cards_are_built_core_cards_with_exam_tags(self):
        expected = {
            "sinh-hoat-01-buoi-sang": {"V/A + -았/었-": "kiip-1", "V + -(으)ㄹ 거예요": "kiip-1", "V/A + -(으)ㄹ 때": "kiip-2", "V/A + -지만": "kiip-1"},
            "sinh-hoat-02-viec-nha": {"V + -고 있다": "kiip-2", "V + -(으)ㄹ 수 있다/없다": "kiip-2", "V/A + -(으)면": "kiip-2", "V + -지 마세요": "kiip-1"},
            "sinh-hoat-03-an-uong": {"V + -고 싶다": "kiip-1", "V + -(으)세요": "kiip-1", "V/A + -(으)ㄴ/는/(으)ㄹ 것 같다": "kiip-2", "V + -는 동안": None},
        }
        for slug, want in expected.items():
            cards = {g.pattern: g for g in LESSONS[slug].seed.grammar}
            for pattern, tag in want.items():
                g = cards[pattern]
                self.assertEqual(g.exam, tag, pattern)
                self.assertFalse((g.source or "").startswith("EXT-"), pattern)
                for label in ("**Cấu tạo:**", "**Hoàn cảnh dùng:**", "**Vì sao chọn nó thay vì"):
                    self.assertIn(label, g.usage_context_vi, pattern)
                self.assertGreaterEqual(len(g.contrasts), 2, pattern)
                self.assertTrue(g.note_vi and g.topik_tip_vi, pattern)
                self.assertEqual(len(g.example_ko.split("\n")), len(g.example_vi.split("\n")), pattern)

    def test_each_foundation_card_is_practised_by_a_tile_exercise_a_frame_and_the_paragraph_or_a_join(self):
        for slug in T1:
            seed_ = LESSONS[slug].seed
            foundation = [g.pattern for g in seed_.grammar[:FOUNDATION[slug]]]
            mains = {}
            for e in self.items(slug):
                if e["skill"] == "build" and e.get("grammar"):
                    mains.setdefault(e["grammar"][0], set()).add(e["rung"])
            for p in foundation:
                self.assertIn(1, mains.get(p, set()), f"{slug}: no tile exercise for {p}")
                self.assertTrue(mains[p] & {2, 3}, f"{slug}: no frame or join for {p}")

    def test_the_thin_cards_of_the_pilot_lessons_were_upgraded(self):
        thin = [
            ("sinh-hoat-01-buoi-sang", "V + -고"), ("sinh-hoat-01-buoi-sang", "N(Thời gian) + 에"),
            ("sinh-hoat-02-viec-nha", "V + -아/어 놓다"), ("sinh-hoat-02-viec-nha", "V + -느라고"),
            ("sinh-hoat-03-an-uong", "V + -(으)ㄹ까요?"), ("sinh-hoat-03-an-uong", "V + -(으)ㅂ시다"),
            ("sinh-hoat-03-an-uong", "V + -아/어 보다"),
        ]
        for slug, pattern in thin:
            g = next(g for g in LESSONS[slug].seed.grammar if g.pattern == pattern)
            self.assertIn("**Vì sao", g.usage_context_vi, pattern)
            self.assertIn("**Lỗi người Việt hay mắc:**", g.note_vi, pattern)
            self.assertTrue(g.contrasts and g.topik_tip_vi, pattern)

    def test_the_paragraph_task_lists_patterns_and_its_model_shows_them_all(self):
        for slug in T1:
            essay = next(e for e in self.items(slug) if e["type"] == "write_essay" and e["skill"] == "build")
            self.assertGreaterEqual(len(essay["detectors"]), 4, slug)
            for d in essay["detectors"]:
                self.assertTrue(re.search(d["regex"], essay["model_answer_ko"]), (slug, d["pattern"]))
            self.assertTrue(essay["limits"]["min"] <= len(essay["model_answer_ko"]) <= essay["limits"]["max"], slug)

    def test_the_scaled_lessons_lead_with_two_foundation_cards_that_carry_exam_tags(self):
        expected = {
            "sinh-hoat-04-mua-sam": {"V/A + -아/어서": "kiip-1", "안 · 못 + V/A (phủ định)": "kiip-1"},
            "sinh-hoat-05-di-lai": {"V + -아/어야 하다/되다": "kiip-2", "V/A + -(으)니까": "kiip-2"},
            "sinh-hoat-06-hoc-lam": {"V + -(으)려고 하다": "kiip-2", "V/A + -아/어도": "kiip-3"},  # -아/어도 is KIIP 중급1 12과
            "sinh-hoat-07-giai-tri": {"V + -(으)ㄴ 적이 있다/없다": "kiip-2", "V + -(으)ㄹ게요 · -(으)ㄹ래요": "kiip-2"},  # KIIP 초급2 2·7과
            "sinh-hoat-08-suc-khoe": {"V + -아/어도 되다 · V + -(으)면 안 되다": "kiip-2", "V + -는 게 좋다": "kiip-2"},
            "sinh-hoat-09-nhat-ky": {"N + 때문에 · V/A + -기 때문에": "kiip-2", "V + -고 나서 · V + -(으)ㄴ 후에": "kiip-2"},
        }
        for slug, want in expected.items():
            cards = LESSONS[slug].seed.grammar
            self.assertEqual({g.pattern for g in cards[:2]}, set(want), slug)
            for g in cards[:2]:
                self.assertEqual(g.exam, want[g.pattern], g.pattern)
                self.assertFalse((g.source or "").startswith("EXT-"), g.pattern)
                for label in ("**Cấu tạo:**", "**Hoàn cảnh dùng:**", "**Vì sao chọn nó thay vì"):
                    self.assertIn(label, g.usage_context_vi, g.pattern)
                self.assertGreaterEqual(len(g.contrasts), 2, g.pattern)
                self.assertIn("**Lỗi người Việt hay mắc:**", g.note_vi, g.pattern)
                self.assertTrue(g.topik_tip_vi, g.pattern)
                self.assertEqual(len(g.example_ko.split("\n")), len(g.example_vi.split("\n")), g.pattern)
                self.assertEqual(len(g.example_ko.split("\n")), 3, g.pattern)

    def test_the_thin_cards_of_the_scaled_lessons_were_upgraded(self):
        thin = [
            ("sinh-hoat-04-mua-sam", "A + -은/ㄴ"), ("sinh-hoat-04-mua-sam", "N + 보다"),
            ("sinh-hoat-04-mua-sam", "N(Đơn vị) + 에"), ("sinh-hoat-05-di-lai", "N + (으)로"),
            ("sinh-hoat-05-di-lai", "V + -는 길에"), ("sinh-hoat-05-di-lai", "V + -는 데 걸리다/들다"),
            ("sinh-hoat-06-hoc-lam", "N1(Thời gian)부터 N2(Thời gian)까지"), ("sinh-hoat-06-hoc-lam", "V + -기 전에"),
            ("sinh-hoat-07-giai-tri", "V + -(으)러 가다/오다"), ("sinh-hoat-07-giai-tri", "V/A + -는데/은데/ㄴ데"),
            ("sinh-hoat-08-suc-khoe", "V + -게 되다"), ("sinh-hoat-08-suc-khoe", "V + -지 않으면 안 되다"),
            ("sinh-hoat-09-nhat-ky", "Thể trần thuật (서술체: -(느)ㄴ다 / -다)"),
        ]
        for slug, pattern in thin:
            g = next(g for g in LESSONS[slug].seed.grammar if g.pattern == pattern)
            self.assertIn("**Vì sao", g.usage_context_vi, pattern)
            self.assertIn("**Lỗi người Việt hay mắc:**", g.note_vi, pattern)
            self.assertTrue(g.contrasts and g.topik_tip_vi, pattern)

    def test_each_scaled_lesson_has_enough_practice_to_climb_the_ladder(self):
        for slug in SCALED:
            built = [e for e in self.items(slug) if e["skill"] == "build"]
            by_rung = {r: [e for e in built if e["rung"] == r] for r in (1, 2, 3, 4)}
            self.assertGreaterEqual(len(by_rung[1]), 5, slug)
            self.assertGreaterEqual(len(by_rung[2]), 2, slug)
            self.assertGreaterEqual(len(by_rung[3]), 1, slug)
            self.assertEqual(len(by_rung[4]), 1, slug)

    def test_a_paragraph_task_never_asks_for_a_pattern_of_a_later_lesson(self):
        order = {g.pattern: LESSONS[slug].seed.sort_order for slug in T1 for g in LESSONS[slug].seed.grammar}
        for slug in T1:
            for e in self.items(slug):
                if e["skill"] == "build" and e["type"] == "write_essay":
                    for d in e["detectors"]:
                        self.assertLessEqual(order[d["pattern"]], LESSONS[slug].seed.sort_order, (slug, d["pattern"]))

    def test_a_detector_that_names_an_unknown_card_is_a_problem(self):
        r = LESSONS["sinh-hoat-01-buoi-sang"]
        essay = next(e for e in r.practice["items"] if e["id"] == "BE01")
        broken = {**essay, "detectors": essay["detectors"] + [{"pattern": "V + -không-có-thẻ-này", "regex": "x"}]}
        problems = seed._detector_problems(r.seed, [broken], r.practice["grammar"])
        self.assertTrue(any("is not a grammar card" in p for p in problems), problems)
        silent = {**essay, "model_answer_ko": "안녕하세요."}
        self.assertTrue(any("model answer does not show" in p for p in seed._detector_problems(r.seed, [silent], r.practice["grammar"])))

    def test_the_review_map_places_every_new_card_in_one_function(self):
        review = LESSONS["sinh-hoat-10-on-tap-chu-de"]
        mapped = [p for f in review.seed.review.functions for p in f.patterns]
        cards = [g.pattern for slug in T1 for g in LESSONS[slug].seed.grammar]
        self.assertTrue(set(cards) <= set(mapped))
        self.assertEqual(len(mapped), len(set(mapped)))
        self.assertEqual(len(mapped), 102)  # the 61 cards of the nine lessons + the foundation round (33 + 8 woven)


class TopicTwoContentTests(unittest.TestCase):
    """Topic 2 (Quan hệ), lessons 1–11, carries the same ladder as topic 1."""

    def items(self, slug):
        return LESSONS[slug].practice["items"]

    def built(self, slug):
        return [e for e in self.items(slug) if e["skill"] == "build"]

    def test_the_eleven_practice_lessons_are_found(self):
        self.assertEqual(len(T2), 11)
        self.assertEqual(T2[0], "quan-he-01-gia-dinh")
        self.assertEqual(T2[-1], "quan-he-11-ky-nghi-van-hoa")

    def test_each_lesson_climbs_all_four_rungs_in_order(self):
        for slug in T2:
            built = self.built(slug)
            rungs = [e["rung"] for e in built]
            self.assertEqual(set(rungs), {1, 2, 3, 4}, slug)
            self.assertEqual(rungs, sorted(rungs), f"{slug}: the ladder must go up")
            self.assertGreaterEqual(rungs.count(1), 4, slug)
            self.assertGreaterEqual(rungs.count(2), 2, slug)
            self.assertGreaterEqual(rungs.count(3), 1, slug)
            self.assertEqual(rungs.count(4), 1, slug)
            by_skill = LESSONS[slug].practice["counts"]["by_skill"]
            keys = list(by_skill)
            if "reading" in keys:
                self.assertLess(keys.index("reading"), keys.index("build"), slug)
            if "writing" in keys:
                self.assertLess(keys.index("build"), keys.index("writing"), slug)
            self.assertEqual(by_skill["build"], sum(len(seed._question_ids(e)) for e in built), slug)

    def test_the_review_lesson_has_no_build_skill_yet(self):
        self.assertNotIn("build", LESSONS["quan-he-12-on-tap-chu-de"].practice["counts"]["by_skill"])
        self.assertNotIn("build", LESSONS["cong-so-08-on-tap-chu-de"].practice["counts"]["by_skill"])

    def test_topic_four_lessons_build_words_into_sentences_and_join_two_sentences(self):
        self.assertEqual(len(T4), 7)
        for slug in T4:
            r = LESSONS[slug]
            built = [e for e in r.practice["items"] if e["skill"] == "build"]
            rungs = [e["rung"] for e in built]
            self.assertEqual(rungs, sorted(rungs), slug)
            self.assertGreaterEqual(rungs.count(1), 3, slug)
            self.assertGreaterEqual(rungs.count(3), 1, slug)
            for e in built:
                links = e.get("grammar") or []
                self.assertTrue(1 <= len(links) <= 3, (e["id"], links))
                for p in links:
                    self.assertLessEqual(r.practice["grammar"][p]["lesson_order"], r.seed.sort_order, e["id"])
                if e["type"] == "build_order":
                    used = {w for a in e["answers"] for w in a.split()}
                    self.assertTrue(set(e["tiles"]) - used, f"{e['id']}: no distractor tile")

    def test_every_build_exercise_links_one_to_three_cards_of_its_lesson_or_before(self):
        for slug in T2:
            r = LESSONS[slug]
            cards = r.practice["grammar"]
            for e in self.built(slug):
                links = e.get("grammar") or []
                self.assertTrue(1 <= len(links) <= 3, (e["id"], links))
                for p in links:
                    self.assertLessEqual(cards[p]["lesson_order"], r.seed.sort_order, e["id"])

    def test_tiles_fit_a_phone_and_leave_a_wrong_form_to_avoid(self):
        for slug in T2:
            for e in self.built(slug):
                if e["type"] != "build_order":
                    continue
                self.assertLessEqual(len(e["tiles"]), 10, e["id"])
                used = {w for a in e["answers"] for w in a.split()}
                self.assertTrue(set(e["tiles"]) - used, f"{e['id']}: no distractor tile")

    def test_every_card_is_explained_in_depth(self):
        for slug in T2:
            for g in LESSONS[slug].seed.grammar:
                self.assertIn("**Vì sao", g.usage_context_vi, (slug, g.pattern))
                self.assertIn("**Lỗi người Việt hay mắc:**", g.note_vi, (slug, g.pattern))
                self.assertTrue(g.contrasts and g.topik_tip_vi, (slug, g.pattern))
                self.assertEqual(len(g.example_ko.split("\n")), len(g.example_vi.split("\n")), (slug, g.pattern))

    def test_the_level_note_taken_from_the_books_survives_the_upgrade(self):
        for slug, pattern in [
            ("quan-he-02-dien-thoai-hen", "V + -는 바람에"), ("quan-he-02-dien-thoai-hen", "V + -고자 하다"),
            ("quan-he-03-sinh-nhat-le-tet", "V/A + -(으)ㄴ/는 셈이다"),
            ("quan-he-07-moi-truong", "V + -(으)ㄹ 필요가 있다 · V + -(으)ㄹ 필요가 없다"),
            ("quan-he-09-thoi-tiet-2", "N + 에 비해(서) · N + 에 비하면"), ("quan-he-09-thoi-tiet-2", "N + 에 따르면"),
            ("quan-he-11-ky-nghi-van-hoa", "V/A + -더라고요"),
            ("quan-he-11-ky-nghi-van-hoa", "V/A + -(으)ㄴ/는 반면(에) · N + 인 반면(에)"),
        ]:
            g = next(g for g in LESSONS[slug].seed.grammar if g.pattern == pattern)
            self.assertIn("**Mức độ:**", g.usage_context_vi, (slug, pattern))

    def test_every_core_card_has_an_exercise_that_leads_with_it(self):
        # The cards marked as extensions (EXT-…) are practised by the paragraph task and the review;
        # the lesson's core cards each lead at least one tile or frame exercise.
        for slug in T2:
            mains = {e["grammar"][0] for e in self.built(slug) if e.get("grammar") and e["rung"] in (1, 2, 3)}
            for g in LESSONS[slug].seed.grammar:
                if (g.source or "").startswith("EXT-") and g.use_level != "produce":
                    continue
                if (g.source or "").startswith("EXT-SUP-"):  # TOPIK II supplement: its own reading question
                    continue
                self.assertIn(g.pattern, mains, f"{slug}: {g.pattern}")

    def test_the_paragraph_task_lists_patterns_and_its_model_shows_them_all(self):
        order = {g.pattern: LESSONS[s].seed.sort_order for s in T2 for g in LESSONS[s].seed.grammar}
        order.update({g.pattern: LESSONS[s].seed.sort_order for s in T1 for g in LESSONS[s].seed.grammar})
        for slug in T2:
            essay = next(e for e in self.built(slug) if e["type"] == "write_essay")
            self.assertGreaterEqual(len(essay["detectors"]), 3, slug)
            self.assertLessEqual(len(essay["grammar"]), 3, slug)
            for d in essay["detectors"]:
                self.assertTrue(re.search(d["regex"], essay["model_answer_ko"]), (slug, d["pattern"]))
                self.assertNotIn("(?<", d["regex"], f"{slug}: the browser grades with JS; avoid lookbehind")
            self.assertTrue(essay["limits"]["min"] <= len(essay["model_answer_ko"]) <= essay["limits"]["max"], slug)
            for d in essay["detectors"]:
                if d["pattern"] in order:
                    self.assertLessEqual(order[d["pattern"]], LESSONS[slug].seed.sort_order, (slug, d["pattern"]))

    def test_the_review_map_still_places_each_card_once(self):
        review = LESSONS["quan-he-12-on-tap-chu-de"]
        mapped = [p for f in review.seed.review.functions for p in f.patterns]
        self.assertEqual(len(mapped), len(set(mapped)))
        cards = [g.pattern for slug in T2 for g in LESSONS[slug].seed.grammar]
        self.assertTrue(set(cards) <= set(mapped), sorted(set(cards) - set(mapped)))


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
        r = LESSONS["sinh-hoat-01-buoi-sang"]
        lesson = SimpleNamespace(id=7, content_hash=r.content_hash, practice=r.practice, title=r.seed.title)
        ex = next(e for e in r.practice["items"] if e["id"] == "BO01")
        db = self.db(lesson)
        body = ExerciseAnswerRequest(exercise_id="BO01", question_id="BO01", correct=False, answer="저는 어제 일어나요.")
        with mock.patch.object(content, "_linked_grammar_ids", mock.AsyncMock(return_value=[(42, "V/A + -았/었-")])):
            await content.answer_lesson_question(7, body, db, self.PROFILE)
        log = next(c.args[0] for c in db.add.call_args_list if isinstance(c.args[0], ErrorLog))
        self.assertEqual((log.skill, log.error_type, log.mode), ("viết", "build_order", "writing"))
        self.assertEqual(log.example_ko, ex["answers"][0])

    async def test_a_tile_exercise_is_one_question(self):
        r = LESSONS["sinh-hoat-02-viec-nha"]
        index = seed.question_index(r.practice)
        self.assertEqual(index["BO06"]["id"], "BO06")
        self.assertEqual(index["BF04:㉠"]["id"], "BF04")


if __name__ == "__main__":
    unittest.main()

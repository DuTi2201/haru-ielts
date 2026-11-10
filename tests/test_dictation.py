"""Chép chính tả (`listen_dictation`): the model keeps a dictation short and explained, the
seeded dictations sit in the topic review lessons and in the three main lessons of topic 1, and they
are practice that is not part of the mock exam (a dictation has no right option, so it cannot be
scored out of 200)."""
import unittest

from pydantic import ValidationError

from app.services import lesson_seed as seed

BUNDLE = seed.load_all()
REVIEWS = {r.seed.slug: r for r in BUNDLE.lessons if r.seed.kind == "review"}

LINE = {"speaker": "N", "text": "내일 오전 열 시부터 도서관 공사가 있습니다.", "vi": "Từ 10 giờ sáng mai thư viện có công trình."}


def make(**kw):
    base = {
        "id": "X1",
        "skill": "listening",
        "type": "listen_dictation",
        "title_vi": "Chép chính tả: thông báo",
        "stimulus": {"kind": "audio", "turns": [dict(LINE)]},
        "focus": [{"ko": "공사", "vi": "công trình"}, {"ko": "-부터", "vi": "từ (mốc thời gian)"}],
    }
    base.update(kw)
    return seed.Dictation.model_validate(base)


class DictationModelTests(unittest.TestCase):
    def test_a_short_explained_script_is_accepted(self):
        self.assertEqual(make().type, "listen_dictation")

    def test_a_script_has_at_most_four_lines(self):
        turns = [{**LINE, "text": "네."}] * 5
        with self.assertRaises(ValidationError):
            make(stimulus={"kind": "audio", "turns": turns})
        make(stimulus={"kind": "audio", "turns": turns[:4]})

    def test_every_line_needs_its_meaning(self):
        with self.assertRaises(ValidationError):
            make(stimulus={"kind": "audio", "turns": [{"speaker": "N", "text": "안녕하세요."}]})

    def test_a_long_script_is_rejected(self):
        with self.assertRaises(ValidationError):
            make(stimulus={"kind": "audio", "turns": [{**LINE, "text": "가" * 131}]})
        make(stimulus={"kind": "audio", "turns": [{**LINE, "text": "가" * 130}]})

    def test_the_words_to_learn_are_two_to_eight(self):
        with self.assertRaises(ValidationError):
            make(focus=[{"ko": "공사", "vi": "công trình"}])
        with self.assertRaises(ValidationError):
            make(focus=[{"ko": f"단어{n}", "vi": "x"} for n in range(9)])

    def test_it_is_a_listening_exercise_only(self):
        with self.assertRaises(ValidationError):
            make(skill="reading")

    def test_the_type_is_a_non_choice_type(self):
        self.assertIn("listen_dictation", seed.NON_MCQ_TYPES)


class SeededDictationTests(unittest.TestCase):
    def dictations(self, review):
        return [it for it in review.practice["items"] if it["type"] == "listen_dictation"]

    def test_every_topic_review_has_one_to_three_dictations(self):
        # "only a few papers: too many and the learner gives up"
        for slug, review in REVIEWS.items():
            self.assertTrue(1 <= len(self.dictations(review)) <= 3, slug)

    def test_the_seeded_dictations(self):
        found = sorted(it["id"] for r in REVIEWS.values() for it in self.dictations(r))
        self.assertEqual(found, ["C41D1", "D01", "D02", "D03", "NCD01", "QD01", "QD02", "X70D1", "X70D2"])

    def test_a_dictation_is_not_in_the_mock(self):
        for slug, review in REVIEWS.items():
            mock_ids = set(review.practice["review"]["mock"]["question_ids"])
            for it in self.dictations(review):
                self.assertFalse(mock_ids & {it["id"]}, slug)
                self.assertNotIn("questions", it)

    def test_a_dictation_follows_the_listening_it_belongs_to(self):
        for review in REVIEWS.values():
            order = [it for it in review.practice["items"]]
            for n, it in enumerate(order):
                if it["type"] == "listen_dictation":
                    self.assertEqual(it["skill"], "listening")
                    self.assertTrue(any(o["skill"] == "listening" for o in order[:n]))

    def test_the_words_to_learn_are_distinct_and_most_are_words_of_the_script(self):
        # `focus` is what the learner studies after the check: no repeats, and most entries are words
        # that literally occur in the script (the rest are forms written with a dash, like -(으)면서)
        for review in REVIEWS.values():
            for it in self.dictations(review):
                kos = [g["ko"] for g in it["focus"]]
                self.assertEqual(len(kos), len(set(kos)), it["id"])
                script = "".join(t["text"] for t in it["stimulus"]["turns"]).replace(" ", "")
                plain = [k for k in kos if not k.startswith("-") and not k.startswith("N ")]
                heard = sum(k.replace(" ", "")[:1] in script for k in plain)
                self.assertGreaterEqual(heard * 2, len(plain), it["id"])  # at least half of them occur in the script


LESSONS = {r.seed.slug: r for r in BUNDLE.lessons}
FOUNDATION = [slug for slug in LESSONS if slug.startswith("sinh-hoat-00-nen-tang-")]
MAIN_THREE = ["sinh-hoat-01-buoi-sang", "sinh-hoat-02-viec-nha", "sinh-hoat-03-an-uong"]


def lesson_dictations(slug):
    return [it for it in LESSONS[slug].practice["items"] if it["type"] == "listen_dictation"]


class DailyLessonDictationTests(unittest.TestCase):
    """The first rollout of chép chính tả to the daily lessons: bài 6-8 only, short, built from the
    lesson's own words and cards; the five Nền tảng lessons have none."""

    def test_the_foundation_lessons_have_no_dictation(self):
        self.assertEqual(len(FOUNDATION), 16)  # the five Nền tảng lessons, cut into sixteen
        for slug in FOUNDATION:
            self.assertEqual(lesson_dictations(slug), [], slug)

    def test_each_of_the_three_main_lessons_has_two_short_dictations(self):
        for slug in MAIN_THREE:
            found = lesson_dictations(slug)
            self.assertEqual(len(found), 2, slug)
            for it in found:
                turns = it["stimulus"]["turns"]
                self.assertTrue(2 <= len(turns) <= 4, it["id"])
                self.assertTrue(2 <= len(it["focus"]) <= 8, it["id"])

    def test_the_new_dictation_ids(self):
        ids = sorted(it["id"] for slug in MAIN_THREE for it in lesson_dictations(slug))
        self.assertEqual(ids, ["D04", "D05", "D06", "D07", "D08", "D09"])

    def test_a_dictation_follows_the_listening_it_belongs_to(self):
        for slug in MAIN_THREE:
            order = LESSONS[slug].practice["items"]
            for n, it in enumerate(order):
                if it["type"] == "listen_dictation":
                    self.assertTrue(any(o["skill"] == "listening" and o["type"] != "listen_dictation" for o in order[:n]), it["id"])

    def test_the_script_is_typed_in_hangul_only(self):
        # a digit would be heard as a word ("6시" -> "여섯 시"), so the learner could not type what they hear
        for slug in MAIN_THREE:
            for it in lesson_dictations(slug):
                for t in it["stimulus"]["turns"]:
                    self.assertNotRegex(t["text"], r"[0-9]", it["id"])

    def test_every_dictation_carries_its_grammar_from_the_lesson(self):
        # the cards named under the check are cards of this lesson (or an earlier one), at most three
        for slug in MAIN_THREE:
            cards = {g.pattern for g in LESSONS[slug].seed.grammar}
            for it in lesson_dictations(slug):
                linked = it.get("grammar") or []
                self.assertTrue(1 <= len(linked) <= 3, it["id"])
                self.assertTrue(set(linked) & cards, it["id"])

    def test_the_words_to_learn_are_distinct(self):
        for slug in MAIN_THREE:
            for it in lesson_dictations(slug):
                kos = [g["ko"] for g in it["focus"]]
                self.assertEqual(len(kos), len(set(kos)), it["id"])

    def test_a_dictation_is_counted_in_the_lesson_practice(self):
        for slug in MAIN_THREE:
            counts = LESSONS[slug].practice["counts"]
            ids = {it["id"] for it in LESSONS[slug].practice["items"]}
            self.assertTrue({"D04", "D05", "D06", "D07", "D08", "D09"} & ids)
            self.assertGreaterEqual(counts["by_skill"]["listening"], 2, slug)


class EveryLessonDictationTests(unittest.TestCase):
    """The rollout to the whole course: every lesson except the five Nền tảng ones holds two short
    dictations of its own (the topic reviews keep the ones they already had), built from the lesson's
    own words and grammar cards."""

    def regular(self):
        return [slug for slug, r in LESSONS.items() if r.seed.kind == "lesson" and slug not in FOUNDATION]

    def test_every_regular_lesson_has_exactly_two(self):
        self.assertEqual(len(self.regular()), 61)
        for slug in self.regular():
            self.assertEqual(len(lesson_dictations(slug)), 2, slug)

    def test_the_review_lessons_keep_their_own(self):
        for slug, r in LESSONS.items():
            if r.seed.kind == "review":
                self.assertTrue(1 <= len(lesson_dictations(slug)) <= 3, slug)

    def test_every_dictation_has_a_unique_id(self):
        ids = [it["id"] for r in LESSONS.values() for it in lesson_dictations(r.seed.slug)]
        self.assertEqual(len(ids), 131)
        self.assertEqual(len(ids), len(set(ids)))

    def test_each_is_short_explained_and_in_hangul_only(self):
        for slug in self.regular():
            for it in lesson_dictations(slug):
                turns = it["stimulus"]["turns"]
                self.assertTrue(2 <= len(turns) <= 4, it["id"])
                self.assertTrue(2 <= len(it["focus"]) <= 8, it["id"])
                self.assertTrue(1 <= len(it["tips_vi"]) <= 3, it["id"])
                for t in turns:
                    self.assertIn(t["speaker"], ("F", "M", "N"), it["id"])
                    self.assertTrue(t["vi"].strip(), it["id"])
                    self.assertNotRegex(t["text"], r"[0-9A-Za-z]", it["id"])  # a digit would be heard as a word

    def test_the_cards_named_under_the_check_belong_to_the_lesson_or_an_earlier_one(self):
        for slug in self.regular():
            order = LESSONS[slug].seed.sort_order
            for it in lesson_dictations(slug):
                linked = it.get("grammar") or []
                self.assertTrue(1 <= len(linked) <= 3, it["id"])
                self.assertTrue(set(linked) <= set(LESSONS[slug].practice["grammar"]), it["id"])
                for pattern in linked:
                    self.assertLessEqual(LESSONS[slug].practice["grammar"][pattern]["lesson_order"], order, it["id"])

    def test_the_main_card_of_a_dictation_is_one_of_the_lesson(self):
        for slug in self.regular():
            cards = {g.pattern for g in LESSONS[slug].seed.grammar}
            for it in lesson_dictations(slug):
                self.assertTrue(set(it.get("grammar") or []) & cards, it["id"])

    def test_the_words_to_learn_are_distinct_and_most_occur_in_the_script(self):
        for slug in self.regular():
            for it in lesson_dictations(slug):
                kos = [g["ko"] for g in it["focus"]]
                self.assertEqual(len(kos), len(set(kos)), it["id"])
                script = "".join(t["text"] for t in it["stimulus"]["turns"]).replace(" ", "")
                plain = [k for k in kos if k[0] not in "-N"]
                heard = sum(k.replace(" ", "")[:1] in script for k in plain)
                self.assertGreaterEqual(heard * 2, len(plain), it["id"])

    def test_the_explanations_have_balanced_backticks(self):
        for slug in self.regular():
            for it in lesson_dictations(slug):
                for tip in it["tips_vi"]:
                    self.assertEqual(tip.count("`") % 2, 0, it["id"])
                    self.assertEqual(tip, tip.strip(), it["id"])

    def test_a_dictation_follows_a_listening_exercise_of_its_lesson(self):
        for slug in self.regular():
            order = LESSONS[slug].practice["items"]
            for n, it in enumerate(order):
                if it["type"] == "listen_dictation":
                    self.assertTrue(
                        any(o["skill"] == "listening" and o["type"] != "listen_dictation" for o in order[:n]), it["id"]
                    )

    def test_a_dictation_is_counted_in_the_lesson_listening(self):
        for slug in self.regular():
            self.assertGreaterEqual(LESSONS[slug].practice["counts"]["by_skill"]["listening"], 2, slug)


if __name__ == "__main__":
    unittest.main()

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


LESSONS = {r.seed.slug: r for r in BUNDLE.lessons}


def lesson_dictations(slug):
    return [it for it in LESSONS[slug].practice["items"] if it["type"] == "listen_dictation"]


class EveryLessonDictationTests(unittest.TestCase):
    """Every B1 unit holds a short dictation built from the unit's own words and grammar cards."""

    def regular(self):
        return [slug for slug, r in LESSONS.items() if r.seed.kind == "lesson"]

    def test_every_regular_lesson_has_a_dictation(self):
        self.assertEqual(len(self.regular()), 42)
        for slug in self.regular():
            self.assertEqual(len(lesson_dictations(slug)), 1, slug)

    def test_every_dictation_has_a_unique_id(self):
        ids = [it["id"] for r in LESSONS.values() for it in lesson_dictations(r.seed.slug)]
        self.assertEqual(len(ids), 42)
        self.assertEqual(len(ids), len(set(ids)))

    def test_each_is_short_explained_and_in_english(self):
        for slug in self.regular():
            for it in lesson_dictations(slug):
                turns = it["stimulus"]["turns"]
                self.assertTrue(2 <= len(turns) <= 4, it["id"])
                self.assertTrue(2 <= len(it["focus"]) <= 8, it["id"])
                self.assertTrue(1 <= len(it["tips_vi"]) <= 3, it["id"])
                for t in turns:
                    self.assertIn(t["speaker"], ("F", "M", "N"), it["id"])
                    self.assertTrue(t["vi"].strip(), it["id"])
                    self.assertRegex(t["text"], r"[A-Za-z]", it["id"])

    def test_the_words_to_learn_are_distinct(self):
        for slug in self.regular():
            for it in lesson_dictations(slug):
                kos = [g["ko"] for g in it["focus"]]
                self.assertEqual(len(kos), len(set(kos)), it["id"])

    def test_the_explanations_have_balanced_backticks(self):
        for slug in self.regular():
            for it in lesson_dictations(slug):
                for tip in it["tips_vi"]:
                    self.assertEqual(tip.count("`") % 2, 0, it["id"])
                    self.assertEqual(tip, tip.strip(), it["id"])

    def test_a_dictation_is_counted_in_the_lesson_listening(self):
        for slug in self.regular():
            self.assertGreaterEqual(LESSONS[slug].practice["counts"]["by_skill"]["listening"], 1, slug)


if __name__ == "__main__":
    unittest.main()

"""Every word is labelled "core" (learn it now) or "recognize" (understand it when met)."""
import collections
import unittest

from pydantic import ValidationError

from app.services import lesson_seed as seed


class VocabPriorityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bundle = seed.load_all()
        cls.rows = [(r.seed.slug, v) for r in cls.bundle.lessons for v in r.seed.vocab]

    def test_a_word_without_a_label_is_refused(self):
        with self.assertRaises(ValidationError):
            seed.VocabSeed(hangul="물", pos="N", meaning_vi="nước")
        with self.assertRaises(ValidationError):
            seed.VocabSeed(hangul="물", pos="N", meaning_vi="nước", priority="important")
        self.assertEqual(seed.VocabSeed(hangul="물", pos="N", meaning_vi="nước", priority="core").priority, "core")

    def test_every_word_of_the_seed_has_a_label(self):
        self.assertEqual(len(self.rows), 1056)
        self.assertTrue({v.priority for _, v in self.rows} <= {"core", "recognize"})

    def test_a_word_is_labelled_alike_in_every_lesson_that_lists_it(self):
        seen = collections.defaultdict(set)
        for slug, v in self.rows:
            seen[v.hangul].add(v.priority)
        self.assertEqual({h: p for h, p in seen.items() if len(p) > 1}, {})

    def test_the_core_list_has_a_sensible_size(self):
        by_word = {v.hangul: v.priority for _, v in self.rows}
        core = {h for h, p in by_word.items() if p == "core"}
        self.assertGreaterEqual(len(core), 800)
        self.assertLessEqual(len(core), 1100)

    def test_the_api_word_serves_its_label(self):
        from app.schemas import VocabItemOut

        base = dict(id=1, lesson_id=1, hangul="물", meaning_vi="nước", definition_ko=None, pos="N", level=1, hanja=None, sino_vietnamese=None, example_ko="x")
        self.assertEqual(VocabItemOut(**base, priority="core").model_dump(mode="json")["priority"], "core")
        self.assertIsNone(VocabItemOut(**base).model_dump(mode="json")["priority"])


if __name__ == "__main__":
    unittest.main()

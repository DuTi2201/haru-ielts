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
        self.assertGreater(len(self.rows), 1400)
        self.assertEqual({v.priority for _, v in self.rows}, {"core", "recognize"})

    def test_a_word_is_labelled_alike_in_every_lesson_that_lists_it(self):
        seen = collections.defaultdict(set)
        for slug, v in self.rows:
            seen[v.hangul].add(v.priority)
        self.assertEqual({h: p for h, p in seen.items() if len(p) > 1}, {})

    def test_the_core_list_has_a_sensible_size(self):
        by_word = {v.hangul: v.priority for _, v in self.rows}
        core = {h for h, p in by_word.items() if p == "core"}
        core_cong_so = {v.hangul for slug, v in self.rows if slug.startswith("cong-so-") and v.priority == "core"}
        core_first = {v.hangul for slug, v in self.rows if not slug.startswith(("cong-so-", "xa-hoi-")) and v.priority == "core"}
        core_xa_hoi = {v.hangul for slug, v in self.rows if slug.startswith("xa-hoi-") and v.priority == "core"}
        # the learner's target for the first three topics is about 800 core words; the list is built from the
        # lessons, so it lands near that without matching it exactly
        self.assertGreaterEqual(len(core_first), 600)
        self.assertLessEqual(len(core_first), 850)
        # the Công sở course (topic 4, aimed at 4급) adds its own level-4 core on top, about 30 a lesson at most
        self.assertLessEqual(len(core_cong_so - core_first), 230)
        # topic 5 (aimed at 5-6급) adds its own core on top: about 20 a lesson at most
        self.assertLessEqual(len(core_xa_hoi - core_first - core_cong_so), 450)
        self.assertGreater(len(by_word) - len(core), 400)  # and there is a real second group

    def test_the_foundation_lessons_are_core(self):
        f = [v.priority for slug, v in self.rows if "-00-nen-tang" in slug]
        self.assertGreater(len(f), 100)
        self.assertGreaterEqual(f.count("core") / len(f), 0.95)

    def test_the_kiip_beginner_words_are_core(self):
        k = [v.priority for _, v in self.rows if v.exam in ("kiip-1", "kiip-2")]
        self.assertGreater(len(k), 250)
        self.assertGreaterEqual(k.count("core") / len(k), 0.9)  # a few specialised words (a medical ointment, a contract) stay recognise-only

    def test_the_api_word_serves_its_label(self):
        from app.schemas import VocabItemOut

        base = dict(id=1, lesson_id=1, hangul="물", meaning_vi="nước", definition_ko=None, pos="N", level=1, hanja=None, sino_vietnamese=None, example_ko="x")
        self.assertEqual(VocabItemOut(**base, priority="core").model_dump(mode="json")["priority"], "core")
        self.assertIsNone(VocabItemOut(**base).model_dump(mode="json")["priority"])


if __name__ == "__main__":
    unittest.main()

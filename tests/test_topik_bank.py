"""«Kho từ TOPIK» (app/services/topik_bank.py, app/seed/nikl/topik_bank.json)."""
import re
import unittest

from app.services import topik_bank

HANGUL = re.compile(r"[가-힣]")


class BankFileTests(unittest.TestCase):
    def test_every_deck_word_exists_once(self):
        words = topik_bank.words()
        seen = set()
        for deck in topik_bank.decks().values():
            self.assertTrue(deck.words, deck.key)
            self.assertLessEqual(len(deck.words), 120, deck.key)
            for e in deck.words:
                self.assertIn(e, words)
                self.assertNotIn(e, seen)
                seen.add(e)
        self.assertEqual(seen, set(words))

    def test_only_intermediate_and_advanced_words(self):
        self.assertEqual({w["grade"] for w in topik_bank.words().values()}, {"mid", "adv"})

    def test_every_word_has_a_vietnamese_meaning_that_fits_the_column(self):
        for w in topik_bank.words().values():
            self.assertTrue(w["meaning_vi"].strip(), w["w"])
            self.assertLessEqual(len(w["meaning_vi"]), 255, w["w"])
            self.assertTrue(HANGUL.search(w["w"]), w["w"])

    def test_a_reading_reads_each_character_once(self):
        for w in topik_bank.words().values():
            if w["sino_vietnamese"]:
                self.assertTrue(w["hanja"], w["w"])
                self.assertEqual(len(w["sino_vietnamese"].split()), len(w["hanja"]), w["w"])
            if w["hanja"]:
                self.assertLessEqual(len(w["hanja"]), len(HANGUL.findall(w["w"])), w["w"])

    def test_a_character_read_two_ways_by_the_course_is_not_guessed(self):
        # 長 is 장 in Korean both in 사장 (xã trưởng) and in 장점 (trường điểm): no single reading
        for w in topik_bank.words().values():
            if w["hanja"] and "長" in w["hanja"]:
                self.assertIsNone(w["sino_vietnamese"], w["w"])

    def test_row_fields_fit_the_vocab_item_columns(self):
        for w in list(topik_bank.words().values())[:500]:
            f = topik_bank.row_fields(w)
            self.assertIn(f["level"], (4, 6))
            self.assertLessEqual(len(f["family"]), 120)
            self.assertEqual(f["priority"], "recognize")
            if f["hanja"]:
                self.assertLessEqual(len(f["hanja"]), 64)

    def test_the_licence_is_named(self):
        self.assertIn("CC BY-SA", topik_bank.load()["license"])


if __name__ == "__main__":
    unittest.main()


class DeckLessonMapTests(unittest.TestCase):
    def test_every_mapped_deck_and_lesson_is_real(self):
        import json
        from pathlib import Path

        slugs = {p.stem for p in Path("app/seed/lessons").glob("*.json")}
        for key, entry in json.loads(topik_bank.DECK_LESSONS_FILE.read_text(encoding="utf-8")).items():
            self.assertIn(key, topik_bank.decks())
            for slug in entry["lessons"]:
                self.assertIn(slug, slugs, f"{key} -> {slug}")
        self.assertTrue(topik_bank.lesson_decks())


class BankHandoffTests(unittest.TestCase):
    WORDS = [{"id": i, "hangul": f"단어{i}", "meaning_vi": f"nghĩa {i}", "example_ko": f"단어{i}를 씁니다."} for i in range(1, 9)]

    def test_targets_are_cards_and_capped(self):
        from app.services import presentation

        out = presentation.bank_handoff("present", "Giao thông", self.WORDS)
        self.assertEqual(len(out["targets"]), presentation.BANK_TARGETS)
        self.assertEqual(out["targets"][0]["key"], "v:1")
        self.assertIn("Giao thông", out["title"])
        self.assertIn("단어1", out["material"])

    def test_debate_and_unknown_kind(self):
        from app.services import presentation

        self.assertIn("lập trường", presentation.bank_handoff("debate", "Kinh tế", self.WORDS)["material"])
        with self.assertRaises(ValueError):
            presentation.bank_handoff("x", "Kinh tế", self.WORDS)

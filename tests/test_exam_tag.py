"""The `exam` tag: a word, grammar card or note can be part of an exam course too (KIIP)."""
import unittest
from datetime import datetime, timezone
from unittest import mock

from pydantic import ValidationError

from app.api.routers import content
from app.services import lesson_seed as seed


def lesson(**over):
    base = {
        "slug": "sinh-hoat-99-thu", "title": "Thử", "topic": "Thử", "track": "intermediate", "level": 3,
        "sort_order": 99, "summary": "x", "vocab": [{"hangul": "가", "pos": "N", "meaning_vi": "a", "priority": "core"}],
    }
    base.update(over)
    return base


class ValidationTests(unittest.TestCase):
    def test_a_stage_tag_is_accepted_on_words_cards_and_notes(self):
        s = seed.LessonSeed.model_validate(
            lesson(
                vocab=[{"hangul": "가", "pos": "N", "meaning_vi": "a", "priority": "core", "exam": "kiip-3"}],
                grammar=[{"pattern": "V + -고", "meaning_vi": "và", "exam": "kiip-2"}],
                notes=[{"title": "t", "body": "b", "kind": "fact", "exam": "kiip-5"}],
            )
        )
        self.assertEqual(s.vocab[0].exam, "kiip-3")
        self.assertEqual(s.grammar[0].exam, "kiip-2")
        self.assertEqual(s.notes[0].exam, "kiip-5")

    def test_an_untagged_item_has_no_exam(self):
        self.assertIsNone(seed.LessonSeed.model_validate(lesson()).vocab[0].exam)

    def test_a_malformed_tag_is_rejected(self):
        for bad in ("kiip-6", "kiip-0", "KIIP 3", "kiip3", "topik-4", ""):
            with self.subTest(tag=bad), self.assertRaises(ValidationError):
                seed.LessonSeed.model_validate(
                    lesson(vocab=[{"hangul": "가", "pos": "N", "meaning_vi": "a", "priority": "core", "exam": bad}])
                )

    def test_the_tag_is_part_of_the_content_hash(self):
        plain = seed.LessonSeed.model_validate(lesson())
        tagged = seed.LessonSeed.model_validate(
            lesson(vocab=[{"hangul": "가", "pos": "N", "meaning_vi": "a", "priority": "core", "exam": "kiip-3"}])
        )
        self.assertNotEqual(seed._lesson_hash(plain, None), seed._lesson_hash(tagged, None))


class ShippedTagsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bundle = seed.load_all()

    def test_the_files_load_clean_with_their_tags(self):
        self.assertEqual(self.bundle.problems, [])

    def test_a_review_lesson_has_no_tagged_items_of_its_own(self):
        for r in self.bundle.lessons:
            if r.seed.kind == "review":
                self.assertFalse(r.seed.notes, r.seed.slug)

    def test_a_tagged_note_is_a_note_of_a_kind_the_screen_shows(self):
        for r in self.bundle.lessons:
            for n in r.seed.notes:
                if n.exam:
                    self.assertIsNotNone(n.kind, f"{r.seed.slug}: a tagged note needs a kind")
                    self.assertTrue(n.title, f"{r.seed.slug}: a tagged note needs a title")


def rows(*items):
    result = mock.MagicMock()
    result.all.return_value = list(items)
    return result


class TalliesTests(unittest.IsolatedAsyncioTestCase):
    async def test_counts_words_cards_and_notes_by_lesson_and_stage(self):
        db = mock.MagicMock()
        db.execute = mock.AsyncMock(
            side_effect=[
                rows((1, 10, "kiip-3"), (1, 11, "kiip-3"), (2, 20, "kiip-2")),  # words
                rows((1, 30, "kiip-4")),  # cards
                rows((1, ["kiip-3"]), (2, None), (3, [])),  # notes: lesson 1 has one tagged note
            ]
        )
        out = await content._kiip_tallies(db)
        keys, vocab_n, grammar_n, note_n, stages = out[1]
        self.assertEqual((vocab_n, grammar_n, note_n), (2, 1, 1))
        self.assertEqual(stages, {"kiip-3": 3, "kiip-4": 1})
        self.assertEqual(sorted(keys), [("grammar_point", 30), ("vocab_item", 10), ("vocab_item", 11)])
        self.assertEqual(out[2][1:4], (1, 0, 0))
        self.assertNotIn(3, out)  # nothing tagged: not listed

    def test_nothing_tagged_means_no_kiip_block(self):
        self.assertIsNone(content._kiip_out(None, {}))

    def test_mastered_is_counted_for_a_signed_in_learner_only(self):
        tally = ([("vocab_item", 1), ("vocab_item", 2)], 2, 0, 0, {"kiip-3": 2})
        self.assertIsNone(content._kiip_out(tally, None).mastered)
        strong = (0.95, datetime(2026, 10, 1, tzinfo=timezone.utc))
        weak = (0.2, datetime(2026, 10, 1, tzinfo=timezone.utc))
        out = content._kiip_out(tally, {("vocab_item", 1): strong, ("vocab_item", 2): weak})
        self.assertEqual((out.vocab, out.mastered), (2, 1))


if __name__ == "__main__":
    unittest.main()

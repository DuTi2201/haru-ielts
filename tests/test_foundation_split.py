"""The five Nền tảng lessons cut into sixteen (scripts/split_foundation.py): nothing lost, nothing
doubled, nothing tested before it is taught, and the moves that keep learners' records."""
import re
import unittest
from collections import defaultdict
from types import SimpleNamespace
from unittest import mock

from app.services import lesson_seed as seed

BUNDLE = seed.load_all()
LESSONS = sorted(BUNDLE.lessons, key=lambda r: r.seed.sort_order)
FOUNDATION = [r for r in LESSONS if r.seed.slug.startswith("sinh-hoat-00-nen-tang-")]
# what the five lessons held before the split (words, cards, practice items)
BEFORE = {"vocab": 111 + 46 + 44 + 195 + 105, "grammar": 7 + 8 + 10 + 3 + 5, "exercise_ids": 42 + 45 + 84 + 52 + 57}


class SplitTests(unittest.TestCase):
    def test_sixteen_parts_hold_exactly_what_the_five_lessons_held(self):
        self.assertEqual(len(FOUNDATION), 16)
        for key, total in BEFORE.items():
            got = [x for r in FOUNDATION for x in getattr(r.seed, key)]
            if key == "exercise_ids":  # FS/FSL items were added later, one check per sitting, not part of the cut
                got = [x for x in got if not re.fullmatch(r"FSL?\d+", x)]
            self.assertEqual(len(got), total, key)
        # each part of one lesson: no word, card or item in two parts
        by_group: dict[str, list] = defaultdict(list)
        for r in FOUNDATION:
            by_group[r.seed.split_from or r.seed.slug].append(r)
        self.assertEqual(len(by_group), 5)
        for group, parts in by_group.items():
            for key, ident in (("vocab", lambda v: v.hangul), ("grammar", lambda g: g.pattern), ("exercise_ids", lambda e: e)):
                flat = [ident(x) for r in parts for x in getattr(r.seed, key)]
                self.assertEqual(len(flat), len(set(flat)), (group, key))

    def test_the_first_part_keeps_the_lessons_slug_and_the_others_name_it(self):
        firsts = [r for r in FOUNDATION if not r.seed.split_from]
        self.assertEqual(len(firsts), 5)
        slugs = {r.seed.slug for r in firsts}
        for r in FOUNDATION:
            if r.seed.split_from:
                self.assertIn(r.seed.split_from, slugs)
                first = next(f for f in firsts if f.seed.slug == r.seed.split_from)
                self.assertGreater(r.seed.sort_order, first.seed.sort_order)

    def test_no_question_tests_a_card_of_a_later_lesson(self):
        taught: dict[str, int] = {}
        for r in LESSONS:
            for g in r.seed.grammar:
                taught.setdefault(g.pattern, r.seed.sort_order)
        for r in LESSONS[:20]:  # the free block: Bảng chữ cái, the parts, Buổi sáng, Việc nhà, Ăn uống
            for ex in (r.practice or {}).get("items") or []:
                for q in seed.question_ids(ex):
                    for p in seed.question_grammar(ex, q):
                        if p in taught:
                            self.assertLessEqual(taught[p], r.seed.sort_order, (r.seed.slug, q, p))
                for d in ex.get("detectors") or []:
                    if d.get("pattern") in taught:
                        self.assertLessEqual(taught[d["pattern"]], r.seed.sort_order, (r.seed.slug, ex["id"]))
            for g in r.seed.grammar:
                for b in g.builds_on:
                    if b in taught:
                        self.assertLessEqual(taught[b], r.seed.sort_order, (r.seed.slug, g.pattern, b))

    def test_buoi_sang_and_viec_nha_sit_among_the_parts_in_the_free_beginner_block(self):
        order = [r.seed.slug for r in LESSONS[:19]]
        self.assertEqual(order[0], "hangul-00-bang-chu-cai")
        self.assertIn("sinh-hoat-01-buoi-sang", order)
        self.assertIn("sinh-hoat-02-viec-nha", order)
        self.assertEqual(order[-1], "sinh-hoat-02-viec-nha")
        self.assertTrue(all(r.seed.track == "beginner" for r in LESSONS[:19]))
        self.assertEqual(LESSONS[19].seed.slug, "sinh-hoat-03-an-uong")

    def test_every_part_has_its_own_goal_and_study_guide(self):
        for r in FOUNDATION:
            self.assertTrue(any(n.kind == "goal" for n in r.seed.notes), r.seed.slug)
            self.assertIsNotNone(r.seed.coach, r.seed.slug)
            self.assertTrue(r.seed.grammar, r.seed.slug)


class MoveTests(unittest.TestCase):
    """On sync, a part takes over its words, cards and answers from the lesson it came from as the
    same rows (checked against a real database when the split was made)."""

    def test_a_part_already_written_costs_one_select(self):
        part = next(r for r in FOUNDATION if r.seed.split_from)
        db = mock.MagicMock()
        res = mock.MagicMock()
        res.scalar_one_or_none.return_value = SimpleNamespace(content_hash=part.content_hash)
        db.execute.return_value = res
        seed._rehome_split(db, seed.SeedBundle(lessons=[part], exercises={}))
        self.assertEqual(db.execute.call_count, 1)
        db.add.assert_not_called()

    def test_nothing_left_to_move_writes_nothing(self):
        part = next(r for r in FOUNDATION if r.seed.split_from)
        db = mock.MagicMock()
        missing, old, empty = mock.MagicMock(), mock.MagicMock(), mock.MagicMock()
        missing.scalar_one_or_none.return_value = None
        old.scalar_one_or_none.return_value = SimpleNamespace(id=1, slug=part.seed.split_from, content_hash="x")
        empty.first.return_value = None
        db.execute.side_effect = [missing, old, empty, empty, empty]
        seed._rehome_split(db, seed.SeedBundle(lessons=[part], exercises={}))
        db.add.assert_not_called()
        db.flush.assert_not_called()


if __name__ == "__main__":
    unittest.main()

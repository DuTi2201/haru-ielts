import unittest

from app.services.reading_path import Candidate, pick, studied_lessons

ORDER = [10, 11, 12, 13, 14]


class StudiedTests(unittest.TestCase):
    def test_lessons_before_the_next_one(self):
        self.assertEqual(studied_lessons(ORDER, 12), [10, 11])

    def test_everything_studied(self):
        self.assertEqual(studied_lessons(ORDER, None), ORDER)

    def test_unknown_next_lesson(self):
        self.assertEqual(studied_lessons(ORDER, 99), [])


class PickTests(unittest.TestCase):
    def test_nothing_before_the_closest_lesson_is_studied(self):
        a = Candidate("a", 3, [12])
        self.assertIsNone(pick([a], [10, 11], set(), editorial_goal=False))

    def test_offered_after_its_lesson(self):
        a = Candidate("a", 3, [11, 12])
        self.assertEqual(pick([a], [10, 11], set(), editorial_goal=False), a)

    def test_the_article_of_the_lesson_just_studied_first(self):
        old = Candidate("old", 3, [10])
        new = Candidate("new", 3, [11])
        self.assertEqual(pick([old, new], [10, 11], set(), editorial_goal=False).id, "new")

    def test_unread_before_read(self):
        read = Candidate("read", 3, [11])
        fresh = Candidate("fresh", 4, [10])
        self.assertEqual(pick([read, fresh], [10, 11], {"read"}, editorial_goal=False).id, "fresh")

    def test_a_read_article_is_still_offered_when_nothing_else_is(self):
        read = Candidate("read", 3, [10])
        self.assertEqual(pick([read], [10], {"read"}, editorial_goal=False).id, "read")

    def test_easier_first_among_equals(self):
        hard = Candidate("hard", 5, [11])
        easy = Candidate("easy", 3, [11])
        self.assertEqual(pick([hard, easy], [10, 11], set(), editorial_goal=False).id, "easy")

    def test_unplaced_article_only_for_the_editorial_goal(self):
        legacy = Candidate("legacy", 5, [], created_ts=5)
        self.assertIsNone(pick([legacy], [10], set(), editorial_goal=False))
        self.assertEqual(pick([legacy], [10], set(), editorial_goal=True), legacy)

    def test_placed_article_beats_unplaced(self):
        legacy = Candidate("legacy", 5, [], created_ts=5)
        placed = Candidate("placed", 3, [10])
        self.assertEqual(pick([legacy, placed], [10], set(), editorial_goal=True).id, "placed")


if __name__ == "__main__":
    unittest.main()

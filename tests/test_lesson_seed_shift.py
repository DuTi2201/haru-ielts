"""Moving every lesson down one place for the Hangul lesson (lesson_seed.shift_lessons)."""
import json
import tempfile
import unittest
from pathlib import Path

from app.services.lesson_seed import shift_lessons


class ShiftLessonsTests(unittest.TestCase):
    def test_only_the_lesson_position_moves_and_the_layout_stays(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            a = '{\n  "slug": "a",\n  "sort_order": 1,\n  "practice": {"items": [{"sort_order": 5}]}\n}\n'
            (d / "a.json").write_text(a, encoding="utf-8")
            (d / "b.json").write_text('{\n  "slug": "b",\n  "sort_order": 71\n}\n', encoding="utf-8")
            self.assertEqual(shift_lessons(1, d), 2)
            moved = (d / "a.json").read_text(encoding="utf-8")
            self.assertEqual(moved, a.replace('"sort_order": 1,', '"sort_order": 2,'))
            self.assertEqual(json.loads((d / "b.json").read_text(encoding="utf-8"))["sort_order"], 72)


if __name__ == "__main__":
    unittest.main()

"""The migration that merges editorial copies into course cards names its targets by lesson slug and
pattern; each must be a card the seed actually has, or that row would silently stay a duplicate."""
import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIGRATION = ROOT / "alembic" / "versions" / "c5e1a7d3f9b2_merge_editorial_cards.py"


def _load():
    spec = importlib.util.spec_from_file_location("merge_editorial_cards", MIGRATION)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class EditorialCardMergeTests(unittest.TestCase):
    def setUp(self):
        self.mig = _load()
        self.lessons = {}
        for path in (ROOT / "app" / "seed" / "lessons").glob("*.json"):
            d = json.loads(path.read_text(encoding="utf-8"))
            self.lessons[d["slug"]] = {g["pattern"] for g in d.get("grammar", [])}

    def test_every_lesson_target_is_a_seed_card(self):
        for orphan, rule in self.mig.GRAMMAR.items():
            if rule[0] == "lesson":
                self.assertIn(rule[1], self.lessons, orphan)
                self.assertIn(rule[2], self.lessons[rule[1]], orphan)

    def test_a_rename_is_written_like_the_course_cards(self):
        for orphan, rule in self.mig.GRAMMAR.items():
            if rule[0] == "rename":
                self.assertRegex(rule[1], r"^(N|V|A|V/A) \+ ", orphan)


if __name__ == "__main__":
    unittest.main()

"""What the learner reads must be written for the learner.

The lesson files started life as a teacher's notes and a printable worksheet, and some of that
voice leaked into the app: "chưa xác minh (mục 12.2 của ghi chép)", "nếu phát cho học viên",
"giáo viên đọc kịch bản", grammar codes such as G5-4 / SH3. These tests keep it out:

* every learner-facing string in the seed is checked against a short list of give-aways;
* notes for the maintainer live in `editor_notes`, which is never stored, shown or read aloud;
* every note carries a `kind` (the lesson screen groups notes by it).

Honest caveats written to the learner ("số liệu chưa đối chiếu văn bản gốc") are welcome; what is
banned is talk about the *making* of the lesson."""
import json
import re
import unittest
from pathlib import Path

from app.services import lesson_audio
from app.services import lesson_seed as seed

SEED_DIR = Path(seed.__file__).resolve().parents[1] / "seed"

# (pattern, what it gives away)
GIVE_AWAYS = [
    (r"mục \d+(?:\.\d+)*\b", "a section number of the author's notes"),
    (r"12\.2", "a section number of the author's notes"),
    (r"ghi chép", "the author's notes"),
    (r"tài liệu gốc|trang gốc", "talk about the source document"),
    (r"sổ ngữ pháp", "the author's grammar register"),
    (r"\bnhóm \d", "the author's numbering of topic groups"),
    (r"học viên|giáo viên|người dạy|phát cho", "written to a teacher, not to the learner"),
    (r"biên tập", "talk about the editing"),
    (r"\bMình\b", "the author speaking in the first person"),
    (r"\bmình (?:soạn|đặt)\b|\bdo mình (?:soạn|đặt)\b", "the author speaking in the first person"),
    (r"mình chưa (?:xác minh|kiểm tra|đối chiếu|mở)", "the author speaking in the first person"),
    (r"\bG\d-\d\b|\bSH\d\b|〔(?:G|SH)", "an internal grammar code"),
]
GIVE_AWAY_RES = [(re.compile(p), why) for p, why in GIVE_AWAYS]
SKIPPED_KEYS = {"source", "editor_notes"}  # audit data and maintainer notes: not learner-facing


def _strings(node, path=()):
    if isinstance(node, dict):
        for k, v in node.items():
            if k not in SKIPPED_KEYS:
                yield from _strings(v, path + (k,))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from _strings(v, path + (i,))
    elif isinstance(node, str):
        yield path, node


class LearnerVoiceTests(unittest.TestCase):
    def test_no_give_aways_in_any_learner_facing_text(self):
        found = []
        for f in sorted(SEED_DIR.rglob("*.json")):
            if f.parent.name == "nikl":  # 한국어기초사전's own words, quoted as the dictionary has them
                continue
            for path, text in _strings(json.loads(f.read_text(encoding="utf8"))):
                for rx, why in GIVE_AWAY_RES:
                    m = rx.search(text)
                    if m:
                        where = "/".join(map(str, path))
                        found.append(f"{f.relative_to(SEED_DIR)} {where}: “{m.group(0)}” ({why})")
        self.assertEqual(found, [], "\n" + "\n".join(found[:25]))


class EditorNotesTests(unittest.TestCase):
    BUNDLE = seed.load_all()

    def test_the_unverified_lists_moved_out_of_the_lessons(self):
        by_slug = {r.seed.slug: r.seed for r in self.BUNDLE.lessons}
        for slug in ("quan-he-05-noi-o", "quan-he-06-hang-xom-rac", "quan-he-07-moi-truong"):
            s = by_slug[slug]
            self.assertTrue(s.editor_notes, slug)
            titles = {n.title for n in s.notes}
            for n in s.editor_notes:
                self.assertNotIn(n.title, titles, slug)

    def test_editor_notes_are_not_in_the_stored_text_nor_in_the_lecture(self):
        for r in self.BUNDLE.lessons:
            s = r.seed
            if not s.editor_notes:
                continue
            stored = seed.lesson_text(s)
            payload = json.dumps([n.model_dump(mode="json", exclude_none=True) for n in s.notes], ensure_ascii=False)
            for n in s.editor_notes:
                self.assertNotIn(n.body[:60], stored, s.slug)
                self.assertNotIn(n.body[:60], payload, s.slug)
            self.assertNotIn("editor_notes", payload)

    def test_the_lecture_never_says_what_is_unverified_about_the_lesson_itself(self):
        # the lecture reads every note: a note about the making of the lesson would be spoken
        for r in self.BUNDLE.lessons:
            if r.seed.kind != "lesson":
                continue
            for n in r.seed.notes:
                for rx, why in GIVE_AWAY_RES:
                    self.assertIsNone(rx.search(n.body), f"{r.seed.slug} / {n.title}: {why}")
                    self.assertIsNone(rx.search(n.title or ""), f"{r.seed.slug} / {n.title}: {why}")


class NoteKindTests(unittest.TestCase):
    BUNDLE = seed.load_all()

    def test_every_note_of_every_lesson_has_a_kind(self):
        missing = [
            f"{r.seed.slug}: {n.title}"
            for r in self.BUNDLE.lessons
            if r.seed.kind == "lesson"
            for n in r.seed.notes
            if n.kind is None
        ]
        self.assertEqual(missing, [])

    def test_at_most_one_goal_and_it_comes_first(self):
        for r in self.BUNDLE.lessons:
            kinds = [n.kind for n in r.seed.notes]
            self.assertLessEqual(kinds.count("goal"), 1, r.seed.slug)
            if "goal" in kinds:
                self.assertEqual(kinds[0], "goal", r.seed.slug)

    def test_the_second_topic_lessons_state_their_goal(self):
        for r in self.BUNDLE.lessons:
            if r.seed.bank == "quan-he" and r.seed.kind == "lesson":
                self.assertIn("goal", [n.kind for n in r.seed.notes], r.seed.slug)

    def test_a_note_without_a_kind_is_still_valid(self):
        n = seed.NoteSeed(title="x", body="y")
        self.assertIsNone(n.kind)
        with self.assertRaises(ValueError):
            seed.NoteSeed(title="x", body="y", kind="bogus")

    def test_the_lecture_filter_skips_provenance_lines(self):
        self.assertTrue(lesson_audio._is_editorial("Nghĩa chi tiết là phần biên soạn bổ sung; nguồn chỉ ghi “Món”."))
        self.assertFalse(lesson_audio._is_editorial("Dạng thường: 먹다 · 마시다"))


if __name__ == "__main__":
    unittest.main()

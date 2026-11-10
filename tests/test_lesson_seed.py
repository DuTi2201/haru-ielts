"""The seeded lessons (lesson-v5): the files must load, hang together, and be written to
the database only when they changed."""
import copy
import re
import unittest
from types import SimpleNamespace
from unittest import mock

from pydantic import ValidationError

from app.services import lesson_seed as seed
from app.services import weakness


class SeedFilesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bundle = seed.load_all()

    def test_the_files_load_without_problems(self):
        self.assertEqual(self.bundle.problems, [])
        self.assertEqual(len(self.bundle.lessons), 83)  # Bảng chữ cái + 16 foundation lessons (5, cut into 16) + 32 topic lessons + one review lesson per topic + the 8 lessons of the Viết 54 course + the lessons of topic 5 + the reading lesson that follows it
        by_topic: dict[str, int] = {}
        for r in self.bundle.lessons:
            by_topic[r.seed.topic] = by_topic.get(r.seed.topic, 0) + 1
        self.assertEqual(
            by_topic,
            {
                "Nhập môn": 17,
                "Sinh hoạt hàng ngày": 10,
                "Quan hệ xã hội, Sự kiện & Không gian sống": 12,
                "Bổ trợ · Nhập cảnh & Thủ tục cư trú": 6,
                "Đời sống xã hội & Công sở": 8,
                "Bổ trợ · Viết câu 54 từ con số 0": 8,
                "Xã hội, Tư tưởng & Chuyên ngành": 21,
                "Bổ trợ · Đọc hiểu: chủ đề, thái độ, mục đích": 1,
            },
        )

    def test_lessons_come_out_in_curriculum_order(self):
        order = [(r.seed.track, r.seed.sort_order) for r in self.bundle.lessons]
        self.assertEqual(order, sorted(order, key=lambda t: (seed.TRACKS.index(t[0]), t[1])))
        self.assertEqual(len({r.seed.slug for r in self.bundle.lessons}), 83)

    def test_every_exercise_belongs_to_a_lesson_and_every_question_id_is_unique(self):
        used = {i for r in self.bundle.lessons for i in r.seed.exercise_ids}
        self.assertEqual(used, set(self.bundle.exercises))
        ids = [q for ex in self.bundle.exercises.values() for q in seed._question_ids(ex)]
        self.assertEqual(len(ids), len(set(ids)))

    def test_a_multiple_choice_answer_is_one_of_its_options(self):
        for ex in self.bundle.exercises.values():
            for q in ex.get("questions", []):
                self.assertIn(q["answer"], [o["id"] for o in q["options"]], q["id"])
                self.assertTrue(q["explanation_vi"].strip(), q["id"])

    def test_a_writing_blank_has_an_accepted_answer(self):
        for ex in self.bundle.exercises.values():
            for blank in ex.get("blanks", []):
                self.assertTrue(blank["accepted"], f"{ex['id']}:{blank['id']}")

    def test_the_practice_set_carries_its_counts(self):
        for r in self.bundle.lessons:
            if not r.seed.exercise_ids:
                continue
            counts = r.practice["counts"]
            self.assertEqual(counts["items"], len(r.seed.exercise_ids))
            self.assertEqual(counts["questions"], sum(counts["by_skill"].values()))
            self.assertEqual(counts["questions"], len(seed.question_index(r.practice)))

    def test_question_ids_of_each_kind(self):
        fill = {"id": "W51", "type": "write_fill", "blanks": [{"id": "a"}, {"id": "b"}]}
        self.assertEqual(seed._question_ids(fill), ["W51:a", "W51:b"])
        self.assertEqual(seed._question_ids({"id": "W53", "type": "write_essay"}), ["W53"])
        self.assertEqual(seed._question_ids({"id": "S1", "type": "speak"}), ["S1"])
        self.assertEqual(seed._question_ids({"id": "L1", "type": "listen_picture", "questions": [{"id": "L1"}]}), ["L1"])

    def test_every_exercise_type_has_a_weakness_label(self):
        for ex in self.bundle.exercises.values():
            self.assertIn(ex["type"], weakness.ERROR_LABELS, ex["id"])

    def test_scene_icons_used_exist(self):
        def walk(node):
            if isinstance(node, dict):
                if "icons" in node and "caption_vi" in node:
                    yield from node["icons"]
                for v in node.values():
                    yield from walk(v)
            elif isinstance(node, list):
                for v in node:
                    yield from walk(v)

        for icon in walk(list(self.bundle.exercises.values())):
            self.assertIn(icon, seed.SCENE_ICONS)


class ValidationTests(unittest.TestCase):
    def lesson(self, **over):
        base = {
            "slug": "sinh-hoat-99-thu", "title": "Thử", "topic": "Thử", "track": "intermediate", "level": 3,
            "sort_order": 99, "summary": "x", "vocab": [{"hangul": "가", "pos": "N", "meaning_vi": "a", "priority": "core"}],
        }
        base.update(over)
        return base

    def test_a_good_lesson_is_accepted(self):
        seed.LessonSeed.model_validate(self.lesson())

    def test_duplicates_and_unknown_fields_are_rejected(self):
        with self.assertRaises(ValidationError):
            seed.LessonSeed.model_validate(self.lesson(vocab=[{"hangul": "가", "pos": "N", "meaning_vi": "a", "priority": "core"}] * 2))
        with self.assertRaises(ValidationError):
            seed.LessonSeed.model_validate(self.lesson(surprise=1))
        with self.assertRaises(ValidationError):
            seed.LessonSeed.model_validate(self.lesson(track="expert"))

    def test_an_exercise_in_the_wrong_skill_file_is_rejected(self):
        raw = {"id": "X1", "skill": "reading", "type": "read_cloze", "title_vi": "t", "questions": []}
        with self.assertRaises(ValueError):
            seed._validate_exercise(raw, "listening")


class ExerciseBankTests(unittest.TestCase):
    """A topic may have its own practice bank (app/seed/exercises/<bank>/): its ids and
    guides stay apart from the first topic's, which uses the same L1 / R1 / S1 names."""

    @classmethod
    def setUpClass(cls):
        cls.bundle = seed.load_all()
        cls.exercises, cls.bank_of, cls.shared, cls.problems = seed.load_exercise_banks()

    def test_the_banks_load_clean_and_are_named_by_their_folder(self):
        self.assertEqual(self.problems, [])
        self.assertEqual(set(self.shared), {"", "hangul", "quan-he", "nhap-canh", "cong-so", "viet54", "xa-hoi", "doc-hieu"})
        self.assertEqual(set(self.bank_of.values()), {"", "hangul", "quan-he", "nhap-canh", "cong-so", "viet54", "xa-hoi", "doc-hieu"})
        self.assertEqual(set(self.exercises), set(self.bundle.exercises))

    def test_a_lesson_only_uses_exercises_of_its_own_bank(self):
        for r in self.bundle.lessons:
            for ex_id in r.seed.exercise_ids:
                self.assertEqual(self.bank_of[ex_id], r.seed.bank, f"{r.seed.slug}: {ex_id}")
        topic2 = [r for r in self.bundle.lessons if r.seed.topic.startswith("Quan hệ")]
        self.assertTrue(topic2)
        for r in topic2:
            self.assertEqual(r.seed.bank, "quan-he")
            self.assertTrue(all(i.startswith("Q") for i in r.seed.exercise_ids))

    def test_the_supplementary_topic_comes_last_with_its_own_ids_and_every_skill(self):
        topic3 = sorted((r for r in self.bundle.lessons if r.seed.bank == "nhap-canh"), key=lambda r: r.seed.sort_order)
        self.assertEqual([r.seed.sort_order for r in topic3], [40, 41, 42, 43, 44, 45])
        self.assertEqual([r.seed.kind for r in topic3], ["lesson"] * 5 + ["review"])
        self.assertLess(max(r.seed.sort_order for r in self.bundle.lessons if r.seed.bank in ("", "quan-he")), 40)
        for r in topic3:
            self.assertTrue(all(i.startswith("NC") for i in r.seed.exercise_ids), r.seed.slug)
            by_skill = r.practice["counts"]["by_skill"]
            for skill in ("listening", "reading", "writing", "speaking"):
                self.assertTrue(by_skill.get(skill), f"{r.seed.slug}: no {skill}")

    def test_topic_four_follows_with_its_own_ids_and_every_skill(self):
        topic4 = sorted((r for r in self.bundle.lessons if r.seed.bank == "cong-so"), key=lambda r: r.seed.sort_order)
        self.assertEqual([r.seed.sort_order for r in topic4], list(range(46, 54)))
        self.assertEqual([r.seed.kind for r in topic4], ["lesson"] * 7 + ["review"])
        for r in topic4:
            self.assertTrue(all(i.startswith("C") for i in r.seed.exercise_ids), r.seed.slug)
            by_skill = r.practice["counts"]["by_skill"]
            for skill in ("listening", "reading", "writing", "speaking"):
                self.assertTrue(by_skill.get(skill), f"{r.seed.slug}: no {skill}")

    def test_the_practice_set_carries_the_guides_of_its_bank(self):
        first = next(r for r in self.bundle.lessons if r.seed.bank == "")
        second = next(r for r in self.bundle.lessons if r.seed.bank == "quan-he")
        self.assertNotEqual(first.practice["overview"], second.practice["overview"])
        # the extension items are cards of the lessons themselves now, not a bank-wide list
        self.assertNotIn("extension", first.practice)
        self.assertNotIn("extension", second.practice)
        for skill, guide in second.practice["guides"].items():
            self.assertEqual(guide, self.shared["quan-he"]["guides"][skill])

    def test_the_second_topic_has_every_skill_and_every_source_item(self):
        ids = {i for i, b in self.bank_of.items() if b == "quan-he"}
        want = (
            {f"QL{n}" for n in range(1, 21)}
            | {f"QR{n}" for n in range(1, 21)}
            | {f"QS{n}" for n in range(1, 7)}
            | {f"QW51{c}" for c in "ABCD"}
            | {f"QW52{c}" for c in "ABC"}
            | {f"QW53{c}" for c in "ABCDEF"} | {"QVW53"}
            | {f"QW54{c}" for c in "ABCDEF"}
        )
        # + the practice questions of the 🟣 extension cards (QE<item><a-d>)
        letters = {1: "abcd", 2: "abcd", 3: "abc", 4: "abc", 5: "abc", 6: "abc", 7: "abcd", 8: "abcd", 9: "abcd", 10: "abc", 11: "abc", 12: "abcd"}
        want |= {f"QE{n:02d}{c}" for n, cs in letters.items() for c in cs}
        # + the topic review lesson (4 listening, 16 reading, the Viết 54 and the Nói S6 capstone)
        want |= {f"QVL{n:02d}" for n in range(1, 5)} | {f"QVR{n:02d}" for n in range(1, 17)} | {"QVW54", "QVS6"}
        # + 12 review questions for the cards of the foundation round (QVR17–28)
        want |= {f"QVR{n:02d}" for n in range(17, 29)}
        # + the review brought up to a TOPIK I paper: 26 more listening (QVLN) and 12 more reading (QVR29–40)
        want |= {f"QVLN{n:02d}" for n in range(1, 27)} | {f"QVR{n:02d}" for n in range(29, 41)}
        # + the "Tạo câu" ladder of lessons 1–11 (QBO tiles, QBF frames, QBC joins, QBE paragraphs)
        want |= {f"QBO{n:02d}" for n in range(1, 71)} | {f"QBF{n:02d}" for n in range(1, 23)}
        want |= {f"QBC{n:02d}" for n in range(1, 12)} | {f"QBE{n:02d}" for n in range(1, 12)}
        # + the foundation round woven into the topic: 41 reading questions (QFR), 9 tile orders (QFBO), 5 frames (QFBF)
        want |= {f"QFR{n:02d}" for n in range(1, 42)} | {f"QFBO{n:02d}" for n in range(1, 10)} | {f"QFBF{n:02d}" for n in range(1, 6)}
        # + the listening round woven into lessons 1–11 (QLN01–81, about a quarter of every lesson)
        want |= {f"QLN{n:02d}" for n in range(1, 82)}
        # + the dictations (QD01–02 of the review lesson, QD03–24: two in each of lessons 1–11; listen, copy down,
        # listen again, learn the words)
        want |= {f"QD{n:02d}" for n in range(1, 25)}
        # + the output contract of Gia đình (QGF…) and Nơi ở (QNH…): a model text to read or hear, the
        # ladder up to the learner's own text (Bước 5) and speaking on the lesson's own topic
        want |= {"QGFL1", "QGFR1", "QGFO1", "QGFO2", "QGFF1", "QGFC1", "QGFE1", "QGFS1", "QGFS2"}
        want |= {"QNHR1", "QNHO1", "QNHO2", "QNHF1", "QNHC1", "QNHE1", "QNHE2", "QNHS1"}
        # + the same output contract for the other lessons of the topic (QU<sort_order>…: a model text, the
        # ladder up to Bước 5, speaking on the lesson's topic); every lesson 18–27 except 21 has one
        contract = {i for i in ids if re.fullmatch(r"QU(\d\d)[A-Z]+\d*", i)}
        self.assertEqual({int(i[2:4]) for i in contract}, {18, 19, 20, 22, 23, 24, 25, 26, 27})
        want |= contract
        # + the beginner grammar that needs -(으)시- / -아/어 주다 (lesson 17): -(으)시겠어요? and -아/어 줄게요/줄까요?
        want |= {"QGB18a", "QGB18b", "QGB18c", "QGB18d"}
        # + one reading question for each 🟣 card added from the TOPIK II grammar list (QSUP01–07)
        want |= {f"QSUP{n:02d}" for n in range(1, 8)}
        self.assertEqual(ids, want)

    def test_every_54_essay_has_a_model_answer_of_600_to_700_characters(self):
        # 53-C and 54-D/E/F have a model written by Haru (the source has none); five paragraphs, 한다체
        for ex_id in ("QW53A", "QW53C", "QW54A", "QW54B", "QW54C", "QW54D", "QW54E", "QW54F"):
            self.assertTrue(self.exercises[ex_id]["model_answer_ko"], ex_id)
        for ex_id in ("QW54D", "QW54E", "QW54F"):
            model = self.exercises[ex_id]["model_answer_ko"]
            self.assertTrue(600 <= len(model.replace("\n", "")) <= 700, ex_id)
            self.assertEqual(model.count("\n"), 4, ex_id)
            self.assertNotIn("요.", model, ex_id)

    def test_an_unknown_bank_or_an_id_of_another_bank_is_a_problem(self):
        import json
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "exercises" / "b").mkdir(parents=True)
            (root / "lessons").mkdir()
            reading = {"skill": "reading", "guide": [], "items": [{
                "id": "R1", "skill": "reading", "type": "read_cloze", "title_vi": "t",
                "questions": [{"id": "R1", "options": [{"id": "1", "text": "a"}, {"id": "2", "text": "b"}],
                               "answer": "1", "explanation_vi": "e"}]}]}
            (root / "exercises" / "reading.json").write_text(json.dumps(reading), encoding="utf-8")
            (root / "exercises" / "b" / "reading.json").write_text(
                json.dumps(reading | {"items": [reading["items"][0] | {"id": "R2", "questions": [
                    reading["items"][0]["questions"][0] | {"id": "R2"}]}]}), encoding="utf-8")

            def lesson(slug, order, bank, ids):
                body = {"slug": slug, "title": "t", "topic": "x", "track": "beginner", "level": 1, "sort_order": order,
                        "summary": "s", "vocab": [{"hangul": "가", "pos": "N", "meaning_vi": "m", "priority": "core"}],
                        "bank": bank, "exercise_ids": ids}
                (root / "lessons" / f"{slug}.json").write_text(json.dumps(body), encoding="utf-8")

            lesson("aaa", 1, "", ["R1"])
            lesson("bbb", 2, "b", ["R2"])
            ok = seed.load_all(root)
            self.assertEqual(ok.problems, [])
            self.assertEqual({r.seed.slug for r in ok.lessons}, {"aaa", "bbb"})

            lesson("ccc", 3, "b", ["R1"])  # R1 lives in the root bank
            lesson("ddd", 4, "nope", [])
            bad = seed.load_all(root)
            self.assertEqual(len(bad.problems), 2, bad.problems)
            self.assertTrue(any("ccc.json" in p and "R1" in p for p in bad.problems))
            self.assertTrue(any("ddd.json" in p and "nope" in p for p in bad.problems))

    def test_the_same_id_in_two_banks_is_a_problem(self):
        import json
        import tempfile
        from pathlib import Path

        item = {"id": "R1", "skill": "reading", "type": "read_cloze", "title_vi": "t",
                "questions": [{"id": "R1", "options": [{"id": "1", "text": "a"}, {"id": "2", "text": "b"}],
                               "answer": "1", "explanation_vi": "e"}]}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "b").mkdir()
            for folder in (root, root / "b"):
                (folder / "reading.json").write_text(
                    json.dumps({"skill": "reading", "guide": [], "items": [item]}), encoding="utf-8")
            _, _, _, problems = seed.load_exercise_banks(root)
            self.assertTrue(problems, "two banks may not both define R1")


class OutputContractTests(unittest.TestCase):
    """Bước 5 (the learner's own text) lists what its model answer is built from (`uses`), and the
    loader holds the sample to it: nothing the learner has not met by that lesson."""

    def essay(self, **over):
        raw = {
            "id": "T5", "skill": "build", "type": "write_essay", "rung": 5, "number": "Bước 5", "title_vi": "t",
            "points": 10, "limits": {"min": 10, "max": 300}, "model_answer_ko": "저희 가족은 모두 네 명입니다.",
            "uses": [{"form": "저희 가족", "card": "저희"}],
        }
        raw.update(over)
        return raw

    def lesson(self, sort_order, vocab=(), grammar=()):
        return seed.LessonSeed.model_validate({
            "slug": f"thu-{sort_order:02d}", "title": "Thử", "topic": "Thử", "track": "intermediate", "level": 3,
            "sort_order": sort_order, "summary": "x",
            "vocab": [{"hangul": h, "pos": "X", "meaning_vi": "a", "priority": "core"} for h in vocab],
            "grammar": [{"pattern": p, "meaning_vi": "a", "importance": "must"} for p in grammar],
        })

    def test_a_rung_5_text_needs_its_model_and_its_uses(self):
        seed.WriteEssay.model_validate(self.essay())
        with self.assertRaises(ValidationError):
            seed.WriteEssay.model_validate(self.essay(uses=[]))
        with self.assertRaises(ValidationError):
            seed.WriteEssay.model_validate(self.essay(model_answer_ko=""))
        with self.assertRaises(ValidationError):
            seed.WriteEssay.model_validate(self.essay(rung=6))

    def test_a_piece_must_be_in_the_model_and_taught_by_then(self):
        early, here, later = self.lesson(1, vocab=["저희"]), self.lesson(2, vocab=["모두"]), self.lesson(3, vocab=["무척"])
        first = seed.taught_at([early, here, later])
        ok = self.essay(uses=[{"form": "저희 가족", "card": "저희"}, {"form": "모두", "card": "모두"}])
        self.assertEqual(seed._uses_problems(here, [ok], first), [])
        bad = self.essay(uses=[
            {"form": "아늑한", "card": "저희"},  # not in the model answer
            {"form": "네 명", "card": "명수"},  # no lesson has this card
            {"form": "저희", "card": "무척"},  # taught only after this lesson
        ])
        problems = seed._uses_problems(here, [bad], first)
        self.assertEqual(len(problems), 3, problems)
        self.assertIn("not in the model answer", problems[0])
        self.assertIn("not a card of any lesson", problems[1])
        self.assertIn("later lesson", problems[2])

    def test_the_family_and_home_lessons_promise_a_text_the_learner_can_write(self):
        bundle = seed.load_all()
        by_slug = {r.seed.slug: r for r in bundle.lessons}
        for slug, ids in (("quan-he-01-gia-dinh", {"QGFE1"}), ("quan-he-05-noi-o", {"QNHE1", "QNHE2"})):
            items = {it["id"]: it for it in by_slug[slug].practice["items"]}
            self.assertTrue(ids <= set(items), slug)
            for i in ids:
                self.assertEqual(items[i]["rung"], 5)
                self.assertGreaterEqual(len(items[i]["uses"]), 10)
        # the lesson's speaking is about the lesson's topic: the house, trip, survey and noise items stay in their own lessons
        family = set(by_slug["quan-he-01-gia-dinh"].seed.exercise_ids)
        self.assertFalse({"QS1", "QS3", "QS5", "QS6"} & family)
        self.assertTrue({"QGFS1", "QGFS2"} <= family)


class MovedCardsTests(unittest.TestCase):
    """The migration that moves cards between lessons (keeping vocab_item.id, so learners keep their
    review schedule) and the seed must agree: otherwise the startup sync deletes the moved rows."""

    def test_the_seed_lists_each_moved_card_in_its_new_lesson_only(self):
        import importlib.util
        from pathlib import Path

        path = Path(__file__).resolve().parent.parent / "alembic" / "versions" / "b3d7f1a9c5e2_move_off_topic_family_cards.py"
        spec = importlib.util.spec_from_file_location("move_cards", path)
        mod = importlib.util.module_from_spec(spec)
        with mock.patch.dict("sys.modules", {"alembic": SimpleNamespace(op=None)}):
            spec.loader.exec_module(mod)
        vocab = {r.seed.slug: {v.hangul for v in r.seed.vocab} for r in seed.load_all().lessons}
        for hangul, target in mod.MOVES.items():
            self.assertIn(hangul, vocab[target], f"{hangul} should be a card of {target}")
            self.assertNotIn(hangul, vocab[mod.SOURCE], f"{hangul} should have left {mod.SOURCE}")

    def test_the_seed_agrees_with_the_move_into_lessons_1_to_16(self):
        import importlib.util
        from pathlib import Path

        path = Path(__file__).resolve().parent.parent / "alembic" / "versions" / "e3b5d7f9a1c4_bring_core_words_earlier.py"
        spec = importlib.util.spec_from_file_location("move_core_words", path)
        mod = importlib.util.module_from_spec(spec)
        with mock.patch.dict("sys.modules", {"alembic": SimpleNamespace(op=None)}):
            spec.loader.exec_module(mod)
        # a Nền tảng lesson cut into parts (split_from) counts as one: the word is in one of its parts
        vocab: dict[str, set[str]] = {}
        for r in seed.load_all().lessons:
            vocab.setdefault(r.seed.split_from or r.seed.slug, set()).update(v.hangul for v in r.seed.vocab)
        for hangul, src, dst in mod.MOVES:
            self.assertIn(hangul, vocab[dst], f"{hangul} should be a card of {dst}")
            self.assertNotIn(hangul, vocab[src], f"{hangul} should have left {src}")


class HashTests(unittest.TestCase):
    def test_editing_an_exercise_changes_the_lessons_hash(self):
        bundle = seed.load_all()
        first = bundle.lessons[0]
        practice = copy.deepcopy(first.practice)
        practice["items"][0]["title_vi"] += "!"
        self.assertNotEqual(first.content_hash, seed._lesson_hash(first.seed, practice))


class SyncTests(unittest.TestCase):
    def test_nothing_is_written_when_the_files_have_problems(self):
        bundle = seed.SeedBundle(lessons=[], exercises={}, problems=["broken.json: nope"])
        db = mock.MagicMock()
        with self.assertRaises(ValueError):
            seed.sync_lessons(db, bundle)
        db.execute.assert_not_called()
        db.commit.assert_not_called()

    def test_an_unchanged_lesson_costs_one_select_and_no_write(self):
        bundle = seed.load_all()
        by_slug = {r.seed.slug: r for r in bundle.lessons}

        def execute(stmt):
            res = mock.MagicMock()
            slug = stmt.compile().params.get("slug_1")
            res.scalar_one_or_none.return_value = SimpleNamespace(content_hash=by_slug[slug].content_hash)
            return res

        db = mock.MagicMock()
        db.execute.side_effect = execute
        report = seed.sync_lessons(db, bundle)
        self.assertEqual(set(report.values()), {"unchanged"})
        self.assertEqual(len(report), 83)
        db.add.assert_not_called()
        # one SELECT a lesson, and one more for each Nền tảng part (is its move done?)
        parts = sum(1 for r in bundle.lessons if r.seed.split_from)
        self.assertEqual(db.execute.call_count, 83 + parts)


if __name__ == "__main__":
    unittest.main()


class ExtensionCardTests(unittest.TestCase):
    """The grammar and words that only the exam banks used ("kiến thức mở rộng") are real
    cards of the lesson that uses them, with practice questions of their own."""

    TIER = "🟣 Mở rộng · Từ trong bộ đề"

    @classmethod
    def setUpClass(cls):
        cls.bundle = seed.load_all()
        cls.lessons = {r.seed.slug: r for r in cls.bundle.lessons}
        cls.cards = [(r.seed.slug, g) for r in cls.bundle.lessons for g in r.seed.grammar if (g.source or "").startswith("EXT-")]

    def test_every_extension_grammar_item_is_a_full_card(self):
        # 11 in the first topic, 12 in the second, 3 in the fourth, + 68 from the TOPIK II grammar list (EXT-SUP-…)
        self.assertEqual(len(self.cards), 94)
        self.assertEqual(len({g.source for _, g in self.cards}), 94)
        for slug, g in self.cards:
            self.assertTrue(g.usage_context_vi.startswith("🟣 **Kiến thức mở rộng** · "), g.source)
            self.assertGreaterEqual(len(g.contrasts), 2, g.source)
            self.assertTrue(g.topik_tip_vi and "**" not in g.topik_tip_vi, g.source)
            self.assertIn("Biên soạn bổ sung", g.note_vi or "", g.source)
            self.assertEqual(len((g.example_ko or "").splitlines()), 3, g.source)
            self.assertEqual(len((g.example_vi or "").splitlines()), 3, g.source)

    def test_the_extension_words_have_a_meaning_and_an_example(self):
        words = [(r.seed.slug, v) for r in self.bundle.lessons for v in r.seed.vocab if v.family == self.TIER]
        self.assertEqual(len(words), 90)  # 17 in the first topic, 73 in the second
        for slug, v in words:
            self.assertTrue(v.meaning_vi and v.example_ko and v.example_vi, v.hangul)
            self.assertTrue(v.source.startswith("EXT-V-"), v.hangul)

    def test_a_card_and_its_questions_live_in_the_same_lesson(self):
        by_item = {g.source[4:]: slug for slug, g in self.cards}  # "T2-01" -> lesson
        placed = 0
        for slug, r in self.lessons.items():
            for ex_id in r.seed.exercise_ids:
                m = re.fullmatch(r"(Q?)E(\d\d)[a-d]", ex_id)
                if not m:
                    continue
                placed += 1
                item = f"{'T2' if m.group(1) else 'T1'}-{m.group(2)}"
                self.assertEqual(by_item[item], slug, ex_id)
                ex = self.bundle.exercises[ex_id]
                self.assertTrue(ex["title_vi"].startswith("🟣 Mở rộng · "), ex_id)
        self.assertEqual(placed, 76)

    def test_the_extension_cards_are_read_aloud_cleanly(self):
        from app.services import lesson_audio

        for slug, g in self.cards:
            spoken = lesson_audio.speakable_pattern(g.pattern)
            self.assertTrue(spoken.strip(), g.source)
            self.assertNotRegex(spoken, r"[/+·\[\]{}|…]", f"{g.source}: {spoken!r}")


class GrammarLinkTests(unittest.TestCase):
    """grammar_links.json says which grammar card each question tests, so a wrong answer can
    send that card back to review and the answer can show it. The links are data written by a
    person and checked here, never guessed at run time."""

    @classmethod
    def setUpClass(cls):
        cls.bundle = seed.load_all()
        cls.lessons = {r.seed.slug: r for r in cls.bundle.lessons}

    def linked(self, resolved):
        """(id, patterns) of every linked question / exercise of a lesson."""
        for ex in resolved.practice["items"]:
            if ex["type"] in seed.NON_MCQ_TYPES:
                if ex.get("grammar"):
                    yield ex["id"], ex["grammar"]
            else:
                for q in ex["questions"]:
                    if q.get("grammar"):
                        yield q["id"], q["grammar"]

    def test_every_link_names_a_real_card_and_a_wrong_one_is_an_error(self):
        import json
        import shutil
        import tempfile
        from pathlib import Path

        self.assertEqual(self.bundle.problems, [])

        def problems_with(edit):
            with tempfile.TemporaryDirectory() as tmp:
                copy_dir = Path(tmp) / "seed"
                shutil.copytree(seed.SEED_DIR, copy_dir)
                path = copy_dir / "exercises" / "grammar_links.json"
                data = json.loads(path.read_text(encoding="utf-8"))
                edit(data["links"])
                path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
                return "\n".join(seed.load_all(copy_dir).problems)

        def wrong(links):
            links["R1"] = ["V + -không-có-thẻ-này"]  # no such card
            links["NOPE"] = ["V + -느라고"]  # no such question

        text = problems_with(wrong)
        self.assertIn("is not a grammar card", text)
        self.assertIn("'NOPE' is neither a question nor an exercise", text)
        self.assertIn("the same card twice", problems_with(lambda links: links.update(R2=["V + -아/어 놓다"] * 2)))

    def test_each_extension_question_is_linked_to_the_card_of_its_set(self):
        cards = {}
        for r in self.bundle.lessons:
            for g in r.seed.grammar:
                if (g.source or "").startswith("EXT-"):
                    cards[(r.seed.bank, g.source[4:])] = g.pattern
        # two listening replies hinge on a word, not on the pattern of the set (a reviewer found the
        # pattern link would only mislead), so they carry no link on purpose
        unlinked_on_purpose = {"QE07d", "QE08d"}
        checked = 0
        for r in self.bundle.lessons:
            for ex in r.practice["items"]:
                m = re.fullmatch(r"(Q?)E(\d\d)[a-d]", ex["id"])
                if not m:
                    continue
                key = ("quan-he" if m.group(1) else "", f"{'T2' if m.group(1) else 'T1'}-{m.group(2)}")
                targets = [ex] if ex["type"] == "write_fill" else ex["questions"]
                for q in targets:
                    qid = q.get("id", ex["id"])
                    if qid in unlinked_on_purpose:
                        self.assertFalse(q.get("grammar"), qid)
                    else:
                        self.assertEqual(q.get("grammar"), [cards[key]], qid)
                    checked += 1
        self.assertEqual(checked, 76)

    def test_a_question_only_offers_cards_the_learner_has_met(self):
        total = 0
        for r in self.bundle.lessons:
            cards = (r.practice or {}).get("grammar") or {}
            for qid, patterns in self.linked(r):
                total += 1
                self.assertLessEqual(len(patterns), 3, qid)
                for p in patterns:
                    self.assertIn(p, cards, qid)
                    self.assertLessEqual(cards[p]["lesson_order"], r.seed.sort_order, f"{r.seed.slug} {qid} {p}")
            self.assertEqual(set(cards), {p for _, ps in self.linked(r) for p in ps}, r.seed.slug)
        self.assertGreaterEqual(total, 90)

    def test_the_links_are_only_to_what_the_question_tests(self):
        # a handful of hand-checked anchors: the pattern the answer actually uses
        t1 = self.lessons["sinh-hoat-02-viec-nha"]
        ex = {e["id"]: e for e in t1.practice["items"]}
        self.assertEqual(ex["R1"]["questions"][0]["grammar"], ["V + -느라고"])
        self.assertEqual(ex["R4"]["questions"][0]["grammar"], ["V + -느라고", "V + -는 바람에"])
        t2 = self.lessons["quan-he-05-noi-o"]
        ex = {e["id"]: e for e in t2.practice["items"]}
        self.assertEqual(ex["QR1"]["questions"][0]["grammar"], ["V + -(으)려면"])
        self.assertEqual(ex["QR2"]["questions"][0]["grammar"], ["A/V + -(으)ㄴ/는 데다가 · N + 인 데다가"])

    def test_a_link_to_a_later_lesson_is_dropped_for_the_earlier_one(self):
        r = self.lessons["quan-he-01-gia-dinh"]
        ex = {e["id"]: e for e in r.practice["items"]}
        # QW51A tests -고자 하다 (lesson 2) too, but a learner of lesson 1 has not met it
        self.assertEqual(ex["QW51A"]["grammar"], ["V + -(으)시기 바랍니다 · V + -(으)십시오"])


    def test_the_cards_say_what_they_are(self):
        from app.services.grammar_tier import grammar_tier

        ext = [g for r in self.bundle.lessons for g in r.seed.grammar if (g.source or "").startswith("EXT-")]
        core = [g for r in self.bundle.lessons for g in r.seed.grammar if not (g.source or "").startswith("EXT-")]
        for g in ext:
            tier, level = grammar_tier(g.usage_context_vi)
            self.assertEqual(tier, "extension", g.source)
            self.assertIn(level, ("recognize", "produce"), g.source)
        for g in core:
            self.assertEqual(grammar_tier(g.usage_context_vi), ("core", None), g.pattern)

    def test_the_box_has_what_it_shows(self):
        r = self.lessons["sinh-hoat-06-hoc-lam"]
        info = r.practice["grammar"]["V + -(으)면서"]
        self.assertEqual((info["tier"], info["use_level"]), ("extension", "produce"))
        self.assertTrue(info["meaning_vi"] and info["contrast"]["diff_vi"] and info["lesson_title"])

    def test_question_grammar_reads_both_shapes(self):
        r = self.lessons["sinh-hoat-06-hoc-lam"]
        ex = {e["id"]: e for e in r.practice["items"]}
        self.assertEqual(seed.question_grammar(ex["E01a"], "E01a"), ["V + -(으)면서"])
        self.assertEqual(seed.question_grammar(ex["E01c"], "E01c:㉠"), ["V + -(으)면서"])
        self.assertEqual(seed.question_grammar(ex["E01a"], "NOPE"), [])

    def test_two_lessons_do_not_share_the_tagged_copy_of_an_exercise(self):
        before = copy.deepcopy(self.bundle.exercises["E01a"])
        seed.load_all()
        self.assertEqual(self.bundle.exercises["E01a"], before)
        self.assertNotIn("grammar", self.bundle.exercises["E01a"]["questions"][0])


class GrammarTextTests(unittest.TestCase):
    """The card text is cut into parts for the app; nothing may be lost or mangled."""

    @classmethod
    def setUpClass(cls):
        cls.bundle = seed.load_all()
        cls.cards = [g for r in cls.bundle.lessons for g in r.seed.grammar]

    def test_every_extension_card_has_the_four_parts_in_order(self):
        from app.services.grammar_text import usage_sections

        ext = [g for g in self.cards if (g.source or "").startswith("EXT-")]
        self.assertEqual(len(ext), 94)
        for g in ext:
            sections = usage_sections(g.usage_context_vi)
            self.assertEqual([s.key for s in sections if s.key != "level"], ["form", "when", "why", "lesson"], g.source)
            for s in sections:
                self.assertTrue(s.body_vi and s.label, (g.source, s.key))
                self.assertNotIn("🟣", s.body_vi, g.source)  # the badge line is not a part
                self.assertFalse(s.body_vi.startswith("**"), (g.source, s.key))

    def test_no_text_is_lost_when_a_card_is_cut(self):
        from app.services.grammar_text import usage_sections

        def squash(text):
            return re.sub(r"\s+", "", re.sub(r"\*{1,2}[^*]+?:\*{1,2}", "", text))

        for g in self.cards:
            raw = g.usage_context_vi or ""
            body = "".join(s.body_vi for s in usage_sections(raw))
            lines = raw.strip().split("\n")
            if lines and lines[0].lstrip().startswith("🟣"):
                raw = "\n".join(lines[1:])
            self.assertEqual(squash(body), squash(raw), g.pattern)

    def test_a_core_card_comes_back_as_one_unlabelled_part(self):
        from app.services.grammar_text import usage_sections

        core = [g for g in self.cards if not (g.source or "").startswith("EXT-") and g.usage_context_vi]
        self.assertTrue(core)
        for g in core:
            sections = usage_sections(g.usage_context_vi)
            self.assertTrue(sections, g.pattern)
            if not re.search(r"^\*\*[^*]+?:\*\*", g.usage_context_vi, re.M):
                self.assertEqual([(s.key, s.label) for s in sections], [("other", None)], g.pattern)

    def test_the_source_line_leaves_the_mistakes_box(self):
        from app.services.grammar_text import split_source_note

        ext = [g for g in self.cards if (g.source or "").startswith("EXT-")]
        for g in ext:
            note, source = split_source_note(g.note_vi)
            self.assertTrue(source and "biên soạn" in source.lower(), g.source)
            self.assertNotIn("Biên soạn bổ sung", note or "", g.source)
            self.assertTrue((note or "").startswith("**Lỗi người Việt"), g.source)
        # a note that has no source line is returned as it is
        for g in self.cards:
            if g.note_vi and "Biên soạn bổ sung" not in g.note_vi:
                self.assertEqual(split_source_note(g.note_vi), (g.note_vi.strip() or None, None), g.pattern)
        self.assertEqual(split_source_note(None), (None, None))
        self.assertEqual(split_source_note("*Biên soạn bổ sung:* x"), (None, "x"))

    def test_the_api_card_serves_the_parts(self):
        from app.schemas import GrammarPointOut

        g = next(g for g in self.cards if (g.source or "").startswith("EXT-"))
        out = GrammarPointOut(
            id=1, lesson_id=1, pattern=g.pattern, meaning_vi=g.meaning_vi, level=1, example_ko=g.example_ko,
            note_vi=g.note_vi, usage_context_vi=g.usage_context_vi, topik_tip_vi=g.topik_tip_vi,
        ).model_dump(mode="json")
        self.assertEqual([s["key"] for s in out["usage_sections"]], ["form", "when", "why", "lesson"])
        self.assertTrue(out["source_note_vi"])
        self.assertNotIn("Biên soạn bổ sung", out["note_vi"])
        self.assertTrue(out["usage_context_vi"].startswith("🟣"))  # old clients still get the whole text


class UseLevelTests(unittest.TestCase):
    """The level a card must be taken to — "nhận ra" or "dùng được" — is a field of the card."""

    @classmethod
    def setUpClass(cls):
        cls.bundle = seed.load_all()
        cls.cards = [g for r in cls.bundle.lessons for g in r.seed.grammar]

    def card(self, **kw):
        return seed.GrammarSeed(pattern="V + -고", meaning_vi="x", **kw)

    def test_every_served_card_has_a_level(self):
        for r in self.bundle.lessons:
            for info in (r.practice or {}).get("grammar", {}).values():
                self.assertIn(info["use_level"], ("recognize", "produce"))

    def test_a_card_without_a_level_is_for_use_and_an_extension_follows_its_marker(self):
        from app.services.grammar_tier import effective_use_level

        self.assertEqual(effective_use_level(None), "produce")
        self.assertEqual(effective_use_level("🟣 **Kiến thức mở rộng** · 👁 **Nhận ra** x"), "recognize")
        self.assertEqual(effective_use_level("🟣 **Kiến thức mở rộng** · 👁 **Nhận ra** x", "produce"), "produce")  # the card's own word wins

    def test_a_level_that_contradicts_the_marker_line_is_refused(self):
        with self.assertRaises(ValidationError):
            self.card(usage_context_vi="🟣 **Kiến thức mở rộng** · ✍ **Dùng được** x", use_level="recognize")
        self.assertEqual(self.card(usage_context_vi="🟣 **Kiến thức mở rộng** · ✍ **Dùng được** x", use_level="produce").use_level, "produce")

    def test_a_level_outside_the_two_is_refused(self):
        with self.assertRaises(ValidationError):
            self.card(use_level="fluent")

    def test_the_levels_written_into_the_seed_are_served_with_the_card(self):
        served = {
            (info["lesson_slug"], pattern): info
            for r in self.bundle.lessons
            for pattern, info in (r.practice or {}).get("grammar", {}).items()
        }
        explicit = [(r.seed.slug, g) for r in self.bundle.lessons for g in r.seed.grammar if g.use_level]
        self.assertGreaterEqual(len(explicit), 25)
        checked = 0
        for slug, g in explicit:
            if (slug, g.pattern) in served:  # a card is served once an exercise of its bank links to it
                self.assertEqual(served[(slug, g.pattern)]["use_level"], g.use_level, (slug, g.pattern))
                checked += 1
        self.assertGreater(checked, 0)

    def test_the_api_card_serves_the_stored_level(self):
        from app.schemas import GrammarPointOut

        base = dict(id=1, lesson_id=1, pattern="V + -고", meaning_vi="x", level=1, example_ko="x")
        self.assertEqual(GrammarPointOut(**base).model_dump(mode="json")["use_level"], "produce")
        self.assertEqual(GrammarPointOut(**base, use_level="recognize").model_dump(mode="json")["use_level"], "recognize")
        self.assertNotIn("use_level_set", GrammarPointOut(**base, use_level="recognize").model_dump(mode="json"))


class HangulLessonTests(unittest.TestCase):
    """Bảng chữ cái: Bài 1, five parts whose reading words use only what was taught so far."""

    @classmethod
    def setUpClass(cls):
        cls.bundle = seed.load_all()
        cls.lesson = next(r for r in cls.bundle.lessons if r.seed.kind == "hangul")

    def test_it_comes_first_free_and_with_its_end_check(self):
        self.assertEqual((self.lesson.seed.sort_order, self.lesson.seed.track), (1, "beginner"))
        self.assertIs(self.bundle.lessons[0], self.lesson)
        self.assertEqual(self.lesson.practice["kind"], "hangul")
        self.assertEqual(self.lesson.practice["counts"]["questions"], 20)
        self.assertEqual([p["id"] for p in self.lesson.practice["hangul"]["parts"]], ["p1", "p2", "p3", "p4", "p5"])

    def test_every_letter_is_taught_once(self):
        taught = [l.jamo for p in self.lesson.seed.hangul.parts for g in p.groups for l in g.letters if p.id != "p4"]
        self.assertEqual(sorted(set(taught) - {"ㅇ"}), sorted(set(seed.JAMO_INITIAL + seed.JAMO_MEDIAL) - {"ㅇ"}))
        self.assertEqual(len(taught), len(set(taught)))

    def test_a_word_with_a_letter_not_taught_yet_is_refused(self):
        raw = self.lesson.seed.hangul.model_dump(mode="json")
        raw["parts"][0]["words"].append({"ko": "가수", "vi": "ca sĩ"})  # ㄱ, ㅅ come in part 2
        with self.assertRaises(ValidationError):
            seed.HangulSeed.model_validate(raw)
        raw = self.lesson.seed.hangul.model_dump(mode="json")
        raw["parts"][1]["words"].append({"ko": "학생", "vi": "học sinh"})  # a final before part 4
        with self.assertRaises(ValidationError):
            seed.HangulSeed.model_validate(raw)

    def test_the_words_come_from_nen_tang_1(self):
        nt1 = next(r for r in self.bundle.lessons if r.seed.slug == "sinh-hoat-00-nen-tang-1-gioi-thieu")
        # the NIKL 초급 words added in Phase 2 (source krdict:…) extend the lesson's word list; the
        # Hangul lesson reads the lesson's own core words, which is what this checks
        vocab = {h.strip() for v in nt1.seed.vocab if not (v.source or "").startswith("krdict:") for h in v.hangul.split("/")}
        read = {w.ko for p in self.lesson.seed.hangul.parts for w in p.words}
        read |= {c.written for p in self.lesson.seed.hangul.parts for r in p.rules for c in r.changes}
        self.assertEqual(vocab - read, set())  # every word of Nền tảng 1 is read before it


class PronunciationTests(unittest.TestCase):
    """vocab `pron`: the standard reading when it differs from the spelling (Nền tảng 1–5)."""

    def test_the_foundation_words_that_change_say_how_they_are_read(self):
        from app.services.lesson_seed import load_all

        by_word = {
            v.hangul: v.pron for r in load_all().lessons if r.seed.slug.startswith("sinh-hoat-00") for v in r.seed.vocab
        }
        for word, pron in {
            "학생": "[학쌩]", "한국어": "[한구거]", "같이": "[가치]", "좋다": "[조타]",
            "맛없다": "[마덥따]", "짧다": "[짤따]", "월요일": "[워료일]",
        }.items():
            self.assertEqual(by_word[word], pron, word)
        self.assertIsNone(by_word["사람"])  # read as written: nothing to show

    def test_a_pron_must_be_hangul_in_brackets(self):
        from pydantic import ValidationError

        from app.services.lesson_seed import VocabSeed

        base = {"hangul": "학생", "pos": "N", "meaning_vi": "Học sinh", "priority": "core"}
        self.assertEqual(VocabSeed.model_validate({**base, "pron": "[학쌩]"}).pron, "[학쌩]")
        for bad in ("학쌩", "[hak-ssaeng]", "[학쌩"):
            with self.assertRaises(ValidationError):
                VocabSeed.model_validate({**base, "pron": bad})


class UsageSectionsLevelLineTests(unittest.TestCase):
    def test_one_star_level_line_is_its_own_section(self):
        from app.services.grammar_text import usage_sections

        text = "**Cấu tạo:** A + 도\n**Hoàn cảnh dùng:** nói điều kiện\n*Mức độ:* KIIP không đưa vào"
        keys = [s.key for s in usage_sections(text)]
        self.assertEqual(keys, ["form", "when", "level"])

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
        self.assertEqual(len(self.bundle.lessons), 46)
        by_topic: dict[str, int] = {}
        for r in self.bundle.lessons:
            by_topic[r.seed.topic] = by_topic.get(r.seed.topic, 0) + 1
        self.assertEqual(
            by_topic,
            {
                "Destination B1 · Lấy gốc": 42,
                "G1 · Các thì hiện tại (Tuần 1)": 4,
            },
        )

    def test_lessons_come_out_in_curriculum_order(self):
        order = [(r.seed.track, r.seed.sort_order) for r in self.bundle.lessons]
        self.assertEqual(order, sorted(order, key=lambda t: (seed.TRACKS.index(t[0]), t[1])))
        self.assertEqual(len({r.seed.slug for r in self.bundle.lessons}), 46)

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
            "sort_order": 99, "summary": "x", "vocab": [{"headword": "가", "pos": "N", "meaning_vi": "a", "priority": "core"}],
        }
        base.update(over)
        return base

    def test_a_good_lesson_is_accepted(self):
        seed.LessonSeed.model_validate(self.lesson())

    def test_duplicates_and_unknown_fields_are_rejected(self):
        with self.assertRaises(ValidationError):
            seed.LessonSeed.model_validate(self.lesson(vocab=[{"headword": "가", "pos": "N", "meaning_vi": "a", "priority": "core"}] * 2))
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
        self.assertEqual(set(self.shared), {"", "b1", "g1"})
        self.assertEqual(set(self.bank_of.values()), {"b1", "g1"})
        self.assertEqual(set(self.exercises), set(self.bundle.exercises))

    def test_a_lesson_only_uses_exercises_of_its_own_bank(self):
        for r in self.bundle.lessons:
            g1 = r.seed.slug.startswith("g1-")
            self.assertEqual(r.seed.bank, "g1" if g1 else "b1", r.seed.slug)
            self.assertTrue(all(i.startswith("G1D" if g1 else "B1U") for i in r.seed.exercise_ids), r.seed.slug)
            for ex_id in r.seed.exercise_ids:
                self.assertEqual(self.bank_of[ex_id], r.seed.bank, f"{r.seed.slug}: {ex_id}")
            by_skill = r.practice["counts"]["by_skill"]
            # week 1 of G1 is phase one of the method: no scored speaking yet
            for skill in ("listening", "reading", "build", "writing") + (() if g1 else ("speaking",)):
                self.assertTrue(by_skill.get(skill), f"{r.seed.slug}: no {skill}")

    def test_the_practice_set_carries_the_guides_of_its_bank(self):
        first = self.bundle.lessons[0]
        self.assertIsNotNone(first.practice["overview"])
        self.assertNotIn("extension", first.practice)
        for skill, guide in first.practice["guides"].items():
            self.assertEqual(guide, self.shared["b1"]["guides"][skill])

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
                        "summary": "s", "vocab": [{"headword": "가", "pos": "N", "meaning_vi": "m", "priority": "core"}],
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
            "points": 10, "limits": {"min": 10, "max": 300}, "model_answer_en": "저희 가족은 모두 네 명입니다.",
            "uses": [{"form": "저희 가족", "card": "저희"}],
        }
        raw.update(over)
        return raw

    def lesson(self, sort_order, vocab=(), grammar=()):
        return seed.LessonSeed.model_validate({
            "slug": f"thu-{sort_order:02d}", "title": "Thử", "topic": "Thử", "track": "intermediate", "level": 3,
            "sort_order": sort_order, "summary": "x",
            "vocab": [{"headword": h, "pos": "X", "meaning_vi": "a", "priority": "core"} for h in vocab],
            "grammar": [{"pattern": p, "meaning_vi": "a", "importance": "must"} for p in grammar],
        })

    def test_a_rung_5_text_needs_its_model_and_its_uses(self):
        seed.WriteEssay.model_validate(self.essay())
        with self.assertRaises(ValidationError):
            seed.WriteEssay.model_validate(self.essay(uses=[]))
        with self.assertRaises(ValidationError):
            seed.WriteEssay.model_validate(self.essay(model_answer_en=""))
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
        self.assertEqual(len(report), 46)
        db.add.assert_not_called()
        parts = sum(1 for r in bundle.lessons if r.seed.split_from)
        self.assertEqual(db.execute.call_count, 46 + parts)


if __name__ == "__main__":
    unittest.main()


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
                path = copy_dir / "exercises" / "b1" / "grammar_links.json"
                data = json.loads(path.read_text(encoding="utf-8"))
                edit(data["links"])
                path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
                return "\n".join(seed.load_all(copy_dir).problems)

        def wrong(links):
            links["B1U01Q1"] = ["V + -không-có-thẻ-này"]  # no such card
            links["NOPE"] = ["Present simple: S + V(s/es)"]  # no such question

        text = problems_with(wrong)
        self.assertIn("is not a grammar card", text)
        self.assertIn("'NOPE' is neither a question nor an exercise", text)
        self.assertIn(
            "the same card twice",
            problems_with(lambda links: links.update(B1U01Q2=["Present simple: S + V(s/es)"] * 2)),
        )

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

    def test_the_cards_say_what_they_are(self):
        from app.services.grammar_tier import grammar_tier

        core = [g for r in self.bundle.lessons for g in r.seed.grammar if not (g.source or "").startswith("EXT-")]
        self.assertTrue(core)
        for g in core:
            self.assertEqual(grammar_tier(g.usage_context_vi), ("core", None), g.pattern)

    def test_the_box_has_what_it_shows(self):
        r = self.lessons["b1-u01-present-simple-present-continuous-stative-verbs"]
        info = r.practice["grammar"]["Present simple: S + V(s/es)"]
        self.assertEqual((info["tier"], info["use_level"]), ("core", "produce"))
        self.assertTrue(info["meaning_vi"] and info["lesson_title"])

    def test_question_grammar_reads_both_shapes(self):
        r = self.lessons["b1-u01-present-simple-present-continuous-stative-verbs"]
        ex = {e["id"]: e for e in r.practice["items"]}
        self.assertEqual(seed.question_grammar(ex["B1U01Q1"], "B1U01Q1"), ["Present simple: S + V(s/es)"])
        fill = {"id": "B1U01F1", "type": "write_fill", "grammar": ["Present simple: S + V(s/es)"]}
        self.assertEqual(seed.question_grammar(fill, "B1U01F1:a"), ["Present simple: S + V(s/es)"])
        self.assertEqual(seed.question_grammar(ex["B1U01Q1"], "NOPE"), [])

    def test_two_lessons_do_not_share_the_tagged_copy_of_an_exercise(self):
        before = copy.deepcopy(self.bundle.exercises["B1U01Q1"])
        seed.load_all()
        self.assertEqual(self.bundle.exercises["B1U01Q1"], before)
        self.assertNotIn("grammar", self.bundle.exercises["B1U01Q1"]["questions"][0])


class GrammarTextTests(unittest.TestCase):
    """The card text is cut into parts for the app; nothing may be lost or mangled."""

    @classmethod
    def setUpClass(cls):
        cls.bundle = seed.load_all()
        cls.cards = [g for r in cls.bundle.lessons for g in r.seed.grammar]

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

        for g in self.cards:
            if g.note_vi and "Biên soạn bổ sung" not in g.note_vi:
                self.assertEqual(split_source_note(g.note_vi), (g.note_vi.strip() or None, None), g.pattern)
        self.assertEqual(split_source_note(None), (None, None))
        self.assertEqual(split_source_note("*Biên soạn bổ sung:* x"), (None, "x"))

    def test_the_api_card_serves_the_parts(self):
        from app.schemas import GrammarPointOut

        out = GrammarPointOut(
            id=1,
            lesson_id=1,
            pattern="Present simple: S + V(s/es)",
            meaning_vi="Hiện tại đơn",
            level=1,
            example_en="I usually get up at six.",
            note_vi="**Lỗi người Việt hay gặp:** quên chia -s.\n*Biên soạn bổ sung:* Destination B1",
            usage_context_vi=(
                "🟣 **Kiến thức mở rộng** · ✍ **Dùng được**\n"
                "**Cấu tạo:** S + V(s/es)\n"
                "**Hoàn cảnh dùng:** thói quen, sự thật\n"
                "**Vì sao dễ nhầm:** quên chia động từ\n"
                "**Trong bài này:** Unit 1"
            ),
            exam_tip_vi="Dùng ở Speaking Part 1.",
        ).model_dump(mode="json")
        self.assertEqual([s["key"] for s in out["usage_sections"]], ["form", "when", "why", "lesson"])
        self.assertTrue(out["source_note_vi"])
        self.assertNotIn("Biên soạn bổ sung", out["note_vi"])
        self.assertTrue(out["usage_context_vi"].startswith("🟣"))


class UseLevelTests(unittest.TestCase):
    """The level a card must be taken to — "nhận ra" or "dùng được" — is a field of the card."""

    @classmethod
    def setUpClass(cls):
        cls.bundle = seed.load_all()
        cls.cards = [g for r in cls.bundle.lessons for g in r.seed.grammar]

    def card(self, **kw):
        return seed.GrammarSeed(pattern="Present simple: S + V(s/es)", meaning_vi="x", **kw)

    def test_every_served_card_has_a_level(self):
        for r in self.bundle.lessons:
            for info in (r.practice or {}).get("grammar", {}).values():
                self.assertIn(info["use_level"], ("recognize", "produce"))

    def test_a_card_without_a_level_is_for_use_and_an_extension_follows_its_marker(self):
        from app.services.grammar_tier import effective_use_level

        self.assertEqual(effective_use_level(None), "produce")
        self.assertEqual(effective_use_level("🟣 **Kiến thức mở rộng** · 👁 **Nhận ra** x"), "recognize")
        self.assertEqual(effective_use_level("🟣 **Kiến thức mở rộng** · 👁 **Nhận ra** x", "produce"), "produce")

    def test_a_level_that_contradicts_the_marker_line_is_refused(self):
        with self.assertRaises(ValidationError):
            self.card(usage_context_vi="🟣 **Kiến thức mở rộng** · ✍ **Dùng được** x", use_level="recognize")
        self.assertEqual(self.card(usage_context_vi="🟣 **Kiến thức mở rộng** · ✍ **Dùng được** x", use_level="produce").use_level, "produce")

    def test_a_level_outside_the_two_is_refused(self):
        with self.assertRaises(ValidationError):
            self.card(use_level="fluent")

    def test_the_api_card_serves_the_stored_level(self):
        from app.schemas import GrammarPointOut

        base = dict(id=1, lesson_id=1, pattern="Present simple: S + V(s/es)", meaning_vi="x", level=1, example_en="x")
        self.assertEqual(GrammarPointOut(**base).model_dump(mode="json")["use_level"], "produce")
        self.assertEqual(GrammarPointOut(**base, use_level="recognize").model_dump(mode="json")["use_level"], "recognize")
        self.assertNotIn("use_level_set", GrammarPointOut(**base, use_level="recognize").model_dump(mode="json"))


class UsageSectionsLevelLineTests(unittest.TestCase):
    def test_one_star_level_line_is_its_own_section(self):
        from app.services.grammar_text import usage_sections

        text = "**Cấu tạo:** A + 도\n**Hoàn cảnh dùng:** nói điều kiện\n*Mức độ:* KIIP không đưa vào"
        keys = [s.key for s in usage_sections(text)]
        self.assertEqual(keys, ["form", "when", "level"])

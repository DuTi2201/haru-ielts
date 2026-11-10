"""The entry diagnostic: the seed file, the rules that turn answers into a summary, and its endpoints."""
import json
import unittest
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest import mock

from fastapi import HTTPException

from app.api.routers import competency as router
from app.models import ItemState, PlacementAttempt
from app.schemas import PlacementAnswerIn, PlacementSubmit
from app.services import lesson_seed as seed
from app.services import placement
from app.services.placement import Answer

LEARNER = uuid.uuid4()
LOADED, PROBLEMS = placement.load()
BUNDLE = seed.load_all()
CARDS = {(r.seed.slug, g.pattern) for r in BUNDLE.lessons for g in r.seed.grammar}


class DiagnosticFileTests(unittest.TestCase):
    def test_the_file_loads_without_problems(self):
        self.assertEqual(PROBLEMS, [])
        self.assertIsNotNone(LOADED)
        self.assertEqual(len(LOADED.items), 16)

    def test_every_item_points_at_a_card_that_exists_and_each_card_is_asked_once(self):
        self.assertEqual(placement.check(LOADED, CARDS), [])
        keys = [(i.lesson, i.pattern) for i in LOADED.items]
        self.assertEqual(len(keys), len(set(keys)))

    def test_all_three_rungs_are_asked_and_ids_are_unique(self):
        self.assertEqual({i.rung for i in LOADED.items}, {0, 1, 2})
        ids = [i.id for i in LOADED.items]
        self.assertEqual(len(ids), len(set(ids)))
        for i in LOADED.items:
            self.assertEqual(len(seed.question_ids(i.exercise)), 1, i.id)

    def test_it_covers_the_twelve_foundation_cards_of_the_first_three_lessons(self):
        # the entry check stays short: it asks the foundation cards of lessons 1–3 once each; the
        # foundation cards the later lessons added are met in their own lessons
        foundation = {
            g.pattern
            for r in BUNDLE.lessons
            for g in r.seed.grammar
            if "ngữ pháp nền" in (g.source or "") and r.seed.slug.startswith(("sinh-hoat-01", "sinh-hoat-02", "sinh-hoat-03"))
        }
        asked = {i.pattern for i in LOADED.items}
        self.assertEqual(len(foundation), 12)
        self.assertEqual(foundation - asked, set())

    def test_the_wording_never_names_the_pattern_it_tests(self):
        # the instruction of a fill-in or a sentence to build describes the job, not the ending
        for i in LOADED.items:
            if i.rung == 0:
                continue
            ending = i.pattern.split("+")[-1].split("·")[0].strip().lstrip("-")
            text = json.dumps({k: v for k, v in i.exercise.items() if k in ("instruction_vi", "title_vi", "meaning_vi")}, ensure_ascii=False)
            self.assertNotIn(f"`-{ending}`", text, i.id)

    def test_the_answer_key_is_one_option_and_distractors_are_not_accepted(self):
        for i in LOADED.items:
            if i.rung == 0:
                (q,) = i.exercise["questions"]
                self.assertIn(q["answer"], [o["id"] for o in q["options"]])
            elif i.rung == 1:
                self.assertTrue(set(i.exercise["tiles"]) >= set(i.exercise["answers"][0].split(" ")))
            else:
                self.assertTrue(all(b["accepted"] for b in i.exercise["blanks"]))

    def test_the_served_items_do_not_name_their_card(self):
        # GET /placement serves `exercise` only; the card lives beside it in the file
        for i in LOADED.items:
            self.assertNotIn("card", i.exercise)


def lookup():
    gid_of, lesson_id_of, pos = {}, {}, {}
    for n, i in enumerate(LOADED.items, 1):
        gid_of[(i.lesson, i.pattern)] = 100 + n
        lesson_id_of.setdefault(i.lesson, len(lesson_id_of) + 1)
    for p, slug in enumerate(sorted(lesson_id_of)):  # alphabetical = curriculum order here
        pos[slug] = p
    return gid_of, lesson_id_of, pos


def answers_for(right_ids, skip=()):
    out = []
    for i in LOADED.items:
        if i.id in skip:
            continue
        out.append(Answer(i.id, i.question_id, i.id in right_ids))
    return {a.exercise_id: a for a in out}


class SummaryTests(unittest.TestCase):
    def summary(self, right, skip=()):
        gid_of, lesson_id_of, pos = lookup()
        return placement.summarize(LOADED, answers_for(set(right), skip), gid_of=gid_of, lesson_id_of=lesson_id_of, lesson_pos=pos)

    def ids(self, rung):
        return [i.id for i in LOADED.items if i.rung == rung]

    def test_everything_right_starts_at_the_top_rung_with_no_lesson_to_go_back_to(self):
        s = self.summary(self.ids(0) + self.ids(1) + self.ids(2))
        self.assertEqual((s["score"], s["total"], s["start_rung"], s["start_label"]), (16, 16, 2, "Điền / nối câu"))
        self.assertIsNone(s["start_lesson_id"])
        self.assertEqual(s["unknown"], [])
        self.assertEqual(s["by_rung"]["1"], {"right": 5, "total": 5})

    def test_two_thirds_right_is_enough_for_a_rung(self):
        s = self.summary(self.ids(0)[:4])  # 4 of 6
        self.assertEqual(s["start_rung"], 0)
        s = self.summary(self.ids(1)[:3])  # 3 of 5 = 60%
        self.assertEqual(s["start_rung"], -1)
        s = self.summary(self.ids(1)[:4])
        self.assertEqual(s["start_rung"], 1)

    def test_nothing_right_starts_from_recognising(self):
        s = self.summary([])
        self.assertEqual((s["score"], s["start_rung"], s["start_label"]), (0, -1, placement.NO_RUNG_LABEL))
        self.assertEqual(len(s["unknown"]), 16)
        self.assertEqual(s["known_ids"], [])

    def test_a_skipped_item_counts_as_not_known(self):
        s = self.summary(self.ids(0), skip=[self.ids(0)[0]])
        self.assertEqual(s["score"], 5)
        self.assertEqual(s["by_rung"]["0"], {"right": 5, "total": 6})

    def test_only_building_and_filling_make_a_card_solid(self):
        s = self.summary(self.ids(0) + self.ids(1)[:2])
        self.assertEqual(len(s["known_ids"]), 8)
        self.assertEqual(len(s["solid_ids"]), 2)
        self.assertTrue(set(s["solid_ids"]) <= set(s["known_ids"]))

    def test_the_lesson_to_start_from_is_the_earliest_one_with_a_card_not_known(self):
        gid_of, lesson_id_of, pos = lookup()
        by_lesson = {}
        for i in LOADED.items:
            by_lesson.setdefault(i.lesson, []).append(i.id)
        earliest, later = sorted(by_lesson, key=lambda s: pos[s])[:2]
        right = [i.id for i in LOADED.items if i.id not in by_lesson[earliest] + by_lesson[later]]
        s = placement.summarize(LOADED, answers_for(set(right)), gid_of=gid_of, lesson_id_of=lesson_id_of, lesson_pos=pos)
        self.assertEqual(s["start_lesson_id"], lesson_id_of[earliest])

    def test_the_evidence_is_the_right_answers_at_their_rung(self):
        gid_of, _l, _p = lookup()
        got = placement.evidence(LOADED, answers_for({"D01", "D07", "D12"}), gid_of)
        self.assertEqual(sorted(r for _g, r in got), [0, 1, 2])
        self.assertEqual(placement.evidence(LOADED, answers_for(set()), gid_of), [])

    def test_resolve_rejects_unknown_items_and_mismatched_questions_and_keeps_the_last_answer(self):
        given, problems = placement.resolve(
            LOADED, [Answer("D01", "D01", False), Answer("D01", "D01", True), Answer("D99", "D99", True), Answer("D12", "D12", True)]
        )
        self.assertTrue(given["D01"].correct)
        self.assertEqual(len(problems), 2)
        self.assertNotIn("D12", given)  # a blank is answered under its own question id


def rows(value):
    res = mock.MagicMock()
    res.all.return_value = value
    res.scalars.return_value.all.return_value = value
    return res


class SubmitEndpointTests(unittest.IsolatedAsyncioTestCase):
    def db(self, have=()):
        gid_of, lesson_id_of, _pos = lookup()
        grammar_rows = [(gid, pattern, slug) for (slug, pattern), gid in gid_of.items()]
        lessons = sorted(lesson_id_of.items(), key=lambda kv: kv[0])
        db = mock.MagicMock()
        db.execute = mock.AsyncMock(side_effect=[rows(grammar_rows), rows(lessons), rows(list(have))])
        db.add = mock.MagicMock()
        db.commit = mock.AsyncMock()
        return db

    def body(self, right, skip=()):
        return PlacementSubmit(
            answers=[
                PlacementAnswerIn(exercise_id=a.exercise_id, question_id=a.question_id, correct=a.correct, answer="x")
                for a in answers_for(set(right), skip).values()
            ]
        )

    async def call(self, db, body):
        record = mock.AsyncMock()
        with mock.patch.object(router.competency_db, "record_outcomes", record):
            out = await router.submit_placement(body, db, SimpleNamespace(id=LEARNER))
        return out, record

    async def test_right_answers_become_evidence_on_their_rung_and_known_cards_get_a_first_review(self):
        db = self.db()
        out, record = await self.call(db, self.body({"D01", "D02", "D07", "D12"}))
        self.assertEqual((out.score, out.total, out.start_rung), (4, 16, -1))  # 2 of 6, 1 of 5, 1 of 5: no rung reached
        rungs = {c.args[3]: sorted(c.args[2]) for c in record.await_args_list}
        self.assertEqual(sorted(rungs), [0, 1, 2])
        self.assertEqual([len(g) for _r, g in sorted(rungs.items())], [2, 1, 1])
        self.assertTrue(all(c.args[4] is True for c in record.await_args_list))  # only right answers are written
        added = [c.args[0] for c in db.add.call_args_list]
        states = [a for a in added if isinstance(a, ItemState)]
        attempts = [a for a in added if isinstance(a, PlacementAttempt)]
        self.assertEqual(len(states), 4)
        self.assertTrue(all(s.item_type == "grammar_point" and s.reps == 1 and s.due_at is not None for s in states))
        (attempt,) = attempts
        self.assertEqual(attempt.summary["score"], 4)
        self.assertEqual(len(attempt.answers), 16)
        db.commit.assert_awaited_once()

    async def test_a_card_that_already_has_a_schedule_keeps_it(self):
        gid_of, _l, _p = lookup()
        first = next(i for i in LOADED.items if i.id == "D01")
        db = self.db(have=[gid_of[(first.lesson, first.pattern)]])
        await self.call(db, self.body({"D01"}))
        states = [c.args[0] for c in db.add.call_args_list if isinstance(c.args[0], ItemState)]
        self.assertEqual(states, [])

    async def test_nothing_known_writes_no_evidence_and_no_schedule(self):
        db = self.db()
        out, record = await self.call(db, self.body(set()))
        record.assert_not_awaited()
        self.assertEqual([c.args[0] for c in db.add.call_args_list if isinstance(c.args[0], ItemState)], [])
        self.assertEqual(out.known_ids, [])
        self.assertEqual(out.start_label, placement.NO_RUNG_LABEL)

    async def test_an_unknown_item_is_a_422_and_nothing_is_stored(self):
        db = self.db()
        body = PlacementSubmit(answers=[PlacementAnswerIn(exercise_id="Z9", question_id="Z9", correct=True)])
        with self.assertRaises(HTTPException) as ctx:
            await self.call(db, body)
        self.assertEqual(ctx.exception.status_code, 422)
        db.add.assert_not_called()
        db.commit.assert_not_awaited()

    async def test_no_answers_is_a_422(self):
        with self.assertRaises(HTTPException) as ctx:
            await self.call(self.db(), PlacementSubmit(answers=[]))
        self.assertEqual(ctx.exception.status_code, 422)


class ReadEndpointTests(unittest.IsolatedAsyncioTestCase):
    async def test_the_diagnostic_is_served_without_its_cards(self):
        db = mock.MagicMock()
        res = mock.MagicMock()
        res.scalar_one_or_none.return_value = None
        db.execute = mock.AsyncMock(return_value=res)
        out = await router.get_placement(db, SimpleNamespace(id=LEARNER))
        self.assertEqual((len(out.items), out.minutes, out.last), (16, 12, None))
        text = json.dumps(out.model_dump(mode="json"), ensure_ascii=False)
        for i in LOADED.items:
            self.assertNotIn(i.pattern, text)
        self.assertEqual([i.rung for i in out.items], sorted(i.rung for i in out.items))  # easiest first

    async def test_the_latest_result_is_read_back_with_its_time(self):
        taken = datetime(2026, 10, 9, 8, 0, tzinfo=timezone.utc)
        row = SimpleNamespace(
            taken_at=taken,
            summary={"score": 9, "total": 16, "known": ["a"], "unknown": ["b"], "start_rung": 1, "start_label": "Xếp câu", "by_rung": {}},
        )
        res = mock.MagicMock()
        res.scalar_one_or_none.return_value = row
        db = mock.MagicMock()
        db.execute = mock.AsyncMock(return_value=res)
        out = await router.get_my_placement(db, SimpleNamespace(id=LEARNER))
        self.assertEqual((out.score, out.taken_at, out.known_ids), (9, taken, []))


if __name__ == "__main__":
    unittest.main()

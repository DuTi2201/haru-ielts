"""The competency ladder and the mixed review (app.services.competency): pure rules."""
import unittest
from datetime import datetime, timedelta, timezone

from app.services import competency as comp
from app.services.competency import CardState, Candidate

NOW = datetime(2026, 10, 9, tzinfo=timezone.utc)


def card(cid, history=None, **kw):
    return CardState(id=cid, pattern=f"P{cid}", lesson_id=kw.pop("lesson_id", 1), history=history or {}, **kw)


class LadderTests(unittest.TestCase):
    def test_the_rung_an_exercise_counts_for(self):
        self.assertEqual(comp.rung_of({"type": "read_cloze", "questions": []}), 0)
        self.assertEqual(comp.rung_of({"type": "listen_reply", "questions": [{}]}), 0)
        self.assertEqual(comp.rung_of({"type": "build_order"}), 1)
        self.assertEqual(comp.rung_of({"type": "write_fill"}), 2)
        self.assertEqual(comp.rung_of({"type": "write_essay"}), 3)
        self.assertEqual(comp.rung_of({"type": "speak"}), 3)
        self.assertIsNone(comp.rung_of({"type": "something_else"}))

    def test_only_the_last_three_outcomes_of_a_rung_are_kept(self):
        h = None
        for ok in (True, False, False, True, True):
            h = comp.record(h, 1, ok)
        self.assertEqual(h, {"1": [0, 1, 1]})

    def test_record_does_not_touch_the_old_history(self):
        old = {"0": [1]}
        new = comp.record(old, 2, True)
        self.assertEqual(old, {"0": [1]})
        self.assertEqual(new, {"0": [1], "2": [1]})
        with self.assertRaises(ValueError):
            comp.record(old, 9, True)

    def test_two_thirds_right_reaches_a_rung(self):
        self.assertTrue(comp.reached_rung([1]))  # a first right answer is a start
        self.assertFalse(comp.reached_rung([0]))
        self.assertFalse(comp.reached_rung([1, 0]))
        self.assertTrue(comp.reached_rung([1, 1]))
        self.assertTrue(comp.reached_rung([1, 0, 1]))
        self.assertFalse(comp.reached_rung([1, 0, 0]))
        self.assertFalse(comp.reached_rung([]))

    def test_two_thirds_wrong_is_failing_but_one_slip_is_not(self):
        self.assertFalse(comp.failing_rung([0]))
        self.assertTrue(comp.failing_rung([0, 0]))
        self.assertFalse(comp.failing_rung([1, 0]))
        self.assertTrue(comp.failing_rung([0, 1, 0]))
        self.assertFalse(comp.failing_rung([1, 1, 0]))

    def test_level_is_the_highest_rung_reached(self):
        self.assertEqual(comp.level({}), -1)
        self.assertEqual(comp.level({"0": [0, 0]}), -1)
        self.assertEqual(comp.level({"0": [1, 1], "1": [1, 0]}), 0)
        self.assertEqual(comp.level({"0": [1], "1": [1], "2": [0, 0]}), 1)
        self.assertEqual(comp.level({"2": [1]}), 2)  # a placement can start above rung 0

    def test_the_goal_depends_on_how_far_the_exam_goes(self):
        self.assertEqual(comp.goal_rung("produce"), 3)
        self.assertEqual(comp.goal_rung(None), 3)
        self.assertEqual(comp.goal_rung("recognize"), 0)
        self.assertTrue(comp.goal_reached({"0": [1]}, "recognize"))
        self.assertFalse(comp.goal_reached({"0": [1], "2": [1]}, "produce"))
        self.assertTrue(comp.goal_reached({"3": [1, 1]}, "produce"))

    def test_serving_moves_up_when_solid_and_down_when_failing(self):
        self.assertEqual(comp.serve_rung({}, "produce"), 0)  # nothing yet: start by recognising
        self.assertEqual(comp.serve_rung({"0": [1, 1]}, "produce"), 1)
        self.assertEqual(comp.serve_rung({"0": [1, 1], "1": [0, 0]}, "produce"), 0)  # rung 1 keeps going wrong: consolidate
        self.assertEqual(comp.serve_rung({"0": [1, 1], "1": [1, 0]}, "produce"), 1)  # one slip: not failing, but not reached
        self.assertEqual(comp.serve_rung({"0": [1], "1": [1], "2": [1]}, "produce"), 3)
        self.assertEqual(comp.serve_rung({"0": [0, 0]}, "produce"), 0)  # cannot go below the first rung
        self.assertEqual(comp.serve_rung({"0": [1]}, "recognize"), 0)  # goal reached: stay on it
        self.assertEqual(comp.serve_rung({"3": [1, 1]}, "produce"), 3)


class MixTests(unittest.TestCase):
    def cands(self):
        return [
            Candidate(1, "BO1", 1, (10,), ("BO1",), lesson_pos=0),
            Candidate(1, "BF1", 2, (10,), ("BF1:a",), lesson_pos=0),
            Candidate(1, "R1", 0, (10,), ("R1.1",), lesson_pos=0),
            Candidate(2, "BO2", 1, (20,), ("BO2",), lesson_pos=1),
            Candidate(2, "BF2", 2, (20,), ("BF2:a",), lesson_pos=1),
            Candidate(3, "BO3", 1, (30,), ("BO3",), lesson_pos=2),  # the lesson the learner is in
        ]

    def test_a_due_card_gets_the_exercise_at_its_serve_rung(self):
        cards = {10: card(10, {"0": [1, 1]}, in_srs=True, due=True), 20: card(20, in_srs=True), 30: card(30)}
        picks = comp.select_mix(self.cands(), cards, {}, current_lesson_id=3)
        self.assertEqual([(p.candidate.exercise_id, p.reason) for p in picks][:1], [("BO1", "due")])  # rung 0 passed -> rung 1

    def test_with_no_exercise_at_the_rung_the_nearest_one_is_used(self):
        cards = {20: card(20, {"1": [1, 1]}, in_srs=True, due=True)}  # serve rung 2; BF2 is rung 2
        self.assertEqual(comp.select_mix(self.cands(), cards, {}, 3)[0].candidate.exercise_id, "BF2")
        only_rung_1 = [c for c in self.cands() if c.exercise_id == "BO2"]
        self.assertEqual(comp.select_mix(only_rung_1, cards, {}, 3)[0].candidate.exercise_id, "BO2")

    def test_leeches_and_the_most_overdue_cards_come_first(self):
        cards = {
            10: card(10, in_srs=True, due=True, overdue_since=NOW - timedelta(days=1)),
            20: card(20, in_srs=True, due=True, overdue_since=NOW - timedelta(days=5)),
            30: card(30, in_srs=True, due=True, leech=True, overdue_since=NOW),
        }
        order = [p.card_id for p in comp.select_mix(self.cands(), cards, {}, current_lesson_id=99)]
        self.assertEqual(order[:3], [30, 20, 10])

    def test_a_card_the_learner_has_not_met_is_never_mixed_in(self):
        cards = {10: card(10), 20: card(20), 30: card(30)}
        self.assertEqual(comp.select_mix(self.cands(), cards, {}, current_lesson_id=3), [])
        cards[20] = card(20, {"1": [1]})  # answered a question about it: met
        picks = comp.select_mix(self.cands(), cards, {}, current_lesson_id=3)
        self.assertEqual({p.candidate.lesson_id for p in picks}, {2})

    def test_questions_answered_wrong_come_back_after_the_due_cards(self):
        cards = {10: card(10, in_srs=True), 20: card(20, in_srs=True, due=True)}
        results = {(1, "BF1:a"): False, (2, "BO2"): True}
        picks = comp.select_mix(self.cands(), cards, results, current_lesson_id=3)
        self.assertEqual([(p.candidate.exercise_id, p.reason) for p in picks][:2], [("BO2", "due"), ("BF1", "wrong")])

    def test_unanswered_exercises_of_earlier_lessons_fill_the_rest_easiest_stage_first(self):
        cards = {10: card(10, in_srs=True, difficulty=3), 20: card(20, in_srs=True, difficulty=1)}
        picks = comp.select_mix(self.cands(), cards, {}, current_lesson_id=3, limit=3)
        self.assertEqual([p.reason for p in picks], ["new"] * 3)
        self.assertEqual(picks[0].candidate.lesson_id, 2)  # card 20 is the easier stage

    def test_the_current_lessons_unanswered_exercises_are_its_own_practice(self):
        cards = {30: card(30, in_srs=True, due=True, lesson_id=3)}
        self.assertEqual(comp.select_mix(self.cands(), cards, {}, current_lesson_id=3), [])
        picks = comp.select_mix(self.cands(), cards, {(3, "BO3"): False}, current_lesson_id=3)
        self.assertEqual([p.candidate.exercise_id for p in picks], ["BO3"])  # answered before: may come back

    def test_nothing_is_offered_twice_and_a_card_has_at_most_two_places(self):
        cards = {10: card(10, in_srs=True, due=True)}
        picks = comp.select_mix(self.cands(), cards, {(1, "R1.1"): False, (1, "BF1:a"): False}, current_lesson_id=9, limit=8)
        ids = [p.candidate.exercise_id for p in picks]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(ids), comp.PER_CARD)

    def test_the_limit_is_respected_and_capped(self):
        cards = {10: card(10, in_srs=True), 20: card(20, in_srs=True)}
        self.assertEqual(len(comp.select_mix(self.cands(), cards, {}, 9, limit=1)), 1)
        self.assertEqual(comp.select_mix(self.cands(), cards, {}, 9, limit=0), [])
        many = [Candidate(1, f"E{i}", 1, (i,), (f"E{i}",)) for i in range(40)]
        cs = {i: card(i, in_srs=True) for i in range(40)}
        self.assertEqual(len(comp.select_mix(many, cs, {}, 9, limit=99)), comp.MAX_MIX)

    def test_a_candidate_without_a_card_is_not_offered(self):
        cands = [Candidate(1, "X", 1, (), ("X",))]
        self.assertEqual(comp.select_mix(cands, {}, {(1, "X"): False}, 9), [])


class ReportTests(unittest.TestCase):
    def test_summarize_counts_levels_and_memory(self):
        cards = [
            card(1),  # never met
            card(2, in_srs=True),  # met, nothing passed
            card(3, {"0": [1]}, in_srs=True, strength=0.8),
            card(4, {"3": [1]}, in_srs=True, strength=0.4, due=True, use_level="produce"),
            card(5, {"0": [1]}, in_srs=True, strength=0.9, use_level="recognize", leech=True),
        ]
        s = comp.summarize(cards)
        self.assertEqual((s["cards"], s["unseen"], s["studying"]), (5, 1, 1))
        self.assertEqual(s["by_level"], {"0": 2, "1": 0, "2": 0, "3": 1})
        self.assertEqual(s["goal_reached"], 2)  # card 4 (rung 3) and card 5 (recognize, rung 0)
        self.assertEqual(s["remembered"], 1)  # card 3; card 5 is a leech
        self.assertEqual((s["due"], s["leeches"]), (1, 1))

    def test_weakest_lists_leeches_then_shaky_then_failing_rungs(self):
        cards = [
            card(1, {"1": [0, 0]}, in_srs=True),
            card(2, in_srs=True, shaky=True),
            card(3, in_srs=True, leech=True),
            card(4, {"0": [1]}, in_srs=True),
            card(5),
        ]
        out = comp.weakest(cards)
        self.assertEqual([w["grammar_id"] for w in out], [3, 2, 1])
        self.assertIn("Xếp câu", out[2]["why"])

    def test_recommendations_are_ordered_and_capped(self):
        l1 = comp.LessonCards(1, "Bài 1", [card(1, {"0": [1]}, in_srs=True, due=True), card(2)])
        l2 = comp.LessonCards(2, "Bài 2", [card(3)])
        recs = comp.recommend([l1, l2])
        self.assertEqual([r["kind"] for r in recs], ["review", "practice", "learn"])
        self.assertEqual(recs[1]["lesson_id"], 1)
        self.assertEqual(recs[1]["skill"], "build")  # card 1 passed rung 0: next is Xếp câu
        self.assertEqual(recs[2]["lesson_id"], 1)  # the first lesson with an unseen card
        self.assertLessEqual(len(comp.recommend([l1, l2], limit=2)), 2)

    def test_when_everything_is_reached_the_advice_is_to_mix(self):
        done = comp.LessonCards(1, "Bài 1", [card(1, {"3": [1]}, in_srs=True, strength=1.0)])
        self.assertEqual([r["kind"] for r in comp.recommend([done])], ["mix"])
        self.assertEqual(comp.recommend([]), [])


if __name__ == "__main__":
    unittest.main()

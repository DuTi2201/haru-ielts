"""Practice on real TOPIK II papers: the papers and guides as files (app.services.real_exam), the
matching of a question to lesson cards, the rules of the selection and the answers."""
import unittest
from datetime import datetime, timedelta, timezone

from app.schemas import RxAnswerOut, RxQuestionOut, RxSetOut
from app.services import real_exam as rx
from app.services import weakness

NOW = datetime(2026, 10, 10, 12, 0, tzinfo=timezone.utc)
BANK = rx.load()


def lex(grammar=(), vocab=()):
    return rx.lexicon_of(grammar, vocab, {1: "Bài 1"})


def item(qid):
    return BANK.items[qid]


def cand(qid, seen=None, status="ready"):
    return rx.Candidate(item(qid), seen, rx.Fit(0, 0, 0, status))  # type: ignore[arg-type]


def seen(status, when=NOW - timedelta(days=30)):
    right = status != "wrong"
    return rx.Seen(attempts=1, last_at=when, last_right=right, last_hints=0 if status == "solid" else 1, ever_unaided=status == "solid", right_count=int(right))


class PapersAreSound(unittest.TestCase):
    def test_the_files_pass_their_own_check(self):
        self.assertEqual(rx.check(BANK), [])

    def test_every_question_has_a_guide_and_every_guide_a_question(self):
        used = {i.type for i in BANK.items.values()}
        self.assertEqual(used, set(BANK.types))

    def test_a_paper_holds_listening_reading_and_writing(self):
        secs = {i.sec for i in BANK.of_exam("topik-96")}
        self.assertEqual(secs, {"L", "R", "W"})
        self.assertEqual(len([i for i in BANK.items.values() if i.sec == "L" and i.exam == "topik-96"]), 50)

    def test_spoken_clips_carry_no_stage_directions_and_fit_the_audio_limit(self):
        for it in BANK.items.values():
            for c in it.clips:
                self.assertNotIn("(", c.ko, it.qid)
                self.assertLessEqual(len(c.ko), 600, it.qid)

    def test_a_what_is_said_next_question_does_not_voice_its_unspoken_last_turn(self):
        it = item("96-L-4")
        self.assertEqual(it.turns[-1][1], "…")
        self.assertEqual(len(it.clips), len(it.turns) - 1)

    def test_questions_that_share_a_recording_share_it(self):
        a, b = item("96-L-21"), item("96-L-22")
        self.assertEqual(a.bundle, b.bundle)
        self.assertEqual(a.clips, b.clips)
        self.assertEqual(b.tr, a.tr)

    def test_every_wrong_option_is_explained_and_the_crossed_out_one_is_wrong(self):
        for it in BANK.items.values():
            if it.is_mcq:
                self.assertNotEqual(it.seed.elim, it.seed.ans, it.qid)
                self.assertEqual(len(it.seed.wrong), 3, it.qid)

    def test_error_labels_cover_every_type(self):
        for code in BANK.types:
            self.assertNotEqual(weakness.label_for(code), code, code)

    def test_nothing_that_gives_the_answer_goes_out_with_a_question(self):
        fields = set(RxQuestionOut.model_fields) | set(RxSetOut.model_fields)
        for leak in ("ans", "why", "wrong", "take", "tr", "focus", "elim", "ov", "model", "sample", "accepted"):
            self.assertNotIn(leak, fields)
        self.assertIn("ans", RxAnswerOut.model_fields)


class MatchingToLessons(unittest.TestCase):
    def test_a_pattern_is_found_whatever_the_marker_or_optional_vowel(self):
        a = rx.pattern_cores("V + -(으)ㄹ 뿐만 아니라")
        b = rx.pattern_cores("-(으)ㄹ 뿐만 아니라")
        self.assertEqual(rx.pattern_match(a, b), 2)

    def test_alternations_are_expanded(self):
        self.assertEqual(rx._variants("-아/어야겠다"), ["-아야겠다", "-어야겠다"])
        self.assertEqual(rx._variants("N을/를 맞이하여"), ["N을 맞이하여", "N를 맞이하여"])
        self.assertEqual(rx._variants("-(으)ㄹ 수 있다/없다"), ["-ㄹ 수 있다", "-ㄹ 수 없다"])

    def test_a_card_listing_several_forms_matches_any_of_them(self):
        card = rx.pattern_cores("N + 덕분에 · V + -(으)ㄴ/는 덕분에")
        self.assertEqual(rx.pattern_match(rx.pattern_cores("N 덕분에"), card), 2)
        self.assertEqual(rx.pattern_match(rx.pattern_cores("-(으)ㄴ/는 덕분에"), card), 2)

    def test_a_close_relative_is_not_the_same_pattern(self):
        self.assertEqual(rx.pattern_match(rx.pattern_cores("-(으)면 좋겠다"), rx.pattern_cores("V + -았/었으면 좋겠다")), 1)

    def test_one_letter_and_vietnamese_labels_never_match(self):
        self.assertEqual(rx.pattern_cores("-다(가)"), set())
        self.assertEqual(rx.pattern_cores("Thể trần thuật (서술체: -(느)ㄴ다 / -다)"), set())

    def test_a_grammar_form_in_a_gloss_is_not_a_word(self):
        self.assertEqual(rx.headwords("-지 그래요?"), [])
        self.assertEqual(rx.headwords("나아지다 / 낫다"), ["나아지다", "낫다"])

    def test_cards_of_a_question_are_found_and_the_fit_follows_what_was_met(self):
        lx = lex(
            [(10, 1, "V + -아/어 보다", "Thử làm"), (11, 1, "V + -고 나서", "Sau khi")],
            [(20, 1, "수박", "dưa hấu")],
        )
        needs = rx.needs_of(item("96-L-1"), lx)
        labels = {r.label for r in needs.cards()}
        self.assertIn("V + -아/어 보다", labels)
        self.assertIn("수박", labels)
        met_all = {("grammar_point", 10), ("vocab_item", 20)}
        self.assertEqual(rx.fit_of(needs, met_all).upcoming, 0)
        self.assertEqual(rx.fit_of(needs, set()).status, "stretch")
        self.assertGreaterEqual(rx.fit_of(needs, set()).new, 1)  # points no lesson has never block a question

    def test_a_pattern_listed_among_the_words_is_shown_once_and_as_grammar(self):
        needs = rx.needs_of(item("96-L-1"), lex())
        shown = [g.k for g, _r in needs.grammar] + [ko for ko, _vi, _r in needs.words]
        self.assertEqual(sum(1 for k in shown if "봐도 되다" in k), 1)  # the grammar list already has it
        self.assertFalse([ko for ko, _vi, _r in needs.words if ko[:1] in "-~"])
        other = rx.needs_of(item("96-L-17"), lex())  # "-거든(요)" is only in the glossary: a grammar point of its own
        self.assertIn("-거든(요)", [g.k for g, _r in other.grammar])

    def test_many_missing_cards_make_a_question_for_later(self):
        refs = tuple(rx.CardRef("grammar_point", i, 1, f"p{i}", "") for i in range(1, 4))
        needs = rx.Needs(grammar=tuple((rx.Gram(k=f"g{i}", vi="x"), (refs[i],)) for i in range(3)), words=())
        self.assertEqual(rx.fit_of(needs, set()).status, "later")


class WhatComesBack(unittest.TestCase):
    def test_rests(self):
        self.assertTrue(rx.due_again(None, NOW))
        self.assertFalse(rx.due_again(seen("wrong", NOW - timedelta(hours=11)), NOW))
        self.assertTrue(rx.due_again(seen("wrong", NOW - timedelta(hours=13)), NOW))
        self.assertFalse(rx.due_again(seen("aided", NOW - timedelta(days=2)), NOW))
        self.assertTrue(rx.due_again(seen("aided", NOW - timedelta(days=4)), NOW))
        self.assertFalse(rx.due_again(seen("solid", NOW - timedelta(days=6)), NOW))
        self.assertTrue(rx.due_again(seen("solid", NOW - timedelta(days=8)), NOW))

    def test_only_an_answer_without_hint_is_solid(self):
        s = rx.seen_of([(NOW - timedelta(days=2), False, 0), (NOW - timedelta(days=1), True, 2)])
        self.assertEqual(s.status, "aided")
        s = rx.seen_of([(NOW - timedelta(days=2), True, 0), (NOW - timedelta(days=1), False, 0)])
        self.assertEqual(s.status, "wrong")
        self.assertTrue(s.ever_unaided)
        self.assertEqual(rx.seen_of([(NOW, True, 0)]).status, "solid")
        self.assertIsNone(rx.seen_of([]))

    def test_a_tier_is_solid_at_80_percent_and_the_lowest_unsolid_tier_is_the_current_one(self):
        self.assertTrue(rx.tier_is_solid(4, 5))
        self.assertFalse(rx.tier_is_solid(3, 5))
        self.assertFalse(rx.tier_is_solid(0, 0))
        standing = {1: (4, 5), 2: (1, 4), 3: (0, 2)}
        self.assertEqual(rx.current_tier(standing), 2)
        self.assertIsNone(rx.current_tier({1: (4, 5)}))

    def test_stage_follows_the_share_of_grammar_met(self):
        self.assertEqual(rx.stage_of(5, 100), "starter")
        self.assertEqual(rx.stage_of(30, 100), "building")
        self.assertEqual(rx.stage_of(60, 100), "solid")
        self.assertEqual(rx.stage_of(0, 0), "starter")


class ChoosingQuestions(unittest.TestCase):
    pool_ids = ["96-L-1", "96-L-2", "96-L-4", "96-L-5", "96-L-6", "96-L-7", "96-L-8"]

    def standing(self, pool):
        return {t: rx.tier_standing([c.it for c in pool if c.it.type == t], {}) for t in {c.it.type for c in pool}}

    def test_easy_questions_come_first_and_all_are_new(self):
        pool = [cand(q) for q in self.pool_ids]
        got = rx.pick_questions(BANK, pool, self.standing(pool), size=4, now=NOW)
        tiers = [i.tier for i in got]
        self.assertEqual(len(got), 4)
        self.assertEqual(tiers, sorted(tiers))
        self.assertEqual(max(tiers), 1)

    def test_a_question_to_try_again_comes_before_new_ones(self):
        pool = [cand("96-L-4"), cand("96-L-5"), cand("96-L-6", seen("wrong", NOW - timedelta(days=2)))]
        got = rx.pick_questions(BANK, pool, self.standing(pool), size=1, now=NOW)
        self.assertEqual([i.qid for i in got], ["96-L-6"])

    def test_a_resting_question_is_not_offered_and_a_solid_one_comes_last(self):
        pool = [
            cand("96-L-4", seen("solid", NOW - timedelta(days=1))),
            cand("96-L-5", seen("wrong", NOW - timedelta(hours=2))),
            cand("96-L-6", seen("solid", NOW - timedelta(days=9))),
            cand("96-L-7"),
        ]
        got = [i.qid for i in rx.pick_questions(BANK, pool, self.standing(pool), size=5, now=NOW)]
        self.assertNotIn("96-L-4", got)
        self.assertNotIn("96-L-5", got)
        self.assertEqual(got, ["96-L-6", "96-L-7"])  # sorted back by number; the due check-in is included

    def test_questions_sharing_a_recording_come_together(self):
        pool = [cand("96-L-21"), cand("96-L-22")]
        got = rx.pick_questions(BANK, pool, self.standing(pool), size=1, now=NOW)
        self.assertEqual({i.qid for i in got}, {"96-L-21", "96-L-22"})

    def test_the_tier_cap_keeps_hard_questions_away_unless_already_tried(self):
        pool = [cand("96-L-8"), cand("96-L-5")]  # tier 3 and tier 1
        got = rx.pick_questions(BANK, pool, self.standing(pool), size=5, now=NOW, tier_cap=2)
        self.assertEqual([i.qid for i in got], ["96-L-5"])

    def test_a_sitting_of_written_answers_is_short(self):
        pool = [cand(q) for q in ("96-W-51", "96-W-52", "96-W-53", "96-W-54")]
        got = rx.pick_questions(BANK, pool, self.standing(pool), size=5, now=NOW)
        self.assertLessEqual(len(got), rx.WRITING_SET_SIZE)

    def test_type_ranking_puts_retries_then_the_lowest_tier_first(self):
        def stat(code, **kw):
            base = dict(code=code, total=4, tried=0, solid=0, wrong_open=0, retry_due=0, open=4, ready_open=2, right=0, attempts=0, cur_tier=1, standing={1: (0, 4)})
            base.update(kw)
            return rx.TypeStat(**base)

        stats = {
            "listen_picture": stat("listen_picture", cur_tier=1),
            "read_cloze": stat("read_cloze", cur_tier=1),
            "listen_match": stat("listen_match", cur_tier=2),
            "read_order": stat("read_order", cur_tier=2, retry_due=1),
            "write_fill": stat("write_fill", cur_tier=1),
        }
        ranked = rx.rank_types(BANK, stats, "starter")
        self.assertEqual(ranked[0], "read_order")  # a retry is due
        self.assertEqual(ranked[1:3], ["listen_picture", "read_cloze"])  # then tier 1, by family order
        self.assertEqual(ranked[-1], "write_fill")  # a starter writes last
        self.assertEqual(rx.rank_types(BANK, {"x": stat("listen_picture", open=0)}, "solid"), [])


class Answering(unittest.TestCase):
    def test_choice(self):
        it = item("96-L-4")
        self.assertTrue(rx.grade_choice(it, it.seed.ans))
        self.assertFalse(rx.grade_choice(it, None))
        self.assertFalse(rx.grade_choice(it, 1 if it.seed.ans != 1 else 2))

    def test_a_written_blank_matches_the_accepted_answers_ignoring_spaces_and_stops(self):
        it = item("96-W-51")
        got = rx.grade_blanks(it, {"㉠": "하려고  합니다.", "㉡": "어디가 좋은지"})
        self.assertTrue(got[0][2])
        self.assertFalse(got[1][2])
        got = rx.grade_blanks(it, {"㉠": "", "㉡": "동네가좋은지"})
        self.assertFalse(got[0][2])
        self.assertTrue(got[1][2])

    def test_the_length_counts_spaces_but_not_line_breaks(self):
        self.assertEqual(rx.char_count("가 나\n다"), 4)

    def test_chart_writing_is_checked_for_length_style_and_numbers(self):
        it = item("96-W-53")
        checks = {c.label: c for c in rx.check_writing(it, "한국스포츠연구소에서 조사하였다. 2013년 40만 명에서 2023년 100만 명으로 증가했습니다.")}
        self.assertFalse(checks["Độ dài"].ok)
        self.assertFalse(checks["Văn phong"].ok)
        self.assertFalse(checks["Số liệu"].ok)
        self.assertIn("2.5", checks["Số liệu"].note)

    def test_an_essay_that_copies_the_prompt_is_flagged(self):
        it = item("96-W-54")
        checks = {c.label: c for c in rx.check_writing(it, it.seed.prompt or "")}
        self.assertFalse(checks["Không chép lại đề"].ok)
        ok = {c.label: c for c in rx.check_writing(it, it.seed.model or "")}
        self.assertTrue(ok["Không chép lại đề"].ok)
        self.assertTrue(ok["Độ dài"].ok)
        self.assertTrue(ok["Văn phong"].ok)

    def test_the_model_answers_of_the_chart_and_essay_pass_their_own_checks(self):
        for qid in ("96-W-53", "96-W-54"):
            it = item(qid)
            for c in rx.check_writing(it, it.seed.model or ""):
                self.assertTrue(c.ok, f"{qid} {c.label}: {c.note}")

    def test_hints_climb_from_what_to_look_for_to_crossing_one_out(self):
        it = item("96-L-4")
        self.assertEqual(rx.hint(it, 1)["kind"], "focus")
        h2 = rx.hint(it, 2)
        self.assertEqual(len(h2["options_vi"]), 4)
        self.assertEqual(rx.hint(it, 3)["option"], it.seed.elim)
        with self.assertRaises(ValueError):
            rx.hint(it, 4)
        w = item("96-W-51")
        self.assertEqual(rx.hint(w, 2)["kind"], "patterns")
        self.assertTrue(rx.hint(w, 3)["items"][0]["text"].endswith("…"))
        self.assertEqual(rx.hint(item("96-W-54"), 3)["kind"], "outline")

    def test_results(self):
        self.assertEqual(rx.result_of(rx.Outcome("q", True, 0)), "solid")
        self.assertEqual(rx.result_of(rx.Outcome("q", True, 2)), "aided")
        self.assertEqual(rx.result_of(rx.Outcome("q", False, 0)), "wrong")
        self.assertEqual(rx.result_of(rx.Outcome("q", False, 0, pending=True)), "pending")

    def test_the_next_step_follows_how_the_sitting_went(self):
        self.assertIn("làm lại", rx.next_step({"wrong": 2}, False, []))
        self.assertIn("3 ngày", rx.next_step({"aided": 1}, False, []))
        self.assertIn("Học tiếp", rx.next_step({"solid": 3}, False, ["V-고 나서"]))
        self.assertIn("bậc tiếp theo", rx.next_step({"solid": 3}, True, []))


if __name__ == "__main__":
    unittest.main()

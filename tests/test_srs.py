"""The review schedule and the daily queue: pure functions, no database."""
import unittest
from datetime import datetime, timedelta, timezone

from app.services import srs
from app.services.srs import Schedule, build_queue, review

NOW = datetime(2026, 10, 1, 9, 0, tzinfo=timezone.utc)
DAY = timedelta(days=1)


def answer_correctly(schedule, times, start=NOW):
    """Answer right every time the item comes due; returns the schedules in order."""
    out, now = [], start
    for _ in range(times):
        schedule = review(schedule, True, now)
        out.append(schedule)
        now = schedule.due_at
    return out


class ReviewTests(unittest.TestCase):
    def test_a_first_correct_answer_brings_the_item_back_tomorrow(self):
        s = review(None, True, NOW)
        self.assertEqual((s.reps, s.lapses, s.interval_days), (1, 0, 1.0))
        self.assertEqual(s.due_at, NOW + DAY)
        self.assertEqual(s.introduced_at, NOW)
        self.assertAlmostEqual(s.strength, 0.2)

    def test_the_gaps_grow_along_the_ladder_1_3_then_by_ease(self):
        steps = answer_correctly(None, 6)
        self.assertEqual([s.interval_days for s in steps], [1, 3, 7, 15, 33, 73])
        self.assertEqual([s.reps for s in steps], [1, 2, 3, 4, 5, 6])

    def test_the_gap_never_exceeds_the_cap(self):
        s = Schedule(reps=9, interval_days=170, ease=2.2, due_at=NOW, strength=1.0)
        self.assertEqual(review(s, True, NOW).interval_days, srs.MAX_INTERVAL_DAYS)

    def test_a_gap_always_grows_even_with_the_lowest_ease(self):
        s = Schedule(reps=4, interval_days=3, ease=srs.MIN_EASE, due_at=NOW)
        self.assertGreaterEqual(review(s, True, NOW).interval_days, 4)

    def test_a_wrong_answer_restarts_the_ladder_and_brings_the_item_back_in_ten_minutes(self):
        s = review(Schedule(reps=4, interval_days=15, ease=2.2, due_at=NOW, strength=0.8, introduced_at=NOW - 20 * DAY), False, NOW)
        self.assertEqual((s.reps, s.lapses, s.interval_days), (0, 1, 0.0))
        self.assertEqual(s.due_at, NOW + srs.RELEARN_DELAY)
        self.assertAlmostEqual(s.ease, 2.0)
        self.assertAlmostEqual(s.strength, 0.6)
        self.assertEqual(s.introduced_at, NOW - 20 * DAY)  # still the day it was first met

    def test_ease_has_a_floor(self):
        s = Schedule(ease=1.35)
        for _ in range(5):
            s = review(s, False, NOW)
        self.assertEqual(s.ease, srs.MIN_EASE)
        self.assertEqual(s.lapses, 5)

    def test_after_a_lapse_one_correct_answer_is_the_first_step_again(self):
        lapsed = review(Schedule(reps=5, interval_days=30, due_at=NOW, strength=1.0), False, NOW)
        again = review(lapsed, True, NOW + timedelta(minutes=10))
        self.assertEqual((again.reps, again.interval_days), (1, 1.0))

    def test_a_wrong_first_answer_is_a_lapse_of_a_new_item(self):
        s = review(None, False, NOW)
        self.assertEqual((s.reps, s.lapses, s.strength), (0, 1, 0.0))
        self.assertEqual(s.due_at, NOW + srs.RELEARN_DELAY)

    def test_strength_stays_between_zero_and_one(self):
        self.assertEqual(review(Schedule(strength=1.0, due_at=NOW), True, NOW).strength, 1.0)
        self.assertEqual(review(Schedule(strength=0.0), False, NOW).strength, 0.0)

    def test_a_correct_answer_before_it_is_due_does_not_move_the_schedule(self):
        due = NOW + 3 * DAY
        s = Schedule(reps=2, interval_days=3, due_at=due, strength=0.4, introduced_at=NOW - DAY)
        after = review(s, True, NOW)  # three days early
        self.assertEqual((after.reps, after.interval_days, after.due_at), (2, 3, due))
        self.assertAlmostEqual(after.strength, 0.6)  # but strength still moves, as it always did

    def test_running_a_deck_again_the_same_day_cannot_push_cards_out(self):
        s = review(None, True, NOW)
        for minutes in (5, 20, 90):
            s = review(s, True, NOW + timedelta(minutes=minutes))
        self.assertEqual((s.reps, s.interval_days), (1, 1.0))

    def test_a_wrong_answer_before_it_is_due_still_counts(self):
        s = review(Schedule(reps=3, interval_days=7, due_at=NOW + 7 * DAY), False, NOW)
        self.assertEqual((s.reps, s.lapses), (0, 1))

    def test_an_answer_in_the_grace_window_counts(self):
        due = NOW + srs.DUE_GRACE - timedelta(minutes=1)  # due in a bit under 6 h: it was offered
        s = review(Schedule(reps=1, interval_days=1, due_at=due), True, NOW)
        self.assertEqual(s.reps, 2)

    def test_the_first_answer_of_a_legacy_row_without_a_due_time_counts(self):
        s = review(Schedule(strength=0.4, reps=0, due_at=None), True, NOW)
        self.assertEqual((s.reps, s.interval_days), (1, 1.0))


class IsDueTests(unittest.TestCase):
    def test_due_includes_the_grace_window_and_the_past(self):
        self.assertTrue(srs.is_due(Schedule(due_at=NOW - DAY), NOW))
        self.assertTrue(srs.is_due(Schedule(due_at=NOW + srs.DUE_GRACE), NOW))
        self.assertFalse(srs.is_due(Schedule(due_at=NOW + srs.DUE_GRACE + timedelta(minutes=1)), NOW))

    def test_an_item_without_a_due_time_is_not_due(self):
        self.assertFalse(srs.is_due(Schedule(), NOW))


def vocab(*ids):
    return [("vocab_item", i) for i in ids]


def grammar(*ids):
    return [("grammar_point", i) for i in ids]


class QueueTests(unittest.TestCase):
    LESSONS = {
        1: vocab(1, 2, 3, 4, 5, 6) + grammar(1, 2),
        2: vocab(7, 8, 9, 10) + grammar(3),
    }

    def test_a_new_learner_gets_the_days_cap_from_the_first_lesson_with_grammar_spread_in(self):
        q = build_queue({}, self.LESSONS, NOW)
        self.assertEqual((q.due_total, q.new_today, q.new_budget), (0, 0, 8))
        self.assertEqual(len(q.new), 8)
        self.assertEqual(q.new, vocab(1, 2) + grammar(1) + vocab(3, 4) + grammar(2) + vocab(5, 6))

    def test_words_that_only_need_recognising_come_after_the_core_words_of_their_lesson(self):
        q = build_queue({}, self.LESSONS, NOW, new_limit=6, later=set(vocab(1, 2, 3)))
        self.assertEqual([k for k in q.new if k[0] == "vocab_item"], vocab(4, 5, 6, 1, 2))  # then lesson 1's own recognise-only words
        # nothing is hidden: with room for everything they are all offered, still before the next lesson
        every = build_queue({}, self.LESSONS, NOW, new_limit=20, later=set(vocab(1, 2, 3)))
        self.assertEqual([k for k in every.new if k[0] == "vocab_item"], vocab(4, 5, 6, 1, 2, 3, 7, 8, 9, 10))

    def test_the_cap_counts_what_was_started_in_the_last_24_hours(self):
        started = {k: Schedule(introduced_at=NOW - timedelta(hours=3), due_at=NOW + DAY) for k in vocab(1, 2, 3, 4, 5)}
        q = build_queue(started, self.LESSONS, NOW)
        self.assertEqual((q.new_today, q.new_budget, len(q.new)), (5, 3, 3))
        self.assertTrue(all(k not in started for k in q.new))

    def test_a_card_started_yesterday_no_longer_counts_against_today(self):
        old = {k: Schedule(introduced_at=NOW - timedelta(hours=25), due_at=NOW + DAY) for k in vocab(1, 2, 3, 4)}
        q = build_queue(old, self.LESSONS, NOW)
        self.assertEqual((q.new_today, q.new_budget), (0, 8))

    def test_when_the_cap_is_used_up_nothing_new_is_offered(self):
        started = {k: Schedule(introduced_at=NOW - timedelta(hours=1), due_at=NOW + DAY) for k in vocab(*range(1, 9))}
        q = build_queue(started, self.LESSONS, NOW)
        self.assertEqual((q.new, q.new_budget), ([], 0))

    def test_new_cards_spill_into_the_next_lesson_when_the_first_runs_out(self):
        seen = {k: Schedule(introduced_at=NOW - 3 * DAY, due_at=NOW + DAY) for k in vocab(1, 2, 3, 4, 5) + grammar(1, 2)}
        q = build_queue(seen, self.LESSONS, NOW, new_limit=4)
        # vocab 6 closes lesson 1, the rest comes from lesson 2; the grammar point is spread among them
        self.assertEqual(sorted(q.new), sorted(vocab(6, 7, 8) + grammar(3)))
        self.assertEqual([k for k in q.new if k[0] == "vocab_item"], vocab(6, 7, 8))

    def test_with_no_vocabulary_left_grammar_fills_the_day(self):
        lessons = {1: grammar(1, 2, 3)}
        self.assertEqual(build_queue({}, lessons, NOW, new_limit=8).new, grammar(1, 2, 3))

    def test_with_no_grammar_vocabulary_fills_the_day(self):
        lessons = {1: vocab(1, 2, 3, 4, 5)}
        self.assertEqual(len(build_queue({}, lessons, NOW, new_limit=4).new), 4)

    def test_a_small_cap_has_no_grammar_until_there_is_room_for_one(self):
        self.assertEqual(build_queue({}, self.LESSONS, NOW, new_limit=3).new, vocab(1, 2, 3))
        self.assertEqual(len([k for k in build_queue({}, self.LESSONS, NOW, new_limit=4).new if k[0] == "grammar_point"]), 1)

    def test_due_cards_come_most_overdue_first_and_are_cut_at_the_limit(self):
        s = {
            ("vocab_item", 1): Schedule(reps=1, due_at=NOW - timedelta(hours=1)),
            ("vocab_item", 2): Schedule(reps=1, due_at=NOW - 3 * DAY),
            ("vocab_item", 3): Schedule(reps=1, due_at=NOW - DAY),
            ("vocab_item", 4): Schedule(reps=1, due_at=NOW + 2 * DAY),  # not due
        }
        q = build_queue(s, self.LESSONS, NOW, limit=2)
        self.assertEqual(q.due, vocab(2, 3))
        self.assertEqual(q.due_total, 3)

    def test_an_item_that_no_longer_exists_is_never_offered(self):
        s = {("vocab_item", 999): Schedule(reps=1, due_at=NOW - DAY)}  # its lesson was rolled back
        q = build_queue(s, self.LESSONS, NOW)
        self.assertEqual((q.due, q.due_total), ([], 0))

    def test_an_item_that_was_forgotten_is_due_again_within_minutes(self):
        s = {("vocab_item", 1): review(None, False, NOW)}
        self.assertEqual(build_queue(s, self.LESSONS, NOW + timedelta(minutes=11)).due, vocab(1))

    def test_a_lesson_with_nothing_to_study_is_skipped(self):
        self.assertEqual(build_queue({}, {1: [], 2: vocab(7)}, NOW).new, vocab(7))

    def test_without_any_content_the_queue_is_empty(self):
        q = build_queue({}, {}, NOW)
        self.assertEqual((q.due, q.new, q.due_total), ([], [], 0))


class LeechTests(unittest.TestCase):
    def test_forgotten_twice_and_not_yet_back_on_its_feet_is_a_leech(self):
        self.assertTrue(srs.is_leech(Schedule(lapses=2, reps=0)))
        self.assertTrue(srs.is_leech(Schedule(lapses=3, reps=2)))

    def test_forgotten_once_is_shaky_but_not_a_leech(self):
        s = Schedule(lapses=1, reps=0)
        self.assertFalse(srs.is_leech(s))
        self.assertTrue(srs.is_shaky(s))

    def test_three_right_answers_in_a_row_make_it_well_again(self):
        s = Schedule(lapses=4, reps=3)
        self.assertFalse(srs.is_leech(s))
        self.assertFalse(srs.is_shaky(s))

    def test_a_card_never_forgotten_is_neither(self):
        self.assertFalse(srs.is_leech(Schedule()))
        self.assertFalse(srs.is_shaky(Schedule()))

    def test_a_leech_goes_before_a_card_that_is_more_overdue(self):
        lessons = {1: vocab(1, 2, 3)}
        s = {
            ("vocab_item", 1): Schedule(reps=1, due_at=NOW - 5 * DAY),
            ("vocab_item", 2): Schedule(reps=0, lapses=2, due_at=NOW - timedelta(minutes=10)),
            ("vocab_item", 3): Schedule(reps=1, due_at=NOW - 2 * DAY),
        }
        self.assertEqual(build_queue(s, lessons, NOW).due, vocab(2, 1, 3))

    def test_a_leech_is_not_cut_by_the_limit_while_other_cards_are(self):
        lessons = {1: vocab(*range(1, 8))}
        s = {("vocab_item", i): Schedule(reps=1, due_at=NOW - i * DAY) for i in range(1, 7)}
        s[("vocab_item", 7)] = Schedule(reps=0, lapses=2, due_at=NOW - timedelta(minutes=1))
        q = build_queue(s, lessons, NOW, limit=3)
        self.assertEqual(q.due[0], ("vocab_item", 7))
        self.assertEqual(q.due_total, 7)

    def test_weak_keys_lists_the_most_forgotten_first_due_or_not(self):
        s = {
            ("vocab_item", 1): Schedule(lapses=1, reps=0, strength=0.0, due_at=NOW + 3 * DAY),
            ("vocab_item", 2): Schedule(lapses=3, reps=1, strength=0.2, due_at=NOW + DAY),
            ("grammar_point", 1): Schedule(lapses=3, reps=0, strength=0.0, due_at=NOW - DAY),
            ("vocab_item", 3): Schedule(lapses=0, reps=5, strength=1.0),
            ("vocab_item", 4): Schedule(lapses=5, reps=4, strength=1.0),  # well again
            ("vocab_item", 99): Schedule(lapses=9, reps=0),  # no longer exists
        }
        existing = {k for k in s if k != ("vocab_item", 99)}
        self.assertEqual(
            srs.weak_keys(s, existing), [("grammar_point", 1), ("vocab_item", 2), ("vocab_item", 1)]
        )
        self.assertEqual(srs.weak_keys(s, existing, limit=1), [("grammar_point", 1)])


class ArticleWordTests(unittest.TestCase):
    LESSONS = {1: vocab(1, 2, 3, 4, 5, 6, 7, 8, 9) + grammar(1, 2)}
    ARTICLES = {"a-new": vocab(101, 102, 103), "a-old": vocab(201, 202)}

    def test_about_one_new_card_in_four_is_an_article_word(self):
        q = build_queue({}, self.LESSONS, NOW, articles=self.ARTICLES)
        words = [k for k in q.new if k[1] > 100]
        self.assertEqual(len(q.new), 8)
        self.assertEqual(words, vocab(101, 102))  # budget 8 // 4
        self.assertEqual(len([k for k in q.new if k[0] == "grammar_point"]), 2)
        self.assertEqual(len([k for k in q.new if k[0] == "vocab_item" and k[1] < 100]), 4)

    def test_the_words_of_one_article_come_before_the_next_articles(self):
        q = build_queue({}, {}, NOW, articles=self.ARTICLES, new_limit=8)
        self.assertEqual(q.new, vocab(101, 102, 103, 201, 202))

    def test_article_words_fill_the_day_when_the_lessons_run_out(self):
        q = build_queue({}, {1: vocab(1, 2) + grammar(1)}, NOW, articles=self.ARTICLES, new_limit=8)
        self.assertEqual(len(q.new), 8)  # the 3 lesson cards plus all 5 article words
        self.assertEqual(sorted(k[1] for k in q.new if k[1] > 100), [101, 102, 103, 201, 202])

    def test_a_small_cap_has_no_article_word_until_the_lessons_are_done(self):
        q = build_queue({}, self.LESSONS, NOW, articles=self.ARTICLES, new_limit=3)
        self.assertEqual(q.new, vocab(1, 2, 3))

    def test_a_word_already_started_is_not_offered_again_but_is_scheduled(self):
        started = {("vocab_item", 101): Schedule(reps=1, introduced_at=NOW - 3 * DAY, due_at=NOW - DAY)}
        q = build_queue(started, self.LESSONS, NOW, articles=self.ARTICLES)
        self.assertEqual(q.due, vocab(101))
        self.assertNotIn(("vocab_item", 101), q.new)
        self.assertEqual(q.article_waiting, 4)

    def test_a_word_of_an_article_that_is_gone_is_not_due(self):
        s = {("vocab_item", 555): Schedule(reps=1, due_at=NOW - DAY)}
        self.assertEqual(build_queue(s, self.LESSONS, NOW, articles=self.ARTICLES).due, [])

    def test_without_articles_nothing_changes(self):
        self.assertEqual(
            build_queue({}, self.LESSONS, NOW).new, build_queue({}, self.LESSONS, NOW, articles={}).new
        )

    def test_words_held_back_for_level_are_not_started_but_a_started_one_stays_scheduled(self):
        hold = {("vocab_item", 102), ("vocab_item", 201)}
        started = {("vocab_item", 102): Schedule(reps=1, introduced_at=NOW - 3 * DAY, due_at=NOW - DAY)}
        q = build_queue(started, {}, NOW, articles=self.ARTICLES, hold=hold, new_limit=8)
        self.assertEqual(q.due, vocab(102))
        self.assertEqual(q.new, vocab(101, 103, 202))
        self.assertEqual(q.article_waiting, 3)

    def test_the_level_cap_follows_the_goal(self):
        self.assertEqual(srs.article_level_cap("topik1"), 2)
        self.assertEqual(srs.article_level_cap("topik4"), 4)
        self.assertEqual(srs.article_level_cap("topik6"), 6)
        self.assertEqual(srs.article_level_cap(None), srs.DEFAULT_ARTICLE_LEVEL_CAP)
        self.assertEqual(srs.article_level_cap("something else"), srs.DEFAULT_ARTICLE_LEVEL_CAP)


class HardAnswerTests(unittest.TestCase):
    """"Chưa chắc": right, but a guess or slow."""

    def test_a_hard_answer_gains_no_strength_drops_ease_and_grows_the_gap_by_a_fifth(self):
        prev = Schedule(strength=0.6, reps=3, lapses=1, ease=2.2, interval_days=10, due_at=NOW, introduced_at=NOW - 20 * DAY)
        s = review(prev, True, NOW, hard=True)
        self.assertAlmostEqual(s.strength, 0.6)
        self.assertAlmostEqual(s.ease, 2.05)
        self.assertEqual(s.interval_days, 12.0)
        self.assertEqual(s.due_at, NOW + 12 * DAY)
        self.assertEqual((s.reps, s.lapses), (3, 1))  # the run of right answers is not extended
        self.assertEqual(s.introduced_at, NOW - 20 * DAY)

    def test_a_hard_first_answer_comes_back_tomorrow_without_counting_a_rep(self):
        s = review(None, True, NOW, hard=True)
        self.assertEqual((s.reps, s.interval_days, s.strength), (0, 1.0, 0.0))
        self.assertEqual(s.due_at, NOW + DAY)
        self.assertEqual(s.introduced_at, NOW)

    def test_ease_never_drops_below_the_floor_and_the_gap_is_capped(self):
        s = review(Schedule(ease=srs.MIN_EASE + 0.05, interval_days=170, reps=8, due_at=NOW), True, NOW, hard=True)
        self.assertEqual(s.ease, srs.MIN_EASE)
        self.assertEqual(s.interval_days, srs.MAX_INTERVAL_DAYS)

    def test_hard_means_nothing_on_a_wrong_answer(self):
        prev = Schedule(reps=2, interval_days=3, due_at=NOW, strength=0.4)
        self.assertEqual(review(prev, False, NOW, hard=True), review(prev, False, NOW))

    def test_a_hard_answer_before_it_is_due_changes_nothing(self):
        prev = Schedule(reps=2, interval_days=3, ease=2.2, due_at=NOW + 3 * DAY, strength=0.4)
        s = review(prev, True, NOW, hard=True)
        self.assertEqual((s.due_at, s.ease, s.strength), (prev.due_at, 2.2, 0.4))

    def test_a_slow_answer_counts_as_hard(self):
        self.assertTrue(srs.is_hard(True))
        self.assertTrue(srs.is_hard(False, srs.SLOW_ANSWER_MS + 1))
        self.assertFalse(srs.is_hard(False, srs.SLOW_ANSWER_MS))
        self.assertFalse(srs.is_hard(False, None))


class KnownTests(unittest.TestCase):
    """"Đã biết": a card the learner already knows stays out of the queue."""

    LESSONS = {1: vocab(1, 2, 3, 4, 5, 6) + grammar(1, 2)}

    def test_a_known_card_is_never_offered_as_new_nor_as_due(self):
        schedules = {
            ("vocab_item", 1): Schedule(known=True),
            ("vocab_item", 2): Schedule(known=True, reps=2, due_at=NOW - DAY, introduced_at=NOW - 5 * DAY),
        }
        q = build_queue(schedules, self.LESSONS, NOW)
        self.assertEqual(q.due, [])
        self.assertNotIn(("vocab_item", 1), q.new)
        self.assertNotIn(("vocab_item", 2), q.new)

    def test_a_known_card_does_not_use_up_the_days_new_cards(self):
        schedules = {("vocab_item", 1): Schedule(known=True, introduced_at=NOW - timedelta(hours=1))}
        q = build_queue(schedules, self.LESSONS, NOW)
        self.assertEqual((q.new_today, q.new_budget), (0, 8))
        self.assertEqual(len(q.new), 7)  # everything else in the lesson

    def test_a_known_card_is_neither_a_leech_nor_weak(self):
        s = Schedule(known=True, lapses=3, reps=0, due_at=NOW)
        self.assertFalse(srs.is_due(s, NOW))
        self.assertFalse(srs.is_leech(s))
        self.assertEqual(srs.weak_keys({("vocab_item", 1): s}, {("vocab_item", 1)}), [])

    def test_undoing_it_brings_the_card_back(self):
        schedules = {("vocab_item", 2): Schedule(reps=2, due_at=NOW - DAY, introduced_at=NOW - 5 * DAY)}
        self.assertEqual(build_queue(schedules, self.LESSONS, NOW).due, vocab(2))

    def test_only_a_row_made_by_the_mark_alone_is_removed_on_undo(self):
        self.assertTrue(srs.only_marked_known(Schedule(known=True)))
        self.assertFalse(srs.only_marked_known(Schedule(known=True, reps=1, introduced_at=NOW)))
        self.assertFalse(srs.only_marked_known(Schedule(known=True, lapses=1)))


class ReviewOnlyDayTests(unittest.TestCase):
    def test_on_a_review_only_day_there_are_no_new_cards(self):
        today = NOW.date()
        self.assertEqual(srs.new_limit_for(8, today, today), 0)
        self.assertEqual(srs.new_limit_for(8, today - DAY, today), 8)  # yesterday's choice is over
        self.assertEqual(srs.new_limit_for(8, None, today), 8)
        q = build_queue({}, {1: vocab(1, 2)}, NOW, new_limit=srs.new_limit_for(8, today, today))
        self.assertEqual((q.new, q.new_budget), ([], 0))


if __name__ == "__main__":
    unittest.main()

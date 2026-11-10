"""The daily reading and dialogue: the draw (app.services.daily_reading), its database side
(app.services.daily_reading_db) and the endpoints (app.api.routers.daily) — against mocked sessions,
plus the real text bank read through the real lessons."""
import dataclasses
import unittest
import uuid
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace
from unittest import mock

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from app.api.routers import content
from app.api.routers import daily as router
from app.models import ReadingLog
from app.schemas import DailyFinishIn
from app.services import daily_reading as dr
from app.services import daily_reading_db as store
from app.services import lesson_seed as seed
from app.services import passages
from app.services.daily_reading import Card

NOW = datetime(2026, 10, 9, 12, 0, tzinfo=timezone.utc)  # 21:00 on 9 Oct in Seoul
TODAY = date(2026, 10, 9)
LEARNER = uuid.UUID("12345678-1234-5678-1234-567812345678")
BUNDLE = seed.load_all()
BANK = {p.id: p for p in passages.all_passages()}


# ------------------------------------------------------------- the real lessons --
def real_context() -> store.Context:
    """The seeded lessons as the database would hold them: a made-up id per card."""
    ctx = store.Context()
    n = 0
    for r in BUNDLE.lessons:
        slug = r.seed.slug
        ctx.lesson_ids[slug] = r.seed.sort_order
        for g in r.seed.grammar:
            n += 1
            ctx.grammar_index[(slug, g.pattern)] = n
            ctx.grammar_info[n] = (g.pattern, g.meaning_vi, r.seed.sort_order)
        for v in r.seed.vocab:
            n += 1
            ctx.vocab_index[(slug, v.hangul)] = n
            ctx.vocab_info[n] = (v.hangul, v.meaning_vi, r.seed.sort_order)
    ctx.slugs = sorted(ctx.lesson_ids)
    return ctx


CTX = real_context()


def met_lessons(*slugs, strength=0.5, due=False) -> dict:
    """The study records of a learner who has met every grammar card and word of these lessons."""
    cards = {}
    for (slug, _), gid in CTX.grammar_index.items():
        if slug in slugs:
            cards[("grammar_point", gid)] = Card(strength, due)
    for (slug, _), vid in CTX.vocab_index.items():
        if slug in slugs:
            cards[("vocab_item", vid)] = Card(strength, due)
    return cards


def pool_for(cards) -> list[dr.Candidate]:
    return dr.candidates(passages.all_passages(), CTX.slugs, CTX.grammar_index, CTX.vocab_index, cards)


# -------------------------------------------------------------- tiny test fixtures --
def make_passage(pid="x-01-d1", kind="dialogue", patterns=("P1",), words=("w1",)):
    return passages.Passage(
        id=pid,
        lesson="x-01-test",
        kind=kind,
        title_ko="제목",
        title_vi="Tiêu đề",
        scene_vi="Cảnh" if kind == "dialogue" else None,
        speakers={"F": "A", "M": "B"} if kind == "dialogue" else {},
        lines=tuple(
            passages.Line(who=who, ko="안녕하세요", vi="Xin chào")
            for who in (("F", "M", "F", "M", "F", "M") if kind == "dialogue" else ("N",) * 4)
        ),
        uses=tuple(passages.Use(pattern=p, regex=".") for p in patterns),
        keywords=tuple(passages.Keyword(word=w, seen=w) for w in words),
        glossary=(passages.Gloss(ko="단어", vi="từ"),),
        questions=(
            passages.Question(q_vi="Q1?", options=["a", "b", "c"], answer=1, explain_vi="vì b"),
            passages.Question(q_vi="Q2?", options=["a", "b", "c"], answer=2, explain_vi="vì c"),
        ),
    )


G = {("x-01-test", "P1"): 1, ("x-01-test", "P2"): 2}
V = {("x-01-test", "w1"): 11, ("x-01-test", "w2"): 12}
SLUGS = ["x-01-test"]


def refs_of(p):
    return dr.resolve(p, SLUGS, G, V)


# ================================================================ the rules ==
class NeedTests(unittest.TestCase):
    def test_a_weak_card_needs_more_than_a_strong_one_and_a_due_card_more_still(self):
        self.assertGreater(dr.need(Card(0.2, False)), dr.need(Card(0.9, False)))
        self.assertAlmostEqual(dr.need(Card(0.2, True)) - dr.need(Card(0.2, False)), dr.DUE_BONUS)

    def test_strength_is_clamped(self):
        self.assertEqual(dr.need(Card(-3, False)), 1.0)
        self.assertEqual(dr.need(Card(5, False)), 0.0)


class UnlockTests(unittest.TestCase):
    def test_a_text_opens_only_when_every_card_it_is_built_on_has_been_met(self):
        p = make_passage(patterns=("P1", "P2"))
        refs = refs_of(p)
        self.assertFalse(dr.unlocked(refs, {}))
        self.assertFalse(dr.unlocked(refs, {("grammar_point", 1): Card(0.5, False)}))
        both = {("grammar_point", 1): Card(0.5, False), ("grammar_point", 2): Card(0.1, False)}
        self.assertTrue(dr.unlocked(refs, both))

    def test_words_do_not_keep_a_text_shut(self):
        p = make_passage()
        self.assertTrue(dr.unlocked(refs_of(p), {("grammar_point", 1): Card(0.5, False)}))

    def test_a_pattern_that_is_not_in_the_database_keeps_the_text_shut(self):
        p = make_passage(patterns=("P1", "NOT-SEEDED"))
        self.assertEqual(refs_of(p).grammar[1], ())
        self.assertFalse(dr.unlocked(refs_of(p), {("grammar_point", 1): Card(0.5, False)}))
        self.assertIsNone(dr.score(refs_of(p), {("grammar_point", 1): Card(0.5, False)}))


class ScoreTests(unittest.TestCase):
    def test_weaker_cards_give_a_higher_score(self):
        refs = refs_of(make_passage())
        weak = dr.score(refs, {("grammar_point", 1): Card(0.1, False)})
        strong = dr.score(refs, {("grammar_point", 1): Card(0.95, False)})
        self.assertGreater(weak, strong)

    def test_a_due_card_raises_the_score(self):
        refs = refs_of(make_passage())
        self.assertGreater(
            dr.score(refs, {("grammar_point", 1): Card(0.6, True)}),
            dr.score(refs, {("grammar_point", 1): Card(0.6, False)}),
        )

    def test_the_words_the_learner_has_met_count_and_the_others_do_not(self):
        refs = refs_of(make_passage(words=("w1", "w2")))
        g = {("grammar_point", 1): Card(0.5, False)}
        grammar_only = dr.score(refs, g)
        with_weak_word = dr.score(refs, {**g, ("vocab_item", 11): Card(0.0, False)})
        with_strong_word = dr.score(refs, {**g, ("vocab_item", 11): Card(1.0, False)})
        self.assertGreater(with_weak_word, grammar_only)
        self.assertLess(with_strong_word, grammar_only)
        # w2 was never met: it is listed as new, not scored
        self.assertEqual(dr.new_words(refs, make_passage(words=("w1", "w2")), {**g, ("vocab_item", 11): Card(0.5, False)}), ["w2"])

    def test_a_card_that_sits_in_two_lessons_counts_by_its_better_remembered_copy(self):
        p = dataclasses.replace(make_passage(), lesson="x-02-test")
        g = {("x-01-test", "P1"): 1, ("x-02-test", "P1"): 5}
        refs = dr.resolve(p, ["x-01-test", "x-02-test"], g, V)
        self.assertEqual(len(refs.grammar[0]), 2)
        cards = {("grammar_point", 1): Card(0.1, False), ("grammar_point", 5): Card(0.9, False)}
        self.assertAlmostEqual(dr.score(refs, cards), dr.need(Card(0.9, False)))


class WeightTests(unittest.TestCase):
    def test_a_text_offered_lately_is_less_likely_than_one_not_offered_for_a_while(self):
        self.assertLess(dr.weight(0.5, 1), dr.weight(0.5, 7))
        self.assertLess(dr.weight(0.5, 7), dr.weight(0.5, 14))
        self.assertEqual(dr.weight(0.5, 14), dr.weight(0.5, 100))
        self.assertEqual(dr.weight(0.5, None), dr.weight(0.5, 14))

    def test_a_recent_text_still_has_a_chance_and_a_strong_card_does_too(self):
        self.assertGreater(dr.weight(0.0, 1), 0)
        self.assertGreater(dr.weight(0.0, None), 0)

    def test_a_weaker_card_pulls_clearly(self):
        self.assertGreater(dr.weight(1.0, None), 3 * dr.weight(0.3, None))


class PickTests(unittest.TestCase):
    def pool(self, *scores):
        out = []
        for i, sc in enumerate(scores):
            p = make_passage(pid=f"x-01-d{i + 1}")
            out.append(dr.Candidate(p, refs_of(p), sc))
        return out

    def test_the_same_inputs_give_the_same_text(self):
        pool = self.pool(0.5, 0.6, 0.7, 0.8)
        a = dr.pick(pool, LEARNER, TODAY, "dialogue", {})
        b = dr.pick(list(reversed(pool)), LEARNER, TODAY, "dialogue", {})  # database order does not matter
        self.assertEqual(a.passage.id, b.passage.id)

    def test_other_days_and_other_learners_draw_again(self):
        pool = self.pool(0.7, 0.7, 0.7, 0.7, 0.7, 0.7)
        days = {dr.pick(pool, LEARNER, TODAY + timedelta(days=i), "dialogue", {}).passage.id for i in range(30)}
        self.assertGreater(len(days), 3)
        people = {dr.pick(pool, uuid.UUID(int=i), TODAY, "dialogue", {}).passage.id for i in range(30)}
        self.assertGreater(len(people), 3)

    def test_it_only_picks_the_kind_asked_for(self):
        d = make_passage(pid="x-01-d1", kind="dialogue")
        r = make_passage(pid="x-01-r1", kind="reading")
        pool = [dr.Candidate(d, refs_of(d), 0.5), dr.Candidate(r, refs_of(r), 0.5)]
        self.assertEqual(dr.pick(pool, LEARNER, TODAY, "reading", {}).passage.id, "x-01-r1")
        self.assertIsNone(dr.pick([pool[0]], LEARNER, TODAY, "reading", {}))
        self.assertIsNone(dr.pick([], LEARNER, TODAY, "dialogue", {}))

    def test_the_day_gets_a_dialogue_then_a_reading_whichever_are_open(self):
        d = make_passage(pid="x-01-d1", kind="dialogue")
        r = make_passage(pid="x-01-r1", kind="reading")
        pool = [dr.Candidate(r, refs_of(r), 0.5), dr.Candidate(d, refs_of(d), 0.5)]
        self.assertEqual([c.passage.kind for c in dr.pick_day(pool, LEARNER, TODAY, {})], ["dialogue", "reading"])
        self.assertEqual([c.passage.kind for c in dr.pick_day(pool[:1], LEARNER, TODAY, {})], ["reading"])
        self.assertEqual(dr.pick_day([], LEARNER, TODAY, {}), [])

    def test_over_many_days_the_text_on_weaker_cards_comes_up_more_often(self):
        pool = self.pool(1.3, 0.1)
        counts = Counter(
            dr.pick(pool, LEARNER, TODAY + timedelta(days=i), "dialogue", {}).passage.id for i in range(300)
        )
        self.assertGreater(counts["x-01-d1"], 4 * counts["x-01-d2"])
        self.assertGreater(counts["x-01-d2"], 0)

    def test_a_text_seen_in_the_last_days_is_not_offered_again_while_another_is_open(self):
        pool = self.pool(0.7, 0.7, 0.7)
        for i in range(120):
            day = TODAY + timedelta(days=i)
            for ago in (1, 2):
                picked = dr.pick(pool, LEARNER, day, "dialogue", {"x-01-d1": day - timedelta(days=ago)})
                self.assertNotEqual(picked.passage.id, "x-01-d1")
        # three days on it may come back
        back = {
            dr.pick(pool, LEARNER, TODAY + timedelta(days=i), "dialogue", {"x-01-d1": TODAY + timedelta(days=i - 3)}).passage.id
            for i in range(60)
        }
        self.assertIn("x-01-d1", back)

    def test_a_learner_with_a_single_text_still_gets_it(self):
        pool = self.pool(0.7)
        self.assertEqual(dr.pick(pool, LEARNER, TODAY, "dialogue", {"x-01-d1": TODAY - timedelta(days=1)}).passage.id, "x-01-d1")

    def test_among_texts_all_seen_lately_the_least_recent_is_not_forced_but_all_stay_possible(self):
        pool = self.pool(0.7, 0.7)
        offered = {"x-01-d1": TODAY - timedelta(days=1), "x-01-d2": TODAY - timedelta(days=2)}
        counts = Counter(
            dr.pick(pool, uuid.UUID(int=i), TODAY, "dialogue", offered).passage.id for i in range(200)
        )
        self.assertGreater(counts["x-01-d2"], counts["x-01-d1"])
        self.assertGreater(counts["x-01-d1"], 0)


class DayTests(unittest.TestCase):
    def test_the_learners_day_is_the_calendar_day_in_seoul(self):
        late_utc = datetime(2026, 10, 9, 16, 0, tzinfo=timezone.utc)  # already 10 Oct in Seoul
        self.assertEqual(dr.local_day(late_utc, "Asia/Seoul"), date(2026, 10, 10))
        self.assertEqual(dr.local_day(late_utc, "UTC"), date(2026, 10, 9))

    def test_an_unknown_zone_does_not_crash(self):
        self.assertEqual(dr.local_day(NOW, "Not/AZone"), date(2026, 10, 9))

    def test_seoul_works_without_a_tz_database(self):
        with mock.patch.object(dr, "ZoneInfo", side_effect=dr.ZoneInfoNotFoundError("x")):
            self.assertEqual(dr.local_day(datetime(2026, 10, 9, 16, 0, tzinfo=timezone.utc), "Asia/Seoul"), date(2026, 10, 10))

    def test_a_naive_time_is_read_as_utc(self):
        self.assertEqual(dr.local_day(datetime(2026, 10, 9, 16, 0), "Asia/Seoul"), date(2026, 10, 10))


class GradeTests(unittest.TestCase):
    def test_right_wrong_blank_and_out_of_range(self):
        p = make_passage()
        graded = dr.grade(p, [1, 0])
        self.assertEqual([g.is_right for g in graded], [True, False])
        self.assertEqual([g.correct for g in graded], [1, 2])
        self.assertEqual([g.is_right for g in dr.grade(p, [None, 2])], [False, True])
        odd = dr.grade(p, [9, -1])
        self.assertEqual([(g.answer, g.is_right) for g in odd], [(None, False), (None, False)])

    def test_the_number_of_answers_must_match(self):
        with self.assertRaises(ValueError):
            dr.grade(make_passage(), [1])


class WhyTests(unittest.TestCase):
    def test_it_names_the_weakest_cards_and_says_when_one_is_due(self):
        p = make_passage(patterns=("P1", "P2"))
        cards = {("grammar_point", 1): Card(0.9, False), ("grammar_point", 2): Card(0.2, True)}
        why = dr.why_vi(p, refs_of(p), cards)
        self.assertIn("sắp quên: P2", why)
        self.assertNotIn("(", why)
        self.assertLess(why.index("P2"), why.index("P1"))

    def test_without_cards_there_is_still_a_line(self):
        p = make_passage()
        self.assertTrue(dr.why_vi(p, refs_of(p), {}))


# ======================================================== the real text bank ==
class RealBankTests(unittest.TestCase):
    def test_every_card_every_text_is_built_on_is_found_in_the_lessons(self):
        for p in passages.all_passages():
            refs = dr.resolve(p, CTX.slugs, CTX.grammar_index, CTX.vocab_index)
            self.assertTrue(all(refs.grammar), f"{p.id}: a grammar card is missing from the lessons")
            self.assertTrue(all(refs.words), f"{p.id}: a key word is missing from the lessons")

    def test_a_new_learner_is_offered_nothing(self):
        self.assertEqual(pool_for({}), [])

    def test_a_learner_who_has_only_met_the_first_lesson_is_offered_only_its_texts(self):
        first = "sinh-hoat-01-buoi-sang"
        pool = pool_for(met_lessons(first))
        self.assertEqual({c.passage.id for c in pool}, {"sinh-hoat-01-d1", "sinh-hoat-01-r1"})

    def test_a_text_opens_exactly_when_all_its_cards_have_been_met(self):
        studied = {"sinh-hoat-01-buoi-sang", "sinh-hoat-02-viec-nha", "sinh-hoat-03-an-uong"}
        known = {pattern for (slug, pattern) in CTX.grammar_index if slug in studied}
        pool = {c.passage.id for c in pool_for(met_lessons(*studied))}
        for p in passages.all_passages():
            expected = all(u.pattern in known for u in p.uses) and p.lesson in studied
            if p.lesson not in studied:
                # a text of a lesson not yet met needs a card of that lesson, which is not known
                expected = False
            self.assertEqual(p.id in pool, expected, p.id)
        self.assertEqual(len(pool), 6)

    def test_having_met_the_whole_first_topic_opens_it_and_nothing_of_the_next_ones(self):
        topic_one = [r.seed.slug for r in BUNDLE.lessons if r.seed.slug.startswith("sinh-hoat")]
        pool = pool_for(met_lessons(*topic_one))
        self.assertEqual(len(pool), 28)  # fourteen lessons (five foundation + nine topic lessons), two texts each
        self.assertTrue(all(c.passage.lesson.startswith("sinh-hoat") for c in pool))

    def test_a_learner_of_the_whole_first_topic_is_offered_variety_over_a_month(self):
        topic_one = [r.seed.slug for r in BUNDLE.lessons if r.seed.slug.startswith("sinh-hoat")]
        pool = pool_for(met_lessons(*topic_one))
        offered: dict[str, date] = {}
        seen: dict[str, list[str]] = {"dialogue": [], "reading": []}
        for i in range(30):
            day = TODAY + timedelta(days=i)
            for c in dr.pick_day(pool, LEARNER, day, offered):
                seen[c.passage.kind].append(c.passage.id)
                offered[c.passage.id] = day
        for kind, ids in seen.items():
            self.assertEqual(len(ids), 30)
            self.assertGreaterEqual(len(set(ids)), 7, f"{kind}: {Counter(ids)}")  # 9 of each exist
            for a, b in zip(ids, ids[1:]):
                self.assertNotEqual(a, b, f"{kind}: the same text two days running")

    def test_a_text_on_cards_the_learner_is_forgetting_is_offered_more_than_one_on_solid_cards(self):
        a, b = "sinh-hoat-01-buoi-sang", "sinh-hoat-02-viec-nha"
        weak = met_lessons(a, strength=0.1, due=True)
        strong = met_lessons(b, strength=0.95)
        pool = pool_for({**weak, **strong})
        counts = Counter(
            dr.pick(pool, LEARNER, TODAY + timedelta(days=i), "dialogue", {}).passage.id for i in range(300)
        )
        self.assertGreater(counts["sinh-hoat-01-d1"], 3 * counts["sinh-hoat-02-d1"])


# ================================================================ the database ==
def result(*, scalars=None, rows=None):
    res = mock.MagicMock()
    if scalars is not None:
        res.scalars.return_value.all.return_value = scalars
    if rows is not None:
        res.all.return_value = rows
    return res


def log(pid, kind, *, finished=False, correct=None, total=None, minute=0):
    return SimpleNamespace(
        learner_id=LEARNER,
        day=TODAY,
        passage_id=pid,
        kind=kind,
        picked_at=NOW + timedelta(minutes=minute),
        finished_at=NOW if finished else None,
        correct=correct,
        total=total,
    )


def db_with(*executes):
    db = mock.MagicMock()
    db.execute = mock.AsyncMock(side_effect=list(executes))
    db.add_all = mock.MagicMock()
    db.commit = mock.AsyncMock()
    db.rollback = mock.AsyncMock()
    return db


FIRST = "sinh-hoat-01-buoi-sang"
CARDS = met_lessons(FIRST, strength=0.4)


class SittingTests(unittest.IsolatedAsyncioTestCase):
    async def test_the_first_look_of_the_day_draws_two_texts_and_writes_them_to_the_log(self):
        db = db_with(result(scalars=[]), result(rows=[]))
        s = await store.sitting(db, LEARNER, CARDS, CTX, NOW, persist=True)
        self.assertEqual(s.day, TODAY)
        self.assertEqual([p.passage.id for p in s.picks], ["sinh-hoat-01-d1", "sinh-hoat-01-r1"])
        (added,) = [c.args[0] for c in db.add_all.call_args_list]
        self.assertEqual([(a.learner_id, a.day, a.passage_id, a.kind) for a in added],
                         [(LEARNER, TODAY, "sinh-hoat-01-d1", "dialogue"), (LEARNER, TODAY, "sinh-hoat-01-r1", "reading")])
        db.commit.assert_awaited_once()
        self.assertTrue(s.written)

    async def test_later_looks_that_day_return_the_same_two_without_drawing(self):
        rows = [log("sinh-hoat-01-r1", "reading", minute=1), log("sinh-hoat-01-d1", "dialogue", minute=0)]
        db = db_with(result(scalars=rows))
        s = await store.sitting(db, LEARNER, {}, CTX, NOW, persist=True)  # even if the cards changed
        self.assertEqual([p.passage.id for p in s.picks], ["sinh-hoat-01-d1", "sinh-hoat-01-r1"])
        db.add_all.assert_not_called()
        db.commit.assert_not_awaited()
        self.assertEqual(db.execute.await_count, 1)

    async def test_a_text_that_left_the_bank_is_skipped(self):
        db = db_with(result(scalars=[log("gone-99-d1", "dialogue"), log("sinh-hoat-01-r1", "reading")]))
        s = await store.sitting(db, LEARNER, CARDS, CTX, NOW, persist=True)
        self.assertEqual([p.passage.id for p in s.picks], ["sinh-hoat-01-r1"])

    async def test_a_preview_writes_nothing(self):
        db = db_with(result(scalars=[]), result(rows=[]))
        s = await store.sitting(db, LEARNER, CARDS, CTX, NOW, persist=False)
        self.assertEqual(len(s.picks), 2)
        self.assertTrue(all(p.log is None for p in s.picks))
        db.add_all.assert_not_called()
        db.commit.assert_not_awaited()

    async def test_nothing_to_offer_when_no_text_is_open(self):
        db = db_with(result(scalars=[]))
        s = await store.sitting(db, LEARNER, {}, CTX, NOW, persist=True)
        self.assertEqual(s.picks, [])
        db.add_all.assert_not_called()

    async def test_a_text_offered_in_the_past_is_taken_into_account(self):
        yesterday = TODAY - timedelta(days=1)
        db = db_with(result(scalars=[]), result(rows=[("sinh-hoat-01-d1", yesterday)]))
        s = await store.sitting(db, LEARNER, CARDS, CTX, NOW, persist=False)
        self.assertEqual(len(s.picks), 2)  # only these two are open, so they are offered anyway

    async def test_two_screens_opened_at_once_end_up_with_one_pair(self):
        winner = [log("sinh-hoat-01-d1", "dialogue"), log("sinh-hoat-01-r1", "reading")]
        db = db_with(result(scalars=[]), result(rows=[]), result(scalars=winner))
        db.commit = mock.AsyncMock(side_effect=IntegrityError("insert", {}, Exception("duplicate")))
        s = await store.sitting(db, LEARNER, CARDS, CTX, NOW, persist=True)
        db.rollback.assert_awaited_once()
        self.assertEqual([p.passage.id for p in s.picks], ["sinh-hoat-01-d1", "sinh-hoat-01-r1"])

    async def test_a_day_never_shows_two_texts_of_one_kind(self):
        rows = [log("sinh-hoat-01-d1", "dialogue", minute=0), log("sinh-hoat-02-d1", "dialogue", minute=1)]
        db = db_with(result(scalars=rows))
        s = await store.sitting(db, LEARNER, CARDS, CTX, NOW, persist=True)
        self.assertEqual([p.passage.id for p in s.picks], ["sinh-hoat-01-d1"])

    async def test_the_day_turns_at_midnight_in_seoul(self):
        late = datetime(2026, 10, 9, 16, 0, tzinfo=timezone.utc)
        db = db_with(result(scalars=[]), result(rows=[]))
        s = await store.sitting(db, LEARNER, CARDS, CTX, late, persist=True)
        self.assertEqual(s.day, date(2026, 10, 10))
        self.assertTrue(all(a.day == date(2026, 10, 10) for a in db.add_all.call_args.args[0]))


class CardsTests(unittest.TestCase):
    def test_due_comes_from_the_schedule(self):
        def state(item_id, due_at):
            return SimpleNamespace(
                item_type="grammar_point", item_id=item_id, strength=0.5, reps=1, lapses=0, ease=2.2,
                interval_days=1.0, due_at=due_at, introduced_at=NOW - timedelta(days=3),
            )

        cards = store.cards_of([state(1, NOW - timedelta(hours=1)), state(2, NOW + timedelta(days=2))], NOW)
        self.assertTrue(cards[("grammar_point", 1)].due)
        self.assertFalse(cards[("grammar_point", 2)].due)


class OutputTests(unittest.TestCase):
    def pick_of(self, pid, log_=None):
        p = BANK[pid]
        return store.Pick(p, dr.resolve(p, CTX.slugs, CTX.grammar_index, CTX.vocab_index), log_)

    def test_a_dialogue_is_sent_line_by_line_with_names_and_voices(self):
        out = store.passage_out(self.pick_of("sinh-hoat-01-d1"), CTX, CARDS)
        self.assertEqual(out.kind, "dialogue")
        self.assertEqual(out.speakers, {"F": "수진", "M": "민수"})
        self.assertEqual([line.voice for line in out.lines[:2]], ["ko-female-1", "ko-male-1"])
        self.assertEqual([line.speaker for line in out.lines[:2]], ["수진", "민수"])
        self.assertEqual(out.status, "todo")

    def test_a_reading_has_one_voice_and_the_whole_text(self):
        out = store.passage_out(self.pick_of("sinh-hoat-01-r1"), CTX, CARDS)
        self.assertEqual({line.voice for line in out.lines}, {"ko-female-1"})
        self.assertTrue(all(line.speaker is None for line in out.lines))
        self.assertEqual(out.text_ko, BANK["sinh-hoat-01-r1"].text_ko)
        self.assertEqual(out.voice, "ko-female-1")

    def test_the_answers_are_not_sent(self):
        dumped = store.passage_out(self.pick_of("sinh-hoat-01-d1"), CTX, CARDS).model_dump_json()
        self.assertNotIn("explain", dumped)
        self.assertNotIn('"answer"', dumped)
        self.assertNotIn('"correct"', dumped.replace('"correct":null', ""))

    def test_the_cards_link_to_the_lessons_and_known_words_are_marked(self):
        out = store.passage_out(self.pick_of("sinh-hoat-01-d1"), CTX, CARDS)
        self.assertTrue(all(g.grammar_id is not None and g.lesson_id is not None and g.meaning_vi for g in out.grammar))
        self.assertTrue(all(w.vocab_item_id is not None and w.meaning_vi for w in out.words))
        self.assertTrue(all(w.known for w in out.words))  # CARDS has the words of lesson 1
        unknown = store.passage_out(self.pick_of("sinh-hoat-01-d1"), CTX, {k: v for k, v in CARDS.items() if k[0] == "grammar_point"})
        self.assertFalse(any(w.known for w in unknown.words))

    def test_a_finished_text_reports_its_score(self):
        done = log("sinh-hoat-01-d1", "dialogue", finished=True, correct=1, total=2)
        out = store.passage_out(self.pick_of("sinh-hoat-01-d1", done), CTX, CARDS)
        self.assertEqual((out.status, out.correct, out.total), ("done", 1, 2))

    def test_an_empty_day_says_why(self):
        out = store.reading_out(store.Sitting(TODAY, [], False), [])
        self.assertEqual((out.total, out.done), (0, 0))
        self.assertIn("Bài học", out.note_vi)


class FinishTests(unittest.IsolatedAsyncioTestCase):
    def logs(self, **over):
        return [log("sinh-hoat-01-d1", "dialogue", **over), log("sinh-hoat-01-r1", "reading", minute=1)]

    async def test_the_first_submission_is_graded_and_kept(self):
        rows = self.logs()
        db = db_with(result(scalars=rows))
        answers = [BANK["sinh-hoat-01-d1"].questions[0].answer, 99]
        out = await store.finish(db, LEARNER, "sinh-hoat-01-d1", answers, NOW)
        self.assertEqual((out.correct, out.total), (1, 2))
        self.assertTrue(out.answers[0].is_right and not out.answers[1].is_right)
        self.assertTrue(out.answers[0].explain_vi)
        self.assertEqual((rows[0].correct, rows[0].total), (1, 2))
        self.assertIsNotNone(rows[0].finished_at)
        db.commit.assert_awaited_once()
        self.assertEqual((out.done, out.day_total), (1, 2))

    async def test_a_second_submission_is_graded_again_but_changes_nothing(self):
        rows = self.logs(finished=True, correct=2, total=2)
        db = db_with(result(scalars=rows))
        out = await store.finish(db, LEARNER, "sinh-hoat-01-d1", [None, None], NOW)
        self.assertEqual(out.correct, 0)
        self.assertEqual(rows[0].correct, 2)  # the first one stands
        db.commit.assert_not_awaited()

    async def test_finishing_both_completes_the_day(self):
        rows = [log("sinh-hoat-01-d1", "dialogue", finished=True, correct=2, total=2), log("sinh-hoat-01-r1", "reading", minute=1)]
        db = db_with(result(scalars=rows))
        out = await store.finish(db, LEARNER, "sinh-hoat-01-r1", [0, 0], NOW)
        self.assertEqual((out.done, out.day_total), (2, 2))

    async def test_a_text_that_is_not_one_of_todays_cannot_be_finished(self):
        db = db_with(result(scalars=self.logs()))
        with self.assertRaises(store.NotToday):
            await store.finish(db, LEARNER, "sinh-hoat-02-d1", [0, 0], NOW)
        db.commit.assert_not_awaited()

    async def test_an_unknown_text_cannot_be_finished(self):
        db = db_with()
        with self.assertRaises(store.NotToday):
            await store.finish(db, LEARNER, "nope", [0], NOW)

    async def test_the_wrong_number_of_answers_is_refused_and_nothing_is_kept(self):
        rows = self.logs()
        db = db_with(result(scalars=rows))
        with self.assertRaises(ValueError):
            await store.finish(db, LEARNER, "sinh-hoat-01-d1", [0], NOW)
        self.assertIsNone(rows[0].finished_at)
        db.commit.assert_not_awaited()


# =============================================================== the endpoints ==
class EndpointTests(unittest.IsolatedAsyncioTestCase):
    async def test_the_screen_returns_the_days_texts(self):
        sitting = store.Sitting(
            TODAY,
            [store.Pick(BANK["sinh-hoat-01-d1"], dr.resolve(BANK["sinh-hoat-01-d1"], CTX.slugs, CTX.grammar_index, CTX.vocab_index), None)],
            True,
        )
        profile = SimpleNamespace(id=LEARNER)
        with mock.patch.object(router, "_states", mock.AsyncMock(return_value=[])), \
             mock.patch.object(store, "load_context", mock.AsyncMock(return_value=CTX)), \
             mock.patch.object(store, "sitting", mock.AsyncMock(return_value=sitting)) as drawn:
            out = await router.get_daily_reading(mock.MagicMock(), profile)
        self.assertEqual((out.day, out.total, out.done), (TODAY, 1, 0))
        self.assertEqual(out.items[0].id, "sinh-hoat-01-d1")
        self.assertTrue(drawn.call_args.kwargs["persist"])
        self.assertIsNone(out.note_vi)

    async def test_finish_maps_the_errors(self):
        profile = SimpleNamespace(id=LEARNER)
        body = DailyFinishIn(answers=[0, 0])
        with mock.patch.object(store, "finish", mock.AsyncMock(side_effect=store.NotToday("x"))):
            with self.assertRaises(HTTPException) as ctx:
                await router.finish_daily_reading("x", body, mock.MagicMock(), profile)
        self.assertEqual(ctx.exception.status_code, 404)
        with mock.patch.object(store, "finish", mock.AsyncMock(side_effect=ValueError("2 answers wanted, got 1"))):
            with self.assertRaises(HTTPException) as ctx:
                await router.finish_daily_reading("x", body, mock.MagicMock(), profile)
        self.assertEqual(ctx.exception.status_code, 422)

    def test_too_many_answers_are_refused_by_the_schema(self):
        with self.assertRaises(ValueError):
            DailyFinishIn(answers=[0] * 7)


class PlanTaskTests(unittest.IsolatedAsyncioTestCase):
    def pick(self, pid, *, finished=False):
        p = BANK[pid]
        row = log(pid, p.kind, finished=finished, correct=1 if finished else None, total=2 if finished else None)
        return store.Pick(p, dr.resolve(p, CTX.slugs, CTX.grammar_index, CTX.vocab_index), row)

    async def task(self, picks, *, has_cards=True):
        sitting = store.Sitting(TODAY, picks, True)
        cards = CARDS if has_cards else {}
        with mock.patch.object(store, "cards_of", return_value=cards), \
             mock.patch.object(store, "load_context", mock.AsyncMock(return_value=CTX)), \
             mock.patch.object(store, "sitting", mock.AsyncMock(return_value=sitting)) as drawn:
            task = await content._daily_reading_task(mock.MagicMock(), LEARNER, [SimpleNamespace()], NOW)
        return task, drawn

    async def test_no_study_record_no_task(self):
        task, drawn = await self.task([], has_cards=False)
        self.assertIsNone(task)
        drawn.assert_not_awaited()

    async def test_no_open_text_no_task(self):
        task, _ = await self.task([])
        self.assertIsNone(task)

    async def test_the_task_reads_the_picks_without_writing(self):
        task, drawn = await self.task([self.pick("sinh-hoat-01-d1"), self.pick("sinh-hoat-01-r1")])
        self.assertEqual((task.kind, task.status), ("daily_reading", "todo"))
        self.assertIn("1 hội thoại + 1 bài đọc", task.subtitle)
        self.assertFalse(drawn.call_args.kwargs["persist"])

    async def test_the_status_follows_the_texts_answered(self):
        half, _ = await self.task([self.pick("sinh-hoat-01-d1", finished=True), self.pick("sinh-hoat-01-r1")])
        self.assertEqual(half.status, "in_progress")
        full, _ = await self.task([self.pick("sinh-hoat-01-d1", finished=True), self.pick("sinh-hoat-01-r1", finished=True)])
        self.assertEqual(full.status, "done")


class ModelTests(unittest.TestCase):
    def test_a_learner_is_offered_a_text_once_a_day(self):
        names = {c.name for c in ReadingLog.__table__.constraints}
        self.assertIn("uq_reading_log_learner_day_text", names)


if __name__ == "__main__":
    unittest.main()

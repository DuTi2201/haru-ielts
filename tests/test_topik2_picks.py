"""“Thử sức TOPIK II”: a lesson names a few real exam questions that suit it. The seed holds only
the picks (an id and why it fits); the questions and their primers are served by the real-exam
routes, behind login, never by the public practice route."""
import asyncio
import unittest
import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest import mock

from pydantic import ValidationError

from app.schemas import LessonPracticeOut
from app.services import lesson_seed as seed
from app.services import real_exam as rx
from app.services import real_exam_db as store

BUNDLE = seed.load_all()
BANK = rx.load()
LESSONS = [r for r in BUNDLE.lessons if r.seed.kind == "lesson"]
WHY = "Cảnh quen thuộc trong bài, có mẫu câu bạn đã học và vài từ mới được giải thích trước."


def pick(qid="96-L-1", why=WHY):
    return {"qid": qid, "why_vi": why}


def lesson_with(**extra):
    """The first seeded lesson, with different picks."""
    data = next(r for r in LESSONS).seed.model_dump(mode="json")
    data.update(extra)
    return seed.LessonSeed.model_validate(data)


class PickModelTests(unittest.TestCase):
    def test_a_lesson_may_name_up_to_three_questions(self):
        self.assertEqual(len(lesson_with(topik2=[pick("96-L-1"), pick("96-L-2"), pick("102-R-1")]).topik2), 3)
        with self.assertRaises(ValidationError):
            lesson_with(topik2=[pick("96-L-1"), pick("96-L-2"), pick("102-R-1"), pick("96-R-2")])

    def test_one_question_is_named_once(self):
        with self.assertRaises(ValidationError):
            lesson_with(topik2=[pick("96-L-1"), pick("96-L-1")])

    def test_only_a_listening_or_reading_id_is_accepted(self):
        for bad in ("96-W-52", "96L1", "96-L-", "TOPIK-96-L-1", ""):
            with self.assertRaises(ValidationError, msg=bad):
                lesson_with(topik2=[pick(bad)])
        lesson_with(topik2=[pick("h1-L-10")])

    def test_the_reason_is_a_sentence_not_a_label(self):
        with self.assertRaises(ValidationError):
            lesson_with(topik2=[pick(why="Hợp bài")])
        with self.assertRaises(ValidationError):
            lesson_with(topik2=[pick(why="x" * 241)])

    def test_a_review_lesson_has_no_picks(self):
        review = next(r for r in BUNDLE.lessons if r.seed.kind == "review").seed.model_dump(mode="json")
        review["topik2"] = [pick()]
        with self.assertRaises(ValidationError):
            seed.LessonSeed.model_validate(review)


class SeededPickTests(unittest.TestCase):
    def picks(self):
        return [(r.seed.slug, p.qid) for r in LESSONS for p in r.seed.topik2]

    def test_the_pilot_covers_a_handful_of_lessons(self):
        with_picks = [r for r in LESSONS if r.seed.topik2 and not r.seed.slug.startswith(("cong-so-", "xa-hoi-"))]
        self.assertTrue(8 <= len(with_picks) <= 14, len(with_picks))
        self.assertTrue(all(1 <= len(r.seed.topik2) <= 2 for r in with_picks))

    def test_every_practice_lesson_of_topic_four_offers_three(self):
        # the course aimed at 4급 puts real exam questions in front of the learner in every lesson
        t4 = [r for r in LESSONS if r.seed.slug.startswith("cong-so-")]
        self.assertEqual(len(t4), 7)
        for r in t4:
            self.assertEqual(len(r.seed.topik2), 3, r.seed.slug)

    def test_every_practice_lesson_of_topic_five_offers_three(self):
        # topic 5 (aimed at 5-6급) also puts real exam questions in front of the learner in every practice lesson
        t5 = [r for r in LESSONS if r.seed.slug.startswith("xa-hoi-") and r.seed.kind != "review"]
        self.assertGreaterEqual(len(t5), 6)
        for r in t5:
            self.assertEqual(len(r.seed.topik2), 3, r.seed.slug)

    def test_every_pick_is_in_the_bank_easy_enough_and_has_a_primer(self):
        self.assertEqual(rx.check_picks(self.picks(), BANK), [])

    def test_only_the_course_aimed_at_4_may_offer_the_hardest_tier(self):
        hard = "102-R-48"  # a tier-3 reading question
        self.assertEqual(BANK.items[hard].tier, 3)
        self.assertEqual(rx.check_picks([("cong-so-01-tuyen-dung-hop-dong", hard)], BANK), [])
        self.assertEqual(len(rx.check_picks([("quan-he-02-dien-thoai-hen", hard)], BANK)), 1)

    def test_a_question_is_offered_by_one_lesson_only(self):
        qids = [q for _slug, q in self.picks()]
        self.assertEqual(len(qids), len(set(qids)))

    def test_the_practice_keeps_only_the_picks_and_the_public_route_never_sends_them(self):
        for r in LESSONS:
            held = (r.practice or {}).get("topik2")
            self.assertEqual(held, [p.model_dump(mode="json") for p in r.seed.topik2] or None, r.seed.slug)
            for p in held or []:
                self.assertEqual(set(p), {"qid", "why_vi"})
        # the practice route is public: it must have no field that could carry the exam text
        self.assertNotIn("topik2", LessonPracticeOut.model_fields)

    def test_a_picks_reason_does_not_give_the_answer_away(self):
        for r in LESSONS:
            for p in r.seed.topik2:
                it = BANK.items[p.qid]
                if it.seed.opts:
                    right = it.seed.opts[it.seed.ans - 1]
                    self.assertNotIn(right, p.why_vi, p.qid)


class PrimerTests(unittest.TestCase):
    def test_a_primer_is_short_and_words_and_forms_are_told_apart(self):
        for qid, it in BANK.items.items():
            if not it.is_mcq:
                continue
            words, forms = rx.primer_of(it)
            self.assertLessEqual(len(words), rx.PRIMER_WORDS, qid)
            self.assertLessEqual(len(forms), rx.PRIMER_FORMS, qid)
            self.assertTrue(all(ko[:1] not in "-~" for ko, _vi in words), qid)

    def test_a_form_listed_among_the_words_is_a_form_not_a_word(self):
        words, forms = rx.primer_of(BANK.items["96-L-1"])  # its gloss lists `-아/어 봐도 되다` with the words
        self.assertEqual([k for k, _ in words], ["수박", "접시", "드시다"])
        self.assertIn("-아/어 봐도 되다", [k for k, _ in forms])

    def test_a_form_the_grammar_already_has_is_not_listed_twice(self):
        for it in BANK.items.values():
            if not it.is_mcq:
                continue
            _words, forms = rx.primer_of(it, max_forms=99)
            cores = [frozenset(rx.pattern_cores(k)) for k, _ in forms]
            self.assertEqual(len(cores), len({c for c in cores if c}) + sum(1 for c in cores if not c), it.qid)


NOW = datetime(2026, 10, 10, 9, 0, tzinfo=timezone.utc)


class FakeDB:
    def __init__(self, lesson, attempts=()):
        self.lesson, self.attempts = lesson, list(attempts)

    async def get(self, _model, pk):
        return self.lesson if self.lesson is not None and pk == 7 else None

    async def execute(self, _stmt):
        res = mock.MagicMock()
        res.scalars.return_value.all.return_value = self.attempts
        return res


def attempt(qid, right, hints=0, ago=timedelta(hours=1)):
    return SimpleNamespace(qid=qid, right=right, hints=hints, created_at=NOW - ago)


class LessonPicksTests(unittest.IsolatedAsyncioTestCase):
    def lesson(self, picks):
        return SimpleNamespace(practice={"topik2": picks})

    async def test_each_pick_carries_its_reason_a_primer_and_where_the_learner_stands(self):
        db = FakeDB(self.lesson([pick("96-L-1"), pick("102-R-3", "Câu nói về khả năng trễ hẹn nếu không xuất phát ngay.")]),
                    [attempt("96-L-1", True, ago=timedelta(days=9))])
        out = await store.lesson_picks(db, SimpleNamespace(id=uuid.uuid4()), 7, NOW)
        first, second = out.picks
        self.assertEqual((first.qid, first.exam, first.sec, first.n, first.tier), ("96-L-1", "topik-96", "L", 1, 1))
        self.assertEqual(first.why_vi, WHY)
        self.assertEqual([w.ko for w in first.words], ["수박", "접시", "드시다"])
        self.assertTrue(first.forms)
        self.assertEqual((first.status, first.resting), ("solid", False))  # solid, but its week of rest is over
        self.assertEqual((second.status, second.resting), ("new", False))

    async def test_a_question_answered_a_moment_ago_is_resting(self):
        db = FakeDB(self.lesson([pick("96-L-1")]), [attempt("96-L-1", True, ago=timedelta(hours=2))])
        out = await store.lesson_picks(db, SimpleNamespace(id=uuid.uuid4()), 7, NOW)
        self.assertEqual((out.picks[0].status, out.picks[0].resting), ("solid", True))

    async def test_nothing_of_the_question_or_its_answer_is_in_the_reply(self):
        db = FakeDB(self.lesson([pick("102-R-3")]))
        out = await store.lesson_picks(db, SimpleNamespace(id=uuid.uuid4()), 7, NOW)
        dumped = out.model_dump_json()
        for secret in ("늦을 수도 있다", "늦는 셈이다", "지금 출발하지 않으면"):
            self.assertNotIn(secret, dumped)

    async def test_a_lesson_without_picks_or_with_a_stale_id_gives_an_empty_list(self):
        db = FakeDB(self.lesson([pick("999-L-1")]))
        self.assertEqual((await store.lesson_picks(db, SimpleNamespace(id=uuid.uuid4()), 7, NOW)).picks, [])
        db = FakeDB(SimpleNamespace(practice=None))
        self.assertEqual((await store.lesson_picks(db, SimpleNamespace(id=uuid.uuid4()), 7, NOW)).picks, [])

    async def test_an_unknown_lesson_is_not_found(self):
        with self.assertRaises(store.NotFound):
            await store.lesson_picks(FakeDB(None), SimpleNamespace(id=uuid.uuid4()), 7, NOW)


if __name__ == "__main__":
    unittest.main()

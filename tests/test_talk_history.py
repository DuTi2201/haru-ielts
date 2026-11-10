"""History of talks with Haru (app.services.talk_history, app.api.routers.conversation_history)."""
import unittest
import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest import mock

from fastapi import HTTPException

from app.api.routers import conversation_history as router
from app.models import ItemState, TalkNote
from app.schemas import TalkNoteUpdate
from app.services import talk_history as th

NOW = datetime(2026, 10, 27, 15, 0, tzinfo=timezone.utc)
ME = uuid.uuid4()


def session(i=0, **kw):
    base = dict(
        id=uuid.uuid4(), learner_id=ME, lesson_id=36, started_at=NOW - timedelta(days=i), ended_at=NOW - timedelta(days=i),
        seconds=300, band=2, metrics={"learner_turns": 6, "band_after": 2, "ko_words_per_turn": 4.0}, saved_at=None,
        turns=[{"role": "haru", "text": "안녕"}, {"role": "learner", "text": "안녕하세요"}],
        report={"summary_vi": "s", "praise_vi": "Tốt!", "fixes": [{"said": "학교 가요", "better": "학교에 가요", "why_vi": "Cần 에."}],
                "words": [{"ko": "출근하다", "vi": "đi làm"}], "next_time_vi": "", "learner_facts": [], "topics_vi": ["đi làm"]},
        pronunciation={"average": 70.0, "overall_vi": "", "items": [
            {"index": 1, "heard_en": "", "target_en": "저는 일곱 시에 일어나요", "score": 55, "good_vi": "",
             "issues": [{"word": "일곱", "heard_as": "일고", "kind": "batchim", "problem_vi": "x", "tip_vi": "Giữ ㅂ cuối."}]}]},
    )
    base.update(kw)
    return SimpleNamespace(**base)


class PureTests(unittest.TestCase):
    def test_summary_row(self):
        r = th.summary_row(session(), "Bài 6")
        self.assertEqual((r["lesson_title"], r["pron_avg"], r["headline_vi"], r["learner_turns"], r["saved"]), ("Bài 6", 70.0, "Tốt!", 6, False))
        bare = th.summary_row(session(report=None, pronunciation=None, metrics=None), None)
        self.assertEqual((bare["has_report"], bare["pron_avg"], bare["learner_turns"]), (False, None, 1))

    def test_insights_counts_recurring_kinds_per_session_and_repeat_words(self):
        rows = [
            session(0, pronunciation={"average": 80.0, "items": [{"issues": [
                {"word": "일곱", "kind": "batchim"}, {"word": "있어요", "kind": "batchim"}, {"word": "써요", "kind": "consonant"}]}]}),
            session(1),
            session(2, pronunciation=None, report={"words": [{"ko": "출근하다", "vi": "đi làm"}]}),
            session(3, ended_at=None),  # never finished: left out
        ]
        out = th.insights(rows)
        self.assertEqual(out["sessions"], 3)
        self.assertEqual([p["pron_avg"] for p in out["points"]], [None, 70.0, 80.0])  # oldest first
        self.assertEqual((out["pron_first"], out["pron_last"], out["checked_sessions"]), (70.0, 80.0, 2))
        self.assertEqual(out["issue_kinds"][0]["kind"], "batchim")
        self.assertEqual(out["issue_kinds"][0]["sessions"], 2)  # per session, not per word
        self.assertEqual(out["issue_kinds"][0]["words"], ["일곱", "있어요"])
        self.assertEqual(out["repeat_words"], [{"ko": "출근하다", "vi": "đi làm", "times": 3}])

    def test_notes_keep_only_suggested_words_and_corrected_sentences(self):
        notes = th.notes_from_report(session().report)
        self.assertEqual([(n["kind"], n["ko"]) for n in notes], [("word", "출근하다"), ("sentence", "학교에 가요")])
        # never the learner's own wording: not the "said" side, not a fix that changes nothing
        same = th.notes_from_report({"fixes": [{"said": "저는 학생이에요", "better": "저는 학생이에요", "why_vi": ""}]})
        self.assertEqual(same, [])
        self.assertEqual(len(th.notes_from_report({"words": [{"ko": "a"}, {"ko": "a"}]})), 1)

    def test_a_saved_word_is_linked_to_its_card_lesson_card_first(self):
        cards = [
            (40, "출근하다", None),  # a news article's card
            (12, "출근하다", 36),  # the lesson card
            (7, "출근하다", 52),  # an older lesson card
            (3, "회의", None),  # only an article has it
            (5, "퇴근", 36),  # not asked for
        ]
        self.assertEqual(th.cards_for_words([" 출근하다", "회의", "없는말", ""], cards), {"출근하다": 7, "회의": 3})
        self.assertEqual(th.cards_for_words([], cards), {})
        self.assertEqual(th.cards_for_words(["없는말"], cards), {})  # no card: no review, nothing made up

class R:
    def __init__(self, v):
        self.v = v

    def scalars(self):
        return self

    def all(self):
        return self.v

    def __iter__(self):
        return iter(self.v)


def db_with(*answers):
    db = mock.MagicMock()
    db.execute = mock.AsyncMock(side_effect=list(answers))
    db.get = mock.AsyncMock()
    db.add = mock.MagicMock()
    db.delete = mock.AsyncMock()
    db.commit = mock.AsyncMock()
    return db


ME_PROFILE = SimpleNamespace(id=ME)


class RouteTests(unittest.IsolatedAsyncioTestCase):
    async def test_list_with_lesson_titles(self):
        db = db_with(R([session(0), session(1, lesson_id=None)]), R([(36, "Bài 6")]))
        out = await router.list_sessions(db, ME_PROFILE, limit=30, before=None)
        self.assertEqual([r["lesson_title"] for r in out], ["Bài 6", None])

    async def test_detail_and_someone_elses(self):
        row = session()
        db = db_with(R([(36, "Bài 6")]))
        db.get.return_value = row
        out = await router.get_session(row.id, db, ME_PROFILE)
        self.assertEqual(out.pronunciation.items[0].issues[0].kind, "batchim")
        self.assertEqual(len(out.turns), 2)
        db.get.return_value = session(learner_id=uuid.uuid4())
        with self.assertRaises(HTTPException) as cm:
            await router.get_session(row.id, db, ME_PROFILE)
        self.assertEqual(cm.exception.status_code, 404)

    async def test_save_puts_cards_in_review_and_notes_in_the_book(self):
        row = session()
        old_state = SimpleNamespace(item_id=9, due_at=NOW + timedelta(days=5))
        reopened = SimpleNamespace(kind="sentence", ko="학교에 가요", done_at=NOW, vi="", vocab_item_id=None, id=uuid.uuid4(), created_at=NOW)
        db = db_with(
            R([(9, "출근하다", 36)]),  # the word is a lesson card
            R([old_state]),  # with a state, due later
            R([reopened]),  # notes already there
            R([reopened]),  # notes after saving
        )
        db.get.return_value = row
        out = await router.save_to_review(row.id, db, ME_PROFILE)
        self.assertEqual(out.added_to_review, ["출근하다"])
        self.assertLessEqual(old_state.due_at, datetime.now(timezone.utc))  # due now
        self.assertIsNone(reopened.done_at)  # came back: open again
        added = [a.args[0] for a in db.add.call_args_list]
        self.assertEqual(sorted((a.kind, a.ko) for a in added if isinstance(a, TalkNote)), [("word", "출근하다")])
        word = next(a for a in added if isinstance(a, TalkNote) and a.kind == "word")
        self.assertEqual(word.vocab_item_id, 9)
        self.assertEqual(out.notes_added, 1)  # the corrected sentence was already there (reopened)
        self.assertIsNotNone(row.saved_at)

    async def test_save_new_card_gets_a_state(self):
        row = session(report={"words": [{"ko": "출근하다", "vi": "đi làm"}]}, pronunciation=None)
        db = db_with(R([(9, "출근하다", 36)]), R([]), R([]), R([]))
        db.get.return_value = row
        await router.save_to_review(row.id, db, ME_PROFILE)
        state = next(a.args[0] for a in db.add.call_args_list if isinstance(a.args[0], ItemState))
        self.assertEqual((state.item_id, state.strength, state.reps), (9, 0.0, 0))
        self.assertIsNotNone(state.due_at)

    async def test_save_links_a_word_saved_before_it_had_a_card(self):
        row = session(report={"words": [{"ko": "출근하다", "vi": "đi làm"}]}, pronunciation=None)
        unlinked = SimpleNamespace(kind="word", ko="출근하다", done_at=NOW, vi="", vocab_item_id=None, id=uuid.uuid4(), created_at=NOW)
        known = SimpleNamespace(item_id=40, due_at=NOW + timedelta(days=30), known_at=NOW)
        db = db_with(R([(40, "출근하다", None)]), R([known]), R([unlinked]), R([unlinked]))
        db.get.return_value = row
        out = await router.save_to_review(row.id, db, ME_PROFILE)
        self.assertEqual(unlinked.vocab_item_id, 40)  # an article card is used when no lesson has the word
        self.assertIsNone(known.known_at)  # met again in a talk: back in review
        self.assertLessEqual(known.due_at, datetime.now(timezone.utc))
        self.assertEqual((out.added_to_review, out.notes_added), (["출근하다"], 0))

    async def test_save_without_report_is_409(self):
        db = db_with()
        db.get.return_value = session(report=None)
        with self.assertRaises(HTTPException) as cm:
            await router.save_to_review(uuid.uuid4(), db, ME_PROFILE)
        self.assertEqual(cm.exception.status_code, 409)

    async def test_notes_tick_and_delete(self):
        note = SimpleNamespace(id=uuid.uuid4(), learner_id=ME, kind="word", ko="출근하다", vi="đi làm", vocab_item_id=9, done_at=None, created_at=NOW)
        db = db_with()
        db.get.return_value = note
        out = await router.update_note(note.id, TalkNoteUpdate(done=True), db, ME_PROFILE)
        self.assertTrue(out.done and out.in_review)
        await router.delete_note(note.id, db, ME_PROFILE)
        db.delete.assert_awaited_once_with(note)
        db.get.return_value = SimpleNamespace(learner_id=uuid.uuid4())
        with self.assertRaises(HTTPException):
            await router.delete_note(note.id, db, ME_PROFILE)

    async def test_insights_route(self):
        db = db_with(R([session(0), session(1)]))
        out = await router.get_insights(db, ME_PROFILE)
        self.assertEqual(out["sessions"], 2)


class BackfillTests(unittest.IsolatedAsyncioTestCase):
    async def test_unlinked_words_get_their_card_and_a_review_state(self):
        from app.services import talk_notes_db

        other = uuid.uuid4()
        open_note = SimpleNamespace(learner_id=ME, kind="word", ko="출근하다", vocab_item_id=None, done_at=None)
        done_note = SimpleNamespace(learner_id=other, kind="word", ko="회의", vocab_item_id=None, done_at=NOW)
        no_card = SimpleNamespace(learner_id=ME, kind="word", ko="없는말", vocab_item_id=None, done_at=None)
        db = db_with(
            R([open_note, done_note, no_card]),  # the unlinked words
            R([(9, "출근하다", 36), (3, "회의", None)]),  # their cards
            R([]),  # ME has no state for card 9 yet
        )
        n = await talk_notes_db.backfill_note_cards(db, now=NOW)
        self.assertEqual(n, 2)
        self.assertEqual((open_note.vocab_item_id, done_note.vocab_item_id, no_card.vocab_item_id), (9, 3, None))
        (state,) = [a.args[0] for a in db.add.call_args_list]  # the ticked-off word is not pushed back
        self.assertEqual((state.learner_id, state.item_id, state.due_at), (ME, 9, NOW))
        self.assertIsNone(state.introduced_at)  # does not use up today's new cards
        db.commit.assert_awaited_once()

    async def test_a_backfill_leaves_a_card_already_being_studied_alone(self):
        from app.services import talk_notes_db

        note = SimpleNamespace(learner_id=ME, kind="word", ko="출근하다", vocab_item_id=None, done_at=None)
        studied = SimpleNamespace(item_id=9, due_at=NOW + timedelta(days=9), known_at=None)
        db = db_with(R([note]), R([(9, "출근하다", 36)]), R([studied]))
        await talk_notes_db.backfill_note_cards(db, now=NOW)
        self.assertEqual((note.vocab_item_id, studied.due_at), (9, NOW + timedelta(days=9)))
        db.add.assert_not_called()

    async def test_nothing_to_link_is_a_no_op(self):
        from app.services import talk_notes_db

        db = db_with(R([]))
        self.assertEqual(await talk_notes_db.backfill_note_cards(db, now=NOW), 0)
        db.commit.assert_not_called()


if __name__ == "__main__":
    unittest.main()

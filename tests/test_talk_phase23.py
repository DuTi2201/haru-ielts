"""Trò chuyện với Haru, phases 2-3: the conversation band and memory (app.services.talk_profile),
the pronunciation check (app.services.pronunciation) and their routes, against mocked sessions."""
import base64
import io
import json
import struct
import unittest
import uuid
import wave
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest import mock

from fastapi import HTTPException

from app.api.routers import conversation as router
from app.models import LearnerTalkProfile
from app.schemas import ConversationFinishRequest, PronunciationRequest
from app.services import conversation as c
from app.services import conversation_db, gemini_client, pronunciation as pron, talk_profile as tp

NOW = datetime(2026, 10, 27, 12, 0, tzinfo=timezone.utc)


def wav(seconds: float, rate: int = 16000, channels: int = 1, width: int = 2) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(channels)
        w.setsampwidth(width)
        w.setframerate(rate)
        w.writeframes(b"\x00" * int(seconds * rate) * width * channels)
    return buf.getvalue()


def learner(*texts):
    """A real transcript: Haru and the learner take turns."""
    out = []
    for t in texts:
        out += [{"role": "haru", "text": "그래요?"}, {"role": "learner", "text": t}]
    return out


# ------------------------------------------------------------------------------ band --
class BandTests(unittest.TestCase):
    def test_initial_band_follows_the_lesson_level(self):
        self.assertEqual([tp.initial_band(l) for l in (None, 1, 2, 3, 4, 5, 6)], [1, 1, 2, 3, 3, 4, 4])

    def test_measure(self):
        m = tp.measure(learner("저는 일곱 시에 일어나요", "아침에 빵을 먹어요", "Tôi không biết nói sao"), 120, 3)
        self.assertEqual(m.learner_turns, 3)
        self.assertAlmostEqual(m.ko_words_per_turn, 7 / 3)
        self.assertAlmostEqual(m.vi_share, 1 / 3)
        self.assertAlmostEqual(m.nudges_per_min, 1.5)

    def test_mostly_vietnamese(self):
        self.assertTrue(tp.mostly_vietnamese("Tôi dậy lúc bảy giờ"))
        self.assertFalse(tp.mostly_vietnamese("저는 bảy 시에 일어나요"))
        self.assertFalse(tp.mostly_vietnamese("..."))

    def test_verdicts(self):
        easy = tp.TalkMetrics(6, 6.0, 0.0, 0.2)
        hard = tp.TalkMetrics(6, 1.0, 0.6, 2.0)
        ok = tp.TalkMetrics(6, 3.0, 0.1, 0.8)
        self.assertEqual(tp.verdict(easy, 2), 1)
        self.assertEqual(tp.verdict(hard, 2), -1)
        self.assertEqual(tp.verdict(hard, 1), 0)  # nowhere lower to go
        self.assertEqual(tp.verdict(ok, 2), 0)
        self.assertIsNone(tp.verdict(tp.TalkMetrics(2, 9.0, 0.0, 0.0), 2))  # too short to judge
        self.assertEqual(tp.verdict(tp.TalkMetrics(6, 9.0, 0.0, 0.0), 5), 0)  # top band: no "easy"
        self.assertEqual(tp.verdict(tp.TalkMetrics(6, 6.0, 0.0, 0.2, pron_avg=40), 2), -1)  # unclear speech

    def test_band_moves_only_on_two_agreeing_verdicts(self):
        self.assertEqual(tp.next_band(2, [1]), 2)
        self.assertEqual(tp.next_band(2, [1, 1]), 3)
        self.assertEqual(tp.next_band(2, [1, -1]), 2)
        self.assertEqual(tp.next_band(2, [-1, -1]), 1)
        self.assertEqual(tp.next_band(1, [-1, -1]), 1)
        self.assertEqual(tp.next_band(5, [1, 1]), 5)
        self.assertEqual(tp.next_band(3, [0, 0]), 3)
        self.assertEqual(len(tp.push_verdict(list(range(10)), 1)), tp.KEEP_VERDICTS)

    def test_change_notes(self):
        self.assertIn("mức 3/5", tp.band_change_note(2, 3))
        self.assertIn("chậm và dễ hơn", tp.band_change_note(3, 2))
        self.assertIsNone(tp.band_change_note(2, 2))

    def test_band_goes_into_the_instruction(self):
        ctx = c.LearnerContext(name=None, goal=None, level=2, topic=None, current=None, band=4,
                               last_topics=["giờ thức dậy"], follow_up="Kể về buổi tối.")
        text = c.build_system_instruction(ctx)
        self.assertIn("MỨC TRÒ CHUYỆN 4/5", text)
        self.assertIn("giờ thức dậy", text)
        self.assertIn("Kể về buổi tối.", text)
        self.assertNotIn("MỨC TRÒ CHUYỆN", c.build_system_instruction(
            c.LearnerContext(name=None, goal=None, level=2, topic=None, current=None)))

    def test_facts_newest_first_dated_and_capped(self):
        facts = tp.add_facts([{"text": "Thích cầu lông", "at": "2026-10-01"}], ["thích cầu lông", "Có con 3 tuổi"], "2026-10-27")
        self.assertEqual(facts, [{"text": "thích cầu lông", "at": "2026-10-27"}, {"text": "Có con 3 tuổi", "at": "2026-10-27"}])
        self.assertEqual(len(tp.add_facts([], [f"f{i}" for i in range(30)], "d")), tp.MAX_FACTS)


# ----------------------------------------------------------------------- pronunciation --
class WavTests(unittest.TestCase):
    def test_accepts_16k_mono_pcm(self):
        self.assertAlmostEqual(pron.wav_seconds(wav(2.5)), 2.5)

    def test_rejects_other_formats(self):
        for bad in (b"nope" * 20, wav(1, rate=48000), wav(1, channels=2), wav(1, width=1)):
            with self.assertRaises(pron.ClipError):
                pron.wav_seconds(bad)

    def test_limits(self):
        ok = pron.Clip(0, "", b"", 3.0)
        pron.check_clips([ok])
        for bad in ([], [ok] * 6, [pron.Clip(1, "", b"", 0.2)], [pron.Clip(1, "", b"", 20.0)], [pron.Clip(i, "", b"", 14.0) for i in range(5)]):
            with self.assertRaises(pron.ClipError):
                pron.check_clips(bad)


class PronParseTests(unittest.TestCase):
    clips = [pron.Clip(3, "저는 학생이에요", b"", 2.0), pron.Clip(7, "커피 좋아해요", b"", 2.0)]

    def test_prompt_lists_clips_in_order(self):
        p = pron.build_prompt(self.clips, "Trình độ: sơ cấp")
        self.assertIn("Câu 3: audio thứ 1", p)
        self.assertIn("Câu 7: audio thứ 2", p)
        self.assertIn("받침", p)

    def test_parse_matches_by_index_bounds_and_averages(self):
        out = pron.parse(
            json.dumps(
                {
                    "items": [
                        {"index": 7, "heard_ko": "커피 조아해요", "target_ko": "커피를 좋아해요", "score": 140,
                         "issues": [{"word": "좋아해요", "heard_as": "조아해요", "problem_vi": "x", "tip_vi": "y"}] * 5, "good_vi": "tốt"},
                        {"index": 3, "heard_ko": "", "target_ko": "저는 학생이에요", "score": 60, "issues": [], "good_vi": ""},
                        {"index": 99, "score": 10},
                        {"index": "x", "score": 10},
                    ],
                    "overall_vi": "Khá rõ.",
                }
            ),
            self.clips,
        )
        self.assertEqual([i["index"] for i in out["items"]], [3, 7])  # clip order
        self.assertEqual(out["items"][1]["score"], 100)
        self.assertEqual(len(out["items"][1]["issues"]), 3)
        self.assertEqual(out["items"][0]["heard_ko"], "저는 학생이에요")  # falls back to the live transcript
        self.assertEqual(out["average"], 80.0)

    def test_parse_garbage(self):
        self.assertEqual(pron.parse("oops", self.clips), {"items": [], "overall_vi": "", "average": None})


# ------------------------------------------------------------------------------ routes --
def profile():
    return SimpleNamespace(id=uuid.uuid4(), display_name="Dương", goal="talk")


def fake_db():
    db = mock.MagicMock()
    db.add = mock.MagicMock()
    db.commit = mock.AsyncMock()
    db.get = mock.AsyncMock()
    return db


def ctx(level=2, band=None):
    return c.LearnerContext(name="D", goal=None, level=level, topic=None, current=None, band=band)


class FinishBandTests(unittest.IsolatedAsyncioTestCase):
    def row(self, p, **kw):
        base = dict(id=uuid.uuid4(), learner_id=p.id, ended_at=None, report=None, remember=True, seconds=0,
                    nudges=0, turns=None, band=2, metrics=None, pronunciation=None)
        base.update(kw)
        return SimpleNamespace(**base)

    async def finish(self, talk, turns, nudges=0, seconds=180, report=None):
        p = profile()
        db = fake_db()
        row = self.row(p)
        db.get.return_value = row
        report = report or {"summary_vi": "s", "praise_vi": "p", "fixes": [], "words": [], "next_time_vi": "Kể về bữa tối.",
                            "learner_facts": ["Thích cà phê"], "topics_vi": ["bữa sáng"]}
        with mock.patch.object(conversation_db, "get_talk_profile", mock.AsyncMock(return_value=talk)), mock.patch.object(
            conversation_db, "load_context", mock.AsyncMock(return_value=ctx())
        ), mock.patch.object(gemini_client, "generate_structured", return_value={"text": json.dumps(report)}):
            out = await router.finish_conversation(
                row.id, ConversationFinishRequest(seconds=seconds, nudges=nudges, turns=turns), db, p
            )
        return out, row, db

    async def test_second_easy_session_moves_the_band_up_and_keeps_memory(self):
        talk = SimpleNamespace(band=2, verdicts=[{"s": "old", "v": 1}], facts=[{"text": "Có con nhỏ", "at": "2026-10-20"}],
                               last_topics=[], follow_up=None, sessions=4)
        turns = learner("저는 아침에 커피를 마시고 빵을 먹어요", "회사에 지하철로 가요 정말 멀어요", "주말에는 친구를 만나서 영화를 봐요",
                        "저는 한국 음식을 정말 좋아해요 특히 김치")
        out, row, _ = await self.finish(talk, turns)
        self.assertEqual((out.band_before, out.band_after), (2, 3))
        self.assertIn("mức 3/5", out.band_note_vi)
        self.assertEqual(talk.band, 3)
        self.assertEqual(talk.sessions, 5)
        self.assertEqual(talk.last_topics, ["bữa sáng"])
        self.assertEqual(talk.follow_up, "Kể về bữa tối.")
        self.assertEqual(talk.facts[0]["text"], "Thích cà phê")
        self.assertEqual(len(talk.facts), 2)
        self.assertEqual(row.metrics["verdict"], 1)
        self.assertEqual(talk.verdicts[-1]["s"], str(row.id))

    async def test_a_new_learner_gets_a_profile_row(self):
        out, row, db = await self.finish(None, learner("네", "아니요", "몰라요"), nudges=6)
        added = [a.args[0] for a in db.add.call_args_list]
        self.assertTrue(any(isinstance(a, LearnerTalkProfile) for a in added))
        self.assertEqual(out.band_after, 2)  # one hard session alone does not move it
        self.assertEqual(row.metrics["verdict"], -1)

    async def test_too_short_gives_no_verdict(self):
        talk = SimpleNamespace(band=3, verdicts=[{"s": "a", "v": -1}], facts=[], last_topics=[], follow_up=None, sessions=1)
        out, row, _ = await self.finish(talk, learner("안녕하세요"))
        self.assertEqual(talk.verdicts, [{"s": "a", "v": -1}])
        self.assertIsNone(row.metrics["verdict"])
        self.assertEqual(out.band_after, 3)


class PronunciationRouteTests(unittest.IsolatedAsyncioTestCase):
    def req(self, *secs):
        return PronunciationRequest(clips=[{"index": i, "heard": "저는 학생이에요", "wav_b64": base64.b64encode(wav(s)).decode()}
                                           for i, s in enumerate(secs)])

    async def test_checks_and_stores_without_audio(self):
        p = profile()
        db = fake_db()
        row = SimpleNamespace(id=uuid.uuid4(), learner_id=p.id, pronunciation=None, metrics=None)
        db.get.return_value = row
        answer = {"items": [{"index": 0, "heard_ko": "저는 학생이에요", "target_ko": "저는 학생이에요", "score": 82, "issues": [], "good_vi": "Rõ."}],
                  "overall_vi": "Tốt."}
        with mock.patch.object(conversation_db, "load_context", mock.AsyncMock(return_value=ctx())), mock.patch.object(
            conversation_db, "get_talk_profile", mock.AsyncMock(return_value=None)
        ), mock.patch.object(gemini_client, "generate_structured", return_value={"text": json.dumps(answer)}) as gen:
            out = await router.check_pronunciation(row.id, self.req(2.0), db, p)
        self.assertEqual(out.average, 82.0)
        parts = gen.call_args.kwargs["prompt"]
        self.assertEqual(len(parts), 2)  # one audio part + the instructions
        self.assertIsInstance(parts[-1], str)
        self.assertNotIn("wav", json.dumps(row.pronunciation))  # only the result is kept

    async def test_bad_audio_is_422(self):
        p = profile()
        db = fake_db()
        db.get.return_value = SimpleNamespace(id=uuid.uuid4(), learner_id=p.id, pronunciation=None, metrics=None)
        with self.assertRaises(HTTPException) as cm:
            await router.check_pronunciation(uuid.uuid4(), self.req(0.2), db, p)
        self.assertEqual(cm.exception.status_code, 422)
        bad = PronunciationRequest(clips=[{"index": 0, "wav_b64": "%%%"}])
        with self.assertRaises(HTTPException):
            await router.check_pronunciation(uuid.uuid4(), bad, db, p)

    async def test_once_per_session(self):
        p = profile()
        db = fake_db()
        stored = {"items": [], "overall_vi": "x", "average": None}
        db.get.return_value = SimpleNamespace(id=uuid.uuid4(), learner_id=p.id, pronunciation=stored, metrics=None)
        with mock.patch.object(gemini_client, "generate_structured") as gen:
            out = await router.check_pronunciation(uuid.uuid4(), self.req(2.0), db, p)
        gen.assert_not_called()
        self.assertEqual(out.overall_vi, "x")

    async def test_unclear_speech_rejudges_the_latest_session(self):
        p = profile()
        db = fake_db()
        row = SimpleNamespace(
            id=uuid.uuid4(), learner_id=p.id, pronunciation=None,
            metrics={"learner_turns": 5, "ko_words_per_turn": 6.0, "vi_share": 0.0, "nudges_per_min": 0.2,
                     "verdict": 1, "band_before": 2, "band_after": 3},
        )
        db.get.return_value = row
        talk = SimpleNamespace(band=3, verdicts=[{"s": "a", "v": 1}, {"s": str(row.id), "v": 1}])
        answer = {"items": [{"index": 0, "heard_ko": "..", "target_ko": "..", "score": 30, "issues": [], "good_vi": ""}], "overall_vi": ""}
        with mock.patch.object(conversation_db, "load_context", mock.AsyncMock(return_value=ctx())), mock.patch.object(
            conversation_db, "get_talk_profile", mock.AsyncMock(return_value=talk)
        ), mock.patch.object(gemini_client, "generate_structured", return_value={"text": json.dumps(answer)}):
            await router.check_pronunciation(row.id, self.req(2.0), db, p)
        self.assertEqual(talk.verdicts[-1]["v"], -1)
        self.assertEqual(talk.band, 2)  # the step up is taken back
        self.assertEqual(row.metrics["pron_avg"], 30.0)


class MemoryRouteTests(unittest.IsolatedAsyncioTestCase):
    async def test_profile_and_forgetting(self):
        p = profile()
        db = fake_db()
        talk = SimpleNamespace(band=3, facts=[{"text": "A", "at": "d"}, {"text": "B", "at": "d"}, {"text": "C", "at": "d"}], sessions=2)
        with mock.patch.object(conversation_db, "get_talk_profile", mock.AsyncMock(return_value=talk)), mock.patch.object(
            conversation_db, "seconds_used_today", mock.AsyncMock(return_value=300)
        ), mock.patch.object(router.settings, "CONVERSATION_DAILY_MINUTES", 20):
            out = await router.get_profile(db, p)
            self.assertEqual((out.band, out.seconds_left_today, len(out.facts)), (3, 900, 3))
            out = await router.forget_facts(db, p, index=1)
            self.assertEqual([f.text for f in out.facts], ["A", "C"])
            out = await router.forget_facts(db, p, index=None)
            self.assertEqual(out.facts, [])
        db.commit.assert_awaited()

    async def test_new_learner_profile_comes_from_the_lesson(self):
        p = profile()
        db = fake_db()
        with mock.patch.object(conversation_db, "get_talk_profile", mock.AsyncMock(return_value=None)), mock.patch.object(
            conversation_db, "load_context", mock.AsyncMock(return_value=ctx(level=3, band=3))
        ), mock.patch.object(conversation_db, "seconds_used_today", mock.AsyncMock(return_value=0)):
            out = await router.get_profile(db, p)
        self.assertEqual((out.band, out.sessions, out.facts), (3, 0, []))


if __name__ == "__main__":
    unittest.main()

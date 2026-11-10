"""Trình bày với Haru (app.services.presentation, app.api.routers.presentation)."""
import base64
import json
import math
import struct
import unittest
import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest import mock

from fastapi import HTTPException

from app.api.routers import presentation as router
from app.models import PresentationSession
from app.schemas import PresentAttemptRequest, PresentOutlineRequest
from app.services import presentation as pr
from app.services.conversation import LearnerContext, LessonBrief, Pattern, Word

ME = uuid.uuid4()
RATE = 16000


def wav(pattern: list[tuple[str, float]]) -> bytes:
    """[("voice"|"quiet", seconds), ...] -> 16 kHz mono PCM16 WAV."""
    samples: list[int] = []
    for kind, secs in pattern:
        n = int(secs * RATE)
        if kind == "voice":
            samples += [int(6000 * math.sin(2 * math.pi * 220 * i / RATE)) for i in range(n)]
        else:
            samples += [(i * 7919) % 61 - 30 for i in range(n)]  # faint room noise
    data = struct.pack(f"<{len(samples)}h", *samples)
    head = b"RIFF" + struct.pack("<I", 36 + len(data)) + b"WAVE"
    fmt = b"fmt " + struct.pack("<IHHIIHH", 16, 1, 1, RATE, RATE * 2, 2, 16)
    return head + fmt + b"data" + struct.pack("<I", len(data)) + data


def eval_json(**over):
    base = {
        "transcript_ko": "음 제 생각에는 도시가 좋아요 왜냐하면 편리하기 때문이에요 어 예를 들어서 지하철이 있어요 그래서 저는 도시가 좋아요",
        "off_topic": False,
        "parts": [
            {"part": "point", "present": True, "said_ko": "제 생각에는 도시가 좋아요", "note_vi": "Rõ."},
            {"part": "reason", "present": True, "said_ko": "편리하기 때문이에요", "note_vi": "Ổn."},
            {"part": "example", "present": True, "said_ko": "지하철이 있어요", "note_vi": "Cụ thể hơn."},
            {"part": "conclusion", "present": True, "said_ko": "그래서 저는 도시가 좋아요", "note_vi": "Tốt."},
        ],
        "scores": {"coherence": 4, "development": 4, "connectives": 5, "language": 3, "fluency": 3},
        "score_notes_vi": {k: "x" for k in pr.CRITERIA},
        "connectives_used": ["왜냐하면", "예를 들어서", "그래서"],
        "strength_vi": "Mở đầu rõ.",
        "tips_vi": ["Thêm ví dụ của bạn.", "Bớt 음.", "c", "d"],
        "upgraded": [{"part": "point", "ko": "제 생각에는 도시가 더 좋아요.", "vi": "Tôi nghĩ thành phố tốt hơn."}],
        "pron_issues": [{"word": "편리", "heard_as": "편니", "kind": "linking", "tip_vi": "ㄹ"}],
        "compare_vi": "",
    }
    base.update(over)
    return json.dumps(base)


MEASURE = pr.AudioMeasure(seconds=60, speaking_seconds=55, voiced_seconds=40, pauses=3, long_pauses=1, longest_pause=2.8)


class FrameTests(unittest.TestCase):
    def test_frames_grow_with_the_band(self):
        self.assertEqual(pr.frame_for(1).parts, ("point", "reason"))
        self.assertEqual(pr.frame_for(3).parts, ("point", "reason", "example", "conclusion"))
        self.assertIn("other_side", pr.frame_for(5).parts)
        self.assertEqual(pr.frame_for(None).band, 1)
        self.assertLessEqual(pr.frame_for(5).max_seconds, pr.HARD_MAX_SECONDS)
        d = pr.frame_for(2).as_dict()
        self.assertEqual([p["key"] for p in d["parts"]], ["point", "reason", "example"])
        self.assertTrue(all(p["starters"] for p in d["parts"]))


class AudioTests(unittest.TestCase):
    def test_measure_counts_pauses_inside_the_answer_only(self):
        m = pr.measure_audio(wav([("quiet", 1.0), ("voice", 2.0), ("quiet", 0.2), ("voice", 1.0),
                                  ("quiet", 1.4), ("voice", 2.0), ("quiet", 3.0), ("voice", 1.0), ("quiet", 2.0)]))
        self.assertAlmostEqual(m.seconds, 13.6, places=1)
        self.assertEqual(m.pauses, 2)  # 1.4 s and 3.0 s; the 0.2 s gap is inside a phrase; edges don't count
        self.assertEqual(m.long_pauses, 1)
        self.assertAlmostEqual(m.longest_pause, 3.0, delta=0.1)
        self.assertAlmostEqual(m.speaking_seconds, 10.6, delta=0.15)
        self.assertAlmostEqual(m.voiced_seconds, 6.2, delta=0.3)

    def test_silence_only(self):
        m = pr.measure_audio(wav([("quiet", 6.0)]))
        self.assertEqual((m.voiced_seconds, m.pauses), (0.0, 0))

    def test_fillers_and_syllables(self):
        t = "음 저는 어… 아 그 사과를 그… 좋아해요 으음 [vi: ừm cái đó] 음."
        self.assertEqual(pr.count_fillers(t), 5)  # 음, 어…, 그…, 으음, 음.  (not 아 / 그 alone)
        self.assertEqual(pr.syllables("저는 [vi: tôi] 학생"), 4)


class ParseTests(unittest.TestCase):
    def test_eval_is_bounded_and_measured(self):
        out = pr.parse_eval(eval_json(), pr.frame_for(3), MEASURE)
        ev, m = out["eval"], out["metrics"]
        self.assertEqual([p["part"] for p in ev["parts"]], ["point", "reason", "example", "conclusion"])
        self.assertEqual(ev["overall"], 3.8)
        self.assertEqual(len(ev["tips_vi"]), 3)
        self.assertEqual(m["fillers"], 2)
        self.assertEqual(m["pauses"], 3)
        self.assertTrue(m["in_target"])
        self.assertGreater(m["syllables_per_sec"], 0)

    def test_missing_part_caps_development(self):
        parts = json.loads(eval_json())["parts"]
        parts[2] = {"part": "example", "present": True, "said_ko": "", "note_vi": "Không có ví dụ."}  # claimed but empty
        out = pr.parse_eval(eval_json(parts=parts[:3], scores={k: 5 for k in pr.CRITERIA}), pr.frame_for(3), MEASURE)
        ev = out["eval"]
        self.assertEqual([p["present"] for p in ev["parts"]], [True, True, False, False])
        self.assertEqual(ev["scores"]["development"], 2)
        self.assertEqual(ev["scores"]["coherence"], 5)

    def test_incomplete_marking_raises(self):
        with self.assertRaises(ValueError):
            pr.parse_eval(eval_json(scores={"coherence": 3}), pr.frame_for(3), MEASURE)
        with self.assertRaises(ValueError):
            pr.parse_eval("not json", pr.frame_for(3), MEASURE)

    def test_scores_clamped(self):
        out = pr.parse_eval(eval_json(scores={k: 9 for k in pr.CRITERIA}), pr.frame_for(3), MEASURE)
        self.assertEqual(max(out["eval"]["scores"].values()), 5)

    def test_outline_keeps_frame_order_and_fills_gaps(self):
        raw = json.dumps({"parts": [
            {"part": "reason", "idea_vi": "tiện", "keywords_ko": ["편리하다", "지하철", "a", "b", "c"], "starter_ko": "왜냐하면…", "suggested": False},
            {"part": "point", "idea_vi": "thành phố", "keywords_ko": ["도시"], "starter_ko": "제 생각에는…", "suggested": False},
            {"part": "other_side", "idea_vi": "x", "keywords_ko": [], "starter_ko": "", "suggested": False},
        ]})
        out = pr.parse_outline(raw, pr.frame_for(2))
        self.assertEqual([o["part"] for o in out], ["point", "reason", "example"])
        self.assertEqual(len(out[1]["keywords_ko"]), 4)
        self.assertTrue(out[2]["suggested"])
        self.assertTrue(out[2]["starter_ko"])

    def test_topic(self):
        self.assertIsNone(pr.parse_topic(json.dumps({"question_ko": "Where?"})))
        t = pr.parse_topic(json.dumps({"question_ko": "주말에 뭐 해요?", "question_vi": "?", "angle_vi": "", "words": [{"ko": "쉬다", "vi": "nghỉ"}]}))
        self.assertEqual(t["words"], [{"ko": "쉬다", "vi": "nghỉ"}])
        fb = pr.fallback_topic(1, seen=[pr.FALLBACK_TOPICS[1][0][0]])
        self.assertNotEqual(fb["question_ko"], pr.FALLBACK_TOPICS[1][0][0])

    def test_second_try_prompt_carries_the_first(self):
        first = {"index": 0, "metrics": {"pauses": 4, "fillers": 6}, **json.loads(json.dumps({"eval": json.loads(eval_json())}))}
        p = pr.build_eval_prompt(level_rules="L", frame=pr.frame_for(3), question_ko="Q?", measure=MEASURE, outline=None, previous=first)
        self.assertIn("LẦN NÓI THỨ 2", p)
        self.assertIn("4 khoảng lặng", p)
        self.assertNotIn("LẦN NÓI THỨ", pr.build_eval_prompt(level_rules="L", frame=pr.frame_for(3), question_ko="Q?", measure=MEASURE, outline=None, previous=None))


# ---------------------------------------------------------------- routes


class R:
    def __init__(self, v):
        self.v = v

    def scalars(self):
        return self

    def all(self):
        return self.v

    def scalar_one_or_none(self):
        return self.v[0] if self.v else None


def ctx(band=3):
    return LearnerContext(
        name=None, goal=None, level=2, topic="Sinh hoạt", current=LessonBrief(id=36, title="Bài 6"),
        words=[Word("출근하다", "đi làm", "strong")], patterns=[Pattern("-아서/어서", "vì", None, "weak")], band=band,
    )


def row(**kw):
    base = dict(id=uuid.uuid4(), learner_id=ME, lesson_id=None, band=3, level=2,
                topic={"question_ko": "도시와 시골 중에 어디가 좋아요?", "question_vi": "", "angle_vi": "", "words": [], "source": "bank"},
                notes_vi="", outline=None, attempts=[], created_at=datetime.now(timezone.utc),
                mode="topic", title="", material="", plan=None)
    base.update(kw)
    return SimpleNamespace(**base)


def db_with(*answers):
    db = mock.MagicMock()
    db.execute = mock.AsyncMock(side_effect=list(answers))
    db.get = mock.AsyncMock()
    db.add = mock.MagicMock()
    db.commit = mock.AsyncMock()
    db.refresh = mock.AsyncMock()
    return db


PROFILE = SimpleNamespace(id=ME)
GOOD_WAV = base64.b64encode(wav([("quiet", 0.5), ("voice", 4.0), ("quiet", 1.2), ("voice", 4.0), ("quiet", 0.5)])).decode()


class RouteTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        patches = [
            mock.patch.object(router.conversation_db, "get_talk_profile", mock.AsyncMock(return_value=None)),
            mock.patch.object(router.conversation_db, "load_context", mock.AsyncMock(return_value=ctx())),
            mock.patch.object(router.settings, "PRESENT_DAILY_ATTEMPTS", 15),
            mock.patch.object(router.presentation_db, "load_knowledge", mock.AsyncMock(return_value=[])),
            mock.patch.object(router.presentation_db, "recent_first_tries", mock.AsyncMock(return_value=[])),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    async def test_start_uses_the_model_topic_and_falls_back_to_the_bank(self):
        made = {"question_ko": "출근할 때 버스와 지하철 중에 뭐가 더 좋아요?", "question_vi": "Đi làm bằng gì?", "angle_vi": "", "words": []}
        db = db_with(R([]), R(["Bài 6"]), R([]))  # seen topics, lesson title, attempts today
        with mock.patch.object(router.gemini_client, "generate_structured", return_value={"text": json.dumps(made)}):
            out = await router.start_presentation(db, PROFILE)
        added = db.add.call_args.args[0]
        self.assertIsInstance(added, PresentationSession)
        self.assertEqual((added.band, added.lesson_id, added.topic["source"]), (3, 36, "model"))
        self.assertEqual(out.frame.parts[-1].key, "conclusion")
        self.assertEqual(out.attempts_left, 3)

        db = db_with(R([]), R(["Bài 6"]), R([]))
        with mock.patch.object(router.gemini_client, "generate_structured", side_effect=RuntimeError("down")):
            await router.start_presentation(db, PROFILE)
        self.assertEqual(db.add.call_args.args[0].topic["source"], "bank")

    async def test_outline(self):
        r = row()
        db = db_with(R([]))
        db.get.return_value = r
        raw = json.dumps({"parts": [{"part": "point", "idea_vi": "thành phố", "keywords_ko": ["도시"], "starter_ko": "제 생각에는…", "suggested": False}]})
        with mock.patch.object(router.gemini_client, "generate_structured", return_value={"text": raw}):
            out = await router.make_outline(r.id, PresentOutlineRequest(notes_vi=" thành phố tiện "), db, PROFILE)
        self.assertEqual(r.notes_vi, "thành phố tiện")
        self.assertEqual(len(out.outline), 4)

    async def test_attempt_is_measured_marked_and_kept(self):
        r = row()
        db = db_with(R([[]]), R([[]]))  # attempts today: before, and in the answer
        db.get.return_value = r
        with mock.patch.object(router.gemini_client, "generate_structured", return_value={"text": eval_json()}) as gen:
            out = await router.add_attempt(r.id, PresentAttemptRequest(wav_b64=GOOD_WAV), db, PROFILE)
        self.assertEqual(len(r.attempts), 1)
        self.assertEqual(out.attempts[0].metrics.pauses, 1)
        ev0 = out.attempts[0].eval
        self.assertEqual(ev0.overall, round(sum(ev0.scores.values()) / 5, 1))
        self.assertIsNotNone(out.attempts[0].metrics.fluency_measured)  # Trôi chảy blended with what was measured
        self.assertEqual(out.attempts_left, 2)
        self.assertEqual(gen.call_args.kwargs["model"], router.settings.PRESENT_EVAL_MODEL or router.settings.CONVERSATION_PRONUNCIATION_MODEL)
        self.assertNotIn("LẦN NÓI THỨ", gen.call_args.kwargs["prompt"][1])

        db = db_with(R([[]]), R([[]]))
        db.get.return_value = r
        with mock.patch.object(router.gemini_client, "generate_structured", return_value={"text": eval_json(compare_vi="Tốt hơn.")}) as gen:
            out = await router.add_attempt(r.id, PresentAttemptRequest(wav_b64=GOOD_WAV), db, PROFILE)
        self.assertIn("LẦN NÓI THỨ 2", gen.call_args.kwargs["prompt"][1])
        self.assertEqual(out.attempts[1].eval.compare_vi, "Tốt hơn.")

    async def test_attempt_refusals(self):
        full = row(attempts=[{"index": i} for i in range(3)])
        db = db_with()
        db.get.return_value = full
        with self.assertRaises(HTTPException) as cm:
            await router.add_attempt(full.id, PresentAttemptRequest(wav_b64=GOOD_WAV), db, PROFILE)
        self.assertEqual(cm.exception.status_code, 409)

        now = datetime.now(timezone.utc).isoformat()
        db = db_with(R([[{"at": now}] * 15]))
        db.get.return_value = row()
        with self.assertRaises(HTTPException) as cm:
            await router.add_attempt(uuid.uuid4(), PresentAttemptRequest(wav_b64=GOOD_WAV), db, PROFILE)
        self.assertEqual(cm.exception.status_code, 429)

        for bad in (base64.b64encode(b"x" * 200).decode(), base64.b64encode(wav([("voice", 2.0)])).decode()):
            db = db_with(R([[]]))
            db.get.return_value = row()
            with self.assertRaises(HTTPException) as cm:
                await router.add_attempt(uuid.uuid4(), PresentAttemptRequest(wav_b64=bad), db, PROFILE)
            self.assertEqual(cm.exception.status_code, 422)

        db = db_with(R([[]]))
        db.get.return_value = row()
        with self.assertRaises(HTTPException) as cm:
            await router.add_attempt(uuid.uuid4(), PresentAttemptRequest(wav_b64=base64.b64encode(wav([("quiet", 8.0)])).decode()), db, PROFILE)
        self.assertEqual(cm.exception.status_code, 422)

        r = row()
        db = db_with(R([[]]))
        db.get.return_value = r
        with mock.patch.object(router.gemini_client, "generate_structured", return_value={"text": "{}"}):
            with self.assertRaises(HTTPException) as cm:
                await router.add_attempt(r.id, PresentAttemptRequest(wav_b64=GOOD_WAV), db, PROFILE)
        self.assertEqual(cm.exception.status_code, 502)
        self.assertEqual(r.attempts, [])  # nothing kept from a failed marking

    async def test_someone_elses_round(self):
        db = db_with()
        db.get.return_value = row(learner_id=uuid.uuid4())
        with self.assertRaises(HTTPException) as cm:
            await router.get_presentation(uuid.uuid4(), db, PROFILE)
        self.assertEqual(cm.exception.status_code, 404)


if __name__ == "__main__":
    unittest.main()

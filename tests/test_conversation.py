"""Trò chuyện với Haru (app.services.conversation, conversation_db, gemini_client.mint_live_token,
app.api.routers.conversation) — pure logic plus the routes against mocked sessions."""
import json
import unittest
import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest import mock

from fastapi import HTTPException

from app.api.routers import conversation as router
from app.schemas import ConversationFinishRequest, ConversationStartRequest
from app.services import conversation as c
from app.services import conversation_db, gemini_client

NOW = datetime(2026, 10, 27, 9, 0, tzinfo=timezone.utc)


def ctx(**kw):
    base = dict(
        name="Dương",
        goal="talk",
        level=2,
        topic="Sinh hoạt hàng ngày",
        current=c.LessonBrief(36, "Nền tảng 6 · Một ngày của tôi", "하루 일과", "Kể về một ngày"),
        earlier=[c.LessonBrief(33, "Nền tảng 3 · Thời gian"), c.LessonBrief(35, "Nền tảng 5 · Bổ nghĩa danh từ")],
        words=[
            c.Word("일어나다", "thức dậy", "new"),
            c.Word("출근하다", "đi làm", "unseen"),
            c.Word("시간", "thời gian", "weak"),
            c.Word("학교", "trường", "strong"),
        ],
        patterns=[
            c.Pattern("N에", "lúc (thời gian)", "일곱 시에 일어나요.", "weak"),
            c.Pattern("V-고", "rồi, và", "밥을 먹고 출근해요.", "new"),
            c.Pattern("V-(으)ㄹ 거예요", "sẽ", None, "strong"),
        ],
        shaky_patterns=["N에"],
        remembered=["Có một con nhỏ 3 tuổi."],
    )
    base.update(kw)
    return c.LearnerContext(**base)


class BucketTests(unittest.TestCase):
    def test_buckets(self):
        self.assertEqual(c.bucket_of(None, None, None, NOW), "unseen")
        self.assertEqual(c.bucket_of(0.3, True, NOW - timedelta(hours=2), NOW), "new")
        self.assertEqual(c.bucket_of(0.9, True, NOW - timedelta(days=5), NOW), "strong")
        self.assertEqual(c.bucket_of(0.9, False, NOW - timedelta(days=5), NOW), "weak")  # just forgotten
        self.assertEqual(c.bucket_of(0.4, None, None, NOW), "weak")


class InstructionTests(unittest.TestCase):
    def test_it_carries_the_lessons_words_and_ladder(self):
        text = c.build_system_instruction(ctx())
        for needle in (
            "Nền tảng 6 · Một ngày của tôi",
            "하루 일과",
            "Nền tảng 3 · Thời gian",  # an earlier lesson of the topic is woven in
            "일어나다 (thức dậy)",
            "시간 (thời gian)",
            "N에 — lúc (thời gian)",
            "Có một con nhỏ 3 tuổi.",
            c.SIGNAL,
            "im lặng ~12 giây",
            "im lặng ~20 giây",
            "Học viên tên Dương.",
        ):
            self.assertIn(needle, text)

    def test_words_land_in_the_right_section(self):
        text = c.build_system_instruction(ctx())
        new_part = text.split("Mới học hôm nay")[1].split("Đang quên")[0]
        weak_part = text.split("Đang quên — khéo léo")[1].split("Đã chắc")[0]
        self.assertIn("일어나다", new_part)
        self.assertIn("출근하다", new_part)  # not met yet: offered like a new word
        self.assertIn("시간", weak_part)
        self.assertNotIn("학교", new_part + weak_part)

    def test_level_rules_follow_the_lesson(self):
        self.assertIn("6–8 từ", c.build_system_instruction(ctx(level=1)))
        self.assertIn("trung cấp", c.build_system_instruction(ctx(level=3)))

    def test_pace_slows_for_beginners_and_on_request(self):
        from app.services import talk_profile as tp

        self.assertIn("một nửa tốc độ thường", tp.BANDS[1]["rules"])
        self.assertIn("2/3", tp.BANDS[2]["rules"])
        self.assertNotIn("một nửa", tp.BANDS[4]["rules"])
        text = c.build_system_instruction(ctx())
        self.assertIn('"Nói chậm"', text)  # the app's pace signal is explained
        self.assertIn("천천히 말해 주세요", text)  # and asking aloud works too
        for kind in ("slower", "normal_pace"):
            self.assertTrue(c.NUDGES[kind].startswith(c.SIGNAL))
        self.assertIn("đến hết buổi", c.NUDGES["slower"])

    def test_no_lesson_yet_still_gives_a_topic(self):
        text = c.build_system_instruction(ctx(current=None, earlier=[], name=None))
        self.assertIn("chưa bắt đầu bài nào", text)
        self.assertIn("có thể hỏi tên", text)


class HintTests(unittest.TestCase):
    def test_new_words_first_and_frames_from_examples(self):
        hints = c.hint_cards(ctx())
        self.assertEqual(hints["words"][0], {"ko": "일어나다", "vi": "thức dậy"})
        self.assertEqual([w["ko"] for w in hints["words"]][-1], "학교")
        # first the frame of a full answer at the learner's band, then the lesson's examples (no example, no frame)
        self.assertEqual(hints["frames"][0]["pattern"], "Trả lời đủ ý")
        self.assertEqual([f["ko"] for f in hints["frames"][1:]], ["밥을 먹고 출근해요.", "일곱 시에 일어나요."])

    def test_limits(self):
        many = ctx(words=[c.Word(f"w{i}", "x", "new") for i in range(20)])
        self.assertEqual(len(c.hint_cards(many, max_words=5)["words"]), 5)


class SetupAndTokenTests(unittest.TestCase):
    def test_setup_is_locked_to_audio_with_transcripts(self):
        s = c.live_setup(ctx(), model="gemini-3.8-live", voice=None)
        self.assertEqual(s["model"], "models/gemini-3.8-live")
        self.assertEqual(s["generationConfig"], {"responseModalities": ["AUDIO"]})
        self.assertEqual(s["inputAudioTranscription"], {})
        self.assertEqual(s["outputAudioTranscription"], {})
        self.assertIn("Nền tảng 6", s["systemInstruction"]["parts"][0]["text"])
        # the context is kept short: Live bills the whole of it again on every turn
        w = s["contextWindowCompression"]
        self.assertGreater(w["triggerTokens"], w["slidingWindow"]["targetTokens"])

    def test_voice_and_prefixed_model(self):
        s = c.live_setup(ctx(), model="models/x-live", voice="Kore")
        self.assertEqual(s["model"], "models/x-live")
        self.assertEqual(s["generationConfig"]["speechConfig"]["voiceConfig"]["prebuiltVoiceConfig"]["voiceName"], "Kore")

    def test_token_request_is_single_use_and_bounded(self):
        body = c.token_request({"model": "m"}, NOW, session_seconds=600)
        self.assertEqual(body["uses"], 1)
        self.assertEqual(body["newSessionExpireTime"], "2026-10-27T09:01:00Z")
        self.assertEqual(body["expireTime"], "2026-10-27T09:15:00Z")
        self.assertEqual(body["bidiGenerateContentSetup"], {"model": "m"})


class TranscriptAndReportTests(unittest.TestCase):
    def test_clean_turns_merges_drops_signals_and_trims(self):
        turns = c.clean_turns(
            [
                {"role": "haru", "text": "안녕하세요!"},
                {"role": "haru", "text": "  몇 시에   일어나요? "},
                {"role": "learner", "text": c.NUDGES["easier"]},
                {"role": "learner", "text": ""},
                {"role": "learner", "text": "일곱 시"},
                {"role": "system", "text": "x"},
                {"role": "learner", "text": "x" * 2000},
            ]
        )
        self.assertEqual(turns[0], {"role": "haru", "text": "안녕하세요! 몇 시에 일어나요?"})
        self.assertEqual(turns[1]["role"], "learner")
        self.assertTrue(turns[1]["text"].startswith("일곱 시 x"))
        self.assertLessEqual(len(turns[1]["text"]), 1200)
        self.assertEqual(len(turns), 2)

    def test_report_prompt_lists_both_sides(self):
        p = c.build_report_prompt(ctx(), [{"role": "learner", "text": "저는 학교 가요"}, {"role": "haru", "text": "아, 그래요?"}])
        self.assertIn("Học viên: 저는 학교 가요", p)
        self.assertIn("Haru: 아, 그래요?", p)
        self.assertIn("Nền tảng 6", p)

    def test_parse_report_is_forgiving_and_bounded(self):
        r = c.parse_report(
            json.dumps(
                {
                    "summary_vi": "Bạn kể về buổi sáng.",
                    "praise_vi": "Phát âm 일어나요 rõ.",
                    "fixes": [{"said": "학교 가요", "better": "학교에 가요", "why_vi": "Cần 에."}] * 5 + [{"said": "x"}],
                    "words": [{"ko": "출근", "vi": "đi làm"}, {"vi": "thiếu ko"}],
                    "next_time_vi": "Kể về buổi tối.",
                    "learner_facts": ["Thích cầu lông", 5, "", None],
                }
            )
        )
        self.assertEqual(len(r["fixes"]), 3)
        self.assertEqual(r["words"], [{"ko": "출근", "vi": "đi làm"}])
        self.assertEqual(r["learner_facts"], ["Thích cầu lông", "5"])
        self.assertEqual(c.parse_report("not json")["fixes"], [])
        self.assertEqual(c.parse_report("[1,2]")["summary_vi"], "")

    def test_merge_remembered(self):
        self.assertEqual(c.merge_remembered(["A", "b"], ["B", "c"]), ["B", "c", "A"])
        self.assertEqual(len(c.merge_remembered([str(i) for i in range(20)], [], keep=8)), 8)


class MintTokenTests(unittest.TestCase):
    def test_returns_the_token_name_and_sends_the_key_in_a_header(self):
        resp = SimpleNamespace(status_code=200, json=lambda: {"name": "auth_tokens/abc"}, text="")
        with mock.patch.object(gemini_client.settings, "GEMINI_API_KEY", "k-secret"), mock.patch("httpx.post", return_value=resp) as post:
            self.assertEqual(gemini_client.mint_live_token({"uses": 1}), "auth_tokens/abc")
        self.assertEqual(post.call_args.kwargs["headers"], {"x-goog-api-key": "k-secret"})
        self.assertNotIn("k-secret", post.call_args.args[0])  # never in the URL

    def test_google_errors_become_live_token_errors(self):
        resp = SimpleNamespace(status_code=400, json=lambda: {"error": {"message": "bad setup"}}, text="")
        with mock.patch.object(gemini_client.settings, "GEMINI_API_KEY", "k"), mock.patch("httpx.post", return_value=resp):
            with self.assertRaises(gemini_client.LiveTokenError) as cm:
                gemini_client.mint_live_token({})
        self.assertEqual((cm.exception.status, str(cm.exception)), (400, "bad setup"))

    def test_no_key(self):
        with mock.patch.object(gemini_client.settings, "GEMINI_API_KEY", ""):
            with self.assertRaises(gemini_client.LiveTokenError):
                gemini_client.mint_live_token({})


def profile():
    return SimpleNamespace(id=uuid.uuid4(), display_name="Dương", goal="talk")


def fake_db():
    db = mock.MagicMock()
    db.add = mock.MagicMock()
    db.commit = mock.AsyncMock()

    async def refresh(row):
        row.id = uuid.uuid4()

    db.refresh = mock.AsyncMock(side_effect=refresh)
    db.get = mock.AsyncMock()
    return db


class StartRouteTests(unittest.IsolatedAsyncioTestCase):
    async def test_daily_cap(self):
        with mock.patch.object(router.settings, "CONVERSATION_DAILY_MINUTES", 20), mock.patch.object(
            conversation_db, "seconds_used_today", mock.AsyncMock(return_value=20 * 60 - 30)
        ):
            with self.assertRaises(HTTPException) as cm:
                await router.start_conversation(ConversationStartRequest(), fake_db(), profile())
        self.assertEqual(cm.exception.status_code, 429)

    async def test_token_refused_is_a_503_and_no_row(self):
        db = fake_db()
        with mock.patch.object(conversation_db, "seconds_used_today", mock.AsyncMock(return_value=0)), mock.patch.object(
            conversation_db, "load_context", mock.AsyncMock(return_value=ctx())
        ), mock.patch.object(gemini_client, "mint_live_token", side_effect=gemini_client.LiveTokenError(400, "x")):
            with self.assertRaises(HTTPException) as cm:
                await router.start_conversation(ConversationStartRequest(), db, profile())
        self.assertEqual(cm.exception.status_code, 503)
        db.add.assert_not_called()

    async def test_success_returns_token_setup_hints_and_time(self):
        db = fake_db()
        with mock.patch.object(router.settings, "CONVERSATION_DAILY_MINUTES", 20), mock.patch.object(
            router.settings, "CONVERSATION_SESSION_SECONDS", 600
        ), mock.patch.object(conversation_db, "seconds_used_today", mock.AsyncMock(return_value=15 * 60)), mock.patch.object(
            conversation_db, "load_context", mock.AsyncMock(return_value=ctx())
        ) as load, mock.patch.object(gemini_client, "mint_live_token", return_value="auth_tokens/t1") as mint:
            out = await router.start_conversation(ConversationStartRequest(remember=True), db, profile())
        self.assertEqual(out.token, "auth_tokens/t1")
        self.assertEqual(out.max_seconds, 300)  # only 5 minutes left today
        self.assertEqual(out.lesson.id, 36)
        self.assertEqual(out.earlier_lessons, ["Nền tảng 3 · Thời gian", "Nền tảng 5 · Bổ nghĩa danh từ"])
        self.assertEqual(out.hints.words[0].ko, "일어나다")
        self.assertIn("BidiGenerateContentConstrained", out.ws_url)
        self.assertEqual(mint.call_args.args[0]["bidiGenerateContentSetup"], out.setup)
        self.assertTrue(load.call_args.kwargs["remember"])
        row = db.add.call_args.args[0]
        self.assertTrue(row.remember)
        self.assertEqual(row.lesson_id, 36)


class FinishRouteTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        patcher = mock.patch.object(conversation_db, "get_talk_profile", mock.AsyncMock(return_value=None))
        patcher.start()
        self.addCleanup(patcher.stop)

    def row(self, p, **kw):
        base = dict(
            id=uuid.uuid4(), learner_id=p.id, ended_at=None, report=None, remember=False, seconds=0, nudges=0,
            turns=None, band=2, metrics=None, pronunciation=None,
        )
        base.update(kw)
        return SimpleNamespace(**base)

    async def test_someone_elses_session_is_404(self):
        db = fake_db()
        db.get.return_value = self.row(profile())
        with self.assertRaises(HTTPException) as cm:
            await router.finish_conversation(uuid.uuid4(), ConversationFinishRequest(seconds=10), db, profile())
        self.assertEqual(cm.exception.status_code, 404)

    async def test_too_short_to_report(self):
        p = profile()
        db = fake_db()
        row = self.row(p)
        db.get.return_value = row
        out = await router.finish_conversation(
            row.id, ConversationFinishRequest(seconds=20, turns=[{"role": "haru", "text": "안녕하세요"}]), db, p
        )
        self.assertIsNone(out.report)
        self.assertIn("chưa nói gì nhiều", out.report_error_vi)
        self.assertIsNotNone(row.ended_at)
        self.assertEqual(row.seconds, 20)

    async def test_report_made_and_facts_dropped_without_consent(self):
        p = profile()
        db = fake_db()
        row = self.row(p, remember=False)
        db.get.return_value = row
        model_out = {"text": json.dumps({"summary_vi": "ok", "praise_vi": "tốt", "fixes": [], "words": [], "next_time_vi": "", "learner_facts": ["Thích cà phê"]})}
        with mock.patch.object(conversation_db, "load_context", mock.AsyncMock(return_value=ctx())), mock.patch.object(
            gemini_client, "generate_structured", return_value=model_out
        ):
            out = await router.finish_conversation(
                row.id,
                ConversationFinishRequest(seconds=99999 // 100, nudges=2, turns=[{"role": "learner", "text": "저는 커피를 좋아해요"}]),
                db,
                p,
            )
        self.assertEqual(out.report.summary_vi, "ok")
        self.assertEqual(out.report.learner_facts, [])
        self.assertEqual(row.nudges, 2)
        self.assertEqual(row.turns, [{"role": "learner", "text": "저는 커피를 좋아해요"}])

    async def test_report_failure_keeps_the_transcript(self):
        p = profile()
        db = fake_db()
        row = self.row(p)
        db.get.return_value = row
        with mock.patch.object(conversation_db, "load_context", mock.AsyncMock(return_value=ctx())), mock.patch.object(
            gemini_client, "generate_structured", side_effect=RuntimeError("boom")
        ):
            out = await router.finish_conversation(
                row.id, ConversationFinishRequest(seconds=60, turns=[{"role": "learner", "text": "저는 학생이에요"}]), db, p
            )
        self.assertIsNone(out.report)
        self.assertIsNotNone(out.report_error_vi)
        self.assertIsNotNone(row.turns)
        db.commit.assert_awaited()

    async def test_finishing_twice_returns_the_first_report(self):
        p = profile()
        db = fake_db()
        report = {"summary_vi": "s", "praise_vi": "p", "fixes": [], "words": [], "next_time_vi": "n", "learner_facts": []}
        row = self.row(p, ended_at=NOW, report=report, seconds=120)
        db.get.return_value = row
        with mock.patch.object(gemini_client, "generate_structured") as gen:
            out = await router.finish_conversation(row.id, ConversationFinishRequest(seconds=5), db, p)
        gen.assert_not_called()
        self.assertEqual((out.seconds, out.report.summary_vi), (120, "s"))


class SecondsUsedTests(unittest.IsolatedAsyncioTestCase):
    async def test_open_sessions_count_as_full(self):
        db = mock.MagicMock()
        r1, r2 = mock.MagicMock(), mock.MagicMock()
        r1.scalar_one.return_value = 250
        r2.scalar_one.return_value = 1
        db.execute = mock.AsyncMock(side_effect=[r1, r2])
        self.assertEqual(await conversation_db.seconds_used_today(db, uuid.uuid4(), session_seconds=600, now=NOW), 850)


if __name__ == "__main__":
    unittest.main()


class LoadContextTests(unittest.IsolatedAsyncioTestCase):
    """The lesson being studied is the one of the card touched last; earlier lessons of its topic
    come in only when the learner has touched them."""

    async def test_current_lesson_topic_and_buckets(self):
        class R:
            def __init__(self, v):
                self.v = v

            def scalars(self):
                return self

            def all(self):
                return self.v

            def first(self):
                return self.v[0] if self.v else None

        states = [
            SimpleNamespace(item_type="vocab_item", item_id=7, strength=0.9, last_seen=NOW, last_correct=True, introduced_at=NOW - timedelta(days=9)),
            SimpleNamespace(item_type="vocab_item", item_id=3, strength=0.3, last_seen=NOW - timedelta(days=2), last_correct=False, introduced_at=NOW - timedelta(days=9)),
        ]
        answers = [
            R(states),  # item_state
            R([(7, 36), (3, 33)]),  # vocab -> lesson
            R([SimpleNamespace(id=2, name="Sinh hoạt hàng ngày")]),  # topic of lesson 36
            R([  # earlier lessons of the topic, newest first; 34 was never touched
                SimpleNamespace(id=34, title="B4", title_ko=None, summary=None, sort_order=4),
                SimpleNamespace(id=33, title="B3", title_ko=None, summary=None, sort_order=3),
            ]),
            R([
                SimpleNamespace(id=7, lesson_id=36, hangul="일어나다", meaning_vi="thức dậy", priority="core"),
                SimpleNamespace(id=8, lesson_id=36, hangul="낯선", meaning_vi="lạ", priority="recognize"),
                SimpleNamespace(id=3, lesson_id=33, hangul="시간", meaning_vi="thời gian", priority="core"),
            ]),
            R([]),  # grammar
            R([{"kind": "adaptive", "tested": True, "gaps": [{"patterns": ["N에서", "V + -고 싶다"]}]}]),  # entry check
            R(["저는 일곱 시에 일어나요."]),  # open sentences of the talk notebook
        ]
        db = mock.MagicMock()
        db.execute = mock.AsyncMock(side_effect=answers)
        db.get = mock.AsyncMock(return_value=SimpleNamespace(id=36, title="B6", title_ko="하루", summary=None, sort_order=6, level=2))
        got = await conversation_db.load_context(db, profile(), remember=False, now=NOW)
        db.get.assert_awaited_once()
        self.assertEqual(db.get.call_args.args[1], 36)  # the lesson of the card touched last
        self.assertEqual(got.topic, "Sinh hoạt hàng ngày")
        self.assertEqual([b.id for b in got.earlier], [33])
        self.assertEqual(
            [(w.ko, w.bucket) for w in got.words], [("일어나다", "strong"), ("시간", "weak")]
        )  # "recognize" words are not pushed into the talk
        self.assertEqual(got.level, 2)
        self.assertEqual(got.practice_lines, ["저는 일곱 시에 일어나요."])
        self.assertEqual(got.entry_gaps, ["N에서", "V + -고 싶다"])
        self.assertEqual(got.band, 1)  # level 2, placed by the check: one band below reading (2 → 1)
        self.assertEqual(db.execute.await_count, 8)


class ChosenLessonTests(unittest.IsolatedAsyncioTestCase):
    """"Nói về bài này" from a lesson: the lesson is used only if the learner may open it."""

    async def test_an_open_lesson_is_kept_a_locked_or_missing_one_is_dropped(self):
        from app.services.billing import access as billing_access

        db = mock.MagicMock()
        db.get = mock.AsyncMock(return_value=SimpleNamespace(id=12, sort_order=30))
        held = SimpleNamespace(can_open=lambda n: n <= 20)
        with mock.patch.object(billing_access, "load_access", mock.AsyncMock(return_value=held)):
            self.assertIsNone(await conversation_db.lesson_they_may_open(db, profile(), 12))  # locked
            db.get.return_value = SimpleNamespace(id=5, sort_order=5)
            self.assertEqual(await conversation_db.lesson_they_may_open(db, profile(), 5), 5)
            db.get.return_value = None
            self.assertIsNone(await conversation_db.lesson_they_may_open(db, profile(), 999))
        self.assertIsNone(await conversation_db.lesson_they_may_open(db, profile(), None))


class AnswerLadderTests(unittest.TestCase):
    """Haru trains a fuller answer one step at a time, the step set by the learner's band."""

    def test_each_band_trains_one_step_and_the_instruction_says_it(self):
        from app.services import talk_profile

        goals = [talk_profile.answer_step(b)["goal_vi"] for b in range(1, 6)]
        self.assertEqual(len(set(goals)), 5)
        self.assertEqual(talk_profile.answer_step(None), talk_profile.ANSWER_STEPS[1])
        context = ctx(band=3, entry_gaps=["V + -아서/어서"])
        text = c.build_system_instruction(context)
        self.assertIn(talk_profile.ANSWER_STEPS[3]["goal_vi"], text)
        self.assertIn("V + -아서/어서", text)
        self.assertIn("tối đa một lần trong mỗi 2–3 lượt", text)

    def test_the_entry_check_starts_speaking_one_band_below_reading(self):
        from app.services import talk_profile

        self.assertEqual([talk_profile.placed_band(l) for l in (1, 2, 3, 5)], [1, 1, 2, 3])


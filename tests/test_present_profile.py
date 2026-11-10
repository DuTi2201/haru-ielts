"""Trình bày với Haru, phases 2-3: fitting to each learner, follow-up answers, own talks."""
import base64
import json
import sys
import unittest
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from fastapi import HTTPException

sys.path.insert(0, str(Path(__file__).parent))
from test_presentation import GOOD_WAV, MEASURE, PROFILE, R, ctx, db_with, eval_json, row, wav  # noqa: E402

from app.api.routers import presentation as router  # noqa: E402
from app.models import PresentationSession  # noqa: E402
from app.schemas import PresentAttemptRequest, PresentStartRequest  # noqa: E402
from app.services import present_profile as pp  # noqa: E402
from app.services import presentation as pr  # noqa: E402

NOW = datetime(2026, 10, 28, 7, 0, tzinfo=timezone.utc)


def item(key, kind="grammar", level=2, strength=0.9, last_correct=True, introduced=NOW - timedelta(days=30), ko=None):
    return pp.KnowItem(key, kind, ko or key, "nghĩa", None, level, strength, last_correct, introduced)


class RubricAndFluencyTests(unittest.TestCase):
    def test_each_band_has_its_own_bar(self):
        self.assertNotEqual(pp.BAND_RUBRIC[1]["language"], pp.BAND_RUBRIC[5]["language"])
        p1 = pr.build_eval_prompt(level_rules="L", frame=pr.frame_for(1), question_ko="Q?", measure=MEASURE, outline=None, previous=None)
        p5 = pr.build_eval_prompt(level_rules="L", frame=pr.frame_for(5), question_ko="Q?", measure=MEASURE, outline=None, previous=None)
        self.assertIn(pp.BAND_RUBRIC[1]["language"], p1)
        self.assertNotIn(pp.BAND_RUBRIC[5]["language"], p1)
        self.assertIn(pp.BAND_RUBRIC[5]["connectives"], p5)
        self.assertIn("1 câu hỏi", p1)  # one easy follow-up for a beginner
        self.assertIn("hội đồng", p5)

    def test_same_speech_is_fluent_for_a_beginner_and_not_for_band_5(self):
        m = {"speaking_seconds": 60, "syllables_per_sec": 1.5, "pauses": 6, "fillers": 5, "long_pauses": 1}
        self.assertGreaterEqual(pp.fluency_score(m, 1), 4)
        self.assertLessEqual(pp.fluency_score(m, 5), 2)
        self.assertIsNone(pp.fluency_score({"speaking_seconds": 3, "syllables_per_sec": 2}, 3))
        self.assertEqual(pp.blend_fluency(3, None), 3)
        self.assertEqual(pp.blend_fluency(2, 5), 4)

    def test_long_pauses_beyond_the_band_allowance_cost(self):
        m = {"speaking_seconds": 60, "syllables_per_sec": 3.0, "pauses": 2, "fillers": 0, "long_pauses": 0}
        self.assertGreater(pp.fluency_score(m, 5), pp.fluency_score({**m, "long_pauses": 3}, 5))


class BandAndFocusTests(unittest.TestCase):
    def ev(self, overall, present=4, fluency=4, dev=4, off=False):
        return {"overall": overall, "off_topic": off, "scores": {"fluency": fluency, "development": dev},
                "parts": [{"present": i < present} for i in range(4)]}

    def test_verdicts(self):
        self.assertEqual(pp.verdict(self.ev(4.4), {"in_target": True}, parts_total=4), 1)
        self.assertEqual(pp.verdict(self.ev(4.4), {"in_target": False}, parts_total=4), 0)
        self.assertEqual(pp.verdict(self.ev(2.2), {}, parts_total=4), -1)
        self.assertEqual(pp.verdict(self.ev(3.5, present=2), {}, parts_total=4), -1)
        self.assertIsNone(pp.verdict(self.ev(4.4, off=True), {"in_target": True}, parts_total=4))
        self.assertEqual(pp.next_present_band(3, [1, 1]), 4)
        self.assertEqual(pp.next_present_band(3, [1, 0]), 3)

    def test_focus_is_the_weakest_recent_criterion(self):
        tries = [{"coherence": 4, "development": 4, "connectives": 2, "language": 3, "fluency": 3},
                 {"coherence": 4, "development": 3, "connectives": 2, "language": 3, "fluency": 4}]
        self.assertEqual(pp.focus_of(tries), "connectives")
        self.assertIsNone(pp.focus_of(tries[:1]))
        self.assertIsNone(pp.focus_of([{k: 5 for k in pp.CRITERIA_ORDER}] * 3))


class TargetTests(unittest.TestCase):
    def test_slipping_and_new_items_first_never_mastered_or_beyond_level(self):
        items = [
            item("g:1", strength=0.9),
            item("g:2", strength=0.3, last_correct=False),  # slipping
            item("g:3", introduced=NOW - timedelta(days=1)),  # just learnt
            item("g:4", level=6),  # beyond level 2
            item("g:5", strength=0.2),  # weak but mastered in speech
            item("v:1", kind="word", strength=0.4),
            item("v:2", kind="word"),
        ]
        usage = {"g:5": {"ok_rounds": ["a", "b", "c"]}}
        out = pp.choose_targets(items, usage, band=3, level=2, mode="topic", seed="r", now=NOW)
        self.assertEqual([t["key"] for t in out], ["g:2", "g:3", "v:1"])  # band 3: 2 grammar + 1 word
        self.assertIn("hay sai", out[0]["why_vi"])
        b1 = pp.choose_targets(items, usage, band=1, level=2, mode="topic", seed="r", now=NOW)
        self.assertEqual(len(b1), 2)

    def test_defense_adds_an_academic_phrase_from_band_3(self):
        out = pp.choose_targets([], {}, band=4, level=3, mode="defense", seed="r", now=NOW)
        self.assertEqual([t["kind"] for t in out], ["phrase"])
        self.assertEqual(pp.choose_targets([], {}, band=2, level=2, mode="defense", seed="r", now=NOW), [])

    def test_usage_counts_a_round_once_and_masters_after_three(self):
        t = [{"key": "g:1", "kind": "grammar", "ko": "-기 때문에", "vi": "vì"}]
        u = {}
        for rid in ("r1", "r1", "r2", "r3"):
            u = pp.update_usage(u, t, [{"key": "g:1", "used": True, "correct": True}], rid, "2026-10-28")
        self.assertTrue(pp.mastered(u, "g:1"))
        u = pp.update_usage(u, t, [{"key": "g:1", "used": True, "correct": False}], "r4", "2026-10-29")
        self.assertEqual(u["g:1"]["miss"], 1)
        m = pp.mastery(u)
        self.assertEqual(m["mastered"][0]["ko"], "-기 때문에")
        self.assertEqual(pp.update_usage({}, t, [{"key": "g:1", "used": False}], "r", "x"), {})


class ParseTests(unittest.TestCase):
    def test_targets_follow_ups_and_stretch(self):
        targets = [{"key": "g:2", "kind": "grammar", "ko": "-기 때문에", "vi": "vì"}, {"key": "v:1", "kind": "word", "ko": "교통", "vi": "giao thông"}]
        raw = json.loads(eval_json())
        raw["targets_used"] = [{"key": "g:2", "used": True, "correct": True, "said_ko": "편리하기 때문이에요", "note_vi": "Đúng."},
                               {"key": "v:1", "used": True, "correct": True, "said_ko": "", "note_vi": ""}]
        raw["follow_ups"] = [{"q_ko": "왜요?", "q_vi": "Vì sao?", "kind": "why"}, {"q_ko": "예를 들면요?", "q_vi": "", "kind": "example"},
                             {"q_ko": "다른 의견은요?", "q_vi": "", "kind": "counter"}, {"q_ko": "no hangul", "q_vi": "", "kind": "why"}]
        raw["stretch"] = [{"ko": "-는 반면에", "vi": "trong khi", "why_vi": "so sánh"}] * 3
        out = pr.parse_eval(json.dumps(raw), pr.frame_for(3), MEASURE, targets)["eval"]
        self.assertEqual([(t["key"], t["used"], t["correct"]) for t in out["targets_used"]], [("g:2", True, True), ("v:1", False, False)])
        self.assertEqual(len(out["follow_ups"]), 2)  # band 3: two questions
        self.assertEqual(len(out["stretch"]), 2)
        d = pr.parse_eval(json.dumps(raw), pr.frame_for(1, "defense"), MEASURE, targets)  # unknown parts are just missing
        self.assertEqual([p["part"] for p in d["eval"]["parts"]], ["opening", "content", "conclusion"])
        self.assertEqual(len(d["eval"]["follow_ups"]), 2)

    def test_defense_frames(self):
        f = pr.frame_for(5, "defense")
        self.assertIn("limitation", f.parts)
        self.assertEqual(f.max_seconds, 270)
        self.assertEqual(pr.frame_for(5).max_seconds, 150)

    def test_answer(self):
        a = pr.parse_answer(json.dumps({"transcript_ko": "음 편리하기 때문이에요", "scores": {"directness": 4, "support": 2, "language": 9},
                                        "note_vi": "x", "better_ko": "y", "better_vi": "z"}), MEASURE)
        self.assertEqual((a["scores"]["language"], a["overall"], a["fillers"]), (5, 3.7, 1))
        with self.assertRaises(ValueError):
            pr.parse_answer("{}", MEASURE)

    def test_ideas(self):
        raw = {"seeds": [{"tool_vi": "t", "stance_vi": f"s{i}", "reason_vi": "", "example_vi": "", "hook_ko": "", "hook_vi": ""} for i in range(5)]}
        self.assertEqual(len(pr.parse_ideas(json.dumps(raw))), 3)
        self.assertIn("câu hỏi cho người nghe", pr.build_ideas_prompt(level_rules="L", frame=pr.frame_for(4), question_ko="Q"))


# ---------------------------------------------------------------- routes


class RouteTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.talk = SimpleNamespace(present_band=3, present_verdicts=[{"s": "x", "v": 1}], present_usage={}, band=2)
        self.know = [item("g:7", strength=0.3, last_correct=False, ko="-기 때문에"), item("v:9", kind="word", ko="교통")]
        patches = [
            mock.patch.object(router.conversation_db, "get_talk_profile", mock.AsyncMock(return_value=self.talk)),
            mock.patch.object(router.conversation_db, "load_context", mock.AsyncMock(return_value=ctx(band=2))),
            mock.patch.object(router.settings, "PRESENT_DAILY_ATTEMPTS", 15),
            mock.patch.object(router.presentation_db, "load_knowledge", mock.AsyncMock(return_value=self.know)),
            mock.patch.object(router.presentation_db, "recent_first_tries", mock.AsyncMock(return_value=[
                {"coherence": 4, "development": 4, "connectives": 2, "language": 4, "fluency": 3}] * 2)),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    async def test_start_is_fitted_to_the_learner(self):
        made = {"question_ko": "출근할 때 뭐가 더 좋아요?", "question_vi": "", "angle_vi": "", "words": []}
        db = db_with(R([]), R(["Bài 6"]), R([]))
        with mock.patch.object(router.gemini_client, "generate_structured", return_value={"text": json.dumps(made)}) as gen:
            out = await router.start_presentation(db, PROFILE, PresentStartRequest(band_shift=1))
        added = db.add.call_args.args[0]
        self.assertEqual((added.band, added.plan["base_band"], added.plan["shift"]), (4, 3, 1))  # present band 3, "Khó hơn"
        self.assertEqual(out.focus, "connectives")
        self.assertEqual([t.key for t in out.targets], ["g:7", "v:9"])
        prompt = gen.call_args.kwargs["prompt"]
        self.assertIn("so sánh", prompt)  # the focus shapes the topic
        self.assertIn("-기 때문에", prompt)  # and the item to deploy

    async def test_defense_round(self):
        with self.assertRaises(HTTPException):
            await router.start_presentation(db_with(), PROFILE, PresentStartRequest(mode="defense"))
        db = db_with(R([]), R([]))
        with mock.patch.object(router.gemini_client, "generate_structured", side_effect=RuntimeError("down")):
            out = await router.start_presentation(db, PROFILE, PresentStartRequest(mode="defense", title="Phát hiện té ngã bằng camera AI", material="YOLO…"))
        added = db.add.call_args.args[0]
        self.assertEqual((added.mode, added.lesson_id, added.topic["source"]), ("defense", None, "title"))
        self.assertEqual(out.frame.parts[0].key, "opening")
        self.assertEqual(out.targets[-1].kind, "phrase")  # band 3: an academic phrase to use

    async def test_first_try_moves_the_band_and_counts_usage(self):
        targets = [{"key": "g:7", "kind": "grammar", "ko": "-기 때문에", "vi": "vì", "example_ko": "", "why_vi": ""}]
        r = row(plan={"base_band": 3, "shift": 0, "focus": None, "targets": targets, "known": ["-아서/어서"]})
        raw = json.loads(eval_json(scores={k: 5 for k in pr.CRITERIA}))
        raw["targets_used"] = [{"key": "g:7", "used": True, "correct": True, "said_ko": "편리하기 때문이에요", "note_vi": ""}]
        db = db_with(R([[]]), R([[]]))
        db.get.return_value = r
        long_wav = base64.b64encode(wav([("voice", 4.0), ("quiet", 0.4)] * 12)).decode()
        with mock.patch.object(router.gemini_client, "generate_structured", return_value={"text": json.dumps(raw)}):
            with mock.patch.object(router.presentation, "parse_eval", wraps=router.presentation.parse_eval) as pe:
                out = await router.add_attempt(r.id, PresentAttemptRequest(wav_b64=long_wav), db, PROFILE)
        a = r.attempts[0]
        self.assertEqual(pe.call_args.args[3], targets)
        self.assertEqual((a["verdict"], a["band_after"]), (1, 4))
        self.assertEqual(self.talk.present_band, 4)  # two +1 in a row
        self.assertEqual(self.talk.present_usage["g:7"]["ok_rounds"], [str(r.id)])
        self.assertTrue(out.attempts[0].eval.targets_used[0].correct)

    async def test_an_eased_round_does_not_move_the_band(self):
        r = row(band=2, plan={"base_band": 3, "shift": -1, "targets": []})
        db = db_with(R([[]]), R([[]]))
        db.get.return_value = r
        with mock.patch.object(router.gemini_client, "generate_structured", return_value={"text": eval_json()}):
            await router.add_attempt(r.id, PresentAttemptRequest(wav_b64=GOOD_WAV), db, PROFILE)
        self.assertNotIn("verdict", r.attempts[0])
        self.assertEqual(self.talk.present_verdicts, [{"s": "x", "v": 1}])

    async def test_follow_up_answer(self):
        raw = json.loads(eval_json())
        raw["follow_ups"] = [{"q_ko": "왜요?", "q_vi": "Vì sao?", "kind": "why"}]
        marked = pr.parse_eval(json.dumps(raw), pr.frame_for(3), MEASURE)
        r = row(attempts=[{"index": 0, "at": NOW.isoformat(), **marked, "answers": {}}])
        ans = {"transcript_ko": "교통이 편리하기 때문이에요", "scores": {"directness": 4, "support": 3, "language": 4}, "note_vi": "", "better_ko": "", "better_vi": ""}
        for expect in (1, 2):
            db = db_with(R([[]]))
            db.get.return_value = r
            with mock.patch.object(router.gemini_client, "generate_structured", return_value={"text": json.dumps(ans)}) as gen:
                out = await router.answer_follow_up(r.id, 0, 0, PresentAttemptRequest(wav_b64=GOOD_WAV), db, PROFILE)
            self.assertEqual(out.attempts[0].answers["0"].tries, expect)
        self.assertIn("왜요?", gen.call_args.kwargs["prompt"][1])
        db = db_with()
        db.get.return_value = r
        with self.assertRaises(HTTPException) as cm:
            await router.answer_follow_up(r.id, 0, 0, PresentAttemptRequest(wav_b64=GOOD_WAV), db, PROFILE)
        self.assertEqual(cm.exception.status_code, 409)
        with self.assertRaises(HTTPException) as cm:
            await router.answer_follow_up(r.id, 0, 3, PresentAttemptRequest(wav_b64=GOOD_WAV), db, PROFILE)
        self.assertEqual(cm.exception.status_code, 404)

    async def test_list_and_insights(self):
        ev = lambda o: {"overall": o, "scores": {k: 3 for k in pr.CRITERIA}}  # noqa: E731
        rows = [
            row(attempts=[{"at": NOW.isoformat(), "eval": ev(3.0), "answers": {"0": {"overall": 4.0}}}, {"eval": ev(3.6)}]),
            row(attempts=[]),
            row(mode="defense", attempts=[{"at": NOW.isoformat(), "eval": ev(2.4)}]),
        ]
        out = await router.list_presentations(db_with(R(rows)), PROFILE, limit=30)
        self.assertEqual([(o.tries, o.first_overall, o.best_overall, o.answers) for o in out], [(2, 3.0, 3.6, 1), (1, 2.4, 2.4, 0)])
        self.talk.present_usage = {"g:7": {"ko": "-기 때문에", "vi": "vì", "kind": "grammar", "ok_rounds": ["a", "b", "c"]}}
        ins = await router.get_insights(db_with(R(rows)), PROFILE)
        self.assertEqual((ins.rounds, ins.present_band, ins.best_overall, ins.answer_avg), (2, 3, 3.6, 4.0))
        self.assertEqual([p["overall"] for p in ins.points], [2.4, 3.0])
        self.assertEqual(ins.mastered[0]["ko"], "-기 때문에")
        self.assertIn("Từ nối", ins.band_rubric_vi)


class PromptKnowledgeTests(unittest.TestCase):
    def test_eval_prompt_carries_targets_known_and_focus(self):
        t = [{"key": "g:2", "kind": "grammar", "ko": "-기 때문에", "vi": "vì", "example_ko": "비가 오기 때문에"}]
        p = pr.build_eval_prompt(level_rules="L", frame=pr.frame_for(3), question_ko="Q?", measure=MEASURE, outline=None,
                                 previous=None, targets=t, known=["-아서/어서"], focus="connectives")
        self.assertIn("[g:2] -기 때문에", p)
        self.assertIn("-아서/어서", p)
        self.assertIn("TRỌNG TÂM LUYỆN của học viên: Từ nối", p)
        self.assertIn("LỒNG ĐỦ các kiến thức", p)
        o = pr.parse_outline(json.dumps({"parts": [{"part": "reason", "idea_vi": "", "keywords_ko": [], "starter_ko": "", "suggested": False, "target_keys": ["g:2", "zz"]}]}),
                             pr.frame_for(3), t)
        self.assertEqual(o[1]["targets"], [{"key": "g:2", "ko": "-기 때문에"}])


class EditorialHandoffTests(unittest.TestCase):
    """"Trình bày 2 phút" / "Phản biện" from a news article (presentation.editorial_handoff)."""

    TERMS = [{"ko": "폭염", "vi": "nắng nóng"}, {"ko": "냉방", "vi": "điều hòa"}, {"ko": "전력", "vi": "điện"},
             {"ko": "취약계층", "vi": "nhóm yếu thế"}, {"ko": "", "vi": "rỗng"}]
    GRAMMAR = [{"id": 3, "pattern": "-기 마련이다", "meaning_vi": "ắt sẽ", "example_ko": None},
               {"id": 4, "pattern": "-(으)ㄹ수록", "meaning_vi": "càng… càng", "example_ko": "x"},
               {"id": 5, "pattern": "-는 셈이다", "meaning_vi": "coi như", "example_ko": ""}]
    OUTLINE = {"phenomenon": "폭염이 길어졌다", "cause": "", "consequence": "전력 수요 급증", "solution": "냉방 지원"}

    def test_present_material_has_the_outline_terms_and_grammar(self):
        out = pr.editorial_handoff("present", "  폭염  대책 ", self.TERMS, self.GRAMMAR, self.OUTLINE, {"폭염": 101})
        self.assertEqual(out["title"], "폭염 대책")
        m = out["material"]
        self.assertTrue(m.startswith("Trình bày khoảng 2 phút"))
        self.assertIn("현상 · Hiện tượng: 폭염이 길어졌다", m)
        self.assertNotIn("원인", m)  # an empty part is left out
        self.assertIn("냉방 (điều hòa)", m)
        self.assertIn("-기 마련이다 (ắt sẽ)", m)

    def test_targets_are_the_articles_grammar_then_its_key_terms(self):
        out = pr.editorial_handoff("debate", "폭염", self.TERMS, self.GRAMMAR, None, {"폭염": 101})
        self.assertEqual([t["key"] for t in out["targets"]], ["g:3", "g:4", "v:101", "k:냉방", "k:전력"])
        self.assertTrue(all(t["kind"] in ("grammar", "word") for t in out["targets"]))
        self.assertIn("Phản biện", out["material"])
        self.assertNotIn("Dàn ý", out["material"])  # no outline: no outline block

    def test_an_unknown_kind_is_refused(self):
        with self.assertRaises(ValueError):
            pr.editorial_handoff("chat", "x", [], [], None)

    def test_merge_puts_the_article_first_without_repeats(self):
        first = [{"key": "g:3"}, {"key": "v:9"}]
        rest = [{"key": "v:9"}, {"key": "g:7"}, {"key": "p:1"}, {"key": "v:2"}, {"key": "v:4"}, {"key": "v:5"}]
        self.assertEqual([t["key"] for t in pr.merge_targets(first, rest)], ["g:3", "v:9", "g:7", "p:1", "v:2", "v:4"])


if __name__ == "__main__":
    unittest.main()

"""Tranh luận · Đàm phán · Phản biện (app.services.debate, app.api.routers.debate)."""
import json
import unittest
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest import mock

from fastapi import HTTPException

from app.api.routers import conversation_history
from app.api.routers import debate as router
from app.models import ConversationSession
from app.schemas import ConversationFinishRequest, DebateStartRequest
from app.services import debate as db_
from app.services.conversation import LearnerContext, LessonBrief

ME = uuid.uuid4()
PROFILE = SimpleNamespace(id=ME)


def report_json(kind="debate", **over):
    keys = list(db_.CRITERIA[kind])
    base = {
        "summary_vi": "s", "outcome_vi": "o", "scores": {k: 4 for k in keys}, "score_notes_vi": {k: "n" for k in keys},
        "best_move": {"said_en": "그 말도 맞지만…", "why_vi": "Công nhận rồi lật lại."},
        "missed": [{"haru_said_en": "a", "you_said_en": "b", "better_en": "c", "better_vi": "d", "why_vi": "e"}] * 4,
        "phrases_used": ["그 말도 맞지만"], "fixes": [], "goal_reached": True, "flaw_found": True, "next_time_vi": "x",
    }
    base.update(over)
    return json.dumps(base)


class ScenarioTests(unittest.TestCase):
    def test_bank_covers_every_kind_and_tier(self):
        for kind in db_.KINDS:
            for tier in (1, 2, 3):
                self.assertGreaterEqual(len([s for s in db_.SCENARIOS if s.kind == kind and s.tier == tier]), 3, (kind, tier))
        self.assertEqual(len(db_.BY_ID), len(db_.SCENARIOS))
        self.assertEqual([db_.tier_of(b) for b in (1, 2, 3, 4, 5)], [1, 1, 2, 3, 3])
        self.assertTrue(all(s.kind == "critique" for s in db_.scenarios_for(4, "critique")))

    def test_public_view_hides_secrets_and_the_claim(self):
        n = db_.BY_ID["n4"].public()
        self.assertNotIn("47", json.dumps(n, ensure_ascii=False))  # the landlord's floor stays hidden
        c = db_.BY_ID["c8"].public()
        self.assertEqual(c["opener_en"], "")
        self.assertNotIn("recall", json.dumps(c))

    def test_instruction_per_kind_and_band(self):
        d = db_.build_system_instruction(db_.Setup(db_.BY_ID["d4"], 3, "L", side_en="반대", known=["-기 때문에"]))
        self.assertIn("Học viên bên 반대; BẠN bên 찬성", d)
        self.assertIn(db_.SPEECH[3], d)
        self.assertIn("-기 때문에", d)
        self.assertIn("chỉ nhượng bộ", d.lower())
        n = db_.build_system_instruction(db_.Setup(db_.BY_ID["n1"], 1, "L"))
        self.assertIn("GIỚI HẠN BÍ MẬT", n)
        self.assertIn("22.000", n)
        self.assertIn("조금 깎아 주세요", n)
        c = db_.build_system_instruction(db_.Setup(db_.BY_ID["c5"], 3, "L"))
        self.assertIn("LỖ HỔNG ĐƯỢC CÀI SẴN", c)
        self.assertEqual(db_.nudges(db_.BY_ID["c5"])["start"][:10], db_.SIGNAL)

    def test_custom_motion(self):
        s = db_.custom_debate("  숙제는   없어야 한다  ", 5)
        self.assertEqual((s.opener_en, s.tier, s.kind), ("숙제는 없어야 한다", 3, "debate"))


class ReportTests(unittest.TestCase):
    def test_parse_bounds_and_kind_criteria(self):
        r = db_.parse_report(report_json("negotiate", scores={"outcome": 9, "strategy": 3, "rapport": 4, "language": 2}), "negotiate")
        self.assertEqual(r["scores"]["outcome"], 5)
        self.assertEqual(r["overall"], 3.5)
        self.assertEqual(len(r["missed"]), 3)
        self.assertFalse(r["flaw_found"])  # only a critique has a flaw
        self.assertTrue(db_.parse_report(report_json("critique"), "critique")["flaw_found"])
        with self.assertRaises(ValueError):
            db_.parse_report(report_json("debate", scores={"argument": 3}), "debate")

    def test_prompt_has_the_tier_rubric_and_the_secret(self):
        p = db_.build_report_prompt(db_.Setup(db_.BY_ID["c8"], 5, "L"), [{"role": "haru", "text": "99%"}, {"role": "learner", "text": "데이터가…"}])
        self.assertIn(db_.RUBRIC["critique"][3]["reasoning"], p)
        self.assertIn("recall", p)
        self.assertIn("Học viên: 데이터가…", p)

    def test_verdict(self):
        self.assertIsNone(db_.verdict({"overall": 5}, 3))
        self.assertEqual(db_.verdict({"overall": 4.5}, 6), 1)
        self.assertEqual(db_.verdict({"overall": 2.0}, 6), -1)
        self.assertEqual(db_.verdict({"overall": 3.5}, 6), 0)


class R:
    def __init__(self, v):
        self.v = v

    def scalars(self):
        return self

    def all(self):
        return self.v


def ctx():
    return LearnerContext(name=None, goal=None, level=3, topic=None, current=LessonBrief(id=1, title="B"), band=2)


def db_with(*answers):
    db = mock.MagicMock()
    db.execute = mock.AsyncMock(side_effect=list(answers))
    db.get = mock.AsyncMock()
    db.add = mock.MagicMock()
    db.commit = mock.AsyncMock()
    return db


class RouteTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.talk = SimpleNamespace(debate_band=None, present_band=4, debate_verdicts=[{"s": "x", "v": 1}])
        patches = [
            mock.patch.object(router.conversation_db, "get_talk_profile", mock.AsyncMock(return_value=self.talk)),
            mock.patch.object(router.conversation_db, "load_context", mock.AsyncMock(return_value=ctx())),
            mock.patch.object(router, "_seconds_left", mock.AsyncMock(return_value=900)),
            mock.patch.object(router, "seconds_to_show", mock.AsyncMock(return_value=900)),
            mock.patch.object(router.presentation_db, "load_knowledge", mock.AsyncMock(return_value=[])),
            mock.patch.object(router.settings, "CONVERSATION_DAILY_MINUTES", 20),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    async def test_options_follow_the_presentation_band_until_there_is_a_debate_band(self):
        out = await router.options(db_with(), PROFILE)
        self.assertEqual((out.band, out.tier), (4, 3))
        self.assertTrue(all(s.tier == 3 for s in out.scenarios))
        self.assertEqual(out.rubric["negotiate"], db_.RUBRIC["negotiate"][3])
        self.talk.debate_band = 1
        out = await router.options(db_with(), PROFILE)
        self.assertEqual((out.band, out.tier), (1, 1))

    async def test_start_mints_a_token_locked_to_the_role(self):
        db = db_with()
        with mock.patch.object(router.gemini_client, "mint_live_token", return_value="auth_tokens/x") as mint:
            out = await router.start_debate(DebateStartRequest(kind="negotiate", scenario_id="n7"), db, PROFILE)
        body = mint.call_args.args[0]
        instruction = body["bidiGenerateContentSetup"]["systemInstruction"]["parts"][0]["text"]
        self.assertIn("230만원", instruction)  # Haru knows its limit…
        self.assertNotIn("230만원", json.dumps(out.scenario.model_dump(), ensure_ascii=False))  # …the learner does not
        row = db.add.call_args.args[0]
        self.assertIsInstance(row, ConversationSession)
        self.assertEqual((row.kind, row.band, row.scenario["id"]), ("debate", 4, "n7"))
        self.assertLessEqual(out.max_seconds, db_.MAX_SECONDS)
        self.assertEqual(out.nudges["start"], db_.nudges(db_.BY_ID["n7"])["start"])

    async def test_start_refusals_and_custom_motion(self):
        with self.assertRaises(HTTPException) as cm:
            await router.start_debate(DebateStartRequest(kind="debate", scenario_id="n1"), db_with(), PROFILE)
        self.assertEqual(cm.exception.status_code, 422)
        db = db_with()
        with mock.patch.object(router.gemini_client, "mint_live_token", return_value="t"):
            out = await router.start_debate(DebateStartRequest(kind="debate", motion="교복은 없어야 한다", side="반대", band_shift=-1), db, PROFILE)
        row = db.add.call_args.args[0]
        self.assertEqual((row.band, row.scenario["motion"], row.scenario["side"], row.scenario["shift"]), (3, "교복은 없어야 한다", "반대", -1))
        self.assertEqual(out.side, "반대")
        with mock.patch.object(router, "_seconds_left", mock.AsyncMock(return_value=30)):
            with self.assertRaises(HTTPException) as cm:
                await router.start_debate(DebateStartRequest(kind="critique", scenario_id="c7"), db_with(), PROFILE)
        self.assertEqual(cm.exception.status_code, 429)

    def row(self, **kw):
        base = dict(id=uuid.uuid4(), learner_id=ME, kind="debate", band=4, ended_at=None, seconds=0, nudges=0, turns=None,
                    report=None, metrics=None, started_at=datetime.now(timezone.utc),
                    scenario={"id": "c8", "kind": "critique", "side": None, "shift": 0})
        base.update(kw)
        return SimpleNamespace(**base)

    async def test_finish_reports_reveals_the_flaw_and_moves_the_band(self):
        r = self.row()
        db = db_with()
        db.get.return_value = r
        turns = [{"role": "haru" if i % 2 == 0 else "learner", "text": "데이터가 대표성이 없어요" if i % 2 else "99%"} for i in range(10)]
        with mock.patch.object(router.gemini_client, "generate_structured", return_value={"text": report_json("critique", scores={k: 5 for k in db_.CRITERIA["critique"]})}) as gen:
            out = await router.finish_debate(r.id, ConversationFinishRequest(seconds=300, turns=turns), db, PROFILE)
        self.assertEqual(gen.call_args.kwargs["prompt_version"], "debate-report-v1")
        self.assertEqual(out.report.flaw_vi, "Chỉ số và dữ liệu không đại diện")
        self.assertEqual((out.band_before, out.band_after), (4, 5))  # two +1 in a row
        self.assertEqual(self.talk.debate_band, 5)
        self.assertEqual(set(out.criteria), set(db_.CRITERIA["critique"]))
        # a retry returns the same, without calling the model again
        with mock.patch.object(router.gemini_client, "generate_structured") as gen2:
            again = await router.finish_debate(r.id, ConversationFinishRequest(seconds=300, turns=turns), db, PROFILE)
        gen2.assert_not_called()
        self.assertEqual(again.report.overall, 5.0)

    async def test_short_or_eased_sessions(self):
        r = self.row()
        db = db_with()
        db.get.return_value = r
        out = await router.finish_debate(r.id, ConversationFinishRequest(seconds=20, turns=[{"role": "learner", "text": "네"}]), db, PROFILE)
        self.assertIsNone(out.report)
        self.assertIsNotNone(out.report_error_vi)
        eased = self.row(band=3, scenario={"id": "d4", "kind": "debate", "side": "찬성", "shift": -1})
        db = db_with()
        db.get.return_value = eased
        turns = [{"role": "haru" if i % 2 == 0 else "learner", "text": "아르바이트는 경험이 되기 때문이에요"} for i in range(10)]
        with mock.patch.object(router.gemini_client, "generate_structured", return_value={"text": report_json(scores={k: 5 for k in db_.CRITERIA["debate"]})}):
            out = await router.finish_debate(eased.id, ConversationFinishRequest(seconds=300, turns=turns), db, PROFILE)
        self.assertEqual(out.band_before, out.band_after)
        self.assertIsNone(eased.metrics["verdict"])

    async def test_talk_and_debate_rows_do_not_mix(self):
        db = db_with()
        db.get.return_value = self.row(kind="talk")
        with self.assertRaises(HTTPException):
            await router.get_debate(uuid.uuid4(), db, PROFILE)
        db.get.return_value = self.row()
        with self.assertRaises(HTTPException):
            await conversation_history.get_session(uuid.uuid4(), db, PROFILE)

    async def test_list_and_detail(self):
        rows = [self.row(ended_at=datetime.now(timezone.utc), seconds=200, report=json.loads(report_json("critique")) | {"kind": "critique", "overall": 4.0}),
                self.row(ended_at=datetime.now(timezone.utc), scenario={"id": "custom", "kind": "debate", "motion": "교복은 없어야 한다", "side": "찬성"})]
        out = await router.list_debates(db_with(R(rows)), PROFILE, limit=30)
        self.assertEqual([(o.kind, o.overall) for o in out], [("critique", 4.0), ("debate", None)])
        self.assertEqual(out[1].title_vi, "교복은 없어야 한다")
        db = db_with()
        db.get.return_value = rows[0]
        d = await router.get_debate(rows[0].id, db, PROFILE)
        self.assertEqual(d.kind, "critique")


if __name__ == "__main__":
    unittest.main()

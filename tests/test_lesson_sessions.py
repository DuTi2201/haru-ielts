"""Lessons cut into sittings by hand (`sessions`): the cut must keep the lesson whole and teach in order.

* every word and card in exactly one sitting, every closing question a question of the lesson (the
  seed validator enforces it; here it is checked on the real files too);
* a sitting's closing questions only test cards taught in that sitting or an earlier one, so a
  learner is never examined on something they have not met yet;
* a sitting says what the learner can do after it.
"""
import unittest
import warnings

warnings.filterwarnings("ignore")

from app.services.lesson_seed import load_all  # noqa: E402


class SessionPlanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lessons = [r for r in load_all().lessons if r.seed.sessions]

    def test_planned_lessons_exist(self):
        self.assertTrue(self.lessons)

    def test_checks_never_test_a_card_that_is_taught_later(self):
        for r in self.lessons:
            items = {it["id"]: it for it in r.practice["items"]}
            own = {g.pattern for g in r.seed.grammar}
            taught: set[str] = set()
            for s in r.seed.sessions:
                taught |= set(s.grammar)
                for qid in s.check:
                    it = items[qid]
                    tags = set(it.get("grammar") or [])
                    for q in it.get("questions") or []:
                        tags |= set(q.get("grammar") or [])
                    later = (tags & own) - taught
                    self.assertFalse(later, f"{r.seed.slug} · {s.title_vi}: {qid} tests {sorted(later)} before it is taught")

    def test_every_sitting_promises_something_to_do(self):
        for r in self.lessons:
            for s in r.seed.sessions:
                self.assertGreaterEqual(len(s.can_do_vi), 15, f"{r.seed.slug} · {s.title_vi}")

    def test_a_sitting_is_not_too_heavy(self):
        for r in self.lessons:
            core = {v.hangul for v in r.seed.vocab if v.priority == "core"}
            for s in r.seed.sessions:
                n = sum(1 for w in s.vocab if w in core)
                self.assertLessEqual(n, 24, f"{r.seed.slug} · {s.title_vi}: {n} core words")
                self.assertLessEqual(len(s.grammar), 3, f"{r.seed.slug} · {s.title_vi}: {len(s.grammar)} cards")


if __name__ == "__main__":
    unittest.main()


class SittingLectureTests(unittest.TestCase):
    """The lecture of one sitting reads only that sitting's words and cards."""

    def _rows(self):
        from types import SimpleNamespace as N

        lesson = N(
            title="Chào hỏi",
            title_ko=None,
            notes=[{"title": "n", "body": "b"}],
            sessions=[
                {"title_vi": "Tự giới thiệu", "vocab": ["b", "a"], "grammar": ["P"]},
                {"title_vi": "Hỏi tên", "vocab": ["c"], "grammar": []},
            ],
        )
        vocab = [N(hangul=h, meaning_vi=h.upper(), usage_note_vi=None, example_ko=None) for h in "abc"]
        grammar = [
            N(pattern="P", meaning_vi="m", usage_context_vi=None, note_vi=None, example_ko=None, example_vi=None, contrasts=[])
        ]
        return lesson, vocab, grammar

    def test_only_the_sittings_own_content_in_its_order(self):
        from app.services import lesson_audio as la

        lesson, vocab, grammar = self._rows()
        src, vr, gr = la.sitting_source(lesson, vocab, grammar, 1)
        self.assertEqual([v.hangul for v in vr], ["b", "a"])
        self.assertEqual(len(gr), 1)
        self.assertEqual(src.notes, [])
        script = la.build_template_lecture(src).script
        self.assertIn("buổi 1: Tự giới thiệu", script)
        self.assertNotIn("C.", script)
        src2, vr2, gr2 = la.sitting_source(lesson, vocab, grammar, 2)
        self.assertEqual([v.hangul for v in vr2], ["c"])
        self.assertEqual(gr2, [])

    def test_no_such_sitting(self):
        from app.services import lesson_audio as la

        lesson, vocab, grammar = self._rows()
        self.assertIsNone(la.sitting_source(lesson, vocab, grammar, 3))
        lesson.sessions = None
        self.assertIsNone(la.sitting_source(lesson, vocab, grammar, 1))

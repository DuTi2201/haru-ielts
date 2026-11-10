"""Intermediate grammar is mostly primary grammar put together: each card says which earlier cards
it is made of, and how much of it the learner must keep."""
import collections
import unittest

from app.services import grammar_graph as gg
from app.services import lesson_seed as seed
from app.services.grammar_tier import grammar_tier


def card(key, lesson, pattern, *builds_on):
    return gg.GraphCard(key, lesson, pattern, tuple(builds_on))


class ResolveTests(unittest.TestCase):
    def test_a_link_goes_to_the_card_with_that_pattern(self):
        cards = [card("a", 0, "N + 이/가"), card("b", 1, "N + 께서", "N + 이/가")]
        edges, problems = gg.resolve(cards)
        self.assertEqual((edges, problems), ({"a": [], "b": ["a"]}, []))
        self.assertEqual(gg.invert(edges), {"a": ["b"]})

    def test_a_card_taught_later_or_not_at_all_is_a_problem(self):
        cards = [card("a", 0, "A", "B"), card("b", 1, "B"), card("c", 2, "C", "Z")]
        edges, problems = gg.resolve(cards)
        self.assertEqual(edges, {"a": [], "b": [], "c": []})
        self.assertEqual(len(problems), 2)
        self.assertIn("only taught later", problems[0])
        self.assertIn("not a card of any lesson", problems[1])

    def test_inside_one_lesson_the_part_comes_first_when_the_order_is_strict(self):
        cards = [card("whole", 3, "W", "P"), card("part", 3, "P")]
        self.assertEqual(len(gg.resolve(cards)[1]), 1)
        edges, problems = gg.resolve(cards, strict_order=False)  # the database does not keep a card's place in its lesson
        self.assertEqual((edges["whole"], problems), (["part"], []))

    def test_a_card_that_revisits_a_pattern_links_to_its_first_card(self):
        cards = [card("first", 0, "V + -는 바람에"), card("again", 5, "V + -는 바람에", "V + -는 바람에")]
        self.assertEqual(gg.resolve(cards), ({"first": [], "again": ["first"]}, []))

    def test_a_card_never_links_to_itself_or_twice_to_one_card(self):
        edges, problems = gg.resolve([card("a", 0, "A", "A"), card("b", 1, "B", "A", "A")])
        self.assertEqual(edges["a"], [])
        self.assertEqual(edges["b"], ["a"])
        self.assertEqual(len(problems), 2)


class SeedGraphTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bundle = seed.load_all()
        cls.seeds = [r.seed for r in cls.bundle.lessons]
        cls.cards = [(s.slug, g) for s in cls.seeds for g in s.grammar]
        ordered = sorted(cls.seeds, key=lambda s: (seed.TRACKS.index(s.track), s.sort_order))
        cls.graph = [
            gg.GraphCard((s.slug, g.pattern), place, g.pattern, tuple(g.builds_on))
            for place, s in enumerate(ordered)
            for g in s.grammar
        ]
        cls.edges, _ = gg.resolve(cls.graph)
        cls.used = gg.invert(cls.edges)

    def test_every_link_leads_to_an_earlier_card(self):
        self.assertEqual(self.bundle.problems, [])
        self.assertGreaterEqual(sum(1 for t in self.edges.values() if t), 100)

    def test_a_link_to_a_later_card_is_refused_by_the_seed_check(self):
        broken = [s.model_copy(deep=True) for s in self.seeds]
        first = next(s for s in broken if s.slug == "sinh-hoat-00-nen-tang-1-gioi-thieu")
        first.grammar[0].builds_on = ["V/A + -지만"]  # taught in the first topic lesson, after this one
        problems = seed.graph_problems(broken)
        self.assertEqual(len(problems), 1)
        self.assertIn("only taught later", problems[0])

    def test_every_core_card_says_how_much_of_it_to_keep_and_an_extension_card_does_not(self):
        for slug, g in self.cards:
            ext = grammar_tier(g.usage_context_vi)[0] == "extension"
            self.assertEqual(g.importance is None, ext, (slug, g.pattern))

    def test_a_card_other_cards_are_built_on_is_required(self):
        labelled = {(s, g.pattern): g.importance for s, g in self.cards}
        for key, builders in self.used.items():
            if len(builders) >= 2 and labelled[key]:
                self.assertEqual(labelled[key], "must", (key, len(builders)))

    def test_the_kiip_first_stage_cards_are_required(self):
        for slug, g in self.cards:
            if g.exam == "kiip-1" and g.importance:
                self.assertEqual(g.importance, "must", (slug, g.pattern))

    def test_both_kinds_exist_in_a_sensible_balance(self):
        n = collections.Counter(g.importance for _, g in self.cards)
        self.assertGreater(n["must"], 60)
        self.assertGreater(n["normal"], 40)
        self.assertGreater(n["must"], n["normal"])  # the labels would mean little if most cards were optional

    def test_the_parts_of_a_composite_card_are_the_cards_a_learner_expects(self):
        def parts(pattern):
            key = next(k for k in self.edges if k[1] == pattern)
            return [p for _, p in self.edges[key]]

        self.assertEqual(
            parts("V + -(으)ㄹ 수 있겠습니까?"),
            ["V + -(으)ㄹ 수 있다/없다", "V/A + -겠-", "V/A + -ㅂ/습니다 · -ㅂ/습니까?"],
        )
        self.assertEqual(parts("V + -(으)려던 참이다"), ["V + -(으)려고 하다"])
        self.assertEqual(parts("V + -고 나면"), ["V + -고 나서 · V + -(으)ㄴ 후에", "V/A + -(으)면"])

    def test_the_basic_cards_are_reused_by_the_intermediate_ones(self):
        by_pattern = {k[1]: v for k, v in self.used.items()}
        self.assertGreaterEqual(len(by_pattern["V/A + -아/어요"]), 8)
        self.assertGreaterEqual(len(by_pattern["V/A + -(으)면"]), 6)


class ApiShapeTests(unittest.TestCase):
    def test_the_card_serves_its_label_and_its_links(self):
        from app.schemas import GrammarPointOut, GrammarRefOut

        base = dict(id=1, lesson_id=2, pattern="V + -고", meaning_vi="x", level=1, example_ko="x")
        ref = GrammarRefOut(pattern="V/A + -아/어요", lesson_id=1, lesson_title="Nền tảng 2")
        out = GrammarPointOut(**base, importance="must", built_from=[ref]).model_dump(mode="json")
        self.assertEqual(out["importance"], "must")
        self.assertEqual(out["built_from"][0]["pattern"], "V/A + -아/어요")
        self.assertEqual(out["built_into"], [])
        self.assertIsNone(GrammarPointOut(**base).model_dump(mode="json")["importance"])
        self.assertNotIn("builds_on", out)


if __name__ == "__main__":
    unittest.main()

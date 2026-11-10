"""«Hội thoại»: every dialogue plays as a chat, the learner's lines are picked out of four, and the
choices are other real lines, never the right one twice."""
import unittest

from app.services import chats, passages

DIALOGUES = [p for p in passages.all_passages() if p.kind == "dialogue"]


class ChatTests(unittest.TestCase):
    def test_every_dialogue_becomes_a_chat_with_four_choices_per_answer(self):
        self.assertGreater(len(DIALOGUES), 60)
        for p in DIALOGUES:
            group = passages.allowed_slugs(p.lesson, {d.lesson for d in DIALOGUES})
            ts = chats.turns(p, [d for d in DIALOGUES if d.lesson in group])
            self.assertEqual([t.ko for t in ts], [ln.ko.strip() for ln in p.lines])
            mine = [t for t in ts if t.mine]
            self.assertGreaterEqual(len(mine), 2, p.id)
            self.assertFalse(ts[0].mine, p.id)  # the other speaker opens
            for t in mine:
                self.assertEqual(len(t.options), chats.OPTIONS, (p.id, t.ko))
                self.assertEqual(len(set(t.options)), chats.OPTIONS, (p.id, t.ko))
                self.assertEqual(t.options.count(t.ko), 1)
                self.assertTrue(t.vi)

    def test_the_same_chat_comes_out_the_same_every_time(self):
        p = DIALOGUES[0]
        self.assertEqual(chats.turns(p, DIALOGUES), chats.turns(p, DIALOGUES))


if __name__ == "__main__":
    unittest.main()

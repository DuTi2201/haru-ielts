"""The lecture's slides (lesson_audio.build_template_lecture): the same script as before, a cue for
every line, and every cue pointing at something its slide holds."""
import unittest
from types import SimpleNamespace as NS

from app.services import lesson_audio as la
from app.services import lesson_seed as seed

BUNDLE = seed.load_all()


def source(s):
    lesson = NS(title=s.title, title_en=s.title_en, notes=[n.model_dump() for n in s.notes])
    vocab = [NS(headword=v.headword, meaning_vi=v.meaning_vi, usage_note_vi=v.note_vi, example_en=v.example_en, example_vi=v.example_vi) for v in s.vocab]
    grammar = [
        NS(pattern=g.pattern, meaning_vi=g.meaning_vi, usage_context_vi=g.usage_context_vi, note_vi=g.note_vi,
           example_en=g.example_en, example_vi=g.example_vi, contrasts=[c.model_dump() for c in g.contrasts])
        for g in s.grammar
    ]
    return la.source_from_rows(lesson, vocab, grammar)


def shows_of(slide: dict) -> set[str]:
    k = slide["kind"]
    if k == "title":
        return {"title", "title_en", "counts"}
    if k in ("section", "end"):
        return {"title"}
    if k == "word":
        return {"word", "note"} | {f"ex{i}" for i in range(len(slide["examples"]))} | {f"ex{i}_vi" for i in range(len(slide["examples"]))}
    if k == "review":
        return {"title"} | {f"w{i}" for i in range(len(slide["words"]))}
    if k == "grammar":
        n = len(slide["examples"])
        return (
            {"pattern", "meaning", "note", "tier"}
            | {f"s{i}" for i in range(len(slide["sections"]))}
            | {f"c{i}" for i in range(len(slide["contrasts"]))}
            | {f"ex{i}{x}" for i in range(n) for x in ("", "_vi", "_say")}
        )
    if k == "note":
        return {"body"}
    if k == "recap":
        return {"title"} | {f"ex{i}" for i in range(len(slide["examples"]))}
    raise AssertionError(k)


class SlideTests(unittest.TestCase):
    def test_every_line_has_a_cue_that_its_slide_can_show(self):
        n = 0
        for r in BUNDLE.lessons:
            if not r.seed.vocab and not r.seed.grammar:
                continue
            lec = la.build_template_lecture(source(r.seed))
            self.assertEqual(lec.script, la.build_template_script(source(r.seed)))
            lines = [x for x in lec.script.split("\n") if x.strip()]
            self.assertEqual(len(lec.lines), len(lines), r.seed.slug)
            last = -1
            for cue in lec.lines:
                self.assertGreaterEqual(cue.slide, last, r.seed.slug)  # the slides only move forward
                last = cue.slide
                if cue.show is not None:
                    self.assertIn(cue.show, shows_of(lec.slides[cue.slide]), (r.seed.slug, cue))
            n += 1
        self.assertEqual(n, 42)

    def test_a_word_slide_comes_in_with_its_word_and_its_meaning_follows_the_gap(self):
        r = BUNDLE.lessons[0]
        lec = la.build_template_lecture(source(r.seed))
        first_word = next(i for i, s in enumerate(lec.slides) if s["kind"] == "word")
        line = next(i for i, c in enumerate(lec.lines) if c.slide == first_word)
        self.assertEqual(lec.lines[line].show, "word")
        said = [x for x in lec.script.split("\n") if x.strip()][line]
        # the word, the gap to say it, then the meaning: two runs of one line (the screen shows the
        # meaning with the second run)
        self.assertIn(r.seed.vocab[0].headword.split("/")[0].strip()[:1], said)
        self.assertIn("...", said)


if __name__ == "__main__":
    unittest.main()

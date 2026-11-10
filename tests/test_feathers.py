"""Lông vũ: every lesson cut into feathers without losing or repeating anything, the lessons gathered
into the five chapters, and the stage, the station and the sparkle that follow from them."""
import unittest
from collections import Counter

from app.services import feathers as F
from app.services import lesson_seed as seed
from app.services.lesson_seed import question_ids


def _course() -> list[F.CourseLesson]:
    """The seeded lessons as the service sees them (fake ids for words and cards: their positions)."""
    out = []
    for n, r in enumerate(seed.load_all().lessons, start=1):
        s = r.seed
        topic = s.topic
        support = F.support_of(s.slug, topic)[0] if F.is_support(topic) else None
        vocab = [n * 1000 + i for i in range(len(s.vocab))]
        grammar = [n * 1000 + 500 + i for i in range(len(s.grammar))]
        out.append(
            F.CourseLesson(
                id=n,
                slug=s.slug,
                sort_order=s.sort_order,
                title=s.title,
                topic=topic,
                chapter=None if support else F.chapter_of(s.slug, s.level),
                support=support,
                feathers=tuple(F.partition(vocab, grammar, r.practice)),
            )
        )
    return sorted(out, key=lambda c: c.sort_order)


def _all_earned(lesson: F.CourseLesson) -> F.Record:
    rec = F.Record()
    for f in lesson.feathers:
        rec.met.update(f.items)
        rec.answered.setdefault(lesson.id, set()).update(f.questions)
        if f.part:
            rec.parts.setdefault(lesson.id, set()).add(f.part)
    return rec


def _merge(*recs: F.Record) -> F.Record:
    out = F.Record()
    for r in recs:
        out.met |= r.met
        for k, v in r.answered.items():
            out.answered.setdefault(k, set()).update(v)
        for k, v in r.parts.items():
            out.parts.setdefault(k, set()).update(v)
    return out


class PartitionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bundle = seed.load_all()
        cls.course = _course()

    def test_every_word_card_and_question_is_in_exactly_one_feather(self):
        for r, lesson in zip(sorted(self.bundle.lessons, key=lambda r: r.seed.sort_order), self.course, strict=True):
            with self.subTest(lesson=lesson.slug):
                items = Counter(k for f in lesson.feathers for k in f.items)
                self.assertTrue(all(n == 1 for n in items.values()))
                self.assertEqual(len(items), len(r.seed.vocab) + len(r.seed.grammar))
                qs = Counter(q for f in lesson.feathers for q in f.questions)
                self.assertTrue(all(n == 1 for n in qs.values()))
                want = {q for ex in (r.practice or {}).get("items", []) for q in question_ids(ex)}
                self.assertEqual(set(qs), want)

    def test_feathers_are_small(self):
        for lesson in self.course:
            for f in lesson.feathers:
                with self.subTest(lesson=lesson.slug, feather=f.id):
                    if f.kind == "vocab":
                        self.assertLessEqual(len(f.items), F.WORDS_PER_FEATHER)
                    elif f.kind == "grammar":
                        self.assertLessEqual(len(f.items), F.PATTERNS_PER_FEATHER)
                    elif f.kind == "practice" and f.id != "check":
                        self.assertLessEqual(len(f.questions), 30)  # one exercise may be longer than 15
                    self.assertTrue(f.label)
                self.assertEqual(len({f.id for f in lesson.feathers}), len(lesson.feathers))

    def test_all_feathers_earned_means_studied(self):
        lesson = self.course[0]
        rec = _all_earned(lesson)
        self.assertTrue(all(F.lesson_status(lesson, rec)))
        one_word_short = F.Record(met=set(rec.met) - {lesson.feathers[0].items[0]}, answered=rec.answered)
        self.assertEqual(F.lesson_status(lesson, one_word_short).count(False), 1)

    def test_about_five_minutes_a_feather(self):
        total = sum(len(l.feathers) for l in self.course)
        self.assertGreater(total, 200)
        per_lesson = [len(l.feathers) for l in self.course]
        self.assertLessEqual(max(per_lesson), 20)


class ChapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.course = _course()

    def test_lessons_by_chapter_and_constellation(self):
        chapters = Counter(l.chapter for l in self.course if l.chapter)
        self.assertEqual(chapters, {1: 11, 2: 10, 3: 11, 4: 10})
        self.assertEqual(max(l.sort_order for l in self.course if l.chapter == 1), 11)

    def test_a_new_main_topic_falls_in_by_level(self):
        self.assertEqual(F.chapter_of("mot-chu-de-moi-01", 1), 1)
        self.assertEqual(F.chapter_of("mot-chu-de-moi-01", 4), 3)
        self.assertEqual(F.chapter_of("mot-chu-de-moi-01", 6), 4)
        self.assertEqual(F.support_of("phong-van-01", "Bổ trợ · Phỏng vấn")[0], "topic:Bổ trợ · Phỏng vấn")

    def test_stage_follows_the_chapters_finished_in_a_row(self):
        none = F.tally(self.course, F.Record())
        self.assertEqual((none.stage, none.station, none.sparkle), (1, False, 0))
        ch1 = _merge(*[_all_earned(l) for l in self.course if l.chapter == 1])
        self.assertEqual(F.tally(self.course, ch1).stage, 2)  # the blindfold falls
        # chapter II alone, without I, moves nothing
        ch2 = _merge(*[_all_earned(l) for l in self.course if l.chapter == 2])
        self.assertEqual(F.tally(self.course, ch2).stage, 1)
        upto3 = _merge(*[_all_earned(l) for l in self.course if l.chapter in (1, 2, 3)])
        self.assertEqual(F.tally(self.course, upto3).stage, 4)  # the sword
        every = _merge(*[_all_earned(l) for l in self.course if l.chapter])
        self.assertEqual(F.tally(self.course, every).stage, 5)  # the crown

    def test_the_station_halfway_through_chapter_three(self):
        rec = _merge(*[_all_earned(l) for l in self.course if l.chapter in (1, 2) or (l.chapter == 3 and l.sort_order <= 27)])
        t = F.tally(self.course, rec)
        self.assertEqual((t.stage, t.station), (3, True))

    def test_the_entry_check_credits_the_lessons_it_skipped(self):
        t = F.tally(self.course, F.Record(), placed_at=12)
        self.assertEqual(t.stage, 2)
        self.assertEqual(t.chapters[1].earned, 0)
        self.assertEqual(t.chapters[1].credited, t.chapters[1].total)

    def test_starlight_sparkles_and_finished_topics_give_relics(self):
        self.assertEqual([F.sparkle_of(n) for n in (0, 9, 10, 59, 60, 110)], [0, 0, 1, 1, 2, 3])


if __name__ == "__main__":
    unittest.main()

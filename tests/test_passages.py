"""The daily readings and dialogues (app/seed/passages): their format, and that each text only
uses what the learner has met by its lesson.

The check against the lessons (every grammar card exists and is really in the text, every key word
is a word of that lesson or an earlier one) is `passages.check`. On top of it, a second guard:
a text must not contain the telltale form of a grammar point that is taught LATER (a table of
surface signs below) — a learner who has not reached 도록 or 수록 should not be handed a text full of it.
That guard is a heuristic: a false alarm is fixed by rewording the text or sharpening the sign."""
import re
import unittest
from collections import Counter

from app.services import lesson_seed as seed
from app.services import passages

BUNDLE = seed.load_all()
INFOS = passages.lesson_infos(BUNDLE.lessons)
LOADED, LOAD_PROBLEMS = passages.load()

# Syllables that end in ㄴ / ㄹ / ㅂ (for signs like "-(으)ㄹ 만하다", "-(으)ㄴ 결과").
def _ending_in(jong: int) -> str:
    return "".join(chr(0xAC00 + i * 28 + jong) for i in range(19 * 21))


NN, LL, BB = _ending_in(4), _ending_in(8), _ending_in(17)
HANGUL = "가-힣"

# (surface sign, [lessons that teach it]) — the text may carry the sign only when one of the lessons
# that teach it is among the lessons it may draw on.
SH = lambda n, slug: f"sinh-hoat-{n:02d}-{slug}"  # noqa: E731
L2, L3, L4, L5, L6, L7, L8, L9 = (
    "sinh-hoat-02-viec-nha", "sinh-hoat-03-an-uong", "sinh-hoat-04-mua-sam", "sinh-hoat-05-di-lai",
    "sinh-hoat-06-hoc-lam", "sinh-hoat-07-giai-tri", "sinh-hoat-08-suc-khoe", "sinh-hoat-09-nhat-ky",
)
Q1, Q2, Q3, Q4, Q5, Q6, Q7, Q8, Q9, Q10, Q11 = (
    "quan-he-01-gia-dinh", "quan-he-02-dien-thoai-hen", "quan-he-03-sinh-nhat-le-tet", "quan-he-04-tim-duong",
    "quan-he-05-noi-o", "quan-he-06-hang-xom-rac", "quan-he-07-moi-truong", "quan-he-08-thoi-tiet-1",
    "quan-he-09-thoi-tiet-2", "quan-he-10-du-lich", "quan-he-11-ky-nghi-van-hoa",
)
N1, N2, N3, N4, N5 = (
    "nhap-canh-01-san-bay-may-bay", "nhap-canh-02-nhap-canh-hai-quan", "nhap-canh-03-bieu-mau",
    "nhap-canh-04-the-cu-tru", "nhap-canh-05-ve-truong",
)
LATER_SIGNS: list[tuple[str, list[str], str]] = [
    (r"고 있|수 (있|없)|지 마[세시]|[아어해] 놓|느라고|는 바람에", [L2, Q2], "sinh-hoat-02"),
    (r"고 싶|것 같|는 동안|까요|[아어해] (보|봐)|" + f"[{BB}]시다|읍시다", [L3], "sinh-hoat-03"),
    (r"(?<=[가-힣])[아어해]서|" + f"[{LL}] 만하|을 만하|밖에 (없|안|못)", [L4, N2], "sinh-hoat-04"),
    (r"[아어해]야 (하|해|되|돼)|는 길에|는 데 (걸|들|시간|돈)|는데도|은데도|" + f"[{NN}]데도|(?<![{BB}])니까", [L5, N3, N5], "sinh-hoat-05"),
    (r"려고|[아어해]도[ ,.?!]|기 전에|면서|다 보면", [L6, N2, N4], "sinh-hoat-06"),
    (r"적이 (있|없)|" + f"[{LL}]게요|[{LL}]래요|을게요|을래요|러 (가|오)|에 비해|{NN} 결과|은 결과|냐고", [L7, N2, N3], "sinh-hoat-07"),
    (r"[아어해]도 (되|돼)|면 안 (되|돼)|는 게 (좋|낫)|게 되|지 않으면 안|에 (좋|나쁘)", [L8, N2, N5], "sinh-hoat-08"),
    (r"때문에|고 나서|" + f"{NN} 후에|은 후에|" + r"(?<![니시])다\.|반면에|그러나|첫째|결론적으로|고 나면", [L9, N4, Q7, Q11], "sinh-hoat-09"),
    (r"께서|드려요|드립니다|드릴|시기 바랍|십시오|라도", [Q1, N1], "quan-he-01"),
    (r"려던 참|고자 하|수 있겠", [Q2], "quan-he-02"),
    (r"곤 (해|했|하)|셈이|위해", [Q3], "quan-he-03"),
    (r"면 (되|돼)|(?<=[가-힣])다가[ ,]|" + f"{NN} 다음에|은 다음에", [Q4, N4], "quan-he-04"),
    (r"려면|데다가|자마자", [Q5, N4], "quan-he-05"),
    (r"라서", [Q5, N2], "quan-he-05"),
    (r"도록|로 인해|로 인한|달라고|말라고|채로|더라도", [Q6], "quan-he-06"),
    (r"필요가 (있|없)", [Q7], "quan-he-07"),
    (r"[아어해](졌|져)|지도 모르|편이|것으로 (예상|보이|전망)", [Q8], "quan-he-08"),
    (r"에 비하면|에 따르면|수록", [Q9], "quan-he-09"),
    (r"계획이|예정이|수밖에|경우|에 따라|에 따른", [Q10, N1, N3, N5], "quan-he-10"),
    (r"었으면 좋겠|았으면 좋겠|더라고요|덕분에|(?<=[가-힣])라는 [가-힣]", [Q11], "quan-he-11"),
]


def _tidy(rows):
    return [(re.compile(rx), set(teachers), label) for rx, teachers, label in rows]


LATER = _tidy(LATER_SIGNS)


def _lesson_set(slug):
    return passages.allowed_slugs(slug, INFOS.keys())


def _make(**over):
    base = dict(
        id="sinh-hoat-01-x1",
        lesson="sinh-hoat-01-buoi-sang",
        kind="reading",
        title_ko="아침",
        title_vi="Buổi sáng",
        scene_vi=None,
        speakers={},
        lines=tuple(passages.Line(who="N", ko=ko, vi="vi") for ko in (
            "저는 아침에 일어나요.", "알람을 맞췄지만 늦잠을 자요.", "피곤할 때는 샤워를 해요.", "그리고 도시락을 들고 출근해요.",
        )),
        uses=(passages.Use(pattern="V/A + -지만", regex="맞췄지만"), passages.Use(pattern="V/A + -(으)ㄹ 때", regex="피곤할 때")),
        keywords=tuple(passages.Keyword(word=w, seen=s) for w, s in (("알람", "알람"), ("늦잠", "늦잠"), ("도시락", "도시락"))),
        glossary=(),
        questions=tuple(passages.Question(q_vi="?", options=["a", "b", "c"], answer=0, explain_vi="x") for _ in range(2)),
    )
    base.update(over)
    return passages.Passage(**base)


class CheckTests(unittest.TestCase):
    """`passages.check` on small, made-up texts: one thing wrong at a time."""

    def problems(self, **over):
        return passages.check([_make(**over)], INFOS)

    def test_a_sound_text_has_no_problems(self):
        self.assertEqual(self.problems(), [])

    def test_a_card_that_is_not_in_the_lessons_so_far_is_refused(self):
        bad = (passages.Use(pattern="V/A + -지만", regex="맞췄지만"), passages.Use(pattern="V + -도록", regex="도록"))
        self.assertTrue(any("not a card" in p for p in self.problems(uses=bad)))

    def test_a_pattern_that_is_not_in_the_text_is_refused(self):
        bad = (passages.Use(pattern="V/A + -지만", regex="맞췄지만"), passages.Use(pattern="V/A + -(으)ㄹ 때", regex="갈 때"))
        self.assertTrue(any("is not in the text" in p for p in self.problems(uses=bad)))

    def test_a_text_needs_a_card_of_its_own_lesson(self):
        own_free = (passages.Use(pattern="V + -고", regex="들고"),)
        self.assertTrue(any("2-5" in p for p in self.problems(uses=own_free)))

    def test_a_key_word_must_be_a_word_of_the_lessons_so_far_and_in_the_text(self):
        kws = (passages.Keyword(word="알람", seen="알람"), passages.Keyword(word="늦잠", seen="늦잠"), passages.Keyword(word="도시락", seen="점심"))
        self.assertTrue(any("is not in the text" in p for p in self.problems(keywords=kws)))
        kws = (passages.Keyword(word="알람", seen="알람"), passages.Keyword(word="늦잠", seen="늦잠"), passages.Keyword(word="환승 할인", seen="알람"))
        self.assertTrue(any("not in sinh-hoat-01" in p for p in self.problems(keywords=kws)))

    def test_a_dialogue_names_its_two_speakers_and_the_scene(self):
        lines = tuple(passages.Line(who=w, ko="네, 알람을 맞췄지만 늦잠을 자요.", vi="vi") for w in "FMFMFM")
        found = self.problems(kind="dialogue", lines=lines)
        self.assertTrue(any("two speakers" in p for p in found))
        self.assertTrue(any("scene_vi" in p for p in found))

    def test_a_reading_is_one_voice(self):
        lines = tuple(passages.Line(who=w, ko="알람을 맞췄지만 늦잠을 자요.", vi="vi") for w in "NNNF")
        self.assertTrue(any("narrated" in p for p in self.problems(lines=lines)))

    def test_a_reading_read_aloud_at_once_stays_within_the_limit(self):
        line = passages.Line(who="N", ko="알람을 맞췄지만 늦잠을 잤어요. " * 8, vi="vi")
        self.assertTrue(any("read aloud at once" in p for p in self.problems(lines=(line,) * 5)))

    def test_a_word_of_the_lessons_is_not_glossed(self):
        self.assertTrue(any("no gloss needed" in p for p in self.problems(glossary=(passages.Gloss(ko="알람", vi="x"),))))
        self.assertEqual(self.problems(glossary=(passages.Gloss(ko="손에 들다", vi="x", seen="들고"),)), [])

    def test_an_answer_must_be_one_of_the_options(self):
        qs = (passages.Question(q_vi="?", options=["a", "b", "c"], answer=3, explain_vi="x"),) * 2
        self.assertTrue(any("answer is not one of the options" in p for p in self.problems(questions=qs)))


class LessonRangeTests(unittest.TestCase):
    def test_a_text_for_topic_two_may_use_topic_one_and_itself_up_to_its_lesson(self):
        allowed = passages.allowed_slugs("quan-he-03-sinh-nhat-le-tet", INFOS.keys())
        self.assertIn("sinh-hoat-09-nhat-ky", allowed)
        self.assertIn("quan-he-02-dien-thoai-hen", allowed)
        self.assertNotIn("quan-he-04-tim-duong", allowed)
        self.assertNotIn("nhap-canh-01-san-bay-may-bay", allowed)

    def test_the_entry_course_does_not_assume_topic_two(self):
        allowed = passages.allowed_slugs("nhap-canh-03-bieu-mau", INFOS.keys())
        self.assertIn("sinh-hoat-05-di-lai", allowed)
        self.assertIn("nhap-canh-02-nhap-canh-hai-quan", allowed)
        self.assertNotIn("quan-he-01-gia-dinh", allowed)

    def test_topic_one_stops_at_its_own_lesson(self):
        allowed = passages.allowed_slugs("sinh-hoat-03-an-uong", INFOS.keys())
        foundation = {s for s in INFOS if s.startswith("sinh-hoat-00-")}  # the foundation lessons (5, cut into 16) come first
        self.assertEqual(len(foundation), 16)
        self.assertEqual(
            {s for s in allowed if s.startswith("sinh-hoat")},
            foundation | {"sinh-hoat-01-buoi-sang", "sinh-hoat-02-viec-nha", "sinh-hoat-03-an-uong"},
        )


class BankTests(unittest.TestCase):
    """The texts that ship."""

    def test_every_file_loads(self):
        self.assertEqual(LOAD_PROBLEMS, [])
        self.assertTrue(LOADED)

    def test_every_text_is_sound(self):
        self.assertEqual(passages.check(LOADED, INFOS), [])

    def test_every_lesson_with_cards_has_a_dialogue_and_a_reading(self):
        self.assertEqual(passages.coverage(LOADED, INFOS), [])
        covered = {INFOS[p.lesson].group or p.lesson for p in LOADED}
        # review lessons and Bảng chữ cái carry no cards of their own, so they carry no texts; the
        # parts of a Nền tảng lesson share the texts written for the whole lesson
        groups = {i.group or s for s, i in INFOS.items()}
        self.assertEqual(len(covered), len(groups) - 6)

    def test_a_lesson_with_cards_and_no_text_is_reported(self):
        some = [p for p in LOADED if p.lesson != "sinh-hoat-02-viec-nha"]
        self.assertEqual(
            passages.coverage(some, INFOS),
            ["sinh-hoat-02-viec-nha: no dialogue written for this lesson",
             "sinh-hoat-02-viec-nha: no reading written for this lesson"],
        )
        only_readings = [p for p in LOADED if not (p.lesson == "quan-he-03-sinh-nhat-le-tet" and p.kind == "dialogue")]
        self.assertEqual(passages.coverage(only_readings, INFOS), ["quan-he-03-sinh-nhat-le-tet: no dialogue written for this lesson"])

    def test_ids_follow_their_lesson_and_kind(self):
        for p in LOADED:
            m = re.match(r"^(?P<lesson>[a-z-]+-\d\d)-(?P<k>[dr])(?P<n>\d+)$", p.id)
            self.assertIsNotNone(m, p.id)
            self.assertTrue(p.lesson.startswith(m.group("lesson") + "-"), f"{p.id} sits in {p.lesson}")
            self.assertEqual(m.group("k"), "d" if p.kind == "dialogue" else "r", p.id)

    def test_no_text_carries_the_sign_of_a_grammar_point_taught_later(self):
        found = []
        for p in LOADED:
            allowed = _lesson_set(p.lesson)
            for line in p.lines:
                for rx, teachers, label in LATER:
                    if teachers & allowed:
                        continue
                    m = rx.search(line.ko)
                    if m:
                        found.append(f"{p.id}: {m.group(0)!r} ({label}) in “{line.ko}”")
        self.assertEqual(found, [])

    def test_the_right_answer_is_not_always_in_the_same_place(self):
        counts = Counter(q.answer for p in LOADED for q in p.questions)
        self.assertGreater(len(counts), 1)
        self.assertLessEqual(max(counts.values()) / sum(counts.values()), 0.6, dict(counts))

    def test_every_dialogue_line_and_reading_has_a_translation_that_is_not_the_korean(self):
        for p in LOADED:
            for line in p.lines:
                self.assertNotEqual(line.vi.strip(), line.ko.strip(), p.id)
                self.assertFalse(re.search(r"[가-힣]{4,}", line.vi), f"{p.id}: Korean left in a translation: {line.vi}")

    def test_the_two_voices_of_a_dialogue_are_a_woman_and_a_man(self):
        self.assertEqual(passages.VOICE_OF["F"], "ko-female-1")
        self.assertEqual(passages.VOICE_OF["M"], "ko-male-1")


if __name__ == "__main__":
    unittest.main()

"""Week 2 · Day 7 (build day 27, careful listening, "The Luddites"): the measurable gates of lesson 44
(docs/QUALITY_LESSON44.md) applied to its four hand-written lectures, the listening method of the course, and the book's key for questions 21-30. Pure tests: no network, no database."""
import importlib.util
import itertools
import re
import sys
from pathlib import Path
from types import SimpleNamespace as NS

import pytest

from app.services import lecture_voice, lesson_audio, lesson_seed

G1 = Path(__file__).resolve().parents[1] / "scripts" / "g1"
sys.path.insert(0, str(G1))
_spec = importlib.util.spec_from_file_location("lecture_w2d7", G1 / "lecture_w2d7.py")
L = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(L)
import day27 as D  # noqa: E402

BUNDLE = lesson_seed.load_all()
DAY = next(x.seed for x in BUNDLE.lessons if x.seed.slug.startswith("g1-d27-"))
SITTINGS = [1, 2, 3, 4]  # words 1, words 2, prepare and listen, go over the answers
AUTHORED = {1: L.SITTING_1, 2: L.SITTING_2, 3: L.PRE, 4: L.POST}


def _lecture(n: int) -> lesson_audio.Lecture:
    vr = [NS(headword=v.headword, meaning_vi=v.meaning_vi, usage_note_vi=v.note_vi, example_en=v.example_en,
             example_vi=v.example_vi, pos=v.pos, pron_en=v.pron) for v in DAY.vocab]
    les = NS(title=DAY.title, title_en=DAY.title_en, notes=[],
             sessions=[s.model_dump(mode="json", exclude_none=True) for s in DAY.sessions])
    src, _v, _g = lesson_audio.sitting_source(les, vr, [], n)
    return lesson_audio.build_template_lecture(src)


def _minutes(script: str) -> float:
    t = 0.0
    for r in lecture_voice.split_runs(script):
        t += len(r.text.split()) / (2.4 if r.lang == lecture_voice.KO else 3.8) + r.pause_after_ms / 1000
    return t / 60


def _says(lecture: list[dict]) -> list[str]:
    return [ln["say"] for s in lecture for ln in s.get("lines", []) if "say" in ln]


def test_seed_is_sound_and_the_day_sits_in_week_two():
    assert BUNDLE.problems == []
    assert DAY.title == "Tuần 2 · Ngày 7 · Nghe kỹ: The Luddites" and DAY.topic == "Tuần 2 · Công nghệ (Technology)"
    assert DAY.sort_order == 127
    titles = [s.title_vi for s in DAY.sessions]
    # the words, prepare and listen, then go over the answers
    assert titles == [*L.TITLES, *L.LISTEN_TITLES]
    assert DAY.sessions[2].check == ["G1D27L1"] and DAY.sessions[3].check == ["G1D27M1"]
    assert DAY.grammar == []


def test_words_come_from_the_recording_and_the_questions():
    assert [v.headword for v in DAY.vocab] == [w for ws in L.S_WORDS for w in ws]
    text = (" ".join(t for _sp, t, _vi in D.TURNS) + " " + " ".join(D.OP.values()) + " " + " ".join(D.PR.values()) + " " + " ".join(D.CM.values())).lower()
    stems = {"threaten": "threatened", "retire": "retiring", "qualification": "qualifications"}
    for v in DAY.vocab:
        assert stems.get(v.headword, v.headword) in text, v.headword
    pos = [v.pos for v in DAY.vocab]
    assert pos.count("V") + pos.count("N") >= 9
    assert {v.headword for v in DAY.vocab if v.priority == "recognize"} == {"census"}
    assert {v.headword: v.pron for v in DAY.vocab} == L.PRON


@pytest.mark.parametrize("n", SITTINGS)
def test_gate_length(n):
    assert 2.5 <= _minutes(_lecture(n).script) <= 15.5


@pytest.mark.parametrize("n", SITTINGS)
def test_gate_no_template_boilerplate_is_read_out(n):
    script = _lecture(n).script
    for banned in ("0 từ vựng", "Phần một", "Phần hai", "Nghĩa là", "Lời thầy", "Lỗi người Việt hay mắc:", "Mẫu số", "Bạn nhắc lại nhé"):
        assert banned not in script, banned


@pytest.mark.parametrize("n", SITTINGS)
def test_gate_an_english_sentence_is_read_by_one_voice(n):
    lec = _lecture(n)
    runs = lecture_voice.split_runs(lec.script)
    for r in runs:
        if r.lang == lecture_voice.KO:
            assert not re.search(r"[À-ỹĐđ]", r.text), r.text
    lines = [ln for ln in lec.script.split("\n") if ln.strip()]
    for li, group in itertools.groupby(runs, key=lambda r: r.line):
        group = list(group)
        if not re.search(r"[À-ỹĐđ]", lines[li]):
            assert len(group) == 1 and group[0].lang == lecture_voice.KO, lines[li]


@pytest.mark.parametrize("n", SITTINGS)
def test_gate_narration_holds_no_long_english_phrase_and_no_bare_letter(n):
    for say in _says(AUTHORED[n]):
        for r in lecture_voice.split_runs(say):
            if r.lang != lecture_voice.KO:
                continue
            for chunk in r.text.split(","):  # a list of single words is not a phrase
                assert len(chunk.split()) < 3, (say, r.text)
        assert not re.search(r"(?<![\w-])[A-Za-z](?![\w-])", say), say  # no paragraph letter, no model letter


@pytest.mark.parametrize("n", SITTINGS)
def test_gate_no_comma_before_va_in_spoken_vietnamese(n):
    # the Vietnamese Chirp voice garbles a multi-sentence run with ", và" (measured 2026-11-25: 7 of 8 takes nonsense,
    # 0 of 8 without the comma); keep it out of everything the voice reads
    assert ", và " not in _lecture(n).script


@pytest.mark.parametrize("n", SITTINGS)
def test_gate_inquiry_before_rule(n):
    lec = _lecture(n)
    kinds = [s["kind"] for s in lec.slides]
    assert kinds[0] == "title" and kinds[-1] == "end"
    if n in (1, 2):
        assert kinds[-2] == "recap"
    assert "?" in " ".join(lec.script.split("\n")[:3])
    for i, s in enumerate(lec.slides):
        if s["kind"] != "scene" or "rule" not in (s.get("data") or {}):
            continue
        shows = [ln.show for ln in lec.lines if ln.slide == i and ln.show]
        assert shows.index("rule") >= 2 and shows[-1] == "rule", (s["title"], shows)


@pytest.mark.parametrize("n", SITTINGS)
def test_gate_every_piece_of_a_picture_is_brought_in_by_a_line(n):
    lec = _lecture(n)
    for i, s in enumerate(lec.slides):
        if s["kind"] != "scene":
            continue
        d = s["data"]
        pieces = {k for k in ("quote", "rule") if d.get(k)}
        pieces |= {r["key"] for r in d.get("rows", []) + d.get("panels", [])}
        if s["visual"] == "para_filter":
            pieces |= {"keep", "drop", "sum", "main", "value"}
        shown = {ln.show for ln in lec.lines if ln.slide == i and ln.show}
        assert pieces <= shown, (s["title"], pieces - shown)


def test_gate_each_vocabulary_sitting_teaches_its_own_words():
    for n, words in ((1, L.S_WORDS[0]), (2, L.S_WORDS[1])):
        assert [s["headword"] for s in _lecture(n).slides if s["kind"] == "word"] == words
    for n in (3, 4):
        assert not [s for s in _lecture(n).slides if s["kind"] == "word"]


def test_the_script_is_the_book_and_the_questions_carry_the_book_key():
    assert len(D.TURNS) == 26 and {sp for sp, _t, _v in D.TURNS} == {"M", "F"}
    script = " ".join(t for _sp, t, _vi in D.TURNS)
    for line in ("ultimately, they didn't achieve anything", "I can see why the Luddites felt so threatened",
                 "I'm not so sure about that", "I can't see how people are about to have more leisure time",
                 "there are more of them than ever", "people's earning power has gone up", "much more responsibility and higher status",
                 "Now it's less than 0.2%", "this sector will see huge growth", "make most of the jobs they do now redundant"):
        assert line in script, line
    key = [q[1].split(".")[0] for q in D.QS]
    assert key == ["A", "E", "B", "D", "G", "E", "B", "C", "F", "A"]
    for q in D.QS:
        assert 4 <= len(q[4]) <= 5 and q[1] in q[4] and sorted([q[1], *q[2]]) == sorted(q[4]) and len(q[3]) > 60
    # the other right answer of a choose-two pair is never offered
    assert not any(o.startswith("E.") for o in D.QS[0][4]) and not any(o.startswith("A.") for o in D.QS[1][4])
    assert not any(o.startswith("D.") for o in D.QS[2][4]) and not any(o.startswith("B.") for o in D.QS[3][4])
    # comments that could be argued for that job are left out
    assert not any(o.startswith("C.") for o in D.QS[9][4]) and not any(o.startswith("G.") for o in D.QS[5][4])
    ex = next(e for e in BUNDLE.lessons if e.seed.slug.startswith("g1-d27-"))
    assert ex is not None


def test_gate_the_listening_method_is_taught():
    says = " ".join(" ".join(_says(lec)) for lec in AUTHORED.values())
    for phrase in ("đọc câu hỏi trước", "thái độ", "mốc thời gian", "hiện tại hoàn thành", "người ta tưởng", "chốt ý",
                   "đọc to câu đúng", "cách nói khác", "nghe lại bao nhiêu lần cũng được"):
        assert phrase.lower() in says.lower(), phrase


BANNED = ("Sách", "Cambridge", "Destination", "thầy", "Thầy", "Minh", "Trích", "trang 5", "Test 3")


def test_gate_learner_facing_text_names_no_book_and_no_teacher():
    for n in SITTINGS:
        lec = _lecture(n)
        for b in BANNED:
            assert b not in lec.script, (n, b)
            assert b not in repr(lec.slides), (n, b)
    for s in DAY.sessions:
        for b in BANNED:
            assert b not in s.title_vi + s.can_do_vi + (s.use_vi or ""), (s.title_vi, b)

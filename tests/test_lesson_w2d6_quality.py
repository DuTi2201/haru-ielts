"""Week 2 · Day 6 (build day 26, slow reading of "The steam car"): the measurable gates of lesson 44
(docs/QUALITY_LESSON44.md) applied to its four hand-written lectures, the reading method of session 4 as
docs/WEEK2_PLAN.md (day 6) asks, and the book's key for questions 14-26. Pure tests: no network, no database."""
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
_spec = importlib.util.spec_from_file_location("lecture_w2d6", G1 / "lecture_w2d6.py")
L = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(L)
import day26 as D  # noqa: E402

BUNDLE = lesson_seed.load_all()
DAY = next(x.seed for x in BUNDLE.lessons if x.seed.slug.startswith("g1-d26-"))
SITTINGS = [1, 2, 3, 4]  # read actively, words 1, words 2, long sentences
AUTHORED = {1: L.READ_1, 2: L.SITTING_1, 3: L.SITTING_2, 4: L.READ_2}


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
    assert DAY.title == "Tuần 2 · Ngày 6 · Đọc chậm: The steam car" and DAY.topic == "Tuần 2 · Công nghệ (Technology)"
    assert DAY.sort_order == 126
    titles = [s.title_vi for s in DAY.sessions]
    # the method first, the words, long sentences, and the questions last
    assert titles[:4] == [L.READ_TITLES[0], *L.TITLES, L.READ_TITLES[1]]
    assert titles[4:6] == ["Đọc chậm · Câu 14–20 · tiêu đề của đoạn", "Đọc chậm · Câu 21–23 · chọn đáp án"]
    assert titles[6].startswith("Rèn luyện")
    assert len(titles) == 7 and DAY.grammar == []
    assert all(len(s.check) <= 24 for s in DAY.sessions)


def test_words_come_from_the_passage_verbs_and_nouns_first():
    assert [v.headword for v in DAY.vocab] == [w for ws in L.S_WORDS for w in ws]
    text = D.TEXT.lower()
    stems = {"phase out": "phased out", "shortcoming": "shortcomings", "emission": "emissions", "enhancement": "enhancements",
             "deposit": "deposits", "glitch": "glitches", "accelerate": "accelerate", "inherit": "inherited", "fold": "folded",
             "comprise": "comprised", "prototype": "prototype"}
    for v in DAY.vocab:
        assert stems.get(v.headword, v.headword) in text, v.headword
    pos = [v.pos for v in DAY.vocab]
    assert pos.count("V") + pos.count("N") >= 12
    assert {v.headword for v in DAY.vocab if v.priority == "recognize"} == {"rekindle", "feat", "glitch"}
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
def test_gate_inquiry_before_rule(n):
    lec = _lecture(n)
    kinds = [s["kind"] for s in lec.slides]
    assert kinds[0] == "title" and kinds[-1] == "end"
    if n in (2, 3):
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
    for n, words in ((2, L.S_WORDS[0]), (3, L.S_WORDS[1])):
        assert [s["headword"] for s in _lecture(n).slides if s["kind"] == "word"] == words
    for n in (1, 4):
        assert not [s for s in _lecture(n).slides if s["kind"] == "word"]


def test_the_highlighted_paragraphs_are_the_passage_word_for_word():
    for k, marked in L.MARK.items():
        assert "".join(g["t"] for g in L.segs(marked)) == D.PARAS[k], k
    assert len(D.PARAS) == 7 and list(D.PARAS) == list("ABCDEFG")


def test_gate_the_reading_method_is_taught():
    says = " ".join(" ".join(_says(lec)) for lec in AUTHORED.values())
    for phrase in ("bảy phút", "từ chuyên ngành", "tra bằng hình ảnh", "danh từ chính", "chủ ngữ chính", "động từ chính",
                   "bản tóm tắt tốt nhất của cả đoạn", "mạch thông tin", "nghĩa bóng", "ngữ pháp khó đọc không phải ngữ pháp hay",
                   "chưa cần mẹo", "quá khứ hoàn thành", "trí nhớ dài hạn"):
        assert phrase in says, phrase
    script = "\n".join(_lecture(n).script for n in SITTINGS)
    for sentence in ("A book, which was given to me, is Harry Potter", "A book, given to me, is Harry Potter",
                     "It comprised parts taken from a wrecked early steam car but reconfigured",
                     "The new engine design, though innovative, was still plagued with serious glitches",
                     "But these early cars inherited steam's weaknesses along with its strengths"):
        assert sentence in script, sentence
    # the jargon of the plan and the long noun phrases
    rows = {r["head"] for s in L.READ_1 if s["kind"] == "scene" for r in s["data"].get("rows", [])}
    assert {"boilers", "hand-crank starters", "pistons", "kerosene"} <= rows
    nouns = {r["en"] for s in L.READ_2 if s["kind"] == "scene" for r in s["data"].get("rows", [])}
    assert {"a key-based ignition in the cabin", "numerous improvements over previous steam cars"} <= nouns


def test_the_questions_carry_the_book_key():
    def picked(q):
        return q[1][0]
    assert [picked(q).split(".")[0] for q in D.HEAD_QS] == ["iii", "viii", "vi", "v", "vii", "i", "iv"]
    for q in D.HEAD_QS:
        assert len(q[3]) == 5 and q[1][0] in q[3] and sorted(q[1]) == sorted(q[3])
        assert len(q[2]) > 80
    assert not any(o.startswith("ii.") for o in D.HEAD_QS[6][3])  # "never a financial success" could be read as heading ii
    assert [picked(q) for q in D.MC_QS] == ["Its success was short-lived.", "needed several attempts to achieve a competitive model.",
                                            "raised financial capital."]
    import book_items as BK
    sec = {code: lines for day, code, *_rest, lines in BK.SECTIONS if day == 26}
    key = [ln.split(" | ")[1] for ln in sec["W6S"]]
    assert key == ["speed;Speed", "fifty;50;Fifty", "strict;Strict"]
    ids = {i for s in DAY.sessions for i in s.check}
    assert {f"G1D26KW6S-{k}" for k in (1, 2, 3)} | {"G1D26RP1", "G1D26RP2", "G1D26M1", "G1D26M2"} <= ids


BANNED = ("Sách", "Cambridge", "Destination", "thầy", "Thầy", "Minh", "Trích", "trang 6", "Test 3", "Urban")


def test_gate_learner_facing_text_names_no_book_and_no_teacher():
    for n in SITTINGS:
        lec = _lecture(n)
        for b in BANNED:
            assert b not in lec.script, (n, b)
            assert b not in repr(lec.slides), (n, b)
    for s in DAY.sessions[:6]:
        for b in BANNED:
            assert b not in s.title_vi + s.can_do_vi + (s.use_vi or ""), (s.title_vi, b)

"""Week 3 · Day 3 (build day 33, appointments, present evidence, the present simple for the future): the measurable gates of lesson 44 (docs/QUALITY_LESSON44.md)
applied to its two hand-written lectures, the voice gates of Week 2, and the corrections of docs/WEEK3_PLAN.md.
Pure tests: no network, no database."""
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
_spec = importlib.util.spec_from_file_location("lecture_w3d3", G1 / "lecture_w3d3.py")
L = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(L)
import book_items as BK  # noqa: E402

BUNDLE = lesson_seed.load_all()
DAY = next(x.seed for x in BUNDLE.lessons if x.seed.slug.startswith("g1-d33-"))
AUTHORED = {1: L.SITTING_1, 2: L.SITTING_2}


def _lecture(n: int) -> lesson_audio.Lecture:
    vr = [NS(headword=v.headword, meaning_vi=v.meaning_vi, usage_note_vi=v.note_vi, example_en=v.example_en,
             example_vi=v.example_vi, pos=v.pos, pron_en=v.pron) for v in DAY.vocab]
    gr = [NS(pattern=g.pattern, meaning_vi=g.meaning_vi, usage_context_vi=g.usage_context_vi, note_vi=g.note_vi,
             example_en=g.example_en, example_vi=g.example_vi, contrasts=[]) for g in DAY.grammar]
    les = NS(title=DAY.title, title_en=DAY.title_en, notes=[],
             sessions=[s.model_dump(mode="json", exclude_none=True) for s in DAY.sessions])
    src, _v, _g = lesson_audio.sitting_source(les, vr, gr, n)
    return lesson_audio.build_template_lecture(src)


def _minutes(script: str) -> float:
    t = 0.0
    for r in lecture_voice.split_runs(script):
        t += len(r.text.split()) / (2.4 if r.lang == lecture_voice.KO else 3.8) + r.pause_after_ms / 1000
    return t / 60


def _says(lecture: list[dict]) -> list[str]:
    return [ln["say"] for s in lecture for ln in s.get("lines", []) if "say" in ln]


def test_seed_is_sound_and_the_day_sits_in_week_three():
    assert BUNDLE.problems == []
    assert DAY.title.startswith("Tuần 3 · Ngày 3 · ") and DAY.topic == "Tuần 3 · Việc làm (Work)"
    titles = [s.title_vi for s in DAY.sessions[:3]]
    assert titles[0].startswith("Buổi 1") and titles[1].startswith("Buổi 2") and titles[2].startswith("Buổi 3")
    assert all(len(s.check) <= 24 for s in DAY.sessions)
    assert len(DAY.grammar) == 5
    assert all(len(s.grammar) <= 3 for s in DAY.sessions)


@pytest.mark.parametrize("n", [1, 2])
def test_gate_length(n):
    assert 3.5 <= _minutes(_lecture(n).script) <= 15.5


@pytest.mark.parametrize("n", [1, 2])
def test_gate_no_template_boilerplate_is_read_out(n):
    script = _lecture(n).script
    for banned in ("0 từ vựng", "Phần một", "Phần hai", "Nghĩa là", "Lời thầy", "Lỗi người Việt hay mắc:", "Mẫu số", "Bạn nhắc lại nhé"):
        assert banned not in script, banned


@pytest.mark.parametrize("n", [1, 2])
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


@pytest.mark.parametrize("n", [1, 2])
def test_gate_narration_holds_no_long_english_phrase_and_no_bare_letter(n):
    for say in _says(AUTHORED[n]):
        for r in lecture_voice.split_runs(say):
            if r.lang != lecture_voice.KO:
                continue
            for chunk in r.text.split(","):  # a list of single words is not a phrase
                assert len(chunk.split()) < 3, (say, r.text)
        assert not re.search(r"(?<![\w-])[A-Za-z](?![\w-])", say), say


@pytest.mark.parametrize("n", [1, 2])
def test_gate_no_comma_before_va_in_spoken_vietnamese(n):
    assert ", và " not in _lecture(n).script


@pytest.mark.parametrize("n", [1, 2])
def test_gate_no_vietnamese_word_is_read_by_the_english_voice(n):
    risky = {"do", "to", "an", "con", "ban", "me", "no", "ca", "la", "mai", "sao", "hay"}
    for r in lecture_voice.split_runs(_lecture(n).script):
        if r.lang == lecture_voice.KO:
            assert r.text.strip(" .,;:!?…").lower() not in risky, r.text


@pytest.mark.parametrize("n", [1, 2])
def test_gate_narration_never_opens_in_the_first_person(n):
    for say in _says(AUTHORED[n]):
        for sentence in re.split(r"(?<=[.?!:])\s+", say):
            assert not sentence.startswith("Mình "), say


@pytest.mark.parametrize("n", [1, 2])
def test_gate_inquiry_before_rule_and_practice_after(n):
    lec = _lecture(n)
    kinds = [s["kind"] for s in lec.slides]
    assert kinds[0] == "title" and kinds[-2:] == ["recap", "end"]
    assert "?" in " ".join(lec.script.split("\n")[:3])
    for i, s in enumerate(lec.slides):
        if s["kind"] != "scene" or "rule" not in (s.get("data") or {}):
            continue
        shows = [ln.show for ln in lec.lines if ln.slide == i and ln.show]
        assert shows.index("rule") >= 2 and shows[-1] == "rule", (s["title"], shows)


@pytest.mark.parametrize("n", [1, 2])
def test_gate_every_piece_of_a_picture_is_brought_in_by_a_line(n):
    lec = _lecture(n)
    for i, s in enumerate(lec.slides):
        if s["kind"] != "scene":
            continue
        d = s["data"]
        pieces = {k for k in ("quote", "rule", "persons", "spelling", "short") if d.get(k)}
        pieces |= {r["key"] for r in d.get("rows", []) + d.get("turns", []) + d.get("parts", [])}
        if s["visual"] == "tense_timeline":
            pieces |= {"q", "axis"} | {a["key"] for a in d["answers"]}
        shown = {ln.show for ln in lec.lines if ln.slide == i and ln.show}
        assert pieces <= shown, (s["title"], pieces - shown)


def test_gate_the_class_examples_are_taught_in_their_corrected_form():
    s1, s2 = _lecture(1).script, _lecture(2).script
    for text, sentence in (
        (s1, "I'm getting my hair cut today"),
        (s1, "I'll have my hair cut today"),
        (s1, "I'm going to see my doctor today"),
        (s1, "Stop! You're going to hit it"),
        (s1, "Look at those clouds. It's going to rain"),
        (s1, "The train for Oxford leaves at 10.15"),
        (s1, "Does the concert on Thursday last more than two hours"),
        (s2, "We'll buy you a games console when we have the money"),
        (s2, "We aren't going to miss the train"),
        (s2, "We're not going to miss the train"),
    ):
        assert sentence in text, sentence
    joined = s1 + s2
    assert "PS5" not in joined  # no brand name
    assert "when we will have" not in joined and "when I will get" not in joined


def test_gate_each_sitting_teaches_its_own_words():
    for n, words in ((1, set(L.S1_WORDS)), (2, set(L.S2_WORDS))):
        lec = _lecture(n)
        assert {s["headword"] for s in lec.slides if s["kind"] == "word"} == words
    assert all(DAY.vocab[i].pos == "V" for i in range(5)) and all(DAY.vocab[i].pos == "N" for i in range(5, 10))


def test_gate_every_word_has_a_checked_transcription_and_a_note():
    assert {v.headword: v.pron for v in DAY.vocab} == L.PRON
    assert {v.headword for v in DAY.vocab} == set(L.NOTES)


def test_book_items_keep_the_key_and_say_when_the_class_prefers_another_form():
    sec = {s[1]: s[6] for s in BK.SECTIONS if s[0] == 33}
    assert list(sec) == ["F3A", "F3B"]
    a = [[x.strip() for x in ln.split(" | ")] for ln in sec["F3A"]]
    assert "You're going to hit" in a[0][1] and "Are you going to" in a[1][1]
    b = [[x.strip() for x in ln.split(" | ")] for ln in sec["F3B"]]
    assert len(b) == 10
    both = "Cả hai đều đúng"
    # the book's key: 1 both; 2 going to do; 3 both; 4 going to buy; 5 both; 6 both; 7 both; 8 broadcasting; 9 leaves; 10 both
    assert [f[1] == both for f in b] == [True, False, True, False, True, True, True, False, False, True]
    assert "going to do" in b[1][1] and "going to buy" in b[3][1] and "broadcasting" in b[7][1] and "leaves" in b[8][1]
    for i in (5, 6, 9):  # the class prefers one of two keyed forms
        assert "Đáp án bài thi" in b[i][-1], i
    for f in a + b:
        assert 3 <= len(f) - 2 <= 5


def test_typed_keys_accept_every_form_their_reason_calls_correct():
    import json
    bank = json.loads((G1.parents[1] / "app" / "seed" / "exercises" / "g1" / "build.json").read_text(encoding="utf-8"))
    items = {e["id"]: e["blanks"][0]["accepted"] for e in bank["items"] if e["id"].startswith("G1D33F")}
    assert len(items) == 5
    assert "have finished" in items["G1D33F2"]
    assert {"Does the shop open", "Is the shop open", "Is the shop opening"} <= set(items["G1D33F4"])
    assert {"are meeting", "are going to meet", "will be meeting"} <= set(items["G1D33F5"])


BANNED = ("Sách", "Destination", "thầy", "Thầy", "Minh", "Trích", "trang 3")


def test_gate_learner_facing_text_names_no_book_and_no_teacher():
    for g in DAY.grammar:
        for field in (g.pattern, g.meaning_vi, g.usage_context_vi, g.note_vi or ""):
            assert not [b for b in BANNED if b in field], (g.pattern, field[:80])
    for n in (1, 2):
        lec = _lecture(n)
        for b in BANNED:
            assert b not in lec.script, (n, b)
    for s in DAY.sessions[:3]:
        for b in BANNED:
            assert b not in s.title_vi + s.can_do_vi + (s.use_vi or ""), (s.title_vi, b)

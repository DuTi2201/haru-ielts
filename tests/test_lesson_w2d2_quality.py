"""Week 2 · Day 2 (build day 22, the past continuous): the same measurable gates as lesson 44 (docs/QUALITY_LESSON44.md),
applied to its two hand-written lectures, plus the corrections of docs/WEEK2_PLAN.md. Pure tests: no network, no database."""
import itertools
import re
from types import SimpleNamespace as NS

import pytest

from app.services import lecture_voice, lesson_audio, lesson_seed

import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location("lecture_w2d2", Path(__file__).resolve().parents[1] / "scripts" / "g1" / "lecture_w2d2.py")
L = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(L)

BUNDLE = lesson_seed.load_all()
DAY3 = next(x.seed for x in BUNDLE.lessons if x.seed.slug.startswith("g1-d22-"))


def _lecture(n: int) -> lesson_audio.Lecture:
    vr = [NS(headword=v.headword, meaning_vi=v.meaning_vi, usage_note_vi=v.note_vi, example_en=v.example_en,
             example_vi=v.example_vi, pos=v.pos, pron_en=v.pron) for v in DAY3.vocab]
    gr = [NS(pattern=g.pattern, meaning_vi=g.meaning_vi, usage_context_vi=g.usage_context_vi, note_vi=g.note_vi,
             example_en=g.example_en, example_vi=g.example_vi, contrasts=[]) for g in DAY3.grammar]
    les = NS(title=DAY3.title, title_en=DAY3.title_en, notes=[],
             sessions=[s.model_dump(mode="json", exclude_none=True) for s in DAY3.sessions])
    src, _v, _g = lesson_audio.sitting_source(les, vr, gr, n)
    return lesson_audio.build_template_lecture(src)


def _minutes(script: str) -> float:
    t = 0.0
    for r in lecture_voice.split_runs(script):
        t += len(r.text.split()) / (2.4 if r.lang == lecture_voice.KO else 3.8) + r.pause_after_ms / 1000
    return t / 60


def test_seed_is_sound_and_the_day_sits_in_week_two():
    assert BUNDLE.problems == []
    assert DAY3.title.startswith("Tuần 2 · Ngày 2 · ") and DAY3.topic == "Tuần 2 · Công nghệ (Technology)"
    titles = [s.title_vi for s in DAY3.sessions[:3]]
    assert titles[0].startswith("Buổi 1") and titles[1].startswith("Buổi 2") and titles[2].startswith("Buổi 3")
    assert all(len(s.check) <= 24 for s in DAY3.sessions)
    assert len(DAY3.grammar) == 6
    assert all(len(s.grammar) <= 3 for s in DAY3.sessions)


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
def test_gate_inquiry_before_rule_and_practice_after(n):
    lec = _lecture(n)
    kinds = [s["kind"] for s in lec.slides]
    assert kinds[0] == "title" and kinds[-2:] == ["recap", "end"]
    assert "?" in " ".join(lec.script.split("\n")[:3])
    for i, s in enumerate(lec.slides):
        if s["kind"] != "scene" or "rule" not in (s.get("data") or {}):
            continue
        shows = [ln.show for ln in lec.lines if ln.slide == i and ln.show]
        assert shows.index("rule") >= 2, (s["title"], shows)


@pytest.mark.parametrize("n", [1, 2])
def test_gate_every_piece_of_a_picture_is_brought_in_by_a_line(n):
    lec = _lecture(n)
    for i, s in enumerate(lec.slides):
        if s["kind"] != "scene":
            continue
        d = s["data"]
        pieces = {k for k in ("quote", "rule", "persons", "spelling", "short") if d.get(k)}
        pieces |= {r["key"] for r in d.get("rows", [])}
        shown = {ln.show for ln in lec.lines if ln.slide == i and ln.show}
        assert pieces <= shown, (s["title"], pieces - shown)


def test_gate_the_class_examples_are_taught_in_their_corrected_form():
    # the script turns a sentence's last stop into a pause marker, so compare without the final punctuation
    s1, s2 = _lecture(1).script, _lecture(2).script
    for text, sentence in (
        (s1, "Yesterday I played football at seven"),
        (s1, "Yesterday I was playing football at seven"),
        (s1, "Richard was watching TV when the phone rang"),
        (s1, "I was playing football while my friends were playing badminton"),
        (s2, "When we shared a room, Zoe was always taking my things"),
        (s2, "Yes, we were hanging out at a convenience store at around 7 p.m"),
        (s2, "I got up at six every morning last week"),
        (s2, "I didn't know the password"),
    ):
        assert sentence in text, sentence
    for text in (s1, s2):
        assert "warring" not in text and "1974" not in text  # the war example is replaced (docs/WEEK2_PLAN.md, point 3)


def test_gate_each_sitting_teaches_its_own_words():
    for n, words in ((1, set(L.S1_WORDS)), (2, set(L.S2_WORDS))):
        lec = _lecture(n)
        assert {s["headword"] for s in lec.slides if s["kind"] == "word"} == words


def test_gate_the_sittings_hold_seven_questions_and_cover_every_card():
    s1, s2 = DAY3.sessions[0], DAY3.sessions[1]
    assert len(s1.check) <= 7 and len(s2.check) <= 7
    taught = {g.pattern for g in DAY3.grammar}
    assert set(s1.grammar) | set(s2.grammar) == taught


def test_gate_the_book_exercises_carry_the_keys_taught_in_class():
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "g1"))
    import book_items as BK
    sec = {code: lines for day, code, *_rest, lines in BK.SECTIONS if day == 22}
    a = [ln.split(" | ")[1] for ln in sec["W2A"]]
    assert a == ["saw", "was watching", "went", "practised", "were you talking", "owned", "did", "jumped", "was working", "got", "were playing", "did pass"]
    b = [ln.split(" | ")[1].split(";")[0] for ln in sec["W2B"]]
    assert b == ["were you going", "Did you enjoy", "was always taking", "didn't have", "went", "became", "was working", "heard", "appeared", "threw"]
    ids = {i for s in DAY3.sessions for i in s.check}
    assert {f"G1D22KW2A-{k}" for k in range(1, 13)} | {f"G1D22KW2B-{k}" for k in range(1, 11)} <= ids


BANNED = ("Sách", "Destination", "thầy", "Thầy", "Minh", "Trích", "trang 2")


def test_gate_learner_facing_text_names_no_book_and_no_teacher():
    for g in DAY3.grammar:
        for field in (g.pattern, g.meaning_vi, g.usage_context_vi, g.note_vi or ""):
            assert not [b for b in BANNED if b in field], (g.pattern, field[:80])
    for n in (1, 2):
        for b in BANNED:
            assert b not in _lecture(n).script, (n, b)


def test_gate_every_word_has_a_checked_transcription():
    assert {v.headword: v.pron for v in DAY3.vocab} == L.PRON

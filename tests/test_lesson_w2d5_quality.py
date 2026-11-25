"""Week 2 · Day 5 (build day 25, change and technology, the vocabulary day): the measurable gates of lesson 44
(docs/QUALITY_LESSON44.md) applied to its five hand-written lectures, plus the class filter and the dictionary
corrections of docs/WEEK2_PLAN.md (day 5, items 9-15). Pure tests: no network, no database."""
import importlib.util
import itertools
import re
import sys
from pathlib import Path
from types import SimpleNamespace as NS

import pytest

from app.services import lecture_voice, lesson_audio, lesson_seed

G1 = Path(__file__).resolve().parents[1] / "scripts" / "g1"
_spec = importlib.util.spec_from_file_location("lecture_w2d5", G1 / "lecture_w2d5.py")
L = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(L)

BUNDLE = lesson_seed.load_all()
DAY = next(x.seed for x in BUNDLE.lessons if x.seed.slug.startswith("g1-d25-"))
SITTINGS = [1, 2, 3, 4, 5]


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
    assert DAY.title == "Tuần 2 · Ngày 5 · Thay đổi và công nghệ" and DAY.topic == "Tuần 2 · Công nghệ (Technology)"
    assert DAY.sort_order == 125
    assert [s.title_vi for s in DAY.sessions[:5]] == L.TITLES
    assert all(len(s.check) <= 24 for s in DAY.sessions)
    assert DAY.grammar == []


def test_thirty_core_words_and_five_to_recognise():
    core = [v.headword for v in DAY.vocab if v.priority == "core"]
    rec = {v.headword for v in DAY.vocab if v.priority == "recognize"}
    assert len(core) == 30 and rec == {"breakthrough", "network", "data", "console", "craft"}
    assert [v.headword for v in DAY.vocab] == [w for ws in L.S_WORDS for w in ws]
    # verbs and nouns first, as in class
    pos = [v.pos for v in DAY.vocab if v.priority == "core"]
    assert pos.count("V") + pos.count("N") >= 20


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
    for say in _says(L.LECTURES[n - 1]):
        for r in lecture_voice.split_runs(say):
            if r.lang != lecture_voice.KO:
                continue
            for chunk in r.text.split(","):  # a list of single words is not a phrase
                assert len(chunk.split()) < 3, (say, r.text)
        assert not re.search(r"(?<![\w-])[B-HJ-Zb-hj-z](?![\w-])", say), say


@pytest.mark.parametrize("n", SITTINGS)
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


@pytest.mark.parametrize("n", SITTINGS)
def test_gate_every_piece_of_a_picture_is_brought_in_by_a_line(n):
    lec = _lecture(n)
    for i, s in enumerate(lec.slides):
        if s["kind"] != "scene":
            continue
        d = s["data"]
        pieces = {k for k in ("quote", "rule") if d.get(k)}
        pieces |= {r["key"] for r in d.get("rows", []) + d.get("panels", [])}
        shown = {ln.show for ln in lec.lines if ln.slide == i and ln.show}
        assert pieces <= shown, (s["title"], pieces - shown)


@pytest.mark.parametrize("n", SITTINGS)
def test_gate_each_sitting_teaches_its_own_words(n):
    lec = _lecture(n)
    assert [s["headword"] for s in lec.slides if s["kind"] == "word"] == L.S_WORDS[n - 1]


def test_gate_the_class_contrasts_are_taught():
    script = "\n".join(_lecture(n).script for n in SITTINGS)
    for sentence in (
        "We try to maintain a balance between work and rest",
        "Please remain calm and wait for the next train",
        "He persisted in asking the same question",
        "He modified his motorbike with new lights",
        "The Internet has transformed the way we study",
        "They amended the contract",
        "Mobile phones have evolved into small computers",
        "We have made a lot of progress",
        "Someone switched our bags at the airport",
        "There's no substitute for experience",
        "Music has a great influence on young people",
        "After the war, Britain underwent radical changes",
        "Water is a precious natural resource",
    ):
        assert sentence in script, sentence
    # not taught in class: phrasal verbs and idioms of the unit
    for phrase in ("turn over a new leaf", "back up", "do away with", "change your tune"):
        assert phrase not in script


def test_gate_dictionary_corrections_are_kept():
    says = " ".join(" ".join(_says(lec)) for lec in L.LECTURES)
    assert "nghĩa rộng là xuống cấp dần" in says.lower()  # decay is not only for organic matter
    assert "cũng dùng cho kế hoạch" in says  # amend is not only for laws and contracts
    assert "Progress into vẫn có" in says  # progress into the final exists
    assert "không cách đọc nào bị coi là sai" in says  # data: other readings are not wrong
    rows = {r["key"]: r for s in L.SITTING_1 if s["kind"] == "scene" for r in s["data"].get("rows", [])}
    assert "maintain calm" not in " ".join(r.get("wrong", "") for r in rows.values())


def test_gate_the_book_exercises_carry_the_book_key():
    sys.path.insert(0, str(G1))
    import book_items as BK
    sec = {code: lines for day, code, *_rest, lines in BK.SECTIONS if day == 25}
    key = {code: [ln.split(" | ")[1] for ln in lines] for code, lines in sec.items()}
    assert key["W5A"] == ["endure", "shift", "innovation", "potential", "mature", "switched", "progress", "substitute", "decay", "modified"]
    assert key["W5B"] == ["last", "revolution", "status quo", "uniform", "radical", "trend", "dynamic", "evolve", "novel", "innovative", "influence", "conservative"]
    assert key["W5C"] == ["reformed", "revise", "distorted", "amended", "maintain", "remain", "adjust", "adapt", "alternate", "alternative",
                          "persist", "sustain", "converted", "transformed", "spoil"]
    assert key["W5D"] == ["network", "broadband", "primitive", "nuclear", "Giữ nguyên", "console", "technique", "Giữ nguyên", "data", "resource"]
    for lines in sec.values():  # a reason for every item, and every choice item has one answer among at least three options
        for ln in lines:
            f = [x.strip() for x in ln.split(" | ")]
            assert len(f[-1]) > 20
    ids = {i for s in DAY.sessions for i in s.check}
    assert {f"G1D25KW5A-{k}" for k in range(1, 11)} | {f"G1D25KW5D-{k}" for k in range(1, 11)} <= ids


BANNED = ("Sách", "Destination", "thầy", "Thầy", "Minh", "Trích", "trang 2", "trang 3")


def test_gate_learner_facing_text_names_no_book_and_no_teacher():
    for n in SITTINGS:
        for b in BANNED:
            assert b not in _lecture(n).script, (n, b)
    for v in DAY.vocab:
        for field in (v.meaning_vi, v.note_vi or "", v.example_vi):
            assert not [b for b in BANNED if b in field], (v.headword, field)


def test_gate_every_word_has_a_checked_transcription():
    assert {v.headword: v.pron for v in DAY.vocab} == L.PRON
    assert all(v.note_vi for v in DAY.vocab)

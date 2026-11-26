"""Week 3 · Day 1 (build day 31, the future simple): the measurable gates of lesson 44 (docs/QUALITY_LESSON44.md)
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
_spec = importlib.util.spec_from_file_location("lecture_w3d1", G1 / "lecture_w3d1.py")
L = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(L)
import book_items as BK  # noqa: E402

BUNDLE = lesson_seed.load_all()
DAY = next(x.seed for x in BUNDLE.lessons if x.seed.slug.startswith("g1-d31-"))
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


def test_seed_is_sound_and_the_day_opens_week_three():
    assert BUNDLE.problems == []
    assert DAY.title.startswith("Tuần 3 · Ngày 1 · ") and DAY.topic == "Tuần 3 · Việc làm (Work)"
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
        (s1, "The universe is going to continue to expand for billions of years"),  # kept: far is no reason for will
        (s1, "Governments will need to create more jobs"),
        (s1, "Will you ever see him again"),
        (s2, "OK Mom, I'll turn it off now"),  # will: the natural form for a decision made while speaking
        (s2, "I know! I'll have a barbecue on my birthday"),
        (s2, "We've decided we're going to try that new restaurant"),
        (s2, "I'm meeting a client now, so I can't talk"),
        (s2, "I'm meeting a client tomorrow"),
    ):
        assert sentence in text, sentence
    # the class's "I'm rushing to do some groceries now" is the present continuous, not a future form
    assert "rushing" not in s1 + s2
    # no near/far rule is taught as true
    assert "tương lai xa phải dùng" not in s1 + s2


def test_gate_each_sitting_teaches_its_own_words():
    for n, words in ((1, set(L.S1_WORDS)), (2, set(L.S2_WORDS))):
        lec = _lecture(n)
        assert {s["headword"] for s in lec.slides if s["kind"] == "word"} == words
    assert all(DAY.vocab[i].pos == "V" for i in range(5)) and all(DAY.vocab[i].pos == "N" for i in range(5, 10))


def test_gate_every_word_has_a_checked_transcription_and_a_note():
    assert {v.headword: v.pron for v in DAY.vocab} == L.PRON
    assert {v.headword for v in DAY.vocab} == set(L.NOTES)


def test_book_items_keep_the_key_and_say_when_the_class_prefers_another_form():
    sec = [s for s in BK.SECTIONS if s[0] == 31]
    assert [s[1] for s in sec] == ["F1A"]
    lines = sec[0][6]
    assert len(lines) == 5
    for ln in lines:
        f = [x.strip() for x in ln.split(" | ")]
        assert f[1] == "Đúng, giữ nguyên"  # the book's key: items 1, 4, 6, 8, 9 are all ticks
        assert 3 <= len(f) - 2 <= 5
    # items 6 and 8: the class reads them in two contexts; the reason names the exam answer
    assert "Đáp án bài thi" in lines[2] and "Đáp án bài thi" in lines[3]
    assert "/ˈrestrɒnt/" in lines[3]


def test_typed_keys_accept_every_form_their_reason_calls_correct():
    import json
    bank = json.loads((G1.parents[1] / "app" / "seed" / "exercises" / "g1" / "build.json").read_text(encoding="utf-8"))
    items = [e for e in bank["items"] if e["id"].startswith("G1D31F")]
    assert len(items) == 5
    for e in items:
        acc = e["blanks"][0]["accepted"]
        tip = e["blanks"][0]["common_errors_vi"]
        for form in ("is going to be", "not going to be", "are going to change", "am turning", "am going to turn", "Will you apply"):
            if form in tip:
                assert any(form in a for a in acc), (e["id"], form)


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

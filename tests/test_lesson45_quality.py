"""G1 · Day 2 (lesson 45): the same measurable gates as lesson 44 (docs/QUALITY_LESSON44.md), applied to the two
hand-written lectures of the present continuous and state verbs. Pure tests: no network, no database."""
import itertools
import re
from types import SimpleNamespace as NS

import pytest

from app.services import lecture_voice, lesson_audio, lesson_seed

BUNDLE = lesson_seed.load_all()
DAY2 = next(x.seed for x in BUNDLE.lessons if x.seed.slug.startswith("g1-d2-"))


def _lecture(n: int) -> lesson_audio.Lecture:
    vr = [NS(headword=v.headword, meaning_vi=v.meaning_vi, usage_note_vi=v.note_vi, example_en=v.example_en,
             example_vi=v.example_vi, pos=v.pos, pron_en=v.pron) for v in DAY2.vocab]
    gr = [NS(pattern=g.pattern, meaning_vi=g.meaning_vi, usage_context_vi=g.usage_context_vi, note_vi=g.note_vi,
             example_en=g.example_en, example_vi=g.example_vi, contrasts=[]) for g in DAY2.grammar]
    les = NS(title=DAY2.title, title_en=DAY2.title_en, notes=[],
             sessions=[s.model_dump(mode="json", exclude_none=True) for s in DAY2.sessions])
    src, _v, _g = lesson_audio.sitting_source(les, vr, gr, n)
    return lesson_audio.build_template_lecture(src)


def _minutes(script: str) -> float:
    t = 0.0
    for r in lecture_voice.split_runs(script):
        t += len(r.text.split()) / (2.4 if r.lang == lecture_voice.KO else 3.8) + r.pause_after_ms / 1000
    return t / 60


def test_seed_is_sound_and_day_two_has_three_teaching_sittings():
    assert BUNDLE.problems == []
    titles = [s.title_vi for s in DAY2.sessions[:3]]
    assert titles[0].startswith("Buổi 1") and titles[1].startswith("Buổi 2") and titles[2].startswith("Buổi 3")
    assert all(len(s.check) <= 24 for s in DAY2.sessions)
    assert len(DAY2.grammar) == 8


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
    assert "?" in lec.script.split("\n")[0]
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


def test_gate_state_verbs_follow_the_book_not_a_blanket_ban():
    card = next(g for g in DAY2.grammar if g.pattern.startswith("State verbs"))
    text = card.usage_context_vi
    for group in ("thinking", "existence", "emotions", "the human senses", "appearance", "possession and relationships"):
        assert group in text
    assert "thường không" in text
    script = _lecture(2).script
    assert "thường không chia tiếp diễn" in script


def test_gate_no_transcription_is_typed_from_memory():
    assert all(v.pron is None for v in DAY2.vocab)  # none checked against the dictionary yet


BANNED = ("Sách", "sách", "Destination", "thầy", "Thầy", "Minh", "Trích", "trang 7", "tr. ")


def test_gate_learner_facing_text_names_no_book_and_no_teacher():
    for g in DAY2.grammar:
        for field in (g.pattern, g.meaning_vi, g.usage_context_vi, g.note_vi or ""):
            assert not [b for b in BANNED if b in field.replace("danh sách", "")], (g.pattern, field[:80])
    for n in (1, 2):
        for b in BANNED:
            assert b not in _lecture(n).script.replace("danh sách", ""), (n, b)


def test_gate_first_grammar_card_is_the_formula_with_a_table():
    first = DAY2.grammar[0]
    assert "công thức" in first.pattern
    assert first.usage_context_vi.count("pat:") >= 3 and "prep:" in first.usage_context_vi


def test_gate_no_wall_of_text_in_any_card():
    for g in DAY2.grammar:
        for chunk in g.usage_context_vi.split("\n"):
            assert len(chunk) < 420, (g.pattern, chunk[:60])


def test_gate_no_jargon_axes():
    blob = " ".join(g.pattern + g.usage_context_vi for g in DAY2.grammar) + _lecture(1).script
    assert "Trục 1" not in blob and "trục 1" not in blob and "Hai trục" not in blob

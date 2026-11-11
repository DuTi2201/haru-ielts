"""G1 · Day 1 (lesson 44): the hand-written lectures, the voice plan, the pronunciation scoring
and the measurable quality gates of docs/QUALITY_LESSON44.md. Pure tests: no network, no database."""
import base64
import itertools
import json
import re
import struct
from types import SimpleNamespace as NS

import pytest

from app.services import azure_pron, lecture_voice, lesson_audio, lesson_seed

BUNDLE = lesson_seed.load_all()
DAY1 = next(x.seed for x in BUNDLE.lessons if x.seed.slug.startswith("g1-d1-"))


def _lecture(n: int) -> lesson_audio.Lecture:
    vr = [NS(headword=v.headword, meaning_vi=v.meaning_vi, usage_note_vi=v.note_vi, example_en=v.example_en,
             example_vi=v.example_vi, pos=v.pos, pron_en=v.pron) for v in DAY1.vocab]
    gr = [NS(pattern=g.pattern, meaning_vi=g.meaning_vi, usage_context_vi=g.usage_context_vi, note_vi=g.note_vi,
             example_en=g.example_en, example_vi=g.example_vi, contrasts=[]) for g in DAY1.grammar]
    les = NS(title=DAY1.title, title_en=DAY1.title_en, notes=[],
             sessions=[s.model_dump(mode="json", exclude_none=True) for s in DAY1.sessions])
    src, _v, _g = lesson_audio.sitting_source(les, vr, gr, n)
    return lesson_audio.build_template_lecture(src)


def _minutes(script: str) -> float:
    """The length the voice plan implies: Vietnamese at 3.8 syllables a second, English at 2.4 words a
    second (the configured paces, rounded down), the silences of the plan, and for a sentence said
    for repeating a gap as long as the sentence."""
    runs = lecture_voice.split_runs(script)
    t = 0.0
    for r in runs:
        n = len(r.text.split())
        t += n / (2.4 if r.lang == lecture_voice.KO else 3.8)
        t += r.pause_after_ms / 1000
    return t / 60


def test_the_gap_after_an_english_sentence_is_long_enough_to_say_it():
    runs = lecture_voice.split_runs("I do like fish...\nThe bus is slow, but it does stop near my office...\nhabit... thói quen.")
    by_text = {r.text: r.pause_after_ms for r in runs}
    assert by_text["I do like fish..."] == 400 + 4 * 545
    assert by_text["The bus is slow, but it does stop near my office..."] >= 6000
    assert by_text["habit..."] == 1200


def test_the_seed_is_sound_and_day_one_has_three_teaching_sittings():
    assert BUNDLE.problems == []
    titles = [s.title_vi for s in DAY1.sessions[:3]]
    assert titles[0].startswith("Buổi 1") and titles[1].startswith("Buổi 2") and titles[2].startswith("Buổi 3")
    assert DAY1.sessions[1].vocab == ["emphasise"]  # taught in the sitting that uses it
    assert all(len(s.check) <= 24 for s in DAY1.sessions)
    assert len(DAY1.vocab) >= 24  # a lesson of vocabulary for IELTS, not six words


@pytest.mark.parametrize("n", [1, 2])
def test_gate_length_up_to_fifteen_minutes(n):
    assert 3.5 <= _minutes(_lecture(n).script) <= 15.5


@pytest.mark.parametrize("n", [1, 2])
def test_gate_no_template_boilerplate_is_read_out(n):
    script = _lecture(n).script
    for banned in ("0 từ vựng", "Phần một", "Phần hai", "Nghĩa là", "Lời thầy", "Lỗi người Việt hay mắc:", "Mẫu số", "Bạn nhắc lại nhé"):
        assert banned not in script, banned


@pytest.mark.parametrize("n", [1, 2])
def test_gate_an_english_sentence_is_read_by_one_voice(n):
    """No English sentence is cut between two voices, and no English run holds a Vietnamese letter."""
    lec = _lecture(n)
    runs = lecture_voice.split_runs(lec.script)
    for r in runs:
        if r.lang == lecture_voice.KO:
            assert not re.search(r"[À-ỹĐđ]", r.text), r.text
    lines = [ln for ln in lec.script.split("\n") if ln.strip()]
    for li, group in itertools.groupby(runs, key=lambda r: r.line):
        group = list(group)
        if not re.search(r"[À-ỹĐđ]", lines[li]):  # an all-English line
            assert len(group) == 1 and group[0].lang == lecture_voice.KO, lines[li]


@pytest.mark.parametrize("n", [1, 2])
def test_gate_inquiry_before_rule_and_practice_after(n):
    """Each lecture opens with a question, shows an experiment before it states its rule, and ends
    with the sentences said back (retrieval) rather than with new material."""
    lec = _lecture(n)
    kinds = [s["kind"] for s in lec.slides]
    assert kinds[0] == "title" and kinds[-2:] == ["recap", "end"]
    assert "?" in lec.script.split("\n")[0]
    for i, s in enumerate(lec.slides):
        if s["kind"] != "scene" or "rule" not in (s.get("data") or {}):
            continue
        shows = [show for slide, show in ((ln.slide, ln.show) for ln in lec.lines) if slide == i and show]
        assert shows.index("rule") >= 2, (s["title"], shows)  # the rule comes after the pieces of the experiment


@pytest.mark.parametrize("n", [1, 2])
def test_gate_every_piece_of_a_picture_is_brought_in_by_a_line(n):
    """Temporal contiguity: whatever a scene can show has a line that shows it, and every line's
    "show" is a piece the scene has."""
    lec = _lecture(n)
    for i, s in enumerate(lec.slides):
        if s["kind"] != "scene":
            continue
        d = s["data"]
        pieces = {k for k in ("quote", "rule", "proof", "signals", "ielts", "plain", "emph", "ex2", "wrong", "right", "persons", "spelling", "short") if d.get(k)}
        pieces |= {b["key"] for b in d.get("boxes", [])} if d.get("sentence") else set()
        pieces |= {c["key"] for c in d.get("cards", [])} | {a["key"] for a in d.get("answers", [])}
        pieces |= {r["key"] for r in d.get("rows", [])} | {r["key"] for r in d.get("parts", [])}
        shown = {ln.show for ln in lec.lines if ln.slide == i and ln.show}
        assert pieces <= shown, (s["title"], pieces - shown)


def test_gate_the_teachers_words_are_verbatim():
    quotes = [c.usage_context_vi for c in DAY1.grammar if "«" in (c.usage_context_vi or "")]
    said = _lecture(1).script.lower()
    found = re.findall(r"«([^»]+)»", "\n".join(quotes))
    assert len(found) == 2
    for q in found:
        assert q.rstrip(".").lower() in said


def test_shadow_runs_mark_the_sentences_to_repeat():
    lec = _lecture(2)
    lines = [ln for ln in lec.script.split("\n") if ln.strip()]
    marked = {lines[l] for l, _r in lesson_audio.shadow_runs(lec.script)}
    assert "I do like fish..." in marked and "He does work hard..." in marked
    assert not any("does works" in m for m in marked)  # the wrong form is heard, never repeated


def test_a_sitting_without_words_announces_none():
    src = lesson_audio.LessonSource("Bài thử", None, [], [lesson_audio.GrammarLine("S + V", "câu đơn", example_en="I work.")])
    script = lesson_audio.build_template_script(src)
    assert "0 từ vựng" not in script and "Từ vựng" not in script and "Phần một. Ngữ pháp." in script


def test_degrees_celsius_stays_with_the_vietnamese_voice():
    assert lesson_audio.spoken_vi("Nước sôi ở 100 độ C.") == "Nước sôi ở 100 độ xê."
    assert lecture_voice._split_paragraph_latin("Hoa works in a hospital.") == [(lecture_voice.KO, "Hoa works in a hospital.")]


def test_transcriptions_are_only_the_checked_ones():
    pron = {v.headword: v.pron for v in DAY1.vocab}
    assert pron["habit"] == "/ˈhæbɪt/" and pron["permanent"] == "/ˈpɜːmənənt/"
    assert pron["state"] is None and pron["fact"] is None  # not checked yet: shown without, never guessed


# ---------------------------------------------------------------- pronunciation scoring --
def _wav(seconds: float) -> bytes:
    data = b"\0\0" * int(16000 * seconds)
    return b"RIFF" + struct.pack("<I", 36 + len(data)) + b"WAVEfmt " + struct.pack("<IHHIIHH", 16, 1, 1, 16000, 32000, 2, 16) + b"data" + struct.pack("<I", len(data)) + data


def test_assessment_header_asks_for_a_scripted_phoneme_level_score():
    params = json.loads(base64.b64decode(azure_pron.assessment_header("I do like fish!")))
    assert params == {"ReferenceText": "I do like fish!", "GradingSystem": "HundredMark", "Granularity": "Phoneme",
                      "Dimension": "Comprehensive", "EnableMiscue": True}


def test_wav_limits_follow_azure():
    assert azure_pron.check_wav(_wav(2.0)) == pytest.approx(2.0)
    for bad in (0.2, 31.0):
        with pytest.raises(Exception):
            azure_pron.check_wav(_wav(bad))


def test_parse_reads_both_answer_shapes_and_names_the_weak_words():
    flat = {"RecognitionStatus": "Success", "NBest": [{"Display": "I do like fish.", "AccuracyScore": 71, "FluencyScore": 90,
            "CompletenessScore": 100, "PronScore": 80.2, "Words": [
                {"Word": "I", "AccuracyScore": 98, "ErrorType": "None"}, {"Word": "do", "AccuracyScore": 95, "ErrorType": "None"},
                {"Word": "like", "AccuracyScore": 88, "ErrorType": "None"}, {"Word": "fish", "AccuracyScore": 41, "ErrorType": "Mispronunciation"}]}]}
    out = azure_pron.parse(flat, "I do like fish!")
    assert out["ok"] and out["accuracy"] == 71 and out["level"] == "fair" and out["weak"] == ["fish"]
    nested = {"RecognitionStatus": "Success", "NBest": [{"Display": "Yes.", "PronunciationAssessment": {"AccuracyScore": 92, "FluencyScore": 99,
              "CompletenessScore": 50, "PronScore": 80}, "Words": [{"Word": "yes", "PronunciationAssessment": {"AccuracyScore": 92, "ErrorType": "None"}},
              {"Word": "do", "PronunciationAssessment": {"ErrorType": "Omission"}}]}]}
    out = azure_pron.parse(nested, "Yes, I do.")
    assert out["level"] == "retry" and out["completeness"] == 50 and out["weak"] == ["do"]  # a word left out: again
    assert azure_pron.parse({"RecognitionStatus": "NoMatch"}, "Yes, I do.") == {"ok": False, "heard": "", "reason": "no_speech"}


def test_only_short_english_sentences_are_scored():
    assert azure_pron.check_reference("  I do   like fish! ") == "I do like fish!"
    with pytest.raises(ValueError):
        azure_pron.check_reference("…")
    with pytest.raises(ValueError):
        azure_pron.check_reference("word " * 41)


def test_day1_has_seven_cards_in_four_steps_each_with_one_check():
    pats = [c.pattern for c in DAY1.grammar]
    assert len(pats) == 7
    assert pats[0].endswith("công thức") and "-s / -es" in pats[1] and pats[2].endswith("cách dùng")
    for c in DAY1.grammar:
        assert c.check and len(c.check.options) >= 3, c.pattern  # the right option first, at least two wrong ones
    # the formula must be on the card itself (formula tiles), not only in the lecture
    f = DAY1.grammar[0].usage_context_vi
    assert "he / she / it + doesn't + work" in f and "Does + he / she / it + work" in f

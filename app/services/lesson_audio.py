"""Audio of a seeded lesson (lesson-v5), pure text work — no network.

Two ways to hear a lesson, both voiced by Google Chirp 3 HD (the voice of every
other audio feature) and both stored once and replayed:

* **template** (default): a fixed script built from the lesson itself — every
  word, every grammar pattern, the notes — in a set order. No model writes it, so it
  is the same every time, cannot invent anything, and costs only the voice.
* **story**: Gemini retells the lesson as a lecture (app.services.podcast_script).
  A model can only write so much in one answer, so a long lesson is cut into parts
  (`plan_parts`), each part is written separately with the previous part's outline for
  continuity, and the parts are joined and voiced as one recording.

This module also holds the small helpers for the dialogue recordings of the practice
set (who says what), so the API and the worker agree on a key.
"""
from __future__ import annotations

import hashlib
import hashlib
import re
from dataclasses import dataclass, field, replace
from typing import Any, Sequence

from app.services import podcast_script
from app.services.grammar_text import split_source_note, usage_sections
from app.services.grammar_tier import grammar_tier

TEMPLATE_VERSION = "tpl-v4"
STORY_VERSION = "story-v1"

# Gemini writes a part of at most this many vocabulary items / grammar patterns, so one
# answer stays well inside what it can write and the voice can carry.
MAX_VOCAB_PER_PART = 12
MAX_GRAMMAR_PER_PART = 3
# The longest script the voice is asked to read in one recording. A template script is
# a few thousand characters; a story of several parts is longer than one answer's limit.
MAX_SCRIPT_CHARS = 36000

_SAY_GAP = "..."  # a Korean line ending in "..." is followed by a gap to repeat it in


# ----------------------------------------------------------------- the lesson --
@dataclass(frozen=True)
class VocabLine:
    headword: str
    meaning_vi: str
    note_vi: str | None = None
    example_en: str | None = None
    example_vi: str | None = None
    pos: str | None = None  # N / V / A / X, shown on the word's slide
    pron: str | None = None  # the dictionary's transcription ("/ˈhæbɪt/"), shown, never read out


@dataclass(frozen=True)
class GrammarLine:
    pattern: str
    meaning_vi: str
    usage_vi: str | None = None
    note_vi: str | None = None
    example_en: str | None = None  # several: one per line
    example_vi: str | None = None
    contrasts: tuple[tuple[str, str], ...] = ()  # (pattern, diff_vi)


@dataclass(frozen=True)
class LessonSource:
    title: str
    title_en: str | None
    vocab: list[VocabLine]
    grammar: list[GrammarLine]
    notes: list[tuple[str | None, str]] = field(default_factory=list)  # (title, body)
    # positions in `notes` of the notes an exam course (KIIP) needs too: read to the end, not cut
    # short. Left out of repr on purpose, see source_signature.
    full_notes: tuple[int, ...] = field(default=(), repr=False)
    # a sitting's lecture written by an editor (SessionSeed.lecture): slides with the lines said on
    # each. When present it replaces the fixed template (build_authored_lecture).
    authored: tuple[dict, ...] = ()


def source_signature(lesson: "LessonSource") -> str:
    """A short hash of everything a lecture is made from. A recording is kept while this stays
    the same, so editing a lesson's exercises does not record its lecture again — but any change
    to a word, a pattern, a note or a title does. Which notes are read in full is part of it only
    when there are some, so a lesson without such notes keeps the recording it already has."""
    text = repr(lesson)
    if lesson.full_notes:
        text += "|full:" + ",".join(str(i) for i in lesson.full_notes)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:24]


def source_from_rows(lesson: Any, vocab_rows: Sequence[Any], grammar_rows: Sequence[Any]) -> LessonSource:
    """ORM rows (Lesson, VocabItem, GrammarPoint) -> LessonSource."""
    notes = getattr(lesson, "notes", None) or []
    return LessonSource(
        title=lesson.title,
        title_en=getattr(lesson, "title_en", None),
        vocab=[
            VocabLine(
                v.headword, v.meaning_vi, v.usage_note_vi, v.example_en, getattr(v, "example_vi", None),
                getattr(v, "pos", None), getattr(v, "pron_en", None),
            )
            for v in vocab_rows
        ],
        grammar=[
            GrammarLine(
                g.pattern,
                g.meaning_vi,
                g.usage_context_vi,
                getattr(g, "note_vi", None),
                g.example_en,
                getattr(g, "example_vi", None),
                tuple((c.get("pattern", ""), c.get("diff_vi", "")) for c in (g.contrasts or [])),
            )
            for g in grammar_rows
        ],
        notes=[(n.get("title"), n.get("body", "")) for n in notes],
        full_notes=tuple(i for i, n in enumerate(notes) if n.get("exam")),
    )


_ICONS: dict[str, str] | None = None


def word_icon(headword: str) -> str | None:
    """The id of the picture for a word (public/illus/<id>.svg of the app), made by hand in
    scripts/icons and listed in app/seed/word_icons.json; None for a word with no picture."""
    global _ICONS
    if _ICONS is None:
        import json
        from pathlib import Path

        path = Path(__file__).resolve().parent.parent / "seed" / "word_icons.json"
        _ICONS = json.loads(path.read_text(encoding="utf8")) if path.exists() else {}
    return _ICONS.get(headword.strip())


def sitting_source(lesson: Any, vocab_rows: Sequence[Any], grammar_rows: Sequence[Any], n: int):
    """The lecture of ONE sitting ("buổi" n, 1-based) of a lesson: only that sitting's words and
    cards, in the order it teaches them, under a title that names the sitting. The lesson's notes
    belong to the whole lesson, so they are not read here. Returns (source, vocab_rows, grammar_rows)
    or None when the lesson has no such sitting."""
    sessions = getattr(lesson, "sessions", None) or []
    if not 1 <= n <= len(sessions):
        return None
    ses = sessions[n - 1]
    by_word = {v.headword: v for v in vocab_rows}
    by_card = {g.pattern: g for g in grammar_rows}
    vr = [by_word[w] for w in ses.get("vocab", []) if w in by_word]
    gr = [by_card[p] for p in ses.get("grammar", []) if p in by_card]
    if not vr and not gr and not ses.get("lecture"):  # a method lecture has no words of its own
        return None
    src = source_from_rows(lesson, vr, gr)
    # the sitting's own title usually opens with "Buổi n ·": say "buổi n" once
    rest = re.sub(r"^\s*buổi\s+\d+\s*[·:\-–—]?\s*", "", ses.get("title_vi", "") or "", flags=re.IGNORECASE).strip()
    title = f"{lesson.title}, buổi {n}: {rest}" if rest else f"{lesson.title}, buổi {n}"
    src = replace(src, title=title, title_en=None, notes=[], full_notes=(), authored=tuple(ses.get("lecture") or ()))
    return src, vr, gr


# ----------------------------------------------------- saying a pattern aloud --
# A grammar pattern is written for the eye ("V + -(으)ㄹ까요?"); read out it has to be
# words and syllables. The rules are small and explicit; tests run every pattern of
# the seed through them.
_JAMO_NAME = {
    "ㄱ": "기역", "ㄴ": "니은", "ㄷ": "디귿", "ㄹ": "리을", "ㅁ": "미음", "ㅂ": "비읍", "ㅅ": "시옷",
    "ㅇ": "이응", "ㅈ": "지읒", "ㅊ": "치읓", "ㅋ": "키읔", "ㅌ": "티읕", "ㅍ": "피읖", "ㅎ": "히읗",
    "ㄲ": "쌍기역", "ㄸ": "쌍디귿", "ㅃ": "쌍비읍", "ㅆ": "쌍시옷", "ㅉ": "쌍지읒",
    "ㅏ": "아", "ㅑ": "야", "ㅓ": "어", "ㅕ": "여", "ㅗ": "오", "ㅛ": "요", "ㅜ": "우", "ㅠ": "유", "ㅡ": "으", "ㅣ": "이",
    "ㅐ": "애", "ㅒ": "얘", "ㅔ": "에", "ㅖ": "예", "ㅘ": "와", "ㅙ": "왜", "ㅚ": "외", "ㅝ": "워", "ㅞ": "웨", "ㅟ": "위", "ㅢ": "의",
    "ㄳ": "기역시옷", "ㄵ": "니은지읒", "ㄶ": "니은히읗", "ㄺ": "리을기역", "ㄻ": "리을미음", "ㄼ": "리을비읍",
    "ㄽ": "리을시옷", "ㄾ": "리을티읕", "ㄿ": "리을피읖", "ㅀ": "리을히읗", "ㅄ": "비읍시옷",
}
_JAMO_RE = re.compile("[" + "".join(_JAMO_NAME) + "]")
_HANGUL = "가-힣"
# (으)ㄹ -> 을 and so on: the form a learner hears most
_OPTIONAL_ENDINGS = (("(으)ㄹ", "을"), ("(으)ㅂ", "읍"), ("(으)ㄴ", "은"), ("(느)ㄴ", "는"))
_LEADING_JAMO = (("ㄴ", "은"), ("ㄹ", "을"), ("ㅂ", "읍"))
_TAGS = (("V/A", "động từ hoặc tính từ"), ("V", "động từ"), ("A", "tính từ"), ("N", "danh từ"))
_NUMBER_WORD = {"1": "một", "2": "hai", "3": "ba"}


def _dedupe_alternatives(text: str) -> str:
    """'는데 hoặc 은데 hoặc 은데' -> '는데 hoặc 은데'."""
    parts = [p.strip() for p in re.split(r"\s+hoặc\s+", text)]
    seen: list[str] = []
    for p in parts:
        if p and p not in seen:
            seen.append(p)
    return " hoặc ".join(seen)


# ---- English formulas (Haru English). Written for the eye ("S + V(s/es)", "V-ing", "V3",
# "adj-er", "-s/-es"); said as words before the generic rules below get to them (those would
# read "V(s/es)" as "động từ chỉ s hoặc es" and "V-ing" as "động từ ing").
_HANGUL_RE = re.compile(f"[{_HANGUL}ㄱ-ㅎㅏ-ㅣ]")
_ENGLISH_FORMS = (
    (re.compile(r"\bV\s*\(\s*s\s*/\s*-?es\s*\)"), "động từ thêm S hoặc ES"),
    (re.compile(r"\bV-s\s*/\s*-?es\b"), "động từ thêm S hoặc ES"),
    (re.compile(r"\bV-ing\b"), "động từ thêm ing"),
    (re.compile(r"\bV-ed\b"), "động từ thêm ed"),
    (re.compile(r"\bV3\b"), "quá khứ phân từ"),
    (re.compile(r"\badj-(er|est)\b"), r"tính từ thêm \1"),
    # a lone ending is spelt (the English voice says "S", "ES"), the longer ones are read
    (re.compile(r"(?<![\w-])-(s|es|ing|ed|er|est)\b"), lambda m: "đuôi " + (m.group(1).upper() if m.group(1) in ("s", "es") else m.group(1))),
    (re.compile(r"(?<![A-Za-zÀ-ỹ0-9])v,\s*"), "động từ, "),
    (re.compile(r"(?<![A-Za-zÀ-ỹ0-9])n,\s*"), "danh từ, "),
    (re.compile(r"(?<![A-Za-zÀ-ỹ0-9])adj,\s*"), "tính từ, "),
    (re.compile(r"(?<![A-Za-zÀ-ỹ0-9])adv,\s*"), "trạng từ, "),
    (re.compile(r"\badj\b"), "tính từ"),
    (re.compile(r"\badv\b"), "trạng từ"),
    (re.compile(r"\bsb\b"), "somebody"),
    (re.compile(r"\bsth\b"), "something"),
    (re.compile(r"\bS\b(?=\s*\+)|(?<=\+)\s*S\b"), " chủ ngữ"),
)
_ASCII_SLASH_RE = re.compile(r"(?<=[A-Za-z'’])\s*/\s*(?:,\s*)?(?=[A-Za-z])")  # am/is/are: one English run, not "hoặc" x2


def _english_forms(s: str) -> str:
    for rx, said in _ENGLISH_FORMS:
        s = rx.sub(said, s)
    return s


_STRIKE_LIST_RE = re.compile(r"(~~[^~]+~~(?:\s*,\s*~~[^~]+~~)*)\s*(?:→|=>|->)\s*")


def _strike_corrections(s: str) -> str:
    """'~~She work~~ → She works' -> 'không nói She work, mà nói She works' (the B1 notes mark the
    wrong form with a strikethrough; read flat, the voice said both forms one after the other)."""
    s = _STRIKE_LIST_RE.sub(lambda m: "không nói " + ", ".join(re.findall(r"~~([^~]+)~~", m.group(1))) + ", mà nói ", s)
    return re.sub(r"~~([^~]+)~~", r"không nói \1", s)


def speakable_pattern(pattern: str) -> str:
    """'V + -(으)ㄹ까요?' -> 'động từ cộng 을까요'."""
    s = pattern.strip()
    s = re.sub(r"(\d+)\s*[–—]\s*(\d+)", r"\1 đến \2", s)
    s = s.replace("–", "-").replace("—", "-")
    s = re.sub(r"\(\s*v\s*\)", "động từ, ", s, flags=re.IGNORECASE)
    s = re.sub(r"\(\s*n\s*\)", "danh từ, ", s, flags=re.IGNORECASE)
    s = re.sub(r"\(\s*adj\s*\)", "tính từ, ", s, flags=re.IGNORECASE)
    s = re.sub(r"\(\s*adv\s*\)", "trạng từ, ", s, flags=re.IGNORECASE)
    english = not _HANGUL_RE.search(s)
    if english:
        s = _english_forms(s)
    for written, spoken in _OPTIONAL_ENDINGS:
        s = s.replace(written, spoken)
    s = s.replace("(ㄴ/는)", "ㄴ/는")  # -(ㄴ/는)다고: the two endings are said side by side, like -ㄴ/는다
    s = s.replace("(으)", "으")
    s = _PARTICLE_IN_BRACKETS_RE.sub("", s)  # 께서(는), 위해(서): the optional part is not read
    s = re.sub(rf"\(([{_HANGUL}]{{1,2}})\)(?=[{_HANGUL}])", r"\1", s)  # (이)시다 -> 이시다
    s = s.replace(" · ", ", ")  # alternatives written side by side
    # 은/ㄴ: the bare jamo alternative adds nothing to the syllable before it
    s = re.sub(rf"(?<=[{_HANGUL}])/[ㄱ-ㅎ](?![{_HANGUL}])", "", s)
    for jamo, syllable in _LEADING_JAMO:
        s = re.sub(rf"{jamo}(?=[{_HANGUL}])", syllable, s)
    for tag, words in _TAGS:  # V/A first, then the single letters
        s = re.sub(rf"(?<![A-Za-zÀ-ỹ0-9]){re.escape(tag)}(\d?)(?![A-Za-zÀ-ỹ])", lambda m, w=words: w + (" " + _NUMBER_WORD.get(m.group(1), m.group(1)) if m.group(1) else ""), s)
    s = re.sub(r"(từ|một|hai|ba)\(([^()]+)\)", lambda m: f"{m.group(1)} chỉ {m.group(2).strip().lower()} ", s)
    s = re.sub(r"\(([^()]+)\)", lambda m: ", " + m.group(1).strip() + ", ", s)
    s = s.replace("+", " cộng ").replace("~", " ").replace("…", " ").replace("?", "")
    s = re.sub(r"(?<=[A-Za-zÀ-ỹ])-(?=[A-Za-zÀ-ỹ])", " ", s)  # Hán-Hàn: a compound, not a dash to read
    s = re.sub(r"(?<![\w])-(?=[" + _HANGUL + "ㄱ-ㅎㅏ-ㅣ])", "", s)
    s = re.sub(rf"(?<=[{_HANGUL}])-(?![\w])", "", s)  # 으시- , 겠-: the dash of a stem
    if english:
        s = _ASCII_SLASH_RE.sub(", ", s)
    s = re.sub(r"\s*/\s*", " hoặc ", s)
    s = _JAMO_RE.sub(lambda m: _JAMO_NAME[m.group(0)], s)
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"\s*,\s*(,\s*)+", ", ", s)
    s = re.sub(r"([:;.])\s*,", r"\1", s)  # "clauses: , who" -> "clauses: who"
    s = re.sub(r"\s+,", ",", s).strip(" ,")
    # the Korean pieces glued to a Vietnamese word are split by the language runs later
    return _dedupe_alternatives(s)


_MARKDOWN_RE = re.compile(r"(\*\*|__|`+)")
_STAR_ITALIC_RE = re.compile(r"(?<!\w)\*([^*\n]+)\*(?!\w)")
_PARTICLE_IN_BRACKETS_RE = re.compile(rf"(?<=[{_HANGUL}])\(([{_HANGUL}]{{1,2}})\)")


_TAG_WORD_RE = re.compile(r"(?<![A-Za-zÀ-ỹ0-9`])(V/A|V|A|N)(?![A-Za-zÀ-ỹ0-9])")
# in English text a lone "A" is the article or a placeholder ("A bridge", "both A and B"), not "tính từ"
_TAG_WORD_EN_RE = re.compile(r"(?<![A-Za-zÀ-ỹ0-9`'’])(V/A|V)(?![A-Za-zÀ-ỹ0-9'’])")
_TAG_SPOKEN = {"V/A": "động từ hoặc tính từ", "V": "động từ", "A": "tính từ", "N": "danh từ"}


def spoken_vi(text: str) -> str:
    """Vietnamese text of a lesson (meaning, usage, notes) -> what the voice should read:
    no markdown or quotes, '/' as 'hoặc' (a date such as 1/10 as 'tháng'), '(X)' / '(O)'
    as sai / đúng, V / A / N as their words, jamo by name, '&' as 'và'."""
    s = (text or "").replace("\r\n", "\n")
    s = _MARKDOWN_RE.sub("", s)
    s = _STAR_ITALIC_RE.sub(r"\1", s)
    s = re.sub(r"(\d+)\s*[–—]\s*(\d+)", r"\1 đến \2", s)
    s = s.replace("–", "-").replace("—", "-")
    s = re.sub(r"(\d)\s*(?:°\s*C|độ C)(?![A-Za-zÀ-ỹ])", r"\1 độ xê", s)  # "100 độ C": the lone C went to the English voice
    s = re.sub(r"\(\s*v\s*\)", "động từ, ", s, flags=re.IGNORECASE)
    s = re.sub(r"\(\s*n\s*\)", "danh từ, ", s, flags=re.IGNORECASE)
    s = re.sub(r"\(\s*adj\s*\)", "tính từ, ", s, flags=re.IGNORECASE)
    s = re.sub(r"\(\s*adv\s*\)", "trạng từ, ", s, flags=re.IGNORECASE)
    english = not _HANGUL_RE.search(s)
    if english:
        s = _strike_corrections(s)
        s = re.sub(r"(?<![\w/])/([^/\s,;]{1,4})/(?![\w/])", r"âm \1", s)  # /t/, /ɪd/: a sound, not a slash
        s = _english_forms(s)
        s = re.sub(r"\s*\+\s*", " cộng ", s)  # the cleaner drops a bare "+" and glued the two sides
        s = re.sub(r"\s*·\s*", ", ", s)
        s = re.sub(r"\s*(?<![=<>-])=(?![=>])\s*", " nghĩa là ", s)
    s = re.sub(r"\s*[✗✘]\s*(?:→|=>|->)\s*", ", sai, nên nói ", s)  # `*sai` ✗ → `đúng`
    s = re.sub(r"\s*[✗✘]\s*", ", sai, ", s)
    s = re.sub(r"\s*[✓✔]\s*", ", đúng, ", s)
    s = re.sub(r"\(\s*[Xx]\s*\)", ", sai,", s)
    s = re.sub(r"\(\s*[OoＯ]\s*\)", ", đúng,", s)
    s = re.sub(r"[\"“”„‟]", "", s)
    s = s.replace("→", ", ").replace("=>", ", ").replace("->", ", ").replace("&", " và ")
    s = re.sub(r"\.{2,}|…", ", ", s)
    for written, spoken in _OPTIONAL_ENDINGS:
        s = s.replace(written, spoken)
    s = s.replace("(으)", "으")
    s = _PARTICLE_IN_BRACKETS_RE.sub("", s)  # 샤워(를) 하다 -> 샤워 하다
    s = re.sub(rf"\(([{_HANGUL}]{{1,2}})\)(?=[{_HANGUL}])", r"\1", s)  # (이)다 -> 이다
    s = re.sub(r"(?<!\d)(\d{1,2})/(\d{1,2})(?!\d)", r"\1 tháng \2", s)
    s = (_TAG_WORD_RE if not english else _TAG_WORD_EN_RE).sub(lambda m: _TAG_SPOKEN[m.group(1)], s)
    if english:
        s = _ASCII_SLASH_RE.sub(", ", s)
    s = re.sub(r"\s*/\s*", " hoặc ", s)
    s = re.sub(rf"(?<![{_HANGUL}\w])-(?=[{_HANGUL}ㄱ-ㅎㅏ-ㅣ])", "", s)
    s = _JAMO_RE.sub(lambda m: " " + _JAMO_NAME[m.group(0)] + " ", s)
    s = re.sub(r"\((.*?)\)", r", \1,", s)
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\s*\n\s*", "\n", s)
    s = re.sub(r"\s*,(\s*,)+", ",", s)
    s = re.sub(r",\s*([.;:!?])", r"\1", s)
    s = re.sub(r"\s+([,.;:!?])", r"\1", s)
    s = re.sub(r"([.;:!?])\s*,", r"\1", s)
    return s.strip(" ,")


def _is_editorial(note: str) -> bool:
    """A note about where the entry came from, not about the word: shown on screen, not read."""
    low = note.lower()
    return "biên tập" in low or "biên soạn" in low or "tài liệu gốc" in low


def _sentence(text: str) -> str:
    text = text.strip()
    return text if not text or text[-1] in ".!?…" else text + "."


def _short(text: str, limit: int = 480) -> str:
    """Cut a long passage at a sentence boundary so one note cannot swamp the recording."""
    if len(text) <= limit:
        return text
    cut = text[:limit]
    end = max(cut.rfind(". "), cut.rfind("; "))
    return (cut[: end + 1] if end > limit // 2 else cut).strip()


def _short_by_line(text: str, limit: int) -> str:
    """Like `_short`, for a list: if it is too long, keep whole lines and drop the rest."""
    if len(text) <= limit:
        return text
    cut = text[:limit]
    end = cut.rfind("\n")
    return (cut[:end] if end > limit // 2 else cut).strip()


def _ko_line(text: str, *, shadow: bool) -> str:
    """A Korean or English sentence as its own line. `shadow` ends it with an ellipsis, which the
    voice plan turns into a real gap for the learner to repeat it in; otherwise the
    sentence keeps its own ending, so a question is still read as one."""
    text = re.sub(r"\s*/\s*", ", ", text.strip())  # 아침 / 점심 -> two words, not "slash"
    text = re.sub(r"\(\s*[^\w()]+\s*\)", "", text)  # 제곱미터(㎡): a symbol is not read
    text = re.sub(r"\(([^()]*)\)", r"\1", text)  # 배(가) 고프다 -> 배가 고프다
    text = re.sub(r"\bsb\b", "somebody", text)
    text = re.sub(r"\bsth\b", "something", text)
    ending = text[-1] if text and text[-1] in ".!?…" else ""
    body = text.rstrip(".!?…").strip()
    if shadow:
        return body + _SAY_GAP
    return body + (ending if ending in ("?", "!") else ".")


def _examples(line: GrammarLine | VocabLine) -> list[tuple[str, str | None]]:
    ko = [x.strip() for x in (line.example_en or "").split("\n") if x.strip()]
    vi = [x.strip() for x in (line.example_vi or "").split("\n") if x.strip()]
    return [(k, vi[i] if i < len(vi) else None) for i, k in enumerate(ko)]


_TIER_SPOKEN = {
    "produce": "Đây là kiến thức mở rộng. Mức cần đạt là dùng được khi viết và nói.",
    "recognize": "Đây là kiến thức mở rộng. Mức cần đạt là nhận ra khi đọc và nghe.",
}


_SCREEN_LAYOUT_LIMIT = 1400  # a section laid out with a table or a word list is longer than a paragraph


def _is_screen_layout(body: str) -> bool:
    """True when a section body uses the `| table |` or `- bullet` layout of the rule-heavy cards
    (the older `•` bullets are plain text, read as they always were)."""
    return any(ln.lstrip().startswith(("|", "- ")) for ln in body.split("\n"))


def _close(cell: str) -> str:
    """A table cell as a sentence of its own: a full stop unless it already ends in one (a question
    stays a question; markup around the end does not count)."""
    return cell if cell.rstrip("`*_ ")[-1:] in (".", "?", "!", "…") else cell + "."


def _unshout(text: str) -> str:
    """The screen marks a table's key words in capitals (NGUYÊN ÂM, GIỮ); the voice reads them as words."""
    return re.sub(r"[^\W\d_]{2,}", lambda m: m.group().lower() if m.group().isupper() else m.group(), text)


def _spoken_body(body: str) -> str:
    """A section body as it is read out. A `| a | b | c |` table is read row by row, without its
    header row and without the list of endings in the first cell: the short label (the part of that
    cell before " — "), then what the other cells say. A `- ` bullet is read as a plain line."""
    out: list[str] = []
    in_table = False
    for ln in body.split("\n"):
        s = ln.strip()
        if s.startswith("|"):
            cells = [c.strip() for c in s.strip("|").split("|")]
            if not in_table:  # the first row of a table is its header: for the screen only
                in_table = True
                continue
            if all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
                continue  # the `---` separator row
            cells = [c for c in cells if c]
            if cells:
                cells[0] = cells[0].split(" — ")[0].strip()
                out.append(" ".join(_close(_unshout(c)) for c in cells))
            continue
        in_table = False
        out.append(re.sub(r"^\s*-\s+", "", ln))
    return "\n".join(out)


def _spoken_usage_parts(g: GrammarLine) -> list[tuple[str, str | None, str, str]]:
    """How a pattern is built and when it is used, as (section key, label, body as written, what is
    said). An extension card says first what level it is (key "tier"); only its "Cấu tạo" and
    "Hoàn cảnh dùng" are read (the "why this one" reasoning is what the contrasts that follow say,
    and "trong bài này" is for the screen)."""
    if not g.usage_vi:
        return []
    out: list[tuple[str, str | None, str, str]] = []
    tier, level = grammar_tier(g.usage_vi)
    if tier == "extension" and level in _TIER_SPOKEN:
        out.append(("tier", None, "", _TIER_SPOKEN[level]))
    for section in usage_sections(g.usage_vi):
        if section.key in ("why", "lesson"):
            continue
        lead = f"{spoken_vi(section.label)}. " if section.label else ""
        text = lead + spoken_vi(_spoken_body(section.body_vi))
        if _is_screen_layout(section.body_vi):
            said = _sentence(_short_by_line(text, _SCREEN_LAYOUT_LIMIT))
        else:
            said = _sentence(_short(text))
        out.append((section.key, section.label, section.body_vi, said))
    return out


def _spoken_usage(g: GrammarLine) -> list[str]:
    return [said for _key, _label, _body, said in _spoken_usage_parts(g)]


# -------------------------------------------------------------- template script --
@dataclass(frozen=True)
class LectureLine:
    """What one line of the script shows on the lecture's slides: the slide it belongs to, and the
    piece of that slide it brings in (None: nothing new, the line only talks about what is there)."""

    slide: int
    show: str | None = None


@dataclass(frozen=True)
class Lecture:
    script: str
    # one per non-empty line of `script`, in order
    lines: list[LectureLine]
    # what each slide holds, for the screen (texts as written in the lesson, not as said)
    slides: list[dict[str, Any]]


def build_template_lecture(lesson: LessonSource) -> Lecture:
    """The fixed lecture of a lesson (`build_template_script`) and the slides that go with it: a
    title, a slide per word, a slide per grammar pattern, a slide per note, the review and the
    recap. Each line of the script says which slide it is on and what it brings onto it, so the
    screen shows a thing when the voice says it, and not before."""
    if lesson.authored:
        return build_authored_lecture(lesson)
    out: list[tuple[str, int, str | None]] = []  # (text, slide, show)
    slides: list[dict[str, Any]] = []

    def slide(kind: str, **data: Any) -> int:
        slides.append({"kind": kind, **data})
        return len(slides) - 1

    def say(text: str, at: int, show: str | None = None) -> None:
        out.append((text, at, show))

    n_v, n_g, n_n = len(lesson.vocab), len(lesson.grammar), len(lesson.notes)

    t = slide("title", title=lesson.title, title_en=lesson.title_en, vocab=n_v, grammar=n_g, notes=n_n)
    say(_sentence(f"Bài học {spoken_vi(lesson.title)}"), t, "title")
    if lesson.title_en:
        say(_ko_line(lesson.title_en.replace("/", ","), shadow=False), t, "title_en")
    counts = ([f"{n_v} từ vựng"] if n_v else []) + ([f"{n_g} mẫu ngữ pháp"] if n_g else []) + ([f"{n_n} lưu ý"] if n_n else [])
    how = "Mỗi từ mình đọc một lần, bạn nhắc lại theo trong quãng nghỉ" if n_v else "Mỗi câu ví dụ mình đọc một lần, bạn nhắc lại theo trong quãng nghỉ"
    say(_sentence(f"Bài này có {', '.join(counts)}. {how}"), t, "counts")

    # ---- vocabulary: the word, a gap to say it, its meaning (a sitting without words has no such part)
    # parts keep their usual numbers (words 1, patterns 2, notes 3); only a sitting with no
    # words at all counts from its patterns
    part = ("một", "hai", "ba") if n_v else ("", "một", "hai")
    if n_v:
        sec = slide("section", n=1, title="Từ vựng", count=n_v)
        say("Phần một. Từ vựng.", sec, "title")
    for i, v in enumerate(lesson.vocab):
        w = slide(
            "word",
            index=i,
            of=n_v,
            headword=v.headword,
            icon=word_icon(v.headword),
            meaning=v.meaning_vi,
            pos=v.pos,
            pron=v.pron,
            note=v.note_vi if v.note_vi and not _is_editorial(v.note_vi) else None,
            examples=[{"ko": ko, "vi": vi} for ko, vi in _examples(v)],
        )
        # one line: the word, the gap to say it, then the meaning (shown with its own run)
        say(f"{_ko_line(v.headword, shadow=True)} {_sentence(spoken_vi(v.meaning_vi))}", w, "word")
        if v.note_vi and not _is_editorial(v.note_vi):
            say(_sentence(spoken_vi(v.note_vi)), w, "note")
        for k, (ko, vi) in enumerate(_examples(v)):
            say(_sentence("Ví dụ"), w, None)
            say(_ko_line(ko, shadow=True), w, f"ex{k}")
            if vi:
                say(_sentence(spoken_vi(vi)), w, f"ex{k}_vi")
    if n_v > 1:
        r = slide("review", words=[{"headword": v.headword, "meaning": v.meaning_vi} for v in lesson.vocab])
        say("Bây giờ mình ôn lại. Nghe từng từ và nhắc lại.", r, "title")
        for i, v in enumerate(lesson.vocab):
            say(_ko_line(v.headword, shadow=True), r, f"w{i}")  # same text as above: the voice reuses it

    # ---- grammar
    if n_g:
        sec = slide("section", n=2 if n_v else 1, title="Ngữ pháp", count=n_g)
        say(f"Phần {part[1]}. Ngữ pháp.", sec, "title")
    shadow_lines: list[str] = []
    recap: list[dict[str, str | None]] = []
    for i, g in enumerate(lesson.grammar, 1):
        parts = _spoken_usage_parts(g)
        note, _source = split_source_note(g.note_vi)  # where an entry came from is shown, not read
        examples = _examples(g)
        gs = slide(
            "grammar",
            index=i - 1,
            of=n_g,
            pattern=g.pattern,
            meaning=g.meaning_vi,
            sections=[{"key": key, "label": label, "body": body} for key, label, body, _said in parts if body],
            contrasts=[{"pattern": other, "diff": diff} for other, diff in g.contrasts if diff],
            note=note or None,
            examples=[{"ko": ko, "vi": vi} for ko, vi in examples],
        )
        say(_sentence(f"Mẫu số {i}. {speakable_pattern(g.pattern)}"), gs, "pattern")
        say(_sentence(f"Nghĩa là {spoken_vi(g.meaning_vi)}"), gs, "meaning")
        k = 0
        for key, _label, body, said in parts:
            say(said, gs, f"s{k}" if body else "tier")
            if body:
                k += 1
        c = 0
        for other, diff in g.contrasts:
            if diff:
                # say which pattern is being compared, unless the text opens with it already
                lead = "" if diff.lstrip().startswith("`") or not other else f"So với {speakable_pattern(other)}. "
                say(_sentence(_short(lead + spoken_vi(diff))), gs, f"c{c}")
                c += 1
        if note:
            say(_sentence(_short(spoken_vi(note), 640)), gs, "note")
        for k, (ko, vi) in enumerate(examples):
            say("Ví dụ.", gs, None)
            say(_ko_line(ko, shadow=False), gs, f"ex{k}")
            if vi:
                say(_sentence(spoken_vi(vi)), gs, f"ex{k}_vi")
            say("Bạn nhắc lại nhé.", gs, f"ex{k}_say")
            say(_ko_line(ko, shadow=True), gs, None)
            shadow_lines.append(_ko_line(ko, shadow=True))
            recap.append({"ko": ko, "vi": vi})

    # ---- notes
    if n_n:
        sec = slide("section", n=3 if n_v else 2, title="Lưu ý", count=n_n)
        say(f"Phần {part[2]}. Lưu ý.", sec, "title")
        for i, (title, body) in enumerate(lesson.notes):
            ns = slide("note", title=title, body=body)
            head = _sentence(spoken_vi(title)) if title else ""
            said = spoken_vi(body)
            # a note the KIIP course needs (life in Korea, the rules) is read to the end
            say(f"{head} {_sentence(said if i in lesson.full_notes else _short(said))}".strip(), ns, "body")

    # ---- take-home
    if shadow_lines:
        rc = slide("recap", examples=recap)
        say("Cuối bài, mình nghe lại các câu ví dụ.", rc, "title")
        for k, line in enumerate(shadow_lines):
            say(line, rc, f"ex{k}")
    end = slide("end", title=lesson.title)
    say("Hết bài. Chúc bạn học tốt.", end, "title")

    script = _finish("\n".join(text for text, _at, _show in out))
    return Lecture(script, _line_cues(script, out), slides)


def _core_meaning(meaning: str) -> str:
    """The meaning as a person would say it: no «Nhớ: …» tail, no "(= synonym)" gloss."""
    core = re.split(r"\s*[·•]\s*Nhớ\b", meaning, maxsplit=1)[0]
    core = re.sub(r"\s*\(=[^)]*\)", "", core).strip()
    return core or meaning


def build_authored_lecture(lesson: LessonSource) -> Lecture:
    """A sitting's lecture as an editor wrote it (SessionSeed.lecture): the slides in order, each
    with the lines said while it is up. A line is Vietnamese narration ({"say": …}) or an English
    sentence on its own ({"en": …}; "gap": true leaves the silence to repeat it in); "show" names
    the piece of the slide the line brings in, as in the template. Three kinds of slide are filled
    in from the lesson so the script cannot drift from the cards: "title" (the counts), "word" (a
    word of the sitting by its headword: meaning, part of speech, transcription, example) and
    "recap" (the sentences said for repeating so far). A "scene" is passed through: a picture the
    app draws ("visual") with the pieces the lines bring in."""
    out: list[tuple[str, int, str | None]] = []
    slides: list[dict[str, Any]] = []
    by_word = {v.headword: v for v in lesson.vocab}
    n_words = sum(1 for s in lesson.authored if s.get("kind") == "word")
    word_i = 0
    said: list[dict[str, str | None]] = []  # every English sentence said for repeating, for the recap

    def say_lines(lines: list[dict], at: int) -> None:
        for ln in lines:
            show = ln.get("show")
            if ln.get("en"):
                gap = bool(ln.get("gap"))
                out.append((_ko_line(str(ln["en"]), shadow=gap), at, show))
                if gap and ln.get("recap", True):
                    said.append({"ko": str(ln["en"]), "vi": ln.get("vi")})
            else:
                out.append((_sentence(spoken_vi(str(ln["say"]))), at, show))

    for spec in lesson.authored:
        kind = spec.get("kind")
        lines = list(spec.get("lines") or [])
        if kind == "title":
            slides.append({
                "kind": "title", "title": lesson.title, "title_en": lesson.title_en,
                "vocab": len(lesson.vocab), "grammar": len(lesson.grammar), "notes": 0,
                "hook": spec.get("hook"),
                # the picture shows this sitting's words, not the whole lesson's
                "words": [str(x["headword"]) for x in lesson.authored if x.get("kind") == "word"],
            })
            say_lines(lines, len(slides) - 1)
        elif kind == "word":
            v = by_word[str(spec["headword"])]
            ex = _examples(v)
            slides.append({
                "kind": "word", "index": word_i, "of": n_words, "headword": v.headword, "icon": word_icon(v.headword),
                "meaning": v.meaning_vi, "pos": v.pos, "pron": v.pron, "note": None,
                "examples": [{"ko": ko, "vi": vi} for ko, vi in ex],
            })
            word_i += 1
            at = len(slides) - 1
            say_lines(lines, at)  # the editor's lead-in: why this word, here
            # the memory hook («Nhớ: …») and the "= synonym" gloss are for the eye; the lead-in already told the story
            out.append((f"{_ko_line(v.headword, shadow=True)} {_sentence(spoken_vi(_core_meaning(v.meaning_vi)))}", at, "word"))
            for k, (ko, vi) in enumerate(ex):
                out.append((_ko_line(ko, shadow=True), at, f"ex{k}"))
                if vi:
                    out.append((_sentence(spoken_vi(vi)), at, f"ex{k}_vi"))
        elif kind == "recap":
            slides.append({"kind": "recap", "examples": list(said)})
            at = len(slides) - 1
            say_lines(lines, at)
            for k, e in enumerate(said):
                out.append((_ko_line(str(e["ko"]), shadow=True), at, f"ex{k}"))
        else:  # "scene", "end": drawn by the app from what the editor wrote
            slides.append({k: v for k, v in spec.items() if k != "lines"} | ({"title": lesson.title} if kind == "end" else {}))
            say_lines(lines, len(slides) - 1)
    script = _finish("\n".join(text for text, _at, _show in out))
    return Lecture(script, _line_cues(script, out), slides)


def shadow_runs(script: str) -> list[list[int]]:
    """[line, run] of every stretch of the script said for the learner to repeat (a target-language
    run that ends in the gap mark), cut exactly as the voice cuts it. The app cannot work this out
    itself for English: without Hangul it sees a line as one run."""
    from app.services import lecture_voice

    return [
        [r.line, r.run]
        for r in lecture_voice.split_runs(script)
        if r.lang == lecture_voice.KO and re.search(r"(\.{2,}|…)\s*$", r.text)
    ]


def _finish(raw: str) -> str:
    script = podcast_script.clean_script_for_tts(raw)
    return re.sub(r"([?!])\.", r"\1", script)


def _line_cues(script: str, out: list[tuple[str, int, str | None]]) -> list[LectureLine]:
    """The cue of every non-empty line of the finished script. Each piece said is cleaned on its
    own and its lines are matched, in order, to the script's lines (cleaning the whole script and
    cleaning piece by piece give the same lines; a line that does not match takes the cue of the
    piece being read, so the slides can only lag, never jump ahead)."""
    lines = [ln for ln in script.split("\n") if ln.strip()]
    cues: list[LectureLine] = []
    i = 0
    for text, at, show in out:
        piece = [ln for ln in _finish(text).split("\n") if ln.strip()]
        for k, ln in enumerate(piece):
            if i >= len(lines):
                break
            if ln == lines[i] or k == 0:
                cues.append(LectureLine(at, show if k == 0 else None))
                i += 1
    last = cues[-1] if cues else LectureLine(0)
    while len(cues) < len(lines):
        cues.append(LectureLine(last.slide))
    return cues[: len(lines)]


def build_template_script(lesson: LessonSource) -> str:
    """The fixed lecture of a lesson: Vietnamese narration with the Korean said slowly
    where the learner is to repeat it. Same lesson, same text, every time."""
    return build_template_lecture(lesson).script


# --------------------------------------------------------------- story (parts) --
@dataclass(frozen=True)
class Part:
    index: int  # 1-based
    total: int
    vocab: tuple[int, int]  # [start, end) into the lesson's vocab list
    grammar: tuple[int, int]


def _even_split(count: int, parts: int) -> list[tuple[int, int]]:
    base, extra = divmod(count, parts)
    out, start = [], 0
    for i in range(parts):
        size = base + (1 if i < extra else 0)
        out.append((start, start + size))
        start += size
    return out


def plan_parts(n_vocab: int, n_grammar: int) -> list[Part]:
    """How a lesson is cut for Gemini: as few parts as keep each within
    MAX_VOCAB_PER_PART words and MAX_GRAMMAR_PER_PART patterns, vocabulary and grammar
    spread evenly so every part teaches something and the parts stay about the same
    length. A short lesson is one part (the lecture is written in one go)."""
    total = max(
        1,
        -(-n_vocab // MAX_VOCAB_PER_PART),
        -(-n_grammar // MAX_GRAMMAR_PER_PART),
    )
    v = _even_split(n_vocab, total)
    g = _even_split(n_grammar, total)
    return [Part(i + 1, total, v[i], g[i]) for i in range(total)]


def story_vocab(lesson: LessonSource) -> list[podcast_script.Vocab]:
    return [
        (v.headword, None, v.meaning_vi, v.example_en, None, None, v.note_vi if v.note_vi and not _is_editorial(v.note_vi) else None)  # type: ignore[misc]
        for v in lesson.vocab
    ]


def story_grammar(lesson: LessonSource) -> list[podcast_script.Grammar]:
    rows: list[Any] = []
    for g in lesson.grammar:
        extra_bits = [b for b in (split_source_note(g.note_vi)[0], *(d for _p, d in g.contrasts)) if b]
        rows.append(
            (
                g.pattern,
                g.meaning_vi,
                g.example_en.replace("\n", " / ") if g.example_en else None,
                g.usage_vi,
                None,
                " ".join(extra_bits) or None,
            )
        )
    return rows


def story_notes(lesson: LessonSource) -> list[str]:
    return [((t + ": ") if t else "") + b for t, b in lesson.notes]


# ---------------------------------------------------------- dialogue recordings --
def exercise_turns(exercise: dict[str, Any]) -> list[tuple[str, str]] | None:
    """The spoken turns of a practice exercise as [(speaker "F"|"M"|"N", text)], or None
    when it has none. A listening exercise keeps them in its audio stimulus, a speaking
    task (S4) in `audio`."""
    block = exercise.get("audio") if exercise.get("type") == "speak" else exercise.get("stimulus")
    if not isinstance(block, dict) or block.get("kind") != "audio":
        return None
    turns = [(str(t["speaker"]), str(t["text"]).strip()) for t in block.get("turns", []) if str(t.get("text", "")).strip()]
    return turns or None


def turns_signature(turns: Sequence[tuple[str, str]]) -> str:
    """Short hash of who says what, so a changed script is recorded again."""
    blob = "\n".join(f"{who}:{text}" for who, text in turns)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:8]


def dialogue_cache_key(exercise_id: str, turns: Sequence[tuple[str, str]], spec: str) -> str:
    return f"lex:{exercise_id}:{turns_signature(turns)}:{spec}"

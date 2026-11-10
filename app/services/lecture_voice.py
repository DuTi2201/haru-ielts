"""Cut a lecture script into runs by language, so each run can be voiced by a
voice that actually speaks that language.

The "Bài giảng tổng hợp" script is Vietnamese explanation with Korean phrases
and examples inside it ("... Mình cùng nói chậm nhé. 이거 얼마예요... nghĩa là
..."). A Google Chirp 3 HD voice belongs to ONE locale: a ko-KR voice reading
Vietnamese (or a vi-VN voice reading Hangul) gets the pronunciation wrong,
which is exactly the part that must be right for Korean. So the script is cut
wherever the language changes and each piece is sent to the matching voice.

Haru English: the script has no Hangul, so the cut is between English and Vietnamese words
(`_split_paragraph_latin`). KO keeps its name but means "the target language" (English here):
tts.py voices those runs with Azure Neural, the Vietnamese runs with Chirp 3 HD.

Pure text processing, no network: the voicing lives in app/services/tts.py.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

KO = "ko"
VI = "vi"

# Silence (ms) inserted after a run. The learner is meant to repeat Korean
# phrases after hearing them, so a Korean run that ends on an ellipsis gets a
# real gap, not just the model's own pause.
GAP_LANGUAGE_SWITCH_MS = 120
GAP_AFTER_PARAGRAPH_MS = 500
GAP_AFTER_ELLIPSIS_KO_MS = 700
GAP_AFTER_ELLIPSIS_VI_MS = 350

_ELLIPSIS_END = re.compile(r"(\.{2,}|…)\s*[\"'”’)\]]*\s*$")


@dataclass(frozen=True)
class Run:
    lang: str  # KO or VI
    text: str
    pause_after_ms: int
    # where it is in the script: the line (counting non-empty lines) and its place in that line,
    # so the recording can say when each one starts (the lecture's slides follow it)
    line: int = -1
    run: int = 0


def _is_hangul(ch: str) -> bool:
    o = ord(ch)
    return 0xAC00 <= o <= 0xD7A3 or 0x1100 <= o <= 0x11FF or 0x3130 <= o <= 0x318F or 0xA960 <= o <= 0xA97F


def _lang_of(ch: str) -> str | None:
    """KO for Hangul, VI for any other letter, None for spaces, digits and
    punctuation (those stay with whatever run they follow)."""
    if _is_hangul(ch):
        return KO
    if ch.isalpha():
        return VI
    return None


def _has_speech(text: str) -> bool:
    return any(ch.isalpha() or ch.isdigit() for ch in text)


# ---- English lectures (no Hangul): Latin letters are both English and Vietnamese, so the
# language is decided word by word. A word with a Vietnamese letter or tone mark is Vietnamese
# ("hard"). A plain-ASCII word that cannot be a Vietnamese syllable is English ("hard"). The rest
# ("hay", "cho", "nghe", but also "to", "do", "so", "the", "in") are "soft": they lean Vietnamese
# unless they are also English words (EN_LIKE), and their neighbours inside the same clause can
# overrule that lean (see `_resolve`).
_VI_MARK_RE = re.compile(r"[À-ÃÈ-ÊÌÍÒ-ÕÙÚÝà-ãè-êìíò-õùúýĂăĐđĨĩŨũƠơƯưẠ-ỹ]")
_WORD_RE = re.compile(r"[A-Za-zÀ-ỹĐđ]+(?:['’][A-Za-z]+)?(?:-[A-Za-z]+)*")
_INITIALS = "b c ch d g gh gi h k kh l m n ng ngh nh p ph qu r s t th tr v x".split() + [""]
# rhymes a level-tone syllable can have without any mark (c/ch/p/t endings always carry a tone mark)
_RHYMES = """a ai ao au ay am an ang anh e eo em en i ia iu im in inh o oi om on ong oa oai oay oan oang
oanh oe oeo oen u ua ui um un ung uy uya uynh uyu y""".split()


def vi_syllables() -> frozenset[str]:
    """Every unmarked Vietnamese syllable (and "tivi"): the words that may be Vietnamese without a mark."""
    return frozenset({i + r for i in _INITIALS for r in _RHYMES} | {"tivi"})


_VI_SYLLABLES = vi_syllables()
# unmarked Vietnamese syllables that are also English words: those found in the pure-English
# strings of the B1 seed (Vietnamese names such as Minh, Lan, Hoa left out) plus short function
# words. Vietnamese words that are rare in English ("con", "tin", "sang", "bay") are not listed:
# inside an English clause they still become English (`_resolve`).
EN_LIKE = frozenset(
    """a am an ban be buy by can day den do don go gun he hen hi him in long man may me men min mum my
    no non on pa pay pen ram ran rang run say sin so son song sun ten than the them then thin to tom ton
    try ray lay hum gum bang gang sum ring i oh hey""".split()
)
_CONNECTORS = frozenset(("hoặc", "cộng", "và"))
_CLAUSE_BREAK_RE = re.compile(r"[.,:;!?…()\"“”]")


def _hard_lang(word: str) -> str | None:
    if _VI_MARK_RE.search(word):
        return VI
    low = word.lower()
    return None if low in _VI_SYLLABLES or low in EN_LIKE else KO


def _resolve(words: list, langs: list[str | None], i: int, line: str) -> str:
    """The language of the soft word i. Its neighbours are the nearest hard words on each side in
    the same clause (punctuation ends a clause; connectors and other soft words are skipped)."""

    def nearest(step: int) -> str | None:
        j = i
        while 0 <= j + step < len(words):
            a, b = (words[j], words[j + step]) if step > 0 else (words[j + step], words[j])
            if _CLAUSE_BREAK_RE.search(line[a.end() : b.start()]):
                return None
            j += step
            if langs[j] is not None and words[j].group().lower() not in _CONNECTORS:
                return langs[j]
        return None

    low = words[i].group().lower()
    left, right = nearest(-1), nearest(1)
    if low in EN_LIKE:
        nxt = words[i + 1] if i + 1 < len(words) else None
        glued_to_vi = (
            nxt is not None and not line[words[i].end() : nxt.start()].strip()
            and langs[i + 1] == VI and nxt.group().lower() not in _CONNECTORS
        )  # "so với", "do đó", "to lớn"
        return VI if glued_to_vi or (left == VI and right == VI) else KO
    return KO if left == KO and right == KO else VI  # "hay" inside an English sentence is English


def _split_paragraph_latin(line: str) -> list[tuple[str, str]]:
    """English (KO, the target language) and Vietnamese (VI) runs of a line with no Hangul.
    Punctuation, digits and spaces stay with the run they follow."""
    words = list(_WORD_RE.finditer(line))
    if not words:
        return [(VI, line.strip())] if line.strip() else []
    hard = [_hard_lang(m.group()) for m in words]
    langs = [lang or _resolve(words, hard, i, line) for i, lang in enumerate(hard)]
    runs: list[list] = []  # [lang, start, end]
    for m, lang in zip(words, langs):
        if runs and runs[-1][0] == lang:
            runs[-1][2] = m.end()
        else:
            runs.append([lang, m.start(), m.end()])
    out: list[tuple[str, str]] = []
    for i, (lang, start, _end) in enumerate(runs):
        begin = 0 if i == 0 else start
        stop = runs[i + 1][1] if i + 1 < len(runs) else len(line)
        out.append((lang, line[begin:stop].strip()))
    return out


def _split_paragraph(line: str) -> list[tuple[str, str]]:
    runs: list[tuple[str, list[str]]] = []
    lead: list[str] = []  # neutral characters before the first letter
    for ch in line:
        lang = _lang_of(ch)
        if lang is None:
            (runs[-1][1] if runs else lead).append(ch)
        elif runs and runs[-1][0] == lang:
            runs[-1][1].append(ch)
        else:
            runs.append((lang, lead + [ch] if not runs else [ch]))
            lead = []
    return [(lang, "".join(chars).strip()) for lang, chars in runs]


def split_runs(script: str) -> list[Run]:
    """script -> language runs in reading order, each with the silence to put
    after it. A paragraph is one line. Runs with nothing to say (only
    punctuation) are dropped, and the paragraph's last run always carries at
    least the paragraph gap; the very last run of the script carries none."""
    out: list[Run] = []
    n = -1
    # a Korean lecture keeps the Hangul split; a script with no Hangul is English + Vietnamese
    split = _split_paragraph if any(_is_hangul(ch) for ch in script) else _split_paragraph_latin
    for line in script.splitlines():
        line = line.strip()
        if not line:
            continue
        n += 1
        pieces = [(lang, text) for lang, text in split(line) if _has_speech(text)]
        for i, (lang, text) in enumerate(pieces):
            last = i == len(pieces) - 1
            pause = GAP_AFTER_PARAGRAPH_MS if last else GAP_LANGUAGE_SWITCH_MS
            if _ELLIPSIS_END.search(text):
                pause = max(pause, GAP_AFTER_ELLIPSIS_KO_MS if lang == KO else GAP_AFTER_ELLIPSIS_VI_MS)
            out.append(Run(lang, text, pause, n, i))
    if out:
        last_run = out[-1]
        out[-1] = Run(last_run.lang, last_run.text, 0, last_run.line, last_run.run)
    return out

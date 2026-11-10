"""Practice on real TOPIK II papers — the content and the rules, with no database.

`app/seed/exams/topik-<n>.json` holds one past paper, question by question, written by hand for this
app (personal study only — the folder never leaves the private repo and is only served behind login).
Every question carries what a learner needs to LEARN from it, not only to answer it:

* the script / passage with a line-by-line Vietnamese translation,
* why the right option is right and why each wrong option is wrong,
* the grammar patterns (V/A + form) and words it rests on,
* what the question teaches ("take") and three hints: what to look for (`focus`), the options in
  Vietnamese (`ov`) and one option to cross out (`elim`).

`types.json` holds the guide of each question type (what it asks, three steps, the traps) and the
eleven "cụm" (families) the types are grouped in. A question has a `tier` (1 = the points nobody
should lose, 2 = the middle, 3 = the hard ones) so a learner can make the easy ones solid first.

This module is pure: it loads and checks the files, finds which lesson cards a question rests on,
and applies the rules of the selection (what to offer next) and of the summary. The database side is
app.services.real_exam_db; the check is `python3 -m app.services.real_exam`.
"""
from __future__ import annotations

import json
import math
import re
from collections import Counter, defaultdict
from collections.abc import Container, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import ConfigDict, Field, ValidationError

from app.services import lesson_seed as seed
from app.services import passages

EXAM_DIR = seed.SEED_DIR / "exams"
IMG_DIR = EXAM_DIR / "img"
SECTIONS = ("L", "R", "W")
SEC_NAME_VI = {"L": "Nghe", "R": "Đọc", "W": "Viết"}
SKILL_OF = {"L": "nghe", "R": "đọc", "W": "viết"}  # the `skill` of an error_log row
VOICE_OF = passages.VOICE_OF  # who speaks -> the Chirp voice (M: male, F: female)
HINT_LEVELS = 3
MCQ_TYPES_PREFIX = ("listen_", "read_")

# ---- how long before a question comes back (the "ăn chắc mặc bền" rules) --------------------
REASK_WRONG = timedelta(hours=12)  # a wrong answer returns after this
REASK_AIDED = timedelta(days=3)  # a right answer that needed a hint is tried again unaided after this
REASK_SOLID = timedelta(days=7)  # a solid answer is checked again after this
SOLID_SHARE = 0.8  # a tier of a type is "vững" when this share of its questions is solid
DEFAULT_SET_SIZE = 5
MAX_SET_SIZE = 12
WRITING_SET_SIZE = 2  # a written answer is long: a sitting holds at most this many
MIN_GRAM_CORE = 3  # shortest grammar core compared by containment (shorter ones must be equal)


# ------------------------------------------------------------------ the files --
class Gram(seed._M):
    k: str = Field(min_length=1, max_length=120)  # the pattern as written in a lesson: "V-고 나서"
    vi: str = Field(min_length=1, max_length=400)


class Blank(seed._M):
    id: str
    model: str
    accepted: list[str] = Field(min_length=1)
    why: str
    gram: list[Gram] = Field(min_length=1)
    traps: list[str] = []


class RubricRow(seed._M):
    k: str
    w: str


class ItemSeed(seed._M):
    model_config = ConfigDict(extra="forbid", protected_namespaces=())

    id: str
    sec: Literal["L", "R", "W"]
    n: int
    type: str
    tier: Literal[1, 2, 3]
    # the question
    stem: str | None = None
    passage: str | None = None
    given: str | None = None  # the sentence to be put in (read_insert)
    givenTr: str | None = None
    turns: list[tuple[Literal["F", "M", "N"], str]] | None = None  # the script, by speaker
    fmt: str | None = None
    tr: str | None = None  # the translation (line by line, same count as the passage or the turns)
    img: str | None = None
    pic: bool = False  # the options are pictures/charts (all in `img`)
    same_as: int | None = None  # shares its passage / script / image with question n of the same section
    opts: list[str] | None = None
    ov: list[str] | None = None
    ans: int | None = None
    # what is explained afterwards
    why: str | None = None
    wrong: dict[str, str] = {}
    gloss: list[tuple[str, str]] = []
    gram: list[Gram] = []
    take: str | None = None
    focus: str | None = None
    elim: int | None = None
    # section W
    blanks: list[Blank] | None = None
    data: list[str] | None = None
    dataTr: list[str] | None = None
    limit: tuple[int, int] | None = None
    model: str | None = None
    modelTr: str | None = None
    phrases: list[Gram] | None = None
    rubric: list[RubricRow] | None = None
    tips: str | None = None
    prompt: str | None = None
    promptTr: str | None = None
    questions: list[str] | None = None
    questionsTr: list[str] | None = None


class ExamFile(seed._M):
    id: str
    title: str
    short: str
    level: str
    omitted: dict[str, list[int]] = {}  # questions of the paper that are not published and so not here
    items: list[ItemSeed]


class FamilySeed(seed._M):
    code: str
    sec: Literal["L", "R", "W"]
    order: int
    name_vi: str
    blurb_vi: str
    gain_vi: str


class TypeSeed(seed._M):
    sec: Literal["L", "R", "W"]
    family: str
    name_vi: str
    asks_vi: str
    steps: list[str] = Field(min_length=3, max_length=3)
    traps: list[str] = Field(min_length=1)
    tips: list[str] = Field(min_length=1)
    gain_vi: str


class TypesFile(seed._M):
    families: list[FamilySeed]
    types: dict[str, TypeSeed]


# ------------------------------------------------------------------- loaded --
@dataclass(frozen=True)
class Clip:
    """One thing said in a listening question: who, in which voice, and the words."""

    who: str
    voice: str
    ko: str


@dataclass(frozen=True)
class Item:
    """A question as the app uses it: the seed plus whatever it borrows from the question it shares
    its passage with (`same_as`)."""

    seed: ItemSeed
    exam: str
    source: ItemSeed  # the question that holds the shared passage / script / image
    bundle: tuple[str, ...]  # ids of the questions sharing the passage, in order (itself included)

    @property
    def qid(self) -> str:
        return self.seed.id

    @property
    def sec(self) -> str:
        return self.seed.sec

    @property
    def n(self) -> int:
        return self.seed.n

    @property
    def type(self) -> str:
        return self.seed.type

    @property
    def tier(self) -> int:
        return self.seed.tier

    @property
    def is_mcq(self) -> bool:
        return self.seed.sec != "W"

    @property
    def stem(self) -> str | None:
        """The instruction of the question. The first listening questions are printed without one:
        the paper's own standing instruction of that type is used."""
        return self.seed.stem or DEFAULT_STEM.get(self.seed.type)

    @property
    def passage(self) -> str | None:
        return self.seed.passage or self.source.passage

    @property
    def tr(self) -> str | None:
        return self.seed.tr or self.source.tr

    @property
    def img(self) -> str | None:
        return self.seed.img or self.source.img

    @property
    def given(self) -> str | None:
        return self.seed.given or self.source.given

    @property
    def given_tr(self) -> str | None:
        return self.seed.givenTr or self.source.givenTr

    @property
    def turns(self) -> list[tuple[str, str]]:
        return list(self.seed.turns or self.source.turns or [])

    @property
    def clips(self) -> list[Clip]:
        return clips_of(self.turns)

    @property
    def tr_lines(self) -> list[str]:
        return (self.tr or "").split("\n") if self.tr else []


@dataclass(frozen=True)
class Bank:
    exams: dict[str, ExamFile]
    items: dict[str, Item]
    families: dict[str, FamilySeed]
    types: dict[str, TypeSeed]

    def of_exam(self, exam: str) -> list[Item]:
        return [i for i in self.items.values() if i.exam == exam]

    def of_type(self, code: str) -> list[Item]:
        return [i for i in self.items.values() if i.type == code]

    def family_of(self, code: str) -> FamilySeed:
        return self.families[self.types[code].family]

    def types_of_family(self, family: str) -> list[str]:
        return sorted(
            (c for c, t in self.types.items() if t.family == family and any(i.type == c for i in self.items.values())),
            key=lambda c: (min(i.n for i in self.items.values() if i.type == c and i.sec == self.types[c].sec), c),
        )


# the standing instruction of the listening types whose questions are printed without one
DEFAULT_STEM = {
    "listen_picture": "다음을 듣고 알맞은 그림을 고르십시오.",
    "listen_chart": "다음을 듣고 알맞은 그래프를 고르십시오.",
    "listen_reply": "다음을 듣고 이어지는 말로 가장 알맞은 것을 고르십시오.",
    "listen_action": "다음을 듣고 이어서 할 행동으로 가장 알맞은 것을 고르십시오.",
    "listen_match": "다음을 듣고 내용과 같은 것을 고르십시오.",
    "listen_main_idea": "다음을 듣고 남자의 중심 생각으로 가장 알맞은 것을 고르십시오.",
}

_SPOKEN_SOUND = re.compile(r"\([^)]*\)")  # (딩동댕) (놀라며) — sound effects and stage directions
_HANGUL = re.compile(r"[가-힣]")


def clips_of(turns: Sequence[tuple[str, str]]) -> list[Clip]:
    """What is voiced: each turn with its sound effects and stage directions removed. A turn that is
    left with no Korean (the unspoken last turn of a "what is said next" question, `…`) is not voiced."""
    out: list[Clip] = []
    for who, text in turns:
        spoken = re.sub(r"\s+", " ", _SPOKEN_SOUND.sub(" ", text)).strip()
        if _HANGUL.search(spoken):
            out.append(Clip(who=who, voice=VOICE_OF[who], ko=spoken))
    return out


def _read(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def load() -> Bank:
    """Read every paper and the type guides. Raises ValueError on a file that does not parse."""
    try:
        guide = TypesFile.model_validate(_read(EXAM_DIR / "types.json"))
    except (ValidationError, OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"exams/types.json: {exc}") from exc
    exams: dict[str, ExamFile] = {}
    items: dict[str, Item] = {}
    for path in sorted(EXAM_DIR.glob("topik-*.json")):
        try:
            exam = ExamFile.model_validate(_read(path))
        except (ValidationError, OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"{path.name}: {exc}") from exc
        exams[exam.id] = exam
        by_n = {(i.sec, i.n): i for i in exam.items}
        bundles: dict[tuple[str, int], list[str]] = defaultdict(list)
        sources: dict[str, ItemSeed] = {}
        for i in exam.items:
            src = i
            seen = {i.n}
            while src.same_as is not None:
                nxt = by_n.get((src.sec, src.same_as))
                if nxt is None or nxt.n in seen:
                    raise ValueError(f"{path.name}: {i.id} shares a passage with a question that is not there")
                seen.add(nxt.n)
                src = nxt
            sources[i.id] = src
            bundles[(src.sec, src.n)].append(i.id)
        for i in exam.items:
            src = sources[i.id]
            items[i.id] = Item(seed=i, exam=exam.id, source=src, bundle=tuple(bundles[(src.sec, src.n)]))
    return Bank(
        exams=exams,
        items=items,
        families={f.code: f for f in guide.families},
        types=dict(guide.types),
    )


# ---------------------------------------------------------------------- checks --
def check(bank: Bank | None = None) -> list[str]:
    """Everything wrong with the papers and guides, as readable lines (empty = fine)."""
    bank = bank or load()
    problems: list[str] = []
    for code, t in bank.types.items():
        if t.family not in bank.families:
            problems.append(f"type {code}: unknown family {t.family}")
        elif bank.families[t.family].sec != t.sec:
            problems.append(f"type {code}: family {t.family} is of another section")
    for exam in bank.exams.values():
        ids = Counter(i.id for i in exam.items)
        problems += [f"{exam.id}: duplicate id {i}" for i, c in ids.items() if c > 1]
    for it in bank.items.values():
        s = it.seed
        tag = it.qid
        if s.id != f"{it.exam.removeprefix('topik-')}-{s.sec}-{s.n}":
            problems.append(f"{tag}: id does not match exam/section/number")
        t = bank.types.get(s.type)
        if t is None:
            problems.append(f"{tag}: type {s.type} has no guide")
        elif t.sec != s.sec:
            problems.append(f"{tag}: type {s.type} belongs to section {t.sec}")
        if not s.take or not s.focus:
            problems.append(f"{tag}: needs `take` and `focus`")
        if s.img and not (IMG_DIR / s.img).is_file():
            problems.append(f"{tag}: image {s.img} is missing")
        if s.sec == "W":
            problems += _check_writing(it)
            continue
        if not it.stem:
            problems.append(f"{tag}: no stem")
        if s.ans not in (1, 2, 3, 4):
            problems.append(f"{tag}: ans {s.ans}")
        if not s.pic:
            if not s.opts or len(s.opts) != 4:
                problems.append(f"{tag}: needs 4 options")
            if not s.ov or len(s.ov) != 4:
                problems.append(f"{tag}: needs 4 option translations")
        elif not it.img:
            problems.append(f"{tag}: picture options without an image")
        if s.elim not in (1, 2, 3, 4) or s.elim == s.ans:
            problems.append(f"{tag}: elim must be a wrong option")
        if set(s.wrong) != {str(x) for x in range(1, 5)} - {str(s.ans)}:
            problems.append(f"{tag}: `wrong` must explain exactly the three wrong options")
        if not s.why:
            problems.append(f"{tag}: no explanation")
        if s.sec == "L" and not s.pic and not it.clips and not s.same_as:
            problems.append(f"{tag}: a listening question with nothing to voice")
        if s.sec == "L" and it.turns and it.tr and len(it.tr_lines) != len(it.turns):
            problems.append(f"{tag}: translation has {len(it.tr_lines)} lines for {len(it.turns)} turns")
        if s.sec == "R" and it.passage and it.tr and len(it.tr_lines) != len(it.passage.split("\n")):
            problems.append(f"{tag}: translation has {len(it.tr_lines)} lines for {len(it.passage.split(chr(10)))} passage lines")
        for ko, vi in s.gloss:
            if not ko or not vi:
                problems.append(f"{tag}: empty gloss")
        for ko in clip_texts_too_long(it):
            problems.append(f"{tag}: a voiced turn is over the text-audio limit ({len(ko)})")
    return problems


def clip_texts_too_long(it: Item) -> list[str]:
    from app.core.config import settings

    return [c.ko for c in it.clips if len(c.ko) > settings.TEXT_AUDIO_MAX_CHARS]


def _check_writing(it: Item) -> list[str]:
    s = it.seed
    tag = it.qid
    out: list[str] = []
    if s.type == "write_fill":
        if not s.blanks or not s.passage:
            out.append(f"{tag}: write_fill needs a passage and blanks")
        for b in s.blanks or []:
            if b.model not in b.accepted:
                out.append(f"{tag}: blank {b.id}: the model answer must be among the accepted ones")
    else:
        for f in ("model", "modelTr", "rubric", "limit", "phrases", "tips"):
            if not getattr(s, f):
                out.append(f"{tag}: needs `{f}`")
        if s.type == "write_chart" and not s.data:
            out.append(f"{tag}: write_chart needs `data`")
        if s.type == "write_essay" and not (s.prompt and s.questions):
            out.append(f"{tag}: write_essay needs `prompt` and `questions`")
    return out


# --------------------------------------------------------- lesson cards of a question --
_FORM_JUNK = re.compile(r"[\s+~…·.,!?:;‘’“”\"'*-]")
_POS_PREFIX = re.compile(r"^(?:V/A|A/V|V|A|N)(?=[\s+\-(]|[가-힣])")
_KOREAN_ONLY = re.compile(r"[가-힣ㄱ-ㅎㅏ-ㅣ]+")
_LEAD = re.compile(r"^[-(]+")


def _expand(token: str) -> list[str]:
    """`-아/어야겠다` -> [`-아야겠다`, `-어야겠다`]; `N을/를` -> [`N을`, `N를`]; `있다/없다` -> both. The two
    alternatives are as wide as the shorter of them (a pair of syllables shares what follows the
    second one); with three or more, each is a whole piece."""
    parts = token.split("/")
    if len(parts) < 2 or not all(parts):
        return [token]
    if len(parts) > 2:
        return parts
    left, right = parts
    k = min(len(_LEAD.sub("", left, count=1)), len(right))
    return [left + right[k:], left[: len(left) - k] + right]


def _variants(text: str) -> list[str]:
    """Every form of a pattern written with alternatives: `-아/어 보다` -> `-아 보다`, `-어 보다`;
    `V/A + -(으)ㄹ 것 같다` -> a form for V and one for A."""
    text = re.sub(r"\([^)]*\)", "", text)  # the optional vowel `(으)` and `(ㄴ/는)` is not part of the match
    out = [""]
    for tok in re.split(r"(\s+)", text):
        forms = _expand(tok) if "/" in tok and not tok.isspace() else [tok]
        out = [o + f for o in out for f in forms][:16]
    return out


def _core(form: str) -> str:
    """The Korean letters of one form, without the part-of-speech marker, the dashes or the spaces:
    `V + -(으)ㄹ 뿐만 아니라` -> `ㄹ뿐만아니라`. A form that is not all Korean (a Vietnamese label)
    has no core."""
    form = _POS_PREFIX.sub("", form.strip())
    core = _FORM_JUNK.sub("", form)
    return core if _KOREAN_ONLY.fullmatch(core) else ""


def pattern_cores(pattern: str) -> set[str]:
    """Every core a pattern (`A · B` lists several forms) can be recognised by. A core of one letter
    is too short to mean anything and is left out."""
    cores: set[str] = set()
    for part in re.split(r"\s+[·/]\s+|\s*·\s*", pattern):
        for v in _variants(part):
            c = _core(v)
            if len(c) >= 2:
                cores.add(c)
    return cores


def pattern_match(a: Iterable[str], b: Iterable[str]) -> int:
    """How one card's cores meet the other's: 2 = the same pattern, 1 = one is part of the other (a
    close relative: `-(으)면 좋겠다` / `-았/었으면 좋겠다`), 0 = unrelated."""
    best = 0
    bs = list(b)
    for x in a:
        for y in bs:
            if x == y:
                return 2
            if min(len(x), len(y)) >= MIN_GRAM_CORE and (x in y or y in x):
                best = 1
    return best


def headwords(ko: str) -> list[str]:
    """The dictionary forms in a gloss: `나아지다 / 낫다` -> both; a grammar form (`-지 그래요?`) -> none."""
    if re.match(r"^[\s\-~N]*[-~]", ko) or "…" in ko or "?" in ko:
        return []
    return [w.strip() for w in re.split(r"\s*/\s*", ko) if w.strip()]


PRIMER_WORDS = 6  # a primer is short: a learner reads it in a minute, not a page
PRIMER_FORMS = 4


def primer_of(it: Item, max_words: int = PRIMER_WORDS, max_forms: int = PRIMER_FORMS) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """What to tell a learner before they meet a question: its new words (`gloss`) and the forms it
    rests on (`gram`, plus the forms that the gloss lists among the words), each with its short meaning."""
    forms = [(g.k, g.vi) for g in it.seed.gram]
    covered = {c for k, _vi in forms for c in pattern_cores(k)}
    words: list[tuple[str, str]] = []
    for ko, vi in it.seed.gloss:
        if ko[:1] in "-~":
            cores = pattern_cores(ko)
            if not covered.intersection(cores):
                forms.append((ko, vi))
                covered.update(cores)
        else:
            words.append((ko, vi))
    return words[:max_words], forms[:max_forms]


# lessons (by slug prefix) that may offer the hardest tier of the real exam: the courses aimed at TOPIK 4
# (Công sở) and TOPIK 5-6 (Xã hội)
TIER3_COURSES = ("cong-so-", "xa-hoi-")


def check_picks(picks: Iterable[tuple[str, str]], bank: Bank | None = None) -> list[str]:
    """The questions the lessons offer as "Thử sức TOPIK II" (`picks`: (lesson slug, qid)): each has to be
    in the bank, a listening or reading question of the first two tiers (the third tier is for later, except
    in the Công sở and Xã hội courses, which are aimed at 4급 and above and may offer it)."""
    bank = bank or load()
    problems: list[str] = []
    for slug, qid in picks:
        it = bank.items.get(qid)
        top = 3 if slug.startswith(TIER3_COURSES) else 2
        if it is None:
            problems.append(f"{slug}: TOPIK II question {qid} is not in the bank")
        elif not it.is_mcq:
            problems.append(f"{slug}: {qid} is a written question; only listening and reading ones can be offered")
        elif it.tier > top:
            problems.append(f"{slug}: {qid} is of tier {it.tier}; this lesson offers only tier 1 to {top}")
        elif not (it.seed.gloss or it.seed.gram):
            problems.append(f"{slug}: {qid} has neither words nor forms for a primer")
    return problems


@dataclass(frozen=True)
class Lexicon:
    """The grammar and vocabulary cards of the seeded lessons, ready to be matched against."""

    grammar: tuple[tuple[int, int, str, str, frozenset[str]], ...] = ()  # id, lesson_id, pattern, meaning_vi, cores
    vocab: Mapping[str, tuple[tuple[int, int, str], ...]] = field(default_factory=dict)  # hangul -> (id, lesson_id, meaning_vi)
    lessons: Mapping[int, str] = field(default_factory=dict)  # lesson_id -> title


def lexicon_of(
    grammar_rows: Iterable[tuple[int, int, str, str]],
    vocab_rows: Iterable[tuple[int, int, str, str]],
    lessons: Mapping[int, str] | None = None,
) -> Lexicon:
    """`grammar_rows`: (id, lesson_id, pattern, meaning_vi); `vocab_rows`: (id, lesson_id, hangul, meaning_vi)."""
    g = tuple(
        (gid, lid, pat, meaning, frozenset(pattern_cores(pat)))
        for gid, lid, pat, meaning in grammar_rows
        if pattern_cores(pat)
    )
    v: dict[str, list[tuple[int, int, str]]] = defaultdict(list)
    for vid, lid, hangul, meaning in vocab_rows:
        for hw in re.split(r"\s*/\s*", hangul.strip()):  # "아침 / 점심 / 저녁" is three words on one card
            if hw:
                v[hw].append((vid, lid, meaning))
    return Lexicon(grammar=g, vocab={k: tuple(x) for k, x in v.items()}, lessons=dict(lessons or {}))


@dataclass(frozen=True)
class CardRef:
    """A lesson card an exam question rests on."""

    kind: Literal["grammar_point", "vocab_item"]
    id: int
    lesson_id: int
    label: str  # the pattern or the headword
    meaning_vi: str
    exact: bool = True  # a grammar card that is the same pattern (False: a close relative)


@dataclass(frozen=True)
class Needs:
    """What a question rests on, found in the lessons. `grammar`/`words` hold one entry per point the
    question teaches: (what the question says, the lesson cards it is — empty when no lesson has it)."""

    grammar: tuple[tuple[Gram, tuple[CardRef, ...]], ...]
    words: tuple[tuple[str, str, tuple[CardRef, ...]], ...]

    def cards(self) -> list[CardRef]:
        seen: dict[tuple[str, int], CardRef] = {}
        for _g, refs in self.grammar:
            for r in refs:
                seen.setdefault((r.kind, r.id), r)
        for _ko, _vi, refs in self.words:
            for r in refs:
                seen.setdefault((r.kind, r.id), r)
        return list(seen.values())


def needs_of(it: Item, lex: Lexicon) -> Needs:
    """Match the grammar and the words of a question to the cards of the lessons."""
    grammar = []
    gram_items = list(it.seed.gram)
    for b in it.seed.blanks or []:
        gram_items += b.gram
    for g in gram_items:
        cores = pattern_cores(g.k)
        refs = []
        for gid, lid, pat, meaning, lc in lex.grammar:
            m = pattern_match(cores, lc) if cores else 0
            if m:
                refs.append(CardRef("grammar_point", gid, lid, pat, meaning, exact=m == 2))
        refs.sort(key=lambda r: not r.exact)
        grammar.append((g, tuple(refs)))
    words = []
    covered = {c for g, _refs in grammar for c in pattern_cores(g.k)}
    for ko, vi in it.seed.gloss:
        if ko[:1] in "-~":
            # a pattern written among the words: one the question's grammar already has is not shown twice;
            # another one is a grammar point of its own
            cores = pattern_cores(ko)
            if not covered.intersection(cores):
                refs = []
                for gid, lid, pat, meaning, lc in lex.grammar:
                    m = pattern_match(cores, lc) if cores else 0
                    if m:
                        refs.append(CardRef("grammar_point", gid, lid, pat, meaning, exact=m == 2))
                refs.sort(key=lambda r: not r.exact)
                grammar.append((Gram(k=ko, vi=vi), tuple(refs)))
                covered.update(cores)
            continue
        refs = tuple(
            CardRef("vocab_item", vid, lid, hw, meaning)
            for hw in headwords(ko)
            for vid, lid, meaning in lex.vocab.get(hw, ())
        )
        words.append((ko, vi, refs))
    return Needs(grammar=tuple(grammar), words=tuple(words))


@dataclass(frozen=True)
class Fit:
    """How a question stands against what a learner has studied."""

    known: int  # points of the question that are cards the learner has met
    upcoming: int  # points that are cards of a lesson the learner has not reached
    new: int  # points no lesson has: they are taught in the explanation
    status: Literal["ready", "stretch", "later"]


def fit_of(needs: Needs, met: Container[tuple[str, int]]) -> Fit:
    """`ready`: nothing the learner is missing from the lessons; `stretch`: one or two cards of lessons
    not yet reached; `later`: more than that. Points no lesson holds are `new` — they never block a question
    (a newcomer must still be able to start; the explanation teaches them)."""
    known = upcoming = new = 0
    for _g, refs in needs.grammar:
        if not refs:
            new += 1
        elif any((r.kind, r.id) in met for r in refs):
            known += 1
        else:
            upcoming += 1
    for _ko, _vi, refs in needs.words:
        if not refs:
            new += 1
        elif any((r.kind, r.id) in met for r in refs):
            known += 1
        else:
            upcoming += 1
    status: Literal["ready", "stretch", "later"] = "ready" if upcoming == 0 else "stretch" if upcoming <= 2 else "later"
    return Fit(known=known, upcoming=upcoming, new=new, status=status)



# ---------------------------------------------------------------- what was answered --
@dataclass(frozen=True)
class Seen:
    """What the learner's attempts at one question add up to."""

    attempts: int
    last_at: datetime
    last_right: bool  # the last attempt was right (self-checked right counts)
    last_hints: int  # hints used in the last attempt
    ever_unaided: bool  # at some point answered right with no hint
    right_count: int = 0  # attempts that were right

    @property
    def status(self) -> Literal["solid", "aided", "wrong"]:
        if not self.last_right:
            return "wrong"
        return "solid" if self.last_hints == 0 else "aided"


def seen_of(rows: Iterable[tuple[datetime, bool, int]]) -> Seen | None:
    """`rows`: (when, right, hints) of every attempt at a question, any order."""
    ordered = sorted(rows, key=lambda r: r[0])
    if not ordered:
        return None
    last = ordered[-1]
    return Seen(
        attempts=len(ordered),
        last_at=last[0],
        last_right=last[1],
        last_hints=last[2],
        ever_unaided=any(r and h == 0 for _t, r, h in ordered),
        right_count=sum(1 for _t, r, _h in ordered if r),
    )


def due_again(seen: Seen | None, now: datetime) -> bool:
    """A question that was tried is offered again only after its rest: 12 h when wrong, 3 days when it
    needed a hint, 7 days when it was solid. One never tried is always open."""
    if seen is None:
        return True
    wait = {"wrong": REASK_WRONG, "aided": REASK_AIDED, "solid": REASK_SOLID}[seen.status]
    return now - seen.last_at >= wait


def tier_standing(items: Iterable[Item], seen: Mapping[str, Seen]) -> dict[int, tuple[int, int]]:
    """For one type: tier -> (solid questions, questions). A question is solid when its last answer was
    right with no hint."""
    out: dict[int, list[int]] = defaultdict(lambda: [0, 0])
    for it in items:
        row = out[it.tier]
        row[1] += 1
        s = seen.get(it.qid)
        if s is not None and s.status == "solid":
            row[0] += 1
    return {t: (a, b) for t, (a, b) in sorted(out.items())}


def tier_is_solid(solid: int, total: int) -> bool:
    return total > 0 and solid >= math.ceil(SOLID_SHARE * total)


def current_tier(standing: Mapping[int, tuple[int, int]]) -> int | None:
    """The lowest tier of a type that is not solid yet (None when all are)."""
    for tier, (solid, total) in standing.items():
        if not tier_is_solid(solid, total):
            return tier
    return None


# ------------------------------------------------------------------- the selection --
@dataclass(frozen=True)
class Scope:
    """What the learner asked to practise: a question type, a family (cụm), a section of a paper,
    explicit questions — or nothing (the app chooses)."""

    type: str | None = None
    family: str | None = None
    sec: str | None = None
    exam: str | None = None
    qids: tuple[str, ...] = ()


def in_scope(it: Item, scope: Scope, bank: Bank) -> bool:
    if scope.qids:
        return it.qid in scope.qids
    if scope.type and it.type != scope.type:
        return False
    if scope.family and bank.types[it.type].family != scope.family:
        return False
    if scope.sec and it.sec != scope.sec:
        return False
    if scope.exam and it.exam != scope.exam:
        return False
    return True


STAGE_FRACTIONS = (0.15, 0.5)  # share of the lessons' grammar met: below the first = starter, below the second = building


def stage_of(known_grammar: int, total_grammar: int) -> Literal["starter", "building", "solid"]:
    share = known_grammar / total_grammar if total_grammar else 0.0
    return "starter" if share < STAGE_FRACTIONS[0] else "building" if share < STAGE_FRACTIONS[1] else "solid"


STAGE_TIER_CAP = {"starter": 2, "building": 2, "solid": 3}  # the highest tier the app offers unasked


@dataclass(frozen=True)
class Candidate:
    it: Item
    seen: Seen | None
    fit: Fit


def _bucket(c: Candidate, cur_tier: int | None) -> int:
    """0 a question to try again (wrong or needed a hint), 1 new at the tier being made solid and ready,
    2 new at that tier but needing a lesson card the learner has not reached, 3 new at a higher tier,
    4 a solid one due for a check."""
    s = c.seen
    if s is not None:
        return 4 if s.status == "solid" else 0
    if cur_tier is None or c.it.tier <= cur_tier:
        return 1 if c.fit.status == "ready" else 2
    return 3


def pick_questions(
    bank: Bank,
    pool: Sequence[Candidate],
    standing_of: Mapping[str, Mapping[int, tuple[int, int]]],
    *,
    size: int,
    now: datetime,
    tier_cap: int | None = None,
) -> list[Item]:
    """Choose up to `size` questions from the candidates (all in one scope): those due to be tried
    again first, then new ones at the lowest tier of each type not yet solid, easiest first, ready
    before stretch. Questions sharing a passage come together (the whole bundle or none)."""
    open_ = [c for c in pool if due_again(c.seen, now) and (tier_cap is None or c.it.tier <= tier_cap or c.seen is not None)]
    cur = {code: current_tier(standing_of.get(code, {})) for code in {c.it.type for c in open_}}
    ranked = sorted(open_, key=lambda c: (_bucket(c, cur.get(c.it.type)), c.it.tier, c.it.type, c.it.n))
    by_id = {c.it.qid: c for c in open_}
    chosen: list[Item] = []
    taken: set[str] = set()
    cap = size if not any(c.it.sec == "W" for c in ranked[:size]) else min(size, WRITING_SET_SIZE)
    for c in ranked:
        if len(chosen) >= cap:
            break
        if c.it.qid in taken:
            continue
        group = [by_id[q].it for q in c.it.bundle if q in by_id and q not in taken]
        if not group:
            continue
        if chosen and len(chosen) + len(group) > cap + 1:
            continue
        for g in group:
            chosen.append(g)
            taken.add(g.qid)
    return sorted(chosen, key=lambda i: (i.exam, SECTIONS.index(i.sec), i.n))


@dataclass(frozen=True)
class TypeStat:
    code: str
    total: int
    tried: int
    solid: int
    wrong_open: int  # tried, last answer wrong or aided
    retry_due: int  # of those, the ones whose rest is over
    open: int  # offered right now (new, or rested long enough)
    ready_open: int  # of those, the ready ones
    right: int  # attempts that were right ...
    attempts: int  # ... of all attempts (the accuracy shown to the learner)
    cur_tier: int | None
    standing: Mapping[int, tuple[int, int]]


def type_stats(code: str, cands: Sequence[Candidate], now: datetime, tier_cap: int | None = None) -> TypeStat:
    """`tier_cap`: questions above this tier that were never tried do not count as open (the app does not
    offer them unasked)."""
    seen = {c.it.qid: c.seen for c in cands if c.seen is not None}
    standing = tier_standing([c.it for c in cands], seen)
    open_ = [
        c for c in cands if due_again(c.seen, now) and (tier_cap is None or c.it.tier <= tier_cap or c.seen is not None)
    ]
    return TypeStat(
        code=code,
        total=len(cands),
        tried=len(seen),
        solid=sum(1 for s in seen.values() if s.status == "solid"),
        wrong_open=sum(1 for c in cands if c.seen is not None and c.seen.status != "solid"),
        retry_due=sum(1 for c in cands if c.seen is not None and c.seen.status != "solid" and due_again(c.seen, now)),
        open=len(open_),
        ready_open=sum(1 for c in open_ if c.fit.status == "ready"),
        right=sum(s.right_count for s in seen.values()),
        attempts=sum(s.attempts for s in seen.values()),
        cur_tier=current_tier(standing),
        standing=standing,
    )


def rank_types(bank: Bank, stats: Mapping[str, TypeStat], stage: str) -> list[str]:
    """The types to practise when the learner has not chosen one, best first: a type with questions to
    try again comes first; otherwise the type whose next tier is the lowest — every type's easy questions
    are made solid before the middle ones are offered — in the order of the families (listening pictures
    and grammar first). A starter does not begin with the long written answers."""
    keyed: list[tuple[tuple, str]] = []
    for code, st in stats.items():
        if st.open == 0:
            continue
        written = bank.types[code].sec == "W"
        keyed.append(
            (
                (
                    0 if st.retry_due else 1,
                    1 if (written and stage == "starter") else 0,
                    st.cur_tier if st.cur_tier is not None else 4,
                    bank.family_of(code).order,
                    -st.ready_open,
                    code,
                ),
                code,
            )
        )
    return [code for _key, code in sorted(keyed)]


def choose_type_today(bank: Bank, stats: Mapping[str, TypeStat], stage: str) -> str | None:
    ranked = rank_types(bank, stats, stage)
    return ranked[0] if ranked else None


# ---------------------------------------------------------------- answering --
def grade_choice(it: Item, choice: int | None) -> bool:
    return choice is not None and choice == it.seed.ans


def _squash(text: str) -> str:
    """For comparing a written answer with the accepted ones: no spaces, no closing punctuation."""
    return re.sub(r"[\s.,!?。]+", "", text.strip().strip("‘’“”\"'"))


def grade_blanks(it: Item, answers: Mapping[str, str]) -> list[tuple[Blank, str, bool]]:
    """Each blank, the learner's text and whether it is one of the accepted answers."""
    out = []
    for b in it.seed.blanks or []:
        text = answers.get(b.id, "")
        ok = bool(_squash(text)) and _squash(text) in {_squash(a) for a in b.accepted}
        out.append((b, text, ok))
    return out


def char_count(text: str) -> int:
    """TOPIK counts every syllable and every space (a line break is not a character)."""
    return len(text.replace("\r", "").replace("\n", ""))


_ENDING_FORMAL = re.compile(r"(?:습니다|ㅂ니다|입니다|니다|합니다|[요])(?=[.!?]?\s*$)", re.M)
_NUMBER = re.compile(r"\d[\d.,]*")


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", text) if s.strip()]


@dataclass(frozen=True)
class Check:
    label: str
    ok: bool
    note: str


def check_writing(it: Item, text: str) -> list[Check]:
    """What a program can say about a written answer without judging its Korean: length, style and
    whether it carries the facts of the chart. The learner then compares with the model and the rubric."""
    s = it.seed
    out: list[Check] = []
    n = char_count(text)
    lo, hi = s.limit or (0, 10_000)
    out.append(
        Check(
            "Độ dài",
            lo <= n <= hi,
            f"{n} chữ (yêu cầu {lo}–{hi}, tính cả khoảng trắng)." if s.limit else f"{n} chữ.",
        )
    )
    sents = _sentences(text)
    polite = [x for x in sents if re.search(r"(?:습니다|ㅂ니다|입니다|요)[.!?]?$", x)]
    out.append(
        Check(
            "Văn phong",
            not polite,
            "Dùng văn viết -ㄴ/는다, -이다." if not polite else f"Có {len(polite)} câu kết thúc bằng -ㅂ/습니다 hoặc -요 — đổi sang -ㄴ/는다.",
        )
    )
    if s.type == "write_chart" and s.data:
        wanted = []
        for line in s.data:
            for tok in _NUMBER.findall(line):
                tok = tok.rstrip(".,")
                if tok not in wanted:
                    wanted.append(tok)
        compact = text.replace(" ", "")
        missing = [t for t in wanted if t not in compact]
        out.append(
            Check(
                "Số liệu",
                not missing,
                "Đã nêu các số liệu của biểu đồ." if not missing else "Chưa thấy: " + ", ".join(missing[:8]),
            )
        )
    if s.type == "write_essay" and s.prompt:
        copied = _longest_common_run(text, s.prompt)
        out.append(
            Check(
                "Không chép lại đề",
                copied < 25,
                "Không chép lại đề." if copied < 25 else f"Có đoạn dài {copied} chữ giống đề — hãy diễn đạt lại.",
            )
        )
    return out


def _longest_common_run(a: str, b: str) -> int:
    a, b = a.replace(" ", ""), b.replace(" ", "")
    best = 0
    prev = [0] * (len(b) + 1)
    for x in a:
        cur = [0] * (len(b) + 1)
        for j, y in enumerate(b, 1):
            if x == y:
                cur[j] = prev[j - 1] + 1
                best = max(best, cur[j])
        prev = cur
    return best


# --------------------------------------------------------------------- the hints --
def hint(it: Item, level: int) -> dict:
    """What hint `level` (1..3) says about a question. The ladder: what to look for, then the
    question in Vietnamese, then one answer to cross out. For the writing questions: what to look
    for, the patterns to use, the first syllables of the model / the outline."""
    s = it.seed
    if not 1 <= level <= HINT_LEVELS:
        raise ValueError("hint level is 1..3")
    if it.sec == "W":
        if level == 1:
            return {"level": 1, "kind": "focus", "text": s.focus}
        if s.type == "write_fill":
            if level == 2:
                return {
                    "level": 2,
                    "kind": "patterns",
                    "items": [{"id": b.id, "gram": [g.model_dump() for g in b.gram]} for b in s.blanks or []],
                }
            return {
                "level": 3,
                "kind": "start",
                "items": [{"id": b.id, "text": b.model[:2] + "…"} for b in s.blanks or []],
            }
        if level == 2:
            return {"level": 2, "kind": "patterns", "items": [{"id": "", "gram": [g.model_dump() for g in s.phrases or []]}]}
        return {"level": 3, "kind": "outline", "rubric": [r.model_dump() for r in s.rubric or []]}
    if level == 1:
        return {"level": 1, "kind": "focus", "text": s.focus}
    if level == 2:
        return {
            "level": 2,
            "kind": "translate",
            "options_vi": list(s.ov or []),
            "gloss": [[ko, vi] for ko, vi in s.gloss],
        }
    return {"level": 3, "kind": "eliminate", "option": s.elim}


# -------------------------------------------------------------------- the summary --
@dataclass(frozen=True)
class Outcome:
    qid: str
    right: bool
    hints: int
    pending: bool = False  # a written answer not yet self-checked


def result_of(o: Outcome) -> Literal["solid", "aided", "wrong", "pending"]:
    if o.pending:
        return "pending"
    if not o.right:
        return "wrong"
    return "solid" if o.hints == 0 else "aided"


def next_step(counts: Mapping[str, int], cur_tier_done: bool, upcoming: Sequence[str]) -> str:
    """One sentence on what to do next, from how the sitting went."""
    if counts.get("wrong", 0):
        return (
            f"Xem lại {counts['wrong']} câu sai: hệ thống sẽ đưa chúng quay lại sau 12 giờ để bạn làm lại "
            "bằng chính cách hiểu mới."
        )
    if counts.get("aided", 0):
        return "Bạn làm đúng nhưng còn dùng gợi ý. Sau 3 ngày câu sẽ quay lại — lần đó hãy thử làm không gợi ý."
    if upcoming:
        return "Bạn làm chắc rồi. Học tiếp: " + ", ".join(upcoming[:3]) + " để mở thêm các câu khó hơn."
    if cur_tier_done:
        return "Bậc này đã vững. Chuyển sang bậc tiếp theo của dạng này hoặc sang dạng khác."
    return "Tiếp tục một bộ câu nữa để bậc này thật vững."


def main(argv: Sequence[str] | None = None) -> int:
    bank = load()
    problems = check(bank)
    problems += check_picks(((r.seed.slug, p.qid) for r in seed.load_all().lessons for p in r.seed.topik2), bank)
    by_sec = Counter((i.exam, i.sec) for i in bank.items.values())
    for (exam, sec), n in sorted(by_sec.items()):
        print(f"{exam} {SEC_NAME_VI[sec]}: {n} câu")
    print(f"{len(bank.types)} dạng, {len(bank.families)} cụm; dạng chưa dùng:",
          sorted(set(bank.types) - {i.type for i in bank.items.values()}) or "không")
    for p in problems:
        print("PROBLEM", p)
    print("OK" if not problems else f"{len(problems)} problems")
    return 1 if problems else 0


if __name__ == "__main__":  # python3 -m app.services.real_exam
    raise SystemExit(main())

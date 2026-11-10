"""Short readings and dialogues for the daily "đọc & nghe" sitting.

`app/seed/passages/<lesson-slug>.json` holds, for one lesson, a few texts written for it: a short
dialogue (two voices) and a short reading (one voice). Each text only uses what the learner has
met by that lesson — the vocabulary and grammar of the lessons up to it — and says which cards it
is built on, so the daily pick (app.services.daily_reading) can offer the texts that match what
THIS learner has studied and is about to forget. Words outside that stock are glossed under the
text.

This module is pure: it loads the files and checks them. Reading them against the lessons (does
every grammar card exist, is every key word one the learner has met, is each pattern really in the
text) is `check`, run by the tests and by `python3 -m app.services.lesson_seed --check`."""
from __future__ import annotations

import json
import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, ValidationError, field_validator

from app.core.config import settings
from app.services import lesson_seed as seed
from app.services import text_audio

PASSAGE_DIR = seed.SEED_DIR / "passages"
KINDS = ("dialogue", "reading")
# Who speaks a line, and the Chirp voice that reads it. A reading has one narrator.
VOICE_OF = {"F": "ko-female-1", "M": "ko-male-1", "N": "ko-female-1"}
_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_SLUG = re.compile(r"^(?P<topic>[a-z]+(?:-[a-z]+)*)-(?P<n>\d\d)-")


# ------------------------------------------------------------------ the file --
class Line(seed._M):
    who: Literal["F", "M", "N"]
    ko: str = Field(min_length=1, max_length=300)
    vi: str = Field(min_length=1, max_length=500)


class Use(seed._M):
    pattern: str  # a grammar card of this lesson or an earlier one (its `pattern`, as in the lesson file)
    regex: str  # what that pattern looks like in this text (checked: it must match)


class Keyword(seed._M):
    word: str  # the headword exactly as the lesson's vocab writes it
    seen: str  # the piece of the text that shows it (a verb is conjugated there): checked to be in the text


class Gloss(seed._M):
    ko: str = Field(min_length=1, max_length=40)  # as shown under the text
    vi: str = Field(min_length=1, max_length=120)
    seen: str | None = None  # the piece of the text that shows it, when it differs from `ko`


class Question(seed._M):
    q_vi: str = Field(min_length=1, max_length=300)
    options: list[str] = Field(min_length=3, max_length=4)
    answer: int
    explain_vi: str = Field(min_length=1, max_length=500)


class PassageSeed(seed._M):
    id: str
    kind: Literal["dialogue", "reading"]
    title_ko: str = Field(min_length=1, max_length=80)
    title_vi: str = Field(min_length=1, max_length=120)
    scene_vi: str | None = None  # a dialogue: where and who
    speakers: dict[str, str] | None = None  # a dialogue: {"F": name, "M": name}
    lines: list[Line]
    uses: list[Use]
    keywords: list[Keyword]  # words of the lesson (or an earlier one) this text rests on
    glossary: list[Gloss] = []
    questions: list[Question]

    @field_validator("id")
    @classmethod
    def _id_shape(cls, v: str) -> str:
        if not _ID.match(v):
            raise ValueError(f"id {v!r}: lowercase letters, digits and hyphens only")
        return v


class PassageFile(seed._M):
    lesson: str
    items: list[PassageSeed]


# ------------------------------------------------------------------- loaded --
@dataclass(frozen=True)
class Passage:
    id: str
    lesson: str  # slug
    kind: str
    title_ko: str
    title_vi: str
    scene_vi: str | None
    speakers: dict[str, str]
    lines: tuple[Line, ...]
    uses: tuple[Use, ...]
    keywords: tuple[Keyword, ...]
    glossary: tuple[Gloss, ...]
    questions: tuple[Question, ...]

    @property
    def text_ko(self) -> str:
        """The whole text as one string (what a reading is voiced from)."""
        return " ".join(line.ko.strip() for line in self.lines)


def load(directory: Path = PASSAGE_DIR) -> tuple[list[Passage], list[str]]:
    """Every passage in the folder and the problems found in the files (a bad file is skipped)."""
    out: list[Passage] = []
    problems: list[str] = []
    if not directory.is_dir():
        return out, problems
    seen: dict[str, str] = {}
    for path in sorted(directory.glob("*.json")):
        try:
            doc = PassageFile.model_validate(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, ValueError, ValidationError) as exc:
            problems.append(f"{path.name}: {exc}")
            continue
        if path.stem != doc.lesson:
            problems.append(f"{path.name}: the file is named for {path.stem!r} but says lesson {doc.lesson!r}")
        for it in doc.items:
            if it.id in seen:
                problems.append(f"{path.name}: id {it.id} is also in {seen[it.id]}")
                continue
            seen[it.id] = path.name
            out.append(
                Passage(
                    id=it.id,
                    lesson=doc.lesson,
                    kind=it.kind,
                    title_ko=it.title_ko,
                    title_vi=it.title_vi,
                    scene_vi=it.scene_vi,
                    speakers=dict(it.speakers or {}),
                    lines=tuple(it.lines),
                    uses=tuple(it.uses),
                    keywords=tuple(it.keywords),
                    glossary=tuple(it.glossary),
                    questions=tuple(it.questions),
                )
            )
    return out, problems


@lru_cache(maxsize=1)
def all_passages() -> tuple[Passage, ...]:
    return tuple(load()[0])


def by_id() -> dict[str, Passage]:
    return {p.id: p for p in all_passages()}


def _squash(text: str) -> str:
    return re.sub(r"\s+", "", text)


def _shows(piece: str, text: str) -> bool:
    return bool(piece.strip()) and _squash(piece) in _squash(text)


# ------------------------------------------------------------------- checks --
@dataclass(frozen=True)
class LessonInfo:
    slug: str
    sort_order: int
    patterns: frozenset[str]
    vocab: frozenset[str]
    # the lesson it was cut out of (lesson_seed `split_from`), or its own slug: the parts of one
    # Nền tảng lesson share that lesson's texts (they were written for the whole lesson)
    group: str = ""


def _own(infos: Mapping[str, LessonInfo], slug: str) -> tuple[frozenset[str], frozenset[str]]:
    """(patterns, words) a text of `slug` counts as its own: its lesson's, and for a part of a split
    lesson those of the earlier parts too."""
    me = infos[slug]
    group = me.group or slug
    mates = [i for i in infos.values() if (i.group or i.slug) == group and i.sort_order <= me.sort_order]
    return frozenset().union(*(i.patterns for i in mates)), frozenset().union(*(i.vocab for i in mates))


# the topics a learner of a topic has finished: every later topic assumes the first (sinh-hoat); the
# Công sở course (topic 4) also assumes Quan hệ, whose grammar its texts use. The Nhập cảnh course does not.
_DEFAULT_ASSUMED = frozenset({"sinh-hoat"})
_ASSUMED_TOPICS = {
    "cong-so": frozenset({"sinh-hoat", "quan-he"}),
    # the Viết 54 course (after topic 4) writes its texts with the words and grammar of topics 1-4
    "viet-nghi-luan": frozenset({"sinh-hoat", "quan-he", "cong-so"}),
    # the Xã hội course (topic 5) is the last one: it assumes the topics before it
    "xa-hoi": frozenset({"sinh-hoat", "quan-he", "cong-so", "viet-nghi-luan"}),
}


def allowed_slugs(slug: str, slugs: Iterable[str]) -> set[str]:
    """The lessons a text for `slug` may draw on: its own topic up to it, and — for the later
    topics — all of the first one (sinh-hoat), plus Quan hệ for the Công sở course. The Nhập cảnh
    course does not assume topic 2."""
    m = _SLUG.match(slug)
    if m is None:
        return {slug}
    topic, number = m.group("topic"), int(m.group("n"))
    allowed: set[str] = set()
    for other in slugs:
        om = _SLUG.match(other)
        if om is None:
            continue
        if om.group("topic") == topic and int(om.group("n")) <= number:
            allowed.add(other)
        elif om.group("topic") in _ASSUMED_TOPICS.get(topic, _DEFAULT_ASSUMED) and topic != om.group("topic"):
            allowed.add(other)
    return allowed


def lesson_infos(lessons: Iterable) -> dict[str, LessonInfo]:
    """From the resolved lessons of `lesson_seed.load_all()`."""
    return {
        r.seed.slug: LessonInfo(
            r.seed.slug,
            r.seed.sort_order,
            frozenset(g.pattern for g in r.seed.grammar),
            frozenset(v.hangul for v in r.seed.vocab),
            r.seed.split_from or r.seed.slug,
        )
        for r in lessons
    }


def coverage(passages: Sequence[Passage], infos: Mapping[str, LessonInfo]) -> list[str]:
    """Every lesson that teaches words and grammar has at least one dialogue and one reading (a
    review lesson, with no cards of its own, has none)."""
    have: dict[str, set[str]] = {}
    for p in passages:
        info = infos.get(p.lesson)
        have.setdefault(info.group if info and info.group else p.lesson, set()).add(p.kind)
    problems: list[str] = []
    seen: set[str] = set()
    for slug, info in sorted(infos.items(), key=lambda kv: kv[1].sort_order):
        if not info.patterns or not info.vocab:
            continue
        group = info.group or slug
        if group in seen:
            continue  # the parts of a split lesson are covered together
        seen.add(group)
        for kind in KINDS:
            if kind not in have.get(group, set()):
                problems.append(f"{group}: no {kind} written for this lesson")
    return problems


def check(passages: Sequence[Passage], infos: Mapping[str, LessonInfo]) -> list[str]:
    """Problems that need the lessons. Empty when every text is sound."""
    problems: list[str] = []
    for p in passages:
        label = p.id
        info = infos.get(p.lesson)
        if info is None:
            problems.append(f"{label}: no lesson {p.lesson!r}")
            continue
        allowed = allowed_slugs(p.lesson, infos.keys())
        known_patterns = set().union(*(infos[s].patterns for s in allowed))
        known_vocab = set().union(*(infos[s].vocab for s in allowed))
        text = p.text_ko
        flat = _squash(text)

        # -- lines
        who = [line.who for line in p.lines]
        if p.kind == "dialogue":
            if set(p.speakers) != {"F", "M"} or not all(p.speakers.values()):
                problems.append(f"{label}: a dialogue names its two speakers F and M")
            if not p.scene_vi:
                problems.append(f"{label}: a dialogue needs scene_vi (where, and who is talking)")
            if not 6 <= len(p.lines) <= 10:
                problems.append(f"{label}: a dialogue has 6-10 lines, this has {len(p.lines)}")
            if set(who) - {"F", "M"} or who.count("F") < 2 or who.count("M") < 2:
                problems.append(f"{label}: both speakers talk at least twice, and only F and M speak")
        else:
            if p.speakers or p.scene_vi:
                problems.append(f"{label}: a reading has no speakers and no scene")
            if set(who) != {"N"}:
                problems.append(f"{label}: every line of a reading is narrated (N)")
            if not 4 <= len(p.lines) <= 9:
                problems.append(f"{label}: a reading has 4-9 lines, this has {len(p.lines)}")
            if len(text) > settings.TEXT_AUDIO_MAX_CHARS:
                problems.append(f"{label}: {len(text)} characters read aloud at once, over {settings.TEXT_AUDIO_MAX_CHARS}")
        for n, line in enumerate(p.lines, 1):
            try:
                text_audio.check_text(line.ko)
            except text_audio.TextNotSpeakable as exc:
                problems.append(f"{label} line {n}: cannot be voiced ({exc})")
        if p.kind == "reading":
            try:
                text_audio.check_text(text)
            except text_audio.TextNotSpeakable as exc:
                problems.append(f"{label}: the whole reading cannot be voiced ({exc})")

        # -- grammar the text is built on
        if not 2 <= len(p.uses) <= 5:
            problems.append(f"{label}: {len(p.uses)} grammar uses (2-5 wanted)")
        own, own_words = _own(infos, p.lesson)
        if not any(u.pattern in own for u in p.uses):
            problems.append(f"{label}: no grammar card of its own lesson {p.lesson} is used")
        seen_patterns: set[str] = set()
        for u in p.uses:
            if u.pattern in seen_patterns:
                problems.append(f"{label}: {u.pattern!r} is listed twice")
            seen_patterns.add(u.pattern)
            if u.pattern not in known_patterns:
                problems.append(f"{label}: {u.pattern!r} is not a card of {p.lesson} or the lessons before it")
                continue
            try:
                rx = re.compile(u.regex)
            except re.error as exc:
                problems.append(f"{label}: {u.pattern!r} regex does not compile ({exc})")
                continue
            if not rx.search(text):
                problems.append(f"{label}: {u.pattern!r} is not in the text (regex {u.regex!r})")

        # -- the words it rests on
        words = [k.word for k in p.keywords]
        if not 3 <= len(words) <= 8:
            problems.append(f"{label}: {len(words)} key words (3-8 wanted)")
        if len(set(words)) != len(words):
            problems.append(f"{label}: a key word is listed twice")
        if not any(w in own_words for w in words):
            problems.append(f"{label}: no key word from its own lesson")
        for k in p.keywords:
            if k.word not in known_vocab:
                problems.append(f"{label}: key word {k.word!r} is not in {p.lesson} or the lessons before it")
            elif not _shows(k.seen, text):
                problems.append(f"{label}: key word {k.word!r}: {k.seen!r} is not in the text")

        # -- words glossed under the text
        if len(p.glossary) > 6:
            problems.append(f"{label}: {len(p.glossary)} glossed words (6 at most)")
        for g in p.glossary:
            if not _shows(g.seen or g.ko, text):
                problems.append(f"{label}: glossed word {g.ko!r} is not in the text")
            if g.ko in words or g.ko in known_vocab:
                problems.append(f"{label}: {g.ko!r} is already a word of the lessons, no gloss needed")

        # -- comprehension questions
        if not 2 <= len(p.questions) <= 3:
            problems.append(f"{label}: {len(p.questions)} questions (2-3 wanted)")
        for n, q in enumerate(p.questions, 1):
            if len(set(q.options)) != len(q.options):
                problems.append(f"{label} question {n}: two options are the same")
            if not 0 <= q.answer < len(q.options):
                problems.append(f"{label} question {n}: the answer is not one of the options")
        if not re.search(r"[가-힣]", p.title_ko):
            problems.append(f"{label}: title_ko has no Korean")
        if not flat:
            problems.append(f"{label}: no text")
    return problems

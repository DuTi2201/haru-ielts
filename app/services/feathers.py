"""Lông vũ: every lesson cut into small parts of about five minutes, each one a feather, and the
feathers gathered into the five chapters of Hành trình Thiên Nga.

A feather is only a way of SHOWING a lesson: it is cut from the lesson's own words, cards and
questions, in their order, and adds or drops nothing. It is earned by the records that already say a
lesson was studied (app.services.progress): a word or card marked once, a question answered. So a
lesson whose feathers are all earned is a studied lesson. (The alphabet lesson has five parts that
leave no other record: those are kept in `lesson_part_done`.)

  vocab      up to 12 words, in the lesson's order
  grammar    2 patterns
  practice   one skill (Nghe, Đọc, Tạo câu, Viết & nói); more than 15 questions is cut in two or
             more, never inside an exercise
  part       a part of the alphabet lesson; its end check is one feather

Main lessons belong to a chapter, by level: I = Sơ cấp (the alphabet and Nền tảng 1–5), II = Sinh
hoạt, III = Quan hệ and Công sở (the rest of Trung cấp), IV = Cao cấp. Finishing a chapter changes
the swan: the blindfold falls (I), it leaves the tower (II), it takes up the sword (III), it is
crowned (IV) and chapter V is where it lives after. Halfway through III, at the end of Quan hệ, is a
station (the far shore comes in sight).

Support lessons (a topic named "Bổ trợ · …") are not in a chapter: each topic is a constellation,
each lesson a star, and every feather of them a starlight feather that makes the swan sparkle
(three steps, fixed counts, so adding lessons never lowers one). A topic finished gives its relic.
What was earned is kept (journey.relics, journey.sparkle) and never taken back."""
from __future__ import annotations

import time
import uuid
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import GrammarPoint, ItemState, Lesson, LessonExerciseResult, LessonPartDone, LessonTopic, Topic, VocabItem
from app.services.lesson_seed import question_ids

ItemKey = tuple[str, int]
Kind = Literal["vocab", "grammar", "practice", "part"]

WORDS_PER_FEATHER = 12
PATTERNS_PER_FEATHER = 2
QUESTIONS_PER_FEATHER = 15
SKILL_GROUPS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Nghe", ("listening",)),
    ("Đọc", ("reading",)),
    ("Tạo câu", ("build",)),
    ("Viết & nói", ("writing", "speaking")),
)
SPARKLE_AT = (10, 60, 110)  # starlight feathers for sparkle 1, 2, 3


@dataclass(frozen=True)
class Feather:
    id: str
    kind: Kind
    label: str
    items: tuple[ItemKey, ...] = ()
    questions: tuple[str, ...] = ()
    part: str | None = None
    skill: str | None = None  # practice: the skill tab it is in


def _span(label: str, start: int, end: int) -> str:
    return f"{label} {start}" if start == end else f"{label} {start}–{end}"


def partition(
    vocab_ids: Sequence[int],
    grammar_ids: Sequence[int],
    practice: Mapping[str, Any] | None,
) -> list[Feather]:
    """The feathers of one lesson, in the order the lesson shows them."""
    practice = practice or {}
    out: list[Feather] = []
    if practice.get("kind") == "hangul":
        for n, p in enumerate((practice.get("hangul") or {}).get("parts") or [], start=1):
            out.append(Feather(id=f"h{n}", kind="part", label=str(p.get("title_vi") or f"Phần {n}"), part=str(p["id"])))
        qs = tuple(q for ex in practice.get("items") or [] for q in question_ids(ex))
        if qs:
            out.append(Feather(id="check", kind="practice", label="Kiểm tra cuối bài", questions=qs))
        return out

    for n, i in enumerate(range(0, len(vocab_ids), WORDS_PER_FEATHER), start=1):
        chunk = vocab_ids[i : i + WORDS_PER_FEATHER]
        out.append(
            Feather(id=f"v{n}", kind="vocab", label=_span("Từ", i + 1, i + len(chunk)), items=tuple(("vocab_item", v) for v in chunk))
        )
    for n, i in enumerate(range(0, len(grammar_ids), PATTERNS_PER_FEATHER), start=1):
        chunk = grammar_ids[i : i + PATTERNS_PER_FEATHER]
        out.append(
            Feather(id=f"g{n}", kind="grammar", label=_span("Mẫu", i + 1, i + len(chunk)), items=tuple(("grammar_point", g) for g in chunk))
        )
    items = practice.get("items") or []
    for name, skills in SKILL_GROUPS:
        exercises = [ex for ex in items if ex.get("skill") in skills]
        chunks: list[list[str]] = []
        for ex in exercises:
            qs = question_ids(ex)
            if chunks and len(chunks[-1]) + len(qs) <= QUESTIONS_PER_FEATHER:
                chunks[-1].extend(qs)
            else:
                chunks.append(list(qs))
        chunks = [c for c in chunks if c]
        for n, c in enumerate(chunks, start=1):
            label = name if len(chunks) == 1 else f"{name} {n}"
            out.append(Feather(id=f"p-{skills[0]}-{n}", kind="practice", label=label, questions=tuple(c), skill=skills[0]))
    # a question outside the four groups (an unknown skill) is never lost: it gets a feather of its own
    known = {q for f in out for q in f.questions}
    rest = tuple(q for ex in items for q in question_ids(ex) if q not in known)
    if rest:
        out.append(Feather(id="p-other-1", kind="practice", label="Luyện thêm", questions=rest))
    return out


def earned(f: Feather, met: set[ItemKey], answered: set[str], parts: set[str]) -> bool:
    if f.kind == "part":
        return f.part in parts
    return all(k in met for k in f.items) and all(q in answered for q in f.questions)


# ------------------------------------------------------------------ chapters --
@dataclass(frozen=True)
class Chapter:
    n: int
    name: str
    level: str  # what finishing it means, in the learner's words
    becomes: str  # what the swan does when it is finished


CHAPTERS: dict[int, Chapter] = {
    1: Chapter(1, "Bóng tối trong tháp gai", "Sơ cấp", "Dải bịt mắt rơi xuống"),
    2: Chapter(2, "Vết nứt ánh sáng", "Trung cấp · phần 1", "Rời tháp gai"),
    3: Chapter(3, "Vượt hồ đêm", "Trung cấp · phần 2", "Cầm lấy thanh kiếm"),
    4: Chapter(4, "Bình minh trên vòm nhọn", "Cao cấp", "Đội vương miện"),
    5: Chapter(5, "Bạch Thiên Nga", "Tự do", ""),
}
# (slug prefix, chapter), the first that matches; support topics are decided before this
_CHAPTER_RULES: tuple[tuple[str, int], ...] = (
    ("hangul-", 1),
    ("sinh-hoat-00-", 1),
    # Buổi sáng and Việc nhà sit between the Nền tảng parts (the free Sơ cấp block): chapter I
    ("sinh-hoat-01-", 1),
    ("sinh-hoat-02-", 1),
    ("sinh-hoat-", 2),
    ("quan-he-", 3),
    ("cong-so-", 3),
    ("xa-hoi-", 4),
)
STATION_AFTER = "quan-he-"  # chapter III's station: every Quan hệ lesson done

# support topics: (slug prefix, code, constellation, relic)
_SUPPORT: tuple[tuple[str, str, str, str | None], ...] = (
    ("nhap-canh-", "compass", "Chòm La Bàn", "La bàn ánh sao"),
    ("viet-nghi-luan-", "quill", "Chòm Bút Lông", "Bút lông thiên nga"),
    ("xa-hoi-22-", "mirror", "Chòm Gương Trăng", "Gương trăng"),
)


def is_support(topic: str | None) -> bool:
    return (topic or "").strip().lower().startswith("bổ trợ")


def chapter_of(slug: str | None, level: int) -> int:
    for prefix, n in _CHAPTER_RULES:
        if (slug or "").startswith(prefix):
            return n
    # a lesson of a new main topic: by its level
    return 1 if level <= 2 else 3 if level <= 4 else 4


def support_of(slug: str | None, topic: str) -> tuple[str, str, str | None]:
    """(code, constellation name, relic name) of a support lesson's topic."""
    for prefix, code, name, relic in _SUPPORT:
        if (slug or "").startswith(prefix):
            return code, name, relic
    label = topic.split("·", 1)[-1].strip() or topic
    return f"topic:{topic}", f"Chòm {label}", None


# ------------------------------------------------------------------ the course --
@dataclass(frozen=True)
class CourseLesson:
    id: int
    slug: str | None
    sort_order: int
    title: str
    topic: str
    chapter: int | None  # None: a support lesson
    support: str | None  # its topic's code
    feathers: tuple[Feather, ...]


_cache: tuple[float, list[CourseLesson]] | None = None
TTL = 300.0


def reset_cache() -> None:
    global _cache
    _cache = None


async def course(db: AsyncSession) -> list[CourseLesson]:
    """Every lesson with its feathers, in course order (cached a few minutes: lessons change only
    when the seed is synced, at start)."""
    global _cache
    now = time.monotonic()
    if _cache is not None and now - _cache[0] < TTL:
        return _cache[1]
    rows = (await db.execute(select(Lesson.id, Lesson.slug, Lesson.sort_order, Lesson.title, Lesson.level, Lesson.practice))).all()
    topics: dict[int, str] = {}
    for lid, name in (await db.execute(select(LessonTopic.lesson_id, Topic.name).join(Topic, Topic.id == LessonTopic.topic_id))).all():
        topics.setdefault(lid, name)
    vocab: dict[int, list[int]] = defaultdict(list)
    for lid, vid in (await db.execute(select(VocabItem.lesson_id, VocabItem.id).order_by(VocabItem.id))).all():
        if lid is not None:
            vocab[lid].append(vid)
    grammar: dict[int, list[int]] = defaultdict(list)
    for lid, gid in (await db.execute(select(GrammarPoint.lesson_id, GrammarPoint.id).order_by(GrammarPoint.id))).all():
        if lid is not None:
            grammar[lid].append(gid)
    out: list[CourseLesson] = []
    for lid, slug, sort_order, title, level, practice in rows:
        topic = topics.get(lid, "")
        support = support_of(slug, topic)[0] if is_support(topic) else None
        out.append(
            CourseLesson(
                id=lid,
                slug=slug,
                sort_order=sort_order or 0,
                title=title,
                topic=topic,
                chapter=None if support else chapter_of(slug, level or 1),
                support=support,
                feathers=tuple(partition(vocab.get(lid, []), grammar.get(lid, []), practice)),
            )
        )
    out.sort(key=lambda c: (c.sort_order, c.id))
    if out:
        _cache = (now, out)
    return out


# ------------------------------------------------------------------ the learner --
@dataclass
class Record:
    met: set[ItemKey] = field(default_factory=set)
    answered: dict[int, set[str]] = field(default_factory=dict)  # lesson id -> question ids
    parts: dict[int, set[str]] = field(default_factory=dict)  # lesson id -> part ids


async def record(db: AsyncSession, learner_id: uuid.UUID, lesson_id: int | None = None) -> Record:
    """What the learner has marked and answered (of one lesson, or of all)."""
    r = Record()
    states = select(ItemState.item_id, ItemState.item_type).where(ItemState.learner_id == learner_id)
    r.met = {(t, i) for i, t in (await db.execute(states)).all()}
    q = select(LessonExerciseResult.lesson_id, LessonExerciseResult.question_id).where(LessonExerciseResult.learner_id == learner_id)
    p = select(LessonPartDone.lesson_id, LessonPartDone.part_id).where(LessonPartDone.learner_id == learner_id)
    if lesson_id is not None:
        q = q.where(LessonExerciseResult.lesson_id == lesson_id)
        p = p.where(LessonPartDone.lesson_id == lesson_id)
    for lid, qid in (await db.execute(q)).all():
        r.answered.setdefault(lid, set()).add(qid)
    for lid, part in (await db.execute(p)).all():
        r.parts.setdefault(lid, set()).add(part)
    return r


def lesson_status(lesson: CourseLesson, rec: Record) -> list[bool]:
    answered = rec.answered.get(lesson.id, set())
    parts = rec.parts.get(lesson.id, set())
    return [earned(f, rec.met, answered, parts) for f in lesson.feathers]


@dataclass(frozen=True)
class ChapterTally:
    n: int
    earned: int
    credited: int  # feathers of lessons the entry check let the learner skip
    total: int
    lessons: int
    lessons_done: int

    @property
    def done(self) -> bool:
        return self.lessons > 0 and self.earned + self.credited >= self.total


@dataclass(frozen=True)
class Star:
    lesson_id: int
    title: str
    earned: int
    total: int

    @property
    def lit(self) -> bool:
        return self.total > 0 and self.earned >= self.total


@dataclass(frozen=True)
class Constellation:
    code: str
    name: str
    topic: str
    relic: str | None
    stars: tuple[Star, ...]

    @property
    def done(self) -> bool:
        return bool(self.stars) and all(s.lit for s in self.stars)


@dataclass(frozen=True)
class Tally:
    chapters: dict[int, ChapterTally]
    stage: int  # 1 + the chapters finished in a row from I
    station: bool  # chapter III's station is reached
    starlight: int
    starlight_total: int
    sparkle: int  # 0..3 by the starlight feathers alone
    constellations: tuple[Constellation, ...]


def sparkle_of(starlight: int) -> int:
    return sum(1 for at in SPARKLE_AT if starlight >= at)


def tally(lessons: Iterable[CourseLesson], rec: Record, placed_at: int | None = None) -> Tally:
    per: dict[int, list[int]] = {n: [0, 0, 0, 0, 0] for n in (1, 2, 3, 4)}  # earned, credited, total, lessons, done
    station_lessons: list[bool] = []
    groups: dict[str, list[tuple[CourseLesson, int]]] = defaultdict(list)
    starlight = starlight_total = 0
    for lesson in lessons:
        got = sum(lesson_status(lesson, rec))
        total = len(lesson.feathers)
        if lesson.chapter is None:
            groups[lesson.support or ""].append((lesson, got))
            starlight += got
            starlight_total += total
            continue
        row = per.setdefault(lesson.chapter, [0, 0, 0, 0, 0])
        skipped = placed_at is not None and lesson.sort_order < placed_at and got < total
        row[0] += got
        row[1] += total - got if skipped else 0
        row[2] += total
        row[3] += 1
        row[4] += 1 if got >= total or skipped else 0
        if (lesson.slug or "").startswith(STATION_AFTER):
            station_lessons.append(got >= total or skipped)
    chapters = {n: ChapterTally(n, r[0], r[1], r[2], r[3], r[4]) for n, r in sorted(per.items())}
    stage = 1
    for n in (1, 2, 3, 4):
        if chapters[n].done:
            stage = n + 1
        else:
            break
    constellations = []
    for code, members in groups.items():
        first = members[0][0]
        _, name, relic = support_of(first.slug, first.topic)
        constellations.append(
            Constellation(
                code=code,
                name=name,
                topic=first.topic,
                relic=relic,
                stars=tuple(Star(l.id, l.title, got, len(l.feathers)) for l, got in members),
            )
        )
    return Tally(
        chapters=chapters,
        stage=stage,
        station=stage > 3 or (bool(station_lessons) and all(station_lessons)),
        starlight=starlight,
        starlight_total=starlight_total,
        sparkle=sparkle_of(starlight),
        constellations=tuple(constellations),
    )


def feathers_out(lesson: CourseLesson, rec: Record) -> list[dict[str, Any]]:
    """One lesson's feathers for the lesson screen: what each holds and whether it is earned."""
    status = lesson_status(lesson, rec)
    return [
        {
            "id": f.id,
            "kind": f.kind,
            "label": f.label,
            "skill": f.skill,
            "part": f.part,
            "item_ids": [i for _, i in f.items],
            "question_ids": list(f.questions),
            "earned": ok,
        }
        for f, ok in zip(lesson.feathers, status, strict=True)
    ]


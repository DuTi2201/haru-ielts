"""The database side of app.services.daily_reading: what a learner has met, what was offered on a
day, and the outcome of a sitting.

Kept apart from the pure rules so the daily-reading endpoints and `/me/plan` read the same picks."""
from __future__ import annotations

import uuid
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import GrammarPoint, ItemState, Lesson, ReadingLog, VocabItem
from app.schemas import (
    DailyAnswerOut,
    DailyFinishOut,
    DailyGlossOut,
    DailyGrammarOut,
    DailyLineOut,
    DailyPassageOut,
    DailyQuestionOut,
    DailyReadingOut,
    DailyWordOut,
)
from app.services import competency_db, daily_reading, passages, srs
from app.services.daily_reading import Card, Key

NOTHING_YET_VI = (
    "Chưa có bài đọc nào phù hợp. Bài đọc/hội thoại mở ra khi bạn đã học qua các mẫu ngữ pháp "
    "của nó — hãy học thêm ở phần Bài học, ngày mai quay lại nhé."
)


# ------------------------------------------------------------------ the lessons --
@dataclass
class Context:
    """The cards of every seeded lesson, found by (lesson slug, pattern | headword)."""

    slugs: list[str] = field(default_factory=list)
    lesson_ids: dict[str, int] = field(default_factory=dict)
    grammar_index: dict[tuple[str, str], int] = field(default_factory=dict)
    vocab_index: dict[tuple[str, str], int] = field(default_factory=dict)
    grammar_info: dict[int, tuple[str, str, int]] = field(default_factory=dict)  # id -> (pattern, meaning_vi, lesson_id)
    vocab_info: dict[int, tuple[str, str, int]] = field(default_factory=dict)  # id -> (headword, meaning_vi, lesson_id)


async def load_context(db: AsyncSession) -> Context:
    """Two narrow queries over the seeded lessons (those with a slug)."""
    ctx = Context()
    slugs: set[str] = set()
    for slug, lesson_id, gid, pattern, meaning in (
        await db.execute(
            select(Lesson.slug, Lesson.id, GrammarPoint.id, GrammarPoint.pattern, GrammarPoint.meaning_vi).join(
                Lesson, Lesson.id == GrammarPoint.lesson_id
            )
        )
    ).all():
        if slug is None:
            continue
        slugs.add(slug)
        ctx.lesson_ids[slug] = lesson_id
        ctx.grammar_index[(slug, pattern)] = gid
        ctx.grammar_info[gid] = (pattern, meaning, lesson_id)
    for slug, lesson_id, vid, headword, meaning in (
        await db.execute(
            select(Lesson.slug, Lesson.id, VocabItem.id, VocabItem.headword, VocabItem.meaning_vi).join(
                Lesson, Lesson.id == VocabItem.lesson_id
            )
        )
    ).all():
        if slug is None:
            continue
        slugs.add(slug)
        ctx.lesson_ids[slug] = lesson_id
        ctx.vocab_index[(slug, headword)] = vid
        ctx.vocab_info[vid] = (headword, meaning, lesson_id)
    ctx.slugs = sorted(slugs)
    return ctx


def cards_of(states: Iterable[ItemState], now: datetime) -> dict[Key, Card]:
    """The learner's study records as the pure rules read them."""
    return {
        (s.item_type, s.item_id): Card(
            strength=s.strength or 0.0, due=srs.is_due(competency_db.schedule_of(s), now)
        )
        for s in states
    }


# ------------------------------------------------------------------ the sitting --
@dataclass
class Pick:
    passage: passages.Passage
    refs: daily_reading.Refs
    log: ReadingLog | None  # None: previewed, not written

    @property
    def done(self) -> bool:
        return self.log is not None and self.log.finished_at is not None


@dataclass
class Sitting:
    day: date
    picks: list[Pick]
    written: bool  # the day's picks are in the log


async def _logs_of_day(db: AsyncSession, learner_id: uuid.UUID, day: date) -> list[ReadingLog]:
    rows = (
        (
            await db.execute(
                select(ReadingLog).where(ReadingLog.learner_id == learner_id, ReadingLog.day == day)
            )
        )
        .scalars()
        .all()
    )
    return sorted(rows, key=lambda r: (r.picked_at is None, r.picked_at, r.passage_id))


def _one_per_kind(logs: Sequence[ReadingLog], texts: dict[str, passages.Passage]) -> list[ReadingLog]:
    """A day holds at most one dialogue and one reading (two screens opened at once could have drawn
    different texts): the first logged of each kind wins. A text no longer in the bank is skipped."""
    out: dict[str, ReadingLog] = {}
    for log in logs:
        p = texts.get(log.passage_id)
        if p is not None and p.kind not in out:
            out[p.kind] = log
    return [out[k] for k in passages.KINDS if k in out]


async def sitting(
    db: AsyncSession,
    learner_id: uuid.UUID,
    cards: dict[Key, Card],
    ctx: Context,
    now: datetime,
    *,
    persist: bool,
) -> Sitting:
    """Today's dialogue and reading for this learner. The first call of the day draws them (and, with
    `persist`, writes them to the log); every later call that day returns the same two."""
    day = daily_reading.local_day(now, settings.DAILY_READING_TZ)
    texts = passages.by_id()

    def pick_of(log: ReadingLog) -> Pick:
        p = texts[log.passage_id]
        return Pick(p, daily_reading.resolve(p, ctx.slugs, ctx.grammar_index, ctx.vocab_index), log)

    logs = _one_per_kind(await _logs_of_day(db, learner_id, day), texts)
    if logs:
        return Sitting(day, [pick_of(log) for log in logs], True)

    pool = daily_reading.candidates(texts.values(), ctx.slugs, ctx.grammar_index, ctx.vocab_index, cards)
    if not pool:
        return Sitting(day, [], False)
    offered = {
        pid: last
        for pid, last in (
            await db.execute(
                select(ReadingLog.passage_id, func.max(ReadingLog.day))
                .where(ReadingLog.learner_id == learner_id, ReadingLog.day < day)
                .group_by(ReadingLog.passage_id)
            )
        ).all()
    }
    chosen = daily_reading.pick_day(pool, learner_id, day, offered)
    if not persist:
        return Sitting(day, [Pick(c.passage, c.refs, None) for c in chosen], False)

    new_logs = [ReadingLog(learner_id=learner_id, day=day, passage_id=c.passage.id, kind=c.passage.kind) for c in chosen]
    db.add_all(new_logs)
    try:
        await db.commit()
    except IntegrityError:
        # another request drew the same text a moment ago: use what it wrote
        await db.rollback()
        logs = _one_per_kind(await _logs_of_day(db, learner_id, day), texts)
        return Sitting(day, [pick_of(log) for log in logs], True)
    return Sitting(day, [Pick(c.passage, c.refs, log) for c, log in zip(chosen, new_logs)], True)


# --------------------------------------------------------------------- the output --
def passage_out(pick: Pick, ctx: Context, cards: dict[Key, Card]) -> DailyPassageOut:
    p = pick.passage
    own_lesson_id = ctx.lesson_ids.get(p.lesson)
    lines = [
        DailyLineOut(
            who=line.who,
            speaker=p.speakers.get(line.who) if p.kind == "dialogue" else None,
            ko=line.ko,
            vi=line.vi,
            voice=passages.VOICE_OF[line.who],
        )
        for line in p.lines
    ]

    def choose(group: Sequence[Key], info: dict[int, tuple[str, str, int]]) -> int | None:
        if not group:
            return None
        for _type, item_id in group:
            if info.get(item_id, ("", "", None))[2] == own_lesson_id:
                return item_id
        return group[0][1]

    grammar = []
    for use, group in zip(p.uses, pick.refs.grammar):
        gid = choose(group, ctx.grammar_info)
        _pattern, meaning, lesson_id = ctx.grammar_info.get(gid, (use.pattern, None, None)) if gid else (use.pattern, None, None)
        grammar.append(DailyGrammarOut(grammar_id=gid, lesson_id=lesson_id, pattern=use.pattern, meaning_vi=meaning))
    words = []
    for kw, group in zip(p.keywords, pick.refs.words):
        vid = choose(group, ctx.vocab_info)
        headword, meaning, lesson_id = ctx.vocab_info.get(vid, (kw.word, None, None)) if vid else (kw.word, None, None)
        words.append(
            DailyWordOut(
                vocab_item_id=vid,
                lesson_id=lesson_id,
                headword=kw.word,
                meaning_vi=meaning,
                known=any(k in cards for k in group),
            )
        )
    log = pick.log
    return DailyPassageOut(
        id=p.id,
        kind=p.kind,  # type: ignore[arg-type]
        title_en=p.title_en,
        title_vi=p.title_vi,
        scene_vi=p.scene_vi,
        speakers=p.speakers,
        lines=lines,
        text_en=p.text_en,
        voice=passages.VOICE_OF["N"],
        glossary=[DailyGlossOut(ko=g.ko, vi=g.vi) for g in p.glossary],
        questions=[DailyQuestionOut(q_vi=q.q_vi, options=list(q.options)) for q in p.questions],
        grammar=grammar,
        words=words,
        why_vi=daily_reading.why_vi(p, pick.refs, cards),
        status="done" if pick.done else "todo",
        correct=log.correct if pick.done and log is not None else None,
        total=log.total if pick.done and log is not None else None,
    )


def reading_out(s: Sitting, items: list[DailyPassageOut]) -> DailyReadingOut:
    return DailyReadingOut(
        day=s.day,
        items=items,
        done=sum(1 for i in items if i.status == "done"),
        total=len(items),
        note_vi=None if items else NOTHING_YET_VI,
    )


# ---------------------------------------------------------------------- finishing --
class NotToday(Exception):
    """The text is not one of today's picks for this learner."""


async def finish(
    db: AsyncSession,
    learner_id: uuid.UUID,
    passage_id: str,
    answers: Sequence[int | None],
    now: datetime,
) -> DailyFinishOut:
    """Grade a sitting of one of today's texts. The first submission is the one that counts (it
    is kept); later ones are graded and explained again but change nothing."""
    p = passages.by_id().get(passage_id)
    if p is None:
        raise NotToday(passage_id)
    day = daily_reading.local_day(now, settings.DAILY_READING_TZ)
    logs = await _logs_of_day(db, learner_id, day)
    log = next((x for x in logs if x.passage_id == passage_id), None)
    if log is None:
        raise NotToday(passage_id)
    graded = daily_reading.grade(p, answers)  # ValueError: wrong number of answers
    right = sum(1 for g in graded if g.is_right)
    if log.finished_at is None:
        log.finished_at = now.astimezone(timezone.utc)
        log.correct = right
        log.total = len(graded)
        await db.commit()
    texts = passages.by_id()
    shown = _one_per_kind(logs, texts)
    return DailyFinishOut(
        passage_id=passage_id,
        correct=right,
        total=len(graded),
        answers=[
            DailyAnswerOut(answer=g.answer, correct=g.correct, is_right=g.is_right, explain_vi=g.explain_vi)
            for g in graded
        ],
        done=sum(1 for x in shown if x.finished_at is not None),
        day_total=len(shown),
    )

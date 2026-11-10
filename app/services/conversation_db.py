"""The database side of "Trò chuyện với Haru" (app.services.conversation): what the learner has
studied and how well they remember it, read into a `LearnerContext`, and the daily minute cap.

"The lesson being studied" is the lesson of the card the learner touched last (the lesson screen
and the review queue both write `item_state`), so it follows what they actually did today rather
than a plan. "Earlier lessons" are the lessons of the same topic that come before it and that the
learner has touched, at most five, oldest first.
"""
from __future__ import annotations

import uuid
from collections.abc import Iterable
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    ConversationSession,
    GrammarPoint,
    ItemState,
    LearnerTalkProfile,
    Lesson,
    LessonTopic,
    PlacementAttempt,
    Profile,
    TalkNote,
    Topic,
    VocabItem,
)
from app.services import talk_profile
from app.services.conversation import LearnerContext, LessonBrief, Pattern, Word, bucket_of

MAX_EARLIER = 5
CURRENT_WORDS = 14
EARLIER_WEAK_WORDS = 10
EARLIER_STRONG_WORDS = 6
CURRENT_PATTERNS = 6
EARLIER_WEAK_PATTERNS = 5
EARLIER_STRONG_PATTERNS = 4


def _brief(lesson: Lesson) -> LessonBrief:
    return LessonBrief(id=lesson.id, title=lesson.title, title_en=lesson.title_en, summary=lesson.summary)


def _take(items: Iterable, n: int) -> list:
    return list(items)[:n]


async def lesson_they_may_open(db: AsyncSession, profile: Profile, lesson_id: int | None) -> int | None:
    """The lesson the learner chose to practise on, if it exists and they may open it (a locked
    lesson is not practised before it is bought: the choice is dropped, the last studied is used)."""
    if lesson_id is None:
        return None
    from app.services.billing import access as billing_access

    lesson = await db.get(Lesson, lesson_id)
    if lesson is None:
        return None
    held = await billing_access.load_access(db, profile)
    return lesson.id if held.can_open(lesson.sort_order) else None


async def load_context(
    db: AsyncSession,
    profile: Profile,
    *,
    remember: bool,
    talk: LearnerTalkProfile | None = None,
    now: datetime | None = None,
    lesson_id: int | None = None,
) -> LearnerContext:
    now = now or datetime.now(timezone.utc)
    states = (await db.execute(select(ItemState).where(ItemState.learner_id == profile.id))).scalars().all()
    state_of = {(s.item_type, s.item_id): s for s in states}

    # -- the lesson being studied: the one holding the card touched last
    current: Lesson | None = None
    if states:
        vocab_ids = [s.item_id for s in states if s.item_type == "vocab_item"]
        grammar_ids = [s.item_id for s in states if s.item_type == "grammar_point"]
        lesson_of: dict[tuple[str, int], int] = {}
        if vocab_ids:
            for vid, lid in (await db.execute(select(VocabItem.id, VocabItem.lesson_id).where(VocabItem.id.in_(vocab_ids)))).all():
                if lid is not None:
                    lesson_of[("vocab_item", vid)] = lid
        if grammar_ids:
            for gid, lid in (
                await db.execute(select(GrammarPoint.id, GrammarPoint.lesson_id).where(GrammarPoint.id.in_(grammar_ids)))
            ).all():
                if lid is not None:
                    lesson_of[("grammar_point", gid)] = lid
        touched = sorted(
            (s for s in states if (s.item_type, s.item_id) in lesson_of), key=lambda s: s.last_seen, reverse=True
        )
        if touched:
            current = await db.get(Lesson, lesson_of[(touched[0].item_type, touched[0].item_id)])
        touched_lessons = set(lesson_of.values())
    else:
        touched_lessons = set()
    if lesson_id is not None:  # the learner chose the lesson ("Nói về bài này" from the lesson screen)
        chosen = await db.get(Lesson, lesson_id)
        if chosen is not None:
            current = chosen
    if current is None:
        # nothing studied yet: the first lesson that has words to talk with (not the alphabet lesson)
        current = (
            (
                await db.execute(
                    select(Lesson)
                    .where(Lesson.id.in_(select(VocabItem.lesson_id).where(VocabItem.lesson_id.isnot(None))))
                    .order_by(Lesson.sort_order, Lesson.id)
                    .limit(1)
                )
            )
            .scalars()
            .first()
        )

    # -- its topic and the earlier lessons of that topic the learner has touched
    topic_name: str | None = None
    earlier: list[Lesson] = []
    if current is not None:
        topic_row = (
            await db.execute(
                select(Topic.id, Topic.name)
                .join(LessonTopic, LessonTopic.topic_id == Topic.id)
                .where(LessonTopic.lesson_id == current.id)
                .limit(1)
            )
        ).first()
        if topic_row is not None:
            topic_name = topic_row.name
            siblings = (
                (
                    await db.execute(
                        select(Lesson)
                        .join(LessonTopic, LessonTopic.lesson_id == Lesson.id)
                        .where(LessonTopic.topic_id == topic_row.id, Lesson.sort_order < current.sort_order)
                        .order_by(Lesson.sort_order.desc(), Lesson.id.desc())
                    )
                )
                .scalars()
                .all()
            )
            earlier = [l for l in siblings if l.id in touched_lessons][:MAX_EARLIER][::-1]

    # -- words and patterns: all of the current lesson, the slipping and some solid ones of the earlier
    lesson_ids = ([current.id] if current else []) + [l.id for l in earlier]
    words: list[Word] = []
    patterns: list[Pattern] = []
    shaky: list[str] = []
    if lesson_ids:
        vocab = (await db.execute(select(VocabItem).where(VocabItem.lesson_id.in_(lesson_ids)).order_by(VocabItem.id))).scalars().all()
        grammar = (
            await db.execute(select(GrammarPoint).where(GrammarPoint.lesson_id.in_(lesson_ids)).order_by(GrammarPoint.id))
        ).scalars().all()

        def bucket(kind: str, item_id: int):
            s = state_of.get((kind, item_id))
            return bucket_of(s.strength if s else None, s.last_correct if s else None, s.introduced_at if s else None, now)

        cur_id = current.id if current else None
        cur_words = [
            Word(v.headword, v.meaning_vi, bucket("vocab_item", v.id))
            for v in vocab
            if v.lesson_id == cur_id and v.priority != "recognize"
        ]
        old_words = [Word(v.headword, v.meaning_vi, bucket("vocab_item", v.id)) for v in vocab if v.lesson_id != cur_id]
        words = (
            _take(cur_words, CURRENT_WORDS)
            + _take((w for w in old_words if w.bucket == "weak"), EARLIER_WEAK_WORDS)
            + _take((w for w in old_words if w.bucket == "strong"), EARLIER_STRONG_WORDS)
        )

        def pat(g: GrammarPoint) -> Pattern:
            return Pattern(g.pattern, g.meaning_vi, g.example_en, bucket("grammar_point", g.id))

        cur_pats = [pat(g) for g in grammar if g.lesson_id == cur_id]
        old_pats = [pat(g) for g in grammar if g.lesson_id != cur_id]
        patterns = (
            _take(cur_pats, CURRENT_PATTERNS)
            + _take((p for p in old_pats if p.bucket == "weak"), EARLIER_WEAK_PATTERNS)
            + _take((p for p in old_pats if p.bucket == "strong"), EARLIER_STRONG_PATTERNS)
        )
        shaky = [
            g.pattern
            for g in grammar
            if (s := state_of.get(("grammar_point", g.id))) is not None and s.last_correct is False
        ][:4]

    # phase 3: what Haru carries over (the band always; the learner's own facts only with consent)
    level = int(current.level) if current is not None and current.level else 1
    entry = await _entry_check(db, profile.id)
    # no talk history: from the lesson's level, one band lower when the entry check placed them
    start = talk_profile.placed_band(level) if entry.get("tested") else talk_profile.initial_band(level)
    band = talk_profile.clamp_band(talk.band, start) if talk else start
    remembered = [str(f.get("text", "")) for f in (talk.facts if talk else []) if f.get("text")] if remember else []
    practice = (
        (
            await db.execute(
                select(TalkNote.ko)
                .where(TalkNote.learner_id == profile.id, TalkNote.kind == "sentence", TalkNote.done_at.is_(None))
                .order_by(TalkNote.created_at.desc())
                .limit(3)
            )
        )
        .scalars()
        .all()
    )

    return LearnerContext(
        name=profile.display_name,
        goal=profile.goal,
        level=level,
        topic=topic_name,
        current=_brief(current) if current is not None else None,
        earlier=[_brief(l) for l in earlier],
        words=words,
        patterns=patterns,
        shaky_patterns=shaky,
        remembered=remembered[:8],
        band=band,
        last_topics=list(talk.last_topics or []) if talk else [],
        follow_up=talk.follow_up if talk else None,
        practice_lines=[str(x) for x in practice],
        entry_gaps=[str(p) for g in entry.get("gaps") or [] for p in (g.get("patterns") or [])][:4],
    )


async def _entry_check(db: AsyncSession, learner_id: uuid.UUID) -> dict:
    """The latest adaptive entry check's summary ({} when none was taken)."""
    rows = (
        await db.execute(
            select(PlacementAttempt.summary)
            .where(PlacementAttempt.learner_id == learner_id)
            .order_by(PlacementAttempt.taken_at.desc())
            .limit(5)
        )
    ).scalars().all()
    return next((s for s in rows if (s or {}).get("kind") == "adaptive"), {}) or {}


async def seconds_used_today(
    db: AsyncSession, learner_id: uuid.UUID, *, session_seconds: int, now: datetime | None = None
) -> int:
    """Talk time in the last 24 hours. A session that was opened but never finished counts as a
    full session until it is an hour old (it may still be running), then as nothing."""
    now = now or datetime.now(timezone.utc)
    since = now - timedelta(hours=24)
    finished = (
        await db.execute(
            select(func.coalesce(func.sum(ConversationSession.seconds), 0)).where(
                ConversationSession.learner_id == learner_id,
                ConversationSession.started_at > since,
                ConversationSession.ended_at.is_not(None),
            )
        )
    ).scalar_one()
    open_now = (
        await db.execute(
            select(func.count()).select_from(ConversationSession).where(
                ConversationSession.learner_id == learner_id,
                ConversationSession.started_at > now - timedelta(hours=1),
                ConversationSession.ended_at.is_(None),
            )
        )
    ).scalar_one()
    return int(finished) + int(open_now) * session_seconds


async def get_talk_profile(db: AsyncSession, learner_id: uuid.UUID) -> LearnerTalkProfile | None:
    return await db.get(LearnerTalkProfile, learner_id)

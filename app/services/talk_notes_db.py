"""Database side of "Sổ trò chuyện" → the review queue.

A word kept from a talk with Haru (`talk_note`, kind "word") is linked to the vocabulary card with
the same headword — a lesson card first, else a news-article card (app.services.talk_history
.cards_for_words) — and that card gets an item_state, so the word comes back in the daily review.
A word with no card stays a note: no vocabulary row is ever made up here.

- `link_cards`: at save time ("Đưa vào ôn tập"), the words of one session;
- `backfill_note_cards`: once, for the notes saved before this linking existed (or before the card
  was added to a lesson): `python -m app.services.talk_notes_db`.
"""
from __future__ import annotations

import asyncio
import sys
import uuid
from collections import defaultdict
from collections.abc import Iterable
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ItemState, TalkNote, VocabItem
from app.services import srs, talk_history


async def cards_by_hangul(db: AsyncSession, words: Iterable[str]) -> dict[str, int]:
    """word -> the id of its vocabulary card, for the words that have one."""
    wanted = sorted({w.strip() for w in words if w and w.strip()})
    if not wanted:
        return {}
    rows = (
        await db.execute(
            select(VocabItem.id, VocabItem.headword, VocabItem.lesson_id)
            .where(VocabItem.headword.in_(wanted))
            .order_by(VocabItem.id)
        )
    ).all()
    return talk_history.cards_for_words(wanted, [tuple(r) for r in rows])


async def put_in_review(
    db: AsyncSession, learner_id: uuid.UUID, vocab_ids: Iterable[int], now: datetime, *, due_now: bool = True
) -> None:
    """Every card gets an item_state, so it is in the review queue. A card with no state yet is due
    now. `due_now` (at save time: the learner just met the word again) also brings a card that is
    already scheduled forward to now and takes back a "Đã biết" mark; the backfill leaves cards
    already being studied alone. A card first met here is `introduced_at` now at save time (it is
    the day's new word), but not in the backfill, so old notes do not use up today's new cards.
    Nothing is committed: the caller does."""
    ids = sorted(set(vocab_ids))
    if not ids:
        return
    states = {
        s.item_id: s
        for s in (
            await db.execute(
                select(ItemState).where(
                    ItemState.learner_id == learner_id,
                    ItemState.item_type == "vocab_item",
                    ItemState.item_id.in_(ids),
                )
            )
        ).scalars()
    }
    for vid in ids:
        s = states.get(vid)
        if s is None:
            db.add(
                ItemState(
                    learner_id=learner_id, item_type="vocab_item", item_id=vid, strength=0.0, last_seen=now,
                    due_at=now, introduced_at=now if due_now else None, reps=0, lapses=0, ease=srs.START_EASE,
                    interval_days=0.0,
                )
            )
        elif due_now:
            s.known_at = None
            if s.due_at is None or s.due_at > now:
                s.due_at = now


async def backfill_note_cards(
    db: AsyncSession, *, learner_id: uuid.UUID | None = None, now: datetime | None = None
) -> int:
    """Link the saved words that have no card yet (`vocab_item_id` NULL) to their card, and put
    those cards in review. Returns how many notes were linked. Commits."""
    now = now or datetime.now(timezone.utc)
    q = select(TalkNote).where(TalkNote.kind == "word", TalkNote.vocab_item_id.is_(None))
    if learner_id is not None:
        q = q.where(TalkNote.learner_id == learner_id)
    notes = list((await db.execute(q)).scalars().all())
    if not notes:
        return 0
    card_of = await cards_by_hangul(db, [n.ko for n in notes])
    by_learner: dict[uuid.UUID, set[int]] = defaultdict(set)
    linked = 0
    for n in notes:
        vid = card_of.get((n.ko or "").strip())
        if vid is None:
            continue
        n.vocab_item_id = vid
        linked += 1
        if n.done_at is None:  # a word ticked off as learned is not pushed back into review
            by_learner[n.learner_id].add(vid)
    for lid, ids in by_learner.items():
        await put_in_review(db, lid, ids, now, due_now=False)
    await db.commit()
    return linked


async def _main() -> int:
    from app.db import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        n = await backfill_note_cards(db)
    print(f"linked {n} saved word(s) to their card")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(_main()))

"""Database side of "Trình bày với Haru" fitting (app.services.present_profile): everything the
learner has studied in the app — grammar points and words with a review card — as items to deploy
when speaking, plus the recent first tries that set the focus."""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import GrammarPoint, ItemState, PresentationSession, VocabItem
from app.services.present_profile import KnowItem

MAX_WORDS = 400


async def load_knowledge(db: AsyncSession, learner_id: uuid.UUID) -> list[KnowItem]:
    grammar = (
        await db.execute(
            select(GrammarPoint, ItemState)
            .join(ItemState, (ItemState.item_id == GrammarPoint.id) & (ItemState.item_type == "grammar_point"))
            .where(ItemState.learner_id == learner_id)
        )
    ).all()
    words = (
        await db.execute(
            select(VocabItem, ItemState)
            .join(ItemState, (ItemState.item_id == VocabItem.id) & (ItemState.item_type == "vocab_item"))
            .where(ItemState.learner_id == learner_id)
            .order_by(ItemState.last_seen.desc())
            .limit(MAX_WORDS)
        )
    ).all()
    out = [
        KnowItem(f"g:{g.id}", "grammar", g.pattern, g.meaning_vi, g.example_ko, int(g.level or 1),
                 s.strength, s.last_correct, s.introduced_at)
        for g, s in grammar
    ]
    out += [
        KnowItem(f"v:{v.id}", "word", v.hangul, v.meaning_vi, None, 1, s.strength, s.last_correct, s.introduced_at)
        for v, s in words
        if v.priority != "recognize"
    ]
    return out


def known_patterns(items: list[KnowItem], limit: int = 25) -> list[str]:
    """Studied grammar, the solid ones first, for the prompts ("suggest with what they know")."""
    g = [i for i in items if i.kind == "grammar"]
    g.sort(key=lambda i: (-(i.strength or 0), i.level))
    return [i.ko for i in g[:limit]]


async def recent_first_tries(db: AsyncSession, learner_id: uuid.UUID, limit: int = 8) -> list[dict[str, Any]]:
    rows = (
        await db.execute(
            select(PresentationSession.attempts)
            .where(PresentationSession.learner_id == learner_id)
            .order_by(PresentationSession.created_at.desc())
            .limit(limit * 2)
        )
    ).scalars().all()
    out = []
    for attempts in rows:
        if attempts:
            out.append(((attempts[0] or {}).get("eval") or {}).get("scores") or {})
        if len(out) >= limit:
            break
    return out

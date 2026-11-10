"""«Kho từ TOPIK»: the decks of intermediate and advanced dictionary words the lessons do not teach
(app/services/topik_bank.py). Anyone may look at a deck; a signed-in learner adds it to their
reviews and its words then come into the daily new cards, a few a day."""
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import _problem, get_current_profile, get_optional_profile
from app.db import get_db
from app.models import ItemState, LearnerBankDeck, Lesson, Profile, VocabItem
from app.schemas import BankDeckOut, BankDeckWordsOut, EditorialPresentRequest, PresentSessionOut, PresentStartRequest, VocabItemOut
from app.api.routers import presentation as presentation_router
from app.services import presentation, topik_bank

router = APIRouter(tags=["topik-bank"])

PRACTICED_REPS = 2  # right answers in a row before a word is used in a sentence or a talk
MIN_PRACTICED = 3  # words needed to build a round


async def _ids_by_entry(db: AsyncSession) -> dict[int, int]:
    return dict((await db.execute(select(VocabItem.bank_key, VocabItem.id).where(VocabItem.bank_key.isnot(None)))).all())


async def _deck_rows(db: AsyncSession, profile: Profile | None) -> list[BankDeckOut]:
    by_entry = await _ids_by_entry(db)
    added: set[str] = set()
    started: set[int] = set()
    practiced: set[int] = set()
    if profile is not None:
        added = set((await db.execute(select(LearnerBankDeck.deck_key).where(LearnerBankDeck.learner_id == profile.id))).scalars())
        bank_ids = list(by_entry.values())
        if bank_ids:
            for item_id, reps in (
                await db.execute(
                    select(ItemState.item_id, ItemState.reps).where(
                        ItemState.learner_id == profile.id,
                        ItemState.item_type == "vocab_item",
                        ItemState.item_id.in_(bank_ids),
                    )
                )
            ).all():
                started.add(item_id)
                if (reps or 0) >= PRACTICED_REPS:
                    practiced.add(item_id)
    out = []
    for deck in topik_bank.decks().values():
        ids = [by_entry[e] for e in deck.words if e in by_entry]
        if not ids:
            continue
        out.append(
            BankDeckOut(
                key=deck.key,
                title_vi=deck.title_vi,
                grade=deck.grade,  # type: ignore[arg-type]
                grade_vi=deck.grade_vi,
                words=len(ids),
                added=deck.key in added,
                started=sum(1 for i in ids if i in started),
                practiced=sum(1 for i in ids if i in practiced),
            )
        )
    return out


@router.get("/bank/decks", response_model=list[BankDeckOut])
async def list_bank_decks(
    db: Annotated[AsyncSession, Depends(get_db)],
    profile: Annotated[Profile | None, Depends(get_optional_profile)] = None,
    lesson_id: Annotated[int | None, Query(description="only the decks that extend this lesson, closest first")] = None,
):
    rows = await _deck_rows(db, profile)
    if lesson_id is None:
        return rows
    slug = (await db.execute(select(Lesson.slug).where(Lesson.id == lesson_id))).scalar_one_or_none()
    order = {key: i for i, key in enumerate(topik_bank.lesson_decks().get(slug or "", []))}
    return sorted((r for r in rows if r.key in order), key=lambda r: order[r.key])


@router.get("/bank/decks/{deck_key}", response_model=BankDeckWordsOut)
async def get_bank_deck(
    deck_key: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    profile: Annotated[Profile | None, Depends(get_optional_profile)] = None,
):
    deck = topik_bank.decks().get(deck_key)
    if deck is None:
        raise _problem(status.HTTP_404_NOT_FOUND, "Không có bộ từ này.", "not_found")
    rows = {
        v.bank_key: v
        for v in (await db.execute(select(VocabItem).where(VocabItem.bank_key.in_(deck.words)))).scalars()
    }
    words = [VocabItemOut.model_validate(rows[e]) for e in deck.words if e in rows]
    added = False
    if profile is not None:
        added = (
            await db.execute(
                select(func.count()).select_from(LearnerBankDeck).where(LearnerBankDeck.learner_id == profile.id, LearnerBankDeck.deck_key == deck_key)
            )
        ).scalar_one() > 0
    return BankDeckWordsOut(
        key=deck.key, title_vi=deck.title_vi, grade=deck.grade, grade_vi=deck.grade_vi, added=added, words=words  # type: ignore[arg-type]
    )


@router.put("/me/bank/decks/{deck_key}", response_model=list[BankDeckOut])
async def add_bank_deck(
    deck_key: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    profile: Annotated[Profile, Depends(get_current_profile)],
):
    if deck_key not in topik_bank.decks():
        raise _problem(status.HTTP_404_NOT_FOUND, "Không có bộ từ này.", "not_found")
    await db.execute(
        pg_insert(LearnerBankDeck).values(learner_id=profile.id, deck_key=deck_key).on_conflict_do_nothing()
    )
    await db.commit()
    return await _deck_rows(db, profile)


@router.delete("/me/bank/decks/{deck_key}", response_model=list[BankDeckOut])
async def remove_bank_deck(
    deck_key: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    profile: Annotated[Profile, Depends(get_current_profile)],
):
    """Stops new words coming from the deck. Words already started stay in the reviews."""
    row = await db.get(LearnerBankDeck, (profile.id, deck_key))
    if row is not None:
        await db.delete(row)
        await db.commit()
    return await _deck_rows(db, profile)


async def practiced_words(db: AsyncSession, profile: Profile, deck_key: str, min_reps: int = PRACTICED_REPS) -> list[VocabItem]:
    """The deck's words this learner has answered right at least `min_reps` times in a row, the
    shakiest first (they gain most from being used)."""
    deck = topik_bank.decks()[deck_key]
    rows = (
        await db.execute(
            select(VocabItem, ItemState)
            .join(ItemState, (ItemState.item_id == VocabItem.id) & (ItemState.item_type == "vocab_item"))
            .where(
                ItemState.learner_id == profile.id,
                VocabItem.bank_key.in_(deck.words),
                ItemState.reps >= min_reps,
                ItemState.known_at.is_(None),
            )
        )
    ).all()
    rows.sort(key=lambda r: (r[1].strength or 0.0, r[1].last_seen))
    return [v for v, _ in rows]


@router.post("/me/bank/decks/{deck_key}/presentation", response_model=PresentSessionOut, status_code=status.HTTP_201_CREATED)
async def present_bank_deck(
    deck_key: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    profile: Annotated[Profile, Depends(get_current_profile)],
    body: EditorialPresentRequest | None = None,
):
    """"Trình bày 2 phút" / "Phản biện" with a deck's words: the topic is the deck's, and the words
    the learner has practised are the first items to use (same path as the news-article round)."""
    body = body or EditorialPresentRequest()
    deck = topik_bank.decks().get(deck_key)
    if deck is None:
        raise _problem(status.HTTP_404_NOT_FOUND, "Không có bộ từ này.", "not_found")
    words = await practiced_words(db, profile, deck_key)
    if len(words) < MIN_PRACTICED:
        raise _problem(
            status.HTTP_409_CONFLICT,
            "Hãy ôn thêm vài từ của bộ này (đúng ít nhất 2 lần) rồi mới luyện nói bằng chính những từ đó.",
            "not_enough_words",
        )
    handoff = presentation.bank_handoff(
        body.kind,
        deck.title_vi,
        [{"id": v.id, "headword": v.headword, "meaning_vi": v.meaning_vi, "example_en": v.example_en} for v in words],
    )
    return await presentation_router.create_round(
        db,
        profile,
        PresentStartRequest(mode="defense", title=handoff["title"], material=handoff["material"], band_shift=body.band_shift),
        first_targets=handoff["targets"],
        source={"kind": "bank", "deck_key": deck_key, "angle": body.kind},
    )

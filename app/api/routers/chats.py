"""«Hội thoại»: the lessons' dialogues as chats where the learner picks their line (app/services/chats.py).

* GET  /me/chats             — every dialogue, in course order: open (its cards met) or not yet, done or not
* GET  /me/chats/{id}        — one chat: the lines, and four choices for each of the learner's
* POST /me/chats/{id}/finish — how many were right on the first try (counts as a study day)

The grading is on the device (the right line is one of the choices shown). A finished chat is filed
as a learning event ("chat_done")."""
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import _problem, get_current_profile, study_day
from app.db import get_db
from app.models import ItemState, LearningEvent, Lesson, Profile
from app.services import chats, daily_reading, passages
from app.services import daily_reading_db as store

router = APIRouter(tags=["chats"])


class ChatSummaryOut(BaseModel):
    id: str
    title_en: str
    title_vi: str
    scene_vi: str | None = None
    partner: str  # who the learner talks to
    lesson_id: int | None
    lesson_title: str
    lines: int
    open: bool
    done: bool


class ChatTurnOut(BaseModel):
    who: str
    speaker: str
    ko: str
    vi: str
    voice: str
    mine: bool
    options: list[str] = []


class ChatOut(BaseModel):
    id: str
    title_en: str
    title_vi: str
    scene_vi: str | None = None
    partner: str
    me: str
    # the lesson the dialogue belongs to (to go back to it)
    lesson_id: int | None = None
    lesson_title: str = ""
    turns: list[ChatTurnOut]


class ChatFinishIn(BaseModel):
    right: int = Field(ge=0, le=20)
    total: int = Field(ge=1, le=20)


async def _done(db: AsyncSession, profile: Profile) -> set[str]:
    rows = (
        await db.execute(
            select(LearningEvent.payload).where(
                LearningEvent.learner_id == profile.id, LearningEvent.event_type == "chat_done"
            )
        )
    ).scalars()
    return {str((p or {}).get("passage")) for p in rows}


def _dialogues() -> list[passages.Passage]:
    return [p for p in passages.all_passages() if p.kind == "dialogue"]


@router.get("/me/chats", response_model=list[ChatSummaryOut])
async def list_chats(
    db: Annotated[AsyncSession, Depends(get_db)],
    profile: Annotated[Profile, Depends(get_current_profile)],
):
    now = datetime.now(timezone.utc)
    states = (await db.execute(select(ItemState).where(ItemState.learner_id == profile.id))).scalars().all()
    cards = store.cards_of(states, now)
    ctx = await store.load_context(db)
    lessons = {
        slug: (lid, title, order)
        for slug, lid, title, order in (await db.execute(select(Lesson.slug, Lesson.id, Lesson.title, Lesson.sort_order))).all()
        if slug
    }
    done = await _done(db, profile)
    out: list[tuple[int, ChatSummaryOut]] = []
    for p in _dialogues():
        refs = daily_reading.resolve(p, ctx.slugs, ctx.grammar_index, ctx.vocab_index)
        lid, title, order = lessons.get(p.lesson, (None, "", 9999))
        me = chats.learner_role(p)
        out.append(
            (
                order or 9999,
                ChatSummaryOut(
                    id=p.id,
                    title_en=p.title_en,
                    title_vi=p.title_vi,
                    scene_vi=p.scene_vi,
                    partner=p.speakers.get("F" if me == "M" else "M", ""),
                    lesson_id=lid,
                    lesson_title=title,
                    lines=len(p.lines),
                    open=daily_reading.unlocked(refs, cards),
                    done=p.id in done,
                ),
            )
        )
    return [c for _order, c in sorted(out, key=lambda t: (t[0], t[1].id))]


@router.get("/me/chats/{passage_id}", response_model=ChatOut)
async def get_chat(
    passage_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    profile: Annotated[Profile, Depends(get_current_profile)],
):
    p = passages.by_id().get(passage_id)
    if p is None or p.kind != "dialogue":
        raise _problem(404, "No such dialogue", "not_found")
    group = passages.allowed_slugs(p.lesson, {d.lesson for d in _dialogues()})
    others = [d for d in _dialogues() if d.lesson in group]
    me = chats.learner_role(p)
    lesson = (await db.execute(select(Lesson.id, Lesson.title).where(Lesson.slug == p.lesson))).first()
    return ChatOut(
        lesson_id=lesson[0] if lesson else None,
        lesson_title=lesson[1] if lesson else "",
        id=p.id,
        title_en=p.title_en,
        title_vi=p.title_vi,
        scene_vi=p.scene_vi,
        partner=p.speakers.get("F" if me == "M" else "M", ""),
        me=p.speakers.get(me, ""),
        turns=[
            ChatTurnOut(
                who=t.who,
                speaker=t.speaker,
                ko=t.ko,
                vi=t.vi,
                voice=passages.VOICE_OF[t.who],
                mine=t.mine,
                options=list(t.options),
            )
            for t in chats.turns(p, others)
        ],
    )


@router.post("/me/chats/{passage_id}/finish", dependencies=[Depends(study_day)])
async def finish_chat(
    passage_id: str,
    body: ChatFinishIn,
    db: Annotated[AsyncSession, Depends(get_db)],
    profile: Annotated[Profile, Depends(get_current_profile)],
) -> dict[str, bool]:
    if passage_id not in passages.by_id():
        raise _problem(404, "No such dialogue", "not_found")
    db.add(
        LearningEvent(
            learner_id=profile.id,
            event_type="chat_done",
            skill="speaking",
            value=round(min(body.right, body.total) / body.total, 3),
            payload={"passage": passage_id, "right": body.right, "total": body.total},
        )
    )
    await db.commit()
    return {"ok": True}


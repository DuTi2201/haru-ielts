"""Studio: drawing, listing and hiding the lesson pictures (editors and admins only).

Learners never trigger a drawing and never wait for one: a picture is made once, on an
editor's button, in a background job, and kept (see app.services.lesson_image). What a
learner sees is decided by the lesson endpoints in app.api.routers.content."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Depends, status
from starlette.concurrency import run_in_threadpool
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import _problem, require_role
from app.api.routers.content import _LESSON_ORDER
from app.core.config import settings
from app.db import get_db
from app.models import Job, Lesson, Profile, SceneImage
from app.schemas import (
    ImageGenerateRequest,
    ImageHideRequest,
    ImageHiddenOut,
    ImageReusedOut,
    ImageReuseRequest,
    ImageReuseSuggestedRequest,
    ImagesOverviewOut,
    ImagesReusedOut,
    ImageSlotOut,
    JobAccepted,
    LessonImagesOut,
    LessonImageSummaryOut,
    ReuseCandidateOut,
)
from app.services import audio_store, image_reuse, lesson_image, lesson_image_db
from app.workers.tasks import generate_lesson_images

router = APIRouter(tags=["lesson-images"])
_editor_or_admin = require_role("editor", "admin")

JOB_TYPE = "lesson_images"
_STALE_AFTER = timedelta(minutes=20)  # a run that has gone quiet this long is dead, not busy


async def _active_job(db: AsyncSession) -> Job | None:
    fresh = datetime.now(timezone.utc) - _STALE_AFTER
    return (
        await db.execute(
            select(Job)
            .where(Job.type == JOB_TYPE, Job.status.in_(["queued", "running"]), Job.updated_at > fresh)
            .order_by(Job.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()


def _lesson_of(job: Job | None) -> int | None:
    value = (job.result or {}).get("lesson_id") if job is not None else None
    return int(value) if isinstance(value, int) else None


async def _stored(db: AsyncSession, keys: list[str]) -> dict[str, Any]:
    """key -> (cache_key, hidden, created_at, model) of the pictures that exist. The bytes are
    left behind on purpose: the Studio lists hundreds of pictures and needs only their state."""
    if not keys:
        return {}
    rows = (
        await db.execute(
            select(SceneImage.cache_key, SceneImage.hidden, SceneImage.created_at, SceneImage.model).where(
                SceneImage.cache_key.in_(keys)
            )
        )
    ).all()
    return {row.cache_key: row for row in rows}


def _reuse_out(candidates: list[image_reuse.Candidate], stored: dict[str, Any]) -> list[ReuseCandidateOut]:
    return [
        ReuseCandidateOut(
            key=c.key,
            label=c.label,
            meaning=c.meaning,
            why=c.why,
            confident=c.confident,
            url=lesson_image_db.url_for(c.key, stored[c.key].created_at),
        )
        for c in candidates
    ]


@router.get("/lesson-images", response_model=ImagesOverviewOut)
async def images_overview(
    db: Annotated[AsyncSession, Depends(get_db)],
    _editor: Annotated[Profile, Depends(_editor_or_admin)],
):
    """Per lesson: how many pictures it wants, how many exist, how many are hidden."""
    groups = await lesson_image_db.lesson_slots_async(db, None, _LESSON_ORDER)
    stored = await _stored(db, [slot.key for g in groups for slot in g.slots])
    suggestions = image_reuse.suggest(groups, stored)
    lessons = [
        LessonImageSummaryOut(
            lesson_id=g.lesson_id,
            slug=g.slug,
            title=g.title,
            total=len(g.slots),
            have=sum(1 for s in g.slots if s.key in stored),
            hidden=sum(1 for s in g.slots if s.key in stored and stored[s.key].hidden),
            reusable=sum(1 for s in g.slots if s.key in suggestions),
        )
        for g in groups
        if g.slots
    ]
    active = await _active_job(db)
    distinct = {slot.key for g in groups for slot in g.slots}
    return ImagesOverviewOut(
        enabled=lesson_image.enabled(),
        model=(settings.GEMINI_MODEL_IMAGE or "").strip(),
        lessons=lessons,
        total=len(distinct),
        have=len(distinct & set(stored)),
        reusable=len(suggestions),
        reusable_sure=sum(1 for found in suggestions.values() if found[0].confident),
        active_job_id=active.id if active else None,
        active_lesson_id=_lesson_of(active),
    )


@router.get("/lessons/{lesson_id}/images", response_model=LessonImagesOut)
async def lesson_images(
    lesson_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _editor: Annotated[Profile, Depends(_editor_or_admin)],
):
    """Every picture one lesson wants, with its prompt and whether it exists."""
    groups = await lesson_image_db.lesson_slots_async(db, [lesson_id])
    if not groups:
        raise _problem(status.HTTP_404_NOT_FOUND, "Lesson not found", "not_found")
    group = groups[0]
    # what could fill a gap is looked for among the pictures of ALL lessons
    everyone = await lesson_image_db.lesson_slots_async(db, None, _LESSON_ORDER)
    stored = await _stored(db, list({s.key for g in (everyone + [group]) for s in g.slots}))
    suggestions = image_reuse.suggest(everyone, stored)
    slots = []
    for slot in group.slots:
        row = stored.get(slot.key)
        slots.append(
            ImageSlotOut(
                key=slot.key,
                kind=slot.kind,  # type: ignore[arg-type]
                label=slot.label,
                prompt=slot.prompt,
                meaning=slot.meaning,
                url=lesson_image_db.url_for(slot.key, row.created_at) if row is not None else None,
                hidden=bool(row.hidden) if row is not None else False,
                model=row.model if row is not None else None,
                reuse=_reuse_out(suggestions.get(slot.key, []), stored),
            )
        )
    active = await _active_job(db)
    return LessonImagesOut(
        lesson_id=lesson_id,
        title=group.title,
        enabled=lesson_image.enabled(),
        model=(settings.GEMINI_MODEL_IMAGE or "").strip(),
        total=len(slots),
        have=sum(1 for s in slots if s.url),
        hidden=sum(1 for s in slots if s.hidden),
        slots=slots,
        active_job_id=active.id if active else None,
    )


@router.post("/lesson-images", response_model=JobAccepted, status_code=status.HTTP_202_ACCEPTED)
async def start_drawing(
    body: ImageGenerateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    editor: Annotated[Profile, Depends(_editor_or_admin)],
):
    """Draw the pictures that are missing (of one lesson, or of all) in the background.
    One run at a time: pressing the button while a run is going returns that run. A picture
    already made is never drawn again unless `force` names it in `keys` (the "draw again"
    button) — a run costs real Gemini calls, so "everything again" is not offered."""
    if not lesson_image.enabled():
        raise _problem(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Lesson pictures are switched off",
            "images_disabled",
            "Bật LESSON_IMAGE_GEN_ENABLED và đặt GEMINI_MODEL_IMAGE trên dịch vụ API.",
        )
    if not settings.GEMINI_API_KEY:
        raise _problem(
            status.HTTP_503_SERVICE_UNAVAILABLE, "No Gemini key", "no_api_key", "Dịch vụ chưa có GEMINI_API_KEY."
        )
    if body.force and not body.keys:
        raise _problem(
            status.HTTP_400_BAD_REQUEST,
            "Name the pictures to draw again",
            "force_needs_keys",
            "Vẽ lại phải chỉ rõ ảnh nào (keys); không có chế độ vẽ lại tất cả.",
        )
    job = await _active_job(db)
    if job is None:
        lesson_ids = [body.lesson_id] if body.lesson_id is not None else None
        if body.lesson_id is not None and await db.get(Lesson, body.lesson_id) is None:
            raise _problem(status.HTTP_404_NOT_FOUND, "Lesson not found", "not_found")
        groups = await lesson_image_db.lesson_slots_async(db, lesson_ids, _LESSON_ORDER)
        stored = await _stored(db, [s.key for g in groups for s in g.slots])
        todo = lesson_image_db.pick_work(groups, set(stored), body.keys, body.force)
        if not todo:
            raise _problem(
                status.HTTP_409_CONFLICT,
                "Nothing to draw",
                "nothing_missing",
                "Mọi ảnh của phần này đã được vẽ.",
            )
        job = Job(
            type=JOB_TYPE,
            owner_id=editor.id,
            status="queued",
            result={"lesson_id": body.lesson_id, "total": len(todo)},
        )
        db.add(job)
        await db.commit()
        await db.refresh(job)
        generate_lesson_images.delay(str(job.id), body.lesson_id, body.keys, body.force)
    return JobAccepted(
        job_id=job.id,
        status=job.status,
        poll_url=f"/api/v1/jobs/{job.id}",
        events_url=f"/api/v1/jobs/{job.id}/events",
    )


@router.patch("/lesson-images/{key}", response_model=ImageHiddenOut)
async def hide_image(
    key: str,
    body: ImageHideRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    _editor: Annotated[Profile, Depends(_editor_or_admin)],
):
    """Take a picture off the lessons (it looks wrong), or put it back. Nothing is deleted,
    and a hidden picture is not drawn again by the next run."""
    row = await db.get(SceneImage, key)
    if row is None:
        raise _problem(status.HTTP_404_NOT_FOUND, "Picture not found", "not_found")
    row.hidden = body.hidden
    await db.commit()
    return ImageHiddenOut(key=key, hidden=row.hidden)


def _drawing_in_progress():
    return _problem(
        status.HTTP_409_CONFLICT,
        "A drawing run is going",
        "drawing_in_progress",
        "Đang vẽ ảnh — đợi lượt vẽ xong rồi hãy dùng lại ảnh có sẵn.",
    )


def _copy_of(source: SceneImage, slot: lesson_image.Slot) -> SceneImage:
    """The picture `source` filed under `slot`'s key, as if it had been drawn for it. Blocking (a
    picture kept in the bucket is read and written there): call it through run_in_threadpool."""
    data = audio_store.read_image(source)
    if not data:
        raise audio_store.StoreError("the source picture has no bytes")
    return SceneImage(
        cache_key=slot.key,
        mime_type=source.mime_type,
        **audio_store.file_image(slot.key, data, source.mime_type),
        prompt=slot.prompt,
        model=f"reuse:{source.model}"[:64],
        kind=slot.kind,
        hidden=False,
    )


async def _copy_in_thread(source: SceneImage, slot: lesson_image.Slot) -> SceneImage:
    try:
        return await run_in_threadpool(_copy_of, source, slot)
    except audio_store.StoreError:
        raise _problem(
            status.HTTP_503_SERVICE_UNAVAILABLE, "Picture storage unreachable", "storage_unavailable",
            "Không đọc/ghi được kho ảnh, thử lại sau.",
        ) from None


@router.post("/lesson-images/reuse", response_model=ImageReusedOut)
async def reuse_image(
    body: ImageReuseRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    _editor: Annotated[Profile, Depends(_editor_or_admin)],
):
    """Give a word that has no picture a copy of the picture of another word (no Gemini call,
    nothing paid). Only for word pictures, only for a word without one, and only while no
    drawing run is going (it might be drawing that very word). The copy is a picture of its own
    from then on: hiding or redrawing one does not touch the other."""
    if await _active_job(db) is not None:
        raise _drawing_in_progress()
    if body.from_key == body.to_key:
        raise _problem(status.HTTP_400_BAD_REQUEST, "Same picture", "same_picture")
    groups = await lesson_image_db.lesson_slots_async(db, None, _LESSON_ORDER)
    slots = {slot.key: slot for g in groups for slot in g.slots}
    target, origin = slots.get(body.to_key), slots.get(body.from_key)
    if target is None or target.kind != "vocab":
        raise _problem(status.HTTP_404_NOT_FOUND, "Word not found", "not_found", "Không có từ nào dùng ảnh này.")
    if origin is None or origin.kind != "vocab":
        raise _problem(status.HTTP_404_NOT_FOUND, "Picture not found", "not_found", "Ảnh nguồn không phải ảnh từ vựng.")
    if await db.get(SceneImage, body.to_key) is not None:
        raise _problem(
            status.HTTP_409_CONFLICT, "Already has a picture", "already_has_picture", "Từ này đã có ảnh."
        )
    source = await db.get(SceneImage, body.from_key)
    if source is None or source.hidden:
        raise _problem(
            status.HTTP_409_CONFLICT, "Nothing to reuse", "source_missing", "Ảnh nguồn chưa có hoặc đang bị ẩn."
        )
    row = await _copy_in_thread(source, target)
    db.add(row)
    try:
        await db.commit()
    except IntegrityError:  # two editors at once: the other one got there first
        await db.rollback()
        raise _problem(
            status.HTTP_409_CONFLICT, "Already has a picture", "already_has_picture", "Từ này vừa có ảnh."
        ) from None
    await db.refresh(row)
    return ImageReusedOut(
        to_key=body.to_key,
        from_key=body.from_key,
        label=target.label,
        url=lesson_image_db.url_for(body.to_key, row.created_at),
    )


@router.post("/lesson-images/reuse-suggested", response_model=ImagesReusedOut)
async def reuse_suggested(
    body: ImageReuseSuggestedRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    _editor: Annotated[Profile, Depends(_editor_or_admin)],
):
    """Fill every missing word picture (of one lesson, or of all) that has a SURE match — a
    word of exactly the same meaning, or its own noun/verb pair — with a copy of that picture.
    Doubtful matches are left for an editor to look at (the per-picture button)."""
    if await _active_job(db) is not None:
        raise _drawing_in_progress()
    groups = await lesson_image_db.lesson_slots_async(db, None, _LESSON_ORDER)
    if body.lesson_id is not None and not any(g.lesson_id == body.lesson_id for g in groups):
        raise _problem(status.HTTP_404_NOT_FOUND, "Lesson not found", "not_found")
    stored = await _stored(db, [slot.key for g in groups for slot in g.slots])
    suggestions = image_reuse.suggest(groups, stored)
    scope = [g for g in groups if body.lesson_id is None or g.lesson_id == body.lesson_id]
    targets: dict[str, lesson_image.Slot] = {}
    for g in scope:
        for slot in g.slots:
            if slot.key in suggestions and suggestions[slot.key][0].confident:
                targets.setdefault(slot.key, slot)
    if not targets:
        return ImagesReusedOut(reused=0, items=[])
    origin_keys = {suggestions[key][0].key for key in targets}
    origins = {
        row.cache_key: row
        for row in (await db.execute(select(SceneImage).where(SceneImage.cache_key.in_(origin_keys)))).scalars().all()
    }
    rows: list[tuple[SceneImage, str, lesson_image.Slot]] = []
    for key, slot in targets.items():
        origin = origins.get(suggestions[key][0].key)
        if origin is None or origin.hidden:
            continue
        copy = await _copy_in_thread(origin, slot)
        db.add(copy)
        rows.append((copy, origin.cache_key, slot))
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise _problem(
            status.HTTP_409_CONFLICT, "Pictures changed meanwhile", "already_has_picture", "Ảnh vừa thay đổi, thử lại."
        ) from None
    items = []
    for row, from_key, slot in rows:
        await db.refresh(row)
        items.append(
            ImageReusedOut(
                to_key=slot.key,
                from_key=from_key,
                label=slot.label,
                url=lesson_image_db.url_for(slot.key, row.created_at),
            )
        )
    return ImagesReusedOut(reused=len(items), items=items)

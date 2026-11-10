"""Job progress fan-out: Postgres `jobs` row is the source of truth;
Redis pub/sub is the live-push side channel the SSE endpoint reads from.
This is the direct replacement for the SDD's Celery+Redis SSE design —
same shape (job.progress / job.succeeded / job.failed events), different
transport (Redis pub/sub instead of an in-process broker sitting beside
FastAPI), because here the publisher (Celery worker) and the subscriber
(FastAPI SSE handler) are different Railway services/processes.
"""
import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.redis_client import job_channel, sync_redis
from app.models import Job


def public_error_message(raw: str) -> str:
    """What a learner may read of a failure. A database error carries the SQL statement and its
    parameters (a whole lesson script, sometimes): that stays in the worker's log, not on screen."""
    low = (raw or "").lower()
    if "diskfull" in low or "no space left" in low:
        return "Máy chủ hết dung lượng lưu trữ nên chưa lưu được âm thanh. Hãy báo quản trị viên."
    if "[sql:" in low or "psycopg2" in low or "sqlalchemy" in low:
        return "Lỗi cơ sở dữ liệu khi lưu. Hãy thử lại sau."
    return raw


def publish_job_event(db: Session, job_id: uuid.UUID, **fields: Any) -> None:
    """Call from a Celery task (sync context). Updates the `jobs` row AND
    publishes the same delta on `job:{id}:events` for anyone subscribed.
    """
    job = db.get(Job, job_id)
    if job is None:
        return
    error = fields.get("error")
    if isinstance(error, dict) and isinstance(error.get("message"), str):
        fields["error"] = {**error, "message": public_error_message(error["message"])}
    for key, value in fields.items():
        setattr(job, key, value)
    job.updated_at = datetime.now(timezone.utc)
    db.add(job)
    db.commit()

    event_type = {
        "succeeded": "job.succeeded",
        "failed": "job.failed",
    }.get(fields.get("status", ""), "job.progress")

    payload = {
        "job_id": str(job_id),
        "status": job.status,
        "progress": job.progress,
        "step": job.step,
        "result": job.result,
        "error": job.error,
    }
    sync_redis.publish(job_channel(str(job_id)), json.dumps({"event": event_type, "data": payload}))


# A worker refreshes `updated_at` with every step it publishes, so a job that is still queued or
# running but has not been touched for this long has lost its worker (a deploy or a crash killed the
# task and Celery does not redeliver it): it would otherwise show "running" for ever, and every later
# request would be handed the same dead job. A queued job may wait behind long ones, so it gets longer.
RUNNING_ABANDONED_AFTER = timedelta(minutes=8)
QUEUED_ABANDONED_AFTER = timedelta(minutes=20)


def abandoned(job: Any, now: datetime | None = None) -> bool:
    """True for a queued/running job whose worker is gone (see above); callers then delete it and queue a new one."""
    if getattr(job, "status", None) not in ("queued", "running"):
        return False
    updated = getattr(job, "updated_at", None)
    if not isinstance(updated, datetime):
        return False
    if updated.tzinfo is None:
        updated = updated.replace(tzinfo=timezone.utc)
    limit = QUEUED_ABANDONED_AFTER if job.status == "queued" else RUNNING_ABANDONED_AFTER
    return (now or datetime.now(timezone.utc)) - updated > limit


def acquire_job_lock(db: Session, job_type: str, idempotency_key: str, owner_id: uuid.UUID | None) -> Job | None:
    """Single-flight guard — the Postgres-table equivalent of a Redis
    SETNX lock (SDD §5, principle: "AI vừa đắt vừa chậm ... không tạo
    job trùng"). Returns the EXISTING job if one with the same
    (type, idempotency_key) is already queued/running, else None meaning
    "safe to create a new one". The unique constraint on
    (type, idempotency_key) in the DB is the actual race-proof guarantee;
    this lookup just gives a fast, friendly 200-with-existing-job path.
    """
    existing = db.execute(
        select(Job).where(
            Job.type == job_type,
            Job.idempotency_key == idempotency_key,
            Job.status.in_(["queued", "running"]),
        )
    ).scalar_one_or_none()
    return existing

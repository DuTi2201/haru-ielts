"""Celery app — the async-worker replacement the SDD calls for: every
Gemini call and every heavy transform (audio transcode, exam ingestion
pass 1-3, writing OCR+grading) runs here, never inline in a FastAPI
request handler.

Railway topology: the "api" service runs uvicorn (app.main:app); the
"worker" service runs this module (`celery -A app.core.celery_app worker`).
Both read the same REDIS_URL and DATABASE_URL, so they share the queue and
the `jobs` table.
"""
from celery import Celery
from celery.schedules import crontab
from celery.signals import worker_ready

from app.core.config import settings

celery_app = Celery(
    "haru",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    # Single-flight: a task id derived from a content hash (cache_key) is
    # rejected if already queued/running — see app/services/job_events.py
    # `acquire_job_lock`, the Postgres-table equivalent of a Redis lock.
    beat_schedule={
        "reset-daily-ai-quota": {
            "task": "app.workers.tasks.reset_daily_ai_quota",
            "schedule": 3600.0,  # hourly tick; task itself checks UTC midnight
        },
        "backup-database": {
            "task": "app.workers.tasks.backup_database",
            "schedule": crontab(hour=20, minute=0),  # 03:00 in Vietnam; see services/db_backup
        },
        "reconcile-billing-orders": {
            "task": "app.workers.tasks.reconcile_billing_orders",
            "schedule": 300.0,  # a no-op until billing is switched on
        },
        "discover-editorial-candidates": {
            "task": "app.workers.tasks.discover_editorial_candidates",
            "schedule": 6 * 3600.0,  # every 6h — RSS feeds don't need finer polling than that
        },
    },
)


@worker_ready.connect
def _offload_audio_when_worker_starts(**_kwargs):
    """With the bucket switched on, files still in Postgres are moved there each time the worker
    starts (a deploy, or after the variables were set; the task is idempotent), and the database is
    backed up too (a day's backup is simply written again), so a deploy never leaves the last copy
    older than the deploy."""
    from app.services import audio_store

    if audio_store.backend() == "gcs":
        celery_app.send_task("app.workers.tasks.offload_audio_to_gcs")
        celery_app.send_task("app.workers.tasks.backup_database")

"""One long voicing job at a time.

A lecture (or a lesson's story) is the one job that holds tens of megabytes while it runs: its
recording is built, encoded twice by ffmpeg and filed. The worker has 2 processes inside a 700 MB
container, so two of these at once, plus the web of small jobs beside them, is how it ran out of
memory and into swap. The short jobs (a word, a sentence) stay parallel; the long ones take turns
through a Redis lock. The lock expires on its own, so a job that dies holding it blocks nobody
for more than `hold_s`."""
from __future__ import annotations

import logging
from collections.abc import Callable, Iterator
from contextlib import contextmanager

from app.core.redis_client import sync_redis

log = logging.getLogger(__name__)

LOCK_NAME = "haru:lock:heavy-voicing"


@contextmanager
def heavy_voicing_slot(on_wait: Callable[[], None] | None = None, *, wait_s: int = 1800, hold_s: int = 3600) -> Iterator[None]:
    """Hold the slot while the body runs. If another long job has it, `on_wait()` is called once
    (to tell the learner) and this one waits up to `wait_s`. If Redis is not answering, or the wait
    runs out, the job goes ahead without the slot — a slow job is better than a refused one."""
    lock = None
    held = False
    try:
        lock = sync_redis.lock(LOCK_NAME, timeout=hold_s, blocking_timeout=wait_s)
        held = lock.acquire(blocking=False)
        if not held:
            if on_wait is not None:
                on_wait()
            held = lock.acquire(blocking=True)
            if not held:
                log.warning("[voicing] waited %ss for the heavy-job slot; going ahead without it", wait_s)
    except Exception as exc:  # noqa: BLE001 - Redis down / network: do the job, unserialised
        log.warning("[voicing] heavy-job slot unavailable (%s); going ahead without it", type(exc).__name__)
        held = False
    try:
        yield
    finally:
        if held and lock is not None:
            try:
                lock.release()
            except Exception:  # noqa: BLE001 - already expired, or Redis gone: nothing to do
                pass

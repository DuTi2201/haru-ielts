"""A spending guard for the public endpoints that start a paid generation (text-to-speech,
Gemini). Playing a recording that already exists costs nothing and is never counted; only a
request that would START a new generation spends from the allowance — per caller and, as a
backstop for callers that hide behind many addresses, over everyone together.

Counters live in Redis (one INCR per window). If Redis cannot be reached the request is let
through: a guard must not take listening down with it."""
from __future__ import annotations

import ipaddress
import logging

from fastapi import HTTPException, Request, status

from app.core.redis_client import async_redis

log = logging.getLogger(__name__)

WINDOW_SECONDS = 3600


def client_ip(request: Request) -> str:
    """The caller's address behind Railway's proxies: the last PUBLIC address in
    X-Forwarded-For (what our own proxy saw — anything a caller prepends sits before it),
    else the socket peer."""
    forwarded = request.headers.get("x-forwarded-for", "") or ""
    for part in reversed([p.strip() for p in forwarded.split(",") if p.strip()]):
        try:
            ip = ipaddress.ip_address(part)
        except ValueError:
            continue
        if ip.is_global:
            return str(ip)
    peer = getattr(request, "client", None)
    return peer.host if peer is not None and peer.host else "unknown"


async def _count(key: str) -> tuple[int, int]:
    """(uses so far in this window, seconds until it resets)."""
    pipe = async_redis.pipeline()
    pipe.incr(key)
    pipe.ttl(key)
    used, ttl = await pipe.execute()
    if ttl is None or ttl < 0:  # first use (or a key that lost its expiry): start the window
        await async_redis.expire(key, WINDOW_SECONDS)
        ttl = WINDOW_SECONDS
    return int(used), int(ttl)


async def spend(request: Request, scope: str, *, per_client: int, overall: int) -> None:
    """Count one new generation of kind `scope`; 429 when this caller, or everyone together,
    has used up the hour's allowance."""
    ip = client_ip(request)
    try:
        for key, limit, who in (
            (f"rl:{scope}:ip:{ip}", per_client, "client"),
            (f"rl:{scope}:all", overall, "all"),
        ):
            used, ttl = await _count(key)
            if used > limit:
                log.warning("rate limit: %s %s over %s/h (%s)", scope, who, limit, ip)
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail={
                        "type": "about:blank",
                        "title": "Too many new recordings",
                        "status": 429,
                        "code": "rate_limited",
                        "detail": "Bạn đang tạo quá nhiều audio mới trong một giờ — thử lại sau ít phút. "
                        "Audio đã có sẵn vẫn nghe bình thường.",
                    },
                    headers={"Retry-After": str(max(ttl, 1))},
                )
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001 - Redis down: allow
        log.warning("rate limit unavailable (%s): allowing", exc)

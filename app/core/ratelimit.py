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


# ------------------------------------------------------------------ sign-in guard
LOGIN_WINDOW_SECONDS = 900
LOGIN_PER_IP = 20
LOGIN_PER_EMAIL = 5


def _login_keys(request: Request, email: str) -> tuple[tuple[str, int], tuple[str, int]]:
    return (f"rl:login:ip:{client_ip(request)}", LOGIN_PER_IP), (f"rl:login:email:{email.strip().lower()}", LOGIN_PER_EMAIL)


def _too_many_logins(ttl: int) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail={
            "type": "about:blank",
            "title": "Thử đăng nhập quá nhiều lần",
            "status": 429,
            "code": "login_rate_limited",
            "detail": "Vui lòng đợi khoảng 15 phút rồi thử lại.",
        },
        headers={"Retry-After": str(max(ttl, 1))},
    )


async def login_check(request: Request, email: str) -> None:
    """Before a password is checked: refuse when this address or this account has already failed
    too often in the last 15 minutes. Unlike `spend`, this guard fails CLOSED: with Redis down
    nobody signs in, because an unguarded sign-in is the one door to the whole app."""
    try:
        for key, limit in _login_keys(request, email):
            used = await async_redis.get(key)
            if used is not None and int(used) >= limit:
                ttl = await async_redis.ttl(key)
                log.warning("sign-in refused: %s at its limit", key.split(":")[2])
                raise _too_many_logins(int(ttl or LOGIN_WINDOW_SECONDS))
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        log.error("sign-in guard unavailable (%s): refusing", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"type": "about:blank", "title": "Tạm thời chưa đăng nhập được", "status": 503, "code": "guard_unavailable"},
        ) from None


async def login_failed(request: Request, email: str) -> None:
    """Count one wrong password against the address and against the account."""
    try:
        for key, _ in _login_keys(request, email):
            if await async_redis.incr(key) == 1:
                await async_redis.expire(key, LOGIN_WINDOW_SECONDS)
    except Exception as exc:  # noqa: BLE001 - the next login_check refuses if Redis is still down
        log.error("sign-in guard could not count a failure (%s)", exc)


async def login_succeeded(request: Request, email: str) -> None:
    """The right password clears the account's count (the address keeps its own)."""
    try:
        await async_redis.delete(f"rl:login:email:{email.strip().lower()}")
    except Exception:  # noqa: BLE001
        pass


async def refresh_token_unused(jti: str, ttl_seconds: int) -> bool:
    """True the first time a refresh token's id is seen, False when it was already redeemed.
    With Redis down the token is accepted (it is still signed, unexpired and tied to the account)."""
    try:
        return bool(await async_redis.set(f"rt:used:{jti}", "1", nx=True, ex=max(int(ttl_seconds), 1)))
    except Exception as exc:  # noqa: BLE001
        log.warning("refresh-token registry unavailable (%s): accepting", exc)
        return True

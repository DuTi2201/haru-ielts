"""Keeping the free trial to one per person.

The trial of the AI speaking features is per account, and an account costs nothing, so the guard
sits on what a second account cannot change as easily:

  the browser   the app keeps a random id in the browser and sends it as X-Haru-Device; a browser
                whose trial was used by one account does not give it to another
  the network   a soft cap on accounts made, and on new trials started, from one IP in 24 hours
                (soft, because a dorm or a mobile carrier puts many people behind one address)
  the inbox     throwaway-mail domains are refused, and "an.nguyen+2@gmail.com" is the same inbox
                as "annguyen@gmail.com"
  the budget    a cap on the trial minutes (and presentation tries) the whole system gives away in
                a day, and a switch that pauses the trial for everyone

Browser ids and IPs are stored only as a keyed hash: enough to see that two accounts share one,
never the address itself. Admins see the accounts that share them (routers/admin_abuse.py).

The numbers are admin settings (billing.setting), read with the rest by settings_db.refresh.
"""
from __future__ import annotations

import hashlib
import hmac
import ipaddress
import logging
import re
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, Request, status
from sqlalchemy import and_, distinct, func, or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.ratelimit import client_ip
from app.models import AccountSignal, BlockedEmailDomain, Profile, TrialUse

log = logging.getLogger(__name__)

DEVICE_HEADER = "x-haru-device"
_DEVICE_RE = re.compile(r"^[A-Za-z0-9_-]{8,64}$")
VN = timezone(timedelta(hours=7))  # the day the budget counts in (Vietnam keeps no summer time)
LIVE = ("talk", "debate")

# admin settings: (default, low, high)
GUARD: dict[str, tuple[int, int, int]] = {
    "trial_enabled": (1, 0, 1),  # 0 pauses the trial for everyone
    "trial_daily_minutes": (600, 0, 100_000),  # live trial minutes for the whole system a day; 0 = no cap
    "trial_daily_present_tries": (300, 0, 100_000),  # marked presentation tries a day; 0 = no cap
    "trial_accounts_per_device": (1, 1, 10),  # accounts that may use the trial from one browser
    "trial_accounts_per_ip_daily": (3, 1, 1000),  # new trial accounts from one network in 24 h
    "signup_per_ip_daily": (5, 1, 1000),  # accounts made from one network in 24 h
}
_guard: dict[str, int] = {k: v[0] for k, v in GUARD.items()}


def apply(numbers: dict[str, int]) -> None:
    out = {k: v[0] for k, v in GUARD.items()}
    for key, value in numbers.items():
        if key in GUARD and isinstance(value, int) and GUARD[key][1] <= value <= GUARD[key][2]:
            out[key] = value
    global _guard
    _guard = out


def guard() -> dict[str, int]:
    return dict(_guard)


# ------------------------------------------------------------- identities --
def _hash(kind: str, value: str) -> str:
    return hmac.new(settings.JWT_SECRET.encode(), f"{kind}:{value}".encode(), hashlib.sha256).hexdigest()[:32]


def device_of(request: Request | None) -> str | None:
    """The hashed browser id the app sent, or None (missing or malformed)."""
    if request is None:
        return None
    raw = (request.headers.get(DEVICE_HEADER) or "").strip()
    return _hash("device", raw) if _DEVICE_RE.match(raw) else None


def ip_of(request: Request | None) -> str | None:
    """The hashed public address of the caller, or None when there is none to go by (a private or
    local peer with no forwarded address: counting those would put every learner in one bucket)."""
    if request is None:
        return None
    ip = client_ip(request)
    try:
        if not ipaddress.ip_address(ip).is_global:
            return None
    except ValueError:
        return None
    return _hash("ip", ip)


def email_key(email: str) -> str:
    """The address as its inbox sees it: lower case, without "+tag", and for Gmail without dots."""
    local, _, domain = (email or "").strip().lower().rpartition("@")
    if not local:
        return (email or "").strip().lower()
    local = local.split("+", 1)[0] or local
    if domain in ("gmail.com", "googlemail.com"):
        local, domain = local.replace(".", ""), "gmail.com"
    return f"{local}@{domain}"


# big mail providers real learners use: never blocked, whatever a list says
PROTECTED_DOMAINS = frozenset(
    {
        "gmail.com", "googlemail.com", "outlook.com", "hotmail.com", "live.com", "msn.com", "yahoo.com",
        "yahoo.com.vn", "icloud.com", "me.com", "proton.me", "protonmail.com", "naver.com", "daum.net",
        "kakao.com", "zoho.com", "fpt.com.vn", "fpt.edu.vn", "vnu.edu.vn", "hust.edu.vn",
    }
)


def _bundled() -> frozenset[str]:
    try:
        from disposable_email_domains import blocklist
    except ImportError:  # the list is a dependency; without it only the admin's own domains count
        log.warning("[abuse] disposable_email_domains is not installed")
        return frozenset()
    return frozenset(blocklist) - PROTECTED_DOMAINS


_BUNDLED = _bundled()


def _suffixes(domain: str) -> list[str]:
    parts = domain.strip().lower().rstrip(".").split(".")
    return [".".join(parts[i:]) for i in range(len(parts) - 1)]


def normalize_domain(domain: str) -> str | None:
    d = (domain or "").strip().lower().lstrip("@").rstrip(".")
    return d if re.match(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)+$", d) and len(d) <= 253 else None


async def is_throwaway(db: AsyncSession, email: str) -> bool:
    domain = email.rpartition("@")[2].lower()
    names = _suffixes(domain)
    if domain in PROTECTED_DOMAINS:
        return False
    if any(n in _BUNDLED for n in names):
        return True
    if not names:
        return False
    hit = await db.execute(select(BlockedEmailDomain.domain).where(BlockedEmailDomain.domain.in_(names)).limit(1))
    return hit.first() is not None


# ---------------------------------------------------------------- traces --
async def remember(db: AsyncSession, profile_id: uuid.UUID, request: Request | None) -> None:
    """Note the browser and network this account was just seen from (not committed here). A
    failure never stops the sign-in: it runs in a savepoint and is logged."""
    pairs = [(k, v) for k, v in (("device", device_of(request)), ("ip", ip_of(request))) if v]
    if not pairs:
        return
    now = datetime.now(timezone.utc)
    try:
        async with db.begin_nested():
            for kind, value in pairs:
                stmt = pg_insert(AccountSignal).values(
                    profile_id=profile_id, kind=kind, value=value, first_seen=now, last_seen=now, seen_count=1
                )
                await db.execute(
                    stmt.on_conflict_do_update(
                        constraint="uq_billing_account_signal",
                        set_={"last_seen": now, "seen_count": AccountSignal.seen_count + 1},
                    )
                )
    except Exception as exc:  # pragma: no cover - a trace is never worth a failed sign-in
        log.warning("[abuse] could not record a trace: %s", exc.__class__.__name__)


def _problem(code: int, title: str, kind: str, detail: str | None = None) -> HTTPException:
    body = {"type": "about:blank", "title": title, "status": code, "code": kind}
    if detail:
        body["detail"] = detail
    return HTTPException(status_code=code, detail=body)


async def check_signup(db: AsyncSession, email: str, request: Request | None) -> str:
    """Refuse a throwaway inbox, a second account on one inbox, or too many accounts from one
    network today. Returns the email key to store."""
    key = email_key(email)
    if await is_throwaway(db, email):
        raise _problem(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Không dùng được email tạm thời",
            "disposable_email",
            "Hãy đăng ký bằng email thật của bạn (Gmail, Outlook, email trường/công ty…).",
        )
    taken = await db.execute(select(Profile.id).where(Profile.email_key == key).limit(1))
    if taken.first() is not None:
        raise _problem(status.HTTP_409_CONFLICT, "Email already registered", "email_taken")
    ip = ip_of(request)
    if ip:
        since = datetime.now(timezone.utc) - timedelta(hours=24)
        made = await db.scalar(
            select(func.count(distinct(Profile.id)))
            .join(AccountSignal, AccountSignal.profile_id == Profile.id)
            .where(AccountSignal.kind == "ip", AccountSignal.value == ip, Profile.created_at >= since)
        )
        if int(made or 0) >= _guard["signup_per_ip_daily"]:
            log.info("[abuse] signup refused: %s accounts from one network today", made)
            raise _problem(
                status.HTTP_429_TOO_MANY_REQUESTS,
                "Mạng này đã tạo nhiều tài khoản hôm nay",
                "too_many_signups",
                "Thử lại sau 24 giờ, hoặc nhắn hỗ trợ nếu cả lớp/nhóm của bạn cùng đăng ký.",
            )
    return key


# ----------------------------------------------------------------- trial --
def day_start(now: datetime | None = None) -> datetime:
    local = (now or datetime.now(timezone.utc)).astimezone(VN)
    return local.replace(hour=0, minute=0, second=0, microsecond=0)


async def used_today(db: AsyncSession, now: datetime | None = None) -> tuple[int, int]:
    """(live trial seconds granted, presentation trial tries) since midnight, Vietnam time."""
    since = day_start(now)
    rows = (
        await db.execute(
            select(TrialUse.feature, func.coalesce(func.sum(TrialUse.amount), 0))
            .where(TrialUse.created_at >= since)
            .group_by(TrialUse.feature)
        )
    ).all()
    live = sum(int(n) for f, n in rows if f in LIVE)
    present = sum(int(n) for f, n in rows if f == "present")
    return live, present


async def _first_claim(db: AsyncSession, profile_id: uuid.UUID) -> bool:
    hit = await db.execute(select(TrialUse.id).where(TrialUse.profile_id == profile_id).limit(1))
    return hit.first() is None


async def _others_on_device(db: AsyncSession, profile_id: uuid.UUID, device: str) -> int:
    """Other accounts that used the trial on this browser, or were seen on it and used it anywhere."""
    seen_here = select(AccountSignal.profile_id).where(AccountSignal.kind == "device", AccountSignal.value == device)
    q = select(func.count(distinct(TrialUse.profile_id))).where(
        TrialUse.profile_id != profile_id,
        or_(TrialUse.device == device, TrialUse.profile_id.in_(seen_here)),
    )
    return int(await db.scalar(q) or 0)


async def _others_on_ip(db: AsyncSession, profile_id: uuid.UUID, ip: str) -> int:
    since = datetime.now(timezone.utc) - timedelta(hours=24)
    first_use = (
        select(TrialUse.profile_id, func.min(TrialUse.created_at).label("first"))
        .group_by(TrialUse.profile_id)
        .subquery()
    )
    q = (
        select(func.count(distinct(TrialUse.profile_id)))
        .join(first_use, and_(first_use.c.profile_id == TrialUse.profile_id, first_use.c.first == TrialUse.created_at))
        .where(TrialUse.ip == ip, TrialUse.created_at >= since, TrialUse.profile_id != profile_id)
    )
    return int(await db.scalar(q) or 0)


def _refuse(feature: str, detail: str, reason: str) -> HTTPException:
    from app.api.deps import payment_required  # late: deps imports this module
    from app.services.billing import catalog

    exc = payment_required(catalog.FEATURE_PASS, detail, catalog.feature_passes(feature))
    exc.detail["reason"] = reason  # type: ignore[index]
    return exc


async def gate_trial(
    db: AsyncSession, profile: Profile, feature: str, request: Request | None, amount: int
) -> int:
    """Let one start on the free trial through, or refuse it (402, with a `reason`). `amount` is the
    live seconds left of the account's trial, or 1 for a presentation try. Returns what is granted
    (the seconds may be cut to what is left of the day's budget) and adds the TrialUse row; the
    caller's commit keeps it, so a start that fails later is not counted."""
    g = _guard
    if not g["trial_enabled"]:
        raise _refuse(
            feature, "Dùng thử miễn phí đang tạm dừng. Bạn vẫn có thể mở gói Haru Nói để luyện ngay.", "trial_paused"
        )
    live_today, present_today = await used_today(db)
    if feature in LIVE:
        cap = g["trial_daily_minutes"] * 60
        if cap:
            amount = min(amount, cap - live_today)
            if amount < 60:
                raise _refuse(
                    feature,
                    "Lượt dùng thử miễn phí của hôm nay đã hết. Quay lại vào ngày mai, hoặc mở gói Haru Nói để luyện ngay.",
                    "trial_budget",
                )
    elif g["trial_daily_present_tries"] and present_today >= g["trial_daily_present_tries"]:
        raise _refuse(
            feature,
            "Lượt chấm thử miễn phí của hôm nay đã hết. Quay lại vào ngày mai, hoặc mở gói Haru Nói để luyện ngay.",
            "trial_budget",
        )

    device, ip = device_of(request), ip_of(request)
    if request is not None and await _first_claim(db, profile.id):
        # only an account's FIRST trial start is checked against the browser and the network: one
        # who has started already keeps their remaining minutes wherever they are
        if device is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "type": "about:blank",
                    "title": "Không nhận ra trình duyệt",
                    "status": 400,
                    "code": "device_missing",
                    "detail": "Tải lại trang rồi thử lại nhé. Nếu vẫn lỗi, tắt chế độ chặn lưu trữ của trình duyệt.",
                },
            )
        if await _others_on_device(db, profile.id, device) >= g["trial_accounts_per_device"]:
            log.info("[abuse] %s: trial refused, browser already used by another account", profile.id)
            raise _refuse(
                feature,
                "Trình duyệt này đã dùng thử Haru Nói bằng một tài khoản khác. Mỗi người được dùng thử một lần; "
                "mở gói Haru Nói để luyện tiếp nhé.",
                "trial_device",
            )
        if ip and await _others_on_ip(db, profile.id, ip) >= g["trial_accounts_per_ip_daily"]:
            log.info("[abuse] %s: trial refused, too many new trials from one network", profile.id)
            raise _refuse(
                feature,
                "Mạng bạn đang dùng đã có nhiều tài khoản dùng thử hôm nay. Thử lại sau, hoặc mở gói Haru Nói để luyện ngay.",
                "trial_network",
            )
    db.add(TrialUse(profile_id=profile.id, feature=feature, amount=amount, device=device, ip=ip))
    await remember(db, profile.id, request)
    return amount

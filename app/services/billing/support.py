"""Where a learner gets help: the channels an admin lists (email, phone, Zalo, Telegram, Messenger,
Facebook) with the hours and a short note, kept in billing.site_setting["support"].

Each channel is stored as the admin typed it and turned into a link here, once, so every screen
opens the same thing: an email becomes mailto:, a phone tel:, a Zalo number zalo.me/<number>,
a Telegram name t.me/<name>. A value that cannot be made into a safe link is refused when saved.

Before an admin saves anything, the server's BILLING_SUPPORT_URL (and MERCHANT_EMAIL / PHONE) are
used, the same way: an address there becomes mailto:, not a page of the app.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from app.core.config import settings

CHANNELS: tuple[str, ...] = ("zalo", "telegram", "messenger", "facebook", "email", "phone")
TEXTS: tuple[str, ...] = ("hours", "note")
LABEL = {
    "zalo": "Zalo",
    "telegram": "Telegram",
    "messenger": "Messenger",
    "facebook": "Facebook",
    "email": "Email",
    "phone": "Điện thoại",
}

_EMAIL = re.compile(r"^[^@\s<>\"']+@[^@\s<>\"']+\.[A-Za-z]{2,}$")
_HANDLE = re.compile(r"^@?([A-Za-z0-9_.]{3,64})$")
_HOSTS = {
    "zalo": ("zalo.me", "chat.zalo.me", "oa.zalo.me"),
    "telegram": ("t.me", "telegram.me"),
    "messenger": ("m.me", "messenger.com", "www.messenger.com"),
    "facebook": ("facebook.com", "www.facebook.com", "fb.com", "m.facebook.com", "fb.me"),
}

_saved: dict[str, str] = {}


class SupportError(ValueError):
    def __init__(self, field: str, message: str):
        super().__init__(message)
        self.field = field


def _digits(text: str) -> str:
    return re.sub(r"\D", "", text)


def _https(value: str, channel: str) -> str | None:
    m = re.match(r"^https://([^/\s?#]+)([^\s]*)$", value)
    if not m:
        return None
    host = m.group(1).lower()
    return value if host in _HOSTS.get(channel, ()) else None


def link_of(channel: str, value: str) -> str | None:
    """The link a channel's value opens, or None when it cannot be made into a safe one."""
    v = (value or "").strip()
    if not v:
        return None
    if channel == "email":
        v = v.removeprefix("mailto:")
        return f"mailto:{v}" if _EMAIL.match(v) else None
    if channel == "phone":
        d = _digits(v)
        if not 8 <= len(d) <= 15:
            return None
        return f"tel:+{d}" if v.startswith("+") else f"tel:{d}"
    if channel == "zalo":
        d = _digits(v)
        if v.replace(" ", "").replace(".", "").replace("+", "").isdigit() and 8 <= len(d) <= 15:
            if d.startswith("84") and len(d) > 10:
                d = "0" + d[2:]
            return f"https://zalo.me/{d}"
        return _https(v, "zalo")
    if channel in ("telegram", "messenger", "facebook"):
        if v.startswith("https://"):
            return _https(v, channel)
        m = _HANDLE.match(v)
        if not m:
            return None
        base = {"telegram": "https://t.me/", "messenger": "https://m.me/", "facebook": "https://facebook.com/"}[channel]
        return base + m.group(1)
    return None


def clean(values: dict[str, Any]) -> dict[str, str]:
    """What an admin sent, checked: every channel must make a link; texts are trimmed."""
    out: dict[str, str] = {}
    for channel in CHANNELS:
        v = str(values.get(channel) or "").strip()
        if not v:
            continue
        if len(v) > 200 or link_of(channel, v) is None:
            raise SupportError(channel, f"{LABEL[channel]} chưa đúng dạng.")
        out[channel] = v
    for key in TEXTS:
        v = str(values.get(key) or "").strip()
        if v:
            out[key] = v[:300]
    return out


def apply(value: dict[str, Any] | None) -> None:
    """What is saved in the database (settings_db.refresh); a value that no longer checks out is dropped."""
    global _saved
    kept: dict[str, str] = {}
    for key, v in (value or {}).items():
        if key in CHANNELS and isinstance(v, str) and link_of(key, v):
            kept[key] = v
        elif key in TEXTS and isinstance(v, str):
            kept[key] = v
    _saved = kept


def _from_env() -> dict[str, str]:
    """Before an admin saves anything: the server's own settings."""
    out: dict[str, str] = {}
    url = (settings.BILLING_SUPPORT_URL or "").strip()
    if url:
        if link_of("email", url):
            out["email"] = url.removeprefix("mailto:")
        else:
            for channel in ("zalo", "telegram", "messenger", "facebook"):
                if link_of(channel, url):
                    out[channel] = url
                    break
    if settings.MERCHANT_EMAIL and "email" not in out and link_of("email", settings.MERCHANT_EMAIL):
        out["email"] = settings.MERCHANT_EMAIL
    if settings.MERCHANT_PHONE and link_of("phone", settings.MERCHANT_PHONE):
        out["phone"] = settings.MERCHANT_PHONE
    return out


def saved() -> dict[str, str]:
    return dict(_saved)


def current() -> dict[str, str]:
    """The channels shown to learners: the admin's, or the server's settings when none is saved."""
    return dict(_saved) if any(k in _saved for k in CHANNELS) else {**_from_env(), **{k: v for k, v in _saved.items() if k in TEXTS}}


@dataclass(frozen=True)
class Link:
    kind: str
    label: str
    value: str
    url: str


def links() -> list[Link]:
    c = current()
    out = []
    for channel in CHANNELS:
        if channel in c:
            url = link_of(channel, c[channel])
            if url:
                out.append(Link(kind=channel, label=LABEL[channel], value=c[channel], url=url))
    return out


def primary_url() -> str | None:
    """One link for the places that have room for a single button (a chat first, then email)."""
    found = links()
    return found[0].url if found else None

"""Who runs Haru (Thông tin vận hành): the name, tax code, address, email and phone shown in the
footer, on /contact and in /terms. An admin edits them once on the admin overview and every page
reads the same value (billing.site_setting["merchant"]); a field left empty falls back to the
server's MERCHANT_* setting."""
from __future__ import annotations

import re
from typing import Any

from app.core.config import settings

FIELDS: tuple[str, ...] = ("name", "tax_id", "address", "email", "phone")
LIMIT = {"name": 120, "tax_id": 20, "address": 200, "email": 120, "phone": 20}
LABEL = {"name": "Tên đơn vị", "tax_id": "Mã số thuế", "address": "Địa chỉ", "email": "Email", "phone": "Điện thoại"}

_EMAIL = re.compile(r"^[^@\s<>\"']+@[^@\s<>\"']+\.[A-Za-z]{2,}$")
_PHONE = re.compile(r"^\+?[0-9 .()-]{8,20}$")
_TAX = re.compile(r"^[0-9]{10}(-[0-9]{3})?$")

_saved: dict[str, str] = {}


class MerchantError(ValueError):
    def __init__(self, field: str, message: str):
        super().__init__(message)
        self.field = field


def clean(values: dict[str, Any]) -> dict[str, str]:
    """What an admin sent, checked; empty fields are left out (the server's setting shows)."""
    out: dict[str, str] = {}
    for key in FIELDS:
        v = " ".join(str(values.get(key) or "").split())
        if not v:
            continue
        if len(v) > LIMIT[key]:
            raise MerchantError(key, f"{LABEL[key]} dài quá {LIMIT[key]} ký tự.")
        if key == "email" and not _EMAIL.match(v):
            raise MerchantError(key, "Email chưa đúng dạng.")
        if key == "phone" and not _PHONE.match(v):
            raise MerchantError(key, "Số điện thoại chưa đúng dạng.")
        if key == "tax_id" and not _TAX.match(v):
            raise MerchantError(key, "Mã số thuế gồm 10 chữ số (có thể thêm -xxx).")
        out[key] = v
    return out


def apply(value: dict[str, Any] | None) -> None:
    """What is saved in the database (settings_db.refresh)."""
    global _saved
    _saved = {k: v for k, v in (value or {}).items() if k in FIELDS and isinstance(v, str) and v.strip()}


def saved() -> dict[str, str]:
    return dict(_saved)


def current() -> dict[str, str | None]:
    """What every page shows: the admin's value, else the server's MERCHANT_* setting."""
    env = {
        "name": settings.MERCHANT_NAME,
        "tax_id": settings.MERCHANT_TAX_ID,
        "address": settings.MERCHANT_ADDRESS,
        "email": settings.MERCHANT_EMAIL,
        "phone": settings.MERCHANT_PHONE,
    }
    return {k: _saved.get(k) or (env[k] or None) for k in FIELDS}

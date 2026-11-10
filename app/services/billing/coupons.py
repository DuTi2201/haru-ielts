"""Discount codes. The price an order is made at is decided here, on the server:
  total = list price - discount, never below MIN_TOTAL (payOS needs an amount, and a 100% code
  would be a gift: an admin grants it by hand instead).
A code can be a percentage (1-90%) or a fixed amount, for every product or a list, with a start,
an end, a use limit (counted on PAID orders, pending ones hold a place) and once per learner.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from app.services.billing import catalog

MIN_TOTAL = 2_000
CODE_RE = re.compile(r"^[A-Z0-9_-]{3,32}$")


def normalize(code: str | None) -> str:
    return re.sub(r"\s+", "", code or "").upper()


@dataclass(frozen=True)
class Quote:
    list_amount: int
    discount: int
    total: int
    coupon_code: str | None = None
    coupon_label_vi: str | None = None
    credit: int = 0  # what the learner already paid for smaller packs inside this one (orders.upgrade_credit)


def label_vi(c: Any) -> str:
    if c.percent_off:
        return f"Giảm {c.percent_off}%"
    return f"Giảm {c.amount_off:,}đ".replace(",", ".")


def check(c: Any, product: catalog.Product, now: datetime) -> str | None:
    """Why this code cannot be used for this product now (None = it can). Counting uses is the
    caller's job (it needs the database)."""
    if c is None or not c.active:
        return "Mã giảm giá không đúng hoặc đã ngừng."
    if c.starts_at and now < c.starts_at:
        return "Mã giảm giá chưa đến ngày dùng."
    if c.ends_at and now >= c.ends_at:
        return "Mã giảm giá đã hết hạn."
    if c.product_codes and product.code not in c.product_codes:
        return "Mã giảm giá không áp dụng cho gói này."
    return None


def price(product: catalog.Product, c: Any | None, credit: int = 0) -> Quote:
    """The code's discount first, then the upgrade credit; the total never goes under MIN_TOTAL."""
    base = product.amount
    off = 0
    if c is not None:
        off = base * c.percent_off // 100 if c.percent_off else int(c.amount_off or 0)
        off = max(0, min(off, base - MIN_TOTAL))
        # payOS amounts are whole VND; round the discount down to the thousand so totals look clean
        off -= off % 1000
    cr = max(0, min(credit, base - off - MIN_TOTAL))
    cr -= cr % 1000
    total = base - off - cr
    if c is None:
        return Quote(base, 0, total, credit=cr)
    return Quote(base, off, total, c.code, label_vi(c), cr)

"""Loads the admin's billing settings (prices, feature rules) into the in-process catalogue.

Every API process and worker keeps its own copy; it is read again at most every `TTL` seconds,
and at once on the paths where a stale price would matter (making an order, the quote) and after
an admin changes something. A failure to read keeps what is loaded (the defaults at worst)."""
from __future__ import annotations

import logging
import time

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import BillingSetting, FeatureRule, ProductSetting, SiteSetting
from app.services import abuse
from app.services.billing import catalog, features, merchant, support

log = logging.getLogger(__name__)
TTL = 30.0
_loaded_at = 0.0


async def refresh(db: AsyncSession, *, force: bool = False) -> None:
    global _loaded_at
    now = time.monotonic()
    if not force and now - _loaded_at < TTL:
        return
    try:
        prices = (await db.execute(select(ProductSetting))).scalars().all()
        rules = (await db.execute(select(FeatureRule))).scalars().all()
        numbers = (await db.execute(select(BillingSetting))).scalars().all()
        help_row = await db.get(SiteSetting, "support")
        merchant_row = await db.get(SiteSetting, "merchant")
    except Exception as exc:  # keep serving with what is loaded
        log.warning("[billing] could not read the billing settings: %s", exc.__class__.__name__)
        return
    catalog.apply_settings(
        {
            r.product_code: {k: getattr(r, k) for k in catalog.EDITABLE if getattr(r, k) is not None}
            for r in prices
        }
    )
    numbers_by_key = {n.key: int(n.value) for n in numbers}
    features.apply_rules({r.feature: r.mode for r in rules}, numbers_by_key)
    abuse.apply(numbers_by_key)
    support.apply(help_row.value if help_row is not None else None)
    merchant.apply(merchant_row.value if merchant_row is not None else None)
    _loaded_at = now


def forget() -> None:
    """The next refresh reads the database (tests, and after an admin's change elsewhere)."""
    global _loaded_at
    _loaded_at = 0.0

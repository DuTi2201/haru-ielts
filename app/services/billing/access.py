"""Who may open what. `Access` is built from a learner's entitlement rows; with billing off
(settings.BILLING_ENABLED false) it is simply "everything", so nothing changes for anyone."""
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import Entitlement, Profile
from app.services.billing import catalog

STAFF_ROLES = ("admin", "editor")


@dataclass(frozen=True)
class Access:
    enforced: bool = True
    everything: bool = False  # staff, an "all" grant (also the grandfathered accounts)
    packs: frozenset[str] = frozenset()  # lesson-pack product codes held
    exam_pass: bool = False
    exam_pass_until: datetime | None = None  # None with exam_pass True = no end
    features: frozenset[str] = frozenset()  # opened by a feature pass (catalog.FEATURES)
    features_until: datetime | None = None  # the latest end of those passes (None = no end)

    def can_open(self, sort_order: int | None) -> bool:
        if not self.enforced or self.everything or catalog.is_free(sort_order):
            return True
        return any((p := catalog.get(code)) is not None and p.covers(sort_order) for code in self.packs)

    def can_use_exam_pass(self) -> bool:
        return not self.enforced or self.everything or self.exam_pass

    def has_feature(self, feature: str) -> bool:
        """Unlimited use of a feature (a pass that opens it, staff, an "all" grant, billing off).
        Without it a learner still has the free daily allowance (billing.features)."""
        return not self.enforced or self.everything or feature in self.features

    def owns(self, product: catalog.Product) -> bool:
        """Nothing left to buy in this product (a pass can always be bought again: it extends)."""
        if product.kind != catalog.LESSON_PACK:
            return False
        if not self.enforced or self.everything:
            return True
        return all(self.can_open(n) for lo, hi in product.lessons for n in range(lo, hi + 1))

    def label_for(self, sort_order: int | None) -> str:
        """The `access` a lesson row shows: free for all, owned (bought or granted), locked."""
        if catalog.is_free(sort_order) or not self.enforced:
            return "free"
        return "owned" if self.can_open(sort_order) else "locked"


OPEN = Access(enforced=False, everything=True)
STAFF = Access(enforced=True, everything=True)
ANONYMOUS = Access()


def build_access(rows: Iterable[Entitlement], now: datetime) -> Access:
    everything = False
    packs: set[str] = set()
    has_pass = False
    until: datetime | None = None
    unlimited = False
    features: set[str] = set()
    f_until: datetime | None = None
    f_unlimited = False
    for r in rows:
        if r.revoked_at is not None or (r.starts_at and r.starts_at > now) or (r.ends_at is not None and r.ends_at <= now):
            continue
        if r.product_code == catalog.ALL:
            everything = True
            continue
        product = catalog.get(r.product_code)
        if product is None:
            continue
        if product.kind == catalog.LESSON_PACK:
            packs.add(product.code)
        elif product.kind == catalog.FEATURE_PASS:
            features.update(product.features)
            if r.ends_at is None:
                f_unlimited = True
            elif f_until is None or r.ends_at > f_until:
                f_until = r.ends_at
        else:
            has_pass = True
            if r.ends_at is None:
                unlimited = True
            elif until is None or r.ends_at > until:
                until = r.ends_at
    return Access(
        everything=everything,
        packs=frozenset(packs),
        exam_pass=has_pass,
        exam_pass_until=None if unlimited else until,
        features=frozenset(features),
        features_until=None if f_unlimited else f_until,
    )


async def load_access(db: AsyncSession, profile: Profile | None) -> Access:
    if not settings.BILLING_ENABLED:
        return OPEN
    if profile is None:
        return ANONYMOUS
    if profile.role in STAFF_ROLES:
        return STAFF
    rows = (await db.execute(select(Entitlement).where(Entitlement.profile_id == profile.id))).scalars().all()
    return build_access(rows, datetime.now(timezone.utc))

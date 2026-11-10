"""Hành trình Thiên Nga: the learner's journey as a swan, from the black swan lost in a tower of
thorns (stage 1) to the crowned white swan (stage 5).

Two numbers decide what the learner sees (frontend: components/journey):

  stage        earned by the chapters finished (app/services/feathers.py: every lesson is cut into
               feathers, the main lessons are gathered into chapters I–IV; finishing chapter n
               gives stage n + 1). It only goes up and is kept in `journey`, so a bad week, or
               lessons added to a chapter later, never take an earned stage away.
  missed_days  full days without studying before today (Vietnam time): studying yesterday or today
               means 0. Each one darkens the castle and brings crows.

Away for 4 days or more, the swan is shown one stage back ("cursed"); coming back breaks the curse
after 2 days in a row. Only the picture changes: the stage itself, the words and the scores stay.

The streak shield: one day off a week (Monday to Sunday, Vietnam time) is forgiven on its own. A
day missed right after a day studied is "shielded" if the week's shield is unused: no petal falls,
no crow comes, the streak goes on (a shielded day does not add to it). The next day missed counts,
so a long absence is softened by one day, never hidden. Today is never shielded: it is open.

A day counts as studied when the learner answered, reviewed, read, talked or practised (the routes
that depend on `deps.study_day`), kept in `learner_day`.
"""
from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Journey, LearnerDay

VN = timezone(timedelta(hours=7))
CURSE_AFTER = 4  # days away before the swan is shown a stage back
LIFT_AFTER = 2  # days in a row back that break the curse
LOOKBACK = 120  # days of history read

NAMES: dict[int, tuple[str, str]] = {
    1: ("Bóng tối trong tháp gai", "8 Kiếm"),
    2: ("Vết nứt ánh sáng", "2 Kiếm"),
    3: ("Vượt hồ đêm", "6 Kiếm"),
    4: ("Bình minh trên vòm nhọn", "Át Kiếm"),
    5: ("Bạch Thiên Nga", "Vương Kiếm"),
}


def today_vn(now: datetime | None = None) -> date:
    return (now or datetime.now(timezone.utc)).astimezone(VN).date()


def day_of(ts: datetime) -> date:
    return ts.astimezone(VN).date()


async def mark(db: AsyncSession, learner_id: uuid.UUID, now: datetime | None = None) -> None:
    """Note that the learner studied today (once a day; the caller's commit keeps it)."""
    await db.execute(
        pg_insert(LearnerDay).values(learner_id=learner_id, day=today_vn(now)).on_conflict_do_nothing()
    )


def week_of(d: date) -> date:
    """The Monday of d's week."""
    return d - timedelta(days=d.weekday())


def shielded_days(days: set[date], today: date) -> set[date]:
    """The days the weekly shield covered: a day missed right after a day studied, once a week,
    before today."""
    if not days:
        return set()
    out: set[date] = set()
    used: set[date] = set()
    d = min(days)
    while d < today:
        if d not in days and d - timedelta(days=1) in days and week_of(d) not in used:
            out.add(d)
            used.add(week_of(d))
        d += timedelta(days=1)
    return out


def kept_streak(real: set[date], covered: set[date], today: date) -> int:
    """Days studied in the unbroken run up to today (or yesterday); shielded days bridge the run
    without adding to it."""
    cursor = today if today in covered else today - timedelta(days=1)
    n = 0
    while cursor in covered:
        n += cursor in real
        cursor -= timedelta(days=1)
    return n


def missed_days(days: set[date], today: date) -> int:
    """Full days away before today: studied today or yesterday -> 0; a learner with no history -> 0."""
    if today in days:
        return 0
    before = [d for d in days if d < today]
    if not before:
        return 0
    return max(0, (today - max(before)).days - 1)


def streak(days: set[date], today: date) -> int:
    cursor = today if today in days else today - timedelta(days=1)
    n = 0
    while cursor in days:
        n += 1
        cursor -= timedelta(days=1)
    return n


def is_cursed(days: set[date], today: date) -> bool:
    """Away CURSE_AFTER days or more, and not yet back LIFT_AFTER days in a row."""
    if missed_days(days, today) >= CURSE_AFTER:
        return True
    run = streak(days, today)
    if run == 0 or run >= LIFT_AFTER:
        return False
    # back for fewer than LIFT_AFTER days: how long was the absence before this run?
    start = (today if today in days else today - timedelta(days=1)) - timedelta(days=run - 1)
    before = [d for d in days if d < start]
    if not before:
        return False
    return (start - max(before)).days - 1 >= CURSE_AFTER


@dataclass
class JourneyState:
    stage: int
    shown_stage: int
    missed_days: int
    cursed: bool
    studied_today: bool
    streak: int
    items: int
    name: str
    card: str
    raised: bool  # the stage went up just now
    relics: list[str] = field(default_factory=list)  # the support topics' relics, kept for good
    sparkle: int = 0  # 0..3, the highest reached
    changed: bool = False  # something new was kept (to commit)
    shield_ready: bool = True  # this week's shield is still unused
    shield_day: date | None = None  # the last day the shield covered, within the past week


async def study_days(db: AsyncSession, learner_id: uuid.UUID, today: date) -> set[date]:
    rows = (
        await db.execute(
            select(LearnerDay.day).where(
                LearnerDay.learner_id == learner_id, LearnerDay.day >= today - timedelta(days=LOOKBACK)
            )
        )
    ).scalars().all()
    return set(rows)


async def compute(
    db: AsyncSession,
    learner_id: uuid.UUID,
    earned: int,
    items: int,
    extra_days: set[date] | None = None,
    now: datetime | None = None,
    relics: Sequence[str] = (),
    sparkle: int = 0,
) -> JourneyState:
    """The learner's journey now. `earned`: the stage the chapters finished give; `relics` and
    `sparkle`: what the support topics give now. Keeps what is new (not committed here) and never
    lowers what was kept."""
    now = now or datetime.now(timezone.utc)
    today = today_vn(now)
    days = await study_days(db, learner_id, today) | (extra_days or set())
    row = await db.get(Journey, learner_id)
    stored = row.stage if row is not None else 1
    kept_relics = list(row.relics or []) if row is not None else []
    kept_sparkle = row.sparkle if row is not None else 0
    earned = max(1, min(5, earned))
    new_relics = [r for r in relics if r not in kept_relics]
    raised = earned > stored
    if raised or new_relics or sparkle > kept_sparkle:
        if row is None:
            row = Journey(learner_id=learner_id, stage=stored, reached_at=now, relics=[], sparkle=0)
            db.add(row)
        if raised:
            row.stage = earned
            row.reached_at = now
        if new_relics:
            row.relics = kept_relics + new_relics
        if sparkle > kept_sparkle:
            row.sparkle = sparkle
    stage = max(stored, earned)
    shields = shielded_days(days, today)
    covered = days | shields
    cursed = is_cursed(covered, today)
    shown = max(1, stage - 1) if cursed else stage
    name, card = NAMES[shown]
    return JourneyState(
        stage=stage,
        shown_stage=shown,
        missed_days=missed_days(covered, today),
        cursed=cursed,
        studied_today=today in days,
        streak=kept_streak(days, covered, today),
        items=items,
        name=name,
        card=card,
        raised=raised,
        relics=kept_relics + new_relics,
        sparkle=max(kept_sparkle, sparkle),
        changed=raised or bool(new_relics) or sparkle > kept_sparkle,
        shield_ready=week_of(today) not in {week_of(d) for d in shields},
        shield_day=max((d for d in shields if d >= today - timedelta(days=7)), default=None),
    )

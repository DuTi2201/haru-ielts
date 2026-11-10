"""How the AI speaking features are sold. Each feature (catalog.FEATURES) has a mode an admin can
change (billing.feature_rule; these are the defaults):

  free   open to every signed-in learner (still within the daily minute / try limits)
  trial  a one-time free trial per ACCOUNT (never renewed), then a Haru Nói pass
  paid   a Haru Nói pass only

The trial is sized by two admin settings (billing.setting), because Gemini Live is paid by the
minute and the presentation marking by the call:

  live_trial_minutes   minutes of live speaking (Trò chuyện + Tranh luận together), for life
  present_trial_tries  marked presentation tries, for life

A live session started on the trial is cut to the minutes left (the token itself expires soon
after), and an unfinished one counts as all the minutes it was allowed, so closing the tab does
not give the minutes back. A learner holding a pass (or staff, or an "all" grant) is never counted.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.services.billing import catalog

Mode = Literal["free", "trial", "paid"]
MODES: tuple[str, ...] = ("free", "trial", "paid")
LIVE_FEATURES = ("talk", "debate")  # Gemini Live: one shared pool of trial minutes


@dataclass(frozen=True)
class Rule:
    mode: Mode


DEFAULTS: dict[str, Rule] = {"talk": Rule("trial"), "present": Rule("trial"), "debate": Rule("trial")}

# the trial's size, and the bounds an admin may set it within
# 5 live minutes cost ~7,500đ per account that uses them all (Gemini Live): enough for two short
# sessions, the moment a learner hears Haru answer back
TRIAL_DEFAULTS: dict[str, int] = {"live_trial_minutes": 5, "present_trial_tries": 1}
TRIAL_BOUNDS: dict[str, tuple[int, int]] = {"live_trial_minutes": (5, 60), "present_trial_tries": (0, 20)}

_rules: dict[str, Rule] = dict(DEFAULTS)
_trial: dict[str, int] = dict(TRIAL_DEFAULTS)


def apply_rules(rows: dict[str, str], settings: dict[str, int] | None = None) -> None:
    """The admin's choices over the defaults (`rows`: feature -> mode; `settings`: trial sizes).
    A mode the code does not know (an old 'quota') reads as 'trial'; an out-of-bounds size is ignored."""
    global _rules, _trial
    out = dict(DEFAULTS)
    for key, mode in rows.items():
        if key in DEFAULTS:
            out[key] = Rule(mode if mode in MODES else "trial")  # type: ignore[arg-type]
    _rules = out
    trial = dict(TRIAL_DEFAULTS)
    for key, value in (settings or {}).items():
        lo, hi = TRIAL_BOUNDS.get(key, (0, -1))
        if isinstance(value, int) and lo <= value <= hi:
            trial[key] = value
    _trial = trial


def rule(feature: str) -> Rule:
    return _rules.get(feature, Rule("free"))


def rules() -> dict[str, Rule]:
    return dict(_rules)


def trial() -> dict[str, int]:
    return dict(_trial)


def trial_size(feature: str) -> tuple[int, str]:
    """(amount, unit) of the trial for a feature: live minutes, or presentation tries."""
    if feature in LIVE_FEATURES:
        return _trial["live_trial_minutes"], "phút"
    return _trial["present_trial_tries"], "lượt"


def trial_left(feature: str, used: int) -> int | None:
    """What is left of the trial (minutes for live features, tries for Trình bày); None = free."""
    r = rule(feature)
    if r.mode == "free":
        return None
    if r.mode == "paid":
        return 0
    amount, _ = trial_size(feature)
    return max(0, amount - used)


def refusal_vi(feature: str) -> str:
    r = rule(feature)
    label = catalog.FEATURES.get(feature, feature)
    if r.mode == "paid":
        return f"{label} thuộc gói Haru Nói. Mở gói để luyện tiếp."
    amount, unit = trial_size(feature)
    what = f"{amount} phút nói với Haru" if feature in LIVE_FEATURES else f"{amount} lượt chấm Trình bày"
    return (
        f"Bạn đã dùng hết phần dùng thử miễn phí ({what}, một lần cho mỗi tài khoản). "
        "Mở gói Haru Nói để luyện tiếp."
    )

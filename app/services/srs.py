"""A small spaced-repetition schedule, and the daily review queue built on it.

`ItemState.strength` (0..1, +/-0.2 per answer) stays the readiness signal. This
module adds *when an item should come back*, in the way an SM-2 deck does but
for a plain right/wrong answer:

* a correct answer moves the item one step up a ladder of gaps — 1 day, 3 days,
  then each gap is the last one times `ease` (about 1-3-7-15-34-75 days);
* a wrong answer is a lapse: the ladder restarts, the item is due again in ten
  minutes (so it comes back in the same sitting) and its `ease` drops a little,
  so an item that keeps failing is seen more often than one that doesn't;
* a correct answer to an item that is not due yet changes nothing in the
  schedule — re-running a deck the same day must not push every card out to
  next month. (Strength still moves, as it always did.)
* an item forgotten twice and not yet back on its feet is a *leech*: it goes to
  the front of the due cards, and "weak" practice lists such items on demand.
* a right answer that was a lucky guess or came slowly ("Chưa chắc", `hard`) is
  not a full step: no strength gained, `ease` drops a little and the gap only
  grows by a fifth, the run of right answers is not extended;
* a card the learner marks as already known ("Đã biết", `known`) is left out of
  the queue altogether: never offered as new, never due, and it does not use up
  the day's new cards. Undoing it puts the card back where it was;
* a "review-only" day ("Hôm nay bận — chỉ ôn") offers no new cards at all.

Pure functions only (no database, no clock of its own): the router loads the rows,
hands them over and stores what comes back, so the rules are unit-tested without
Postgres.
"""
from __future__ import annotations

from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass, field, replace
from datetime import date, datetime, timedelta

START_EASE = 2.2
MIN_EASE = 1.3
LAPSE_EASE_PENALTY = 0.2
MAX_INTERVAL_DAYS = 180.0
FIRST_INTERVAL_DAYS = 1.0
SECOND_INTERVAL_DAYS = 3.0
RELEARN_DELAY = timedelta(minutes=10)
STRENGTH_STEP = 0.2
HARD_EASE_PENALTY = 0.15  # a right answer that was a guess, or slow
HARD_INTERVAL_FACTOR = 1.2
SLOW_ANSWER_MS = 8000  # a right answer that took longer than this counts as hard
KNOWN_STRENGTH = 0.8  # a card marked "Đã biết" before it was ever studied counts as mastered

# An item counts as due this long before its due time. People study at about the
# same hour each day, so "due in exactly 24 h" would otherwise mean "tomorrow,
# an hour after you open the app".
DUE_GRACE = timedelta(hours=6)

DEFAULT_REVIEW_LIMIT = 20  # due cards in one sitting
DEFAULT_NEW_PER_DAY = 8  # new cards per rolling 24 h
NEW_WINDOW = timedelta(hours=24)
GRAMMAR_SHARE = 4  # one new card in four is a grammar point (when there is one)
ARTICLE_SHARE = 4  # ...and one in four is a word from a news article (when there is one)

# Words from news articles are written for native readers; the ones that are
# above the learner's goal are not pushed into the daily queue (they stay in the
# article's own page). Cap = the highest word level offered, by goal.
ARTICLE_LEVEL_CAP = {"talk": 3, "topik1": 2, "topik4": 4, "topik5": 5, "topik6": 6}
DEFAULT_ARTICLE_LEVEL_CAP = 4

LEECH_LAPSES = 2  # forgotten this many times...
RECOVERED_REPS = 3  # ...and not yet right this many times in a row = a leech

ItemKey = tuple[str, int]  # ("vocab_item" | "grammar_point", content id)


@dataclass(frozen=True)
class Schedule:
    strength: float = 0.0
    reps: int = 0  # correct answers in a row since the last lapse
    lapses: int = 0
    ease: float = START_EASE
    interval_days: float = 0.0
    due_at: datetime | None = None
    introduced_at: datetime | None = None
    known: bool = False  # "Đã biết": out of the queue until undone


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def is_hard(hard: bool = False, response_ms: int | None = None) -> bool:
    """A right answer counts as hard when the learner said "Chưa chắc" or took long."""
    return bool(hard) or (response_ms is not None and response_ms > SLOW_ANSWER_MS)


def review(prev: Schedule | None, correct: bool, now: datetime, *, hard: bool = False) -> Schedule:
    """The schedule after one answer given at `now`. `hard` (only meaningful for a right
    answer): it was a guess or slow — no strength gained, `ease` -0.15 (never below the
    floor), the gap grows by a fifth (at least a day), the run of right answers stays."""
    base = prev or Schedule(introduced_at=now)
    hard = hard and correct
    step = 0.0 if hard else STRENGTH_STEP if correct else -STRENGTH_STEP
    strength = _clamp(base.strength + step)
    introduced = base.introduced_at or now

    if not correct:
        return Schedule(
            strength=strength,
            reps=0,
            lapses=base.lapses + 1,
            ease=max(MIN_EASE, base.ease - LAPSE_EASE_PENALTY),
            interval_days=0.0,
            due_at=now + RELEARN_DELAY,
            introduced_at=introduced,
        )

    if prev is not None and prev.due_at is not None and now < prev.due_at - DUE_GRACE:
        return replace(base, strength=strength, introduced_at=introduced)  # early: no credit

    if hard:
        interval = min(MAX_INTERVAL_DAYS, float(max(1, round(base.interval_days * HARD_INTERVAL_FACTOR))))
        return replace(
            base,
            strength=strength,
            ease=max(MIN_EASE, base.ease - HARD_EASE_PENALTY),
            interval_days=interval,
            due_at=now + timedelta(days=interval),
            introduced_at=introduced,
        )

    reps = base.reps + 1
    if reps == 1:
        interval = FIRST_INTERVAL_DAYS
    elif reps == 2:
        interval = SECOND_INTERVAL_DAYS
    else:
        interval = max(base.interval_days + 1, round(base.interval_days * base.ease))
    interval = min(MAX_INTERVAL_DAYS, float(interval))
    return Schedule(
        strength=strength,
        reps=reps,
        lapses=base.lapses,
        ease=base.ease,
        interval_days=interval,
        due_at=now + timedelta(days=interval),
        introduced_at=introduced,
    )


def is_due(schedule: Schedule, now: datetime) -> bool:
    return not schedule.known and schedule.due_at is not None and schedule.due_at <= now + DUE_GRACE


def new_limit_for(requested: int, review_only_on: date | None, today: date) -> int:
    """The day's new-card cap: none on the day the learner said "Hôm nay bận — chỉ ôn"."""
    return 0 if review_only_on is not None and review_only_on == today else requested


def only_marked_known(schedule: Schedule) -> bool:
    """A row that exists only because the card was marked "Đã biết" (never answered, never
    introduced): undoing the mark removes it, so the card is new again."""
    return schedule.reps == 0 and schedule.lapses == 0 and schedule.introduced_at is None


def article_level_cap(goal: str | None) -> int:
    return ARTICLE_LEVEL_CAP.get(goal or "", DEFAULT_ARTICLE_LEVEL_CAP)


def is_leech(schedule: Schedule) -> bool:
    """Forgotten at least twice and not yet answered right three times in a row since."""
    return not schedule.known and schedule.lapses >= LEECH_LAPSES and schedule.reps < RECOVERED_REPS


def is_shaky(schedule: Schedule) -> bool:
    """Forgotten at least once and not yet back on its feet: what "weak" practice offers."""
    return not schedule.known and schedule.lapses >= 1 and schedule.reps < RECOVERED_REPS


@dataclass
class Queue:
    due: list[ItemKey] = field(default_factory=list)  # most overdue first, cut at `limit`
    due_total: int = 0  # everything due, before the cut
    new: list[ItemKey] = field(default_factory=list)
    new_today: int = 0  # started in the last 24 h
    new_budget: int = 0  # how many new cards today's cap still allows
    article_waiting: int = 0  # unseen article words that could be offered (before the cap)


def _spread(main: list[ItemKey], extra: list[ItemKey]) -> list[ItemKey]:
    """`extra` spaced evenly among `main` (grammar in between the chunks, not
    all at the end when the learner is tired)."""
    if not extra:
        return list(main)
    out: list[ItemKey] = []
    step = max(1, round(len(main) / (len(extra) + 1)))
    pending = list(extra)
    for i, key in enumerate(main, start=1):
        out.append(key)
        if pending and i % step == 0:
            out.append(pending.pop(0))
    out.extend(pending)
    return out


def build_queue(
    schedules: Mapping[ItemKey, Schedule],
    lessons: Mapping[int, Sequence[ItemKey]],
    now: datetime,
    *,
    limit: int = DEFAULT_REVIEW_LIMIT,
    new_limit: int = DEFAULT_NEW_PER_DAY,
    articles: Mapping[str, Sequence[ItemKey]] | None = None,
    hold: Collection[ItemKey] = (),
    order: Sequence[int] | None = None,
    later: Collection[ItemKey] = (),
) -> Queue:
    """What to study now.

    `schedules` is this learner's ItemState rows; `lessons` is lesson id -> the
    items in it (only items that exist are in there, so a row whose lesson was
    rolled back is never offered); `articles` is news-article id -> its words, in
    the order the articles should be studied; `hold` are article words that exist
    but must not be started yet (above the learner's level) — one already started
    is still scheduled. Due items come first — leeches, then the most
    overdue. New items are capped at `new_limit` per rolling 24 h: lesson cards
    come from the lowest-numbered lessons that still have unseen items, about one
    in four is a grammar point and about one in four an article word, and every
    item of a family stays next to its mates because the lesson's own order is
    kept. When one kind runs out, the others fill its place. `order` is the
    curriculum order of the lessons (ids); without it, lowest id first. `later` are
    the words that only need recognising: inside their lesson they come after the words to
    learn now, so a short day goes to the words the next lessons build on. A card marked
    known has a row in `schedules`, so it is never new, and `is_due` never offers it.
    """
    articles = articles or {}
    in_content = {key for items in lessons.values() for key in items}
    in_content |= {key for items in articles.values() for key in items}
    due = sorted(
        (key for key, s in schedules.items() if key in in_content and is_due(s, now)),
        key=lambda key: (not is_leech(schedules[key]), schedules[key].due_at, key),  # type: ignore[arg-type,return-value]
    )

    introduced = sum(  # a card marked "Đã biết" does not use up the day's new cards
        1
        for s in schedules.values()
        if not s.known and s.introduced_at is not None and s.introduced_at > now - NEW_WINDOW
    )
    budget = max(0, new_limit - introduced)

    vocab_pool: list[ItemKey] = []
    grammar_pool: list[ItemKey] = []
    if order is None:
        sequence = sorted(lessons)
    else:
        listed = [i for i in order if i in lessons]
        sequence = listed + sorted(set(lessons) - set(listed))
    for lesson_id in sequence:
        unseen = sorted((key for key in lessons[lesson_id] if key not in schedules), key=lambda key: (key in later, key))
        vocab_pool += [key for key in unseen if key[0] == "vocab_item"]
        grammar_pool += [key for key in unseen if key[0] == "grammar_point"]
    article_pool: list[ItemKey] = []
    for items in articles.values():  # article by article, so one article's words stay together
        article_pool += sorted(key for key in items if key not in schedules and key not in hold)

    grammar_n = min(len(grammar_pool), budget // GRAMMAR_SHARE)
    article_n = min(len(article_pool), budget // ARTICLE_SHARE)
    vocab_n = min(len(vocab_pool), budget - grammar_n - article_n)
    grammar_n = min(len(grammar_pool), grammar_n + (budget - grammar_n - article_n - vocab_n))  # no vocab left: grammar fills the day
    article_n = min(len(article_pool), article_n + (budget - grammar_n - article_n - vocab_n))  # ...then articles
    new = _spread(_spread(vocab_pool[:vocab_n], grammar_pool[:grammar_n]), article_pool[:article_n])

    return Queue(
        due=due[:limit],
        due_total=len(due),
        new=new,
        new_today=introduced,
        new_budget=budget,
        article_waiting=len(article_pool),
    )


def weak_keys(
    schedules: Mapping[ItemKey, Schedule],
    existing: set[ItemKey],
    *,
    limit: int = DEFAULT_REVIEW_LIMIT,
) -> list[ItemKey]:
    """The items the learner keeps forgetting, most forgotten first, whether or not
    they are due — for practice on demand. Only items that still exist."""
    shaky = [key for key, s in schedules.items() if key in existing and is_shaky(s)]
    shaky.sort(key=lambda key: (-schedules[key].lapses, schedules[key].strength, key))
    return shaky[:limit]

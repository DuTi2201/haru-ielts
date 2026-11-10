"""Kiểm tra đầu vào thích ứng: where a learner stands on the course, in about two minutes.

The question bank is the lessons' own short reading questions (fill a blank, pick the closest
meaning), each tied to the lesson that teaches it: written and checked by a person, never generated
here. The course is a LADDER: the lessons in order, without the review lessons and the Viết câu 54
course (a writing technique, not a level).

What is estimated is the learner's FRONTIER `k`: they can do the lessons before rung k and not yet
the ones from k on (k = 0: start at the first lesson; k = len(ladder): the whole course). We keep a
probability for every k and update it after each answer:

* right on a lesson the learner knows: 0.85 (a slip is possible); right on one they do not: 0.25
  (a guess among four options);
* "Chưa học mẫu này" (an honest skip): 0.05 if known, 0.95 if not: no reason to guess;
* the next question sits where the frontier is most in doubt (the median of the probabilities),
  so a beginner never climbs to TOPIK 6 and an advanced learner is not kept on Bài 1.

It stops as soon as the estimate is tight (most of the probability within a few lessons), after
at least MIN_ITEMS questions, or at MAX_ITEMS. The survey answer "where do you think you are" only
sets where the first question lands; the answers decide.

This module is pure (no database, no model): the router feeds it the answers so far and stores
what it concludes."""
from __future__ import annotations

import json
import math
from collections.abc import Sequence
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from app.services import lesson_seed as seed

MIN_ITEMS = 5
MAX_ITEMS = 12
WINDOW = 3  # the estimate is tight when this many rungs either side of the median hold...
TIGHT = 0.85  # ...this share of the probability
SLIP, GUESS, SKIP_KNOWN, SKIP_UNKNOWN = 0.15, 0.25, 0.05, 0.95
TYPES = ("read_cloze", "read_blank", "read_similar")  # short, four options, no audio
MAX_STIMULUS = 260  # characters of the question's text: two minutes, not a reading test
SKIPPED_SLUGS = ("viet-nghi-luan-",)  # the Viết câu 54 course: a technique, not a level

# where the first question lands for each answer to "bạn đang ở đâu?" (a lesson slug prefix)
SELF_LEVELS: dict[str, str | None] = {
    "new": None,  # chưa biết gì: no test, start at the first lesson
    "basic": "sinh-hoat-00-nen-tang-3",
    "elementary": "sinh-hoat-03-an-uong",  # Sơ cấp done: the first question is the first lesson of Trung cấp
    "intermediate": "nhap-canh-01",
    "advanced": "xa-hoi-01",
}
LEVEL_LABEL = {1: "Sơ cấp (TOPIK I)", 2: "Sơ cấp (TOPIK I)", 3: "Trung cấp (TOPIK 3)", 4: "Trung cấp (TOPIK 4)",
               5: "Cao cấp (TOPIK 5–6)", 6: "Cao cấp (TOPIK 5–6)"}
NEW_LABEL = "Mới bắt đầu"


@dataclass(frozen=True)
class Rung:
    sort_order: int
    slug: str
    title: str
    level: int
    topic: str
    # the lesson it was cut out of (Nền tảng parts), else its own slug: the prior measures distance
    # in whole lessons, so cutting a lesson into parts does not move where a self-rating lands
    group: str = ""


@dataclass(frozen=True)
class Question:
    ref: str  # "<lesson slug>/<question id>": what the browser sends back
    rung: int  # index on the ladder
    exercise: dict[str, Any]  # the exercise with this one question, the answer taken out
    answer: str
    grammar: tuple[str, ...]


@dataclass(frozen=True)
class Bank:
    ladder: tuple[Rung, ...]
    by_rung: tuple[tuple[Question, ...], ...]
    by_ref: dict[str, Question]


def _short(ex: dict[str, Any]) -> bool:
    return len(json.dumps(ex.get("stimulus") or {}, ensure_ascii=False)) <= MAX_STIMULUS


def build(lessons: Sequence[Any]) -> Bank:
    """The ladder and its questions from the loaded seed (`lesson_seed.load_all().lessons`)."""
    ladder: list[Rung] = []
    per: list[tuple[Question, ...]] = []
    for r in sorted(lessons, key=lambda r: r.seed.sort_order):
        s = r.seed
        if s.kind in ("review", "hangul") or s.slug.startswith(SKIPPED_SLUGS):
            continue
        qs: list[Question] = []
        for ex in (r.practice or {"items": []})["items"]:
            if ex.get("type") not in TYPES or not _short(ex):
                continue
            for q in ex.get("questions") or []:
                if len(q.get("options") or []) != 4 or not q.get("answer"):
                    continue
                public = {k: v for k, v in q.items() if k not in ("answer", "explanation_vi", "tags", "grammar")}
                # the title names the pattern being tested ("Là N · chọn 이에요 hay 예요"): not shown
                shown = {k: v for k, v in ex.items() if k not in ("questions", "title_vi")} | {"questions": [public]}
                qs.append(Question(f"{s.slug}/{q['id']}", len(ladder), shown, str(q["answer"]), tuple(q.get("grammar") or ())))
        if not qs:
            continue
        ladder.append(Rung(s.sort_order, s.slug, s.title, s.level, s.topic, s.split_from or s.slug))
        per.append(tuple(qs))
    return Bank(tuple(ladder), tuple(per), {q.ref: q for qs in per for q in qs})


@lru_cache(maxsize=1)
def _lessons() -> tuple[Any, ...]:
    return tuple(seed.load_all().lessons)


@lru_cache(maxsize=1)
def bank() -> Bank:
    return build(_lessons())


def course() -> list[dict[str, Any]]:
    """Every seeded lesson with what it holds (for the roadmap's minutes)."""
    out = []
    for r in _lessons():
        s = r.seed
        out.append({
            "slug": s.slug, "sort_order": s.sort_order, "title": s.title, "kind": s.kind,
            "vocab": len(s.vocab), "grammar": len(s.grammar),
            "questions": sum(len(e.get("questions") or []) for e in (r.practice or {"items": []})["items"]),
        })
    return out


# ------------------------------------------------------------------ the estimate --
@dataclass(frozen=True)
class Answer:
    ref: str
    choice: str  # an option id, or "" for "Chưa học mẫu này"


def prior(n_rungs: int, ladder: Sequence[Rung], self_level: str | None) -> list[float]:
    """P(k) for k = 0..n_rungs before any answer: a third spread evenly (anyone can be anywhere),
    the rest around where the learner says they are."""
    n = n_rungs + 1
    flat = [1.0 / n] * n
    slug = SELF_LEVELS.get(self_level or "")
    if not slug:
        return flat
    # rung k -> its place counted in whole lessons (the parts of one Nền tảng lesson share a place)
    place: list[int] = []
    seen: list[str] = []
    for r in ladder:
        g = r.group or r.slug
        if g not in seen:
            seen.append(g)
        place.append(seen.index(g))
    place.append(len(seen))  # k = n_rungs: past the last lesson
    centre_rung = next((i for i, r in enumerate(ladder) if r.slug.startswith(slug)), n // 2)
    centre = place[centre_rung] if centre_rung < len(place) else len(seen) // 2
    peak = [math.exp(-0.5 * ((place[k] - centre) / 6.0) ** 2) for k in range(n)]
    total = sum(peak)
    return [0.35 * f + 0.65 * p / total for f, p in zip(flat, peak)]


def likelihood(known: bool, outcome: str) -> float:
    if outcome == "right":
        return 1 - SLIP if known else GUESS
    if outcome == "wrong":
        return SLIP if known else 1 - GUESS
    return SKIP_KNOWN if known else SKIP_UNKNOWN  # "skip"


def outcome_of(q: Question, choice: str) -> str:
    if not choice:
        return "skip"
    return "right" if choice == q.answer else "wrong"


def posterior(b: Bank, answers: Sequence[Answer], self_level: str | None) -> list[float]:
    p = prior(len(b.ladder), b.ladder, self_level)
    for a in answers:
        q = b.by_ref.get(a.ref)
        if q is None:
            continue
        out = outcome_of(q, a.choice)
        # the learner knows rung q.rung exactly when the frontier is past it (k > rung)
        p = [pk * likelihood(k > q.rung, out) for k, pk in enumerate(p)]
        s = sum(p) or 1.0
        p = [x / s for x in p]
    return p


def median(p: Sequence[float]) -> int:
    run = 0.0
    for k, x in enumerate(p):
        run += x
        if run >= 0.5:
            return k
    return len(p) - 1


def quantile(p: Sequence[float], q: float) -> int:
    run = 0.0
    for k, x in enumerate(p):
        run += x
        if run >= q:
            return k
    return len(p) - 1


def tight(p: Sequence[float]) -> bool:
    m = median(p)
    return sum(p[max(0, m - WINDOW): m + WINDOW + 1]) >= TIGHT


def done(p: Sequence[float], n_answered: int, answers_skipped_at_start: int) -> bool:
    if n_answered >= MAX_ITEMS:
        return True
    if answers_skipped_at_start >= 3 and p[0] + (p[1] if len(p) > 1 else 0) >= 0.85:
        return True  # three honest "chưa học" at the bottom: no need to go on
    return n_answered >= MIN_ITEMS and tight(p)


def next_question(b: Bank, answers: Sequence[Answer], p: Sequence[float]) -> Question:
    """A question on the rung where it is most uncertain whether the learner is past it: the rung
    just before the median frontier. Never one already asked; a rung used up gives way to its
    nearest neighbour."""
    asked = {a.ref for a in answers}
    used_rungs = [b.by_ref[a.ref].rung for a in answers if a.ref in b.by_ref]
    target = min(max(median(p) - 1, 0), len(b.ladder) - 1)
    # do not ask the very same rung three times in a row: the neighbour tells as much
    if len(used_rungs) >= 2 and used_rungs[-1] == used_rungs[-2] == target:
        target = min(target + 1, len(b.ladder) - 1) if p[target + 1 :] and sum(p[target + 1 :]) >= 0.5 else max(target - 1, 0)
    for d in range(len(b.ladder)):
        for r in (target - d, target + d):
            if 0 <= r < len(b.ladder):
                fresh = [q for q in b.by_rung[r] if q.ref not in asked]
                if fresh:
                    # the same learner gets the same question for the same history; another learner
                    # (or a retake) gets a different one
                    return fresh[(len(answers) * 7 + r) % len(fresh)]
    raise LookupError("the bank is used up")


def skipped_at_start(b: Bank, answers: Sequence[Answer]) -> int:
    n = 0
    for a in answers:
        q = b.by_ref.get(a.ref)
        if q is None or outcome_of(q, a.choice) == "right":
            break
        n += 1
    return n


# ------------------------------------------------------------------ the result --
@dataclass(frozen=True)
class Result:
    frontier: int  # rungs the learner can do (0 = start at the first lesson)
    low: int  # the frontier is very likely between low and high
    high: int
    start: Rung | None  # the first lesson to study (None: the whole course is behind them)
    level_label: str
    gaps: tuple[tuple[Rung, tuple[str, ...]], ...]  # lessons before the start answered wrong, and the patterns
    advice: str  # "start_here" | "fill_gaps" | "restart_from"
    restart: Rung | None  # with "restart_from": where
    asked: int
    right: int


def conclude(b: Bank, answers: Sequence[Answer], self_level: str | None) -> Result:
    p = posterior(b, answers, self_level)
    k = median(p)
    low, high = quantile(p, 0.1), quantile(p, 0.9)
    graded = [(b.by_ref[a.ref], outcome_of(b.by_ref[a.ref], a.choice)) for a in answers if a.ref in b.by_ref]
    below = [(q, o) for q, o in graded if q.rung < k]
    missed: dict[int, list[str]] = {}
    for q, o in below:
        if o != "right":
            missed.setdefault(q.rung, []).extend(g for g in q.grammar if g not in missed.get(q.rung, []))
    gaps = tuple((b.ladder[r], tuple(gs)) for r, gs in sorted(missed.items()))
    advice, restart = "start_here", None
    if below and len(missed) >= 2 and sum(1 for _, o in below if o != "right") / len(below) >= 0.4:
        # many misses below the frontier: the lower end of the estimate is the safer start
        advice, restart = "restart_from", b.ladder[min(low, k - 1)] if k > 0 else None
    elif gaps:
        advice = "fill_gaps"
    start = b.ladder[k] if k < len(b.ladder) else None
    label = NEW_LABEL if k == 0 else LEVEL_LABEL.get(b.ladder[k - 1].level, NEW_LABEL)
    return Result(k, low, high, start, label, gaps, advice, restart, len(graded), sum(1 for _, o in graded if o == "right"))

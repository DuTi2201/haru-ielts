"""What a learner can DO with a grammar card — the "bộ nhớ năng lực" — and the mixed review built on it.

`ItemState` (app.services.srs) remembers whether a card is still *remembered*. This module is
about *use*: each answer to a practice question linked to a card is an outcome on one rung of a
ladder,

    0  Nhận ra          choose the right form / read it (multiple choice, the flip-card review)
    1  Xếp câu          put word tiles in order (build_order)
    2  Điền / nối câu   type the form or a whole sentence (write_fill, rungs 2-3 of "Tạo câu")
    3  Tự viết, tự nói  a paragraph or a spoken answer (write_essay, speak: marked by the learner)

and only the last three outcomes per rung are kept (see `models.GrammarCompetency`). A rung is
*reached* when at least two thirds of those outcomes are right (one right answer on its own is
enough to start with: 1 of 1); it is *failing* when at least two thirds are wrong. Those two
words drive everything:

* the **level** of a card is the highest rung reached (-1 = none yet);
* the **goal** of a card is rung 3 when the card is for use ("produce") and rung 0 when the exam
  only asks the learner to recognise it ("recognize");
* the mixed review serves the rung *above* the level (up when the last answers were mostly right)
  unless that rung is failing, in which case it serves the level itself again (down when they
  were mostly wrong), and a card at its goal keeps being served at the goal rung;
* only cards the learner has already met are mixed in, so the review never brings in a card above
  their level; among cards with nothing else to rank them, the easier exam stage comes first.

Pure functions and small dataclasses only (no database, no clock of its own): the routers load the
rows and hand them over, so every rule here is unit-tested without Postgres.
"""
from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime

RUNG_LABEL = {0: "Nhận ra", 1: "Xếp câu", 2: "Điền / nối câu", 3: "Tự viết, tự nói"}
RUNGS = tuple(RUNG_LABEL)
WINDOW = 3  # outcomes kept per rung
DEFAULT_MIX = 8  # exercises in one mixed review
MAX_MIX = 15
PER_CARD = 2  # one card fills at most this many places of a mixed review
MASTERED = 0.8  # the same bar as app.services.progress.MASTERY_THRESHOLD
_EPS = 1e-9

History = dict[str, list[int]]


# ------------------------------------------------------------------ the ladder --
def rung_of(exercise: Mapping) -> int | None:
    """The rung an exercise's answers count for (None for something that is not graded here)."""
    kind = exercise.get("type")
    if kind == "build_order":
        return 1
    if kind == "write_fill":
        return 2
    if kind in ("write_essay", "speak"):
        return 3
    if exercise.get("questions") is not None:
        return 0
    return None


def mixable(exercise: Mapping) -> bool:
    """Whether a mixed review may offer the exercise: short and graded at once in the browser. Word
    tiles and fill-ins; reading questions; not listening (it needs audio) and not paragraphs or
    spoken tasks (the learner marks them and they take minutes)."""
    rung = rung_of(exercise)
    return rung in (1, 2) or (rung == 0 and exercise.get("skill") == "reading")


def record(history: Mapping[str, Sequence[int]] | None, rung: int, correct: bool) -> History:
    """`history` after one more outcome on `rung` (a new dict; the old one is untouched)."""
    if rung not in RUNG_LABEL:
        raise ValueError(f"unknown rung {rung!r}")
    out: History = {k: [int(x) for x in v] for k, v in (history or {}).items()}
    out[str(rung)] = (out.get(str(rung), []) + [1 if correct else 0])[-WINDOW:]
    return out


def recent(history: Mapping[str, Sequence[int]] | None, rung: int) -> list[int]:
    return [int(x) for x in (history or {}).get(str(rung), [])][-WINDOW:]


def reached_rung(results: Sequence[int]) -> bool:
    """At least two thirds of the recent outcomes are right (1 of 1 counts: it is a start)."""
    n = len(results)
    return n > 0 and sum(results) * 3 >= 2 * n


def failing_rung(results: Sequence[int]) -> bool:
    """At least two thirds are wrong, over at least two outcomes (one slip is not a pattern)."""
    n = len(results)
    return n >= 2 and (n - sum(results)) * 3 >= 2 * n


def level(history: Mapping[str, Sequence[int]] | None) -> int:
    """The highest rung reached, -1 when none is."""
    top = -1
    for rung in RUNGS:
        if reached_rung(recent(history, rung)):
            top = rung
    return top


def goal_rung(use_level: str | None) -> int:
    return 0 if use_level == "recognize" else max(RUNGS)


def goal_reached(history: Mapping[str, Sequence[int]] | None, use_level: str | None) -> bool:
    return level(history) >= goal_rung(use_level)


def serve_rung(history: Mapping[str, Sequence[int]] | None, use_level: str | None) -> int:
    """The rung to practise next: up one rung when the level is solid, the level itself again
    when the rung above keeps going wrong, the goal rung once the goal is reached."""
    top, goal = level(history), goal_rung(use_level)
    if top >= goal:
        return goal
    above = top + 1
    if failing_rung(recent(history, above)):
        return max(top, 0)
    return above


def failing_rungs(history: Mapping[str, Sequence[int]] | None) -> list[int]:
    return [r for r in RUNGS if failing_rung(recent(history, r))]


# --------------------------------------------------------------------- the cards --
@dataclass(frozen=True)
class CardState:
    """One grammar card as one learner stands with it."""

    id: int
    pattern: str
    lesson_id: int
    use_level: str = "produce"
    difficulty: int = 3  # the exam stage ("kiip-2" = 2); 3 when the card has no tag
    history: Mapping[str, Sequence[int]] = field(default_factory=dict)
    in_srs: bool = False  # an ItemState row exists: it has been introduced in the daily review
    strength: float = 0.0
    due: bool = False
    leech: bool = False
    shaky: bool = False  # forgotten at least once and not yet back on its feet
    overdue_since: datetime | None = None

    @property
    def met(self) -> bool:
        """The learner has seen the card in the review or answered a question about it."""
        return self.in_srs or any(self.history.get(str(r)) for r in RUNGS)

    @property
    def level(self) -> int:
        return level(self.history)

    @property
    def reached(self) -> bool:
        return goal_reached(self.history, self.use_level)

    @property
    def remembered(self) -> bool:
        return self.in_srs and self.strength >= MASTERED - _EPS and not self.leech


# ------------------------------------------------------------------ mixed review --
@dataclass(frozen=True)
class Candidate:
    """An exercise a mixed review may offer, with the cards its questions are linked to."""

    lesson_id: int
    exercise_id: str
    rung: int
    cards: tuple[int, ...]
    questions: tuple[str, ...]
    lesson_pos: int = 0  # where its lesson comes in the curriculum

    @property
    def key(self) -> tuple[int, str]:
        return (self.lesson_id, self.exercise_id)


@dataclass(frozen=True)
class Pick:
    candidate: Candidate
    reason: str  # due | wrong | new
    card_id: int | None = None  # the card that put it in the review (due: the due card)


def _nearest(options: Iterable[Candidate], want: int) -> Candidate | None:
    """The option whose rung is closest to `want` (the lower one on a tie), then the earliest."""
    ranked = sorted(options, key=lambda c: (abs(c.rung - want), c.rung, c.lesson_pos, c.exercise_id))
    return ranked[0] if ranked else None


def select_mix(
    candidates: Sequence[Candidate],
    cards: Mapping[int, CardState],
    results: Mapping[tuple[int, str], bool],
    current_lesson_id: int,
    *,
    limit: int = DEFAULT_MIX,
) -> list[Pick]:
    """The exercises of a mixed review, in the order they are asked:

    1. **due** — for each met card that is due (cards the learner keeps forgetting first, then the
       most overdue), one exercise at the rung `serve_rung` names, or the nearest rung there is;
    2. **wrong** — exercises with a question the learner last got wrong;
    3. **new** — exercises of EARLIER lessons the learner has not answered yet, easier exam
       stages first.

    An exercise of the lesson the learner is in that they have not answered yet is never offered
    (it is that lesson's own practice), nothing is offered twice and one card fills at most
    `PER_CARD` places. `results` maps (lesson id, question id) to the last outcome.
    """
    limit = max(0, min(limit, MAX_MIX))
    used: set[tuple[int, str]] = set()
    per_card: dict[int, int] = defaultdict(int)
    picks: list[Pick] = []

    def answered(c: Candidate) -> bool:
        return any((c.lesson_id, q) in results for q in c.questions)

    def wrong(c: Candidate) -> bool:
        return any(results.get((c.lesson_id, q)) is False for q in c.questions)

    def allowed(c: Candidate) -> bool:
        if c.key in used or not c.cards:
            return False
        if c.lesson_id == current_lesson_id and not answered(c):
            return False
        return all(per_card[cid] < PER_CARD for cid in c.cards if cid in cards)

    def take(c: Candidate, reason: str, card_id: int | None) -> None:
        used.add(c.key)
        for cid in c.cards:
            per_card[cid] += 1
        picks.append(Pick(c, reason, card_id))

    by_card: dict[int, list[Candidate]] = defaultdict(list)
    for c in candidates:
        for cid in c.cards:
            by_card[cid].append(c)

    due = sorted(
        (cs for cs in cards.values() if cs.met and cs.due),
        key=lambda cs: (not cs.leech, cs.overdue_since.timestamp() if cs.overdue_since else 0.0, cs.id),
    )
    for cs in due:
        if len(picks) >= limit:
            return picks
        pick = _nearest((c for c in by_card.get(cs.id, []) if allowed(c)), serve_rung(cs.history, cs.use_level))
        if pick is not None:
            take(pick, "due", cs.id)

    for c in sorted(candidates, key=lambda c: (c.lesson_pos, c.exercise_id)):
        if len(picks) >= limit:
            return picks
        if wrong(c) and allowed(c):
            take(c, "wrong", None)

    def easiest(c: Candidate) -> int:
        return min((cards[cid].difficulty for cid in c.cards if cid in cards), default=3)

    for c in sorted(candidates, key=lambda c: (easiest(c), c.lesson_pos, c.exercise_id)):
        if len(picks) >= limit:
            return picks
        if (
            c.lesson_id != current_lesson_id
            and not answered(c)
            and any(cid in cards and cards[cid].met for cid in c.cards)
            and allowed(c)
        ):
            take(c, "new", None)
    return picks


@dataclass(frozen=True)
class PracticeSet:
    """One lesson's practice set as stored: its exercises and the cards its questions link to
    (`grammar`: pattern -> card info, with the `lesson_slug` of the lesson that teaches it)."""

    lesson_id: int
    pos: int  # where the lesson comes in the curriculum
    items: Sequence[Mapping]
    grammar: Mapping[str, Mapping]


def exercise_patterns(exercise: Mapping) -> list[str]:
    """The grammar patterns an exercise is linked to (its own link, or its questions' links)."""
    out: list[str] = list(exercise.get("grammar") or [])
    for q in exercise.get("questions") or []:
        out += [p for p in q.get("grammar") or [] if p not in out]
    return list(dict.fromkeys(out))


def build_candidates(sets: Iterable[PracticeSet], gid_of: Mapping[tuple[str, str], int]) -> list[Candidate]:
    """The exercises a mixed review may offer, with the cards they are linked to.
    `gid_of` maps (slug of the teaching lesson, pattern) to the grammar point's id; an exercise
    none of whose links resolves to a card is left out (nothing says what it would revise)."""
    from app.services.lesson_seed import question_ids

    out: list[Candidate] = []
    for ps in sets:
        for ex in ps.items:
            if not mixable(ex):
                continue
            ids = sorted(
                {
                    gid_of[(ps.grammar[p]["lesson_slug"], p)]
                    for p in exercise_patterns(ex)
                    if p in ps.grammar and (ps.grammar[p]["lesson_slug"], p) in gid_of
                }
            )
            if ids:
                out.append(Candidate(ps.lesson_id, ex["id"], rung_of(ex) or 0, tuple(ids), tuple(question_ids(dict(ex))), ps.pos))
    return out


# ------------------------------------------------------------------ the report --
@dataclass(frozen=True)
class LessonCards:
    lesson_id: int
    title: str
    cards: Sequence[CardState]


def summarize(cards: Sequence[CardState]) -> dict:
    """The numbers of a set of cards: how many are met, at which level, reached, remembered."""
    seen = [c for c in cards if c.met]
    by_level = {str(r): 0 for r in RUNGS}
    for c in seen:
        if c.level >= 0:
            by_level[str(c.level)] += 1
    return {
        "cards": len(cards),
        "unseen": len(cards) - len(seen),
        "studying": sum(1 for c in seen if c.level < 0),
        "by_level": by_level,
        "goal_reached": sum(1 for c in cards if c.met and c.reached),
        "remembered": sum(1 for c in cards if c.remembered),
        "due": sum(1 for c in seen if c.due),
        "leeches": sum(1 for c in seen if c.leech),
    }


def weakest(cards: Sequence[CardState], limit: int = 5) -> list[dict]:
    """Cards worth attention: forgotten again and again, or failing a rung, worst first."""
    out = []
    for c in cards:
        if not c.met:
            continue
        failing = failing_rungs(c.history)
        if not (c.leech or c.shaky or failing):
            continue
        why = (
            "hay quên khi ôn" if c.leech else "đã quên, chưa nhớ lại vững" if c.shaky else
            f"hay sai ở bước «{RUNG_LABEL[failing[0]]}»"
        )
        out.append((c, why, 0 if c.leech else 1 if c.shaky else 2))
    out.sort(key=lambda t: (t[2], t[0].level, t[0].id))
    return [
        {"grammar_id": c.id, "pattern": c.pattern, "lesson_id": c.lesson_id, "why": why, "level": c.level}
        for c, why, _ in out[:limit]
    ]


def recommend(lessons: Sequence[LessonCards], limit: int = 3) -> list[dict]:
    """What to do next in a topic (at most `limit`, most useful first). Each item says where to
    go: `path` is a route of the app, `lesson_id` + `skill` open a lesson's practice tab."""
    cards = [c for lc in lessons for c in lc.cards]
    seen = [c for c in cards if c.met]
    recs: list[dict] = []

    due = sum(1 for c in seen if c.due)
    if due:
        recs.append({"kind": "review", "title": f"Ôn {due} thẻ đến hạn", "subtitle": "Thẻ ngữ pháp của chủ đề này đã đến lúc ôn lại", "path": "/review"})
    leeches = sum(1 for c in seen if c.leech)
    if leeches:
        recs.append({"kind": "weak", "title": f"Luyện lại {leeches} thẻ hay quên", "subtitle": "Quên từ hai lần trở lên và chưa nhớ lại vững", "path": "/review"})

    for lc in lessons:  # curriculum order: the earliest lesson with something unfinished
        open_cards = [c for c in lc.cards if c.met and not c.reached]
        if not open_cards:
            continue
        rung = min(serve_rung(c.history, c.use_level) for c in open_cards)
        recs.append(
            {
                "kind": "practice",
                "title": f"Làm bước «{RUNG_LABEL[rung]}» ở bài {lc.title}",
                "subtitle": f"{len(open_cards)} thẻ chưa đạt mức dùng được",
                "lesson_id": lc.lesson_id,
                "skill": "reading" if rung == 0 else "build",
            }
        )
        break

    for lc in lessons:
        fresh = sum(1 for c in lc.cards if not c.met)
        if fresh:
            recs.append(
                {
                    "kind": "learn",
                    "title": f"Học {fresh} thẻ mới ở bài {lc.title}",
                    "subtitle": "Chưa gặp trong ôn tập hay bài tập",
                    "lesson_id": lc.lesson_id,
                }
            )
            break

    if cards and not recs:
        recs.append({"kind": "mix", "title": "Ôn trộn cuối bài", "subtitle": "Mọi thẻ đã đạt mức dùng được; trộn lại để giữ vững", "path": "/lesson"})
    return recs[:limit]

"""Looking back at the talks with Haru — pure logic for the history screens.

- `summary_row`: one line of the session list (when, lesson, how long, how clear, band).
- `insights`: the trend over the last sessions — pronunciation average and band per session, the
  kinds of pronunciation mistakes that keep coming back (counted per session, with the words), and
  the words Haru suggested more than once.
- `notes_from_report`: what "Đưa vào ôn tập" keeps from a session — words to learn and the
  sentences Haru corrected (never the learner's own wording) — for the learner's "Sổ trò chuyện" (and, for words that are lesson cards, the review
  queue; see the router).
- `cards_for_words`: which existing vocabulary card a saved word is (same hangul; a lesson card
  before an article word), so the word is linked to it and enters the review queue. No card is
  ever made up for a word that has none.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Iterable
from typing import Any

from app.services.pronunciation import ISSUE_KINDS


def _report(row: Any) -> dict:
    return row.report if isinstance(getattr(row, "report", None), dict) else {}


def _pron(row: Any) -> dict:
    return row.pronunciation if isinstance(getattr(row, "pronunciation", None), dict) else {}


def summary_row(row: Any, lesson_title: str | None) -> dict[str, Any]:
    report = _report(row)
    pron = _pron(row)
    metrics = row.metrics if isinstance(getattr(row, "metrics", None), dict) else {}
    return {
        "id": row.id,
        "started_at": row.started_at,
        "seconds": int(row.seconds or 0),
        "lesson_title": lesson_title,
        "band": row.band,
        "band_after": metrics.get("band_after"),
        "learner_turns": int(metrics.get("learner_turns") or sum(1 for t in (row.turns or []) if t.get("role") == "learner")),
        "pron_avg": pron.get("average"),
        "headline_vi": report.get("praise_vi") or report.get("summary_vi") or None,
        "topics_vi": list(report.get("topics_vi") or []),
        "has_report": bool(report),
        "saved": row.saved_at is not None,
    }


def insights(rows: list[Any], *, recent: int = 10) -> dict[str, Any]:
    """`rows`: finished sessions, newest first."""
    rows = [r for r in rows if r.ended_at is not None]
    points = [
        {
            "at": r.started_at,
            "pron_avg": _pron(r).get("average"),
            "band": (r.metrics or {}).get("band_after") or r.band,
            "ko_words_per_turn": (r.metrics or {}).get("ko_words_per_turn"),
        }
        for r in reversed(rows[:20])  # oldest first, for a chart
    ]
    window = rows[:recent]
    kind_sessions: Counter[str] = Counter()
    kind_words: dict[str, list[str]] = defaultdict(list)
    word_count: Counter[str] = Counter()
    word_vi: dict[str, str] = {}
    for r in window:
        kinds_here: set[str] = set()
        for item in _pron(r).get("items") or []:
            for issue in item.get("issues") or []:
                kind = issue.get("kind") if issue.get("kind") in ISSUE_KINDS else "other"
                kinds_here.add(kind)
                word = str(issue.get("word") or "").strip()
                if word and word not in kind_words[kind]:
                    kind_words[kind].append(word)
        kind_sessions.update(kinds_here)
        for w in _report(r).get("words") or []:
            ko = str(w.get("ko") or "").strip()
            if ko:
                word_count[ko] += 1
                word_vi.setdefault(ko, str(w.get("vi") or ""))
    checked = sum(1 for r in window if _pron(r).get("items"))
    scores = [p["pron_avg"] for p in points if p["pron_avg"] is not None]
    return {
        "sessions": len(rows),
        "minutes": round(sum(int(r.seconds or 0) for r in rows) / 60),
        "points": points,
        "pron_first": scores[0] if scores else None,
        "pron_last": scores[-1] if scores else None,
        "checked_sessions": checked,
        "issue_kinds": [
            {"kind": k, "label_vi": ISSUE_KINDS[k], "sessions": n, "words": kind_words[k][:6]}
            for k, n in kind_sessions.most_common()
            if k != "other" or n >= 2
        ][:5],
        "repeat_words": [{"ko": k, "vi": word_vi[k], "times": n} for k, n in word_count.most_common() if n >= 2][:8],
    }


def notes_from_report(report: dict) -> list[dict[str, str]]:
    """What "Đưa vào ôn tập" keeps: the words Haru suggested and the sentences Haru CORRECTED (the
    `better` of each fix). Never what the learner said themselves: the pronunciation check copies
    the learner's own sentence (it judges sounds, not meaning), so a muddled or wrong sentence
    would be learned as if it were right; a "fix" that changes nothing is dropped too. Pronunciation
    mistakes are followed in the insights ("Lỗi phát âm hay lặp lại") instead."""
    out: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()

    def add(kind: str, ko: str, vi: str) -> None:
        ko = ko.strip()
        if ko and (kind, ko) not in seen:
            seen.add((kind, ko))
            out.append({"kind": kind, "ko": ko[:300], "vi": vi.strip()[:300]})

    for w in report.get("words") or []:
        add("word", str(w.get("ko") or ""), str(w.get("vi") or ""))
    for f in report.get("fixes") or []:
        better = str(f.get("better") or "").strip()
        if better and better != str(f.get("said") or "").strip():
            add("sentence", better, str(f.get("why_vi") or ""))
    return out


def cards_for_words(words: Iterable[str], cards: Iterable[tuple[int, str, int | None]]) -> dict[str, int]:
    """word -> the vocabulary card it is. `cards` are (id, hangul, lesson_id) rows whose hangul may
    match; the match is on the trimmed text. A lesson card wins over a card that belongs to no
    lesson (a news article's word), then the oldest card (lowest id). Words with no card are left
    out: they stay notes only."""
    wanted = {w.strip() for w in words if w and w.strip()}
    best: dict[str, tuple[tuple[bool, int], int]] = {}
    for card_id, hangul, lesson_id in cards:
        key = (hangul or "").strip()
        if key not in wanted:
            continue
        rank = (lesson_id is None, card_id)
        if key not in best or rank < best[key][0]:
            best[key] = (rank, card_id)
    return {word: card_id for word, (_, card_id) in best.items()}

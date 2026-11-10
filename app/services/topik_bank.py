"""«Kho từ TOPIK»: the intermediate (중급) and advanced (고급) words of 한국어기초사전 (NIKL) that the
lessons do not teach, in topic decks (app/seed/nikl/topik_bank.json, built by
scripts/build_topik_bank.py). A learner adds a deck; its words then come into their daily new cards
like the words of a news article (app/api/routers/content.py get_review_queue), a few a day.

The words are content.vocab_item rows with no lesson and `bank_key` = the dictionary entry id, so
the cards, the audio, the review and the error log work for them as for any word. A word a lesson
teaches is left out of the bank (the lesson's card is the one learned): when a lesson starts
teaching a bank word, the bank row goes, with its schedule.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

BANK_FILE = Path(__file__).resolve().parents[1] / "seed" / "nikl" / "topik_bank.json"
LEVEL = {"mid": 4, "adv": 6}  # the course's 1–6 scale: trung cấp = 3–4, cao cấp = 5–6
POS_LABEL = {"N": "danh từ", "V": "động từ", "A": "tính từ", "X": "khác"}
CONFIG_NAME = "topik_bank_sync"


@dataclass(frozen=True)
class Deck:
    key: str
    title_vi: str
    grade: str
    grade_vi: str
    words: tuple[int, ...]  # dictionary entry ids, in the deck's order


@lru_cache(maxsize=1)
def load() -> dict[str, Any]:
    return json.loads(BANK_FILE.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def decks() -> dict[str, Deck]:
    return {
        d["key"]: Deck(d["key"], d["title_vi"], d["grade"], d["grade_vi"], tuple(d["words"]))
        for d in load()["decks"]
    }


DECK_LESSONS_FILE = BANK_FILE.with_name("deck_lessons.json")


@lru_cache(maxsize=1)
def lesson_decks() -> dict[str, list[str]]:
    """lesson slug -> the deck keys that extend it, closest first (app/seed/nikl/deck_lessons.json:
    {deck_key: {"lessons": [slug, ...]}}). A learner who finishes the lesson is offered these decks."""
    if not DECK_LESSONS_FILE.exists():
        return {}
    out: dict[str, list[str]] = {}
    known = decks()
    for key, entry in json.loads(DECK_LESSONS_FILE.read_text(encoding="utf-8")).items():
        if key not in known:
            continue
        for rank, slug in enumerate(entry.get("lessons", [])):
            out.setdefault(slug, []).append((rank, key))  # type: ignore[arg-type]
    return {slug: [k for _, k in sorted(pairs)] for slug, pairs in out.items()}


@lru_cache(maxsize=1)
def words() -> dict[int, dict[str, Any]]:
    return {w["id"]: w for w in load()["words"]}


def row_fields(w: dict[str, Any]) -> dict[str, Any]:
    """The vocab_item columns of one bank word."""
    deck = decks()[w["deck"]]
    return {
        "hangul": w["w"],
        "pos": POS_LABEL.get(w["pos"], "khác"),
        "meaning_vi": w["meaning_vi"][:255],
        "definition_ko": w.get("definition_ko"),
        "level": LEVEL[w["grade"]],
        "hanja": w.get("hanja"),
        "sino_vietnamese": w.get("sino_vietnamese"),
        "example_ko": w.get("example_ko"),
        "example_vi": None,  # the dictionary's examples have no translation
        "usage_note_vi": w.get("note_vi"),
        "pron_ko": w.get("pron"),
        "family": f"TOPIK {deck.grade_vi.lower()} · {deck.title_vi}"[:120],
        "priority": "recognize",
    }


def _fingerprint(lesson_words: set[str]) -> str:
    h = hashlib.sha256(BANK_FILE.read_bytes())
    h.update("\n".join(sorted(lesson_words)).encode("utf-8"))
    return h.hexdigest()


def sync_bank(db: Any) -> dict[str, int]:
    """Bring the bank's vocab_item rows in line with the file (sync Session). Skipped when neither
    the file nor the set of lesson words changed since the last run."""
    from sqlalchemy import delete, select

    from app.models import AppConfig, ErrorLog, ItemState, VocabItem, VocabItemAudio

    lesson_words = set(db.execute(select(VocabItem.hangul).where(VocabItem.lesson_id.isnot(None))).scalars())
    stamp = _fingerprint(lesson_words)
    cfg = db.get(AppConfig, (CONFIG_NAME, 1))
    if cfg is not None and (cfg.value or {}).get("fingerprint") == stamp:
        return {}

    wanted = {wid: w for wid, w in words().items() if w["w"] not in lesson_words}
    have = {r.bank_key: r for r in db.execute(select(VocabItem).where(VocabItem.bank_key.isnot(None))).scalars()}
    added = changed = 0
    for wid, w in wanted.items():
        fields = row_fields(w)
        row = have.pop(wid, None)
        if row is None:
            db.add(VocabItem(lesson_id=None, bank_key=wid, **fields))
            added += 1
            continue
        if any(getattr(row, k) != v for k, v in fields.items()):
            for k, v in fields.items():
                setattr(row, k, v)
            changed += 1
    gone = [r.id for r in have.values()]
    if gone:
        db.execute(delete(ItemState).where(ItemState.item_type == "vocab_item", ItemState.item_id.in_(gone)))
        db.execute(delete(ErrorLog).where(ErrorLog.item_type == "vocab_item", ErrorLog.item_id.in_(gone)))
        db.execute(delete(VocabItemAudio).where(VocabItemAudio.vocab_item_id.in_(gone)))
        db.execute(delete(VocabItem).where(VocabItem.id.in_(gone)))
    if cfg is None:
        db.add(AppConfig(name=CONFIG_NAME, version=1, value={"fingerprint": stamp}, active=True))
    else:
        cfg.value = {"fingerprint": stamp}
    db.commit()
    return {"added": added, "changed": changed, "removed": len(gone)}


def deck_title(key: str) -> str | None:
    d = decks().get(key)
    return f"Kho từ TOPIK · {d.grade_vi} · {d.title_vi}" if d else None

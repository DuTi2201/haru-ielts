"""Curated editorial articles, kept as JSON in app/seed/editorial/ and loaded by hand.

Two kinds of record (see the files):
  * NEW      has `source_url` + `body_ko` -> inserted (or refreshed when the url is already there);
  * REPAIR   has `article_id_prefix`      -> the vocab / grammar / outline / links / practice of an
             article already in the database are replaced; its body is never touched.

A word or pattern the course (or an earlier article) already teaches is LINKED (its id goes into
vocab_ids / grammar_ids), never filed twice: same rule as ingestion._existing_card. Only a word
nobody teaches yet becomes a new card (lesson_id NULL).

    python -m app.services.editorial_seed --dry-run     # everything in one transaction, rolled back
    python -m app.services.editorial_seed               # for real
"""

from __future__ import annotations

import argparse
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.models import EditorialArticle, GrammarPoint, Lesson, VocabItem
from app.services import lesson_extract
from app.services.ingestion import _existing_card

log = logging.getLogger("editorial_seed")
SEED_DIR = Path(__file__).resolve().parent.parent / "seed" / "editorial"

_VOCAB_COLS = (
    "hangul", "pos", "meaning_vi", "definition_ko", "level", "hanja", "sino_vietnamese",
    "example_ko", "example_vi", "usage_note_vi", "register", "exam",
)
_GRAMMAR_COLS = (
    "pattern", "meaning_vi", "level", "example_ko", "example_vi", "usage_context_vi", "topik_tip_vi",
    "contrast_group", "contrasts",
)
_REGISTER = {"văn viết": "written", "văn nói": "spoken", "written": "written", "spoken": "spoken", "neutral": "neutral"}


def _vocab_row(card: dict[str, Any]) -> dict[str, Any]:
    data = {k: card.get(k) for k in _VOCAB_COLS if card.get(k) is not None}
    data["register"] = _REGISTER.get(str(card.get("register") or "").lower())
    note = (card.get("usage_note_vi") or "").strip()
    colls = [c for c in (card.get("collocations") or []) if isinstance(c, str)]
    if colls:
        note = (note + "\nHay đi với: " + " · ".join(colls)).strip()
    data["usage_note_vi"] = note or None
    data["level"] = int(card.get("level") or 4)
    lesson_extract.tidy_vocab(data)
    data.pop("collocations", None)
    return data


def _grammar_row(card: dict[str, Any]) -> dict[str, Any]:
    data = {k: card.get(k) for k in _GRAMMAR_COLS if card.get(k) is not None}
    data["level"] = int(card.get("level") or 4)
    lesson_extract.tidy_grammar(data)
    return data


def _link_or_create(db: Session, kind: str, new: list[dict], reuse: list[str], stats: dict) -> list[int]:
    model = VocabItem if kind == "vocab_item" else GrammarPoint
    key = "hangul" if kind == "vocab_item" else "pattern"
    ids: list[int] = []

    def add(row_id: int) -> None:
        if row_id not in ids:
            ids.append(row_id)

    for name in reuse:
        found = _existing_card(db, kind, {key: name})
        if found is None:
            stats["missing_reuse"].append(f"{kind}:{name}")
            continue
        add(found)
        stats["linked"] += 1
    for card in new:
        found = _existing_card(db, kind, {key: card[key]})
        if found is not None:
            add(found)
            stats["linked"] += 1
            continue
        data = _vocab_row(card) if kind == "vocab_item" else _grammar_row(card)
        row = model(lesson_id=None, **data)
        db.add(row)
        db.flush()
        add(row.id)
        stats["created"] += 1
    return ids


def _drop_orphans(db: Session, kind: str, old_ids: list[int], keep: set[int], stats: dict) -> None:
    """An article-only card the repaired article no longer lists is deleted — unless another
    article still lists it or a learner already has a review state on it."""
    model = VocabItem if kind == "vocab_item" else GrammarPoint
    column = "vocab_ids" if kind == "vocab_item" else "grammar_ids"
    for card_id in old_ids:
        if card_id in keep:
            continue
        row = db.get(model, card_id)
        if row is None or row.lesson_id is not None:
            continue
        used = db.execute(
            text(f"select 1 from editorial.editorial_article where :i = any({column}) limit 1"), {"i": card_id}
        ).first()
        studied = db.execute(
            text("select 1 from item_state where item_type = :t and item_id = :i limit 1"),
            {"t": kind, "i": card_id},
        ).first()
        if used or studied:
            continue
        db.delete(row)
        stats["dropped"] += 1


def _apply(db: Session, rec: dict[str, Any], article: EditorialArticle, old_vocab: list[int], old_grammar: list[int], stats: dict) -> None:
    vocab = _link_or_create(db, "vocab_item", rec.get("vocab", []), rec.get("reuse_vocab", []), stats)
    grammar = _link_or_create(db, "grammar_point", rec.get("grammar", []), rec.get("reuse_grammar", []), stats)
    article.vocab_ids = vocab
    article.grammar_ids = grammar
    article.level_estimate = rec["level_estimate"]
    article.topic_tags = rec["topic_tags"]
    article.model_outline = rec["model_outline"]
    article.thinking_guide_text = rec["thinking_guide_text"]
    ids = [
        lid
        for slug in rec["related_lesson_slugs"]
        if (lid := db.execute(select(Lesson.id).where(Lesson.slug == slug)).scalar_one_or_none()) is not None
    ]
    if len(ids) != len(rec["related_lesson_slugs"]):
        stats["missing_lessons"].append(rec.get("title_ko") or rec.get("article_id_prefix"))
    article.related_lesson_ids = ids
    article.unlock_hint = rec["unlock_hint"]
    article.practice = rec["practice"]
    db.add(article)
    db.flush()
    _drop_orphans(db, "vocab_item", old_vocab, set(vocab), stats)
    _drop_orphans(db, "grammar_point", old_grammar, set(grammar), stats)


def load(db: Session) -> dict[str, Any]:
    stats: dict[str, Any] = {"articles_new": 0, "articles_updated": 0, "repaired": 0, "created": 0,
                             "linked": 0, "dropped": 0, "missing_reuse": [], "missing_article": [], "missing_lessons": []}
    for path in sorted(SEED_DIR.glob("*.json")):
        for rec in json.loads(path.read_text(encoding="utf-8")):
            if "article_id_prefix" in rec:
                row = db.execute(
                    text("select id from editorial.editorial_article where id::text like :p"),
                    {"p": rec["article_id_prefix"] + "%"},
                ).first()
                if row is None:
                    stats["missing_article"].append(rec["article_id_prefix"])
                    continue
                article = db.get(EditorialArticle, row[0])
                _apply(db, rec, article, list(article.vocab_ids or []), list(article.grammar_ids or []), stats)
                stats["repaired"] += 1
                continue
            article = db.execute(
                select(EditorialArticle).where(EditorialArticle.source_url == rec["source_url"])
            ).scalar_one_or_none()
            old_v: list[int] = []
            old_g: list[int] = []
            if article is None:
                article = EditorialArticle(source_name=rec["source_name"], source_url=rec["source_url"], study_status="none")
                stats["articles_new"] += 1
            else:
                old_v, old_g = list(article.vocab_ids or []), list(article.grammar_ids or [])
                stats["articles_updated"] += 1
            article.source_name = rec["source_name"]
            article.title_ko = rec["title_ko"]
            article.body_ko = rec["body_ko"]
            if rec.get("published_date"):
                article.published_date = datetime.fromisoformat(rec["published_date"]).replace(tzinfo=timezone.utc)
            _apply(db, rec, article, old_v, old_g, stats)
    return stats


def main() -> None:
    from app.workers.tasks import _sync_engine

    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    with Session(_sync_engine) as db:
        stats = load(db)
        if args.dry_run:
            db.rollback()
        else:
            db.commit()
    print(json.dumps(stats, ensure_ascii=False, indent=1), "(dry-run, rolled back)" if args.dry_run else "(committed)")


if __name__ == "__main__":
    main()

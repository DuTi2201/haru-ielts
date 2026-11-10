"""Retire five editorial articles the course does not need.

Chosen with the owner after the editorial audit:
* a36a092f… [여적] 여명학교 — the same event as [사설] 여명학교 교장 '눈물' 호소, which stays;
* 0d149350… [정동칼럼] 미 국채시장, 마이런 보고서의 관점 — US bond-market detail, far from TOPIK II;
* 85ab1aba… [정보라의 세상 속으로] 입장이 없다 — a one-off dispute between named parties;
* 7a1d60a5… [정동칼럼] 공무원 헌법교육의 방향 — built on a contested domestic political event;
* 17c169a6… [여적] '살상 무기' 최루탄 — a short historical news item, not an argument piece.

Each article goes with its outline submissions; an import batch keeps its history but loses the
link. The article's own cards (lesson_id NULL) go too unless another article lists them — with
the learners' review rows of those cards (they were only reachable through this article).
Course cards an article listed are never touched.

Revision ID: d7a2c4e6f8b1
Revises: c5e1a7d3f9b2
"""
from alembic import op
from sqlalchemy import text

revision = "d7a2c4e6f8b1"
down_revision = "c5e1a7d3f9b2"
branch_labels = None
depends_on = None

ARTICLES = (
    "a36a092f-1cd6-4948-bcdf-ecd5f80736d3",
    "0d149350-cd7f-4643-bffc-6490a6fdd093",
    "85ab1aba-c342-4362-951a-f073efa6093e",
    "7a1d60a5-d7a3-499e-b256-c0a56c5a4c10",
    "17c169a6-6c38-4903-8347-102438cdeb12",
)


def _drop(conn, table: str, state: str, cid: int) -> None:
    conn.execute(text("DELETE FROM public.item_state WHERE item_type = :t AND item_id = :c"), {"t": state, "c": cid})
    conn.execute(text("DELETE FROM public.error_log WHERE item_type = :t AND item_id = :c"), {"t": state, "c": cid})
    if state == "vocab_item":
        conn.execute(text("DELETE FROM audio.vocab_item_audio WHERE vocab_item_id = :c"), {"c": cid})
        conn.execute(text("UPDATE public.talk_note SET vocab_item_id = NULL WHERE vocab_item_id = :c"), {"c": cid})
    else:
        conn.execute(text("DELETE FROM public.grammar_competency WHERE grammar_id = :c"), {"c": cid})
        conn.execute(
            text("UPDATE corpus.corpus_item SET grammar_point_ids = array_remove(grammar_point_ids, :c) WHERE :c = ANY(grammar_point_ids)"),
            {"c": cid},
        )
    conn.execute(text(f"DELETE FROM {table} WHERE id = :c"), {"c": cid})


def upgrade() -> None:
    conn = op.get_bind()
    ids = [
        r[0]
        for r in conn.execute(
            text("SELECT id::text FROM editorial.editorial_article WHERE id = ANY(CAST(:p AS uuid[]))"), {"p": list(ARTICLES)}
        ).all()
    ]
    others = "SELECT 1 FROM editorial.editorial_article o WHERE o.id <> ALL(CAST(:ids AS uuid[])) AND :cid = ANY(o.{col})"
    for kind, table, col, state in (
        ("vocab", "content.vocab_item", "vocab_ids", "vocab_item"),
        ("grammar", "content.grammar_point", "grammar_ids", "grammar_point"),
    ):
        cards = {
            c
            for (arr,) in conn.execute(
                text(f"SELECT {col} FROM editorial.editorial_article WHERE id = ANY(CAST(:ids AS uuid[]))"), {"ids": ids}
            ).all()
            for c in (arr or [])
        }
        for cid in sorted(cards):
            row = conn.execute(text(f"SELECT lesson_id FROM {table} WHERE id = :c"), {"c": cid}).first()
            if row is None or row[0] is not None:
                continue  # gone already, or a course card
            if conn.execute(text(others.format(col=col)), {"ids": ids, "cid": cid}).first():
                continue  # another article still lists it
            _drop(conn, table, state, cid)
    conn.execute(
        text("DELETE FROM editorial.editorial_outline_submission WHERE editorial_article_id = ANY(CAST(:ids AS uuid[]))"), {"ids": ids}
    )
    conn.execute(
        text("UPDATE public.import_batch SET editorial_article_id = NULL WHERE editorial_article_id = ANY(CAST(:ids AS uuid[]))"), {"ids": ids}
    )
    conn.execute(text("DELETE FROM editorial.editorial_article WHERE id = ANY(CAST(:ids AS uuid[]))"), {"ids": ids})
    # an article-owned card no article lists any more (these five, or an earlier rollback) is dropped
    for table, col, state in (("content.vocab_item", "vocab_ids", "vocab_item"), ("content.grammar_point", "grammar_ids", "grammar_point")):
        loose = [
            r[0]
            for r in conn.execute(text(
                f"SELECT c.id FROM {table} c WHERE c.lesson_id IS NULL"
                f" AND NOT EXISTS (SELECT 1 FROM editorial.editorial_article e WHERE c.id = ANY(e.{col}))"
            )).all()
        ]
        for cid in loose:
            _drop(conn, table, state, cid)


def downgrade() -> None:
    # the articles came from scraped pages; re-import them from Studio if ever needed
    pass

"""Kho từ TOPIK: vocab_item.bank_key and learner_bank_deck

Revision ID: b5d9f1a3c7e2
Revises: a2c6e8f0b4d7

* content.vocab_item.bank_key — the 한국어기초사전 entry id of a word of the TOPIK word bank
  (app/services/topik_bank.py); such a word has no lesson. NULL for every existing row.
* learner_bank_deck — the decks of the bank a learner has added to their reviews.
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "b5d9f1a3c7e2"
down_revision = "a2c6e8f0b4d7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("vocab_item", sa.Column("bank_key", sa.Integer(), nullable=True), schema="content")
    op.create_index(
        "ux_vocab_item_bank_key",
        "vocab_item",
        ["bank_key"],
        unique=True,
        schema="content",
        postgresql_where=sa.text("bank_key IS NOT NULL"),
    )
    op.create_table(
        "learner_bank_deck",
        sa.Column("learner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("profiles.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("deck_key", sa.String(64), primary_key=True),
        sa.Column("added_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("learner_bank_deck")
    op.drop_index("ux_vocab_item_bank_key", table_name="vocab_item", schema="content")
    op.drop_column("vocab_item", "bank_key", schema="content")

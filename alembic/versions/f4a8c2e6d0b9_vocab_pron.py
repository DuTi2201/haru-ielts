"""vocab_item.pron_ko: how a word is read when that differs from its spelling ("[학쌩]").

Revision ID: f4a8c2e6d0b9
Revises: e2f6a9c3b8d1
"""
import sqlalchemy as sa
from alembic import op

revision = "f4a8c2e6d0b9"
down_revision = "e2f6a9c3b8d1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("vocab_item", sa.Column("pron_ko", sa.String(160), nullable=True), schema="content")


def downgrade() -> None:
    op.drop_column("vocab_item", "pron_ko", schema="content")

"""grammar_point.check_item: the card's one self-check question

Revision ID: b8d4f0a2c6e3
Revises: a7c3e9d1b5f2
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "b8d4f0a2c6e3"
down_revision = "a7c3e9d1b5f2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("grammar_point", sa.Column("check_item", postgresql.JSONB(), nullable=True), schema="content")


def downgrade() -> None:
    op.drop_column("grammar_point", "check_item", schema="content")

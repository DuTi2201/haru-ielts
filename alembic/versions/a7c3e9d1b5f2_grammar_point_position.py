"""grammar_point.position: the author's card order within a lesson

Revision ID: a7c3e9d1b5f2
Revises: f9a2b4c6d8e0
"""
import sqlalchemy as sa
from alembic import op

revision = "a7c3e9d1b5f2"
down_revision = "f9a2b4c6d8e0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "grammar_point",
        sa.Column("position", sa.SmallInteger(), nullable=False, server_default="0"),
        schema="content",
    )


def downgrade() -> None:
    op.drop_column("grammar_point", "position", schema="content")

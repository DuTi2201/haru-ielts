"""grammar_point.step_vi: the lesson step a card belongs to (names the card tabs)

Revision ID: c9e5a1b3d7f4
Revises: b8d4f0a2c6e3
"""
import sqlalchemy as sa
from alembic import op

revision = "c9e5a1b3d7f4"
down_revision = "b8d4f0a2c6e3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("grammar_point", sa.Column("step_vi", sa.String(length=40), nullable=True), schema="content")


def downgrade() -> None:
    op.drop_column("grammar_point", "step_vi", schema="content")

"""Lông vũ (feathers): the parts of the alphabet lesson a learner has finished (its other feathers
come from records that already exist: cards marked and questions answered), and what the swan has
earned for good from the support topics (their relics and its sparkle).

Revision ID: c5e2a8f1d4b7
Revises: b4d1f7a2c9e3
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "c5e2a8f1d4b7"
down_revision = "b4d1f7a2c9e3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "lesson_part_done",
        sa.Column("learner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("profiles.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("lesson_id", sa.Integer(), sa.ForeignKey("content.lesson.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("part_id", sa.String(16), primary_key=True),
        sa.Column("done_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.add_column("journey", sa.Column("relics", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=False))
    op.add_column("journey", sa.Column("sparkle", sa.SmallInteger(), server_default="0", nullable=False))


def downgrade() -> None:
    op.drop_column("journey", "sparkle")
    op.drop_column("journey", "relics")
    op.drop_table("lesson_part_done")

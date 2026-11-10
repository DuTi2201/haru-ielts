"""presentation_session: "Trình bày với Haru" rounds

Revision ID: f6b2d8a4c1e7
Revises: e4a8c2d6f0b5

One row per "Trình bày" round: the topic, the learner's notes and keyword outline, and up to three
marked tries at saying the answer in one go (app.services.presentation). The audio is not kept.
A new table only: nothing existing changes.
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "f6b2d8a4c1e7"
down_revision = "e4a8c2d6f0b5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "presentation_session",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("learner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("lesson_id", sa.Integer(), sa.ForeignKey("content.lesson.id", ondelete="SET NULL"), nullable=True),
        sa.Column("band", sa.SmallInteger(), nullable=False),
        sa.Column("level", sa.SmallInteger(), nullable=False, server_default="1"),
        sa.Column("topic", postgresql.JSONB(), nullable=False),
        sa.Column("notes_vi", sa.Text(), nullable=False, server_default=""),
        sa.Column("outline", postgresql.JSONB(), nullable=True),
        sa.Column("attempts", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_presentation_session_learner_id", "presentation_session", ["learner_id"])
    op.create_index("ix_presentation_session_created_at", "presentation_session", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_presentation_session_created_at", table_name="presentation_session")
    op.drop_index("ix_presentation_session_learner_id", table_name="presentation_session")
    op.drop_table("presentation_session")

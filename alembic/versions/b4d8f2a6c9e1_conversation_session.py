"""conversation_session: "Trò chuyện với Haru" voice sessions

Revision ID: b4d8f2a6c9e1
Revises: a8c2e4f6b1d3

One row per spoken session with Haru (Gemini Live). The audio stays between the browser and
Gemini; the row keeps the transcript, duration (for the daily minute cap), nudge count and the
end-of-session report. A new table only: nothing existing changes.
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "b4d8f2a6c9e1"
down_revision = "a8c2e4f6b1d3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "conversation_session",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("learner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("lesson_id", sa.Integer(), sa.ForeignKey("content.lesson.id", ondelete="SET NULL"), nullable=True),
        sa.Column("model", sa.String(64), nullable=False),
        sa.Column("remember", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("seconds", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("nudges", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("turns", postgresql.JSONB(), nullable=True),
        sa.Column("report", postgresql.JSONB(), nullable=True),
    )
    op.create_index("ix_conversation_session_learner_id", "conversation_session", ["learner_id"])
    op.create_index("ix_conversation_session_started_at", "conversation_session", ["started_at"])


def downgrade() -> None:
    op.drop_index("ix_conversation_session_started_at", table_name="conversation_session")
    op.drop_index("ix_conversation_session_learner_id", table_name="conversation_session")
    op.drop_table("conversation_session")

"""learner_talk_profile + conversation_session band / metrics / pronunciation

Revision ID: c7e1a3f5d9b2
Revises: b4d8f2a6c9e1

"Trò chuyện với Haru" phases 2-3. A per-learner profile of how Haru talks to them (band 1-5 that
moves with their sessions, the last topics, the thread to pick up, and — only with consent — a few
things they told about themselves). Each session row also keeps the band it ran at, what it
measured and the per-sentence pronunciation check (no audio). New nullable columns and a new
table: nothing existing changes.
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "c7e1a3f5d9b2"
down_revision = "b4d8f2a6c9e1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("conversation_session", sa.Column("band", sa.SmallInteger(), nullable=True))
    op.add_column("conversation_session", sa.Column("metrics", postgresql.JSONB(), nullable=True))
    op.add_column("conversation_session", sa.Column("pronunciation", postgresql.JSONB(), nullable=True))
    op.create_table(
        "learner_talk_profile",
        sa.Column("learner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("profiles.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("band", sa.SmallInteger(), nullable=True),
        sa.Column("verdicts", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("facts", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("last_topics", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("follow_up", sa.Text(), nullable=True),
        sa.Column("sessions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("learner_talk_profile")
    op.drop_column("conversation_session", "pronunciation")
    op.drop_column("conversation_session", "metrics")
    op.drop_column("conversation_session", "band")

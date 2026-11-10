"""debates: Tranh luận · Đàm phán · Phản biện with Haru

Revision ID: c8e2a6d4f9b1
Revises: a3d7f1c9e5b2

Debate sessions are Gemini Live sessions like the talks, so they live in conversation_session with
kind = 'debate' and the scenario played; existing rows are talks. learner_talk_profile gains the
debate band and the verdicts that move it. Columns and one index only.
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "c8e2a6d4f9b1"
down_revision = "a3d7f1c9e5b2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("conversation_session", sa.Column("kind", sa.String(10), nullable=False, server_default="talk"))
    op.add_column("conversation_session", sa.Column("scenario", postgresql.JSONB(), nullable=True))
    op.create_index("ix_conversation_session_kind", "conversation_session", ["kind"])
    op.add_column("learner_talk_profile", sa.Column("debate_band", sa.SmallInteger(), nullable=True))
    op.add_column("learner_talk_profile", sa.Column("debate_verdicts", postgresql.JSONB(), nullable=False, server_default="[]"))


def downgrade() -> None:
    op.drop_column("learner_talk_profile", "debate_verdicts")
    op.drop_column("learner_talk_profile", "debate_band")
    op.drop_index("ix_conversation_session_kind", table_name="conversation_session")
    op.drop_column("conversation_session", "scenario")
    op.drop_column("conversation_session", "kind")

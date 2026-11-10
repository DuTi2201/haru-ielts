"""talk history: conversation_session.saved_at + talk_note ("Sổ trò chuyện")

Revision ID: d2f6b8a4e1c3
Revises: c7e1a3f5d9b2

The history of talks with Haru can send a session's words and sentences to the learner's
notebook ("Đưa vào ôn tập"): a talk_note row per word / sentence (one per learner and text), and
the session remembers that it was saved. New table and a nullable column only.
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "d2f6b8a4e1c3"
down_revision = "c7e1a3f5d9b2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("conversation_session", sa.Column("saved_at", sa.DateTime(timezone=True), nullable=True))
    op.create_table(
        "talk_note",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("learner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("conversation_session.id", ondelete="SET NULL"), nullable=True),
        sa.Column("kind", sa.String(10), nullable=False),
        sa.Column("ko", sa.String(300), nullable=False),
        sa.Column("vi", sa.String(300), nullable=False, server_default=""),
        sa.Column("vocab_item_id", sa.Integer(), nullable=True),
        sa.Column("done_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("learner_id", "kind", "ko", name="uq_talk_note_learner_kind_ko"),
    )
    op.create_index("ix_talk_note_learner_id", "talk_note", ["learner_id"])


def downgrade() -> None:
    op.drop_index("ix_talk_note_learner_id", table_name="talk_note")
    op.drop_table("talk_note")
    op.drop_column("conversation_session", "saved_at")

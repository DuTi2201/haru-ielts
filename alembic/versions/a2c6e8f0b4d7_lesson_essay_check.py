"""lesson_essay_check: the AI check of a paragraph written for a lesson

Revision ID: a2c6e8f0b4d7
Revises: d8b4f2a6c3e9

One new table, nothing else changes. A row is one check the learner asked for on a lesson's
`write_essay` item: the text, the job that checks it and the result (app.services.essay_check).
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "a2c6e8f0b4d7"
down_revision = "d8b4f2a6c3e9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "lesson_essay_check",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("learner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("lesson_id", sa.Integer(), sa.ForeignKey("content.lesson.id", ondelete="CASCADE"), nullable=False),
        sa.Column("exercise_id", sa.String(32), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("result", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_lesson_essay_check_learner_id", "lesson_essay_check", ["learner_id"])
    op.create_index("ix_lesson_essay_check_lesson_id", "lesson_essay_check", ["lesson_id"])


def downgrade() -> None:
    op.drop_index("ix_lesson_essay_check_lesson_id", table_name="lesson_essay_check")
    op.drop_index("ix_lesson_essay_check_learner_id", table_name="lesson_essay_check")
    op.drop_table("lesson_essay_check")

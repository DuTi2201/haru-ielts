"""mistake book: "Đã hiểu" on a wrong practice answer

* lesson_exercise_result.understood_at — set when the learner marks a mistake as understood in the
  mistake book (Sổ lỗi sai); the next wrong answer to the question clears it.

Revision ID: b8d2f4a6c1e3
Revises: a4c7e1b9d2f6
Create Date: 2026-10-11 17:30:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'b8d2f4a6c1e3'
down_revision = 'a4c7e1b9d2f6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('lesson_exercise_result', sa.Column('understood_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('lesson_exercise_result', 'understood_at')

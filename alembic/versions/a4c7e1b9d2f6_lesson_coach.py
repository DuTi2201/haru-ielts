"""lesson coach block: the "Việc cần làm" at the top of a lesson

* content.lesson.coach — JSONB, NULL = the lesson has none (see app.services.lesson_seed.CoachSeed);
  the lesson seed fills it.

Revision ID: a4c7e1b9d2f6
Revises: e2c7a9d4f6b1
Create Date: 2026-10-11 16:30:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'a4c7e1b9d2f6'
down_revision = 'e2c7a9d4f6b1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('lesson', sa.Column('coach', postgresql.JSONB(astext_type=sa.Text()), nullable=True), schema='content')


def downgrade() -> None:
    op.drop_column('lesson', 'coach', schema='content')

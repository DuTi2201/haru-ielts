"""lesson sessions: the lesson cut into sittings by hand

* content.lesson.sessions — JSONB, NULL = the app cuts the lesson evenly (see
  app.services.lesson_seed.SessionSeed); the lesson seed fills it.

Revision ID: d8f3b6a2c4e1
Revises: c7e1a5b9d3f2
Create Date: 2026-11-05 18:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'd8f3b6a2c4e1'
down_revision = 'c7e1a5b9d3f2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('lesson', sa.Column('sessions', postgresql.JSONB(astext_type=sa.Text()), nullable=True), schema='content')


def downgrade() -> None:
    op.drop_column('lesson', 'sessions', schema='content')

"""editorial.editorial_read — which articles a learner has read to the end

A short beginner passage has no outline to write, so the learner marks it read; Today then moves on
to the next article instead of offering the same one again.

Revision ID: b7d2f9a4c1e6
Revises: a1c5e8f2b7d4
Create Date: 2026-11-06 17:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'b7d2f9a4c1e6'
down_revision = 'a1c5e8f2b7d4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'editorial_read',
        sa.Column('learner_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('profiles.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('editorial_article_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        schema='editorial',
    )


def downgrade() -> None:
    op.drop_table('editorial_read', schema='editorial')

"""vocab priority: which words to learn now and which only to recognise

* content.vocab_item.priority — "core" (learn it now) | "recognize" (understand it when met) or
  NULL (a word taken from an article, which belongs to no lesson). The seed loader fills it.

Revision ID: d6b1f3a8c2e5
Revises: c9f4b2a7e1d3
Create Date: 2026-10-10 20:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'd6b1f3a8c2e5'
down_revision = 'c9f4b2a7e1d3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('vocab_item', sa.Column('priority', sa.String(length=12), nullable=True), schema='content')


def downgrade() -> None:
    op.drop_column('vocab_item', 'priority', schema='content')

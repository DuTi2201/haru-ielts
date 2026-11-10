"""grammar revisits: a card that teaches an earlier card again (spaced review)

* content.grammar_point.revisits — the `pattern` of the earlier card; NULL for a first teaching.

Revision ID: e9b4d7a1c3f5
Revises: d8f3b6a2c4e1
Create Date: 2026-11-05 18:40:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'e9b4d7a1c3f5'
down_revision = 'd8f3b6a2c4e1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('grammar_point', sa.Column('revisits', sa.String(length=160), nullable=True), schema='content')


def downgrade() -> None:
    op.drop_column('grammar_point', 'revisits', schema='content')

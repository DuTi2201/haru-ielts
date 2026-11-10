"""grammar graph: what a card is built on, and how much of it a learner must keep

* content.grammar_point.builds_on — JSONB list of the `pattern`s of the earlier cards this card is
  made of or rests on (NULL = none); the lesson seed fills it.
* content.grammar_point.importance — "must" (Bắt buộc) | "normal" (Bổ trợ), or NULL on the
  extension cards, which carry `use_level` instead.

Revision ID: e2c7a9d4f6b1
Revises: d6b1f3a8c2e5
Create Date: 2026-10-10 21:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'e2c7a9d4f6b1'
down_revision = 'd6b1f3a8c2e5'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('grammar_point', sa.Column('builds_on', postgresql.JSONB(astext_type=sa.Text()), nullable=True), schema='content')
    op.add_column('grammar_point', sa.Column('importance', sa.String(length=8), nullable=True), schema='content')


def downgrade() -> None:
    op.drop_column('grammar_point', 'importance', schema='content')
    op.drop_column('grammar_point', 'builds_on', schema='content')

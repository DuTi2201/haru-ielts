"""exam tag: a word or grammar card can be part of an exam course too (KIIP)

* content.vocab_item.exam / content.grammar_point.exam — "kiip-1" … "kiip-5" (the stage of the
  사회통합프로그램 course the item belongs to) or NULL. A note keeps its tag inside the lesson's
  `notes` JSON, so it needs no column.

Revision ID: b8e3c5a1d7f2
Revises: a2d7f4b8c1e6
Create Date: 2026-10-09 12:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'b8e3c5a1d7f2'
down_revision = 'a2d7f4b8c1e6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('vocab_item', sa.Column('exam', sa.String(length=16), nullable=True), schema='content')
    op.add_column('grammar_point', sa.Column('exam', sa.String(length=16), nullable=True), schema='content')


def downgrade() -> None:
    op.drop_column('grammar_point', 'exam', schema='content')
    op.drop_column('vocab_item', 'exam', schema='content')

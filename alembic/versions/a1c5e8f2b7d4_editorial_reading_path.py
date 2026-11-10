"""editorial reading path: which course lessons an article follows, a hint, and practice after reading

* editorial.editorial_article.related_lesson_ids — the course lessons whose topic/words the article
  reinforces (closest first); the reading path offers the article once the learner has been through the first;
* editorial.editorial_article.unlock_hint — one Vietnamese line: when to read it;
* editorial.editorial_article.practice — the questions asked right after reading (JSON list).

Revision ID: a1c5e8f2b7d4
Revises: e9b4d7a1c3f5
Create Date: 2026-11-06 09:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'a1c5e8f2b7d4'
down_revision = 'e9b4d7a1c3f5'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'editorial_article',
        sa.Column('related_lesson_ids', postgresql.ARRAY(sa.Integer()), server_default='{}', nullable=False),
        schema='editorial',
    )
    op.add_column('editorial_article', sa.Column('unlock_hint', sa.Text(), nullable=True), schema='editorial')
    op.add_column('editorial_article', sa.Column('practice', postgresql.JSONB(), nullable=True), schema='editorial')


def downgrade() -> None:
    op.drop_column('editorial_article', 'practice', schema='editorial')
    op.drop_column('editorial_article', 'unlock_hint', schema='editorial')
    op.drop_column('editorial_article', 'related_lesson_ids', schema='editorial')

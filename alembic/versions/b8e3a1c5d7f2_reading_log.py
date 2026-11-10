"""reading_log — the reading and dialogue offered to a learner each day

Revision ID: b8e3a1c5d7f2
Revises: a7d2f9c4e1b6
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'b8e3a1c5d7f2'
down_revision = 'a7d2f9c4e1b6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'reading_log',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('learner_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('profiles.id'), nullable=False),
        sa.Column('day', sa.Date(), nullable=False),
        sa.Column('passage_id', sa.String(80), nullable=False),
        sa.Column('kind', sa.String(16), nullable=False),
        sa.Column('picked_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('correct', sa.SmallInteger(), nullable=True),
        sa.Column('total', sa.SmallInteger(), nullable=True),
        sa.UniqueConstraint('learner_id', 'day', 'passage_id', name='uq_reading_log_learner_day_text'),
    )
    op.create_index('ix_reading_log_learner_id', 'reading_log', ['learner_id'])


def downgrade() -> None:
    op.drop_index('ix_reading_log_learner_id', table_name='reading_log')
    op.drop_table('reading_log')

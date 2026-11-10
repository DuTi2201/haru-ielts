"""real_exam_set, real_exam_attempt — practice on real TOPIK II papers

Revision ID: c9f4b2a7e1d3
Revises: b8e3a1c5d7f2
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'c9f4b2a7e1d3'
down_revision = 'b8e3a1c5d7f2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'real_exam_set',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('learner_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('profiles.id', ondelete='CASCADE'), nullable=False),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('why', sa.Text(), nullable=False, server_default=''),
        sa.Column('scope', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('qids', postgresql.JSONB(), nullable=False, server_default='[]'),
        sa.Column('hints', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_real_exam_set_learner_id', 'real_exam_set', ['learner_id'])
    op.create_table(
        'real_exam_attempt',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('learner_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('profiles.id', ondelete='CASCADE'), nullable=False),
        sa.Column('set_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('real_exam_set.id', ondelete='SET NULL'), nullable=True),
        sa.Column('qid', sa.String(24), nullable=False),
        sa.Column('qtype', sa.String(32), nullable=False),
        sa.Column('tier', sa.SmallInteger(), nullable=False),
        sa.Column('chosen', sa.SmallInteger(), nullable=True),
        sa.Column('answer', postgresql.JSONB(), nullable=True),
        sa.Column('correct', sa.Boolean(), nullable=False),
        sa.Column('pending', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('self_ok', sa.Boolean(), nullable=True),
        sa.Column('hints', sa.SmallInteger(), nullable=False, server_default='0'),
        sa.Column('detail', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint('set_id', 'qid', name='uq_real_exam_attempt_set_question'),
    )
    op.create_index('ix_real_exam_attempt_learner_id', 'real_exam_attempt', ['learner_id'])
    op.create_index('ix_real_exam_attempt_set_id', 'real_exam_attempt', ['set_id'])


def downgrade() -> None:
    op.drop_index('ix_real_exam_attempt_set_id', table_name='real_exam_attempt')
    op.drop_index('ix_real_exam_attempt_learner_id', table_name='real_exam_attempt')
    op.drop_table('real_exam_attempt')
    op.drop_index('ix_real_exam_set_learner_id', table_name='real_exam_set')
    op.drop_table('real_exam_set')

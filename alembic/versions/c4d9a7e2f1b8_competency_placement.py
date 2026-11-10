"""competency memory and the entry diagnostic

* content.grammar_point.use_level — "recognize" | "produce" | NULL (the card's own level)
* grammar_competency — per learner and card, the last outcomes per rung of the ladder
* placement_attempt — one sitting of the entry diagnostic

Revision ID: c4d9a7e2f1b8
Revises: b8e3c5a1d7f2
Create Date: 2026-10-09 15:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'c4d9a7e2f1b8'
down_revision = 'b8e3c5a1d7f2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('grammar_point', sa.Column('use_level', sa.String(length=10), nullable=True), schema='content')
    op.create_table(
        'grammar_competency',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('learner_id', sa.UUID(), nullable=False),
        sa.Column('grammar_id', sa.Integer(), nullable=False),
        sa.Column('history', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['learner_id'], ['profiles.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('learner_id', 'grammar_id', name='uq_grammar_competency_learner_card'),
    )
    op.create_index(op.f('ix_grammar_competency_learner_id'), 'grammar_competency', ['learner_id'], unique=False)
    op.create_table(
        'placement_attempt',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('learner_id', sa.UUID(), nullable=False),
        sa.Column('taken_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('answers', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('summary', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.ForeignKeyConstraint(['learner_id'], ['profiles.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_placement_attempt_learner_id'), 'placement_attempt', ['learner_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_placement_attempt_learner_id'), table_name='placement_attempt')
    op.drop_table('placement_attempt')
    op.drop_index(op.f('ix_grammar_competency_learner_id'), table_name='grammar_competency')
    op.drop_table('grammar_competency')
    op.drop_column('grammar_point', 'use_level', schema='content')

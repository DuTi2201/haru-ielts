"""audio.text_audio — the recording of a text, filed under a hash of what it says

Revision ID: a7d2f9c4e1b6
Revises: c4d9a7e2f1b8
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'a7d2f9c4e1b6'
down_revision = 'c4d9a7e2f1b8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'text_audio',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('cache_key', sa.String(160), nullable=False),
        sa.Column('text_ko', sa.Text(), nullable=False),
        sa.Column('voice', sa.String(64), nullable=False),
        sa.Column('prompt_version', sa.String(32), nullable=False),
        sa.Column('provider', sa.String(16), nullable=False, server_default='chirp'),
        sa.Column('duration_sec', sa.Integer(), nullable=False),
        sa.Column('storage', sa.String(16), nullable=False, server_default='db'),
        sa.Column('opus_key', sa.String(300), nullable=True),
        sa.Column('aac_key', sa.String(300), nullable=True),
        sa.Column('opus_data', sa.LargeBinary(), nullable=True),
        sa.Column('aac_data', sa.LargeBinary(), nullable=True),
        sa.Column('opus_bytes', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('aac_bytes', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        schema='audio',
    )
    op.create_index('ix_audio_text_audio_cache_key', 'text_audio', ['cache_key'], unique=True, schema='audio')


def downgrade() -> None:
    op.drop_index('ix_audio_text_audio_cache_key', table_name='text_audio', schema='audio')
    op.drop_table('text_audio', schema='audio')

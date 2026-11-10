"""lecture_audio: bytes may live in the bucket (storage, opus_key, aac_key)

Revision ID: c5e9a3b7d1f2
Revises: b8d2f4a6c1e3
"""
import sqlalchemy as sa
from alembic import op

revision = "c5e9a3b7d1f2"
down_revision = "b8d2f4a6c1e3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # a constant default is a catalogue change only: no table rewrite, no space needed
    op.add_column("lecture_audio", sa.Column("storage", sa.String(16), nullable=False, server_default="db"), schema="audio")
    op.add_column("lecture_audio", sa.Column("opus_key", sa.String(300), nullable=True), schema="audio")
    op.add_column("lecture_audio", sa.Column("aac_key", sa.String(300), nullable=True), schema="audio")


def downgrade() -> None:
    op.drop_column("lecture_audio", "aac_key", schema="audio")
    op.drop_column("lecture_audio", "opus_key", schema="audio")
    op.drop_column("lecture_audio", "storage", schema="audio")

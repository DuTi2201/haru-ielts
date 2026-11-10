"""Sentence/word recordings and lesson pictures may live in the bucket (storage, *_key)

Revision ID: b6f2d8a4c0e7
Revises: a9d3e7c1b5f4

Same move lecture_audio and text_audio already made: the row keeps a link (`storage` = "gcs" and
the object's name) and its data column stays empty, so the data columns can no longer be NOT NULL.
All catalogue changes (a constant default is not a table rewrite), so no free space is needed.
"""
import sqlalchemy as sa
from alembic import op

revision = "b6f2d8a4c0e7"
down_revision = "a9d3e7c1b5f4"
branch_labels = None
depends_on = None

_WORD_TABLES = ("corpus_item_audio", "vocab_item_audio")


def upgrade() -> None:
    for table in _WORD_TABLES:
        op.add_column(table, sa.Column("storage", sa.String(16), nullable=False, server_default="db"), schema="audio")
        op.add_column(table, sa.Column("opus_key", sa.String(300), nullable=True), schema="audio")
        op.add_column(table, sa.Column("aac_key", sa.String(300), nullable=True), schema="audio")
        op.alter_column(table, "opus_data", existing_type=sa.LargeBinary(), nullable=True, schema="audio")
        op.alter_column(table, "aac_data", existing_type=sa.LargeBinary(), nullable=True, schema="audio")
    op.add_column("scene_image", sa.Column("storage", sa.String(16), nullable=False, server_default="db"), schema="content")
    op.add_column("scene_image", sa.Column("object_key", sa.String(300), nullable=True), schema="content")
    op.alter_column("scene_image", "data", existing_type=sa.LargeBinary(), nullable=True, schema="content")


def downgrade() -> None:
    """Only valid while no row is in the bucket (its bytes would be missing)."""
    op.alter_column("scene_image", "data", existing_type=sa.LargeBinary(), nullable=False, schema="content")
    op.drop_column("scene_image", "object_key", schema="content")
    op.drop_column("scene_image", "storage", schema="content")
    for table in _WORD_TABLES:
        op.alter_column(table, "aac_data", existing_type=sa.LargeBinary(), nullable=False, schema="audio")
        op.alter_column(table, "opus_data", existing_type=sa.LargeBinary(), nullable=False, schema="audio")
        op.drop_column(table, "aac_key", schema="audio")
        op.drop_column(table, "opus_key", schema="audio")
        op.drop_column(table, "storage", schema="audio")

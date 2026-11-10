"""audio.lecture_audio.timeline: when each part of a lecture starts

Revision ID: c7e1a5b9d3f2
Revises: b5d9f1a3c7e2

[[line, run, ms], ...]: the start of every language run of the script in the recording (line
counts the script's non-empty lines). The lecture's slides follow it. NULL for a recording made
before it (or by the Gemini fallback): the slides then follow an estimate.
"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "c7e1a5b9d3f2"
down_revision = "b5d9f1a3c7e2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("lecture_audio", sa.Column("timeline", postgresql.JSONB(), nullable=True), schema="audio")


def downgrade() -> None:
    op.drop_column("lecture_audio", "timeline", schema="audio")

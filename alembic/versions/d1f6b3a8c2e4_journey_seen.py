"""journey.seen: the moments of the journey already shown to the learner, kept per account

Revision ID: d1f6b3a8c2e4
Revises: c9e5a1b3d7f4
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "d1f6b3a8c2e4"
down_revision = "c9e5a1b3d7f4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("journey", sa.Column("seen", postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    op.drop_column("journey", "seen")

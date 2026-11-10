"""billing.site_setting: content an admin sets, first the help channels shown to learners

Revision ID: f4b8c2e6a1d3
Revises: e1c5a9f3d7b6
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "f4b8c2e6a1d3"
down_revision = "e1c5a9f3d7b6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "site_setting",
        sa.Column("key", sa.String(40), primary_key=True),
        sa.Column("value", postgresql.JSONB(), nullable=False),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        schema="billing",
    )


def downgrade() -> None:
    op.drop_table("site_setting", schema="billing")

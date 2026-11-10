"""item_state.last_correct: the last answer to a card

Revision ID: a8c2e4f6b1d3
Revises: d3a7c1e9b5f2

The lesson screen shows "Đã hiểu" / "Chưa chắc" again when the learner returns, so it needs to know the
last answer, which strength / reps alone cannot say (an early right answer leaves reps unchanged).
One nullable column: every existing row starts empty and nothing else changes.
"""
import sqlalchemy as sa
from alembic import op

revision = "a8c2e4f6b1d3"
down_revision = "d3a7c1e9b5f2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("item_state", sa.Column("last_correct", sa.Boolean(), nullable=True))


def downgrade() -> None:
    op.drop_column("item_state", "last_correct")

"""item_state.known_at and profiles.review_only_on: "Đã biết" and "Hôm nay bận — chỉ ôn"

Revision ID: d8b4f2a6c3e9
Revises: e3b5d7f9a1c4

Two nullable columns, nothing else changes:

* item_state.known_at — the learner marked the card as already known. The review queue leaves it
  out (never new, never due, not counted in the day's new cards) until they undo it. Every
  existing row starts empty, i.e. studied as before.
* profiles.review_only_on — the day the learner asked for reviews only: on that day the queue
  offers no new cards. A date, so it lapses on its own the next day.
"""
import sqlalchemy as sa
from alembic import op

revision = "d8b4f2a6c3e9"
down_revision = "e3b5d7f9a1c4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("item_state", sa.Column("known_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("profiles", sa.Column("review_only_on", sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column("profiles", "review_only_on")
    op.drop_column("item_state", "known_at")

"""Account lock and password reset: four columns on profiles

Revision ID: d3a7c1e9b5f2
Revises: c4e8a2f7d1b9

- disabled_at / disabled_reason: an admin locked the account (no login, no token works).
- temp_password_expires_at: the password is a temporary one an admin set; the learner must change it
  before this time (after it the temporary password no longer logs in).
- tokens_valid_after: tokens issued before this moment are refused (set when an admin resets the
  password or the learner changes it, so an old session does not outlive the old password).
Nothing changes for any existing account: every column starts empty.
"""
import sqlalchemy as sa
from alembic import op

revision = "d3a7c1e9b5f2"
down_revision = "c4e8a2f7d1b9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("profiles", sa.Column("disabled_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("profiles", sa.Column("disabled_reason", sa.String(255), nullable=True))
    op.add_column("profiles", sa.Column("temp_password_expires_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("profiles", sa.Column("tokens_valid_after", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    for column in ("tokens_valid_after", "temp_password_expires_at", "disabled_reason", "disabled_at"):
        op.drop_column("profiles", column)

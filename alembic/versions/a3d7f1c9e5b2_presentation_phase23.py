"""presentation phases 2-3: own talks, per-learner fitting, follow-up answers

Revision ID: a3d7f1c9e5b2
Revises: f6b2d8a4c1e7

presentation_session gains the round's mode ("topic" | "defense"), the learner's own title and
material for "Bảo vệ đề tài", and the plan the round was fitted with (band shift, focus, the
studied items to deploy). learner_talk_profile gains the presentation band, the verdicts that move
it, and per studied item how often it was used correctly when presenting. Columns only, with
defaults: existing rows read as "topic" rounds with no plan.
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "a3d7f1c9e5b2"
down_revision = "f6b2d8a4c1e7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("presentation_session", sa.Column("mode", sa.String(10), nullable=False, server_default="topic"))
    op.add_column("presentation_session", sa.Column("title", sa.String(200), nullable=False, server_default=""))
    op.add_column("presentation_session", sa.Column("material", sa.Text(), nullable=False, server_default=""))
    op.add_column("presentation_session", sa.Column("plan", postgresql.JSONB(), nullable=True))
    op.add_column("learner_talk_profile", sa.Column("present_band", sa.SmallInteger(), nullable=True))
    op.add_column("learner_talk_profile", sa.Column("present_verdicts", postgresql.JSONB(), nullable=False, server_default="[]"))
    op.add_column("learner_talk_profile", sa.Column("present_usage", postgresql.JSONB(), nullable=False, server_default="{}"))


def downgrade() -> None:
    op.drop_column("learner_talk_profile", "present_usage")
    op.drop_column("learner_talk_profile", "present_verdicts")
    op.drop_column("learner_talk_profile", "present_band")
    op.drop_column("presentation_session", "plan")
    op.drop_column("presentation_session", "material")
    op.drop_column("presentation_session", "title")
    op.drop_column("presentation_session", "mode")

"""Hành trình Thiên Nga: the days a learner studied, and the stage of the journey reached

Revision ID: a7c3e9b1d5f2
Revises: f4b8c2e6a1d3

- learner_day: one row per learner per day (Vietnam time) on which they studied — a review, a
  lesson question, a drill, a talk, a reading. The streak and the journey's "days away" read it.
  Filled from what is already recorded (item states, errors, lesson answers, talks, readings,
  real-exam and drill attempts, placements).
- journey: the stage (1–5) a learner has reached; it only goes up (app/services/journey.py).
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "a7c3e9b1d5f2"
down_revision = "f4b8c2e6a1d3"
branch_labels = None
depends_on = None

_SOURCES = [
    ("item_state", "last_seen"),
    ("error_log", "created_at"),
    ("lesson_exercise_result", "updated_at"),
    ("conversation_session", "started_at"),
    ("reading_log", "finished_at"),
    ("real_exam_attempt", "created_at"),
    ("exam_attempt", "created_at"),
    ("placement_attempt", "taken_at"),
]


def upgrade() -> None:
    op.create_table(
        "learner_day",
        sa.Column("learner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("profiles.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("day", sa.Date(), primary_key=True),
    )
    op.create_table(
        "journey",
        sa.Column("learner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("profiles.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("stage", sa.SmallInteger(), nullable=False, server_default="1"),
        sa.Column("reached_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("stage between 1 and 5", name="ck_journey_stage"),
    )
    for table, column in _SOURCES:
        op.execute(
            f"""
            insert into learner_day (learner_id, day)
            select distinct learner_id, ({column} at time zone 'Asia/Ho_Chi_Minh')::date
            from {table}
            where {column} is not null and learner_id is not null
            on conflict do nothing
            """
        )


def downgrade() -> None:
    op.drop_table("journey")
    op.drop_table("learner_day")

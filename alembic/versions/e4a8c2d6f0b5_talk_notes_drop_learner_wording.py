"""talk_note: drop sentences that were the learner's own wording

Revision ID: e4a8c2d6f0b5
Revises: d2f6b8a4e1c3

"Đưa vào ôn tập" used to also keep, from the pronunciation check, each sentence scored under 70.
That check copies what the learner said (it judges sounds, not meaning), so muddled or wrong
sentences landed in the notebook as if they were right (owner report). The notebook now keeps only
suggested words and sentences Haru corrected; this removes the sentence notes that came from a
pronunciation target and are not also a correction in the same session. Nothing else changes; the
session reports and pronunciation results themselves are kept.
"""
from alembic import op

revision = "e4a8c2d6f0b5"
down_revision = "d2f6b8a4e1c3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DELETE FROM talk_note n
        USING conversation_session s
        WHERE n.session_id = s.id
          AND n.kind = 'sentence'
          AND jsonb_typeof(s.pronunciation -> 'items') = 'array'
          AND EXISTS (
              SELECT 1 FROM jsonb_array_elements(s.pronunciation -> 'items') AS it
              WHERE it ->> 'target_ko' = n.ko
          )
          AND NOT EXISTS (
              SELECT 1
              FROM jsonb_array_elements(
                  CASE WHEN jsonb_typeof(s.report -> 'fixes') = 'array' THEN s.report -> 'fixes' ELSE '[]'::jsonb END
              ) AS f
              WHERE f ->> 'better' = n.ko
          )
        """
    )


def downgrade() -> None:
    # the removed notes were the learner's own (unchecked) wording; they are not brought back
    pass

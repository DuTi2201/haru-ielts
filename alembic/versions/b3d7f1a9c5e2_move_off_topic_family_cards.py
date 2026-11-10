"""Move five vocabulary cards out of Gia đình into the lessons whose exercises they come from.

The cards 물론 · 오히려 (the floor-noise speaking task QS6), 일단 (the Jeju trip story QS3), 퍼센트 ·
여전히 (the holiday survey QS5) were filed under quan-he-01-gia-dinh because those shared speaking
tasks used to be part of that lesson. The seed now lists them in their own lessons.

The seed sync matches a lesson's cards by `hangul` and deletes the ones a lesson no longer lists,
together with every learner's review state (item_state, error_log, audio). So the rows are moved
HERE, before the API starts with the new seed (deploy runs `alembic upgrade head` first): the
sync then finds each card already in its new lesson and updates it in place. `vocab_item.id`
never changes, so item_state / error_log / vocab_item_audio / talk_note keep pointing at it.

Safe on any database: a lesson that does not exist yet (a fresh install, lessons are written by
the first start), a card that is not in the source lesson, or a target lesson that already has a
card with that hangul are all left alone.

Revision ID: b3d7f1a9c5e2
Revises: f4a8c2e6d0b9
"""
from alembic import op

revision = "b3d7f1a9c5e2"
down_revision = "f4a8c2e6d0b9"
branch_labels = None
depends_on = None

SOURCE = "quan-he-01-gia-dinh"
# hangul -> the lesson (slug) that now teaches it; tests/test_lesson_seed.py checks the seed agrees
MOVES = {
    "물론": "quan-he-06-hang-xom-rac",
    "오히려": "quan-he-06-hang-xom-rac",
    "일단": "quan-he-10-du-lich",
    "퍼센트": "quan-he-11-ky-nghi-van-hoa",
    "여전히": "quan-he-11-ky-nghi-van-hoa",
}

_MOVE = """
UPDATE content.vocab_item AS v
   SET lesson_id = dst.id, level = dst.level
  FROM content.lesson AS src, content.lesson AS dst
 WHERE src.slug = '{src}' AND dst.slug = '{dst}'
   AND v.lesson_id = src.id AND v.hangul = '{hangul}'
   AND NOT EXISTS (
       SELECT 1 FROM content.vocab_item AS w WHERE w.lesson_id = dst.id AND w.hangul = '{hangul}'
   )
"""


def upgrade() -> None:
    for hangul, target in MOVES.items():
        op.execute(_MOVE.format(src=SOURCE, dst=target, hangul=hangul))


def downgrade() -> None:
    # back to Gia đình; the old seed's sync then finds them there again
    for hangul, target in MOVES.items():
        op.execute(_MOVE.format(src=target, dst=SOURCE, hangul=hangul))

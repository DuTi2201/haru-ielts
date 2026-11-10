"""Bring the position nouns and a few core adverbs/connectors into lessons 1–16.

Korean Grammar in Use (Beginner) and TOPIK I need 앞 · 뒤 · 위 · 아래 · 옆 · 안 · 밖 · 사이 · 오른쪽 ·
왼쪽 in the foundation (N에 있다), and 자주 · 항상 · 전혀 · 그러나 in the everyday lessons; the seed
taught them only in lessons 17–51. The seed now lists them earlier; as with b3d7f1a9c5e2, the rows
are moved here before the API's seed sync runs, so `vocab_item.id` — and every learner's review
state — stays. A card missing from the source lesson, or already in the target, is left alone.

Revision ID: e3b5d7f9a1c4
Revises: d7a2c4e6f8b1
"""
from alembic import op

revision = "e3b5d7f9a1c4"
down_revision = "d7a2c4e6f8b1"
branch_labels = None
depends_on = None

# (hangul, from lesson, to lesson); tests/test_lesson_seed.py checks the seed agrees
MOVES = (
    ('위', 'quan-he-04-tim-duong', 'sinh-hoat-00-nen-tang-2-noi-chon'),
    ('아래', 'quan-he-04-tim-duong', 'sinh-hoat-00-nen-tang-2-noi-chon'),
    ('앞', 'quan-he-04-tim-duong', 'sinh-hoat-00-nen-tang-2-noi-chon'),
    ('뒤', 'quan-he-04-tim-duong', 'sinh-hoat-00-nen-tang-2-noi-chon'),
    ('옆', 'quan-he-04-tim-duong', 'sinh-hoat-00-nen-tang-2-noi-chon'),
    ('안', 'quan-he-04-tim-duong', 'sinh-hoat-00-nen-tang-2-noi-chon'),
    ('밖', 'quan-he-04-tim-duong', 'sinh-hoat-00-nen-tang-2-noi-chon'),
    ('사이', 'quan-he-04-tim-duong', 'sinh-hoat-00-nen-tang-2-noi-chon'),
    ('오른쪽', 'quan-he-04-tim-duong', 'sinh-hoat-00-nen-tang-2-noi-chon'),
    ('왼쪽', 'quan-he-04-tim-duong', 'sinh-hoat-00-nen-tang-2-noi-chon'),
    ('가운데', 'quan-he-04-tim-duong', 'sinh-hoat-00-nen-tang-2-noi-chon'),
    ('밑', 'quan-he-04-tim-duong', 'sinh-hoat-00-nen-tang-2-noi-chon'),
    ('자주', 'quan-he-01-gia-dinh', 'sinh-hoat-01-buoi-sang'),
    ('늘 · 항상', 'quan-he-01-gia-dinh', 'sinh-hoat-01-buoi-sang'),
    ('그러나', 'viet-nghi-luan-04-doan-van', 'sinh-hoat-09-nhat-ky'),
    ('전혀', 'xa-hoi-01-suy-doan-quan-sat', 'sinh-hoat-07-giai-tri'),
)

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
    for hangul, src, dst in MOVES:
        op.execute(_MOVE.format(src=src, dst=dst, hangul=hangul))


def downgrade() -> None:
    for hangul, src, dst in MOVES:
        op.execute(_MOVE.format(src=dst, dst=src, hangul=hangul))

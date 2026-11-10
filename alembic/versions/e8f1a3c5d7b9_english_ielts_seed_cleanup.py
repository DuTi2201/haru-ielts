"""Remove Korean seeded rows and add English/IELTS question types

Revision ID: e8f1a3c5d7b9
Revises: b7d2f9a4c1e6
Create Date: 2026-11-10 18:30:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "e8f1a3c5d7b9"
down_revision = "b7d2f9a4c1e6"
branch_labels = None
depends_on = None

_IELTS_QUESTION_TYPES = [
    ("9208e737-cf14-4e86-b8a6-742f61a5cad0", "đọc", "read_cloze", "Sentence completion / Cloze", "Chọn từ/cụm từ điền vào chỗ trống"),
    ("7cc1ddc4-3c32-4142-85a0-50f13c070d7b", "đọc", "read_match", "Grammar & vocabulary choice", "Chọn ngữ pháp/từ vựng đúng"),
    ("88e13931-15a9-408d-a093-87f56fd20fdf", "đọc", "read_passage", "Reading passage & True/False/Not Given", "Đọc hiểu đoạn văn & True/False/Not Given"),
    ("616ca5fd-bd41-41cf-b5b8-e37513915220", "nghe", "listen_dictation", "Listening dictation", "Nghe chép chính tả câu tiếng Anh"),
    ("c875c6df-f843-411e-a4e6-ffcc9120c215", "viết", "write_essay", "Short paragraph / IELTS Writing", "Viết đoạn văn ngắn / IELTS Writing"),
    ("ca0867d1-64a9-49b0-934c-325ed35d64a9", "nói", "speak", "IELTS Speaking turn", "Nói theo chủ đề IELTS Speaking"),
]


def upgrade() -> None:
    op.execute("ALTER TYPE profile_goal ADD VALUE IF NOT EXISTS 'ielts65'")
    op.execute("ALTER TYPE profile_goal ADD VALUE IF NOT EXISTS 'b1'")
    op.execute("DELETE FROM editorial.editorial_source")
    op.execute("DELETE FROM billing.product_setting")
    op.execute("DELETE FROM billing.setting")
    op.execute("DELETE FROM content.question_type WHERE id NOT IN (SELECT DISTINCT qtype_id FROM content.exam_item)")

    question_type = sa.table(
        "question_type",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("skill", sa.String),
        sa.column("code", sa.String),
        sa.column("name_ko", sa.String),
        sa.column("name_vi", sa.String),
        sa.column("active", sa.Boolean),
        schema="content",
    )
    op.bulk_insert(
        question_type,
        [
            {"id": qid, "skill": skill, "code": code, "name_ko": name_en, "name_vi": name_vi, "active": True}
            for qid, skill, code, name_en, name_vi in _IELTS_QUESTION_TYPES
        ],
    )


def downgrade() -> None:
    op.execute(
        "DELETE FROM content.question_type WHERE code IN ("
        + ", ".join(f"'{c[2]}'" for c in _IELTS_QUESTION_TYPES)
        + ")"
    )


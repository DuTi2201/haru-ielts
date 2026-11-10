"""Rename Korean schema/column names to English equivalents for Haru English (IELTS)

Revision ID: f9a2b4c6d8e0
Revises: e8f1a3c5d7b9
Create Date: 2026-11-10 20:35:00.000000
"""
from typing import Sequence, Union

from alembic import op

revision: str = "f9a2b4c6d8e0"
down_revision: Union[str, None] = "e8f1a3c5d7b9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

RENAMES = (
    ("audio", "text_audio", "text_ko", "text_en"),
    ("corpus", "corpus_item", "text_ko", "text_en"),
    ("content", "question_type", "name_ko", "name_en"),
    ("content", "exam_passage", "body_ko", "body_en"),
    ("content", "exam_item", "instruction_ko", "instruction_en"),
    ("content", "exam_item", "stem_ko", "stem_en"),
    ("content", "lesson", "title_ko", "title_en"),
    ("content", "vocab_item", "hangul", "headword"),
    ("content", "vocab_item", "definition_ko", "definition_en"),
    ("content", "vocab_item", "example_ko", "example_en"),
    ("content", "vocab_item", "pron_ko", "pron_en"),
    ("content", "grammar_point", "example_ko", "example_en"),
    ("content", "grammar_point", "topik_tip_vi", "exam_tip_vi"),
    ("public", "error_log", "example_ko", "example_en"),
    ("editorial", "editorial_article", "title_ko", "title_en"),
    ("editorial", "editorial_article", "body_ko", "body_en"),
    ("editorial", "editorial_candidate", "title_ko", "title_en"),
    ("editorial", "editorial_candidate", "snippet_ko", "snippet_en"),
)


def upgrade() -> None:
    for schema, table, old_col, new_col in RENAMES:
        op.execute(f'ALTER TABLE "{schema}"."{table}" RENAME COLUMN "{old_col}" TO "{new_col}"')
    # Force startup sync to re-populate content.lesson.practice JSONB with renamed keys (prompt_en, model_answer_en)
    op.execute("UPDATE content.lesson SET content_hash = 'renamed:' || id::text")


def downgrade() -> None:
    for schema, table, old_col, new_col in reversed(RENAMES):
        op.execute(f'ALTER TABLE "{schema}"."{table}" RENAME COLUMN "{new_col}" TO "{old_col}"')


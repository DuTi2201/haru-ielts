"""lesson-v5: lessons are written once and seeded, not generated from an upload

* content.lesson gets the fields a structured lesson needs: slug (the seed file's
  identity), title_ko, summary, track (sơ / trung / cao), sort_order, notes and the
  practice set (JSONB).
* content.vocab_item / grammar_point get example_vi, grammar_point a note_vi.
* lesson_exercise_result: the learner's latest answer per practice question.
* scene_image: generated pictures of practice scenes (optional, the feature is off by default).
* Every lesson that exists now came from the old upload flow and was test data
  (the owner confirmed it): they are deleted together with everything that points at
  them by a bare id and would otherwise be left dangling — review schedule
  (item_state), error log, listening audio of their words, the lecture recordings,
  the corpus sentences' grammar ids and the lesson import batches.
  Editorial words/patterns (lesson_id NULL) and every other table are untouched.
  The new lessons are loaded at start-up from app/seed/lessons (app.services.lesson_seed).

Revision ID: e7a3c9d5b1f8
Revises: b6e2d9a4c7f3
Create Date: 2026-10-05 22:30:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'e7a3c9d5b1f8'
down_revision = 'b6e2d9a4c7f3'
branch_labels = None
depends_on = None

_OLD_LESSONS = "SELECT id FROM content.lesson WHERE slug IS NULL"
_OLD_VOCAB = f"SELECT id FROM content.vocab_item WHERE lesson_id IN ({_OLD_LESSONS})"
_OLD_GRAMMAR = f"SELECT id FROM content.grammar_point WHERE lesson_id IN ({_OLD_LESSONS})"


def upgrade() -> None:
    # ---- schema ----------------------------------------------------------
    op.add_column('lesson', sa.Column('slug', sa.String(length=80), nullable=True), schema='content')
    op.add_column('lesson', sa.Column('title_ko', sa.String(length=255), nullable=True), schema='content')
    op.add_column('lesson', sa.Column('summary', sa.Text(), nullable=True), schema='content')
    op.add_column('lesson', sa.Column('track', sa.String(length=16), nullable=True), schema='content')
    op.add_column(
        'lesson', sa.Column('sort_order', sa.Integer(), server_default='0', nullable=False), schema='content'
    )
    op.add_column('lesson', sa.Column('notes', postgresql.JSONB(astext_type=sa.Text()), nullable=True), schema='content')
    op.add_column(
        'lesson', sa.Column('practice', postgresql.JSONB(astext_type=sa.Text()), nullable=True), schema='content'
    )
    op.create_unique_constraint('uq_lesson_slug', 'lesson', ['slug'], schema='content')

    op.add_column('vocab_item', sa.Column('example_vi', sa.Text(), nullable=True), schema='content')
    op.add_column('grammar_point', sa.Column('example_vi', sa.Text(), nullable=True), schema='content')
    op.add_column('grammar_point', sa.Column('note_vi', sa.Text(), nullable=True), schema='content')

    op.create_table(
        'lesson_exercise_result',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('learner_id', sa.UUID(), nullable=False),
        sa.Column('lesson_id', sa.Integer(), nullable=False),
        sa.Column('exercise_id', sa.String(length=32), nullable=False),
        sa.Column('question_id', sa.String(length=32), nullable=False),
        sa.Column('correct', sa.Boolean(), nullable=False),
        sa.Column('attempts', sa.Integer(), server_default='1', nullable=False),
        sa.Column('last_answer', sa.String(length=500), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['learner_id'], ['profiles.id']),
        sa.ForeignKeyConstraint(['lesson_id'], ['content.lesson.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('learner_id', 'lesson_id', 'question_id', name='uq_lesson_exercise_result'),
    )
    op.create_index('ix_lesson_exercise_result_learner_id', 'lesson_exercise_result', ['learner_id'])
    op.create_index('ix_lesson_exercise_result_lesson_id', 'lesson_exercise_result', ['lesson_id'])

    op.create_table(
        'scene_image',
        sa.Column('cache_key', sa.String(length=48), nullable=False),
        sa.Column('mime_type', sa.String(length=32), nullable=False),
        sa.Column('data', sa.LargeBinary(), nullable=False),
        sa.Column('prompt', sa.Text(), nullable=False),
        sa.Column('model', sa.String(length=64), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('cache_key'),
        schema='content',
    )

    # ---- purge the old (test) lessons and everything that points at them ----
    op.execute(
        f"""DELETE FROM item_state
            WHERE (item_type = 'vocab_item' AND item_id IN ({_OLD_VOCAB}))
               OR (item_type = 'grammar_point' AND item_id IN ({_OLD_GRAMMAR}))"""
    )
    op.execute(
        f"""DELETE FROM error_log
            WHERE (item_type = 'vocab_item' AND item_id IN ({_OLD_VOCAB}))
               OR (item_type = 'grammar_point' AND item_id IN ({_OLD_GRAMMAR}))"""
    )
    # corpus sentences list the grammar patterns they use as a bare id array
    op.execute(
        f"""UPDATE corpus.corpus_item
            SET grammar_point_ids = ARRAY(
                SELECT g FROM unnest(grammar_point_ids) AS g WHERE g NOT IN ({_OLD_GRAMMAR})
            )
            WHERE grammar_point_ids && ARRAY({_OLD_GRAMMAR})"""
    )
    op.execute(f"DELETE FROM audio.vocab_item_audio WHERE vocab_item_id IN ({_OLD_VOCAB})")
    # lecture recordings of a lesson: "podcast:lesson:{id}:..." and "{lesson_id}:{voice}:{version}"
    op.execute("DELETE FROM audio.lecture_audio WHERE cache_key LIKE 'podcast:lesson:%' OR cache_key ~ '^[0-9]+:'")
    op.execute(
        """DELETE FROM jobs
           WHERE type IN ('generate_content_podcast', 'generate_lecture_audio')
             AND (idempotency_key LIKE 'podcast:lesson:%' OR idempotency_key ~ '^[0-9]+:')"""
    )
    op.execute("DELETE FROM import_batch WHERE kind = 'lesson'")  # its import_item rows go with it
    op.execute(f"DELETE FROM content.vocab_item WHERE lesson_id IN ({_OLD_LESSONS})")
    op.execute(f"DELETE FROM content.grammar_point WHERE lesson_id IN ({_OLD_LESSONS})")
    op.execute(f"DELETE FROM content.lesson_topic WHERE lesson_id IN ({_OLD_LESSONS})")
    op.execute("DELETE FROM content.lesson WHERE slug IS NULL")


def downgrade() -> None:
    # The purged test lessons are not restored; only the structure is undone.
    op.drop_table('scene_image', schema='content')
    op.drop_index('ix_lesson_exercise_result_lesson_id', table_name='lesson_exercise_result')
    op.drop_index('ix_lesson_exercise_result_learner_id', table_name='lesson_exercise_result')
    op.drop_table('lesson_exercise_result')
    op.drop_column('grammar_point', 'note_vi', schema='content')
    op.drop_column('grammar_point', 'example_vi', schema='content')
    op.drop_column('vocab_item', 'example_vi', schema='content')
    op.drop_constraint('uq_lesson_slug', 'lesson', schema='content', type_='unique')
    for col in ('practice', 'notes', 'sort_order', 'track', 'summary', 'title_ko', 'slug'):
        op.drop_column('lesson', col, schema='content')

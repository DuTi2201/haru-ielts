"""SQLAlchemy models — one module, sectioned to match the SDD's module
boundaries (identity / content / audio / corpus / analytics / practice /
writing / ingest). Kept in one file for a first scaffold; split into
app/models/<module>.py once a module's table count grows.

Field names/types follow the SDD verbatim where it gave CREATE TABLE
snippets (audio.lecture_audio, corpus.corpus_item, analytics.learning_event,
content.exam_paper/question_type/exam_passage/exam_item/exam_item_tag).
Tables the SDD only indexed without a full column list (vocab_item,
item_state, import_item, writing_submission, error_log, writing_score,
jobs, profiles) are reasonable extensions inferred from context — revisit
once the corresponding module is actually implemented.
"""
import uuid
from datetime import date, datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    ARRAY,
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    LargeBinary,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    false,
    true,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def _uuid_pk():
    return mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


# ---------------------------------------------------------------- identity --
class Profile(Base):
    """Learner/editor/admin profile. `id` mirrors the auth subject id."""

    __tablename__ = "profiles"

    id: Mapped[uuid.UUID] = _uuid_pk()
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(
        Enum("learner", "editor", "admin", name="profile_role"), default="learner"
    )
    display_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    goal: Mapped[str | None] = mapped_column(
        Enum("talk", "topik1", "topik4", "topik5", "topik6", "ielts65", "b1", name="profile_goal"),
        nullable=True,
    )
    exam_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    daily_minutes: Mapped[int] = mapped_column(Integer, default=15)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    # An admin locked the account: it cannot log in and none of its tokens work.
    disabled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    disabled_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # The password is a temporary one an admin set: it must be changed before this time.
    temp_password_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Tokens issued before this moment are refused (a password reset / change ends old sessions).
    tokens_valid_after: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # The address as its inbox sees it (app.services.abuse.email_key): one inbox, one account.
    email_key: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    # "Hôm nay bận — chỉ ôn": on this day (Vietnam time) the review queue offers no new cards.
    # A date, not a flag, so it lapses on its own the next morning.
    review_only_on: Mapped[date | None] = mapped_column(Date, nullable=True)

    @property
    def disabled(self) -> bool:
        return self.disabled_at is not None

    @property
    def must_change_password(self) -> bool:
        return self.temp_password_expires_at is not None


# --------------------------------------------------------------------- jobs --
class Job(Base):
    """Replaces Celery+SSE-over-Redis fan-out with a durable row: worker
    updates status/progress here AND publishes the same payload on the
    `job:{id}:events` Redis channel for live streaming (see
    app/services/job_events.py). Poll this table if you miss the stream.
    """

    __tablename__ = "jobs"

    id: Mapped[uuid.UUID] = _uuid_pk()
    type: Mapped[str] = mapped_column(String(64), index=True)
    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("profiles.id"), nullable=True
    )
    status: Mapped[str] = mapped_column(
        Enum("queued", "running", "succeeded", "failed", "cancelled", name="job_status"),
        default="queued",
        index=True,
    )
    progress: Mapped[float] = mapped_column(Float, default=0.0)
    step: Mapped[str | None] = mapped_column(String(255), nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    result: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    error: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        UniqueConstraint("type", "idempotency_key", name="uq_job_type_idempotency"),
    )


class AppConfig(Base):
    """Versioned config: rubric, gate thresholds, model names, prompt
    versions — "cấu hình thay cho hard-code" (SDD §5, principle 6)."""

    __tablename__ = "app_config"

    name: Mapped[str] = mapped_column(String(120), primary_key=True)
    version: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    value: Mapped[dict] = mapped_column(JSONB)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# ------------------------------------------------------------------- audio --
class LectureAudio(Base):
    """`opus_path`/`aac_path` hold this app's own streaming-route URLs
    (e.g. `/api/v1/lessons/audio/{cache_key}.opus`), not filesystem paths —
    Railway's containers are ephemeral, so the actual encoded bytes live
    in `opus_data`/`aac_data` (Postgres bytea) instead of on disk. Simple,
    and avoids standing up S3/a Railway volume for what is, so far, a
    single-user/family-scale amount of audio."""

    __tablename__ = "lecture_audio"
    __table_args__ = {"schema": "audio"}

    id: Mapped[uuid.UUID] = _uuid_pk()
    cache_key: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    opus_path: Mapped[str] = mapped_column(String(500))
    aac_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    opus_data: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    aac_data: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    # Where the bytes are: "db" (the two columns above) or "gcs" (objects `opus_key`/`aac_key` in
    # the private bucket, the data columns then empty). A podcast is ~40 MB, so with the 500 MB
    # Postgres volume these go to the bucket (AUDIO_STORAGE=gcs, see services/audio_store.py).
    storage: Mapped[str] = mapped_column(String(16), default="db", server_default="db")
    opus_key: Mapped[str | None] = mapped_column(String(300), nullable=True)
    aac_key: Mapped[str | None] = mapped_column(String(300), nullable=True)
    prompt_version: Mapped[str] = mapped_column(String(32))
    voice: Mapped[str] = mapped_column(String(64))
    duration_sec: Mapped[int] = mapped_column(Integer)
    # Transcript of what was actually synthesized. NULL for the original
    # arbitrary-text lecture use (the caller already has that text), but
    # ALWAYS set for a generated "bài giảng tổng hợp" (see
    # app.workers.tasks.generate_content_podcast) — cache_key there is
    # prefixed "podcast:lesson:.../podcast:article:..." so it shares this
    # same table/route instead of standing up a parallel one.
    script_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    # [[line, run, ms], ...]: when each language run of `script_text` starts in the recording (the
    # lecture's slides follow it). NULL for older recordings and the Gemini fallback.
    timeline: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CorpusItemAudio(Base):
    """Same content-addressed cache pattern as LectureAudio, but keyed to
    one corpus.corpus_item (a single listening sentence) instead of a
    whole lesson. `corpus_item_id` is a bare id — crosses from `audio`
    into `corpus`, so no physical FK (SDD modular-monolith principle)."""

    __tablename__ = "corpus_item_audio"
    __table_args__ = {"schema": "audio"}

    id: Mapped[uuid.UUID] = _uuid_pk()
    corpus_item_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    cache_key: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    opus_data: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    aac_data: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    # "db" (the two columns above) or "gcs" (objects `opus_key`/`aac_key` in the private bucket)
    storage: Mapped[str] = mapped_column(String(16), default="db", server_default="db")
    opus_key: Mapped[str | None] = mapped_column(String(300), nullable=True)
    aac_key: Mapped[str | None] = mapped_column(String(300), nullable=True)
    prompt_version: Mapped[str] = mapped_column(String(32))
    voice: Mapped[str] = mapped_column(String(64))
    duration_sec: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class VocabItemAudio(Base):
    """Same content-addressed cache pattern as CorpusItemAudio, but keyed
    to one content.vocab_item — backs the "nghe" (listen) button on a
    vocab flashcard (SRS/SDD: vocab study must offer audio, not just the
    written headword). `vocab_item_id` is a plain integer (content.vocab_item
    uses an autoincrement int PK, not a UUID) and stays a bare id for the
    same cross-module reason as corpus_item_id above — no physical FK."""

    __tablename__ = "vocab_item_audio"
    __table_args__ = {"schema": "audio"}

    id: Mapped[uuid.UUID] = _uuid_pk()
    vocab_item_id: Mapped[int] = mapped_column(Integer, index=True)
    cache_key: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    opus_data: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    aac_data: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    storage: Mapped[str] = mapped_column(String(16), default="db", server_default="db")  # as CorpusItemAudio
    opus_key: Mapped[str | None] = mapped_column(String(300), nullable=True)
    aac_key: Mapped[str | None] = mapped_column(String(300), nullable=True)
    prompt_version: Mapped[str] = mapped_column(String(32))
    voice: Mapped[str] = mapped_column(String(64))
    duration_sec: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class TextAudio(Base):
    """The recording of one TEXT (a sentence, a line of a dialogue, a reading passage), filed
    under what it says: `cache_key` is a hash of the text, the voice in use and the version
    (app/services/audio_keys.text_audio_key), so the same text asked for again, by any
    device, is found here and played at once — Google is called only for a text nobody has
    had voiced.

    The row is the LINK between the text and its file. Where the bytes live is `storage`:
    "db" — in `opus_data`/`aac_data` of this row; "gcs" — as objects `opus_key`/`aac_key`
    of the private bucket (the data columns are then empty). `provider` says who voiced it:
    a recording Gemini made because Chirp failed is replaced the next time it is asked for."""

    __tablename__ = "text_audio"
    __table_args__ = {"schema": "audio"}

    id: Mapped[uuid.UUID] = _uuid_pk()
    cache_key: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    text_en: Mapped[str] = mapped_column(Text)
    voice: Mapped[str] = mapped_column(String(64))
    prompt_version: Mapped[str] = mapped_column(String(32))
    provider: Mapped[str] = mapped_column(String(16), default="chirp")
    duration_sec: Mapped[int] = mapped_column(Integer)
    storage: Mapped[str] = mapped_column(String(16), default="db")
    opus_key: Mapped[str | None] = mapped_column(String(300), nullable=True)
    aac_key: Mapped[str | None] = mapped_column(String(300), nullable=True)
    opus_data: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    aac_data: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    opus_bytes: Mapped[int] = mapped_column(Integer, default=0)
    aac_bytes: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# ------------------------------------------------------------------ corpus --
class Film(Base):
    """SRS §5 FILM — the registry a subtitle upload is filed under. Named
    by the admin at upload time (not AI-derived), so unlike everything
    else this module writes, a row here is created immediately rather
    than staged through import_item/review (SDD's "khu chờ duyệt" rule
    protects against hallucinated *content*, not an admin-typed title).
    """

    __tablename__ = "film"
    __table_args__ = {"schema": "corpus"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), unique=True)


class CorpusItem(Base):
    """SRS §5 CORPUS_ITEM. `film_id`/`topic_ids` stay bare ids with no
    physical FK to `content` (cross-schema — SDD principle: modules never
    JOIN/FK across schema boundaries); `film_id` DOES get a real FK since
    both tables live in `corpus`. `grammar_point_ids` is the
    `CORPUS_ITEM }o--o{ GRAMMAR_POINT : dùng` relationship from the SRS
    ER diagram — present in the diagram but not in the SDD's DDL snippet,
    so it's added here the same bare-array way as `topic_ids`.
    Deliberately has NO `import_item_id` (SRS's "Nguồn dữ liệu" convention
    only lists it for từ/ngữ pháp/bài đọc, not câu) — see ingest.py's
    corpus rollback note for what that means for undo.
    """

    __tablename__ = "corpus_item"
    __table_args__ = (
        UniqueConstraint("film_id", "source_ref", name="uq_corpus_item_film_source_ref"),
        {"schema": "corpus"},
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    film_id: Mapped[int] = mapped_column(ForeignKey("corpus.film.id", ondelete="CASCADE"), index=True)
    text_en: Mapped[str] = mapped_column(Text)
    kind: Mapped[str] = mapped_column(Enum("câu", "cụm từ", "mẫu ngữ pháp", name="corpus_item_kind"))
    level: Mapped[int] = mapped_column(SmallInteger)
    register: Mapped[str] = mapped_column(Enum("존댓말", "반말", "hỗn hợp", name="corpus_item_register"))
    source_ref: Mapped[str | None] = mapped_column(String(64), nullable=True)
    topic_ids: Mapped[list[int]] = mapped_column(ARRAY(Integer), default=list)
    grammar_point_ids: Mapped[list[int]] = mapped_column(ARRAY(Integer), default=list)
    embedding = mapped_column(Vector(768), nullable=True)
    # What the line means / how it is used, for the learner (filled by the
    # AI enrichment step; NULL until then). `naturalness` is that step's
    # verdict — 'natural' | 'awkward' | 'unnatural' — and 'unnatural' lines
    # are hidden from learners. `enriched_version` records which prompt wrote
    # the three, so the backfill is resumable and re-runnable.
    meaning_vi: Mapped[str | None] = mapped_column(Text, nullable=True)
    usage_note_vi: Mapped[str | None] = mapped_column(Text, nullable=True)
    naturalness: Mapped[str | None] = mapped_column(String(16), nullable=True)
    enriched_version: Mapped[str | None] = mapped_column(String(16), nullable=True)


# --------------------------------------------------------------- analytics --
class LearningEvent(Base):
    """Partitioned by occurred_at range per SDD. SQLAlchemy declares the
    parent table's shape; the actual `PARTITION BY RANGE (occurred_at)`
    DDL + monthly partitions live in the Alembic migration (raw SQL),
    not here — the ORM layer doesn't need to know about partitions.
    """

    __tablename__ = "learning_event"
    __table_args__ = {"schema": "analytics"}

    learner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("profiles.id"), primary_key=True
    )
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), primary_key=True, server_default=func.now()
    )
    event_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type: Mapped[str] = mapped_column(String(64))
    skill: Mapped[str] = mapped_column(String(32))
    value: Mapped[float] = mapped_column(Float)
    payload: Mapped[dict] = mapped_column(JSONB, default=dict)


# ------------------------------------------------------------------ content --
class ExamPaper(Base):
    __tablename__ = "exam_paper"
    __table_args__ = {"schema": "content"}

    id: Mapped[uuid.UUID] = _uuid_pk()
    exam_kind: Mapped[str] = mapped_column(String(32))
    session_label: Mapped[str] = mapped_column(String(64))
    owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("profiles.id"))
    file_hash: Mapped[str] = mapped_column(String(64))
    answer_status: Mapped[str] = mapped_column(String(32), default="pending")
    import_job_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    prompt_version: Mapped[str] = mapped_column(String(32))

    __table_args__ = (
        UniqueConstraint("owner_id", "file_hash", name="uq_exam_paper_owner_hash"),
        {"schema": "content"},
    )


class QuestionType(Base):
    __tablename__ = "question_type"
    __table_args__ = {"schema": "content"}

    id: Mapped[uuid.UUID] = _uuid_pk()
    skill: Mapped[str] = mapped_column(String(32))
    code: Mapped[str] = mapped_column(String(32), unique=True)
    name_en: Mapped[str] = mapped_column(String(120))
    name_vi: Mapped[str] = mapped_column(String(120))
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class ExamPassage(Base):
    __tablename__ = "exam_passage"
    __table_args__ = {"schema": "content"}

    id: Mapped[uuid.UUID] = _uuid_pk()
    paper_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("content.exam_paper.id", ondelete="CASCADE")
    )
    kind: Mapped[str] = mapped_column(String(32))
    body_en: Mapped[str | None] = mapped_column(Text, nullable=True)
    chart_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    image_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    audio_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    source_page: Mapped[int] = mapped_column(Integer)
    source_bbox: Mapped[dict] = mapped_column(JSONB)
    embedding = mapped_column(Vector(768), nullable=True)


class ExamItem(Base):
    __tablename__ = "exam_item"
    __table_args__ = (
        UniqueConstraint("paper_id", "number", name="uq_exam_item_paper_number"),
        {"schema": "content"},
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    paper_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("content.exam_paper.id", ondelete="CASCADE")
    )
    passage_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("content.exam_passage.id"), nullable=True
    )
    number: Mapped[int] = mapped_column(Integer)
    qtype_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("content.question_type.id"))
    # The instruction printed once above a group of questions ("[9~12] 다음 글 또는
    # 도표의 내용과 같은 것을 고르십시오."), copied onto each question of the group.
    instruction_en: Mapped[str | None] = mapped_column(Text, nullable=True)
    stem_en: Mapped[str] = mapped_column(Text)
    options: Mapped[dict] = mapped_column(JSONB)
    answer: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    answer_source: Mapped[str | None] = mapped_column(
        Enum("editor", "ai_guess", name="exam_item_answer_source"), nullable=True
    )
    difficulty_est: Mapped[float] = mapped_column(Float, default=0.5)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    import_item_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    embedding = mapped_column(Vector(768), nullable=True)


class ExamItemTag(Base):
    __tablename__ = "exam_item_tag"
    __table_args__ = {"schema": "content"}

    item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("content.exam_item.id", ondelete="CASCADE"), primary_key=True
    )
    tag_kind: Mapped[str] = mapped_column(String(32), primary_key=True)
    ref_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    score: Mapped[float] = mapped_column(Float, default=0.0)
    source: Mapped[str] = mapped_column(String(32))


# --------------------------------------------------------- content: lessons --
# SRS §5: LESSON, TOPIC, VOCAB_ITEM, GRAMMAR_POINT — all lesson-scoped,
# all in `content` (same schema as the exam_* tables above), field lists
# transcribed verbatim from the SRS ER diagram (pages 12-14).
class Topic(Base):
    __tablename__ = "topic"
    __table_args__ = {"schema": "content"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    quizlet_url: Mapped[str | None] = mapped_column(String(500), nullable=True)


class Lesson(Base):
    __tablename__ = "lesson"
    __table_args__ = {"schema": "content"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255))
    level: Mapped[int] = mapped_column(SmallInteger)  # 1-6, TOPIK-tương ứng, ước lượng — not an exam score
    content: Mapped[str] = mapped_column(Text)
    content_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    quizlet_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    import_item_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    # lesson-v5: lessons are no longer generated from an upload; they are written
    # once, checked by a person, and kept as JSON in the repo (app/seed/lessons)
    # and loaded by app.services.lesson_seed. `slug` is that file's identity
    # (NULL on a lesson from the old upload flow, which no longer exists).
    slug: Mapped[str | None] = mapped_column(String(80), unique=True, nullable=True)
    title_en: Mapped[str | None] = mapped_column(String(255), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    track: Mapped[str | None] = mapped_column(String(16), nullable=True)  # beginner | intermediate | advanced
    sort_order: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    notes: Mapped[list | None] = mapped_column(JSONB, nullable=True)  # [{"title": "...", "body": "..."}] — the "Lưu ý" of the lesson
    # "Việc cần làm" shown at the top of the lesson (see app.services.lesson_seed.CoachSeed); NULL = none
    coach: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # The lesson cut into sittings by hand (see app.services.lesson_seed.SessionSeed); NULL = cut evenly by the app
    sessions: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    # The practice set: {"items": [...exercises...], "skills": {...per-skill advice...}, "extension": [...]}.
    # Graded in the browser; the learner-facing shape is in app.services.lesson_seed.
    practice: Mapped[dict | None] = mapped_column(JSONB, nullable=True)


class LessonTopic(Base):
    """LESSON }o--o{ TOPIC : thuộc — real FK join table (both sides are
    same-schema `content`, unlike corpus_item's bare topic_ids array,
    which crosses into `corpus`)."""

    __tablename__ = "lesson_topic"
    __table_args__ = {"schema": "content"}

    lesson_id: Mapped[int] = mapped_column(
        ForeignKey("content.lesson.id", ondelete="CASCADE"), primary_key=True
    )
    topic_id: Mapped[int] = mapped_column(
        ForeignKey("content.topic.id", ondelete="CASCADE"), primary_key=True
    )


class VocabItem(Base):
    """`lesson_id` is nullable: a row created from a lesson import always
    has one, but a row created from an editorial-article import (see
    editorial.editorial_article, added later) does not belong to any
    lesson — it's referenced only via that article's bare `vocab_ids`."""

    __tablename__ = "vocab_item"
    __table_args__ = {"schema": "content"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lesson_id: Mapped[int | None] = mapped_column(
        ForeignKey("content.lesson.id", ondelete="CASCADE"), index=True, nullable=True
    )
    headword: Mapped[str] = mapped_column(String(120))
    pos: Mapped[str | None] = mapped_column(String(32), nullable=True)
    meaning_vi: Mapped[str] = mapped_column(String(255))
    definition_en: Mapped[str | None] = mapped_column(Text, nullable=True)
    level: Mapped[int] = mapped_column(SmallInteger)
    hanja: Mapped[str | None] = mapped_column(String(64), nullable=True)
    sino_vietnamese: Mapped[str | None] = mapped_column(String(120), nullable=True)
    example_en: Mapped[str | None] = mapped_column(Text, nullable=True)
    example_vi: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Chunk-first learning (lesson-v4): TOPIK tests which words go together
    # (which verb takes 우산, which register), not isolated words. All nullable,
    # so cards extracted before v4 keep working and simply show less.
    family: Mapped[str | None] = mapped_column(String(120), nullable=True)  # the set it is learned in, e.g. "Động từ đi với thời tiết"
    node_word: Mapped[str | None] = mapped_column(String(120), nullable=True)  # the part of `headword` a learner must choose correctly (오다 in 비가 오다)
    register: Mapped[str | None] = mapped_column(String(16), nullable=True)  # spoken | written | neutral
    # The exam course this word is part of as well ("kiip-3" = KIIP stage 3); see lesson_seed.ExamTag
    exam: Mapped[str | None] = mapped_column(String(16), nullable=True)
    # "core" (learn now) | "recognize" (understand when met); null on words that come from an article
    priority: Mapped[str | None] = mapped_column(String(12), nullable=True)
    usage_note_vi: Mapped[str | None] = mapped_column(Text, nullable=True)
    pron_en: Mapped[str | None] = mapped_column(String(160), nullable=True)  # "[학쌩]": read this way
    collocations: Mapped[list | None] = mapped_column(JSONB, nullable=True)  # [{"ko": "...", "vi": "..."}]
    distractors: Mapped[list | None] = mapped_column(JSONB, nullable=True)  # wrong-but-tempting stand-ins for node_word
    import_item_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    # a word of the TOPIK word bank (app/services/topik_bank.py): its 한국어기초사전 entry id; no lesson
    bank_key: Mapped[int | None] = mapped_column(Integer, nullable=True)


class GrammarPoint(Base):
    """`lesson_id` nullable — same reasoning as VocabItem.lesson_id above."""

    __tablename__ = "grammar_point"
    __table_args__ = {"schema": "content"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lesson_id: Mapped[int | None] = mapped_column(
        ForeignKey("content.lesson.id", ondelete="CASCADE"), index=True, nullable=True
    )
    pattern: Mapped[str] = mapped_column(String(255))  # V/A + hình thái, vd "V + -(으)ㄹ 뿐만 아니라"
    meaning_vi: Mapped[str] = mapped_column(String(255))
    level: Mapped[int] = mapped_column(SmallInteger)
    example_en: Mapped[str | None] = mapped_column(Text, nullable=True)
    example_vi: Mapped[str | None] = mapped_column(Text, nullable=True)
    # A caution that belongs to this pattern alone ("both clauses need the same
    # subject", "not with adjectives"), as the lesson's author wrote it.
    note_vi: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Added per owner feedback: a bare "V/A + form" pattern + one example
    # sentence isn't enough to actually use a grammar point — usage_context_vi
    # explains WHEN/in what situation it's used (Vietnamese), exam_tip_vi
    # explains how it actually shows up in TOPIK exam questions. Nullable so
    # existing rows (extracted before this field existed) degrade gracefully
    # until backfilled/re-extracted.
    usage_context_vi: Mapped[str | None] = mapped_column(Text, nullable=True)
    exam_tip_vi: Mapped[str | None] = mapped_column(Text, nullable=True)
    # TOPIK asks "which is closest in meaning", so patterns are learned as a set:
    # the label of the set and, for each other member, how it differs.
    contrast_group: Mapped[str | None] = mapped_column(String(120), nullable=True)
    contrasts: Mapped[list | None] = mapped_column(JSONB, nullable=True)  # [{"pattern": "...", "diff_vi": "..."}]
    # The exam course this card is part of as well ("kiip-3" = KIIP stage 3); see lesson_seed.ExamTag
    exam: Mapped[str | None] = mapped_column(String(16), nullable=True)
    # How far the exam asks the learner to take this card: "recognize" (understand it when reading
    # or listening) or "produce" (use it when writing and speaking). NULL = the card says nothing
    # itself; see app.services.grammar_tier.effective_use_level.
    use_level: Mapped[str | None] = mapped_column(String(10), nullable=True)
    # The `pattern`s of the earlier cards this one is made of or rests on (app.services.grammar_graph)
    builds_on: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    # The `pattern` of an earlier card this one teaches again (spaced review); see lesson_seed.GrammarSeed
    revisits: Mapped[str | None] = mapped_column(String(160), nullable=True)
    # "must" (Bắt buộc) | "normal" (Bổ trợ); NULL on an extension card, which carries use_level
    importance: Mapped[str | None] = mapped_column(String(8), nullable=True)
    import_item_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)


# ----------------------------------------------------------------- practice --
class ItemState(Base):
    """SRS §5 ITEM_STATE — a single decay-style `strength` per learner
    per (vocab_item|grammar_point), nudged by quick in-app checks.
    `strength` stays the readiness signal (mastered >= 0.8, /me/plan).
    On top of it sits a small SM-2-style schedule (app.services.srs):
    `due_at` says when the item should come back, `reps` the correct answers
    in a row, `lapses` how often it was forgotten, `ease` and `interval_days`
    how fast the gaps grow. `introduced_at` is when it was first studied, so
    "new items per day" can be capped. `item_id` is a bare id (polymorphic
    across two `content` tables), so — same as corpus_item.topic_ids — no
    physical FK.
    """

    __tablename__ = "item_state"

    id: Mapped[uuid.UUID] = _uuid_pk()
    learner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("profiles.id"), index=True)
    item_type: Mapped[str] = mapped_column(Enum("vocab_item", "grammar_point", name="item_state_type"))
    item_id: Mapped[int] = mapped_column(Integer)
    strength: Mapped[float] = mapped_column(Float, default=0.0)
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    reps: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    lapses: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    ease: Mapped[float] = mapped_column(Float, default=2.2, server_default="2.2")
    interval_days: Mapped[float] = mapped_column(Float, default=0.0, server_default="0")
    introduced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # The last answer: True = "đã hiểu / đã nhớ", False = "chưa chắc / chưa nhớ". The lesson screen shows it
    # again when the learner comes back. Empty on rows from before this column existed.
    last_correct: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    # "Đã biết": the learner already knows this card. The queue leaves it out (never new, never
    # due, not counted in the day's new cards) until they undo it or answer it wrong.
    known_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("learner_id", "item_type", "item_id", name="uq_item_state_learner_item"),
    )


class GrammarCompetency(Base):
    """What a learner can DO with a grammar card, not only whether they remember it
    (`ItemState` is memory). `history` keeps the last few outcomes per rung of the ladder
    ("0" recognise, "1" put words in order, "2" fill / join a sentence, "3" write or say a
    paragraph): {"1": [1, 0, 1]} = right, wrong, right, oldest first. Small on purpose: a
    rung counts as reached when two of its last three outcomes are right, which is also the
    rule that raises or lowers the difficulty of what the mixed review offers
    (app.services.competency). `grammar_id` is a bare id like `ItemState.item_id`."""

    __tablename__ = "grammar_competency"

    id: Mapped[uuid.UUID] = _uuid_pk()
    learner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("profiles.id"), index=True)
    grammar_id: Mapped[int] = mapped_column(Integer)
    history: Mapped[dict] = mapped_column(JSONB, default=dict)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (UniqueConstraint("learner_id", "grammar_id", name="uq_grammar_competency_learner_card"),)


class ReadingLog(Base):
    """A reading or dialogue offered to a learner on a day (app.services.daily_reading). The pick
    is written the first time the day's screen is opened, so it stays the same all day even as
    the learner's cards change, and so a text offered lately is less likely to be offered again.
    `finished_at`/`correct`/`total` fill in when the learner submits the comprehension questions.
    `passage_id` is the id in app/seed/passages (a bare string, like `ItemState.item_id`)."""

    __tablename__ = "reading_log"

    id: Mapped[uuid.UUID] = _uuid_pk()
    learner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("profiles.id"), index=True)
    day: Mapped[date] = mapped_column(Date)
    passage_id: Mapped[str] = mapped_column(String(80))
    kind: Mapped[str] = mapped_column(String(16))
    picked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    correct: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    total: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)

    __table_args__ = (UniqueConstraint("learner_id", "day", "passage_id", name="uq_reading_log_learner_day_text"),)


class RealExamSet(Base):
    """One sitting of the real-exam practice (app.services.real_exam): the questions chosen for the
    learner (`qids`, in the order shown), why they were chosen, and the hints used so far per question
    (`hints`: {qid: highest hint level opened}). The sitting can be left and resumed; it is finished when
    every question has an answer. `qids` are ids in app/seed/exams (bare strings, like
    `ReadingLog.passage_id`)."""

    __tablename__ = "real_exam_set"

    id: Mapped[uuid.UUID] = _uuid_pk()
    learner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(200))
    why: Mapped[str] = mapped_column(Text, default="")
    scope: Mapped[dict] = mapped_column(JSONB, default=dict)
    qids: Mapped[list] = mapped_column(JSONB, default=list)
    hints: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class RealExamAttempt(Base):
    """A learner's answer to one real exam question. Kept for right answers too: the next questions
    offered, the "vững" standing of a type and the summary all read these rows. `hints` is the highest
    hint level opened before answering (0 = on their own: only such an answer counts as solid).
    A written answer is stored in `answer` ({"㉠": "...", ...} or {"text": "..."}); one the program
    cannot judge (`pending`) waits for the learner's own check (`self_ok`)."""

    __tablename__ = "real_exam_attempt"

    id: Mapped[uuid.UUID] = _uuid_pk()
    learner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), index=True
    )
    set_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("real_exam_set.id", ondelete="SET NULL"), index=True, nullable=True
    )
    qid: Mapped[str] = mapped_column(String(24))
    qtype: Mapped[str] = mapped_column(String(32))
    tier: Mapped[int] = mapped_column(SmallInteger)
    chosen: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)  # 1-based; None = "chưa biết"
    answer: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    correct: Mapped[bool] = mapped_column(Boolean)
    pending: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    self_ok: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    hints: Mapped[int] = mapped_column(SmallInteger, default=0, server_default="0")
    detail: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (UniqueConstraint("set_id", "qid", name="uq_real_exam_attempt_set_question"),)

    @property
    def right(self) -> bool:
        """Counts as right: what the program judged, or the learner's own check where it has the last word."""
        return self.self_ok if self.self_ok is not None else self.correct


class PlacementAttempt(Base):
    """One sitting of the entry diagnostic. `answers` = what was right or wrong per item and
    `summary` = what was concluded (known patterns, where to start); the latest attempt is the
    learner's starting point."""

    __tablename__ = "placement_attempt"

    id: Mapped[uuid.UUID] = _uuid_pk()
    learner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("profiles.id"), index=True)
    taken_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    answers: Mapped[list] = mapped_column(JSONB, default=list)
    summary: Mapped[dict] = mapped_column(JSONB, default=dict)


class ErrorLog(Base):
    """One wrong answer, kept so the same mistake can be found again: a review
    card answered wrong (`item_type`/`item_id` say which card, `mode` how it was
    asked), an exam question answered wrong (`error_type` is its question type)
    or a writing slip (`error_type` is the kind of slip). `app.services.weakness`
    turns these rows into the "điểm yếu" report and the weak-card queue."""

    __tablename__ = "error_log"

    id: Mapped[uuid.UUID] = _uuid_pk()
    learner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("profiles.id"))
    skill: Mapped[str] = mapped_column(String(32))  # vocab | grammar | đọc | nghe | viết
    error_type: Mapped[str] = mapped_column(String(64))
    example_en: Mapped[str] = mapped_column(Text)
    item_type: Mapped[str | None] = mapped_column(String(16), nullable=True)  # vocab_item | grammar_point
    item_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mode: Mapped[str | None] = mapped_column(String(16), nullable=True)  # recognize | cloze | exam | writing
    detail: Mapped[dict | None] = mapped_column(JSONB, nullable=True)  # what was chosen, the right answer…
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SceneImage(Base):
    """A generated lesson picture (a lesson banner, a word, a grammar point or a practice
    scene — see app.services.lesson_image). `cache_key` identifies the prompt (and house
    style); the bytes (a small WebP) live here for the same reason lecture audio does
    (ephemeral containers). `hidden`: an editor took it off the lessons."""

    __tablename__ = "scene_image"
    __table_args__ = {"schema": "content"}

    cache_key: Mapped[str] = mapped_column(String(48), primary_key=True)
    mime_type: Mapped[str] = mapped_column(String(32))
    data: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    # "db" (the bytes in `data`) or "gcs" (the object `object_key` of the private bucket, `data` empty)
    storage: Mapped[str] = mapped_column(String(16), default="db", server_default="db")
    object_key: Mapped[str | None] = mapped_column(String(300), nullable=True)
    prompt: Mapped[str] = mapped_column(Text)
    model: Mapped[str] = mapped_column(String(64))
    hidden: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    kind: Mapped[str | None] = mapped_column(String(16), nullable=True)  # lesson | vocab | grammar | scene
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class LessonExerciseResult(Base):
    """The learner's latest answer to one question of a lesson's practice set
    (lesson-v5). The question is graded in the browser against the answer that
    ships with the lesson, so this row only records what happened: which
    question, right or wrong, how many tries — enough to show "Luyện tập 7/12"
    on any device and to find the mistakes again. A wrong answer is also written
    to `error_log`, where the weak-spot report already reads."""

    __tablename__ = "lesson_exercise_result"

    id: Mapped[uuid.UUID] = _uuid_pk()
    learner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("profiles.id"), index=True)
    lesson_id: Mapped[int] = mapped_column(ForeignKey("content.lesson.id", ondelete="CASCADE"), index=True)
    exercise_id: Mapped[str] = mapped_column(String(32))
    question_id: Mapped[str] = mapped_column(String(32))
    correct: Mapped[bool] = mapped_column(Boolean)
    attempts: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    # What the learner chose or typed (kept short; shown back in review).
    last_answer: Mapped[str | None] = mapped_column(String(500), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    # "Đã hiểu" in the mistake book: the learner has read the explanation. Cleared by the next wrong answer.
    understood_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("learner_id", "lesson_id", "question_id", name="uq_lesson_exercise_result"),
    )


class ExamAttempt(Base):
    """A learner's answer to one real exam question (the mini-drill). Kept for
    right answers too, so a question type's accuracy can be shown and a question
    answered right recently is not asked again straight away."""

    __tablename__ = "exam_attempt"

    id: Mapped[uuid.UUID] = _uuid_pk()
    learner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), index=True
    )
    exam_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("content.exam_item.id", ondelete="CASCADE")
    )
    chosen: Mapped[int] = mapped_column(SmallInteger)  # 1-based, like ExamItem.answer
    correct: Mapped[bool] = mapped_column(Boolean)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class WritingDrill(Base):
    """One "viết câu 51–52" exercise built from the learner's own cards: a short
    practical text with two blanks (㉠ ㉡), what the learner wrote for them, and
    the check of that. `status` is the generation of the text (pending → ready |
    failed), `grade_status` the check of the answers (none → pending → ready |
    failed). The JSON columns are shaped by app.services.writing_drill."""

    __tablename__ = "writing_drill"

    id: Mapped[uuid.UUID] = _uuid_pk()
    learner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), index=True
    )
    source_items: Mapped[list] = mapped_column(JSONB, default=list)  # [{"item_type", "item_id"}]
    job_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)  # the running generate/grade job
    prompt: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    answers: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    result: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="pending", server_default="pending")
    grade_status: Mapped[str] = mapped_column(String(16), default="none", server_default="none")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class LearnerBankDeck(Base):
    """A deck of the TOPIK word bank the learner added to their reviews (app/services/topik_bank.py)."""

    __tablename__ = "learner_bank_deck"

    learner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), primary_key=True
    )
    deck_key: Mapped[str] = mapped_column(String(64), primary_key=True)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class LessonEssayCheck(Base):
    """An AI check of a paragraph the learner wrote for a lesson's `write_essay` item (Bước 4, the
    Bước 5 own text, Viết 53/54): the text sent, then the score on the item's rubric and the
    corrections (shaped by app.services.essay_check). `status`: pending → ready | failed."""

    __tablename__ = "lesson_essay_check"

    id: Mapped[uuid.UUID] = _uuid_pk()
    learner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), index=True
    )
    lesson_id: Mapped[int] = mapped_column(Integer, ForeignKey("content.lesson.id", ondelete="CASCADE"), index=True)
    exercise_id: Mapped[str] = mapped_column(String(32))
    text: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), default="pending", server_default="pending")
    job_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    result: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ConversationSession(Base):
    """One "Trò chuyện với Haru" voice session (app.services.conversation). The audio never
    reaches this server: the browser talks to Gemini Live with a single-use token minted for this
    row. What comes back at the end is the transcript the browser saw, how long it ran, how often
    the learner needed a nudge, and the report made from it. `seconds` feeds the daily minute cap."""

    __tablename__ = "conversation_session"

    id: Mapped[uuid.UUID] = _uuid_pk()
    learner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), index=True
    )
    lesson_id: Mapped[int | None] = mapped_column(
        ForeignKey("content.lesson.id", ondelete="SET NULL"), nullable=True
    )
    model: Mapped[str] = mapped_column(String(64))
    # the learner let Haru keep what they told about themselves for the next sessions
    remember: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    seconds: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    nudges: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    turns: Mapped[list | None] = mapped_column(JSONB, nullable=True)  # [{"role": "learner"|"haru", "text"}]
    report: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # phase 2-3: the band Haru talked at, what the session measured (app.services.talk_profile.measure)
    # and the per-sentence pronunciation check (app.services.pronunciation; the audio is not kept)
    band: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    metrics: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    pronunciation: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # "Đưa vào ôn tập" was pressed for this session (its words / sentences went to the notebook)
    saved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # phase 4: "talk" (Trò chuyện) or "debate" (Tranh luận · Đàm phán · Phản biện, app.services.debate);
    # for a debate, the scenario played: {"id", "kind", "side", "motion"?}
    kind: Mapped[str] = mapped_column(String(10), default="talk", server_default="talk", index=True)
    scenario: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # how long the session was allowed to run (billing: a trial session never finished counts as all of it)
    allowed_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)


class TalkNote(Base):
    """Sổ trò chuyện: a word to learn or a sentence to say again, kept from a talk with Haru
    ("Đưa vào ôn tập"). Haru brings a few open sentences back into the next talks; the learner
    ticks them off when they have them."""

    __tablename__ = "talk_note"

    id: Mapped[uuid.UUID] = _uuid_pk()
    learner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), index=True
    )
    session_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("conversation_session.id", ondelete="SET NULL"), nullable=True
    )
    kind: Mapped[str] = mapped_column(String(10))  # word | sentence
    ko: Mapped[str] = mapped_column(String(300))
    vi: Mapped[str] = mapped_column(String(300), default="", server_default="")
    # the lesson card this word was found as (then it is in the review queue too)
    vocab_item_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    done_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (UniqueConstraint("learner_id", "kind", "ko", name="uq_talk_note_learner_kind_ko"),)


class PresentationSession(Base):
    """One "Trình bày" round (app.services.presentation): a topic, the learner's notes and outline,
    and up to three tries at saying the answer in one go, each marked (the audio is not kept)."""

    __tablename__ = "presentation_session"

    id: Mapped[uuid.UUID] = _uuid_pk()
    learner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), index=True
    )
    lesson_id: Mapped[int | None] = mapped_column(
        ForeignKey("content.lesson.id", ondelete="SET NULL"), nullable=True
    )
    band: Mapped[int] = mapped_column(SmallInteger)
    level: Mapped[int] = mapped_column(SmallInteger, default=1, server_default="1")
    topic: Mapped[dict] = mapped_column(JSONB)  # question_en, question_vi, angle_vi, words, source
    notes_vi: Mapped[str] = mapped_column(Text, default="", server_default="")
    outline: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    # [{"index", "at", "metrics", "eval", "answers": {"<q>": {...}}}], oldest first
    attempts: Mapped[list] = mapped_column(JSONB, default=list, server_default="[]")
    # phases 2-3: "topic" (a question from the lesson) or "defense" (the learner's own talk: title +
    # material they pasted), and how the round was fitted to the learner (app.services.present_profile):
    # {"base_band", "shift", "focus", "targets": [...], "known": [...]}
    mode: Mapped[str] = mapped_column(String(10), default="topic", server_default="topic")
    title: Mapped[str] = mapped_column(String(200), default="", server_default="")
    material: Mapped[str] = mapped_column(Text, default="", server_default="")
    plan: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)


class LearnerTalkProfile(Base):
    """What Haru carries from one conversation to the next (app.services.talk_profile): the band it
    talks at, the last verdicts that move it, what the last session was about, the thread to pick
    up, and — only what the learner allowed — a few things they told about themselves, each with
    the day it was said. The learner can read and delete the facts on the talk screen."""

    __tablename__ = "learner_talk_profile"

    learner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), primary_key=True
    )
    band: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    verdicts: Mapped[list] = mapped_column(JSONB, default=list, server_default="[]")
    facts: Mapped[list] = mapped_column(JSONB, default=list, server_default="[]")  # [{"text", "at"}]
    last_topics: Mapped[list] = mapped_column(JSONB, default=list, server_default="[]")
    follow_up: Mapped[str | None] = mapped_column(Text, nullable=True)
    sessions: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    # "Trình bày với Haru" (app.services.present_profile): its own band, the verdicts that move it,
    # and per studied item how often it was used correctly in a talk ({key: {"ok_rounds", "miss", ...}})
    present_band: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    present_verdicts: Mapped[list] = mapped_column(JSONB, default=list, server_default="[]")
    present_usage: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    # phase 4: the band debates / negotiations / critiques are pitched at, and the verdicts that move it
    debate_band: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    debate_verdicts: Mapped[list] = mapped_column(JSONB, default=list, server_default="[]")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


# ------------------------------------------------------------------ writing --
class WritingSubmission(Base):
    """State machine (SDD §11):
    uploaded ↔ image_rejected → transcribing → awaiting_confirmation →
    grading → graded → revising → revised → rewriting → grading (loop)
    """

    __tablename__ = "writing_submission"

    id: Mapped[uuid.UUID] = _uuid_pk()
    learner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("profiles.id"))
    prompt_id: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(
        Enum(
            "uploaded",
            "image_rejected",
            "transcribing",
            "awaiting_confirmation",
            "grading",
            "graded",
            "revising",
            "revised",
            "rewriting",
            name="writing_submission_status",
        ),
        default="uploaded",
    )
    image_key: Mapped[str] = mapped_column(String(500))
    transcript: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class WritingScore(Base):
    __tablename__ = "writing_score"

    id: Mapped[uuid.UUID] = _uuid_pk()
    submission_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("writing_submission.id", ondelete="CASCADE")
    )
    criteria: Mapped[dict] = mapped_column(JSONB)
    score_min: Mapped[int] = mapped_column(Integer)
    score_max: Mapped[int] = mapped_column(Integer)
    priority_fixes: Mapped[dict] = mapped_column(JSONB, default=list)

    __table_args__ = (CheckConstraint("score_min <= score_max", name="ck_writing_score_range"),)


# ------------------------------------------------------------------- ingest --
class ImportBatch(Base):
    """queued → extracting → validating → awaiting_review →
    confirmed|cancelled → rolled_back (extracting/validating can → failed)
    """

    __tablename__ = "import_batch"

    id: Mapped[uuid.UUID] = _uuid_pk()
    kind: Mapped[str] = mapped_column(
        Enum("lesson", "corpus", "exam_paper", "editorial_article", name="import_kind")
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("profiles.id"))
    status: Mapped[str] = mapped_column(
        Enum(
            "queued",
            "extracting",
            "validating",
            "awaiting_review",
            "confirmed",
            "cancelled",
            "rolled_back",
            "failed",
            name="import_batch_status",
        ),
        default="queued",
    )
    flagged_count: Mapped[int] = mapped_column(Integer, default=0)
    source_file: Mapped[str | None] = mapped_column(String(255), nullable=True)
    file_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # Bare id, no FK — only meaningful for kind="corpus"; crosses into
    # `corpus` schema, same bare-id convention as corpus_item.topic_ids.
    film_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Bare id, no FK — only meaningful for kind="exam_paper"; crosses into
    # `content` schema. Set inside extract_exam_paper_import (same
    # find-or-create-immediately timing as film_id, since exam_kind/
    # session_label are admin-typed, not AI-derived).
    exam_paper_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    # Bare id, no FK — only meaningful for kind="editorial_article";
    # crosses into the new `editorial` schema. Same immediate-creation
    # timing as film_id/exam_paper_id: source_url/source_name are
    # admin-typed at submission time, so find_or_create_editorial_article
    # runs before extraction, not after.
    editorial_article_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("kind", "file_hash", name="uq_import_batch_kind_file_hash"),
    )


class ImportItem(Base):
    __tablename__ = "import_item"

    id: Mapped[uuid.UUID] = _uuid_pk()
    import_batch_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("import_batch.id", ondelete="CASCADE")
    )
    kind: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(
        Enum("pending", "flagged_yellow", "flagged_red", "confirmed", "rejected", name="import_item_status"),
        default="pending",
    )
    payload: Mapped[dict] = mapped_column(JSONB)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)


# --------------------------------------------------------------- editorial --
# New module (not in the original SRS/SDD): short Korean editorials/columns
# (사설, 칼럼) as reading practice that scaffolds TOPIK 쓰기 question 54 —
# see the "Đề xuất SRS/SDD" doc for the full proposal this implements.
# Same staging convention as everything else: extraction stages
# import_item rows (kind="editorial_meta"/"vocab_item"/"grammar_point"),
# and only POST /imports/{id}/confirm writes here.
class EditorialSource(Base):
    """A registered outlet (KBS/Chosun Ilbo/Naver News...). Admin-managed
    config, not staged — same immediacy as Film/ExamPaper naming."""

    __tablename__ = "editorial_source"
    __table_args__ = {"schema": "editorial"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    base_url: Mapped[str] = mapped_column(String(500))
    rss_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    license_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class EditorialArticle(Base):
    """Created immediately (find_or_create, keyed by `source_url`) when an
    editorial_article import_batch is submitted — same timing as Film/
    ExamPaper, since source_url/source_name are admin-given, not
    AI-derived. Enrichment fields (title_en..thinking_guide_text) start
    NULL and are filled in by apply_editorial_batch once the single
    "editorial_meta" import_item is confirmed — `import_item_id` records
    that lineage so rollback can reset them. `vocab_ids`/`grammar_ids` are
    bare arrays into content.vocab_item/grammar_point (cross-schema — no
    physical FK, same convention as corpus_item.topic_ids).

    Full body text (not just an excerpt) is intentionally in scope here:
    the owner has confirmed this deployment is for internal/family use
    only, not published publicly, so the usual excerpt-only copyright
    mitigation doesn't apply — see the proposal doc's §4 for the general
    (public-deployment) recommendation this deliberately overrides.
    """

    __tablename__ = "editorial_article"
    __table_args__ = {"schema": "editorial"}

    id: Mapped[uuid.UUID] = _uuid_pk()
    source_name: Mapped[str] = mapped_column(String(120))
    source_url: Mapped[str] = mapped_column(String(1000), unique=True)
    title_en: Mapped[str | None] = mapped_column(String(500), nullable=True)
    topic_tags: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    level_estimate: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    published_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    body_en: Mapped[str | None] = mapped_column(Text, nullable=True)
    vocab_ids: Mapped[list[int]] = mapped_column(ARRAY(Integer), default=list)
    grammar_ids: Mapped[list[int]] = mapped_column(ARRAY(Integer), default=list)
    model_outline: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    thinking_guide_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Inline photos scraped with the article: [{url, caption, after_paragraph}]
    # (hotlinked, not copied — same internal/family-use scope as body_en).
    # `images_fetched_at` NULL = never attempted: GET /editorials/{id} then
    # queues a one-off refresh_editorial_images so articles imported before
    # this column existed get their photos without any admin action.
    images: Mapped[list[dict]] = mapped_column(JSONB, default=list, server_default="[]")
    images_fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Beginner "reading ladder" generated once per article (see
    # app.services.study_pack): Vietnamese summary, per-sentence translation /
    # word breakdown / grammar notes, simplified-Korean paragraphs. `study_status`
    # is none | pending | ready | failed; `study_updated_at` doubles as the
    # worker's heartbeat so a dead task is noticed and re-queued.
    study_pack: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    study_status: Mapped[str] = mapped_column(String(16), default="none", server_default="none")
    study_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # The reading path: the course lessons this article follows (closest first; empty = not placed on
    # the path), a one-line "when to read it", and the questions asked right after reading
    # ([{type: mcq|apply, skill, prompt_en|prompt_vi, options, answer_index, explanation_vi, model_en}]).
    related_lesson_ids: Mapped[list[int]] = mapped_column(ARRAY(Integer), default=list, server_default="{}")
    unlock_hint: Mapped[str | None] = mapped_column(Text, nullable=True)
    practice: Mapped[list[dict] | None] = mapped_column(JSONB, nullable=True)
    import_item_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EditorialRead(Base):
    """An article the learner marked "đã đọc xong" (a short passage has no outline to write).
    `editorial_article_id` is a bare id, like the outline submission's."""

    __tablename__ = "editorial_read"
    __table_args__ = {"schema": "editorial"}

    learner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), primary_key=True)
    editorial_article_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EditorialOutlineSubmission(Base):
    """A learner's own 4-part outline/notes for one article (현상/원인/
    결과/대책 — Hiện tượng/Nguyên nhân/Hậu quả/Giải pháp) — brainstorm
    practice for TOPIK 쓰기 câu 54, not a graded essay. One row per
    (learner, article); re-saving updates it in place and bumps
    `revision_count`. `editorial_article_id` is a bare id (cross-schema,
    no FK); `learner_id` DOES get a real FK — `profiles` is the shared
    identity table every module is allowed to FK into (same convention as
    analytics.learning_event.learner_id)."""

    __tablename__ = "editorial_outline_submission"
    __table_args__ = (
        UniqueConstraint("learner_id", "editorial_article_id", name="uq_editorial_outline_learner_article"),
        {"schema": "editorial"},
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    learner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), index=True
    )
    editorial_article_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    phenomenon_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    cause_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    consequence_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    solution_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    revision_count: Mapped[int] = mapped_column(Integer, default=0)
    # Real Gemini feedback on the learner's OWN outline (added per owner
    # feedback — previously saving an outline never actually analyzed it).
    # "none" until a save first triggers grade_editorial_outline, "pending"
    # while that Celery job runs, then "ready"/"failed".
    feedback_status: Mapped[str] = mapped_column(String(16), default="none")
    feedback_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class EditorialCandidate(Base):
    """RSS auto-discovery staging (SRS/SDD proposal doc §3, "Giai đoạn
    sau" — implemented now per owner's request). A periodic Celery task
    (discover_editorial_candidates) upserts rows here from official RSS
    feeds; nothing here is ever auto-published — an admin browses these in
    Studio and picks one, which POSTs it through the normal
    `imports?kind=editorial_article` flow (marking this row "ingested").
    Keeps the SDD's "nguồn staged, con người xác nhận" rule: only the
    *search* step is automated."""

    __tablename__ = "editorial_candidate"
    __table_args__ = {"schema": "editorial"}

    id: Mapped[uuid.UUID] = _uuid_pk()
    source_name: Mapped[str] = mapped_column(String(120))
    source_url: Mapped[str] = mapped_column(String(1000), unique=True)
    title_en: Mapped[str] = mapped_column(String(500))
    snippet_en: Mapped[str | None] = mapped_column(Text, nullable=True)
    topic_tags: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    published_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(
        Enum("new", "dismissed", "ingested", name="editorial_candidate_status"), default="new"
    )
    discovered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# ------------------------------------------------------------------ billing --
# Paid access (app/services/billing). Money rows are never deleted. A learner's rights are the
# `entitlement` rows, not the status of an order: changing or refunding an order never silently
# takes a lesson away, an admin revokes an entitlement on purpose.
ORDER_STATUSES = ("PENDING", "PAID", "EXPIRED", "CANCELLED", "UNDERPAID", "NEEDS_REVIEW")


class BillingOrder(Base):
    """One attempt to buy one product. `amount` is the catalogue price read on the server when the
    order was made (the client only names the product). `order_code` is the number payOS knows it by."""

    __tablename__ = "orders"
    __table_args__ = (
        CheckConstraint(
            "status in ('PENDING','PAID','EXPIRED','CANCELLED','UNDERPAID','NEEDS_REVIEW')", name="ck_billing_order_status"
        ),
        CheckConstraint("amount > 0", name="ck_billing_order_amount"),
        Index("ix_billing_orders_profile_created", "profile_id", "created_at"),
        {"schema": "billing"},
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    order_code: Mapped[int] = mapped_column(BigInteger, unique=True)
    profile_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="RESTRICT"))
    product_code: Mapped[str] = mapped_column(String(40))
    amount: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(16), default="PENDING", index=True)
    payment_link_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    checkout_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    # what the paying screen shows: bank bin / account / name, the transfer content, the QR string
    payment_info: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # the sum of the payments (billing.payment_event) that name this order
    paid_amount: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    # the bank reference of the payment that completed the order
    provider_ref: Mapped[str | None] = mapped_column(String(80), nullable=True)
    # an admin should look at it: money in excess of the price, a second payment, a short payment
    needs_review: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # the price before a discount code, the discount, and the code (amount = list_amount - discount)
    list_amount: Mapped[int | None] = mapped_column(Integer, nullable=True)
    discount: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    coupon_code: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class PaymentEvent(Base):
    """Money that reached payOS for an order code (from a webhook or from the reconcile job). The
    bank `reference` is UNIQUE: the same payment seen twice (webhook retry, webhook + reconcile)
    is counted once. Only signed events are stored; nothing here is a key."""

    __tablename__ = "payment_event"
    __table_args__ = (
        UniqueConstraint("reference", name="uq_billing_payment_event_reference"),
        {"schema": "billing"},
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    reference: Mapped[str] = mapped_column(String(120))
    order_code: Mapped[int] = mapped_column(BigInteger, index=True)
    order_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    amount: Mapped[int] = mapped_column(Integer)
    source: Mapped[str] = mapped_column(String(16))  # webhook | reconcile
    outcome: Mapped[str] = mapped_column(String(24))  # granted | underpaid | extra | unknown_order | ...
    raw: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Entitlement(Base):
    """A right a learner holds: a lesson pack (lifetime), an exam pass (until `ends_at`) or a grant.
    (`order_id`, `product_code`) is UNIQUE: one paid order grants each of its products once (a
    combo grants several), however many times it is processed."""

    __tablename__ = "entitlement"
    __table_args__ = (
        UniqueConstraint("order_id", "product_code", name="uq_billing_entitlement_order_product"),
        CheckConstraint("kind in ('lesson_pack','exam_pass','feature_pass','grant')", name="ck_billing_entitlement_kind"),
        {"schema": "billing"},
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="RESTRICT"), index=True
    )
    kind: Mapped[str] = mapped_column(String(16))
    product_code: Mapped[str] = mapped_column(String(40))
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)  # None = for life
    source: Mapped[str] = mapped_column(String(16))  # order | admin | grandfather | voucher
    order_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("billing.orders.id", ondelete="RESTRICT"), nullable=True
    )
    granted_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ProductSetting(Base):
    """An admin's change to a catalogue product (app/services/billing/catalog.py): its price, a
    struck-through "was" price, its name and blurb, on sale or not. A null field keeps the default."""

    __tablename__ = "product_setting"
    __table_args__ = ({"schema": "billing"},)

    product_code: Mapped[str] = mapped_column(String(40), primary_key=True)
    amount: Mapped[int | None] = mapped_column(Integer, nullable=True)
    compare_at: Mapped[int | None] = mapped_column(Integer, nullable=True)
    title_vi: Mapped[str | None] = mapped_column(String(120), nullable=True)
    blurb_vi: Mapped[str | None] = mapped_column(Text, nullable=True)
    active: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class FeatureRule(Base):
    """How a feature is sold (app/services/billing/features.py): free for all, a one-time trial
    per account then a pass, or pass only."""

    __tablename__ = "feature_rule"
    __table_args__ = (
        CheckConstraint("mode in ('free','trial','paid')", name="ck_billing_feature_rule_mode"),
        {"schema": "billing"},
    )

    feature: Mapped[str] = mapped_column(String(20), primary_key=True)
    mode: Mapped[str] = mapped_column(String(8))
    updated_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class BillingSetting(Base):
    """A number an admin sets for billing (the trial's size: live_trial_minutes, present_trial_tries)."""

    __tablename__ = "setting"
    __table_args__ = ({"schema": "billing"},)

    key: Mapped[str] = mapped_column(String(40), primary_key=True)
    value: Mapped[int] = mapped_column(Integer)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Coupon(Base):
    """A discount code (app/services/billing/coupons.py). `used` counts PAID orders only."""

    __tablename__ = "coupon"
    __table_args__ = (
        CheckConstraint(
            "(percent_off is null) <> (amount_off is null)", name="ck_billing_coupon_one_kind"
        ),
        CheckConstraint("percent_off is null or (percent_off between 1 and 90)", name="ck_billing_coupon_percent"),
        CheckConstraint("amount_off is null or amount_off > 0", name="ck_billing_coupon_amount"),
        {"schema": "billing"},
    )

    code: Mapped[str] = mapped_column(String(32), primary_key=True)  # upper case
    percent_off: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    amount_off: Mapped[int | None] = mapped_column(Integer, nullable=True)
    product_codes: Mapped[list | None] = mapped_column(JSONB, nullable=True)  # null = every product
    max_uses: Mapped[int | None] = mapped_column(Integer, nullable=True)  # null = no limit
    once_per_learner: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())
    used: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class BillingClaim(Base):
    """"I paid but nothing unlocked": a learner's report, answered by an admin."""

    __tablename__ = "claim"
    __table_args__ = (
        CheckConstraint("status in ('open','resolved','rejected')", name="ck_billing_claim_status"),
        {"schema": "billing"},
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="RESTRICT"), index=True
    )
    order_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("billing.orders.id", ondelete="RESTRICT"), nullable=True
    )
    note: Mapped[str] = mapped_column(Text)
    bank_ref: Mapped[str | None] = mapped_column(String(80), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="open", index=True)
    resolution: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AccountSignal(Base):
    """Which browser (the app's random device id) and which network (IP) an account was seen from,
    both stored as a keyed hash (app/services/abuse.py), never the raw value."""

    __tablename__ = "account_signal"
    __table_args__ = (
        CheckConstraint("kind in ('device','ip')", name="ck_billing_account_signal_kind"),
        UniqueConstraint("profile_id", "kind", "value", name="uq_billing_account_signal"),
        Index("ix_billing_account_signal_value", "kind", "value"),
        {"schema": "billing"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    profile_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"))
    kind: Mapped[str] = mapped_column(String(8))
    value: Mapped[str] = mapped_column(String(64))
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    seen_count: Mapped[int] = mapped_column(Integer, default=1, server_default="1")


class TrialUse(Base):
    """One start on the free trial: a live session (`amount` = seconds granted) or a marked
    presentation try (`amount` = 1), with the hashed browser and network it came from."""

    __tablename__ = "trial_use"
    __table_args__ = (
        Index("ix_billing_trial_use_created", "created_at"),
        Index("ix_billing_trial_use_device", "device"),
        Index("ix_billing_trial_use_ip", "ip", "created_at"),
        Index("ix_billing_trial_use_profile", "profile_id"),
        {"schema": "billing"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    profile_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"))
    feature: Mapped[str] = mapped_column(String(20))
    amount: Mapped[int] = mapped_column(Integer)
    device: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class BlockedEmailDomain(Base):
    """A throwaway-mail domain an admin added on top of the bundled list."""

    __tablename__ = "blocked_email_domain"
    __table_args__ = ({"schema": "billing"},)

    domain: Mapped[str] = mapped_column(String(253), primary_key=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SiteSetting(Base):
    """A piece of site content an admin sets (key "support": the help channels shown to learners)."""

    __tablename__ = "site_setting"
    __table_args__ = ({"schema": "billing"},)

    key: Mapped[str] = mapped_column(String(40), primary_key=True)
    value: Mapped[dict] = mapped_column(JSONB)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class LessonPartDone(Base):
    """A part of a lesson the learner has finished that leaves no other record: the five parts of
    the alphabet lesson (each one a feather, app/services/feathers.py)."""

    __tablename__ = "lesson_part_done"

    learner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), primary_key=True
    )
    lesson_id: Mapped[int] = mapped_column(Integer, ForeignKey("content.lesson.id", ondelete="CASCADE"), primary_key=True)
    part_id: Mapped[str] = mapped_column(String(16), primary_key=True)
    done_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class LearnerDay(Base):
    """A day (Vietnam time) on which the learner studied (app/services/journey.py)."""

    __tablename__ = "learner_day"

    learner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), primary_key=True
    )
    day: Mapped[date] = mapped_column(Date, primary_key=True)


class Journey(Base):
    """The stage of Hành trình Thiên Nga a learner has reached (1–5, only goes up)."""

    __tablename__ = "journey"
    __table_args__ = (CheckConstraint("stage between 1 and 5", name="ck_journey_stage"),)

    learner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), primary_key=True
    )
    stage: Mapped[int] = mapped_column(SmallInteger, default=1, server_default="1")
    reached_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    # earned for good from the support topics (app/services/feathers.py): the relics of the topics
    # finished, and the highest sparkle reached; adding lessons later never takes them back
    relics: Mapped[list] = mapped_column(JSONB, default=list, server_default=text("'[]'::jsonb"))
    sparkle: Mapped[int] = mapped_column(SmallInteger, default=0, server_default="0")

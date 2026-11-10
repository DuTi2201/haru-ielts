"""Pydantic schemas — the contract the Lovable client's TypeScript types
must mirror exactly (see initial Lovable message: "Khai báo TypeScript
types đồng bộ chính xác với Pydantic schemas của backend FastAPI").
"""
import uuid
from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, EmailStr, Field, computed_field, field_serializer, field_validator

from app.services.grammar_text import split_source_note, usage_sections
from app.services.grammar_tier import effective_use_level, grammar_tier

JobStatus = Literal["queued", "running", "succeeded", "failed", "cancelled"]
Role = Literal["learner", "editor", "admin"]


# --------------------------------------------------------------------- auth --
class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    display_name: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=200)
    new_password: str = Field(min_length=8, max_length=72)

    @field_validator("new_password")
    @classmethod
    def _fits_bcrypt(cls, v: str) -> str:
        # bcrypt reads at most 72 BYTES; a long password with accents must not be cut silently
        if len(v.encode("utf-8")) > 72:
            raise ValueError("password is longer than 72 bytes")
        return v


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"


class ProfileOut(BaseModel):
    id: uuid.UUID
    email: EmailStr
    role: Role
    display_name: str | None
    goal: str | None
    exam_date: datetime | None
    daily_minutes: int
    # an admin set a temporary password: the app asks for a new one before anything else
    must_change_password: bool = False

    model_config = {"from_attributes": True}


# --------------------------------------------------------------------- jobs --
class JobOut(BaseModel):
    id: uuid.UUID
    type: str
    status: JobStatus
    progress: float
    step: str | None
    result: dict[str, Any] | None
    error: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class JobAccepted(BaseModel):
    """The SDD's "202 Accepted + Job ID" envelope."""

    job_id: uuid.UUID
    status: JobStatus = "queued"
    poll_url: str
    events_url: str


class ProblemDetail(BaseModel):
    """RFC 9457 problem+json, as SDD §7 requires for all error responses."""

    type: str = "about:blank"
    title: str
    status: int
    detail: str | None = None
    code: str | None = None
    retryable: bool | None = None


# ------------------------------------------------------------------- audio --
VoiceId = Literal[
    "en-female-1",
    "en-female-2",
    "en-male-1",
    "en-male-2",
    "ko-female-1",
    "ko-female-2",
    "ko-male-1",
    "ko-male-2",
]


class LectureAudioRequest(BaseModel):
    lesson_id: str
    text_en: str
    voice: str = "en-female-1"
    prompt_version: str = "v1"


class CorpusAudioRequest(BaseModel):
    """No corpus_item_id field — it's the path param on POST
    /corpus/{corpus_item_id}/audio (mirrors LectureAudioRequest's shape,
    minus the redundant id). The sentence itself is read from the database: `text_en` is
    accepted for older clients and ignored."""

    text_en: str | None = None
    voice: VoiceId = "en-female-1"
    # Part of the audio cache key, and owned by the server: "v2" = the first generation
    # voiced by Google Chirp 3 HD; clips cached under "v1" (Gemini voice) are not reused.
    prompt_version: Literal["v2"] = "v2"


class VocabAudioRequest(BaseModel):
    """The word is read from the database (content.vocab_item.headword): `text_en` is
    accepted for older clients and ignored, so a request can neither make the server
    voice something else nor file it under a word's key. Voice and version are fixed
    sets for the same reason — a new value would be a new cache entry to pay for."""

    text_en: str | None = None
    voice: VoiceId = "en-female-1"
    prompt_version: Literal["v1"] = "v1"


class TextAudioRequest(BaseModel):
    """POST /audio/text: read this English text aloud. The server checks it (English only, a length
    cap) and files the recording under a hash of what it says, so asking again is free. The voice
    and version are fixed sets, as for a word: a new value would be a new recording to pay for."""

    text: str = Field(min_length=1, max_length=4000)
    voice: VoiceId = "en-female-1"
    prompt_version: Literal["v1"] = "v1"


class PodcastRequest(BaseModel):
    """POST /lessons/{id}/podcast and /editorials/{id}/podcast: no text
    from the caller at all — unlike lecture/corpus/vocab audio, THIS
    endpoint generates its own script (Gemini synthesizes the lesson's/
    article's vocab+grammar into one consolidated teaching script) before
    handing it to TTS. See app.workers.tasks.generate_content_podcast."""

    voice: str = "ko-female-1"
    # lessons only: the lecture of this sitting ("buổi", 1-based) alone, not the whole lesson's
    sitting: int | None = Field(default=None, ge=1, le=40)
    # Accepted for compatibility but ignored: the server decides which prompt
    # version writes the lecture (app.services.podcast_script.PODCAST_VERSION),
    # so improving the prompt regenerates lectures without a client release.
    prompt_version: str = "podcast-v2"
    # lesson-v5, lessons only. "template" (default): a fixed script built from the
    # lesson itself, no model involved. "story": Gemini retells the lesson as a
    # lecture (long lessons are written in parts and joined). Each is stored and
    # reused on its own. Articles ignore this and always use Gemini.
    mode: Literal["template", "story"] = "template"


class ArticleAudioRequest(BaseModel):
    """POST /editorials/{id}/audio: reads the article's OWN body_en text
    aloud verbatim (native-length sentences, real pacing/pauses) — no
    Gemini script-writing step at all, unlike PodcastRequest. Deliberately
    separate from the podcast feature: a learner listening to the actual
    news article and a learner listening to a teaching script ABOUT its
    vocab/grammar are two different study modes, cached independently
    (see app.workers.tasks.generate_article_audio)."""

    voice: str = "ko-female-1"
    prompt_version: str = "article-v1"
    # "original" = the article's own text; "easy" = the simplified-Korean
    # (TOPIK 1-2) rewrite from the study pack, for beginners who can't follow
    # the original at native speed yet. Cached independently per text.
    variant: Literal["original", "easy"] = "original"


# ----------------------------------------------------------------- writing --
class WritingSubmissionOut(BaseModel):
    id: uuid.UUID
    prompt_id: str
    status: str
    transcript: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class WritingConfirmTranscriptRequest(BaseModel):
    transcript: str


class WritingScoreOut(BaseModel):
    submission_id: uuid.UUID
    criteria: dict[str, Any]
    score_min: int
    score_max: int
    priority_fixes: list[dict[str, Any]]

    model_config = {"from_attributes": True}


# ------------------------------------------------------------------ content --
class TopicOut(BaseModel):
    id: int
    name: str
    quizlet_url: str | None

    model_config = {"from_attributes": True}


class CollocationOut(BaseModel):
    ko: str
    vi: str


class ContrastOut(BaseModel):
    pattern: str
    diff_vi: str


class VocabItemOut(BaseModel):
    id: int
    lesson_id: int | None
    headword: str
    pos: str | None
    meaning_vi: str
    definition_en: str | None
    level: int
    hanja: str | None
    sino_vietnamese: str | None
    example_en: str | None
    example_vi: str | None = None
    # chunk layers (lesson-v4); null on cards extracted before they existed
    family: str | None = None
    node_word: str | None = None
    register: str | None = None
    # the exam course this word is part of as well: "kiip-3" = KIIP stage 3 (null = none)
    exam: str | None = None
    # "core" = learn it now, "recognize" = understand it when met; null for article words
    priority: str | None = None
    usage_note_vi: str | None = None
    # the standard pronunciation when it differs from the spelling: "[학쌩]"
    pron_en: str | None = None
    collocations: list[CollocationOut] | None = None
    distractors: list[str] | None = None
    # lesson-v5 pictures: URL of this word's picture when one has been made (and not hidden)
    image_url: str | None = None

    model_config = {"from_attributes": True}


class UsageSectionOut(BaseModel):
    key: Literal["form", "when", "why", "lesson", "level", "other"]
    label: str | None = None
    body_vi: str


class GrammarRefOut(BaseModel):
    """Another card, as a link from a card: its pattern and the lesson it is taught in."""

    pattern: str
    lesson_id: int
    lesson_title: str
    importance: Literal["must", "normal"] | None = None


class GrammarPointOut(BaseModel):
    id: int
    lesson_id: int | None
    pattern: str
    meaning_vi: str
    level: int
    example_en: str | None
    # lesson-v5: several examples are one per line, example_vi aligned line by line
    example_vi: str | None = None
    note_vi: str | None = None
    usage_context_vi: str | None = None
    exam_tip_vi: str | None = None
    contrast_group: str | None = None
    contrasts: list[ContrastOut] | None = None
    exam: str | None = None  # the exam course this card is part of as well ("kiip-3"), or null
    image_url: str | None = None  # the illustration of this pattern, when one has been made
    # "must" (Bắt buộc) | "normal" (Bổ trợ); null on an extension card (it has `use_level`)
    importance: Literal["must", "normal"] | None = None
    # the earlier cards this one is made of, and the later cards made of this one; filled by the
    # lesson endpoint (app.services.grammar_graph)
    built_from: list[GrammarRefOut] = []
    built_into: list[GrammarRefOut] = []
    # spaced review: the earlier card this one teaches again (filled by the lesson endpoint)
    revisit_of: GrammarRefOut | None = None
    # the level the card itself carries (the column); `use_level` below is what the learner is told
    use_level_set: Literal["recognize", "produce"] | None = Field(default=None, validation_alias="use_level", exclude=True)

    model_config = {"from_attributes": True}

    # "extension" cards are the authored 🟣 additions, read from the card's own text
    # (app.services.grammar_tier); `use_level` says whether the exam only asks the learner to
    # recognise the pattern (👁 nhận ra) or to use it (✍ dùng được): the level written on the card,
    # else the one in an extension card's marker line, else "produce".
    @computed_field  # type: ignore[prop-decorator]
    @property
    def tier(self) -> Literal["core", "extension"]:
        return grammar_tier(self.usage_context_vi)[0]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def use_level(self) -> Literal["recognize", "produce"]:
        return effective_use_level(self.usage_context_vi, self.use_level_set)

    # The same text, cut into the parts the app lays out one by one (app.services.grammar_text);
    # `usage_context_vi` and `note_vi` keep their old shape for older clients, except that the
    # provenance line leaves `note_vi` and is served as `source_note_vi` (a footnote).
    @computed_field  # type: ignore[prop-decorator]
    @property
    def usage_sections(self) -> list[UsageSectionOut]:
        return [UsageSectionOut(key=s.key, label=s.label, body_vi=s.body_vi) for s in usage_sections(self.usage_context_vi)]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def source_note_vi(self) -> str | None:
        return split_source_note(self.note_vi)[1]

    @field_serializer("note_vi")
    def _note_without_source(self, value: str | None) -> str | None:
        return split_source_note(value)[0]


class NoteOut(BaseModel):
    title: str | None = None
    body: str
    # goal | language | sample | fact | writing | pitfall (None on lessons from before kinds)
    kind: str | None = None
    exam: str | None = None  # "kiip-3": a note the KIIP course needs too


class CoachCheckOut(BaseModel):
    prompt_vi: str
    answer: str | None = None


class CoachOut(BaseModel):
    """"Việc cần làm" at the top of a lesson: study advice written for this lesson. The counts shown
    next to it (words, cards, questions) come from the lesson itself, not from here."""

    goal_vi: str | None = None
    focus_vi: list[str] = []
    watch_out_vi: list[str] = []
    notebook_vi: list[str] = []
    self_check: list[CoachCheckOut] = []
    tip_vi: str | None = None


class SessionOut(BaseModel):
    """One hand-planned sitting of a lesson (see app.services.lesson_seed.SessionSeed). Words and
    cards are named by their `headword` / `pattern`; the closing questions by exercise id."""

    title_vi: str
    can_do_vi: str
    use_vi: str | None = None
    topik_vi: str | None = None
    vocab: list[str] = []
    grammar: list[str] = []
    check: list[str] = []
    # a short dialogue situation closing the sitting (lesson_seed.SituationSeed), passed through as is
    situation: dict | None = None


class PracticeCountsOut(BaseModel):
    """What a lesson's practice set holds, small enough to ride along in the lesson list."""

    items: int = 0
    questions: int = 0
    by_skill: dict[str, int] = {}


class LessonTotalsOut(BaseModel):
    """How much a locked lesson holds, shown with its preview."""

    vocab: int = 0
    grammar: int = 0
    notes: int = 0


class LessonOut(BaseModel):
    id: int
    title: str
    level: int
    content: str
    created_at: datetime
    topics: list[TopicOut]
    vocab: list[VocabItemOut]
    grammar: list[GrammarPointOut]
    # lesson-v5 (null on a lesson that predates the seeded format)
    slug: str | None = None
    title_en: str | None = None
    summary: str | None = None
    track: Literal["beginner", "intermediate", "advanced"] | None = None
    sort_order: int = 0
    # "review" = the topic's review lesson: no vocab/grammar of its own, a grammar map, a timed
    # mixed set and a capstone (see app.services.lesson_seed.ReviewSeed)
    kind: Literal["lesson", "review", "hangul"] = "lesson"
    notes: list[NoteOut] = []
    coach: CoachOut | None = None
    sessions: list[SessionOut] = []
    # The practice set itself is fetched on demand (GET /lessons/{id}/practice).
    practice: PracticeCountsOut | None = None
    image_url: str | None = None  # the lesson's banner picture, when one has been made
    # paid access: "free" (also every lesson while billing is off), "owned" (bought / granted) or
    # "locked" — then this is only a PREVIEW (the goal, the first three words, `totals`) and
    # `unlock_with` lists the product codes that open it (GET /billing/catalog)
    access: Literal["free", "owned", "locked"] = "free"
    unlock_with: list[str] = []
    totals: "LessonTotalsOut | None" = None


class KiipCountsOut(BaseModel):
    """How much of a lesson is part of the KIIP course (items tagged `kiip-N`), for the picker.
    `stages` counts words + cards + notes by stage ("kiip-3": 12); `mastered` is how many of the
    tagged words and cards the signed-in learner has mastered (None for an anonymous caller)."""

    vocab: int = 0
    grammar: int = 0
    notes: int = 0
    stages: dict[str, int] = {}
    mastered: int | None = None


class LessonSummaryOut(BaseModel):
    """One row of the lesson picker (GET /lessons): enough to choose a lesson
    without fetching its whole content."""

    id: int
    title: str
    level: int
    topics: list[str]
    vocab_count: int
    grammar_count: int
    # Items of this lesson the signed-in learner has mastered; None when the
    # caller is anonymous (nothing to report — not "0").
    mastered: int | None = None
    # True for the lesson /me/plan would hand this learner next (never for anonymous callers).
    is_next: bool = False
    kind: Literal["lesson", "review", "hangul"] = "lesson"
    # lesson-v5
    slug: str | None = None
    title_en: str | None = None
    summary: str | None = None
    track: Literal["beginner", "intermediate", "advanced"] | None = None
    sort_order: int = 0
    practice: PracticeCountsOut | None = None
    # Practice questions the signed-in learner has answered right / answered at all
    # (None for an anonymous caller).
    practice_correct: int | None = None
    practice_answered: int | None = None
    image_url: str | None = None  # the lesson's banner picture (thumbnail in the picker)
    topic_image_url: str | None = None  # the cover of its (first) topic, for the topic card
    # words / cards / notes of this lesson that the KIIP course needs too (None = none are tagged)
    kiip: KiipCountsOut | None = None
    # Hành trình Thiên Nga (app/services/feathers.py): the chapter of a main lesson (None: a
    # support lesson, then `support` is its constellation), its feathers, and the signed-in
    # learner's earned ones (None for an anonymous caller)
    chapter: int | None = None
    support: str | None = None
    feathers_total: int = 0
    feathers_earned: int | None = None
    # paid access, see LessonOut
    access: Literal["free", "owned", "locked"] = "free"
    unlock_with: list[str] = []


class LessonPracticeOut(BaseModel):
    """GET /lessons/{id}/practice — the lesson's whole practice set. The exercises
    are the validated seed shape (app.services.lesson_seed); answers and
    explanations ship with them because the browser grades instantly."""

    lesson_id: int
    # each item may carry `tier` ("warm" / "challenge": a long text with many words not met yet,
    # shown after the rest), `new_words` (how many) and `support` (words, grammar ahead with the
    # `lesson_id` that teaches it, a three-step hint) — app/services/practice_tiers.py
    items: list[dict[str, Any]]
    guides: dict[str, list[dict[str, Any]]] = {}
    # question type -> {name_vi, how_vi}: the types this lesson is the first in the course to use
    type_intro: dict[str, dict[str, str]] = {}
    overview: dict[str, Any] | None = None
    extension: dict[str, Any] | None = None
    # pattern -> the grammar card a question is linked to (`grammar: [pattern, …]` on the
    # question): meaning, tier (core / extension), 👁/✍ level, the lesson that teaches it
    # (`lesson_id` to open it) and its first contrast. Empty when nothing is linked.
    grammar: dict[str, dict[str, Any]] = {}
    # the topic review lesson only: grammar map by function, the timed mixed set and the
    # capstone (`review.cards` = pattern -> card info with `lesson_id`)
    kind: Literal["lesson", "review", "hangul"] = "lesson"
    review: dict[str, Any] | None = None
    # Bảng chữ cái only (kind "hangul"): its five parts (app.services.lesson_seed.HangulSeed)
    hangul: dict[str, Any] | None = None
    # image prompt -> URL of the generated picture; empty unless scene pictures are
    # switched on (app.services.lesson_image) and have been made. The lesson draws every
    # scene from icons whether or not there is a picture.
    scene_images: dict[str, str] = {}


class ReuseCandidateOut(BaseModel):
    """An existing picture that could stand in for a missing one (a word of the same meaning)."""

    key: str  # the existing picture
    label: str  # the word it was made for
    meaning: str | None = None
    why: str  # "Cùng nghĩa với …"
    confident: bool = False  # sure enough for the "reuse all sure ones" button
    url: str


class ImageSlotOut(BaseModel):
    """One picture a lesson wants, as the Studio shows it."""

    key: str
    kind: Literal["lesson", "vocab", "grammar", "scene"]
    label: str  # the word, the pattern, the scene's caption
    prompt: str
    meaning: str | None = None  # a word's meaning
    url: str | None = None  # None until the picture is made
    hidden: bool = False
    model: str | None = None
    # when the picture is missing: existing pictures of words that mean the same, best first
    reuse: list[ReuseCandidateOut] = []


class LessonImagesOut(BaseModel):
    lesson_id: int
    title: str
    enabled: bool
    model: str
    total: int
    have: int
    hidden: int
    slots: list[ImageSlotOut]
    active_job_id: uuid.UUID | None = None


class LessonImageSummaryOut(BaseModel):
    lesson_id: int
    slug: str | None = None
    title: str
    total: int
    have: int
    hidden: int
    reusable: int = 0  # missing pictures that an existing one of the same meaning could fill


class ImagesOverviewOut(BaseModel):
    enabled: bool
    model: str
    lessons: list[LessonImageSummaryOut]
    # distinct pictures over all lessons: one shared by two lessons is drawn (and paid for)
    # once, so these are the numbers a "draw everything missing" run is measured in
    total: int = 0
    have: int = 0
    # missing pictures an existing one could fill (distinct), and how many of those are sure
    reusable: int = 0
    reusable_sure: int = 0
    # a drawing run in progress (only one at a time) and the lesson it is for
    active_job_id: uuid.UUID | None = None
    active_lesson_id: int | None = None


class ImageGenerateRequest(BaseModel):
    """POST /lesson-images — draw what is missing. `lesson_id` empty = every lesson;
    `keys` = only these pictures; `force` = draw them again even if they exist."""

    lesson_id: int | None = None
    keys: list[str] | None = Field(default=None, max_length=300)
    force: bool = False


class ImageHideRequest(BaseModel):
    hidden: bool


class ImageReuseRequest(BaseModel):
    """POST /lesson-images/reuse — give the word `to_key` a copy of the picture `from_key`."""

    from_key: str = Field(min_length=1, max_length=48)
    to_key: str = Field(min_length=1, max_length=48)


class ImageReuseSuggestedRequest(BaseModel):
    """POST /lesson-images/reuse-suggested — fill every missing word picture (of one lesson, or
    of all) that has a SURE match among the existing pictures."""

    lesson_id: int | None = None


class ImageReusedOut(BaseModel):
    to_key: str
    from_key: str
    label: str | None = None
    url: str


class ImagesReusedOut(BaseModel):
    reused: int
    items: list[ImageReusedOut]


class ImageHiddenOut(BaseModel):
    key: str
    hidden: bool


class ExerciseAnswerRequest(BaseModel):
    """POST /lessons/{id}/answers — one practice question the learner just answered."""

    exercise_id: str = Field(min_length=1, max_length=32)
    question_id: str = Field(min_length=1, max_length=32)
    correct: bool
    # what was chosen (an option id) or typed — kept short, shown back when reviewing
    answer: str | None = Field(default=None, max_length=500)


class ExerciseResultOut(BaseModel):
    exercise_id: str
    question_id: str
    correct: bool
    attempts: int
    answer: str | None = None


class LessonProgressOut(BaseModel):
    lesson_id: int
    total: int
    answered: int
    correct: int
    results: list[ExerciseResultOut]


class CardStudyOut(BaseModel):
    """What this learner did with one vocabulary word / grammar card of a lesson."""

    item_type: Literal["vocab_item", "grammar_point"]
    item_id: int
    # the last answer: True = "đã hiểu / đã nhớ", False = "chưa chắc / chưa nhớ"
    last_correct: bool
    strength: float


class FeatherOut(BaseModel):
    """One small part of a lesson (about five minutes), earned by marking its words / cards once, or
    answering its questions, or finishing its part (the alphabet lesson)."""

    id: str
    kind: Literal["vocab", "grammar", "practice", "part"]
    label: str
    skill: str | None = None
    part: str | None = None
    item_ids: list[int] = []
    question_ids: list[str] = []
    earned: bool


class LessonStudyOut(BaseModel):
    """Where the learner stands in one lesson: what the lesson screen needs to open on the part that is
    left and to show the cards already marked. Only cards with a record are listed in `cards`."""

    lesson_id: int
    vocab_total: int
    vocab_met: int
    grammar_total: int
    grammar_met: int
    practice_total: int
    practice_answered: int
    # the first part with something left; None when every part is done
    resume_step: Literal["listen", "vocab", "grammar", "practice"] | None = None
    cards: list[CardStudyOut] = []
    # the lesson cut into feathers (app/services/feathers.py), in the order it shows them
    feathers: list[FeatherOut] = []
    chapter: int | None = None  # the chapter of Hành trình Thiên Nga it belongs to; None: support
    support: str | None = None  # a support lesson: its constellation's code


class MistakeLineOut(BaseModel):
    text: str
    vi: str | None = None
    speaker: str | None = None


class MistakeOptionOut(BaseModel):
    id: str
    text: str


class MistakeFocusOut(BaseModel):
    ko: str
    vi: str


class MistakeGrammarOut(BaseModel):
    """A grammar card the question is about, with enough to read it and to open the lesson that teaches it."""

    pattern: str
    meaning_vi: str | None = None
    lesson_id: int | None = None
    lesson_title: str | None = None


class MistakeOut(BaseModel):
    """One practice question whose latest answer is wrong, written out to read again."""

    exercise_id: str
    question_id: str
    type: str
    skill: str
    title: str
    prompt: str | None = None
    context: list[MistakeLineOut] = []
    options: list[MistakeOptionOut] = []
    chosen_id: str | None = None
    correct_id: str | None = None
    chosen: str | None = None
    correct: list[str] = []
    explanation_vi: str | None = None
    notes_vi: list[str] = []
    focus: list[MistakeFocusOut] = []
    translation: list[str] = []
    grammar: list[MistakeGrammarOut] = []
    attempts: int
    updated_at: datetime
    understood: bool = False


class MistakeLessonOut(BaseModel):
    lesson_id: int
    title: str
    sort_order: int
    mistakes: list[MistakeOut]


class MistakeBookOut(BaseModel):
    """Sổ lỗi sai: the mistakes of the lessons that have the study guide, by lesson in curriculum order."""

    lessons: list[MistakeLessonOut]
    open: int  # not yet marked "Đã hiểu"
    understood: int


class MistakeUnderstoodRequest(BaseModel):
    lesson_id: int
    question_id: str = Field(min_length=1, max_length=32)
    understood: bool = True


class CorpusItemOut(BaseModel):
    id: uuid.UUID
    film_id: int
    film_title: str
    text_en: str
    kind: str
    level: int
    register: str
    topics: list[str]
    grammar_patterns: list[str]
    # Vietnamese meaning of the line and how/when to use it; null until the
    # enrichment step has covered the sentence (the app shows the Korean alone).
    meaning_vi: str | None = None
    usage_note_vi: str | None = None

    model_config = {"from_attributes": True}


class CorpusSimilarOut(CorpusItemOut):
    """A sentence close in meaning to another one (pgvector cosine distance on
    the stored embedding; 0 = identical, larger = further apart) — typically
    the same idea in another speech level or with other word forms."""

    distance: float


class CorpusLevelCount(BaseModel):
    level: int
    count: int


class CorpusRegisterCount(BaseModel):
    register: str
    count: int


class CorpusTopicCount(BaseModel):
    id: int
    name: str
    count: int


class CorpusGrammarCount(BaseModel):
    id: int
    pattern: str
    count: int


class CorpusFilmCount(BaseModel):
    id: int
    title: str
    count: int


class CorpusFacetsOut(BaseModel):
    """What the listening picker can filter by, with how many distinct
    sentences each choice holds (repeated sentences counted once)."""

    total: int
    levels: list[CorpusLevelCount]
    registers: list[CorpusRegisterCount]
    topics: list[CorpusTopicCount]
    grammar: list[CorpusGrammarCount]
    films: list[CorpusFilmCount]


class CorpusPageOut(BaseModel):
    """One page of a listening session: `total` is the size of the whole
    filtered set, so the client knows how far it can keep paging."""

    total: int
    offset: int
    items: list[CorpusItemOut]


class CorpusEnrichmentStatusOut(BaseModel):
    """Studio: how far the corpus is from having a Vietnamese meaning, usage
    note and naturalness verdict on every sentence. Counts are stored rows
    (a sentence imported twice counts twice here, once for learners)."""

    version: str
    total: int
    pending: int  # not yet covered by the current enrichment prompt
    enriched: int
    hidden: int  # judged unnatural or awkward: not shown to learners
    awkward: int  # of which judged awkward (stiff translationese)
    active_job_id: uuid.UUID | None = None  # a run in progress, if any


class HiddenCorpusItemOut(BaseModel):
    id: uuid.UUID
    film_title: str
    text_en: str


class ItemStateReviewRequest(BaseModel):
    """Records a learner's quick in-app check on one vocab/grammar item: nudges
    SRS §5 ITEM_STATE's `strength` and moves its review schedule
    (app.services.srs)."""

    item_type: Literal["vocab_item", "grammar_point"]
    item_id: int
    correct: bool
    # How the card was asked and, for a wrong fill-in-the-blank, what was picked.
    # Optional (older clients send neither); they only enrich the error log.
    mode: Literal["recognize", "cloze"] | None = None
    chosen: str | None = Field(default=None, max_length=120)
    # "Chưa chắc": right, but a guess. A right answer slower than srs.SLOW_ANSWER_MS counts the
    # same (app.services.srs.review, `hard`). Both optional: older clients send neither.
    hard: bool = False
    response_ms: int | None = Field(default=None, ge=0, le=3_600_000)


class ItemStateOut(BaseModel):
    item_type: str
    item_id: int
    strength: float
    last_seen: datetime
    # the spaced-review schedule (app.services.srs): when it comes back, how many
    # right answers in a row, how often it was forgotten
    due_at: datetime | None = None
    reps: int = 0
    lapses: int = 0
    interval_days: float = 0.0
    known_at: datetime | None = None  # "Đã biết": out of the review queue until undone

    model_config = {"from_attributes": True}


class ReviewOnlyRequest(BaseModel):
    """"Hôm nay bận — chỉ ôn": on = no new cards today (Vietnam time); off = back to normal."""

    on: bool


class ReviewOnlyOut(BaseModel):
    review_only: bool
    day: date | None = None  # the day it applies to, when on


class ClozeOut(BaseModel):
    """A fill-in-the-blank question. The answer is sent along so the app can mark
    it at once, without a round trip per card."""

    prompt_en: str
    answer: str
    choices: list[str]


class ReviewQueueItem(BaseModel):
    item_type: Literal["vocab_item", "grammar_point"]
    item_id: int
    is_new: bool
    mode: Literal["recognize", "cloze"]
    reps: int
    lapses: int
    leech: bool = False  # forgotten again and again: shown first, flagged "hay sai"
    due_at: datetime | None = None
    lesson_title: str | None = None
    # A word that comes from a news article rather than a lesson.
    article_id: uuid.UUID | None = None
    article_title: str | None = None
    # A word from a deck of the TOPIK word bank the learner added.
    bank_deck: str | None = None
    bank_title: str | None = None
    vocab: VocabItemOut | None = None
    grammar: GrammarPointOut | None = None
    cloze: ClozeOut | None = None


class ReviewQueueOut(BaseModel):
    """Today's sitting: what is due, then what is new."""

    due_total: int  # everything due now, which can be more than the due cards returned
    new_available: int  # new cards today's cap still allows
    new_today: int  # new cards started in the last 24 hours
    items: list[ReviewQueueItem]
    focus: Literal["due", "weak"] = "due"  # "weak": the cards the learner keeps forgetting, due or not
    article_waiting: int = 0  # article words not started yet that fit the learner's level
    article_above_level: int = 0  # article words held back because they are above the goal level
    review_only: bool = False  # "Hôm nay bận — chỉ ôn" is on for today: no new cards


# ------------------------------------------------------- practice: weak spots --
class WeakTypeOut(BaseModel):
    error_type: str
    label: str
    skill: str
    count: int


class WeakItemOut(BaseModel):
    item_type: Literal["vocab_item", "grammar_point"]
    item_id: int
    title: str  # the chunk or the grammar pattern
    meaning_vi: str
    family: str | None = None
    errors: int


class WeakFamilyOut(BaseModel):
    family: str
    errors: int


class ExamAccuracyOut(BaseModel):
    qtype_code: str
    name: str
    attempts: int
    correct: int
    accuracy_pct: int


class WeaknessesOut(BaseModel):
    """Where the learner keeps going wrong in the last `days` days — counts of what
    happened, never a prediction of an exam score."""

    days: int
    total_errors: int
    by_type: list[WeakTypeOut]
    top_items: list[WeakItemOut]  # cards that went wrong more than once
    families: list[WeakFamilyOut]  # sets ("họ từ") the mistakes gather in
    exam: list[ExamAccuracyOut]  # per question type, weakest first
    weak_cards: int  # cards forgotten and not yet back on their feet ("Ôn thẻ hay sai")
    leeches: int  # of those, forgotten twice or more
    exam_ready: int  # confirmed reading questions available for the mini-drill


# ------------------------------------------------------ practice: exam drill --
class ExamDrillQuestion(BaseModel):
    id: uuid.UUID
    number: int
    qtype_code: str
    qtype_name_vi: str
    instruction_en: str | None = None  # the group instruction above the question
    stem_en: str
    options: list[str]
    passage_en: str | None = None
    paper_label: str


class ExamDrillOut(BaseModel):
    items: list[ExamDrillQuestion]
    available: int  # usable questions in the bank, whether or not they are offered now


class ExamAnswerRequest(BaseModel):
    item_id: uuid.UUID
    chosen: int = Field(ge=1, le=5)  # 1-based, like the key


class ExamAnswerOut(BaseModel):
    item_id: uuid.UUID
    chosen: int
    answer: int
    correct: bool


# ---------------------------------------------------- practice: writing drill --
class WritingBlankView(BaseModel):
    label: str
    intent_vi: str
    uses: list[str] = Field(default_factory=list)


class WritingTargetOut(BaseModel):
    item_id: int
    headword: str
    meaning_vi: str


class WritingPromptOut(BaseModel):
    """The exercise as the learner sees it. The model answers are not here — they
    come with the result."""

    text_type: str | None = None
    title_en: str | None = None
    body_en: str
    register: str | None = None
    blanks: list[WritingBlankView]
    targets: list[WritingTargetOut] = Field(default_factory=list)


class WritingFixOut(BaseModel):
    original: str
    corrected: str = ""
    category: str
    reason_vi: str
    source: Literal["ai", "auto"]


class WritingBlankResultOut(BaseModel):
    label: str
    answer: str
    verdict: Literal["good", "minor", "off", "unchecked"]
    comment_vi: str = ""
    fixes: list[WritingFixOut] = Field(default_factory=list)
    model_answer: str
    alt_answers: list[str] = Field(default_factory=list)
    intent_vi: str


class WritingResultOut(BaseModel):
    blanks: list[WritingBlankResultOut]
    ai_checked: bool
    note: str


class WritingDrillOut(BaseModel):
    id: uuid.UUID
    status: Literal["pending", "ready", "failed"]  # the exercise being made
    grade_status: Literal["none", "pending", "ready", "failed"]  # the answers being checked
    job_id: uuid.UUID | None = None
    prompt: WritingPromptOut | None = None
    answers: dict[str, str] | None = None
    result: WritingResultOut | None = None
    created_at: datetime


class WritingDrillStartRequest(BaseModel):
    """`deck_key`: write with the words of this «Kho từ TOPIK» deck the learner has started."""

    deck_key: str | None = Field(default=None, max_length=80)


class WritingDrillStartOut(BaseModel):
    drill_id: uuid.UUID
    status: Literal["pending", "ready", "failed"]
    job_id: uuid.UUID | None = None  # follow it with the jobs API while status is "pending"


class WritingAnswersRequest(BaseModel):
    answers: dict[Literal["㉠", "㉡"], str]  # one sentence per blank; each at most 200 characters


class TodayPlanTask(BaseModel):
    """One real, clickable suggestion for /me/plan — never a fabricated
    stat. `status` is only ever computed from data that actually exists;
    a task whose progress genuinely isn't tracked yet (e.g. listening)
    always reports "todo" rather than faking a checkmark."""

    kind: Literal["review", "vocab_review", "topic_review", "listening", "reading", "placement", "daily_reading"]
    title: str
    subtitle: str
    status: Literal["todo", "in_progress", "done"]
    lesson_id: int | None = None
    article_id: uuid.UUID | None = None
    # vocab_review only: the part of the lesson to open first (what is left to do)
    step: Literal["listen", "vocab", "grammar", "practice"] | None = None


# ------------------------------------------------------- daily reading / dialogue --
class DailyLineOut(BaseModel):
    who: Literal["F", "M", "N"]  # F = the woman, M = the man, N = the narrator of a reading
    speaker: str | None = None  # the name shown for a dialogue line
    ko: str
    vi: str
    voice: str  # the Chirp voice of the line (ko-female-1 | ko-male-1) — pass it to POST /audio/text


class DailyGlossOut(BaseModel):
    ko: str
    vi: str


class DailyQuestionOut(BaseModel):
    q_vi: str
    options: list[str]  # the right answer is NOT sent: POST .../finish grades and explains


class DailyGrammarOut(BaseModel):
    grammar_id: int | None = None
    lesson_id: int | None = None
    pattern: str
    meaning_vi: str | None = None


class DailyWordOut(BaseModel):
    vocab_item_id: int | None = None
    lesson_id: int | None = None
    headword: str
    meaning_vi: str | None = None
    known: bool  # the learner has met this word (it has a study record)


class DailyPassageOut(BaseModel):
    id: str
    kind: Literal["dialogue", "reading"]
    title_en: str
    title_vi: str
    scene_vi: str | None = None
    speakers: dict[str, str] = {}
    lines: list[DailyLineOut]
    text_en: str  # the whole text, to be voiced as ONE clip (a reading)
    voice: str  # the voice of the whole text
    glossary: list[DailyGlossOut]
    questions: list[DailyQuestionOut]
    grammar: list[DailyGrammarOut]
    words: list[DailyWordOut]
    why_vi: str
    status: Literal["todo", "done"]
    correct: int | None = None
    total: int | None = None


class DailyReadingOut(BaseModel):
    day: date
    items: list[DailyPassageOut]
    done: int
    total: int
    note_vi: str | None = None  # why there is nothing to read yet


class DailyFinishIn(BaseModel):
    answers: list[int | None] = Field(max_length=6)  # one per question, null = left blank


class DailyAnswerOut(BaseModel):
    answer: int | None = None
    correct: int
    is_right: bool
    explain_vi: str


class DailyFinishOut(BaseModel):
    passage_id: str
    correct: int
    total: int
    answers: list[DailyAnswerOut]
    done: int
    day_total: int


class JourneyChapterOut(BaseModel):
    n: int
    name: str
    level: str
    becomes: str  # what the swan does when the chapter is finished
    earned: int
    credited: int  # feathers of lessons the entry check let the learner skip
    total: int
    lessons: int
    lessons_done: int
    done: bool


class StarOut(BaseModel):
    lesson_id: int
    title: str
    earned: int
    total: int
    lit: bool


class ConstellationOut(BaseModel):
    code: str
    name: str
    topic: str
    relic: str | None = None  # the relic's name; None while it has no picture
    relic_earned: bool = False
    stars: list[StarOut] = []


class JourneyOut(BaseModel):
    """Hành trình Thiên Nga (app/services/journey.py)."""

    stage: int  # 1-5 reached, only goes up
    shown_stage: int  # what the swan wears now (one back while cursed)
    missed_days: int  # full days away before today
    cursed: bool
    studied_today: bool
    items: int  # words and cards studied
    next_readiness: int | None = None  # no longer used (stages come from chapters): always None
    next_items: int | None = None
    name: str
    card: str
    shield_ready: bool = True  # the weekly streak shield is unused this week
    shield_day: date | None = None  # the last day the shield covered (within the past week)
    # feathers (app/services/feathers.py)
    chapters: list[JourneyChapterOut] = []
    station: bool = False  # chapter III's station (the far shore in sight) is reached
    starlight: int = 0  # feathers of the support lessons
    starlight_total: int = 0
    sparkle: int = 0  # 0..3, never lowered
    next_sparkle_at: int | None = None  # starlight feathers for the next sparkle; None at 3
    relics: list[str] = []  # codes of the relics earned, kept for good
    constellations: list[ConstellationOut] = []


class TodayPlanOut(BaseModel):
    streak_days: int
    readiness_pct: float | None
    goal: str | None
    exam_date: datetime | None
    tasks: list[TodayPlanTask]
    journey: JourneyOut | None = None


# ------------------------------------------------------------------- ingest --
class ImportBatchOut(BaseModel):
    id: uuid.UUID
    kind: str
    status: str
    flagged_count: int
    source_file: str | None
    film_id: int | None
    exam_paper_id: uuid.UUID | None
    editorial_article_id: uuid.UUID | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ImportBatchAccepted(BaseModel):
    """POST /imports's 202 envelope: same job_id/poll_url/events_url shape
    as JobAccepted, plus the batch id — the caller needs it immediately
    (to list/patch/confirm items) and can't wait for the job to finish."""

    import_batch_id: uuid.UUID
    job_id: uuid.UUID
    status: JobStatus = "queued"
    poll_url: str
    events_url: str


class ImportItemOut(BaseModel):
    id: uuid.UUID
    import_batch_id: uuid.UUID
    kind: str
    status: str
    payload: dict[str, Any]
    confidence: float

    model_config = {"from_attributes": True}


class ExamAnswerTextRequest(BaseModel):
    """Answers an editor typed or pasted for an exam batch: "1-2, 2-1, …" pairs, or an
    unbroken run of digits taken as the answers from question `start`."""

    text: str = Field(min_length=1, max_length=4000)
    start: int = Field(default=1, ge=1, le=200)
    dry_run: bool = False  # only report what would change


class ExamAnswerReportOut(BaseModel):
    dry_run: bool
    skill: str | None = None
    answers: dict[int, int]  # what was read from the text / key
    applied: list[int]  # question numbers that got an answer
    changed: list[int]  # ...of which replaced a different answer
    unmatched: list[int]  # given, but no such question in the paper
    missing: list[int]  # questions of the paper with no answer given
    conflicts: list[int] = []  # numbers a key could not be read reliably for


class ImportItemPatch(BaseModel):
    payload: dict[str, Any] | None = None
    status: Literal["confirmed", "rejected"] | None = None


# ---------------------------------------------------------------- editorial --
class EditorialSourceCreate(BaseModel):
    name: str
    base_url: str
    rss_url: str | None = None
    license_note: str | None = None
    active: bool = True


class EditorialSourceUpdate(BaseModel):
    base_url: str | None = None
    rss_url: str | None = None
    license_note: str | None = None
    active: bool | None = None


class EditorialSourceOut(BaseModel):
    id: int
    name: str
    base_url: str
    rss_url: str | None
    license_note: str | None
    active: bool

    model_config = {"from_attributes": True}


class EditorialArticleSummaryOut(BaseModel):
    """GET /editorials list card — no body_en (too big for a list) and no
    model_outline (that's revealed only after the learner submits their
    own outline attempt — see EditorialOutlineOut). `cover_image_url` is the
    article's first scraped photo, for the card thumbnail."""

    id: uuid.UUID
    source_name: str
    title_en: str | None
    level_estimate: int | None
    topic_tags: list[str]
    created_at: datetime
    cover_image_url: str | None = None
    related_lesson_ids: list[int] = []
    unlock_hint: str | None = None

    model_config = {"from_attributes": True}


class ArticleImageOut(BaseModel):
    """One photo from the source article. `after_paragraph` = how many body
    paragraphs precede it (0 = above the first paragraph), so the reader
    can put it back where it sat in the original."""

    url: str
    caption: str | None = None
    after_paragraph: int = 0


class StudyWordOut(BaseModel):
    surface: str
    base: str | None = None
    pos: str | None = None
    meaning_vi: str


class StudySentenceOut(BaseModel):
    ko: str
    vi: str | None = None
    words: list[StudyWordOut] = []
    grammar_notes_vi: list[str] = []


class StudyParagraphOut(BaseModel):
    """One body paragraph, aligned by index with the paragraphs of `body_en`
    (split on newlines): its sentences with translations + word breakdowns,
    and the paragraph rewritten in simple Korean."""

    easy_en: str | None = None
    sentences: list[StudySentenceOut] = []


class StudyKeyTermOut(BaseModel):
    ko: str
    vi: str


class StudyPackOut(BaseModel):
    """Beginner "reading ladder" — see app.services.study_pack."""

    summary_vi: str = ""
    key_points_vi: list[str] = []
    key_terms: list[StudyKeyTermOut] = []
    paragraphs: list[StudyParagraphOut] = []


class EditorialArticleOut(BaseModel):
    id: uuid.UUID
    source_name: str
    source_url: str
    title_en: str | None
    level_estimate: int | None
    topic_tags: list[str]
    body_en: str
    vocab: list[VocabItemOut]
    grammar: list[GrammarPointOut]
    thinking_guide_text: str | None
    created_at: datetime
    images: list[ArticleImageOut] = []
    # True when this article's photos have never been fetched (imported
    # before photos existed) and a background fetch was just queued — the
    # client refetches once after a few seconds instead of showing none.
    images_pending: bool = False
    # none = not requested yet, pending = being generated (client polls),
    # ready = `study` is present, failed = generation failed (retried later).
    study_status: Literal["none", "pending", "ready", "failed"] = "none"
    study: StudyPackOut | None = None
    # the course lessons this article follows, a one-line "when to read it", and the practice asked after reading
    related_lesson_ids: list[int] = []
    unlock_hint: str | None = None
    practice: list[dict] = []


class EditorialOutlineSubmitRequest(BaseModel):
    phenomenon_text: str | None = None
    cause_text: str | None = None
    consequence_text: str | None = None
    solution_text: str | None = None


class EditorialOutlineOut(BaseModel):
    """The learner's own outline attempt. `model_outline` is included only
    once revision_count > 0 — the point of "luyện dàn ý" is thinking it
    through first, so the reference answer stays hidden until the learner
    has actually written and saved their own attempt at least once."""

    editorial_article_id: uuid.UUID
    phenomenon_text: str | None
    cause_text: str | None
    consequence_text: str | None
    solution_text: str | None
    revision_count: int
    updated_at: datetime
    model_outline: dict[str, Any] | None = None
    # Real Gemini analysis of the learner's OWN outline (not the static
    # model_outline reference) — "none" until the first save triggers
    # grade_editorial_outline, "pending" while it runs, then "ready"/"failed".
    feedback_status: str = "none"
    feedback_text: str | None = None

    model_config = {"protected_namespaces": ()}


class EditorialCandidateOut(BaseModel):
    id: uuid.UUID
    source_name: str
    source_url: str
    title_en: str
    snippet_en: str | None
    topic_tags: list[str]
    published_date: datetime | None
    status: str
    discovered_at: datetime

    model_config = {"from_attributes": True}


# ------------------------------------------------- competency, mixed review, placement --
class MixItemOut(BaseModel):
    """One exercise of the mixed review. It is graded in the browser like any practice exercise and
    its answers are filed under `lesson_id` (POST /lessons/{lesson_id}/answers)."""

    lesson_id: int
    lesson_title: str
    reason: Literal["due", "wrong", "new"]  # a card due for review / answered wrong before / not done yet
    rung: int  # 0 nhận ra · 1 xếp câu · 2 điền / nối câu
    exercise: dict[str, Any]
    grammar: dict[str, dict[str, Any]] = {}  # pattern -> card info (with `lesson_id`), for the box under each answer


class MixOut(BaseModel):
    lesson_id: int
    items: list[MixItemOut]
    by_reason: dict[str, int] = {}
    pool: int = 0  # how many exercises could have been offered


class CompetencyWeakOut(BaseModel):
    grammar_id: int
    pattern: str
    lesson_id: int
    why: str
    level: int


class CompetencyNextOut(BaseModel):
    kind: Literal["review", "weak", "practice", "learn", "mix", "placement"]
    title: str
    subtitle: str
    path: str | None = None  # a route of the app
    lesson_id: int | None = None
    skill: str | None = None  # the practice tab to open


class CompetencySummaryOut(BaseModel):
    cards: int = 0
    unseen: int = 0
    studying: int = 0
    by_level: dict[str, int] = {}  # highest rung reached -> number of cards
    goal_reached: int = 0
    remembered: int = 0
    due: int = 0
    leeches: int = 0


class CompetencyLessonOut(BaseModel):
    lesson_id: int
    title: str
    summary: CompetencySummaryOut


class CompetencyTopicOut(BaseModel):
    topic: str
    summary: CompetencySummaryOut
    lessons: list[CompetencyLessonOut]
    weakest: list[CompetencyWeakOut] = []
    next: list[CompetencyNextOut] = []


class PlacementSummaryOut(BaseModel):
    taken_at: datetime
    score: int
    total: int
    known: list[str]  # patterns answered right
    unknown: list[str]
    known_ids: list[int] = []  # the cards behind `known` (grammar point ids)
    solid_ids: list[int] = []  # ...of which right on a sentence to build or a blank to fill (not a lucky guess)
    start_rung: int  # the highest rung reached in the diagnostic, -1 when none
    start_label: str
    start_lesson_id: int | None = None
    by_rung: dict[str, dict[str, int]] = {}  # rung -> {"right": n, "total": n}


class CompetencyOut(BaseModel):
    rungs: dict[str, str]
    topics: list[CompetencyTopicOut]
    placement: PlacementSummaryOut | None = None


class PlacementItemOut(BaseModel):
    """One question of the entry diagnostic: an exercise of the lesson shapes, graded in the browser."""

    id: str
    rung: int  # 0 nhận ra · 1 xếp câu · 2 điền câu
    exercise: dict[str, Any]


class PlacementOut(BaseModel):
    title_vi: str
    intro_vi: str
    minutes: int
    items: list[PlacementItemOut]
    last: PlacementSummaryOut | None = None  # the learner's latest attempt, when there is one


class PlacementAnswerIn(BaseModel):
    exercise_id: str = Field(max_length=40)
    question_id: str = Field(max_length=60)
    correct: bool
    answer: str = Field(default="", max_length=300)


class PlacementSubmit(BaseModel):
    answers: list[PlacementAnswerIn] = Field(max_length=60)


# ----------------------------------------------------------- adaptive entry check --
# "Kiểm tra đầu vào" (app.services.placement_cat): a short survey, then one question at a time
# where the learner's level is most in doubt; nothing sent here carries an answer.
SelfLevel = Literal["new", "basic", "elementary", "intermediate", "advanced"]
Purpose = Literal["talk", "work", "topik1", "topik4", "topik5"]


class SurveyIn(BaseModel):
    purpose: Purpose
    self_level: SelfLevel
    daily_minutes: int = Field(ge=5, le=120)


class AdaptiveAnswerIn(BaseModel):
    ref: str = Field(max_length=120)
    choice: str = Field(default="", max_length=8)  # an option id; "" = "Chưa học mẫu này"


class AdaptiveStepIn(BaseModel):
    self_level: SelfLevel
    answers: list[AdaptiveAnswerIn] = Field(default=[], max_length=20)


class AdaptiveItemOut(BaseModel):
    ref: str
    exercise: dict[str, Any]  # one question, its answer taken out


class AdaptiveStepOut(BaseModel):
    done: bool
    item: AdaptiveItemOut | None = None
    asked: int
    progress: float  # 0..1, how settled the estimate is (for the light bar, not a count)
    last_right: bool | None = None  # the answer just given, for Haru's one-word reaction


class AdaptiveFinishIn(BaseModel):
    survey: SurveyIn
    answers: list[AdaptiveAnswerIn] = Field(default=[], max_length=20)


class RoadLessonOut(BaseModel):
    id: int
    title: str
    minutes: int
    free: bool


class GapOut(BaseModel):
    lesson_id: int | None = None
    title: str
    patterns: list[str] = []


class AdaptiveResultOut(BaseModel):
    taken_at: datetime
    tested: bool  # false: the learner said they are new and went straight to the first lesson
    level_label: str
    asked: int
    right: int
    start_lesson_id: int | None = None
    start_title: str | None = None
    advice: Literal["start_here", "fill_gaps", "restart_from"]
    gaps: list[GapOut] = []
    purpose: Purpose
    goal_label: str
    lessons_to_goal: int
    minutes_to_goal: int
    weeks: int
    daily_minutes: int
    exam_weeks: int | None = None
    need_daily: int | None = None
    next_lessons: list[RoadLessonOut] = []
    headline: str
    tips: list[str] = []
    words_by: Literal["gemini", "rules"] = "rules"


# ----------------------------------------------------------- real exam practice --
# "Luyện đề thi thật": questions of past TOPIK II papers, practised by type and cluster
# (app.services.real_exam). Nothing here carries the answer before the learner has answered.
RxResult = Literal["solid", "aided", "wrong", "pending"]
RxSec = Literal["L", "R", "W"]


class RxGuideOut(BaseModel):
    code: str
    sec: RxSec
    name_vi: str
    asks_vi: str
    steps: list[str]
    traps: list[str]
    tips: list[str]
    gain_vi: str
    family: str
    family_name_vi: str


class RxCardOut(BaseModel):
    """A card of the lessons a question rests on."""

    kind: Literal["grammar_point", "vocab_item"]
    id: int
    lesson_id: int
    lesson_title: str | None = None
    label: str
    meaning_vi: str
    known: bool  # the learner has met it
    exact: bool  # the same pattern (False: a close relative)


class RxPointOut(BaseModel):
    """One piece of knowledge a question teaches: a pattern (V/A + form) or a word."""

    kind: Literal["grammar", "word"]
    ko: str
    vi: str
    status: Literal["known", "upcoming", "new"]  # in the lessons and met / in a lesson not yet reached / in no lesson
    cards: list[RxCardOut]


class RxClipOut(BaseModel):
    who: Literal["F", "M", "N"]
    voice: str
    ko: str


class RxFitOut(BaseModel):
    known: int
    upcoming: int
    new: int
    status: Literal["ready", "stretch", "later"]


class RxBlankIn(BaseModel):
    id: str


class RxQuestionOut(BaseModel):
    qid: str
    exam: str
    exam_short: str
    sec: RxSec
    n: int
    type: str
    type_name: str
    tier: int
    stem: str | None
    passage: str | None
    given: str | None
    image_url: str | None  # behind login: fetch with the token
    pic: bool  # the options are the pictures / charts of the image
    opts: list[str]
    clips: list[RxClipOut]
    bundle_index: int  # position among the questions sharing one passage / recording (0-based)
    bundle_size: int
    blanks: list[str]  # ids of the blanks of a write-in question (㉠, ㉡)
    limit: tuple[int, int] | None
    prompt: str | None
    questions: list[str]
    fit: RxFitOut
    hint_level: int  # the highest hint already opened for this question in this sitting
    answered: bool


class RxSetOut(BaseModel):
    id: uuid.UUID
    title_vi: str
    why_vi: str
    created_at: datetime
    finished: bool
    done: int
    total: int
    guides: list[RxGuideOut]
    questions: list[RxQuestionOut]


class RxScopeIn(BaseModel):
    type: str | None = None
    family: str | None = None
    sec: RxSec | None = None
    exam: str | None = None
    qids: list[str] = Field(default_factory=list, max_length=12)
    size: int | None = Field(default=None, ge=1, le=12)
    redo_wrong: bool = False  # only questions to try again


class RxHintIn(BaseModel):
    qid: str
    level: int = Field(ge=1, le=3)


class RxHintOut(BaseModel):
    level: int
    kind: Literal["focus", "translate", "eliminate", "patterns", "start", "outline"]
    text: str | None = None
    options_vi: list[str] | None = None
    gloss: list[list[str]] | None = None
    option: int | None = None
    items: list[dict[str, Any]] | None = None
    rubric: list[dict[str, str]] | None = None


class RxAnswerIn(BaseModel):
    qid: str
    choice: int | None = Field(default=None, ge=1, le=4)  # None = "chưa biết, cho tôi xem"
    answers: dict[str, str] = Field(default_factory=dict, max_length=4)  # write-in blanks
    text: str | None = Field(default=None, max_length=4000)  # a written passage


class RxTurnOut(BaseModel):
    who: str
    ko: str
    vi: str | None
    voice: str | None  # None: not voiced (the unspoken last turn)


class RxBlankResultOut(BaseModel):
    id: str
    text: str
    matched: bool
    sample: str
    accepted: list[str]
    why: str
    gram: list[dict[str, str]]
    traps: list[str]


class RxCheckOut(BaseModel):
    label: str
    ok: bool
    note: str


class RxRubricOut(BaseModel):
    k: str
    w: str


class RxAnswerOut(BaseModel):
    attempt_id: uuid.UUID
    qid: str
    result: RxResult
    hints: int
    chosen: int | None
    ans: int | None
    why: str | None
    option_notes: dict[str, str]  # option number -> why it is wrong ("" for the right one)
    options_vi: list[str]
    passage_lines: list[tuple[str, str]]  # (Korean, Vietnamese) per line
    turns: list[RxTurnOut]
    given_vi: str | None
    points: list[RxPointOut]
    take: str
    guide_tip: str | None
    # write-in questions
    blanks: list[RxBlankResultOut]
    checks: list[RxCheckOut]
    sample: str | None
    sample_vi: str | None
    data: list[tuple[str, str]]
    phrases: list[dict[str, str]]
    rubric: list[RxRubricOut]
    tips: str | None
    needs_self_check: bool
    done: int
    total: int


class RxSelfCheckIn(BaseModel):
    ok: bool | None = None  # a blank answer judged by the learner
    rubric_ok: list[bool] | None = Field(default=None, max_length=12)  # the rubric rows ticked


class RxSelfCheckOut(BaseModel):
    attempt_id: uuid.UUID
    result: RxResult
    right: int
    total: int


class RxTierOut(BaseModel):
    tier: int
    solid: int
    total: int
    is_solid: bool


class RxTypeStatOut(BaseModel):
    code: str
    name_vi: str
    sec: RxSec
    total: int
    tried: int
    solid: int
    to_redo: int  # tried, last answer wrong or needed a hint
    open: int  # offered right now
    ready_open: int
    attempts: int
    right: int
    cur_tier: int | None
    tiers: list[RxTierOut]
    next_vi: str


class RxFamilyOut(BaseModel):
    code: str
    sec: RxSec
    order: int
    name_vi: str
    blurb_vi: str
    gain_vi: str
    total: int
    tried: int
    solid: int
    types: list[RxTypeStatOut]


class RxStageOut(BaseModel):
    key: Literal["starter", "building", "solid"]
    label_vi: str
    known_grammar: int
    total_grammar: int
    tier_cap: int
    goal: str | None


class RxPlanOut(BaseModel):
    scope: RxScopeIn
    title_vi: str
    why_vi: str
    size: int


class RxResumeOut(BaseModel):
    set_id: uuid.UUID
    title_vi: str
    done: int
    total: int


class RxSectionOut(BaseModel):
    sec: RxSec
    name_vi: str
    total: int
    tried: int
    solid: int


class RxExamOut(BaseModel):
    id: str
    title: str
    short: str
    note_vi: str | None
    sections: list[RxSectionOut]


class RxRecentOut(BaseModel):
    set_id: uuid.UUID
    title_vi: str
    finished_at: datetime | None
    solid: int
    aided: int
    wrong: int
    total: int


class RxPrimerWordOut(BaseModel):
    ko: str
    vi: str


class RxPrimerFormOut(BaseModel):
    k: str  # a form or pattern, "V-(으)ㄹ 테니까"
    vi: str  # what it means, with the example the paper uses


class RxLessonPickOut(BaseModel):
    """A real exam question that suits a lesson, with a short primer of what is new in it. Never the
    question itself, nor its answer: the learner opens it as a one-question sitting."""

    qid: str
    exam: str
    exam_title: str
    sec: Literal["L", "R"]
    n: int
    type: str
    type_name_vi: str
    tier: int
    why_vi: str
    words: list[RxPrimerWordOut]
    forms: list[RxPrimerFormOut]
    status: Literal["new", "solid", "aided", "wrong"]  # how the learner stands on it
    resting: bool  # answered recently: a sitting for it would be refused for now


class RxLessonOut(BaseModel):
    lesson_id: int
    picks: list[RxLessonPickOut]


class RxOverviewOut(BaseModel):
    stage: RxStageOut
    today: RxPlanOut | None
    resume: RxResumeOut | None
    exams: list[RxExamOut]
    families: list[RxFamilyOut]
    recent: list[RxRecentOut]


class RxItemStatusOut(BaseModel):
    qid: str
    exam: str
    exam_short: str
    sec: RxSec
    n: int
    type: str
    type_name: str
    tier: int
    status: Literal["new", "solid", "aided", "wrong"]
    fit: Literal["ready", "stretch", "later"]
    open: bool


class RxTypeDetailOut(BaseModel):
    guide: RxGuideOut
    stat: RxTypeStatOut
    items: list[RxItemStatusOut]
    points: list[RxPointOut]  # what this type keeps asking, found in the lessons


class RxExamDetailOut(BaseModel):
    id: str
    title: str
    note_vi: str | None
    items: list[RxItemStatusOut]


class RxSummaryItemOut(BaseModel):
    qid: str
    n: int
    exam_short: str
    sec: RxSec
    type: str
    type_name: str
    tier: int
    result: RxResult
    hints: int
    take: str


class RxSummaryOut(BaseModel):
    set_id: uuid.UUID
    title_vi: str
    finished: bool
    total: int
    answered: int
    solid: int
    aided: int
    wrong: int
    pending: int
    headline_vi: str
    value_vi: str
    items: list[RxSummaryItemOut]
    new_points: list[RxPointOut]  # met for the first time in this sitting
    to_review: list[RxCardOut]  # lesson cards behind the questions that went wrong or needed a hint
    types: list[RxTypeStatOut]
    next_vi: str


# ------------------------------------------------------- conversation (Trò chuyện) --
class ConversationStartRequest(BaseModel):
    # the learner lets Haru keep what they tell about themselves, for the next sessions
    remember: bool = False
    # talk about this lesson (from the lesson screen); None: the lesson studied last
    lesson_id: int | None = None
    # typing instead of speaking: no Gemini Live token is minted; Haru answers in text
    # (POST /{session_id}/reply), so a Live outage does not stop a learner who has no microphone
    typing: bool = False


class ConversationWordOut(BaseModel):
    ko: str
    vi: str


class ConversationFrameOut(BaseModel):
    ko: str
    vi: str
    pattern: str


class ConversationHintsOut(BaseModel):
    words: list[ConversationWordOut]
    frames: list[ConversationFrameOut]


class ConversationLessonOut(BaseModel):
    id: int
    title: str


class ConversationStartOut(BaseModel):
    session_id: uuid.UUID
    # single-use Gemini Live token (auth_tokens/...), opened within a minute; the setup it is
    # locked to is sent back so the browser's first WebSocket message matches it
    token: str = ""
    ws_url: str = ""
    setup: dict
    nudges: dict[str, str]
    max_seconds: int
    seconds_left_today: int
    lesson: ConversationLessonOut | None
    topic: str | None
    earlier_lessons: list[str]
    hints: ConversationHintsOut
    # phase 3: the band Haru talks at this time (1-5) and what that means
    band: int
    band_label_vi: str
    band_note_vi: str
    # the step of a full answer Haru trains this time (app.services.talk_profile.ANSWER_STEPS)
    answer_goal_vi: str = ""


class ConversationTurnIn(BaseModel):
    role: Literal["learner", "haru"]
    text: str = Field(max_length=4000)


class ConversationReplyRequest(BaseModel):
    # the talk so far (the learner's last line is the one to answer); empty: Haru opens
    turns: list[ConversationTurnIn] = Field(default_factory=list, max_length=120)


class ConversationReplyOut(BaseModel):
    text: str


class ConversationFinishRequest(BaseModel):
    seconds: int = Field(ge=0, le=7200)
    nudges: int = Field(default=0, ge=0, le=1000)
    turns: list[ConversationTurnIn] = Field(default_factory=list, max_length=400)


class ConversationFixOut(BaseModel):
    said: str
    better: str
    why_vi: str


class ConversationReportOut(BaseModel):
    summary_vi: str
    praise_vi: str
    fixes: list[ConversationFixOut]
    words: list[ConversationWordOut]
    next_time_vi: str
    learner_facts: list[str]
    topics_vi: list[str] = []


class ConversationFinishOut(BaseModel):
    session_id: uuid.UUID
    seconds: int
    learner_turns: int
    # null when the session was too short to report on, or the report could not be made
    report: ConversationReportOut | None
    report_error_vi: str | None = None
    band_before: int | None = None
    band_after: int | None = None
    band_note_vi: str | None = None


class ConversationFactOut(BaseModel):
    text: str
    at: str


class ConversationProfileOut(BaseModel):
    band: int
    band_label_vi: str
    band_note_vi: str
    facts: list[ConversationFactOut]
    sessions: int
    seconds_left_today: int
    daily_minutes: int


class PronunciationClipIn(BaseModel):
    index: int = Field(ge=0, le=1000)  # the learner turn the sentence belongs to
    heard: str = Field(default="", max_length=600)  # what the live transcription wrote
    wav_b64: str = Field(max_length=700_000)  # 16 kHz 16-bit mono WAV, <= 15 s


class PronunciationRequest(BaseModel):
    clips: list[PronunciationClipIn] = Field(min_length=1, max_length=5)


class PronunciationIssueOut(BaseModel):
    word: str
    heard_as: str
    kind: str = "other"  # app.services.pronunciation.ISSUE_KINDS
    problem_vi: str
    tip_vi: str


class PronunciationItemOut(BaseModel):
    index: int
    heard_en: str
    target_en: str
    score: int
    issues: list[PronunciationIssueOut]
    good_vi: str


class PronunciationOut(BaseModel):
    items: list[PronunciationItemOut]
    overall_vi: str
    average: float | None


# ------------------------------------------------------------ talk history --
class TalkSessionRowOut(BaseModel):
    id: uuid.UUID
    started_at: datetime
    seconds: int
    lesson_title: str | None
    band: int | None
    band_after: int | None
    learner_turns: int
    pron_avg: float | None
    headline_vi: str | None
    topics_vi: list[str]
    has_report: bool
    saved: bool


class TalkSessionDetailOut(TalkSessionRowOut):
    report: ConversationReportOut | None
    pronunciation: PronunciationOut | None
    turns: list[ConversationTurnIn]
    band_note_vi: str | None


class TalkTrendPointOut(BaseModel):
    at: datetime
    pron_avg: float | None
    band: int | None
    ko_words_per_turn: float | None


class TalkIssueKindOut(BaseModel):
    kind: str
    label_vi: str
    sessions: int
    words: list[str]


class TalkRepeatWordOut(BaseModel):
    ko: str
    vi: str
    times: int


class TalkInsightsOut(BaseModel):
    sessions: int
    minutes: int
    points: list[TalkTrendPointOut]
    pron_first: float | None
    pron_last: float | None
    checked_sessions: int
    issue_kinds: list[TalkIssueKindOut]
    repeat_words: list[TalkRepeatWordOut]


class TalkNoteOut(BaseModel):
    id: uuid.UUID
    kind: Literal["word", "sentence"]
    ko: str
    vi: str
    in_review: bool  # the word is a lesson card, now in the review queue
    done: bool
    created_at: datetime


class TalkNoteUpdate(BaseModel):
    done: bool


class TalkSaveOut(BaseModel):
    notes_added: int
    added_to_review: list[str]  # words that are vocabulary cards (a lesson card first), now due in the review queue
    notes: list[TalkNoteOut]


# ---------------------------------------------------------------- Trình bày với Haru


class PresentFramePartOut(BaseModel):
    key: str
    label_vi: str
    hint_vi: str
    starters: list[str]


class PresentFrameOut(BaseModel):
    band: int
    mode: str = "topic"
    target_seconds: list[int]
    max_seconds: int
    parts: list[PresentFramePartOut]


class PresentWordOut(BaseModel):
    ko: str
    vi: str = ""


class PresentTopicOut(BaseModel):
    question_en: str
    question_vi: str = ""
    angle_vi: str = ""
    words: list[PresentWordOut] = []
    source: str = "model"


class PresentOutlinePartOut(BaseModel):
    part: str
    label_vi: str
    idea_vi: str = ""
    keywords_en: list[str] = []
    starter_en: str = ""
    suggested: bool = False
    targets: list[dict[str, str]] = []  # [{"key", "ko"}]: studied items that fit this part


class PresentPartOut(BaseModel):
    part: str
    label_vi: str
    present: bool
    said_en: str = ""
    note_vi: str = ""


class PresentUpgradedOut(BaseModel):
    part: str
    label_vi: str
    ko: str
    vi: str = ""


class PresentPronIssueOut(BaseModel):
    word: str
    heard_as: str = ""
    kind: str = "other"
    tip_vi: str = ""


class PresentTargetUseOut(BaseModel):
    key: str
    kind: str
    ko: str
    vi: str = ""
    used: bool
    correct: bool
    said_en: str = ""
    note_vi: str = ""


class PresentStretchOut(BaseModel):
    ko: str
    vi: str = ""
    why_vi: str = ""


class PresentFollowUpOut(BaseModel):
    q_en: str
    q_vi: str = ""
    kind: str = "why"


class PresentAnswerOut(BaseModel):
    transcript_en: str
    scores: dict[str, int]
    overall: float
    note_vi: str = ""
    better_en: str = ""
    better_vi: str = ""
    seconds: float = 0
    pauses: int = 0
    fillers: int = 0
    tries: int = 1


class PresentEvalOut(BaseModel):
    transcript_en: str
    off_topic: bool = False
    parts: list[PresentPartOut]
    scores: dict[str, int]
    score_notes_vi: dict[str, str] = {}
    overall: float
    connectives_used: list[str] = []
    strength_vi: str = ""
    tips_vi: list[str] = []
    upgraded: list[PresentUpgradedOut] = []
    pron_issues: list[PresentPronIssueOut] = []
    compare_vi: str = ""
    targets_used: list[PresentTargetUseOut] = []
    stretch: list[PresentStretchOut] = []
    follow_ups: list[PresentFollowUpOut] = []


class PresentMetricsOut(BaseModel):
    seconds: float
    speaking_seconds: float
    voiced_seconds: float
    pauses: int
    long_pauses: int
    longest_pause: float
    fillers: int
    syllables: int
    syllables_per_sec: float | None = None
    in_target: bool = False
    fluency_measured: int | None = None


class PresentAttemptOut(BaseModel):
    index: int
    at: datetime
    metrics: PresentMetricsOut
    eval: PresentEvalOut
    answers: dict[str, PresentAnswerOut] = {}


class PresentTargetOut(BaseModel):
    key: str
    kind: str
    ko: str
    vi: str = ""
    example_en: str = ""
    why_vi: str = ""


class PresentSessionOut(BaseModel):
    id: uuid.UUID
    mode: str = "topic"
    title: str = ""
    material: str = ""
    band: int
    band_label_vi: str
    base_band: int | None = None  # the learner's presentation band; band = base_band + shift
    shift: int = 0
    focus: str | None = None
    focus_label_vi: str | None = None
    targets: list[PresentTargetOut] = []
    answer_criteria: dict[str, str] = {}
    frame: PresentFrameOut
    topic: PresentTopicOut
    lesson: dict[str, Any] | None = None
    outline: list[PresentOutlinePartOut] | None = None
    notes_vi: str = ""
    attempts: list[PresentAttemptOut] = []
    attempts_left: int  # in this round
    attempts_left_today: int | None = None  # None = no daily cap
    criteria: dict[str, str]


class PresentStartRequest(BaseModel):
    mode: Literal["topic", "defense"] = "topic"
    band_shift: int = Field(default=0, ge=-1, le=1)  # "Dễ hơn" / "Khó hơn" for this round only
    title: str = Field(default="", max_length=200)
    material: str = Field(default="", max_length=6000)
    lesson_id: int | None = None  # "topic": a question from this lesson; None: the lesson studied last


class EditorialPresentRequest(BaseModel):
    """At the end of an editorial article: "Trình bày 2 phút" (present) or "Phản biện" (debate) —
    a "defense" round built from the article (app.services.presentation.editorial_handoff)."""

    kind: Literal["present", "debate"] = "present"
    band_shift: int = Field(default=0, ge=-1, le=1)


class PresentIdeaOut(BaseModel):
    tool_vi: str = ""
    stance_vi: str
    reason_vi: str = ""
    example_vi: str = ""
    hook_en: str = ""
    hook_vi: str = ""


class PresentRowOut(BaseModel):
    id: uuid.UUID
    created_at: datetime
    mode: str
    title_en: str
    band: int
    tries: int
    first_overall: float | None = None
    best_overall: float | None = None
    answers: int = 0


class PresentInsightsOut(BaseModel):
    rounds: int
    present_band: int
    band_label_vi: str
    band_rubric_vi: dict[str, str]
    focus: str | None = None
    focus_label_vi: str | None = None
    points: list[dict[str, Any]]  # first tries, oldest first: {"at", "overall", "scores", "band"}
    best_overall: float | None = None
    mastered: list[dict[str, Any]]
    practicing: list[dict[str, Any]]
    answer_avg: float | None = None


class PresentOutlineRequest(BaseModel):
    notes_vi: str = Field(default="", max_length=1200)


class PresentAttemptRequest(BaseModel):
    wav_b64: str = Field(min_length=100, max_length=11_700_000)  # 16 kHz 16-bit mono WAV, <= 270 s


# ---------------------------------------------------------------- Tranh luận · Đàm phán · Phản biện


class DebateScenarioOut(BaseModel):
    id: str
    kind: str
    tier: int
    title_vi: str
    situation_vi: str
    learner_role_vi: str
    haru_role_vi: str
    learner_goal_vi: str
    opener_en: str = ""  # the motion / Haru's first line; empty for a critique (the claim is the surprise)
    sides: list[str] = []


class DebatePhraseOut(BaseModel):
    ko: str
    vi: str


class DebateOptionsOut(BaseModel):
    band: int
    band_label_vi: str
    tier: int
    kinds: dict[str, str]
    scenarios: list[DebateScenarioOut]
    phrases: dict[str, list[DebatePhraseOut]]  # by kind, for the learner's tier
    criteria: dict[str, dict[str, str]]
    rubric: dict[str, dict[str, str]]  # by kind: what a 4 means at the learner's tier
    seconds_left_today: int
    daily_minutes: int


class DebateStartRequest(BaseModel):
    kind: Literal["debate", "negotiate", "critique"]
    scenario_id: str | None = Field(default=None, max_length=20)
    motion: str = Field(default="", max_length=200)  # a debate motion of the learner's own
    side: Literal["찬성", "반대"] = "찬성"
    band_shift: int = Field(default=0, ge=-1, le=1)


class DebateStartOut(BaseModel):
    session_id: uuid.UUID
    token: str
    ws_url: str
    setup: dict
    nudges: dict[str, str]
    max_seconds: int
    seconds_left_today: int
    band: int
    band_label_vi: str
    scenario: DebateScenarioOut
    side: str | None = None
    phrases: list[DebatePhraseOut]
    criteria: dict[str, str]


class DebateReportOut(BaseModel):
    kind: str
    summary_vi: str = ""
    outcome_vi: str = ""
    scores: dict[str, int]
    score_notes_vi: dict[str, str] = {}
    overall: float
    best_move: dict[str, str] = {}
    missed: list[dict[str, str]] = []
    phrases_used: list[str] = []
    fixes: list[dict[str, str]] = []
    goal_reached: bool = False
    flaw_found: bool = False
    next_time_vi: str = ""
    flaw_vi: str = ""  # critique: the planted flaw, revealed now


class DebateFinishOut(BaseModel):
    session_id: uuid.UUID
    seconds: int
    learner_turns: int
    report: DebateReportOut | None = None
    report_error_vi: str | None = None
    band_before: int | None = None
    band_after: int | None = None
    criteria: dict[str, str] = {}


class DebateRowOut(BaseModel):
    id: uuid.UUID
    started_at: datetime
    seconds: int
    kind: str
    title_vi: str
    band: int | None = None
    overall: float | None = None
    goal_reached: bool = False


class DebateDetailOut(DebateFinishOut):
    started_at: datetime
    kind: str
    title_vi: str
    side: str | None = None
    turns: list[dict[str, str]] = []


# ------------------------------------------------------------- lesson essay check --
class EssayCheckRequest(BaseModel):
    text: str = Field(min_length=1, max_length=3000)


class EssayFixOut(BaseModel):
    original: str
    corrected: str = ""
    category: str
    reason_vi: str
    source: Literal["ai", "auto"] = "ai"


class EssayCriterionOut(BaseModel):
    criterion_vi: str
    max: float
    score: float | None = None
    comment_vi: str = ""


class EssayPatternOut(BaseModel):
    pattern: str
    label_vi: str
    found: bool


class EssayLengthOut(BaseModel):
    chars: int
    min: int | None = None
    max: int | None = None
    status: Literal["ok", "short", "long"]


class EssayResultOut(BaseModel):
    score: float | None = None
    points: float
    criteria: list[EssayCriterionOut] = []
    fixes: list[EssayFixOut] = []
    missing_vi: list[str] = []
    strengths_vi: list[str] = []
    corrected_en: str = ""
    summary_vi: str = ""
    length: EssayLengthOut | None = None
    patterns: list[EssayPatternOut] = []
    ai_checked: bool = False
    note: str = ""


class EssayCheckOut(BaseModel):
    id: uuid.UUID
    lesson_id: int
    exercise_id: str
    status: Literal["pending", "ready", "failed"]
    job_id: uuid.UUID | None = None
    text: str
    result: EssayResultOut | None = None
    created_at: datetime


# ------------------------------------------------------------------ TOPIK word bank --
class BankDeckOut(BaseModel):
    key: str
    title_vi: str
    grade: Literal["mid", "adv"]
    grade_vi: str
    words: int
    added: bool = False  # in the learner's reviews
    started: int = 0  # words of the deck the learner has started
    practiced: int = 0  # words answered right at least twice: enough to use them in a sentence or a talk


class BankDeckWordsOut(BaseModel):
    key: str
    title_vi: str
    grade: Literal["mid", "adv"]
    grade_vi: str
    added: bool = False
    words: list[VocabItemOut]

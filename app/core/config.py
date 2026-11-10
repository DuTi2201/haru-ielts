from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central config, read from env vars (Railway service Variables).

    Mirrors SDD §5 "cấu hình thay cho hard-code": nothing here should be
    hard-coded into business logic — rubric versions, model names and
    prompt versions belong in the `app_config` table (see app/models.py),
    not here. This file is transport/infra config only.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    ENVIRONMENT: str = "development"

    # Postgres — asyncpg driver for the app, psycopg2 for Alembic (sync)
    DATABASE_URL: str = "postgresql+asyncpg://haru:haru@localhost:5432/haru"

    @property
    def SYNC_DATABASE_URL(self) -> str:
        return self.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql+psycopg2://")

    # Redis — broker/result backend for Celery AND the job.progress pub/sub
    # channel that replaces the SDD's SSE-over-Redis fan-out.
    REDIS_URL: str = "redis://localhost:6379/0"
    # A new recording (TTS / Gemini) started from a public endpoint spends from these hourly
    # allowances, per caller and over everyone. Playing a recording that exists is free.
    # "word" = one word or one sentence (cheap, a learner meets many); "lecture" = a whole
    # lecture or dialogue (costly).
    AUDIO_WORD_PER_CLIENT_HOURLY: int = 150
    AUDIO_WORD_ALL_HOURLY: int = 600
    AUDIO_LECTURE_PER_CLIENT_HOURLY: int = 12
    AUDIO_LECTURE_ALL_HOURLY: int = 60

    # CORS — the Lovable frontend is a separate origin (no Supabase, no
    # same-origin cookies), so this must be explicit and not "*".
    CORS_ORIGINS: str = ""
    CORS_ORIGIN_REGEX: str = r"^https://.*\.lovable\.app$"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    # Auth
    JWT_SECRET: str = "dev-secret-change-me"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TTL_MIN: int = 60
    JWT_REFRESH_TTL_DAYS: int = 30

    # Gemini — model choice is config, not hard-coded (SDD §5 principle 6);
    # override per-env on Railway if a cheaper/newer model becomes the
    # better fit. Flash-Lite for both ingestion jobs: high volume, well-
    # constrained JSON schema, no need for Pro-tier reasoning.
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL_LESSON_INGEST: str = "gemini-3.5-flash-lite"
    GEMINI_MODEL_CORPUS_INGEST: str = "gemini-3.5-flash-lite"
    # Reads an exam paper (and its answer key) off the pages — see
    # app/services/exam_extract.py. Copying every character exactly is the one
    # job where a stronger model pays off, so this is NOT the lesson model.
    # A GEMINI_MODEL_EXAM_INGEST variable set on Railway wins over this default;
    # empty falls back to GEMINI_MODEL_LESSON_INGEST.
    GEMINI_MODEL_EXAM_INGEST: str = "gemini-3.8-flash"
    # Everything that analyses or solves exam material: the writing drill's
    # exercise generation and grading (app/services/writing_drill.py). Same
    # override rule: a Railway variable of this name wins; empty = the study model.
    GEMINI_MODEL_EXAM_ANALYSIS: str = "gemini-3.8-flash"
    # Read the paper a second time and show where the two readings differ.
    EXAM_VERIFY_PASS: bool = True
    # Look again, page by page, at the spots a first reading left empty (an
    # underline nobody saw, a banner / chart that came back blank).
    EXAM_REFINE_PASS: bool = True
    # Text model for the beginner study pack (translation / simplified Korean /
    # word breakdown) — see app/services/study_pack.py. Override via env to use
    # a stronger model without a code change.
    GEMINI_MODEL_STUDY: str = "gemini-3.5-flash-lite"
    # Model that writes the "Bài giảng tổng hợp" script (story, phrases,
    # synonyms, idioms — see app/services/podcast_script.py). Empty = use
    # GEMINI_MODEL_LESSON_INGEST; set a stronger model here for richer lectures.
    GEMINI_MODEL_PODCAST: str = ""
    GEMINI_EMBEDDING_MODEL: str = "gemini-embedding-2"
    # TTS: a real Gemini call (app/services/tts.py), not a stub — always
    # cache the result (audio.lecture_audio / audio.corpus_item_audio) and
    # never call this per-playback.
    GEMINI_MODEL_TTS: str = "gemini-2.5-flash-preview-tts"
    # Gemini's free-tier TTS quota is tracked per-model (e.g. a hard 10
    # requests/day cap on gemini-2.5-flash-tts alone), so a fallback model
    # is a genuinely separate quota bucket, not just cosmetic redundancy.
    # synthesize_korean_tts only fails over to this on a RESOURCE_EXHAUSTED
    # (429) from the primary model — kept a same-generation TTS model (not
    # one of the newer 3.x models) since it's confirmed to use the exact
    # same generate_content/response_modalities/speech_config call shape.
    GEMINI_MODEL_TTS_FALLBACK: str = "gemini-2.5-pro-preview-tts"

    # Google Cloud Text-to-Speech, Chirp 3 HD — the PRIMARY voice for Korean
    # article / passage read-aloud (app/services/google_tts.py); Gemini above
    # stays as the fallback. The credential is ONLY ever read from the
    # environment (Railway variable `TTS_GG_Chirp`; env names are matched
    # case-insensitively) and must never be written into code, docs or
    # tests. Empty => Chirp is off and everything behaves exactly as before.
    TTS_GG_CHIRP: str = ""
    # Non-secret tuning: change on Railway to swap the voice or pace without a
    # deploy of code. Changing either also changes the article-audio cache key
    # (see google_tts.spec), so recordings regenerate with the new voice.
    TTS_CHIRP_VOICE: str = "ko-KR-Chirp3-HD-Iapetus"
    TTS_CHIRP_SPEAKING_RATE: float = 0.85
    # The "Bài giảng tổng hợp" lecture mixes Vietnamese explanation with Korean
    # examples. A Chirp voice belongs to ONE language, so the lecture is voiced
    # run by run: Hangul with TTS_CHIRP_VOICE (pace above, slowed for
    # shadowing) and Vietnamese with the voice below. Empty voice = the same
    # persona as the Korean one in vi-VN (e.g. vi-VN-Chirp3-HD-Iapetus), so
    # the lecturer sounds like one person. Both are cache-key inputs.
    TTS_CHIRP_VOICE_VI: str = ""
    TTS_CHIRP_SPEAKING_RATE_VI: float = 0.95
    # The recorded dialogues of a lesson's practice set (listening questions, speaking
    # S4): two people, so two voices — the male is TTS_CHIRP_VOICE above, the female is
    # this one — read at a natural pace (exam audio is not slowed for shadowing). If
    # Google refuses the female name, a Korean Chirp voice of that gender is picked.
    TTS_CHIRP_VOICE_FEMALE: str = "ko-KR-Chirp3-HD-Aoede"
    TTS_CHIRP_SPEAKING_RATE_EXAM: float = 1.0
    # A lecture is hundreds of short requests (a Korean word, its Vietnamese meaning, ...).
    # They are sent over a few connections at once, but never faster than this many per
    # minute: Chirp 3 HD allows 200 a minute per Google project, and the rest of the app
    # (word and passage audio) shares that allowance.
    TTS_LECTURE_WORKERS: int = 3
    TTS_LECTURE_RPM: int = 170

    # Where the bytes of a recording made from a TEXT (app/services/text_audio.py) are filed.
    # "db" (default): in the row itself, no setup. "gcs": an object in a PRIVATE Google Cloud
    # Storage bucket, the row keeps only the link; if an upload fails the recording is kept
    # in the row instead, so audio is never lost. The bucket name is not a secret; the
    # service-account JSON (AUDIO_GCS_CREDENTIALS) is, and lives ONLY in a Railway variable.
    AUDIO_STORAGE: str = "db"
    AUDIO_GCS_BUCKET: str = ""
    AUDIO_GCS_CREDENTIALS: str = ""
    # Long recordings (lectures): send the player to a signed link into the bucket instead of reading
    # the file through the API. Falls back to serving it here by itself if the bucket refuses the link.
    AUDIO_REDIRECT_TO_GCS: bool = True
    # The longest text one request may have voiced (a reading passage is cut by line first).
    TEXT_AUDIO_MAX_CHARS: int = 600

    # The daily reading + dialogue (app.services.daily_reading): a learner's "today" is the
    # calendar day in this zone. Change it if the app is used elsewhere.
    DAILY_READING_TZ: str = "Asia/Ho_Chi_Minh"
    BACKUP_GCS_PREFIX: str = "backup"

    # Pictures for lessons and exercises (app/services/lesson_image.py). An editor presses
    # "Tạo ảnh" in Studio; every picture is made once and kept in the database. The model is a
    # Gemini image model ("Nano Banana" family, e.g. gemini-3.1-flash-image, or the cheaper
    # gemini-3.1-flash-lite-image) — change it with GEMINI_MODEL_IMAGE; pictures already made are kept.
    # Set LESSON_IMAGE_GEN_ENABLED=false to switch the feature off (lessons then use icons only).
    LESSON_IMAGE_GEN_ENABLED: bool = True
    GEMINI_MODEL_IMAGE: str = "gemini-3.1-flash-image"
    # auto = the Interactions endpoint, falling back to generateContent if it is not there;
    # or force one: interactions | generate_content
    GEMINI_IMAGE_API: str = "auto"

    # Content-ingestion tuning (Studio uploads — admin.py/ingest.py)
    MAX_INGEST_FILE_MB: int = 20
    # Cues per Gemini call when classifying a subtitle file — the knob
    # that keeps FR-19/Gate-G6's "prompt size không phình theo độ dài
    # kịch bản" true: each call's prompt is this many cues, however long
    # the film is; a longer film means more calls, never a bigger prompt.
    CORPUS_CHUNK_SIZE: int = 40
    # Sentences per Gemini call when adding a meaning / usage note to corpus
    # sentences (app/services/corpus_enrich.py). Smaller than the classifier's
    # chunk because the answer is long-form text per sentence; the pause keeps
    # a backfill of the whole corpus under the per-minute request limit.
    CORPUS_ENRICH_CHUNK_SIZE: int = 20
    CORPUS_ENRICH_PAUSE_SEC: float = 1.0

    # Rate limiting (Postgres-table equivalent of the SDD's Redis quota)
    AI_DAILY_JOB_LIMIT: int = 200
    # What one learner may ask the model to mark in a rolling 24 hours (each one is a paid model
    # call): a confirmed handwriting transcript (Xưởng viết) and a saved editorial outline. These
    # caps apply with or without billing.
    WRITING_GRADES_PER_DAY: int = 10
    # AI checks of a paragraph written in a lesson (Bước 4/5, Viết 53/54; app.services.essay_check)
    LESSON_ESSAY_CHECKS_PER_DAY: int = 8
    # Azure Neural TTS for short Korean texts (app/services/azure_tts.py): when the key and region are
    # set, every Korean text, word and letter is voiced by Azure (with the NIKL pronunciation table);
    # empty = Google Chirp as before. Lectures and article read-alongs stay on Chirp.
    AZURE_SPEECH_KEY: str = ""
    AZURE_SPEECH_REGION: str = ""
    AZURE_TTS_VOICE: str = "ko-KR-SunHiNeural"
    AZURE_TTS_VOICE_MALE: str = "ko-KR-InJoonNeural"
    AZURE_TTS_RATE: float = 0.95
    # "Trò chuyện với Haru" (app.services.conversation): the Gemini Live model the browser talks to
    # with a single-use token, its voice (empty = the model's default), how long one session may
    # run, how many minutes a learner may talk per 24 hours (0 = no cap), and the model that writes
    # the end-of-session report (empty = GEMINI_MODEL_STUDY).
    CONVERSATION_LIVE_MODEL: str = "gemini-3.8-live"
    CONVERSATION_VOICE: str = ""
    CONVERSATION_SESSION_SECONDS: int = 600
    CONVERSATION_DAILY_MINUTES: int = 20
    CONVERSATION_REPORT_MODEL: str = ""
    # phase 2: the model that listens to the learner's own sentences (multimodal audio) after a session
    CONVERSATION_PRONUNCIATION_MODEL: str = "gemini-3.8-flash"
    # "Trình bày với Haru" (app.services.presentation): the model that listens to a whole answer and
    # marks it (empty = CONVERSATION_PRONUNCIATION_MODEL), the one that writes topics and outlines
    # (empty = GEMINI_MODEL_STUDY), and how many marked tries a learner gets per 24 hours (0 = no cap).
    PRESENT_EVAL_MODEL: str = ""
    PRESENT_TEXT_MODEL: str = ""
    PRESENT_DAILY_ATTEMPTS: int = 15
    EDITORIAL_OUTLINES_PER_DAY: int = 10

    # ---- Paid access (app/services/billing). EVERYTHING here is off by default: with
    # BILLING_ENABLED=false the app behaves exactly as before (all lessons open).
    # The three PAYOS_* values are SECRETS: they live ONLY in the server's env file
    # (.env.prod on the owner's Mac and /opt/haru/.env.prod on the VM), never in code, docs,
    # tests, the repository, Lovable, Railway or GitHub.
    BILLING_ENABLED: bool = False
    # True closes the corpus (Luyện nghe), the editorial commentaries and the real past papers to
    # everyone but editors and admins. Open by default: the app is used inside a small group
    # (owner's decision, October 2026). Set BILLING_PRIVATE_SOURCES=true to close them again.
    BILLING_PRIVATE_SOURCES: bool = False
    PAYOS_CLIENT_ID: str = ""
    PAYOS_API_KEY: str = ""
    PAYOS_CHECKSUM_KEY: str = ""
    PAYOS_BASE_URL: str = "https://api-merchant.payos.vn"
    # Where payOS sends the browser back to (no trailing slash), e.g. https://haru.lovable.app.
    # Empty = the first entry of CORS_ORIGINS.
    FRONTEND_URL: str = ""
    # Not a secret: a Zalo / Telegram link shown on the "I paid but nothing unlocked" screen.
    BILLING_SUPPORT_URL: str = ""
    BILLING_ORDER_TTL_MIN: int = 15
    BILLING_MAX_PENDING_ORDERS: int = 3
    BILLING_MAX_ORDERS_PER_HOUR: int = 10
    # Who sells (not secrets; shown on the terms, refund and contact pages, which payment gateways
    # and buyers expect). Empty fields read "đang cập nhật" on those pages.
    MERCHANT_NAME: str = ""
    MERCHANT_TAX_ID: str = ""
    MERCHANT_ADDRESS: str = ""
    MERCHANT_EMAIL: str = ""
    MERCHANT_PHONE: str = ""


    @property
    def billing_configured(self) -> bool:
        """Billing is on AND payOS can be called (all three values set)."""
        return bool(self.BILLING_ENABLED and self.PAYOS_CLIENT_ID and self.PAYOS_API_KEY and self.PAYOS_CHECKSUM_KEY)

    @property
    def frontend_origin(self) -> str:
        return (self.FRONTEND_URL or (self.cors_origin_list[0] if self.cors_origin_list else "")).rstrip("/")


settings = Settings()

# Haru English (IELTS Academic 6.5) — handoff notes

Read this first. It says what exists, what is checked, what is not, and what to do next.
Update it in the same commit as any work you push.

## Goal
A private self-study app for one Vietnamese learner: from a weak base (about band 3.5–4.0) to
IELTS Academic 6.5. Study time 2–4 hours a day. Exam window: September 2027 to January 2028.
Design target: Listening 7.0, Reading 7.0, Writing 6.0, Speaking 6.0.
Gate before booking the test: three Cambridge tests in a row, timed, on a computer, with
Listening ≥ 30/40, Reading ≥ 30/40, Writing and Speaking ≥ 6.0 on a calibrated marker.

## Repositories
| Repo | What | State |
| --- | --- | --- |
| `DuTi2201/haru-ielts` | backend, fork of `haru-korea` at `e93bc78` | Korean lessons replaced by the B1 course; code not yet adapted |
| `DuTi2201/haru-ielts-journey` | frontend, fork of `haru-korean-journey` at `e8dcb2f` | untouched baseline; `.env` still points at the Korean API |
| `DuTi2201/haru-korea`, `haru-korean-journey` | the Korean product, live | do not change from this project |

## Decisions the owner has made
* Host: upgrade the existing Haru VM (2 vCPU, 2 GB RAM, already swapping) to 4 GB (`e2-medium`, done 2026-11-10 after full DB backup) and run a second
  api + worker + db + redis stack (`haru-ielts`) with its own database (`haru_ielts`).
* Hostname & Frontend: `https://ielts.34-9-216-231.sslip.io`, served by Caddy (static build of `haru-ielts-journey` + reverse proxy `/api/*` and `/healthz` to `haru-ielts-api-1`).
* Credentials & Backups: reuse Gemini / Google TTS / Azure Speech / GCS credentials from the VM's `.env.prod` (never committed), with a separate `JWT_SECRET`, separate `POSTGRES_PASSWORD`, and separate GCS backup prefix (`backup-ielts/`).
* Single-user access: owner account uses the same admin email as Haru Korean; registration (`/api/v1/auth/signup`) is closed once the owner account exists; billing and paywalls are disabled.
* Writing length: count words (IELTS standard, e.g. 60–150 words for B1 unit writing tasks) instead of Korean characters.
* Four-skills course books: use both Mindset for IELTS and Complete IELTS Bands 5–6.5.
* Deploy all of Destination B1 at once, with listening, speaking, reading and writing tied to each unit.

## Deployment & Adaptation Plan (2026-11-10)
1. **Item 1 — Boot with the B1 seed (`feature/b1-boot`)**:
   - Remove Korean seed folders (`nikl`, `exams`, `passages`, `editorial`, `placement`, `images.json`, `practice_support.json`, `practice_tiers.json`, `word_icons.json`).
   - Switch off Korean-only routers (`topik_bank`, `editorial`, `daily`, `real_exam`, `billing`, `admin_abuse`, `onboarding`) and Korean-only beat tasks.
   - Adapt `lesson_seed.py`, `roadmap.py`, `journey.py`, and `essay_check.py` (word count instead of character count; B1 lesson limits updated in `scripts/b1/skills.txt` & regenerated via `scripts/b1/build.py`).
2. **Item 2 — Migrations**:
   - Add a new Alembic migration on top of `head` that removes seeded Korean rows (`editorial_source`, Korean `app_config` / `site_setting`) without modifying historical migrations.
3. **Item 3 — Voices**:
   - Update `azure_tts.py` to accept `en-GB-*Neural` and `en-US-*Neural` voices (default `en-GB-SoniaNeural` / `en-GB-RyanNeural`), bypass `korean_g2p`, and set `xml:lang` from the voice locale.
   - Update `google_tts.py`, `lecture_voice.py`, `lesson_audio.py`, and `tts.py` to default to English Chirp 3 HD voices (`en-GB-Chirp3-HD-Aoede` / `en-GB-Chirp3-HD-Iapetus`) while keeping Vietnamese (`vi-VN`) for lecture explanations.
4. **Item 4 — Billing & Abuse Controls**:
   - Make `ensure_lesson_open` a no-op (all lessons open), disable trials/payments/signup throttling, and close `/api/v1/auth/signup` once at least one account exists.
5. **Item 5 — Tests**:
   - Rewrite Korean-specific assertions in `tests/test_lesson_seed.py` and `tests/test_lesson_sessions.py` for the 42 B1 units, remove Hangul/hanja/TOPIK tests, and verify the full suite passes locally.
6. **VM Stack, Caddy & Frontend**:
   - Deploy `/opt/haru-ielts` (`haru-ielts` compose project: `api` 400 MB, `worker` 500 MB, `db` 350 MB, `redis` 64 MB) and configure daily GCS backup under `backup-ielts/`.
   - Build `DuTi2201/haru-ielts-journey` with `VITE_API_BASE_URL=https://ielts.34-9-216-231.sslip.io`, replace Korean/TOPIK UI labels with English/IELTS, hide switched-off screens, and serve via Caddy under `ielts.34-9-216-231.sslip.io`.
7. **Item 6 — Mechanical Rename**:
   - Rename `hangul` → `headword`, `*_ko` → `*_en`, `topik_tip_vi` → `exam_tip_vi` across models, schemas, `scripts/b1/build.py`, seeds, a new Alembic migration, and frontend types, then redeploy.

## What was switched off (Commit 1 — `feature/b1-boot`)
* **Korean seed folders & files removed**: `app/seed/nikl/`, `app/seed/exams/`, `app/seed/passages/`, `app/seed/editorial/`, `app/seed/placement/`, `app/seed/images.json`, `app/seed/practice_support.json`, `app/seed/practice_tiers.json`, `app/seed/practice_type_tips.json`, `app/seed/word_icons.json`.
* **Routers detached from `app/api/router.py`**: `topik_bank`, `editorial`, `daily`, `chats`, `real_exam`, `billing`, `admin_abuse`, `onboarding`, `audio.corpus_router` (service modules in `app/services/` kept per owner instruction).
* **Celery beat schedules disabled in `app/core/celery_app.py`**: `reconcile-billing-orders`, `discover-editorial-candidates` (kept `reset-daily-ai-quota` and `backup-database` with configurable `BACKUP_GCS_PREFIX`).
* **Writing limits & word count**: `writing_task` in `scripts/b1/build.py` updated to `{"min": 30, "max": 90}` words; `app/services/essay_check.py` switched to English word counting (`count_words`).
* **Migrations (Commit 2 — `e8f1a3c5d7b9`)**: Added migration `e8f1a3c5d7b9_english_ielts_seed_cleanup.py` on top of `b7d2f9a4c1e6` to delete Korean `editorial.editorial_source`, `billing.product_setting`, and TOPIK `content.question_type` rows, seed IELTS `question_type` rows, and add `ielts65` / `b1` to `profile_goal` enum without modifying old migrations.
* **Voices (Commit 3)**: Updated `app/core/config.py`, `app/services/azure_tts.py`, `app/services/google_tts.py`, `app/services/text_audio.py`, `app/services/tts.py`, `app/services/landing_audio.py`, and `app/schemas.py` so Azure TTS accepts `en-GB-*Neural` / `en-US-*Neural` (default `en-GB-SoniaNeural` / `en-GB-RyanNeural`) and skips `korean_g2p` for English voices, Google Chirp defaults to `en-GB-Chirp3-HD-Iapetus` / `en-GB-Chirp3-HD-Aoede` (preserving Vietnamese lecture voice), and `text_audio.check_text` validates English text.
* **Billing & Abuse Controls (Commit 4)**: Disabled payments, trials, and signup abuse throttling in `app/api/deps.py` and `app/api/routers/auth.py`; `/api/v1/auth/signup` is closed (`403 registration_closed`) once the single owner account exists.

## What exists
* `scripts/b1/` — the source of the B1 course (see its README). `build.py` writes
  `app/seed/lessons/b1-*.json` (42 lessons) and `app/seed/exercises/b1/` (1,237 exercises).
  Every unit ends with its own reading (a short passage, one choice question and two True/False/Not Given),
  a short writing task with a frame, a checklist and a model, a dictation and a speaking task (`scripts/b1/skills.txt`).
  28 grammar units, 85 cards; 14 vocabulary units, 1,056 words and phrases; 104 sittings.
* `tools/study_page/` — builds one self-contained HTML page from the seed, so the course can be
  studied before the app is deployed (cards, questions, dictation with the browser's voice, speaking
  prompts with a timer and a model answer; progress kept in the browser).
* Design document (owner's copy): "Haru English — Đánh giá & bản thiết kế lộ trình IELTS Academic 6.5".

## Content rule
From a book we take the syllabus only: unit titles, page numbers, word lists. Explanations, examples,
questions and model answers are written for this course; each lesson sends the learner to the book's
own exercises. Do not paste book exercises, reading passages or audio scripts into the repository.

## Checked / not checked
* Checked: `load_all()` of `app.services.lesson_seed` reports 42 lessons and no problems; the
  sitting tests of `tests/test_lesson_sessions.py` pass (≤ 24 core words, ≤ 3 cards per sitting).
* Not checked: the full test suite (the sandbox lacked sqlalchemy/httpx). 31 tests of
  `tests/test_lesson_seed.py` fail because they assert Korean content.
* Unit placement of phrasal verbs, prepositional phrases, word patterns and word families is now
  checked against the book: the fourteen unit opening pages were read from the PDF as images and
  typed into `scripts/b1/book_units.py`. That check moved 111 items to another unit (the earlier
  OCR-based placement was wrong far more often than the 42 it had flagged), added three items the
  lists lacked (`by credit card/cheque`, `ask (sb) about`, `accuse sb of`) and replaced the word
  family `identify` with the book's `identical`. `unverified` is empty. Run
  `python3 scripts/b1/book_units.py` to check again; never run `assign_units.py`.
* Preposition questions: `ALSO_OK` in `build.py` lists prepositions that would also be acceptable in
  the example sentence and are never offered as wrong options (72 items reviewed by hand, once).
  Phrasal-verb questions show the meaning wanted, because several particles make a real verb.
* Writing tasks set `limits` to 150–600 as characters (the Korean app counts characters); decide
  whether the English app should count words.
* The readings and model texts are written for the course and have not been read by a second person.
* Nothing has been read by a second person yet.

## Known debt
* Schema field names are still Korean (`hangul`, `title_ko`, `example_ko`, `prompt_ko`,
  `model_answer_ko`, `topik_tip_vi`) and hold English.
* Korean-only code is still in the fork: `korean_g2p.py`, the Hangul lesson, TOPIK banks,
  `app/seed/{nikl,exams,passages,editorial,placement}`, billing, ko-KR voices, Asia/Seoul.
* Pronunciation is judged by Gemini listening; Azure Pronunciation Assessment (en-US only for
  prosody) is not wired in. Azure is used for Korean TTS only.

## Next steps, in order
1. Adapt and deploy (brief: `docs/DEPLOY_PROMPT.md`): rename fields (one mechanical commit), drop Korean-only modules and tests,
   English TTS voices, new database, point the frontend at the new API, upgrade the VM.
2. Done 2026-11-10: unit placement checked against the book pages (`scripts/b1/book_units.py`).
3. Per-unit skills links for B1, still missing: Mindset for IELTS Foundation units, British Council
   B1 listening, longer listening than the two-sentence dictation, a Task 1 chart task. The teacher's methods are folded into B1
   (summary, topic sentence, paragraph frame, speaking sets): see `docs/METHODS.md`, which also holds the Task 1 and Task 2 rules for B2.
4. Destination B2 the same way (28 units; grammar is the odd units), then four C1&C2 grammar units
   (11 Conditionals, 17 Clauses, 19 Complex sentences, 21 Noun phrases).
5. IELTS question types, one Cambridge test as the model for the computer-style mock screen,
   the calibrated writing and speaking markers.

## Where the learner's materials are
On the owner's Mac: `~/Downloads/Ielts_Giáo trình` (Destination B1/B2/C1-C2, Cambridge IELTS 17–21
with audio, Mindset Foundation, Complete IELTS 5–6.5, Official Cambridge Guide, Cullen's books)
and `~/Downloads/Pre_IELTS_thầy Minh` (a Vietnamese teacher's foundation course notes).
The B1 book is a scan without a text layer: OCR it (tesseract, 200 dpi) before reading it.

## Log
* 2026-11-10 — baseline forks pushed; B1 course generated and validated; study page added.
* 2026-11-10 — `docs/DEPLOY_PROMPT.md` (brief for the agent that deploys to the VM); a reading and a
  writing task for each of the 42 units; second pass on unit placement; safer wrong options.
* 2026-11-10 — branch `content/b1-methods` (on top of `feature/b1-boot` at bcc6042): unit placement
  checked against the book pages; per unit a passage summary (`R2`) and a topic-sentence question
  (`T1`); paragraph frame in every writing task; Part 1/2/3 speaking sets for the 14 vocabulary
  units (`S2`–`S4`); `docs/METHODS.md`; study page rebuilt and opened once in headless Chrome
  (all 1,237 exercises render, no script errors). `load_all()`: 42 lessons, 1,237 exercises, no
  problems. The same 32 Korean-era tests fail before and after this change.
  To merge: `git merge content/b1-methods` into `feature/b1-boot`; only `scripts/b1`, `tools/study_page`,
  `docs` and the generated `app/seed/lessons/b1-*`, `app/seed/exercises/b1/*` change. If the field rename
  has happened by then, re-run `python3 scripts/b1/build.py` after the merge instead of keeping the generated files.

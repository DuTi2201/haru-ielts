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
| `DuTi2201/haru-ielts` | backend, fork of `haru-korea` at `e93bc78` | B1 course live; schema renamed to English (`headword`, `*_en`, `exam_tip_vi`); deployed on `haru-vm` |
| `DuTi2201/haru-ielts-journey` | frontend, fork of `haru-korean-journey` at `e8dcb2f` | adapted to IELTS/English, renamed fields, deployed at `https://ielts.34-9-216-231.sslip.io` |
| `DuTi2201/haru-korea`, `haru-korean-journey` | the Korean product, live | do not change from this project |

## Decisions the owner has made
* Host: upgrade the existing Haru VM (2 vCPU, 2 GB RAM, already swapping) to 4 GB (`e2-medium`, done 2026-11-10 after full DB backup) and run a second
  api + worker + db + redis stack (`haru-ielts`) with its own database (`haru_ielts`).
* Hostname & Frontend: `https://ielts.34-9-216-231.sslip.io` (verified `34.9.216.231` is a reserved external static IP `haru-ip`), served by Caddy (static build of `haru-ielts-journey` + reverse proxy `/api/*` and `/healthz` to `haru-ielts-api-1`).
* Credentials & Backups: reuse Gemini / Google TTS / Azure Speech / GCS credentials from the VM's `.env.prod` (never committed), with a separate `JWT_SECRET`, separate `POSTGRES_PASSWORD`, and separate GCS backup prefix (`backup-ielts/`).
* Single-user access: owner account uses the same admin email as Haru Korean; registration (`/api/v1/auth/signup`) is closed once the owner account exists; billing and paywalls are disabled.
* Writing length: count words (IELTS standard, `30–90` words in `writing_task` of `scripts/b1/build.py` for B1 unit writing tasks) instead of Korean characters.
* Keep service modules: only detach Korean routers from `app/api/router.py` and remove Korean seed files/folders; keep the service modules in `app/services/` (`editorial`, `daily`, `real_exam`, `onboarding`, `conversation`, `presentation`, `debate`, etc.).
* Four-skills course books: use both Mindset for IELTS and Complete IELTS Bands 5–6.5.
* Deploy all of Destination B1 at once, with listening, speaking, reading and writing tied to each unit.

## Deployment & Adaptation Plan (2026-11-10)
1. **Item 1 — Boot with the B1 seed (`feature/b1-boot`)**:
   - Remove Korean seed folders (`nikl`, `exams`, `passages`, `editorial`, `placement`, `images.json`, `practice_support.json`, `practice_tiers.json`, `practice_type_tips.json`, `word_icons.json`).
   - Switch off Korean-only routers (`topik_bank`, `editorial`, `daily`, `chats`, `real_exam`, `billing`, `admin_abuse`, `onboarding`, `audio.corpus_router`, `writing`, `conversation`, `conversation_history`, `presentation`, `debate`) and Korean-only beat tasks (`reconcile-billing-orders`, `discover-editorial-candidates`).
   - Adapt `lesson_seed.py`, `roadmap.py`, `journey.py`, and `essay_check.py` (word count instead of character count; B1 lesson writing limits set to `30–90` words in `scripts/b1/build.py` and regenerated).
2. **Item 2 — Migrations**:
   - Add `e8f1a3c5d7b9_english_ielts_seed_cleanup.py` on top of `b7d2f9a4c1e6` that removes seeded Korean rows (`editorial_source`, Korean `product_setting`, TOPIK `question_type`) and seeds IELTS `question_type` rows without modifying historical migrations.
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
7. **Item 6 — Mechanical Rename (`f9a2b4c6d8e0`)**:
   - Rename `hangul` → `headword`, `*_ko` → `*_en`, `topik_tip_vi` → `exam_tip_vi` across models, schemas, `scripts/b1/build.py`, `tools/study_page/build_page.py` (and rebuild `tools/study_page/dist/b1-study.html`), seeds, Alembic migration `f9a2b4c6d8e0_rename_ko_fields_to_en.py`, and frontend types, then redeploy.

## What was switched off & completed
* **Korean seed folders & files removed**: `app/seed/nikl/`, `app/seed/exams/`, `app/seed/passages/`, `app/seed/editorial/`, `app/seed/placement/`, `app/seed/images.json`, `app/seed/practice_support.json`, `app/seed/practice_tiers.json`, `app/seed/practice_type_tips.json`, `app/seed/word_icons.json`.
* **Routers detached from `app/api/router.py`**: `topik_bank`, `editorial`, `daily`, `chats`, `real_exam`, `billing`, `admin_abuse`, `onboarding`, `audio.corpus_router`, `writing`, `conversation`, `conversation_history`, `presentation`, `debate` (all service modules in `app/services/` and router files in `app/api/routers/` kept intact per owner instruction).
* **Celery beat schedules disabled in `app/core/celery_app.py`**: `reconcile-billing-orders`, `discover-editorial-candidates` (kept `reset-daily-ai-quota` and `backup-database` with configurable `BACKUP_GCS_PREFIX=backup-ielts`).
* **Writing limits & word count**: `writing_task` in `scripts/b1/build.py` updated to `{"min": 30, "max": 90}` words; `app/services/essay_check.py` switched to English word counting (`count_words`).
* **Migrations (`e8f1a3c5d7b9` & `f9a2b4c6d8e0`)**:
  - `e8f1a3c5d7b9_english_ielts_seed_cleanup.py`: deletes Korean `editorial.editorial_source`, `billing.product_setting`, and TOPIK `content.question_type` rows, seeds IELTS `question_type` rows, and adds `ielts65` / `b1` to `profile_goal` enum.
  - `f9a2b4c6d8e0_rename_ko_fields_to_en.py`: renames `hangul` → `headword`, `*_ko` → `*_en`, and `topik_tip_vi` → `exam_tip_vi` across PostgreSQL tables (`content.lesson`, `content.vocab_item`, `content.grammar_point`, `content.question_type`, `content.exam_passage`, `content.exam_item`, `editorial.editorial_article`, `editorial.editorial_candidate`, `audio.text_audio`, `corpus.corpus_item`, `public.error_log`) and forces startup sync to re-populate `content.lesson.practice` JSONB with renamed keys.
* **Voices**: Updated `app/core/config.py`, `app/services/azure_tts.py`, `app/services/google_tts.py`, `app/services/text_audio.py`, `app/services/tts.py`, `app/services/landing_audio.py`, and `app/schemas.py` so Azure TTS accepts `en-GB-*Neural` / `en-US-*Neural` (default `en-GB-SoniaNeural` / `en-GB-RyanNeural`) and skips `korean_g2p` for English voices, Google Chirp defaults to `en-GB-Chirp3-HD-Iapetus` / `en-GB-Chirp3-HD-Aoede` (preserving Vietnamese lecture voice), and `text_audio.check_text` validates English text.
* **Billing & Abuse Controls**: Disabled payments, trials, and signup abuse throttling in `app/api/deps.py` and `app/api/routers/auth.py`; `/api/v1/auth/signup` is closed (`403 registration_closed`) once the single owner account exists.
* **Tests**:
  - **Before adaptation**: `1452 passed, 151 failed, 171 skipped, 17 errors` (plus 6 collection errors on deleted Korean seed modules).
  - **After adaptation & rename**: `1467 passed, 0 failed, 176 skipped, 0 errors` (`428 subtests passed`).
  - Rewrote `tests/test_lesson_seed.py`, `tests/test_lesson_sessions.py`, `tests/test_sentence_building.py`, `tests/test_feathers.py`, `tests/test_mistake_book.py`, `tests/test_lesson_audio.py`, `tests/test_lesson_images.py`, `tests/test_image_reuse.py`, `tests/test_lecture_slides.py`, `tests/test_grammar_graph.py`, `tests/test_coach.py`, `tests/test_vocab_priority.py`, `tests/test_lesson_api.py`, `tests/test_learner_voice.py`, `tests/test_dictation.py`, `tests/test_essay_check.py`, `tests/test_google_tts.py`, `tests/test_azure_korean_voice.py`, `tests/test_text_audio.py`, `tests/test_audio_sharing.py` for the 42 B1 units and English voices.
  - Deleted 12 purely Korean seed/router test files: `test_topik_bank.py`, `test_topik2_picks.py`, `test_real_exam.py`, `test_passages.py`, `test_daily_reading.py`, `test_placement.py`, `test_placement_cat.py`, `test_foundation_split.py`, `test_review_lesson.py`, `test_editorial_card_merge.py`, `test_practice_tiers.py`, `test_chats.py`.
* **Mechanical Rename (Commit 6)**: Renamed `hangul` → `headword`, `*_ko` → `*_en`, and `topik_tip_vi` → `exam_tip_vi` across models, schemas, services, routers, `scripts/b1/build.py`, `tools/study_page/build_page.py`, `tools/study_page/dist/b1-study.html`, `app/seed/lessons/b1-*.json`, `app/seed/exercises/b1/*.json`, tests, and frontend TypeScript types/components.

## What exists
* `scripts/b1/` — the source of the B1 course (see its README). `build.py` writes
  `app/seed/lessons/b1-*.json` (42 lessons) and `app/seed/exercises/b1/` (1,108 exercises).
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
* Checked: the full test suite passes (`1467 passed, 176 skipped, 0 failed, 0 errors, 428 subtests passed`).
* 42 phrasal verbs / prepositional phrases / word patterns / word families are placed in a unit by
  topic and were not found on the unit's pages by either OCR search (84 before a second, looser
  search confirmed 28 and moved 14): `scripts/b1/unit_assignment.json` → `unverified`. Settling the
  rest needs a person with the book. Do not re-run `assign_units.py` without the OCR pages: it
  rewrites that file.
* Preposition questions: `ALSO_OK` in `build.py` lists prepositions that would also be acceptable in
  the example sentence and are never offered as wrong options (72 items reviewed by hand, once).
  Phrasal-verb questions show the meaning wanted, because several particles make a real verb.
* Writing tasks set `limits` to 30–90 words (`writing_task` in `scripts/b1/build.py`) and `essay_check.py` counts English words.
* The readings and model texts are written for the course and have not been read by a second person.
* Nothing has been read by a second person yet.

## Known debt
* Schema field names have been renamed (`headword`, `title_en`, `example_en`, `prompt_en`,
  `model_answer_en`, `exam_tip_vi`).
* Unmounted service modules in `app/services/` (`editorial`, `daily`, `real_exam`, `onboarding`, `conversation`, `presentation`, `debate`) are kept in the repo per owner instruction while their routers are detached from `app/api/router.py`.
* Pronunciation is judged by Gemini listening; Azure Pronunciation Assessment (en-US only for
  prosody) is not wired in. Azure is used for English TTS (`en-GB-SoniaNeural`, `en-GB-RyanNeural`).

## Next steps, in order
1. Check the 84 unverified items and the preposition distractors against the book.
2. Per-unit skills links for B1, still missing: Mindset for IELTS Foundation units, British Council
   B1 listening, longer listening than the two-sentence dictation, a Task 1 chart task. Teacher notes to fold in ("Pre-IELTS thầy Minh"): six-step reading summary by
   keywords, the claim → reason → explanation → evidence paragraph frame, the Task 1 sentence formula.
3. Destination B2 the same way (28 units; grammar is the odd units), then four C1&C2 grammar units
   (11 Conditionals, 17 Clauses, 19 Complex sentences, 21 Noun phrases).
4. IELTS question types, one Cambridge test as the model for the computer-style mock screen,
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
* 2026-11-10 — adapted backend & frontend for English/IELTS, upgraded VM to `e2-medium` (4 GB RAM), deployed `haru-ielts` stack and `https://ielts.34-9-216-231.sslip.io`, completed mechanical rename (`hangul` → `headword`, `*_ko` → `*_en`, `topik_tip_vi` → `exam_tip_vi`) + rebuilt study page (`b1-study.html`), full test suite passing (`1467 passed, 176 skipped`).

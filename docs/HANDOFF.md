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
  `app/seed/lessons/b1-*.json` (42 lessons) and `app/seed/exercises/b1/` (1,236 exercises).
  Every unit ends with its own reading (a short passage, one choice question and two True/False/Not Given),
  a short writing task with a frame, a checklist and a model, a dictation and a speaking task (`scripts/b1/skills.txt`).
  28 grammar units, 85 cards; 14 vocabulary units, 1,060 words and phrases; 101 sittings.
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
* Checked end-to-end on live `https://ielts.34-9-216-231.sslip.io`:
  - `/healthz` returns `{"status":"ok","environment":"production"}` on both `https://ielts.34-9-216-231.sslip.io/healthz` and Korean `https://34-9-216-231.sslip.io/healthz`.
  - Owner account (`vuvanduong802@gmail.com`) logs in with existing credentials; `/api/v1/auth/signup` is closed (`403 registration_closed`).
  - `/api/v1/lessons` lists all 42 B1 units in order (`sort_order` 1..42).
  - Unit 1 (`b1-u01-present-simple-present-continuous-stative-verbs`) opens with renamed fields (`headword`, `example_en`, `exam_tip_vi`), MCQ (`B1U01Q1`), sentence-building (`B1U01B1`), fill-in (`B1U01F1`), dictation (`B1U01D1` with English TTS `/api/v1/audio/text`), speaking (`B1U01S1`), reading (`B1U01R1`), summary (`B1U01R2`), topic sentence (`B1U01T1`), and writing (`B1U01W1`, 30–90 words, graded by Gemini at `/api/v1/lessons/1/essays/B1U01W1/checks`).
  - SRS review (`/api/v1/progress/reviews` + `/api/v1/me/review-queue`) schedules B1 cards for the next day (`interval_days: 1.0`) and offers them when due.
  - Daily GCS backup (`python -m app.services.db_backup backup`) writes 57 tables (`backup-ielts/2026-11-10/manifest.json`).
  - Memory after deployment (`free -m`): 3,924 MB total, 1,832 MB used, 2,092 MB available, 49 MB swap (no swap pressure).
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
1. Done 2026-11-10: adapted and deployed to `haru-vm` (`https://ielts.34-9-216-231.sslip.io`).
2. Done 2026-11-10: unit placement checked against the book pages (`scripts/b1/book_units.py`), merged `content/b1-methods` into `feature/b1-boot` & `main` and reloaded B1 seed (1,236 exercises).
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
  (all 1,236 exercises render, no script errors). `load_all()`: 42 lessons, 1,236 exercises, no
  problems.
* 2026-11-10 — adapted backend & frontend for English/IELTS, upgraded VM to `e2-medium` (4 GB RAM), deployed `haru-ielts` stack and `https://ielts.34-9-216-231.sslip.io`, completed mechanical rename (`hangul` → `headword`, `*_ko` → `*_en`, `topik_tip_vi` → `exam_tip_vi`), merged `content/b1-methods` into `feature/b1-boot` & `main`, regenerated B1 seed (42 lessons, 1,236 exercises) and `b1-study.html`, reloaded B1 seed on live VM, full test suite passing.
* 2026-11-10 — fixed lesson lecture audio synthesis for English/IELTS:
  * Hybrid bilingual voicing: English runs voiced by Azure Neural (`en-GB-SoniaNeural`, `SAMPLE_RATE = 24000`), Vietnamese runs voiced by Google Chirp 3 HD (`vi-VN-Chirp3-HD-Iapetus`), with Chirp fallback if Azure fails. Cache keys include `azure_tts.spec()`.
  * Latin language classifier in `lecture_voice.py` (`_split_paragraph_latin`): splits Latin text into English target runs vs Vietnamese explanation runs using syllable structure and clause context; trailing ellipses stripped to '.' for Azure so no end-of-utterance hallucinations while preserving 700ms repeat gap.
  * Formula and notation cleaners in `lesson_audio.py` (`TEMPLATE_VERSION = tpl-v3`): removed 29-second looping glitch by converting table formulas (`+` -> `cộng`, `·` -> `, `, `V-s/es` -> `động từ thêm S hoặc ES`, `V(s/es)` -> `động từ thêm S hoặc ES`, `V3` -> `quá khứ phân từ`, `V-ing` -> `động từ thêm ing`), converted `~~wrong~~ → right` to `không nói wrong, mà nói right`, eliminated duplicate `buổi 1: Buổi 1`, expanded `(v)`, `(n)`, `(adj)`, `(adv)` to full Vietnamese words, and expanded `sb` -> `somebody`, `sth` -> `something`.
  * Added `tests/test_lecture_english.py` (11 tests). Full suite passing (1,479 passed, 176 skipped).
* 2026-11-11 — new frame agreed with the owner: Destination B2's 14 grammar units are the main track, B1 becomes the
  fallback layer behind a gate, vocabulary pairs B2 with a filtered C1&C2 list anchored to simple synonyms, following the
  owner's teacher. `docs/WEEK1_PLAN.md` (Vietnamese) is the design for week 1 (module G1, present tenses + education
  vocabulary): 7-day schedule, card-by-card content, 15 screens, iPhone rules, data changes, and the result of an
  independent UI review. Design only: nothing is built, no practice items or answer keys are written yet. Book page
  numbers in it were checked against scans. Book answer keys and Cambridge texts must stay out of the repository.
* 2026-11-11 — branch `content/g1-week1`: content of G1 days 1–4 (`scripts/g1/`, bank `g1`): 4 lessons, 21 cards,
  37 words, 83 exercises; `load_all()` reports 46 lessons, 1,319 exercises, no problems. Seed tests updated for the
  second bank (46 lessons, 1,097 words; a G1 lesson needs no speaking task). The five tests that need sqlalchemy or
  email-validator could not run in the sandbox. Screens: the new kinds are plain `read_match` / `write_essay` for now
  (see `scripts/g1/README.md`); the frontend can restyle them by id prefix (`G1D?I`, `G1D?T`, `G1D?M`). The book-first
  step is a lesson note plus `scripts/g1/book_tasks.json`; the answer sheet screen (M8) and the gate are not built.
  Merging this branch into `main` makes four G1 lessons appear after the B1 list (sort_order 101–104) at the next deploy.


## 2026-11-11 — book exercises, keys and entry test inside the app (branch `content/g1-week1`)
- Owner's decision: put the books' exercises, answers and explanations into the app (private use, private repo). The earlier rule "no answer keys in the repo" is lifted for the books below; keep the repository private.
- All five books of this week were OCR'd (tesseract, ~1,165 pages); the text is not committed (it is scratch, 3 MB). Exercises were typed from OCR and checked against page images where OCR was unsure.
- `scripts/g1/book_items.py`: Destination B2 Unit 1 exercises A–J (96 items) and IELTS Grammar 6.5+ Unit 1 exercises C1–C4 (33 items), each with the book's answer and a Vietnamese reason. Days: 1 → A, B; 2 → G, F, C1, C2, C3; 3 → C, D; 4 → E, H, I, J, C4. Each day gets "Bài trong sách" sittings of at most ~24 items.
- `scripts/g1/entry_test.py`: the book's 50-item entry test (lesson `g1-entry-test`, sort_order 100) with the unit to study for each wrong answer.
- Seed now: 47 lessons, 0 problems. Five tests still fail only in the sandbox (no sqlalchemy/email_validator).
- Not yet typed in: Grammar 6.5+ Unit 1 listening (needs audio), Unit 3 exercises, B2 Unit 18 and C1&C2 Unit 2 exercises, IELTS Vocabulary 6.5+ units 1/5/21/22, Cambridge 18 Test 1.

## 2026-11-11 (later) — days 5–6, Grammar Unit 3, charts
- Added `scripts/g1/days56.py` + `vocab_day()` in `scripts/g1/build.py`: Day 5 (school, exams, 7 study phrasal verbs) and Day 6 (collocations, word families, 9 C1 anchor words: assess, baffle, plausible, speculate, presume, grasp, notion, dilemma, query) with Destination B2 Unit 18 exercises A–I and the book's key (key p. 244). Day 7 (reading/listening on Cambridge 18) is not written yet.
- Added IELTS Grammar 6.5+ Unit 3 exercises C1 (wrong verbs only), C2 (chart), C3, C4 to Day 3.
- Chart exercises use the seed's native `chart` stimulus (`CHARTS` in `scripts/g1/book_items.py`); the bar values were read from the printed charts and rounded (noted in each chart). Unit 3 C2 item 6: the key was unclear in OCR, so the reason says `caught up with` and the chart shows women still slightly below men.
- Seed: 49 lessons, 388 G1 exercises, 0 problems. Five tests still fail only in the sandbox (no sqlalchemy/email_validator).
- Still not typed: Grammar Unit 1 listening (audio), C1&C2 Unit 2 exercises, IELTS Vocabulary 6.5+ units, Cambridge 18.

## G1 Ngày 7: Destination C1&C2 Unit 2 (Thinking and learning), lớp nâng cấp của B2 Unit 18
- Bài A–O của sách (có đáp án trang 282) nằm trong app, bài `G1D7K…`. Lõi: từ chủ đề, kết hợp từ, biến đổi từ. Cụm động từ và thành ngữ (E, F, G, L) nằm ở buổi riêng "Mở rộng không bắt buộc" theo bộ lọc của thầy (ẩn mặc định được).
- Từ C1 được neo vào từ B2 đồng nghĩa (plausible→reasonable, baffle→confuse, assess→evaluate...).
- Cho agent màn hình: cuối bài từ vựng gộp B2+C1&C2, cho học viên tick 5 đến 10 từ thích nhất và gõ 1 đến 2 câu của riêng mình (thầy nhấn mạnh bước này); buổi "Mở rộng không bắt buộc" cho phép ẩn.
- Nguồn: `scripts/g1/day7.py`; chạy lại `python3 scripts/g1/build.py`. Lesson sort_order 107.

## G1 Ngày 8–9 + kiểm tra tích hợp Ngày 1–7
- Ngày 8 (Complete IELTS 5-6.5 Unit 1): bài đọc "Australian culture and culture shock" (3 + 6 + 7 câu, đáp án sách), problem/trouble, affect/effect, percent/percentage, câu mở đầu Writing Task 1 (gõ từ, không chấm). Chưa có: Listening (cần file âm thanh), Speaking, so sánh tính từ (để dành Unit 11 của B2).
- Ngày 9 (Cambridge IELTS 18 Test 1 Passage 1, "Urban farming"): 13 câu, đáp án trang 120; gõ lại 7 câu điền. Chưa có: Listening Part 1 (script OCR hai cột bị lẫn, cần dựng lại từ ảnh; cần âm thanh).
- Bài đọc nhiều câu dùng `read_passage` (đoạn văn + câu hỏi), đúng/sai/không có thông tin theo thứ tự cố định True, False, Not Given.
- Ngày 5–9 có thêm bài "Câu của tôi" (gõ hai câu của chính mình với từ vừa học), cuối ngày.
- Từ C1 khó chỉ để nhận ra gắn priority `recognize`; ngưỡng core nâng lên 1200.
- Nguồn: `scripts/g1/day89.py`; `python3 scripts/g1/build.py`.
- Ngày 10 (IELTS Vocabulary 6.5+ Unit 1, Human nature): tính từ tính cách (tích cực/tiêu cực, self-/well-, tiền tố phủ định), personality/character/characteristic, bài đọc popular và well-liked (7 câu TFNG), tìm từ đồng nghĩa (paraphrase). Chưa đưa vào: bài nghe và Test practice Part 4 (cần âm thanh). Còn lại của Vocabulary 6.5+: Unit 5, 21, 22 (tuần 1 của thầy có cả ba).

## G1 Ngày 1–7: chuỗi học và tên buổi (sửa theo kiểm tra tích hợp)
- Tên buổi sách giờ nói rõ nó luyện gì: «Luyện theo sách · B2 Unit 1 · Khoanh từ đúng (+1)» (ngày ngữ pháp), «Tiếp nhận / Rèn luyện · …» (ngày từ vựng).
- Ngày 3 đã đúng nguồn: hiện tại hoàn thành nằm ở B2 Unit 1 (bài C, D) cùng Grammar 6.5+ Unit 3. B2 Unit 3 là Past time, thuộc tuần ngữ pháp sau, không đưa vào đây.
- Ngày 5–6 (B2 Unit 18): «Đọc trước B2 · giải nghĩa và liên tưởng» (mỗi từ có dòng «Nhớ: …», file `scripts/g1/assoc.py`) → Tiếp nhận → Vận dụng (câu của tôi) → Rèn luyện → Ôn tập (Ngày 6 ôn từ Ngày 5).
- Chín từ C1 chuyển từ Ngày 6 sang đầu Ngày 7. Ngày 7: Làm quen C1 (28 thẻ, neo vào từ B2) → Tiếp nhận → Vận dụng → Rèn luyện → Ôn tập (từ Ngày 5–6) → Mở rộng không bắt buộc (cụm động từ, thành ngữ).
- Bài ôn tập tự sinh từ câu ví dụ của từ (bỏ từ ra, gõ lại), id `G1D{n}O{ngày}-{k}`. Việc nhắc ôn cách quãng theo lịch vẫn do hệ thống thẻ ôn chung của app; chưa kiểm tra trong repo này.
- Hai file mp3 Cambridge 18 Section 1 (Part 1, Part 2) đã nhận nhưng chưa dùng: app chỉ có audio kiểu `turns` (lời thoại đọc bằng giọng tổng hợp), và môi trường này không có công cụ nhận dạng giọng nói để lấy script.

## G1 Ngày 11: Cambridge IELTS 18 Test 1, Listening Part 1 (Transport survey)
- 10 câu nghe (`G1D11L1`, loại `listen_interview`, lời thoại 41 lượt có nghĩa tiếng Việt) lấy từ script in trong sách (trang 99–100); đáp án khớp bảng đáp án sách (DW30 7YZ, 24th April, dentist, parking, Claxby, late, evening, supermarket, pollution, storage). Gõ lại 10 câu ở bài `G1D11KLT-*`.
- Âm thanh: app đọc lại script bằng giọng tổng hợp. Hai file mp3 Part 1 và Part 2 đã nhận nhưng app chưa phát được file riêng; muốn dùng mp3 gốc cần thêm trường âm thanh cho bài nghe (việc của agent giao diện/backend).
- File phân tích audio của AI khác (mốc thời gian, JSON riêng) chưa dùng: mốc thời gian chưa kiểm chứng; chỉ đối chiếu được độ dài file Part 1 (431,29 giây). Part 2 (câu 11–20) chưa đưa vào; script của sách có sẵn, làm tiếp khi cần.

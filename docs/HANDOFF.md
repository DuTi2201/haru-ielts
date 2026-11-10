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
* Host: upgrade the existing Haru VM (2 vCPU, 2 GB RAM, already swapping) to 4 GB and run a second
  api + worker pair with its own database. Not done yet: it needs a VM restart, so ask for a time.
* Four-skills course books: use both Mindset for IELTS and Complete IELTS Bands 5–6.5.
* Deploy all of Destination B1 at once, with listening, speaking, reading and writing tied to each unit.

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
* Not checked: the full test suite (the sandbox lacked sqlalchemy/httpx). 31 tests of
  `tests/test_lesson_seed.py` fail because they assert Korean content.
* 42 phrasal verbs / prepositional phrases / word patterns / word families are placed in a unit by
  topic and were not found on the unit's pages by either OCR search (84 before a second, looser
  search confirmed 28 and moved 14): `scripts/b1/unit_assignment.json` → `unverified`. Settling the
  rest needs a person with the book. Do not re-run `assign_units.py` without the OCR pages: it
  rewrites that file.
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
2. Check the 84 unverified items and the preposition distractors against the book.
3. Per-unit skills links for B1, still missing: Mindset for IELTS Foundation units, British Council
   B1 listening, longer listening than the two-sentence dictation, a Task 1 chart task. Teacher notes to fold in ("Pre-IELTS thầy Minh"): six-step reading summary by
   keywords, the claim → reason → explanation → evidence paragraph frame, the Task 1 sentence formula.
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

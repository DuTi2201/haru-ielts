# Module G1, week 1 (bank `g1`)

Days 1–4 of the week designed in `docs/WEEK1_PLAN.md`: the four present tenses, taught the way the owner's teacher
teaches them (choose the tense by what the speaker means), on the frame of Destination B2, Unit 1.

| File | Holds |
| --- | --- |
| `days.txt` | per day: book tasks to do first, cards, words, questions, sentences to build, gaps, dictation, own-sentence tasks |
| `build.py` | builds `app/seed/lessons/g1-*.json` and `app/seed/exercises/g1/` with the builders of `scripts/b1/build.py` |
| `book_items.py` | the book exercises typed in from the scans WITH the books' answer keys and a Vietnamese reason per answer: Destination B2 Unit 1 (A–J), IELTS Grammar 6.5+ Unit 1 (C1–C4); ids `G1D{day}K{code}-{n}`, one or more "Bài trong sách" sittings at the end of each day |
| `entry_test.py` | the 50-item entry test of IELTS Grammar 6.5+ with the key and the unit to study for each wrong answer; lesson `g1-entry-test` (sort_order 100), ids `G1E{n}` |
| `book_tasks.json` | generated: the book exercises of each day (book, page, exercise, number of items, minutes) for the "do it in the book" screen |

    python3 scripts/g1/build.py
    python3 -c "from app.services.lesson_seed import load_all; b = load_all(); print(len(b.lessons), b.problems)"

Now: 4 lessons, 21 cards, 37 words, 83 exercises. Exercise ids are `G1D{day}{kind}{n}`:

| Kind | Type in the seed | Screen in the plan |
| --- | --- | --- |
| `I` say what you mean | `read_match`, a Vietnamese situation, 2–3 English sentences | M6 |
| `T` timeline | `read_match`, four timelines drawn in text | M7 |
| `Q` gap choice | `read_cloze` | existing |
| `B` word order, `F` typed gap | `build_order`, `write_fill` | existing |
| `D` dictation | `listen_dictation` | M14, then shadowing |
| `M` my sentences | `write_essay`, 8–40 words | M11 |

Rules kept: the ideas and their order are the teacher's; every sentence, question and explanation is written for this
course. No sentence of the book's exercises is reused, so the app never gives away a book answer before the learner
has done the exercise. The owner decided (2026-11-11) that the books' exercises, keys and notes go into the app: it is private use and the repository is private. Keep the repository private.

Not here yet: the entry test (15 items from the B1 bank), day 4's one-page table as a screen, the G1 test (25 items,
start of day 5), days 5–7, minimal-pair listening items. The lessons have no speaking task on purpose (phase one).
`overview.json` of this bank is a copy of the B1 one and still needs its own text.

# Lesson seed (lesson-v5)

Lessons are **written once, checked by a person, and kept here as JSON**. A model never
generates a lesson from an upload any more. The API loads these files when it starts
(`app/services/lesson_seed.py`), validates them, and writes them to the database.
Editing a file and deploying updates the lesson in place (vocabulary by `hangul`, grammar
by `pattern`), so learners keep their review schedule.

Validate before you commit:

```
python3 -m app.services.lesson_seed --check                 # everything, cross-checked
python3 -m app.services.lesson_seed --check-file app/seed/lessons/xxx.json   # one file
```

(`--file <path>` is accepted too.) No secret ever goes in these files.

```
lessons/<slug>.json        one lesson: vocab, grammar, notes, exercise_ids
exercises/listening.json   {"skill","guide":[...],"items":[...]}   Nghe
exercises/reading.json     same                                     Đọc
exercises/writing.json     same                                     Viết
exercises/speaking.json    same                                     Nói
exercises/overview.json    {"blocks":[GuideBlock], "disclaimer_vi":[str]}
exercises/grammar_links.json  {"links": {"<question id or exercise id>": ["<grammar pattern>", ...]}} — see below
exercises/extension.json   OPTIONAL bank-wide list {"grammar":[{item,used_in,meaning_vi,simpler_vi}], "vocab_note_vi", "vocab_ko":[str]}
                           (both topics now carry their extension items as 🟣 grammar/vocab cards of the lesson that uses them)
```

## Lesson file

```json
{
  "slug": "sinh-hoat-01-buoi-sang",
  "title": "Buổi sáng & Sinh hoạt đầu ngày",
  "title_ko": "아침 및 일과 시작",
  "topic": "Sinh hoạt hàng ngày",
  "track": "intermediate",
  "level": 3,
  "sort_order": 1,
  "summary": "one or two sentences, only what the lesson really contains",
  "vocab":   [ {"hangul","pos":"N|V|A|X","meaning_vi","note_vi?","example_ko?","example_vi?","family?","source?"} ],
  "grammar": [ {"pattern","meaning_vi","usage_context_vi?","contrasts":[{"pattern","diff_vi"}],"note_vi?","topik_tip_vi?","example_ko?","example_vi?","source?"} ],
  "notes":   [ {"title?","body","kind"} ],
  "editor_notes": [ {"title?","body"} ],
  "exercise_ids": ["L12", "R10", "W52", "S1"]
}
```

* `hangul` is unique inside a lesson (merge duplicates into one card); `pattern` too.
* `source` keeps the original citation for audit. It is never shown to the learner and the
  original file says those citations are not yet checked against the books.
* `kind` says what a note is for, and the lesson screen groups notes by it (a lesson with at
  most one `goal`, which comes first): `goal` (the lesson's aims), `language` (sentences and
  review of grammar), `sample` (a model dialogue or reading text), `fact` (life in Korea, for
  context), `writing` (model texts and outlines for Viết 51–54; blanks written as
  `**(㉠ answer)**` are hidden until the learner asks), `pitfall` (typical Vietnamese-speaker
  mistakes). Every note of a lesson carries one.
* **Write for the learner.** Everything outside `source` and `editor_notes` is read by the
  learner (and the lecture reads the notes aloud). Do not write about the making of the
  lesson there: no section numbers of the original notes, no "ghi chép", no grammar codes such
  as G5-4 / SH3, no "giáo viên đọc", "học viên", no first-person "Mình …". A caveat the
  learner should have ("số liệu lấy từ báo, chưa đối chiếu văn bản gốc") is written to the
  learner, in the note it belongs to. What only the maintainer needs (which figures are
  unverified, where a claim came from) goes in `editor_notes`: kept in this file, never
  stored, shown or read out. `tests/test_learner_voice.py` fails on the usual give-aways.
* Several examples for one grammar point: one per line in `example_ko`, and `example_vi`
  has the same number of lines in the same order.

## The topic review lesson (`"kind": "review"`)

The last lesson of a topic closes it ("Ôn tập chủ đề"). It has **no vocabulary, no cards and no notes
of its own**; it reads the topic's. Same slug/topic/bank/track rules as any lesson, `sort_order` after
the topic's other lessons, plus a `review` section:

```json
"kind": "review",
"exercise_ids": ["VL01", "…", "VR16", "VW54", "VS6"],   // 4 listening + 16 reading first (the mock), then one essay and one speak
"review": {
  "functions": [ {"id", "title_vi", "summary_vi", "patterns": [card patterns], "rules": [ {"when_vi", "use": [1–3 patterns, the right one first], "note_vi"} ], "pitfalls_vi": []} ],
  "mock":      {"minutes": 28, "bands": [ {"label_vi", "min_correct"} ]},
  "capstone":  {"essay_id", "speak_id", "min_required": 3, "required": [ {"pattern", "regex", "label_vi"} ]}
}
```

* **Grammar map** (`functions`): the topic's grammar grouped by the job it does in a sentence. Every
  card of the topic is in **exactly one** function; every pattern named in `patterns`/`use`/`required`
  must be a real card of the bank (the loader checks the strings against the lessons).
  A rule is a *decision*: the cue in the sentence that picks one pattern over its look-alikes. Cloze
  cues write the blank as `( )`.
* **Mock** (`Thi thử`): the multiple-choice exercises, in order, no hints, marked after hand-in.
  `bands` are ascending ratios (3급 40% · 4급 50% · 5급 63% · 6급 77%), **approximate, not a TOPIK score**.
  Every function needs ≥ 2 questions and every 🟣 card a question or a capstone requirement.
  Tag each question with the cards it tests in `grammar_links.json` (that feeds the report by pattern
  and the review queue: a wrong answer lapses the linked card). No duplicate `tags` in a question.
* **Capstone**: one Viết 54 (`write_essay`, 600–700 characters of model answer) and one Nói S6
  (`speak`) that must use ≥ `min_required` of the `required` patterns. `regex` runs on the learner's
  text (JS and Python read it alike, no lookbehind): it must match the real forms and not words that
  only look similar (`쓰레기 때문에`, `여기로 한 번`). The loader checks that both model answers meet
  `min_required`.
* A review lesson is not read aloud as a lecture (`POST /lessons/{id}/podcast` answers 404). `/me/plan`
  offers it (`kind: "topic_review"`) once the learner has met every grammar card of the topic, until all
  mock questions are answered.

## Which grammar card a question tests (`grammar_links.json`)

`exercises/grammar_links.json` (and one per bank folder) links questions to the grammar cards they
are built to test. The key is a question id (one question) or an exercise id (every question of it:
the way to link a `write_fill`); the value lists the cards' `pattern` **exactly as the lesson
writes it**, the main card first, at most three. Link only what the question really tests, never
its distractors, and leave out essays/speaking (they are self-marked) and global-comprehension
questions (main idea, order, insert…).

What it does:

* the box "Kiến thức trong câu này" under the answer (meaning, 🟣 mở rộng + 👁/✍ level, the nearest
  look-alike, a way into the card);
* a **wrong** answer to a linked question goes into the error log with that card, and the card
  returns to the learner's review queue (a lapse, see `app/services/srs.py`; once per sitting; a
  card never studied before simply becomes due, it does not use the day's new-card budget);
* the "điểm yếu" report lists the card by name when it keeps going wrong.

`load_all` rejects a link to a pattern that no lesson of the bank has, to a question that does not
exist, or a pattern that two lessons of one bank both write. A card of a *later* lesson (by
`sort_order`) is not offered in an earlier lesson: the learner has not met it, and a wrong answer
must not put an unseen card into their queue.

## Vừa sức / Thử thách, new question types, help before a hard item

```
practice_tiers.json       MADE by `python -m app.services.practice_tiers --build` (needs `pip install kiwipiepy`)
practice_type_tips.json   one line on how to do each type that exams/types.json does not cover
practice_support.json     {"lessons": {slug: {exercise id: help}}}, written by hand
```

* A learner who follows the course has met every earlier lesson's words. An item with at least
  20 content words of which fewer than 85% were met is **Thử thách**: it is shown after the
  other items of its skill (the "Tạo câu" ladder, topic reviews and the alphabet keep their order).
* The first lesson (in course order) that uses a question type shows a one-line "Dạng mới" card.
* `practice_support.json` gives a hard item, **in one lesson**, its words with their meaning in
  that text, the grammar it uses that the learner has not met yet (with the lesson that teaches
  it), and a three-step hint. Every `seen` must appear in the item; checked by `--check`.
* After editing an exercise's Korean text, run `--build` again: `lesson_seed --check` reports
  items whose text changed since the file was made.

## Exercises

Every exercise has a unique `id`; every *question* has an id unique across the whole bank
(learner answers are filed by it). Question ids of a writing fill-in are `"<exercise id>:<blank id>"`.

* `McqExercise` (`skill` listening|reading): `id, skill, type, title_vi, instruction_ko?,
  instruction_vi?, stimulus?, questions[]`. A question: `id, prompt_ko?, prompt_vi?,
  options[{id:"1".."4", text? | scene? | chart?}], answer:"<option id>", explanation_vi, tags[]`.
  * stimulus `kind`: `audio{turns:[{speaker:F|M|N,text}]}` (all listening),
    `cloze{text with "( )"}`, `underline{text with 【…】}`, `notice{title?,lines[]}`,
    `chart{block:DataBlock}`, `order{items:[{id:"가",text}]}`, `headline{text,hint_vi?}`,
    `passage{text}` (`\n` between paragraphs, 【…】 for an underlined part),
    `insert{given, text with (㉠)(㉡)…}`.
  * `Scene`: `{caption_vi, icons:[1-4 names from SCENE_ICONS], image_prompt?}` — a picture
    described in words and drawn from icons for now.
  * `Chart`: `{type: bar|line|pie, title_vi?, unit?, categories[], series:[{name, values[]}]}`.
    `DataBlock`: `{title_vi?, note_vi?, chart | table:{header[], rows[][]}}`.
* `write_fill`: `id, skill:"writing", type:"write_fill", number, title_vi, points,
  instruction_ko?, instruction_vi?, context_vi?, heading_ko?, text with "( ㉠ )", blanks[{id,points,
  accepted[],common_errors_vi?}], tips_vi[]`.
* `write_essay`: `… number, points, limits{min,max}, data[DataBlock], prompt_ko?, bullets_ko[],
  framework_vi[], patterns_vi[], outline[{part_vi,content_vi,chars?}], model_answer_ko,
  model_note_vi?, common_errors_vi[], rubric[{criterion_vi,max,note_vi?}], checklist_vi[]`.
* `speak`: `id, skill:"speaking", type:"speak", number, title_vi, max_points, prep_sec, answer_sec,
  instruction_ko?, prompt_ko, prompt_vi?, situation_vi?, frames[Scene], audio?{kind:"audio",turns}, data[DataBlock],
  plan[{when_vi,do_vi,phrases_ko?}], tips_vi[], patterns_vi[], model_answer_ko, syllables_vi?,
  common_errors_vi[], pronunciation_vi[], practice[{id,label_vi,prompt_ko?,prompt_vi?,hint_vi?,frames[],data[]}]`.
* `GuideBlock`: `{title_vi, body_vi?, bullets_vi[], table?}` — generic advice shown above a skill's items.

The text of every Korean sentence, number and answer is copied from the source documents
exactly; only the structure changes.

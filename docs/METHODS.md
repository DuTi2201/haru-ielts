# Study methods used in Haru English

The learner's Vietnamese teacher ("Pre-IELTS thầy Minh", on the owner's Mac in
`~/Downloads/Pre_IELTS_thầy Minh`) teaches a small set of methods. The course uses the methods;
the wording, examples, passages and questions in the app are written for this course. Nothing from
the teacher's files is copied, and the class files that hold other students' names and answers are
not used at all. His grammar notes (tenses, articles, conditionals) are not a source: several of
their example sentences are wrong, and Destination covers the same ground.

## In the B1 course now

| Method | Where it lives | Exercise |
| --- | --- | --- |
| Reading by keywords, six steps: keywords of each sentence (nouns first) → drop small details → link keywords with arrows → write the summary → name the main idea → say what the paragraph is for | `scripts/b1/methods.txt` (`M:`), `summary_task` in `build.py` | `B1UnnR2`, after the unit's reading: a 10–40 word summary, with a model keyword chain |
| Topic sentence = the idea + what the paragraph will say. Three grades: good; topic only ("for many reasons"); a detail | `methods.txt` (`T:`), `topic_sentence_task` | `B1UnnT1`, before the unit's writing (40 units; units 23 and 34 ask for questions and a message, not a paragraph) |
| Paragraph frame: outline in nouns and arrows first → topic sentence → each next sentence answers "why?" or "how?" about the one before it → one specific example → closing sentence with no new idea | `FRAME` in `build.py` | framework of every `B1UnnW1`; model answers open with the good topic sentence |
| Speaking, four levels of preparation: write full sentences → notes with arrows → no notes → record and correct one thing | plan of `B1UnnS2` | all speaking tasks |
| Part 1: answer in the first sentence, then a reason or a detail, 2–3 sentences | `scripts/b1/speaking_bank.txt` (`P1:`) | `B1UnnS2` in the 14 vocabulary units |
| Part 2: four lines of notes (what → describe → why → my own story: when, what, who, what it meant) | `speaking_bank.txt` (`P2:`) | `B1UnnS3`, 60 s to prepare, 90 s to speak |
| Part 3: opinion → why (ask "why?" twice) → one specific example; talk about people in general first | `speaking_bank.txt` (`P3:`) | `B1UnnS4` |

The three speaking sets of a vocabulary unit are in the lesson's `exercise_ids` but in no sitting,
so a sitting stays about fifteen minutes. The study page lists them as their own block.

## For the B2 course (not built yet)

Writing Task 1 and Task 2 start with Destination B2. Build them from these rules.

### Task 1
* Two families of chart. Static: one point in time, so compare. Dynamic: several points in time, so describe change.
* Four parts: introduction (the question in other words) → overview → two body paragraphs.
* Overview, static chart: the total or the general picture, then the highest and the lowest.
  Overview, dynamic chart: the main trend of each line or group, no figures.
* Body paragraphs: group the data, do not list it. Static: by size (large items, small items).
  Dynamic: by direction (what rose, what fell or stayed level), in time order. The trend words
  belong in the overview; the body gives figures.
* One sentence, six slots, to practise as a drill: (1) measure — "the number of visitors" ·
  (2) what or who — "to museums" · (3) where or when — "in France in 2020" · (4) verb in the right
  tense · (5) comparison or change — "was twice as high as", "rose sharply to" · (6) the other
  item or the figure.
* Change language as two interchangeable patterns: verb + adverb ("rose steadily") and
  there + be / see / experience + adjective + noun ("there was a steady rise", "sales saw a steady rise").
* Exercise forms to build: choose the right overview for a chart; put six tiles in the slot order;
  rewrite verb + adverb as adjective + noun; sort figures into two groups before writing.

### Task 2
* Introduction is two sentences: the question in other words, then the position (thesis). No
  opening sentence about "the modern world": it carries no argument.
* Each body paragraph is one claim, built with the B1 paragraph frame, 90–120 words.
* Outline before writing, in nouns and arrows, one line per paragraph.
* Outlines by question type:
  * Agree or disagree: thesis gives the side → reason 1 → reason 2 (or the other side and why it is weaker) → conclusion.
  * Discuss both views: view A and why people hold it → view B and why → own view in the thesis and the conclusion.
  * Advantages and disadvantages (do they outweigh?): the smaller side first, the heavier side second, and say which is heavier.
  * Positive or negative development: same as agree or disagree, about a change.
  * Two questions (causes and solutions, or why and what): one body paragraph per question, the thesis answers both.
* Exercise forms to build: match a question to its type; choose the thesis that answers the
  question; put outline lines in order; extend a claim by answering "why?" twice; write one body
  paragraph, marked on the four IELTS criteria.

### Speaking question bank
The B1 bank covers the topics of the 14 vocabulary units. For B2 write new sets on the B2 topics
the same way: three Part 1 questions, one card, two Part 3 questions, with one model each.

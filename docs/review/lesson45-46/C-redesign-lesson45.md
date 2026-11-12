# C. Redesign of lesson 45 (G1 Day 2: present continuous and state verbs)

Scope: `scripts/g1/days.txt` lines 150-197 (Day 2), `scripts/g1/lecture_d2.py`, generated `app/seed/lessons/g1-d2-*.json`, `app/seed/exercises/g1/*`. Gold standard: lesson 44 (`days.txt` 26-110, `lecture_d1.py`). Read-only audit; nothing else was edited.

## 0. What the code actually supports (confirmed)

Parser `scripts/g1/build.py:60-95` (card keys: `G:` / ` step:` / ` use:` / ` ex:` / ` quote:` / ` trap:` / ` tip:` / ` vs:`). `use:` is one string, lines separated by a literal `\n`.

Renderer `src/components/lesson/Rich.tsx` `toBlocks()` (lines 129-192):

| Syntax inside `use:` | Renders as |
|---|---|
| `## Title` | section heading |
| `### 1 · Title · English label` then `ex: EN = VI` lines | numbered group with example rows |
| `pat: Label \| a + b + c \| example` | colored formula chips joined by `+`, example under it (Rich.tsx 304-330). Part split is on ` + `. |
| `prep: badge \| label \| examples \| say` | badge tile + two text lines + speaker button. Badge icon only for `@store @bus @school`; any other badge is plain text. |
| `chips: a; b; c` | pill row |
| `tl: when \| tense \| en` | vertical timeline with dots (Rich.tsx 333-350) |
| `ask: question` | question bubble |
| `%90 · words` | percentage bar |
| `> text` | yellow quote box with a big quote mark |
| `!text` | blue callout with warning icon |
| `\| Sai \| Đúng \| Vì sao \|` table | MistakeRows (strike-through wrong, right under it). Other 2-col tables: compact list. 3+ cols: stacked cards on phone. |
| `==x==`, `~~x~~`, `` `x` `` | highlight, strike-through, mono |

Card-level: `ex:` become the "Ví dụ" list (with speaker), `trap:` becomes the red-ish "Lỗi người Việt hay mắc" box (`note_vi`), `tip:` the yellow "Mẹo thi IELTS" box, `vs:` goes inside a folded "WhyBox" ("Khác biệt"), `quote:` is appended by `build.py:196` as a plain line `Trích: «...»`.

Three findings that matter for the redesign:

1. **`step:` is stored (`step_vi`) but no frontend component reads it** (`grep step_vi src` = 0 hits). Day 1's "Cấu tạo" step label is therefore invisible. The visible order is only `usage_context_vi` order. So "formula first" must be done by putting the `pat:` / `prep:` rows first in `use:`.
2. **`quote:` has no styling in the card**: it becomes a plain paragraph starting `Trích: «...»`. `> ...` inside `use:` is the only styled quote. In the lecture, `data.quote` is shown in the footer with the label "Trích dẫn" (`LectureScenes.tsx` Foot, line ~113).
3. **Bug in lecture scene `sentence_forms`** (`LectureScenes.tsx` 495-520): the `persons` tiles do `p.verb.replace(/s$/, "")` and then draw a yellow `s` chip for every tile after the first. Written for present simple. With `lecture_d2.py` persons (`am working / is working / are working`) it would print "is working" + "s" and "are working" + "s". The spelling box is also hard-coded "Thêm s không đơn giản" (wrong for -ing). Both must be fixed before Day 2 uses this scene (see section C).

---

## A. Card-by-card diagnosis of lesson 45 vs lesson 44

Lesson 44 pattern per card: formula rows (`pat:`/`prep:`/chips) -> `!` callout -> 2-3 `ex:` -> `trap:` -> `tip:`. A forgetful beginner can build a sentence from card 1.

| # | Card (days.txt line) | Verdict | What is missing / wrong |
|---|---|---|---|
| 1 | Hai trục · đúng ngữ pháp và hàm ý (L161-164) | **Jargon, teaches nothing** | "Trục 1... Trục 2..." is meta-talk about linguistics. Gives no rule, no formula, no usable choice. Its only valuable content is the pair `lives` vs `is living`. The card is `must` yet nothing in it can be tested; no exercise maps to it cleanly. It also sits before the learner has seen any present continuous sentence. Lecture uses the same words (TWO_AXES) so the jargon repeats. |
| 2 | Present continuous · tạm thời (L165-170) | **Text wall + raw quote + no formula** | Zero build instructions: no am/is/are table, no negative, no question, no short answers. Only a 2-line paragraph and the `quote:` line (L168) which renders as `Trích: «Cái bọn tiếp diễn này luôn luôn...»` in the teacher's spoken register (oral filler "cái bọn"). The formula is only in the card *title* (`am / is / are + V-ing`). The lecture (`sentence_forms`) does teach the formula but the card, which is what the learner reviews, does not. `vs:` exists but is hidden in the folded box. |
| 3 | chữ now và mốc đang diễn ra (L171-174) | **Text wall, no visual** | Two dense paragraphs with the contrast `lives` / `is living` described, not shown. The decision rule (stable / temporary / exact moment) is a sentence, not a 3-row table. Time words (`right now`, `at the moment`, `at 3 o'clock`) are buried in a back-ticked sentence. |
| 4 | xu hướng đang thay đổi (L175-179) | **Mostly fine, thin** | Has examples and a tip. Missing: the verb list learners need (`becoming, getting, rising, increasing, growing, falling`) and the pattern row. "Dùng hiện tại đơn nếu..." is a sentence not a contrast. |
| 5 | always + V-ing để than phiền (L180-184) | **Text wall** | Second paragraph packs 4 rules (usually/often, on Saturdays, every weekend, "tháng này tuần nào cũng") in one block. No formula row (`be + always + V-ing`). |
| 6 | kế hoạch đã lên lịch (L185-188) | **Too thin** | One sentence, no pattern row, no time-word list (`tomorrow`, `on Friday`, `at four`), no warning that a bare future word is needed. |
| 7 | State verbs · sáu nhóm... (L189-193) | **Text wall + book citation + table overload** | Opens "Sách Destination B2 (trang 7) viết:" (L188) (complaint 4). Contains two big tables in one `use:` (6 rows then 5 rows x 3 cols) which stack into 11 cards on a phone. The trap line (L191) has the "Sách nói..." sentence, 3 ideas, 4 struck-through wrong forms in one run. Two different jobs (list of stative verbs; verbs with two meanings) are in one card. |
| - | (absent) | **Missing cards** | -ing spelling rules; time words; common-errors table (Sai/Đúng) like Day 1's "câu hỏi và lỗi thường gặp"; negative/question/short answers. Day 1 has 7 cards, 4 of them formula-led; Day 2 has 0 formula-led. |

Summary: of 7 cards, 0 have `pat:`/`prep:` rows, 0 have `chips:`, 0 have `!` callouts, 1 has a `tl:`-able contrast but described in prose, 1 has a raw teacher quote, 1 cites the book, 2 are jargon/meta. Sentence building is taught only in the lecture slide, not on the card.

---

## B. Proposed card list for Day 2 (10 cards, replaces the 7)

Order = formula -> spelling -> uses -> state verbs -> errors. Session split in `lecture_d2.reshape()` changes from `pats[:4]/[4:]` and `card_of[i] < 4` to `pats[:5]/[5:]` and `card_of[i] < 5` (cards 1-5 = lecture sitting 1; cards 6-10 = sitting 2). The `I:` and `Q:` items carry a card number as last field; renumber with this map (old -> new): old1 (Hai trục) -> 3; old2 (tạm thời) -> 3; old3 (now) -> 4; old4 (xu hướng) -> 5; old5 (always) -> 6; old6 (kế hoạch) -> 7; old7 (state verbs) -> 8 or 9 (items about `think of`/`being`/`see` -> 9; the rest -> 8). Add 2-3 new `I:` items for cards 1, 2, 10 (see end of section).

Notation below: this is the literal `days.txt` text. `\n` is the literal two characters. Pipes inside `pat:`/`prep:` rows are the field separator ` | `.

### Card 1 (must) · formula

```
G: Present continuous · công thức | am / is / are + V-ing: khẳng định, phủ định, câu hỏi, trả lời ngắn | must
 step: Cấu tạo
 use: ## Chọn am / is / are theo chủ ngữ\nprep: am | I | I am working → I'm working | I'm working.\nprep: is | he / she / it | She is working → She's working | She's working.\nprep: are | you / we / they | They are working → They're working | They're working.\n## Ba dạng câu\npat: Khẳng định | chủ ngữ + am / is / are + V-ing | Lan is talking to a customer.\npat: Phủ định | chủ ngữ + am / is / are + not + V-ing | Lan isn't talking to a customer.\npat: Câu hỏi | Am / Is / Are + chủ ngữ + V-ing ? | Is Lan talking to a customer?\npat: Có từ để hỏi | Từ để hỏi + am / is / are + chủ ngữ + V-ing ? | What is Lan doing?\n!Với I chỉ có I'm not working. Không có amn't.\n## Trả lời ngắn dùng lại be\npat: Có | Yes, + chủ ngữ + am / is / are | Yes, she is.\npat: Không | No, + chủ ngữ + isn't / aren't / 'm not | No, she isn't.\n!Chỉ be đổi theo chủ ngữ. V-ing giữ nguyên, không thêm -s.
 ex: Lan is talking to a customer. = Lan đang nói chuyện với khách.
 ex: Are you studying now? = Bây giờ bạn đang học à?
 ex: I'm not drinking coffee this month. = Tháng này tôi không uống cà phê.
 trap: Quên be: ~~She living in Hue~~ → She is living in Hue. Quên đảo be: ~~Where she is going?~~ → Where is she going?
 tip: Speaking Part 1: nói đủ cả am / is / are. Bỏ be là lỗi ngữ pháp rõ nhất của thì này.
```
Why: reproduces Day 1 card 1 structure (`prep` rows per subject, `pat` per sentence type, short answers).

### Card 2 (must) · -ing spelling

```
G: Present continuous · viết V-ing | Thêm -ing đúng chính tả: bỏ e, gấp đôi phụ âm, ie → y | must
 step: Cấu tạo
 use: ## Thêm -ing\nprep: + ing | phần lớn động từ | work → working, play → playing, eat → eating | working, playing\nprep: bỏ e | tận cùng -e | write → writing, make → making, have → having | writing, making\nprep: gấp đôi | 1 nguyên âm + 1 phụ âm, nhấn ở âm cuối | run → running, sit → sitting, begin → beginning | running, sitting\nprep: ie → y | tận cùng -ie | lie → lying, die → dying | lying, dying\nprep: giữ y | tận cùng -y | study → studying, try → trying | studying, trying\n!Không gấp đôi khi nhấn ở âm đầu: visit → visiting, open → opening. Giữ ee: see → seeing, be → being.
 ex: She is writing an email. = Cô ấy đang viết email.
 ex: They are running in the park. = Họ đang chạy trong công viên.
 ex: He is studying at the library. = Anh ấy đang học ở thư viện.
 trap: ~~writeing~~ → writing. ~~runing~~ → running. ~~studing~~ → studying.
 tip: Writing Task 1: rising, increasing, becoming, getting (gấp đôi t trong getting).
```

### Card 3 (must) · one idea: temporary (replaces "Hai trục" + old "tạm thời")

```
G: Present continuous · khi nào dùng: việc tạm thời | Việc đang diễn ra hoặc chỉ kéo dài một thời gian, rồi sẽ hết | must
 step: Khi nào dùng
 use: ask: Việc này có kéo dài mãi không?\ntl: Ổn định | Hiện tại đơn | My sister lives in Thailand.\ntl: Tạm thời, rồi sẽ đổi | Hiện tại tiếp diễn | My sister is living in Thailand.\n!Cả hai câu đều đúng ngữ pháp. Câu bạn chọn quyết định người nghe hiểu gì.\n## Ba kiểu tạm thời\n### 1 · Đang xảy ra · Right now\nex: Lan is talking to a customer. = Lan đang nói chuyện với khách.\n### 2 · Giai đoạn tạm · This week / this month\nex: I'm staying at my aunt's this week. = Tuần này tôi ở nhà dì.\n### 3 · Thói quen chỉ lần này · For a limited time\nex: I'm not drinking coffee this month. = Tháng này tôi không uống cà phê.\n## Từ chỉ thời gian hay đi cùng\nchips: now; right now; at the moment; today; this week; this month; these days; currently
 ex: My sister lives in Thailand. = Chị tôi sống ở Thái Lan. (ổn định)
 ex: My sister is living in Thailand. = Chị tôi đang sống ở Thái Lan. (tạm thời)
 trap: Dùng đơn khi muốn nói tạm thời: câu vẫn đúng, nhưng người nghe không biết là việc tạm.
 tip: Speaking Part 1: dùng this week, these days để cho thấy bạn nói việc tạm.
 vs: Present simple · cách dùng | Hiện tại đơn nêu sự thật ổn định; tiếp diễn báo thêm rằng việc đó tạm thời.
```
Replacement of the teacher quote: the sentence is turned into the `!` callout above ("Tiếp diễn = việc tạm thời...") and the `ask:` bubble. No `quote:` line.

### Card 4 (must) · the "now" trap

```
G: Present continuous · chữ now không quyết định thì | Chọn thì theo điều muốn nói, không theo chữ now | must
 step: Khi nào dùng
 use: ask: Where does your sister live now?\n## Cùng chữ now, hai câu khác nhau\npat: Ổn định | She + lives + in Hanoi + now | She lives in Hanoi now.\npat: Tạm thời | She + is living + in Hanoi + now | She is living in Hanoi now.\npat: Đúng lúc nói | Lan + is talking + right now | Lan is talking to a customer right now.\n!Now ở câu đầu chỉ so với trước kia: trước ở chỗ khác, giờ ở Hà Nội.\n## Đúng một mốc thì dùng tiếp diễn\nchips: right now; at the moment; at 3 o'clock; at this time
 ex: She lives in Hanoi now. = Chị ấy đã chuyển hẳn ra Hà Nội.
 ex: She is living in Hanoi now. = Chị ấy đang ở Hà Nội một thời gian.
 ex: Lan is talking to a customer right now. = Lan đang nói chuyện với khách ngay lúc này.
 trap: Thấy now là chia tiếp diễn ngay. Hỏi mình trước: ổn định, tạm thời, hay đúng một mốc?
```

### Card 5 (must) · trend

```
G: Present continuous · xu hướng đang thay đổi | is becoming, is rising, is getting: việc đang đổi dần | must
 step: Khi nào dùng
 use: ## Đang đổi dần\npat: Xu hướng | chủ ngữ + am / is / are + V-ing + more and more | Online courses are becoming more popular.\npat: Số liệu | the + số liệu + is / are + rising | The price of rice is rising.\nchips: becoming; getting; rising; increasing; growing; falling; changing\n## Đứng yên\npat: Nhận định | chủ ngữ + V (hiện tại đơn) | Online learning saves time.\n!Thay đổi cũng là tạm thời: nó đang trên đường tới trạng thái khác. Hay đi với increasingly, more and more.
 ex: Online courses are becoming more popular in Vietnam. = Các khóa học trực tuyến đang ngày càng phổ biến ở Việt Nam.
 ex: The price of rice is rising. = Giá gạo đang tăng.
 ex: Flights to Da Nang are getting cheaper every year. = Vé bay vào Đà Nẵng ngày càng rẻ.
 trap: Dùng đơn cho thay đổi: ~~The price of rice rises~~ khi muốn nói giá đang tăng → The price of rice is rising.
 tip: Speaking Part 3 và Writing Task 1 khi biểu đồ kéo tới hiện tại.
```

### Card 6 (normal) · always + V-ing

```
G: Present continuous · always + V-ing | be + always + V-ing: thói quen làm người nói bực | normal
 step: Khi nào dùng
 use: pat: Than phiền | chủ ngữ + am / is / are + always + V-ing | My sister is always playing her music so loudly!\npat: Thân mật | chủ ngữ + 're / 's + always + V-ing | You're always leaving the lights on.\n!Có cảm xúc (bực, ngạc nhiên): always + V-ing. Chỉ nêu thói quen: hiện tại đơn.\n## Tiếp diễn không đi với usually, often\n| Sai | Đúng | Vì sao |\n| He is usually having lunch at twelve. | He usually has lunch at twelve. | usually = thói quen, không tạm thời |\n| She is often going to the gym. | She often goes to the gym. | often = thói quen |\n!Có on Saturdays, every weekend: thường là việc lặp lại, dùng hiện tại đơn.
 ex: My sister is always playing her music so loudly! = Chị tôi lúc nào cũng bật nhạc to ơi là to!
 ex: You're always leaving the lights on. = Cậu lúc nào cũng để đèn sáng.
 trap: Dùng always + V-ing để nêu thói quen bình thường: người nghe sẽ hiểu là bạn đang phàn nàn.
```
(The line "Chỉ khi nói một giai đoạn tạm thời (tháng này tuần nào cũng...)" goes to a `tip:` or is dropped: it is a rare case.)

### Card 7 (normal) · arranged future

```
G: Present continuous · kế hoạch đã hẹn | Việc đã hẹn, đã sắp xếp cho tương lai gần | normal
 step: Khi nào dùng
 use: pat: Kế hoạch | chủ ngữ + am / is / are + V-ing + thời điểm | We are flying to Da Nang on Friday.\ntl: Bây giờ | Đã hẹn xong | I'm seeing my tutor tomorrow morning.\nchips: tomorrow; tonight; on Friday; next week; at four\n!Cần một từ chỉ thời điểm tương lai. Không có thì chỉ là việc đang diễn ra.
 ex: I'm seeing my tutor tomorrow morning. = Sáng mai tôi gặp giáo viên hướng dẫn.
 ex: We are flying to Da Nang on Friday. = Thứ Sáu chúng tôi bay vào Đà Nẵng.
 tip: Kế hoạch tương lai nói chung sẽ học ở bài sau.
```

### Card 8 (must) · six groups of state verbs

```
G: State verbs · sáu nhóm không chia tiếp diễn | Động từ chỉ trạng thái dùng hiện tại đơn, kể cả khi việc xảy ra lúc nói | must
 step: Khi nào dùng
 use: ask: Hỏi được "đang làm gì?" thì là hành động. Không hỏi được thì là trạng thái.\nprep: nghĩ | thinking | know, believe, understand, think, mean, imagine | I know the answer.\nprep: tồn tại | existence | be, exist | Dragons don't exist.\nprep: cảm xúc | emotions | like, love, hate, need, want, prefer | I want to finish this page.\nprep: giác quan | senses | hear, see, smell, taste, sound | This soup smells good.\nprep: vẻ ngoài | appearance | look, seem, appear, resemble | He looks tired.\nprep: sở hữu | possession | have, own, belong to, include, consist of | She has dark hair.\n!Hiện tại đơn, không nói: ~~I am knowing~~ → I know. ~~I am wanting~~ → I want.
 ex: Wait! I want to finish this page. = Khoan đã! Tôi muốn đọc xong trang này.
 ex: From the chart, we can see that sales rose. = Nhìn biểu đồ, ta thấy doanh số tăng.
 trap: ~~From the chart we are seeing that~~ → we can see that. ~~She is having dark hair~~ → She has dark hair.
 tip: Trong bài thi và bài viết, giữ hiện tại đơn cho nghĩa trạng thái. Trong hội thoại đời thường có ngoại lệ như I'm feeling happy; đừng bắt chước khi viết.
```
Replacement for the teacher's "thường không dùng, không phải không bao giờ" (complaint 3/4): moved to `tip:` as an exam-safe rule, with no attribution.

### Card 9 (must) · one verb, two meanings

```
G: State verbs · một động từ, hai nghĩa | have, think, see, be: nghĩa trạng thái dùng đơn, nghĩa hành động chia tiếp diễn được | must
 step: Khi nào dùng
 use: ## have\npat: Trạng thái · có | have + danh từ | Do you have your ticket with you?\npat: Hành động · ăn | am / is / are + having + bữa ăn | Are you having lunch at the moment?\n## think\npat: Trạng thái · cho rằng | think + mệnh đề | I think this plan is good.\npat: Hành động · cân nhắc | am / is / are + thinking of + V-ing | I'm thinking of changing my job.\n## see\npat: Trạng thái · hiểu | see + mệnh đề | I see what you mean.\npat: Hành động · hẹn gặp | am / is / are + seeing + người | I'm seeing the dentist at four.\n## be\npat: Trạng thái · tính vốn thế | is + tính từ | He is rude.\npat: Hành động · đang cư xử | is being + tính từ | He's being rude today.\nchips: look → trông / đang tìm; taste → có vị / đang nếm; smell → có mùi / đang ngửi
 ex: I think this plan is good. I'm thinking of changing my job. = Tôi cho rằng kế hoạch này tốt. Tôi đang cân nhắc đổi việc.
 trap: ~~I'm think of changing~~ → I'm thinking of changing. ~~He is being tired~~ (being + tính từ chỉ hành vi: rude, silly, annoying) → He is tired.
 tip: Nghĩa hành động thì chia tiếp diễn được; nghĩa trạng thái thì giữ đơn.
```

### Card 10 (must) · common errors

```
G: Present continuous · lỗi thường gặp | Các lỗi người Việt hay mắc với tiếp diễn và động từ trạng thái | must
 step: Hỏi & đáp
 use: | Sai | Đúng | Vì sao |\n| She living in Hue. | She is living in Hue. | Thiếu be |\n| Where she is going? | Where is she going? | Đảo be lên trước chủ ngữ |\n| He is runing. | He is running. | Gấp đôi n |\n| I am knowing the answer. | I know the answer. | know là trạng thái |\n| We are seeing that sales rose. | We can see that sales rose. | see (nhìn thấy) là giác quan |\n| She is having dark hair. | She has dark hair. | have (có) là sở hữu |\n| He is usually having lunch. | He usually has lunch. | usually = thói quen |\n| It is rise. | It is rising. | Sau be là V-ing |\n!Hiện tại đơn cho thói quen và nghĩa trạng thái. Tiếp diễn cho việc tạm thời và đang đổi.
 ex: She is living in Hue. = Cô ấy đang sống ở Huế.
 ex: I know the answer. = Tôi biết đáp án.
 trap: Học thuộc danh sách rồi cấm tuyệt đối. Hỏi nghĩa của câu trước.
 tip: Rà một lượt bài Writing: be + V-ing có đủ be chưa, động từ trạng thái có bị chia tiếp diễn không.
```

New exercise items required for cards 1, 2, 10 (otherwise their self-check slot is empty): e.g. `Q: Lan ( ) to a customer right now. | is talking | talking | talks | are talking | ...`, `Q: She is ( ) an email. | writing | writeing | writting | writes | ...`, `I:` for the errors card.

---

## C. Lecture scenes (`lecture_d2.py`): clarity and visual replacement

Scene types that exist in `LectureScenes.tsx`: five_boxes, adverb_toggle, truth_cards, tense_timeline, do_does, sentence_forms, speaking_answer, ref_table, fix_pairs. Day 2 uses only ref_table (6 of 9 content scenes), sentence_forms (1), fix_pairs (1). `tense_timeline` is unused though Day 2 is the "time" lesson.

### Sitting 1

| # | Scene | Clear to a beginner? | Replace text with |
|---|---|---|---|
| 1 | title (hook) | Yes. Hook is good ("Hai câu cùng đúng...") but its second line says "hiện tại tiếp diễn theo đúng một ý: tính tạm thời" which is fine. | Keep. |
| 2 | ref_table "Hai trục" (TWO_AXES) | **No.** Jargon "Trục 1/Trục 2", row 1 is an ungrammatical sentence that is not about the tense, rule line is meta ("chọn thì là chọn theo trục 2"). | Rename "Hai câu đúng, hai ý khác". Use `tense_timeline` with 2 lanes: `at:"always"` (bar across now, both directions) for `My sister lives in Thailand.` and `at:"window"` (bracket around now) for `My sister is living in Thailand.` Needs 2 new lane values and a configurable question label (see new-scene list). Rule: "Cùng đúng ngữ pháp. Chọn câu nào là chọn ý người nghe hiểu." Delete `Play I football` row. |
| 3 | word temporary | Yes | Keep. |
| 4 | sentence_forms (formula) | **Content good, rendering buggy.** Persons tiles print "is workings" (bug in section 0). Eyebrow cites "Destination B2 trang 6". Spelling box titled "Thêm s". Persons shown before the sentence, formula `am/is/are + V-ing` appears only in the last `rule` line. | Fix component: persons tiles show `verb` as given, no `s` chip, tile label `I → am`, `he/she/it → is`, `you/we/they → are`; take spelling heading from `data.spelling_title` ("Thêm -ing"). Add a 4th row `Từ để hỏi` (`What is Lan doing?`) and `short` as two chips. Eyebrow: "Công thức". This one scene then mirrors card 1. |
| 5 | ref_table TEMPORARY + `quote` | **Partly.** 3 rows are good but all text; contains the raw teacher quote in footer ("Trích dẫn"). | Make it a three-lane `tense_timeline`: `at:"now"` dot (Lan is talking), `at:"window"` bracket labeled "this week" (aunt's house), `at:"window"` bracket labeled "this month" (coffee). Delete `quote`. Rule line becomes the footer: "Tiếp diễn = việc tạm thời, rồi sẽ hết." |
| 6 | ref_table NOW_TRAP | **Mostly clear.** 4 rows, but row 1 is a question and rows 2-3 differ by one verb form only; learner must read English to see the difference. | `tense_timeline` with question "Where does your sister live now?" and answers: `lives` (`at:"always"`), `is living` (`at:"window"`), `is talking right now` (`at:"now"`). Same pattern Day 1 uses for "Do you believe in God?" so the learner already knows how to read it. |
| 7 | word trend | Yes | Keep. |
| 8 | ref_table TREND | **Clear but flat.** | `tense_timeline` with `at:"slope"` (rising line to now) for the two continuous rows and `at:"always"` for `Online learning saves time.`. Alternatively keep ref_table and add a verb chip row (becoming, rising, getting). |
| 9 | recap / end | Fine | Keep. In `end` line: "Buổi hai nói về than phiền, kế hoạch và động từ trạng thái" is fine. |

### Sitting 2

| # | Scene | Clear? | Replace text with |
|---|---|---|---|
| 1 | title | Yes ("Vì sao I am knowing là sai, mà He is being rude lại đúng?") | Keep. |
| 2 | ref_table ALWAYS | Clear. Three rows with a good contrast. | Keep `ref_table`; add tone dots: red for complaint, amber for friendly, grey for neutral habit (small `tone` field per row; new optional field only). Else keep. |
| 3 | ref_table ARRANGED | Thin: 2 rows, no timeline. | `tense_timeline` with 2 lanes `at:"future"`, tense label "Tiếp diễn + thời điểm". Footer rule unchanged. |
| 4 | word annoying | Yes | Keep. |
| 5 | ref_table SIX_GROUPS + `quote` + opening line | **No.** Eyebrow "Destination B2 · trang 7", narrator says "Sách Destination B2 trang 7 viết...", "Động từ trong sách" column, raw teacher quote ("Thầy nhấn mạnh đúng chỗ này"). Six rows of `en` text where the *verbs* are in bold 14px and the example is in the small `vi` slot (the example sentence is in the wrong visual weight). | New `group_grid` scene (see list): 2 x 3 tiles, each a line icon + group name + verbs as chips + one example. Narration: "Sáu nhóm động từ chỉ trạng thái. Mẹo: hỏi được 'đang làm gì?' thì là hành động." Delete both book mentions and quote. |
| 6 | ref_table TWO_MEANINGS | **No.** 8 rows, mixed state/action in a flat list; the learner has to pair rows 1+2, 3+4 by reading. | New `verb_split` scene: 4 cards, each with the verb and two halves (left "Trạng thái · đơn", right "Hành động · tiếp diễn"), each half = sentence + VI. |
| 7 | fix_pairs STATE_TRAPS | **Clear.** Best scene of the day. | Keep. Add the be-missing and -ing spelling errors from card 10 (6 rows max). |
| 8 | recap / end | Fine | Keep. |

### New scene types / extensions needed

1. `tense_timeline` lane extension (frontend `Lane`): add `at` values `always` (bar through the centre line, extended on both sides), `window` (bracket around the now line with a label from the answer `tense`), `slope` (rising arrow ending at now). Plus optional `data.q_label` for the yellow question box (currently hard-coded "Câu hỏi · hiện tại đơn").
2. `verb_split` (new): `data.pairs: [{key, verb, state:{en,vi}, action:{en,vi}}]`; shows two coloured halves per verb.
3. `group_grid` (new): `data.groups: [{key, name, icon, verbs:[...], en, vi}]`; icon from a fixed set (brain, infinity/exist, heart, ear/eye, glasses, key).
4. Fix `sentence_forms`: persons tile verb as given, no `s` chip; `spelling_title`.

---

## D. Sweep: user-facing strings naming a book, a page, or the teacher

Grep used: `Sách|sách|Destination|IELTS Grammar|trang|tr\.|thầy|Thầy|Minh|Trích|quote`. "Minh" returned no hits in Day 2/3 content. Generated seed JSON repeats everything below, so fixing the sources and re-running `build.py` is enough; do not hand-edit JSON.

### D.1 `scripts/g1/days.txt`

| Line | Text (abbrev.) | Proposed |
|---|---|---|
| 154-156 | `book: Destination B2 \| 7 \| ...` , `\| 10 \| G ...`, `\| 10 \| F ...` | Feed lesson notes and sitting titles. Keep in source data but change the user-visible renderings in `build.py` (see D.3). |
| 165 | `quote: Cái bọn tiếp diễn này luôn luôn...` | Delete the line. Meaning moves into card 3 as `!Tiếp diễn luôn gắn với việc tạm thời: việc đó không kéo dài mãi.` |
| 188 | `use: Sách Destination B2 (trang 7) viết: động từ chỉ trạng thái thường không dùng...` | "Động từ chỉ trạng thái thường không chia tiếp diễn, vì chúng không mô tả hành động. Đi theo nghĩa của câu, không theo danh sách." (or delete, replaced by `ask:` in card 8) |
| 188 | table header `Động từ trong sách` | `Động từ` (or removed with the prep rows) |
| 188 | `Sách thêm: be, have, imagine, look, see, smell, taste, think là trạng thái ở nghĩa này nhưng là hành động ở nghĩa khác.` | "Một số động từ có hai nghĩa: be, have, imagine, look, see, smell, taste, think. Nghĩa trạng thái dùng đơn, nghĩa hành động chia tiếp diễn được." (card 9) |
| 191 | trap `Sách nói "thường không", không phải "không bao giờ": ...` | "Trong bài thi, giữ hiện tại đơn cho nghĩa trạng thái. Đời thường vẫn có ngoại lệ như I'm feeling happy." (as `tip:`) |
| 228-230 | D3 `book:` lines | same as 154-156 |
| 256 | D3 `use: Quy tắc của thầy: chỗ nào dùng được...` | "Mẹo thay thế: chỗ nào dùng được hiện tại hoàn thành tiếp diễn thì thay bằng hiện tại hoàn thành được. Đúng khi câu có khoảng thời gian kéo dài..." |
| 256 | `Sách Destination B2 trang 7 cũng nêu: I have read that book...` | "Nhưng khi nhấn vào quá trình, hai thì khác nghĩa: I have read that book (đã đọc xong) khác I have been reading that book (chưa xong)." |
| 256 | `(sách: thường không dùng với ever, never)` | "(thường không dùng với ever, never)" |
| 257 | `quote: Các bạn lưu ý cho mình là cứ chỗ nào...` | Delete. Same meaning is in line 256 as restated. |
| 259 | `ex: ... (sách B2, trang 7: hai thì khác nghĩa)` | `(hai thì khác nghĩa)` |
| Day 1 (not asked, same defect) | L30 `> Nguồn: Destination B2, tr. 6; IELTS Grammar 6.5+, tr. 2.`; L46 `> «Ngôn ngữ tồn tại ...»` (raw quote) plus `«Ngữ pháp nó không rạch ròi như cái cách mà một quyển sách...»`; L80 `(Destination B2, tr. 6)` | Delete the Nguồn quote box; restate the two quotes: "Ngữ pháp không chia rạch ròi như sách. Người ta nói điều mình nghĩ, nên phần lớn câu nói là sự thật theo cách nhìn của người nói."; delete the parenthesis. Day 1 is the gold standard so fix it too. |

### D.2 Lectures (`scripts/g1/lecture_d2.py`, `lecture_d3.py`)

| File:line | Text | Proposed |
|---|---|---|
| d2:94 | eyebrow `Công thức · Destination B2 trang 6` | `Công thức` |
| d2:116 | `"quote": "Cái bọn tiếp diễn này luôn luôn..."` | remove key |
| d2:124 | `say: "Có một câu đáng nhớ: cái bọn tiếp diễn..."` `show: quote` | "Nhớ một ý: tiếp diễn luôn nói về việc tạm thời, không kéo dài mãi." `show: rule` |
| d2:184 | eyebrow `Destination B2 · trang 7` | `Động từ trạng thái` |
| d2:185 | col `Động từ trong sách` | `Động từ` |
| d2:186 | `"quote": "Sách nó viết rất khéo: are not normally used..."` | remove; rule line already says it |
| d2:188 | `say: "Sách Destination B2 trang 7 viết: ... Sách chia thành sáu nhóm."` | "Động từ chỉ trạng thái thường không chia tiếp diễn, vì chúng không mô tả hành động. Có sáu nhóm." |
| d2:198 | `say: "...sách viết thường không dùng, chứ không viết không bao giờ. Thầy nhấn mạnh đúng chỗ này."` | "Chữ 'thường' quan trọng: đây không phải luật tuyệt đối. Trong thi, giữ hiện tại đơn cho nghĩa trạng thái." |
| d2:187 rule | `Sách viết thường không dùng, không phải không bao giờ. Nhìn vào nghĩa của câu.` | "Thường không dùng, không phải không bao giờ. Nhìn vào nghĩa của câu." |
| d2:204 | `say: "...Sách nêu be, have, imagine, look, see, smell, taste, think. Bốn cặp tiêu biểu."` | "Các động từ be, have, imagine, look, see, smell, taste, think có hai nghĩa. Xem bốn cặp tiêu biểu." |
| d2:1-8 (docstring) | mentions "the teacher", not shown to user | no change |
| d2:5 `TWO_AXES`, d2:20-26, d2:38 | "Trục 1 · ngữ pháp", "Trục 2 · hàm ý" heads and `rule` text | remove with the scene rewrite |
| d3:65 | STATE `why`: `Sách: tiếp diễn thường không dùng với ever và never.` | "Tiếp diễn thường không dùng với ever và never." |
| d3:153 | `say: "Cách nhớ của thầy: đừng học thuộc lý thuyết..."` | "Cách nhớ: đừng học thuộc lý thuyết, hãy nhớ hai câu mẫu rồi suy ra." |
| d3:165 | eyebrow `Quy tắc của thầy` | `Mẹo thay thế` |
| d3:167 | `"quote": "Các bạn lưu ý cho mình là cứ chỗ nào..."` | remove |
| d3:169 | `say: "...thầy nói đúng nguyên văn: các bạn lưu ý..."` | "Có một mẹo rất tiện: chỗ nào dùng được hiện tại hoàn thành tiếp diễn thì thay bằng hiện tại hoàn thành được." |
| d3:183 | rule `Sách Destination B2 trang 7 cũng nêu như vậy.` | delete the sentence |
| d3:184 | `say: "Quy tắc của thầy đúng khi..."` | "Mẹo này đúng khi câu có khoảng thời gian kéo dài..." |
| d3:186 | `say: "...Sách Destination B2 trang 7 có một cặp ví dụ rất rõ."` | "Xem một cặp ví dụ rất rõ." |
| d3:189 | no hit | - |
| d3:196 | `say: "Lỗi thứ hai: sách ghi rằng tiếp diễn thường không dùng với ever và never."` | "Lỗi thứ hai: tiếp diễn thường không dùng với ever và never." |

(`lecture_d1.py` has the same pattern: L75, 77, 79, 89, 100-101, 105, 116, 123, 221, 234, 405. Same replacements.)

### D.3 Generators (these produce the strings in every exercise and note)

| File:line | What it produces | Proposed |
|---|---|---|
| `build.py:196` | appends `Trích: «...»` to every card with a `quote:` | Stop appending. Keep `quote:` parsing only for content that has been restated, or remove the key altogether. |
| `build.py:145, 398` | title `Sách · {title} ({i}/{n})` | `Luyện tập · {title} ({i}/{n})` |
| `build.py:147, 156, 400, 404` | explanation suffix ` [Destination B2, Unit 1 · bài F (trang 10)]` | drop the suffix from `why`/`common_errors_vi`/`explanation_vi`. If the provenance is wanted, keep it in a non-rendered field. |
| `build.py:368, 381` | `explanation_vi` + ` [{source}]` (listening) | same |
| `build.py:254, 453` | lesson note `• Destination B2, trang 7: ...` under title "Bài của sách nằm trong app" | Title "Bài luyện của ngày"; lines "• Đọc bảng động từ trạng thái (khoảng 10 phút)", "• Bài nối câu: 8 câu, khoảng 8 phút". No book or page. Also change the text "Nếu có sách giấy, bạn có thể làm trên sách trước..." to "Làm các bài này sau khi học thẻ." |
| `build.py:199` | `source: "Destination B2 ..., pp. ...; cách giảng của khóa học"` per card | Not rendered for core cards (`source_note_vi` only derives from "Biên soạn bổ sung" lines). Verify in the API response; if shown anywhere, clear it. |
| `build.py:271, 307, 464` | `editor_notes` title "Nguồn" with book names | Verify these are editor-only; if shown to learners, remove. |
| `book_items.py:44, 54, 89` (D2); `100, 112, 121, 135, 152, 162` (D3) | `B2 + " · bài G (trang 9)"`, session title `Luyện theo sách · B2 Unit 1 · Nối để thành câu` | Session titles: `Luyện tập · Nối để thành câu`. Drop the `· bài G (trang 9)` part from anything the learner sees. |
| `book_items.py` (D3 U3C4 instruction) | `Sách đã làm mẫu câu 1: «How long have you been living here?».` (15 items) | `Câu 1 đã làm mẫu: «How long have you been living here?».` |
| `book_items.py` (D3 U3C3 instruction) | `Email của sinh viên Sunita gửi thầy Paul` | Fictional character, fine. Optionally `gửi giảng viên Paul`. |
| `book_items.py` (D3 U3C2) | stimulus note `Số liệu đọc từ biểu đồ cột của sách, làm tròn.` | `Số liệu đọc từ biểu đồ, làm tròn.` |
| exercise rows | `G1D2KF-5` "Sách chấp nhận cả `know` và `see`." | "Cả `know` và `see` đều đúng." |
| exercise rows | `G1D2KC3-1` "(Ví dụ của sách.)" | delete |
| exercise rows | `G1D3KU3C4-2` "Sách chọn tiếp diễn vì nhấn vào hoạt động học." | "Chọn tiếp diễn vì nhấn vào hoạt động học." |

### D.4 Counts in the seed (all follow from the sources above)

Day 2 exercises with a book/page string in title and/or explanation: `G1D2KF` 9, `G1D2KC3` 8, `G1D2KG` 8 (25 total). Day 3: `G1D3KC` 10, `G1D3KD` 10, `G1D3KU3C1` 7, `G1D3KU3C4` 15 (+15 instruction), `G1D3KU3C3` 12, `G1D3KU3C2` 8 (73 total). Lesson JSONs: 22 hits in `g1-d2-*.json`; D3 similar. `Minh` / `thầy Minh` do not appear in Day 2/3 content (only "thầy" as "teacher" and "thầy Paul" as a story character).

---

## E. Wording rules for Vietnamese learners (card, lecture, exercise)

1. **Formula before words.** First visible block of a grammar card is `prep:`/`pat:` rows. No paragraph above it. (`step:` is not rendered, so do not rely on it.)
2. **One idea per line.** Max ~12 words per line. If a sentence has "và"/"nhưng"/"còn" joining two rules, split it into two `!` callouts or two rows.
3. **Show, then tell.** Anything with a contrast (đơn vs tiếp diễn, trạng thái vs hành động, sai vs đúng) is a `tl:`, `pat:` pair, or `| Sai | Đúng |` table. A paragraph may only add a reason, never carry the contrast.
4. **No meta-talk.** Ban: "Trục 1/2", "hàm ý của cấu trúc", "chọn thì là chọn có chủ đích", "bản chất", "Hãy đi theo nghĩa của câu, không theo danh sách" unless it follows a visible example. Say what to do: "Hỏi: việc này có kéo dài mãi không?"
5. **No source talk.** Never write "sách viết", "theo sách", "trang N", "Destination", "thầy", "quy tắc của thầy", "Trích dẫn", "nguyên văn". If a rule is from an authority, state the rule itself. Never print a teacher's spoken sentence; restate it as a rule in neutral written Vietnamese ("Tiếp diễn luôn gắn với việc tạm thời").
6. **Plain verbs, imperative.** "Thêm be", "Bỏ e rồi thêm -ing", "Đảo be lên đầu". Avoid noun-heavy phrases ("việc lựa chọn dạng thức").
7. **Terms: Vietnamese first, English in parentheses once.** "động từ chỉ trạng thái (state verb)". Use the same Vietnamese term every time ("việc tạm thời", not alternately "tạm bợ", "ngắn hạn").
8. **English chunks stay whole and highlighted.** Use `==always==` or backticks, never split a pattern across lines; keep example sentences under 10 words where possible.
9. **Every rule has one example in the same row.** Row = rule + sample + (VI meaning in `ex:`).
10. **Callouts (`!`) are for exceptions and traps only**, max 2 per card, max 1 line each. A `!` that restates the rule is noise.
11. **Traps are written as wrong -> right with a one-clause reason**, using `~~wrong~~ → right`. Max 2 per `trap:`.
12. **Spoken lecture lines**: one sentence per `say`, no filler openers ("Có một câu đáng nhớ:", "Có một chi tiết quan trọng:"); every `say` that introduces a visual has `show:` for that visual.
13. **Scene footer = a rule in 8-14 words.** Never a quote.
14. **Exercise explanations**: "Dấu hiệu -> thì -> vì sao" in one line (`for hours` -> hoàn thành tiếp diễn -> nhấn vào độ dài). No provenance tag at the end.

---

## F. Implementation order (smallest risk first)

1. Fix D.1 / D.2 / D.3 strings (pure text; removes complaints 3 and 4 completely).
2. Replace 7 cards with the 10 cards of section B; update `reshape()` split to 5/5 and renumber `I:`/`Q:` card numbers; add three new `Q:`/`I:` items.
3. Fix `sentence_forms` persons/spelling in `LectureScenes.tsx`, then rewrite Sitting 1 scene 4 data.
4. Add `Lane` values (`always`, `window`, `slope`) and `q_label`, then swap the 4 `ref_table` scenes for `tense_timeline` (complaint 5).
5. Add `verb_split` and `group_grid` scenes for Sitting 2.
6. Regenerate with `build.py`; check that no learner-facing string matches `Sách|Destination|trang \d|thầy|Trích`.

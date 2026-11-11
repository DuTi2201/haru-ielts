# Agent B: Đánh giá UI/UX bài tập (Haru-IELTS)

Phạm vi: đọc code `haru-ielts-journey/src/components/lesson/*` (WriteFill, WriteEssay, McqExercise, BuildOrder, DictationExercise, Disclosure, ExerciseView, PracticePanel), kiểu `src/lib/api/types.ts` (dòng 566-700), dữ liệu `haru-ielts/app/seed/exercises/g1/{build,reading,writing,listening}.json` và bộ sinh `scripts/g1/{build.py,book_items.py}`. Không sửa code.

## 0. Kết luận một đoạn

Người học không hiểu vì CẢ HAI nguyên nhân, và dữ liệu là nguyên nhân nặng hơn:

1. DỮ LIỆU THIẾU mà UI không có chỗ hiển thị: bài "Sửa cho đúng" không lưu câu gốc sai (`book_items.py` dòng 33-42 chỉ lưu `text` đã thay phần sai bằng `( ㉠ )` + đáp án). Vì vậy ảnh (2) không thể hiện phần in đậm: không có gì để hiện. Tương tự không có `bank[]` (ảnh 3: danh sách từ bị nhét vào `instruction_vi`, 15 câu lặp lại cùng một đoạn), không có `answer_kind`, không có `hint` riêng (gợi ý "(work)" chỉ là chữ nằm trong `text`), không có `frames[]` cho bài viết.
2. TRÌNH BÀY sai ưu tiên: mọi dạng dùng chung một "header" kiểu Hàn-TOPIK (sao chép từ app Haru-Korea): dòng tiêu đề chính là nhãn uppercase 12px xanh, nhiệm vụ thật nằm ở dòng xám 12px bên dưới, toàn bộ chữ `font-semibold` nên không có phân cấp.
3. Lỗi kế thừa từ bản TOPIK: `BLANK = /\(\s*([㉠㉡㉢㉣㉤])\s*\)/` (WriteFill.tsx:11) và hộp vàng hiển thị chính ký tự `㉠` (dòng 123-129). Font `font-korean` hoặc font dự phòng trên điện thoại vẽ `㉠` thành "ⓣ". Với người Việt học IELTS, ký tự này vô nghĩa.

Phần lớn cải thiện P0 chỉ cần sửa component (không đụng dữ liệu); riêng "hiện câu gốc sai" và "ngân hàng từ" cần thêm trường dữ liệu.

## 1. Hiện trạng chung (khung chung của mọi dạng)

Cấu trúc lặp ở WriteFill.tsx:92-117, WriteEssay.tsx:80-98, McqExercise.tsx:~385-400, BuildOrder.tsx:67-79, DictationExercise.tsx:75-86:

```
<p text-[12px] font-semibold uppercase tracking-wide text-blue-deep>  {title_vi} · {points} điểm
<p lang=ko font-korean 13px semibold>  instruction_en        (hầu như không có ở IELTS)
<p text-xs font-semibold text-ink-2>   instruction_vi        (12px, xám)
```

Vấn đề cụ thể:
- Tiêu đề chính = nhãn kiểu loại bài ("GÕ DẠNG ĐÚNG · NGÀY 1 · 3 ĐIỂM"). Mắt đọc nhãn trước, bỏ qua dòng xám nhỏ chứa nhiệm vụ. `uppercase` còn làm chữ có dấu tiếng Việt khó đọc.
- Nhiệm vụ ở `text-xs` (12px) `text-ink-2`: chữ chính của bài lại là chữ yếu nhất trang. Bắt đầu 12px là sàn của repo ("min 12px text" theo commit 96d530e) nhưng hướng dẫn phải là 14-15px.
- `font-semibold` ở khắp nơi (nhãn, mô tả, câu hỏi, nút) khiến mọi thứ "to ngang nhau".
- Điểm số "· 3 điểm" hiện ở header (WriteFill:93) rồi lại hiện ở từng ô nhập (dòng 143: `ⓣ · 3 điểm`). Bài tự học: điểm của câu 1 ô là nhiễu. Thông tin quan trọng hơn (câu số mấy/tổng) lại bị nhét trong tiêu đề `(1/8)` do `build.py:142` (`ttl = f"Sách · {title} ({i}/{len(lines)})"`).
- Thiếu thanh tiến độ cho BỘ bài: `PracticePanel.tsx:394` có `progress` tổng cả bài (Đã làm x/y câu) nhưng ở trên cùng, không dính vào từng thẻ; trong bộ 15 câu cùng dạng, người học không thấy "2/15" dạng trực quan, và phải lặp đọc lại hướng dẫn ở mỗi thẻ.
- `instruction_vi` lặp nguyên văn ở từng thẻ trong bộ (`book_items.py` dòng 33, 385...: một chuỗi cho cả section, gán vào từng câu ở `build.py:~150: ex["instruction_vi"] = instr`). 15 thẻ = 15 lần cùng một đoạn.
- Placeholder: WriteFill.tsx:~148 `exercise.rung === 2 ? "Điền dạng đúng…" : "Viết một câu hoàn chỉnh…"`: mọi bài write_fill build đều rung 2 nên chỉ có một câu cho "điền từ", "sửa lỗi", "chia động từ", "điền cả cụm". Placeholder biến mất khi gõ nên không giúp gì.
- Nút chính: `bg-blue ... disabled:opacity-50` (WriteFill:~239): khi chưa gõ, nút thành tím nhạt, trông như đã hỏng chứ không phải "gõ vào để mở khóa". Không có lời giải thích vì sao khóa.
- Hit-area: `hit-area` chỉ mở rộng 7px dọc (styles.css:585), chip và nút phụ `min-h-9` (36px) dưới 44px cho nút "Viết lại", "Bỏ mảnh cuối", "Làm lại".

## 2. Đánh giá theo từng dạng bài

Ký hiệu: [TB] = lỗi trình bày (sửa component được); [DL] = dữ liệu thiếu (cần backend/seed).

### 2.1 Chọn đáp án cloze (`read_cloze`, McqExercise + StimulusView `cloze`)
(a) Thấy gì: nhãn xanh "CHỌN DẠNG ĐÚNG · NGÀY 1" -> dòng xám "Chọn phương án đúng cho chỗ trống." -> thẻ câu `Water ( ) at 100 degrees Celsius.` với `Gap` gạch dưới (McqExercise:27-39) -> 4 nút radio tròn ①②③④.
(b) Dạng này RÕ NHẤT trong app: chỗ trống đã là ô gạch dưới, đáp án là nút to. Tuy vậy:
(c) [TB] Nhãn uppercase vẫn là tiêu đề; không có câu mệnh lệnh nổi. [TB] `Gap` min-w 3.6em, không báo "bạn đang chọn cho chỗ này": khi chọn xong, chữ mới điền vào chỗ trống (tốt), nhưng trước khi chọn người học không thấy mối liên hệ ①②③④ <-> chỗ trống. [TB] Không có "Câu 3/15" trong thẻ. [TB] `read_match` ("Nói đúng ý") dùng `prompt_vi` xám 12px (dòng ~Question) làm tình huống, là thông tin cần đọc nhất nhưng bị làm nhỏ nhất. Đề xuất: tình huống thành khối trích dẫn 15px.

### 2.2 Điền chỗ trống gõ (`write_fill`, "Gõ dạng đúng · Ngày 1", ảnh 1)
(a) Mắt đọc: nhãn xanh -> dòng xám "Gõ từ hoặc cụm từ còn thiếu." -> thẻ trắng với ô vàng `ⓣ` + "your sister live near here?" -> dòng "ⓣ · 3 điểm" -> ô nhập -> nút mờ.
(b) Người học không biết: ô vàng là gì, "ⓣ" là gì, phải gõ gì (một từ? động từ chia?), ô nhập ứng với chỗ trống nào, gõ bao nhiêu từ, vì sao nút mờ. Dữ liệu thật là `( ㉠ ) your sister live near here?` đáp án `Does`: ô vàng thay đúng chỗ trống nhưng chữ bên trong là ký tự `㉠` (WriteFill.tsx:124-128 render `{p}` là nhóm bắt được).
(c) Cụ thể:
- [TB P0] Ô vàng chứa glyph `㉠` (hiện là "ⓣ" khi thiếu font). Đổi thành ô gạch dưới nội tuyến (hoặc chính ô nhập nội tuyến khi chỉ có 1 chỗ trống).
- [TB P0] Dòng nhãn ô nhập (`ⓣ · 3 điểm`, dòng 138-146) lặp điểm và lặp ký hiệu. Với bài 1 ô trống: bỏ nhãn hẳn; ô nhập đã có `aria-label` là đủ.
- [TB P0] Placeholder chung "Điền dạng đúng…".
- [TB P1] Ô nhập `w-full min-h-11` dài hết thẻ dù đáp án là 1 từ (`Does`): gợi ý sai rằng cần viết cả câu. Cần độ rộng theo độ dài đáp án (`ch` = độ dài đáp án dài nhất + 2).
- [TB P1] Khi `accepted` có nhiều đáp án không ghi rõ số từ ("one word" vs "đầy đủ cả trợ động từ").
- [DL] Không có `task_vi` ngắn/`answer_kind` (một từ, dạng của động từ trong ngoặc, cụm từ). 381 item write_fill đều chỉ có `instruction_vi` dài/lặp.
- [DL] Gợi ý trong ngoặc (66/381 item có dạng `( ㉠ ) (work)`) là chữ thường trong `text`, không nổi bật.
- Sau chấm (dòng 160-208): phản hồi tốt (xanh/đỏ, đáp án chấp nhận, "Lỗi hay gặp", nút "Câu của tôi cũng đúng"), nhưng cụm "Chưa khớp đáp án" nghe như lỗi máy; nên "Chưa đúng" + hiện đáp án đầu tiên đậm.

### 2.3 Sửa lỗi (gõ lại) (`write_fill` Sách "Sửa cho đúng (gõ lại)", ảnh 2)
(a) Thấy: "SÁCH · SỬA CHO ĐÚNG (GÕ LẠI) (1/8) · 3 ĐIỂM" / "Câu gốc đang sai ở phần in đậm. Gõ phần thay thế đúng..." / `My dad [ô vàng] late on Saturday mornings.`
(b) Đây là lỗi DỮ LIỆU: hướng dẫn nói về "phần in đậm" nhưng không có phần in đậm nào. Trong scan sách, câu gốc là kiểu "My dad **is often getting up** late on Saturday mornings."; seed chỉ giữ phần đã sửa. UI không có trường nào để hiện nó (WriteFillOut không có `original`, types.ts:601-617).
(c) Hệ quả nghiêm trọng: người học không thể "sửa" cái họ không nhìn thấy; họ chỉ thấy một câu thiếu động từ, tức là bài điền từ không có gợi ý (động từ gì? dạng nào?). Đây là nguyên nhân chính của "đọc đề mà không hiểu phải làm gì".
- [DL P0] Thêm `original` (câu gốc sai, có đánh dấu phần sai) và nguồn: lấy từ scan (bộ nhập `book_items.py` format `text | accepted | tip` cần thêm một cột `original`).
- [TB P0] Hiện `original` bằng gạch ngang đỏ phần sai, kèm câu "Sửa phần gạch ngang" làm nhiệm vụ.
- [TB P1, nếu chưa có `original`] Fallback: đổi lời nhiệm vụ thành "Điền cụm từ còn thiếu cho đúng nghĩa" (đừng nói "phần in đậm"). Hoặc giấu hẳn phần "Câu gốc đang sai ở phần in đậm" khi dữ liệu không có.
- Cách làm ("hỏi trước 'người nói muốn nói gì?'") là lời khuyên chung nhét vào mô tả của từng thẻ; nên chuyển thành 1 hộp "Cách làm" thu gọn ở đầu bộ.

### 2.4 Viết lại câu (rewrite)
Seed g1 hiện KHÔNG có dạng rewrite riêng (kiểm tra `type`: chỉ `write_fill`, `build_order`, `read_*`, `listen_*`, `write_essay`). Các câu "nối hai vế" (rung 3, types.ts:603 "join two sentences") dùng cùng `WriteFill`. Khi có, cần: hiện câu gốc + từ bắt buộc (key word) + ô nhập rộng 1-2 dòng; đừng dùng chung placeholder.

### 2.5 Điền từ trong khung / Mỗi chỗ trống một từ (ảnh 3, `write_fill` Sách "Mỗi chỗ trống một từ: cách nói thời gian (1/15)")
(a) Thấy: hướng dẫn dài "Gõ đúng một từ cho mỗi chỗ trống. Đây là bài về cách nói tần suất và thời điểm: always, present, moment, being, rarely, every, never, time, right, days…" -> câu `Fifteen teachers are teaching here full-time at ( ㉠ ).` (đáp án `present`/`the moment`).
(b) Lỗi DỮ LIỆU + TRÌNH BÀY: danh sách từ là ngân hàng từ nhưng bị gói thành chuỗi trong `instruction_vi`, bị cắt bằng "…" (do tác giả seed `book_items.py:385`), lặp ở cả 15 thẻ, ở chữ 12px xám. Ngân hàng không tương tác: người học phải gõ lại từng từ.
(c) 
- [DL P0] `bank: string[]` riêng; `bank_scope: "set"` (cả bộ dùng chung) hoặc theo câu (như bài A18: nhóm câu có khung riêng ở `book_items.py:236`).
- [TB P0] Hiện bank dạng chip bấm để điền (nếu `bank` có), có chip "đã dùng" mờ đi.
- [TB P1] Fallback khi chưa có `bank`: tách chữ in sau dấu ":" trong `instruction_vi` bằng regex (`/:\s*([a-z'’ ,/-]+)(?:…|\.)$/i`) chỉ là vá tạm; tốt hơn ẩn hoàn toàn cụm đó và dùng nút "Xem gợi ý" (Disclosure).
- Hiện "một từ" bằng độ rộng ô gạch dưới ngắn; nếu đáp án nhiều từ (`the moment`) chip `answer_kind: "phrase"` đổi lời nhiệm vụ thành "Điền một cụm".

### 2.6 Chia động từ trong ngoặc (`write_fill`, ví dụ `My brother ( ㉠ ) (work) in a bank.` đáp án `works`)
(a) Thấy: ô vàng `ⓣ` rồi chữ `(work)`. (b) [TB] Không biết `(work)` là động từ phải chia (không có nhãn); người mới tưởng đó là chú thích. (c) Gợi ý trong ngoặc phải tách khỏi câu: `answer_kind: "inflect"`, `hint: "work"`; UI hiện chip "Chia động từ: work" ngay trên câu và ô gạch dưới giữa câu; phần `(work)` hiển thị như nhãn nhỏ bên cạnh ô, không phải chữ thường. Nhiệm vụ: "Chia động từ (work)". Nếu chưa có `hint`: regex `\)\s*\(([a-z' ]+)\)` bắt `(work)` ngay sau `( ㉠ )` (66 item có dạng này, dễ làm).

### 2.7 Xếp câu (`build_order`, BuildOrder.tsx)
(a) Thấy: nhãn "XẾP CÂU · NGÀY 1" -> xám "Chạm vào các mảnh theo đúng thứ tự…" -> hộp vàng "Hãy nói: Tôi thích ăn cam." -> khay đích nét đứt "Chạm vào các mảnh bên dưới…" -> các mảnh -> "Bỏ mảnh cuối" / "Kiểm tra".
(b) Dạng này dễ hiểu nhất sau cloze: cơ chế chạm có phản hồi trực quan, đích rõ, nghĩa tiếng Việt nổi bật. Điểm yếu nhỏ:
(c) [TB] Nhiệm vụ vẫn là dòng xám; "Hãy nói:" nên là tiêu đề chính cỡ 16px. [TB] Nút "Kiểm tra" `disabled:opacity-50` giống WriteFill; nên "Kiểm tra" luôn rõ hoặc ẩn đến khi có >=1 mảnh. [TB] Mảnh `min-h-11` đủ 44px, tốt; "Bỏ mảnh cuối" 36px (dưới chuẩn). [TB] Dòng "Đã dùng hết các mảnh — bấm “Kiểm tra”…" chữ xám nhỏ, nên chuyển sang nhấn nút chính. [Tốt] Phát âm câu đúng (`audio.play`).

### 2.8 Nghe chép (`listen_dictation`, DictationExercise.tsx)
(a) Thấy: nhãn + xám -> trình phát âm thanh -> danh sách "Câu 1 [F]" + textarea 2 dòng placeholder "Gõ những gì bạn nghe được…".
(b) Dễ hiểu nhờ đúng một hành động. Vấn đề: `lang="ko"` trên textarea (dòng ~125) khiến bàn phím/spellcheck và trình đọc màn hình hiểu nhầm là tiếng Hàn (phải `lang="en"`); `spellCheck=false` là hợp lý. Nhãn "Câu 1 [F]" (giới tính người nói) thừa với người học. "Nghe lại bao nhiêu lần cũng được" nằm trong đoạn xám dài. [TB] Nút "Kiểm tra" disabled mờ như trên. [TB] Chip "Khớp 85%" là phản hồi tốt.

### 2.9 Viết đoạn (`write_essay`, "Câu của tôi · Ngày 1", ảnh 4, WriteEssay.tsx)
(a) Thấy: nhãn tím/xanh "CÂU CỦA TÔI · NGÀY 1 · 5 ĐIỂM" -> hướng dẫn xám 3 dòng -> thẻ đề `Answer in two different tenses: Do you like your hometown?` -> HỘP MỞ SẴN "Khung bài viết gợi ý" (3 gạch đầu dòng chung) -> "Bài viết của bạn" -> textarea `rows={9}` -> "0 từ · yêu cầu 8–40 · Chưa viết" -> nút "Nhờ Haru chấm và sửa bài" -> nút "Tự chấm".
(b) Mắt đọc theo thứ tự: nhãn, xám, ĐỀ BÀI (đúng thứ tự cần), nhưng chiếm màn hình bởi khung gợi ý và textarea lớn; đề yêu cầu 8-40 từ (2 câu) mà ô viết cao 9 dòng (~250px) gợi ý viết cả bài. Đề bài (`prompt_en`) là thứ quan trọng nhất mà không nổi bật hơn nhãn.
(c) Cụ thể:
- [DL] `framework_vi` của cả 13 đề Ngày 1-11 là **cùng một khung 3 dòng** (kiểm tra `writing.json`: 13/13 item có `framework_vi` với 3 phần tử; D1M1 = "Nghĩ điều bạn muốn nói trước…/Tự hỏi: việc đó nằm ở đâu trên trục thời gian?/Chọn thì theo câu trả lời đó…"). Không có `patterns_vi`, `detectors`, `outline` (đều null). Không có gì cụ thể cho từng đề -> người học nói "vô giá trị" là đúng.
- [TB P0] `<Disclosure title="Khung bài viết gợi ý">` ở WriteEssay.tsx mặc định đóng (`defaultOpen=false`) theo code; nếu người học thấy mở sẵn, kiểm tra phiên bản triển khai: dù mở hay đóng, nội dung chung chung phải thay bằng sentence frames.
- [TB P0] `rows={9}` cố định cho mọi đề (dòng 174): đặt `rows` theo `limits.max` (<=50 từ: 4 dòng; tự tăng theo nội dung, `field-sizing: content` hoặc auto-resize).
- [TB P0] Placeholder `Write your paragraph in English…` nhắc "paragraph" trong khi đề là 2 câu. Nên theo đề: "Viết câu 1 (hiện tại đơn)…".
- [TB P1] Đếm từ chỉ có chữ (dòng ~189) "0 từ · yêu cầu 8–40 · Chưa viết": thêm thanh đếm trực quan (vạch min-max) và màu theo trạng thái; hiện đã có icon `CheckCircle2/AlertCircle` nhưng không có thanh.
- [TB P1] `checklist_vi` (3 ý/đề, có sẵn) chỉ hiện SAU khi bấm "Xem bài mẫu" (dòng ~253-286, trong `revealed`); đúng chỗ nó có giá trị nhất là NGAY lúc đang viết. Đưa lên cạnh ô viết, tick tay hoặc tự động (xem §3.9).
- [TB P1] Hai nút ngang hàng ("Nhờ Haru chấm" và "Xem bài mẫu & tự chấm") đều full-width, không ưu tiên; nên chỉ "Nhờ Haru chấm" là nút chính, "Xem bài mẫu" là link phụ.
- [TB P2] Tiêu đề "5 ĐIỂM" cho bài tự luyện.

## 3. Thiết kế lại theo từng dạng

### 3.0 Khung chung `ExerciseShell` (một lần, dùng cho mọi dạng)

Quy tắc:
1. Dòng đầu: chip loại việc nhỏ + số thứ tự "3/15" + (tùy chọn) thanh tiến độ mảnh của BỘ. Một chỗ duy nhất.
2. Dòng 2: NHIỆM VỤ 1 câu mệnh lệnh in đậm 17px/600 (`text-[17px] font-semibold text-ink leading-6`), không uppercase, không màu xanh.
3. Dòng 3 (tùy chọn): gợi ý/ngữ cảnh 14px `text-ink-2`, tối đa 2 dòng; phần dài vào `Disclosure "Cách làm"` ở đầu bộ, hiện 1 lần.
4. Điểm: bỏ khỏi thẻ; chỉ tổng điểm ở màn hình kết quả. Nếu cần: chip "3 đ" nhỏ ở góc phải dòng 1.
5. Nút chính: một nút `bg-blue text-white` luôn đủ tương phản. Khi chưa sẵn sàng dùng `aria-disabled` + nền `bg-progress text-ink-2` (không dùng `opacity-50`) + dòng "Gõ đáp án để chấm".

```
┌──────────────────────────────────────────┐
│ [Sửa lỗi]  ● ● ○ ○ ○ ○ ○ ○   3/8      3 đ │  <- chip loại, tiến độ, điểm nhỏ
│ **Sửa phần gạch ngang**                   │  <- nhiệm vụ 1 câu, đậm
│ Hỏi: người nói muốn nói gì?    [Cách làm] │  <- gợi ý 1 dòng
└──────────────────────────────────────────┘
```

### 3.1 Chọn đáp án cloze
```
[Chọn 1] 4/15
**Chọn từ đúng cho chỗ trống**
Water ____ at 100 degrees Celsius.
( ) boils   ( ) is boiling   ( ) boil   ( ) has boiled
```
Quy tắc: giữ `Gap`, tăng cỡ chữ câu lên 17px; chỗ trống sáng viền xanh khi chưa chọn; sau khi chọn gạch dưới nhận chữ đã chọn (đã có). Nút đáp án: giữ nút radio; `min-h-12`.

### 3.2 Điền chỗ trống gõ (1 từ)
```
[Điền 1 từ]  2/15
**Điền một từ**
┌ ______ ┐ your sister live near here?     <- ô nhập NỘI TUYẾN, rộng ~ 6 ký tự
Gợi ý: ngôi thứ ba số ít                     <- chỉ khi có hint_vi
[        Chấm bài        ]
```
Quy tắc: nếu 1 chỗ trống: input nằm TRONG câu (`<input style={{width:`${n}ch`}}>`, `n = max(len(accepted))+2`, tối thiểu 4ch). 2+ chỗ trống: các ô nội tuyến đánh số nhỏ 1,2 và Tab nhảy theo thứ tự. Bỏ `㉠`/ô vàng; dùng `border-b-2 border-blue` + nền `bg-blue-soft` khi focus.
Placeholder: trống (không dùng placeholder cho ô nội tuyến); dùng `aria-label="Chỗ trống 1 trong câu: …"`.

### 3.3 Sửa lỗi
```
[Sửa lỗi]  3/8
**Sửa phần gạch ngang**
  ✗  My dad ~~is often getting up~~ late on Saturday mornings.
  ✓  My dad [ ____________ ] late on Saturday mornings.
Gợi ý: thói quen hay việc đang xảy ra?
```
Quy tắc: câu gốc sai ở trên (đỏ nhạt `bg-danger-soft`, phần sai `line-through decoration-danger`), câu cần điền ở dưới. Ô nhập rộng theo đáp án (`often gets up` = 13 ký tự -> 15ch). Nếu thiếu `original`: ẩn dòng ✗ và đổi nhiệm vụ thành "Điền cụm còn thiếu cho đúng" (xem §4).

### 3.4 Viết lại câu
```
[Viết lại]  1/6
**Viết lại câu, giữ nguyên nghĩa**
Câu gốc:  "I started learning English five years ago."
Dùng từ:  [for]
______________________________________  I have been learning English ____ .
```
Quy tắc: câu gốc ở khối riêng; từ bắt buộc là chip đậm; ô nhập 1-2 dòng tự giãn.

### 3.5 Điền từ trong khung (ngân hàng từ)
```
[Điền 1 từ]  3/15
**Điền một từ trong khung**
┌ always │ present │ moment │ being │ rarely │ every ┐   <- chip bấm, `min-h-11`
Fifteen teachers are teaching here full-time at [ ______ ].
```
Quy tắc: bấm chip -> điền vào ô trống đang focus (hoặc ô trống đầu tiên chưa điền); chip đã dùng mờ `opacity-40` nhưng vẫn gỡ được; vẫn cho gõ tay (`inputMode="text"`). Ngân hàng dùng chung cho cả bộ -> hiện sticky ở đầu bộ chứ không lặp ở mỗi thẻ (chip "Ngân hàng từ" thu gọn trên điện thoại).

### 3.6 Chia động từ trong ngoặc
```
[Chia động từ]  5/16
**Chia động từ (work)**
My brother [ ______ ] in a bank.
```
Quy tắc: `hint` (động từ nguyên thể) là chip đậm nằm trên câu và ngay cạnh ô: `(work)` hiển thị `font-semibold text-blue-deep bg-blue-soft rounded px-1.5`. Nhiệm vụ lấy từ `answer_kind: "inflect"` -> câu mệnh lệnh "Chia động từ (work)".

### 3.7 Xếp câu
```
[Xếp câu]  2/8
**Xếp thành câu: "Tôi thích ăn cam."**           <- meaning_vi thành nhiệm vụ
┌ I  enjoy  eating  oranges ┐   <- khay đích, đánh số dần
 [oranges] [eating] [I] [enjoy]    <- mảnh còn lại
[Hoàn tác]            [ Kiểm tra ]
```
Quy tắc: `meaning_vi` là dòng nhiệm vụ đậm; "Kiểm tra" luôn đủ tương phản (cùng quy tắc nút), "Hoàn tác" `min-h-11`.

### 3.8 Nghe chép
```
[Nghe chép]  1/3
**Nghe rồi gõ lại câu bạn nghe**
[▶ Nghe]  [🐢 Chậm]    Nghe bao nhiêu lần tùy ý
Câu 1: [ ______________________________ ]
```
Quy tắc: `lang="en"` cho textarea; bỏ nhãn người nói; textarea 1 dòng cho câu <=10 từ (`rows={1}` tự giãn).

### 3.9 Viết đoạn (Câu của tôi)
```
[Viết 2 câu]  8-40 từ                                
**Trả lời bằng 2 câu ở 2 thì khác nhau**         <- nhiệm vụ đậm
┌─ Do you like your hometown? ────────────────┐   <- đề bài trong khối nổi
└────────────────────────────────────────────┘
Khung câu (bấm để chèn):                          <- chip từ frames[]
 [ Yes, I do. I ____ ]  [ I have lived … since ____ ]  [ I'm living … at the moment ]
[ Công cụ ▾ ]  mẫu câu hữu ích · tránh                <- Disclosure thu gọn
┌────────────────────────────────────────────┐
│ ...                              (4 dòng)  │   <- tự giãn
└────────────────────────────────────────────┘
 ▰▰▰▱▱▱▱▱▱  12/8-40 từ ✓
 ☑ Có chủ ngữ và động từ đã chia   ☐ Hai thì khác nhau   ☐ Đúng với tôi   <- checklist_vi
[      Nhờ Haru chấm      ]      Xem bài mẫu (link)
```
Quy tắc:
- `frames[]`: mỗi frame là chuỗi có `____` (vd `"Yes, I do. I have lived there ____."`). Bấm = chèn vào vị trí con trỏ (hoặc cuối), đặt selection vào `____` đầu tiên để gõ đè. Hiển thị tối đa 3-4 chip, cuộn ngang.
- `useful_vi[]` (từ/cụm nên dùng) và `avoid_vi[]` (lỗi cần tránh) trong một Disclosure "Công cụ" ĐÓNG mặc định; mở ra có hai cột/hai nhóm chip. Chip `useful` cũng bấm để chèn.
- `checklist_vi` hiện ngay dưới ô viết, tick tay (có sẵn) và nếu có `detectors` thì tự tick (PatternsUsed đã có logic `detect(text, detectors)`, dùng lại).
- Đếm từ: thanh dài kèm vạch min và max; màu `text-ink-2` -> `text-green` khi đủ, `text-danger` khi quá; kết quả thông báo `role="status"` ổn định (tránh đọc mỗi phím: dùng `aria-live="polite"` + debounce).
- Textarea: `min-height` theo `max` (<=50 từ: 4 dòng; <=150: 8; còn lại 12) và tự giãn.
- "Nhờ Haru chấm" là nút chính; "Xem bài mẫu" là nút chữ (`underline`).

## 4. Đặc tả dữ liệu tối thiểu và cách suy biến

Tất cả trường mới là TÙY CHỌN; UI luôn đúng khi thiếu (triển khai dần).

| Dạng | Trường backend | Fallback khi thiếu |
|---|---|---|
| Chung | `task_vi` (<=60 ký tự, mệnh lệnh), `kind` (chip: `fill1`, `fix`, `inflect`, `rewrite`, `bank`, `build`, `dictate`, `write`) | `task_vi` <- câu đầu của `instruction_vi` (đến dấu `.`); `kind` suy từ `title_vi` ("Sửa cho đúng" -> `fix`, "Mỗi chỗ trống một từ" -> `fill1`) hoặc từ `type`; nếu không đoán được, không hiện chip. |
| Chung | `set_id`, `index`, `total` | Hiện tại phải tách từ `title_vi` bằng regex `\((\d+)\/(\d+)\)\s*$` (làm ngay trong component, P0), rồi bỏ phần đó khỏi tiêu đề. |
| Chung | `guide_vi` cho BỘ (Disclosure ở đầu bộ) | `instruction_vi` dài hiện 1 lần cho item đầu của bộ cùng `title_vi` gốc; item sau chỉ hiện `task_vi`. |
| write_fill (fill1/inflect/bank) | `text` dùng `____`/`{1}` (thay `( ㉠ )`), `blanks[].accepted`, `answer_kind`: `word` / `phrase` / `inflect`, `hint` (động từ trong ngoặc), `hint_vi` | Giữ regex `BLANK` cũ nhưng không hiện `㉠`; `hint` suy từ `\)\s*\(([^)]+)\)`; độ rộng ô theo `max(len(accepted))`. |
| write_fill `fix` | `original` (câu gốc sai), `error_span` (hoặc `original_md` với `~~sai~~`) | Không có `original`: ẩn khối ✗, `task_vi` = "Điền cụm còn thiếu cho đúng nghĩa"; KHÔNG dùng chữ "phần in đậm". |
| bank | `bank: string[]`, `bank_scope: "item" | "set"` | Không có `bank`: không hiện chip; vẫn có ô gõ. Tạm thời có thể tách danh sách từ trong `instruction_vi` (chỉ khi chuỗi kết thúc bằng "…" hoặc dạng `a, b, c`), nhưng nên gỡ khỏi `instruction_vi` ở seed. |
| rewrite | `original`, `must_use`, `starter` | Ẩn khối "từ bắt buộc"/"mở đầu" khi thiếu. |
| build_order | đã đủ (`meaning_vi`, `tiles`, `answers`) | Không cần. |
| listen_dictation | đã đủ; thêm `lang:"en"` | Hard-code `lang="en"` trong IELTS. |
| write_essay | `frames: string[]` (câu khung có `____`), `useful_vi: string[]`, `avoid_vi: string[]`, `checklist_vi` (đã có), `detectors` (đã có kiểu, seed chưa dùng), `rows_hint` (tùy chọn) | Không có `frames`: không hiện dải chip; có `framework_vi` chung chung thì gom vào Disclosure "Công cụ" đóng; `rows` suy từ `limits.max`. |

Thứ tự triển khai dữ liệu: (1) `original` của "Sửa cho đúng" (8+ item mỗi ngày), (2) `bank` cho các bài "Điền từ trong khung"/"Mỗi chỗ trống một từ" (đang nhét trong `instruction_vi`, `book_items.py:162,236,385`), (3) `frames/useful_vi/avoid_vi` cho 13 đề viết, (4) `task_vi`/`kind` cho toàn bộ.

## 5. Trợ năng và di động (kiểm tra nhanh)

- Hit-area: `hit-area` chỉ thêm 7px mỗi phía dọc (styles.css:585-591); các nút `min-h-9` (36px): "Viết lại", "Làm lại", "Bỏ mảnh cuối", "Xếp lại" thành 50px ảo nhưng ô bên cạnh cùng hàng có thể chồng; đổi sang `min-h-11`. Chip ngân hàng từ và chip khung câu >=44px (hoặc 40px + khoảng cách 8px).
- Tương phản: `text-ink-2` đã >=4.5:1 theo comment styles.css:32; nhưng `bg-blue` + chữ trắng + `disabled:opacity-50` hạ về dưới 3:1 (ảnh 1). Ô vàng `bg-yellow-soft` (alpha 0.22) trên `bg-card` cho nền rất nhạt, chữ `㉠` không có viền; ô gạch dưới nội tuyến (viền 2px `border-blue`) đạt 3:1 cho thành phần UI.
- Bàn phím ảo che nút: `Chấm bài` nằm cuối thẻ; trên điện thoại bàn phím che nút khi đang gõ. Khuyến nghị: nút chính `position: sticky; bottom: calc(var(--tabbar-h) + 8px)` trong thẻ, hoặc `enterKeyHint="done"` + Enter trong input một dòng gửi chấm (hiện chưa có: không thấy `onKeyDown`/`enterKeyHint`/`inputMode` trong lesson/*.tsx). Khi focus, `scrollIntoView({block:"center"})`. Dùng `visualViewport` để tính `padding-bottom` nếu cần.
- Focus: các input có `focus-visible:ring-2 ring-blue/50` (50% mờ, có thể thấp so với nền trắng; dùng `ring-blue`). Sau khi chấm, chuyển focus tới `role="status"` hoặc nút "Câu tiếp"; hiện chỉ `role="status"` (đọc nhưng không focus).
- aria cho chỗ trống nội tuyến: ô nhập nội tuyến cần `aria-label` đầy đủ ("Chỗ trống 1 trên 1: điền một từ vào câu: ___ your sister live near here"), không để trình đọc màn hình đọc `㉠` (trình đọc có thể đọc tên ký tự Hàn thay vì "chỗ trống"). `Gap` (McqExercise:27) đã có `aria-label="Chỗ trống"`: nên kèm đáp án đã chọn.
- `lang`: các input tiếng Anh dùng `lang="en"` (WriteFill, WriteEssay), nhưng Dictation dùng `lang="ko"` (sai), và nhiều chỗ `font-korean` + `lang="ko"` cho văn bản tiếng Anh (`McqExercise` Question prompt, option text). Trình đọc sẽ phát âm tiếng Hàn: đổi thành `lang="en"` và `font-sans`.
- Phản hồi động: `role="status"` trong textarea đếm từ cập nhật mỗi phím. Dùng `aria-live="off"` cho đếm từ, chỉ báo trạng thái đủ/dài khi đổi.
- Chuyển động (`prefers-reduced-motion`): đã tôn trọng (`motion-reduce:*`).

## 6. Ưu tiên

Chú thích: [C] = chỉ sửa component, không đụng dữ liệu; [D] = cần dữ liệu.

### P0 (tác động lớn nhất, công sức nhỏ)
1. [C] Đảo phân cấp header ở mọi dạng: nhiệm vụ = câu đậm 17px; nhãn loại bài thành chip nhỏ; bỏ `uppercase`; bỏ điểm khỏi header. Tách `ExerciseShell` dùng chung (WriteFill, WriteEssay, McqExercise, BuildOrder, DictationExercise).
2. [C] Bỏ ô vàng `㉠`: render chỗ trống `( ㉠ )` thành ô gạch dưới nội tuyến, input rộng theo `accepted` (`ch`). Bỏ dòng nhãn `ⓣ · 3 điểm`. Một chỗ trống thì input ở NGAY trong câu.
3. [C] Tách `(1/8)` từ `title_vi` bằng regex, hiện thành "3/8" + thanh tiến độ bộ; xóa khỏi tiêu đề.
4. [C] Nút chính không dùng `opacity-50`: chuyển sang kiểu "chưa sẵn sàng" rõ ràng; thêm dòng trợ giúp "Gõ đáp án để chấm".
5. [D+C] "Sửa cho đúng": thêm `original`; nếu chưa có, ẩn lời "phần in đậm" và đổi nhiệm vụ (fallback). Đây là sửa chữa trực tiếp cho ảnh 2.
6. [D+C] `bank[]` thay danh sách từ trong `instruction_vi`; trước mắt [C]: ẩn đoạn "…" cắt cụt, hiện nút "Xem từ gợi ý" nếu tách được.
7. [C] Textarea viết: `rows` theo `limits.max`, auto-grow; placeholder theo đề; đưa checklist lên cạnh ô viết.

### P1
8. [C] Placeholder theo `kind`/`answer_kind` hoặc bỏ placeholder (ô nội tuyến); `aria-label` đầy đủ cho từng chỗ trống.
9. [C] Tách `hint` `(work)` bằng regex thành chip nổi bật; nhiệm vụ "Chia động từ (work)".
10. [D+C] `frames[]`, `useful_vi[]`, `avoid_vi[]` cho 13 đề viết; chip bấm để chèn; "Công cụ" Disclosure thu gọn, bỏ `framework_vi` chung 3 dòng.
11. [C] Bàn phím ảo: nút sticky, Enter để chấm, `scrollIntoView` khi focus.
12. [C] `lang="en"` cho nội dung tiếng Anh (Dictation, Mcq) và bỏ `font-korean` cho tiếng Anh.
13. [C] `instruction_vi` dài chỉ hiện một lần cho cả bộ (item đầu) + Disclosure "Cách làm".
14. [C] Đếm từ trực quan (thanh + vạch min/max); nút Haru chấm là nút chính duy nhất.

### P2
15. [D] `task_vi` + `kind` tường minh cho toàn bộ item (thay suy luận từ `title_vi`).
16. [C] Sticky bank chip cho bộ; gỡ chip đã dùng; Tab/Enter điều hướng giữa các ô.
17. [C] Làm gọn "Chưa khớp đáp án" -> "Chưa đúng" + đáp án đậm; ẩn "Lần trước: …" khi chưa làm.
18. [C] Hit-area `min-h-11` cho nút phụ; `ring-blue` đậm hơn.
19. [D] `rewrite` có `original` + `must_use` khi có bài dạng này.

## 7. Ngoài phạm vi / chưa kiểm chứng
- Không chạy giao diện thật; mô tả ảnh dựa trên 6 ảnh người học mô tả và code. Việc "khung gợi ý mở sẵn" (ảnh 4) mâu thuẫn với `defaultOpen=false` trong code hiện tại: có thể bản triển khai khác, nên kiểm tra.
- "ⓣ" là suy đoán có căn cứ: dữ liệu chứa `㉠` (U+3260), regex WriteFill.tsx:11 hiển thị chính ký tự đó; việc font vẽ ra "ⓣ" phụ thuộc thiết bị, không kiểm chứng được ở đây.
- Chưa đo tương phản thực bằng công cụ; số liệu dựa trên bình luận ở styles.css.

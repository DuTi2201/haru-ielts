# Reviewer B (senior product + UI/UX): bài 45 (G1 Ngày 2) và 46 (G1 Ngày 3) so với bài 44

Ngày 2026-11-12. Phạm vi: đọc seed `g1-d1|d2|d3`, `scripts/g1/{days.txt,build.py,lecture_d1.py}`, `docs/QUALITY_LESSON44.md`, `docs/review/{lesson44-grammar-ui,exercises-ui}`, và frontend `src/components/lesson/**`, `lib/lesson-sessions.ts`. Không chạy app, không sửa code hay seed. Con số lấy từ file seed hiện có; chỗ nào là suy luận thì ghi rõ.

## 0. Kết luận một đoạn

Bài 44 là một sản phẩm biên soạn tay (2 buổi giảng 30 slide, 9 loại hình vẽ, 7 thẻ dày, 110 bài, phiên âm, Azure). Bài 45 và 46 là bản sinh tự động từ `days.txt`: cùng khung kỹ thuật nhưng nội dung màn hình mỏng hơn nhiều. Khoảng cách lớn nhất không nằm ở component (chúng dùng chung) mà ở **dữ liệu chưa có**: không có kịch bản giảng, không có hình vẽ, thẻ chữ ngắn, không phiên âm, ít bài tập hơn kế hoạch. Phần lớn nâng cấp UI vì thế là biên soạn nội dung theo đúng khuôn bài 44, cộng thêm 5–6 hình vẽ mới cho Ngày 2–3.

## 1. Bảng đối chiếu từng thành phần màn hình

| Thành phần | Bài 44 | Bài 45 | Bài 46 | Khoảng cách |
|---|---|---|---|---|
| Buổi giảng (có `lecture` trong seed) | 22 + 8 slide, biên soạn tay; buổi 3 là luyện | **0 slide**, cả 3 buổi không có `lecture` | **0 slide** | Lớn nhất. Buổi giảng chạy bằng mẫu máy (từ → nghĩa → ví dụ), đúng cái mà QUALITY_LESSON44 mục 1 đã bỏ |
| Hình vẽ (scene SVG) | 9 loại, 13 lần dùng | 0 | 0 | Cần hình mới (mục 3) |
| «Nói theo» / «Tự dừng để nói theo» | 24 / 18 chỗ | 0 (không có lời giảng để gắn) | 0 | Đi theo kịch bản giảng |
| Thẻ ngữ pháp | 7 thẻ; độ dài `use`+`note`+`tip` 660–3.360 ký tự; bảng, nhóm, 7 lỗi người Việt | 7 thẻ; **69–715 ký tự**; thẻ 6 (kế hoạch lên lịch) chỉ ~69 ký tự và không có lỗi người Việt | 7 thẻ; 110–432 ký tự; thẻ 7 (breath/breathe/breadth) 110 | Thẻ mỏng, không bảng, không `step_vi` |
| Thẻ có câu kiểm tra tại chỗ (`check`) | 7/7 | 6/7 (thẻ 1 «Hai trục» không có) | 5/7 (thẻ 1 và 2 không có) | Thiếu 1–2 thẻ |
| Phiên âm từ vựng | 4/24 (OALD) | 0/11 | 0/10 | Mục tiêu 45–46: ít nhất các từ có trọng âm khó |
| Từ vựng | 24 từ, 3 buổi, 10 + 1 + 13 | 11 từ, dồn hết vào buổi 1 (buổi 2–3 có 0) | 10 từ, dồn buổi 1 | Mất nhịp: ba buổi chỉ có một buổi có từ |
| Số câu kiểm tra mỗi buổi | 15 / 8 / 16 / 18 / 20 / 18 / 15 | 3 / 3 / 14 / 17 / 8 | 5 / 4 / 13 / 17 / 12 / 23 / 10 | Buổi 1–2 chỉ 3–5 câu (ngưỡng 44: 8–15); buổi cuối dồn 13–14 câu «rest» |
| Dạng bài tập | I 8, Q 15, B 7, F 5, D 1, M 3 + sách 71 | I 8, Q **2**, B 4, F 4, D 1, M **1** + sách 34 | T 4, I 6, Q 2, B 4, F 4, D 1, M 1 + sách 62 (KU 42) | Kế hoạch WEEK1_PLAN hứa 18 câu/ngày; Q và M thiếu |
| Sách trước, giảng sau | 4 nhóm sách (B2, G65, C1&C2 ×2) | 2 nhóm (B2 tr.10; G65) | 3 nhóm (B2, G65 ×2) | Ngày 2–3 chưa có C1&C2 Unit 1 (tr. 9–11) |
| Bài viết «Câu của tôi» (M) | 3, có rubric riêng M1–M3 | 1, rubric chung | 1, rubric chung | M thiếu 2 đề; rubric chưa riêng |
| Mục tiêu / `can_do_vi` / `use_vi` | có, đã rà (mục 17 audit) | có nhưng **`use_vi` lặp nguyên văn ở cả 3 buổi** | như 45 | Cùng một đoạn «Writing Task 1… xu hướng» hiện 3 lần |
| Ghi chú `notes` (goal/language/IELTS) | 154 / 824 / 217 ký tự | 139 / 466 / 143 | 144 / 490 / 139 | Mục «Dùng ở đâu trong IELTS» chỉ ~140 ký tự |
| Bài gõ lại «Sửa cho đúng» có câu gốc sai | có cho 8 câu KB | KF/KG: chưa kiểm | KU: chưa kiểm | Lỗi dữ liệu đã biết ở 44; kiểm tra cho 45–46 |
| Nghe chép (D) | 1 bài (3 câu) | 1 | 1 | Bằng nhau; âm cuối của Ngày 2 (talks, lives, aren't, stops) cần câu riêng |

## 2. Rà soát theo chi tiết giao diện

### 2.1 Header và mục tiêu
- `use_vi` lặp 3 lần trong ba buổi của 45 và của 46 (suy ra từ dữ liệu seed: cùng chuỗi ở mỗi `sessions[i].use_vi`). Người học đọc cùng đoạn ba lần trong cùng một ngày; nên mỗi buổi một câu «dùng ở đâu» riêng (Ngày 2: xu hướng Task 1 → than phiền Speaking → kế hoạch; Ngày 3: Part 1 «how long» → Part 2 «first time» → Task 2 «has led to»).
- Tên buổi sách quá dài, tự cắt giữa chữ («Điền từ trong khung: dấu hiệu của hoàn…», «Điền động từ: phỏng vấn… (+1)»). Cắt theo từ và dồn «(+1)» thành «2 bài».
- `can_do_vi` ghép nhãn thô («nối để thành câu; điền động từ: ancient aviators?.»). Có dấu `?.` và nhãn tiếng Anh lọt vào câu tiếng Việt: sửa tay.

### 2.2 Thứ tự các bước
Khung của 44: Sách trước → 3 buổi giảng (mỗi buổi: từ, thẻ, câu kiểm tra, nói thử) → bài sách → luyện. 45 và 46 dùng cùng bộ máy nên thứ tự đúng, nhưng:
- Buổi 1 của 45 có 11 từ + 3 thẻ + chỉ 3 câu kiểm tra: người học học xong 14 thứ mà được hỏi 3 câu. Cân lại: 4 từ + 3 thẻ + 8 câu; chuyển 3 từ sang buổi 2 và 3.
- Buổi 3 của 46 và 45 vẫn là «thùng chứa» (13–14 câu «rest», gồm nghe chép, xếp câu, viết); người học thấy một buổi dài bất thường. Đặt mục tiêu 8–12 câu mỗi buổi và đẩy phần «rest» thành một buổi «Vận dụng» riêng như buổi 3 của bài 44.

### 2.3 Buổi giảng
- Đây là hạng mục nặng nhất và phải làm trước mọi thứ khác: viết `lecture_d2.py`, `lecture_d3.py` theo khuôn `lecture_d1.py` (câu hỏi mở → thí nghiệm → kết luận → nói lại), qua các cổng của `tests/test_lesson44_quality.py` (3,5–7 phút/buổi, quãng nhắc lại 0,4 s + 0,545 s/từ, một giọng cho câu tiếng Anh, 0 câu thừa của mẫu).
- Mỗi ngày nên là 2 buổi giảng (4–7 phút) + 1 buổi vận dụng, như 44, thay vì 3 buổi chia theo thẻ.
- «Nói theo» sinh tự động từ `shadow_runs` khi có câu tiếng Anh trong lời giảng: sẽ có ngay khi kịch bản có câu mẫu.

### 2.4 Thẻ ngữ pháp
Chuẩn từ bài 44 (audit và `docs/review/lesson44-grammar-ui`): công thức → cách dùng theo nhóm → bảng → lỗi người Việt → kiểm tra. Đối chiếu:
- **Ngày 2, thẻ 6 (kế hoạch lên lịch)** gần như trống: cần công thức `am/is/are + V-ing + mốc tương lai`, so với `will` và `be going to` ở mức chỉ dẫn, 2–3 ví dụ, và lỗi hay gặp (`I see him tomorrow`).
- **Ngày 2, thẻ 7 (động từ trạng thái)** là bảng quan trọng nhất của ngày mà chỉ có 715 ký tự: cần bảng 3 cột (luôn trạng thái · đổi nghĩa khi tiếp diễn · không bao giờ tiếp diễn) với `think/have/look/see/taste/smell/be` và cảnh báo `I am knowing`, `I am liking`. Sách IELTS Grammar xếp *enjoy* vào động từ trạng thái, bài 44 đã chọn tránh mâu thuẫn: giữ nguyên quy ước đó.
- **Ngày 3, thẻ 4–5 (hai câu hỏi, thay thế một chiều)**: nội dung đúng nhưng chữ dày, không có hình. Đây là chỗ sơ đồ quyết định (mục 3) thay thế được 60–70% chữ.
- **Ngày 3, thẻ 7 (breath/breathe/breadth)** 110 ký tự: là nhắc chính tả, không phải thẻ ngữ pháp; chuyển thành một câu nghe chép + một ô trong bảng «từ dễ lẫn», đỡ chiếm một thẻ.
- Thẻ nào cũng cần `step_vi` (một bước làm) và `note_vi` «Lỗi người Việt hay mắc» như 44; hiện Ngày 2 có `note_vi` ở 5/7 thẻ, Ngày 3 ở 5/7.
- Độ dài: bài 44 chứng tỏ thẻ 800–1.500 ký tự đọc được trên iPhone khi chia nhóm bằng tiêu đề nhỏ; đừng vượt quá ~1.500 ký tự trừ thẻ «cách dùng». Chữ không dưới 12 px (commit 96d530e).

### 2.5 Từ vựng
- Thêm phiên âm cho mọi từ có trọng âm khó, lấy từ mục từ OALD (BrE) như 44, **không gõ từ trí nhớ**. Từ nên có: `temporary`, `annoying`, `recognise`, `achieve`, `certificate`, `measure`, `secondary`.
- Cặp dễ nhầm đã có trong dữ liệu (`pupil/student`, `teach/learn`, `achieve/reach`, `count/measure`): hiển thị thành thẻ so sánh hai cột chứ không phải hai thẻ rời; đây là thiết kế đúng cho Ngày 5 và có thể sớm hơn ở 45–46.
- Dàn đều 3–4 từ cho mỗi buổi (xem 2.2).

### 2.6 Bài tập
- Tỷ lệ Q (điền) và M (viết) thiếu so với kế hoạch: Ngày 2 cần 4 câu điền, 2 chép chính tả, 8 cặp hàm ý (đã có I 8); Ngày 3 cần 4 điền, 4 viết lại câu (hiện chưa có dạng «viết lại câu»).
- Câu «cặp hàm ý» (I) là dạng đặc trưng của Ngày 2 và là bài hay nhất của thầy; đảm bảo mỗi cặp hai đáp án **đều đúng ngữ pháp** và chỉ khác hàm ý (đúng tinh thần thẻ «Hai trục»); kiểm tra lại các đáp án nhiễu như đã làm ở 44 (audit mục 7–10).
- KU (42 câu, IELTS Grammar Unit 3) chiếm 2/3 bài của Ngày 3: kiểm tra có chia nhóm theo buổi chưa, vì 23 câu trong một buổi là quá dài.
- Hai lỗi UI đã biết từ `docs/review/exercises-ui/B.md` ảnh hưởng mọi bài (cả 44): ký tự `㉠` trong ô trống, tiêu đề là nhãn loại bài, hướng dẫn 12 px xám, `instruction_vi` lặp từng thẻ, nút khoá nhìn như hỏng. Chưa biết đã sửa chưa; nếu chưa, sửa trước rồi mới nâng 45–46 để khỏi nhân đôi việc.

### 2.7 Nói thử / Azure
`SayStep` đã có ghi âm, chấm từng từ, ngưỡng 80/60. Với 45–46 cần lưu ý:
- Câu nói thử tự lấy từ ví dụ thẻ và từ; khi thẻ mỏng thì câu cũng ít (Ngày 2 buổi 2–3 có thể không có «Nói thử»). Mỗi buổi cần ≥ 4 câu.
- Không đưa câu **sai** vào «Nói thử» (cổng của 44: câu sai chỉ nghe). Cặp hàm ý của Ngày 2 có câu «sai hàm ý» nhưng đúng ngữ pháp: cho đọc cả hai, đó là bài luyện ngữ điệu tốt.
- Chỗ có thể dùng thêm khoá luyện phát âm vừa làm (`/pronunciation`): âm cuối -s/-ed ở Ngày 2 (`talks`, `lives`, `stops`), -ed ở Ngày 3 (`worked`, `lived`). Gợi ý một liên kết từ thẻ sang video âm tương ứng.

### 2.8 Bài viết, ngân hàng câu, trạng thái rỗng và lỗi
- M: 3 đề mỗi ngày như 44, đề nào cũng cần khung gợi ý đúng thì của Ngày đó (Ngày 2: một câu than phiền với always + V-ing, một câu xu hướng; Ngày 3: `for/since`, `first time`) và rubric riêng.
- Ngân hàng câu: `bank: "g1"` dùng chung; khi người học lưu câu của Ngày 2–3 cần nhãn ngày để lọc.
- Trạng thái rỗng/tải/lỗi: dùng chung `states.tsx`, không khác biệt theo ngày; không cần làm lại cho 45–46.
- Bàn phím và cỡ chạm: component dùng chung, sửa một lần cho cả ba bài (xem 2.6). Chip và nút phụ 36 px dưới ngưỡng 44 px: sửa chung.

## 3. Hình vẽ cần làm cho Ngày 2 và 3

Hình dùng cùng cơ chế `scene` (SVG thuần, từng phần hiện theo dòng đang đọc, mỗi phần chạm để nghe lại, một phần «đang nói» tương phản cao, không in lại lời giảng). Tái dùng `tense_timeline` (đã có trong 44) cho Ngày 3.

**Ngày 2: 4 hình (hai buổi giảng)**
1. `two_axes` — Hai trục: một lưới 2 cột (đúng ngữ pháp / hàm ý). `Play I football` rơi ra ngoài trục ngữ pháp; `My sister lives…` và `…is living…` nằm cùng cột đúng, khác hàm ý. Thẻ 2.1.
2. `implication_pairs` — Cặp hàm ý: hai câu cạnh nhau, giữa là thanh trượt «cố định ↔ tạm thời». Dùng cho 8 cặp (`lives/is living`, `works/is working`…). Thẻ 2.2.
3. `now_not_decisive` — Trục «bây giờ»: hai nhánh từ `now` (thói quen → đơn; mốc cụ thể `right now`, `at 3 o'clock` → tiếp diễn). Thẻ 2.3.
4. `state_verbs_table` — Bảng động từ trạng thái: ba vùng màu (không tiếp diễn · đổi nghĩa · chỉ hành động) với `think/have/see/look` kéo qua lại giữa hai nghĩa. Thẻ 2.7. Có thể gộp xu hướng, than phiền, kế hoạch thành bảng tra nhanh `ref_table` đã có (không cần hình riêng).

**Ngày 3: 5 hình (hai buổi giảng)**
1. `tense_timeline` (tái dùng) — vẽ hai trục cho `since 2003` (kéo tới bây giờ) và `already eaten` (đã xong, không nói lúc nào). Thẻ 3.1–3.3.
2. `since_for` — thanh thời gian với điểm mốc (`since` + mốc) và đoạn (`for` + khoảng); người học chạm vào mốc/đoạn để nghe câu. Thẻ 3.2.
3. `gone_been` — hai đường đi: `have gone to` (mũi tên đi mà chưa về) và `have been to` (đi và về). Thẻ 3.4.
4. `two_questions` — sơ đồ quyết định đúng ý thẻ 3.5: «Đã bắt đầu làm chưa?» → «Lúc nói còn làm / vừa dừng và còn dấu vết?» → «Muốn nhấn quá trình?» → `have been V-ing`; mỗi ô có một câu mẫu (`out of breath… have been running`). Đây là hình quan trọng nhất của ngày.
5. `one_way` — mũi tên một chiều: hoàn thành thay được cho hoàn thành tiếp diễn, ngược lại không (`waited` vs `have been waiting`). Thẻ 3.6.

Tổng 9 hình mới (4 + 5), bằng quy mô 9 loại của bài 44. Mỗi hình cần: dữ liệu `data`, khoá `shown`, và test «mọi phần hình có một dòng đọc đưa nó ra» (100%).

## 4. Việc nên làm, theo thứ tự ưu tiên

1. **Soát lại câu «sai/đúng» của 45–46 trước tiên** (không đổi UI): đáp án nhiễu, đáp án chấp nhận, câu gốc sai, đối chiếu đáp án in (Destination B2 tr. 229; IELTS Grammar tr. 220). Sai kiến thức nặng hơn mọi thứ thẩm mỹ.
2. **Viết kịch bản giảng Ngày 2 và 3** (hai buổi + một buổi vận dụng mỗi ngày) theo khuôn `lecture_d1.py`, gắn cổng chất lượng. Cần tài liệu thầy (mục 5).
3. **Viết lại 7 thẻ mỗi ngày** theo khuôn sách + thầy; thẻ 2.6 và 2.7 làm đầu tiên.
4. **Vẽ 9 hình** (mục 3), bắt đầu `two_questions` và `implication_pairs`.
5. **Cân lại buổi**: 8–12 câu mỗi buổi, từ vựng 3–4 từ/buổi, bỏ `use_vi` lặp, buổi «Vận dụng» riêng.
6. **Bổ sung bài tập đúng kế hoạch**: Q +2..4, M +2 với khung và rubric riêng, dạng «viết lại câu» cho Ngày 3.
7. **Thêm bài sách còn thiếu** (C1&C2 Unit 1 bài C–J, tr. 9–11) vào đúng ngày; chỉ khi có ảnh sách và đáp án.
8. **Phiên âm OALD** cho các từ khó; liên kết âm cuối sang `/pronunciation`.
9. **Sửa chung UI bài tập** (nhãn tiêu đề, 14–15 px cho hướng dẫn, bỏ `㉠`, nút khoá, cỡ chạm 44 px) nếu chưa làm; lợi cho cả ba bài.
10. **Đo**: gắn lại các chỉ số của 44 (`lecture_complete`, `lecture_replay`, `say_score`, `first_try`, `step_abandon`) cho 45–46 và so sánh. Với một người học chỉ là nhật ký, không phải thống kê.

## 5. Điều cần từ chủ dự án để làm tiếp

- Ghi chép/ghi âm bài giảng của thầy Minh cho Ngày 2 và 3 (hiện tại đơn là nguồn của 44 theo QUALITY_LESSON44). Không có bản này thì thứ tự và «thí nghiệm» của thầy phải đoán.
- Ảnh trang sách: Destination B2 Unit 1 tr. 7 (bảng stative verbs và Watch out), tr. 9–11 nếu chưa có; IELTS Grammar 6.5+ Unit 1 phần tiếp diễn và Unit 3 (hoàn thành); Destination C1&C2 Unit 1 tr. 9–11 kèm đáp án tr. 281.
- Quyết định thiết kế: (a) mỗi ngày 2 buổi giảng + 1 buổi vận dụng như 44, hay giữ 3 buổi chia theo thẻ; (b) có đưa Ngày 2 «kế hoạch lên lịch» vào cùng buổi với «xu hướng» hay tách ra; (c) có cho phép liên kết sang khoá phát âm trong thẻ.
- Giả định cần dữ liệu thật: số câu 8–12 mỗi buổi và ngưỡng chữ 1.500 ký tự mỗi thẻ rút từ bài 44 và từ một người học; chưa kiểm chứng. Sau khi 44 chạy ít nhất vài ngày, đọc `step_abandon` và `first_try` trước khi chốt.

Không có commit nào trong báo cáo này.

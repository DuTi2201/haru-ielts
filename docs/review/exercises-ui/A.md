# AGENT A: Soát tính "làm được" của đề (Haru-IELTS G1)

Phạm vi: toàn bộ `build.json` write_fill (381), `reading.json` (297, mẫu + đếm), `writing.json` (13). Chỉ đọc. Script đếm: `/home/claude/haru-ielts/docs/review/exercises-ui/A_audit.py` (chạy lại được, không ghi dữ liệu).

## 0. Kết luận 10 dòng
1. 222/381 write_fill (58%) có lỗi đề: 116 (30%) khiến người học không xác định được việc phải làm; 106 (28%) làm được nhưng thiếu dữ kiện; 159 (42%) ổn.
2. Nguyên nhân: khoảng 80% là TRÌNH BÀY/SINH DỮ LIỆU (thông tin có trong nguồn hoặc đáp án nhưng không lên màn hình), khoảng 20% là THIẾU DỮ LIỆU THẬT (câu gốc sai của sách, 2 câu còn lại của bài "một từ cho ba câu").
3. Nguyên nhân gốc: `write_fill()` trong `scripts/b1/build.py` cứng instruction "Gõ từ hoặc cụm từ còn thiếu." và `text` chỉ chứa câu đã đục lỗ; ngân hàng từ, nghĩa Việt, câu sai nằm trong instruction hoặc trong `common_errors_vi` (chỉ hiện SAU khi chấm).
4. `WriteFill.tsx` đã có chip `context_vi` nhưng 381/381 mục để trống; chưa có trường ngân hàng từ.
5. Bài Viết: 13 bài chỉ có 2 khung khác nhau (6 + 7 bài), 2 checklist, rubric chỉ có ở 3 bài (giống hệt), 10 bài rubric rỗng.
6. Khung D9 (tóm tắt bài đọc) bảo "nói về chính bạn": mâu thuẫn đề. Khung D5-D11 bảo "chọn 5-10 từ" trong khi đề chỉ viết 2 câu.
7. Bản viết lại 13 khung (JSON, mục 2) dùng sẵn các trường UI đang hỗ trợ: `framework_vi`, `patterns_vi`, `common_errors_vi`; chỉ `avoid_vi` là trường mới.
8. 12 mục chấp nhận đáp án thiếu dạng rút gọn (I've / they're) và 2 mục thiếu chính tả Mỹ (recognize); `normalizeAnswer` bỏ dấu nháy nên "'re walking" không khớp "are walking".
9. Reading: phần lớn làm được (có chart, có prompt); lỗi chính ở 8 mục "Tìm từ đồng nghĩa" (G1D10KH5) không hiện bài đọc.
10. Ưu tiên: P0 tự động hóa instruction + chip nghĩa/ngân hàng từ (khoảng 190 mục, sửa bằng script); P0 viết tay 18 câu gốc sai + 13 khung.

## 1. Kiểm kê answerability (script)
| Nhóm lỗi | Số mục | Id ví dụ | Chẩn đoán |
|---|---|---|---|
| B1 Câu gốc sai / động từ gốc bị ẩn (Sửa cho đúng, Sửa thì, Tìm động từ sai) | 18 | G1D1KB-1..8, G1D3KU3C1-1..7, G1D4KC4-1..3 | Đề bảo "sửa phần in đậm" nhưng không hiện câu gốc. Thiếu dữ liệu thật. |
| B2 "Ôn lại" không hiện nghĩa tiếng Việt | 31 (O5 22 + O6 9) | G1D6O5-2 "A degree is a useful ( )." | Instruction hứa "nhìn nghĩa tiếng Việt gợi ý" nhưng nghĩa chỉ hiện sau khi chấm (trong common_errors_vi). Đáp án qualification/asset/advantage đều hợp. 22 mục trùng nội dung giữa G1D6O5 và G1D7O5. Trình bày. |
| B3 Phụ thuộc nội dung không hiện: audio, bài đọc, 2 câu còn lại | 24 (KLT 10, KTY 7, KXI 7) | G1D11KLT-1 "Sadie's postcode: ( )." (cần audio), G1D7KXI-1 ("think ( )" cần thấy cả ba câu) | KLT/KTY: dữ liệu có sẵn (reading/listening) nhưng chưa liên kết. KXI: thiếu 14 câu thật. |
| B4 Ngân hàng từ bị cắt "…" | 15 (KCB) | G1D1KCB-2 | Danh sách 10 từ cho 15 chỗ; 4 đáp án (whenever, for, it/that, most) không có trong danh sách. Trình bày. |
| B5 Tên bài nói "trong khung/bộ từ" mà không liệt kê | 23 (KXL 12, KXC 11) | G1D7KXL-8 "take ( ) of the situation" | Bank = tập đáp án của nhóm, sinh tự động được. |
| B6 F không có gợi ý loại từ | 3 | G1D1F5 (Does), G1D1F3 (Do), G1D3F4 (since) | Instruction "Gõ từ hoặc cụm từ" cho 19/19 mục F. |
| B7 Instruction nói "chia động từ trong ngoặc" nhưng ô trống là trợ động từ | 2 | G1D1KCA-3 (doesn't), G1D1KCA-7 (does) | Lệch nhiệm vụ. |
| W1 Khung từ chỉ là cặp gạch chéo trong instruction | 13 (KA18) | G1D5KA18-1 (pupils) | Phải đoán nhóm, tự chia số nhiều. |
| W2 Ngân hàng từ là chữ thường trong instruction, không chip | 36 (KXB 9, KD 10, KC3 8, KF 9) | G1D3KD-1 | Làm được nhưng chậm hơn 5 giây. |
| W3 Instruction chung chung dù có (động từ) | 16 | G1D2F1 | Thiếu "Chia động từ trong ngoặc". |
| W4 Câu rời khỏi đoạn văn / hội thoại | 41 (KI 12, KU3C4 15, KXJ 6, KG18 8) | G1D4KI-2 ("I ( ) wish..." do/really) | Mất bối cảnh; nhiều đáp án hợp lệ. |
| OK | 159 | G1D1KC2-1, G1D4KJ-1 | Vẫn nhiều mục thiếu số từ cần gõ, từ cho sẵn không phải chip. |

Tiêu đề bị ảnh hưởng nhiều nhất (tỷ lệ mục lỗi trong nhóm = 100%): "Ôn lại · từ Ngày 5" (22), "Mỗi chỗ trống một từ: cách nói thời gian" (15), "Điền từ trong khung: trường học" (13), "Thành ngữ: điền từ trong khung" (12), "Danh từ về suy nghĩ" (11), "Sửa cho đúng (gõ lại)" (8), "Sửa thì: thư xin học" (7), "Gõ đáp án: khảo sát giao thông" (10).

Lỗi chấm (trong 381): 12 mục thiếu dạng rút gọn cho chủ ngữ đại từ (G1D1KCA-13 "They ( ) walking" chỉ nhận "are walking"; G1D3KU3C1-1/-2/-5; G1D4KI-6/-9; G1D4KJ-6...), 2 mục chỉ nhận "recognise" (G1D6O5-6, G1D7O5-6). `normalizeAnswer` (lesson-grade.ts) xóa dấu nháy nên "'re" thành "re", không khớp "are".

Reading (297): 50 đầu vào + 129 cloze + 112 match, chủ yếu ổn (có prompt hoặc chart). Mục lỗi: 8 mục G1D10KH5 "«look down on» = cụm nào trong bài?" không hiện bài; 10 mục G1D7KXG "có nghĩa tìm thông tin không?" (Có/Không) hỏi chung chung; 14 mục "Phẩm chất tích cực hay tiêu cực?" mang tính chủ quan (chỉ đúng theo bảng sách). Khoảng 30/297 (10%) cần sửa nhẹ.

Kết luận: CẢ HAI; 58% mục có lỗi, trong đó ~80% là trình bày/sinh dữ liệu (sửa bằng script), ~20% thiếu dữ liệu thật (viết tay).

## 2. Soát 13 bài Viết
Chung: 13/13 `model_note_vi` giống nhau; 13/13 `points` = 5; `instruction_vi` lặp đuôi "Đúng sai chưa quan trọng..." ở cả 13 bài; `limits` min = 8 cho mọi bài (D3M1 ba câu, D4M1 bốn câu mà chỉ cần 8 từ); rubric có ở D1M1-3 (3 tiêu chí giống nhau), D2-D11 trống nên UI chỉ hiện một tiêu chí "Bài viết nói chung".
- Số khung khác nhau: 2 (A: D1M1,M2,M3,D2M1,D3M1,D4M1; B: D5-D11, 7 bài). Số checklist khác nhau: 2. Không khung nào có mẫu câu, từ nối hay lỗi Việt.
- Khung A: "việc đó nằm ở đâu trên trục thời gian?" không áp dụng cho D1M2 (cả hai câu hiện tại đơn) và D1M3.
- Khung B: bullet "Chọn 5-10 từ" mâu thuẫn "viết hai câu"; "từ C1 thì thêm từ B2" vô nghĩa với D5, D8, D10, D11 (không có từ C1); D9 (tóm tắt) bị bảo "nói về chính mình" và checklist "Câu nói về chính bạn, không chép câu mẫu".
- Checklist không kiểm ràng buộc của đề (D1M3 "2 trạng từ tần suất + 1 cụm thời gian", D3M1 "ba công thức", D4M1 "bốn thì").
- Bài mẫu: G1D11M1 "the buses are rare in the evening" là lỗi collocation kiểu Việt (nên "there are few buses"); prompt D11 "two sentences ... and one thing" mơ hồ (2 hay 3 câu); D5 bài mẫu không dùng pupil/student dù đề nhắc; còn lại đúng.
- Rubric đề xuất cho 10 bài trống (sinh bằng script theo mẫu): Task response 1; Dùng đúng cấu trúc/thì mục tiêu 2; Chính xác (chia động từ, giới từ) 2. Từ D5 trở đi thêm "Dùng đúng từ của bài" 1.

Bản viết lại (JSON hợp lệ; `framework_vi` thay khung cũ, `patterns_vi` hiện ở "Mẫu câu nên dùng", `common_errors_vi` hiện sau khi tự chấm; `avoid_vi` là trường mới hiện trong khung trước khi viết; `limits` nâng min):
```json
[
 {"id": "G1D1M1",
  "limits": {"min": 10, "max": 40},
  "framework_vi": ["Câu 1 = hiện tại đơn, nói điều bạn thấy bây giờ: Yes, I do. / Not really. Động từ chính chỉ là like/love/enjoy (động từ trạng thái, không thêm -ing, không thêm am/is).", "Câu 2 = một thì KHÁC, chọn theo ý: hiện tại hoàn thành cho điều kéo dài tới nay (I have lived there for ___ years / since ___), hoặc quá khứ đơn/used to cho điều đã hết (I used to ___, but now ___).", "Nối hai ý bằng because / so / although để câu 2 giải thích câu 1; mỗi câu một mệnh đề đầy đủ có chủ ngữ + động từ.", "Mục tiêu 12-25 từ, đúng 2 câu; câu 2 phải có mốc thời gian (for/since/when I was a child) để thì lộ ra."],
  "patterns_vi": ["Yes, I do. I have lived in ___ for/since ___, so ___.", "Not really. I used to ___ , but now ___ .", "I like ___ because ___ ."],
  "avoid_vi": "Không viết 'I am like my hometown' (am + like) và không viết 'I live here since 2010'.",
  "common_errors_vi": ["I am like → I like.", "I live here since 2010 → I have lived here since 2010 (since + mốc cần hoàn thành)."]},
 {"id": "G1D1M2",
  "limits": {"min": 12, "max": 40},
  "framework_vi": ["Cả hai câu đều hiện tại đơn nên không cần chọn thì; việc cần chọn là TRẠNG TỪ: câu thật dùng usually/often/sometimes, câu nói quá dùng always/never/every single/millions of.", "Vị trí trạng từ tần suất: SAU be (I am always late), TRƯỚC động từ thường (I never have time).", "Câu nói quá nên có dấu ! và một con số hoặc cụm cường điệu: I have read a million books.", "Ngôi thứ ba: nếu kể về anh/chị/bạn thì động từ thêm -s (My brother never washes up)."],
  "patterns_vi": ["I usually/often ___ at/on ___ .", "I never/always ___ , not even ___ !", "My ___ always ___ every single ___ ."],
  "avoid_vi": "Không đặt trạng từ sau động từ thường: 'I go always' sai.",
  "common_errors_vi": ["I always am late → I am always late.", "My brother play games → My brother plays games."]},
 {"id": "G1D1M3",
  "limits": {"min": 18, "max": 45},
  "framework_vi": ["Đi theo trục thời gian trong ngày: sáng -> chiều -> tối, mỗi câu một hoạt động, câu nào cũng ở hiện tại đơn.", "Cần đủ 2 trạng từ tần suất (usually, often, rarely, never...) và 1 cụm chỉ giờ/buổi: at 6.30, in the evening, on weekdays, at weekends.", "Giới từ thời gian: at + giờ (at six), in + buổi (in the morning), on + thứ/ngày (on Sundays).", "Nối bằng then / after that / before; 3 câu, 18-35 từ."],
  "patterns_vi": ["I usually get up at ___ and ___ .", "I rarely/never ___ before ___ .", "On weekdays/At weekends, I ___ in the evening."],
  "avoid_vi": "Không viết 'at the morning'.",
  "common_errors_vi": ["at the morning → in the morning.", "I am usually go → I usually go (đã có usually thì không thêm am)."]},
 {"id": "G1D2M1",
  "limits": {"min": 14, "max": 40},
  "framework_vi": ["Câu 1 = sự thật lâu dài -> hiện tại đơn: I live in ___ ./ My flat has ___ rooms. (live, have, be: trạng thái).", "Câu 2 = tình huống tạm thời -> hiện tại tiếp diễn + mốc tạm: at the moment, this month, for now, these days.", "Dùng nối tương phản để thấy hai thì đối nhau: but this month / although ___ , at the moment ___ .", "Lỗi hay gặp: 'have' nghĩa 'có' không dùng tiếp diễn (I am having a flat sai), nhưng have + lunch/a haircut được."],
  "patterns_vi": ["I live in ___ with ___ .", "At the moment/This month, I am staying/living ___ because ___ .", "___ is being repaired/painted, so ___ ."],
  "avoid_vi": "Không dùng tiếp diễn cho việc lâu dài (I am living in Hanoi all my life).",
  "common_errors_vi": ["I am having a small flat → I have a small flat.", "I am living here all my life → I have lived here all my life (việc lâu dài không dùng tiếp diễn)."]},
 {"id": "G1D3M1",
  "limits": {"min": 18, "max": 45},
  "framework_vi": ["Ba câu = ba công thức khác nhau của have: (1) have + V3 + for/since, (2) have already + V3, (3) have been + V-ing.", "Câu 1 'đã lâu': for + khoảng thời gian (for two years) hoặc since + mốc (since 2022). Câu 2 'hôm nay đã xong': already đứng giữa have và V3. Câu 3 'tuần này đang làm dở': nhấn quá trình, thêm this week.", "Dùng động từ trạng thái (know, have, live) ở dạng đơn, động từ hoạt động (read, work, study) ở dạng been + V-ing.", "Mỗi câu 8-12 từ; viết 18-35 từ cho cả bài."],
  "patterns_vi": ["I have ___ (V3) for ___ years / since ___ .", "I have already ___ (V3) today.", "I have been ___ (V-ing) ___ this week."],
  "avoid_vi": "Không dùng 'since' với khoảng thời gian và 'for' với mốc.",
  "common_errors_vi": ["I have studied English since two years → for two years.", "I already have done → I have already done.", "I have been read → I have been reading."]},
 {"id": "G1D4M1",
  "limits": {"min": 28, "max": 60},
  "framework_vi": ["Bốn câu = bốn thì, đúng thứ tự để so sánh: (1) hiện tại đơn = thói quen/sự thật, (2) tiếp diễn = tạm thời lúc này, (3) hoàn thành = đã xong/kéo tới nay, (4) hoàn thành tiếp diễn = nhấn độ dài của việc đang làm.", "Mỗi câu một dấu hiệu thời gian riêng: every day / this month / since 2021 hoặc already / for three weeks.", "Chọn động từ phù hợp: know, have, like không dùng tiếp diễn; work, study, learn dùng được cả bốn.", "Mỗi câu 7-10 từ; nối bằng and/but để khỏi lặp chủ ngữ I."],
  "patterns_vi": ["I ___ (V) every ___ .", "This month, I am ___ (V-ing) .", "I have ___ (V3) for/since ___ .", "I have been ___ (V-ing) for ___ ."],
  "avoid_vi": "Không viết 'I am knowing' và không viết 'I am working here since 2020'.",
  "common_errors_vi": ["I am working here since 2020 → I have worked/been working here since 2020.", "I am knowing him → I know him."]},
 {"id": "G1D5M1",
  "limits": {"min": 14, "max": 50},
  "framework_vi": ["Chọn từ trước: ví dụ student/pupil, take an exam, pass, revise, attend. Phân biệt: pupil = học sinh nhỏ, student = sinh viên/học sinh lớn.", "Dùng đúng kết hợp từ: take (không make) an exam, pass = đậu, attend classes (không 'attend to'), revise for a test.", "Câu 1 kể thói quen học bằng hiện tại đơn + trạng từ tần suất; câu 2 nêu việc sắp tới hoặc kết quả, dùng will/hope.", "Mỗi câu có ít nhất một từ mới, đúng từ loại (revise = động từ, revision = danh từ)."],
  "patterns_vi": ["I attend ___ classes at ___ , and I always revise for ___ by ___ -ing.", "I take ___ exams every ___ ; I hope I will pass ___ ."],
  "avoid_vi": "Không dùng 'make an exam' và 'attend to class'.",
  "common_errors_vi": ["I made an exam → I took an exam.", "I attend to the class → I attend the class.", "I will pass the exam = chắc chắn đậu; dùng hope I pass nếu chưa chắc."]},
 {"id": "G1D6M1",
  "limits": {"min": 16, "max": 50},
  "framework_vi": ["Chọn 2 kết hợp từ của bài và đặt đúng giới từ: pay attention to + danh từ/V-ing, make sense of + danh từ, succeed in + V-ing.", "Sau giới từ là V-ing, không phải to V: succeed in passing, pay attention to listening.", "Một câu thêm từ C1 (assess, grasp, notion) và câu kia dùng từ B2 đồng nghĩa (assess ~ evaluate, grasp ~ understand).", "Dùng find it hard to / try to để nói cách học của mình bằng hiện tại đơn."],
  "patterns_vi": ["I find it hard to pay attention to ___ , so I ___ .", "To make sense of ___ , I ___ first.", "I succeeded in ___ -ing ___ by ___ ."],
  "avoid_vi": "Không viết 'succeed to pass' hay 'pay attention listening'.",
  "common_errors_vi": ["succeed to pass → succeed in passing.", "pay attention listen → pay attention to listening.", "make sense it → make sense of it."]},
 {"id": "G1D7M1",
  "limits": {"min": 18, "max": 50},
  "framework_vi": ["Chọn một cặp C1 - B2: assess ~ evaluate, ponder ~ consider. Câu 1 dùng từ C1, câu 2 dùng từ B2 cho cùng ý.", "Nói về quyết định đang cân nhắc: dùng hiện tại tiếp diễn (I am pondering my options) hoặc whether to + V. Hunch là danh từ: have a hunch that + mệnh đề.", "Dùng khung đối lập: I am still ___ , but I have a hunch that ___ .", "Ponder là ngoại động từ: ponder my options, hoặc ponder over/on (không ponder about)."],
  "patterns_vi": ["Before I choose ___ , I need to assess ___ .", "I am still pondering whether to ___ or ___ .", "I have a hunch that ___ , so I will evaluate ___ ."],
  "avoid_vi": "Không viết 'I am having a hunch' hay 'ponder about'.",
  "common_errors_vi": ["ponder about → ponder / ponder over.", "I am having a hunch → I have a hunch (trạng thái, không tiếp diễn)."]},
 {"id": "G1D8M1",
  "limits": {"min": 18, "max": 50},
  "framework_vi": ["Kể một lần ĐÃ QUA nên dùng quá khứ đơn: When I moved to ___ , I felt homesick. Mốc when/last year đặt đầu câu.", "adjust/adapt luôn đi với to: adjust to + danh từ/V-ing. Công thức thời gian: It took me + khoảng thời gian + to V.", "Dùng impolite/homesick như tính từ sau felt/found it: I found it impolite that ___ .", "Hai câu: câu 1 = chuyện gì và cảm giác, câu 2 = bạn thích nghi ra sao."],
  "patterns_vi": ["When I started ___ , I felt ___ because ___ .", "It took me ___ to adjust to ___ .", "At first I found it hard to adapt to ___ -ing."],
  "avoid_vi": "Không viết 'adapt with / adjust with'.",
  "common_errors_vi": ["adjust with → adjust to.", "It took me a month adjusted → It took me a month to adjust.", "I felt homesick with my family → homesick for my family."]},
 {"id": "G1D9M1",
  "limits": {"min": 20, "max": 50},
  "framework_vi": ["Đây là bài TÓM TẮT, không phải viết về bản thân: dùng hiện tại đơn để nói điều bài viết nói (The passage describes..., The writer says...).", "Câu 1 nêu ý chính bằng chủ ngữ mới, câu 2 nêu một lợi ích hoặc hạn chế: ..., although/however ... (tương phản).", "Diễn đạt lại bằng từ của bạn: method thay cho way, intensive, constraint; không chép quá 3 từ liên tiếp.", "Giữ 20-40 từ; không thêm ý kiến cá nhân."],
  "patterns_vi": ["The passage describes how ___ .", "This method ___ , although ___ .", "One constraint is that ___ ."],
  "avoid_vi": "Không chép câu gốc và không viết 'The passage talk/said' (dùng talks/says hoặc describes).",
  "common_errors_vi": ["The text talk about → The text talks about.", "The writer said → The writer says (tóm tắt dùng hiện tại)."]},
 {"id": "G1D10M1",
  "limits": {"min": 20, "max": 55},
  "framework_vi": ["Vẽ sơ đồ ba nhánh trước (học, giao tiếp, cảm xúc), mỗi nhánh một tính từ, rồi mỗi nhánh thành một câu.", "Tính từ ghép phải viết có gạch nối: self-confident, well-organised; dùng sau am/can be, không thêm danh từ nếu không cần.", "Dùng I'd describe myself as + (a/an) + tính từ + person và can be + tính từ cho xu hướng, không tuyệt đối.", "Một câu nêu mặt yếu bằng I wish I were more ___ (dạng were cho điều chưa đúng)."],
  "patterns_vi": ["I'd describe myself as a ___ person, because ___ .", "I can be ___ when ___ .", "I wish I were more ___ ."],
  "avoid_vi": "Không dùng danh từ thay tính từ: 'I am confidence'.",
  "common_errors_vi": ["I am confidence → I am confident.", "I am a self confident → I am a self-confident person (gạch nối).", "I wish I was → I wish I were."]},
 {"id": "G1D11M1",
  "limits": {"min": 22, "max": 60},
  "framework_vi": ["Câu 1 nêu cách đi: I usually go to ___ by + phương tiện (by bus, không có a/the), on foot (không 'by foot'). Thêm it takes ___ .", "Câu 2 nêu một điều hài lòng hoặc phàn nàn bằng từ của bài: convenient, timetable, satisfied with, parking.", "Câu 3 (nếu đề hiểu là ba câu): so sánh bằng more convenient than / cheaper than.", "Dùng because / so để giải thích; buses are rare là sai kiểu Việt, nói there are few buses hoặc buses are infrequent."],
  "patterns_vi": ["I usually go to ___ by ___ , which takes ___ .", "I am (not) satisfied with ___ because ___ .", "It is more convenient than ___ ."],
  "avoid_vi": "Không viết 'go by foot' hoặc 'the traffic is crowded'.",
  "common_errors_vi": ["by foot → on foot.", "by the bus → by bus.", "buses are rare → there are few buses / buses are infrequent.", "crowded traffic → heavy traffic."]}
]
```
Đề xuất schema: thêm `avoid_vi: string` (1 dòng cảnh báo lỗi Việt, hiện sát khung); `frames` có thể dùng chính `patterns_vi`, không cần trường mới. Sửa bài mẫu G1D11M1 và đề D11 ("three sentences").

## 3. Quy tắc thiết kế đề theo dạng (5 giây)
Mọi dạng phải hiện 1 câu mệnh lệnh `task_vi` (<= 12 từ), không dài hơn đề.
| Dạng | Phải hiện | Trường dữ liệu |
|---|---|---|
| Cloze chọn | Câu có ( ), 2-4 chip lựa chọn, 1 câu lệnh "Chọn từ đúng" | stimulus.text, options, task_vi |
| Điền từ gõ (open cloze) | Câu, "1 từ", loại từ cần điền (trợ động từ/giới từ/từ nối) | task_vi, slot_type, word_count |
| Sửa lỗi | Câu GỐC SAI với phần sai đánh dấu, nhiệm vụ "Gõ lại phần in đậm cho đúng" | original_wrong, wrong_span |
| Viết lại câu | Câu gốc, TỪ CHO SẴN dạng chip, số từ cần gõ, phần câu đã cho | source, keyword, word_count |
| Điền từ trong khung | Ngân hàng từ dạng chip (xáo trộn), số chỗ trống, nhắc chia dạng | bank[], inflect_note |
| Chia động từ | (động từ gốc) sát chỗ trống, các thì được chọn | given, allowed_forms |
| Dictation | nút nghe, số câu, nhắc "gõ đúng chính tả" | audio, n_sentences |
| Viết đoạn | Đề, số câu/số từ, 3-5 khung cụ thể, mẫu câu | limits, framework_vi, patterns_vi, avoid_vi |

BEFORE/AFTER (id thật):
1. G1D1F5. Trước: instruction "Gõ từ hoặc cụm từ còn thiếu." + "( ㉠ ) your sister live near here?". Sau: task_vi "Điền trợ động từ (Do/Does/Did) để hoàn thành câu hỏi", chip bank [Do, Does, Did], word_count 1.
2. G1D1KB-1. Trước: chỉ "My dad ( ㉠ ) late on Saturday mornings.". Sau: hiện "Câu gốc sai: My dad **is often getting up** late on Saturday mornings." (gốc suy ra từ common_errors_vi, cần đối chiếu sách); task_vi "Gõ lại phần in đậm cho đúng"; đáp án often gets up.
3. G1D1KCB-2. Trước: instruction nhét "always, present, moment, being, rarely, every, never, time, right, days…". Sau: task_vi "Điền 1 từ chỉ thời gian"; chip bank gồm đủ 15 đáp án của nhóm (always, present, moment, being, rarely, every, most, never, time, right, days, whenever, for, it); câu "Fifteen teachers are teaching here full-time at ( ㉠ )." Đáp án present.
4. G1D6O5-2 ("A degree is a useful ( ㉠ )."). Sau: chip nghĩa "bằng cấp: tấm bằng như một thứ gì đó có giá trị (n.)" và chữ cái đầu "q___".

## 4. Ưu tiên sửa
P0 (tác động lớn, công sức nhỏ):
- Tự động (script từ days.txt/build.py): (a) instruction theo dạng, suy ra từ đáp án và mẫu (động từ trong ngoặc, trợ động từ, giới từ), sửa cho 19 mục F + 16 mục W3; (b) đặt nghĩa Việt của W: vào `context_vi` cho 31 mục Ôn lại và bỏ 11 mục trùng D7O5; (c) sinh `bank` = hợp các accepted của nhóm cho KCB, KXL, KXC, KXB, KD, KC3, KF, KA18 (khoảng 100 mục), tạm thời đưa vào `context_vi` (chưa cần đổi UI); (d) thêm biến thể rút gọn I've/they're/she's và recognize/recognise vào accepted (14 mục); (e) xử lý dấu nháy trong `normalizeAnswer` (hiện xóa dấu nháy nên "'re" thành "re") hoặc thêm đủ biến thể vào accepted.
- Viết tay: 18 câu gốc sai (KB, KU3C1, KC4) từ sách; 13 bài Viết (bản ở mục 2); sửa bài mẫu D11.
P1: chip ngân hàng từ và chip từ cho sẵn (đổi `WriteFill.tsx`, thêm `bank`, `keyword`); liên kết KLT/KTY tới bài nghe/đọc (script, gắn id + nút "xem đoạn"); viết tay 14 câu còn thiếu của KXI; rubric 10 bài Viết (script theo mẫu).
P2: gom câu rời thành đoạn văn trong W4 (41 mục); rà 14 mục tích cực/tiêu cực và 10 mục "tìm thông tin" ở reading; thêm kiểm tra chấm tự động "đề có đủ trường" vào validator `lesson_seed.py` để lỗi không quay lại.

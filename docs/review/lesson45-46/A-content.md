# Reviewer A — Rà soát NỘI DUNG bài 45 (G1 Ngày 2) và 46 (G1 Ngày 3) so với chuẩn bài 44

Nhiệm vụ: đối chiếu seed g1-d2-*/g1-d3-* với g1-d1-* (bài 44), QUALITY_LESSON44.md, lesson44-knowledge-audit.md, lecture_d1.py, WEEK1_PLAN.md; tìm lỗi kiến thức, khoảng cách chất lượng, và liệt kê tài liệu cần người dùng cung cấp. Không sửa seed.
Phạm vi đã đọc: 717 bài tập G1 (dump /tmp/g1ex.json), days.txt D2 (dòng 150–223), D3 (224–297), ghi chú thầy Minh (recordings b1_02–b1_05, chuyên đề 1.2–1.4), OCR Destination B2, IELTS Grammar (Unit 1, 3), Complete IELTS C1&C2 Unit 1 (PDF 009–013).
Lưu ý độ chắc chắn: lỗi đánh dấu [X] đã đối chiếu trực tiếp với sách/đáp án; [?] là nghi vấn cần xác nhận bằng ảnh trang sách.

## 1. Kết luận ngắn
- Bài 45/46 hiện ở mức "bài sinh tự động từ sách + thẻ ngữ pháp tóm tắt". Bài 44 ở mức "bài giảng viết tay + cảnh SVG + IPA OALD + nói thử Azure + test chất lượng". Khoảng cách chủ yếu là **thiếu lớp giảng viết tay**, không phải thiếu bài tập.
- Phần lớn tài liệu gốc ĐÃ có trong /mnt/user-data/uploads và OCR. Cái còn thiếu là **bản chép nguyên văn / audio các đoạn thầy Minh** và vài quyết định sư phạm (mục 5).

## 2. Khoảng cách so với bài 44

| # | Hạng mục chuẩn 44 | Bài 45 | Bài 46 | Mức |
|---|---|---|---|---|
| G1 | Lecture viết tay (lecture_d1.py) theo Mayer: mỗi ý một màn, có ví dụ → quy tắc | Chưa có lecture_d2 | Chưa có lecture_d3 | Nặng |
| G2 | Cảnh SVG minh hoạ (trục thời gian, "now" trap, state vs action) | Không | Không (cần timeline since/for, 2 câu hỏi của perfect continuous) | Nặng |
| G3 | IPA OALD cho từ khoá + mục phát âm | Không | Không (b1_05 có breath/breathe/breadth, âm cuối /s/ /t/ /θ/ chưa vào bài) | Vừa |
| G4 | "Nói thử" shadowing có chấm Azure | Chưa | Chưa (nên có: câu present perfect, "It's the first time I've…") | Vừa |
| G5 | Thẻ ngữ pháp viết theo hình dạng sách (bảng 5 nhóm stative; bảng perfect simple vs continuous) | Thẻ tóm tắt, chưa có bảng 5 nhóm động từ trạng thái | Thẻ tóm tắt, chưa có bảng so sánh simple/continuous và cấu trúc "It's the first time" | Nặng |
| G6 | Quy tắc "một chiều" của thầy (Unit_1_Present_tense.docx) | Thiếu | n/a | Vừa |
| G7 | Bẫy "now" (b1_02), always + V-ing (cảm xúc), usually/often không đi với continuous | Có rải rác, chưa thành bài giảng | n/a | Vừa |
| G8 | Hai câu hỏi của present perfect continuous (kéo dài/kết quả), since/for, "I have already eaten pizza" (b1_03–b1_04) | n/a | Thiếu | Nặng |
| G9 | Emphatic do/does (b1_05) | Thiếu | Thiếu (đặt ở D3 hay D2 cần quyết định) | Nhẹ |
| G10 | Kiểm tra bằng tests/test_lesson44_quality.py (cổng chất lượng) | Chưa có test tương đương | Chưa có | Nặng |
| G11 | Bảng audit kiến thức (docs/review/lesson44-knowledge-audit.md) | Mục 3–4 dưới đây là bản đầu | idem | — |
| G12 | Ba tầng bài tập (nhận biết → điền → viết) với lỗi thường gặp có giải thích | Bài tập sách dày, nhưng "common_errors" nhiều mục chung chung | idem | Vừa |

Đối chiếu WEEK1_PLAN: Day 2 thẻ 2.1–2.7, Day 3 thẻ 3.1–3.7 — mọi thẻ đều có bài tập tương ứng, nhưng thẻ 2.x/3.x chưa có lecture đi kèm. Cần kiểm tra lại thứ tự thẻ khớp với trình tự dạy của thầy (xem 3.5).

## 3. Lỗi kiến thức / dữ liệu (theo kiểu audit 44)

### 3.1 Lỗi nặng — đáp án sai hoặc bỏ sót dữ liệu của sách
| ID | Vấn đề | Cách sửa |
|---|---|---|
| G1D3KU3C1-1, -2 | [X] Câu gốc của sách (IELTS Grammar Unit 3 C1, thư xin học Zoology) có trạng từ; seed đã bỏ trạng từ khi tách câu, nên đáp án thay đổi nghĩa (-1: "As you ㉠ (see) in Section A…"; -2: "I ㉠ (receive) the results of my recent exams…" — mất "just" so với câu -3 "have just received"). Học viên không thể suy ra thì đúng nếu thiếu tín hiệu. | Khôi phục trạng từ nguyên văn từ trang 24 sách (cần ảnh trang, xem mục 5 — Q1). Đối chiếu đáp án p.221. |
| G1D3KU3C1 (cả bộ) | [X] Câu -3 và -7 trùng nội dung/trạng từ với -2 và -4 sau khi tách: bài "sửa thì" thành bài điền đáp án đã lộ. Cùng với nhận xét ở G1D4KC4 (câu gốc sai ở backlog). | Dựng lại bộ 7 câu từ nguyên bản, giữ câu sai gốc nếu sách có. |
| Thẻ "page" | [X] Nhãn trang sai lệch 1: Destination B2 PDF = trang in + 1; chart Unit 3 in ở tr.22 (PDF 035). Một số thẻ ghi số PDF như trang in (hoặc ngược lại). | Quét toàn bộ nhãn "tr./p." trong days.txt D2–D3 và chuẩn hoá về trang in. |
| G1D3KG-* | [X] Bộ chọn từ ("Circle the correct word", sách Complete IELTS Ex G): sách cho phép "if both are correct, circle both". Seed dùng một lựa chọn duy nhất ở vài câu (VD "They've filled / been filling…", "I've stood / been standing…") nên có hai đáp án hợp lệ nhưng chỉ chấp nhận một. | Cho phép đáp án kép như sách, hoặc đổi sang dạng chọn nhiều đáp án; bổ sung giải thích vì sao cả hai được. Cần đáp án p.281 (xem mục 5). |
| G1D2KF-2 | [X] Điền "it ㉠ possible…" (be): chấp nhận cả "'s" và "is" nhưng rubric chấm theo nhóm accepted không bao gồm dạng rút gọn ở mọi blank; không đồng nhất giữa các câu cùng bộ. | Chuẩn hoá accepted: luôn nhận dạng đầy đủ + rút gọn. |

### 3.2 Lỗi vừa — giải thích / khẳng định quá khái quát
| ID | Vấn đề |
|---|---|
| G1D2KC-2 ("see") | [X] Giải thích "see = state verb nên không dùng continuous" quá cứng: sách (Complete IELTS Unit 1 E) và thầy nêu "see" = gặp/hẹn dùng được continuous (I'm seeing the doctor); chỉ "see = nhìn thấy" là trạng thái. Thầy còn mẹo can see/can smell. |
| Thẻ ngữ pháp D2 | [X] Câu kiểu "động từ chỉ trạng thái KHÔNG BAO GIỜ dùng thì tiếp diễn" — sai về học thuật; sách nói "generally", nhiều động từ (have, think, feel, look, taste, smell, weigh, consider…) có dùng continuous khi là hành động. Cần nói theo nghĩa, không theo động từ. |
| Thẻ D2 | [X] "always + V-ing = phàn nàn" quá hẹp: thầy dạy cả sắc thái cảm xúc (khó chịu/ngạc nhiên/thân mật), không chỉ phàn nàn. |
| Thẻ D2 | [?] "usually/often không đi với continuous" — thầy nói thêm nhánh "almost every weekend" vẫn có thể với continuous khi diễn tả giai đoạn tạm thời; thẻ hiện không có ngoại lệ. |
| Thẻ D3 | [?] Nói "since + mốc, for + khoảng" nhưng thiếu: thêm "It's the first time + present perfect", "ever/never/just/already/yet/still", và khác biệt Anh–Mỹ (Complete IELTS p.009: Mỹ hay dùng past simple, "gotten"). |
| Thẻ D3 | [?] Hai "câu hỏi" của present perfect continuous (thầy b1_03–b1_04) bị gộp thành một dòng "nhấn mạnh quá trình". |
| Ví dụ KA/KB D3 | [?] Một số câu ví dụ present perfect đi kèm mốc quá khứ rõ ràng (yesterday, last year) trong phần "so sánh" mà không đánh dấu là phản ví dụ — dễ gây hiểu nhầm. Cần đọc lại từng thẻ (chưa rà hết từng chữ). |

### 3.3 Điểm nhỏ
- Một số `common_errors` dùng cùng một câu mẫu cho nhiều blank (không phản ánh lỗi thật của từng câu).
- Tên/tiêu đề bài tập tiếng Việt chưa thống nhất (VD "Điền động từ", "Sửa thì", "Điền động từ trong khung").
- Câu chỉ dẫn chép nguyên văn nhưng thiếu đơn vị quy chiếu ("Hỏi từng chỗ: đây là trạng thái hay hành động?") — hay nhưng chỉ có ở KF, không có ở KC.

### 3.4 Điều ĐÃ ĐÚNG (không phải sửa)
- Đáp án IELTS Grammar Unit 1 C3 và Unit 3 C1–C4 khớp key p.221 trong các blank đã đối chiếu (trừ mục 3.1).
- Bảng 5 nhóm động từ trạng thái của thầy khớp bảng Complete IELTS p.009 (communication, thinking, existence, emotions, perception, possession).
- Bài đọc Nazca (KF) và bài năng lượng (KC3) khớp văn bản Destination B2 p.10.

### 3.5 Cần quyết định sư phạm (không phải lỗi)
1. Thứ tự dạy D2: thầy dạy **hai trục (ngữ pháp / ngữ nghĩa) → bẫy "now" → always+V-ing → state verbs**; seed đang đi theo thứ tự sách. Nên theo thầy và dùng sách làm bài tập.
2. D3: thầy dạy present perfect trước, perfect continuous sau, với "one-way replacement rule" (có thể thay simple bằng continuous một chiều, ngược lại thì không). Seed chưa có quy tắc này.
3. Emphatic do/does và breath/breathe/breadth (b1_05) đặt ở D3 hay làm bài phát âm riêng.

## 4. Mức sẵn sàng theo bài
| Bài | Bài tập sách | Thẻ | Lecture | SVG | IPA/Nói | Test | Đánh giá |
|---|---|---|---|---|---|---|---|
| 44 (chuẩn) | Đủ, đã audit | Hand-written | Có | Có | Có | Có | Chuẩn |
| 45 | Đủ (C1 Unit 1 + Destination p.10 F/G…) | Cần viết lại | Chưa | Chưa | Chưa | Chưa | ~40% |
| 46 | Đủ nhưng KU3C1 lỗi | Cần viết lại | Chưa | Chưa | Chưa | Chưa | ~35% |

## 5. Tài liệu cần người dùng cung cấp (ưu tiên)

Nguyên tắc: các sách đã có PDF/OCR trong repo/uploads. Chỉ xin những gì OCR không thể thay thế. "Trong repo?" = đã tìm thấy trong /mnt/user-data/uploads hoặc OCR.

### 5.1 BẮT BUỘC (không có thì không viết lecture đúng giọng thầy được)
| Q | Tài liệu | Mục đích | Trong repo? |
|---|---|---|---|
| Q1 | Ảnh chụp/scan **IELTS Grammar Unit 3, tr.22–24** (chart + C1–C4), đặc biệt **bản gốc bài C1** (thư Zoology) | Khôi phục trạng từ bị mất ở G1D3KU3C1-1/-2; kiểm tra G1D3KU3C1 và G1D4KC4 | Có OCR (grammar), nhưng OCR đã làm mất trạng từ → cần ảnh gốc |
| Q2 | **Bản chép nguyên văn hoặc file ghi âm** các đoạn b1_02, b1_03, b1_04 (thầy Minh dạy present simple/continuous, present perfect, perfect continuous) | Viết lecture_d2/d3 đúng cách giảng của thầy (ví dụ, câu hỏi, bẫy) thay vì tóm tắt | Có tóm tắt + một phần transcript (f655ac6d dòng 115–225); chưa đủ nguyên văn |
| Q3 | **Hình bảng/hình vẽ thầy viết trên bảng** (hai trục, timeline since/for, sơ đồ one-way rule) | Dựng SVG đúng với cách thầy vẽ | Không |
| Q4 | **Complete IELTS C1&C2 Unit 1 key, tr.281 và Unit 3 key tr.283** | Đáp án chính thức cho Ex A–J (D2/D3) và G1D3KG (chọn kép) | Chưa tìm thấy key trang này trong OCR; cần xác nhận |

### 5.2 NÊN CÓ
| Q | Tài liệu | Mục đích | Trong repo? |
|---|---|---|---|
| Q5 | Ghi âm **b1_05** (breath/breathe/breadth, âm cuối /s/ /t/ /θ/, emphatic do/does) | Bài phát âm D3 + shadowing | Có tóm tắt; thiếu audio/transcript nguyên văn |
| Q6 | File **audio của sách ngữ pháp** (nếu có) hoặc xác nhận cho phép dùng giọng TTS/OALD làm mẫu | Mẫu nói cho "Nói thử" | Chưa rõ |
| Q7 | **Destination B2 tr.10–11 (ảnh)** — Ex F/G nếu có Ex khác chưa dùng | Kiểm tra page tag lệch 1 và độ đầy đủ | Có OCR; ảnh để kiểm chéo |
| Q8 | **Vocabulary nhóm chủ đề** gắn D2/D3 (nếu thầy có từ vựng theo bài) | Đưa vào mục từ vựng của bài như bài 44 | Chưa kiểm |

### 5.3 TUỲ CHỌN
| Q | Tài liệu | Mục đích |
|---|---|---|
| Q9 | Ghi chú/video thầy về emphatic do/does & contrast (nếu ngoài b1_05) | Nội dung phụ |
| Q10 | Phản hồi của học viên thật về bài 44 (chỗ khó/bỏ qua) | Điều chỉnh độ dài lecture |
| Q11 | Quyết định mục 3.5 (3 câu hỏi) | Chốt trình tự bài |

## 6. Việc phía Claude có thể làm ngay không cần tài liệu mới
1. Sửa các lỗi 3.1 trừ KU3C1 (cần Q1) và KG (cần Q4); chuẩn hoá accepted; quét nhãn trang.
2. Viết lại thẻ D2/D3 theo hình dạng sách và nguồn thầy (bảng 5 nhóm, bảng simple vs continuous, "It's the first time").
3. Soạn khung lecture_d2/d3 (cấu trúc màn, ví dụ, câu hỏi) từ ghi chú hiện có; điền chi tiết sau khi nhận Q2/Q3.
4. Thêm IPA OALD cho từ khoá; thêm 6–8 câu "Nói thử" mỗi bài.
5. Viết tests/test_lesson45_46_quality.py nhân bản cổng của 44.

## 7. Ghi chú trạng thái
- Báo cáo này chưa commit (thư mục làm việc hiện không phải git repo). Không sửa seed.
- [?] chưa kiểm chứng đầy đủ vì chưa có ảnh trang gốc; sẽ xác nhận khi nhận Q1/Q4.

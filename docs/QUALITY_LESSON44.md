# Lesson 44 (G1 · Ngày 1 · Hiện tại đơn): chuẩn chất lượng, cách đo, kết quả

Cập nhật 2026-11-11. Bài này là bài mẫu: mọi quyết định thiết kế ghi rõ dựa vào đâu, đo bằng gì, kết quả bao nhiêu,
và cái gì CHƯA chứng minh được. Các cổng tự động nằm trong `tests/test_lesson44_quality.py`.

## 1. Thay đổi so với bản trước (số đo thật)

| Hạng mục | Trước | Sau | Cách đo |
|---|---|---|---|
| Kịch bản bài giảng | mẫu cố định đọc từng trường (từ → nghĩa → mẫu → cách dùng → ví dụ) | biên soạn tay: câu hỏi → thí nghiệm → kết luận → nói lại | `scripts/g1/lecture_d1.py` |
| Thời lượng buổi 1 / buổi 2 | 373 s / 195 s | 376 s / 275 s | bản ghi thật (Chirp 3 HD + Azure), 2026-11-11 |
| Quãng im để nhắc lại sau một câu tiếng Anh | cố định 0,7 s | 0,4 s + 0,545 s mỗi từ (câu 11 từ: 6,4 s; một từ: 1,2 s) | `lecture_voice.english_repeat_gap_ms` |
| Thời gian dành cho tiếng Anh + quãng nhắc lại | buổi 1: 84 s (22%) | buổi 1: 141 s (38%); buổi 2: 140 s (51%) | cộng theo timeline của bản ghi |
| Câu tiếng Anh bị đổi giọng giữa câu | có ("Hoa" giọng Việt, phần còn lại giọng Anh) | 0 | test `an_english_sentence_is_read_by_one_voice` |
| Câu thừa của mẫu ("0 từ vựng", "Phần một", "Nghĩa là", "Lời thầy:", "Bạn nhắc lại nhé") | có | 0 | test `no_template_boilerplate_is_read_out` |
| Slide ngữ pháp | 1 loại thẻ chữ, chép lại lời đọc | 5 hình SVG, từng phần hiện theo đúng dòng đang đọc | `LectureScenes.tsx`, test `every_piece_of_a_picture_is_brought_in_by_a_line` |
| Gợi ý «Nói theo» và «Tự dừng để nói theo» | không bao giờ bật với tiếng Anh (app cắt theo chữ Hàn) | bật đúng 24 / 18 chỗ | `shadow_runs`, trả về trong `/lecture-slides` |
| Bước «Nói thử» | tự bấm "Tôi đã nói" | ghi âm, Azure chấm từng từ (0–100) | `POST /me/speech/assess` |
| Chữ tiếng Anh trên giao diện | gắn `lang="ko"`, font Hàn, `word-break: keep-all` | `lang="en"` | `Rich.tsx` |
| Phiên âm | không có | 4/6 từ, theo Oxford Advanced Learner's Dictionary (BrE) | `lecture_d1.PRON` |
| Buổi 2 | 14 câu luyện | 7 câu; phần vận dụng thành buổi 3 (7 câu) | `lecture_d1.reshape` |

## 2. Dựa vào đâu

| Quyết định | Căn cứ | Độ mạnh của căn cứ |
|---|---|---|
| Hình và lời đi cùng lúc, từng phần hiện khi được nói | Temporal contiguity, Mayer (2021): trung vị d = 1,31, 8/8 thí nghiệm | mạnh |
| Slide không in lại lời giảng; chỉ in câu tiếng Anh đang học + nhãn vài chữ | Coherence d = 0,86 (18/19). Redundancy: d = 0,86 trong tổng hợp 2014 nhưng chỉ 0,10 (8/12) trong tổng hợp 2021 | coherence mạnh; redundancy YẾU, không dùng làm lý do chính. Câu tiếng Anh vẫn in ra vì đó là nội dung cần học, không phải chú thích |
| Một phần "đang nói" duy nhất ở độ tương phản cao | Signaling d = 0,70 (26/28) | khá |
| Học 5 chữ nhãn hộp trước thí nghiệm | Pre-training d = 0,46 | vừa |
| Buổi 4–7 phút, chia 3 buổi, người học tự bấm sang bước | Segmenting d = 0,67–0,77 | khá |
| Giọng xưng hô trò chuyện ("bạn"), câu hỏi mở đầu | Personalization d = 0,79 | khá |
| Kết buổi bằng nói lại các câu, rồi 5–7 câu hỏi ngay | Luyện truy hồi (testing effect) | có cơ sở rộng trong tâm lý học nhận thức; CHƯA trích số liệu riêng ở đây |
| Mục tiêu ngữ pháp: đổi thì theo điều muốn nói | IELTS Speaking band descriptors (bản công khai): band 6 "uses a mix of simple and complex structures, but with limited flexibility"; band 7 "uses a range of complex structures with some flexibility" | nguồn chính thức |
| Điểm phát âm không gọi là band | Band descriptors chấm phát âm khi nói tự do (độ dễ hiểu, các "pronunciation features"); Azure chấm đọc theo câu mẫu | nguồn chính thức + tài liệu Azure |
| Nội dung và thứ tự giảng | Tài liệu tuần 1 của thầy Minh (thí nghiệm "ăn cam", bỏ trạng từ, mẹ trách, lời nói dối, bốn cách đáp, do/does); hai câu trích nguyên văn | test `the_teachers_words_are_verbatim` |
| Phiên âm | oxfordlearnersdictionaries.com, đọc 2026-11-11: habit /ˈhæbɪt/, permanent /ˈpɜːmənənt/, frequency /ˈfriːkwənsi/, emphasize /ˈemfəsaɪz/ | từ điển |

Các effect size trên đo ở bài học khoa học cho sinh viên, phần lớn không phải học ngoại ngữ. Chúng là lý do để chọn thiết kế,
KHÔNG phải bằng chứng rằng bài 44 dạy tốt hơn. Bằng chứng đó chỉ có từ mục 5.

## 3. Cổng tự động (chạy mỗi lần build)

| Cổng | Ngưỡng | Kết quả |
|---|---|---|
| Thời lượng theo kế hoạch giọng | 3,5–7,0 phút/buổi | 6,3 và 4,6 phút |
| Mở đầu bằng câu hỏi; quy tắc chỉ xuất hiện sau ít nhất 2 phần của thí nghiệm; kết bằng nói lại | bắt buộc | đạt |
| Mọi phần của hình đều có một dòng đọc đưa nó ra | 100% | đạt |
| Câu tiếng Anh: một giọng, không có chữ Việt trong đoạn giọng Anh | 0 vi phạm | đạt |
| Câu sai ngữ pháp ("He does works hard") chỉ nghe, không bao giờ bắt nhắc lại | bắt buộc | đạt |
| Câu thừa của mẫu | 0 | đạt |
| Lời thầy nguyên văn | 2/2 câu | đạt |
| Phiên âm chỉ lấy từ mục từ đã tra | state, fact để trống | đạt |
| Quãng nhắc lại đủ dài | ≥ 1,2× thời gian đọc câu | đạt |
| Seed hợp lệ, mỗi câu hỏi thuộc đúng một buổi | 0 lỗi | đạt |

Bộ test toàn repo: 1.494 đạt, 6 hỏng. Cả 6 đã hỏng trên `main` trước thay đổi này (chúng đếm cứng 42 bài B1, nay có 54 bài).

## 4. Kiểm chứng chấm phát âm (Azure, chạy thật 2026-11-11)

Giọng tổng hợp en-GB đọc, rồi đưa vào `azure_pron.assess`:

| Câu mẫu | Câu được đọc | Accuracy | Completeness | Mức | Từ yếu |
|---|---|---|---|---|---|
| I do like fish! | đúng câu | 100 | 100 | good | — |
| The bus is slow, but it does stop near my office. | đúng câu | 100 | 100 | good | — |
| I do like fish! | "I like dish." | 71 | 75 | retry (thiếu từ) | do |
| Yes, I have played badminton since last year. | "Yes, I play badminton." | 50 | 50 | retry | have, since, last, year |

Giới hạn đã thấy: "dish" được nghe thành "fish" (chấm theo câu mẫu nên máy thiên về câu mẫu); mới thử bằng giọng máy,
CHƯA thử bằng giọng người Việt. Ngưỡng 80/60 là do Haru đặt, Azure không công bố ngưỡng; cần chỉnh theo dữ liệu thật.

## 5. Chưa chứng minh được, và cách chứng minh

1. **Bài mới có giúp học tốt hơn không: chưa biết.** Hiện có 1 người học. Chỉ số đã gắn: `lecture_complete`, `lecture_replay`,
   `audio_seek`, `say_score`, `first_try`, `step_abandon`. So sánh trước/sau trên: tỷ lệ nghe hết buổi; số lần tua mỗi phút;
   tỷ lệ đúng ngay lần đầu của 5 câu sau buổi 1 và 7 câu sau buổi 2; accuracy trung bình ở «Nói thử». Với một người học, đọc
   các con số này như nhật ký, không như thống kê.
2. **Chất lượng âm thanh nghe bằng tai: chưa ai nghe.** Bản ghi đã tạo được và timeline đủ (79/79 và 61/61 đoạn), nhưng
   ngữ điệu giọng Việt, chỗ chuyển giọng ở "IELTS", "do", "does" cần người nghe.
3. **Ba hình (ba sự thật, trục bốn thì, do/does) chưa được xem bằng mắt.** Cả năm hình đã dựng ra HTML đủ nội dung bằng `react-dom/server`; hai hình đầu đã xem trên màn 375 px tại `/preview/lecture`.
4. **Ghi âm trên điện thoại thật** (Safari iOS, Chrome Android) chưa thử.
5. **Phiên âm của `state`, `fact`** chưa tra được mục từ nên để trống.

"""Days 5 and 6 of week 1: education vocabulary. Words of Destination B2 Unit 18 (Education and learning) plus nine C1 words
anchored to simple B2 words the way the teacher does it (assess = evaluate, baffle = confuse, plausible = reasonable...).
Each word: (headword, pos N/V/A/X, meaning_vi, example_en, example_vi). Examples are written for this course."""
from __future__ import annotations

DAYS = {
    5: {
        "stage": "b2",
        "title": "Education vocabulary 1: school, exams and study verbs", "title_vi": "Từ vựng giáo dục 1: trường học, thi cử và cụm động từ",
        "goal": "Phân biệt các cặp từ dễ nhầm về trường học và thi cử (pupil/student, pass/take, speak/talk) và dùng được 7 cụm động từ học tập.",
        "ielts": "Chủ đề giáo dục xuất hiện ở Speaking Part 1 và 2, ở Writing Task 2 và ở nhiều bài Reading/Listening. Các cặp từ này là chỗ thí sinh Band 6 hay nhầm.",
        "book": [("Destination B2", "113", "A", 13, 20), ("Destination B2", "113", "B", 10, 10), ("Destination B2", "113", "C", 7, 10), ("Destination B2", "114", "D", 6, 10)],
        "sittings": [
            ("Trường học và thi cử", [
                ("pupil", "N", "học sinh (ở trường, nhỏ tuổi)", "Our class has thirty pupils.", "Lớp chúng tôi có ba mươi học sinh."),
                ("student", "N", "sinh viên, người đi học", "She is a student at the University of Hanoi.", "Cô ấy là sinh viên Đại học Hà Nội."),
                ("achieve", "V", "đạt được (mục tiêu)", "He achieved his goal of passing the exam.", "Anh ấy đạt được mục tiêu đỗ kỳ thi."),
                ("qualification", "N", "bằng cấp, chứng chỉ để làm một nghề", "A degree is a useful qualification.", "Bằng đại học là một bằng cấp hữu ích."),
                ("certificate", "N", "giấy chứng nhận", "I received a certificate after the course.", "Tôi nhận được giấy chứng nhận sau khóa học."),
                ("degree", "N", "bằng đại học", "She has a degree in physics.", "Cô ấy có bằng đại học ngành vật lý."),
                ("measure", "V", "đo lường (mức độ)", "It is hard to measure intelligence.", "Khó đo trí thông minh."),
                ("recognise", "V", "nhận ra", "I did not recognise my old teacher.", "Tôi không nhận ra thầy giáo cũ."),
                ("task", "N", "nhiệm vụ được giao", "Our task is to design a poster.", "Nhiệm vụ của chúng tôi là thiết kế một tấm áp phích."),
                ("subject", "N", "môn học, chủ đề", "Maths is my favourite subject.", "Toán là môn học yêu thích của tôi."),
            ]),
            ("Cụm động từ học tập", [
                ("get on with", "X", "tiếp tục làm việc gì", "Please get on with your work.", "Hãy tiếp tục làm bài của em."),
                ("sail through", "X", "vượt qua rất dễ dàng", "She sailed through the exam.", "Cô ấy vượt qua kỳ thi rất dễ dàng."),
                ("get at", "X", "cố nói, ám chỉ", "I did not understand what he was getting at.", "Tôi không hiểu anh ấy muốn nói gì."),
                ("come round", "X", "đổi ý, bị thuyết phục", "After a long talk, he came round to our idea.", "Sau cuộc nói chuyện dài, anh ấy đổi ý theo ý chúng tôi."),
                ("cross out", "X", "gạch bỏ", "Cross out the wrong answer.", "Hãy gạch bỏ đáp án sai."),
                ("keep up with", "X", "theo kịp", "It is hard to keep up with the class.", "Thật khó theo kịp cả lớp."),
                ("catch on", "X", "hiểu ra", "He caught on quickly.", "Anh ấy hiểu ra rất nhanh."),
            ]),
        ],
    },
    6: {
        "stage": "b2",
        "title": "Education vocabulary 2: collocations, word families and C1 anchors", "title_vi": "Từ vựng giáo dục 2: kết hợp từ và họ từ",
        "goal": "Dùng đúng các kết hợp từ và giới từ về học tập (pay attention, make sense of, succeed in) và dùng đúng họ từ (scholarship, solution, revision).",
        "ielts": "Kết hợp từ chính xác được tính ở tiêu chí Lexical Resource. Họ từ đúng (behave → behaviour, revise → revision) cũng ăn điểm Grammatical Range and Accuracy.",
        "book": [("Destination B2", "114", "E", 14, 15), ("Destination B2", "115", "F", 8, 8), ("Destination B2", "115", "G", 8, 10), ("Destination B2", "115", "H", 8, 10), ("Destination B2", "115", "I", 10, 12)],
        "sittings": [
            ("Kết hợp từ và họ từ", [
                ("pay attention", "X", "chú ý", "You should pay attention in class.", "Em nên chú ý trong lớp."),
                ("make sense of", "X", "hiểu được", "I cannot make sense of this sentence.", "Tôi không hiểu được câu này."),
                ("make up your mind", "X", "quyết định", "I cannot make up my mind about the course.", "Tôi chưa quyết định được về khóa học."),
                ("see the point of", "X", "thấy được ích lợi của", "I do not see the point of this rule.", "Tôi không thấy ích lợi của quy định này."),
                ("be capable of", "X", "có khả năng làm gì", "She is capable of doing very well.", "Cô ấy có khả năng làm rất tốt."),
                ("succeed in", "X", "thành công trong việc gì", "He succeeded in passing the test.", "Anh ấy thành công trong việc vượt qua bài kiểm tra."),
                ("congratulate on", "X", "chúc mừng về", "We congratulated her on her results.", "Chúng tôi chúc mừng cô ấy về kết quả."),
                ("settle for", "X", "chấp nhận (thứ kém hơn)", "He had to settle for a smaller college.", "Anh ấy phải chấp nhận một trường nhỏ hơn."),
                ("scholarship", "N", "học bổng", "She won a scholarship to study abroad.", "Cô ấy giành học bổng đi du học."),
                ("solution", "N", "lời giải, giải pháp", "Can you find a solution to this problem?", "Bạn tìm được lời giải cho bài này không?"),
                ("revision", "N", "việc ôn tập", "Revision is important before an exam.", "Ôn tập rất quan trọng trước kỳ thi."),
                ("behaviour", "N", "cách cư xử", "His behaviour in class was very good.", "Cách cư xử của cậu ấy trong lớp rất tốt."),
                ("illiteracy", "N", "nạn mù chữ", "Illiteracy is still a problem in some countries.", "Nạn mù chữ vẫn là vấn đề ở một số nước."),
            ]),
            
        ],
    },
}


from day7 import DAY as _DAY7  # noqa: E402

DAYS[7] = _DAY7


DAYS[5]["my"] = [{"vi": "Chọn 5 đến 10 từ hôm nay bạn thích nhất rồi viết về cuộc sống học tập của chính bạn. Dùng ít nhất hai từ, ví dụ pupil/student, pass/take an exam, attend, revise.",
                  "en": "Write two sentences about your own school or study life using words from today.",
                  "model": "I take an exam every month, and I always revise the night before. I hope I will pass the next one."}]
DAYS[6]["my"] = [{"vi": "Dùng ít nhất hai kết hợp từ của hôm nay (ví dụ pay attention to, make sense of, succeed in) để nói về cách bạn học. Một câu nên có một từ C1 trong bài (ví dụ assess, grasp, notion).",
                  "en": "Write two sentences about how you study, using collocations from today.",
                  "model": "I find it hard to pay attention to long lectures, so I make notes to make sense of them. I try to grasp the main idea first."}]

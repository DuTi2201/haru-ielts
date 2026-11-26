"""Week 2 · Day 7 (build day 27): careful listening, "The Luddites" (Cambridge IELTS 18, Test 3, Listening Part 3,
questions 21-30; questions pp. 58-59, audioscript pp. 111-112, key p. 123).

Two students talk about a seminar on automation and the future of work: the Luddites (21-22), predictions they doubt
(23-24), and what they say about six jobs (25-30). The script is the book's, word for word; the app reads it with two
synthetic voices (M = young man, F = young woman), as on Week 1 Day 7.

The method follows the course's listening work (Week 1 syllabus, phase 1: listen slowly, study each sentence and the
paraphrase between question and recording; the answer table "paraphrase, traps"; session 3: go over only the right
answer so a wrong one does not stay in the memory): read the questions first and guess how they may be said, listen
for who speaks and for the point they settle on, watch the time each comment refers to.
Questions 21-22 and 23-24 (choose two) are split as on Week 1 Day 7: each item leaves out the other right answer.
Questions 25-30 have seven comments; the schema allows five options, so each job offers five of them (the book's
letters kept), and a comment that could be argued for that job is left out (C for bank clerks, G for hairdressers).
"""
from __future__ import annotations

C18 = "Cambridge IELTS 18, Test 3"

TURNS = [
    ("M", "That seminar yesterday on automation and the future of work was really good, wasn't it? Looking at the first industrial revolution in Britain in the 19th century and seeing how people reacted to massive change was a real eye-opener.",
     "Buổi seminar hôm qua về tự động hóa và tương lai của việc làm hay thật, nhỉ? Nhìn lại cuộc cách mạng công nghiệp đầu tiên ở Anh vào thế kỷ 19 và thấy người ta phản ứng thế nào trước một thay đổi lớn đúng là mở mang tầm mắt."),
    ("F", "Yes. It was interesting to hear how people felt about automation then and what challenges they faced. I didn't know that first started with workers in the textile industry.",
     "Ừ. Thú vị khi nghe người thời đó cảm thấy thế nào về tự động hóa và họ gặp những khó khăn gì. Tôi không biết là chuyện đó bắt đầu từ công nhân ngành dệt."),
    ("M", "With those protesting workers called the Luddites destroying their knitting machines because they were so worried about losing their jobs.",
     "Ừ, những công nhân phản đối, gọi là người Luddite, đã đập phá máy dệt kim vì quá sợ mất việc."),
    ("F", "Yes, and ultimately, they didn't achieve anything. And anyway, industrialisation created more jobs than it destroyed.",
     "Ừ, và rốt cuộc họ chẳng đạt được gì. Mà dù sao thì công nghiệp hóa tạo ra nhiều việc làm hơn số việc nó xóa đi."),
    ("M", "Yes, that's true – but it probably didn't seem a positive thing at the time. I can see why the Luddites felt so threatened.",
     "Đúng vậy, nhưng có lẽ vào lúc đó, điều ấy chẳng có vẻ gì là tốt đẹp. Tôi hiểu vì sao những người Luddite cảm thấy bị đe dọa đến thế."),
    ("F", "I know. I'm sure I would have felt the same. The discussion about the future of work was really optimistic for a change. I like the idea that work won't involve doing boring, repetitive tasks, as robots will do all that. Normally, you only hear negative stuff about the future.",
     "Phải. Chắc tôi cũng sẽ cảm thấy như vậy. Phần bàn về tương lai việc làm lần này lạc quan hẳn. Tôi thích ý tưởng là công việc sẽ không còn những việc nhàm chán, lặp đi lặp lại, vì robot sẽ làm hết. Bình thường toàn nghe chuyện tiêu cực về tương lai."),
    ("M", "Bit too optimistic, don't you think? For example, I can't see how people are about to have more leisure time, when all the evidence shows people are spending longer than ever at work.",
     "Hơi lạc quan quá, bạn có thấy vậy không? Chẳng hạn, tôi không thấy làm sao người ta lại sắp có thêm thời gian rảnh được, khi mọi bằng chứng cho thấy người ta đang làm việc nhiều giờ hơn bao giờ hết."),
    ("F", "No – that's true. And what about lower unemployment? I'm not so sure about that.",
     "Ừ, đúng thế. Còn chuyện thất nghiệp giảm thì sao? Tôi không chắc lắm."),
    ("M", "Perhaps in the long term – but not in the foreseeable future.",
     "Có thể về lâu dài, nhưng trong tương lai gần thì không."),
    ("F", "Mmm. And I expect most people will be expected to work until they're much older – as everyone's living much longer.",
     "Ừm. Và tôi nghĩ phần lớn mọi người sẽ phải làm việc tới khi già hơn nhiều, vì ai cũng sống lâu hơn."),
    ("M", "That's already happening.", "Chuyện đó đang xảy ra rồi."),
    ("F", "I enjoyed all that stuff on how technology has changed some jobs and how they're likely to change in the near future.",
     "Tôi thích cả phần nói về chuyện công nghệ đã thay đổi một số nghề ra sao, và các nghề đó có thể sẽ thay đổi thế nào trong tương lai gần."),
    ("M", "Yeah, incredible. Like accountants. You might think all the technological innovations would have put them out of a job, but in fact there are more of them than ever. They're still really in demand and have become far more efficient.",
     "Ừ, đáng kinh ngạc thật. Như kế toán chẳng hạn. Người ta cứ tưởng bao nhiêu cải tiến công nghệ đã khiến họ mất việc, nhưng thật ra số kế toán nhiều hơn bao giờ hết. Họ vẫn rất được cần đến và làm việc hiệu quả hơn nhiều."),
    ("F", "Right. That was amazing. Twenty times more accountants in this country compared to the 19th century.",
     "Đúng. Thật đáng kinh ngạc. Số kế toán ở nước này gấp hai mươi lần so với thế kỷ 19."),
    ("M", "I know. I'd never have thought that demand for hairdressing would have gone up so much in the last hundred years. One hairdresser for every 287 people now, compared to one for over 1,500.",
     "Phải. Tôi chưa bao giờ nghĩ nhu cầu làm tóc lại tăng nhiều như vậy trong một trăm năm qua. Bây giờ cứ 287 người có một thợ làm tóc, so với trước kia hơn 1.500 người mới có một."),
    ("F", "Yeah because people's earning power has gone up so they can afford to spend more on personal services like that.",
     "Ừ, vì thu nhập của người ta đã tăng nên họ có tiền chi nhiều hơn cho những dịch vụ cá nhân như thế."),
    ("M", "But technology hasn't changed the actual job that much.", "Nhưng công nghệ không làm thay đổi bản thân công việc đó nhiều lắm."),
    ("F", "No, they've got hairdryers, etc. but it's one job where you don't depend on a computer ... The kind of work that administrative staff do has changed enormously, thanks to technology. Even 20 years ago there were secretaries doing dictation and typing.",
     "Đúng, họ có máy sấy tóc các thứ, nhưng đó là một nghề không phụ thuộc vào máy tính... Còn công việc của nhân viên hành chính thì thay đổi rất nhiều nhờ công nghệ. Mới hai mươi năm trước vẫn còn thư ký ngồi ghi lời đọc và đánh máy."),
    ("M", "Yes. Really boring compared to these days, when they're given much more responsibility and higher status.",
     "Ừ. Chán thật so với bây giờ, khi họ được giao nhiều trách nhiệm hơn hẳn và có địa vị cao hơn."),
    ("F", "Mmm. A lot of graduates go in for this kind of work now ... I'd expected there to be a much bigger change in the number of agricultural workers in the 19th century. But the 1871 census showed that roughly 25% of the population worked on the land.",
     "Ừm. Bây giờ nhiều người tốt nghiệp đại học chọn làm công việc này... Tôi cứ tưởng hồi thế kỷ 19 số người làm nông còn đông hơn thế nhiều. Nhưng cuộc điều tra dân số năm 1871 cho thấy khoảng 25% dân số làm nông."),
    ("M", "Yeah, I'd have assumed it would be more than 50%. Now it's less than 0.2%.",
     "Ừ, tôi cứ đinh ninh phải hơn 50%. Bây giờ thì chưa tới 0,2%."),
    ("F", "What about care workers?", "Còn nhân viên chăm sóc thì sao?"),
    ("M", "They barely existed in the 19th century as people's lifespan was so much shorter. But now of course this sector will see huge growth.",
     "Ở thế kỷ 19 hầu như không có nghề này, vì tuổi thọ của con người ngắn hơn nhiều. Nhưng giờ thì tất nhiên ngành này sẽ tăng trưởng rất mạnh."),
    ("F", "Yeah – and it's hard enough to meet current demand. The future looks quite bleak for bank clerks. They've been in decline since ATMs were introduced in the eighties.",
     "Ừ, và đáp ứng nhu cầu hiện nay đã đủ khó rồi. Tương lai của nhân viên giao dịch ngân hàng thì khá ảm đạm. Số nhân viên này giảm dần từ khi máy ATM xuất hiện vào thập niên 1980."),
    ("M", "And technology will certainly make most of the jobs they do now redundant, I think.",
     "Và tôi nghĩ công nghệ chắc chắn sẽ làm phần lớn công việc họ đang làm trở nên thừa."),
    ("F", "I agree, although the situation may change. It's very hard to predict what will happen.",
     "Tôi đồng ý, dù tình hình có thể thay đổi. Rất khó đoán trước chuyện gì sẽ xảy ra."),
]

OP = {"A": "Their actions were ineffective.", "B": "They are still influential today.", "C": "They have received unfair criticism.",
      "D": "They were proved right.", "E": "Their attitude is understandable."}
PR = {"A": "Work will be more rewarding.", "B": "Unemployment will fall.", "C": "People will want to delay retiring.",
      "D": "Working hours will be shorter.", "E": "People will change jobs more frequently."}
CM = {"A": "These jobs are likely to be at risk.", "B": "Their role has become more interesting in recent years.",
      "C": "The number of people working in this sector has fallen dramatically.", "D": "This job will require more qualifications.",
      "E": "Higher disposable income has led to a huge increase in jobs.", "F": "There is likely to be a significant rise in demand for this service.",
      "G": "Both employment and productivity have risen."}


def pick(box: dict[str, str], right: str, letters: str, prompt: str, why: str):
    """One item: the right letter and the other letters given, in the book's order, labelled with the book's letters."""
    assert right in letters and len(letters) == len(set(letters)) and 2 <= len(letters) <= 5, (prompt, letters)
    lab = {k: f"{k}. {box[k]}" for k in letters}
    return (prompt, lab[right], [lab[k] for k in letters if k != right], why, [lab[k] for k in sorted(letters)])


Q21 = "Which TWO opinions about the Luddites do the students express?"
Q23 = "Which TWO predictions about the future of work are the students doubtful about?"
Q25 = "What comment do the students make about these jobs?"

QS = [
    pick(OP, "A", "ABCD", f"Câu 21. {Q21} (câu 21 và 22 là hai đáp án của cùng một câu hỏi; câu này tìm một đáp án)",
         "Cô gái: `ultimately, they didn't achieve anything` (rốt cuộc chẳng đạt được gì) = ineffective. B và C không ai nói. "
         "D ngược lại: công nghiệp hóa tạo ra nhiều việc làm hơn, nên nỗi lo của họ không đúng."),
    pick(OP, "E", "BCDE", f"Câu 22. {Q21} (đáp án còn lại)",
         "Chàng trai: `I can see why the Luddites felt so threatened` (tôi hiểu vì sao họ thấy bị đe dọa) = their attitude is understandable; "
         "cô gái đồng ý: `I'm sure I would have felt the same`. B, C, D không ai nói (D còn ngược với bài)."),
    pick(PR, "B", "ABCE", f"Câu 23. {Q23} (câu 23 và 24 là hai đáp án của cùng một câu hỏi; câu này tìm một đáp án)",
         "Cô gái: `And what about lower unemployment? I'm not so sure about that.` Chàng trai: `not in the foreseeable future`. "
         "Nghi ngờ thất nghiệp giảm = B. A là điều cô gái thích, không nghi ngờ. C sai: hai bạn không nghi ngờ điều này (`That's already happening`); "
         "vả lại bài nói bị buộc làm lâu hơn (`will be expected to`), không phải muốn. E không ai nói."),
    pick(PR, "D", "ACDE", f"Câu 24. {Q23} (đáp án còn lại)",
         "Chàng trai: `I can't see how people are about to have more leisure time` (vì người ta đang làm việc lâu hơn bao giờ hết). "
         "Không tin sẽ có thêm thời gian rảnh = nghi ngờ giờ làm việc ngắn lại (D). A, C, E: xem lời giải câu 23."),
    pick(CM, "G", "ABCEG", f"Câu 25. {Q25} Accountants",
         "`there are more of them than ever` (số người tăng = employment) và `have become far more efficient` (hiệu quả hơn = productivity): G. "
         "A là bẫy: `You might think … would have put them out of a job, but in fact …`; ý chính nằm sau `but in fact`."),
    pick(CM, "E", "ABCEF", f"Câu 26. {Q25} Hairdressers",
         "`people's earning power has gone up so they can afford to spend more` (thu nhập tăng, có tiền chi) = higher disposable income; "
         "từ 1 thợ cho hơn 1.500 người thành 1 thợ cho 287 người = a huge increase in jobs: E. B sai: `technology hasn't changed the actual job that much`. "
         "F là bẫy thì: nhu cầu làm tóc đã tăng (`has gone up … in the last hundred years`), còn F nói điều sẽ xảy ra."),
    pick(CM, "B", "ABCDG", f"Câu 27. {Q25} Administrative staff",
         "Trước kia là ghi lời đọc và đánh máy, `really boring compared to these days`, nay `much more responsibility and higher status`: B. "
         "D là bẫy: `A lot of graduates go in for this kind of work now` chỉ nói ai chọn nghề này, không nói nghề sẽ đòi hỏi thêm bằng cấp."),
    pick(CM, "C", "ACEFG", f"Câu 28. {Q25} Agricultural workers",
         "Năm 1871 khoảng 25% dân số làm nông, `Now it's less than 0.2%`: giảm mạnh, C. Con số 50% chỉ là điều chàng trai từng nghĩ (`I'd have assumed`), "
         "không phải sự thật."),
    pick(CM, "F", "BDEFG", f"Câu 29. {Q25} Care workers",
         "`this sector will see huge growth` và `it's hard enough to meet current demand`: nhu cầu sẽ tăng mạnh, F (tương lai: `There is likely to be`). "
         "E là bẫy thì và lý do: E nói việc làm đã tăng (`has led to`) vì thu nhập; nghề chăm sóc sẽ tăng vì người ta sống lâu hơn."),
    pick(CM, "A", "ABDFG", f"Câu 30. {Q25} Bank clerks",
         "`technology will certainly make most of the jobs they do now redundant` (công nghệ sẽ làm công việc của họ thành thừa) = at risk: A; cô gái cũng nói `The future looks quite bleak for bank clerks`. "
         "Cô gái thêm `the situation may change`, nhưng vẫn đồng ý (`I agree`)."),
]

DAY = {
    "title": "The Luddites", "slug_title": "The Luddites", "title_vi": "Nghe kỹ: The Luddites",
    "goal": "Nghe kỹ một cuộc thảo luận của hai sinh viên (Part 3): đọc câu hỏi trước và đoán cách nói lại, theo được ai đang nói và điều họ chốt, nhận ra mốc thời gian của mỗi nhận xét.",
    "can": ["Đọc câu hỏi trước và đoán được các cách nói lại của mỗi lựa chọn.",
            "Phân biệt câu đồng ý, câu nghi ngờ và câu thông cảm của người nói.",
            "Nhận ra bẫy: ý đứng trước `but in fact`, điều người nói từng tưởng, và nhận xét sai mốc thời gian.",
            "Giải thích được vì sao mỗi đáp án đúng bằng câu trong bài nghe."],
    "ielts": "Part 3 có hai người nói và các lựa chọn gần nghĩa nhau. Quy tắc: đọc trước câu hỏi, nghe ai đang nói và nghe đến lúc chốt ý, vì người nói thường đổi ý giữa chừng.",
    "source": C18 + ", Listening Part 3; từ vựng chọn từ bài nghe theo phương pháp của khóa học",
    "family": "Việc làm và công nghệ",
    "recognize": {"census"},
    "editor": ("Bài nghe theo Cambridge IELTS 18, Test 3, Part 3 (đề trang 58–59, script trang 111–112, đáp án trang 123). Lời thoại đúng script "
               "của sách; app đọc lại bằng hai giọng tổng hợp. Câu 21–22, 23–24 tách như Tuần 1 Ngày 7. Câu 25–30: mỗi nghề cho năm trong bảy "
               "nhận xét (giữ chữ cái của sách); bỏ C ở câu 30 và G ở câu 26 vì có thể tranh luận."),
    "book": [("Cambridge IELTS 18", "58–59", "Bài nghe The Luddites, câu 21–30 (trong app: chọn đáp án, nghe lại bao nhiêu lần cũng được)", 10, 15)],
    "sittings": [
        ("Từ để nghe trước · phong trào và tương lai việc làm", [
            ("automation", "N", "sự tự động hóa", "Automation has changed many factory jobs.", "Tự động hóa đã thay đổi nhiều công việc trong nhà máy."),
            ("textile", "N", "hàng dệt; ngành dệt", "The textile industry employed many workers.", "Ngành dệt từng sử dụng rất nhiều công nhân."),
            ("threaten", "V", "đe dọa", "New machines threatened their jobs.", "Máy móc mới đe dọa việc làm của họ."),
            ("repetitive", "A", "lặp đi lặp lại, đơn điệu", "Robots can do boring, repetitive tasks.", "Robot có thể làm những việc nhàm chán, lặp đi lặp lại."),
            ("leisure", "N", "thời gian rảnh, sự nghỉ ngơi", "People want more leisure time.", "Mọi người muốn có thêm thời gian rảnh."),
            ("unemployment", "N", "tình trạng thất nghiệp", "Unemployment fell last year.", "Năm ngoái tỷ lệ thất nghiệp giảm."),
            ("retire", "V", "nghỉ hưu", "Many people retire at sixty.", "Nhiều người nghỉ hưu ở tuổi sáu mươi."),
        ]),
        ("Từ để nghe trước · các nghề xưa và nay", [
            ("productivity", "N", "năng suất", "New software has raised productivity.", "Phần mềm mới đã nâng năng suất."),
            ("qualification", "N", "bằng cấp, chứng chỉ", "Nurses need professional qualifications.", "Y tá cần có bằng cấp chuyên môn."),
            ("census", "N", "cuộc điều tra dân số", "The census showed that the city had grown.", "Cuộc điều tra dân số cho thấy thành phố đã đông hơn."),
            ("lifespan", "N", "tuổi thọ", "People's lifespan is much longer now.", "Tuổi thọ của con người bây giờ dài hơn nhiều."),
            ("redundant", "A", "thừa, không còn cần đến", "Machines made many jobs redundant.", "Máy móc khiến nhiều công việc trở nên thừa."),
        ]),
    ],
    "listening": [
        {"id": "L1", "title": "The Luddites (Part 3, câu 21–30)",
         "instr": ("Hai sinh viên bàn về buổi seminar về tự động hóa và tương lai việc làm. Đọc câu hỏi trước, nghe lại bao nhiêu lần cũng được. "
                   "Câu 21 và 22, câu 23 và 24 là hai đáp án khác nhau của cùng một câu hỏi, thứ tự nào cũng được. Câu 25–30: mỗi nghề có một "
                   "nhận xét; trong đề gốc mỗi nhận xét dùng một lần và có một nhận xét không dùng. Âm thanh do app đọc lại lời thoại."),
         "turns": TURNS, "qs": QS},
    ],
    "my": [
        {"vi": "Viết 3–5 câu về một nghề ở Việt Nam đang giảm và một nghề đang tăng. Dùng ít nhất ba từ của bài (automation, unemployment, redundant, productivity, qualification...).",
         "en": "Write 3–5 sentences about one job in Vietnam that is in decline and one that is growing.",
         "model": "In Vietnam, automation has made many factory jobs redundant, so fewer people work on production lines. At the same time, care workers are in great demand because people are living longer. In future, this job will probably require more qualifications."},
    ],
}

"""Week 3 · Day 4 (build day 34): will have done, will be doing, will have been doing. Two lectures written by hand
(lesson_audio.build_authored_lecture) and the day's sittings reshaped around them. Same format as lecture_w3d1.py.

Sources: session 5 of the course, stages 3-4 (docs/WEEK3_PLAN.md, Day 4): the future perfect as "sẽ đã" ("I will
have finished reading this book by 10 o'clock" against "I will finish…"; by, not in: "By 2026, I will have finished
my PhD"), the future continuous as "sẽ đang" ("this time next year, I will still be working on my dissertation"; the
Spain example across three tenses), the future perfect continuous as "sẽ đã đang" (two questions: done a stretch
already? still going on?; the mirror of the present perfect continuous), and how often each is used; session 6,
stages 1-2: exercises C and D and the position of probably.
Corrections made before use (docs/WEEK3_PLAN.md, last section): the future continuous is not useless; it also asks
politely about plans ("Will you be using the car tonight?"). "By this time next year, I will still be working" is
taught as "This time next year, I'll be working". The class put probably before the whole verb phrase ("probably will
have passed"); the standard rule (Swan) is after will in an affirmative clause and before won't in a negative one,
which is also the book's key, so that is taught, with "probably will" noted as heard in speech.

Pronunciations: Oxford Learner's Dictionaries, British English, read 2026-11-26. A word without a checked
entry has none.
"""

PRON = {
    "complete": "/kəmˈpliːt/",
    "submit": "/səbˈmɪt/",
    "expand": "/ɪkˈspænd/",
    "manage": "/ˈmænɪdʒ/",
    "train": "/treɪn/",
    "project": "/ˈprɒdʒekt/",
    "target": "/ˈtɑːɡɪt/",
    "quarter": "/ˈkwɔːtə(r)/",
    "milestone": "/ˈmaɪlstəʊn/",
    "trainee": "/ˌtreɪˈniː/",
}

NOTES = {
    "complete": "complete a project, complete a form. Trang trọng hơn finish.",
    "submit": "submit a report, submit an application. Gần nghĩa: hand in.",
    "expand": "expand into a new market: mở rộng sang thị trường mới. Danh từ: expansion.",
    "manage": "manage a team, manage a project. Người quản lý: manager.",
    "train": "train new staff: đào tạo nhân viên mới. Danh từ: training.",
    "project": "Danh từ nhấn âm đầu: PRO-ject. work on a project: làm một dự án.",
    "target": "reach a target, meet a target: đạt chỉ tiêu.",
    "quarter": "Một phần tư; trong kinh doanh là một quý, ba tháng: the first quarter.",
    "milestone": "Nghĩa gốc là cột cây số bên đường; nghĩa bóng là cột mốc quan trọng.",
    "trainee": "Đuôi ee chỉ người được làm gì: trainee (người được đào tạo), employee (người được thuê).",
}

S1_WORDS = ["complete", "submit", "expand", "manage", "train"]
S2_WORDS = ["project", "target", "quarter", "milestone", "trainee"]

WILL_HAVE = [
    {"key": "a1", "icon": "steak", "head": "Sẽ đã · xong trước mốc", "en": "I'll have cooked dinner by the time you get home.", "vi": "Lúc bạn về, bữa tối đã nấu xong."},
    {"key": "a2", "icon": "book", "head": "Bình thường", "en": "I'll finish this book by ten.", "vi": "Chỉ báo là sẽ đọc xong."},
    {"key": "a3", "icon": "check_bubble", "head": "Nhấn đã xong", "en": "I'll have finished this book by ten.", "vi": "Mười giờ là đã xong rồi."},
    {"key": "a4", "icon": "cap", "head": "Mốc đi với by", "en": "By 2030, I'll have finished my master's degree.", "vi": "Không dùng in cho mốc này."},
]

WILL_BE = [
    {"key": "b1", "head": "Sẽ đang · một lúc ở tương lai", "en": "This time next year, I'll be working on my dissertation.", "vi": "Giờ này năm sau: đang làm luận văn."},
    {"key": "b2", "head": "Sẽ đang · kỳ nghỉ", "en": "This time next summer, I'll be lying on a beach in Spain.", "vi": "Đang nằm trên bãi biển."},
    {"key": "b3", "head": "Hỏi lịch sự về kế hoạch", "en": "Will you be using the car tonight?", "vi": "Nhẹ nhàng hơn câu hỏi bằng will."},
]

TWO_QUESTIONS = [
    {"key": "c1", "head": "Mốc ở tương lai", "en": "At three tomorrow", "vi": "Ba giờ chiều mai."},
    {"key": "c2", "head": "Đã làm được một quãng chưa?", "en": "for two hours", "vi": "Rồi: hai tiếng."},
    {"key": "c3", "head": "Còn làm tiếp không?", "en": "I'll have been doing homework for two hours.", "vi": "Thường là còn: sẽ đã đang."},
    {"key": "c4", "head": "Giống hiện tại hoàn thành tiếp diễn", "en": "I've been doing homework for two hours.", "vi": "Mốc là bây giờ."},
]

SPAIN = [
    {"key": "s1", "icon": "plane", "head": "Sẽ · tương lai đơn", "en": "I'll go to Spain next summer.", "vi": "Dùng nhiều nhất."},
    {"key": "s2", "icon": "suitcase", "head": "Sẽ đang · tiếp diễn", "en": "This time next summer, I'll be travelling around Spain.", "vi": "Đang đi du lịch vào lúc đó."},
    {"key": "s3", "icon": "check_bubble", "head": "Sẽ đã · hoàn thành", "en": "By next summer, I'll have been to Spain.", "vi": "Đã đi rồi."},
    {"key": "s4", "icon": "clock", "head": "Sẽ đã đang", "en": "By next summer, I'll have been learning Spanish for a year.", "vi": "Học được một năm, còn học tiếp."},
]

PROBABLY = [
    {"key": "p1", "head": "Khẳng định · sau will", "en": "You'll probably have passed your driving test.", "vi": "Chắc bạn đã thi đỗ rồi."},
    {"key": "p2", "head": "Phủ định · trước won't", "en": "We probably won't have left by then.", "vi": "Có lẽ chúng tôi vẫn chưa đi."},
    {"key": "p3", "head": "Khi nói · nhấn mạnh", "en": "You probably will have passed by then.", "vi": "Có gặp; khi viết dùng hai vị trí trên."},
]

TRAPS = [
    {"key": "e1", "wrong": "In 2030, I'll have finished my degree.", "right": "By 2030, I'll have finished my degree.", "why": "Xong trước một mốc: dùng by."},
    {"key": "e2", "wrong": "I'll have finish the report by ten.", "right": "I'll have finished the report by ten.", "why": "Sau will have là động từ dạng ba."},
    {"key": "e3", "wrong": "We won't probably have left.", "right": "We probably won't have left.", "why": "Câu phủ định: probably đứng trước won't."},
    {"key": "e4", "wrong": "By June, I'll be working here for ten years.", "right": "By June, I'll have been working here for ten years.", "why": "Mốc tương lai cộng for: sẽ đã đang."},
]

ANSWER = [
    {"key": "q1", "role": "Sẽ đã", "tense": "will have + V3", "en": "Five years from now, I'll have finished my master's degree.", "vi": "Năm năm nữa, tôi đã học xong thạc sĩ."},
    {"key": "q2", "role": "Sẽ đang", "tense": "will be + V-ing", "en": "I'll probably be working for an international company.", "vi": "Chắc tôi đang làm cho một công ty quốc tế."},
    {"key": "q3", "role": "Sẽ đã đang", "tense": "will have been + V-ing", "en": "By then, I'll have been learning English for over ten years.", "vi": "Đến lúc đó, tôi đã học tiếng Anh hơn mười năm."},
    {"key": "q4", "role": "Dự đoán", "tense": "will", "en": "I think I'll be much more confident at work.", "vi": "Tôi nghĩ mình sẽ tự tin hơn nhiều trong công việc."},
]

SITTING_1 = [
    {"kind": "title", "hook": "Bạn về nhà lúc bảy giờ. Lúc đó bữa tối đã nấu xong, hay đang nấu?", "lines": [
        {"say": "Bạn nhắn: bảy giờ mình về đến nhà. Lúc đó, bữa tối đã nấu xong, hay vẫn đang nấu? Mỗi ý cần một thì khác nhau.", "show": "hook"},
        {"say": "Buổi này học ba thì tương lai, dịch gọn bằng tiếng Việt: sẽ đã, sẽ đang, rồi sẽ đã đang."},
    ]},
    {"kind": "scene", "visual": "picture_cards", "eyebrow": "Sẽ đã", "title": "Tương lai hoàn thành: xong trước một mốc",
     "data": {"rows": WILL_HAVE, "rule": "Sẽ đã: will have + động từ dạng ba. Tại một mốc ở tương lai, việc đã xong. Mốc là một thời điểm thì đi với by, không dùng in."}, "lines": [
        {"say": "Nếu lúc bạn về bữa tối đã nấu xong, câu đó là sẽ đã. Công thức: will have cộng động từ dạng ba.", "show": "a1"},
        {"en": "I'll have cooked dinner by the time you get home.", "vi": "Lúc bạn về đến nhà, tôi đã nấu xong bữa tối.", "gap": True},
        {"say": "So sánh hai câu. Câu thứ nhất chỉ báo là sẽ đọc xong cuốn sách trước mười giờ.", "show": "a2"},
        {"en": "I'll finish this book by ten.", "vi": "Tôi sẽ đọc xong cuốn sách này trước mười giờ.", "gap": True},
        {"say": "Câu thứ hai nhấn vào lúc đã xong: đúng mười giờ, cuốn sách đã đọc xong rồi.", "show": "a3"},
        {"en": "I'll have finished this book by ten.", "vi": "Đến mười giờ tôi đã đọc xong cuốn sách này.", "gap": True},
        {"say": "Mốc là một thời điểm, như một năm cụ thể, thì đi với by. Đừng dùng in với thời điểm đó. Còn in cộng một khoảng thời gian, như năm năm nữa, thì vẫn dùng được.", "show": "a4"},
        {"en": "By 2030, I'll have finished my master's degree.", "vi": "Đến năm 2030 tôi đã học xong thạc sĩ.", "gap": True},
        {"say": "Sẽ đã: will have cộng động từ dạng ba. Tại một mốc ở tương lai, việc đã xong. Mốc là một thời điểm thì đi với by, không dùng in.", "show": "rule"},
    ]},
    {"kind": "scene", "visual": "ref_table", "eyebrow": "Sẽ đang", "title": "Tương lai tiếp diễn: đang diễn ra lúc đó",
     "data": {"rows": WILL_BE, "rule": "Sẽ đang: will be + V-ing. Tại một lúc ở tương lai, việc đang diễn ra. Cũng dùng để hỏi lịch sự về kế hoạch."}, "lines": [
        {"say": "Còn nếu lúc đó bạn vẫn đang làm, câu đó là sẽ đang: will be cộng động từ đuôi ing. Giờ này năm sau, bạn đang làm luận văn.", "show": "b1"},
        {"en": "This time next year, I'll be working on my dissertation.", "vi": "Giờ này năm sau tôi đang làm luận văn.", "gap": True},
        {"say": "Giờ này hè năm sau, bạn đang nằm trên một bãi biển ở Spain.", "show": "b2"},
        {"en": "This time next summer, I'll be lying on a beach in Spain.", "vi": "Giờ này hè năm sau tôi đang nằm trên một bãi biển ở Tây Ban Nha.", "gap": True},
        {"say": "Thì này ít gặp. Nhưng có một cách dùng rất hay nghe: hỏi nhẹ nhàng về kế hoạch của người khác.", "show": "b3"},
        {"en": "Will you be using the car tonight?", "vi": "Tối nay bạn có dùng xe không?", "gap": True},
        {"say": "Sẽ đang: will be cộng đuôi ing. Tại một lúc ở tương lai, việc đang diễn ra. Thì này cũng dùng để hỏi lịch sự về kế hoạch.", "show": "rule"},
    ]},
    {"kind": "scene", "visual": "ref_table", "eyebrow": "Sẽ đã đang", "title": "Hai câu hỏi: đã được bao lâu, còn tiếp không?",
     "data": {"rows": TWO_QUESTIONS, "rule": "Sẽ đã đang: will have been + V-ing + for. Tính đến một mốc ở tương lai, việc đã kéo dài được bao lâu, thường vẫn còn tiếp."}, "lines": [
        {"say": "Thì cuối dài nhất. Đặt một mốc ở tương lai: ba giờ chiều mai.", "show": "c1"},
        {"say": "Câu hỏi thứ nhất: đến mốc đó, đã làm được một quãng chưa? Rồi: hai tiếng.", "show": "c2"},
        {"say": "Câu hỏi thứ hai: còn làm tiếp không? Thường là còn. Lúc đó, dùng sẽ đã đang.", "show": "c3"},
        {"en": "I'll have been doing homework for two hours.", "vi": "Đến lúc đó tôi đã làm bài được hai tiếng.", "gap": True},
        {"say": "Thì này giống hệt hiện tại hoàn thành tiếp diễn đã học ở tuần một. Chỉ khác là mốc dời từ bây giờ sang một lúc ở tương lai.", "show": "c4"},
        {"en": "I've been doing homework for two hours.", "vi": "Tôi làm bài được hai tiếng rồi.", "gap": True, "recap": False},
        {"say": "Sẽ đã đang: tính đến một mốc ở tương lai, đã làm được bao lâu, thường vẫn còn làm tiếp. Dấu hiệu là for cộng một khoảng thời gian.", "show": "rule"},
    ]},
    {"kind": "word", "headword": "complete", "lines": [{"say": "Năm động từ của buổi này là việc của một dự án. Từ thứ nhất: hoàn thành. Câu ví dụ là sẽ đã."}]},
    {"kind": "word", "headword": "submit", "lines": [{"say": "Từ thứ hai: nộp bài, nộp hồ sơ."}]},
    {"kind": "word", "headword": "expand", "lines": [{"say": "Từ thứ ba: mở rộng."}]},
    {"kind": "word", "headword": "manage", "lines": [{"say": "Từ thứ tư: quản lý. Câu ví dụ là sẽ đang."}]},
    {"kind": "word", "headword": "train", "lines": [{"say": "Từ cuối: đào tạo. Ở đây là động từ, không phải tàu hỏa."}]},
    {"kind": "recap", "lines": [
        {"say": "Bảy giờ bạn về: bữa tối đã nấu xong là sẽ đã, vẫn đang nấu là sẽ đang. Giờ nói lại các câu của buổi này. Nghe một câu, rồi nói to trong quãng nghỉ.", "show": "title"},
    ]},
    {"kind": "end", "next": "Tiếp theo: học thẻ và từ của buổi này, rồi làm bài.", "lines": [
        {"say": "Hết buổi một. Bạn học các thẻ và từ trong app, rồi làm bài. Buổi hai so sánh bốn thì tương lai qua một chuyến du lịch, rồi học vị trí của probably.", "show": "title"},
    ]},
]

SITTING_2 = [
    {"kind": "title", "hook": "Bốn thì tương lai: thì nào bạn sẽ dùng nhiều nhất?", "lines": [
        {"say": "Bây giờ bạn có bốn thì tương lai. Thử đoán: thì nào người bản ngữ dùng nhiều nhất? Thì nào ít nhất?", "show": "hook"},
        {"say": "Buổi này so sánh cả bốn thì qua một chuyến đi, học vị trí của probably, rồi một câu Speaking về năm năm tới."},
    ]},
    {"kind": "scene", "visual": "picture_cards", "eyebrow": "So sánh", "title": "Một chuyến đi, bốn thì",
     "data": {"rows": SPAIN, "rule": "Tương lai đơn dùng nhiều nhất; ba thì còn lại ít gặp hơn nhiều, hiếm nhất là sẽ đã đang."}, "lines": [
        {"say": "Thì thứ nhất, đơn giản nhất: hè năm sau bạn sẽ đi Spain.", "show": "s1"},
        {"en": "I'll go to Spain next summer.", "vi": "Hè năm sau tôi sẽ đi Tây Ban Nha.", "gap": True},
        {"say": "Sẽ đang: giờ này hè năm sau, bạn đang đi du lịch khắp nước đó.", "show": "s2"},
        {"en": "This time next summer, I'll be travelling around Spain.", "vi": "Giờ này hè năm sau tôi đang đi du lịch khắp Tây Ban Nha.", "gap": True},
        {"say": "Sẽ đã: đến hè năm sau, bạn đã đi Spain rồi.", "show": "s3"},
        {"en": "By next summer, I'll have been to Spain.", "vi": "Đến hè năm sau tôi đã đi Tây Ban Nha rồi.", "gap": True},
        {"say": "Sẽ đã đang: đến hè năm sau, bạn đã học tiếng của nước đó được một năm, mà vẫn còn học tiếp.", "show": "s4"},
        {"en": "By next summer, I'll have been learning Spanish for a year.", "vi": "Đến hè năm sau tôi đã học tiếng Tây Ban Nha được một năm.", "gap": True},
        {"say": "Câu trả lời cho câu hỏi đầu buổi: tương lai đơn dùng nhiều nhất. Ba thì còn lại ít gặp hơn nhiều, hiếm nhất là sẽ đã đang. Phần lớn câu nói về tương lai chỉ cần will.", "show": "rule"},
    ]},
    {"kind": "scene", "visual": "ref_table", "eyebrow": "Vị trí", "title": "Probably đứng ở đâu?",
     "data": {"rows": PROBABLY, "rule": "Câu khẳng định: probably sau will. Câu phủ định: probably trước won't."}, "lines": [
        {"say": "Thêm từ probably, nghĩa là có lẽ, vào một câu sẽ đã. Bạn đặt nó ở chỗ nào? Thử đoán trước khi nghe."},
        {"say": "Câu khẳng định: probably đứng ngay sau will.", "show": "p1"},
        {"en": "You'll probably have passed your driving test.", "vi": "Chắc bạn đã thi đỗ bằng lái rồi.", "gap": True},
        {"say": "Câu phủ định: probably đứng trước dạng phủ định của will, không chen vào sau.", "show": "p2"},
        {"en": "We probably won't have left by then.", "vi": "Đến lúc đó có lẽ chúng tôi vẫn chưa đi.", "gap": True},
        {"say": "Khi nói, đôi khi bạn nghe probably đứng trước will để nhấn mạnh. Khi viết, dùng hai vị trí chuẩn ở trên.", "show": "p3"},
        {"en": "You probably will have passed by then.", "vi": "Đến lúc đó chắc là bạn đã đỗ rồi.", "gap": True, "recap": False},
        {"say": "Câu khẳng định: probably đứng sau will. Câu phủ định: probably đứng trước will not, viết gọn như trên bảng.", "show": "rule"},
    ]},
    {"kind": "scene", "visual": "fix_pairs", "eyebrow": "Lỗi thường gặp", "title": "Bốn lỗi, bốn cách sửa",
     "data": {"rows": TRAPS, "rule": "Mốc đi với by. Sau will have: dạng ba. Probably trước won't. Mốc tương lai cộng for: sẽ đã đang."}, "lines": [
        {"say": "Bốn lỗi hay gặp nhất của hôm nay. Lỗi một: dùng in cho mốc của thì sẽ đã.", "show": "e1"},
        {"en": "By 2030, I'll have finished my degree.", "vi": "Đến năm 2030 tôi đã học xong.", "gap": True},
        {"say": "Lỗi hai: quên động từ dạng ba sau will have.", "show": "e2"},
        {"en": "I'll have finished the report by ten.", "vi": "Đến mười giờ tôi đã làm xong báo cáo.", "gap": True},
        {"say": "Lỗi ba: đặt probably sau dạng phủ định.", "show": "e3"},
        {"en": "We probably won't have left.", "vi": "Có lẽ chúng tôi vẫn chưa đi.", "gap": True, "recap": False},
        {"say": "Lỗi bốn: có mốc tương lai cộng for, mà lại dùng sẽ đang.", "show": "e4"},
        {"en": "By June, I'll have been working here for ten years.", "vi": "Đến tháng Sáu tôi đã làm ở đây được mười năm.", "gap": True},
        {"say": "Mốc đi với by. Sau will have là dạng ba. Probably đứng trước dạng phủ định của will. Mốc tương lai cộng for thì dùng sẽ đã đang.", "show": "rule"},
    ]},
    {"kind": "word", "headword": "project", "lines": [{"say": "Trước câu Speaking, học năm danh từ của một dự án. Từ thứ nhất: dự án. Danh từ nhấn âm đầu."}]},
    {"kind": "word", "headword": "target", "lines": [{"say": "Từ thứ hai: chỉ tiêu, mục tiêu. Câu ví dụ có probably đứng sau will."}]},
    {"kind": "word", "headword": "quarter", "lines": [{"say": "Từ thứ ba: một phần tư, trong kinh doanh là một quý."}]},
    {"kind": "word", "headword": "milestone", "lines": [{"say": "Từ thứ tư: cột mốc quan trọng."}]},
    {"kind": "word", "headword": "trainee", "lines": [{"say": "Từ cuối: người được đào tạo. Trọng âm rơi vào âm tiết cuối."}]},
    {"kind": "scene", "visual": "speaking_answer", "eyebrow": "IELTS Speaking", "title": "Năm năm nữa: sẽ đã, sẽ đang, sẽ đã đang",
     "data": {"question": "Where do you see yourself in five years?", "question_vi": "Năm năm nữa bạn thấy mình ở đâu?",
              "short": "Working.", "parts": ANSWER,
              "rule": "Việc xong trước mốc: sẽ đã. Việc đang làm lúc đó: sẽ đang. Đã làm được bao lâu: sẽ đã đang. Còn lại: will."}, "lines": [
        {"say": "Giám khảo hỏi năm năm nữa bạn thấy mình ở đâu."},
        {"en": "Where do you see yourself in five years?", "show": "q"},
        {"say": "Đáp một chữ thì quá ngắn.", "show": "short"},
        {"say": "Câu một: một việc sẽ xong trước lúc đó."},
        {"en": "Five years from now, I'll have finished my master's degree.", "vi": "Năm năm nữa, tôi đã học xong thạc sĩ.", "gap": True, "show": "q1"},
        {"say": "Câu hai: một việc sẽ đang làm lúc đó, có probably đứng sau will."},
        {"en": "I'll probably be working for an international company.", "vi": "Chắc tôi đang làm cho một công ty quốc tế.", "gap": True, "show": "q2"},
        {"say": "Câu ba: đã học tiếng Anh được bao lâu."},
        {"en": "By then, I'll have been learning English for over ten years.", "vi": "Đến lúc đó, tôi đã học tiếng Anh hơn mười năm.", "gap": True, "show": "q3"},
        {"say": "Câu bốn: một dự đoán đơn giản bằng will."},
        {"en": "I think I'll be much more confident at work.", "vi": "Tôi nghĩ mình sẽ tự tin hơn nhiều trong công việc.", "gap": True, "show": "q4"},
        {"say": "Việc xong trước mốc: sẽ đã. Việc đang làm lúc đó: sẽ đang. Đã làm được bao lâu: sẽ đã đang. Còn lại, cứ dùng will. Hãy viết lại bốn câu này cho đúng với chính bạn.", "show": "rule"},
    ]},
    {"kind": "recap", "lines": [
        {"say": "Thì dùng nhiều nhất vẫn là tương lai đơn; hiếm nhất là sẽ đã đang. Giờ nói lại các câu của buổi này. Nghe một câu, rồi nói to trong quãng nghỉ.", "show": "title"},
    ]},
    {"kind": "end", "next": "Tiếp theo: học thẻ và từ, làm bài, rồi buổi 3 để xếp câu, nghe chép và viết.", "lines": [
        {"say": "Hết phần giảng của ngày bốn. Bạn học các thẻ và từ trong app, làm bài, rồi sang buổi ba để xếp câu, nghe chép và viết về cuộc sống của bạn năm năm nữa.", "show": "title"},
    ]},
]

RUBRIC = [
    {"criterion_vi": "Đúng đề: có một việc sẽ xong, một việc sẽ đang làm, một khoảng thời gian đã làm", "max": 1, "note_vi": "Task response"},
    {"criterion_vi": "Đúng thì: will have + V3 với by; will be + V-ing; will have been + V-ing với for", "max": 2, "note_vi": "Grammatical range"},
    {"criterion_vi": "Dạng đúng: động từ dạng ba sau will have; probably sau will, trước won't", "max": 2, "note_vi": "Grammatical accuracy"},
]


def reshape(sessions: list[dict], exercise_ids: list[str], card_of: dict[str, int]) -> list[dict]:
    """Sitting 1 teaches cards 1-3 (future perfect, future continuous, future perfect continuous) with five verbs;
    sitting 2 cards 4-5 (choosing among the four, the position of probably) with five nouns; the production work is a
    third sitting without a lecture."""
    pats = [g for s in sessions[:2] for g in s["grammar"]]
    allcheck = [i for s in sessions[:2] for i in s["check"]]
    s1, s2 = sessions[0], sessions[1]
    rest = sessions[2:]
    all_words = [w for s in sessions[:2] for w in s["vocab"]]
    assert sorted(all_words) == sorted(S1_WORDS + S2_WORDS), all_words
    s1["vocab"], s2["vocab"] = S1_WORDS, S2_WORDS
    s1["grammar"], s2["grammar"] = pats[:3], pats[3:]
    quiz = [i for i in allcheck if i[5] in "IQT"]
    s1["check"] = sorted([i for i in quiz if card_of[i] < 3], key=lambda i: card_of[i])
    s2_all = sorted([i for i in quiz if card_of[i] >= 3], key=lambda i: (card_of[i], i[5] != "T"))
    s2["check"], spill = s2_all[:7], s2_all[7:]
    moved = spill + [i for i in allcheck if i not in quiz]
    s1["lecture"], s2["lecture"] = SITTING_1, SITTING_2
    s1["title_vi"] = "Buổi 1 · sẽ đã, sẽ đang, sẽ đã đang"
    s2["title_vi"] = "Buổi 2 · chọn thì tương lai; vị trí probably"
    s1["can_do_vi"] = "Sau buổi này bạn nói được việc sẽ xong trước một mốc (will have + V3, by), việc sẽ đang diễn ra (will be + V-ing), và việc đã làm được bao lâu tính đến một mốc tương lai (will have been + V-ing)."
    s2["can_do_vi"] = "Sau buổi này bạn chọn được thì tương lai hợp với ý, đặt probably đúng chỗ, và trả lời câu hỏi về năm năm tới."
    s3 = {
        "title_vi": "Buổi 3 · vận dụng: xếp câu, gõ, nghe chép, viết",
        "can_do_vi": "Sau buổi này bạn tự xếp và gõ đúng câu sẽ đã, sẽ đang, sẽ đã đang; nghe chép được câu có will have và will be; và viết về cuộc sống của bạn năm năm nữa.",
        "use_vi": s1["use_vi"],
        "vocab": [],
        "check": moved,
    }
    assert set(s1["check"] + s2["check"] + moved) <= set(exercise_ids)
    return [s1, s2, s3] + rest

"""Week 3 · Day 5 (build day 35): time and work, the vocabulary day. Five lectures written by hand
(lesson_audio.build_authored_lecture), one per word group; vocab_day() gives each of the first five sittings its
lecture and title. Same format as lecture_w2d5.py.

Sources: session 6 of the course, stages 2-4 (docs/WEEK3_PLAN.md, day 5): the filter "gold and chaff" (learn in full
what is worth writing: provisional, timely, prompt, long-standing, span, frequency, phase, era; only recognise spell,
stint, millennium, century, vintage, antique, lifetime, anachronism, interval, abrupt, contemporaries, lapse), the
collocations taught in place of one Vietnamese word (a temporary worker but a provisional draft; an era of mass
communication; a span of ten years; a long-standing institution; a prompt reply), on time against in time (the train
at ten, arriving at 9.59), prompt against quick in writing, the memory trick for hard adjectives (the root noun plus
"có tính": subsequent), effective against efficient (a medicine that works after three days; robots), make someone
redundant in place of fire when writing, on leave, strike, be headhunted, and the upgrade of "job opportunities" to
"opportunities to be headhunted by multinational corporations"; pronunciation: enunciate (say each first and last
sound: move, egg, ship / sheep), copy the mouth like a parrot, punctual /ˈpʌŋktʃuəl/.
Corrections made before use: the class note gives exercise C item 7 as chronological; the key and the sentence give
permanent, so chronological is taught with its own example (in chronological order). Quick is not wrong in writing;
it is only plainer and can suggest haste, so prompt is taught as the better choice, not quick as an error.
Not taught: phrasal verbs and idioms (exercise F onwards), exercise E, and the "chaff" words, which are met in the
exercises only.

Pronunciations: Oxford Learner's Dictionaries, British English, read 2026-11-27 (the phrases put together from their
words' entries).
"""

PRON = {
    "temporary": "/ˈtemprəri/",
    "provisional": "/prəˈvɪʒənl/",
    "permanent": "/ˈpɜːmənənt/",
    "long-standing": "/ˌlɒŋ ˈstændɪŋ/",
    "obsolete": "/ˈɒbsəliːt/",
    "overdue": "/ˌəʊvəˈdjuː/",
    "expire": "/ɪkˈspaɪə(r)/",
    "timely": "/ˈtaɪmli/",
    "punctual": "/ˈpʌŋktʃuəl/",
    "on time": "/ɒn taɪm/",
    "in time": "/ɪn taɪm/",
    "prompt": "/prɒmpt/",
    "simultaneous": "/ˌsɪmlˈteɪniəs/",
    "instantaneous": "/ˌɪnstənˈteɪniəs/",
    "subsequent": "/ˈsʌbsɪkwənt/",
    "era": "/ˈɪərə/",
    "period": "/ˈpɪəriəd/",
    "span": "/spæn/",
    "phase": "/feɪz/",
    "frequency": "/ˈfriːkwənsi/",
    "annual": "/ˈænjuəl/",
    "elapse": "/ɪˈlæps/",
    "chronological": "/ˌkrɒnəˈlɒdʒɪkl/",
    "multinational corporation": "/ˌmʌltiˈnæʃnəl ˌkɔːpəˈreɪʃn/",
    "marketing campaign": "/ˈmɑːkɪtɪŋ kæmˈpeɪn/",
    "consultant": "/kənˈsʌltənt/",
    "senior executive": "/ˈsiːniə(r) ɪɡˈzekjətɪv/",
    "effective": "/ɪˈfektɪv/",
    "efficient": "/ɪˈfɪʃnt/",
    "make someone redundant": "/meɪk ˈsʌmwʌn rɪˈdʌndənt/",
    "on leave": "/ɒn liːv/",
    "strike": "/straɪk/",
    "headhunt": "/ˈhedhʌnt/",
}

NOTES = {
    "temporary": "Chỉ kéo dài một thời gian ngắn rồi hết: a temporary worker, a temporary solution.",
    "provisional": "Dùng tạm cho đến khi thành bản chính thức: a provisional draft, provisional results.",
    "permanent": "Trái nghĩa với temporary: a permanent job, a permanent member.",
    "long-standing": "Khen một thứ có từ lâu và vẫn vững: a long-standing institution, a long-standing tradition.",
    "obsolete": "Lỗi thời đến mức không dùng được nữa, như phần mềm hay máy móc cũ.",
    "overdue": "Hay đi thành cụm long overdue: lẽ ra phải có từ lâu rồi.",
    "expire": "Chủ ngữ là thẻ, hợp đồng, hộ chiếu. Khác postpone (hoãn một sự kiện).",
    "timely": "Đuôi -ly nhưng là tính từ: a timely solution, a timely arrival.",
    "punctual": "Đọc /ˈpʌŋktʃuəl/: có âm /k/ nhẹ trước /tʃ/. Danh từ: punctuality.",
    "on time": "Đúng giờ theo lịch: the train left on time.",
    "in time": "Kịp, trước khi quá muộn: just in time to catch the train.",
    "prompt": "Nhanh chóng, không chậm trễ: a prompt reply, prompt action. Trang trọng hơn quick.",
    "simultaneous": "Hai việc xảy ra cùng một lúc. Trạng từ: simultaneously.",
    "instantaneous": "Xảy ra ngay lập tức, không có độ trễ.",
    "subsequent": "Mẹo nhớ: danh từ gốc là sự theo sau; thêm «có tính» là ra nghĩa: có tính theo sau, tiếp theo.",
    "era": "an era of mass communication. Đọc /ˈɪərə/. Gần nghĩa: age.",
    "period": "Một khoảng thời gian liền mạch: over the period, the period I spent abroad.",
    "span": "a span of ten years = a period of ten years; attention span: thời gian tập trung được.",
    "phase": "go through a phase: trải qua một giai đoạn rồi sẽ hết. Đọc /feɪz/.",
    "frequency": "Danh từ: tần suất. Tính từ frequent mới là thường xuyên.",
    "annual": "Mỗi năm một lần: an annual dinner, annual sales. Đọc /ˈænjuəl/.",
    "elapse": "Chủ ngữ luôn là thời gian: three months had elapsed. Khác lapse (hết hiệu lực).",
    "chronological": "in chronological order: theo trình tự thời gian.",
    "multinational corporation": "Tập đoàn hoạt động ở nhiều nước. Cụm rất hay dùng khi viết về việc làm.",
    "marketing campaign": "Chiến dịch tiếp thị: launch a marketing campaign.",
    "consultant": "Người được thuê để tư vấn: a freelance business consultant.",
    "senior executive": "Lãnh đạo cấp cao trong một công ty.",
    "effective": "Đạt được kết quả mong muốn, không bàn đến tốc độ.",
    "efficient": "Đạt kết quả nhanh, ít tốn thời gian và công sức.",
    "make someone redundant": "Cắt giảm nhân sự vì không còn cần vị trí đó, không phải lỗi của người lao động. Khác fire (đuổi vì lỗi).",
    "on leave": "Đang nghỉ phép: be on leave, go on leave.",
    "strike": "Động từ: đình công. Danh từ: go on strike, be on strike.",
    "headhunt": "Hay dùng ở bị động: be headhunted by a company.",
}


def _row(key, icon, head, en, vi):
    r = {"key": key, "head": head, "en": en, "vi": vi}
    if icon:
        r["icon"] = icon
    return r


FILTER = [
    _row("f1", "star", "Vàng · học kỹ để viết", "a provisional draft · a prompt reply · a long-standing institution", "Đáng dùng trong bài viết IELTS."),
    _row("f2", "eye", "Cám · chỉ cần nhận ra", "spell · stint · millennium · anachronism", "Gặp thì hiểu, không cần dùng."),
    _row("f3", "checklist", "Học cả cụm", "a provisional draft", "Học cả cụm, không ghép từ theo chữ tiếng Việt."),
]
TEMP = [
    _row("t1", "user_icon", "temporary · ngắn rồi hết", "I'm a temporary worker.", "Người làm tạm thời vài tuần."),
    _row("t2", "doc", "provisional · chờ bản chính thức", "It's only a provisional draft.", "Bản nháp sẽ còn được sửa."),
    _row("t3", "bulb", "temporary · giải pháp", "We need a temporary solution.", "Dùng tạm một thời gian rồi thôi."),
    _row("t4", "house", "permanent · lâu dài", "She has a permanent contract.", "Trái nghĩa với temporary."),
]
OLD = [
    _row("o1", None, "long-standing · lâu đời", "It is a long-standing institution.", "Có từ lâu và vẫn vững: lời khen."),
    _row("o2", None, "obsolete · lỗi thời", "This software is now obsolete.", "Cũ đến mức không dùng được nữa."),
    _row("o3", None, "long overdue · quá hạn lâu", "These changes are long overdue.", "Lẽ ra phải có từ lâu."),
    _row("o4", None, "expire · hết hạn", "My membership expired last month.", "Chủ ngữ là thẻ, hợp đồng."),
]
TRAIN = [
    _row("a1", "clock", "on time · đúng lịch", "The train left on time.", "Đúng giờ ghi trên lịch."),
    _row("a2", "car", "in time · vừa kịp", "We arrived just in time to catch the train.", "Đến trước lúc quá muộn."),
    _row("a3", "calendar", "punctual · người đúng giờ", "I try to be punctual.", "Nói về thói quen của một người."),
    _row("a4", "check_bubble", "timely · đúng lúc cần", "What a timely arrival!", "Đến đúng lúc đang cần."),
]
PROMPT = [
    _row("p1", None, "quick · rất hay dùng khi nói", "Let's have a quick look.", "Trung tính, giản dị."),
    _row("p2", None, "prompt · khi viết", "Thank you for your prompt reply.", "Không chậm trễ; trang trọng."),
    _row("p3", None, "prompt · Writing Task 2", "Governments should take prompt action.", "Cụm hay gặp trong bài mẫu."),
]
TOGETHER = [
    _row("s1", None, "simultaneous · cùng lúc", "Our answers were simultaneous.", "Hai việc xảy ra cùng một lúc."),
    _row("s2", None, "instantaneous · tức thì", "The change was instantaneous.", "Không có độ trễ."),
    _row("s3", None, "subsequent · theo sau", "Subsequent studies confirmed the results.", "Danh từ gốc + có tính: có tính theo sau."),
]
SOUNDS = [
    _row("n1", None, "punctual · /ˈpʌŋktʃuəl/", "I try to be punctual.", "Âm /k/ nhẹ rồi nối sang /tʃ/."),
    _row("n2", None, "simultaneous · /ˌsɪmlˈteɪniəs/", "Our answers were simultaneous.", "Nhấn vào âm tiết thứ ba."),
    _row("n3", None, "ship · sheep", "a ship, a sheep", "Nguyên âm ngắn và nguyên âm dài."),
]
PERIOD = [
    _row("q1", None, "Câu thường", "The figures cover ten years.", "Đúng, nhưng đơn giản."),
    _row("q2", None, "a period of", "The figures cover a period of ten years.", "Cách viết phổ biến."),
    _row("q3", None, "a span of", "The figures cover a span of ten years.", "Một cách khác để đổi từ."),
]
SPANS = [
    _row("e1", "share_nodes", "era · thời đại", "We live in an era of mass communication.", "Một thời kỳ dài, có đặc điểm riêng."),
    _row("e2", "user_icon", "phase · giai đoạn", "It's just a phase that most teenagers go through.", "Rồi sẽ qua đi."),
    _row("e3", "repeat", "frequency · tần suất", "The council will increase the frequency of buses.", "Danh từ, khác frequent."),
    _row("e4", "calendar", "annual · hằng năm", "The club holds an annual dinner.", "Mỗi năm một lần."),
]
PAIRS = [
    {"key": "c1", "wrong": "Three months had lapsed.", "right": "Three months had elapsed.", "why": "Thời gian trôi qua: elapse."},
    {"key": "c2", "wrong": "The interval I spent as chairman.", "right": "The period I spent as chairman.", "why": "Một khoảng liền mạch: period. interval là quãng nghỉ xen giữa."},
    {"key": "c3", "wrong": "List the events in anachronistic order.", "right": "List the events in chronological order.", "why": "Theo trình tự thời gian: chronological."},
]
COMPANY = [
    _row("m1", "share_nodes", "multinational corporation", "She works for a multinational corporation.", "Tập đoàn có mặt ở nhiều nước."),
    _row("m2", "upgrade", "marketing campaign", "The marketing campaign starts next month.", "Chiến dịch tiếp thị."),
    _row("m3", "discuss", "consultant", "Charlene is a freelance business consultant.", "Được thuê để tư vấn."),
    _row("m4", "user_icon", "senior executive", "My dad is a senior executive.", "Lãnh đạo cấp cao."),
]
EFFECT = [
    _row("x1", "upgrade", "effective · đạt kết quả", "The campaign was effective: sales rose by 50%.", "Có kết quả, không bàn tốc độ."),
    _row("x2", "plus_heart", "effective · dù chậm", "The medicine was effective, but it took three days.", "Ba ngày mới khỏi vẫn là hiệu quả."),
    _row("x3", "gear", "efficient · nhanh, ít tốn", "Robots are more efficient than people.", "Làm nhiều hơn với cùng thời gian."),
]
JOBS = [
    _row("r1", None, "on leave · nghỉ phép", "Darren is home on leave.", "Nghỉ có phép, vẫn còn việc."),
    _row("r2", None, "strike · đình công", "The union is planning to strike.", "Cả nhóm cùng nghỉ để phản đối."),
    _row("r3", None, "fire · đuổi vì lỗi", "They fired him for stealing.", "Lỗi của người bị đuổi."),
    _row("r4", None, "make someone redundant · cắt giảm", "The company had to make fifty staff redundant.", "Không còn cần vị trí, không phải lỗi."),
]
UPGRADE = [
    _row("u1", None, "Câu thường", "Highly skilled workers have more job opportunities.", "Cụm ai cũng viết."),
    _row("u2", None, "Câu hay hơn", "Highly skilled workers have more opportunities to be headhunted by multinational corporations.", "Ghép hai cụm vừa học."),
    _row("u3", None, "Câu thường", "Many companies fire workers when sales fall.", "fire là đuổi vì lỗi; ở đây là cắt giảm."),
    _row("u4", None, "Câu hay hơn", "Many companies make staff redundant when sales fall.", "Cụm trang trọng cho bài viết."),
]

SITTING_1 = [
    {"kind": "title", "hook": "Bản nháp đầu tiên của bài luận là bản tạm thời. Temporary hay provisional?", "lines": [
        {"say": "Bạn vừa viết xong bản nháp đầu tiên của một bài luận, còn sửa nhiều. Bản nháp tạm thời: dùng temporary, hay provisional?", "show": "hook"},
        {"say": "Buổi này học cách lọc từ của một bài từ vựng nâng cao, rồi bảy từ về tạm thời, lâu dài và lỗi thời."},
    ]},
    {"kind": "scene", "visual": "picture_cards", "eyebrow": "Trước khi học", "title": "Vàng và cám",
     "data": {"rows": FILTER, "rule": "Từ đáng dùng khi viết thì học kỹ, cả cụm đi kèm. Từ chỉ cần nhận ra thì gặp trong bài tập là đủ."}, "lines": [
        {"say": "Bài từ vựng này có hơn bốn mươi từ về thời gian. Không phải từ nào cũng đáng học kỹ. Từ đáng dùng trong bài viết gọi là vàng: học kỹ, học cả cụm.", "show": "f1"},
        {"say": "Có những từ ít khi cần dùng trong bài IELTS. Đó là cám: gặp thì hiểu, không cần nhớ để dùng.", "show": "f2"},
        {"say": "Và luôn học cả cụm. Hai từ cùng dịch là tạm thời, nhưng với bản nháp, người bản ngữ thường dùng provisional.", "show": "f3"},
        {"say": "Từ đáng dùng khi viết thì học kỹ, cả cụm đi kèm. Từ chỉ cần nhận ra thì gặp trong bài tập là đủ.", "show": "rule"},
    ]},
    {"kind": "scene", "visual": "picture_cards", "eyebrow": "Một chữ tiếng Việt, hai từ tiếng Anh", "title": "temporary và provisional",
     "data": {"rows": TEMP, "rule": "temporary: chỉ kéo dài một thời gian ngắn rồi hết. provisional: dùng tạm cho đến khi thành bản chính thức. Trái nghĩa: permanent."}, "lines": [
        {"say": "Người làm vài tuần rồi nghỉ là người làm tạm thời. Thứ chỉ kéo dài một thời gian ngắn rồi hết thì dùng temporary.", "show": "t1"},
        {"en": "I'm a temporary worker.", "vi": "Tôi là nhân viên tạm thời.", "gap": True},
        {"say": "Còn bản nháp, thứ dùng tạm cho đến khi sửa thành bản chính thức, thì dùng provisional. Câu trả lời cho câu hỏi đầu buổi.", "show": "t2"},
        {"en": "It's only a provisional draft.", "vi": "Đây chỉ là bản nháp tạm thời.", "gap": True},
        {"say": "Một giải pháp dùng tạm một thời gian thì là temporary. Cụm này rất hay gặp trong bài viết Task 2.", "show": "t3"},
        {"en": "We need a temporary solution.", "vi": "Chúng ta cần một giải pháp tạm thời.", "gap": True},
        {"say": "Trái nghĩa với tạm thời là lâu dài, vĩnh viễn: permanent.", "show": "t4"},
        {"en": "She has a permanent contract.", "vi": "Cô ấy có hợp đồng dài hạn.", "gap": True},
        {"say": "Chỉ kéo dài một thời gian ngắn rồi hết: temporary. Dùng tạm cho đến khi thành bản chính thức: provisional. Trái nghĩa là permanent.", "show": "rule"},
    ]},
    {"kind": "scene", "visual": "ref_table", "eyebrow": "Cũ và mới", "title": "Lâu đời, lỗi thời, quá hạn, hết hạn",
     "data": {"rows": OLD, "rule": "long-standing là lời khen; obsolete là lời chê; long overdue là lẽ ra phải có từ lâu; expire là hết hạn."}, "lines": [
        {"say": "Bốn từ nói về một thứ đã có từ lâu, nhưng mang sắc thái khác nhau. Từ thứ nhất là một lời khen: lâu đời, vẫn vững.", "show": "o1"},
        {"en": "It is a long-standing institution.", "vi": "Đó là một tổ chức lâu đời.", "gap": True},
        {"say": "Từ thứ hai là lời chê: cũ đến mức không dùng được nữa.", "show": "o2"},
        {"en": "This software is now obsolete.", "vi": "Phần mềm này giờ đã lỗi thời.", "gap": True},
        {"say": "Từ thứ ba: một việc lẽ ra phải làm từ lâu mà chưa làm.", "show": "o3"},
        {"en": "These changes are long overdue.", "vi": "Những thay đổi này lẽ ra phải có từ lâu.", "gap": True},
        {"say": "Từ thứ tư là động từ: thẻ, hợp đồng, hộ chiếu hết hạn.", "show": "o4"},
        {"en": "My membership expired last month.", "vi": "Thẻ hội viên của tôi hết hạn tháng trước.", "gap": True},
        {"say": "Lâu đời là lời khen. Lỗi thời là lời chê. Quá hạn lâu là lẽ ra phải có từ lâu. Expire là hết hạn.", "show": "rule"},
    ]},
    {"kind": "word", "headword": "temporary", "lines": [{"say": "Giờ học từng từ. Từ thứ nhất: tạm thời, dùng cho người và công việc."}]},
    {"kind": "word", "headword": "provisional", "lines": [{"say": "Từ thứ hai: tạm thời, dùng cho văn bản và giải pháp."}]},
    {"kind": "word", "headword": "permanent", "lines": [{"say": "Từ thứ ba: lâu dài, vĩnh viễn."}]},
    {"kind": "word", "headword": "long-standing", "lines": [{"say": "Từ thứ tư: lâu đời. Khi viết, ghép với institution, hoặc tradition."}]},
    {"kind": "word", "headword": "obsolete", "lines": [{"say": "Từ thứ năm: lỗi thời."}]},
    {"kind": "word", "headword": "overdue", "lines": [{"say": "Từ thứ sáu: quá hạn. Hay đi cùng long thành một cụm."}]},
    {"kind": "word", "headword": "expire", "lines": [{"say": "Từ cuối: hết hạn."}]},
    {"kind": "recap", "lines": [
        {"say": "Bản nháp đầu tiên là provisional, người làm vài tuần là temporary. Giờ nói lại các câu của buổi này. Nghe một câu, rồi nói to trong quãng nghỉ.", "show": "title"},
    ]},
    {"kind": "end", "next": "Tiếp theo: buổi 2, kịp thời, đúng giờ, cùng lúc.", "lines": [
        {"say": "Hết buổi một. Buổi hai học các từ về đúng giờ, kịp thời, cùng lúc, rồi cách luyện đọc một từ mới cho rõ.", "show": "title"},
    ]},
]

SITTING_2 = [
    {"kind": "title", "hook": "Tàu chạy đúng mười giờ, bạn đến lúc chín giờ năm mươi chín. Ai on time, ai in time?", "lines": [
        {"say": "Tàu chạy đúng mười giờ như lịch. Bạn đến ga lúc chín giờ năm mươi chín, vừa kịp nhảy lên. Câu nào nói về con tàu, câu nào nói về bạn: on time, hay in time?", "show": "hook"},
        {"say": "Buổi này học tám từ và cụm về đúng giờ, kịp thời, cùng lúc và tiếp theo, rồi cách luyện đọc từ mới."},
    ]},
    {"kind": "scene", "visual": "picture_cards", "eyebrow": "Thí nghiệm", "title": "on time, in time, punctual, timely",
     "data": {"rows": TRAIN, "rule": "on time: đúng giờ theo lịch. in time: kịp, trước khi quá muộn. punctual nói về người; timely nói về việc đến đúng lúc cần."}, "lines": [
        {"say": "Chuyến tàu khởi hành đúng giờ ghi trên lịch: on time.", "show": "a1"},
        {"en": "The train left on time.", "vi": "Tàu chạy đúng giờ.", "gap": True},
        {"say": "Còn bạn, đến trước lúc tàu chạy một phút: vừa kịp, in time.", "show": "a2"},
        {"en": "We arrived just in time to catch the train.", "vi": "Chúng tôi đến vừa kịp bắt chuyến tàu.", "gap": True},
        {"say": "Một người luôn đúng giờ thì là người punctual.", "show": "a3"},
        {"en": "I try to be punctual.", "vi": "Tôi cố gắng đúng giờ.", "gap": True},
        {"say": "Còn một việc xảy ra đúng lúc đang cần thì là timely. Đuôi ly ở đây là tính từ, không phải trạng từ.", "show": "a4"},
        {"en": "What a timely arrival!", "vi": "Đến đúng lúc quá!", "gap": True},
        {"say": "Đúng giờ theo lịch là on time. Kịp trước khi quá muộn là in time. Còn punctual nói về người, timely nói về việc đến đúng lúc cần.", "show": "rule"},
    ]},
    {"kind": "scene", "visual": "ref_table", "eyebrow": "Văn nói và văn viết", "title": "quick hay prompt?",
     "data": {"rows": PROMPT, "rule": "quick trung tính, rất hay dùng khi nói. Khi viết thư hay bài luận, prompt trang trọng hơn: a prompt reply, prompt action."}, "lines": [
        {"say": "Quick là nhanh, rất hay dùng khi nói. Khi viết thư hay bài luận, có một từ trang trọng hơn.", "show": "p1"},
        {"en": "Let's have a quick look.", "vi": "Chúng ta xem qua một chút nhé.", "gap": True, "recap": False},
        {"say": "Prompt là nhanh chóng, không chậm trễ, lại trang trọng hơn. Lời cảm ơn trong thư.", "show": "p2"},
        {"en": "Thank you for your prompt reply.", "vi": "Cảm ơn bạn đã trả lời nhanh chóng.", "gap": True},
        {"say": "Trong bài viết Task 2, prompt action là cụm trang trọng hay gặp.", "show": "p3"},
        {"en": "Governments should take prompt action.", "vi": "Các chính phủ nên hành động kịp thời.", "gap": True},
        {"say": "Quick trung tính, rất hay dùng khi nói. Khi viết thư hay bài luận, prompt trang trọng hơn.", "show": "rule"},
    ]},
    {"kind": "scene", "visual": "ref_table", "eyebrow": "Cùng lúc và tiếp theo", "title": "simultaneous, instantaneous, subsequent",
     "data": {"rows": TOGETHER, "rule": "Cùng lúc: simultaneous. Ngay lập tức: instantaneous. Theo sau: subsequent. Tính từ khó: nhớ danh từ gốc rồi thêm «có tính»."}, "lines": [
        {"say": "Hai người nói cùng một câu, đúng cùng một lúc.", "show": "s1"},
        {"en": "Our answers were simultaneous.", "vi": "Câu trả lời của chúng tôi bật ra cùng lúc.", "gap": True},
        {"say": "Một thay đổi xảy ra ngay lập tức, không chờ đợi gì.", "show": "s2"},
        {"en": "The change was instantaneous.", "vi": "Sự thay đổi diễn ra ngay lập tức.", "gap": True},
        {"say": "Tính từ thứ ba khó nhớ hơn. Mẹo: nhớ danh từ gốc, nghĩa là sự theo sau, rồi thêm có tính. Có tính theo sau, tức là tiếp theo.", "show": "s3"},
        {"en": "Subsequent studies confirmed the results.", "vi": "Các nghiên cứu tiếp theo đã xác nhận kết quả.", "gap": True},
        {"say": "Cùng lúc là simultaneous. Ngay lập tức là instantaneous. Theo sau là subsequent. Gặp tính từ khó, hãy nhớ danh từ gốc rồi thêm có tính.", "show": "rule"},
    ]},
    {"kind": "scene", "visual": "ref_table", "eyebrow": "Luyện đọc", "title": "Đọc rõ từng âm, nhại như con vẹt",
     "data": {"rows": SOUNDS, "rule": "Từ mới: đọc chậm, rõ từng âm đầu và âm cuối. Nhìn khẩu hình người bản ngữ và nhại lại đến khi giống."}, "lines": [
        {"say": "Học một từ mới, hãy đọc chậm và rõ từng âm. Từ đúng giờ có một âm cờ rất nhẹ, rồi nối sang âm chờ.", "show": "n1"},
        {"en": "I try to be punctual.", "vi": "Tôi cố gắng đúng giờ.", "gap": True, "recap": False},
        {"say": "Từ cùng lúc có năm âm tiết. Nhấn vào âm tiết thứ ba.", "show": "n2"},
        {"en": "Our answers were simultaneous.", "vi": "Câu trả lời của chúng tôi bật ra cùng lúc.", "gap": True, "recap": False},
        {"say": "Phân biệt nguyên âm ngắn và dài: con tàu và con cừu. Đọc đủ cả âm cuối, như trong move, hay egg.", "show": "n3"},
        {"en": "a ship, a sheep", "vi": "con tàu, con cừu", "gap": True, "recap": False},
        {"say": "Trẻ con sửa phát âm nhanh vì chịu nhại lại giống hệt, nhiều lần. Từ mới: đọc chậm, rõ từng âm đầu và âm cuối, nhìn khẩu hình người bản ngữ và nhại lại đến khi giống.", "show": "rule"},
    ]},
    {"kind": "word", "headword": "timely", "lines": [{"say": "Giờ học từng từ. Từ thứ nhất: kịp thời, đúng lúc."}]},
    {"kind": "word", "headword": "punctual", "lines": [{"say": "Từ thứ hai: đúng giờ, nói về một người."}]},
    {"kind": "word", "headword": "on time", "lines": [{"say": "Cụm thứ ba: đúng giờ theo lịch."}]},
    {"kind": "word", "headword": "in time", "lines": [{"say": "Cụm thứ tư: vừa kịp."}]},
    {"kind": "word", "headword": "prompt", "lines": [{"say": "Từ thứ năm: nhanh chóng, không chậm trễ."}]},
    {"kind": "word", "headword": "simultaneous", "lines": [{"say": "Từ thứ sáu: cùng một lúc."}]},
    {"kind": "word", "headword": "instantaneous", "lines": [{"say": "Từ thứ bảy: ngay lập tức."}]},
    {"kind": "word", "headword": "subsequent", "lines": [{"say": "Từ cuối: có tính theo sau, tức là tiếp theo."}]},
    {"kind": "recap", "lines": [
        {"say": "Đến ga lúc chín giờ năm mươi chín là in time, vừa kịp. Giờ nói lại các câu của buổi này. Nghe một câu, rồi nói to trong quãng nghỉ.", "show": "title"},
    ]},
    {"kind": "end", "next": "Tiếp theo: buổi 3, những quãng thời gian.", "lines": [
        {"say": "Hết buổi hai. Buổi ba học các từ chỉ quãng thời gian, rất có ích khi mô tả biểu đồ.", "show": "title"},
    ]},
]

SITTING_3 = [
    {"kind": "title", "hook": "Biểu đồ trải từ năm 2010 đến 2020. Viết «mười năm» thế nào cho hay?", "lines": [
        {"say": "Một biểu đồ trong bài viết Task 1 trải từ năm 2010 đến năm 2020. Ngoài cách nói mười năm, bạn còn cách nào hay hơn?", "show": "hook"},
        {"say": "Buổi này học tám từ chỉ các quãng thời gian, nhịp lặp lại, rồi thời gian trôi qua."},
    ]},
    {"kind": "scene", "visual": "ref_table", "eyebrow": "Writing Task 1", "title": "Mười năm, ba cách viết",
     "data": {"rows": PERIOD, "rule": "Đổi cách nói một quãng thời gian: a period of ten years, a span of ten years."}, "lines": [
        {"say": "Cách đơn giản nhất: đúng, nhưng ai cũng viết.", "show": "q1"},
        {"en": "The figures cover ten years.", "vi": "Số liệu trải dài mười năm.", "gap": True, "recap": False},
        {"say": "Cách thứ hai dùng period, một khoảng thời gian liền mạch.", "show": "q2"},
        {"en": "The figures cover a period of ten years.", "vi": "Số liệu trải dài trong khoảng mười năm.", "gap": True},
        {"say": "Cách thứ ba dùng span. Khi một bài cần nói nhiều lần về quãng thời gian, đổi từ như vậy giúp tránh lặp.", "show": "q3"},
        {"en": "The figures cover a span of ten years.", "vi": "Số liệu trải dài trong mười năm.", "gap": True},
        {"say": "Đổi cách nói một quãng thời gian bằng period hoặc span.", "show": "rule"},
    ]},
    {"kind": "scene", "visual": "picture_cards", "eyebrow": "Dài, ngắn, lặp lại", "title": "era, phase, frequency, annual",
     "data": {"rows": SPANS, "rule": "era: một thời đại dài. phase: một giai đoạn rồi qua. frequency: tần suất, là danh từ. annual: mỗi năm một lần."}, "lines": [
        {"say": "Một thời đại dài có đặc điểm riêng: era. Cụm hay gặp là thời đại truyền thông đại chúng.", "show": "e1"},
        {"en": "We live in an era of mass communication.", "vi": "Chúng ta sống trong thời đại truyền thông đại chúng.", "gap": True},
        {"say": "Một giai đoạn ngắn, rồi sẽ qua đi: phase. Đừng dịch là bước.", "show": "e2"},
        {"en": "It's just a phase that most teenagers go through.", "vi": "Đó chỉ là một giai đoạn mà phần lớn thanh thiếu niên trải qua.", "gap": True},
        {"say": "Bao nhiêu lần một việc lặp lại: frequency, tần suất. Đây là danh từ; đừng dịch là thường xuyên.", "show": "e3"},
        {"en": "The council will increase the frequency of buses.", "vi": "Hội đồng thành phố sẽ tăng tần suất xe buýt.", "gap": True},
        {"say": "Mỗi năm một lần: annual.", "show": "e4"},
        {"en": "The club holds an annual dinner.", "vi": "Câu lạc bộ tổ chức tiệc tối hằng năm.", "gap": True},
        {"say": "Era là một thời đại dài. Phase là một giai đoạn rồi qua. Frequency là tần suất, một danh từ. Annual là mỗi năm một lần.", "show": "rule"},
    ]},
    {"kind": "scene", "visual": "fix_pairs", "eyebrow": "Cặp dễ nhầm", "title": "elapse, period, chronological",
     "data": {"rows": PAIRS, "rule": "Thời gian trôi qua: elapse. Một khoảng liền mạch: period. Theo trình tự thời gian: chronological."}, "lines": [
        {"say": "Cặp thứ nhất. Chủ ngữ là thời gian trôi qua, dùng elapse, không dùng lapse.", "show": "c1"},
        {"en": "Three months had elapsed.", "vi": "Ba tháng đã trôi qua.", "gap": True},
        {"say": "Cặp thứ hai. Thời gian làm chủ tịch là một khoảng liền mạch: period. Interval là quãng nghỉ xen giữa hai việc, như giờ giải lao của một vở kịch.", "show": "c2"},
        {"en": "The period I spent as chairman.", "vi": "Khoảng thời gian tôi làm chủ tịch.", "gap": True, "recap": False},
        {"say": "Cặp thứ ba. Theo trình tự thời gian là chronological. Từ kia nói về một thứ lạc thời, như một chiếc điện thoại rất cũ giữa thời nay.", "show": "c3"},
        {"en": "List the events in chronological order.", "vi": "Hãy liệt kê các sự kiện theo trình tự thời gian.", "gap": True},
        {"say": "Thời gian trôi qua là elapse. Một khoảng liền mạch là period. Theo trình tự thời gian là chronological.", "show": "rule"},
    ]},
    {"kind": "word", "headword": "era", "lines": [{"say": "Giờ học từng từ. Từ thứ nhất: thời đại."}]},
    {"kind": "word", "headword": "period", "lines": [{"say": "Từ thứ hai: một khoảng thời gian liền mạch."}]},
    {"kind": "word", "headword": "span", "lines": [{"say": "Từ thứ ba: một quãng thời gian."}]},
    {"kind": "word", "headword": "phase", "lines": [{"say": "Từ thứ tư: giai đoạn."}]},
    {"kind": "word", "headword": "frequency", "lines": [{"say": "Từ thứ năm: tần suất."}]},
    {"kind": "word", "headword": "annual", "lines": [{"say": "Từ thứ sáu: hằng năm."}]},
    {"kind": "word", "headword": "elapse", "lines": [{"say": "Từ thứ bảy: thời gian trôi qua."}]},
    {"kind": "word", "headword": "chronological", "lines": [{"say": "Từ cuối: theo trình tự thời gian."}]},
    {"kind": "recap", "lines": [
        {"say": "Mười năm trong biểu đồ: dùng period, hoặc span. Giờ nói lại các câu của buổi này. Nghe một câu, rồi nói to trong quãng nghỉ.", "show": "title"},
    ]},
    {"kind": "end", "next": "Tiếp theo: buổi 4, công ty và chức vụ.", "lines": [
        {"say": "Hết buổi ba. Buổi bốn chuyển sang công việc: công ty, chức vụ, rồi hai từ hiệu quả hay bị nhầm.", "show": "title"},
    ]},
]

SITTING_4 = [
    {"kind": "title", "hook": "Quảng cáo làm doanh số tăng năm mươi phần trăm. Effective hay efficient?", "lines": [
        {"say": "Một chiến dịch quảng cáo làm doanh số tăng năm mươi phần trăm. Chiến dịch đó effective, hay efficient?", "show": "hook"},
        {"say": "Buổi này học bốn cụm về công ty và chức vụ, rồi hai từ hiệu quả hay bị nhầm."},
    ]},
    {"kind": "scene", "visual": "picture_cards", "eyebrow": "Trong một công ty lớn", "title": "Tập đoàn, chiến dịch, chuyên gia, lãnh đạo",
     "data": {"rows": COMPANY, "rule": "Học cả cụm: multinational corporation, marketing campaign, business consultant, senior executive."}, "lines": [
        {"say": "Tập đoàn có mặt ở nhiều nước. Cụm này rất hay gặp trong bài viết về việc làm.", "show": "m1"},
        {"en": "She works for a multinational corporation.", "vi": "Cô ấy làm cho một tập đoàn đa quốc gia.", "gap": True},
        {"say": "Chiến dịch tiếp thị của tập đoàn đó.", "show": "m2"},
        {"en": "The marketing campaign starts next month.", "vi": "Chiến dịch tiếp thị bắt đầu vào tháng sau.", "gap": True},
        {"say": "Người được thuê từ bên ngoài để tư vấn. Làm tự chủ, không thuộc công ty nào, gọi là freelance; người làm như vậy là freelancer.", "show": "m3"},
        {"en": "Charlene is a freelance business consultant.", "vi": "Charlene là chuyên gia tư vấn kinh doanh độc lập.", "gap": True},
        {"say": "Người lãnh đạo cấp cao trong công ty.", "show": "m4"},
        {"en": "My dad is a senior executive.", "vi": "Bố tôi là một lãnh đạo cấp cao.", "gap": True},
        {"say": "Học cả cụm, không học từng từ rời: tập đoàn đa quốc gia, chiến dịch tiếp thị, chuyên gia tư vấn, lãnh đạo cấp cao.", "show": "rule"},
    ]},
    {"kind": "scene", "visual": "picture_cards", "eyebrow": "Hiệu quả hay hiệu suất", "title": "effective và efficient",
     "data": {"rows": EFFECT, "rule": "effective: đạt được kết quả mong muốn, không bàn tốc độ. efficient: đạt kết quả nhanh, ít tốn thời gian và công sức."}, "lines": [
        {"say": "Chiến dịch làm doanh số tăng: đạt được kết quả mong muốn. Đó là effective, câu trả lời cho câu hỏi đầu buổi.", "show": "x1"},
        {"en": "The campaign was effective: sales rose by 50%.", "vi": "Chiến dịch hiệu quả: doanh số tăng 50%.", "gap": True},
        {"say": "Uống thuốc ba ngày mới khỏi bệnh: chậm, nhưng thuốc vẫn effective, vì có kết quả.", "show": "x2"},
        {"en": "The medicine was effective, but it took three days.", "vi": "Thuốc có hiệu quả, nhưng phải ba ngày mới khỏi.", "gap": True},
        {"say": "Robot làm suốt ngày đêm, không mệt, không sai: làm được nhiều hơn với cùng thời gian. Đó là efficient.", "show": "x3"},
        {"en": "Robots are more efficient than people.", "vi": "Robot làm việc hiệu suất cao hơn con người.", "gap": True},
        {"say": "Effective là đạt được kết quả mong muốn, không bàn tốc độ. Efficient là đạt kết quả nhanh, ít tốn thời gian và công sức.", "show": "rule"},
    ]},
    {"kind": "word", "headword": "multinational corporation", "lines": [{"say": "Giờ học từng cụm. Cụm thứ nhất: tập đoàn đa quốc gia."}]},
    {"kind": "word", "headword": "marketing campaign", "lines": [{"say": "Cụm thứ hai: chiến dịch tiếp thị."}]},
    {"kind": "word", "headword": "consultant", "lines": [{"say": "Từ thứ ba: chuyên gia tư vấn."}]},
    {"kind": "word", "headword": "senior executive", "lines": [{"say": "Cụm thứ tư: lãnh đạo cấp cao."}]},
    {"kind": "word", "headword": "effective", "lines": [{"say": "Từ thứ năm: hiệu quả, đạt kết quả."}]},
    {"kind": "word", "headword": "efficient", "lines": [{"say": "Từ cuối: hiệu suất cao, nhanh và ít tốn."}]},
    {"kind": "recap", "lines": [
        {"say": "Doanh số tăng năm mươi phần trăm: chiến dịch effective. Giờ nói lại các câu của buổi này. Nghe một câu, rồi nói to trong quãng nghỉ.", "show": "title"},
    ]},
    {"kind": "end", "next": "Tiếp theo: buổi 5, nghỉ phép, đình công, mất việc, được săn đón.", "lines": [
        {"say": "Hết buổi bốn. Buổi năm học cách nói nghỉ phép, đình công, mất việc và được săn đón, rồi nâng cấp một câu viết rất quen.", "show": "title"},
    ]},
]

SITTING_5 = [
    {"kind": "title", "hook": "Rất nhiều bài viết dùng cụm «job opportunities». Có cách nào nói hay hơn?", "lines": [
        {"say": "Rất nhiều bài viết về việc làm dùng cụm job opportunities. Có cách nào nói hay hơn không?", "show": "hook"},
        {"say": "Buổi này học bốn cụm về nghỉ phép, đình công, mất việc và được săn đón, rồi ghép chúng thành câu viết hay hơn."},
    ]},
    {"kind": "scene", "visual": "ref_table", "eyebrow": "Nghỉ việc và mất việc", "title": "on leave, strike, fire, make redundant",
     "data": {"rows": JOBS, "rule": "on leave: nghỉ phép. strike: đình công. fire: đuổi vì lỗi. make redundant: cắt giảm vì không còn cần vị trí."}, "lines": [
        {"say": "Nghỉ có phép, vẫn còn việc để quay lại: on leave.", "show": "r1"},
        {"en": "Darren is home on leave.", "vi": "Darren đang về nhà nghỉ phép.", "gap": True},
        {"say": "Cả nhóm cùng nghỉ việc để phản đối: đình công.", "show": "r2"},
        {"en": "The union is planning to strike.", "vi": "Công đoàn đang dự định đình công.", "gap": True},
        {"say": "Bị đuổi việc vì lỗi của chính mình: fire. Khi viết trang trọng, có từ dismiss.", "show": "r3"},
        {"en": "They fired him for stealing.", "vi": "Họ đuổi việc anh ta vì ăn cắp.", "gap": True, "recap": False},
        {"say": "Công ty cắt giảm nhân sự vì không còn cần vị trí đó, không phải lỗi của ai: make redundant.", "show": "r4"},
        {"en": "The company had to make fifty staff redundant.", "vi": "Công ty đã phải cắt giảm năm mươi nhân viên.", "gap": True},
        {"say": "On leave là nghỉ phép. Strike là đình công. Fire là đuổi vì lỗi. Make redundant là cắt giảm vì không còn cần vị trí.", "show": "rule"},
    ]},
    {"kind": "scene", "visual": "ref_table", "eyebrow": "Nâng cấp câu viết", "title": "Từ câu thường đến câu hay hơn",
     "data": {"rows": UPGRADE, "rule": "Ghép những cụm vừa học để câu viết tự nhiên và mới hơn: be headhunted by multinational corporations, make staff redundant."}, "lines": [
        {"say": "Câu thường: đúng, nhưng ai cũng viết.", "show": "u1"},
        {"en": "Highly skilled workers have more job opportunities.", "vi": "Người lao động giỏi có nhiều cơ hội việc làm hơn.", "gap": True, "recap": False},
        {"say": "Ghép hai cụm vừa học: được săn đón, cùng tập đoàn đa quốc gia. Câu nghe mới và cụ thể hơn hẳn.", "show": "u2"},
        {"en": "Highly skilled workers have more opportunities to be headhunted by multinational corporations.", "vi": "Người lao động giỏi có nhiều cơ hội được các tập đoàn đa quốc gia săn đón hơn.", "gap": True},
        {"say": "Câu thường thứ hai dùng fire, nhưng ý câu là cắt giảm khi doanh số giảm, không phải đuổi vì lỗi.", "show": "u3"},
        {"en": "Many companies fire workers when sales fall.", "vi": "Nhiều công ty đuổi việc nhân viên khi doanh số giảm.", "gap": True, "recap": False},
        {"say": "Đổi sang cụm đúng ý và trang trọng hơn.", "show": "u4"},
        {"en": "Many companies make staff redundant when sales fall.", "vi": "Nhiều công ty cắt giảm nhân sự khi doanh số giảm.", "gap": True},
        {"say": "Tiêu chí từ vựng chấm độ chính xác, độ tự nhiên của cụm từ và việc dùng được từ ít phổ biến. Ghép những cụm vừa học để câu viết chính xác và mới hơn.", "show": "rule"},
    ]},
    {"kind": "word", "headword": "make someone redundant", "lines": [{"say": "Giờ học từng cụm. Cụm thứ nhất: cắt giảm nhân sự."}]},
    {"kind": "word", "headword": "on leave", "lines": [{"say": "Cụm thứ hai: đang nghỉ phép."}]},
    {"kind": "word", "headword": "strike", "lines": [{"say": "Từ thứ ba: đình công."}]},
    {"kind": "word", "headword": "headhunt", "lines": [{"say": "Từ cuối: săn đón, chiêu mộ. Hay dùng ở dạng bị động."}]},
    {"kind": "recap", "lines": [
        {"say": "Thay cụm cơ hội việc làm quen thuộc bằng cơ hội được các tập đoàn đa quốc gia săn đón. Giờ nói lại các câu của buổi này. Nghe một câu, rồi nói to trong quãng nghỉ.", "show": "title"},
    ]},
    {"kind": "end", "next": "Tiếp theo: làm bài tập, rồi gõ hai câu của bạn.", "lines": [
        {"say": "Hết phần giảng của ngày năm. Bạn làm bài tập, rồi chọn năm đến mười từ bạn thích nhất và gõ hai câu về công việc hay thời gian biểu của chính bạn.", "show": "title"},
    ]},
]

S_WORDS = [
    ["temporary", "provisional", "permanent", "long-standing", "obsolete", "overdue", "expire"],
    ["timely", "punctual", "on time", "in time", "prompt", "simultaneous", "instantaneous", "subsequent"],
    ["era", "period", "span", "phase", "frequency", "annual", "elapse", "chronological"],
    ["multinational corporation", "marketing campaign", "consultant", "senior executive", "effective", "efficient"],
    ["make someone redundant", "on leave", "strike", "headhunt"],
]

TITLES = [
    "Từ vựng nâng cao · tạm thời, lâu dài, lỗi thời",
    "Từ vựng nâng cao · kịp thời, đúng giờ, cùng lúc, tiếp theo",
    "Từ vựng nâng cao · những quãng thời gian",
    "Từ vựng nâng cao · công ty và chức vụ",
    "Từ vựng nâng cao · nghỉ phép, đình công, mất việc, được săn đón",
]

LECTURES = [SITTING_1, SITTING_2, SITTING_3, SITTING_4, SITTING_5]

RUBRIC = None  # the vocabulary day has no speaking card; "Câu của tôi" keeps the default checklist


def reshape(sessions: list[dict]) -> list[dict]:
    """The five vocabulary sittings get their lecture and title; every other sitting is kept as built."""
    for i, lecture in enumerate(LECTURES):
        ses = sessions[i]
        words = [s["headword"] for s in lecture if s.get("kind") == "word"]
        assert words == S_WORDS[i], (i, words)
        assert sorted(words) == sorted(ses["vocab"]), (i, set(words) ^ set(ses["vocab"]))
        ses["lecture"] = lecture
        ses["title_vi"] = TITLES[i]
        assert len(ses["title_vi"]) <= 70
    return sessions

"""G1 · Day 3 (lesson 46): the two lectures written by hand (lesson_audio.build_authored_lecture), and the
day's sittings reshaped around them. Same format as lecture_d1.py / lecture_d2.py.

Sources: the teacher's week-1 and session-3 material (two uses of the present perfect, since / for / in,
"When did you go?", the two sample sentences of the present perfect continuous, his replacement rule)
and Destination B2, Unit 1, p. 6-8 (the present perfect continuous with ever / never, read that book vs
been reading that book, It's the first time ...). His replacement rule is quoted verbatim, followed by the
exception the book itself gives. No transcription is typed from memory.
"""

PRON: dict[str, str] = {}

HANOI = [
    {"key": "a1", "at": "past", "tense": "Hiện tại hoàn thành", "en": "Yes, I have been to Hanoi.", "vi": "Tôi từng đến Hà Nội rồi."},
    {"key": "a2", "at": "past", "tense": "Quá khứ đơn", "en": "I went there last summer.", "vi": "Có mốc thời gian: chuyển sang quá khứ đơn."},
    {"key": "a3", "at": "span", "tense": "Hiện tại hoàn thành", "en": "I have lived in Hanoi since 2023.", "vi": "Bắt đầu từ trước và kéo tới bây giờ."},
]

BRANCHES = [
    {"key": "b1", "head": "Kéo tới bây giờ", "en": "I have studied the piano since 2023.", "vi": "Bắt đầu năm 2023, bây giờ vẫn học."},
    {"key": "b2", "head": "Kéo tới bây giờ", "en": "I have studied the piano for two years.", "vi": "Hai năm nay, bây giờ vẫn học."},
    {"key": "b3", "head": "Đã xong, không nói lúc nào", "en": "I have already eaten pizza.", "vi": "Tôi ăn rồi, đừng hỏi lúc nào."},
    {"key": "b4", "head": "Có mốc thời gian: quá khứ đơn", "en": "I ate pizza last night.", "vi": "Nói được lúc nào thì quá khứ đơn."},
]

SINCE_FOR = [
    {"key": "f1", "head": "since + mốc: luôn là hoàn thành", "en": "I have studied the piano since 2003.", "vi": "Từ năm 2003 tới giờ."},
    {"key": "f2", "head": "in + năm: quá khứ đơn", "en": "I studied the piano in 2003.", "vi": "Học năm 2003, đã xong."},
    {"key": "f3", "head": "for + độ dài, còn làm", "en": "I have studied the piano for two years.", "vi": "Hai năm nay, vẫn học."},
    {"key": "f4", "head": "for + độ dài, đã nghỉ", "en": "I studied the piano for two years.", "vi": "Từng học hai năm, giờ đã nghỉ."},
]

PATTERNS = [
    {"key": "p1", "head": "It's the first time + hoàn thành", "en": "It's the first time I have ever eaten octopus.", "vi": "Lần đầu tiên tôi ăn bạch tuộc."},
    {"key": "p2", "head": "have gone to: đi và chưa về", "en": "They have gone to Spain.", "vi": "Họ đi Tây Ban Nha rồi, chưa về."},
    {"key": "p3", "head": "have been to: đã từng đến và về rồi", "en": "I have been to Spain twice.", "vi": "Tôi đã đến Tây Ban Nha hai lần."},
]

TRAPS_1 = [
    {"key": "e1", "wrong": "I work there since 2020.", "right": "I have worked there since 2020.", "why": "since cần thì hoàn thành."},
    {"key": "e2", "wrong": "I have been there two years ago.", "right": "I went there two years ago.", "why": "Có mốc thời gian đã qua: quá khứ đơn."},
    {"key": "e3", "wrong": "When have you been there?", "right": "When did you go there?", "why": "Hỏi lúc nào: quá khứ đơn."},
    {"key": "e4", "wrong": "It's the first time I am speaking English on the phone.", "right": "It's the first time I have spoken English on the phone.", "why": "Sau It's the first time dùng hoàn thành."},
]

TWO_SAMPLES = [
    {"key": "q1", "head": "Vẫn đang làm", "en": "I have been playing football for three hours.", "vi": "Bắt đầu từ ba tiếng trước, bây giờ vẫn đang chơi."},
    {"key": "q2", "head": "Vừa dừng, còn dấu vết", "en": "I'm out of breath because I have been running.", "vi": "Tôi hết hơi vì vừa chạy."},
]

REPLACE = [
    {"key": "r1", "head": "for hours", "en": "She has been writing that essay for hours.", "vi": "Thay được: She has written that essay for hours."},
    {"key": "r2", "head": "all morning", "en": "I have been trying to get in touch with Jenny all morning.", "vi": "Thay được: I have tried to get in touch with Jenny all morning."},
    {"key": "r3", "head": "for the last six years", "en": "We have been living here for the last six years.", "vi": "Thay được: We have lived here for the last six years."},
]

EXCEPTION = [
    {"key": "x1", "head": "Nhấn vào dấu vết", "en": "I've been crying.", "vi": "Mắt còn đỏ. Không đổi được thành I've cried."},
    {"key": "x2", "head": "Hoàn thành: đã xong", "en": "I have read that book.", "vi": "Đã đọc xong cuốn đó."},
    {"key": "x3", "head": "Tiếp diễn: chưa xong", "en": "I have been reading that book.", "vi": "Đang đọc dở cuốn đó."},
]

TRAPS_2 = [
    {"key": "g1", "wrong": "I have been knowing her for years.", "right": "I have known her for years.", "why": "know là động từ trạng thái, không chia tiếp diễn."},
    {"key": "g2", "wrong": "Have you ever been visiting Hue?", "right": "Have you ever visited Hue?", "why": "Sách: tiếp diễn thường không dùng với ever và never."},
    {"key": "g3", "wrong": "I am living here since 2020.", "right": "I have been living here since 2020.", "why": "since cần thì hoàn thành."},
]

BREATH = [
    {"key": "w1", "head": "breath · danh từ", "en": "I am out of breath.", "vi": "Hơi thở: tôi hết hơi."},
    {"key": "w2", "head": "breathe · động từ", "en": "Breathe slowly.", "vi": "Thở: hãy thở chậm."},
]

SITTING_1 = [
    {"kind": "title", "hook": "Hỏi Have you ever been to Hanoi rồi, vì sao câu sau lại phải đổi sang quá khứ đơn?", "lines": [
        {"say": "Có người hỏi bạn đã từng đến Hà Nội chưa. Bạn đáp bằng hiện tại hoàn thành. Nhưng khi kể đi lúc nào, vì sao phải đổi sang quá khứ đơn?", "show": "hook"},
        {"say": "Buổi này mình học hiện tại hoàn thành: hai nhánh của nó, và lúc nào thì phải bỏ nó."},
    ]},
    {"kind": "scene", "visual": "tense_timeline", "eyebrow": "Thí nghiệm", "title": "Một câu hỏi, ba câu đáp",
     "data": {"question": "Have you ever been to Hanoi?", "question_vi": "Bạn đã từng đến Hà Nội chưa?", "answers": HANOI,
              "rule": "Hỏi trải nghiệm: hiện tại hoàn thành. Nói được lúc nào thì quá khứ đơn."}, "lines": [
        {"say": "Giám khảo hỏi một câu ở hiện tại hoàn thành."},
        {"en": "Have you ever been to Hanoi?", "vi": "Bạn đã từng đến Hà Nội chưa?", "gap": True, "show": "q"},
        {"say": "Bạn muốn nói là đã từng, không cần nói lúc nào. Hiện tại hoàn thành."},
        {"en": "Yes, I have been to Hanoi.", "vi": "Có, tôi từng đến Hà Nội.", "gap": True, "show": "a1"},
        {"say": "Người ta hỏi tiếp: when did you go there? Hỏi lúc nào thì không dùng hiện tại hoàn thành nữa. Bạn nói được lúc nào, thì dùng quá khứ đơn."},
        {"en": "I went there last summer.", "vi": "Tôi đến đó mùa hè năm ngoái.", "gap": True, "show": "a2"},
        {"say": "Nếu thay vì nói đã đến, bạn muốn nói việc sống ở đó vẫn tiếp tục, bạn lại dùng hiện tại hoàn thành."},
        {"en": "I have lived in Hanoi since 2023.", "vi": "Tôi sống ở Hà Nội từ năm 2023.", "gap": True, "show": "a3"},
        {"say": "Hiện tại hoàn thành là thì của việc không nói lúc nào, hoặc của việc kéo tới bây giờ. Có mốc thời gian đã qua, chuyển sang quá khứ đơn.", "show": "rule"},
    ]},
    {"kind": "word", "headword": "achieve", "lines": [{"say": "Một từ cho kết quả đã đạt được, rất hợp với thì này."}]},
    {"kind": "scene", "visual": "ref_table", "eyebrow": "Hai nhánh", "title": "Kéo tới bây giờ, hoặc đã xong không nói lúc nào",
     "data": {"cols": ["Nhánh", "Ví dụ"], "rows": BRANCHES,
              "rule": "Công thức: have hoặc has cộng dạng quá khứ phân từ. Nhánh nào cũng không có mốc thời gian đã qua."}, "lines": [
        {"say": "Nhánh thứ nhất: việc bắt đầu trong quá khứ và kéo tới bây giờ. Đi với since cộng mốc, hoặc for cộng độ dài.", "show": "b1"},
        {"en": "I have studied the piano since 2023.", "vi": "Tôi học piano từ năm 2023.", "gap": True},
        {"en": "I have studied the piano for two years.", "vi": "Tôi học piano hai năm nay.", "gap": True, "show": "b2"},
        {"say": "Nhánh thứ hai: việc đã xong, và người nói không quan tâm lúc nào. Thường đi với already, yet, ever, never, before.", "show": "b3"},
        {"en": "I have already eaten pizza.", "vi": "Tôi ăn pizza rồi.", "gap": True},
        {"say": "Nếu nói được lúc nào thì là quá khứ đơn."},
        {"en": "I ate pizza last night.", "vi": "Tối qua tôi ăn pizza.", "gap": True, "show": "b4"},
        {"say": "Công thức: have hoặc has, cộng quá khứ phân từ. Và không có mốc thời gian đã qua.", "show": "rule"},
    ]},
    {"kind": "scene", "visual": "ref_table", "eyebrow": "Bẫy since, for, in", "title": "For chỉ là một giới từ",
     "data": {"cols": ["Cách nói", "Ví dụ"], "rows": SINCE_FOR,
              "rule": "since luôn đi với thì hoàn thành. for chỉ nói độ dài: còn làm thì hoàn thành, đã nghỉ thì quá khứ đơn."}, "lines": [
        {"say": "Nhiều người học vẹt: thấy for là chia hiện tại hoàn thành. Hãy xem since trước, vì since luôn đi với thì hoàn thành.", "show": "f1"},
        {"en": "I have studied the piano since 2003.", "vi": "Tôi học piano từ năm 2003.", "gap": True},
        {"say": "Còn in cộng một năm là mốc đã qua, nên quá khứ đơn."},
        {"en": "I studied the piano in 2003.", "vi": "Tôi học piano vào năm 2003.", "gap": True, "show": "f2"},
        {"say": "For thì khác. For two years chỉ nói độ dài. Nếu bây giờ vẫn còn học, dùng hiện tại hoàn thành."},
        {"en": "I have studied the piano for two years.", "vi": "Tôi học piano hai năm nay.", "gap": True, "show": "f3"},
        {"say": "Nếu đã nghỉ rồi thì quá khứ đơn, cùng cụm for two years."},
        {"en": "I studied the piano for two years.", "vi": "Tôi từng học piano hai năm.", "gap": True, "show": "f4"},
        {"say": "Đừng nhìn dấu hiệu. Hãy hỏi: việc đó còn kéo tới bây giờ không?", "show": "rule"},
    ]},
    {"kind": "scene", "visual": "ref_table", "eyebrow": "Ba mẫu cần thuộc", "title": "It's the first time, gone to, been to",
     "data": {"cols": ["Mẫu", "Ví dụ"], "rows": PATTERNS,
              "rule": "Sau It's the first time dùng hoàn thành. Gone to là chưa về, been to là đã về."}, "lines": [
        {"say": "Mẫu thứ nhất: sau It's the first time, dùng hiện tại hoàn thành.", "show": "p1"},
        {"en": "It's the first time I have ever eaten octopus.", "vi": "Lần đầu tiên tôi ăn bạch tuộc.", "gap": True},
        {"say": "Mẫu thứ hai: have gone to nghĩa là đã đi và chưa về."},
        {"en": "They have gone to Spain.", "vi": "Họ đi Tây Ban Nha rồi, chưa về.", "gap": True, "show": "p2"},
        {"say": "Mẫu thứ ba: have been to nghĩa là đã từng đến và đã về rồi."},
        {"en": "I have been to Spain twice.", "vi": "Tôi đã đến Tây Ban Nha hai lần.", "gap": True, "show": "p3"},
        {"say": "Gone là chưa về. Been là đã về rồi.", "show": "rule"},
    ]},
    {"kind": "scene", "visual": "fix_pairs", "eyebrow": "Lỗi thường gặp", "title": "Bốn lỗi, bốn cách sửa",
     "data": {"rows": TRAPS_1,
              "rule": "Có mốc thời gian đã qua thì quá khứ đơn. Since và It's the first time thì hoàn thành."}, "lines": [
        {"say": "Bốn lỗi người Việt hay mắc. Lỗi thứ nhất: since đi với hiện tại đơn.", "show": "e1"},
        {"en": "I have worked there since 2020.", "vi": "Tôi làm ở đó từ năm 2020.", "gap": True},
        {"say": "Lỗi thứ hai: hiện tại hoàn thành cùng mốc thời gian đã qua.", "show": "e2"},
        {"en": "I went there two years ago.", "vi": "Hai năm trước tôi đến đó.", "gap": True},
        {"say": "Lỗi thứ ba: hỏi lúc nào bằng hiện tại hoàn thành.", "show": "e3"},
        {"en": "When did you go there?", "vi": "Bạn đến đó lúc nào?", "gap": True},
        {"say": "Lỗi thứ tư: sau It's the first time.", "show": "e4"},
        {"en": "It's the first time I have spoken English on the phone.", "vi": "Lần đầu tiên tôi nói tiếng Anh qua điện thoại.", "gap": True},
        {"say": "Có mốc thời gian đã qua thì quá khứ đơn. Since và It's the first time thì hoàn thành.", "show": "rule"},
    ]},
    {"kind": "recap", "lines": [
        {"say": "Giờ nói lại các câu của buổi này. Nghe một câu, rồi nói to trong quãng nghỉ.", "show": "title"},
    ]},
    {"kind": "end", "next": "Tiếp theo: học các từ và mẫu ngữ pháp của buổi này, rồi làm bài tập.", "lines": [
        {"say": "Hết buổi một. Việc tiếp theo là học các từ và mẫu ngữ pháp trong app, rồi làm bài tập. Buổi hai nói về hiện tại hoàn thành tiếp diễn.", "show": "title"},
    ]},
]

SITTING_2 = [
    {"kind": "title", "hook": "Khi nào thì nên nói have been V-ing, và khi nào have V3 là đủ?", "lines": [
        {"say": "Khi nào thì nên nói have been V-ing, và khi nào chỉ cần have V3 là đủ?", "show": "hook"},
        {"say": "Cách nhớ của thầy: đừng học thuộc lý thuyết, hãy nhớ hai câu mẫu rồi suy ra."},
    ]},
    {"kind": "scene", "visual": "ref_table", "eyebrow": "Hai câu mẫu", "title": "Nhớ hai câu, suy ra hai cách dùng",
     "data": {"cols": ["Cách dùng", "Câu mẫu"], "rows": TWO_SAMPLES,
              "rule": "Công thức: have hoặc has, been, rồi động từ thêm ing. Cả hai cách dùng đều đã bắt đầu từ trước."}, "lines": [
        {"say": "Câu mẫu thứ nhất. Bạn bắt đầu chơi bóng từ ba tiếng trước, và ngay lúc nói vẫn đang chơi.", "show": "q1"},
        {"en": "I have been playing football for three hours.", "vi": "Tôi chơi bóng ba tiếng nay rồi.", "gap": True},
        {"say": "Câu mẫu thứ hai. Bạn chạy một lúc lâu, vừa dừng lại, và hơi thở còn dồn dập."},
        {"en": "I'm out of breath because I have been running.", "vi": "Tôi hết hơi vì vừa chạy.", "gap": True, "show": "q2"},
        {"say": "Hai câu này đủ để suy ra hai cách dùng. Một: đã bắt đầu từ trước và còn đang làm. Hai: vừa dừng và còn dấu vết ở hiện tại.", "show": "rule"},
    ]},
    {"kind": "word", "headword": "reach", "lines": [{"say": "Một từ cho phần tiếp theo."}]},
    {"kind": "scene", "visual": "ref_table", "eyebrow": "Quy tắc của thầy", "title": "Thay bằng hiện tại hoàn thành",
     "data": {"cols": ["Cụm chỉ độ dài", "Ví dụ"], "rows": REPLACE,
              "quote": "Các bạn lưu ý cho mình là cứ chỗ nào mà các bạn sử dụng được Hiện tại hoàn thành tiếp diễn ấy, là các bạn có thể thay nó bằng Hiện tại hoàn thành được nhá!",
              "rule": "Có for hours, all morning, for the last six years: hai thì đều đúng."}, "lines": [
        {"say": "Có một quy tắc rất tiện, và thầy nói đúng nguyên văn: các bạn lưu ý cho mình là cứ chỗ nào mà các bạn sử dụng được Hiện tại hoàn thành tiếp diễn ấy, là các bạn có thể thay nó bằng Hiện tại hoàn thành được nhá!", "show": "quote"},
        {"say": "Xem ba câu có khoảng thời gian kéo dài.", "show": "r1"},
        {"en": "She has been writing that essay for hours.", "vi": "Cô ấy viết bài luận đó cả mấy tiếng rồi.", "gap": True},
        {"en": "She has written that essay for hours.", "vi": "Cô ấy viết bài luận đó cả mấy tiếng rồi.", "gap": True},
        {"say": "Câu thứ hai, về all morning.", "show": "r2"},
        {"en": "I have been trying to get in touch with Jenny all morning.", "vi": "Cả sáng nay tôi cố liên lạc với Jenny.", "gap": True},
        {"en": "I have tried to get in touch with Jenny all morning.", "vi": "Cả sáng nay tôi cố liên lạc với Jenny.", "gap": True},
        {"say": "Câu thứ ba.", "show": "r3"},
        {"en": "We have been living here for the last six years.", "vi": "Chúng tôi sống ở đây sáu năm nay.", "gap": True},
        {"en": "We have lived here for the last six years.", "vi": "Chúng tôi sống ở đây sáu năm nay.", "gap": True},
        {"say": "Có khoảng thời gian kéo dài, hai thì đều đúng.", "show": "rule"},
    ]},
    {"kind": "scene", "visual": "ref_table", "eyebrow": "Một lưu ý", "title": "Khi nào hai thì khác nghĩa",
     "data": {"cols": ["Nhấn vào", "Ví dụ"], "rows": EXCEPTION,
              "rule": "Nhấn vào quá trình hoặc dấu vết: hai thì khác nghĩa. Sách Destination B2 trang 7 cũng nêu như vậy."}, "lines": [
        {"say": "Quy tắc của thầy đúng khi câu có khoảng thời gian kéo dài. Nhưng khi người nói nhấn vào dấu vết còn lại ở hiện tại, hai thì khác nghĩa."},
        {"en": "I've been crying.", "vi": "Tôi vừa khóc.", "gap": True, "show": "x1"},
        {"say": "Mắt bạn còn đỏ. Nói I've cried thì mất ý đó. Sách Destination B2 trang 7 có một cặp ví dụ rất rõ."},
        {"en": "I have read that book.", "vi": "Tôi đã đọc xong cuốn đó.", "gap": True, "show": "x2"},
        {"en": "I have been reading that book.", "vi": "Tôi đang đọc dở cuốn đó.", "gap": True, "show": "x3"},
        {"say": "Cuốn sách đã đọc xong, hay vẫn đang đọc dở? Hai thì cho hai ý khác nhau. Khi phân vân, hãy hỏi mình muốn nhấn vào kết quả hay vào quá trình.", "show": "rule"},
    ]},
    {"kind": "scene", "visual": "fix_pairs", "eyebrow": "Lỗi thường gặp", "title": "Ba lỗi, ba cách sửa",
     "data": {"rows": TRAPS_2,
              "rule": "Động từ trạng thái không chia tiếp diễn. Với ever và never, thường dùng hoàn thành. Since cần thì hoàn thành."}, "lines": [
        {"say": "Ba lỗi hay gặp. Lỗi thứ nhất: động từ trạng thái.", "show": "g1"},
        {"en": "I have known her for years.", "vi": "Tôi biết cô ấy nhiều năm rồi.", "gap": True},
        {"say": "Lỗi thứ hai: sách ghi rằng tiếp diễn thường không dùng với ever và never.", "show": "g2"},
        {"en": "Have you ever visited Hue?", "vi": "Bạn đã từng đến Huế chưa?", "gap": True},
        {"say": "Lỗi thứ ba: since mà thiếu have been.", "show": "g3"},
        {"en": "I have been living here since 2020.", "vi": "Tôi sống ở đây từ năm 2020.", "gap": True},
        {"say": "Động từ trạng thái không chia tiếp diễn, và since cần thì hoàn thành.", "show": "rule"},
    ]},
    {"kind": "scene", "visual": "ref_table", "eyebrow": "Phát âm", "title": "breath và breathe",
     "data": {"cols": ["Từ loại", "Ví dụ"], "rows": BREATH,
              "rule": "breath là danh từ, đọc ngắn. breathe là động từ, có e ở cuối."}, "lines": [
        {"say": "Câu mẫu của buổi này có từ breath. Đừng đọc nhầm nó với breathe. Breath không có e, là danh từ.", "show": "w1"},
        {"en": "I am out of breath.", "vi": "Tôi hết hơi.", "gap": True},
        {"say": "Breathe có e ở cuối, là động từ."},
        {"en": "Breathe slowly.", "vi": "Hãy thở chậm.", "gap": True, "show": "w2"},
        {"say": "Danh từ không có e, động từ có e.", "show": "rule"},
    ]},
    {"kind": "recap", "lines": [
        {"say": "Giờ nói lại các câu của buổi này. Nghe một câu, rồi nói to trong quãng nghỉ.", "show": "title"},
    ]},
    {"kind": "end", "next": "Tiếp theo: học từ và mẫu ngữ pháp, làm bài tập, rồi buổi 3 để vận dụng.", "lines": [
        {"say": "Hết phần giảng của ngày ba. Bây giờ bạn học các từ và mẫu ngữ pháp trong app, làm bài tập, rồi sang buổi ba để nghe, nói và viết.", "show": "title"},
    ]},
]

RUBRIC = [
    {"criterion_vi": "Đúng đề, nội dung là của chính bạn", "max": 1, "note_vi": "Task response"},
    {"criterion_vi": "Chọn thì hợp với điều muốn nói: kéo tới bây giờ, đã xong, hay có mốc", "max": 2, "note_vi": "Grammatical range"},
    {"criterion_vi": "Dạng động từ đúng: have / has + V3, since và for, quá khứ đơn khi có mốc", "max": 2, "note_vi": "Grammatical accuracy"},
]


def reshape(sessions: list[dict], exercise_ids: list[str], card_of: dict[str, int]) -> list[dict]:
    """Day 3's sittings around the two lectures. Sitting 1 teaches cards 1-4 (timeline, two branches,
    first time / gone / been), sitting 2 cards 5-7 (the continuous, replacement and its exception, breath);
    the rest is a third sitting without a lecture."""
    pats = [g for s in sessions[:3] for g in s["grammar"]]
    allcheck = [i for s in sessions[:3] for i in s["check"]]
    s1, s2 = sessions[0], sessions[1]
    rest = sessions[3:]
    S1_WORDS = ["achieve"]
    S2_WORDS = ["reach"]
    all_words = [w for s in sessions[:3] for w in s["vocab"]]
    left = [w for w in all_words if w not in S1_WORDS + S2_WORDS]
    s1["vocab"], s2["vocab"] = S1_WORDS, S2_WORDS
    s1["grammar"], s2["grammar"] = pats[:4], pats[4:]
    quiz = [i for i in allcheck if i[4] in "IQ"]
    s1["check"] = [i for i in quiz if card_of[i] < 4]
    s2["check"] = [i for i in quiz if card_of[i] >= 4]
    moved = [i for i in allcheck if i not in quiz]
    s1["lecture"], s2["lecture"] = SITTING_1, SITTING_2
    s1["title_vi"] = "Buổi 1 · hiện tại hoàn thành, since và for, first time"
    s2["title_vi"] = "Buổi 2 · hoàn thành tiếp diễn, quy tắc thay thế, lưu ý"
    s3 = {
        "title_vi": "Buổi 3 · từ vựng và vận dụng: nghe chép, nói, viết",
        "can_do_vi": "Sau buổi này bạn biết thêm các từ về kết quả học tập, tự xếp và gõ được câu hoàn thành, nghe chép được câu và viết câu về chính mình.",
        "use_vi": s1["use_vi"],
        "vocab": left,
        "check": moved,
    }
    assert set(s1["check"] + s2["check"] + moved) <= set(exercise_ids)
    return [s1, s2, s3] + rest

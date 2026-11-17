"""G1 · Day 3 (lesson 46): the two lectures written by hand (lesson_audio.build_authored_lecture), and the
day's sittings reshaped around them. Same format as lecture_d1.py / lecture_d2.py.

Sources: the teacher's sessions 2 and 3. From session 2 (the Unit 1 exercises): a finished thing whose time the
speaker does not give; "all morning ... but I can't find her" and the three-step check; his replacement rule; frequency
adverbs with the present perfect; one gap, three right tenses (have gone / went / are going). From session 3: the two
separate branches of the present perfect, the vegetables question ("nobody is still buying them"), "Have you ever
been ...?" answered in the past simple, since / in / for (for is only a preposition), the two sample sentences of the
present perfect continuous. Destination B2, Unit 1, p. 6-8 gives the frame (It's the first time ..., read that book vs
been reading that book). The examples are this course's own; no teacher, book or page is named on a slide.
"""

PRON: dict[str, str] = {}

VEG = [
    {"key": "a1", "icon": "basket", "at": "done", "tense": "Hiện tại hoàn thành", "en": "Yes, I have bought some vegetables.", "vi": "Mua rồi. Lúc nào thì không nói."},
    {"key": "a2", "icon": "clock", "at": "point", "tense": "Quá khứ đơn", "en": "Yes, I bought some this morning.", "vi": "Mua rồi, và nói được lúc nào."},
]

BRANCHES = [
    {"key": "b1", "head": "Nhánh 1 · kéo tới bây giờ", "en": "I have studied the piano since 2003.", "vi": "Bắt đầu năm 2003, bây giờ vẫn học."},
    {"key": "b2", "head": "Nhánh 1 · kéo tới bây giờ", "en": "I have studied the piano for two years.", "vi": "Hai năm nay, bây giờ vẫn học."},
    {"key": "b3", "head": "Nhánh 2 · đã xong, không nói lúc nào", "en": "I have bought some vegetables.", "vi": "Mua xong rồi, không nêu thời điểm."},
    {"key": "b4", "head": "Nói được lúc nào: quá khứ đơn", "en": "I bought some vegetables this morning.", "vi": "Có thời điểm thì đổi thì."},
]

TWO_BRANCH_MIX = [
    {"key": "n1", "wrong": "I have studied the piano in 2003.", "right": "I studied the piano in 2003.", "why": "Việc đã xong mà nêu năm: quá khứ đơn."},
    {"key": "n2", "wrong": "I have been there two years ago.", "right": "I went there two years ago.", "why": "Có mốc đã qua: quá khứ đơn."},
]

ITALY = [
    {"key": "i1", "icon": "plane", "at": "done", "tense": "Hiện tại hoàn thành", "en": "Yes, I have.", "vi": "Đã từng. Chưa cần nói lúc nào."},
    {"key": "i2", "icon": "qmark", "at": "point", "tense": "Hỏi tiếp · quá khứ đơn", "en": "When did you go there?", "vi": "Hỏi lúc nào thì hỏi bằng quá khứ đơn."},
    {"key": "i3", "icon": "calendar", "at": "point", "tense": "Quá khứ đơn", "en": "I went there with my family two years ago.", "vi": "Kể lúc nào thì kể bằng quá khứ đơn."},
]

SINCE_FOR = [
    {"key": "f1", "head": "since + mốc: luôn là hoàn thành", "en": "I have studied the piano since 2003.", "vi": "Từ năm 2003 tới giờ."},
    {"key": "f2", "head": "in + năm: quá khứ đơn", "en": "I studied the piano in 2003.", "vi": "Học năm 2003, đã xong."},
    {"key": "f3", "head": "for + độ dài, còn làm", "en": "I have studied the piano for two years.", "vi": "Hai năm nay, vẫn học."},
    {"key": "f4", "head": "for + độ dài, đã nghỉ", "en": "I studied the piano for two years.", "vi": "Từng học hai năm, giờ đã nghỉ."},
]

FREQ = [
    {"key": "t1", "head": "Thói quen bây giờ", "en": "I often go to the library.", "vi": "Hiện tại đơn."},
    {"key": "t2", "head": "Từ trước tới nay", "en": "I have often seen him at the library.", "vi": "Hiện tại hoàn thành: gộp cả trước và nay."},
    {"key": "t3", "head": "Hỏi gộp trước và nay", "en": "Have you usually studied alone or in a group?", "vi": "Từ trước tới nay bạn thường học thế nào?"},
]

THREE_WAYS = [
    {"key": "h1", "head": "Đã đi, chưa về", "en": "My parents have gone to Hue.", "vi": "Hiện tại hoàn thành."},
    {"key": "h2", "head": "Chỉ kể việc đã đi", "en": "My parents went to Hue.", "vi": "Quá khứ đơn."},
    {"key": "h3", "head": "Sắp đi, đã có kế hoạch", "en": "My parents are going to Hue.", "vi": "Hiện tại tiếp diễn."},
]

PATTERNS = [
    {"key": "p1", "head": "It's the first time + hoàn thành", "en": "It's the first time I have ever eaten octopus.", "vi": "Lần đầu tiên tôi ăn bạch tuộc."},
    {"key": "p2", "head": "never … before: chưa bao giờ", "en": "Lan has never eaten sushi before.", "vi": "Lan chưa bao giờ ăn sushi."},
    {"key": "p3", "head": "have been to: đã đến và đã về", "en": "I have been to Hue twice.", "vi": "Tôi đã đến Huế hai lần."},
]

TRAPS_1 = [
    {"key": "e1", "wrong": "I work there since 2020.", "right": "I have worked there since 2020.", "why": "since cần thì hoàn thành."},
    {"key": "e2", "wrong": "When have you been there?", "right": "When did you go there?", "why": "Hỏi lúc nào: quá khứ đơn."},
    {"key": "e3", "wrong": "It's the first time I am speaking English on the phone.", "right": "It's the first time I have spoken English on the phone.", "why": "Sau It's the first time dùng hoàn thành."},
    {"key": "e4", "wrong": "Lan has ever eaten sushi before.", "right": "Lan has never eaten sushi before.", "why": "Giữ never để còn nghĩa chưa bao giờ."},
]

CALL = [
    {"key": "c1", "wrong": "I try to call Lan all morning.", "right": "I have been trying to call Lan all morning.", "why": "Bắt đầu từ sáng và bây giờ vẫn đang gọi."},
    {"key": "c2", "wrong": "I tried to call Lan all morning, but she isn't answering.", "right": "I have been trying to call Lan all morning, but she isn't answering.", "why": "Vế sau ở hiện tại: việc gọi chưa dừng."},
]

STEPS = [
    {"key": "k1", "head": "1 · Tìm cụm chỉ độ dài", "en": "all morning · for hours now · for the last four hours", "vi": "Việc kéo dài bao lâu?"},
    {"key": "k2", "head": "2 · Xem vế hiện tại", "en": "she still hasn't finished · Turn it off!", "vi": "Bây giờ còn làm không?"},
    {"key": "k3", "head": "3 · Chọn thì", "en": "have / has been + V-ing", "vi": "Hoặc have / has + V3."},
]

TWO_SAMPLES = [
    {"key": "q1", "icon": "ball", "at": "span", "tense": "Vẫn đang làm", "en": "I have been playing football for three hours.", "vi": "Bắt đầu ba tiếng trước, bây giờ vẫn đang chơi."},
    {"key": "q2", "icon": "runner", "at": "trace", "tense": "Vừa dừng, còn dấu vết", "en": "I'm out of breath because I have been running.", "vi": "Đã dừng chạy, nhưng vẫn còn thở dốc."},
]

REPLACE = [
    {"key": "r1", "head": "all morning", "en": "I have been trying to call Lan all morning.", "vi": "Thay được: I have tried to call Lan all morning."},
    {"key": "r2", "head": "for the last six years", "en": "We have been living here for the last six years.", "vi": "Thay được: We have lived here for the last six years."},
    {"key": "r3", "head": "for hours", "en": "She has been writing that essay for hours.", "vi": "Thay được: She has written that essay for hours."},
]

EXCEPTION = [
    {"key": "x1", "head": "Nhấn vào dấu vết", "en": "I've been crying.", "vi": "Mắt còn đỏ. Không đổi được thành I've cried."},
    {"key": "x2", "head": "Hoàn thành: đã xong", "en": "I have read that book.", "vi": "Đã đọc xong cuốn đó."},
    {"key": "x3", "head": "Tiếp diễn: chưa xong", "en": "I have been reading that book.", "vi": "Đang đọc dở cuốn đó."},
    {"key": "x4", "head": "Đếm việc đã xong", "en": "I have written three essays this week.", "vi": "Có số lượng: dùng hoàn thành."},
]

TRAPS_2 = [
    {"key": "g1", "wrong": "I have been knowing her for years.", "right": "I have known her for years.", "why": "know là động từ trạng thái, không chia tiếp diễn."},
    {"key": "g2", "wrong": "Have you ever been visiting Hue?", "right": "Have you ever visited Hue?", "why": "Tiếp diễn thường không dùng với ever và never."},
    {"key": "g3", "wrong": "I am living here since 2020.", "right": "I have been living here since 2020.", "why": "since cần thì hoàn thành."},
]

BREATH = [
    {"key": "w1", "head": "breath · danh từ", "en": "I am out of breath.", "vi": "Hơi thở: tôi hết hơi."},
    {"key": "w2", "head": "breathe · động từ", "en": "Breathe slowly.", "vi": "Thở: hãy thở chậm."},
]

SITTING_1 = [
    {"kind": "title", "hook": "Mua rau xong rồi. Vậy sao vẫn nói I have bought?", "lines": [
        {"say": "Bạn đi chợ về, rau đã nằm trong bếp. Việc mua đã xong. Vậy sao người ta vẫn đáp bằng hiện tại hoàn thành?", "show": "hook"},
        {"say": "Buổi này học hiện tại hoàn thành: hai nhánh tách biệt của nó, và lúc nào thì phải chuyển sang quá khứ đơn."},
    ]},
    {"kind": "scene", "visual": "tense_timeline", "eyebrow": "Thí nghiệm 1", "title": "Một câu hỏi, hai câu đáp",
     "data": {"question": "Did you buy any vegetables for tonight?", "question_vi": "Mua rau cho tối nay chưa?", "question_label": "Người nhà hỏi · quá khứ đơn",
              "answers": VEG, "rule": "Việc đã xong. Không nói lúc nào: hiện tại hoàn thành. Nói được lúc nào: quá khứ đơn."}, "lines": [
        {"say": "Người nhà hỏi bạn một câu ở quá khứ đơn."},
        {"en": "Did you buy any vegetables for tonight?", "vi": "Mua rau cho tối nay chưa?", "gap": True, "show": "q"},
        {"say": "Hãy đặt câu trả lời lên trục thời gian. Bên trái là quá khứ, vạch giữa là bây giờ.", "show": "axis"},
        {"say": "Cách đáp thứ nhất dùng hiện tại hoàn thành, dù câu hỏi ở quá khứ đơn."},
        {"en": "Yes, I have bought some vegetables.", "vi": "Có, tôi mua rau rồi.", "gap": True, "show": "a1"},
        {"say": "Có bạn hiểu câu này là vẫn đang mua. Không phải. Rau đã về tới bếp, không ai còn đứng ở chợ mà mua tiếp. Việc đã xong, chỉ là người nói không nêu lúc nào. Trên trục, nó nằm đâu đó trong quá khứ, kèm một dấu hỏi."},
        {"say": "Cách đáp thứ hai: bạn nói được lúc nào, nên dùng quá khứ đơn."},
        {"en": "Yes, I bought some this morning.", "vi": "Có, sáng nay tôi mua rồi.", "gap": True, "show": "a2"},
        {"say": "Cả hai câu đều đúng. Khác nhau ở một điểm: có nói lúc nào hay không. Và hỏi ở thì này, bạn vẫn đáp được ở thì khác.", "show": "rule"},
    ]},
    {"kind": "scene", "visual": "ref_table", "eyebrow": "Bản chất", "title": "Một dạng, hai nhánh tách biệt",
     "data": {"cols": ["Nhánh", "Ví dụ"], "rows": BRANCHES,
              "rule": "Công thức: have hoặc has, cộng quá khứ phân từ. Hai nhánh, hai ý khác nhau."}, "lines": [
        {"say": "Hiện tại hoàn thành có hai nhánh, và đừng trộn chúng với nhau. Nhánh một: việc bắt đầu trong quá khứ và bây giờ vẫn còn.", "show": "b1"},
        {"en": "I have studied the piano since 2003.", "vi": "Tôi học piano từ năm 2003.", "gap": True},
        {"en": "I have studied the piano for two years.", "vi": "Tôi học piano hai năm nay.", "gap": True, "show": "b2"},
        {"say": "Nhánh hai: việc đã xong, và người nói không nêu lúc nào. Đây chính là câu mua rau.", "show": "b3"},
        {"en": "I have bought some vegetables.", "vi": "Tôi mua rau rồi.", "gap": True, "recap": False},
        {"say": "Còn khi nêu được lúc nào thì đó là quá khứ đơn."},
        {"en": "I bought some vegetables this morning.", "vi": "Sáng nay tôi mua rau.", "gap": True, "show": "b4"},
        {"say": "Công thức chung: have hoặc has, cộng quá khứ phân từ. Nhưng hai nhánh mang hai ý khác nhau.", "show": "rule"},
    ]},
    {"kind": "scene", "visual": "fix_pairs", "eyebrow": "Một câu hỏi hay gặp", "title": "Không nói thời gian, sao lại có since 2003?",
     "data": {"rows": TWO_BRANCH_MIX,
              "rule": "Nhánh kéo tới bây giờ đi được với since và for. Nhánh đã xong thì không nêu lúc nào."}, "lines": [
        {"say": "Nhiều bạn thắc mắc: hiện tại hoàn thành không nêu thời gian, vậy sao lại nói được since 2003? Vì đó là hai nhánh khác nhau. Nhánh kéo tới bây giờ đi kèm được mốc bắt đầu và độ dài."},
        {"say": "Còn nhánh đã xong thì không được nêu lúc nào. Nêu ra là sai.", "show": "n1"},
        {"en": "I studied the piano in 2003.", "vi": "Tôi học piano vào năm 2003.", "gap": True},
        {"say": "Câu thứ hai cũng vậy: đã có two years ago thì dùng quá khứ đơn.", "show": "n2"},
        {"en": "I went there two years ago.", "vi": "Hai năm trước tôi đến đó.", "gap": True},
        {"say": "Since và for thuộc về nhánh kéo tới bây giờ. Nhánh đã xong thì không nêu lúc nào.", "show": "rule"},
    ]},
    {"kind": "scene", "visual": "tense_timeline", "eyebrow": "Thí nghiệm 2", "title": "Hỏi thì này, kể bằng thì khác",
     "data": {"question": "Have you ever been to Italy?", "question_vi": "Bạn đã từng đến Ý chưa?", "question_label": "Giám khảo hỏi · hiện tại hoàn thành",
              "answers": ITALY, "rule": "Hỏi trải nghiệm: hiện tại hoàn thành. Chạm tới lúc nào: quá khứ đơn."}, "lines": [
        {"say": "Trong phòng thi nói, giám khảo hỏi về trải nghiệm."},
        {"en": "Have you ever been to Italy?", "vi": "Bạn đã từng đến Ý chưa?", "gap": True, "show": "q"},
        {"say": "Bạn xác nhận là đã từng. Chưa cần nói lúc nào.", "show": "axis"},
        {"en": "Yes, I have.", "vi": "Có, tôi từng đến rồi.", "gap": True, "show": "i1"},
        {"say": "Giám khảo hỏi tiếp. Hỏi lúc nào thì không hỏi bằng hiện tại hoàn thành nữa."},
        {"en": "When did you go there?", "vi": "Bạn đến đó lúc nào?", "gap": True, "show": "i2"},
        {"say": "Và từ lúc bạn bắt đầu kể chi tiết, cả câu chuyện chuyển sang quá khứ đơn."},
        {"en": "I went there with my family two years ago.", "vi": "Hai năm trước tôi đến đó cùng gia đình.", "gap": True, "show": "i3"},
        {"say": "Không có chuyện hỏi thì nào phải đáp đúng thì đó. Hỏi trải nghiệm thì hoàn thành. Chạm tới lúc nào thì quá khứ đơn.", "show": "rule"},
    ]},
    {"kind": "word", "headword": "achieve", "lines": [{"say": "Một từ cho kết quả đã đạt được, rất hợp với thì này."}]},
    {"kind": "scene", "visual": "ref_table", "eyebrow": "Bẫy since, in, for", "title": "For chỉ là một giới từ",
     "data": {"cols": ["Cách nói", "Ví dụ"], "rows": SINCE_FOR,
              "rule": "since luôn đi với thì hoàn thành. for chỉ nói độ dài: còn làm thì hoàn thành, đã nghỉ thì quá khứ đơn."}, "lines": [
        {"say": "Ở trường, nhiều bạn học mẹo: thấy for là chia hiện tại hoàn thành. Mẹo đó sai. Hãy xem since trước, vì since luôn đi với thì hoàn thành.", "show": "f1"},
        {"en": "I have studied the piano since 2003.", "vi": "Tôi học piano từ năm 2003.", "gap": True, "recap": False},
        {"say": "Còn in cộng một năm là mốc đã qua, nên quá khứ đơn."},
        {"en": "I studied the piano in 2003.", "vi": "Tôi học piano vào năm 2003.", "gap": True, "show": "f2", "recap": False},
        {"say": "For thì khác. For two years chỉ nói độ dài. Nếu bây giờ vẫn còn học, dùng hiện tại hoàn thành."},
        {"en": "I have studied the piano for two years.", "vi": "Tôi học piano hai năm nay.", "gap": True, "show": "f3", "recap": False},
        {"say": "Nếu đã nghỉ rồi thì quá khứ đơn, vẫn cùng cụm for two years."},
        {"en": "I studied the piano for two years.", "vi": "Tôi từng học piano hai năm.", "gap": True, "show": "f4"},
        {"say": "For chỉ là một giới từ. Đừng nhìn dấu hiệu. Hãy hỏi: việc đó còn kéo tới bây giờ không?", "show": "rule"},
    ]},
    {"kind": "scene", "visual": "ref_table", "eyebrow": "Trạng từ tần suất", "title": "Often và usually đi được với hoàn thành",
     "data": {"cols": ["Ý muốn nói", "Ví dụ"], "rows": FREQ,
              "rule": "Trạng từ tần suất không đi với hiện tại tiếp diễn, nhưng đi được với hiện tại hoàn thành."}, "lines": [
        {"say": "Ngày một bạn đã học: trạng từ tần suất đi với hiện tại đơn, để nói thói quen bây giờ.", "show": "t1"},
        {"en": "I often go to the library.", "vi": "Tôi thường đến thư viện.", "gap": True, "recap": False},
        {"say": "Chúng không đi với hiện tại tiếp diễn, vì tiếp diễn là việc tạm thời, không lặp lại. Nhưng chúng đi được với hiện tại hoàn thành, khi bạn gộp cả trước kia lẫn bây giờ."},
        {"en": "I have often seen him at the library.", "vi": "Từ trước tới nay tôi thường thấy anh ấy ở thư viện.", "gap": True, "show": "t2"},
        {"say": "Câu hỏi cũng vậy: hỏi gộp từ trước tới nay."},
        {"en": "Have you usually studied alone or in a group?", "vi": "Từ trước tới nay bạn thường học một mình hay học nhóm?", "gap": True, "show": "t3"},
        {"say": "Tần suất không đi với tiếp diễn, nhưng đi được với hoàn thành.", "show": "rule"},
    ]},
    {"kind": "scene", "visual": "ref_table", "eyebrow": "Thí nghiệm 3", "title": "Một chỗ trống, ba cách chia",
     "data": {"cols": ["Điều muốn nói", "Câu"], "rows": THREE_WAYS,
              "rule": "Cả ba đều có lúc đúng. Chọn thì theo điều bạn muốn nói."}, "lines": [
        {"say": "Bố mẹ bạn đi Huế và tới Chủ nhật mới về. Chỗ trống cho động từ go chia thế nào? Có ba đáp án, mỗi đáp án một ý."},
        {"say": "Muốn nói đã đi và chưa về: hiện tại hoàn thành.", "show": "h1"},
        {"en": "My parents have gone to Hue.", "vi": "Bố mẹ tôi đi Huế rồi, chưa về.", "gap": True},
        {"say": "Chỉ muốn kể lại việc đã đi: quá khứ đơn.", "show": "h2"},
        {"en": "My parents went to Hue.", "vi": "Bố mẹ tôi đã đi Huế.", "gap": True, "recap": False},
        {"say": "Còn nếu chuyến đi chưa bắt đầu và đã có kế hoạch: hiện tại tiếp diễn.", "show": "h3"},
        {"en": "My parents are going to Hue.", "vi": "Bố mẹ tôi sắp đi Huế.", "gap": True, "recap": False},
        {"say": "Sách bài tập thường chỉ in một đáp án. Ngoài đời, bạn chọn thì theo điều mình muốn nói.", "show": "rule"},
    ]},
    {"kind": "scene", "visual": "ref_table", "eyebrow": "Ba mẫu cần thuộc", "title": "first time, never, been to",
     "data": {"cols": ["Mẫu", "Ví dụ"], "rows": PATTERNS,
              "rule": "Sau It's the first time dùng hoàn thành. Gone to là chưa về, been to là đã về."}, "lines": [
        {"say": "Ba mẫu nên thuộc. Mẫu thứ nhất: sau It's the first time, dùng hiện tại hoàn thành.", "show": "p1"},
        {"en": "It's the first time I have ever eaten octopus.", "vi": "Lần đầu tiên tôi ăn bạch tuộc.", "gap": True},
        {"say": "Mẫu thứ hai: never đi với hiện tại hoàn thành, nghĩa là chưa bao giờ.", "show": "p2"},
        {"en": "Lan has never eaten sushi before.", "vi": "Lan chưa bao giờ ăn sushi.", "gap": True},
        {"say": "Mẫu thứ ba: have been to nghĩa là đã từng đến và đã về. Khác với have gone to ở slide trước: đi và chưa về.", "show": "p3"},
        {"en": "I have been to Hue twice.", "vi": "Tôi đã đến Huế hai lần.", "gap": True},
        {"say": "Gone là chưa về. Been là đã về rồi.", "show": "rule"},
    ]},
    {"kind": "scene", "visual": "fix_pairs", "eyebrow": "Lỗi thường gặp", "title": "Bốn lỗi, bốn cách sửa",
     "data": {"rows": TRAPS_1,
              "rule": "Since và It's the first time thì hoàn thành. Hỏi lúc nào thì quá khứ đơn."}, "lines": [
        {"say": "Bốn lỗi người Việt hay mắc. Lỗi thứ nhất: since đi với hiện tại đơn.", "show": "e1"},
        {"en": "I have worked there since 2020.", "vi": "Tôi làm ở đó từ năm 2020.", "gap": True},
        {"say": "Lỗi thứ hai: hỏi lúc nào bằng hiện tại hoàn thành.", "show": "e2"},
        {"en": "When did you go there?", "vi": "Bạn đến đó lúc nào?", "gap": True, "recap": False},
        {"say": "Lỗi thứ ba: sau It's the first time.", "show": "e3"},
        {"en": "It's the first time I have spoken English on the phone.", "vi": "Lần đầu tiên tôi nói tiếng Anh qua điện thoại.", "gap": True},
        {"say": "Lỗi thứ tư: đổi never thành ever, làm mất nghĩa chưa bao giờ.", "show": "e4"},
        {"en": "Lan has never eaten sushi before.", "vi": "Lan chưa bao giờ ăn sushi.", "gap": True, "recap": False},
        {"say": "Since và It's the first time thì hoàn thành. Hỏi lúc nào thì quá khứ đơn.", "show": "rule"},
    ]},
    {"kind": "recap", "lines": [
        {"say": "Giờ nói lại các câu của buổi này. Nghe một câu, rồi nói to trong quãng nghỉ.", "show": "title"},
    ]},
    {"kind": "end", "next": "Tiếp theo: học các từ và mẫu ngữ pháp của buổi này, rồi làm bài tập.", "lines": [
        {"say": "Hết buổi một. Việc tiếp theo là học các từ và mẫu ngữ pháp trong app, rồi làm bài tập. Buổi hai nói về hiện tại hoàn thành tiếp diễn.", "show": "title"},
    ]},
]

SITTING_2 = [
    {"kind": "title", "hook": "Gọi cho Lan cả buổi sáng mà chưa được. I tried, hay I have been trying?", "lines": [
        {"say": "Bạn gọi cho Lan từ sáng. Bây giờ vẫn chưa gọi được, và bạn vẫn đang gọi. Nói I tried, hay I have been trying?", "show": "hook"},
        {"say": "Buổi này học hiện tại hoàn thành tiếp diễn: ba bước để chọn nó, và hai câu mẫu để nhớ nó."},
    ]},
    {"kind": "scene", "visual": "fix_pairs", "eyebrow": "Tình huống", "title": "Cả buổi sáng, và bây giờ vẫn chưa xong",
     "data": {"rows": CALL,
              "rule": "Bắt đầu từ trước, bây giờ vẫn đang làm: have been cộng động từ thêm ing."}, "lines": [
        {"say": "Nhiều bạn chia hiện tại đơn, vì thấy việc đang diễn ra. Nhưng việc gọi đã bắt đầu từ sáng.", "show": "c1"},
        {"en": "I have been trying to call Lan all morning.", "vi": "Cả sáng nay tôi cố gọi cho Lan.", "gap": True},
        {"say": "Có bạn lại chia quá khứ đơn. Hãy nhìn vế sau: she isn't answering. Vế đó ở hiện tại, nghĩa là bạn vẫn đang gọi.", "show": "c2"},
        {"en": "I have been trying to call Lan all morning, but she isn't answering.", "vi": "Cả sáng nay tôi cố gọi cho Lan, mà cô ấy không nghe máy.", "gap": True, "recap": False},
        {"say": "Một việc bắt đầu từ trước và bây giờ vẫn đang làm: hiện tại hoàn thành tiếp diễn.", "show": "rule"},
    ]},
    {"kind": "scene", "visual": "ref_table", "eyebrow": "Cách kiểm tra", "title": "Ba bước để chọn hoàn thành tiếp diễn",
     "data": {"cols": ["Bước", "Tìm gì trong câu"], "rows": STEPS,
              "rule": "Có độ dài, bây giờ còn làm: have been cộng động từ thêm ing."}, "lines": [
        {"say": "Gặp một câu như vậy, bạn kiểm tra ba bước. Bước một: tìm cụm chỉ độ dài, như all morning, for hours now, for the last four hours.", "show": "k1"},
        {"say": "Bước hai: xem vế ở hiện tại. Nó cho biết việc đó còn tiếp diễn hay không. Ví dụ she still hasn't finished: cô ấy vẫn chưa xong. Hay Turn it off: tắt đi, tức là tivi vẫn đang bật.", "show": "k2"},
        {"en": "Have you been watching TV for the last four hours? Turn it off!", "vi": "Em xem tivi bốn tiếng nay rồi à? Tắt đi!", "gap": True},
        {"say": "Bước ba: chọn have been cộng động từ thêm ing. Hoặc dùng hiện tại hoàn thành cũng được, lát nữa sẽ nói rõ.", "show": "k3"},
        {"say": "Có độ dài, và bây giờ còn làm: đó là chỗ của hoàn thành tiếp diễn.", "show": "rule"},
    ]},
    {"kind": "scene", "visual": "tense_timeline", "eyebrow": "Hai câu mẫu", "title": "Nhớ hai câu, suy ra hai cách dùng",
     "data": {"question": "have / has been + V-ing", "question_vi": "hai cách dùng", "question_label": "Công thức",
              "answers": TWO_SAMPLES, "rule": "Một: còn đang làm. Hai: vừa dừng, còn dấu vết ở hiện tại."}, "lines": [
        {"say": "Đừng học thuộc lý thuyết. Hãy nhớ hai câu mẫu, rồi từ đó suy ra cách dùng.", "show": "q"},
        {"say": "Câu mẫu thứ nhất. Bạn bắt đầu chơi bóng từ ba tiếng trước, và ngay lúc nói vẫn đang chơi. Trên trục, thanh kéo dài tới tận vạch bây giờ.", "show": "axis"},
        {"en": "I have been playing football for three hours.", "vi": "Tôi chơi bóng ba tiếng nay rồi.", "gap": True, "show": "q1"},
        {"say": "Câu mẫu thứ hai. Bạn chạy một lúc lâu, vừa dừng lại, và vẫn còn thở dốc. Thanh dừng ngay trước bây giờ, nhưng dấu vết thì còn."},
        {"en": "I'm out of breath because I have been running.", "vi": "Tôi hết hơi vì vừa chạy.", "gap": True, "show": "q2"},
        {"say": "Một câu tương tự: bạn rất mệt, vì đã chạy suốt ba tiếng và vừa dừng."},
        {"en": "I am very tired. I have been running for three hours.", "vi": "Tôi rất mệt. Tôi vừa chạy suốt ba tiếng.", "gap": True},
        {"say": "Hai câu này đủ để suy ra hai cách dùng. Một: đã bắt đầu từ trước và còn đang làm. Hai: vừa dừng và còn dấu vết ở hiện tại.", "show": "rule"},
    ]},
    {"kind": "word", "headword": "reach", "lines": [{"say": "Một từ cho phần tiếp theo."}]},
    {"kind": "scene", "visual": "ref_table", "eyebrow": "Quy tắc nhớ nhanh", "title": "Thay bằng hiện tại hoàn thành",
     "data": {"cols": ["Cụm chỉ độ dài", "Ví dụ"], "rows": REPLACE,
              "rule": "Chỗ nào dùng được hoàn thành tiếp diễn, thì thay bằng hiện tại hoàn thành cũng được."}, "lines": [
        {"say": "Có một quy tắc nhớ nhanh, rất có ích khi bạn phân vân. Xem ba câu có khoảng thời gian kéo dài.", "show": "r1"},
        {"en": "I have tried to call Lan all morning.", "vi": "Cả sáng nay tôi cố gọi cho Lan.", "gap": True},
        {"say": "Câu thứ hai.", "show": "r2"},
        {"en": "We have been living here for the last six years.", "vi": "Chúng tôi sống ở đây sáu năm nay.", "gap": True},
        {"en": "We have lived here for the last six years.", "vi": "Chúng tôi sống ở đây sáu năm nay.", "gap": True},
        {"say": "Câu thứ ba.", "show": "r3"},
        {"en": "She has been writing that essay for hours.", "vi": "Cô ấy viết bài luận đó mấy tiếng rồi.", "gap": True},
        {"say": "Chỗ nào dùng được hiện tại hoàn thành tiếp diễn, thì thay bằng hiện tại hoàn thành cũng được. Khi không chắc, chọn hiện tại hoàn thành.", "show": "rule"},
    ]},
    {"kind": "scene", "visual": "ref_table", "eyebrow": "Một lưu ý", "title": "Khi nào hai thì khác nghĩa",
     "data": {"cols": ["Nhấn vào", "Ví dụ"], "rows": EXCEPTION,
              "rule": "Kết quả và số lượng: hoàn thành. Quá trình và dấu vết: hoàn thành tiếp diễn."}, "lines": [
        {"say": "Quy tắc nhớ nhanh đúng khi câu có khoảng thời gian kéo dài. Nhưng khi người nói nhấn vào dấu vết còn lại ở hiện tại, hai thì khác nghĩa."},
        {"en": "I've been crying.", "vi": "Tôi vừa khóc.", "gap": True, "show": "x1"},
        {"say": "Mắt bạn còn đỏ. Nói I've cried thì mất ý đó. Còn một cặp ví dụ rất rõ nữa."},
        {"en": "I have read that book.", "vi": "Tôi đã đọc xong cuốn đó.", "gap": True, "show": "x2"},
        {"en": "I have been reading that book.", "vi": "Tôi đang đọc dở cuốn đó.", "gap": True, "show": "x3"},
        {"say": "Và khi đếm việc đã xong, dùng hiện tại hoàn thành, không dùng tiếp diễn.", "show": "x4"},
        {"en": "I have written three essays this week.", "vi": "Tuần này tôi viết xong ba bài luận.", "gap": True},
        {"say": "Khi phân vân, hãy hỏi mình muốn nhấn vào kết quả, hay vào quá trình.", "show": "rule"},
    ]},
    {"kind": "scene", "visual": "fix_pairs", "eyebrow": "Lỗi thường gặp", "title": "Ba lỗi, ba cách sửa",
     "data": {"rows": TRAPS_2,
              "rule": "Động từ trạng thái không chia tiếp diễn. Với ever và never, thường dùng hoàn thành. Since cần thì hoàn thành."}, "lines": [
        {"say": "Ba lỗi hay gặp. Lỗi thứ nhất: động từ trạng thái.", "show": "g1"},
        {"en": "I have known her for years.", "vi": "Tôi biết cô ấy nhiều năm rồi.", "gap": True},
        {"say": "Lỗi thứ hai: tiếp diễn thường không dùng với ever và never.", "show": "g2"},
        {"en": "Have you ever visited Hue?", "vi": "Bạn đã từng đến Huế chưa?", "gap": True},
        {"say": "Lỗi thứ ba: since mà thiếu have been.", "show": "g3"},
        {"en": "I have been living here since 2020.", "vi": "Tôi sống ở đây từ năm 2020.", "gap": True},
        {"say": "Động từ trạng thái không chia tiếp diễn, và since cần thì hoàn thành.", "show": "rule"},
    ]},
    {"kind": "scene", "visual": "ref_table", "eyebrow": "Phát âm", "title": "breath và breathe",
     "data": {"cols": ["Từ loại", "Ví dụ"], "rows": BREATH,
              "rule": "breath là danh từ, đọc ngắn. breathe là động từ, có e ở cuối."}, "lines": [
        {"say": "Câu mẫu của buổi này có từ breath. Đừng đọc nhầm nó với breathe. Breath là danh từ.", "show": "w1"},
        {"en": "I am out of breath.", "vi": "Tôi hết hơi.", "gap": True},
        {"say": "Breathe dài hơn một chữ ở cuối, và là động từ."},
        {"en": "Breathe slowly.", "vi": "Hãy thở chậm.", "gap": True, "show": "w2"},
        {"say": "Breath là danh từ, đọc ngắn. Breathe là động từ, đọc dài.", "show": "rule"},
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
    s1["title_vi"] = "Buổi 1 · hiện tại hoàn thành: hai nhánh, since và for"
    s2["title_vi"] = "Buổi 2 · hoàn thành tiếp diễn: ba bước, hai câu mẫu"
    s3 = {
        "title_vi": "Buổi 3 · từ vựng và vận dụng: nghe chép, nói, viết",
        "can_do_vi": "Sau buổi này bạn biết thêm các từ về kết quả học tập, tự xếp và gõ được câu hoàn thành, nghe chép được câu và viết câu về chính mình.",
        "use_vi": s1["use_vi"],
        "vocab": left,
        "check": moved,
    }
    assert set(s1["check"] + s2["check"] + moved) <= set(exercise_ids)
    return [s1, s2, s3] + rest

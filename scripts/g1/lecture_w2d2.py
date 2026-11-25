"""Week 2 · Day 2 (build day 22): the past continuous. Two lectures written by hand
(lesson_audio.build_authored_lecture) and the day's sittings reshaped around them. Same format as lecture_w2d1.py.

Sources: session 3 of the course, stages 2-5 (docs/WEEK2_PLAN.md, day 2): the point and the period on the time axis
("the past simple is one mark on the axis; the past continuous stresses the temporary stretch"), Yesterday I played /
was playing football at seven, Did you hang out with John? answered in two tenses, the estimated moment (at around
7 p.m.), the complaint with always, two actions at the same time with while (and what is lost with two past simples
and when), while with continuous forms and when with both, the short action that cuts in (Richard was watching TV
when the phone rang), repetition removes the temporariness (almost every day, every morning last week), stative own,
the split-second jumped, the translation trap of the Vietnamese word "đang", "questions about the past start with the
simplest tense" (Did you enjoy the film?), the guiding rule (unsure: past simple), the mixed paragraph
(I was playing football for a while, then I got bored...), and the bus scene of exercise B, item 1.
Corrections made before use (docs/WEEK2_PLAN.md, last section): the 1974/1975 war example is replaced by neutral
sentences; the mixed paragraph keeps only its first, natural part; "I went to drink" is not used.

Pronunciations: Oxford Learner's Dictionaries, British English, read 2026-11-25. A word without a checked
entry has none.
"""

PRON = {
    "crash": "/kræʃ/",
    "freeze": "/friːz/",
    "install": "/ɪnˈstɔːl/",
    "download": "/ˌdaʊnˈləʊd/",
    "connect": "/kəˈnekt/",
    "battery": "/ˈbætri/",
    "screen": "/skriːn/",
    "signal": "/ˈsɪɡnəl/",
    "software": "/ˈsɒftweə(r)/",
    "update": "/ˈʌpdeɪt/",
}

# a line under each word: its past form, or how the word is used
NOTES = {
    "crash": "Quá khứ: crashed, đuôi -ed đọc /t/. My laptop crashed: máy bị sập.",
    "freeze": "Động từ bất quy tắc: freeze, froze, frozen. The screen froze: màn hình bị treo.",
    "install": "Quá khứ: installed, đuôi -ed đọc /d/. install an app, install an update.",
    "download": "Quá khứ: downloaded, đuôi -ed thêm một âm tiết /ɪd/. Trái nghĩa: upload.",
    "connect": "Quá khứ: connected, đuôi -ed thêm một âm tiết /ɪd/. connect to the Internet.",
    "battery": "The battery died: hết pin. charge the battery: sạc pin.",
    "screen": "Màn hình của điện thoại, máy tính, TV. a cracked screen: màn hình bị nứt.",
    "signal": "no signal: không có sóng. a weak signal: sóng yếu.",
    "software": "Danh từ không đếm được: some software, a piece of software; không nói a software.",
    "update": "Danh từ nhấn âm đầu: UP-date. Động từ update nhấn âm sau.",
}

S1_WORDS = ["crash", "freeze", "install", "download", "connect"]
S2_WORDS = ["battery", "screen", "signal", "software", "update"]

FOOTBALL = [
    {"key": "a1", "icon": "ball", "at": "point", "tense": "Quá khứ đơn · một điểm", "en": "Yesterday I played football at seven.", "vi": "Kể việc đã xảy ra lúc bảy giờ."},
    {"key": "a2", "icon": "ball", "at": "pwin", "tense": "Quá khứ tiếp diễn · một khoảng", "en": "Yesterday I was playing football at seven.", "vi": "Lúc bảy giờ, việc đá bóng đang diễn ra."},
]

PERIODS = [
    {"key": "p1", "icon": "clock", "head": "Quanh một mốc", "en": "At five o'clock, I was reading a book.", "vi": "Lúc năm giờ, việc đọc sách đang diễn ra."},
    {"key": "p2", "icon": "house", "head": "Một giai đoạn tạm thời", "en": "In 2019, my brother was living in Da Nang.", "vi": "Sống ở đó một thời gian, rồi chuyển đi."},
    {"key": "p3", "icon": "tv", "head": "Suốt một quãng", "en": "I was playing video games all morning.", "vi": "Kéo dài cả buổi sáng."},
]

TWO_ACTIONS = [
    {"key": "c1", "icon": "phone", "at": "cut", "tense": "when · bị cắt ngang", "en": "Richard was watching TV when the phone rang.", "vi": "Việc dài đang diễn ra, việc ngắn chen vào."},
    {"key": "c2", "icon": "crash", "at": "cut", "tense": "when · bị cắt ngang", "en": "I was downloading a file when my laptop crashed.", "vi": "Đang tải tệp thì máy sập."},
    {"key": "c3", "icon": "ball", "at": "pair", "tense": "while · song song", "en": "I was playing football while my friends were playing badminton.", "vi": "Hai việc diễn ra cùng lúc."},
    {"key": "c4", "icon": "ball", "at": "two", "tense": "hai câu quá khứ đơn", "en": "I played football when my friends played badminton.", "vi": "Chỉ kể hai việc; không rõ có cùng lúc không."},
]

SCENE = [
    {"key": "h1", "icon": "angry", "head": "Than phiền · was always + V-ing", "en": "When we shared a room, Zoe was always taking my things.", "vi": "Một thói quen gây bực mình trong quá khứ."},
    {"key": "h2", "icon": "rain", "head": "Cảnh nền · quá khứ tiếp diễn", "en": "It was raining and everyone was hurrying home.", "vi": "Bức tranh đang diễn ra khi câu chuyện bắt đầu."},
    {"key": "h3", "icon": "bulb_off", "head": "Việc chính · quá khứ đơn", "en": "Then the lights went out.", "vi": "Việc xảy ra, đẩy câu chuyện đi tiếp."},
]

NOT_CONT = [
    {"key": "n1", "head": "Việc lặp lại", "en": "Last summer I went swimming almost every day.", "vi": "Lặp lại nhiều lần: không còn là một khoảng tạm thời."},
    {"key": "n2", "head": "Động từ trạng thái", "en": "I didn't know the password.", "vi": "know, own, need, believe: hầu như không dùng tiếp diễn."},
    {"key": "n3", "head": "Việc chớp nhoáng", "en": "A car came round the corner and I jumped out of the way.", "vi": "Xảy ra trong tích tắc."},
    {"key": "n4", "head": "Việc nối tiếp", "en": "I charged my phone as soon as I got home.", "vi": "Việc này xong mới tới việc kia."},
]

JOHN = [
    {"key": "j1", "icon": "cup", "at": "point", "tense": "Quá khứ đơn · kể việc", "en": "Yes, I hung out with him at a convenience store.", "vi": "Có, tôi đi chơi với cậu ấy ở một cửa hàng tiện lợi."},
    {"key": "j2", "icon": "cup", "at": "pwin", "tense": "Quá khứ tiếp diễn · nhấn khoảng", "en": "Yes, we were hanging out at a convenience store at around 7 p.m.", "vi": "Khoảng bảy giờ tối, hai người đang ở đó."},
]

TRAPS = [
    {"key": "e1", "wrong": "I watching TV at eight.", "right": "I was watching TV at eight.", "why": "Thì tiếp diễn luôn có was hoặc were."},
    {"key": "e2", "wrong": "We was playing football at seven.", "right": "We were playing football at seven.", "why": "We đi với were."},
    {"key": "e3", "wrong": "I wasn't knowing the password.", "right": "I didn't know the password.", "why": "know là động từ trạng thái."},
    {"key": "e4", "wrong": "In 2015, the population was reaching ten million.", "right": "In 2015, the population reached ten million.", "why": "Số liệu một năm đã qua: quá khứ đơn."},
]

ANSWER = [
    {"key": "q1", "role": "Dựng cảnh", "tense": "Quá khứ tiếp diễn", "en": "Last month I was writing an important essay on my laptop.", "vi": "Tháng trước tôi đang viết một bài luận quan trọng trên laptop."},
    {"key": "q2", "role": "Việc bất ngờ", "tense": "Tiếp diễn + quá khứ đơn", "en": "I was working on the last paragraph when the screen suddenly froze.", "vi": "Tôi đang viết đoạn cuối thì màn hình bỗng bị treo."},
    {"key": "q3", "role": "Kết quả", "tense": "Quá khứ đơn", "en": "I restarted it, but I lost about an hour of work.", "vi": "Tôi khởi động lại, nhưng mất khoảng một giờ làm việc."},
    {"key": "q4", "role": "Bây giờ", "tense": "Hiện tại đơn", "en": "Now I save my files every few minutes.", "vi": "Bây giờ cứ vài phút tôi lại lưu tệp."},
]

SITTING_1 = [
    {"kind": "title", "hook": "Tám giờ tối qua bạn đang làm gì?", "lines": [
        {"say": "Một người bạn hỏi: tám giờ tối qua bạn đang làm gì? Bạn trả lời bằng thì nào, và câu đó khác gì một câu quá khứ đơn?", "show": "hook"},
        {"say": "Hôm qua, quá khứ đơn là một điểm trên trục thời gian. Hôm nay ta phóng to vào bên trong điểm đó. Buổi này học công thức của thì quá khứ tiếp diễn, sự khác nhau giữa một điểm và một khoảng, rồi hai việc xảy ra cùng lúc."},
    ]},
    {"kind": "scene", "visual": "sentence_forms", "eyebrow": "Công thức", "title": "Ba dạng câu của quá khứ tiếp diễn",
     "data": {"rows": [
                  {"key": "aff", "label": "Khẳng định", "parts": ["I", "was watching", "TV at eight."], "hi": [1], "vi": "Lúc tám giờ tôi đang xem TV."},
                  {"key": "neg", "label": "Phủ định", "parts": ["They", "weren't listening", "to the teacher."], "hi": [1], "vi": "Họ không nghe giáo viên giảng."},
                  {"key": "qst", "label": "Câu hỏi", "parts": ["What", "were you doing", "at eight?"], "hi": [1], "vi": "Lúc tám giờ bạn đang làm gì?"},
              ],
              "persons": [{"who": "I · he · she · it", "verb": "was watching"}, {"who": "you · we · they", "verb": "were watching"}],
              "persons_plain": True,
              "spelling_title": "Thêm đuôi ing",
              "spelling": [["download", "downloading"], ["charge", "charging"], ["stop", "stopping"], ["lie", "lying"]],
              "short": ["Yes, I was.", "No, I wasn't."],
              "rule": "Mọi câu đều có was hoặc were, theo sau là động từ thêm đuôi ing."}, "lines": [
        {"say": "Công thức có hai phần: was hoặc were, rồi động từ thêm đuôi ing. Ngôi I, he, she, it dùng was; ngôi you, we, they dùng were.", "show": "persons"},
        {"en": "I was watching TV at eight.", "vi": "Lúc tám giờ tôi đang xem TV.", "gap": True, "show": "aff"},
        {"say": "Câu phủ định: wasn't hoặc weren't."},
        {"en": "They weren't listening to the teacher.", "vi": "Họ không nghe giáo viên giảng.", "gap": True, "show": "neg"},
        {"say": "Câu hỏi: đưa was hoặc were lên trước chủ ngữ. Đây cũng là câu hỏi ở đầu buổi."},
        {"en": "What were you doing at eight last night?", "vi": "Tám giờ tối qua bạn đang làm gì?", "gap": True, "show": "qst"},
        {"say": "Trả lời ngắn thì dùng lại was hoặc were, và đọc rõ chữ was.", "show": "short"},
        {"say": "Cách viết đuôi ing: phần lớn động từ chỉ cần thêm vào, như downloading. Động từ có chữ e ở cuối thì bỏ e: charge thành charging. Từ một âm tiết tận cùng bằng một nguyên âm và một phụ âm, như stop, thì gấp đôi phụ âm cuối: stopping. Work hay rain thì không. Lie thành lying.", "show": "spelling"},
        {"say": "Lỗi hay gặp nhất là bỏ mất was. Câu sau thiếu động từ chính."},
        {"en": "I watching TV at eight."},
        {"say": "Mọi câu đều có was hoặc were, theo sau là động từ thêm đuôi ing.", "show": "rule"},
    ]},
    {"kind": "scene", "visual": "tense_timeline", "eyebrow": "Bản chất", "title": "Một điểm hay một khoảng",
     "data": {"question": "What did you do yesterday at seven?", "question_vi": "Hôm qua lúc bảy giờ bạn làm gì?", "question_label": "Có người hỏi",
              "answers": FOOTBALL, "rule": "Quá khứ đơn: một điểm, việc đã xảy ra. Quá khứ tiếp diễn: một khoảng tạm thời đang diễn ra quanh mốc đó."}, "lines": [
        {"say": "Hôm qua lúc bảy giờ, bạn đi đá bóng. Có hai cách kể, và cả hai đều đúng.", "show": "q"},
        {"say": "Trên trục này, bên trái là quá khứ, vạch giữa là bây giờ.", "show": "axis"},
        {"say": "Cách một: quá khứ đơn. Bạn nhìn việc đá bóng như một điểm trên trục: nó đã xảy ra, vậy thôi.", "show": "a1"},
        {"en": "Yesterday I played football at seven.", "vi": "Hôm qua lúc bảy giờ tôi đá bóng.", "gap": True},
        {"say": "Cách hai: quá khứ tiếp diễn. Bạn phóng to vào bên trong khoảng thời gian đó: lúc bảy giờ, trận bóng đang diễn ra, đã bắt đầu từ trước.", "show": "a2"},
        {"en": "Yesterday I was playing football at seven.", "vi": "Hôm qua lúc bảy giờ tôi đang đá bóng.", "gap": True},
        {"say": "Mốc không cần chính xác tới từng phút. Khoảng bảy giờ vẫn là một mốc."},
        {"en": "at around seven", "vi": "khoảng bảy giờ", "gap": True, "recap": False},
        {"say": "Kể cả khi người nói nhớ nhầm hay nói dối về giờ giấc, câu vẫn chia như vậy, vì ngữ pháp theo điều người nói trình bày. Quá khứ đơn là một điểm, việc đã xảy ra. Quá khứ tiếp diễn là một khoảng tạm thời đang diễn ra quanh mốc đó.", "show": "rule"},
    ]},
    {"kind": "scene", "visual": "picture_cards", "eyebrow": "Mở rộng", "title": "Ba kiểu khoảng tạm thời",
     "data": {"rows": PERIODS, "rule": "Quá khứ tiếp diễn nhìn từ bên trong một khoảng tạm thời."}, "lines": [
        {"say": "Khoảng tạm thời có ba kiểu. Kiểu một: quanh một mốc giờ cụ thể.", "show": "p1"},
        {"en": "At five o'clock, I was reading a book.", "vi": "Lúc năm giờ tôi đang đọc sách.", "gap": True},
        {"say": "Kiểu hai: một giai đoạn tạm thời trong đời. Anh tôi sống ở Đà Nẵng một thời gian, rồi chuyển đi.", "show": "p2"},
        {"en": "In 2019, my brother was living in Da Nang.", "vi": "Năm 2019, anh tôi đang sống ở Đà Nẵng.", "gap": True},
        {"say": "Kiểu ba: kéo dài suốt một quãng, như cả buổi sáng.", "show": "p3"},
        {"en": "I was playing video games all morning.", "vi": "Tôi chơi điện tử suốt buổi sáng.", "gap": True},
        {"say": "Một lưu ý cho người Việt: đừng thấy chữ đang trong câu tiếng Việt là chọn thì tiếp diễn. Một sự kiện được kể trọn vẹn, như kết quả một trận đấu hay một kỳ thi đã xong, vẫn kể bằng quá khứ đơn. Quá khứ tiếp diễn nhìn từ bên trong một khoảng tạm thời.", "show": "rule"},
    ]},
    {"kind": "scene", "visual": "tense_timeline", "eyebrow": "Hai việc cùng lúc", "title": "Cắt ngang và song song",
     "data": {"question": "when · while", "question_vi": "hai việc trong cùng một câu", "question_label": "Hai liên từ",
              "answers": TWO_ACTIONS, "rule": "Việc ngắn cắt ngang: when + quá khứ đơn. Hai việc song song: while + quá khứ tiếp diễn."}, "lines": [
        {"say": "Giờ là hai việc trong cùng một câu.", "show": "q"},
        {"say": "Vẫn là trục thời gian, quá khứ bên trái.", "show": "axis"},
        {"say": "Trường hợp một: một việc dài đang diễn ra, thì một việc ngắn chen vào. Việc dài chia tiếp diễn, việc ngắn chia quá khứ đơn, nối bằng when.", "show": "c1"},
        {"en": "Richard was watching TV when the phone rang.", "vi": "Richard đang xem TV thì điện thoại reo.", "gap": True},
        {"say": "Cùng khuôn đó với chuyện công nghệ: đang tải tệp thì máy sập.", "show": "c2"},
        {"en": "I was downloading a file when my laptop crashed.", "vi": "Tôi đang tải một tệp thì laptop bị sập.", "gap": True},
        {"say": "Trường hợp hai: hai việc diễn ra cùng một lúc. Cả hai vế chia tiếp diễn, nối bằng while.", "show": "c3"},
        {"en": "I was playing football while my friends were playing badminton.", "vi": "Tôi đá bóng trong lúc các bạn tôi chơi cầu lông.", "gap": True},
        {"say": "Nếu đổi cả hai vế sang quá khứ đơn, câu chỉ còn kể hai việc. Có thể tôi đá bóng lúc bảy giờ sáng, còn các bạn chơi cầu lông lúc chín giờ.", "show": "c4"},
        {"en": "I played football when my friends played badminton.", "vi": "Tôi đá bóng, các bạn tôi chơi cầu lông.", "gap": True, "recap": False},
        {"say": "While thường đi với thì tiếp diễn; when đi được với cả hai thì. Việc ngắn cắt ngang: when cộng quá khứ đơn. Hai việc song song: while cộng quá khứ tiếp diễn.", "show": "rule"},
    ]},
    {"kind": "word", "headword": "crash", "lines": [{"say": "Năm động từ của buổi này đều là chuyện công nghệ gặp sự cố, rất hợp để kể bằng thì tiếp diễn. Từ thứ nhất. Quá khứ là crashed, đuôi ed giống worked."}]},
    {"kind": "word", "headword": "freeze", "lines": [{"say": "Từ thứ hai, một động từ bất quy tắc: quá khứ là froze."}]},
    {"kind": "word", "headword": "install", "lines": [{"say": "Từ thứ ba. Quá khứ là installed, đuôi ed giống played."}]},
    {"kind": "word", "headword": "download", "lines": [{"say": "Từ thứ tư. Quá khứ là downloaded, đuôi ed thêm một âm tiết, giống wanted."}]},
    {"kind": "word", "headword": "connect", "lines": [{"say": "Từ cuối. Quá khứ là connected, cũng thêm một âm tiết."}]},
    {"kind": "recap", "lines": [
        {"say": "Giờ nói lại các câu của buổi này. Nghe một câu, rồi nói to trong quãng nghỉ.", "show": "title"},
    ]},
    {"kind": "end", "next": "Tiếp theo: học thẻ và từ của buổi này, rồi làm bài.", "lines": [
        {"say": "Hết buổi một. Bạn học các thẻ và từ trong app, rồi làm bài. Buổi hai nói về những lúc không dùng thì tiếp diễn, và cách kể một câu chuyện bằng hai thì.", "show": "title"},
    ]},
]

SITTING_2 = [
    {"kind": "title", "hook": "I was getting up at six every morning last week: câu này sai ở đâu?", "lines": [
        {"say": "Tuần trước sáng nào bạn cũng dậy lúc sáu giờ, và bạn kể lại bằng câu dưới đây. Trong bài thi, câu này sai ở đâu?", "show": "hook"},
        {"en": "I was getting up at six every morning last week."},
        {"say": "Buổi này học những lúc không dùng thì tiếp diễn, hai cách dùng nữa của nó, và cách kể một câu chuyện bằng hai thì."},
    ]},
    {"kind": "scene", "visual": "ref_table", "eyebrow": "Khi nào không dùng", "title": "Bốn trường hợp dùng quá khứ đơn",
     "data": {"rows": NOT_CONT, "rule": "Lặp lại, trạng thái, chớp nhoáng, nối tiếp: dùng quá khứ đơn."}, "lines": [
        {"say": "Trường hợp một trả lời câu hỏi đầu buổi: việc lặp lại. Sáng nào cũng dậy lúc sáu giờ là lặp lại nhiều lần, không còn là một khoảng tạm thời quanh một mốc. Bài thi chọn quá khứ đơn.", "show": "n1"},
        {"en": "I got up at six every morning last week.", "vi": "Tuần trước sáng nào tôi cũng dậy lúc sáu giờ.", "gap": True},
        {"en": "Last summer I went swimming almost every day.", "vi": "Hè năm ngoái hầu như ngày nào tôi cũng đi bơi.", "gap": True},
        {"say": "Trường hợp hai: động từ trạng thái, như know, own, need, believe. Biết hay không biết là một trạng thái, không phải một việc đang làm.", "show": "n2"},
        {"en": "I didn't know the password.", "vi": "Tôi không biết mật khẩu.", "gap": True},
        {"say": "Trường hợp ba: việc chớp nhoáng. Không ai nhấn khoảng nửa giây đang nhảy.", "show": "n3"},
        {"en": "A car came round the corner and I jumped out of the way.", "vi": "Một chiếc xe rẽ qua góc phố và tôi nhảy tránh sang bên.", "gap": True},
        {"say": "Trường hợp bốn: các việc nối tiếp nhau, việc này xong mới tới việc kia.", "show": "n4"},
        {"en": "I charged my phone as soon as I got home.", "vi": "Vừa về đến nhà là tôi sạc điện thoại.", "gap": True},
        {"say": "Lặp lại, trạng thái, chớp nhoáng, nối tiếp: dùng quá khứ đơn. Và khi phân vân mà không thấy tính tạm thời, hãy chọn quá khứ đơn.", "show": "rule"},
    ]},
    {"kind": "scene", "visual": "picture_cards", "eyebrow": "Hai cách dùng nữa", "title": "Than phiền và dựng cảnh",
     "data": {"rows": SCENE, "rule": "was always + V-ing: than phiền. Thì tiếp diễn dựng cảnh nền; quá khứ đơn kể việc chính."}, "lines": [
        {"say": "Cách dùng thứ nhất: than phiền về một thói quen gây bực mình trong quá khứ. Công thức là was hoặc were, rồi always, rồi động từ thêm đuôi ing.", "show": "h1"},
        {"en": "When we shared a room, Zoe was always taking my things. It was so annoying!", "vi": "Hồi ở chung phòng, Zoe cứ lấy đồ của tôi. Bực lắm!", "gap": True},
        {"say": "Để ý: always đứng sau was. Và câu thường đi kèm một lời bình, nói rằng việc đó thật phiền."},
        {"say": "Cách dùng thứ hai: dựng cảnh nền ở đầu một câu chuyện, như mở đầu một bộ phim.", "show": "h2"},
        {"en": "It was raining and everyone was hurrying home.", "vi": "Trời đang mưa, mọi người đang vội về nhà.", "gap": True},
        {"say": "Rồi việc chính xảy ra, đẩy câu chuyện đi tiếp. Việc chính chia quá khứ đơn.", "show": "h3"},
        {"en": "Then the lights went out.", "vi": "Rồi đèn tắt phụt.", "gap": True},
        {"say": "Was always cộng động từ thêm đuôi ing để than phiền. Thì tiếp diễn dựng cảnh nền, còn quá khứ đơn kể việc chính.", "show": "rule"},
    ]},
    {"kind": "scene", "visual": "tense_timeline", "eyebrow": "Hỏi và kể", "title": "Người hỏi dùng thì đơn giản nhất",
     "data": {"question": "Did you hang out with John yesterday?", "question_vi": "Hôm qua bạn có đi chơi với John không?", "question_label": "Có người hỏi",
              "answers": JOHN, "rule": "Câu hỏi về quá khứ thường mở đầu bằng quá khứ đơn; người trả lời chọn thì theo điều muốn nhấn."}, "lines": [
        {"say": "Khi hỏi về quá khứ, người bản xứ thường dùng thì đơn giản nhất: quá khứ đơn.", "show": "q"},
        {"en": "Did you hang out with John yesterday?", "vi": "Hôm qua bạn có đi chơi với John không?", "gap": True, "recap": False},
        {"say": "Quá khứ bên trái, bây giờ ở vạch giữa.", "show": "axis"},
        {"say": "Người trả lời có thể chỉ kể việc, bằng quá khứ đơn.", "show": "j1"},
        {"en": "Yes, I hung out with him at a convenience store.", "vi": "Có, tôi đi chơi với cậu ấy ở một cửa hàng tiện lợi.", "gap": True},
        {"say": "Hoặc nhấn vào khoảng tạm thời quanh một mốc, bằng thì tiếp diễn.", "show": "j2"},
        {"en": "Yes, we were hanging out at a convenience store at around 7 p.m.", "vi": "Có, khoảng bảy giờ tối chúng tôi đang ở một cửa hàng tiện lợi.", "gap": True},
        {"say": "Vì vậy khi hỏi cảm nhận về cả bộ phim, hãy hỏi gọn bằng quá khứ đơn."},
        {"en": "Did you enjoy the film?", "vi": "Bạn có thích bộ phim không?", "gap": True},
        {"say": "Câu hỏi về quá khứ thường mở đầu bằng quá khứ đơn; người trả lời chọn thì theo điều mình muốn nhấn.", "show": "rule"},
    ]},
    {"kind": "scene", "visual": "fix_pairs", "eyebrow": "Lỗi thường gặp", "title": "Bốn lỗi, bốn cách sửa",
     "data": {"rows": TRAPS, "rule": "Có was hoặc were, đúng ngôi. Trạng thái, số liệu đã qua: quá khứ đơn."}, "lines": [
        {"say": "Bốn lỗi hay gặp nhất. Lỗi một: bỏ mất was.", "show": "e1"},
        {"en": "I was watching TV at eight.", "vi": "Lúc tám giờ tôi đang xem TV.", "gap": True, "recap": False},
        {"say": "Lỗi hai: sai ngôi. We, you, they đi với were.", "show": "e2"},
        {"en": "We were playing football at seven.", "vi": "Lúc bảy giờ chúng tôi đang đá bóng.", "gap": True},
        {"say": "Lỗi ba: dùng tiếp diễn cho động từ trạng thái.", "show": "e3"},
        {"en": "I didn't know the password.", "vi": "Tôi không biết mật khẩu.", "gap": True, "recap": False},
        {"say": "Lỗi bốn hay gặp trong bài viết mô tả số liệu: dịch chữ đang thành thì tiếp diễn. Số liệu của một năm đã qua dùng quá khứ đơn.", "show": "e4"},
        {"en": "In 2015, the population reached ten million.", "vi": "Năm 2015, dân số đạt mười triệu.", "gap": True},
        {"say": "Thì tiếp diễn luôn có was hoặc were, đúng ngôi. Động từ trạng thái và số liệu đã qua dùng quá khứ đơn.", "show": "rule"},
    ]},
    {"kind": "word", "headword": "battery", "lines": [{"say": "Trước khi kể một câu chuyện, học năm danh từ về thiết bị. Từ thứ nhất. Câu ví dụ có cách nói hết pin: pin chết."}]},
    {"kind": "word", "headword": "screen", "lines": [{"say": "Từ thứ hai: màn hình."}]},
    {"kind": "word", "headword": "signal", "lines": [{"say": "Từ thứ ba: sóng điện thoại."}]},
    {"kind": "word", "headword": "software", "lines": [{"say": "Từ thứ tư. Đây là danh từ không đếm được, nên không đi với a."}]},
    {"kind": "word", "headword": "update", "lines": [{"say": "Từ cuối. Khi là danh từ, trọng âm rơi vào âm đầu."}]},
    {"kind": "scene", "visual": "speaking_answer", "eyebrow": "IELTS Speaking Part 2", "title": "Dựng cảnh, rồi kể việc chính",
     "data": {"question": "Describe a time when a piece of technology stopped working.", "question_vi": "Kể về một lần một thiết bị công nghệ ngừng hoạt động.",
              "short": "My laptop froze.", "parts": ANSWER,
              "rule": "Dựng cảnh bằng quá khứ tiếp diễn, kể việc chính bằng quá khứ đơn, nói tới bây giờ bằng thì hiện tại."}, "lines": [
        {"say": "Đề Part 2: kể về một lần một thiết bị công nghệ ngừng hoạt động."},
        {"en": "Describe a time when a piece of technology stopped working.", "show": "q"},
        {"say": "Chỉ nói máy bị treo thì câu chuyện chưa bắt đầu.", "show": "short"},
        {"say": "Câu một: dựng cảnh bằng thì tiếp diễn. Lúc đó bạn đang làm gì?"},
        {"en": "Last month I was writing an important essay on my laptop.", "vi": "Tháng trước tôi đang viết một bài luận quan trọng trên laptop.", "gap": True, "show": "q1"},
        {"say": "Câu hai: việc bất ngờ cắt ngang. Việc dài chia tiếp diễn, việc ngắn chia quá khứ đơn."},
        {"en": "I was working on the last paragraph when the screen suddenly froze.", "vi": "Tôi đang viết đoạn cuối thì màn hình bỗng bị treo.", "gap": True, "show": "q2"},
        {"say": "Câu ba: kết quả, các việc nối tiếp, nên dùng quá khứ đơn."},
        {"en": "I restarted it, but I lost about an hour of work.", "vi": "Tôi khởi động lại, nhưng mất khoảng một giờ làm việc.", "gap": True, "show": "q3"},
        {"say": "Câu bốn: thói quen của bạn bây giờ, nên dùng hiện tại đơn."},
        {"en": "Now I save my files every few minutes.", "vi": "Bây giờ cứ vài phút tôi lại lưu tệp.", "gap": True, "show": "q4"},
        {"say": "Dựng cảnh bằng quá khứ tiếp diễn, kể việc chính bằng quá khứ đơn, nói tới bây giờ bằng thì hiện tại. Hãy viết lại bốn câu này cho đúng với chuyện của chính bạn.", "show": "rule"},
    ]},
    {"kind": "recap", "lines": [
        {"say": "Giờ nói lại các câu của buổi này. Nghe một câu, rồi nói to trong quãng nghỉ.", "show": "title"},
    ]},
    {"kind": "end", "next": "Tiếp theo: học thẻ và từ, làm bài, rồi buổi 3 và hai bài luyện theo sách.", "lines": [
        {"say": "Hết phần giảng của ngày hai. Bạn học các thẻ và từ trong app, làm bài, rồi sang buổi ba để xếp câu, nghe chép và kể chuyện của chính bạn. Cuối ngày có hai bài luyện theo sách, mỗi câu kèm lời giải thích.", "show": "title"},
    ]},
]

RUBRIC = [
    {"criterion_vi": "Đúng đề: có cảnh lúc đó, việc xảy ra và kết quả", "max": 1, "note_vi": "Task response"},
    {"criterion_vi": "Dựng cảnh bằng quá khứ tiếp diễn, kể việc chính bằng quá khứ đơn", "max": 2, "note_vi": "Grammatical range"},
    {"criterion_vi": "Dạng động từ đúng: was / were + V-ing, V-ed và dạng bất quy tắc", "max": 2, "note_vi": "Grammatical accuracy"},
]

CAP = 7  # a lecture sitting holds at most seven questions; the rest open sitting 3


def reshape(sessions: list[dict], exercise_ids: list[str], card_of: dict[str, int]) -> list[dict]:
    """Sitting 1 teaches cards 1-3 (forms, point and period, when and while) with five verbs; sitting 2 cards 4-6
    (complaint and scene, when not to use it, asking and telling) with five nouns; the production work (build,
    type, dictation, speaking) is a third sitting without a lecture. The book's exercises follow as their own sittings."""
    pats = [g for s in sessions[:2] for g in s["grammar"]]
    allcheck = [i for s in sessions[:2] for i in s["check"]]
    s1, s2 = sessions[0], sessions[1]
    rest = sessions[2:]
    all_words = [w for s in sessions[:2] for w in s["vocab"]]
    assert sorted(all_words) == sorted(S1_WORDS + S2_WORDS), all_words
    s1["vocab"], s2["vocab"] = S1_WORDS, S2_WORDS
    s1["grammar"], s2["grammar"] = pats[:3], pats[3:]
    quiz = [i for i in allcheck if i[5] in "IQT"]
    def pick(cards: range) -> tuple[list[str], list[str]]:
        """Round-robin over the sitting's cards (one timeline question first in each), so every card it teaches gets
        a question before any card gets a second one; shown in card order."""
        def queue(c: int) -> list[str]:
            mine = sorted(i for i in quiz if card_of[i] == c)
            ts = [i for i in mine if i[5] == "T"]
            return ts[:1] + [i for i in mine if i[5] != "T"] + ts[1:]  # one timeline question, then other kinds
        queues = [queue(c) for c in cards]
        chosen: list[str] = []
        while len(chosen) < CAP and any(queues):
            for q in queues:
                if q and len(chosen) < CAP:
                    chosen.append(q.pop(0))
        rank = {x: k for k, x in enumerate(chosen)}
        chosen.sort(key=lambda i: (card_of[i], rank[i]))
        return chosen, [i for q in queues for i in q]
    s1["check"], spill1 = pick(range(0, 3))
    s2["check"], spill2 = pick(range(3, 6))
    moved = spill1 + spill2 + [i for i in allcheck if i not in quiz]
    s1["lecture"], s2["lecture"] = SITTING_1, SITTING_2
    s1["title_vi"] = "Buổi 1 · công thức, một điểm hay một khoảng, when và while"
    s2["title_vi"] = "Buổi 2 · khi nào không dùng tiếp diễn, kể chuyện bằng hai thì"
    s1["can_do_vi"] = "Sau buổi này bạn lập được câu quá khứ tiếp diễn, phân biệt một điểm với một khoảng tạm thời, và kể được việc bị cắt ngang hoặc hai việc song song."
    s2["can_do_vi"] = "Sau buổi này bạn biết khi nào chỉ cần quá khứ đơn, than phiền và dựng cảnh bằng thì tiếp diễn, và kể được một câu chuyện Speaking bằng hai thì."
    s3 = {
        "title_vi": "Buổi 3 · vận dụng: xếp câu, gõ, nghe chép, kể chuyện",
        "can_do_vi": "Sau buổi này bạn chọn đúng giữa quá khứ đơn và tiếp diễn, tự xếp và gõ đúng câu, nghe chép được câu có was, were và đuôi ing, và kể một chuyện của chính mình.",
        "use_vi": s1["use_vi"],
        "vocab": [],
        "check": moved,
    }
    assert set(s1["check"] + s2["check"] + moved) <= set(exercise_ids)
    return [s1, s2, s3] + rest

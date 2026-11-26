"""Week 3 · Day 3 (build day 33): plans and appointments, what you can see coming, and the present simple for the
future. Two lectures written by hand (lesson_audio.build_authored_lecture) and the day's sittings reshaped around
them. Same format as lecture_w3d1.py.

Sources: session 5 of the course, stage 3 (docs/WEEK3_PLAN.md, Day 3): plans that are appointments ("I'm going to
see my doctor today", "I'm getting my hair cut today" against "I'll have my hair cut today"; in many countries a
doctor, a hairdresser or a restaurant needs a booking), predictions from present evidence (dark clouds; two friends
on a motorbike about to hit the car in front: "Stop! It's going to hit!"), the present simple for timetables and
after when ("We will buy you your PS5 when we have the money"); session 6, stage 1: exercise B (We aren't / We're
not; Does the concert last…? is information, not a prediction; the timetable; Does the restaurant open…?).
Corrections made before use (docs/WEEK3_PLAN.md, last section): We're not stresses the negative only as a habit of
speech, not a rule; the brand name of the games console is not used.

Pronunciations: Oxford Learner's Dictionaries, British English, read 2026-11-26. A word without a checked
entry has none.
"""

PRON = {
    "book": "/bʊk/",
    "confirm": "/kənˈfɜːm/",
    "attend": "/əˈtend/",
    "commute": "/kəˈmjuːt/",
    "negotiate": "/nɪˈɡəʊʃieɪt/",
    "reservation": "/ˌrezəˈveɪʃn/",
    "conference": "/ˈkɒnfərəns/",
    "overtime": "/ˈəʊvətaɪm/",
    "branch": "/brɑːntʃ/",
    "receptionist": "/rɪˈsepʃənɪst/",
}

NOTES = {
    "book": "book a table, book a ticket, book an appointment. Là động từ, khác book (quyển sách).",
    "confirm": "confirm a booking: xác nhận đặt chỗ. Danh từ: confirmation.",
    "attend": "attend a meeting, attend a conference. Không thêm to sau attend.",
    "commute": "Đi làm hằng ngày, thường là đường xa. Người đi làm như vậy: commuter.",
    "negotiate": "negotiate a contract, negotiate a salary. Danh từ: negotiation.",
    "reservation": "make a reservation: đặt chỗ trước (nhà hàng, khách sạn). Gần nghĩa: booking.",
    "conference": "Hội nghị lớn, nhiều người, thường kéo dài một hai ngày. Trọng âm ở âm tiết đầu.",
    "overtime": "work overtime: làm thêm giờ. Không có a đứng trước.",
    "branch": "Chi nhánh của ngân hàng, cửa hàng, công ty. Nghĩa gốc: cành cây.",
    "receptionist": "Người ở quầy lễ tân, nhận lịch hẹn và đón khách.",
}

S1_WORDS = ["book", "confirm", "attend", "commute", "negotiate"]
S2_WORDS = ["reservation", "conference", "overtime", "branch", "receptionist"]

HAIRCUT = [
    {"key": "a1", "icon": "calendar", "head": "Đã đặt lịch", "en": "I'm getting my hair cut today.", "vi": "Đã gọi hẹn giờ với tiệm."},
    {"key": "a2", "icon": "bulb", "head": "Vừa quyết định", "en": "I'll have my hair cut today.", "vi": "Mới nghĩ ra, chưa hẹn."},
    {"key": "a3", "icon": "plus_heart", "head": "Khám bác sĩ", "en": "I'm going to see my doctor today.", "vi": "Ở nhiều nước, phải hẹn trước."},
    {"key": "a4", "icon": "steak", "head": "Ăn nhà hàng", "en": "We're having dinner with a client tonight.", "vi": "Đã đặt bàn."},
]

MOTORBIKE = [
    {"key": "r1", "icon": "discuss", "label": "Cảnh 1", "en": "Two friends are chatting on a motorbike.", "vi": "Hai bạn vừa đi xe máy vừa nói chuyện."},
    {"key": "r2", "icon": "car", "label": "Cảnh 2", "en": "The car in front stops suddenly.", "vi": "Ô tô phía trước dừng đột ngột."},
    {"key": "r3", "icon": "crash", "label": "Cảnh 3", "en": "Stop! You're going to hit it!", "vi": "Dừng lại! Sắp đâm vào rồi!"},
    {"key": "r4", "icon": "rain", "label": "Cảnh 4", "en": "Look at those clouds. It's going to rain.", "vi": "Nhìn mây kìa. Sắp mưa rồi."},
]

TIMETABLE = [
    {"key": "t1", "head": "Lịch tàu", "en": "The train for Oxford leaves at 10.15.", "vi": "Lịch cố định, người nói không đổi được."},
    {"key": "t2", "head": "Hỏi thông tin", "en": "Does the concert on Thursday last more than two hours?", "vi": "Không đoán, chỉ hỏi điều đã định."},
    {"key": "t3", "head": "Giờ mở cửa", "en": "Does the restaurant open next Sunday?", "vi": "Hỏi nhà hàng có mở cửa không."},
]

WHEN = [
    {"key": "w1", "icon": "gamepad", "head": "when", "en": "We'll buy you a games console when we have the money.", "vi": "Khi nào có tiền: vẫn chia hiện tại."},
    {"key": "w2", "icon": "phone", "head": "as soon as", "en": "Let me know as soon as you arrive.", "vi": "Đến nơi là báo ngay."},
    {"key": "w3", "icon": "clock", "head": "until", "en": "We won't start until everyone is here.", "vi": "Chưa đủ người thì chưa bắt đầu."},
    {"key": "w4", "icon": "checklist", "head": "as soon as · đã xong", "en": "I'll send you the report as soon as I've finished it.", "vi": "Nhấn việc xong trước: hiện tại hoàn thành."},
]

NOT = [
    {"key": "n1", "head": "We aren't", "en": "We aren't going to miss the train.", "vi": "Rút gọn are not."},
    {"key": "n2", "head": "We're not", "en": "We're not going to miss the train.", "vi": "Rút gọn we are; dễ nhấn vào not."},
    {"key": "n3", "head": "I'm not", "en": "I'm not working tomorrow.", "vi": "Với I chỉ có một cách."},
]

TRAPS = [
    {"key": "e1", "wrong": "I'll call you when I will get there.", "right": "I'll call you when I get there.", "why": "Vế when nói về tương lai vẫn chia hiện tại đơn."},
    {"key": "e2", "wrong": "Look out! You will hit the car!", "right": "Look out! You're going to hit the car!", "why": "Dấu hiệu ngay trước mắt: going to."},
    {"key": "e3", "wrong": "The train is leaving at 10.15, according to the timetable.", "right": "The train leaves at 10.15, according to the timetable.", "why": "Lịch trình cố định: hiện tại đơn."},
    {"key": "e4", "wrong": "I'm buying a yacht when I'm older.", "right": "I'm going to buy a yacht when I'm older.", "why": "Ý định chưa sắp xếp: going to, không dùng đuôi ing."},
]

ANSWER = [
    {"key": "p1", "role": "Việc đã hẹn", "tense": "be + V-ing", "en": "I'm meeting some old friends on Saturday morning.", "vi": "Sáng thứ Bảy tôi gặp mấy người bạn cũ."},
    {"key": "p2", "role": "Bằng chứng đã hẹn", "tense": "hiện tại hoàn thành", "en": "We've booked a table at a small café near my office.", "vi": "Chúng tôi đã đặt bàn ở một quán cà phê nhỏ gần chỗ làm."},
    {"key": "p3", "role": "Giờ cố định", "tense": "hiện tại đơn", "en": "In the afternoon, my yoga class starts at three.", "vi": "Buổi chiều, lớp yoga của tôi bắt đầu lúc ba giờ."},
    {"key": "p4", "role": "Sau khi xong", "tense": "when + hiện tại · will", "en": "When the class finishes, I'll probably just relax at home.", "vi": "Học xong, chắc tôi chỉ ở nhà nghỉ ngơi."},
]

SITTING_1 = [
    {"kind": "title", "hook": "Hai người cùng nói chiều nay đi cắt tóc. Ai đã đặt lịch?", "lines": [
        {"say": "Hai người cùng nói: hôm nay tôi đi cắt tóc. Một người dùng will, một người dùng đuôi ing. Người nào đã gọi điện đặt lịch?", "show": "hook"},
        {"say": "Buổi này học ba trường hợp của tương lai: việc đã hẹn, dự đoán từ dấu hiệu trước mắt, rồi khi nào hiện tại đơn cũng nói về tương lai."},
    ]},
    {"kind": "scene", "visual": "picture_cards", "eyebrow": "Thí nghiệm", "title": "Đã hẹn hay mới định?",
     "data": {"rows": HAIRCUT, "rule": "Việc đã đặt lịch, đã hẹn: đuôi ing hoặc going to. Vừa quyết định: will."}, "lines": [
        {"say": "Người thứ nhất đã gọi cho tiệm và hẹn giờ. Người đó dùng đuôi ing.", "show": "a1"},
        {"en": "I'm getting my hair cut today.", "vi": "Hôm nay tôi đi cắt tóc.", "gap": True},
        {"say": "Người thứ hai mới nhìn gương sáng nay, thấy tóc dài quá, nên quyết định luôn. Người đó dùng will.", "show": "a2"},
        {"en": "I'll have my hair cut today.", "vi": "Hôm nay tôi sẽ đi cắt tóc.", "gap": True},
        {"say": "Ở Việt Nam, muốn cắt tóc thì cứ ra tiệm. Nhưng ở nhiều nước, khám bác sĩ, cắt tóc, ăn nhà hàng đều phải đặt lịch trước. Vì vậy, người bản ngữ mặc định đó là việc đã hẹn.", "show": "a3"},
        {"en": "I'm going to see my doctor today.", "vi": "Hôm nay tôi đi khám bác sĩ.", "gap": True},
        {"say": "Bữa tối với khách hàng cũng thế: bàn đã đặt, giờ đã hẹn.", "show": "a4"},
        {"en": "We're having dinner with a client tonight.", "vi": "Tối nay chúng tôi ăn tối với một khách hàng.", "gap": True},
        {"say": "Việc đã đặt lịch, đã hẹn với người khác thì dùng đuôi ing hoặc going to. Còn ý vừa quyết định ngay lúc nói thì dùng will.", "show": "rule"},
    ]},
    {"kind": "scene", "visual": "story_strip", "eyebrow": "Dấu hiệu trước mắt", "title": "Sắp đâm rồi!",
     "data": {"frame": "strip", "panels": MOTORBIKE, "rule": "Thấy rõ dấu hiệu ngay lúc nói, việc gần như chắc xảy ra: going to. Không dùng will."}, "lines": [
        {"say": "Hai bạn vừa đi xe máy vừa mải nói chuyện.", "show": "r1"},
        {"en": "Two friends are chatting on a motorbike.", "vi": "Hai bạn vừa đi xe máy vừa nói chuyện.", "gap": True, "recap": False},
        {"say": "Bỗng chiếc ô tô phía trước phanh gấp.", "show": "r2"},
        {"en": "The car in front stops suddenly.", "vi": "Ô tô phía trước dừng đột ngột.", "gap": True, "recap": False},
        {"say": "Người ngồi sau thấy rõ chuyện sắp xảy ra, liền hét lên.", "show": "r3"},
        {"en": "Stop! You're going to hit it!", "vi": "Dừng lại! Sắp đâm vào rồi!", "gap": True},
        {"say": "Cũng vậy khi bạn nhìn lên trời và thấy mây đen kéo đến.", "show": "r4"},
        {"en": "Look at those clouds. It's going to rain.", "vi": "Nhìn mây kìa. Sắp mưa rồi.", "gap": True},
        {"say": "Dấu hiệu nằm ngay trước mắt người nói, việc gần như chắc chắn xảy ra: dùng going to. Lúc đó không ai hét lên bằng will.", "show": "rule"},
    ]},
    {"kind": "scene", "visual": "ref_table", "eyebrow": "Hiện tại đơn chỉ tương lai", "title": "Không đoán, chỉ thông tin",
     "data": {"rows": TIMETABLE, "rule": "Lịch trình cố định và câu hỏi thông tin về một sự kiện: hiện tại đơn, dù việc ở tương lai."}, "lines": [
        {"say": "Bạn đọc lịch tàu. Tàu đi Oxford chạy lúc mười giờ mười lăm. Người nói không đoán gì cả, cũng không đổi được lịch đó. Vì vậy dùng hiện tại đơn.", "show": "t1"},
        {"en": "The train for Oxford leaves at 10.15.", "vi": "Tàu đi Oxford chạy lúc 10 giờ 15.", "gap": True},
        {"say": "Buổi hòa nhạc ở thứ Năm, tức là ở tương lai. Nhưng người hỏi chỉ muốn biết thông tin đã định: dài bao lâu. Không có ý đoán, nên hỏi bằng does.", "show": "t2"},
        {"en": "Does the concert on Thursday last more than two hours?", "vi": "Buổi hòa nhạc thứ Năm kéo dài hơn hai tiếng không?", "gap": True},
        {"say": "Hỏi chủ nhật tới nhà hàng có mở cửa không cũng vậy.", "show": "t3"},
        {"en": "Does the restaurant open next Sunday?", "vi": "Chủ nhật tới nhà hàng có mở cửa không?", "gap": True},
        {"say": "Lịch trình cố định, hay câu hỏi thông tin về một sự kiện đã định: dùng hiện tại đơn, dù việc ở tương lai. Will dành cho lúc bạn muốn hỏi người nghe đoán thế nào.", "show": "rule"},
    ]},
    {"kind": "word", "headword": "book", "lines": [{"say": "Năm động từ của buổi này là những việc của lịch hẹn ở chỗ làm. Từ thứ nhất: đặt bàn, đặt vé, đặt lịch. Ở đây là động từ, không phải quyển sách."}]},
    {"kind": "word", "headword": "confirm", "lines": [{"say": "Từ thứ hai: xác nhận."}]},
    {"kind": "word", "headword": "attend", "lines": [{"say": "Từ thứ ba: tham dự. Câu ví dụ dùng đuôi ing cho một hội nghị đã lên lịch."}]},
    {"kind": "word", "headword": "commute", "lines": [{"say": "Từ thứ tư: đi làm hằng ngày, thường là đường xa."}]},
    {"kind": "word", "headword": "negotiate", "lines": [{"say": "Từ cuối: đàm phán. Câu ví dụ là một cuộc họp đã hẹn cho ngày mai."}]},
    {"kind": "recap", "lines": [
        {"say": "Người đã gọi điện hẹn tiệm tóc là người dùng đuôi ing. Giờ nói lại các câu của buổi này. Nghe một câu, rồi nói to trong quãng nghỉ.", "show": "title"},
    ]},
    {"kind": "end", "next": "Tiếp theo: học thẻ và từ của buổi này, rồi làm bài.", "lines": [
        {"say": "Hết buổi một. Bạn học các thẻ và từ trong app, rồi làm bài. Buổi hai học vế câu bắt đầu bằng when, until, hay cụm ngay khi, rồi hai cách rút gọn của câu phủ định.", "show": "title"},
    ]},
]

SITTING_2 = [
    {"kind": "title", "hook": "Khi nào có tiền, bố mẹ sẽ mua máy chơi game. Vế đầu chia thì gì?", "lines": [
        {"say": "Bố mẹ hứa với con: khi nào có tiền, bố mẹ sẽ mua máy chơi game. Vế khi nào có tiền nói về tương lai. Vậy có dùng will không?", "show": "hook"},
        {"say": "Buổi này học vế câu bắt đầu bằng when, until, hay cụm ngay khi; hai cách rút gọn của câu phủ định; rồi một câu Speaking về cuối tuần."},
    ]},
    {"kind": "scene", "visual": "picture_cards", "eyebrow": "Thí nghiệm", "title": "Vế sau when: vẫn chia hiện tại",
     "data": {"rows": WHEN, "rule": "Nói về tương lai, vế sau when, as soon as, before, after, until chia hiện tại đơn, không dùng will. Vế chính mới dùng will."}, "lines": [
        {"say": "Câu của bố mẹ. Vế chính dùng will. Vế khi nào có tiền chia hiện tại đơn, dù việc đó ở tương lai.", "show": "w1"},
        {"en": "We'll buy you a games console when we have the money.", "vi": "Khi nào có tiền, bố mẹ sẽ mua cho con máy chơi game.", "gap": True},
        {"say": "Với cụm nghĩa là ngay khi cũng vậy: đến nơi là báo ngay.", "show": "w2"},
        {"en": "Let me know as soon as you arrive.", "vi": "Đến nơi thì báo tôi ngay.", "gap": True},
        {"say": "Với until: chưa đủ người thì chưa bắt đầu.", "show": "w3"},
        {"en": "We won't start until everyone is here.", "vi": "Chưa đủ mọi người thì chúng ta chưa bắt đầu.", "gap": True},
        {"say": "Muốn nhấn là việc kia phải xong trước, dùng hiện tại hoàn thành. Vẫn không dùng will.", "show": "w4"},
        {"en": "I'll send you the report as soon as I've finished it.", "vi": "Tôi làm xong báo cáo là gửi bạn ngay.", "gap": True},
        {"say": "Nói về tương lai, vế bắt đầu bằng when, before, after, until, hay cụm ngay khi, chia hiện tại đơn, hoặc hiện tại hoàn thành. Chỉ vế chính mới dùng will.", "show": "rule"},
    ]},
    {"kind": "scene", "visual": "ref_table", "eyebrow": "Phủ định", "title": "We aren't hay We're not?",
     "data": {"rows": NOT, "rule": "We aren't và We're not đều đúng. Khi nói, tách riêng not ra thì dễ nhấn vào ý phủ định."}, "lines": [
        {"say": "Hai cách rút gọn của câu phủ định. Cách thứ nhất gộp are với not.", "show": "n1"},
        {"en": "We aren't going to miss the train.", "vi": "Chúng ta sẽ không lỡ chuyến tàu.", "gap": True},
        {"say": "Cách thứ hai gộp we với are, để not đứng riêng. Khi nói, chữ not đứng riêng nên dễ nhấn giọng hơn.", "show": "n2"},
        {"en": "We're not going to miss the train.", "vi": "Chúng ta sẽ không lỡ chuyến tàu đâu.", "gap": True},
        {"say": "Với chủ ngữ tôi thì chỉ có một cách.", "show": "n3"},
        {"en": "I'm not working tomorrow.", "vi": "Mai tôi không đi làm.", "gap": True},
        {"say": "Cả hai cách đều đúng ngữ pháp, đừng sửa câu vốn đã đúng. Khi nói, tách riêng not ra thì dễ nhấn vào ý phủ định.", "show": "rule"},
    ]},
    {"kind": "scene", "visual": "fix_pairs", "eyebrow": "Lỗi thường gặp", "title": "Bốn lỗi, bốn cách sửa",
     "data": {"rows": TRAPS, "rule": "Vế when: hiện tại. Dấu hiệu trước mắt: going to. Lịch trình: hiện tại đơn. Ý định chưa sắp xếp: going to."}, "lines": [
        {"say": "Bốn lỗi hay gặp nhất của hôm nay. Lỗi một: dùng will ở vế có when.", "show": "e1"},
        {"en": "I'll call you when I get there.", "vi": "Tôi sẽ gọi bạn khi tôi đến nơi.", "gap": True},
        {"say": "Lỗi hai: dùng will khi dấu hiệu ở ngay trước mắt.", "show": "e2"},
        {"en": "Look out! You're going to hit the car!", "vi": "Coi chừng! Bạn sắp đâm vào xe rồi!", "gap": True, "recap": False},
        {"say": "Lỗi ba: dùng đuôi ing cho lịch tàu.", "show": "e3"},
        {"en": "The train leaves at 10.15, according to the timetable.", "vi": "Theo lịch, tàu chạy lúc 10 giờ 15.", "gap": True, "recap": False},
        {"say": "Lỗi bốn: dùng đuôi ing cho một ý định xa, chưa sắp xếp gì.", "show": "e4"},
        {"en": "I'm going to buy a yacht when I'm older.", "vi": "Lớn lên, tôi sẽ mua một chiếc du thuyền.", "gap": True},
        {"say": "Vế sau when chia hiện tại. Dấu hiệu trước mắt: going to. Lịch trình cố định: hiện tại đơn. Ý định chưa sắp xếp: going to.", "show": "rule"},
    ]},
    {"kind": "word", "headword": "reservation", "lines": [{"say": "Trước câu Speaking, học năm danh từ về lịch hẹn và chỗ làm. Từ thứ nhất: sự đặt chỗ trước."}]},
    {"kind": "word", "headword": "conference", "lines": [{"say": "Từ thứ hai: hội nghị. Câu ví dụ dùng hiện tại đơn cho giờ bắt đầu đã định."}]},
    {"kind": "word", "headword": "overtime", "lines": [{"say": "Từ thứ ba: giờ làm thêm."}]},
    {"kind": "word", "headword": "branch", "lines": [{"say": "Từ thứ tư: chi nhánh. Nghĩa gốc là cành cây."}]},
    {"kind": "word", "headword": "receptionist", "lines": [{"say": "Từ cuối: lễ tân. Câu ví dụ có vế when chia hiện tại đơn."}]},
    {"kind": "scene", "visual": "speaking_answer", "eyebrow": "IELTS Speaking Part 1", "title": "Lịch hẹn, giờ cố định, rồi sau đó",
     "data": {"question": "What are you going to do this weekend?", "question_vi": "Cuối tuần này bạn định làm gì?",
              "short": "Nothing much.", "parts": ANSWER,
              "rule": "Việc đã hẹn: đuôi ing. Giờ cố định: hiện tại đơn. Vế when: hiện tại đơn, vế chính will."}, "lines": [
        {"say": "Giám khảo hỏi cuối tuần này bạn định làm gì."},
        {"en": "What are you going to do this weekend?", "show": "q"},
        {"say": "Đáp cụt một câu thì quá ngắn.", "show": "short"},
        {"say": "Câu một: một việc đã hẹn, dùng đuôi ing."},
        {"en": "I'm meeting some old friends on Saturday morning.", "vi": "Sáng thứ Bảy tôi gặp mấy người bạn cũ.", "gap": True, "show": "p1"},
        {"say": "Câu hai: chứng tỏ đã hẹn, vì bàn đã được đặt."},
        {"en": "We've booked a table at a small café near my office.", "vi": "Chúng tôi đã đặt bàn ở một quán cà phê nhỏ gần chỗ làm.", "gap": True, "show": "p2"},
        {"say": "Câu ba: một lớp học có giờ cố định, dùng hiện tại đơn."},
        {"en": "In the afternoon, my yoga class starts at three.", "vi": "Buổi chiều, lớp yoga của tôi bắt đầu lúc ba giờ.", "gap": True, "show": "p3"},
        {"say": "Câu bốn: sau khi học xong. Vế when chia hiện tại, vế chính dùng will."},
        {"en": "When the class finishes, I'll probably just relax at home.", "vi": "Học xong, chắc tôi chỉ ở nhà nghỉ ngơi.", "gap": True, "show": "p4"},
        {"say": "Việc đã hẹn: đuôi ing. Giờ cố định: hiện tại đơn. Vế when chia hiện tại, vế chính dùng will. Hãy viết lại bốn câu này cho đúng với cuối tuần của bạn.", "show": "rule"},
    ]},
    {"kind": "recap", "lines": [
        {"say": "Khi nào có tiền: vế đó vẫn chia hiện tại đơn, vế chính mới dùng will. Giờ nói lại các câu của buổi này. Nghe một câu, rồi nói to trong quãng nghỉ.", "show": "title"},
    ]},
    {"kind": "end", "next": "Tiếp theo: học thẻ và từ, làm bài, rồi buổi 3 để xếp câu, nghe chép và viết.", "lines": [
        {"say": "Hết phần giảng của ngày ba. Bạn học các thẻ và từ trong app, làm bài, rồi sang buổi ba để xếp câu, nghe chép và viết về kế hoạch tuần sau của bạn.", "show": "title"},
    ]},
]

RUBRIC = [
    {"criterion_vi": "Đúng đề: có một lịch hẹn, một việc có giờ cố định, một việc sau khi một việc khác kết thúc", "max": 1, "note_vi": "Task response"},
    {"criterion_vi": "Đúng cách dùng: việc đã hẹn bằng be + V-ing / be going to; giờ cố định bằng hiện tại đơn; vế when bằng hiện tại đơn", "max": 2, "note_vi": "Grammatical range"},
    {"criterion_vi": "Dạng đúng: am / is / are + V-ing, ngôi thứ ba thêm -s, không có will sau when", "max": 2, "note_vi": "Grammatical accuracy"},
]


def reshape(sessions: list[dict], exercise_ids: list[str], card_of: dict[str, int]) -> list[dict]:
    """Sitting 1 teaches cards 1-3 (appointments, present evidence, the present simple for the future) with five
    verbs; sitting 2 cards 4-5 (time clauses, We aren't / We're not) with five nouns; the production work is a third
    sitting without a lecture."""
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
    s1["title_vi"] = "Buổi 1 · việc đã hẹn, dấu hiệu trước mắt, lịch trình"
    s2["title_vi"] = "Buổi 2 · vế sau when, as soon as; We aren't, We're not"
    s1["can_do_vi"] = "Sau buổi này bạn nói được việc đã hẹn bằng be + V-ing, dự đoán từ dấu hiệu trước mắt bằng be going to, và dùng hiện tại đơn cho lịch trình, câu hỏi thông tin."
    s2["can_do_vi"] = "Sau buổi này bạn chia đúng hiện tại đơn sau when, as soon as, until khi nói về tương lai, dùng được cả We aren't lẫn We're not, và trả lời câu hỏi về cuối tuần."
    s3 = {
        "title_vi": "Buổi 3 · vận dụng: xếp câu, gõ, nghe chép, viết",
        "can_do_vi": "Sau buổi này bạn tự xếp và gõ đúng câu về lịch hẹn, lịch trình, câu có when; nghe chép được câu có be + V-ing và hiện tại đơn chỉ tương lai; và viết về kế hoạch tuần sau.",
        "use_vi": s1["use_vi"],
        "vocab": [],
        "check": moved,
    }
    assert set(s1["check"] + s2["check"] + moved) <= set(exercise_ids)
    return [s1, s2, s3] + rest

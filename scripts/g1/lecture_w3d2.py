"""Week 3 · Day 2 (build day 32): only will — offers, requests, and the question that sounds like an order.
Two lectures written by hand (lesson_audio.build_authored_lecture) and the day's sittings reshaped around them.
Same format as lecture_w3d1.py.

Sources: session 5 of the course, stage 2 (docs/WEEK3_PLAN.md, Day 2): offers take will ("I'll get the door for
you", "I'll see you out", "I will buy you dinner"); requests take Will you ("Will you get me some coffee?"); the same
request with be going to or be + V-ing becomes a rhetorical question (mother and son: "Will you help me clean the
house?" / "Are you going to help me now?"; the teacher asking the class to be quiet); stage 5, exercise A items 3,
5, 7; stage 6, items 10 and 11 and the four question words Shall, Should, Can, Will.
Corrections made before use (docs/WEEK3_PLAN.md, last section): Are you going to…? is neutral when it asks about a
plan ("Are you going to be at the party on Saturday?"; the book's item 12 reads "Will you go to Jason's party next Saturday?"); it sounds pushy only as a request or invitation.
Offers never take Will I (Shall I, Can I, Do you want me to). Will we does not make a suggestion (Shall we, Should
we, Let's, Why don't we). "I would certainly see that play" is not used. The romantic "Will you leave me now?" pair is
left out; the mother-and-son pair carries the same contrast.

Pronunciations: Oxford Learner's Dictionaries, British English, read 2026-11-26. A word without a checked
entry has none.
"""

PRON = {
    "arrange": "/əˈreɪndʒ/",
    "cancel": "/ˈkænsl/",
    "remind": "/rɪˈmaɪnd/",
    "deliver": "/dɪˈlɪvə(r)/",
    "sign": "/saɪn/",
    "schedule": "/ˈʃedjuːl/",
    "document": "/ˈdɒkjumənt/",
    "request": "/rɪˈkwest/",
    "contract": "/ˈkɒntrækt/",
    "agenda": "/əˈdʒendə/",
}

NOTES = {
    "arrange": "arrange a meeting: sắp xếp một cuộc họp. Danh từ: arrangement.",
    "cancel": "cancel a meeting, cancel an order. Trái nghĩa: confirm (xác nhận).",
    "remind": "remind someone to do something: nhắc ai làm gì. Khác remember (tự nhớ).",
    "deliver": "deliver an order, deliver a letter. Danh từ: delivery.",
    "sign": "Chữ g không đọc: /saɪn/. Danh từ chữ ký: signature.",
    "schedule": "Kiểu Anh đọc /ˈʃedjuːl/, kiểu Mỹ đọc /ˈskedʒuːl/. on schedule: đúng tiến độ.",
    "document": "Trọng âm ở âm tiết đầu: DOC-u-ment.",
    "request": "make a request: đưa ra yêu cầu. Cũng là động từ: request something.",
    "contract": "sign a contract: ký hợp đồng. Danh từ nhấn âm đầu: CON-tract.",
    "agenda": "Danh sách việc cần bàn trong một cuộc họp: the first item on the agenda.",
}

S1_WORDS = ["arrange", "cancel", "remind", "deliver", "sign"]
S2_WORDS = ["schedule", "document", "request", "contract", "agenda"]

OFFERS = [
    {"key": "o1", "icon": "key", "head": "Mở cửa giúp", "en": "I'll get the door for you.", "vi": "Nói ngay lúc thấy người cần giúp."},
    {"key": "o2", "icon": "house", "head": "Tiễn khách", "en": "I'll see you out.", "vi": "Lời mời rất lịch sự."},
    {"key": "o3", "icon": "steak", "head": "Mời bữa tối", "en": "I'll buy you dinner.", "vi": "Tự nguyện làm điều tốt cho người kia."},
]

ASK_FIRST = [
    {"key": "s1", "head": "Shall I · kiểu Anh", "en": "Shall I carry some of those bags for you?", "vi": "Hỏi trước khi giúp."},
    {"key": "s2", "head": "Can I · phổ biến", "en": "Can I help you with that?", "vi": "Dùng ở mọi nơi."},
    {"key": "s3", "head": "Do you want me to", "en": "Do you want me to send it again?", "vi": "Thân mật, rất hay gặp."},
]

REQUEST = [
    {"key": "r1", "who": "A", "tag": "Nhờ · Will you", "en": "Will you get me some coffee, please?", "vi": "Bạn lấy giúp mình ít cà phê nhé?"},
    {"key": "r2", "who": "B", "tag": "Nhận lời", "en": "Sure.", "vi": "Được chứ."},
    {"key": "r3", "who": "A", "tag": "Lịch sự hơn · Could you", "en": "Could you also send me the document?", "vi": "Bạn gửi giúp mình tài liệu nữa được không?"},
    {"key": "r4", "who": "B", "tag": "Nhận lời", "en": "Of course.", "vi": "Tất nhiên rồi."},
]

HOUSE = [
    {"key": "h1", "icon": "house", "head": "Nhờ", "en": "Will you help me clean the house?", "vi": "Con đáp: Yes, I will."},
    {"key": "h2", "icon": "angry", "head": "Ra lệnh ngầm", "en": "Are you going to help me now?", "vi": "Con lặng lẽ dọn, không cần đáp."},
    {"key": "h3", "icon": "board", "head": "Giáo viên hỏi lớp", "en": "Are you going to be quiet now?", "vi": "Đừng đáp Yes!"},
    {"key": "h4", "icon": "calendar", "head": "Hỏi kế hoạch", "en": "Are you going to be at the party on Saturday?", "vi": "Câu hỏi thật, không có ý ép."},
]

FOUR_ROLES = [
    {"key": "q1", "head": "Shall we · rủ cùng làm", "en": "Shall we start the meeting?", "vi": "Giống Let's, ở dạng câu hỏi."},
    {"key": "q2", "head": "Should we · có nên không", "en": "Should we invite Tom?", "vi": "Gợi ý nhẹ nhàng, hỏi ý kiến."},
    {"key": "q3", "head": "Can I · xin phép", "en": "Can I leave early today?", "vi": "Hỏi người có quyền quyết định."},
    {"key": "q4", "head": "Will you · nhờ", "en": "Will you close the window?", "vi": "Nhờ người nghe làm một việc."},
]

TONY = [
    {"key": "t1", "who": "A", "tag": "Rủ · Shall we", "en": "Shall we invite Tony and Tim round tonight?", "vi": "Tối nay mình mời Tony với Tim qua chơi nhé?"},
    {"key": "t2", "who": "B", "tag": "Đồng ý", "en": "Good idea!", "vi": "Ý hay đấy!"},
    {"key": "t3", "who": "A", "tag": "Hỏi kế hoạch · going to", "en": "Are we going to invite Tony and Tim round tonight?", "vi": "Tối nay mình có mời Tony với Tim không?"},
]

SOUNDS = [
    {"key": "n1", "head": "I'll · /aɪl/", "en": "I'll call you back.", "vi": "Một âm tiết, đọc liền."},
    {"key": "n2", "head": "won't · /wəʊnt/", "en": "I won't be late.", "vi": "Nguyên âm đôi, môi tròn dần."},
    {"key": "n3", "head": "want · /wɒnt/", "en": "I want to be early.", "vi": "Nguyên âm ngắn. Đọc nhầm là đổi nghĩa."},
]

TRAPS = [
    {"key": "e1", "wrong": "Will I carry your bags?", "right": "Shall I carry your bags?", "why": "Đề nghị giúp dạng câu hỏi: Shall I hoặc Can I."},
    {"key": "e2", "wrong": "I'm going to do the washing-up, if you like.", "right": "I'll do the washing-up, if you like.", "why": "Đề nghị giúp: will."},
    {"key": "e3", "wrong": "Will we start the meeting?", "right": "Shall we start the meeting?", "why": "Rủ cùng làm: Shall we, hoặc Let's."},
    {"key": "e4", "wrong": "Are you going to send me the file?", "right": "Could you send me the file?", "why": "Muốn nhờ: Will you, Can you, Could you."},
]

ANSWER = [
    {"key": "p1", "role": "Trả lời thẳng", "tense": "hiện tại đơn", "en": "Yes, I do. It makes me feel useful.", "vi": "Có. Việc đó làm tôi thấy mình có ích."},
    {"key": "p2", "role": "Ví dụ · đề nghị", "tense": "I'll", "en": "If a colleague looks busy, I often say, I'll handle that for you.", "vi": "Thấy đồng nghiệp bận, tôi hay nói: để tôi lo việc đó."},
    {"key": "p3", "role": "Nhờ lại", "tense": "Could you", "en": "When I need help myself, I ask, Could you give me a hand?", "vi": "Khi tôi cần giúp, tôi hỏi: bạn giúp tôi một tay được không?"},
    {"key": "p4", "role": "Dự đoán", "tense": "will", "en": "I think people will help you more if you help them first.", "vi": "Tôi nghĩ mình giúp người trước thì người ta sẽ giúp lại nhiều hơn."},
]

SITTING_1 = [
    {"kind": "title", "hook": "Đồng nghiệp ôm chồng tài liệu, không mở được cửa. Bạn nói gì?", "lines": [
        {"say": "Đồng nghiệp ôm một chồng tài liệu và không mở được cửa. Bạn muốn giúp. Bạn nói bằng will, hay bằng going to?", "show": "hook"},
        {"say": "Buổi này học hai việc chỉ dùng will: đề nghị giúp và nhờ vả. Rồi một câu hỏi với going to trông như lời nhờ nhưng thật ra là ra lệnh."},
    ]},
    {"kind": "scene", "visual": "picture_cards", "eyebrow": "Thí nghiệm", "title": "Đề nghị giúp: chỉ dùng will",
     "data": {"rows": OFFERS, "rule": "Tự nguyện làm giúp ai: I'll + động từ. Không dùng going to hay đuôi ing."}, "lines": [
        {"say": "Bạn bước tới giữ cửa, rồi nói.", "show": "o1"},
        {"en": "I'll get the door for you.", "vi": "Để tôi mở cửa cho bạn.", "gap": True},
        {"say": "Khách ra về, bạn đưa họ ra tận cửa.", "show": "o2"},
        {"en": "I'll see you out.", "vi": "Để tôi tiễn bạn ra cửa.", "gap": True},
        {"say": "Bạn muốn cảm ơn ai đó bằng một bữa tối.", "show": "o3"},
        {"en": "I'll buy you dinner.", "vi": "Để tôi mời bạn bữa tối.", "gap": True},
        {"say": "Thử đổi sang going to: nghe như bạn đang báo một kế hoạch đã định, không còn là lời mời giúp nữa. Người bản ngữ không nói như vậy."},
        {"say": "Tự nguyện làm giúp ai thì nói will cộng động từ, thường rút gọn như trên bảng. Không dùng going to, cũng không dùng đuôi ing.", "show": "rule"},
    ]},
    {"kind": "scene", "visual": "ref_table", "eyebrow": "Hỏi trước khi giúp", "title": "Shall I, Can I: không dùng Will I",
     "data": {"rows": ASK_FIRST, "rule": "Hỏi trước khi giúp: Shall I, Can I, hoặc Do you want me to. Không nói Will I."}, "lines": [
        {"say": "Có khi bạn muốn hỏi trước, xem người kia có cần giúp không. Người Anh hay mở đầu bằng shall.", "show": "s1"},
        {"en": "Shall I carry some of those bags for you?", "vi": "Tôi xách giúp bạn mấy cái túi nhé?", "gap": True},
        {"say": "Cách dùng được ở mọi nơi: can.", "show": "s2"},
        {"en": "Can I help you with that?", "vi": "Tôi giúp bạn việc đó nhé?", "gap": True},
        {"say": "Cách thân mật, rất hay gặp trong hội thoại.", "show": "s3"},
        {"en": "Do you want me to send it again?", "vi": "Bạn có muốn tôi gửi lại không?", "gap": True},
        {"say": "Một lỗi hay gặp: mở đầu lời đề nghị bằng will cộng với tôi. Câu đó sai. Hỏi trước khi giúp thì dùng shall, can, hoặc câu hỏi thân mật ở dòng cuối.", "show": "rule"},
    ]},
    {"kind": "scene", "visual": "chat_dialogue", "eyebrow": "Nhờ vả", "title": "Will you…? Could you…?",
     "data": {"names": {"A": "Bạn", "B": "Đồng nghiệp"}, "turns": REQUEST, "rule": "Nhờ người nghe làm gì: Will you + động từ. Lịch sự hơn: Would you, Could you."}, "lines": [
        {"say": "Giờ đổi vai: bạn đang bận, cần nhờ người khác. Lời nhờ mở đầu bằng will you.", "show": "r1"},
        {"en": "Will you get me some coffee, please?", "vi": "Bạn lấy giúp mình ít cà phê nhé?", "gap": True},
        {"say": "Đồng nghiệp nhận lời.", "show": "r2"},
        {"en": "Sure.", "vi": "Được chứ.", "gap": True, "recap": False},
        {"say": "Với việc khó hơn, hoặc người lạ, dùng could you, hoặc would you, cho lịch sự hơn.", "show": "r3"},
        {"en": "Could you also send me the document?", "vi": "Bạn gửi giúp mình tài liệu nữa được không?", "gap": True},
        {"say": "Và người kia đáp.", "show": "r4"},
        {"en": "Of course.", "vi": "Tất nhiên rồi.", "gap": True, "recap": False},
        {"say": "Nhờ người nghe làm gì thì nói will you cộng động từ. Muốn lịch sự hơn, dùng would you hoặc could you. Thêm please thì câu nhờ mềm hơn.", "show": "rule"},
    ]},
    {"kind": "scene", "visual": "picture_cards", "eyebrow": "Câu hỏi tu từ", "title": "Nhờ hay ra lệnh?",
     "data": {"rows": HOUSE, "rule": "Dùng going to hay đuôi ing để nhờ thì câu thành câu hỏi tu từ, nghe như ra lệnh. Hỏi kế hoạch thì vẫn bình thường."}, "lines": [
        {"say": "Cuối tuần, mẹ muốn con dọn nhà cùng. Nếu mẹ hỏi bằng will you, đó là lời nhờ. Con đáp: vâng, con sẽ giúp.", "show": "h1"},
        {"en": "Will you help me clean the house?", "vi": "Con dọn nhà giúp mẹ nhé?", "gap": True},
        {"say": "Nhưng con cứ ngồi chơi game. Mẹ hỏi lại, lần này bằng going to. Câu này không chờ câu trả lời: con nên lặng lẽ đứng dậy dọn ngay.", "show": "h2"},
        {"en": "Are you going to help me now?", "vi": "Thế bây giờ có định giúp mẹ không đây?", "gap": True},
        {"say": "Đây gọi là câu hỏi tu từ: hỏi mà không cần trả lời. Giống giáo viên hỏi cả lớp có trật tự được không. Bạn nào đáp có là chuẩn bị viết bản kiểm điểm.", "show": "h3"},
        {"en": "Are you going to be quiet now?", "vi": "Thế bây giờ các em có trật tự được không?", "gap": True, "recap": False},
        {"say": "Nhưng đừng sợ going to trong câu hỏi. Khi bạn chỉ muốn biết lịch của người kia, đây là một câu hỏi thật, rất bình thường.", "show": "h4"},
        {"en": "Are you going to be at the party on Saturday?", "vi": "Thứ Bảy bạn có đến bữa tiệc không?", "gap": True},
        {"say": "Dùng going to hay đuôi ing để nhờ thì câu thành câu hỏi tu từ, nghe như ra lệnh. Muốn nhờ, hãy dùng will you. Còn hỏi kế hoạch thì going to vẫn bình thường.", "show": "rule"},
    ]},
    {"kind": "word", "headword": "arrange", "lines": [{"say": "Năm động từ của buổi này là những việc hay được nhờ ở chỗ làm. Từ thứ nhất: sắp xếp, thu xếp."}]},
    {"kind": "word", "headword": "cancel", "lines": [{"say": "Từ thứ hai: hủy. Câu ví dụ là một lời đề nghị bằng shall."}]},
    {"kind": "word", "headword": "remind", "lines": [{"say": "Từ thứ ba: nhắc ai làm gì. Câu ví dụ là một lời nhờ bằng will you."}]},
    {"kind": "word", "headword": "deliver", "lines": [{"say": "Từ thứ tư: giao hàng, giao thư."}]},
    {"kind": "word", "headword": "sign", "lines": [{"say": "Từ cuối: ký tên. Chữ gờ ở giữa không đọc. Câu ví dụ là lời nhờ lịch sự bằng could you."}]},
    {"kind": "recap", "lines": [
        {"say": "Đồng nghiệp không mở được cửa: bạn dùng will, vì đề nghị giúp chỉ dùng will. Giờ nói lại các câu của buổi này. Nghe một câu, rồi nói to trong quãng nghỉ.", "show": "title"},
    ]},
    {"kind": "end", "next": "Tiếp theo: học thẻ và từ của buổi này, rồi làm bài.", "lines": [
        {"say": "Hết buổi một. Bạn học các thẻ và từ trong app, rồi làm bài. Buổi hai học cách rủ, gợi ý, xin phép cho đúng vai, rồi cách đọc will cho rõ.", "show": "title"},
    ]},
]

SITTING_2 = [
    {"kind": "title", "hook": "Cả nhóm đã đến đủ. Bạn rủ mọi người bắt đầu họp bằng câu nào?", "lines": [
        {"say": "Cả nhóm đã đến đủ. Bạn muốn rủ mọi người bắt đầu họp. Mở đầu bằng will we, hay bằng shall we?", "show": "hook"},
        {"say": "Buổi này học bốn câu hỏi có bốn vai khác nhau, một câu của bài tập có hai cách hiểu, rồi cách đọc will cho rõ."},
    ]},
    {"kind": "scene", "visual": "ref_table", "eyebrow": "Thí nghiệm", "title": "Bốn câu hỏi, bốn vai",
     "data": {"rows": FOUR_ROLES, "rule": "Rủ: Shall we. Có nên không: Should we. Xin phép: Can I. Nhờ: Will you. Không dùng Will we để rủ."}, "lines": [
        {"say": "Vai thứ nhất: rủ cùng làm. Người Anh dùng shall we, nghĩa giống như nào chúng ta cùng làm.", "show": "q1"},
        {"en": "Shall we start the meeting?", "vi": "Chúng ta bắt đầu họp nhé?", "gap": True},
        {"say": "Vai thứ hai: gợi ý nhẹ nhàng, hỏi xem có nên làm không.", "show": "q2"},
        {"en": "Should we invite Tom?", "vi": "Có nên mời Tom không?", "gap": True},
        {"say": "Vai thứ ba: xin phép người có quyền. Người hỏi tự đặt mình thấp hơn một chút.", "show": "q3"},
        {"en": "Can I leave early today?", "vi": "Hôm nay tôi xin về sớm được không?", "gap": True},
        {"say": "Vai thứ tư: nhờ người nghe, như ở buổi trước.", "show": "q4"},
        {"en": "Will you close the window?", "vi": "Bạn đóng giúp cửa sổ nhé?", "gap": True},
        {"say": "Còn will we thì sao? Câu đó hỏi một việc ở tương lai, ví dụ chúng ta có xong kịp không. Nó không dùng để rủ. Câu hỏi đầu buổi nên mở đầu bằng shall we.", "show": "rule"},
    ]},
    {"kind": "scene", "visual": "chat_dialogue", "eyebrow": "Một câu, hai cách hiểu", "title": "Mời Tony và Tim tối nay",
     "data": {"names": {"A": "Bạn", "B": "Bạn cùng nhà"}, "turns": TONY, "rule": "Rủ: Shall we. Hỏi kế hoạch chung: Are we going to cũng đúng, nhưng nói giọng gắt thì nghe như ép."}, "lines": [
        {"say": "Bạn muốn rủ bạn cùng nhà mời hai người bạn qua chơi tối nay. Câu rủ tự nhiên nhất.", "show": "t1"},
        {"en": "Shall we invite Tony and Tim round tonight?", "vi": "Tối nay mình mời Tony với Tim qua chơi nhé?", "gap": True},
        {"say": "Người kia đồng ý.", "show": "t2"},
        {"en": "Good idea!", "vi": "Ý hay đấy!", "gap": True, "recap": False},
        {"say": "Còn câu này thì sao? Nếu hai người đã bàn chuyện tối nay rồi, bạn chỉ hỏi kế hoạch chung, câu này đúng. Bài thi chấm giữ nguyên.", "show": "t3"},
        {"en": "Are we going to invite Tony and Tim round tonight?", "vi": "Tối nay mình có mời Tony với Tim không?", "gap": True, "recap": False},
        {"say": "Nhưng nếu người kia còn lưỡng lự, mà bạn hỏi câu này với giọng gắt, câu thành câu hỏi tu từ: có mời hay không đây. Muốn rủ thì dùng shall we. Hỏi kế hoạch chung thì going to cũng đúng.", "show": "rule"},
    ]},
    {"kind": "scene", "visual": "ref_table", "eyebrow": "Phát âm", "title": "I'll, won't, want",
     "data": {"rows": SOUNDS, "rule": "I'll đọc liền một âm tiết. won't có nguyên âm đôi; want có nguyên âm ngắn."}, "lines": [
        {"say": "Dạng rút gọn của will đọc liền thành một âm tiết: ai, rồi lướt sang âm lờ cuối.", "show": "n1"},
        {"en": "I'll call you back.", "vi": "Tôi sẽ gọi lại cho bạn.", "gap": True},
        {"say": "Dạng phủ định rút gọn có một nguyên âm đôi: miệng mở rồi tròn môi dần, giống trong từ go.", "show": "n2"},
        {"en": "I won't be late.", "vi": "Tôi sẽ không đến muộn.", "gap": True},
        {"say": "Từ want chỉ có một nguyên âm ngắn, giống trong từ hot. Đọc nhầm hai từ này thì không muốn thành muốn.", "show": "n3"},
        {"en": "I want to be early.", "vi": "Tôi muốn đến sớm.", "gap": True},
        {"say": "Dạng rút gọn của will đọc liền một âm tiết. Dạng phủ định có nguyên âm đôi; want có nguyên âm ngắn.", "show": "rule"},
    ]},
    {"kind": "scene", "visual": "fix_pairs", "eyebrow": "Lỗi thường gặp", "title": "Bốn lỗi, bốn cách sửa",
     "data": {"rows": TRAPS, "rule": "Đề nghị: I'll, Shall I, Can I. Nhờ: Will you, Could you. Rủ: Shall we."}, "lines": [
        {"say": "Bốn lỗi hay gặp nhất của hôm nay. Lỗi một: hỏi trước khi giúp bằng will.", "show": "e1"},
        {"en": "Shall I carry your bags?", "vi": "Tôi xách túi giúp bạn nhé?", "gap": True},
        {"say": "Lỗi hai: đề nghị giúp bằng going to.", "show": "e2"},
        {"en": "I'll do the washing-up, if you like.", "vi": "Để tôi rửa bát nhé, nếu bạn muốn.", "gap": True},
        {"say": "Lỗi ba: rủ cùng làm bằng will we.", "show": "e3"},
        {"en": "Shall we start the meeting?", "vi": "Chúng ta bắt đầu họp nhé?", "gap": True, "recap": False},
        {"say": "Lỗi bốn: muốn nhờ, nhưng hỏi bằng going to.", "show": "e4"},
        {"en": "Could you send me the file?", "vi": "Bạn gửi giúp tôi tệp đó được không?", "gap": True},
        {"say": "Đề nghị giúp: will, shall, can. Nhờ: will you, could you. Rủ: shall we.", "show": "rule"},
    ]},
    {"kind": "word", "headword": "schedule", "lines": [{"say": "Trước câu Speaking, học năm danh từ của một buổi họp. Từ thứ nhất: lịch làm việc. Kiểu Anh và kiểu Mỹ đọc khác nhau ở âm đầu."}]},
    {"kind": "word", "headword": "document", "lines": [{"say": "Từ thứ hai: tài liệu, văn bản. Trọng âm ở âm tiết đầu."}]},
    {"kind": "word", "headword": "request", "lines": [{"say": "Từ thứ ba: yêu cầu, lời nhờ."}]},
    {"kind": "word", "headword": "contract", "lines": [{"say": "Từ thứ tư: hợp đồng. Câu ví dụ là một lời xin phép bằng can."}]},
    {"kind": "word", "headword": "agenda", "lines": [{"say": "Từ cuối: chương trình cuộc họp. Câu ví dụ là một lời rủ bằng shall we."}]},
    {"kind": "scene", "visual": "speaking_answer", "eyebrow": "IELTS Speaking Part 1", "title": "Đề nghị bằng I'll, nhờ bằng Could you",
     "data": {"question": "Do you like helping other people?", "question_vi": "Bạn có thích giúp đỡ người khác không?",
              "short": "Yes.", "parts": ANSWER,
              "rule": "Kể lời đề nghị bằng I'll, lời nhờ bằng Could you; dự đoán bằng will."}, "lines": [
        {"say": "Giám khảo hỏi bạn có thích giúp đỡ người khác không."},
        {"en": "Do you like helping other people?", "show": "q"},
        {"say": "Chỉ đáp một chữ thì quá ngắn.", "show": "short"},
        {"say": "Câu một: trả lời thẳng, kèm một nguyên nhân."},
        {"en": "Yes, I do. It makes me feel useful.", "vi": "Có. Việc đó làm tôi thấy mình có ích.", "gap": True, "show": "p1"},
        {"say": "Câu hai: một ví dụ, kể lại lời đề nghị giúp bằng will."},
        {"en": "If a colleague looks busy, I often say, I'll handle that for you.", "vi": "Thấy đồng nghiệp bận, tôi hay nói: để tôi lo việc đó.", "gap": True, "show": "p2"},
        {"say": "Câu ba: chiều ngược lại, khi bạn nhờ người khác."},
        {"en": "When I need help myself, I ask, Could you give me a hand?", "vi": "Khi tôi cần giúp, tôi hỏi: bạn giúp tôi một tay được không?", "gap": True, "show": "p3"},
        {"say": "Câu bốn: một dự đoán, dùng will."},
        {"en": "I think people will help you more if you help them first.", "vi": "Tôi nghĩ mình giúp người trước thì người ta sẽ giúp lại nhiều hơn.", "gap": True, "show": "p4"},
        {"say": "Kể lời đề nghị bằng will, lời nhờ bằng could you, dự đoán bằng will. Hãy viết lại bốn câu này cho đúng với chính bạn.", "show": "rule"},
    ]},
    {"kind": "recap", "lines": [
        {"say": "Rủ cả nhóm bắt đầu họp: dùng shall we, không dùng will we. Giờ nói lại các câu của buổi này. Nghe một câu, rồi nói to trong quãng nghỉ.", "show": "title"},
    ]},
    {"kind": "end", "next": "Tiếp theo: học thẻ và từ, làm bài, rồi buổi 3 để xếp câu, nghe chép và viết.", "lines": [
        {"say": "Hết phần giảng của ngày hai. Bạn học các thẻ và từ trong app, làm bài, rồi sang buổi ba để xếp câu, nghe chép và viết vài câu giúp một đồng nghiệp đang bận.", "show": "title"},
    ]},
]

RUBRIC = [
    {"criterion_vi": "Đúng đề: có một lời đề nghị, một lời nhờ, một lời rủ", "max": 1, "note_vi": "Task response"},
    {"criterion_vi": "Đúng chức năng: đề nghị bằng I'll / Shall I; nhờ bằng Will you / Could you; rủ bằng Shall we / Let's", "max": 2, "note_vi": "Grammatical range"},
    {"criterion_vi": "Dạng đúng: will / Shall / Could + động từ nguyên thể, không có to", "max": 2, "note_vi": "Grammatical accuracy"},
]


def reshape(sessions: list[dict], exercise_ids: list[str], card_of: dict[str, int]) -> list[dict]:
    """Sitting 1 teaches cards 1-3 (offers, requests, the rhetorical question) with five verbs; sitting 2 cards 4-5
    (Shall we / Should we / Can I / Will you, the sounds of will) with five nouns; the production work is a third
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
    s1["title_vi"] = "Buổi 1 · đề nghị giúp, nhờ vả, câu hỏi tu từ"
    s2["title_vi"] = "Buổi 2 · rủ, gợi ý, xin phép; cách đọc will"
    s1["can_do_vi"] = "Sau buổi này bạn đề nghị giúp bằng I'll, Shall I, Can I, nhờ lịch sự bằng Will you, Could you, và nhận ra câu hỏi Are you going to…? dùng để nhờ thì nghe như ra lệnh."
    s2["can_do_vi"] = "Sau buổi này bạn rủ, gợi ý, xin phép đúng vai bằng Shall we, Should we, Can I, Will you, và đọc rõ I'll, won't, want."
    s3 = {
        "title_vi": "Buổi 3 · vận dụng: xếp câu, gõ, nghe chép, viết",
        "can_do_vi": "Sau buổi này bạn tự xếp và gõ đúng lời đề nghị, lời nhờ, lời rủ, nghe chép được câu có I'll, Will you, Shall we, và viết vài câu giúp một đồng nghiệp đang bận.",
        "use_vi": s1["use_vi"],
        "vocab": [],
        "check": moved,
    }
    assert set(s1["check"] + s2["check"] + moved) <= set(exercise_ids)
    return [s1, s2, s3] + rest

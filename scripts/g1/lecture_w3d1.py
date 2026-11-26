"""Week 3 · Day 1 (build day 31): the future simple. Two lectures written by hand
(lesson_audio.build_authored_lecture) and the day's sittings reshaped around them. Same format as lecture_w2d1.py.

Sources: session 5 of the course, stage 1 (docs/WEEK3_PLAN.md, Day 1): three ways to write the future simple
(will, be going to, be + V-ing), predictions with will or be going to whether near or far ("everything in the
future is a prediction"), will is more formal (academic writing: "Governments will..."), the two school rules to
drop (near/far, "sure in your head": the date story, the mother asking about the extra class), the decision made
while speaking ("OK Mom, I'll turn it off now"); stage 5, exercise A items 1, 4, 6, 8 (the barbecue and the
restaurant read in two contexts) and the pronunciation of restaurant and hundreds of years.
Corrections made before use (docs/WEEK3_PLAN.md, last section): for a decision made while speaking will is
taught as the natural form (be + V-ing also heard; be going to correct but long); "I'm rushing to do some
groceries now" is the present continuous for what is happening now, so it is used as the contrast "now or
future", not as a future form.

Pronunciations: Oxford Learner's Dictionaries, British English, read 2026-11-26. A word without a checked
entry has none.
"""

PRON = {
    "apply": "/əˈplaɪ/",
    "hire": "/ˈhaɪə(r)/",
    "earn": "/ɜːn/",
    "promote": "/prəˈməʊt/",
    "resign": "/rɪˈzaɪn/",
    "career": "/kəˈrɪə(r)/",
    "salary": "/ˈsæləri/",
    "interview": "/ˈɪntəvjuː/",
    "employer": "/ɪmˈplɔɪə(r)/",
    "deadline": "/ˈdedlaɪn/",
}

# a line under each word: how it is used, or what it is easily mixed up with
NOTES = {
    "apply": "apply for a job: xin một công việc; apply to a company: nộp đơn vào một công ty. Danh từ: application.",
    "hire": "hire = tuyển, thuê người làm. Trái nghĩa: fire (đuổi việc).",
    "earn": "earn money: kiếm tiền; earn a living: kiếm sống.",
    "promote": "Hay dùng ở bị động: be promoted (được thăng chức). Danh từ: promotion.",
    "resign": "resign from a job. Chữ g không đọc: /rɪˈzaɪn/.",
    "career": "Trọng âm ở âm tiết thứ hai: ca-REER. Đừng nhầm với carrier (hãng vận chuyển).",
    "salary": "Lương cố định theo tháng hoặc theo năm. Tiền công theo giờ, theo tuần là wage.",
    "interview": "a job interview: buổi phỏng vấn xin việc. Người phỏng vấn: interviewer.",
    "employer": "Người hoặc công ty thuê bạn. Người được thuê: employee.",
    "deadline": "meet a deadline: kịp hạn; miss a deadline: trễ hạn.",
}

S1_WORDS = ["apply", "hire", "earn", "promote", "resign"]
S2_WORDS = ["career", "salary", "interview", "employer", "deadline"]

THREE_WAYS = [
    {"key": "w1", "icon": "phone", "head": "will + V", "en": "I'll start a new job next month.", "vi": "Ngắn, dùng được nhiều nhất."},
    {"key": "w2", "icon": "calendar", "head": "be going to + V", "en": "I'm going to start a new job next month.", "vi": "Cùng nghĩa, dài hơn."},
    {"key": "w3", "icon": "clock", "head": "be + V-ing", "en": "I'm starting a new job next month.", "vi": "Cùng nghĩa, cần mốc tương lai."},
]

PREDICT = [
    {"key": "f1", "icon": "check_bubble", "at": "future", "tense": "Gần · will", "en": "I think you'll get the job.", "vi": "Dự đoán việc tuần sau."},
    {"key": "f2", "icon": "crystal", "at": "future", "tense": "Xa · going to", "en": "The universe is going to continue to expand for billions of years.", "vi": "Dự đoán việc hàng tỷ năm sau."},
    {"key": "f3", "icon": "doc", "at": "future", "tense": "Bài viết · will", "en": "Governments will need to create more jobs.", "vi": "Văn viết học thuật dùng will."},
]

DATE = [
    {"key": "k1", "who": "A", "tag": "Hỏi về tương lai", "en": "Will you ever see him again?", "vi": "Bạn có gặp lại anh ấy nữa không?"},
    {"key": "k2", "who": "B", "tag": "will · dự đoán", "en": "Yes, I will.", "vi": "Có chứ."},
    {"key": "k3", "who": "B", "tag": "đuôi ing · đã hẹn", "mark": "anchor", "en": "Yes, I'm seeing him again next week.", "vi": "Có, tuần sau mình gặp lại."},
]

CLASS = [
    {"key": "m1", "who": "A", "tag": "Mẹ hỏi", "en": "Are you going to your extra class this weekend?", "vi": "Cuối tuần con có đi học thêm không?"},
    {"key": "m2", "who": "B", "tag": "Con đáp chắc nịch", "en": "Yes, I am.", "vi": "Có ạ."},
    {"key": "m3", "who": "B", "tag": "Cuối tuần", "mark": "anchor", "en": "I went to the cinema with my friends.", "vi": "Con đi xem phim với bạn."},
]

MOM = [
    {"key": "j1", "who": "A", "tag": "Mẹ nhắc", "en": "John, please turn off the computer and do your homework.", "vi": "John, tắt máy tính rồi làm bài đi con."},
    {"key": "j2", "who": "B", "tag": "will · tự nhiên nhất", "mark": "anchor", "en": "OK Mom, I'll turn it off now.", "vi": "Vâng, con tắt ngay đây."},
    {"key": "j3", "who": "B", "tag": "đuôi ing · cũng được", "en": "OK Mom, I'm turning it off now.", "vi": "Vâng, con đang tắt đây."},
]

TWO_CONTEXTS = [
    {"key": "d1", "icon": "bulb", "head": "Vừa nảy ra ý", "en": "I know! I'll have a barbecue on my birthday!", "vi": "Ý tưởng đến ngay lúc nói: will."},
    {"key": "d2", "icon": "calendar", "head": "Đã tính sẵn", "en": "I'm going to have a barbecue on my birthday.", "vi": "Kế hoạch có từ trước: going to."},
    {"key": "d3", "icon": "checklist", "head": "Đã bàn, đã đặt bàn", "en": "We've decided we're going to try that new restaurant.", "vi": "Quyết từ trước: going to, hoặc đuôi ing."},
    {"key": "d4", "icon": "discuss", "head": "Vừa bàn xong", "en": "OK, we'll try that new restaurant.", "vi": "Quyết ngay lúc nói: will."},
]

NOW_OR_LATER = [
    {"key": "c1", "icon": "discuss", "at": "now", "tense": "now · đang diễn ra", "en": "I'm meeting a client now, so I can't talk.", "vi": "Việc đang làm lúc nói."},
    {"key": "c2", "icon": "calendar", "at": "future", "tense": "tomorrow · đã hẹn", "en": "I'm meeting a client tomorrow.", "vi": "Một cuộc hẹn ở tương lai."},
]

TRAPS = [
    {"key": "e1", "wrong": "I will to apply for the job.", "right": "I will apply for the job.", "why": "Sau will là động từ nguyên thể, không có to."},
    {"key": "e2", "wrong": "He wills start next week.", "right": "He will start next week.", "why": "will không đổi theo ngôi."},
    {"key": "e3", "wrong": "I going to apply for the job.", "right": "I'm going to apply for the job.", "why": "going to cần am, is, are đứng trước."},
    {"key": "e4", "wrong": "In the future, people are living longer.", "right": "In the future, people will live longer.", "why": "Dự đoán chung: will. Đuôi ing dành cho việc đã hẹn."},
]

ANSWER = [
    {"key": "p1", "role": "Trả lời thẳng", "tense": "will", "en": "No, I don't think I will.", "vi": "Không, tôi nghĩ là không."},
    {"key": "p2", "role": "Việc đã lên lịch", "tense": "be + V-ing", "en": "I'm starting a new job at a bank next month.", "vi": "Tháng sau tôi bắt đầu làm ở một ngân hàng."},
    {"key": "p3", "role": "Dự định", "tense": "will", "en": "In a few years, I think I'll apply for a job abroad.", "vi": "Vài năm nữa, chắc tôi sẽ xin việc ở nước ngoài."},
    {"key": "p4", "role": "Dự đoán chung", "tense": "will", "en": "Most people will have several employers in their career.", "vi": "Phần lớn mọi người sẽ làm cho vài chỗ trong sự nghiệp."},
]

SITTING_1 = [
    {"kind": "title", "hook": "Năm năm nữa bạn sẽ làm nghề gì? Nói bằng will hay going to?", "lines": [
        {"say": "Năm năm nữa bạn sẽ làm nghề gì? Thử trả lời bằng tiếng Anh. Bạn chọn will, hay going to? Và nếu chọn sai thì sao?", "show": "hook"},
        {"say": "Buổi này học ba cách viết thì tương lai đơn, cách dùng cả ba để dự đoán, và hai quy tắc học thuộc mà bạn nên bỏ."},
    ]},
    {"kind": "scene", "visual": "picture_cards", "eyebrow": "Thí nghiệm", "title": "Một câu, ba cách viết",
     "data": {"rows": THREE_WAYS, "rule": "Tương lai đơn có ba cách viết. Nhiều chỗ thay nhau được; vài chỗ chỉ một cách dùng được."}, "lines": [
        {"say": "Bạn kể với bạn bè: tháng sau mình bắt đầu một công việc mới. Cách thứ nhất dùng will.", "show": "w1"},
        {"en": "I'll start a new job next month.", "vi": "Tháng sau tôi bắt đầu công việc mới.", "gap": True},
        {"say": "Cách thứ hai dùng going to.", "show": "w2"},
        {"en": "I'm going to start a new job next month.", "vi": "Tháng sau tôi bắt đầu công việc mới.", "gap": True},
        {"say": "Cách thứ ba dùng am, is hoặc are cộng động từ đuôi ing.", "show": "w3"},
        {"en": "I'm starting a new job next month.", "vi": "Tháng sau tôi bắt đầu công việc mới.", "gap": True},
        {"say": "Ba câu, cùng một nghĩa. Cả ba đều là thì tương lai đơn. Trong nhiều trường hợp chúng thay nhau được; chỉ có vài trường hợp một cách dùng được mà cách kia thì không. Những trường hợp đó sẽ học ở các ngày sau.", "show": "rule"},
    ]},
    {"kind": "scene", "visual": "sentence_forms", "eyebrow": "Công thức", "title": "Ba dạng câu với will",
     "data": {"rows": [
                  {"key": "aff", "label": "Khẳng định", "parts": ["I", "'ll call", "you tomorrow."], "hi": [1], "vi": "Mai tôi sẽ gọi cho bạn."},
                  {"key": "neg", "label": "Phủ định", "parts": ["I", "won't be", "late."], "hi": [1], "vi": "Tôi sẽ không đến muộn."},
                  {"key": "qst", "label": "Câu hỏi", "parts": ["Will", "you be", "at the meeting?"], "hi": [0, 1], "vi": "Bạn có dự cuộc họp không?"},
              ],
              "persons": [{"who": "I · you · we · they", "verb": "will call"}, {"who": "he · she · it", "verb": "will call"}],
              "persons_plain": True,
              "spelling_title": "Dạng rút gọn khi nói",
              "spelling": [["I will", "I'll"], ["you will", "you'll"], ["will not", "won't"], ["I am going to", "I'm going to"]],
              "short": ["Yes, I will.", "No, I won't."],
              "rule": "will + động từ nguyên thể, mọi ngôi như nhau. Phủ định: won't. Câu hỏi: đưa will lên đầu."}, "lines": [
        {"say": "Bây giờ là công thức của will. Will không đổi theo ngôi: tôi, bạn, anh ấy, cô ấy đều là will. Sau will là động từ nguyên thể.", "show": "persons"},
        {"en": "I'll call you tomorrow.", "vi": "Mai tôi sẽ gọi cho bạn.", "gap": True, "show": "aff"},
        {"say": "Khi nói, will thường được rút gọn, như trên bảng. Phủ định là won't.", "show": "spelling"},
        {"en": "I won't be late.", "vi": "Tôi sẽ không đến muộn.", "gap": True, "show": "neg"},
        {"say": "Câu hỏi: đưa will lên đầu câu. Trả lời ngắn cũng dùng lại will hoặc won't.", "show": "qst"},
        {"en": "Will you be at the meeting?", "vi": "Bạn có dự cuộc họp không?", "gap": True},
        {"en": "Yes, I will.", "vi": "Có.", "gap": True, "show": "short", "recap": False},
        {"say": "Với going to thì am, is, are phải đổi theo ngôi: tôi dùng am, anh ấy dùng is, họ dùng are. Won't và want đọc khác nhau; nghe kỹ câu sau."},
        {"en": "I won't stay. I want to go home.", "vi": "Tôi sẽ không ở lại. Tôi muốn về nhà.", "gap": True, "recap": False},
        {"say": "Tóm lại: will cộng động từ nguyên thể, mọi ngôi như nhau. Phủ định: won't. Câu hỏi: đưa will lên đầu câu.", "show": "rule"},
    ]},
    {"kind": "scene", "visual": "tense_timeline", "eyebrow": "Bản chất", "title": "Dự đoán: gần hay xa đều được",
     "data": {"question": "will · going to", "question_vi": "ba dự đoán", "question_label": "Cùng là dự đoán",
              "answers": PREDICT, "rule": "Dự đoán thì will và going to đều đúng, gần hay xa cũng vậy. will trang trọng hơn: khi viết, dùng will."}, "lines": [
        {"say": "Đoán về tương lai, người ta dùng will hoặc going to. Thử ba dự đoán.", "show": "q"},
        {"say": "Trên trục này, vạch giữa là bây giờ, bên phải là tương lai.", "show": "axis"},
        {"say": "Dự đoán thứ nhất, cho việc tuần sau: bạn của bạn đi phỏng vấn, và bạn đoán cô ấy sẽ được nhận.", "show": "f1"},
        {"en": "I think you'll get the job.", "vi": "Tôi nghĩ bạn sẽ được nhận việc.", "gap": True},
        {"say": "Dự đoán thứ hai, cho hàng tỷ năm sau. Có bạn sửa going to thành will, vì nghĩ việc xa như vậy thì phải dùng will. Không cần sửa: câu này đúng.", "show": "f2"},
        {"en": "The universe is going to continue to expand for billions of years.", "vi": "Vũ trụ sẽ tiếp tục giãn nở hàng tỷ năm nữa.", "gap": True},
        {"say": "Hai cách khác nhau ở văn phong. Will trang trọng hơn going to, nên trong bài viết học thuật, người ta viết will.", "show": "f3"},
        {"en": "Governments will need to create more jobs.", "vi": "Các chính phủ sẽ phải tạo thêm việc làm.", "gap": True},
        {"say": "Khi dự đoán, will và going to đều đúng, việc ở gần hay ở xa cũng vậy. Will trang trọng hơn, nên khi viết thì dùng will.", "show": "rule"},
    ]},
    {"kind": "scene", "visual": "chat_dialogue", "eyebrow": "Quy tắc cần bỏ", "title": "Gần hay xa: ai quyết định?",
     "data": {"names": {"A": "Bạn thân", "B": "Bạn"}, "turns": DATE, "rule": "Gần hay xa là cảm nhận của từng người. Thì không phụ thuộc vào đó."}, "lines": [
        {"say": "Ở trường, nhiều bạn được dạy: tương lai gần dùng cách này, tương lai xa dùng cách kia. Thử một tình huống. Bạn vừa đi hẹn hò về, và bạn thân hỏi.", "show": "k1"},
        {"en": "Will you ever see him again?", "vi": "Bạn có gặp lại anh ấy nữa không?", "gap": True},
        {"say": "Bạn có thể đáp bằng will.", "show": "k2"},
        {"en": "Yes, I will.", "vi": "Có chứ.", "gap": True, "recap": False},
        {"say": "Hoặc nói luôn là đã hẹn tuần sau.", "show": "k3"},
        {"en": "Yes, I'm seeing him again next week.", "vi": "Có, tuần sau mình gặp lại.", "gap": True},
        {"say": "Tuần sau là gần hay xa? Với người đang mong gặp lại, một tuần dài lắm. Với người khác, một tuần chẳng là bao. Gần hay xa là cảm nhận của từng người, nên thì không phụ thuộc vào đó.", "show": "rule"},
    ]},
    {"kind": "scene", "visual": "chat_dialogue", "eyebrow": "Quy tắc cần bỏ", "title": "Chắc chắn trong đầu: ai nhìn thấy?",
     "data": {"names": {"A": "Mẹ", "B": "Bạn"}, "turns": CLASS, "rule": "Không ai nhìn được vào đầu người khác. Mọi điều ở tương lai đều là dự đoán."}, "lines": [
        {"say": "Quy tắc thứ hai: chắc chắn trong đầu thì dùng going to, không chắc thì dùng will. Thử tiếp. Mẹ hỏi cuối tuần có đi học thêm không.", "show": "m1"},
        {"en": "Are you going to your extra class this weekend?", "vi": "Cuối tuần con có đi học thêm không?", "gap": True, "recap": False},
        {"say": "Bạn đáp rất chắc.", "show": "m2"},
        {"en": "Yes, I am.", "vi": "Có ạ.", "gap": True, "recap": False},
        {"say": "Rồi đến cuối tuần, bạn trốn học đi xem phim với bạn bè.", "show": "m3"},
        {"en": "I went to the cinema with my friends.", "vi": "Con đi xem phim với bạn.", "gap": True, "recap": False},
        {"say": "Lúc nói, người nghe làm sao biết trong đầu bạn chắc đến đâu? Không ai nhìn được vào đầu người khác. Vì vậy, mọi điều ở tương lai đều là dự đoán. Nếu thầy cô trên lớp vẫn chấm theo quy tắc cũ, khi thi trên trường bạn cứ làm theo; còn khi nói thật và khi thi IELTS, hãy chọn theo nghĩa.", "show": "rule"},
    ]},
    {"kind": "word", "headword": "apply", "lines": [{"say": "Năm động từ của buổi này đều về chuyện đi làm, và câu ví dụ nào cũng ở tương lai. Từ thứ nhất: nộp đơn xin việc."}]},
    {"kind": "word", "headword": "hire", "lines": [{"say": "Từ thứ hai: công ty tuyển người. Câu ví dụ dùng will."}]},
    {"kind": "word", "headword": "earn", "lines": [{"say": "Từ thứ ba: kiếm tiền. Âm giữa kéo dài, giống trong từ bird."}]},
    {"kind": "word", "headword": "promote", "lines": [{"say": "Từ thứ tư: thăng chức. Câu ví dụ là một dự đoán với will."}]},
    {"kind": "word", "headword": "resign", "lines": [{"say": "Từ cuối: xin nghỉ việc. Chữ cái gờ trong từ này không đọc. Câu ví dụ dùng đuôi ing, vì việc đã định sẵn."}]},
    {"kind": "recap", "lines": [
        {"say": "Năm năm nữa bạn làm nghề gì: will hay going to đều được, vì đó là một dự đoán. Giờ nói lại các câu của buổi này. Nghe một câu, rồi nói to trong quãng nghỉ.", "show": "title"},
    ]},
    {"kind": "end", "next": "Tiếp theo: học thẻ và từ của buổi này, rồi làm bài.", "lines": [
        {"say": "Hết buổi một. Bạn học các thẻ và từ trong app, rồi làm bài. Buổi hai nói về quyết định ngay lúc nói, và khi nào đuôi ing chỉ tương lai.", "show": "title"},
    ]},
]

SITTING_2 = [
    {"kind": "title", "hook": "Mẹ bảo tắt máy tính đi học bài. Bạn đáp «OK Mom, …» thế nào?", "lines": [
        {"say": "Mẹ bảo bạn tắt máy tính đi học bài. Bạn đồng ý, và tắt ngay. Bạn sẽ nói câu đó bằng tiếng Anh thế nào?", "show": "hook"},
        {"say": "Buổi này học quyết định ngay lúc nói, quyết định đã có từ trước, và cách nhận ra đuôi ing đang nói về bây giờ hay tương lai."},
    ]},
    {"kind": "scene", "visual": "chat_dialogue", "eyebrow": "Thí nghiệm", "title": "Quyết định ngay lúc nói",
     "data": {"names": {"A": "Mẹ", "B": "John"}, "turns": MOM, "rule": "Quyết định ngay lúc nói: will tự nhiên nhất. Đuôi ing cũng được; going to đúng nhưng dài."}, "lines": [
        {"say": "Mẹ của John nhắc.", "show": "j1"},
        {"en": "John, please turn off the computer and do your homework.", "vi": "John, tắt máy tính rồi làm bài đi con.", "gap": True, "recap": False},
        {"say": "John quyết định ngay lúc đó, và đáp bằng will. Đây là cách tự nhiên nhất.", "show": "j2"},
        {"en": "OK Mom, I'll turn it off now.", "vi": "Vâng, con tắt ngay đây.", "gap": True},
        {"say": "Người bản ngữ cũng hay đáp bằng đuôi ing, vì việc tắt máy gần như đang diễn ra.", "show": "j3"},
        {"en": "OK Mom, I'm turning it off now.", "vi": "Vâng, con đang tắt đây.", "gap": True},
        {"say": "Đáp bằng going to thì không sai ngữ pháp, chỉ dài nên ít ai nói. Còn hiện tại đơn thì sai: hiện tại đơn không dùng cho một lời hứa hay một quyết định."},
        {"say": "Quyết định ngay lúc nói: will là tự nhiên nhất. Đuôi ing cũng được. Going to đúng, nhưng dài.", "show": "rule"},
    ]},
    {"kind": "scene", "visual": "picture_cards", "eyebrow": "Một câu, hai bối cảnh", "title": "Vừa nảy ra, hay đã tính từ trước?",
     "data": {"rows": TWO_CONTEXTS, "rule": "Vừa quyết ngay lúc nói: will. Đã quyết từ trước, đã đặt chỗ: going to hoặc đuôi ing. Hai cách đều đúng ngữ pháp."}, "lines": [
        {"say": "Một người reo lên: biết rồi! Nếu ý tưởng vừa nảy ra ngay lúc nói, will là tự nhiên nhất.", "show": "d1"},
        {"en": "I know! I'll have a barbecue on my birthday!", "vi": "Biết rồi! Sinh nhật mình sẽ làm tiệc nướng!", "gap": True},
        {"say": "Nếu đó là kế hoạch đã tính sẵn từ lâu, going to hợp hơn.", "show": "d2"},
        {"en": "I'm going to have a barbecue on my birthday.", "vi": "Sinh nhật mình sẽ làm tiệc nướng.", "gap": True},
        {"say": "Câu thứ hai: hai người đã bàn xong, có thể đã đặt bàn cho tối mai. Going to hợp nhất.", "show": "d3"},
        {"en": "We've decided we're going to try that new restaurant.", "vi": "Bọn mình quyết rồi, sẽ thử nhà hàng mới đó.", "gap": True},
        {"say": "Còn nếu hai người vừa bàn xong ngay lúc nói, will vẫn được. Để ý cách đọc restaurant kiểu Anh: hai âm tiết.", "show": "d4"},
        {"en": "OK, we'll try that new restaurant.", "vi": "Được, mình sẽ thử nhà hàng mới đó.", "gap": True},
        {"say": "Vừa quyết định ngay lúc nói: will. Đã quyết từ trước, đã đặt chỗ: going to hoặc đuôi ing. Hai cách đều đúng ngữ pháp; bối cảnh cho biết cách nào hợp hơn.", "show": "rule"},
    ]},
    {"kind": "scene", "visual": "tense_timeline", "eyebrow": "Ranh giới", "title": "Đuôi ing: bây giờ hay tương lai?",
     "data": {"question": "I'm meeting a client …", "question_vi": "cùng một dạng câu", "question_label": "Hai câu",
              "answers": NOW_OR_LATER, "rule": "Đuôi ing chỉ tương lai khi có mốc tương lai hoặc bối cảnh rõ. Không có thì đó là việc đang diễn ra."}, "lines": [
        {"say": "Hai câu cùng dạng: am cộng động từ đuôi ing. Một câu nói về bây giờ, một câu nói về tương lai.", "show": "q"},
        {"say": "Trục thời gian: vạch giữa là bây giờ, bên phải là tương lai.", "show": "axis"},
        {"say": "Câu thứ nhất có now. Bạn đang ngồi với khách, nên không nói chuyện được.", "show": "c1"},
        {"en": "I'm meeting a client now, so I can't talk.", "vi": "Tôi đang gặp khách nên không nói chuyện được.", "gap": True},
        {"say": "Câu thứ hai có tomorrow: một cuộc hẹn đã lên lịch.", "show": "c2"},
        {"en": "I'm meeting a client tomorrow.", "vi": "Mai tôi gặp một khách hàng.", "gap": True},
        {"say": "Đuôi ing chỉ nói về tương lai khi có mốc tương lai hoặc bối cảnh rõ. Không có, người nghe sẽ hiểu là việc đang diễn ra. Và đuôi ing hợp nhất với việc đã hẹn, đã lên lịch, không dùng cho dự đoán chung.", "show": "rule"},
    ]},
    {"kind": "scene", "visual": "fix_pairs", "eyebrow": "Lỗi thường gặp", "title": "Bốn lỗi, bốn cách sửa",
     "data": {"rows": TRAPS, "rule": "Sau will: nguyên thể, mọi ngôi như nhau. going to cần am, is, are. Dự đoán chung: will."}, "lines": [
        {"say": "Bốn lỗi hay gặp nhất. Lỗi một: thêm to sau will.", "show": "e1"},
        {"en": "I will apply for the job.", "vi": "Tôi sẽ nộp đơn xin việc đó.", "gap": True},
        {"say": "Lỗi hai: thêm đuôi s cho will.", "show": "e2"},
        {"en": "He will start next week.", "vi": "Tuần sau anh ấy bắt đầu.", "gap": True},
        {"say": "Lỗi ba: quên am, is, are trước going to.", "show": "e3"},
        {"en": "I'm going to apply for the job.", "vi": "Tôi sẽ nộp đơn xin việc đó.", "gap": True, "recap": False},
        {"say": "Lỗi bốn: dùng đuôi ing cho một dự đoán chung.", "show": "e4"},
        {"en": "In the future, people will live longer.", "vi": "Trong tương lai, con người sẽ sống lâu hơn.", "gap": True},
        {"say": "Sau will là động từ nguyên thể, mọi ngôi như nhau. Going to cần am, is, are đứng trước. Dự đoán chung thì dùng will.", "show": "rule"},
    ]},
    {"kind": "word", "headword": "career", "lines": [{"say": "Trước câu Speaking, học năm danh từ về công việc. Từ thứ nhất: sự nghiệp. Trọng âm rơi vào âm tiết thứ hai."}]},
    {"kind": "word", "headword": "salary", "lines": [{"say": "Từ thứ hai: lương trả theo tháng hoặc theo năm."}]},
    {"kind": "word", "headword": "interview", "lines": [{"say": "Từ thứ ba: buổi phỏng vấn. Câu ví dụ dùng đuôi ing cho một cuộc hẹn sáng mai."}]},
    {"kind": "word", "headword": "employer", "lines": [{"say": "Từ thứ tư: người hoặc công ty thuê bạn làm."}]},
    {"kind": "word", "headword": "deadline", "lines": [{"say": "Từ cuối: hạn chót. Câu ví dụ là phủ định với won't."}]},
    {"kind": "scene", "visual": "speaking_answer", "eyebrow": "IELTS Speaking Part 1", "title": "Dự đoán bằng will, lịch hẹn bằng đuôi ing",
     "data": {"question": "Do you think you will stay in the same job for your whole career?", "question_vi": "Bạn nghĩ mình sẽ làm một công việc suốt cả sự nghiệp không?",
              "short": "No.", "parts": ANSWER,
              "rule": "Dự đoán và dự định: will. Việc đã lên lịch: đuôi ing. Khi viết, dùng will."}, "lines": [
        {"say": "Giám khảo hỏi bạn có nghĩ mình sẽ làm một công việc suốt cả sự nghiệp không."},
        {"en": "Do you think you will stay in the same job for your whole career?", "show": "q"},
        {"say": "Chỉ đáp một chữ thì quá ngắn.", "show": "short"},
        {"say": "Câu một: trả lời thẳng, dùng lại will của câu hỏi."},
        {"en": "No, I don't think I will.", "vi": "Không, tôi nghĩ là không.", "gap": True, "show": "p1"},
        {"say": "Câu hai: một việc đã lên lịch, nên dùng đuôi ing."},
        {"en": "I'm starting a new job at a bank next month.", "vi": "Tháng sau tôi bắt đầu làm ở một ngân hàng.", "gap": True, "show": "p2"},
        {"say": "Câu ba: một dự định cho vài năm nữa, dùng will."},
        {"en": "In a few years, I think I'll apply for a job abroad.", "vi": "Vài năm nữa, chắc tôi sẽ xin việc ở nước ngoài.", "gap": True, "show": "p3"},
        {"say": "Câu bốn: một dự đoán chung, dùng will."},
        {"en": "Most people will have several employers in their career.", "vi": "Phần lớn mọi người sẽ làm cho vài chỗ trong sự nghiệp.", "gap": True, "show": "p4"},
        {"say": "Dự đoán và dự định: will. Việc đã lên lịch: đuôi ing. Khi viết thì dùng will. Hãy viết lại bốn câu này cho đúng với chính bạn.", "show": "rule"},
    ]},
    {"kind": "recap", "lines": [
        {"say": "Mẹ nhắc, bạn tắt máy ngay: quyết định ngay lúc nói dùng will. Giờ nói lại các câu của buổi này. Nghe một câu, rồi nói to trong quãng nghỉ.", "show": "title"},
    ]},
    {"kind": "end", "next": "Tiếp theo: học thẻ và từ, làm bài, rồi buổi 3 để xếp câu, nghe chép và viết.", "lines": [
        {"say": "Hết phần giảng của ngày một. Bạn học các thẻ và từ trong app, làm bài, rồi sang buổi ba để xếp câu, nghe chép và viết về công việc của bạn trong tương lai.", "show": "title"},
    ]},
]

RUBRIC = [
    {"criterion_vi": "Đúng đề, nội dung là của chính bạn", "max": 1, "note_vi": "Fluency and coherence"},
    {"criterion_vi": "Dự đoán, dự định bằng will; việc đã lên lịch bằng be + V-ing hoặc be going to", "max": 2, "note_vi": "Grammatical range"},
    {"criterion_vi": "Dạng động từ đúng: will / won't + nguyên thể, am / is / are going to + nguyên thể, am / is / are + V-ing", "max": 2, "note_vi": "Grammatical accuracy"},
]


def reshape(sessions: list[dict], exercise_ids: list[str], card_of: dict[str, int]) -> list[dict]:
    """Sitting 1 teaches cards 1-3 (three forms, predictions, the two rules to drop) with five verbs; sitting 2
    cards 4-5 (the decision made while speaking, be + V-ing now or later) with five nouns; the production work
    (build, type, dictation, writing) is a third sitting without a lecture."""
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
    s1["title_vi"] = "Buổi 1 · ba cách viết, dự đoán gần hay xa"
    s2["title_vi"] = "Buổi 2 · quyết định lúc nói, đuôi -ing chỉ tương lai"
    s1["can_do_vi"] = "Sau buổi này bạn lập được câu tương lai đơn với will, be going to, be + V-ing và dự đoán được bằng will hoặc be going to mà không theo luật gần hay xa."
    s2["can_do_vi"] = "Sau buổi này bạn dùng will cho quyết định ngay lúc nói, chọn được cách viết theo bối cảnh và nhận ra be + V-ing đang nói về bây giờ hay tương lai."
    s3 = {
        "title_vi": "Buổi 3 · vận dụng: xếp câu, gõ, nghe chép, viết",
        "can_do_vi": "Sau buổi này bạn tự xếp và gõ đúng câu tương lai đơn, nghe chép được câu có 'll và won't, và viết vài câu về công việc của bạn trong tương lai.",
        "use_vi": s1["use_vi"],
        "vocab": [],
        "check": moved,
    }
    assert set(s1["check"] + s2["check"] + moved) <= set(exercise_ids)
    return [s1, s2, s3] + rest

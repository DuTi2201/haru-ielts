"""G1 · Day 2 (lesson 45): the two lectures written by hand (lesson_audio.build_authored_lecture), and the
day's sittings reshaped around them. Same format as lecture_d1.py.

Sources: the teacher's week-1 material (two axes of a sentence, "Where is your sister?" pair,
temporariness as the one idea behind the continuous, complaint with always, planned arrangements,
the book's "not normally used" for state verbs) and Destination B2, Unit 1, p. 7 (the six groups of
state verbs and the verbs that have both meanings). His quoted sentences are verbatim from the notes.

Pronunciations: none are typed from memory. A word with no checked Oxford Advanced Learner's Dictionary
entry has no transcription (PRON stays empty until the entries are read).
"""

PRON: dict[str, str] = {}

TWO_AXES = [
    {"key": "x2", "head": "Hiện tại đơn", "en": "My sister lives in Thailand.", "vi": "Nêu một sự thật: chị ấy sống ở đó."},
    {"key": "x3", "head": "Tiếp diễn", "en": "My sister is living in Thailand.", "vi": "Thêm một ý: chỉ tạm thời, rồi sẽ khác."},
]

COMMON = [
    {"key": "k1", "head": "Đang xảy ra", "en": "Jan is watching a DVD upstairs.", "vi": "Phim rồi sẽ hết."},
    {"key": "k2", "head": "Ở tạm", "en": "We're staying in a hotel this week.", "vi": "Kỳ nghỉ rồi sẽ hết."},
    {"key": "k3", "head": "Cả một giai đoạn", "en": "I'm not drinking coffee this month.", "vi": "Tháng này qua là uống lại."},
]

DIET = [
    {"key": "d1", "head": "Bình thường: thói quen", "en": "We eat meat every day.", "vi": "Nhà tôi ngày nào cũng ăn thịt."},
    {"key": "d2", "head": "Đang ăn kiêng: tạm thời", "en": "We aren't eating any meat at the moment, as we're both on a diet.", "vi": "Lúc này chúng tôi không ăn thịt, vì cả hai đang ăn kiêng."},
]

USUALLY = [
    {"key": "u1", "wrong": "Are you usually playing hockey?", "right": "Do you usually play hockey?", "why": "usually nói việc lặp lại; tiếp diễn nói việc tạm thời. Hai ý xung đột."},
    {"key": "u2", "wrong": "He is often having lunch at twelve.", "right": "He often has lunch at twelve.", "why": "often cũng là lặp lại có quy luật: hiện tại đơn."},
]

TEMPORARY = [
    {"key": "t1", "head": "Việc đang diễn ra", "en": "Lan is talking to a customer.", "vi": "Lan đang nói chuyện với khách."},
    {"key": "t2", "head": "Tình huống tạm thời", "en": "I'm staying at my aunt's this week.", "vi": "Tuần này tôi ở nhà dì."},
    {"key": "t3", "head": "Thói quen tạm thời", "en": "I'm not drinking coffee this month.", "vi": "Tháng này tôi không uống cà phê."},
]

NOW_TRAP = [
    {"key": "n1", "head": "now so với trước kia", "en": "Where does your sister live now?", "vi": "Bây giờ chị bạn sống ở đâu?"},
    {"key": "n2", "head": "Đáp: sự thật ổn định", "en": "She lives in Hanoi now.", "vi": "Chị ấy sống ở Hà Nội."},
    {"key": "n3", "head": "Đáp: tạm thời", "en": "She is living in Hanoi now.", "vi": "Chị ấy đang sống ở Hà Nội (rồi sẽ đổi)."},
    {"key": "n4", "head": "Đúng một mốc", "en": "Lan is talking to a customer right now.", "vi": "Lan đang tiếp khách ngay lúc này."},
]

TREND = [
    {"key": "r1", "head": "Đổi dần, đang trên đường", "en": "Online courses are becoming more popular.", "vi": "Các khóa học trực tuyến đang ngày càng phổ biến."},
    {"key": "r2", "head": "Số liệu đang chuyển động", "en": "The price of rice is rising.", "vi": "Giá gạo đang tăng."},
    {"key": "r3", "head": "Nhận định đứng yên: hiện tại đơn", "en": "Online learning saves time.", "vi": "Học trực tuyến tiết kiệm thời gian."},
]

ALWAYS = [
    {"key": "a1", "head": "Thiếu trạng từ", "en": "My sister is turning the music loudly.", "vi": "Người nghe chỉ hiểu: ngay lúc này chị ấy đang vặn nhạc to."},
    {"key": "a2", "head": "Có always: than phiền", "en": "My sister is always turning the music so loudly!", "vi": "Lặp đi lặp lại, và bạn bực."},
    {"key": "a3", "head": "Thân mật, hơi ngạc nhiên", "en": "You're always leaving the lights on.", "vi": "Cậu lúc nào cũng để đèn sáng."},
]

ARRANGED = [
    {"key": "g1", "head": "Đã hẹn, đã sắp xếp", "en": "I'm seeing my tutor tomorrow morning.", "vi": "Sáng mai tôi gặp giáo viên hướng dẫn."},
    {"key": "g2", "head": "Có thời điểm cụ thể", "en": "We are flying to Da Nang on Friday.", "vi": "Thứ Sáu chúng tôi bay vào Đà Nẵng."},
]

SIX_GROUPS = [
    {"key": "s1", "head": "thinking · suy nghĩ", "en": "believe, imagine, know, mean, think, understand", "vi": "I know the answer."},
    {"key": "s2", "head": "existence · tồn tại", "en": "be, exist", "vi": "Dragons don't exist."},
    {"key": "s3", "head": "emotions · cảm xúc", "en": "hate, like, love, need, prefer, satisfy, want", "vi": "I want to finish this page."},
    {"key": "s4", "head": "the human senses · giác quan", "en": "hear, see, smell, sound, taste", "vi": "This soup smells good."},
    {"key": "s5", "head": "appearance · vẻ ngoài", "en": "appear, look, resemble, seem", "vi": "He looks tired."},
    {"key": "s6", "head": "possession and relationships · sở hữu, quan hệ", "en": "belong to, consist of, have, include, involve, own", "vi": "This book belongs to me."},
]

TWO_MEANINGS = [
    {"key": "m1", "head": "have · trạng thái", "en": "Do you have your plane ticket with you?", "vi": "Bạn mang vé máy bay theo không?"},
    {"key": "m2", "head": "have · hành động", "en": "Are you having lunch at the moment?", "vi": "Bạn đang ăn trưa à?"},
    {"key": "m3", "head": "think · trạng thái", "en": "I think this plan is good.", "vi": "Tôi cho rằng kế hoạch này tốt."},
    {"key": "m4", "head": "think · hành động", "en": "I'm thinking of changing my job.", "vi": "Tôi đang cân nhắc đổi việc."},
    {"key": "m5", "head": "see · trạng thái", "en": "I see what you mean.", "vi": "Tôi hiểu ý bạn."},
    {"key": "m6", "head": "see · hành động", "en": "I'm seeing the dentist at four.", "vi": "Bốn giờ tôi hẹn gặp nha sĩ."},
    {"key": "m7", "head": "be · tính vốn thế", "en": "He is rude.", "vi": "Anh ấy là người thô lỗ."},
    {"key": "m8", "head": "be · đang cư xử như vậy", "en": "He's being rude today.", "vi": "Hôm nay anh ấy cư xử thô lỗ."},
]

STATE_TRAPS = [
    {"key": "e1", "wrong": "I am knowing the answer.", "right": "I know the answer.", "why": "know là động từ trạng thái, không có nghĩa hành động."},
    {"key": "e2", "wrong": "I am wanting a coffee.", "right": "I want a coffee.", "why": "want thuộc nhóm cảm xúc: dùng hiện tại đơn."},
    {"key": "e3", "wrong": "From the chart, we are seeing that sales rose.", "right": "From the chart, we can see that sales rose.", "why": "see nghĩa nhìn thấy là giác quan: dùng can see."},
    {"key": "e4", "wrong": "She is having dark hair.", "right": "She has dark hair.", "why": "have nghĩa có là sở hữu: hiện tại đơn."},
]

SITTING_1 = [
    {"kind": "title", "hook": "Chị bạn vừa sang Thái Lan: nên nói lives hay is living, khi cả hai câu đều đúng với chữ now?", "lines": [
        {"say": "Hãy tưởng tượng thế này. Bạn đang ngồi uống cà phê với một người bạn nước ngoài, và cô ấy hỏi thăm chị gái bạn. Chị bạn vừa chuyển sang Thái Lan.", "show": "hook"},
        {"say": "Bạn mở miệng định trả lời, rồi khựng lại. Nên nói she lives, hay she is living? Từ hồi đi học, bạn được dạy: thấy chữ now thì chia tiếp diễn. Nhưng hôm nay bạn sẽ thấy chuyện không đơn giản như vậy."},
        {"say": "Cuối buổi, bạn sẽ không còn phải học thuộc năm gạch đầu dòng cách dùng nữa. Cả thì tiếp diễn chỉ xoay quanh một chữ duy nhất."},
    ]},
    {"kind": "scene", "visual": "tense_timeline", "eyebrow": "Tình huống", "title": "Một câu hỏi, hai câu đáp",
     "data": {"question": "Where does your sister live now?", "question_vi": "Bây giờ chị bạn sống ở đâu?", "question_label": "Bạn của bạn hỏi",
              "answers": [
                  {"key": "a1", "icon": "house", "at": "always", "tense": "Hiện tại đơn", "en": "She lives in Thailand now.", "vi": "Chị ấy định cư ở đó. Now chỉ so với trước kia."},
                  {"key": "a2", "icon": "suitcase", "at": "window", "tense": "Tiếp diễn", "en": "She is living in Thailand now.", "vi": "Chị ấy chỉ ở tạm, rồi sẽ đổi."},
              ],
              "rule": "Cùng chữ now, cả hai câu đều đúng. Khác nhau ở điều bạn muốn người nghe hiểu: ổn định hay tạm thời."}, "lines": [
        {"say": "Bạn bè hỏi bạn một câu ở hiện tại đơn."},
        {"en": "Where does your sister live now?", "vi": "Bây giờ chị bạn sống ở đâu?", "gap": True, "show": "q"},
        {"say": "Giả sử chị bạn đã chuyển hẳn sang đó: mua nhà, định cư lâu dài. Trước kia chị sống ở Việt Nam, bây giờ thì khác rồi. Chữ now ở đây chỉ để đối lại với trước kia. Bạn trả lời bằng hiện tại đơn.", "show": "axis"},
        {"en": "She lives in Thailand now.", "vi": "Chị ấy sống ở Thái Lan bây giờ.", "gap": True, "show": "a1"},
        {"say": "Bây giờ giả sử khác đi. Chị bạn chỉ sang học trao đổi sáu tháng, hết sáu tháng là về. Bạn muốn người nghe hiểu đúng điều đó, nên bạn đổi sang tiếp diễn."},
        {"en": "She is living in Thailand now.", "vi": "Chị ấy đang sống ở Thái Lan.", "gap": True, "show": "a2"},
        {"say": "Hai câu đều đúng một trăm phần trăm, và cả hai đều có chữ now. Vậy chữ now không quyết định thì. Điều quyết định là bạn muốn nói gì: việc này ổn định, hay chỉ tạm thời.", "show": "rule"},
    ]},
    {"kind": "scene", "visual": "ref_table", "eyebrow": "Một chữ cho mọi cách dùng", "title": "Điểm chung của ba câu",
     "data": {"cols": ["Cách dùng", "Ví dụ"], "rows": COMMON,
              "rule": "Mọi cách dùng của tiếp diễn đều có chung một ý: tạm thời, không kéo dài mãi mãi."}, "lines": [
        {"say": "Ở trường, người ta dạy thì tiếp diễn có năm cách dùng, và bắt học thuộc từng gạch đầu dòng. Thử làm khác đi. Hãy nhìn ba câu sau, rồi tự tìm điểm chung."},
        {"en": "Jan is watching a DVD upstairs.", "vi": "Jan đang xem đĩa ở tầng trên.", "gap": True, "show": "k1"},
        {"en": "We're staying in a hotel this week.", "vi": "Tuần này chúng tôi ở khách sạn.", "gap": True, "show": "k2"},
        {"en": "I'm not drinking coffee this month.", "vi": "Tháng này tôi không uống cà phê.", "gap": True, "show": "k3"},
        {"say": "Tìm ra điểm chung chưa? Cả ba việc rồi sẽ kết thúc. Phim sẽ hết, kỳ nghỉ ở khách sạn sẽ hết, qua tháng này bạn lại uống cà phê. Mọi cách dùng của tiếp diễn đều phản ánh tính tạm thời: việc đó không xảy ra mãi mãi.", "show": "rule"},
    ]},
    {"kind": "word", "headword": "temporary", "lines": [{"say": "Đây là từ chìa khóa của cả buổi."}]},
    {"kind": "scene", "visual": "sentence_forms", "eyebrow": "Công thức", "title": "Ba dạng câu của hiện tại tiếp diễn",
     "data": {"rows": [
                  {"key": "aff", "label": "Khẳng định", "parts": ["Lan", "is talking", "to a customer."], "hi": [1], "vi": "Lan đang nói chuyện với khách."},
                  {"key": "neg", "label": "Phủ định", "parts": ["Lan", "isn't talking", "to a customer."], "hi": [1], "vi": "Lan không đang nói chuyện với khách."},
                  {"key": "qst", "label": "Câu hỏi", "parts": ["Is", "Lan talking", "to a customer?"], "hi": [0, 1], "vi": "Lan đang nói chuyện với khách à?"},
              ],
              "persons_plain": True, "spelling_title": "Thêm -ing", "persons": [{"who": "I", "verb": "am + V-ing"}, {"who": "he · she · it", "verb": "is + V-ing"}, {"who": "you · we · they", "verb": "are + V-ing"}],
              "spelling": [["write", "writing"], ["run", "running"], ["lie", "lying"], ["study", "studying"], ["have", "having"]],
              "short": ["Yes, she is.", "No, she isn't."],
              "rule": "am / is / are + động từ thêm -ing. Câu hỏi: đưa am / is / are lên đầu."}, "lines": [
        {"say": "Biết khi nào dùng rồi, giờ mình học cách đặt câu. Công thức chỉ có một: am, is hoặc are, cộng động từ thêm ing. Với I dùng am, với he, she, it dùng is, với you, we, they dùng are.", "show": "persons"},
        {"en": "Lan is talking to a customer.", "vi": "Lan đang nói chuyện với khách.", "gap": True, "show": "aff"},
        {"say": "Phủ định: thêm not sau be. Câu hỏi: đưa be lên đầu câu."},
        {"en": "Lan isn't talking to a customer.", "vi": "Lan không đang nói chuyện với khách.", "gap": True, "show": "neg"},
        {"en": "Is Lan talking to a customer?", "vi": "Lan đang nói chuyện với khách à?", "gap": True, "show": "qst"},
        {"say": "Trả lời ngắn thì dùng lại be: yes, she is, hoặc no, she isn't.", "show": "short"},
        {"say": "Chú ý chính tả: write bỏ e thành writing, run gấp đôi n thành running, lie đổi thành lying.", "show": "spelling"},
        {"say": "Một lỗi người Việt hay mắc là quên be: She living in Hue. Luôn có am, is hoặc are."},
        {"say": "Tóm lại: be cộng ing, và câu hỏi đưa be lên đầu.", "show": "rule"},
    ]},
    {"kind": "scene", "visual": "ref_table", "eyebrow": "Cùng một động từ", "title": "Ăn thịt hay ăn kiêng?",
     "data": {"cols": ["Tình huống", "Ví dụ"], "rows": DIET,
              "rule": "Cùng động từ eat: thói quen thì hiện tại đơn, nhưng có lý do tạm thời thì tiếp diễn."}, "lines": [
        {"say": "Thử một ví dụ nữa. Eat là động từ bình thường, thường nói về thói quen. Nhà bạn ăn thịt mỗi ngày."},
        {"en": "We eat meat every day.", "vi": "Nhà tôi ngày nào cũng ăn thịt.", "gap": True, "show": "d1"},
        {"say": "Nhưng dạo này hai vợ chồng đang ăn kiêng. Ăn kiêng là một giai đoạn tạm thời: hết ăn kiêng, bạn lại ăn thịt như thường. Vì lý do tạm thời đó, dù eat thường chỉ thói quen, ở đây bạn dùng tiếp diễn."},
        {"en": "We aren't eating any meat at the moment, as we're both on a diet.", "vi": "Lúc này chúng tôi không ăn thịt, vì cả hai đang ăn kiêng.", "gap": True, "show": "d2"},
        {"say": "Động từ giống nhau, thì khác nhau, chỉ vì bạn muốn nói điều khác nhau.", "show": "rule"},
    ]},
    {"kind": "word", "headword": "trend", "lines": [{"say": "Từ cuối của phần này, rất hay gặp trong bài viết."}]},
    {"kind": "scene", "visual": "ref_table", "eyebrow": "Dùng trong IELTS", "title": "Xu hướng đang thay đổi",
     "data": {"cols": ["Dùng khi", "Ví dụ"], "rows": TREND,
              "rule": "Việc đang đổi dần: tiếp diễn. Một nhận định đứng yên: hiện tại đơn."}, "lines": [
        {"say": "Từ chữ tạm thời, mình suy ra ngay một cách dùng nữa. Thế giới không đứng yên. Cái gì đang đổi dần thì chưa dừng lại: nó đang trên đường đi tới một trạng thái khác. Thường có increasingly hoặc more and more.", "show": "r1"},
        {"en": "Online courses are becoming more popular in Vietnam.", "vi": "Các khóa học trực tuyến đang ngày càng phổ biến ở Việt Nam.", "gap": True},
        {"en": "The price of rice is rising.", "vi": "Giá gạo đang tăng.", "gap": True, "show": "r2"},
        {"say": "Nếu bạn chỉ nêu một nhận định đứng yên thì dùng hiện tại đơn."},
        {"en": "Online learning saves time.", "vi": "Học trực tuyến tiết kiệm thời gian.", "gap": True, "show": "r3"},
        {"say": "Đây là thì chính để nói về xu hướng ở Speaking Part 3 và khi mô tả biểu đồ kéo tới hiện tại.", "show": "rule"},
    ]},
    {"kind": "recap", "lines": [
        {"say": "Giờ nói lại các câu của buổi này. Nghe một câu, rồi nói to trong quãng nghỉ.", "show": "title"},
    ]},
    {"kind": "end", "next": "Tiếp theo: học các từ và mẫu ngữ pháp của buổi này, rồi làm bài tập.", "lines": [
        {"say": "Hết buổi một. Việc tiếp theo là học các từ và mẫu ngữ pháp trong app, rồi làm bài tập. Buổi hai nói về than phiền, kế hoạch và động từ trạng thái.", "show": "title"},
    ]},
]

SITTING_2 = [
    {"kind": "title", "hook": "Em gái bật nhạc ầm ĩ làm bạn phát bực, vì sao câu bạn nói ra lại nghe hoàn toàn bình thường, chẳng có chút bực nào?", "lines": [
        {"say": "Bạn có một cô em gái rất thích bật nhạc thật to. Hôm nay bạn bực quá, bạn kể với bạn bè về chuyện đó.", "show": "hook"},
        {"say": "Bạn nói một câu hoàn toàn đúng ngữ pháp. Nhưng bạn bè nghe xong chỉ gật gù, chẳng thấy cơn bực của bạn đâu cả. Vì sao vậy? Hôm nay mình đi tìm xem câu đó thiếu thứ gì."},
        {"say": "Sau đó bạn sẽ học thêm hai việc: kế hoạch đã hẹn, và những động từ không chia tiếp diễn."},
    ]},
    {"kind": "scene", "visual": "ref_table", "eyebrow": "Than phiền", "title": "Câu thiếu mất một chữ",
     "data": {"cols": ["Câu nói", "Ví dụ"], "rows": ALWAYS,
              "rule": "Muốn than phiền bằng tiếp diễn, chèn always hoặc constantly vào giữa be và V-ing."}, "lines": [
        {"say": "Đây là câu bạn đã nói với bạn bè."},
        {"en": "My sister is turning the music loudly.", "vi": "Chị tôi đang vặn nhạc to.", "gap": True, "show": "a1"},
        {"say": "Bạn bè hiểu gì? Chỉ hiểu rằng ngay lúc này chị ấy đang vặn nhạc to. Không có chuyện lặp đi lặp lại, và cũng chẳng có chút bực mình nào."},
        {"say": "Muốn than phiền hay chỉ trích, bạn phải chèn một trạng từ tần suất rất cao vào giữa be và V-ing: always, constantly, continually, forever.", "show": "a2"},
        {"en": "My sister is always turning the music so loudly!", "vi": "Chị tôi lúc nào cũng vặn nhạc to ơi là to!", "gap": True},
        {"say": "Cũng có khi không bực mà chỉ thân mật, hơi ngạc nhiên."},
        {"en": "You're always leaving the lights on.", "vi": "Cậu lúc nào cũng để đèn sáng.", "gap": True, "show": "a3"},
        {"say": "Tóm lại: muốn than phiền bằng tiếp diễn, chèn always hoặc constantly vào giữa be và V-ing.", "show": "rule"},
    ]},
    {"kind": "scene", "visual": "fix_pairs", "eyebrow": "Xung đột bản chất", "title": "Vì sao usually không đi với tiếp diễn",
     "data": {"rows": USUALLY,
              "rule": "Lặp lại có quy luật thì hiện tại đơn. Tiếp diễn chỉ nói việc tạm thời."}, "lines": [
        {"say": "Có một câu hỏi rất hay. Vì sao không ai nói are you usually playing? Không cần học thuộc luật. Chỉ cần nhìn bản chất."},
        {"say": "Usually và often nói về việc lặp lại có quy luật, năm này qua năm khác. Tiếp diễn nói về việc tạm thời. Hai ý đó đánh nhau, nên không đi cùng nhau.", "show": "u1"},
        {"en": "Do you usually play hockey?", "vi": "Bạn có hay chơi khúc côn cầu không?", "gap": True},
        {"say": "Often cũng vậy.", "show": "u2"},
        {"en": "He often has lunch at twelve.", "vi": "Anh ấy thường ăn trưa lúc mười hai giờ.", "gap": True},
        {"say": "Lặp lại có quy luật thì hiện tại đơn. Tiếp diễn chỉ dành cho việc tạm thời.", "show": "rule"},
    ]},
    {"kind": "word", "headword": "annoying", "lines": [{"say": "Một từ cho cảm xúc của phần trên."}]},
    {"kind": "scene", "visual": "ref_table", "eyebrow": "Tương lai gần", "title": "Việc đã hẹn, đã sắp xếp",
     "data": {"cols": ["Dùng khi", "Ví dụ"], "rows": ARRANGED,
              "rule": "Đã hẹn xong, có thời điểm cụ thể: dùng tiếp diễn."}, "lines": [
        {"say": "Cách dùng thứ ba: nói về tương lai gần khi việc đã được hẹn hoặc sắp xếp xong, kèm thời điểm.", "show": "g1"},
        {"en": "I'm seeing my tutor tomorrow morning.", "vi": "Sáng mai tôi gặp giáo viên hướng dẫn.", "gap": True},
        {"en": "We are flying to Da Nang on Friday.", "vi": "Thứ Sáu chúng tôi bay vào Đà Nẵng.", "gap": True, "show": "g2"},
        {"say": "Buổi về thì tương lai sẽ nói kỹ hơn. Hôm nay chỉ cần nhận ra: đã hẹn rồi thì dùng tiếp diễn.", "show": "rule"},
    ]},
    {"kind": "scene", "visual": "ref_table", "eyebrow": "Sáu nhóm", "title": "Động từ trạng thái",
     "data": {"cols": ["Nhóm", "Động từ"], "rows": SIX_GROUPS,
              "rule": "Thường không chia tiếp diễn, không phải không bao giờ. Nhìn vào nghĩa của câu."}, "lines": [
        {"say": "Nếu tiếp diễn là sự vận động tạm thời, thì những động từ nào chắc chắn không hợp? Là những động từ nói về điều đứng yên và bền vững: bạn biết, bạn yêu, bạn sở hữu. Chúng nói về trạng thái, không phải hành động, nên thường không chia tiếp diễn. Có sáu nhóm.", "show": "title"},
        {"say": "Nhóm một, suy nghĩ.", "show": "s1"},
        {"en": "I know the answer.", "vi": "Tôi biết đáp án.", "gap": True},
        {"say": "Nhóm hai, tồn tại: be và exist.", "show": "s2"},
        {"say": "Nhóm ba, cảm xúc.", "show": "s3"},
        {"en": "I want to finish this page.", "vi": "Tôi muốn đọc xong trang này.", "gap": True},
        {"say": "Nhóm bốn, giác quan: hear, see, smell, sound, taste.", "show": "s4"},
        {"say": "Nhóm năm, vẻ ngoài.", "show": "s5"},
        {"en": "He looks tired.", "vi": "Anh ấy trông mệt.", "gap": True},
        {"say": "Nhóm sáu, sở hữu và quan hệ.", "show": "s6"},
        {"say": "Chữ quan trọng là thường, không phải không bao giờ. Đừng học thuộc danh sách rồi cấm tuyệt đối: hãy nhìn vào nghĩa của câu.", "show": "rule"},
    ]},
    {"kind": "scene", "visual": "ref_table", "eyebrow": "Một động từ, hai nghĩa", "title": "Trạng thái và hành động",
     "data": {"cols": ["Nghĩa", "Ví dụ"], "rows": TWO_MEANINGS,
              "rule": "Nghĩa trạng thái: hiện tại đơn. Nghĩa hành động: chia tiếp diễn được."}, "lines": [
        {"say": "Một số động từ có cả nghĩa trạng thái lẫn nghĩa hành động. Có tám động từ như vậy: be, have, imagine, look, see, smell, taste, think. Đây là các cặp tiêu biểu.", "show": "title"},
        {"say": "Have nghĩa là có thì là trạng thái. Have lunch nghĩa là ăn thì là hành động.", "show": "m1"},
        {"en": "Do you have your plane ticket with you?", "vi": "Bạn mang vé máy bay theo không?", "gap": True},
        {"en": "Are you having lunch at the moment?", "vi": "Bạn đang ăn trưa à?", "gap": True, "show": "m2"},
        {"say": "Think nghĩa là cho rằng là trạng thái. Think of nghĩa là cân nhắc thì là hành động.", "show": "m3"},
        {"en": "I think this plan is good.", "vi": "Tôi cho rằng kế hoạch này tốt.", "gap": True},
        {"en": "I'm thinking of changing my job.", "vi": "Tôi đang cân nhắc đổi việc.", "gap": True, "show": "m4"},
        {"say": "See nghĩa là hiểu là trạng thái. See nghĩa là hẹn gặp thì là hành động.", "show": "m5"},
        {"en": "I see what you mean.", "vi": "Tôi hiểu ý bạn.", "gap": True},
        {"en": "I'm seeing the dentist at four.", "vi": "Bốn giờ tôi hẹn gặp nha sĩ.", "gap": True, "show": "m6"},
        {"say": "Be rude nghĩa là tính vốn thô lỗ. Be being rude nghĩa là hôm nay đang cư xử thô lỗ.", "show": "m7"},
        {"en": "He's being rude today.", "vi": "Hôm nay anh ấy cư xử thô lỗ.", "gap": True, "show": "m8"},
        {"say": "Cùng một động từ, nghĩa trạng thái dùng hiện tại đơn, nghĩa hành động chia tiếp diễn được.", "show": "rule"},
    ]},
    {"kind": "scene", "visual": "fix_pairs", "eyebrow": "Lỗi thường gặp", "title": "Bốn lỗi, bốn cách sửa",
     "data": {"rows": STATE_TRAPS,
              "rule": "Nghĩa trạng thái thì hiện tại đơn, kể cả khi việc đang xảy ra lúc nói. Mô tả biểu đồ dùng can see."}, "lines": [
        {"say": "Bốn lỗi người Việt hay mắc, đặc biệt trong bài viết. Lỗi thứ nhất.", "show": "e1"},
        {"en": "I know the answer.", "vi": "Tôi biết đáp án.", "gap": True},
        {"say": "Lỗi thứ hai.", "show": "e2"},
        {"en": "I want a coffee.", "vi": "Tôi muốn một cốc cà phê.", "gap": True},
        {"say": "Lỗi thứ ba rất hay gặp khi mô tả biểu đồ: dùng can see, không dùng are seeing.", "show": "e3"},
        {"en": "From the chart, we can see that sales rose.", "vi": "Nhìn biểu đồ, ta thấy doanh số tăng.", "gap": True},
        {"say": "Lỗi thứ tư.", "show": "e4"},
        {"en": "She has dark hair.", "vi": "Cô ấy có mái tóc đen.", "gap": True},
        {"say": "Nghĩa trạng thái thì hiện tại đơn, kể cả khi việc đang xảy ra lúc nói.", "show": "rule"},
    ]},
    {"kind": "recap", "lines": [
        {"say": "Giờ nói lại các câu của buổi này. Nghe một câu, rồi nói to trong quãng nghỉ.", "show": "title"},
    ]},
    {"kind": "end", "next": "Tiếp theo: học từ và mẫu ngữ pháp, làm bài tập, rồi buổi 3 để vận dụng.", "lines": [
        {"say": "Hết phần giảng của ngày hai. Bây giờ bạn học các từ và mẫu ngữ pháp trong app, làm bài tập, rồi sang buổi ba để nghe, nói và viết.", "show": "title"},
    ]},
]

# Each row of these scenes gets one drawn picture (frontend StoryArt.tsx); the scene type becomes picture_cards.
ICON = {
    "k1": "tv", "k2": "bed", "k3": "coffee_off",
    "d1": "steak", "d2": "salad",
    "r1": "trend", "r2": "trend", "r3": "thought",
    "a1": "speaker", "a2": "angry", "a3": "bulb",
    "g1": "calendar", "g2": "plane",
    "s1": "thought", "s2": "house", "s3": "heart", "s4": "eye", "s5": "face", "s6": "key",
}
for _rows in (COMMON, DIET, TREND, ALWAYS, ARRANGED, SIX_GROUPS):
    for _r in _rows:
        _r["icon"] = ICON[_r["key"]]
for _sitting in (SITTING_1, SITTING_2):
    for _slide in _sitting:
        _rows = (_slide.get("data") or {}).get("rows") or []
        if _slide.get("visual") == "ref_table" and _rows and _rows[0].get("key") in ICON:
            _slide["visual"] = "picture_cards"
            _slide["data"].pop("cols", None)

RUBRIC = [
    {"criterion_vi": "Đúng đề, nội dung là của chính bạn", "max": 1, "note_vi": "Task response"},
    {"criterion_vi": "Chọn thì hợp với điều muốn nói: sự thật hay tạm thời", "max": 2, "note_vi": "Grammatical range"},
    {"criterion_vi": "Dạng động từ đúng: be + V-ing, động từ trạng thái không chia tiếp diễn", "max": 2, "note_vi": "Grammatical accuracy"},
]


def reshape(sessions: list[dict], exercise_ids: list[str], card_of: dict[str, int]) -> list[dict]:
    """Day 2's sittings around the two lectures. Sitting 1 teaches cards 1-3 (formula, when to use, trend),
    sitting 2 cards 4-7 (always, arranged, state verbs in two cards); the rest (words from the books, production work) is
    a third sitting without a lecture."""
    pats = [g for s in sessions[:3] for g in s["grammar"]]
    allcheck = [i for s in sessions[:3] for i in s["check"]]
    s1, s2 = sessions[0], sessions[1]
    rest = sessions[3:]
    S1_WORDS = ["temporary", "trend"]
    S2_WORDS = ["annoying"]
    all_words = [w for s in sessions[:3] for w in s["vocab"]]
    left = [w for w in all_words if w not in S1_WORDS + S2_WORDS]
    s1["vocab"], s2["vocab"] = S1_WORDS, S2_WORDS
    s1["grammar"], s2["grammar"] = pats[:3], pats[3:]
    quiz = [i for i in allcheck if i[4] in "IQ"]
    s1["check"] = [i for i in quiz if card_of[i] < 3]
    s2["check"] = [i for i in quiz if card_of[i] >= 3]
    moved = [i for i in allcheck if i not in quiz]
    s1["lecture"], s2["lecture"] = SITTING_1, SITTING_2
    s1["title_vi"] = "Buổi 1 · công thức, tính tạm thời, chữ now, xu hướng"
    s2["title_vi"] = "Buổi 2 · than phiền, kế hoạch, động từ trạng thái"
    s3 = {
        "title_vi": "Buổi 3 · từ vựng và vận dụng: nghe chép, nói, viết",
        "can_do_vi": "Sau buổi này bạn biết thêm các từ về học tập, tự xếp và gõ được câu tiếp diễn, nghe chép được câu và viết câu về chính mình.",
        "use_vi": s1["use_vi"],
        "vocab": left,
        "check": moved,
    }
    assert set(s1["check"] + s2["check"] + moved) <= set(exercise_ids)
    return [s1, s2, s3] + rest

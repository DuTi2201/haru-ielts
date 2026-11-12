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
    {"key": "a1", "head": "Than phiền", "en": "My sister is always playing her music so loudly!", "vi": "Chị tôi lúc nào cũng bật nhạc to ơi là to!"},
    {"key": "a2", "head": "Thân mật, hơi ngạc nhiên", "en": "You're always leaving the lights on.", "vi": "Cậu lúc nào cũng để đèn sáng."},
    {"key": "a3", "head": "Chỉ nêu thói quen: hiện tại đơn", "en": "He usually has lunch at twelve.", "vi": "Anh ấy thường ăn trưa lúc mười hai giờ."},
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
    {"kind": "title", "hook": "Hai câu cùng đúng ngữ pháp, vì sao vẫn nói hai điều khác nhau?", "lines": [
        {"say": "Chị bạn sống ở Thái Lan. Hai cách nói đều đúng ngữ pháp, vậy vì sao người nghe lại hiểu hai chuyện khác nhau?", "show": "hook"},
        {"say": "Buổi này mình học hiện tại tiếp diễn theo đúng một ý: tính tạm thời. Hiểu ý đó, bạn sẽ không còn chọn thì theo chữ now."},
    ]},
    {"kind": "scene", "visual": "ref_table", "eyebrow": "Hai câu, hai ý", "title": "Cùng đúng ngữ pháp, khác ý",
     "data": {"cols": ["Thì", "Ví dụ"], "rows": TWO_AXES,
              "rule": "Hiện tại đơn nêu sự thật. Tiếp diễn thêm một ý: việc này tạm thời."}, "lines": [
        {"say": "Câu đầu nêu một sự thật: chị bạn sống ở Thái Lan.", "show": "x2"},
        {"en": "My sister lives in Thailand.", "vi": "Chị tôi sống ở Thái Lan.", "gap": True},
        {"say": "Câu sau thêm một ý: chị ấy chỉ ở tạm, rồi sẽ khác.", "show": "x3"},
        {"en": "My sister is living in Thailand.", "vi": "Chị tôi đang sống ở Thái Lan.", "gap": True},
        {"say": "Cả hai đều đúng ngữ pháp. Chọn thì là chọn điều bạn muốn người nghe hiểu thêm.", "show": "rule"},
    ]},
    {"kind": "word", "headword": "temporary", "lines": [{"say": "Từ chìa khóa của buổi này."}]},
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
        {"say": "Công thức chỉ có một: am, is hoặc are, cộng động từ thêm ing. Với I dùng am, với he, she, it dùng is, với you, we, they dùng are.", "show": "persons"},
        {"en": "Lan is talking to a customer.", "vi": "Lan đang nói chuyện với khách.", "gap": True, "show": "aff"},
        {"say": "Phủ định: thêm not sau be. Câu hỏi: đưa be lên đầu câu."},
        {"en": "Lan isn't talking to a customer.", "vi": "Lan không đang nói chuyện với khách.", "gap": True, "show": "neg"},
        {"en": "Is Lan talking to a customer?", "vi": "Lan đang nói chuyện với khách à?", "gap": True, "show": "qst"},
        {"say": "Trả lời ngắn thì dùng lại be: yes, she is, hoặc no, she isn't.", "show": "short"},
        {"say": "Chú ý chính tả: write bỏ e thành writing, run gấp đôi n thành running, lie đổi thành lying.", "show": "spelling"},
        {"say": "Một lỗi người Việt hay mắc là quên be: She living in Hue. Luôn có am, is hoặc are."},
        {"say": "Tóm lại: be cộng ing, và câu hỏi đưa be lên đầu.", "show": "rule"},
    ]},
    {"kind": "scene", "visual": "ref_table", "eyebrow": "Một ý duy nhất", "title": "Mọi cách dùng đều là tạm thời",
     "data": {"cols": ["Cách dùng", "Ví dụ"], "rows": TEMPORARY,
              "rule": "Tiếp diễn luôn gắn với tính tạm thời: việc đang diễn ra, rồi sẽ dừng hoặc đổi."}, "lines": [
        {"say": "Các cách dùng của hiện tại tiếp diễn nhìn thì nhiều, nhưng chung một ý. Đó là tính tạm thời. Việc đang diễn ra thì rồi sẽ kết thúc.", "show": "t1"},
        {"en": "Lan is talking to a customer.", "vi": "Lan đang nói chuyện với khách.", "gap": True},
        {"say": "Tình huống tạm thời: tuần này tôi ở nhà dì, tuần sau tôi về nhà."},
        {"en": "I'm staying at my aunt's this week.", "vi": "Tuần này tôi ở nhà dì.", "gap": True, "show": "t2"},
        {"say": "Cả một thói quen cũng có thể tạm thời: chỉ trong tháng này."},
        {"en": "I'm not drinking coffee this month.", "vi": "Tháng này tôi không uống cà phê.", "gap": True, "show": "t3"},
        {"say": "Đang xem phim, đang ở khách sạn, đang bỏ cà phê: tất cả rồi sẽ hết. Vì vậy tiếp diễn luôn gắn với tính tạm thời.", "show": "rule"},
    ]},
    {"kind": "scene", "visual": "ref_table", "eyebrow": "Bẫy chữ now", "title": "Thấy now là chia tiếp diễn?",
     "data": {"cols": ["Tình huống", "Ví dụ"], "rows": NOW_TRAP,
              "rule": "Now chỉ so với trước kia. Hỏi mình: muốn nói sự thật ổn định, hay tạm thời, hay đúng một mốc?"}, "lines": [
        {"say": "Bẫy lớn nhất của người học: thấy chữ now là chia tiếp diễn. Xem câu hỏi này."},
        {"en": "Where does your sister live now?", "vi": "Bây giờ chị bạn sống ở đâu?", "gap": True, "show": "n1"},
        {"say": "Chị ấy chuyển hẳn đến Hà Nội, bạn đáp bằng hiện tại đơn. Now chỉ nói bây giờ khác trước kia."},
        {"en": "She lives in Hanoi now.", "vi": "Chị ấy sống ở Hà Nội.", "gap": True, "show": "n2"},
        {"say": "Nếu chị ấy chỉ ở tạm, bạn đáp bằng tiếp diễn. Cùng chữ now, hai câu khác nhau."},
        {"en": "She is living in Hanoi now.", "vi": "Chị ấy đang sống ở Hà Nội.", "gap": True, "show": "n3"},
        {"say": "Còn khi nói một hành động đang diễn ra đúng lúc nói, như right now hoặc at the moment, dùng tiếp diễn."},
        {"en": "Lan is talking to a customer right now.", "vi": "Lan đang tiếp khách ngay lúc này.", "gap": True, "show": "n4"},
        {"say": "Chữ now không quyết định thì. Điều bạn muốn nói mới quyết định.", "show": "rule"},
    ]},
    {"kind": "word", "headword": "trend", "lines": [{"say": "Từ cuối của phần này, rất hay gặp trong bài viết."}]},
    {"kind": "scene", "visual": "ref_table", "eyebrow": "Dùng trong IELTS", "title": "Xu hướng đang thay đổi",
     "data": {"cols": ["Dùng khi", "Ví dụ"], "rows": TREND,
              "rule": "Việc đang đổi dần: tiếp diễn. Một nhận định đứng yên: hiện tại đơn."}, "lines": [
        {"say": "Thay đổi cũng là tạm thời, vì nó đang trên đường tới một trạng thái khác. Thường có increasingly hoặc more and more.", "show": "r1"},
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
    {"kind": "title", "hook": "Vì sao I am knowing là sai, mà He is being rude lại đúng?", "lines": [
        {"say": "Vì sao nói I am knowing là sai, mà He is being rude lại đúng? Có những động từ thường không chia tiếp diễn, và có những động từ chia được khi đổi nghĩa.", "show": "hook"},
        {"say": "Buổi hai có ba việc: than phiền với always, kế hoạch đã hẹn, và động từ trạng thái."},
    ]},
    {"kind": "scene", "visual": "ref_table", "eyebrow": "Cảm xúc của người nói", "title": "always + V-ing",
     "data": {"cols": ["Sắc thái", "Ví dụ"], "rows": ALWAYS,
              "rule": "Có cảm xúc về việc lặp lại: always + V-ing. Chỉ nêu thói quen: hiện tại đơn."}, "lines": [
        {"say": "Hiện tại tiếp diễn đi với always khi người nói có cảm xúc về việc lặp lại đó. Phổ biến nhất là bực mình.", "show": "a1"},
        {"en": "My sister is always playing her music so loudly!", "vi": "Chị tôi lúc nào cũng bật nhạc to ơi là to!", "gap": True},
        {"say": "Cũng có thể là thân mật, hơi ngạc nhiên."},
        {"en": "You're always leaving the lights on.", "vi": "Cậu lúc nào cũng để đèn sáng.", "gap": True, "show": "a2"},
        {"say": "Nếu không có cảm xúc, chỉ nêu thói quen, thì dùng hiện tại đơn. Tiếp diễn thường không đi với usually hay often."},
        {"en": "He usually has lunch at twelve.", "vi": "Anh ấy thường ăn trưa lúc mười hai giờ.", "gap": True, "show": "a3"},
        {"say": "Tóm lại: có cảm xúc thì always cộng V-ing, không có thì hiện tại đơn.", "show": "rule"},
    ]},
    {"kind": "scene", "visual": "ref_table", "eyebrow": "Tương lai gần", "title": "Việc đã hẹn, đã sắp xếp",
     "data": {"cols": ["Dùng khi", "Ví dụ"], "rows": ARRANGED,
              "rule": "Đã hẹn xong, có thời điểm cụ thể: dùng tiếp diễn."}, "lines": [
        {"say": "Cách dùng thứ ba: nói về tương lai gần khi việc đã được hẹn hoặc sắp xếp xong, kèm thời điểm.", "show": "g1"},
        {"en": "I'm seeing my tutor tomorrow morning.", "vi": "Sáng mai tôi gặp giáo viên hướng dẫn.", "gap": True},
        {"en": "We are flying to Da Nang on Friday.", "vi": "Thứ Sáu chúng tôi bay vào Đà Nẵng.", "gap": True, "show": "g2"},
        {"say": "Buổi về thì tương lai sẽ nói kỹ hơn. Hôm nay chỉ cần nhận ra: đã hẹn rồi thì dùng tiếp diễn.", "show": "rule"},
    ]},
    {"kind": "word", "headword": "annoying", "lines": [{"say": "Một từ cho cảm xúc của phần trên."}]},
    {"kind": "scene", "visual": "ref_table", "eyebrow": "Sáu nhóm", "title": "Động từ trạng thái",
     "data": {"cols": ["Nhóm", "Động từ"], "rows": SIX_GROUPS,
              "rule": "Thường không chia tiếp diễn, không phải không bao giờ. Nhìn vào nghĩa của câu."}, "lines": [
        {"say": "Động từ trạng thái nói về điều đang là, không phải một hành động, nên thường không chia tiếp diễn. Có sáu nhóm.", "show": "title"},
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

"""Week 2 · Day 1 (build day 21): the past simple. Two lectures written by hand
(lesson_audio.build_authored_lecture) and the day's sittings reshaped around them. Same format as lecture_d1.py.

Sources: session 3 of the course, stages 1, 2 and 5 (docs/WEEK2_PLAN.md): the two uses of the past simple
(finished, and a chain of actions: "when you list actions in the past, the past simple is right"), the
vegetables question answered in two tenses, "no rule says a Have question takes a Have answer"
(Have you ever been to Italy? / I went there two years ago; When did you go there?), since / in / for with the
piano sentences ("for is only a preposition"), The last time vs It's the first time, emphatic did
(exercise A, item 12), the lie told about the past, the guiding rule (unsure, no temporariness, no before-after:
past simple), and the pronunciation slips (read /red/, -ed as /ɪd/, didn't hear, I was).
Corrections made before use (docs/WEEK2_PLAN.md, last section): "I went to drink" is written "I went for a
drink"; the stopped piano sentence is "I studied the piano for two years, then I stopped", not "for the last
two years" (that phrase runs up to now and goes with the present perfect).

Pronunciations: Oxford Learner's Dictionaries, British English, read 2026-11-25. A word without a checked
entry has none.
"""

PRON = {
    "invent": "/ɪnˈvent/",
    "invention": "/ɪnˈvenʃn/",
    "design": "/dɪˈzaɪn/",
    "develop": "/dɪˈveləp/",
    "improve": "/ɪmˈpruːv/",
    "replace": "/rɪˈpleɪs/",
    "device": "/dɪˈvaɪs/",
    "engine": "/ˈendʒɪn/",
    "vehicle": "/ˈviːəkl/",
    "prototype": "/ˈprəʊtətaɪp/",
}

# a line under each word: the past form and how its -ed sounds, or what the word names
NOTES = {
    "invent": "Quá khứ: invented, đuôi -ed đọc /ɪd/.",
    "design": "Quá khứ: designed, đuôi -ed đọc /d/.",
    "develop": "Quá khứ: developed, đuôi -ed đọc /t/.",
    "improve": "Quá khứ: improved, đuôi -ed đọc /d/.",
    "replace": "Quá khứ: replaced, đuôi -ed đọc /t/. replace A with B: thay A bằng B.",
    "invention": "Danh từ của invent: vật hoặc ý tưởng được phát minh.",
    "device": "Một vật được làm ra cho một việc cụ thể: điện thoại, máy tính bảng, đồng hồ thông minh.",
    "engine": "Bộ phận tạo ra sức chạy cho xe, máy bay, tàu.",
    "vehicle": "Từ chung cho mọi loại xe chở người hoặc chở hàng. Chữ h thường không đọc.",
    "prototype": "Bản làm thử đầu tiên, trước khi làm mẫu cuối cùng.",
}

S1_WORDS = ["invent", "design", "develop", "improve", "replace"]
S2_WORDS = ["invention", "device", "engine", "vehicle", "prototype"]

CHAIN = [
    {"key": "r1", "icon": "cup", "label": "Việc 1", "kind": "chain", "en": "I went for a drink,", "vi": "Tôi đi uống nước,"},
    {"key": "r2", "icon": "house", "label": "Việc 2", "kind": "chain", "en": "then I came home,", "vi": "rồi về nhà,"},
    {"key": "r3", "icon": "bed", "label": "Việc 3", "kind": "chain", "en": "and after that I went to bed.", "vi": "sau đó đi ngủ."},
]

ED_SOUNDS = [
    {"key": "e1", "head": "/t/ · sau âm vô thanh", "en": "developed, worked, watched", "vi": "Sau /p/, /k/, /s/, /ʃ/, /tʃ/, /f/. Không thêm âm tiết."},
    {"key": "e2", "head": "/d/ · sau âm hữu thanh", "en": "designed, improved, played", "vi": "Sau âm hữu thanh và nguyên âm. Không thêm âm tiết."},
    {"key": "e3", "head": "/ɪd/ · sau /t/, /d/", "en": "invented, wanted, ended", "vi": "Thêm một âm tiết: in-ven-tid."},
]

USES = [
    {"key": "u1", "icon": "phone", "head": "Việc đã khép lại", "en": "My grandfather bought his first phone in 1998.", "vi": "Người nói coi việc đó thuộc về quá khứ."},
    {"key": "u2", "icon": "house", "head": "Không cần trạng từ thời gian", "en": "My grandfather built this house.", "vi": "Không nói lúc nào, nhưng việc thuộc về một lúc đã qua."},
    {"key": "u3", "icon": "clock", "head": "Kể cả khi nói dối", "en": "I came home at six.", "vi": "Thật ra về lúc chín giờ: vẫn là quá khứ đơn."},
]

VEG = [
    {"key": "a1", "icon": "basket", "at": "point", "tense": "Quá khứ đơn · biết lúc nào", "en": "Yes, I bought some on the way home.", "vi": "Người nói biết đã mua lúc nào."},
    {"key": "a2", "icon": "basket", "at": "done", "tense": "Hiện tại hoàn thành · đã làm", "en": "Yes, I have bought some.", "vi": "Mua rồi, đừng hỏi mấy giờ."},
]

DIALOGUE = [
    {"key": "k1", "who": "A", "tag": "Hiện tại hoàn thành", "en": "Have you ever been to Italy?", "vi": "Bạn đã đến Ý bao giờ chưa?"},
    {"key": "k2", "who": "B", "tag": "Chưa nói lúc nào", "en": "Yes, I have.", "vi": "Rồi."},
    {"key": "k3", "who": "A", "tag": "Hỏi lúc nào · quá khứ đơn", "en": "When did you go there?", "vi": "Bạn đi khi nào?"},
    {"key": "k4", "who": "B", "tag": "Có mốc · quá khứ đơn", "mark": "anchor", "en": "I went there two years ago.", "vi": "Tôi đi hai năm trước."},
]

PIANO = [
    {"key": "b1", "icon": "piano", "at": "span", "tense": "since · vẫn học", "en": "I have studied the piano since 2003.", "vi": "Bắt đầu năm 2003, bây giờ vẫn học."},
    {"key": "b2", "icon": "calendar", "at": "point", "tense": "in · một năm đã qua", "en": "I studied the piano in 2003.", "vi": "Học trong năm 2003."},
    {"key": "b3", "icon": "piano", "at": "span", "tense": "for · vẫn học", "en": "I have studied the piano for two years.", "vi": "Hai năm nay, vẫn học."},
    {"key": "b4", "icon": "piano", "at": "past", "tense": "for · đã nghỉ", "en": "I studied the piano for two years, then I stopped.", "vi": "Học hai năm rồi nghỉ."},
]

TWO_PATTERNS = [
    {"key": "l1", "icon": "calendar", "at": "point", "tense": "The last time · quá khứ đơn", "en": "The last time I saw Lan, she talked about changing jobs.", "vi": "Một mốc đã qua."},
    {"key": "l2", "icon": "phone", "at": "span", "tense": "It's the first time · hiện tại hoàn thành", "en": "It's the first time I have used this app.", "vi": "Tính từ trước tới bây giờ."},
]

TRAPS = [
    {"key": "e1", "wrong": "I didn't heard the phone.", "right": "I didn't hear the phone.", "why": "Sau didn't là động từ nguyên thể."},
    {"key": "e2", "wrong": "I have been there two years ago.", "right": "I went there two years ago.", "why": "Có mốc thời gian: quá khứ đơn."},
    {"key": "e3", "wrong": "I have studied the piano in 2003.", "right": "I studied the piano in 2003.", "why": "in 2003 là một năm đã qua."},
    {"key": "e4", "wrong": "The last time I had seen her, she looked tired.", "right": "The last time I saw her, she looked tired.", "why": "Vế The last time chia quá khứ đơn."},
]

ANSWER = [
    {"key": "p1", "role": "Trả lời thẳng", "tense": "Quá khứ đơn", "en": "I got my first mobile phone in 2012, when I was fourteen.", "vi": "Tôi có chiếc điện thoại đầu tiên năm 2012, năm mười bốn tuổi."},
    {"key": "p2", "role": "Ai, nhân dịp gì", "tense": "Quá khứ đơn", "en": "My parents bought it for my birthday.", "vi": "Bố mẹ mua cho tôi nhân sinh nhật."},
    {"key": "p3", "role": "Kể thêm", "tense": "Quá khứ đơn", "en": "It was a simple device, but I used it every day.", "vi": "Đó là một thiết bị đơn giản, nhưng ngày nào tôi cũng dùng."},
    {"key": "p4", "role": "Nối tới bây giờ", "tense": "Hiện tại hoàn thành", "en": "I have changed phones three times since then.", "vi": "Từ đó tới giờ tôi đã đổi điện thoại ba lần."},
]

SITTING_1 = [
    {"kind": "title", "hook": "Kể ba việc bạn làm tối qua: cần bao nhiêu thì?", "lines": [
        {"say": "Thử kể lại tối qua bằng tiếng Anh: bạn đi uống nước, về nhà, rồi đi ngủ. Ba việc. Bạn cần bao nhiêu thì để kể?", "show": "hook"},
        {"say": "Buổi này trả lời câu hỏi đó, rồi học công thức, cách viết và cách đọc đuôi ed, và hai cách dùng của thì quá khứ đơn."},
    ]},
    {"kind": "scene", "visual": "story_strip", "eyebrow": "Thí nghiệm", "title": "Ba việc, một thì",
     "data": {"frame": "strip", "panels": CHAIN, "rule": "Kể lần lượt các việc đã xảy ra: tất cả đều chia quá khứ đơn."}, "lines": [
        {"say": "Việc thứ nhất: đi uống nước.", "show": "r1"},
        {"en": "I went for a drink,", "vi": "Tôi đi uống nước,", "gap": True, "recap": False},
        {"say": "Việc thứ hai: về nhà.", "show": "r2"},
        {"en": "then I came home,", "vi": "rồi về nhà,", "gap": True, "recap": False},
        {"say": "Việc thứ ba: đi ngủ.", "show": "r3"},
        {"en": "and after that I went to bed.", "vi": "sau đó đi ngủ.", "gap": True, "recap": False},
        {"say": "Cả câu đọc liền một lượt."},
        {"en": "I went for a drink, then I came home, and after that I went to bed.", "vi": "Tôi đi uống nước, rồi về nhà, sau đó đi ngủ.", "gap": True},
        {"say": "Vậy chỉ cần một thì. Đây là một cách dùng của quá khứ đơn: kể lần lượt các việc đã xảy ra. Bạn chia tất cả ở quá khứ đơn là đúng, không cần cân nhắc việc nào trước, việc nào sau, vì thứ tự câu đã nói điều đó.", "show": "rule"},
    ]},
    {"kind": "scene", "visual": "sentence_forms", "eyebrow": "Công thức", "title": "Ba dạng câu của quá khứ đơn",
     "data": {"rows": [
                  {"key": "aff", "label": "Khẳng định", "parts": ["We", "watched", "the match."], "hi": [1], "vi": "Chúng tôi xem trận đấu."},
                  {"key": "neg", "label": "Phủ định", "parts": ["We", "didn't watch", "the news."], "hi": [1], "vi": "Chúng tôi không xem thời sự."},
                  {"key": "qst", "label": "Câu hỏi", "parts": ["Did", "you watch", "the match?"], "hi": [0, 1], "vi": "Bạn có xem trận đấu không?"},
              ],
              "persons": [{"who": "I · you · we · they", "verb": "watched"}, {"who": "he · she · it", "verb": "watched"}],
              "persons_plain": True,
              "spelling_title": "Viết đuôi ed, và động từ bất quy tắc",
              "spelling": [["work", "worked"], ["replace", "replaced"], ["study", "studied"], ["stop", "stopped"], ["go", "went"], ["buy", "bought"]],
              "short": ["Yes, I did.", "No, I didn't."],
              "rule": "Khẳng định: V-ed hoặc dạng bất quy tắc, mọi ngôi như nhau. Phủ định và câu hỏi: didn't, did, động từ về nguyên thể."}, "lines": [
        {"say": "Bây giờ là công thức. Trước hết, ở quá khứ đơn mọi ngôi dùng cùng một dạng. Ngôi thứ ba số ít không thêm gì riêng.", "show": "persons"},
        {"en": "We watched the match.", "vi": "Chúng tôi xem trận đấu.", "gap": True, "show": "aff"},
        {"say": "Cách viết: phần lớn động từ thêm đuôi ed, như work thành worked. Replace đã có sẵn nửa đuôi, chỉ thêm phần còn thiếu: replaced.", "show": "spelling"},
        {"say": "Study thành studied. Từ một âm tiết tận cùng bằng một nguyên âm và một phụ âm, như stop, thì gấp đôi phụ âm cuối: stopped. Work hay rain thì không."},
        {"say": "Và có một nhóm động từ bất quy tắc phải học thuộc: go thành went, buy thành bought."},
        {"say": "Câu phủ định: đặt didn't trước động từ, và động từ về nguyên thể."},
        {"en": "We didn't watch the news.", "vi": "Chúng tôi không xem thời sự.", "gap": True, "show": "neg"},
        {"say": "Câu hỏi: đưa did lên đầu câu, động từ cũng về nguyên thể. Trả lời ngắn thì dùng lại did.", "show": "short"},
        {"en": "Did you watch the match?", "vi": "Bạn có xem trận đấu không?", "gap": True, "show": "qst"},
        {"say": "Riêng động từ be không mượn did. Chủ ngữ tôi, anh ấy, cô ấy, nó dùng was; bạn, chúng tôi, họ dùng were."},
        {"say": "Câu hỏi về chủ ngữ cũng không mượn did: người hỏi chưa biết ai làm việc đó."},
        {"en": "Who invented the telephone?", "vi": "Ai phát minh ra điện thoại?", "gap": True},
        {"say": "Tóm lại. Câu khẳng định: động từ thêm đuôi ed, hoặc đổi sang dạng bất quy tắc, mọi ngôi như nhau. Câu phủ định và câu hỏi: dùng didn't hoặc did, và động từ về nguyên thể.", "show": "rule"},
    ]},
    {"kind": "scene", "visual": "do_does", "eyebrow": "Nhấn mạnh", "title": "did + động từ nguyên thể",
     "data": {"plain": "I passed the test.", "emph": ["I", "did", "pass the test!"], "emph_vi": "Tôi có đỗ mà!",
              "ex2": ["The film was long, but I", "did", "enjoy it."], "ex2_vi": "Phim dài, nhưng tôi vẫn thích.",
              "wrong": "I did passed the test.", "right": "I did pass the test.",
              "rule": "Đã có did thì động từ sau nó ở dạng nguyên thể."}, "lines": [
        {"say": "Câu khẳng định ở quá khứ đơn bình thường không có did."},
        {"en": "I passed the test.", "show": "plain"},
        {"say": "Nhưng khi ai đó nói bạn trượt, và bạn muốn cãi lại, bạn đặt did trước động từ: không đúng đâu, tôi có đỗ mà, còn được điểm khá."},
        {"en": "No, that's not right. I did pass the test. I got a B.", "vi": "Không đúng đâu. Tôi có đỗ mà. Tôi được điểm B.", "gap": True, "show": "emph"},
        {"say": "Hoặc khi muốn nêu một điểm bù lại."},
        {"en": "The film was long, but I did enjoy it.", "vi": "Phim dài, nhưng tôi vẫn thích.", "gap": True, "show": "ex2"},
        {"say": "Đừng chia hai lần. Câu sai.", "show": "wrong"},
        {"en": "I did passed the test."},
        {"say": "Câu đúng.", "show": "right"},
        {"en": "I did pass the test.", "vi": "Tôi có đỗ mà.", "gap": True},
        {"say": "Đã có did thì động từ sau nó ở dạng nguyên thể.", "show": "rule"},
    ]},
    {"kind": "scene", "visual": "ref_table", "eyebrow": "Phát âm", "title": "Ba cách đọc đuôi ed",
     "data": {"rows": ED_SOUNDS, "rule": "Chỉ động từ tận cùng bằng âm /t/ hoặc /d/ mới thêm một âm tiết /ɪd/."}, "lines": [
        {"say": "Đuôi ed có ba cách đọc, tùy âm cuối của động từ. Nhóm một: động từ tận cùng bằng âm vô thanh, như develop, work, watch. Đuôi ed đọc nhẹ, giống cuối từ worked.", "show": "e1"},
        {"en": "developed, worked, watched", "gap": True, "recap": False},
        {"say": "Nhóm hai: động từ tận cùng bằng âm hữu thanh hoặc nguyên âm, như design, improve, play. Đuôi ed đọc giống cuối từ played.", "show": "e2"},
        {"en": "designed, improved, played", "gap": True, "recap": False},
        {"say": "Nhóm ba: động từ tận cùng bằng âm tờ hoặc đờ, như invent, want, end. Lúc này đuôi ed thành một âm tiết riêng, giống cuối từ wanted.", "show": "e3"},
        {"en": "invented, wanted, ended", "gap": True, "recap": False},
        {"say": "Người Việt hay nuốt mất âm tiết này: invented nghe thành invent, và người nghe tưởng bạn đang nói ở hiện tại. Còn một chữ hay đọc sai: read ở quá khứ viết như cũ nhưng đọc là red."},
        {"en": "I read the whole book last night.", "vi": "Tối qua tôi đọc hết cả cuốn sách.", "gap": True},
        {"say": "Chỉ những động từ như invent, want, end mới thêm một âm tiết khi có đuôi ed. Các động từ khác giữ nguyên số âm tiết.", "show": "rule"},
    ]},
    {"kind": "scene", "visual": "picture_cards", "eyebrow": "Bản chất", "title": "Việc đã khép lại",
     "data": {"rows": USES, "rule": "Quá khứ đơn kể một việc người nói coi là đã khép lại, dù có nói lúc nào hay không."}, "lines": [
        {"say": "Cách dùng cốt lõi, thường gặp nhất của quá khứ đơn: kể một việc đã xảy ra và đã khép lại.", "show": "u1"},
        {"en": "My grandfather bought his first phone in 1998.", "vi": "Ông tôi mua chiếc điện thoại đầu tiên năm 1998.", "gap": True},
        {"say": "Câu không bắt buộc phải có trạng từ thời gian. Ông xây ngôi nhà này năm nào thì câu không nói, nhưng trong đầu người nói, việc đó thuộc về một lúc đã qua.", "show": "u2"},
        {"en": "My grandfather built this house.", "vi": "Ông tôi xây ngôi nhà này.", "gap": True},
        {"say": "Và kể cả khi người nói nhớ nhầm hay nói dối. Bạn về nhà lúc chín giờ, nhưng nói với bố mẹ là sáu giờ. Bạn trình bày điều đó như một việc đã xảy ra, nên vẫn dùng quá khứ đơn.", "show": "u3"},
        {"en": "I came home at six.", "vi": "Con về nhà lúc sáu giờ.", "gap": True},
        {"say": "Quá khứ đơn kể một việc người nói coi là đã khép lại, dù có nói lúc nào hay không.", "show": "rule"},
    ]},
    {"kind": "word", "headword": "invent", "lines": [{"say": "Năm động từ của buổi này đều hay dùng khi kể chuyện công nghệ, và mỗi từ cho bạn tập một cách đọc đuôi ed. Từ thứ nhất. Quá khứ là invented, đuôi ed thêm một âm tiết, giống wanted."}]},
    {"kind": "word", "headword": "design", "lines": [{"say": "Từ thứ hai. Quá khứ là designed, đuôi ed giống played."}]},
    {"kind": "word", "headword": "develop", "lines": [{"say": "Từ thứ ba. Quá khứ là developed, đuôi ed giống worked."}]},
    {"kind": "word", "headword": "improve", "lines": [{"say": "Từ thứ tư. Quá khứ là improved, đuôi ed giống played."}]},
    {"kind": "word", "headword": "replace", "lines": [{"say": "Từ cuối. Quá khứ là replaced, đuôi ed giống worked."}]},
    {"kind": "recap", "lines": [
        {"say": "Ba việc tối qua, một thì. Giờ nói lại các câu của buổi này. Nghe một câu, rồi nói to trong quãng nghỉ.", "show": "title"},
    ]},
    {"kind": "end", "next": "Tiếp theo: học thẻ và từ của buổi này, rồi làm bài.", "lines": [
        {"say": "Hết buổi một. Bạn học các thẻ và từ trong app, rồi làm bài. Buổi hai nói về ranh giới giữa quá khứ đơn và hiện tại hoàn thành.", "show": "title"},
    ]},
]

SITTING_2 = [
    {"kind": "title", "hook": "I have been there two years ago: câu này sai ở đâu?", "lines": [
        {"say": "Có người hỏi bạn đã đến Ý bao giờ chưa. Bạn trả lời như sau. Câu này sai ở đâu?", "show": "hook"},
        {"en": "I have been there two years ago."},
        {"say": "Buổi này vạch ranh giới giữa quá khứ đơn và hiện tại hoàn thành: khi nào phải đổi thì, và ba chữ since, in, for."},
    ]},
    {"kind": "scene", "visual": "tense_timeline", "eyebrow": "Nhắc lại và mở rộng", "title": "Mua rau: hai câu đáp đều đúng",
     "data": {"question": "Did you buy any vegetables for tonight?", "question_vi": "Bạn đã mua rau cho tối nay chưa?", "question_label": "Có người hỏi",
              "answers": VEG, "rule": "Quá khứ đơn: người nói biết lúc nào. Hiện tại hoàn thành: chỉ báo đã làm, lúc nào không quan trọng."}, "lines": [
        {"say": "Bạn đi chợ về, và người nhà hỏi."},
        {"en": "Did you buy any vegetables for tonight?", "vi": "Bạn đã mua rau cho tối nay chưa?", "gap": True, "show": "q", "recap": False},
        {"say": "Trên trục này, bên trái là quá khứ, vạch giữa là bây giờ.", "show": "axis"},
        {"say": "Câu đáp thứ nhất dùng quá khứ đơn. Bạn biết mình mua lúc nào: trên đường về.", "show": "a1"},
        {"en": "Yes, I bought some on the way home.", "vi": "Có, tôi mua trên đường về.", "gap": True},
        {"say": "Câu đáp thứ hai dùng hiện tại hoàn thành, cũng đúng.", "show": "a2"},
        {"say": "Có bạn giải thích: đáp bằng hiện tại hoàn thành nghĩa là bây giờ vẫn đang mua. Bạn đang đứng trong bếp, dùng phép thuật gì mà vẫn đang mua rau ở chợ? Việc mua đã xong. Đây là nhánh thứ hai của hiện tại hoàn thành: đã xong, và người nói không cần nói lúc nào."},
        {"en": "Yes, I have bought some.", "vi": "Rồi, tôi mua rồi.", "gap": True},
        {"say": "Để ý: câu hỏi dùng did, câu đáp vẫn được dùng have. Không có quy tắc nào bắt hỏi thì nào phải đáp thì đó. Quá khứ đơn: người nói biết lúc nào. Hiện tại hoàn thành: chỉ báo đã làm, còn lúc nào thì không quan trọng.", "show": "rule"},
    ]},
    {"kind": "scene", "visual": "chat_dialogue", "eyebrow": "Quy tắc đổi thì", "title": "Có mốc thời gian: quá khứ đơn",
     "data": {"names": {"A": "Bạn", "B": "Tôi"}, "turns": DIALOGUE, "rule": "Câu hỏi hay câu trả lời nêu một mốc thời gian đã qua: đổi sang quá khứ đơn."}, "lines": [
        {"say": "Một đoạn hội thoại bốn bước. Bước một: hỏi trải nghiệm, đã từng hay chưa. Đó là hiện tại hoàn thành.", "show": "k1"},
        {"en": "Have you ever been to Italy?", "vi": "Bạn đã đến Ý bao giờ chưa?", "gap": True},
        {"say": "Bước hai: đáp có hay chưa. Vẫn chưa ai nói lúc nào.", "show": "k2"},
        {"en": "Yes, I have.", "vi": "Rồi.", "gap": True, "recap": False},
        {"say": "Bước ba: người kia hỏi lúc nào. Câu hỏi có when, nên dùng quá khứ đơn.", "show": "k3"},
        {"en": "When did you go there?", "vi": "Bạn đi khi nào?", "gap": True},
        {"say": "Bước bốn: bạn kể chi tiết, có mốc thời gian. Đây cũng là câu trả lời cho câu hỏi đầu buổi: hai năm trước là một mốc đã qua, nên dùng quá khứ đơn.", "show": "k4"},
        {"en": "I went there two years ago.", "vi": "Tôi đi hai năm trước.", "gap": True},
        {"say": "Câu hỏi hay câu trả lời nêu một mốc thời gian đã qua thì đổi sang quá khứ đơn. Trong Speaking, câu đầu có thể xác nhận bằng hiện tại hoàn thành; phần kể chi tiết dùng quá khứ đơn.", "show": "rule"},
    ]},
    {"kind": "scene", "visual": "tense_timeline", "eyebrow": "Nhắc lại và mở rộng", "title": "since, in, for",
     "data": {"question": "I ... the piano ...", "question_vi": "bốn câu về việc học piano", "question_label": "Cùng một việc",
              "answers": PIANO, "rule": "since: vế chính thường chia hoàn thành. in + năm đã qua: quá khứ đơn. for: còn tiếp hay đã dừng mới quyết định."}, "lines": [
        {"say": "Bốn câu về cùng một việc: học piano. Chỉ khác nhau một chữ.", "show": "q"},
        {"say": "Câu một có since: bắt đầu năm 2003, bây giờ vẫn học. Vế chính có since thường chia thì hoàn thành.", "show": "axis"},
        {"en": "I have studied the piano since 2003.", "vi": "Tôi học piano từ năm 2003.", "gap": True, "show": "b1"},
        {"say": "Có bạn sẽ hỏi: hiện tại hoàn thành không nói lúc nào, sao câu một lại có since? Vì thì này có hai nhánh. Nhánh còn tiếp tới bây giờ đi được với since và for. Nhánh đã xong, như câu mua rau, thì không nêu lúc nào. Nêu một năm đã qua là phải đổi sang quá khứ đơn."},
        {"say": "Câu hai có in cộng một năm đã qua. Đó là một mốc, nên dùng quá khứ đơn.", "show": "b2"},
        {"en": "I studied the piano in 2003.", "vi": "Tôi học piano vào năm 2003.", "gap": True},
        {"say": "Câu ba và câu bốn cùng có for. For chỉ là một giới từ cho biết độ dài. Nếu bây giờ vẫn học, dùng hiện tại hoàn thành.", "show": "b3"},
        {"en": "I have studied the piano for two years.", "vi": "Tôi học piano được hai năm rồi.", "gap": True},
        {"say": "Nếu đã nghỉ, dùng quá khứ đơn, dù câu vẫn có for.", "show": "b4"},
        {"en": "I studied the piano for two years, then I stopped.", "vi": "Tôi học piano hai năm, rồi nghỉ.", "gap": True},
        {"say": "Riêng cụm sau nghĩa là hai năm tính tới bây giờ, nên thường đi với hiện tại hoàn thành."},
        {"en": "for the last two years", "vi": "trong hai năm qua", "gap": True, "recap": False},
        {"say": "Since: vế chính thường chia thì hoàn thành. In cộng một năm đã qua: quá khứ đơn. For: việc còn tiếp hay đã dừng mới quyết định.", "show": "rule"},
    ]},
    {"kind": "scene", "visual": "tense_timeline", "eyebrow": "Hai mẫu cần thuộc", "title": "The last time và It's the first time",
     "data": {"question": "lần cuối · lần đầu", "question_vi": "hai mẫu hay bị nhầm", "question_label": "Hai mẫu", "answers": TWO_PATTERNS, "rule": "Vế The last time chia quá khứ đơn. It's the first time đi với hiện tại hoàn thành."}, "lines": [
        {"say": "Hai mẫu câu rất hay bị nhầm với nhau.", "show": "q"},
        {"say": "Trên trục, quá khứ bên trái, bây giờ ở vạch giữa.", "show": "axis"},
        {"say": "Mẫu một: lần cuối. Vế này là một mốc đã qua nên chia quá khứ đơn; vế sau kể việc lúc đó, thường cũng là quá khứ đơn.", "show": "l1"},
        {"en": "The last time I saw Lan, she talked about changing jobs.", "vi": "Lần cuối tôi gặp Lan, cô ấy nói về chuyện đổi việc.", "gap": True},
        {"say": "Mẫu hai: lần đầu. Tính từ trước tới bây giờ, nên dùng hiện tại hoàn thành.", "show": "l2"},
        {"en": "It's the first time I have used this app.", "vi": "Đây là lần đầu tôi dùng ứng dụng này.", "gap": True},
        {"say": "Vế lần cuối chia quá khứ đơn. Mẫu lần đầu đi với hiện tại hoàn thành.", "show": "rule"},
    ]},
    {"kind": "scene", "visual": "fix_pairs", "eyebrow": "Lỗi thường gặp", "title": "Bốn lỗi, bốn cách sửa",
     "data": {"rows": TRAPS, "rule": "Sau did, didn't: nguyên thể. Có mốc đã qua: quá khứ đơn. Vế The last time: quá khứ đơn."}, "lines": [
        {"say": "Bốn lỗi hay gặp nhất của buổi hôm nay. Lỗi một: chia hai lần sau didn't.", "show": "e1"},
        {"en": "I didn't hear the phone.", "vi": "Tôi không nghe thấy điện thoại.", "gap": True},
        {"say": "Lỗi hai: giữ hiện tại hoàn thành khi đã có mốc thời gian.", "show": "e2"},
        {"en": "I went there two years ago.", "vi": "Tôi đi đến đó hai năm trước.", "gap": True},
        {"say": "Lỗi ba: hiện tại hoàn thành đi với in cộng một năm đã qua.", "show": "e3"},
        {"en": "I studied the piano in 2003.", "vi": "Tôi học piano vào năm 2003.", "gap": True, "recap": False},
        {"say": "Lỗi bốn: nhầm mẫu lần cuối với mẫu lần đầu.", "show": "e4"},
        {"en": "The last time I saw her, she looked tired.", "vi": "Lần cuối tôi gặp cô ấy, trông cô ấy mệt.", "gap": True},
        {"say": "Sau did và didn't là động từ nguyên thể. Có mốc thời gian đã qua: quá khứ đơn. Vế lần cuối: quá khứ đơn.", "show": "rule"},
    ]},
    {"kind": "word", "headword": "invention", "lines": [{"say": "Trước khi trả lời một câu Speaking, học năm danh từ về công nghệ. Từ thứ nhất là danh từ của invent ở buổi trước."}]},
    {"kind": "word", "headword": "device", "lines": [{"say": "Từ thứ hai: một vật được làm ra cho một việc cụ thể."}]},
    {"kind": "word", "headword": "engine", "lines": [{"say": "Từ thứ ba. Câu ví dụ là quá khứ đơn, phủ định."}]},
    {"kind": "word", "headword": "vehicle", "lines": [{"say": "Từ thứ tư: từ chung cho mọi loại xe. Âm ở giữa từ này thường không đọc."}]},
    {"kind": "word", "headword": "prototype", "lines": [{"say": "Từ cuối: bản làm thử đầu tiên. Từ này sẽ gặp lại trong bài đọc của tuần."}]},
    {"kind": "scene", "visual": "speaking_answer", "eyebrow": "IELTS Speaking Part 1", "title": "Kể bằng quá khứ đơn, nối tới bây giờ",
     "data": {"question": "When did you get your first mobile phone?", "question_vi": "Bạn có chiếc điện thoại đầu tiên khi nào?",
              "short": "In 2012.", "parts": ANSWER,
              "rule": "Kể việc đã qua bằng quá khứ đơn; câu nối tới bây giờ mới dùng hiện tại hoàn thành."}, "lines": [
        {"say": "Giám khảo hỏi bạn có chiếc điện thoại đầu tiên khi nào."},
        {"en": "When did you get your first mobile phone?", "show": "q"},
        {"say": "Chỉ nêu một mốc thời gian thì câu trả lời quá ngắn.", "show": "short"},
        {"say": "Câu một: trả lời thẳng, có mốc thời gian, nên dùng quá khứ đơn."},
        {"en": "I got my first mobile phone in 2012, when I was fourteen.", "vi": "Tôi có chiếc điện thoại đầu tiên năm 2012, năm mười bốn tuổi.", "gap": True, "show": "p1"},
        {"say": "Câu hai: ai mua, nhân dịp gì. Vẫn là quá khứ đơn."},
        {"en": "My parents bought it for my birthday.", "vi": "Bố mẹ mua cho tôi nhân sinh nhật.", "gap": True, "show": "p2"},
        {"say": "Câu ba: kể thêm về chiếc điện thoại đó."},
        {"en": "It was a simple device, but I used it every day.", "vi": "Đó là một thiết bị đơn giản, nhưng ngày nào tôi cũng dùng.", "gap": True, "show": "p3"},
        {"say": "Câu bốn: nối tới bây giờ, có since then, nên dùng hiện tại hoàn thành."},
        {"en": "I have changed phones three times since then.", "vi": "Từ đó tới giờ tôi đã đổi điện thoại ba lần.", "gap": True, "show": "p4"},
        {"say": "Kể việc đã qua bằng quá khứ đơn. Chỉ câu nối tới bây giờ mới dùng hiện tại hoàn thành. Hãy viết lại bốn câu này cho đúng với chính bạn.", "show": "rule"},
    ]},
    {"kind": "recap", "lines": [
        {"say": "Hỏi có hay chưa: hiện tại hoàn thành; nêu lúc nào: quá khứ đơn. Giờ nói lại các câu của buổi này. Nghe một câu, rồi nói to trong quãng nghỉ.", "show": "title"},
    ]},
    {"kind": "end", "next": "Tiếp theo: học thẻ và từ, làm bài, rồi buổi 3 để xếp câu, nghe chép và viết.", "lines": [
        {"say": "Hết phần giảng của ngày một. Bạn học các thẻ và từ trong app, làm bài, rồi sang buổi ba để xếp câu, nghe chép và viết về chiếc điện thoại đầu tiên của bạn.", "show": "title"},
    ]},
]

RUBRIC = [
    {"criterion_vi": "Đúng đề, nội dung là của chính bạn", "max": 1, "note_vi": "Fluency and coherence"},
    {"criterion_vi": "Kể việc đã qua bằng quá khứ đơn; chỉ câu nối tới bây giờ dùng hiện tại hoàn thành", "max": 2, "note_vi": "Grammatical range"},
    {"criterion_vi": "Dạng động từ đúng: V-ed và dạng bất quy tắc, didn't / did + nguyên thể, was / were", "max": 2, "note_vi": "Grammatical accuracy"},
]


def reshape(sessions: list[dict], exercise_ids: list[str], card_of: dict[str, int]) -> list[dict]:
    """Sitting 1 teaches cards 1-3 (forms, -ed, uses) with five verbs; sitting 2 cards 4-6 (the line with the
    present perfect, since / in / for, two fixed patterns) with five nouns; the production work (build, type,
    dictation, writing) is a third sitting without a lecture."""
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
    s1["title_vi"] = "Buổi 1 · công thức, đuôi -ed, việc đã khép lại"
    s2["title_vi"] = "Buổi 2 · ranh giới với hiện tại hoàn thành: since, in, for"
    s1["can_do_vi"] = "Sau buổi này bạn lập được câu quá khứ đơn ở ba dạng, đọc đúng đuôi -ed và kể được một chuỗi việc đã qua."
    s2["can_do_vi"] = "Sau buổi này bạn biết khi nào phải đổi sang quá khứ đơn, chọn đúng since, in, for, và kể được một câu Speaking về quá khứ."
    s3 = {
        "title_vi": "Buổi 3 · vận dụng: xếp câu, gõ, nghe chép, viết",
        "can_do_vi": "Sau buổi này bạn chọn đúng thì trong các câu có since, for, The last time, tự xếp và gõ đúng câu quá khứ đơn, nghe chép được câu có đuôi -ed và didn't, và viết vài câu về chính mình.",
        "use_vi": s1["use_vi"],
        "vocab": [],
        "check": moved,
    }
    assert set(s1["check"] + s2["check"] + moved) <= set(exercise_ids)
    return [s1, s2, s3] + rest

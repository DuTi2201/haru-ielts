"""Week 2 · Day 3 (build day 23): the past perfect and the past perfect continuous. Two lectures written by hand
(lesson_audio.build_authored_lecture) and the day's sittings reshaped around them. Same format as lecture_w2d2.py.

Sources: session 3 of the course, stages 3, 5 and 6 (docs/WEEK2_PLAN.md, day 3): had + V3 only to stress which
action came before another past one, with no need for before / after; the context rule ("never write a past
perfect sentence standing alone"), with the Jim dialogue; the overuse caught in exercise C (had, not had had; was,
got, had left; learned, not had learned; The last time with the past simple); the simple form for results,
quantities, experience with before and stative verbs, the continuous form for a stretch up to a past moment and for
a trace left at that moment (Before I saw Anna, I had run / had been running for two hours); stative verbs "not
normally" used in continuous forms; collocations (get ready, have / get lessons); pronunciation (breath /breθ/,
written, chose, ended). Book theory: It was the first time + past perfect; after one past perfect, the story goes
back to the past simple.
Corrections made before use (docs/WEEK2_PLAN.md, last section): the Jim dialogue's last line says when ("earlier");
"I had played football. But my mother came home." is not used; the continuous form is not said to need a stated
duration in every case (Her eyes were red because she had been crying).

Pronunciations: Oxford Learner's Dictionaries, British English, read 2026-11-25. A word without a checked
entry has none.
"""

PRON = {
    "launch": "/lɔːntʃ/",
    "save": "/seɪv/",
    "fail": "/feɪl/",
    "fix": "/fɪks/",
    "delete": "/dɪˈliːt/",
    "bug": "/bʌɡ/",
    "version": "/ˈvɜːʃn/",
    "backup": "/ˈbækʌp/",
    "feature": "/ˈfiːtʃə(r)/",
    "file": "/faɪl/",
}

NOTES = {
    "launch": "Quá khứ: launched, đuôi -ed đọc /t/. launch a product, launch an app.",
    "save": "Quá khứ: saved, đuôi -ed đọc /d/. save a file: lưu một tệp. Trái nghĩa trong buổi này: delete.",
    "fail": "Quá khứ: failed, đuôi -ed đọc /d/. Danh từ: failure.",
    "fix": "Quá khứ: fixed, đuôi -ed đọc /t/. fix a bug: sửa một lỗi phần mềm.",
    "delete": "Quá khứ: deleted, đuôi -ed thêm một âm tiết /ɪd/. delete a file.",
    "bug": "Nghĩa gốc là con bọ; trong phần mềm là một lỗi làm chương trình chạy sai.",
    "version": "the latest version: phiên bản mới nhất. Oxford ghi thêm cách đọc /ˈvɜːʒn/.",
    "backup": "make a backup: sao lưu. Động từ viết tách: back up your files.",
    "feature": "a new feature: một tính năng mới. Cũng là động từ: có, làm nổi bật.",
    "file": "open, save, delete a file: mở, lưu, xóa một tệp.",
}

S1_WORDS = ["launch", "save", "fail", "fix", "delete"]
S2_WORDS = ["bug", "version", "backup", "feature", "file"]

STATION = [
    {"key": "t1", "icon": "clock", "at": "pointat", "tense": "Hai vế quá khứ đơn · cùng lúc", "en": "When I got to the station, the train left.", "vi": "Tàu chạy đúng lúc tôi tới."},
    {"key": "t2", "icon": "clock", "at": "before", "tense": "had + V3 · xảy ra trước", "en": "When I got to the station, the train had left.", "vi": "Tôi tới thì tàu đã chạy mất."},
]

JIM = [
    {"key": "d1", "head": "Hỏi", "en": "What did you do when you were home?", "vi": "Hỏi về một quãng đã qua."},
    {"key": "d2", "head": "Tạo mốc · quá khứ đơn", "en": "I met Jim.", "vi": "Mốc để dựa vào."},
    {"key": "d3", "head": "Hỏi thêm", "en": "Did you do anything else?", "vi": "Còn gì nữa không?"},
    {"key": "d4", "head": "Trước mốc · had + V3", "en": "Oh, I had bought a new phone earlier.", "vi": "Việc này xảy ra trước lúc gặp Jim."},
]

LETTER = [
    {"key": "s1", "icon": "clock", "head": "Kết quả · quá khứ đơn", "en": "I was late for the lesson", "vi": "Việc được kể lại."},
    {"key": "s2", "icon": "suitcase", "head": "Lùi về trước · had + V3", "en": "because when I got there, I realised I had left my judo suit at home.", "vi": "Để quên đồ xảy ra trước lúc đến nơi."},
    {"key": "s3", "icon": "house", "head": "Kể tiếp · quá khứ đơn", "en": "So I went all the way home.", "vi": "Câu chuyện đi tiếp."},
]

TWO_USES = [
    {"key": "w1", "icon": "clock", "at": "upto", "tense": "Kéo dài tới mốc", "en": "We had been waiting for over an hour when the bus finally came.", "vi": "Thời lượng chờ, tới lúc xe tới."},
    {"key": "w2", "icon": "face", "at": "ptrace", "tense": "Vừa dừng, còn dấu vết", "en": "Her eyes were red because she had been crying.", "vi": "Việc vừa dừng; đôi mắt đỏ là dấu vết."},
]

NGA = [
    {"key": "n1", "icon": "runner", "at": "before", "tense": "had + V3 · bản thân việc", "en": "Before I met Anna, I had run five kilometres.", "vi": "Nhấn việc đã làm và kết quả."},
    {"key": "n2", "icon": "runner", "at": "upto", "tense": "had been + V-ing · quá trình", "en": "Before I met Anna, I had been running for two hours.", "vi": "Nhấn thời lượng kéo dài."},
]

CHOOSE = [
    {"key": "c1", "head": "Kết quả, số lượng · đơn", "en": "By 2020, the company had sold a million phones.", "vi": "Con số đã đạt được."},
    {"key": "c2", "head": "Trải nghiệm · đơn", "en": "I had never used a smartphone before I went to university.", "vi": "Đã từng hay chưa từng, thường có before."},
    {"key": "c3", "head": "Động từ trạng thái · đơn", "en": "I had known Lan for ten years when we started the company.", "vi": "know, own, believe: thường không dùng tiếp diễn."},
    {"key": "c4", "head": "Thời lượng · tiếp diễn", "en": "She had been working there for ten years when she retired.", "vi": "Nhấn quãng thời gian kéo dài."},
    {"key": "c5", "head": "Dấu vết · tiếp diễn", "en": "The road was wet because it had been raining.", "vi": "Việc vừa dừng, còn dấu vết lúc đó."},
]

ANSWER = [
    {"key": "q1", "role": "Dựng cảnh", "tense": "Tiếp diễn + quá khứ đơn", "en": "Last year I was working on a group project when my laptop suddenly crashed.", "vi": "Năm ngoái tôi đang làm dự án nhóm thì laptop bỗng bị sập."},
    {"key": "q2", "role": "Việc trước đó", "tense": "had been + V-ing, had + V3", "en": "I had been writing the report for three hours, and I hadn't saved it.", "vi": "Tôi đã viết báo cáo suốt ba tiếng, và chưa lưu lại."},
    {"key": "q3", "role": "May mắn", "tense": "had + V3", "en": "Luckily, my friend had made a backup the day before, so we didn't lose everything.", "vi": "May mà hôm trước bạn tôi đã sao lưu, nên chúng tôi không mất hết."},
    {"key": "q4", "role": "Tới bây giờ", "tense": "Hiện tại hoàn thành", "en": "Since then, I've always saved my work every few minutes.", "vi": "Từ đó tới giờ, cứ vài phút tôi lại lưu bài."},
]

SITTING_1 = [
    {"kind": "title", "hook": "Bạn tới ga thì tàu đã chạy mất: việc nào xảy ra trước?", "lines": [
        {"say": "Bạn tới ga, nhưng tàu đã chạy mất. Hai việc trong quá khứ. Làm sao để người nghe biết việc nào xảy ra trước?", "show": "hook"},
        {"say": "Hai hôm trước ta kể lần lượt bằng quá khứ đơn; hôm qua ta phóng to vào bên trong một khoảng. Hôm nay ta lùi về trước một mốc quá khứ: thì quá khứ hoàn thành."},
    ]},
    {"kind": "scene", "visual": "tense_timeline", "eyebrow": "Thí nghiệm", "title": "Cùng lúc hay xảy ra trước",
     "data": {"question": "When I got to the station, ...", "question_vi": "Khi tôi tới ga, ...", "question_label": "Cùng một mốc",
              "answers": STATION, "rule": "Việc xảy ra trước chia had + V3; việc làm mốc chia quá khứ đơn."}, "lines": [
        {"say": "Hai câu chỉ khác nhau một chữ had.", "show": "q"},
        {"say": "Quá khứ bên trái, bây giờ ở vạch giữa.", "show": "axis"},
        {"say": "Câu một: hai vế đều là quá khứ đơn. Tàu chạy đúng lúc tôi tới, như thể tôi kịp nhìn thấy nó lăn bánh.", "show": "t1"},
        {"en": "When I got to the station, the train left.", "vi": "Khi tôi tới ga, tàu chạy.", "gap": True},
        {"say": "Câu hai: vế sau có had. Tàu chạy trước lúc tôi tới. Tôi tới nơi thì sân ga đã trống.", "show": "t2"},
        {"en": "When I got to the station, the train had left.", "vi": "Khi tôi tới ga thì tàu đã chạy mất.", "gap": True},
        {"say": "Thì quá khứ hoàn thành chỉ làm một việc: nhấn việc nào xảy ra trước một việc quá khứ khác. Việc xảy ra trước chia had cộng quá khứ phân từ; việc làm mốc chia quá khứ đơn.", "show": "rule"},
    ]},
    {"kind": "scene", "visual": "sentence_forms", "eyebrow": "Công thức", "title": "Ba dạng câu của quá khứ hoàn thành",
     "data": {"rows": [
                  {"key": "aff", "label": "Khẳng định", "parts": ["The train", "had left."], "hi": [1], "vi": "Tàu đã chạy mất."},
                  {"key": "neg", "label": "Phủ định", "parts": ["I", "hadn't seen", "the film."], "hi": [1], "vi": "Tôi chưa xem bộ phim đó."},
                  {"key": "qst", "label": "Câu hỏi", "parts": ["Had", "you met", "him before the party?"], "hi": [0, 1], "vi": "Trước bữa tiệc bạn đã gặp anh ấy chưa?"},
              ],
              "persons": [{"who": "I · you · we · they", "verb": "had left"}, {"who": "he · she · it", "verb": "had left"}],
              "persons_plain": True,
              "spelling_title": "V3 bất quy tắc hay gặp",
              "spelling": [["write", "written"], ["go", "gone"], ["see", "seen"], ["eat", "eaten"], ["leave", "left"], ["fly", "flown"]],
              "short": ["Yes, I had.", "No, I hadn't."],
              "rule": "had cộng V3, mọi ngôi như nhau."}, "lines": [
        {"say": "Công thức dễ nhất trong các thì quá khứ: had cộng quá khứ phân từ, và mọi ngôi dùng cùng một dạng.", "show": "persons"},
        {"en": "The train had left.", "vi": "Tàu đã chạy mất.", "gap": True, "show": "aff"},
        {"say": "Phủ định: hadn't cộng quá khứ phân từ."},
        {"en": "I hadn't seen the film.", "vi": "Tôi chưa xem bộ phim đó.", "gap": True, "show": "neg"},
        {"say": "Câu hỏi: đưa had lên trước chủ ngữ. Trả lời ngắn thì dùng lại had.", "show": "short"},
        {"en": "Had you met him before the party?", "vi": "Trước bữa tiệc bạn đã gặp anh ấy chưa?", "gap": True, "show": "qst"},
        {"say": "Điểm khó là quá khứ phân từ của động từ bất quy tắc. Write thành written, đọc với âm i ngắn, không đọc như write. Go thành gone, see thành seen, fly thành flown.", "show": "spelling"},
        {"say": "Khi nói, had thường rút gọn thành một âm rất nhẹ sau chủ ngữ. Nghe kỹ âm này trong bài nghe. Công thức: had cộng quá khứ phân từ, mọi ngôi như nhau.", "show": "rule"},
    ]},
    {"kind": "scene", "visual": "ref_table", "eyebrow": "Quy tắc bối cảnh", "title": "Luôn có một mốc quá khứ đơn",
     "data": {"cols": ["Bước", "Câu"], "rows": JIM, "rule": "Không viết một câu had + V3 đứng một mình: phải có một mốc quá khứ đơn làm điểm tựa."}, "lines": [
        {"say": "Thì này cần một điểm tựa. Một đoạn hội thoại bốn bước. Bước một: hỏi về một quãng đã qua.", "show": "d1"},
        {"en": "What did you do when you were home?", "vi": "Hồi ở nhà bạn đã làm gì?", "gap": True, "recap": False},
        {"say": "Bước hai: trả lời bằng quá khứ đơn. Câu này tạo ra một mốc.", "show": "d2"},
        {"en": "I met Jim.", "vi": "Tôi gặp Jim.", "gap": True},
        {"say": "Bước ba: người kia hỏi thêm.", "show": "d3"},
        {"en": "Did you do anything else?", "vi": "Bạn còn làm gì nữa không?", "gap": True, "recap": False},
        {"say": "Bước bốn: kể một việc xảy ra trước lúc gặp Jim. Không cần nói thêm là trước khi gặp Jim, vì mốc đã có ở câu trước.", "show": "d4"},
        {"en": "Oh, I had bought a new phone earlier.", "vi": "À, trước đó tôi đã mua một chiếc điện thoại mới.", "gap": True},
        {"say": "Ngược lại, khi câu đã có before hay after, thứ tự đã rõ, nên quá khứ đơn thường cũng đủ. Không viết một câu had cộng quá khứ phân từ đứng một mình: phải có một mốc quá khứ đơn làm điểm tựa.", "show": "rule"},
    ]},
    {"kind": "scene", "visual": "picture_cards", "eyebrow": "Không lạm dụng", "title": "Chỉ một việc lùi về trước",
     "data": {"rows": LETTER, "rule": "Chỉ việc xảy ra trước một mốc mới chia had + V3; kể tiếp thì trở lại quá khứ đơn."}, "lines": [
        {"say": "Một bạn kể về buổi học judo đầu tiên. Câu một: bị muộn. Đây là việc được kể lại, nên dùng quá khứ đơn.", "show": "s1"},
        {"en": "I was late for the lesson", "vi": "Tôi đến buổi học muộn", "gap": True, "recap": False},
        {"say": "Câu hai: nguyên nhân xảy ra trước, là để quên bộ đồ ở nhà. Chỉ việc này mới lùi về trước, nên chỉ nó chia had cộng quá khứ phân từ.", "show": "s2"},
        {"en": "because when I got there, I realised I had left my judo suit at home.", "vi": "vì khi tới nơi, tôi nhận ra mình đã để quên bộ đồ judo ở nhà.", "gap": True},
        {"say": "Câu ba: câu chuyện đi tiếp, trở lại quá khứ đơn.", "show": "s3"},
        {"en": "So I went all the way home.", "vi": "Thế là tôi đi về tận nhà.", "gap": True},
        {"say": "Lỗi hay gặp là thấy chuyện quá khứ thì dùng had ở mọi nơi. Buổi học hôm qua không xảy ra trước việc nào, nên câu đúng là quá khứ đơn."},
        {"en": "I had my first judo lesson yesterday.", "vi": "Hôm qua tôi học buổi judo đầu tiên.", "gap": True},
        {"say": "Còn một mẫu cần thuộc. Hai hôm trước bạn học mẫu lần đầu, đi với hiện tại hoàn thành. Khi lùi cả câu về quá khứ, mẫu này đi với had cộng quá khứ phân từ."},
        {"en": "It was the first time I had used a smartwatch.", "vi": "Đó là lần đầu tôi dùng đồng hồ thông minh.", "gap": True},
        {"say": "Chỉ việc xảy ra trước một mốc mới chia had cộng quá khứ phân từ; kể tiếp thì trở lại quá khứ đơn.", "show": "rule"},
    ]},
    {"kind": "word", "headword": "launch", "lines": [{"say": "Năm động từ của buổi này kể đời của một sản phẩm công nghệ và dữ liệu của bạn: ra mắt, lưu, thất bại, sửa, xóa. Từ thứ nhất. Quá khứ là launched, đuôi ed giống worked."}]},
    {"kind": "word", "headword": "save", "lines": [{"say": "Từ thứ hai. Quá khứ là saved, đuôi ed giống played. Câu ví dụ có hadn't cộng quá khứ phân từ."}]},
    {"kind": "word", "headword": "fail", "lines": [{"say": "Từ thứ ba. Quá khứ là failed, đuôi ed giống played."}]},
    {"kind": "word", "headword": "fix", "lines": [{"say": "Từ thứ tư. Quá khứ là fixed, đuôi ed giống worked."}]},
    {"kind": "word", "headword": "delete", "lines": [{"say": "Từ cuối. Quá khứ là deleted, thêm một âm tiết."}]},
    {"kind": "recap", "lines": [
        {"say": "Giờ nói lại các câu của buổi này. Nghe một câu, rồi nói to trong quãng nghỉ.", "show": "title"},
    ]},
    {"kind": "end", "next": "Tiếp theo: học thẻ và từ của buổi này, rồi làm bài.", "lines": [
        {"say": "Hết buổi một. Bạn học các thẻ và từ trong app, rồi làm bài. Buổi hai học dạng tiếp diễn của thì này, và cách chọn giữa hai dạng.", "show": "title"},
    ]},
]

SITTING_2 = [
    {"kind": "title", "hook": "had run hay had been running: hai câu khác nhau ở đâu?", "lines": [
        {"say": "Có hai câu kể về việc trước khi gặp Anna. Nghe rồi đoán: hai câu khác nhau ở đâu?", "show": "hook"},
        {"en": "Before I met Anna, I had run five kilometres."},
        {"en": "Before I met Anna, I had been running for two hours."},
        {"say": "Buổi này học công thức và hai cách dùng của thì quá khứ hoàn thành tiếp diễn, rồi cách chọn giữa dạng đơn và dạng tiếp diễn."},
    ]},
    {"kind": "scene", "visual": "sentence_forms", "eyebrow": "Công thức", "title": "Ba dạng câu của quá khứ hoàn thành tiếp diễn",
     "data": {"rows": [
                  {"key": "aff", "label": "Khẳng định", "parts": ["We", "had been waiting", "for an hour."], "hi": [1], "vi": "Chúng tôi đã chờ được một tiếng."},
                  {"key": "neg", "label": "Phủ định", "parts": ["She", "hadn't been sleeping", "well."], "hi": [1], "vi": "Dạo đó cô ấy ngủ không ngon."},
                  {"key": "qst", "label": "Câu hỏi", "parts": ["How long", "had you been waiting?"], "hi": [1], "vi": "Bạn đã chờ bao lâu rồi?"},
              ],
              "persons": [{"who": "I · you · we · they", "verb": "had been waiting"}, {"who": "he · she · it", "verb": "had been waiting"}],
              "persons_plain": True,
              "short": ["Yes, I had.", "No, I hadn't."],
              "rule": "had been cộng động từ thêm đuôi ing, mọi ngôi như nhau."}, "lines": [
        {"say": "Công thức có ba phần: had, been, rồi động từ thêm đuôi ing. Mọi ngôi như nhau.", "show": "persons"},
        {"en": "We had been waiting for an hour.", "vi": "Chúng tôi đã chờ được một tiếng.", "gap": True, "show": "aff"},
        {"say": "Phủ định: hadn't been."},
        {"en": "She hadn't been sleeping well.", "vi": "Dạo đó cô ấy ngủ không ngon.", "gap": True, "show": "neg"},
        {"say": "Câu hỏi thường gặp nhất bắt đầu bằng how long. Trả lời ngắn vẫn dùng had.", "show": "short"},
        {"en": "How long had you been waiting?", "vi": "Bạn đã chờ bao lâu rồi?", "gap": True, "show": "qst"},
        {"say": "Đây là thì có nhiều chữ nhất, nhưng khi nói, had been đọc lướt rất nhanh. Công thức: had been cộng động từ thêm đuôi ing, mọi ngôi như nhau.", "show": "rule"},
    ]},
    {"kind": "scene", "visual": "tense_timeline", "eyebrow": "Bản chất", "title": "Hai cách dùng",
     "data": {"question": "had been + V-ing", "question_vi": "trước một mốc quá khứ", "question_label": "Một công thức",
              "answers": TWO_USES, "rule": "Kéo dài tới một mốc quá khứ, hoặc vừa dừng trước mốc và còn dấu vết."}, "lines": [
        {"say": "Thì này có hai cách dùng, cả hai đều nhìn về một mốc trong quá khứ.", "show": "q"},
        {"say": "Mốc nằm bên trái vạch bây giờ.", "show": "axis"},
        {"say": "Cách dùng thứ nhất: một việc kéo dài tới mốc đó. Câu thường có for cộng một khoảng thời gian.", "show": "w1"},
        {"en": "We had been waiting for over an hour when the bus finally came.", "vi": "Chúng tôi đã chờ hơn một tiếng thì xe buýt mới tới.", "gap": True},
        {"say": "Cách dùng thứ hai: việc vừa dừng ngay trước mốc, và để lại dấu vết lúc đó. Câu này không cần nói bao lâu.", "show": "w2"},
        {"en": "Her eyes were red because she had been crying.", "vi": "Mắt cô ấy đỏ vì cô ấy vừa khóc.", "gap": True},
        {"say": "Một câu tương tự với chữ hay đọc sai: hết hơi. Hơi thở ở đây là danh từ breath, đọc ngắn, kết thúc bằng âm đầu lưỡi giữa hai hàm răng; khác động từ breathe."},
        {"en": "I was out of breath because I had been running.", "vi": "Tôi hết hơi vì vừa chạy.", "gap": True},
        {"say": "Kéo dài tới một mốc quá khứ, hoặc vừa dừng trước mốc và còn dấu vết.", "show": "rule"},
    ]},
    {"kind": "scene", "visual": "tense_timeline", "eyebrow": "So sánh", "title": "Bản thân việc hay quá trình",
     "data": {"question": "Before I met Anna, ...", "question_vi": "Trước khi gặp Anna, ...", "question_label": "Câu hỏi đầu buổi",
              "answers": NGA, "rule": "had + V3 nhấn bản thân việc và kết quả. had been + V-ing nhấn quá trình kéo dài."}, "lines": [
        {"say": "Quay lại hai câu đầu buổi.", "show": "q"},
        {"say": "Mốc là lúc gặp Anna.", "show": "axis"},
        {"say": "Câu một: had cộng quá khứ phân từ. Nhấn bản thân việc chạy và kết quả: năm cây số.", "show": "n1"},
        {"en": "Before I met Anna, I had run five kilometres.", "vi": "Trước khi gặp Anna, tôi đã chạy năm cây số.", "gap": True},
        {"say": "Câu hai: had been cộng đuôi ing. Nhấn quá trình kéo dài: suốt hai tiếng.", "show": "n2"},
        {"en": "Before I met Anna, I had been running for two hours.", "vi": "Trước khi gặp Anna, tôi đã chạy suốt hai tiếng.", "gap": True},
        {"say": "Dạng đơn nhấn bản thân việc và kết quả. Dạng tiếp diễn nhấn quá trình kéo dài.", "show": "rule"},
    ]},
    {"kind": "scene", "visual": "ref_table", "eyebrow": "Cách chọn", "title": "Năm trường hợp",
     "data": {"rows": CHOOSE, "rule": "Kết quả, trải nghiệm, trạng thái: had + V3. Thời lượng, dấu vết: had been + V-ing."}, "lines": [
        {"say": "Khi làm bài, có năm trường hợp. Ba trường hợp đầu chọn dạng đơn. Một: có kết quả hay con số.", "show": "c1"},
        {"en": "By 2020, the company had sold a million phones.", "vi": "Đến năm 2020, công ty đã bán được một triệu chiếc điện thoại.", "gap": True},
        {"say": "Hai: kể trải nghiệm, đã từng hay chưa từng, thường có before.", "show": "c2"},
        {"en": "I had never used a smartphone before I went to university.", "vi": "Trước khi vào đại học, tôi chưa từng dùng điện thoại thông minh.", "gap": True},
        {"say": "Ba: động từ trạng thái như know. Động từ trạng thái thường không dùng ở thì tiếp diễn. Đó là xu hướng, không phải lệnh cấm tuyệt đối, nhưng bài thi chọn dạng đơn.", "show": "c3"},
        {"en": "I had known Lan for ten years when we started the company.", "vi": "Lúc chúng tôi mở công ty, tôi đã quen Lan được mười năm.", "gap": True},
        {"say": "Hai trường hợp cuối chọn dạng tiếp diễn. Bốn: nhấn thời lượng kéo dài.", "show": "c4"},
        {"en": "She had been working there for ten years when she retired.", "vi": "Bà ấy đã làm ở đó mười năm thì nghỉ hưu.", "gap": True},
        {"say": "Năm: dấu vết lúc đó.", "show": "c5"},
        {"en": "The road was wet because it had been raining.", "vi": "Mặt đường ướt vì trời vừa mưa.", "gap": True},
        {"say": "Kết quả, trải nghiệm, trạng thái: had cộng quá khứ phân từ. Thời lượng, dấu vết: had been cộng đuôi ing.", "show": "rule"},
    ]},
    {"kind": "word", "headword": "bug", "lines": [{"say": "Trước khi kể một câu chuyện, học năm danh từ của đời sống số. Từ thứ nhất: nghĩa gốc là con bọ, trong phần mềm là một lỗi."}]},
    {"kind": "word", "headword": "version", "lines": [{"say": "Từ thứ hai: phiên bản."}]},
    {"kind": "word", "headword": "backup", "lines": [{"say": "Từ thứ ba: bản sao lưu. Câu ví dụ có had cộng quá khứ phân từ."}]},
    {"kind": "word", "headword": "feature", "lines": [{"say": "Từ thứ tư: tính năng."}]},
    {"kind": "word", "headword": "file", "lines": [{"say": "Từ cuối: tệp."}]},
    {"kind": "scene", "visual": "speaking_answer", "eyebrow": "IELTS Speaking Part 2", "title": "Kể chuyện bằng bốn thì quá khứ",
     "data": {"question": "Describe a time when you lost some work on a computer or phone.", "question_vi": "Kể về một lần bạn mất dữ liệu trên máy tính hoặc điện thoại.",
              "short": "My laptop crashed.", "parts": ANSWER,
              "rule": "Việc chính: quá khứ đơn. Cảnh: tiếp diễn. Việc trước đó: had + V3 hoặc had been + V-ing."}, "lines": [
        {"say": "Đề Part 2: kể về một lần bạn mất dữ liệu trên máy tính hoặc điện thoại."},
        {"en": "Describe a time when you lost some work on a computer or phone.", "show": "q"},
        {"say": "Chỉ nói máy bị sập thì câu chuyện chưa có gì.", "show": "short"},
        {"say": "Câu một: dựng cảnh bằng thì tiếp diễn, rồi việc bất ngờ bằng quá khứ đơn."},
        {"en": "Last year I was working on a group project when my laptop suddenly crashed.", "vi": "Năm ngoái tôi đang làm dự án nhóm thì laptop bỗng bị sập.", "gap": True, "show": "q1"},
        {"say": "Câu hai: lùi về trước mốc đó. Đã viết bao lâu: had been cộng đuôi ing. Chưa lưu: hadn't cộng quá khứ phân từ."},
        {"en": "I had been writing the report for three hours, and I hadn't saved it.", "vi": "Tôi đã viết báo cáo suốt ba tiếng, và chưa lưu lại.", "gap": True, "show": "q2"},
        {"say": "Câu ba: một việc may mắn đã xảy ra từ hôm trước: had cộng quá khứ phân từ."},
        {"en": "Luckily, my friend had made a backup the day before, so we didn't lose everything.", "vi": "May mà hôm trước bạn tôi đã sao lưu, nên chúng tôi không mất hết.", "gap": True, "show": "q3"},
        {"say": "Câu bốn: nối tới bây giờ bằng hiện tại hoàn thành."},
        {"en": "Since then, I've always saved my work every few minutes.", "vi": "Từ đó tới giờ, cứ vài phút tôi lại lưu bài.", "gap": True, "show": "q4"},
        {"say": "Việc chính dùng quá khứ đơn, cảnh dùng thì tiếp diễn, việc xảy ra trước dùng had cộng quá khứ phân từ hoặc had been cộng đuôi ing. Hãy viết lại bốn câu này cho đúng với chuyện của chính bạn.", "show": "rule"},
    ]},
    {"kind": "recap", "lines": [
        {"say": "Giờ nói lại các câu của buổi này. Nghe một câu, rồi nói to trong quãng nghỉ.", "show": "title"},
    ]},
    {"kind": "end", "next": "Tiếp theo: học thẻ và từ, làm bài, rồi buổi 3 và hai bài luyện theo sách.", "lines": [
        {"say": "Hết phần giảng của ngày ba. Bạn học các thẻ và từ trong app, làm bài, rồi sang buổi ba để xếp câu, nghe chép và kể chuyện của chính bạn. Cuối ngày có hai bài luyện theo sách: một lá thư mười sáu chỗ trống, và mười câu chọn giữa hai dạng của thì này.", "show": "title"},
    ]},
]

RUBRIC = [
    {"criterion_vi": "Đúng đề: có việc chính, việc xảy ra trước đó và kết quả", "max": 1, "note_vi": "Task response"},
    {"criterion_vi": "Việc xảy ra trước dùng had + V3 hoặc had been + V-ing, dựa vào một mốc quá khứ đơn", "max": 2, "note_vi": "Grammatical range"},
    {"criterion_vi": "Dạng động từ đúng: had + V3, had been + V-ing, V2 và V3 bất quy tắc", "max": 2, "note_vi": "Grammatical accuracy"},
]

CAP = 7  # a lecture sitting holds at most seven questions; the rest open sitting 3


def reshape(sessions: list[dict], exercise_ids: list[str], card_of: dict[str, int]) -> list[dict]:
    """Sitting 1 teaches cards 1-3 (the past perfect: form and meaning, the context rule, no overuse) with five
    verbs; sitting 2 cards 4-5 (the past perfect continuous, and choosing between the two forms) with five nouns;
    the production work is a third sitting without a lecture. The book's exercises follow as their own sittings."""
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
            return ts[:1] + [i for i in mine if i[5] != "T"] + ts[1:]
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
    s2["check"], spill2 = pick(range(3, len(pats)))
    moved = spill1 + spill2 + [i for i in allcheck if i not in quiz]
    s1["lecture"], s2["lecture"] = SITTING_1, SITTING_2
    s1["title_vi"] = "Buổi 1 · quá khứ hoàn thành: việc xảy ra trước, quy tắc bối cảnh"
    s2["title_vi"] = "Buổi 2 · quá khứ hoàn thành tiếp diễn, chọn dạng đơn hay tiếp diễn"
    s1["can_do_vi"] = "Sau buổi này bạn lập được câu quá khứ hoàn thành, nhấn được việc xảy ra trước, luôn dựa vào một mốc quá khứ đơn và không lạm dụng had."
    s2["can_do_vi"] = "Sau buổi này bạn lập được câu quá khứ hoàn thành tiếp diễn, chọn đúng giữa dạng đơn và dạng tiếp diễn, và kể được một câu chuyện Speaking bằng bốn thì quá khứ."
    s3 = {
        "title_vi": "Buổi 3 · vận dụng: xếp câu, gõ, nghe chép, kể chuyện",
        "can_do_vi": "Sau buổi này bạn chọn đúng giữa had + V3 và had been + V-ing, tự xếp và gõ đúng câu, nghe chép được câu có had và had been, và kể một chuyện của chính mình.",
        "use_vi": s1["use_vi"],
        "vocab": [],
        "check": moved,
    }
    assert set(s1["check"] + s2["check"] + moved) <= set(exercise_ids)
    return [s1, s2, s3] + rest

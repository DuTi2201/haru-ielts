"""G1 · Day 1: the two lectures written by hand (lesson_audio.build_authored_lecture), and the
day's sittings reshaped around them.

Why by hand: the fixed template reads a lesson's fields in a set order (word, meaning, pattern,
usage, example), which is a summary. The teacher's lesson is an enquiry: a question, an experiment
the learner runs, the conclusion in the teacher's own words, then practice. Every claim and example
below is from his week-1 material (the orange sentence in five boxes, dropping the adverb, the
mother's exaggeration, the lie, the four answers to one question, do/does); nothing is put in his
mouth that he did not say. His two quoted sentences are verbatim.

Format: a list of slides; each has "lines" said while it is up. {"say": …} is Vietnamese
narration, {"en": …} an English sentence read by the English voice ("gap": True leaves the silence
to repeat it in and puts it in the recap). "show" names the piece of the picture the line brings in.

Pronunciations: Oxford Advanced Learner's Dictionary (oxfordlearnersdictionaries.com), British
English, read 2026-11-11. A word without a checked entry has none (never typed from memory).
"""

# headword -> transcription, only those checked against the dictionary entry
PRON = {
    "habit": "/ˈhæbɪt/",
    "permanent": "/ˈpɜːmənənt/",
    "frequency": "/ˈfriːkwənsi/",
    "emphasise": "/ˈemfəsaɪz/",
}

BOXES = [
    {"key": "t1", "en": "Habits", "vi": "Thói quen"},
    {"key": "t2", "en": "Frequency", "vi": "Tần suất"},
    {"key": "t3", "en": "Permanent situations", "vi": "Lâu dài"},
    {"key": "t4", "en": "States", "vi": "Trạng thái"},
    {"key": "t5", "en": "Facts", "vi": "Sự thật"},
]

USES = [
    {"key": "u1", "head": "1. Hành động lặp lại", "en": "Toby walks to work.", "vi": "Gộp thói quen và tần suất."},
    {"key": "u2", "head": "2. Nói quá, than phiền", "en": "You don't visit me at all!", "vi": "Việc vẫn xảy ra, nhưng nói như không có."},
    {"key": "u3", "head": "3. Tình huống lâu dài", "en": "Carlo works in a travel agent's.", "vi": "Lâu dài chỉ là tương đối."},
    {"key": "u4", "head": "4. Trạng thái, ý kiến", "en": "Do you believe in God?", "vi": "Hỏi thì này, đáp không buộc thì này."},
    {"key": "u5", "head": "5. Sự thật theo người nói", "en": "Poland is in the European Union.", "vi": "Kể cả khi người nói nói dối."},
    {"key": "u6", "head": "Thêm: chỉ đường, hướng dẫn", "en": "You go down to the traffic lights, then you turn left.", "vi": "IELTS Grammar 6.5+."},
    {"key": "u7", "head": "Thêm: kể cốt truyện", "en": "In the film, the tea lady falls in love with the Prime Minister.", "vi": "IELTS Grammar 6.5+."},
]

FREQ = [
    {"key": "f1", "head": "100% · always", "en": "She is always late.", "vi": "Cô ấy lúc nào cũng muộn."},
    {"key": "f2", "head": "~90% · usually, normally, generally", "en": "I usually walk to school.", "vi": "Tôi thường đi bộ đến trường."},
    {"key": "f3", "head": "~70% · often, frequently", "en": "We often eat out.", "vi": "Chúng tôi hay ăn ngoài."},
    {"key": "f4", "head": "~50% · sometimes", "en": "Sometimes I cycle.", "vi": "Thỉnh thoảng tôi đạp xe."},
    {"key": "f5", "head": "~20% · occasionally", "en": "I occasionally go to the cinema.", "vi": "Tôi thỉnh thoảng mới đi xem phim."},
    {"key": "f6", "head": "~10% · rarely, seldom, hardly ever", "en": "I hardly ever get up before seven.", "vi": "Tôi gần như không dậy trước bảy giờ."},
    {"key": "f7", "head": "0% · never", "en": "He never eats meat.", "vi": "Anh ấy không bao giờ ăn thịt."},
]

POSITION = [
    {"key": "p1", "head": "Sau be", "en": "She is always late.", "vi": "be đứng trước, trạng từ theo sau."},
    {"key": "p2", "head": "Trước động từ thường", "en": "I usually walk to school.", "vi": "Trạng từ nằm giữa chủ ngữ và động từ."},
    {"key": "p3", "head": "Sau don't / doesn't", "en": "I don't often eat out.", "vi": "Trạng từ nằm sau trợ từ."},
    {"key": "p4", "head": "Đầu câu (usually, often, sometimes)", "en": "Sometimes I cycle to work.", "vi": "Đứng đầu câu để nhấn."},
    {"key": "p5", "head": "never, hardly ever đã là phủ định", "en": "I never go there.", "vi": "Không nói: I don't never go."},
]

WHEN = [
    {"key": "w1", "head": "at + giờ", "en": "I get up at half past six.", "vi": "Tôi dậy lúc sáu giờ rưỡi."},
    {"key": "w2", "head": "on + thứ", "en": "I play football on Mondays.", "vi": "Thứ Hai nào tôi cũng đá bóng."},
    {"key": "w3", "head": "in + buổi trong ngày", "en": "I study in the evenings.", "vi": "Tôi học vào các buổi tối."},
    {"key": "w4", "head": "at the weekend, at night", "en": "I stay up late at the weekend.", "vi": "Cuối tuần tôi thức khuya."},
    {"key": "w5", "head": "số lần + khoảng thời gian", "en": "I go to the gym three times a week.", "vi": "Tôi đi tập ba lần một tuần."},
    {"key": "w6", "head": "thỉnh thoảng", "en": "We go out every now and then.", "vi": "Thỉnh thoảng chúng tôi đi chơi."},
]

SITTING_1 = [
    {"kind": "title", "hook": "Vì sao biết ngữ pháp rồi mà lúc nói vẫn khựng lại?", "lines": [
        {"say": "Bạn đã bao giờ định nói một câu tiếng Anh rồi khựng lại vài giây, vì còn mải nhớ xem câu đó thuộc quy tắc nào chưa?", "show": "hook"},
        {"say": "Buổi này mình học thì hiện tại đơn theo sách Destination B2, nhưng chọn lọc theo cách của một người thầy giỏi: học cái dùng được ngay, và hiểu vì sao nó dùng được."},
    ]},
    {"kind": "scene", "visual": "five_boxes", "eyebrow": "Destination B2 · trang 6", "title": "Năm cái hộp của sách",
     "data": {"boxes": BOXES, "sentence": None}, "lines": [
        {"say": "Mở sách Destination B2, trang 6. Sách chia hiện tại đơn thành năm cách dùng. Gọi đó là năm cái hộp.", "show": "boxes"},
        {"say": "Trên nắp mỗi hộp có một chữ. Trước hết, học năm chữ đó. Mỗi chữ đọc một lần, bạn nhắc lại trong quãng nghỉ."},
    ]},
    {"kind": "word", "headword": "habit", "lines": [{"say": "Hộp thứ nhất."}]},
    {"kind": "word", "headword": "frequency", "lines": [{"say": "Hộp thứ hai."}]},
    {"kind": "word", "headword": "permanent", "lines": [{"say": "Hộp thứ ba."}]},
    {"kind": "word", "headword": "state", "lines": [{"say": "Hộp thứ tư."}]},
    {"kind": "word", "headword": "fact", "lines": [{"say": "Và hộp thứ năm."}]},
    {"kind": "scene", "visual": "five_boxes", "eyebrow": "Thí nghiệm 1", "title": "Một câu, xếp vào hộp nào?",
     "data": {"boxes": BOXES, "sentence": "I enjoy eating oranges.", "sentence_vi": "Tôi thích ăn cam.",
              "quote": "Ngữ pháp nó không rạch ròi như cái cách mà một quyển sách nó chia ra.",
              "rule": "Hộp để đọc sách. Lúc nói, không ai dừng lại chọn hộp."}, "lines": [
        {"say": "Bây giờ làm một thí nghiệm nhỏ. Lấy một câu thật bình thường.", "show": "boxes"},
        {"en": "I enjoy eating oranges.", "vi": "Tôi thích ăn cam.", "gap": True, "show": "sentence"},
        {"say": "Tôi thích ăn cam. Bạn thử xếp câu này vào từng hộp."},
        {"say": "Thích ăn cam có phải một thói quen không? Có.", "show": "t1"},
        {"say": "Có nói lên tần suất không? Có: thích thì ăn thường xuyên.", "show": "t2"},
        {"say": "Có lâu dài không? Có: thích từ bé tới giờ.", "show": "t3"},
        {"say": "Có phải một trạng thái không? Thích chính là một trạng thái.", "show": "t4"},
        {"say": "Có phải một sự thật không? Với tôi thì đúng là sự thật.", "show": "t5"},
        {"say": "Một câu, và cả năm hộp đều nhận.", "show": "merge"},
        {"say": "Có một câu đáng nhớ về chuyện này: ngữ pháp nó không rạch ròi như cái cách mà một quyển sách nó chia ra.", "show": "quote"},
        {"say": "Năm cái hộp giúp ta đọc sách. Nhưng lúc nói, không ai dừng lại để chọn hộp. Cái khựng vài giây lúc nãy chính là lúc bạn đang chọn hộp.", "show": "rule"},
    ]},
    {"kind": "scene", "visual": "ref_table", "eyebrow": "Gộp lại theo bản chất", "title": "Năm nhóm cách dùng",
     "data": {"cols": ["Nhóm", "Ví dụ"], "rows": USES,
              "rule": "Sách chia năm hộp. Gộp theo bản chất, còn năm nhóm, cộng hai cách dùng thêm cho IELTS."}, "lines": [
        {"say": "Vì ranh giới giữa các hộp mờ như vậy, cách học có chọn lọc là gộp lại theo bản chất. Còn năm nhóm. Nhóm một: hành động lặp lại. Nó gộp cả thói quen lẫn tần suất, vì có nói tần suất hay không là tùy bạn.", "show": "u1"},
        {"en": "Toby walks to work.", "vi": "Toby đi bộ đi làm.", "gap": True},
        {"say": "Nhóm hai: nói quá, than phiền. Việc vẫn xảy ra, nhưng người nói nói như thể không có.", "show": "u2"},
        {"en": "You don't visit me at all!", "vi": "Con chẳng về thăm mẹ gì cả!", "gap": True},
        {"say": "Nhóm ba: tình huống lâu dài. Chữ lâu dài chỉ là tương đối: năm nay làm đại lý du lịch, năm sau có thể đi lái xe buýt.", "show": "u3"},
        {"en": "Carlo works in a travel agent's.", "vi": "Carlo làm ở một đại lý du lịch.", "gap": True},
        {"say": "Nhóm bốn: trạng thái và ý kiến. Câu hỏi ở hiện tại đơn, nhưng câu trả lời không bắt buộc ở hiện tại đơn. Buổi sau mình làm kỹ chỗ này.", "show": "u4"},
        {"en": "Do you believe in God?", "vi": "Bạn có tin vào Chúa không?", "gap": True},
        {"say": "Nhóm năm: sự thật theo người nói, kể cả khi người nói nói dối. Chỗ này mình cũng làm kỹ ngay sau đây.", "show": "u5"},
        {"en": "Poland is in the European Union.", "vi": "Ba Lan nằm trong Liên minh châu Âu.", "gap": True},
        {"say": "Sách IELTS Grammar 6.5+ thêm hai cách dùng rất có ích cho thi. Chỉ đường và hướng dẫn thao tác.", "show": "u6"},
        {"en": "You go down to the traffic lights, then you turn left.", "vi": "Đi xuống đến đèn giao thông rồi rẽ trái.", "gap": True},
        {"say": "Và kể lại cốt truyện phim hoặc sách, dùng nhiều trong Speaking Part 2.", "show": "u7"},
        {"en": "In the film, the tea lady falls in love with the Prime Minister.", "vi": "Trong phim, cô bán trà phải lòng ngài thủ tướng.", "gap": True},
        {"say": "Một lưu ý: nói một việc đã kéo dài bao lâu thì dùng hiện tại hoàn thành, không dùng hiện tại đơn. Ví dụ: I have worked there since I was fifteen."},
        {"say": "Năm nhóm, và hai cách dùng thêm: đó là toàn bộ bảng cách dùng bạn cần.", "show": "rule"},
    ]},
    {"kind": "scene", "visual": "sentence_forms", "eyebrow": "Công thức · Destination B2 trang 6", "title": "Ba dạng câu của hiện tại đơn",
     "data": {"rows": [
                  {"key": "aff", "label": "Khẳng định", "parts": ["Minh", "cycles", "to school."], "hi": [1], "vi": "Minh đạp xe đi học."},
                  {"key": "neg", "label": "Phủ định", "parts": ["Minh", "doesn't cycle", "to school."], "hi": [1], "vi": "Minh không đạp xe đi học."},
                  {"key": "qst", "label": "Câu hỏi", "parts": ["Does", "Minh cycle", "to school?"], "hi": [0, 1], "vi": "Minh có đạp xe đi học không?"},
              ],
              "persons": [{"who": "I · you · we · they", "verb": "visit"}, {"who": "he · she · it", "verb": "visits"}],
              "spelling": [["work", "works"], ["watch", "watches"], ["go", "goes"], ["study", "studies"], ["have", "has"]],
              "short": ["Yes, he does.", "No, he doesn't."],
              "rule": "Khẳng định: he / she / it thêm s hoặc es. Phủ định và câu hỏi: does / doesn't, động từ về nguyên thể."}, "lines": [
        {"say": "Bây giờ là công thức. Chỉ có ba dạng: khẳng định, phủ định và câu hỏi."},
        {"say": "Một. Câu khẳng định. Với I, you, we, they, động từ giữ nguyên. Với he, she, it, nghĩa là một người hoặc một vật, động từ thêm s.", "show": "persons"},
        {"en": "Minh cycles to school.", "vi": "Minh đạp xe đi học.", "gap": True, "show": "aff"},
        {"say": "Không phải lúc nào cũng chỉ thêm s. Động từ tận cùng là s, sh, ch, x hoặc o thì thêm es: watch thành watches, go thành goes. Phụ âm đứng trước y thì đổi y thành ies: study thành studies. Và have thành has.", "show": "spelling"},
        {"say": "Hai. Câu phủ định. Đặt don't hoặc doesn't trước động từ. Với he, she, it dùng doesn't. Đã có doesn't thì động từ không còn s nữa, nó về nguyên thể."},
        {"en": "Minh doesn't cycle to school.", "vi": "Minh không đạp xe đi học.", "gap": True, "show": "neg"},
        {"say": "Ba. Câu hỏi. Đưa do hoặc does lên đầu câu, và động từ cũng về nguyên thể."},
        {"en": "Does Minh cycle to school?", "vi": "Minh có đạp xe đi học không?", "gap": True, "show": "qst"},
        {"say": "Trả lời ngắn thì dùng lại chính trợ từ đó: yes, he does, hoặc no, he doesn't.", "show": "short"},
        {"say": "Riêng động từ be không mượn do hay does: she isn't a student, is he late?"},
        {"say": "Tóm lại. Câu khẳng định: với he, she, it, động từ thêm s hoặc es. Câu phủ định và câu hỏi: dùng does hoặc doesn't, và động từ về nguyên thể.", "show": "rule"},
    ]},
    {"kind": "scene", "visual": "adverb_toggle", "eyebrow": "Thí nghiệm 2", "title": "Bỏ trạng từ đi thì sao?",
     "data": {"core": ["I", "visit", "my parents"], "verb": "visit", "adverb": "twice a week",
              "signals": ["always", "usually", "very often", "twice a week"],
              "proof": "I wake up at six.", "proof_vi": "Không có trạng từ nào, vẫn là thói quen.",
              "rule": "Trạng từ tần suất là phần thêm vào. Bỏ nó đi, câu vẫn là hiện tại đơn."}, "lines": [
        {"say": "Thí nghiệm thứ hai. Nhiều bạn chờ thấy always, usually, very often, twice a week rồi mới dám chia hiện tại đơn.", "show": "signals"},
        {"en": "I visit my parents twice a week.", "vi": "Tôi về thăm bố mẹ hai lần một tuần.", "gap": True, "show": "full"},
        {"say": "Bây giờ bỏ phần hai lần một tuần đi.", "show": "drop"},
        {"en": "I visit my parents.", "vi": "Tôi về thăm bố mẹ.", "gap": True},
        {"say": "Việc về thăm bố mẹ vẫn là việc lặp lại. Đâu có ai cả đời chỉ thăm bố mẹ đúng một lần."},
        {"say": "Thêm một câu không có trạng từ nào."},
        {"en": "I wake up at six.", "vi": "Tôi dậy lúc sáu giờ.", "gap": True, "show": "proof"},
        {"say": "Vẫn là thói quen. Trạng từ tần suất chỉ là phần thêm vào: nói hay không là tùy bạn muốn cho người nghe thêm thông tin gì.", "show": "rule"},
    ]},
    {"kind": "word", "headword": "routine", "lines": [{"say": "Giờ là cách nói tần suất. Năm từ chỉ mức độ, bắt đầu từ chính chữ thói quen hằng ngày."}]},
    {"kind": "word", "headword": "regularly", "lines": [{"say": "Một từ chỉ sự đều đặn."}]},
    {"kind": "word", "headword": "frequently", "lines": [{"say": "Một từ nữa."}]},
    {"kind": "word", "headword": "occasionally", "lines": [{"say": "Mức thấp hơn."}]},
    {"kind": "word", "headword": "rarely", "lines": [{"say": "Và mức thấp nhất, trước chữ không bao giờ."}]},
    {"kind": "scene", "visual": "ref_table", "eyebrow": "Trạng từ tần suất", "title": "Từ 100% xuống 0%",
     "data": {"cols": ["Mức xấp xỉ · từ", "Ví dụ"], "rows": FREQ,
              "rule": "Chỉ là mức xấp xỉ: người nói tự chọn từ hợp với điều muốn nói."}, "lines": [
        {"say": "Xếp các trạng từ theo mức, từ cao xuống thấp. Mức cao nhất là always, một trăm phần trăm.", "show": "f1"},
        {"en": "She is always late."},
        {"say": "Usually, normally và generally, khoảng chín mươi phần trăm.", "show": "f2"},
        {"en": "I usually walk to school."},
        {"say": "Often và frequently, khoảng bảy mươi.", "show": "f3"},
        {"en": "We often eat out."},
        {"say": "Sometimes, khoảng một nửa.", "show": "f4"},
        {"en": "Sometimes I cycle."},
        {"say": "Occasionally, khoảng hai mươi.", "show": "f5"},
        {"say": "Rarely, seldom và hardly ever, khoảng mười, gần như không.", "show": "f6"},
        {"en": "I hardly ever get up before seven.", "vi": "Tôi gần như không dậy trước bảy giờ.", "gap": True},
        {"say": "Và never, không bao giờ.", "show": "f7"},
        {"en": "He never eats meat.", "vi": "Anh ấy không bao giờ ăn thịt.", "gap": True},
        {"say": "Đây chỉ là mức xấp xỉ. Người nói tự chọn từ hợp với điều mình muốn nói.", "show": "rule"},
    ]},
    {"kind": "scene", "visual": "ref_table", "eyebrow": "Vị trí trong câu", "title": "Trạng từ đứng ở đâu?",
     "data": {"cols": ["Vị trí", "Ví dụ"], "rows": POSITION,
              "rule": "Sau be, trước động từ thường, sau don't. Never và hardly ever đã mang nghĩa phủ định."}, "lines": [
        {"say": "Trạng từ tần suất đứng ở đâu trong câu? Một. Sau động từ be.", "show": "p1"},
        {"en": "She is always late.", "vi": "Cô ấy lúc nào cũng muộn.", "gap": True},
        {"say": "Hai. Trước động từ thường.", "show": "p2"},
        {"en": "I usually walk to school.", "vi": "Tôi thường đi bộ đến trường.", "gap": True},
        {"say": "Ba. Trong câu phủ định hoặc câu hỏi, sau don't hoặc doesn't.", "show": "p3"},
        {"en": "I don't often eat out.", "vi": "Tôi không hay ăn ngoài.", "gap": True},
        {"say": "Bốn. Usually, often và sometimes còn đứng được ở đầu câu.", "show": "p4"},
        {"en": "Sometimes I cycle to work.", "vi": "Thỉnh thoảng tôi đạp xe đi làm.", "gap": True},
        {"say": "Năm. Never và hardly ever đã mang nghĩa phủ định rồi, nên không thêm don't. Người Việt hay nói thừa một lần phủ định.", "show": "p5"},
        {"en": "I never go there.", "vi": "Tôi không bao giờ đến đó.", "gap": True},
        {"say": "Nhớ ba chỗ: sau be, trước động từ thường, sau don't.", "show": "rule"},
    ]},
    {"kind": "scene", "visual": "ref_table", "eyebrow": "Cách nói thời gian", "title": "Giờ, ngày, buổi và số lần",
     "data": {"cols": ["Giới từ và cụm", "Ví dụ"], "rows": WHEN,
              "rule": "At cho giờ, on cho thứ, in cho buổi trong ngày."}, "lines": [
        {"say": "Cuối cùng, cách nói thời gian. Giờ giấc dùng at: at six, at half past six, at a quarter to seven.", "show": "w1"},
        {"en": "I get up at half past six.", "vi": "Tôi dậy lúc sáu giờ rưỡi.", "gap": True},
        {"say": "Thứ trong tuần dùng on. Thêm s sau thứ nghĩa là thứ nào cũng vậy.", "show": "w2"},
        {"en": "I play football on Mondays.", "vi": "Thứ Hai nào tôi cũng đá bóng.", "gap": True},
        {"say": "Buổi trong ngày dùng in: in the morning, in the afternoon, in the evening.", "show": "w3"},
        {"en": "I study in the evenings.", "vi": "Tôi học vào các buổi tối.", "gap": True},
        {"say": "Cuối tuần và ban đêm dùng at: at the weekend, at night.", "show": "w4"},
        {"en": "I stay up late at the weekend.", "vi": "Cuối tuần tôi thức khuya.", "gap": True},
        {"say": "Số lần: once, twice, rồi three times, cộng một khoảng thời gian.", "show": "w5"},
        {"en": "I go to the gym three times a week.", "vi": "Tôi đi tập ba lần một tuần.", "gap": True},
        {"say": "Và một cụm rất tự nhiên cho Speaking: every now and then, nghĩa là thỉnh thoảng.", "show": "w6"},
        {"en": "We go out every now and then.", "vi": "Thỉnh thoảng chúng tôi đi chơi.", "gap": True},
        {"say": "Giờ dùng at, thứ dùng on, buổi trong ngày dùng in.", "show": "rule"},
    ]},
    {"kind": "scene", "visual": "truth_cards", "eyebrow": "Bản chất", "title": "Điều người nói coi là thật",
     "data": {"groups": ["Việc lặp lại", "Trạng thái", "Sự thật"],
              "cards": [
                  {"key": "c1", "tag": "Sự thật khách quan", "art": "kettle", "en": "Water boils at 100 degrees Celsius.", "vi": "Nước sôi ở 100 độ C."},
                  {"key": "c2", "tag": "Nói quá", "art": "mother", "en": "You don't visit me at all!", "vi": "Con chẳng về thăm mẹ gì cả!"},
                  {"key": "c3", "tag": "Nói dối, ngữ pháp vẫn đúng", "art": "mask", "en": "No, I don't have a girlfriend.", "vi": "Không, anh chưa có bạn gái."},
              ],
              "quote": "Phần lớn thời gian cái các bạn nghĩ sẽ là cái các bạn nói, thế nên phần lớn cái chúng ta nói ra đều là sự thật chủ quan.",
              "rule": "Hiện tại đơn: điều người nói coi là thật, hoặc muốn người nghe coi là thật, lúc nói.",
              "ielts": "Writing Task 2: Online learning saves time."}, "lines": [
        {"say": "Vậy gom các hộp lại, hiện tại đơn dùng cho ba việc: việc lặp lại, trạng thái, và sự thật.", "show": "groups"},
        {"say": "Nhưng chữ sự thật ở đây rộng hơn bạn nghĩ. Câu đầu tiên."},
        {"en": "Water boils at 100 degrees Celsius.", "vi": "Nước sôi ở 100 độ C.", "gap": True, "show": "c1"},
        {"say": "Đây là sự thật khách quan, ai cũng công nhận. Nhưng ngoài đời, mấy khi mình ngồi nói với nhau chuyện nước sôi ở bao nhiêu độ."},
        {"say": "Tình huống thứ hai. Tuần nào bạn cũng về thăm mẹ hai lần. Tuần này bận thi, bạn chỉ về một lần. Mẹ trách ngay."},
        {"en": "You don't visit me at all!", "vi": "Con chẳng về thăm mẹ gì cả!", "gap": True, "show": "c2"},
        {"say": "Con chẳng về thăm mẹ gì cả. Mẹ nói quá lên, và mẹ vẫn dùng hiện tại đơn, vì lúc đó mẹ trình bày điều ấy như một sự thật."},
        {"say": "Tình huống thứ ba. Một anh đang có bạn gái, nhưng muốn người đối diện tin là chưa có."},
        {"en": "No, I don't have a girlfriend.", "vi": "Không, anh chưa có bạn gái.", "gap": True, "show": "c3"},
        {"say": "Anh ta nói dối, và câu vẫn đúng ngữ pháp hoàn toàn. Ngữ pháp không kiểm tra thật giả."},
        {"say": "Và một câu nữa, cũng đáng nhớ: phần lớn thời gian cái các bạn nghĩ sẽ là cái các bạn nói, thế nên phần lớn cái chúng ta nói ra đều là sự thật chủ quan.", "show": "quote"},
        {"say": "Vậy hiện tại đơn là điều người nói coi là thật, hoặc muốn người nghe coi là thật, vào lúc nói.", "show": "rule"},
        {"say": "Bạn sẽ dùng đúng điều này trong bài viết IELTS. Khi bạn nêu một nhận định trong Writing Task 2, bạn dùng hiện tại đơn, vì bạn trình bày nó như sự thật.", "show": "ielts"},
    ]},
    {"kind": "recap", "lines": [
        {"say": "Bây giờ mình nói lại các câu của buổi này. Nghe một câu, rồi nói to trong quãng nghỉ.", "show": "title"},
    ]},
    {"kind": "end", "next": "Tiếp theo: học các từ và mẫu ngữ pháp của buổi này, rồi mới làm bài tập.", "lines": [
        {"say": "Hết buổi một. Việc tiếp theo là học các từ và các mẫu ngữ pháp của buổi này trong app. Làm xong, bạn mới sang phần bài tập.", "show": "title"},
    ]},
]

ANSWERS = [
    {"key": "a1", "at": "now", "tense": "Hiện tại đơn", "en": "Yes, I do.", "vi": "Hiện tại tôi tin."},
    {"key": "a2", "at": "span", "tense": "Hiện tại hoàn thành", "en": "I have believed in God for a while.", "vi": "Tin từ trước đến giờ."},
    {"key": "a3", "at": "past", "tense": "Quá khứ đơn", "en": "I did, but not anymore.", "vi": "Trước có, giờ hết."},
    {"key": "a4", "at": "future", "tense": "Tương lai, có điều kiện", "en": "I will, if you can show me who God is.", "vi": "Sẽ tin, nếu…"},
]

ERRORS = [
    {"key": "e1", "wrong": "Does she works here?", "right": "Does she work here?", "why": "Đã có does thì động từ về nguyên thể."},
    {"key": "e2", "wrong": "Where you live?", "right": "Where do you live?", "why": "Thiếu do."},
    {"key": "e3", "wrong": "Do you can swim?", "right": "Can you swim?", "why": "can không mượn do."},
    {"key": "e4", "wrong": "Are you like jazz?", "right": "Do you like jazz?", "why": "like là động từ thường, không đi với are."},
    {"key": "e5", "wrong": "Who does live next door?", "right": "Who lives next door?", "why": "Hỏi về chủ ngữ thì không mượn do."},
    {"key": "e6", "wrong": "What means this word?", "right": "What does this word mean?", "why": "Phải mượn does và đảo thứ tự."},
    {"key": "e7", "wrong": "Yes, I like.", "right": "Yes, I do.", "why": "Trả lời ngắn dùng lại do hoặc does."},
]

COMPARE = [
    {"key": "k1", "head": "Việc đang xảy ra", "en": "I'm waiting for my friends.", "vi": "Tôi đang đợi bạn."},
    {"key": "k2", "head": "Tình huống tạm thời", "en": "My cousin is living in Thailand at the moment.", "vi": "Anh họ tôi đang sống ở Thái Lan."},
    {"key": "k3", "head": "Xu hướng đang đổi", "en": "The price of petrol is rising dramatically.", "vi": "Giá xăng đang tăng mạnh."},
    {"key": "k4", "head": "Phàn nàn, thêm always", "en": "My sister is always playing her music so loudly!", "vi": "Chị tôi lúc nào cũng bật nhạc ầm ĩ."},
]

SITTING_2 = [
    {"kind": "title", "hook": "Hỏi sai ở đâu, và hỏi thì nào có phải đáp thì nấy?", "lines": [
        {"say": "Buổi hai: hỏi sai ở đâu, và hỏi thì nào có phải đáp thì nấy?", "show": "hook"},
        {"say": "Buổi này có bốn việc. Một là sửa các lỗi hay gặp khi đặt câu hỏi. Hai là bỏ thói quen hỏi gì đáp nấy. Ba là một cách nhấn mạnh rất hay dùng khi nói. Bốn là so nhanh với hiện tại tiếp diễn."},
    ]},
    {"kind": "scene", "visual": "fix_pairs", "eyebrow": "Lỗi thường gặp khi hỏi", "title": "Bảy lỗi, bảy cách sửa",
     "data": {"rows": ERRORS,
              "rule": "Đã có do hoặc does thì động từ về nguyên thể. Hỏi về chủ ngữ thì không mượn do."}, "lines": [
        {"say": "Giám khảo Speaking Part 1 hỏi toàn câu hỏi, và người học hay sai ở đúng chỗ đó. Lỗi thứ nhất: chia hai lần.", "show": "e1"},
        {"en": "Does she work here?", "vi": "Cô ấy có làm ở đây không?", "gap": True},
        {"say": "Lỗi thứ hai: quên mượn do khi có từ để hỏi.", "show": "e2"},
        {"en": "Where do you live?", "vi": "Bạn sống ở đâu?", "gap": True},
        {"say": "Lỗi thứ ba: can không mượn do.", "show": "e3"},
        {"en": "Can you swim?", "vi": "Bạn biết bơi không?", "gap": True},
        {"say": "Lỗi thứ tư: dùng are với động từ thường.", "show": "e4"},
        {"en": "Do you like jazz?", "vi": "Bạn có thích nhạc jazz không?", "gap": True},
        {"say": "Lỗi thứ năm: khi từ để hỏi chính là chủ ngữ, thì không mượn do.", "show": "e5"},
        {"en": "Who lives next door?", "vi": "Ai sống ở nhà bên?", "gap": True},
        {"say": "Lỗi thứ sáu: hỏi nghĩa của từ.", "show": "e6"},
        {"en": "What does this word mean?", "vi": "Từ này nghĩa là gì?", "gap": True},
        {"say": "Lỗi thứ bảy: trả lời ngắn.", "show": "e7"},
        {"en": "Yes, I do.", "vi": "Có.", "gap": True},
        {"say": "Gói lại: đã có do hoặc does thì động từ về nguyên thể. Hỏi về chủ ngữ thì không mượn do.", "show": "rule"},
    ]},
    {"kind": "scene", "visual": "tense_timeline", "eyebrow": "Thí nghiệm 3", "title": "Một câu hỏi, bốn thì",
     "data": {"question": "Do you believe in God?", "question_vi": "Bạn có tin vào Chúa không?", "answers": ANSWERS,
              "rule": "Người hỏi chọn thì cho câu hỏi. Thì của câu trả lời là của bạn.",
              }, "lines": [
        {"say": "Giám khảo hỏi bạn một câu ở hiện tại đơn."},
        {"en": "Do you believe in God?", "show": "q"},
        {"say": "Bạn có tin vào Chúa không? Ở trường, hễ câu hỏi chia thì nào là mình đáp đúng thì đó. Nhưng ngoài đời thì không cần vậy: câu này có ít nhất bốn cách đáp, ở bốn thì. Chọn thì nào là tùy điều bạn muốn nói nằm ở đâu trên trục thời gian.", "show": "axis"},
        {"say": "Bây giờ bạn tin."},
        {"en": "Yes, I do.", "vi": "Có, tôi tin.", "gap": True, "show": "a1"},
        {"say": "Bạn tin từ trước tới giờ, và muốn nói cả quãng thời gian đó."},
        {"en": "I have believed in God for a while.", "vi": "Tôi tin được một thời gian rồi.", "gap": True, "show": "a2"},
        {"say": "Trước đây bạn tin, bây giờ thì hết."},
        {"en": "I did, but not anymore.", "vi": "Trước thì có, giờ thì không.", "gap": True, "show": "a3"},
        {"say": "Hiện giờ chưa tin, nhưng bạn để ngỏ."},
        {"en": "I will, if you can show me who God is.", "vi": "Tôi sẽ tin, nếu bạn chỉ cho tôi Chúa là ai.", "gap": True, "show": "a4"},
        {"say": "Một câu hỏi, bốn thì. Người hỏi chọn thì cho câu hỏi. Còn thì của câu trả lời là của bạn.", "show": "rule"},
        {"say": "Hôm nay bạn chưa cần nắm hết bốn thì. Việc của hôm nay chỉ là bỏ phản xạ hỏi gì đáp nấy."},
    ]},
    {"kind": "scene", "visual": "speaking_answer", "eyebrow": "IELTS Speaking Part 1", "title": "Một câu trả lời đầy đủ",
     "data": {"question": "Do you play any sports?", "question_vi": "Bạn có chơi môn thể thao nào không?",
              "short": "Yes, I do.",
              "parts": [
                  {"key": "p1", "role": "Trả lời thẳng", "tense": "Hiện tại đơn", "en": "Yes, I do.", "vi": "Có, tôi có chơi."},
                  {"key": "p2", "role": "Thêm thời gian", "tense": "Hiện tại hoàn thành", "en": "I have played badminton since last year.", "vi": "Tôi chơi cầu lông từ năm ngoái."},
                  {"key": "p3", "role": "Thêm thói quen", "tense": "Hiện tại đơn", "en": "I usually play with my friends twice a week.", "vi": "Tôi thường chơi với bạn hai lần một tuần."},
              ],
              "rule": "Trả lời thẳng, rồi thêm một hai ý. Mỗi câu chọn thì theo điều muốn nói."}, "lines": [
        {"say": "Bây giờ đưa vào phòng thi. Đây là Speaking Part 1: giám khảo hỏi những câu quen thuộc về bản thân bạn."},
        {"en": "Do you play any sports?", "show": "q"},
        {"say": "Bạn có chơi môn thể thao nào không? Nếu bạn chỉ đáp đúng một câu, nghe rất cụt, và giám khảo chưa nghe được bạn dùng tiếng Anh nhiều. Câu trả lời tự nhiên thường dài hai đến ba câu.", "show": "short"},
        {"say": "Cách làm: trước hết trả lời thẳng vào câu hỏi."},
        {"en": "Yes, I do.", "vi": "Có, tôi có chơi.", "gap": True, "show": "p1"},
        {"say": "Rồi thêm một ý về khoảng thời gian bạn đã chơi. Từ năm ngoái đến giờ, nên dùng hiện tại hoàn thành."},
        {"en": "I have played badminton since last year.", "vi": "Tôi chơi cầu lông từ năm ngoái.", "gap": True, "show": "p2"},
        {"say": "Cuối cùng thêm một chi tiết về thói quen. Câu này quay lại hiện tại đơn, có thêm trạng từ tần suất."},
        {"en": "I usually play with my friends twice a week.", "vi": "Tôi thường chơi với bạn hai lần một tuần.", "gap": True, "show": "p3"},
        {"say": "Ba câu, hai thì khác nhau, và thì nào cũng được chọn theo điều bạn muốn nói. Hôm nay bạn chưa cần giỏi cả hai: chỉ cần thử nói dài hơn một câu.", "show": "rule"},
    ]},
    {"kind": "word", "headword": "emphasise", "lines": [{"say": "Nửa sau của buổi này cần một từ."}]},
    {"kind": "scene", "visual": "do_does", "eyebrow": "Nhấn mạnh", "title": "do / does + động từ nguyên thể",
     "data": {"plain": "I like fish.", "emph": ["I", "do", "like fish!"], "emph_vi": "Tôi có thích cá mà!",
              "ex2": ["The bus is slow, but it", "does", "stop near my office."], "ex2_vi": "Xe buýt chậm, nhưng nó có dừng gần cơ quan tôi.",
              "wrong": "He does works hard.", "right": "He does work hard.",
              "rule": "Đã có do / does thì động từ sau nó ở dạng nguyên thể."}, "lines": [
        {"say": "Câu khẳng định ở hiện tại đơn bình thường không có do hay does."},
        {"en": "I like fish.", "show": "plain"},
        {"say": "Khi muốn nhấn mạnh, hoặc cãi lại điều người kia vừa nói, bạn đặt do hoặc does trước động từ. Bạn của bạn bảo: cậu có thích cá đâu. Bạn cãi lại."},
        {"en": "I do like fish!", "vi": "Tôi có thích cá mà!", "gap": True, "show": "emph"},
        {"say": "Hoặc khi bạn muốn nêu một điểm bù lại."},
        {"en": "The bus is slow, but it does stop near my office.", "vi": "Xe buýt chậm, nhưng nó có dừng gần cơ quan tôi.", "gap": True, "show": "ex2"},
        {"say": "Lỗi người Việt hay mắc là chia hai lần. Đã có does thì động từ sau nó về nguyên thể. Câu sai."},
        {"en": "He does works hard.", "show": "wrong"},
        {"say": "Câu đúng."},
        {"en": "He does work hard.", "vi": "Anh ấy có làm việc chăm chỉ mà.", "gap": True, "show": "right"},
        {"say": "Sau do và does, động từ luôn ở dạng nguyên thể.", "show": "rule"},
    ]},
    {"kind": "recap", "lines": [
        {"say": "Giờ nói lại các câu của buổi này. Nghe một câu, rồi nói to trong quãng nghỉ.", "show": "title"},
    ]},
    {"kind": "end", "next": "Tiếp theo: học từ và mẫu ngữ pháp, làm bài tập, rồi buổi 3 để vận dụng.", "lines": [
        {"say": "Hết phần giảng của ngày một. Bây giờ bạn học các từ và mẫu ngữ pháp trong app, rồi làm bài tập. Sau đó là buổi ba: nghe chép, nói có chấm điểm, và viết câu về chính bạn.", "show": "title"},
    ]},
]

# the rubric of the day's two "my own sentences" tasks: what IELTS rewards at this stage
RUBRIC = [
    {"criterion_vi": "Trả lời đúng câu hỏi, nội dung là của chính bạn", "max": 1, "note_vi": "Task response"},
    {"criterion_vi": "Chọn thì đúng với điều muốn nói (mỗi câu một ý trên trục thời gian)", "max": 2, "note_vi": "Grammatical range"},
    {"criterion_vi": "Dạng động từ đúng: -s ngôi thứ ba, do/does + nguyên thể, have + V3", "max": 2, "note_vi": "Grammatical accuracy"},
]


def reshape(sessions: list[dict], exercise_ids: list[str], card_of: dict[str, int]) -> list[dict]:
    """Day 1's sittings around the two lectures. Sitting 1 teaches cards 1-4 with its ten words, sitting 2
    cards 5-8 with `emphasise`; the questions of each stay with its own cards. The production work (build,
    type, dictation, say, write) and the remaining words (from the books' own texts) become a third sitting
    without a lecture, so no sitting runs much past 15 minutes."""
    pats = [g for s in sessions[:3] for g in s["grammar"]]
    allcheck = [i for s in sessions[:3] for i in s["check"]]
    s1, s2 = sessions[0], sessions[1]
    rest = sessions[3:]
    S1_WORDS = ["habit", "frequency", "permanent", "state", "fact", "routine", "regularly", "frequently", "occasionally", "rarely"]
    S2_WORDS = ["emphasise"]
    all_words = [w for s in sessions[:3] for w in s["vocab"]]
    left = [w for w in all_words if w not in S1_WORDS + S2_WORDS]
    s1["vocab"], s2["vocab"] = S1_WORDS, S2_WORDS
    s1["grammar"], s2["grammar"] = pats[:4], pats[4:]
    quiz = [i for i in allcheck if i[4] in "IQ"]
    s1["check"] = [i for i in quiz if card_of[i] < 4]
    s2["check"] = [i for i in quiz if card_of[i] >= 4]
    moved = [i for i in allcheck if i not in quiz]
    s1["lecture"], s2["lecture"] = SITTING_1, SITTING_2
    s1["title_vi"] = "Buổi 1 · công thức, cách dùng, tần suất và thời gian"
    s2["title_vi"] = "Buổi 2 · câu hỏi, lỗi thường gặp, hỏi thì này đáp thì khác"
    s3 = {
        "title_vi": "Buổi 3 · từ vựng và vận dụng: nghe chép, nói, viết",
        "can_do_vi": "Sau buổi này bạn biết thêm các từ của sách (tần suất, học thuật, năng lượng), tự xếp và gõ được câu hiện tại đơn, nghe chép được ba câu và viết câu về chính mình.",
        "use_vi": s1["use_vi"],
        "vocab": left,
        "check": moved,
    }
    assert set(s1["check"] + s2["check"] + moved) <= set(exercise_ids)
    return [s1, s2, s3] + rest

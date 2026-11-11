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

SITTING_1 = [
    {"kind": "title", "hook": "Vì sao biết ngữ pháp rồi mà lúc nói vẫn khựng lại?", "lines": [
        {"say": "Bạn đã bao giờ định nói một câu tiếng Anh rồi khựng lại vài giây, vì còn mải nhớ xem câu đó thuộc quy tắc nào chưa?", "show": "hook"},
        {"say": "Nhiều người điểm ngữ pháp rất cao vẫn bị như vậy. Buổi này mình tìm xem cái khựng đó từ đâu ra, bằng một thí nghiệm nhỏ với thì hiện tại đơn."},
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
    {"kind": "scene", "visual": "adverb_toggle", "eyebrow": "Thí nghiệm 2", "title": "Bỏ trạng từ đi thì sao?",
     "data": {"core": ["I", "visit", "my parents"], "verb": "visit", "adverb": "twice a week",
              "signals": ["always", "usually", "very often", "twice a week"],
              "proof": "I wake up at six.", "proof_vi": "Không có trạng từ nào, vẫn là thói quen.",
              "rule": "Trạng từ tần suất là phần thêm vào. Bỏ nó đi, câu vẫn là hiện tại đơn."}, "lines": [
        {"say": "Thí nghiệm thứ hai. Nhiều bạn chờ thấy always, usually, very often, twice a week rồi mới dám chia hiện tại đơn.", "show": "signals"},
        {"say": "Xem câu này."},
        {"en": "I visit my parents twice a week.", "vi": "Tôi về thăm bố mẹ hai lần một tuần.", "gap": True, "show": "full"},
        {"say": "Bây giờ bỏ phần hai lần một tuần đi.", "show": "drop"},
        {"en": "I visit my parents.", "vi": "Tôi về thăm bố mẹ.", "gap": True},
        {"say": "Việc về thăm bố mẹ vẫn là việc lặp lại. Đâu có ai cả đời chỉ thăm bố mẹ đúng một lần."},
        {"say": "Thêm một câu không có trạng từ nào."},
        {"en": "I wake up at six.", "vi": "Tôi dậy lúc sáu giờ.", "gap": True, "show": "proof"},
        {"say": "Vẫn là thói quen. Trạng từ tần suất chỉ là phần thêm vào: nói hay không là tùy bạn muốn cho người nghe thêm thông tin gì.", "show": "rule"},
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
        {"say": "Vậy gom năm hộp lại, hiện tại đơn dùng cho ba việc: việc lặp lại, trạng thái, và sự thật.", "show": "groups"},
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
    {"kind": "scene", "visual": "sentence_forms", "eyebrow": "Cách lập câu", "title": "Ba dạng câu của hiện tại đơn",
     "data": {"rows": [
                  {"key": "aff", "label": "Khẳng định", "parts": ["Minh", "cycles", "to school."], "hi": [1], "vi": "Minh đạp xe đi học."},
                  {"key": "neg", "label": "Phủ định", "parts": ["Minh", "doesn't cycle", "to school."], "hi": [1], "vi": "Minh không đạp xe đi học."},
                  {"key": "qst", "label": "Câu hỏi", "parts": ["Does", "Minh cycle", "to school?"], "hi": [0, 1], "vi": "Minh có đạp xe đi học không?"},
              ],
              "persons": [{"who": "I · you · we · they", "verb": "visit"}, {"who": "he · she · it", "verb": "visits"}],
              "spelling": [["work", "works"], ["watch", "watches"], ["study", "studies"], ["have", "has"]],
              "short": ["Yes, he does.", "No, he doesn't."],
              "rule": "Khẳng định: he / she / it thêm s. Phủ định và câu hỏi: does / doesn't, động từ về nguyên thể."}, "lines": [
        {"say": "Bây giờ là cách lập câu. Chỉ có ba dạng: khẳng định, phủ định và câu hỏi."},
        {"say": "Một. Câu khẳng định. Với I, you, we, they, động từ giữ nguyên. Với he, she, it, nghĩa là một người hoặc một vật, động từ thêm s.", "show": "persons"},
        {"say": "Ví dụ."},
        {"en": "Minh cycles to school.", "vi": "Minh đạp xe đi học.", "gap": True, "show": "aff"},
        {"say": "Minh là một người, tức là he, nên cycle thành cycles. Không phải lúc nào cũng chỉ thêm s: watch thành watches, study thành studies, và have thành has.", "show": "spelling"},
        {"say": "Hai. Câu phủ định. Đặt don't hoặc doesn't trước động từ. Với he, she, it dùng doesn't. Chú ý: đã có doesn't thì động từ không còn s nữa, nó về nguyên thể."},
        {"en": "Minh doesn't cycle to school.", "vi": "Minh không đạp xe đi học.", "gap": True, "show": "neg"},
        {"say": "Ba. Câu hỏi. Đưa do hoặc does lên đầu câu, và động từ cũng về nguyên thể."},
        {"en": "Does Minh cycle to school?", "vi": "Minh có đạp xe đi học không?", "gap": True, "show": "qst"},
        {"say": "Trả lời ngắn thì dùng lại chính trợ từ đó: yes, he does, hoặc no, he doesn't.", "show": "short"},
        {"say": "Tóm lại. Câu khẳng định: với he, she, it, động từ thêm s. Câu phủ định và câu hỏi: dùng does hoặc doesn't, và động từ về nguyên thể.", "show": "rule"},
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

SITTING_2 = [
    {"kind": "title", "hook": "Hỏi thì nào, có phải đáp thì nấy?", "lines": [
        {"say": "Buổi hai: hỏi thì nào, có phải đáp thì nấy?", "show": "hook"},
        {"say": "Buổi này có hai việc. Một là bỏ thói quen hỏi gì đáp nấy. Hai là học một cách nhấn mạnh rất hay dùng khi nói."},
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
        {"say": "Hết phần giảng của ngày một. Bây giờ bạn học các từ và mẫu ngữ pháp trong app, rồi làm bài tập. Sau đó là buổi ba: nghe chép, nói có chấm điểm, và viết hai câu về chính bạn.", "show": "title"},
    ]},
]

# the rubric of the day's two "my own sentences" tasks: what IELTS rewards at this stage
RUBRIC = [
    {"criterion_vi": "Trả lời đúng câu hỏi, nội dung là của chính bạn", "max": 1, "note_vi": "Task response"},
    {"criterion_vi": "Chọn thì đúng với điều muốn nói (mỗi câu một ý trên trục thời gian)", "max": 2, "note_vi": "Grammatical range"},
    {"criterion_vi": "Dạng động từ đúng: -s ngôi thứ ba, do/does + nguyên thể, have + V3", "max": 2, "note_vi": "Grammatical accuracy"},
]


def reshape(sessions: list[dict], exercise_ids: list[str]) -> list[dict]:
    """Day 1's sittings around the two lectures: `emphasise` moves to the sitting that uses it, the
    second sitting keeps the questions on its own two cards, and the production work (build, type,
    dictation, say, write) becomes a third sitting, so no sitting runs much past 15 minutes."""
    s1, s2, rest = sessions[0], sessions[1], sessions[2:]
    s1["vocab"] = [w for w in s1["vocab"] if w != "emphasise"]
    s2["vocab"] = ["emphasise"]
    keep = [i for i in s2["check"] if i[4] in "IQ"] + ["G1D1B4", "G1D1F2", "G1D1F3"]
    moved = [i for i in s2["check"] if i not in keep]
    s2["check"] = keep
    s1["lecture"], s2["lecture"] = SITTING_1, SITTING_2
    s3 = {
        "title_vi": "Buổi 3 · vận dụng: nghe chép, nói, viết câu của tôi",
        "can_do_vi": "Sau buổi này bạn tự xếp và gõ được câu hiện tại đơn, nghe chép được ba câu, và viết được hai câu ở hai thì khác nhau về chính mình.",
        "use_vi": s1["use_vi"],
        "check": moved,
    }
    assert set(keep + moved) <= set(exercise_ids)
    return [s1, s2, s3] + rest

"""G1 · Day 7 (Destination C1&C2, Unit 2: Thinking and learning): the four lectures written by hand
(lesson_audio.build_authored_lecture), and the day's sittings reshaped around them. Same format as
lecture_d1.py / d2 / d3.

The method is the teacher's: a situation first, then ONE idea per word group; every hard word is anchored to an
easy one the learner already owns (plausible = reasonable); a word with a narrow context is shown with its
context (deliberate: a jury) and the safe word to use instead; abstract words are explained with a scene from
daily life (a paradox: the more extra classes, the worse the marks; the wider the road, the worse the jam);
sounds that change a word are named without typing a transcription (faith / fate, access / assess).
Priorities follow his filter: the ten thinking verbs and the education words are learned in full; collocations are
picked; phrasal verbs are only recognised. Every picture is drawn in code (StoryArtWords.tsx) and moves only while
its own sentence is said. No transcription is typed from memory.
"""

PRON: dict[str, str] = {}


def _row(key, icon, head, en, vi):
    return {"key": key, "icon": icon, "head": head, "en": en, "vi": vi}


# ------------------------------------------------------------------ sitting 1: ten thinking verbs
ANCHORS = [
    _row("a1", "scales", "assess = evaluate", "She assessed the risk.", "Đánh giá: cân hai phía rồi kết luận."),
    _row("a2", "crystal", "speculate = guess", "We can only speculate.", "Phỏng đoán khi chưa có bằng chứng."),
    _row("a3", "dotted_check", "presume = assume", "I presume you have finished.", "Cho là đúng, chưa kiểm tra."),
]

SPELL = [
    {"key": "s1", "head": "assess · đánh giá", "en": "assess", "vi": "Nhấn âm thứ hai. Có hai âm xờ liền nhau."},
    {"key": "s2", "head": "access · tiếp cận", "en": "access", "vi": "Nhấn âm thứ nhất. Âm đầu nghe như át."},
]

BELIEVE = [
    _row("b1", "dotted_check", "assume · mặc định", "I assume the shop is open.", "Coi là đúng, chưa đi kiểm tra."),
    _row("b2", "thought", "presume · cho là", "I presume you have finished.", "Cho là đúng vì có căn cứ nào đó."),
    _row("b3", "crystal", "speculate · phỏng đoán", "We can only speculate about the reason.", "Chưa đủ bằng chứng, chỉ đoán."),
]

NUMBERS = [
    _row("n1", "ruler", "estimate · ước tính", "I estimate the painting will cost at least two thousand euros.", "Ước lượng một con số."),
    _row("n2", "magnifier", "deduce · suy ra", "From the damage, I deduce that the car hit a wall.", "Từ dấu vết có sẵn, suy ra điều chưa thấy."),
]

TRAPS_V = [
    {"key": "e1", "wrong": "It is hard to access someone's suitability in a short interview.", "right": "It is hard to assess someone's suitability in a short interview.", "why": "access là tiếp cận. Đánh giá là assess."},
    {"key": "e2", "wrong": "The painting will cost two thousand euro.", "right": "The painting will cost two thousand euros.", "why": "Hơn một euro thì viết euros, có đuôi số nhiều."},
    {"key": "e3", "wrong": "I estimate that he is guilty from the evidence.", "right": "I deduce that he is guilty from the evidence.", "why": "Suy ra từ bằng chứng là deduce. Estimate dành cho một con số."},
]

SITTING_1 = [
    {"kind": "title", "hook": "Ngoài think, bạn còn động từ nào để nói về suy nghĩ?", "lines": [
        {"say": "Ngoài think, bạn còn động từ nào để nói về suy nghĩ?", "show": "hook"},
        {"say": "Nếu chỉ có think, bài viết sẽ đơn điệu. Hôm nay học mười động từ, mỗi từ một sắc thái. Mười từ này đáng học thuộc."},
    ]},
    {"kind": "scene", "visual": "picture_cards", "eyebrow": "Mẹo của buổi này", "title": "Gắn từ khó vào từ quen",
     "data": {"rows": ANCHORS, "rule": "Đừng học nghĩa tiếng Việt dài. Mỗi từ khó gắn vào một từ quen."}, "lines": [
        {"say": "Thay vì học thuộc lời giải thích dài trong từ điển, hãy làm thế này. Assess, gắn vào evaluate: đánh giá.", "show": "a1"},
        {"en": "She assessed the risk.", "vi": "Cô ấy đánh giá rủi ro.", "gap": True},
        {"say": "Speculate, gắn vào guess: đoán.", "show": "a2"},
        {"en": "We can only speculate.", "vi": "Chúng ta chỉ có thể phỏng đoán.", "gap": True},
        {"say": "Presume, gắn vào assume hoặc suppose: cho rằng.", "show": "a3"},
        {"en": "I presume you have finished.", "vi": "Tôi cho rằng bạn đã xong.", "gap": True},
        {"say": "Từ lạ trở thành từ quen đội một cái mũ mới. Giờ mình đi từng từ.", "show": "rule"},
    ]},
    {"kind": "word", "headword": "assess", "lines": [
        {"say": "Từ đầu tiên. Người ta đánh giá một ứng viên chỉ qua mười phút phỏng vấn. Đánh giá, tức là cân ưu nhược rồi kết luận. Neo nó vào evaluate."},
    ]},
    {"kind": "scene", "visual": "ref_table", "eyebrow": "Dễ nhầm", "title": "assess và access",
     "data": {"cols": ["Từ", "Cách đọc"], "rows": SPELL,
              "rule": "assess nhấn âm hai. access nhấn âm một. Nhấn sai là người nghe hiểu thành từ kia."}, "lines": [
        {"say": "Cẩn thận, assess rất dễ lẫn với access. Assess nhấn âm thứ hai.", "show": "s1"},
        {"en": "assess", "vi": "đánh giá", "gap": True},
        {"say": "Access nhấn âm thứ nhất, nghe như át xét. Nghĩa là tiếp cận.", "show": "s2"},
        {"en": "access", "vi": "tiếp cận", "gap": True},
        {"say": "Nói sai trọng âm, người nghe sẽ hiểu thành từ kia.", "show": "rule"},
    ]},
    {"kind": "word", "headword": "assume", "lines": [
        {"say": "Bạn thấy đèn nhà hàng xóm tắt, và nghĩ ngay họ đi vắng. Chưa kiểm tra mà đã coi là thật. Đó là assume."},
    ]},
    {"kind": "word", "headword": "presume", "lines": [
        {"say": "Presume cũng là cho rằng, và neo vào assume. Bạn nhờ bạn mình làm bài, và nghĩ chắc là xong rồi."},
    ]},
    {"kind": "word", "headword": "speculate", "lines": [
        {"say": "Còn khi chưa có bằng chứng nào, mà mọi người vẫn bàn tán? Ví dụ, vì sao một công ty đóng cửa. Đó là speculate. Neo vào guess."},
    ]},
    {"kind": "scene", "visual": "picture_cards", "eyebrow": "Ba cách cho rằng", "title": "Mặc định, cho là, phỏng đoán",
     "data": {"rows": BELIEVE, "rule": "Cùng là cho rằng, nhưng mức chắc chắn khác nhau. Speculate là yếu nhất."}, "lines": [
        {"say": "Ba từ này đều là cho rằng, nhưng khác sắc thái. Assume: coi là đúng, chưa đi kiểm tra.", "show": "b1"},
        {"en": "I assume the shop is open.", "vi": "Tôi cho là cửa hàng đang mở.", "gap": True},
        {"say": "Presume: cho là đúng, vì có căn cứ nào đó.", "show": "b2"},
        {"en": "I presume you have finished.", "vi": "Tôi cho là bạn đã xong.", "gap": True},
        {"say": "Speculate: chưa đủ bằng chứng, chỉ đoán.", "show": "b3"},
        {"en": "We can only speculate about the reason.", "vi": "Chúng ta chỉ có thể phỏng đoán nguyên nhân.", "gap": True},
        {"say": "Chọn từ theo mức chắc chắn của bạn. Speculate là yếu nhất.", "show": "rule"},
    ]},
    {"kind": "word", "headword": "estimate", "lines": [
        {"say": "Bạn nhìn một bức tranh bị hỏng và nói: sửa chắc hết khoảng hai nghìn. Ước lượng một con số. Đó là estimate."},
    ]},
    {"kind": "word", "headword": "deduce", "lines": [
        {"say": "Deduce thì khác. Không đoán con số. Từ những gì đang thấy, bạn suy ra điều chưa thấy. Như thám tử nhìn dấu chân, rồi kết luận ai đã đi qua."},
    ]},
    {"kind": "scene", "visual": "picture_cards", "eyebrow": "Con số hay bằng chứng", "title": "estimate và deduce",
     "data": {"rows": NUMBERS, "rule": "Ước một con số: estimate. Suy ra từ bằng chứng: deduce. Hơn một euro thì viết euros."}, "lines": [
        {"say": "Estimate ước một con số. Và để ý cách đọc tiền: hai nghìn euro phải đọc là euros, có s, vì lớn hơn một.", "show": "n1"},
        {"en": "I estimate the painting will cost at least two thousand euros.", "vi": "Tôi ước bức tranh sửa hết ít nhất hai nghìn euro.", "gap": True},
        {"say": "Deduce thì đi từ dấu vết đến kết luận.", "show": "n2"},
        {"en": "From the damage, I deduce that the car hit a wall.", "vi": "Nhìn chỗ hư hại, tôi suy ra xe đã đâm vào tường.", "gap": True},
        {"say": "Con số: estimate. Bằng chứng: deduce.", "show": "rule"},
    ]},
    {"kind": "word", "headword": "justify", "lines": [
        {"say": "Chính phủ chi rất nhiều tiền cho quân đội, và bạn hỏi: làm sao biện minh được khoản này? Phải đưa ra lý lẽ để bảo vệ. Đó là justify. Chữ y ở cuối đọc là ai, không đọc là i."},
    ]},
    {"kind": "word", "headword": "reflect", "lines": [
        {"say": "Reflect là quay lại nhìn điều đã xảy ra rồi suy ngẫm. Neo vào think carefully."},
    ]},
    {"kind": "word", "headword": "discriminate", "lines": [
        {"say": "Discriminate là đối xử khác nhau với người ta, vì tuổi tác, giới tính hay nơi sinh. Từ này hay gặp khi viết về xã hội."},
    ]},
    {"kind": "word", "headword": "baffle", "lines": [
        {"say": "Từ cuối cùng. Giám khảo hỏi một câu quá hóc búa, bạn đứng hình, rối như sợi chỉ. Đó là baffle. Neo vào confuse."},
    ]},
    {"kind": "scene", "visual": "fix_pairs", "eyebrow": "Lỗi thường gặp", "title": "Ba lỗi, ba cách sửa",
     "data": {"rows": TRAPS_V, "rule": "Đánh giá là assess, không phải access. Hơn một euro thì viết euros. Suy ra từ bằng chứng là deduce."}, "lines": [
        {"say": "Ba lỗi người học hay mắc. Lỗi thứ nhất: nhầm access với assess.", "show": "e1"},
        {"en": "It is hard to assess someone's suitability in a short interview.", "vi": "Khó đánh giá một người chỉ qua buổi phỏng vấn ngắn.", "gap": True},
        {"say": "Lỗi thứ hai: quên s sau số tiền.", "show": "e2"},
        {"en": "The painting will cost two thousand euros.", "vi": "Bức tranh sẽ tốn hai nghìn euro.", "gap": True},
        {"say": "Lỗi thứ ba: dùng estimate cho một suy luận.", "show": "e3"},
        {"en": "I deduce that he is guilty from the evidence.", "vi": "Từ bằng chứng, tôi suy ra anh ta có tội.", "gap": True},
        {"say": "Nhớ ba điều. Đánh giá là assess, không phải access. Hơn một euro thì viết euros. Suy ra từ bằng chứng là deduce, không phải estimate.", "show": "rule"},
    ]},
    {"kind": "recap", "lines": [
        {"say": "Giờ nói lại các câu của buổi này. Nghe một câu, rồi nói to trong quãng nghỉ.", "show": "title"},
    ]},
    {"kind": "end", "next": "Tiếp theo: chọn từ theo ngữ cảnh. Rồi chọn 5 đến 10 từ bạn thích nhất.", "lines": [
        {"say": "Hết buổi một. Đừng ép mình thuộc hết ngay. Hãy chọn năm đến mười từ bạn thích nhất, rồi tự nhẩm một hai câu về cuộc sống của chính bạn. Từ nào có quan hệ cá nhân với bạn thì nhớ lâu. Buổi hai nói về cách chọn từ đúng ngữ cảnh.", "show": "title"},
    ]},
]

# ------------------------------------------------------------------ sitting 2: understand, believe, weigh up
HEAR = [
    _row("g1", "ear", "gather · nghe được", "I gather from your tutor that you are changing course.", "Đời thường: nghe từ người khác."),
    _row("g2", "eye", "perceive · nhận ra", "Scientists perceive a pattern in the data.", "Rất trang trọng, hợp văn học thuật."),
]

WEIGH = [
    _row("w1", "scales", "contemplate · cân nhắc", "I am seriously contemplating asking for a pay rise.", "Một quyết định thực tế. Hợp với consider."),
    _row("w2", "ripples", "ponder · suy ngẫm", "She sat by the sea and pondered why the universe exists.", "Câu hỏi lớn, sâu, triết lý."),
    _row("w3", "gavel", "deliberate · nghị án", "The jury are still deliberating.", "Bối cảnh hẹp: bồi thẩm đoàn, hội đồng."),
]

TRAPS_W = [
    {"key": "e1", "wrong": "I grasp from your tutor that you are leaving.", "right": "I gather from your tutor that you are leaving.", "why": "grasp là hiểu. Nghe được thông tin thì dùng gather."},
    {"key": "e2", "wrong": "I am pondering asking for a pay rise tomorrow.", "right": "I am contemplating asking for a pay rise tomorrow.", "why": "ponder dành cho câu hỏi lớn, sâu. Quyết định thực tế dùng contemplate."},
]

SITTING_2 = [
    {"kind": "title", "hook": "Cùng nghĩa suy nghĩ, nhưng không thay bừa được. Vì sao?", "lines": [
        {"say": "Cùng nghĩa suy nghĩ, nhưng không thay bừa được. Vì sao?", "show": "hook"},
        {"say": "Vì mỗi từ có ngữ cảnh riêng. Hôm nay học cách soi ngữ cảnh."},
    ]},
    {"kind": "word", "headword": "grasp", "lines": [
        {"say": "Mở đầu với từ dễ: bạn mất một lúc lâu mới hiểu luật chơi của trò chơi. Hiểu thấu, nắm được. Đó là grasp. Neo vào understand."},
    ]},
    {"kind": "word", "headword": "plausible", "lines": [
        {"say": "Plausible là nghe có lý. Hãy neo vào reasonable. A plausible explanation, chính là a reasonable explanation. Lời giải thích nghe có lý."},
    ]},
    {"kind": "word", "headword": "gather", "lines": [
        {"say": "Gather ngoài nghĩa tụ họp, còn một nghĩa rất hay: nghe được thông tin từ ai đó. I gather from your tutor, nghĩa là: tôi nghe thầy hướng dẫn của bạn nói rằng."},
    ]},
    {"kind": "scene", "visual": "picture_cards", "eyebrow": "Độ trang trọng", "title": "gather hay perceive",
     "data": {"rows": HEAR, "rule": "Chuyện đời thường thì gather. Perceive quá trang trọng cho chuyện đổi khóa học."}, "lines": [
        {"say": "Có thể thay gather bằng perceive không? Không. Gather là cách nói đời thường.", "show": "g1"},
        {"en": "I gather from your tutor that you are changing course.", "vi": "Tôi nghe giáo viên nói bạn định đổi khóa học.", "gap": True},
        {"say": "Perceive là nhận ra, lĩnh hội. Quá trang trọng, hợp với văn học thuật chứ không hợp chuyện đổi môn học.", "show": "g2"},
        {"en": "Scientists perceive a pattern in the data.", "vi": "Các nhà khoa học nhận ra một quy luật trong dữ liệu.", "gap": True},
        {"say": "Chọn từ phải hợp cả nghĩa lẫn độ trang trọng.", "show": "rule"},
    ]},
    {"kind": "word", "headword": "reckon", "lines": [
        {"say": "Reckon và suppose đều là nghĩ rằng, đoán rằng. Hai từ này thay được cho nhau. Reckon nghe thân mật hơn."},
    ]},
    {"kind": "word", "headword": "suppose", "lines": [
        {"say": "Suppose cũng vậy. Một mẫu rất hay dùng để nhờ vả lịch sự: I don't suppose, rồi câu hỏi."},
        {"en": "I don't suppose I could borrow your notes, could I?", "vi": "Chắc tôi không mượn được vở ghi của bạn nhỉ?", "gap": True},
    ]},
    {"kind": "word", "headword": "ponder", "lines": [
        {"say": "Bây giờ đến ba từ dễ dùng sai nhất. Từ thứ nhất: ponder. Bạn ngồi bên biển và tự hỏi vì sao vũ trụ lại tồn tại. Đó là suy ngẫm lâu, câu hỏi lớn. Neo vào think about."},
    ]},
    {"kind": "word", "headword": "contemplate", "lines": [
        {"say": "Từ thứ hai: contemplate. Bạn đang cân nhắc nghiêm túc việc xin tăng lương. Quyết định thực tế, có thể xảy ra. Neo vào consider."},
    ]},
    {"kind": "word", "headword": "deliberate", "lines": [
        {"say": "Từ thứ ba: deliberate. Mở từ điển ra, bạn sẽ thấy gần như mọi câu ví dụ đều nói về bồi thẩm đoàn hoặc ủy ban đang bàn bạc để ra phán quyết. Bối cảnh rất hẹp."},
    ]},
    {"kind": "scene", "visual": "picture_cards", "eyebrow": "Ba bậc cân nhắc", "title": "contemplate, ponder, deliberate",
     "data": {"rows": WEIGH, "rule": "Không chắc 100% về ngữ cảnh thì đừng dùng. Chọn từ an toàn: think carefully, contemplate, ponder."}, "lines": [
        {"say": "Xếp ba từ lên một hàng. Contemplate: cân nhắc một quyết định thực tế.", "show": "w1"},
        {"en": "I am seriously contemplating asking for a pay rise.", "vi": "Tôi đang nghiêm túc cân nhắc xin tăng lương.", "gap": True},
        {"say": "Ponder: suy ngẫm một câu hỏi lớn, sâu, mang tính triết lý.", "show": "w2"},
        {"en": "She sat by the sea and pondered why the universe exists.", "vi": "Cô ngồi bên biển và suy ngẫm vì sao vũ trụ tồn tại.", "gap": True},
        {"say": "Deliberate: nghị án, bàn bạc để đưa ra phán quyết.", "show": "w3"},
        {"en": "The jury are still deliberating.", "vi": "Bồi thẩm đoàn vẫn đang nghị án.", "gap": True},
        {"say": "Và đây là lời khuyên quan trọng. Đi thi, nếu bạn không chắc chắn hoàn toàn từ đó dùng được trong câu của mình, thì đừng dùng. Hãy chọn từ an toàn hơn: think carefully, contemplate hoặc ponder.", "show": "rule"},
    ]},
    {"kind": "scene", "visual": "fix_pairs", "eyebrow": "Lỗi thường gặp", "title": "Hai lỗi, hai cách sửa",
     "data": {"rows": TRAPS_W, "rule": "Nghe được thông tin: gather. Quyết định thực tế: contemplate."}, "lines": [
        {"say": "Hai lỗi hay gặp. Lỗi thứ nhất: nhầm grasp với gather.", "show": "e1"},
        {"en": "I gather from your tutor that you are leaving.", "vi": "Tôi nghe giáo viên nói bạn sắp đi.", "gap": True},
        {"say": "Lỗi thứ hai: dùng ponder cho một chuyện đời thường.", "show": "e2"},
        {"en": "I am contemplating asking for a pay rise tomorrow.", "vi": "Ngày mai tôi đang cân nhắc xin tăng lương.", "gap": True},
        {"say": "Nghe được thông tin: gather. Quyết định thực tế: contemplate.", "show": "rule"},
    ]},
    {"kind": "recap", "lines": [
        {"say": "Giờ nói lại các câu của buổi này. Nghe một câu, rồi nói to trong quãng nghỉ.", "show": "title"},
    ]},
    {"kind": "end", "next": "Tiếp theo: danh từ về suy nghĩ, từ thế khó đến nghịch lý.", "lines": [
        {"say": "Hết buổi hai. Buổi ba là nhóm danh từ: thế khó, linh cảm, nghịch lý.", "show": "title"},
    ]},
]

# ------------------------------------------------------------------ sitting 3: nouns of thinking
IDEAS = [
    _row("i1", "bulb", "notion = idea", "Paying mothers a salary is an interesting notion.", "Quan niệm, ý tưởng."),
    _row("i2", "qmark", "query = question", "I have a small query about the syllabus.", "Thắc mắc, trang trọng hơn question."),
    _row("i3", "crossroads", "dilemma = difficult situation", "I am in a real dilemma.", "Thế khó: hai lựa chọn đều khó."),
]

NOEVIDENCE = [
    _row("h1", "bolt", "hunch · linh cảm", "I have a hunch that someone will be promoted.", "Một cảm giác chợt đến."),
    _row("h2", "eye", "intuition · trực giác", "Her intuition told her something was wrong.", "Cảm nhận sâu, không cần bằng chứng."),
    _row("h3", "dice", "guesswork · phỏng đoán", "It is educated guesswork, not a fact.", "Đoán, và educated nghĩa là có cơ sở."),
]

FAITH = [
    _row("f1", "heart", "faith · niềm tin", "I have complete faith in my teacher.", "Kết thúc bằng âm cắn lưỡi: đầu lưỡi giữa hai hàm răng, thổi hơi."),
    _row("f2", "star", "fate · số phận", "It was fate that we met.", "Kết thúc bằng âm tờ: đọc nhầm là thành số phận."),
]

PARADOX = [
    _row("p1", "book", "Học thêm", "The more extra classes I took, the worse my marks became.", "Đi học thêm càng nhiều, càng dốt."),
    _row("p2", "roadmap", "Giao thông Hà Nội", "The wider the road, the worse the traffic.", "Đường càng mở rộng, càng tắc."),
]

SITTING_3 = [
    {"kind": "title", "hook": "Hai lời mời tiệc cùng giờ. Bạn đi bên nào?", "lines": [
        {"say": "Hai lời mời tiệc cùng giờ. Bạn đi bên nào? Cảm giác bí ấy có tên trong tiếng Anh.", "show": "hook"},
        {"say": "Hôm nay học nhóm danh từ về suy nghĩ."},
    ]},
    {"kind": "word", "headword": "dilemma", "lines": [
        {"say": "Đó là dilemma: thế khó, phải chọn giữa hai điều đều khó xử. Neo vào difficult situation."},
    ]},
    {"kind": "word", "headword": "notion", "lines": [
        {"say": "Notion neo vào idea: một ý tưởng, một quan niệm."},
    ]},
    {"kind": "word", "headword": "query", "lines": [
        {"say": "Query neo vào question, nhưng trang trọng hơn. Bạn có một thắc mắc nhỏ về đề cương thi, và muốn hỏi cô giáo."},
    ]},
    {"kind": "scene", "visual": "picture_cards", "eyebrow": "Ba từ, ba từ quen", "title": "notion, query, dilemma",
     "data": {"rows": IDEAS, "rule": "Notion là idea. Query là question. Dilemma là difficult situation."}, "lines": [
        {"say": "Ba từ này đều neo vào từ quen. Notion là idea.", "show": "i1"},
        {"en": "Paying mothers a salary is an interesting notion.", "vi": "Trả lương cho các bà mẹ là một ý tưởng thú vị.", "gap": True},
        {"say": "Query là question.", "show": "i2"},
        {"en": "I have a small query about the syllabus.", "vi": "Tôi có một thắc mắc nhỏ về đề cương.", "gap": True},
        {"say": "Dilemma là difficult situation.", "show": "i3"},
        {"en": "I am in a real dilemma.", "vi": "Tôi đang ở thế khó thật sự.", "gap": True},
        {"say": "Nhớ cặp từ quen và từ mới.", "show": "rule"},
    ]},
    {"kind": "word", "headword": "hunch", "lines": [
        {"say": "Giờ đến ba cách biết một điều khi chưa có bằng chứng. Thứ nhất, hunch: một linh cảm bất chợt, kiểu bạn đoán văn phòng sắp có người được thăng chức."},
    ]},
    {"kind": "word", "headword": "intuition", "lines": [
        {"say": "Thứ hai, intuition: trực giác. Thám tử không có bằng chứng nào, nhưng trực giác mách bảo ông ta rằng nghi phạm có liên quan."},
    ]},
    {"kind": "word", "headword": "guesswork", "lines": [
        {"say": "Thứ ba, guesswork: sự phỏng đoán. Có một cụm rất hay: educated guesswork, đoán có cơ sở, dựa trên kiến thức và kinh nghiệm. Giải ô chữ khó thường cần một chút như vậy. Đừng thay bằng educated intuition, nghe sẽ ngô nghê."},
    ]},
    {"kind": "scene", "visual": "picture_cards", "eyebrow": "Biết mà chưa có bằng chứng", "title": "hunch, intuition, guesswork",
     "data": {"rows": NOEVIDENCE, "rule": "Linh cảm: hunch. Trực giác: intuition. Phỏng đoán có cơ sở: educated guesswork."}, "lines": [
        {"say": "Hunch là cảm giác chợt đến.", "show": "h1"},
        {"en": "I have a hunch that someone will be promoted.", "vi": "Tôi có linh cảm sắp có người được thăng chức.", "gap": True},
        {"say": "Intuition là cảm nhận sâu, không cần bằng chứng.", "show": "h2"},
        {"en": "Her intuition told her something was wrong.", "vi": "Trực giác mách cô ấy có chuyện không ổn.", "gap": True},
        {"say": "Guesswork là đoán, và nếu có cơ sở thì gọi là educated guesswork.", "show": "h3"},
        {"en": "It is educated guesswork, not a fact.", "vi": "Đó là phỏng đoán có cơ sở, không phải sự thật.", "gap": True},
        {"say": "Ba cách biết khi chưa có bằng chứng.", "show": "rule"},
    ]},
    {"kind": "word", "headword": "genius", "lines": [
        {"say": "Genius là thiên tài. Một người có thể là thiên tài về thiên văn, mà vẫn ngớ ngẩn trong những việc đời thường."},
    ]},
    {"kind": "word", "headword": "faith", "lines": [
        {"say": "Faith là niềm tin tuyệt đối vào ai đó. Và đây là chỗ phải rất cẩn thận về âm cuối."},
    ]},
    {"kind": "scene", "visual": "picture_cards", "eyebrow": "Âm cuối đổi nghĩa", "title": "faith và fate",
     "data": {"rows": FAITH, "rule": "Âm cuối của danh từ thuộc về bản chất của từ. Đọc sai là thành từ khác."}, "lines": [
        {"say": "Faith kết thúc bằng âm cắn lưỡi. Đặt đầu lưỡi giữa hai hàm răng rồi thổi hơi.", "show": "f1"},
        {"en": "faith", "vi": "niềm tin", "gap": True},
        {"say": "Nếu bạn nuốt âm cuối, hoặc đọc thành âm tờ, người nghe sẽ hiểu thành fate, nghĩa là số phận.", "show": "f2"},
        {"en": "fate", "vi": "số phận", "gap": True},
        {"say": "Những âm cuối ngữ pháp, như đuôi thì quá khứ, nói nhanh đôi khi còn bỏ qua được. Nhưng âm cuối thuộc về chính từ, thì không được bỏ.", "show": "rule"},
    ]},
    {"kind": "word", "headword": "paradox", "lines": [
        {"say": "Từ cuối cùng và là từ nhiều người hiểu sai: paradox, nghịch lý. Nhiều bạn nghĩ nghịch lý là điều trái với thực tế. Không phải. Nghịch lý là một điều mà ngay bên trong nó đã có hai vế tự mâu thuẫn."},
    ]},
    {"kind": "scene", "visual": "picture_cards", "eyebrow": "Nghịch lý đời thường", "title": "Hai nghịch lý quen thuộc",
     "data": {"rows": PARADOX, "rule": "Hai vế tự mâu thuẫn ngay trong một sự việc: đó là paradox."}, "lines": [
        {"say": "Ví dụ thứ nhất. Thời cấp hai, có bạn đi học thêm càng nhiều thì lại càng học dốt, vì ỷ lại vào lớp thêm, lên lớp chính thì ngồi chơi.", "show": "p1"},
        {"en": "The more extra classes I took, the worse my marks became.", "vi": "Học thêm càng nhiều, điểm tôi càng tệ.", "gap": True},
        {"say": "Ví dụ thứ hai, ở Hà Nội. Đáng lẽ mở rộng đường thì thông thoáng hơn. Nhưng nhiều khi đường càng rộng thì lại càng tắc.", "show": "p2"},
        {"en": "The wider the road, the worse the traffic.", "vi": "Đường càng rộng, giao thông càng tệ.", "gap": True},
        {"say": "Hai vế đối nghịch nằm ngay trong cùng một sự việc. Đó là paradox.", "show": "rule"},
    ]},
    {"kind": "recap", "lines": [
        {"say": "Giờ nói lại các câu của buổi này. Nghe một câu, rồi nói to trong quãng nghỉ.", "show": "title"},
    ]},
    {"kind": "end", "next": "Tiếp theo: nhóm từ giáo dục, học trọn không chọn lọc.", "lines": [
        {"say": "Hết buổi ba. Buổi bốn là từ giáo dục. Riêng nhóm này, bạn nên học hết.", "show": "title"},
    ]},
]

# ------------------------------------------------------------------ sitting 4: education
COLLOC = [
    {"key": "e1", "wrong": "students with special wants", "right": "students with special needs", "why": "Cụm cố định. Dùng từ khác, câu đúng ngữ pháp mà vẫn ngô nghê."},
    {"key": "e2", "wrong": "make her more academic about her subjects", "right": "make her more knowledgeable about her subjects", "why": "Ôn một môn chỉ giúp biết nhiều hơn về môn đó."},
    {"key": "e3", "wrong": "give students any subject in social skills", "right": "give students any lesson in social skills", "why": "Sau give, dùng lesson."},
]

SESSIONS = [
    _row("u1", "speaker", "lecture · bài giảng", "The lecture is in the big hall.", "Giảng lý thuyết trên giảng đường lớn."),
    _row("u2", "discuss", "seminar · thảo luận", "Read the article before the seminar.", "Đọc trước ở nhà, lên lớp tranh luận."),
    _row("u3", "pencil_sheet", "tutorial · hướng dẫn", "We work through the problems in the tutorial.", "Nhóm nhỏ, cùng giải bài tập."),
    _row("u4", "coin", "tuition · học phí", "Tuition is paid every term.", "Tiền học phí."),
]

SITTING_4 = [
    {"kind": "title", "hook": "Chủ đề giáo dục: học từ nào, bỏ từ nào?", "lines": [
        {"say": "Chủ đề giáo dục: học từ nào, bỏ từ nào?", "show": "hook"},
        {"say": "Nhóm này học hết, không chọn lọc. Và chú ý kết hợp từ: đúng ngữ pháp chưa đủ."},
    ]},
    {"kind": "word", "headword": "special needs", "lines": [
        {"say": "Hệ thống giáo dục gọi học sinh yếu cần hỗ trợ thêm là học sinh có special needs. Cụm cố định."},
    ]},
    {"kind": "word", "headword": "conscientious", "lines": [
        {"say": "Học sinh giỏi nhất, tận tâm nhất, mà vẫn không được khuyến khích phát triển. Tận tâm là conscientious. Neo vào hard-working. Từ này khá dài, nên đọc chậm theo từng khúc, rồi nhanh dần."},
    ]},
    {"kind": "word", "headword": "cram", "lines": [
        {"say": "Con gái của tác giả lá thư học nhồi suốt một tháng cho kỳ thi. Học nhồi nhét là cram."},
    ]},
    {"kind": "word", "headword": "mock exam", "lines": [
        {"say": "Mà đó chỉ là kỳ thi thử, không phải thi thật. Thi thử là mock exam. Lưu ý, mock còn có nghĩa chế giễu, nhưng đứng trước exam thì là thi thử."},
    ]},
    {"kind": "word", "headword": "knowledgeable", "lines": [
        {"say": "Ôn xong liệu cô bé có hiểu biết hơn về môn học không? Hiểu biết nhiều về một lĩnh vực là knowledgeable."},
    ]},
    {"kind": "scene", "visual": "fix_pairs", "eyebrow": "Vì sao câu đúng ngữ pháp vẫn bị trừ điểm", "title": "Loại trừ để chọn từ tự nhiên",
     "data": {"rows": COLLOC, "rule": "Đúng ngữ pháp chưa đủ. Kết hợp từ sai khiến câu ngô nghê và bị trừ điểm từ vựng."}, "lines": [
        {"say": "Hãy học cách loại trừ như thế này. Vì sao không nói special wants? Vì cụm cố định là special needs.", "show": "e1"},
        {"en": "students with special needs", "vi": "học sinh có nhu cầu giáo dục đặc biệt", "gap": True},
        {"say": "Vì sao không nói academic? Vì ôn một môn chỉ giúp cô bé biết nhiều hơn về môn đó. Chưa thể thành người mang tính học thuật.", "show": "e2"},
        {"en": "more knowledgeable about her subjects", "vi": "hiểu biết nhiều hơn về các môn học", "gap": True},
        {"say": "Và vì sao không nói give subject? Vì sau động từ give, ta dùng lesson.", "show": "e3"},
        {"en": "give students any lesson in social skills", "vi": "dạy cho học sinh bài học về kỹ năng xã hội", "gap": True},
        {"say": "Đúng ngữ pháp chưa đủ. Phải đúng kết hợp từ.", "show": "rule"},
    ]},
    {"kind": "word", "headword": "curriculum", "lines": [
        {"say": "Chương trình học là curriculum. Số nhiều của nó bất quy tắc: curricula, đuôi um đổi thành a. Nhấn âm thứ hai."},
    ]},
    {"kind": "word", "headword": "give lessons in", "lines": [
        {"say": "Và đây là cụm vừa thấy: chương trình chuẩn không dạy học sinh bài học nào về kỹ năng sống. Give lessons in."},
    ]},
    {"kind": "word", "headword": "tuition", "lines": [
        {"say": "Giờ đến ba cái tên dễ lẫn ở đại học phương Tây. Trước hết tuition: tiền học phí, hoặc việc được dạy kèm."},
    ]},
    {"kind": "word", "headword": "seminar", "lines": [
        {"say": "Seminar là buổi thảo luận chuyên đề. Giảng viên chỉ dẫn dắt ngắn. Học viên phải đọc tài liệu trước ở nhà rồi lên lớp phân tích, tranh luận."},
    ]},
    {"kind": "word", "headword": "tutorial", "lines": [
        {"say": "Tutorial là buổi hướng dẫn nhóm nhỏ, thường để cùng giải bài tập khó, nhất là các môn Toán, Lý, Hóa, Sinh."},
    ]},
    {"kind": "scene", "visual": "picture_cards", "eyebrow": "Các kiểu buổi học", "title": "lecture, seminar, tutorial, tuition",
     "data": {"rows": SESSIONS, "rule": "Lecture: nghe giảng. Seminar: thảo luận. Tutorial: giải bài tập. Tuition: học phí."}, "lines": [
        {"say": "Xếp lại cho gọn. Lecture là bài giảng lý thuyết trên giảng đường lớn.", "show": "u1"},
        {"en": "The lecture is in the big hall.", "vi": "Bài giảng ở giảng đường lớn.", "gap": True},
        {"say": "Seminar: đọc trước, lên lớp thảo luận.", "show": "u2"},
        {"en": "Read the article before the seminar.", "vi": "Hãy đọc bài báo trước buổi seminar.", "gap": True},
        {"say": "Tutorial: nhóm nhỏ, cùng giải bài tập.", "show": "u3"},
        {"en": "We work through the problems in the tutorial.", "vi": "Chúng tôi cùng giải các bài trong buổi tutorial.", "gap": True},
        {"say": "Tuition là tiền học phí.", "show": "u4"},
        {"en": "Tuition is paid every term.", "vi": "Học phí được đóng mỗi học kỳ.", "gap": True},
        {"say": "Bốn thứ khác nhau, đừng lẫn.", "show": "rule"},
    ]},
    {"kind": "word", "headword": "plagiarise", "lines": [
        {"say": "Plagiarise là đạo văn. Và nó không chỉ là chép chữ. Chuyện đạo nhái tranh vẽ trên mạng xã hội cho thấy lấy cắp ý tưởng và hình ảnh cũng là đạo nhái. Danh từ là plagiarism."},
    ]},
    {"kind": "word", "headword": "self-study", "lines": [
        {"say": "Self-study là tự học. Ở đại học không ai bảo bạn phải làm gì, nên đây là kỹ năng sống còn."},
    ]},
    {"kind": "word", "headword": "graduate", "lines": [
        {"say": "Từ cuối cùng: graduate, tốt nghiệp. Chú ý âm cuối theo từ loại. Động từ graduate, đuôi kéo dài như trong chữ eight. Còn danh từ graduate, nghĩa là cử nhân, đuôi đọc ngắn và nhẹ."},
    ]},
    {"kind": "recap", "lines": [
        {"say": "Giờ nói lại các câu của buổi này. Nghe một câu, rồi nói to trong quãng nghỉ.", "show": "title"},
    ]},
    {"kind": "end", "next": "Tiếp theo: học các cụm cố định, làm bài tập, rồi chọn 5 đến 10 từ yêu thích.", "lines": [
        {"say": "Hết phần giảng của ngày bảy. Bây giờ bạn làm bài tập trong app. Cuối cùng hãy chọn năm đến mười từ bạn thích nhất trong cả unit, và gõ một hai câu của riêng bạn. Từ nào gắn với chuyện của chính bạn thì nhớ rất lâu.", "show": "title"},
    ]},
]

TITLES = [
    "Buổi 1 · mười động từ tư duy, cách neo vào từ quen",
    "Buổi 2 · hiểu, tin, cân nhắc: chọn từ theo ngữ cảnh",
    "Buổi 3 · danh từ tư duy: thế khó, linh cảm, nghịch lý",
    "Buổi 4 · từ giáo dục: học hết, không chọn lọc",
]
LECTURES = [SITTING_1, SITTING_2, SITTING_3, SITTING_4]


def reshape(sessions: list[dict]) -> list[dict]:
    """The first four vocabulary sittings get their lecture and title; every other sitting is kept as built."""
    for i, lecture in enumerate(LECTURES):
        ses = sessions[i]
        words = [s["headword"] for s in lecture if s.get("kind") == "word"]
        assert sorted(words) == sorted(ses["vocab"]), (i, set(words) ^ set(ses["vocab"]))
        ses["lecture"] = lecture
        ses["title_vi"] = TITLES[i]
        assert len(ses["title_vi"]) <= 70
    return sessions

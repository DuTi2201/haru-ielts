"""Week 2 · Day 7 (build day 27): careful listening, "The Luddites". Four lectures written by hand
(lesson_audio.build_authored_lecture): one before listening (the story, reading the questions first, how people agree,
doubt and sympathise, the traps of time and of "you might think … but in fact"), two short vocabulary sittings with the
words to hear first, and one after listening (going over only the right answers, the paraphrase between question and
recording, why each trap is wrong). vocab_day() gives the two vocabulary sittings their lecture (reshape); finish()
builds the order of the day.

Sources: the course's listening work (Week 1 syllabus: phase 1 listens slowly and studies the paraphrase between
question and recording; the answer tables "paraphrase, traps", with the tense trap of a number said three times;
session 3: only the right answer is read out, so a wrong one does not stay in the memory); Week 1 Day 7 (Part 3: read
the questions first, follow who speaks and listen until the point is settled). History of the Luddites kept to what is
common knowledge (textile workers who broke machines in England, 1811-1816) and to what the recording says.
No teacher, book or page is named on the slides or in the narration.

Pronunciations: Oxford Learner's Dictionaries, British English, read 2026-11-26.
"""

PRON = {
    "automation": "/ˌɔːtəˈmeɪʃn/",
    "textile": "/ˈtekstaɪl/",
    "threaten": "/ˈθretn/",
    "repetitive": "/rɪˈpetətɪv/",
    "leisure": "/ˈleʒə(r)/",
    "unemployment": "/ˌʌnɪmˈplɔɪmənt/",
    "retire": "/rɪˈtaɪə(r)/",
    "productivity": "/ˌprɒdʌkˈtɪvəti/",
    "qualification": "/ˌkwɒlɪfɪˈkeɪʃn/",
    "census": "/ˈsensəs/",
    "lifespan": "/ˈlaɪfspæn/",
    "redundant": "/rɪˈdʌndənt/",
}

NOTES = {
    "automation": "automatic là tự động; automation là việc để máy tự làm thay người.",
    "textile": "Ngành dệt: the textile industry. Từ này hay gặp trong bài về cách mạng công nghiệp.",
    "threaten": "threat là mối đe dọa; feel threatened là cảm thấy bị đe dọa.",
    "repetitive": "repeat là lặp lại; repetitive tasks là những việc lặp đi lặp lại.",
    "leisure": "Phát âm Anh: /ˈleʒə/. Cụm hay gặp: leisure time, leisure activities.",
    "unemployment": "employ là thuê người làm; un- là không; unemployment là tình trạng thất nghiệp.",
    "retire": "retirement là sự nghỉ hưu; delay retiring là hoãn nghỉ hưu.",
    "productivity": "produce là sản xuất; productivity là năng suất, làm ra bao nhiêu trong một khoảng thời gian.",
    "qualification": "qualify là đủ điều kiện; qualification là bằng cấp, chứng chỉ.",
    "census": "Cuộc điều tra dân số của cả nước, làm theo định kỳ.",
    "lifespan": "life là đời sống; span là khoảng; lifespan là tuổi thọ.",
    "redundant": "Không còn cần đến; ở Anh, be made redundant là bị cho thôi việc vì không còn việc.",
}

# ============================================================ lecture 1: before listening

STORY = [
    {"key": "p1", "icon": "gear", "label": "Đầu thế kỷ 19", "kind": "bg", "en": "New machines came into the textile industry.", "vi": "Máy móc mới vào ngành dệt ở Anh."},
    {"key": "p2", "icon": "crash", "label": "1811–1816", "kind": "event", "en": "The Luddites destroyed their knitting machines.", "vi": "Công nhân đập máy vì sợ mất việc."},
    {"key": "p3", "icon": "trend", "label": "Về sau", "kind": "chain", "en": "Industrialisation created more jobs than it destroyed.", "vi": "Công nghiệp hóa tạo ra nhiều việc hơn."},
    {"key": "p4", "icon": "screen", "label": "Hôm nay", "kind": "chain", "en": "What will automation do to our jobs?", "vi": "Câu hỏi cũ, công nghệ mới."},
]
PREDICT = [
    {"key": "r1", "head": "ineffective", "en": "didn't achieve anything · had no effect", "vi": "không có tác dụng"},
    {"key": "r2", "head": "proved right", "en": "they were right after all", "vi": "hóa ra họ đúng"},
    {"key": "r3", "head": "Unemployment will fall", "en": "lower unemployment · fewer people out of work", "vi": "ít người thất nghiệp hơn"},
    {"key": "r4", "head": "Working hours will be shorter", "en": "more leisure time · work less", "vi": "nhiều thời gian rảnh hơn"},
]
SIGNALS = [
    {"key": "s1", "head": "Đồng ý", "en": "That's true. · I agree.", "vi": "Người nói nhận ý của người kia."},
    {"key": "s2", "head": "Nghi ngờ", "en": "Bit too optimistic, don't you think? · I'm not so sure about that.", "vi": "Người nói không tin điều được dự đoán."},
    {"key": "s3", "head": "Thông cảm", "en": "I can see why … · I'm sure I would have felt the same.", "vi": "Hiểu được cảm xúc của người khác."},
]
TIMES = [
    {"key": "t1", "head": "Đã xảy ra, tới nay", "en": "has become · has fallen · have risen · has led to", "vi": "Nhận xét về một thay đổi đã có."},
    {"key": "t2", "head": "Sẽ xảy ra", "en": "are likely to be · there is likely to be · will require", "vi": "Nhận xét về điều người nói dự đoán."},
]
TRAPS = [
    {"key": "x1", "wrong": "You might think … would have put them out of a job", "right": "but in fact there are more of them than ever", "why": "Ý chính nằm sau `but in fact`; phần trước chỉ là điều người ta tưởng."},
    {"key": "x2", "wrong": "I'd have assumed it would be more than 50%.", "right": "Now it's less than 0.2%.", "why": "`I'd have assumed` là điều người nói từng tưởng, không phải sự thật."},
]

PRE = [
    {"kind": "title", "hook": "Đập máy để giữ việc làm: chuyện xưa hay chuyện của chúng ta?", "lines": [
        {"say": "Đập máy để giữ việc làm: đó là chuyện của hai trăm năm trước, hay cũng là chuyện của chúng ta hôm nay?", "show": "hook"},
        {"say": "Bài nghe hôm nay là cuộc trò chuyện của hai sinh viên sau một buổi seminar về tự động hóa và tương lai của việc làm. Trước khi nghe, mình chuẩn bị ba việc."},
    ]},
    {"kind": "scene", "visual": "story_strip", "eyebrow": "Câu chuyện", "title": "Những người đập máy",
     "data": {"frame": "strip", "panels": STORY, "rule": "Biết trước câu chuyện thì nghe dễ hơn: tai chỉ còn phải bắt chi tiết."}, "lines": [
        {"say": "Đầu thế kỷ mười chín, máy móc mới được đưa vào ngành dệt ở nước Anh.", "show": "p1"},
        {"say": "Từ năm 1811 tới năm 1816, nhiều công nhân dệt đập phá máy vì sợ mất việc. Họ được gọi là những người Luddite.", "show": "p2"},
        {"say": "Về sau, công nghiệp hóa lại tạo ra nhiều việc làm hơn số việc nó xóa đi.", "show": "p3"},
        {"say": "Ngày nay câu hỏi ấy quay lại với robot và trí tuệ nhân tạo: tự động hóa sẽ làm gì với việc làm của chúng ta?", "show": "p4"},
        {"say": "Biết trước câu chuyện thì nghe dễ hơn nhiều: tai không phải đoán bối cảnh, chỉ còn phải bắt chi tiết.", "show": "rule"},
    ]},
    {"kind": "scene", "visual": "ref_table", "eyebrow": "Việc thứ nhất", "title": "Đọc câu hỏi trước, đoán cách nói lại",
     "data": {"cols": ["Trong câu hỏi", "Bài nghe có thể nói", "Nghĩa"], "rows": PREDICT,
              "rule": "Bài nghe hiếm khi lặp đúng chữ của câu hỏi; nó nói cùng ý bằng chữ khác."}, "lines": [
        {"say": "Đề hiếm khi dùng lại đúng chữ của bài nghe. Vì vậy, đọc mỗi lựa chọn, bạn đoán xem người nói có thể diễn đạt nó thế nào. Không có tác dụng có thể được nói là chẳng đạt được gì.", "show": "r1"},
        {"say": "Được chứng minh là đúng có thể được nói là hóa ra họ đúng.", "show": "r2"},
        {"say": "Thất nghiệp giảm có thể thành ít người mất việc hơn.", "show": "r3"},
        {"say": "Giờ làm ngắn lại có thể thành có nhiều thời gian rảnh hơn.", "show": "r4"},
        {"say": "Đoán trước không phải để đoán đáp án, mà để khi nghe thấy một cách nói khác, bạn nhận ra ngay nó đang nói về lựa chọn nào.", "show": "rule"},
    ]},
    {"kind": "scene", "visual": "ref_table", "eyebrow": "Việc thứ hai", "title": "Nghe thái độ của người nói",
     "data": {"cols": ["Thái độ", "Câu nghe được", "Nghĩa là"], "rows": SIGNALS,
              "rule": "Câu hỏi hỏi ý kiến hay sự nghi ngờ: nghe thái độ, không chỉ nghe chủ đề."}, "lines": [
        {"say": "Câu hỏi hai mươi ba hỏi những dự đoán mà hai bạn nghi ngờ. Cả năm dự đoán có thể đều được nhắc tới; điều phân biệt là thái độ. Câu đồng ý nghe như thế này.", "show": "s1"},
        {"en": "That's true. I agree."},
        {"say": "Câu nghi ngờ nghe như thế này.", "show": "s2"},
        {"en": "Bit too optimistic, don't you think? I'm not so sure about that."},
        {"say": "Còn câu thông cảm, hiểu được cảm xúc của người khác, nghe như thế này.", "show": "s3"},
        {"en": "I can see why they felt so threatened."},
        {"say": "Gặp câu hỏi về ý kiến hay sự nghi ngờ, hãy nghe thái độ của người nói, không chỉ nghe chủ đề.", "show": "rule"},
    ]},
    {"kind": "scene", "visual": "ref_table", "eyebrow": "Việc thứ ba", "title": "Nhận xét nói về lúc nào?",
     "data": {"cols": ["Mốc thời gian", "Trong các nhận xét", "Dùng khi"], "rows": TIMES,
              "rule": "Một nhận xét đúng nội dung mà sai mốc thời gian vẫn là đáp án sai."}, "lines": [
        {"say": "Phần câu hỏi từ hai mươi lăm tới ba mươi có bảy nhận xét. Hãy để ý thì của từng nhận xét. Một nhóm nói về thay đổi đã xảy ra, kéo tới bây giờ: hiện tại hoàn thành, đúng phần ngữ pháp của tuần này.", "show": "t1"},
        {"say": "Nhóm kia nói về điều sẽ xảy ra: người nói dự đoán.", "show": "t2"},
        {"say": "Nghe một nghề đang tăng hay sẽ tăng, đã thay đổi hay sẽ thay đổi, rồi mới chọn. Một nhận xét đúng nội dung mà sai mốc thời gian vẫn là đáp án sai.", "show": "rule"},
    ]},
    {"kind": "scene", "visual": "fix_pairs", "eyebrow": "Bẫy hay gặp", "title": "Điều người ta tưởng và điều có thật",
     "data": {"rows": TRAPS, "rule": "Nghe tới lúc người nói chốt: ý chính thường đứng sau chữ but hay chữ now."}, "lines": [
        {"say": "Bẫy thứ nhất: người nói nêu một điều bạn có thể tưởng, rồi đảo lại.", "show": "x1"},
        {"en": "You might think they would be out of a job, but in fact there are more of them than ever."},
        {"say": "Phần trước chỉ là điều người ta tưởng. Ý chính nằm sau cụm nghĩa là nhưng thật ra."},
        {"say": "Bẫy thứ hai: người nói kể điều mình từng nghĩ, rồi mới nói con số thật.", "show": "x2"},
        {"en": "I'd have assumed it would be more than fifty per cent. Now it's less than nought point two per cent."},
        {"say": "Nghe tới lúc người nói chốt ý: ý chính thường đứng sau chữ but, hay sau chữ now.", "show": "rule"},
    ]},
    {"kind": "end", "next": "Tiếp theo: từ để nghe trước, rồi nghe bài và chọn đáp án.", "lines": [
        {"say": "Hết phần chuẩn bị. Tiếp theo là những từ nên biết trước khi nghe. Sau đó bạn nghe bài, đọc câu hỏi trước, nghe lại bao nhiêu lần cũng được.", "show": "title"},
    ]},
]

# ============================================================ the two vocabulary sittings

FAMILY = [
    {"key": "f1", "head": "automatic", "en": "automation", "vi": "tự động → sự tự động hóa"},
    {"key": "f2", "head": "employ", "en": "unemployment", "vi": "thuê người làm → tình trạng thất nghiệp"},
    {"key": "f3", "head": "produce", "en": "productivity", "vi": "sản xuất → năng suất"},
    {"key": "f4", "head": "qualify", "en": "qualification", "vi": "đủ điều kiện → bằng cấp"},
]

SITTING_1 = [
    {"kind": "title", "hook": "Robot làm hết việc nhàm chán: tin vui hay tin buồn?", "lines": [
        {"say": "Robot làm hết những việc nhàm chán: đó là tin vui hay tin buồn?", "show": "hook"},
        {"say": "Bảy từ của buổi này là bảy từ bạn sẽ nghe trong nửa đầu bài: câu chuyện người Luddite và những dự đoán về tương lai việc làm."},
    ]},
    {"kind": "word", "headword": "automation", "lines": [
        {"say": "Automatic là tự động. Khi máy tự làm thay người, ta có tự động hóa. Bài nghe mở đầu bằng một buổi seminar về chủ đề này."},
    ]},
    {"kind": "word", "headword": "textile", "lines": [
        {"say": "Hàng dệt, ngành dệt. Cuộc cách mạng công nghiệp ở Anh bắt đầu từ ngành dệt, và những người Luddite là công nhân dệt."},
    ]},
    {"kind": "word", "headword": "threaten", "lines": [
        {"say": "Đe dọa. Trong bài, chàng trai nói anh hiểu vì sao những người Luddite cảm thấy bị đe dọa."},
        {"en": "I can see why the Luddites felt so threatened.", "vi": "Tôi hiểu vì sao những người Luddite cảm thấy bị đe dọa đến thế.", "gap": True},
    ]},
    {"kind": "word", "headword": "repetitive", "lines": [
        {"say": "Repeat là lặp lại. Những việc lặp đi lặp lại, nhàm chán, là việc robot được kỳ vọng sẽ làm thay con người."},
        {"en": "Work won't involve doing boring, repetitive tasks.", "vi": "Công việc sẽ không còn những việc nhàm chán, lặp đi lặp lại.", "gap": True},
    ]},
    {"kind": "word", "headword": "leisure", "lines": [
        {"say": "Thời gian rảnh, thời gian nghỉ ngơi. Để ý cách đọc kiểu Anh. Nghe thấy có thêm thời gian rảnh, bạn nghĩ ngay tới giờ làm việc ngắn lại."},
    ]},
    {"kind": "word", "headword": "unemployment", "lines": [
        {"say": "Employ là thuê người làm; thêm tiền tố un là không có việc. Thất nghiệp giảm, trong bài được nói thành thất nghiệp thấp hơn."},
        {"en": "What about lower unemployment?", "vi": "Còn chuyện thất nghiệp giảm thì sao?", "gap": True},
    ]},
    {"kind": "word", "headword": "retire", "lines": [
        {"say": "Nghỉ hưu. Một lựa chọn trong đề nói người ta sẽ muốn hoãn nghỉ hưu. Trong bài, người ta sẽ phải làm việc tới khi già hơn: bị buộc, không phải muốn."},
    ]},
    {"kind": "recap", "lines": [
        {"say": "Giờ nói lại các câu của buổi này. Nghe một câu, rồi nói to trong quãng nghỉ.", "show": "title"},
    ]},
    {"kind": "end", "next": "Tiếp theo: năm từ về các nghề xưa và nay.", "lines": [
        {"say": "Hết buổi từ thứ nhất. Buổi sau là năm từ của nửa sau bài nghe: các nghề thay đổi ra sao từ thế kỷ mười chín tới nay.", "show": "title"},
    ]},
]

SITTING_2 = [
    {"kind": "title", "hook": "Thế kỷ 19 có bao nhiêu người làm nông?", "lines": [
        {"say": "Bạn đoán thử: vào thế kỷ mười chín, bao nhiêu phần trăm dân số nước Anh làm nông?", "show": "hook"},
        {"say": "Câu trả lời có trong bài nghe. Trước đó là năm từ để nghe được phần các nghề xưa và nay."},
    ]},
    {"kind": "word", "headword": "productivity", "lines": [
        {"say": "Năng suất: làm ra bao nhiêu trong một khoảng thời gian. Kế toán bây giờ làm việc hiệu quả hơn nhiều, tức là năng suất tăng."},
    ]},
    {"kind": "word", "headword": "qualification", "lines": [
        {"say": "Bằng cấp, chứng chỉ. Trong bài có nói nhiều người tốt nghiệp đại học chọn làm hành chính, nhưng không ai nói nghề này sẽ đòi hỏi thêm bằng cấp."},
    ]},
    {"kind": "word", "headword": "census", "lines": [
        {"say": "Cuộc điều tra dân số. Cuộc điều tra năm 1871 cho thấy khoảng một phần tư dân số làm nông. Từ này chỉ cần nhận ra khi nghe."},
    ]},
    {"kind": "word", "headword": "lifespan", "lines": [
        {"say": "Life là đời sống, span là một khoảng: tuổi thọ. Ở thế kỷ mười chín, tuổi thọ ngắn nên hầu như không có nghề chăm sóc người già."},
        {"en": "People's lifespan was so much shorter.", "vi": "Tuổi thọ của con người ngắn hơn nhiều.", "gap": True},
    ]},
    {"kind": "word", "headword": "redundant", "lines": [
        {"say": "Thừa, không còn cần đến. Người Anh còn nói một người bị cho thôi việc vì công việc không còn nữa. Trong bài, công nghệ sẽ làm phần lớn công việc của nhân viên ngân hàng trở nên thừa."},
        {"en": "Technology will make most of the jobs they do now redundant.", "vi": "Công nghệ sẽ làm phần lớn công việc họ đang làm trở nên thừa.", "gap": True},
    ]},
    {"kind": "scene", "visual": "ref_table", "eyebrow": "Một họ từ", "title": "Biết từ gốc, nghe ra danh từ",
     "data": {"cols": ["Từ gốc", "Danh từ", "Nghĩa"], "rows": FAMILY, "rule": "Nghe được từ gốc trong một danh từ dài là hiểu được nó, dù chưa gặp bao giờ."}, "lines": [
        {"say": "Bốn danh từ dài của hai buổi này đều sinh ra từ một từ gốc ngắn. Automatic là tự động, thành sự tự động hóa.", "show": "f1"},
        {"say": "Employ là thuê người làm, thành tình trạng thất nghiệp.", "show": "f2"},
        {"say": "Produce là sản xuất, thành năng suất.", "show": "f3"},
        {"say": "Qualify là đủ điều kiện, thành bằng cấp.", "show": "f4"},
        {"say": "Khi nghe, danh từ dài trôi qua rất nhanh. Bắt được từ gốc ở giữa là hiểu được nó, dù bạn chưa gặp bao giờ.", "show": "rule"},
    ]},
    {"kind": "recap", "lines": [
        {"say": "Giờ nói lại các câu của buổi này. Nghe một câu, rồi nói to trong quãng nghỉ.", "show": "title"},
    ]},
    {"kind": "end", "next": "Tiếp theo: nghe bài The Luddites và chọn đáp án.", "lines": [
        {"say": "Hết buổi từ thứ hai. Giờ bạn nghe bài. Đọc câu hỏi trước, nghe lại bao nhiêu lần cũng được, rồi mới xem lời giải.", "show": "title"},
    ]},
]

# ============================================================ lecture 2: after listening

KEY_1 = [
    {"key": "k1", "head": "21–22", "en": "they didn't achieve anything", "vi": "= ineffective: không có tác dụng"},
    {"key": "k2", "head": "21–22", "en": "I can see why the Luddites felt so threatened", "vi": "= understandable: hiểu được"},
    {"key": "k3", "head": "23–24", "en": "lower unemployment? I'm not so sure about that", "vi": "nghi ngờ thất nghiệp giảm"},
    {"key": "k4", "head": "23–24", "en": "I can't see how people are about to have more leisure time", "vi": "nghi ngờ giờ làm ngắn lại"},
]
KEY_2 = [
    {"key": "j1", "head": "Kế toán", "en": "more of them than ever · far more efficient", "vi": "việc làm và năng suất đều tăng"},
    {"key": "j2", "head": "Thợ làm tóc", "en": "earning power has gone up · can afford to spend more", "vi": "thu nhập tăng, việc làm tăng mạnh"},
    {"key": "j3", "head": "Hành chính", "en": "much more responsibility and higher status", "vi": "vai trò thú vị hơn"},
    {"key": "j4", "head": "Làm nông", "en": "about 25% in 1871 · now less than 0.2%", "vi": "số người giảm mạnh"},
    {"key": "j5", "head": "Chăm sóc", "en": "this sector will see huge growth", "vi": "nhu cầu sẽ tăng mạnh"},
    {"key": "j6", "head": "Ngân hàng", "en": "technology will make most of the jobs redundant", "vi": "có nguy cơ mất việc"},
]
WHY_WRONG = [
    {"key": "w1", "wrong": "Hành chính: This job will require more qualifications.", "right": "A lot of graduates go in for this kind of work now.", "why": "Câu chỉ nói ai chọn nghề này, không nói nghề sẽ đòi hỏi thêm bằng cấp."},
    {"key": "w2", "wrong": "Chăm sóc: Higher disposable income has led to a huge increase in jobs.", "right": "this sector will see huge growth", "why": "Bài nói tương lai và vì tuổi thọ; nhận xét kia nói việc đã xảy ra và vì thu nhập."},
    {"key": "w3", "wrong": "Hưu trí: People will want to delay retiring.", "right": "most people will be expected to work until they're much older", "why": "Bị buộc làm lâu hơn, không phải muốn; và không ai nghi ngờ điều đó."},
]

POST = [
    {"kind": "title", "hook": "Làm đúng mà không biết vì sao đúng thì lần sau vẫn có thể sai.", "lines": [
        {"say": "Làm đúng mà không biết vì sao đúng thì lần sau vẫn có thể sai.", "show": "hook"},
        {"say": "Buổi này mình đối chiếu từng câu hỏi với đúng câu trong bài nghe. Chỉ xem câu đúng, không đọc đi đọc lại đáp án sai, để đầu óc không bị nhiễu."},
    ]},
    {"kind": "scene", "visual": "ref_table", "eyebrow": "Câu 21–24", "title": "Câu hỏi và cách bài nghe nói lại",
     "data": {"cols": ["Câu", "Bài nghe", "Ý"], "rows": KEY_1, "rule": "Đáp án là một cách nói khác của câu trong bài nghe, không phải chữ trùng."}, "lines": [
        {"say": "Câu hai mươi mốt và hai mươi hai hỏi hai ý kiến về những người Luddite. Ý thứ nhất: cô gái nói rốt cuộc họ chẳng đạt được gì, tức là hành động của họ không có tác dụng.", "show": "k1"},
        {"en": "Ultimately, they didn't achieve anything.", "gap": True},
        {"say": "Ý thứ hai: chàng trai nói anh hiểu vì sao họ cảm thấy bị đe dọa. Hiểu được thái độ của họ.", "show": "k2"},
        {"say": "Câu hai mươi ba và hai mươi bốn hỏi hai dự đoán bị nghi ngờ. Thứ nhất: thất nghiệp giảm. Cô gái nói thẳng là cô không chắc.", "show": "k3"},
        {"en": "I'm not so sure about that.", "gap": True},
        {"say": "Thứ hai: chàng trai không tin người ta sắp có thêm thời gian rảnh, vì ai cũng đang làm việc lâu hơn bao giờ hết. Thêm thời gian rảnh là cách nói lại của giờ làm ngắn hơn.", "show": "k4"},
        {"say": "Đáp án là một cách nói khác của câu trong bài nghe. Ít khi nó trùng chữ.", "show": "rule"},
    ]},
    {"kind": "scene", "visual": "ref_table", "eyebrow": "Câu 25–30", "title": "Sáu nghề, sáu nhận xét",
     "data": {"cols": ["Nghề", "Bài nghe", "Nhận xét"], "rows": KEY_2, "rule": "Ghép nghề với nhận xét bằng cả nội dung lẫn mốc thời gian."}, "lines": [
        {"say": "Kế toán: số người nhiều hơn bao giờ hết, và làm việc hiệu quả hơn nhiều. Việc làm tăng, năng suất cũng tăng.", "show": "j1"},
        {"say": "Thợ làm tóc: thu nhập của người ta tăng nên họ có tiền chi cho dịch vụ này. Số thợ tăng mạnh.", "show": "j2"},
        {"say": "Nhân viên hành chính: trước kia chỉ ghi lời đọc và đánh máy, bây giờ có nhiều trách nhiệm và vị trí cao hơn. Vai trò thú vị hơn.", "show": "j3"},
        {"say": "Người làm nông: năm 1871 khoảng một phần tư dân số, bây giờ chưa tới hai phần nghìn. Giảm rất mạnh.", "show": "j4"},
        {"say": "Nhân viên chăm sóc: ngành này sẽ tăng trưởng rất mạnh. Đây là dự đoán, nên chọn nhận xét nói về tương lai.", "show": "j5"},
        {"say": "Nhân viên ngân hàng: công nghệ sẽ làm phần lớn công việc của họ trở nên thừa. Có nguy cơ mất việc.", "show": "j6"},
        {"say": "Ghép nghề với nhận xét bằng cả nội dung lẫn mốc thời gian.", "show": "rule"},
    ]},
    {"kind": "scene", "visual": "fix_pairs", "eyebrow": "Vì sao sai", "title": "Ba lựa chọn dễ chọn nhầm",
     "data": {"rows": WHY_WRONG, "rule": "Nghe được chữ quen chưa đủ: phải khớp cả ý, cả lý do, cả mốc thời gian."}, "lines": [
        {"say": "Lựa chọn dễ nhầm thứ nhất: nghe thấy người tốt nghiệp đại học, nhiều bạn chọn nhận xét về bằng cấp. Nhưng câu đó chỉ nói ai chọn nghề này.", "show": "w1"},
        {"say": "Thứ hai: nghề chăm sóc có tăng mạnh, nhưng là sẽ tăng, và vì người ta sống lâu hơn. Nhận xét về thu nhập nói một việc đã xảy ra, vì một lý do khác.", "show": "w2"},
        {"say": "Thứ ba: người ta sẽ bị buộc làm việc tới khi già hơn. Bị buộc khác với muốn, và cả hai bạn đều không nghi ngờ điều đó.", "show": "w3"},
        {"say": "Nghe được chữ quen chưa đủ. Đáp án đúng phải khớp cả ý, cả lý do, cả mốc thời gian.", "show": "rule"},
    ]},
    {"kind": "end", "next": "Tiếp theo: viết vài câu về một nghề đang giảm và một nghề đang tăng ở Việt Nam.", "lines": [
        {"say": "Hết phần giảng. Bạn nghe lại bài một lần nữa, lần này vừa nghe vừa nhìn lời thoại. Rồi viết vài câu về một nghề đang giảm và một nghề đang tăng ở Việt Nam.", "show": "title"},
    ]},
]

S_WORDS = [
    ["automation", "textile", "threaten", "repetitive", "leisure", "unemployment", "retire"],
    ["productivity", "qualification", "census", "lifespan", "redundant"],
]
TITLES = ["Từ để nghe trước · Luddite và tương lai việc làm", "Từ để nghe trước · các nghề xưa và nay"]
LECTURES = [SITTING_1, SITTING_2]
LISTEN_TITLES = ["Nghe chủ động · chuẩn bị trước khi nghe", "Nghe lại · đối chiếu đáp án và cách nói lại"]


def reshape(sessions: list[dict]) -> list[dict]:
    """The two vocabulary sittings get their lecture and title; every other sitting is kept as built."""
    for i, lecture in enumerate(LECTURES):
        ses = sessions[i]
        words = [s["headword"] for s in lecture if s.get("kind") == "word"]
        assert words == S_WORDS[i], (i, words)
        assert sorted(words) == sorted(ses["vocab"]), (i, set(words) ^ set(ses["vocab"]))
        ses["lecture"] = lecture
        ses["title_vi"] = TITLES[i]
    return sessions


def finish(sessions: list[dict], bank: dict[str, list[dict]]) -> list[dict]:
    """The order of the day: prepare (lecture), the words, listen, go over the answers (lecture + writing)."""
    mine = next(s for s in sessions if s["title_vi"].startswith("Vận dụng"))
    pre = {"title_vi": LISTEN_TITLES[0], "lecture": PRE,
           "can_do_vi": "Sau buổi này bạn biết đọc câu hỏi trước, đoán cách nói lại, nghe thái độ của người nói và nhận ra bẫy về mốc thời gian.",
           "use_vi": "Part 3 có hai người nói; chuẩn bị trước giúp bạn biết phải nghe gì ở từng câu hỏi."}
    post = {"title_vi": LISTEN_TITLES[1], "lecture": POST, "check": list(mine["check"]),
            "can_do_vi": "Sau buổi này bạn giải thích được mỗi đáp án bằng đúng câu trong bài nghe, và vì sao các lựa chọn gần nghĩa vẫn sai.",
            "use_vi": "Đối chiếu đáp án với lời thoại là cách nhanh nhất để lần sau nghe ra cách nói lại."}
    vocab = [s for s in sessions if s.get("lecture") in LECTURES]
    rest = [s for s in sessions if s is not mine and s not in vocab]
    sessions[:] = [pre, *vocab, *rest, post]
    for s in sessions:
        assert len(s["title_vi"]) <= 70, s["title_vi"]
    return sessions

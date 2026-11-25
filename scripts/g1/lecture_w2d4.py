"""Week 2 · Day 4 (build day 24): eight tenses as one system, and three steps to choose a past tense. Two lectures
written by hand (lesson_audio.build_authored_lecture) and the day's sittings reshaped around them. Same format as
lecture_w2d3.py.

Sources: session 3 of the course, summary (docs/WEEK2_PLAN.md, day 4): the frame of eight core tenses (four present,
four past), the three-step procedure for choosing a past tense ((1) a chain of actions, a finished action, repetition,
a stative verb: past simple; (2) a temporary stretch cut into, or two actions at once: past continuous; (3) before a
past simple anchor: past perfect, then simple for result / experience / stative, continuous for duration / trace),
"grammar is a tool for what the speaker wants to say, not separate boxes", the guiding rule (unsure: past simple),
the exam answer next to everyday use (exercise D, item 10: had been listening / had listened / was listening), and
the Week 1 map of the four present tenses (two questions, four cells), which this day extends with a third question.
Not taught (not covered in class): used to, would, be / get used to.

Pronunciations: Oxford Learner's Dictionaries, British English, read 2026-11-25.
"""

PRON = {
    "share": "/ʃeə(r)/",
    "store": "/stɔː(r)/",
    "access": "/ˈækses/",
    "upload": "/ˌʌpˈləʊd/",
    "browse": "/braʊz/",
    "account": "/əˈkaʊnt/",
    "password": "/ˈpɑːswɜːd/",
    "storage": "/ˈstɔːrɪdʒ/",
    "user": "/ˈjuːzə(r)/",
    "privacy": "/ˈprɪvəsi/",
}

NOTES = {
    "share": "Quá khứ: shared, đuôi -ed đọc /d/. share something with someone.",
    "store": "Quá khứ: stored, đuôi -ed đọc /d/. Danh từ store còn có nghĩa là cửa hàng.",
    "access": "Quá khứ: accessed, đuôi -ed đọc /t/. Cũng là danh từ: have access to the Internet.",
    "upload": "Quá khứ: uploaded, đuôi -ed thêm một âm tiết /ɪd/. Trái nghĩa: download.",
    "browse": "Quá khứ: browsed, đuôi -ed đọc /d/. browse the Internet, browse in a shop.",
    "account": "create an account, log in to your account.",
    "password": "Chữ w không đọc: /ˈpɑːswɜːd/. change your password.",
    "storage": "run out of storage: hết dung lượng. Động từ gốc: store.",
    "user": "Người dùng một sản phẩm, một dịch vụ. Động từ gốc: use.",
    "privacy": "Tính từ: private /ˈpraɪvət/. Danh từ privacy đọc /ˈprɪvəsi/ theo Anh Anh.",
}

S1_WORDS = ["share", "store", "access", "upload", "browse"]
S2_WORDS = ["account", "password", "storage", "user", "privacy"]

ROW_HEADS = ["Chưa nối với việc trước", "Nối với việc trước · thêm have"]
COL_HEADS = ["Không nhấn tạm thời", "Nhấn tạm thời, quá trình"]
ROW_HEADS_PAST = ["Chưa nối với việc trước", "Nối với việc trước · thêm had"]

PRESENT = [
    {"key": "c1", "tense": "Hiện tại đơn", "form": "V / V-s", "at": "always", "en": "She lives in Hanoi.", "vi": "Chị ấy sống ở Hà Nội."},
    {"key": "c2", "tense": "Hiện tại tiếp diễn", "form": "am / is / are + V-ing", "at": "window", "en": "She is living in Hanoi now.", "vi": "Bây giờ chị ấy đang ở Hà Nội."},
    {"key": "c3", "tense": "Hiện tại hoàn thành", "form": "have / has + V3", "at": "span", "en": "I have studied the piano since 2003.", "vi": "Tôi học piano từ năm 2003."},
    {"key": "c4", "tense": "Hoàn thành tiếp diễn", "form": "have / has been + V-ing", "at": "span", "en": "I have been playing football for three hours.", "vi": "Tôi chơi bóng ba tiếng nay rồi."},
]

PAST = [
    {"key": "c1", "tense": "Quá khứ đơn", "form": "V2 / V-ed", "at": "point", "en": "Yesterday I played football at seven.", "vi": "Hôm qua lúc bảy giờ tôi đá bóng."},
    {"key": "c2", "tense": "Quá khứ tiếp diễn", "form": "was / were + V-ing", "at": "pwin", "en": "Yesterday I was playing football at seven.", "vi": "Hôm qua lúc bảy giờ tôi đang đá bóng."},
    {"key": "c3", "tense": "Quá khứ hoàn thành", "form": "had + V3", "at": "before", "en": "When I got to the station, the train had left.", "vi": "Khi tôi tới ga thì tàu đã chạy mất."},
    {"key": "c4", "tense": "Hoàn thành tiếp diễn", "form": "had been + V-ing", "at": "upto", "en": "We had been waiting for an hour when the bus came.", "vi": "Chúng tôi đã chờ một tiếng thì xe buýt tới."},
]

PAIRS = [
    {"key": "k1", "head": "Dấu vết", "en": "I was tired because I had been running.", "vi": "Cặp của: I'm tired because I have been running."},
    {"key": "k2", "head": "Than phiền", "en": "He was always leaving his clothes on the floor!", "vi": "Cặp của: He is always leaving his clothes on the floor!"},
    {"key": "k3", "head": "Lần đầu", "en": "It was the first time I had used this app.", "vi": "Cặp của: It's the first time I have used this app."},
]

STEPS = [
    {"key": "s1", "head": "Bước 1 · quá khứ đơn", "en": "I got up at six every morning last week.", "vi": "Chuỗi việc, việc đã khép lại, lặp lại, trạng thái."},
    {"key": "s2", "head": "Bước 2 · tiếp diễn", "en": "My cousin and I were playing on the computer when there was a power cut.", "vi": "Một khoảng tạm thời bị cắt ngang, hoặc hai việc song song."},
    {"key": "s3", "head": "Bước 3 · hoàn thành", "en": "When I got there, I realised I had left my judo suit at home.", "vi": "Xảy ra trước một mốc quá khứ đơn."},
]

FROZE = [
    {"key": "m1", "icon": "frozen", "at": "upto", "tense": "had been + V-ing · quá trình trước mốc", "en": "I had been watching the film for ten minutes when the screen froze.", "vi": "Nhấn quãng mười phút đã trôi qua."},
    {"key": "m2", "icon": "frozen", "at": "before", "tense": "had + V3 · việc xảy ra trước", "en": "I had watched ten minutes of the film when the screen froze.", "vi": "Nhấn phần phim đã xem xong."},
    {"key": "m3", "icon": "frozen", "at": "cut", "tense": "Tiếp diễn · khoảng lúc đó", "en": "I was watching the film when the screen froze.", "vi": "Nhấn việc đang diễn ra lúc màn hình treo."},
]

TRAPS = [
    {"key": "e1", "wrong": "When I got home, my brother has eaten all the pizza.", "right": "When I got home, my brother had eaten all the pizza.", "why": "Mốc là quá khứ: lùi have thành had."},
    {"key": "e2", "wrong": "I was tired because I have been running.", "right": "I was tired because I had been running.", "why": "Hai vế cùng nhìn từ một mốc đã qua."},
    {"key": "e3", "wrong": "Yesterday I have seen her.", "right": "Yesterday I saw her.", "why": "Có mốc đã qua: quá khứ đơn."},
    {"key": "e4", "wrong": "I had been knowing Lan for ten years when we started the company.", "right": "I had known Lan for ten years when we started the company.", "why": "know là động từ trạng thái."},
]

ANSWER = [
    {"key": "q1", "role": "Dựng cảnh", "tense": "Quá khứ tiếp diễn", "en": "Last summer I was travelling around Da Nang with two friends.", "vi": "Hè năm ngoái tôi đang đi du lịch quanh Đà Nẵng với hai người bạn."},
    {"key": "q2", "role": "Việc chính, lùi về trước", "tense": "Quá khứ đơn + had + V3", "en": "One evening we got lost because our phone battery had died.", "vi": "Một buổi tối chúng tôi bị lạc vì điện thoại đã hết pin."},
    {"key": "q3", "role": "Quá trình trước đó", "tense": "had been + V-ing", "en": "We had been walking for two hours, so we were very tired.", "vi": "Chúng tôi đã đi bộ suốt hai tiếng nên rất mệt."},
    {"key": "q4", "role": "Kết thúc", "tense": "Quá khứ đơn", "en": "Luckily, a shop owner let us charge the phone, and the map app showed us the way back.", "vi": "May mà một chủ cửa hàng cho chúng tôi sạc điện thoại, và ứng dụng bản đồ chỉ đường cho chúng tôi về."},
]

SITTING_1 = [
    {"kind": "title", "hook": "Tám thì: cần mấy câu hỏi để chọn đúng một thì?", "lines": [
        {"say": "Đến hôm nay bạn đã học đủ tám thì. Nếu chỉ được đặt vài câu hỏi để chọn đúng một thì, bạn cần mấy câu hỏi?", "show": "hook"},
        {"say": "Câu trả lời là ba. Buổi này dựng bản đồ tám thì từ ba câu hỏi đó, rồi ghép từng cặp hiện tại và quá khứ."},
    ]},
    {"kind": "scene", "visual": "tense_grid", "eyebrow": "Nhắc lại Tuần 1", "title": "Bốn ô nhìn từ bây giờ",
     "data": {"row_heads": ROW_HEADS, "col_heads": COL_HEADS, "cells": PRESENT,
              "rule": "Nối với việc trước: thêm have. Nhấn tạm thời, quá trình: thêm be và ing."}, "lines": [
        {"say": "Tuần trước, hai câu hỏi chia bốn thì hiện tại ra bốn ô. Câu hỏi thứ nhất: có nối với một việc trước đó không? Có thì xuống hàng dưới và thêm have.", "show": "rows"},
        {"say": "Câu hỏi thứ hai: có nhấn tạm thời, hay quá trình, không? Có thì sang cột phải và thêm be cùng đuôi ing.", "show": "cols"},
        {"say": "Bốn câu mẫu của tuần trước, mỗi câu một ô."},
        {"en": "She lives in Hanoi.", "vi": "Chị ấy sống ở Hà Nội.", "gap": True, "show": "c1", "recap": False},
        {"en": "She is living in Hanoi now.", "vi": "Bây giờ chị ấy đang ở Hà Nội.", "gap": True, "show": "c2", "recap": False},
        {"en": "I have studied the piano since 2003.", "vi": "Tôi học piano từ năm 2003.", "gap": True, "show": "c3", "recap": False},
        {"en": "I have been playing football for three hours.", "vi": "Tôi chơi bóng ba tiếng nay rồi.", "gap": True, "show": "c4", "recap": False},
        {"say": "Có nối với việc trước thì thêm have. Có nhấn tạm thời hay quá trình thì thêm be và ing.", "show": "rule"},
    ]},
    {"kind": "scene", "visual": "tense_grid", "eyebrow": "Câu hỏi thứ ba", "title": "Bốn ô nhìn từ một mốc quá khứ",
     "data": {"row_heads": ROW_HEADS_PAST, "col_heads": COL_HEADS, "cells": PAST,
              "rule": "Nhìn từ một mốc quá khứ: giữ hai câu hỏi cũ, lùi động từ chia đầu tiên về quá khứ."}, "lines": [
        {"say": "Câu hỏi thứ ba: nhìn từ bây giờ, hay từ một mốc trong quá khứ? Nếu từ một mốc quá khứ, bản đồ giữ nguyên hai câu hỏi cũ. Hàng dưới giờ thêm had.", "show": "rows"},
        {"say": "Cột phải vẫn là be cộng đuôi ing, nhưng be lùi thành was hoặc were.", "show": "cols"},
        {"say": "Ô thứ nhất: không nối, không nhấn tạm thời. Quá khứ đơn, một điểm trên trục."},
        {"en": "Yesterday I played football at seven.", "vi": "Hôm qua lúc bảy giờ tôi đá bóng.", "gap": True, "show": "c1"},
        {"say": "Ô thứ hai: nhấn khoảng tạm thời. Quá khứ tiếp diễn."},
        {"en": "Yesterday I was playing football at seven.", "vi": "Hôm qua lúc bảy giờ tôi đang đá bóng.", "gap": True, "show": "c2"},
        {"say": "Ô thứ ba: xảy ra trước một mốc quá khứ. Quá khứ hoàn thành."},
        {"en": "When I got to the station, the train had left.", "vi": "Khi tôi tới ga thì tàu đã chạy mất.", "gap": True, "show": "c3"},
        {"say": "Ô thứ tư: kéo dài tới một mốc quá khứ. Quá khứ hoàn thành tiếp diễn."},
        {"en": "We had been waiting for an hour when the bus came.", "vi": "Chúng tôi đã chờ một tiếng thì xe buýt tới.", "gap": True, "show": "c4"},
        {"say": "Nhìn từ một mốc quá khứ: giữ hai câu hỏi cũ, và lùi động từ chia đầu tiên về quá khứ, như ba cặp sau."},
        {"en": "lives, lived. am, was. have, had.", "recap": False},
        {"say": "Riêng quá khứ đơn còn là thì mặc định cho mọi việc đã xảy ra. Ba ô còn lại mới là cặp đúng nghĩa của ba ô hiện tại.", "show": "rule"},
    ]},
    {"kind": "scene", "visual": "ref_table", "eyebrow": "Từng cặp", "title": "Cùng nghĩa, khác mốc",
     "data": {"rows": PAIRS, "rule": "Cách dùng giữ nguyên; chỉ mốc nhìn đổi từ bây giờ sang một lúc đã qua."}, "lines": [
        {"say": "Mỗi thì quá khứ là cặp của một thì hiện tại. Cặp một: dấu vết. Hiện tại là tôi mệt vì vừa chạy. Lùi về một mốc đã qua, cả hai vế cùng lùi.", "show": "k1"},
        {"en": "I was tired because I had been running.", "vi": "Lúc đó tôi mệt vì vừa chạy.", "gap": True},
        {"say": "Cặp hai: than phiền với always, nhìn từ quá khứ.", "show": "k2"},
        {"en": "He was always leaving his clothes on the floor!", "vi": "Hồi đó nó cứ vứt quần áo dưới sàn!", "gap": True},
        {"say": "Cặp ba: mẫu lần đầu. Tuần này bạn đã gặp cả hai phiên bản.", "show": "k3"},
        {"en": "It was the first time I had used this app.", "vi": "Đó là lần đầu tôi dùng ứng dụng này.", "gap": True},
        {"say": "Cách dùng giữ nguyên; chỉ mốc nhìn đổi từ bây giờ sang một lúc đã qua. Nói được ở hiện tại là kể được ở quá khứ.", "show": "rule"},
    ]},
    {"kind": "word", "headword": "share", "lines": [{"say": "Năm động từ của buổi này là những việc bạn làm mỗi ngày trên mạng. Từ thứ nhất. Quá khứ là shared, đuôi ed giống played."}]},
    {"kind": "word", "headword": "store", "lines": [{"say": "Từ thứ hai: lưu trữ. Danh từ cùng chữ còn có nghĩa là cửa hàng."}]},
    {"kind": "word", "headword": "access", "lines": [{"say": "Từ thứ ba. Câu ví dụ có hai thì: không truy cập được, vì đã quên mật khẩu từ trước."}]},
    {"kind": "word", "headword": "upload", "lines": [{"say": "Từ thứ tư, trái nghĩa với download ở ngày hai. Câu ví dụ có while và thì tiếp diễn."}]},
    {"kind": "word", "headword": "browse", "lines": [{"say": "Từ cuối: lướt xem. Câu ví dụ là một việc đang diễn ra bị cắt ngang."}]},
    {"kind": "recap", "lines": [
        {"say": "Giờ nói lại các câu của buổi này. Nghe một câu, rồi nói to trong quãng nghỉ.", "show": "title"},
    ]},
    {"kind": "end", "next": "Tiếp theo: học thẻ và từ của buổi này, rồi làm bài.", "lines": [
        {"say": "Hết buổi một. Bạn học các thẻ và từ trong app, rồi làm bài. Buổi hai học ba bước chọn thì quá khứ khi làm bài, khác biệt giữa đáp án bài thi và điều bạn muốn nói, rồi kể một câu chuyện bằng bốn thì quá khứ.", "show": "title"},
    ]},
]

SITTING_2 = [
    {"kind": "title", "hook": "Đang xem phim thì màn hình bị treo: có mấy cách nói đúng?", "lines": [
        {"say": "Bạn đang xem phim thì màn hình bị treo. Khi làm bài, chọn thì thế nào; khi nói thật, có bao nhiêu cách kể lại câu này cho đúng?", "show": "hook"},
        {"say": "Buổi này học ba bước chọn thì quá khứ khi làm bài, rồi ba cách nói khi dùng thật, sửa bốn lỗi hay gặp, và kể một câu chuyện Part 2 bằng bốn thì quá khứ."},
    ]},
    {"kind": "scene", "visual": "ref_table", "eyebrow": "Khi làm bài", "title": "Ba bước chọn thì quá khứ",
     "data": {"rows": STEPS, "rule": "Không khớp bước 2 hay bước 3: chọn quá khứ đơn."}, "lines": [
        {"say": "Khi làm bài với một câu ở quá khứ, đi qua ba bước. Bước một: có chuỗi việc, việc đã khép lại, việc lặp lại, hay động từ trạng thái không? Có thì chọn quá khứ đơn.", "show": "s1"},
        {"en": "I got up at six every morning last week.", "vi": "Tuần trước sáng nào tôi cũng dậy lúc sáu giờ.", "gap": True},
        {"say": "Bước hai: có một khoảng tạm thời bị cắt ngang, hay hai việc song song không? Có thì chọn quá khứ tiếp diễn.", "show": "s2"},
        {"en": "My cousin and I were playing on the computer when there was a power cut.", "vi": "Tôi và em họ đang chơi máy tính thì mất điện.", "gap": True},
        {"say": "Bước ba: đã có một mốc quá khứ đơn chưa, và việc đang xét có xảy ra trước mốc đó không? Có thì chọn quá khứ hoàn thành. Rồi chọn tiếp: kết quả, trải nghiệm, trạng thái thì dùng dạng đơn; thời lượng, dấu vết thì dùng dạng tiếp diễn.", "show": "s3"},
        {"en": "When I got there, I realised I had left my judo suit at home.", "vi": "Khi tới nơi, tôi nhận ra mình đã để quên bộ đồ judo ở nhà.", "gap": True},
        {"say": "Và trước khi chọn, hãy đọc trọn cả câu, cả câu trước và câu sau. Không khớp bước hai hay bước ba thì chọn quá khứ đơn: xác suất đúng cao nhất.", "show": "rule"},
    ]},
    {"kind": "scene", "visual": "tense_timeline", "eyebrow": "Dùng thật", "title": "Một câu, ba cách nói",
     "data": {"question": "... when the screen froze.", "question_vi": "... thì màn hình bị treo.", "question_label": "Cùng một mốc",
              "answers": FROZE, "rule": "Ngoài đời, bạn muốn nhấn điều gì thì chọn thì đó. Bài thi: đi qua ba bước với cả câu."}, "lines": [
        {"say": "Mốc chung là lúc màn hình bị treo, chia quá khứ đơn.", "show": "q"},
        {"say": "Quá khứ bên trái, bây giờ ở vạch giữa.", "show": "axis"},
        {"say": "Cách một: nhấn quá trình đã kéo dài tới mốc đó, mười phút.", "show": "m1"},
        {"en": "I had been watching the film for ten minutes when the screen froze.", "vi": "Tôi đã xem suốt mười phút thì màn hình bị treo.", "gap": True},
        {"say": "Cách hai: nhấn phần việc đã xảy ra trước mốc.", "show": "m2"},
        {"en": "I had watched ten minutes of the film when the screen froze.", "vi": "Tôi đã xem xong mười phút đầu của phim thì màn hình bị treo.", "gap": True},
        {"say": "Cách ba: nhấn việc đang diễn ra ngay lúc đó.", "show": "m3"},
        {"en": "I was watching the film when the screen froze.", "vi": "Tôi đang xem phim thì màn hình bị treo.", "gap": True},
        {"say": "Cả ba đều đúng, mỗi câu nhấn một ý. Ngữ pháp là công cụ cho điều bạn muốn nói, không phải những chiếc hộp tách rời. Còn bài thi chỉ có một đáp án: đi qua ba bước với cả câu, không dựa vào một chữ đơn lẻ.", "show": "rule"},
    ]},
    {"kind": "scene", "visual": "fix_pairs", "eyebrow": "Lỗi thường gặp", "title": "Bốn lỗi khi trộn tám thì",
     "data": {"rows": TRAPS, "rule": "Một câu kể, một mốc nhìn. Có mốc đã qua: quá khứ đơn. know: dạng đơn."}, "lines": [
        {"say": "Bốn lỗi hay gặp khi trộn tám thì. Lỗi một: mốc là quá khứ nhưng vế sau vẫn dùng have.", "show": "e1"},
        {"en": "When I got home, my brother had eaten all the pizza.", "vi": "Khi tôi về đến nhà, em tôi đã ăn hết chỗ pizza.", "gap": True},
        {"say": "Lỗi hai: vế đầu đã lùi về quá khứ, vế sau thì chưa.", "show": "e2"},
        {"en": "I was tired because I had been running.", "vi": "Lúc đó tôi mệt vì vừa chạy.", "gap": True, "recap": False},
        {"say": "Lỗi ba: hiện tại hoàn thành đi với một mốc đã qua.", "show": "e3"},
        {"en": "Yesterday I saw her.", "vi": "Hôm qua tôi gặp cô ấy.", "gap": True},
        {"say": "Lỗi bốn: động từ trạng thái ở dạng tiếp diễn.", "show": "e4"},
        {"en": "I had known Lan for ten years when we started the company.", "vi": "Lúc chúng tôi mở công ty, tôi đã quen Lan được mười năm.", "gap": True, "recap": False},
        {"say": "Một câu kể, một mốc nhìn. Có mốc đã qua thì dùng quá khứ đơn. Động từ trạng thái như know giữ dạng đơn.", "show": "rule"},
    ]},
    {"kind": "word", "headword": "account", "lines": [{"say": "Trước khi kể chuyện, học năm danh từ của đời sống số. Từ thứ nhất: tài khoản."}]},
    {"kind": "word", "headword": "password", "lines": [{"say": "Từ thứ hai: mật khẩu. Chữ vê kép ở giữa không đọc."}]},
    {"kind": "word", "headword": "storage", "lines": [{"say": "Từ thứ ba, danh từ của store ở buổi trước: dung lượng lưu trữ."}]},
    {"kind": "word", "headword": "user", "lines": [{"say": "Từ thứ tư: người dùng. Câu ví dụ có had cộng quá khứ phân từ, với mốc là cuối năm đầu tiên của ứng dụng."}]},
    {"kind": "word", "headword": "privacy", "lines": [{"say": "Từ cuối: quyền riêng tư, một chủ đề rất hay gặp trong Writing Task 2 về công nghệ."}]},
    {"kind": "scene", "visual": "speaking_answer", "eyebrow": "IELTS Speaking Part 2", "title": "Một câu chuyện, bốn thì quá khứ",
     "data": {"question": "Describe a time when a piece of technology helped you.", "question_vi": "Kể về một lần một thiết bị công nghệ giúp bạn.",
              "short": "My phone helped me.", "parts": ANSWER,
              "rule": "Cảnh: tiếp diễn. Việc chính: quá khứ đơn. Việc trước đó: had + V3. Quá trình trước đó: had been + V-ing."}, "lines": [
        {"say": "Đề Part 2: kể về một lần một thiết bị công nghệ giúp bạn."},
        {"en": "Describe a time when a piece of technology helped you.", "show": "q"},
        {"say": "Một câu trả lời ngắn chưa phải là câu chuyện.", "show": "short"},
        {"say": "Câu một: dựng cảnh bằng thì tiếp diễn."},
        {"en": "Last summer I was travelling around Da Nang with two friends.", "vi": "Hè năm ngoái tôi đang đi du lịch quanh Đà Nẵng với hai người bạn.", "gap": True, "show": "q1"},
        {"say": "Câu hai: việc chính bằng quá khứ đơn, và lý do xảy ra trước đó bằng had cộng quá khứ phân từ."},
        {"en": "One evening we got lost because our phone battery had died.", "vi": "Một buổi tối chúng tôi bị lạc vì điện thoại đã hết pin.", "gap": True, "show": "q2"},
        {"say": "Câu ba: quá trình kéo dài trước đó, had been cộng đuôi ing."},
        {"en": "We had been walking for two hours, so we were very tired.", "vi": "Chúng tôi đã đi bộ suốt hai tiếng nên rất mệt.", "gap": True, "show": "q3"},
        {"say": "Câu bốn: kết thúc bằng quá khứ đơn."},
        {"en": "Luckily, a shop owner let us charge the phone, and the map app showed us the way back.", "vi": "May mà một chủ cửa hàng cho chúng tôi sạc điện thoại, và ứng dụng bản đồ chỉ đường cho chúng tôi về.", "gap": True, "show": "q4"},
        {"say": "Bốn câu, bốn thì quá khứ, mỗi thì một vai. Hãy viết lại câu chuyện này bằng một chuyện của chính bạn.", "show": "rule"},
    ]},
    {"kind": "recap", "lines": [
        {"say": "Giờ nói lại các câu của buổi này. Nghe một câu, rồi nói to trong quãng nghỉ.", "show": "title"},
    ]},
    {"kind": "end", "next": "Tiếp theo: học thẻ và từ, làm bài, rồi buổi 3 và bài luyện theo sách.", "lines": [
        {"say": "Hết phần giảng của ngày bốn, cũng là hết phần ngữ pháp của tuần. Bạn học các thẻ và từ trong app, làm bài, rồi sang buổi ba. Cuối ngày có tám câu luyện theo sách, mỗi câu chọn một trong bốn dạng quá khứ.", "show": "title"},
    ]},
]

RUBRIC = [
    {"criterion_vi": "Đúng đề: có cảnh, việc chính, việc xảy ra trước và kết thúc", "max": 1, "note_vi": "Fluency and coherence"},
    {"criterion_vi": "Dùng được bốn thì quá khứ, mỗi thì đúng vai trong câu chuyện", "max": 2, "note_vi": "Grammatical range"},
    {"criterion_vi": "Dạng động từ đúng; cả câu nhìn từ cùng một mốc", "max": 2, "note_vi": "Grammatical accuracy"},
]

CAP = 7  # a lecture sitting holds at most seven questions; the rest open sitting 3


def reshape(sessions: list[dict], exercise_ids: list[str], card_of: dict[str, int]) -> list[dict]:
    """Sitting 1 teaches cards 1-2 (the eight-tense map, present-past pairs) with five verbs; sitting 2 cards 3-5
    (the three steps, exam answer and intended meaning, a story in four past tenses) with five nouns; the
    production work is a third sitting without a lecture. The book's exercise follows as its own sitting."""
    pats = [g for s in sessions[:2] for g in s["grammar"]]
    allcheck = [i for s in sessions[:2] for i in s["check"]]
    s1, s2 = sessions[0], sessions[1]
    rest = sessions[2:]
    all_words = [w for s in sessions[:2] for w in s["vocab"]]
    assert sorted(all_words) == sorted(S1_WORDS + S2_WORDS), all_words
    s1["vocab"], s2["vocab"] = S1_WORDS, S2_WORDS
    s1["grammar"], s2["grammar"] = pats[:2], pats[2:]
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
    s1["check"], spill1 = pick(range(0, 2))
    s2["check"], spill2 = pick(range(2, len(pats)))
    moved = spill1 + spill2 + [i for i in allcheck if i not in quiz]
    s1["lecture"], s2["lecture"] = SITTING_1, SITTING_2
    s1["title_vi"] = "Buổi 1 · bản đồ tám thì, cặp hiện tại và quá khứ"
    s2["title_vi"] = "Buổi 2 · ba bước chọn thì, đáp án bài thi và ý muốn nói, kể chuyện"
    s1["can_do_vi"] = "Sau buổi này bạn đặt được một câu vào đúng ô của tám thì và chuyển một câu hiện tại sang cặp quá khứ của nó."
    s2["can_do_vi"] = "Sau buổi này bạn chọn được thì quá khứ theo ba bước, phân biệt được đáp án bài thi với điều mình muốn nhấn, tránh bốn lỗi khi trộn tám thì, và kể được một câu chuyện Speaking bằng bốn thì quá khứ."
    s3 = {
        "title_vi": "Buổi 3 · vận dụng: xếp câu, gõ, nghe chép, kể chuyện",
        "can_do_vi": "Sau buổi này bạn chọn đúng thì quá khứ theo ba bước, tự xếp và gõ đúng câu, nghe chép được câu trộn nhiều thì, và kể một chuyện của chính mình.",
        "use_vi": s1["use_vi"],
        "vocab": [],
        "check": moved,
    }
    assert set(s1["check"] + s2["check"] + moved) <= set(exercise_ids)
    return [s1, s2, s3] + rest

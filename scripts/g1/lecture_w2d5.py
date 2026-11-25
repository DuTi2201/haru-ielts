"""Week 2 · Day 5 (build day 25): change and technology, the vocabulary day. Five lectures written by hand
(lesson_audio.build_authored_lecture), one per word group; vocab_day() gives each of the first five sittings its
lecture and title. Same format as lecture_d7.py (the vocabulary day of Week 1).

Sources: session 4 of the course, stages 1-3 (docs/WEEK2_PLAN.md, day 5): the way to learn words (verbs and nouns
first; about ten a day, seen and rehearsed many times rather than crammed; a word stays when its idea is understood,
it is used and it comes back; learn the whole phrase), the thirty filtered words in groups (lasting; changing;
replacing; society; technology), and the elimination used in class: the preposition that goes with the word
(evolve into, influence on, persist in), time (potential is for what has not happened yet) and the range a word
combines with (amend a document, not a society). Corrected against the dictionaries as listed in the plan (items
9-15): decay also means a slow decline of buildings and districts; amend is used for documents and plans as well
as laws; for a person's state remain calm is the natural phrase; progress into exists (the final), it is only not
the word for a society developing; data is usually /ˈdeɪtə/ but other readings are not wrong.
Not taught: phrasal verbs and idioms (exercise E onwards).

Pronunciations: Oxford Learner's Dictionaries, British English, read 2026-11-25 (progress and shift as nouns,
as taught).
"""

PRON = {
    "endure": "/ɪnˈdjʊə(r)/",
    "last": "/lɑːst/",
    "maintain": "/meɪnˈteɪn/",
    "remain": "/rɪˈmeɪn/",
    "sustain": "/səˈsteɪn/",
    "persist": "/pəˈsɪst/",
    "shift": "/ʃɪft/",
    "modify": "/ˈmɒdɪfaɪ/",
    "transform": "/trænsˈfɔːm/",
    "reform": "/rɪˈfɔːm/",
    "adjust": "/əˈdʒʌst/",
    "distort": "/dɪˈstɔːt/",
    "evolve": "/ɪˈvɒlv/",
    "progress": "/ˈprəʊɡres/",
    "mature": "/məˈtʃʊə(r)/",
    "deteriorate": "/dɪˈtɪəriəreɪt/",
    "decay": "/dɪˈkeɪ/",
    "substitute": "/ˈsʌbstɪtjuːt/",
    "switch": "/swɪtʃ/",
    "radical": "/ˈrædɪkl/",
    "dynamic": "/daɪˈnæmɪk/",
    "uniform": "/ˈjuːnɪfɔːm/",
    "conservative": "/kənˈsɜːvətɪv/",
    "novel": "/ˈnɒvl/",
    "influence": "/ˈɪnfluəns/",
    "innovation": "/ˌɪnəˈveɪʃn/",
    "potential": "/pəˈtenʃl/",
    "primitive": "/ˈprɪmətɪv/",
    "technique": "/tekˈniːk/",
    "resource": "/rɪˈsɔːs/",
    "breakthrough": "/ˈbreɪkθruː/",
    "network": "/ˈnetwɜːk/",
    "data": "/ˈdeɪtə/",
    "console": "/ˈkɒnsəʊl/",
    "craft": "/krɑːft/",
}

NOTES = {
    "endure": "Đứng một mình, không cần tân ngữ. Danh từ: endurance (sức bền).",
    "last": "last + khoảng thời gian: last two hours. Không cần tân ngữ.",
    "maintain": "maintain + tân ngữ: maintain a balance, maintain a car (bảo dưỡng). Danh từ: maintenance.",
    "remain": "remain + tính từ: remain calm, remain open. Về trạng thái của một người, remain calm là cách nói tự nhiên.",
    "sustain": "sustain + tân ngữ cần sức lực để giữ lâu: sustain growth. Tính từ: sustainable (bền vững).",
    "persist": "persist in + V-ing: persist in asking. Tính từ: persistent.",
    "shift": "a shift in attitudes, a shift in opinion. Cũng là động từ: shift = chuyển dịch.",
    "modify": "Đổi một phần, vẫn là nó (như độ xe). Đổi toàn bộ: transform.",
    "transform": "Đổi toàn bộ, thành thứ khác hẳn. transform A into B.",
    "reform": "Cải cách một hệ thống, chính sách: reform the school system. Sửa bài viết: revise. Sửa điều khoản: amend.",
    "adjust": "Chỉnh một chi tiết cho vừa: adjust the seat. Thay đổi để hợp hoàn cảnh mới: adapt.",
    "distort": "distort the truth, distort the facts: bóp méo sự thật.",
    "evolve": "evolve into: dần phát triển thành. Danh từ: evolution.",
    "progress": "Danh từ không đếm được: make progress, a lot of progress (không thêm -s). Động từ nhấn âm hai: /prəˈɡres/.",
    "mature": "Nhấn âm hai: /məˈtʃʊə(r)/. Trái nghĩa: immature.",
    "deteriorate": "Không có tân ngữ: the weather deteriorated. Làm hỏng một thứ: spoil.",
    "decay": "Nghĩa gốc: mục rữa (lá, gỗ, răng). Nghĩa rộng: xuống cấp dần (urban decay).",
    "substitute": "B thế chỗ A, A mất đi. there's no substitute for …: không gì thay thế được.",
    "switch": "Hai thứ cùng còn, chỉ đổi chỗ: switch bags, switch seats.",
    "radical": "radical changes: thay đổi triệt để, tận gốc.",
    "dynamic": "Đối lập với fixed (cố định).",
    "uniform": "Danh từ là đồng phục; tính từ là đồng nhất, giống nhau hết.",
    "conservative": "Ngại thay đổi, muốn giữ lối cũ. Trái nghĩa gần: progressive.",
    "novel": "Danh từ là tiểu thuyết; tính từ là mới lạ: a novel idea.",
    "influence": "have an influence on somebody: có ảnh hưởng tới ai. Tính từ: influential.",
    "innovation": "Danh từ. Động từ: innovate. Tính từ: innovative.",
    "potential": "Điều có thể xảy ra nhưng chưa xảy ra: have a lot of potential.",
    "primitive": "Thô sơ, ở giai đoạn đầu: primitive tools.",
    "technique": "Danh từ, nhấn âm hai: /tekˈniːk/. Tính từ: technical.",
    "resource": "natural resources: tài nguyên thiên nhiên.",
    "breakthrough": "a breakthrough in medicine: bước đột phá.",
    "network": "a network of computers; social network.",
    "data": "Cách đọc phổ biến /ˈdeɪtə/; người ta cũng đọc /ˈdɑːtə/.",
    "console": "games console: máy chơi trò chơi điện tử.",
    "craft": "Làm thủ công khéo léo: crafted by hand.",
}


def _row(key, icon, head, en, vi):
    return {"key": key, "icon": icon, "head": head, "en": en, "vi": vi}


# ------------------------------------------------------------------ sitting 1: lasting and keeping
METHOD = [
    _row("m1", "repeat", "Nhẩm nhiều lần", "ten words a day", "Mỗi ngày khoảng mười từ, nhìn lại và nhẩm nhiều lần, không dồn vào một buổi."),
    _row("m2", "bulb", "Hiểu khái niệm, học cả cụm", "make progress", "Hiểu ý của từ và học luôn từ đi kèm. Ưu tiên động từ và danh từ."),
    _row("m3", "heart", "Dùng cho chuyện của mình", "a change in my life", "Từ dùng cho chuyện của chính mình và gặp lại nhiều lần thì nhớ lâu."),
]

LAST = [
    _row("l1", "hourglass", "last · kéo dài", "The meeting lasted two hours.", "Đo một khoảng thời gian."),
    _row("l2", "oak", "endure · bền lâu", "Some traditions endure for centuries.", "Vượt qua thời gian, thường là điều có giá trị."),
]

KEEP = [
    _row("k1", "scales", "maintain + tân ngữ", "We try to maintain a balance between work and rest.", "Duy trì một thứ: a balance, a car."),
    _row("k2", "calm_face", "remain + tính từ", "Please remain calm and wait for the next train.", "Vẫn ở nguyên trạng thái: calm, open."),
    _row("k3", "trend", "sustain + tân ngữ cần sức", "Can the company sustain this growth?", "Giữ lâu dài một thứ tốn sức: growth, effort."),
]

TRAPS_1 = [
    {"key": "e1", "wrong": "He persisted to ask the same question.", "right": "He persisted in asking the same question.", "why": "persist đi với in, rồi động từ thêm -ing."},
    {"key": "e2", "wrong": "It is hard to remain a balance between work and study.", "right": "It is hard to maintain a balance between work and study.", "why": "remain không có tân ngữ. Duy trì một thứ: maintain."},
]

SITTING_1 = [
    {"kind": "title", "hook": "Chiếc điện thoại năm năm trước của bạn còn không? Thay đổi nào ở lại lâu?", "lines": [
        {"say": "Chiếc điện thoại năm năm trước của bạn còn không? Có những thay đổi đến rồi đi, có những thay đổi ở lại rất lâu. Thay đổi nào ở lại lâu?", "show": "hook"},
        {"say": "Hôm nay học ba mươi từ về thay đổi và công nghệ, chia thành năm buổi nhỏ. Buổi một: kéo dài và giữ nguyên."},
    ]},
    {"kind": "scene", "visual": "picture_cards", "eyebrow": "Trước khi học", "title": "Học từ thế nào cho nhớ lâu",
     "data": {"rows": METHOD, "rule": "Mười từ một ngày, nhẩm nhiều lần, học cả cụm, dùng cho chuyện của mình."}, "lines": [
        {"say": "Trước hết là cách học. Đừng dồn ba mươi từ vào một tối. Hãy chia ra, mỗi ngày khoảng mười từ, nhìn lại và nhẩm nhiều lần trong ngày.", "show": "m1"},
        {"say": "Từ chỉ ở lại khi bạn hiểu khái niệm của nó, và biết nó đi với từ nào. Vì vậy hãy học cả cụm. Ưu tiên động từ và danh từ, vì đó là xương sống của câu.", "show": "m2"},
        {"say": "Cuối cùng, dùng từ cho chuyện của chính mình, và gặp lại nó nhiều lần. Đó là lúc từ vào trí nhớ dài hạn.", "show": "m3"},
        {"say": "Mười từ một ngày, nhẩm nhiều lần, học cả cụm, và dùng cho chuyện của mình.", "show": "rule"},
    ]},
    {"kind": "word", "headword": "endure", "lines": [
        {"say": "Một trào lưu trên mạng đến rồi đi trong một tuần. Nhưng có những truyền thống ở lại hàng trăm năm. Ở lại lâu bền, vượt qua thời gian: đó là endure. Neo vào last."},
    ]},
    {"kind": "word", "headword": "last", "lines": [
        {"say": "Last ở đây là động từ, nghĩa là kéo dài. Theo sau thường là một khoảng thời gian."},
    ]},
    {"kind": "scene", "visual": "picture_cards", "eyebrow": "Hai từ đứng một mình", "title": "last và endure",
     "data": {"rows": LAST, "rule": "Cả hai đứng một mình, không cần tân ngữ. Đo thời gian: last. Bền lâu, vượt thời gian: endure."}, "lines": [
        {"say": "Last đo một khoảng thời gian: cuộc họp kéo dài hai tiếng.", "show": "l1"},
        {"en": "The meeting lasted two hours.", "vi": "Cuộc họp kéo dài hai tiếng.", "gap": True},
        {"say": "Endure nói về điều bền lâu, vượt qua thời gian, thường là điều có giá trị.", "show": "l2"},
        {"en": "Some traditions endure for centuries.", "vi": "Có những truyền thống tồn tại hàng thế kỷ.", "gap": True},
        {"say": "Cả hai đứng một mình, không cần tân ngữ. Vì vậy khi chỗ trống không có tân ngữ theo sau, hãy nghĩ tới last hoặc endure.", "show": "rule"},
    ]},
    {"kind": "word", "headword": "maintain", "lines": [
        {"say": "Maintain là duy trì một thứ gì đó. Sau maintain luôn có tân ngữ: duy trì cái gì. Ví dụ, một sự cân bằng."},
    ]},
    {"kind": "word", "headword": "remain", "lines": [
        {"say": "Còn remain là vẫn ở nguyên trạng thái cũ. Sau remain thường là một tính từ, như calm, bình tĩnh."},
    ]},
    {"kind": "word", "headword": "sustain", "lines": [
        {"say": "Sustain cũng là duy trì, nhưng là giữ lâu dài một thứ cần sức lực. Một công ty tăng trưởng rất nhanh trong một năm. Câu hỏi là: giữ được tốc độ đó bao lâu?"},
    ]},
    {"kind": "scene", "visual": "picture_cards", "eyebrow": "Nhìn từ đứng sau", "title": "maintain, remain, sustain",
     "data": {"rows": KEEP, "rule": "Có tân ngữ: maintain hoặc sustain. Có tính từ: remain. Trạng thái của một người: remain calm."}, "lines": [
        {"say": "Ba từ đều là giữ, nhưng nhìn từ đứng sau để chọn. Maintain cộng một tân ngữ.", "show": "k1"},
        {"en": "We try to maintain a balance between work and rest.", "vi": "Chúng tôi cố duy trì cân bằng giữa làm việc và nghỉ ngơi.", "gap": True},
        {"say": "Remain cộng một tính từ.", "show": "k2"},
        {"en": "Please remain calm and wait for the next train.", "vi": "Xin hãy giữ bình tĩnh và chờ chuyến tàu sau.", "gap": True},
        {"say": "Sustain cộng một tân ngữ cần sức lực để giữ lâu, như tăng trưởng.", "show": "k3"},
        {"en": "Can the company sustain this growth?", "vi": "Công ty có duy trì được mức tăng trưởng này không?", "gap": True},
        {"say": "Có tân ngữ thì chọn maintain hoặc sustain. Có tính từ thì chọn remain. Nói về một người giữ bình tĩnh, cách tự nhiên là remain calm.", "show": "rule"},
    ]},
    {"kind": "word", "headword": "persist", "lines": [
        {"say": "Từ cuối của buổi này. Bạn đã nhắc một người ba lần, nhưng người đó vẫn cứ làm. Cứ khăng khăng tiếp tục, dù bị phản đối: đó là persist. Sau persist là giới từ in, rồi động từ thêm đuôi ing."},
    ]},
    {"kind": "scene", "visual": "fix_pairs", "eyebrow": "Lỗi thường gặp", "title": "Hai lỗi, hai cách sửa",
     "data": {"rows": TRAPS_1, "rule": "persist đi với in và động từ thêm -ing. remain không có tân ngữ."}, "lines": [
        {"say": "Lỗi thứ nhất: dùng to sau persist.", "show": "e1"},
        {"en": "He persisted in asking the same question.", "vi": "Anh ấy cứ khăng khăng hỏi mãi một câu.", "gap": True},
        {"say": "Lỗi thứ hai: dùng remain với một tân ngữ.", "show": "e2"},
        {"en": "It is hard to maintain a balance between work and study.", "vi": "Thật khó duy trì cân bằng giữa việc làm và việc học.", "gap": True},
        {"say": "Persist đi với in và động từ thêm đuôi ing. Remain không có tân ngữ.", "show": "rule"},
    ]},
    {"kind": "recap", "lines": [
        {"say": "Giờ nói lại các câu của buổi này. Nghe một câu, rồi nói to trong quãng nghỉ.", "show": "title"},
    ]},
    {"kind": "end", "next": "Tiếp theo: thay đổi một phần hay toàn bộ.", "lines": [
        {"say": "Hết buổi một. Sáu từ: endure, last, maintain, remain, sustain, persist. Hôm nay nhẩm lại vài lần, mỗi lần nhìn từ đứng sau nó. Buổi hai nói về thay đổi một phần hay toàn bộ.", "show": "title"},
    ]},
]

# ------------------------------------------------------------------ sitting 2: changing a part or the whole
PART = [
    _row("t1", "gear", "modify · đổi một phần", "He modified his motorbike with new lights.", "Thay bộ đèn, chiếc xe vẫn là chiếc xe đó."),
    _row("t2", "butterfly", "transform · đổi toàn bộ", "The Internet has transformed the way we study.", "Đổi đến mức thành một thứ khác hẳn."),
]

TEXTS = [
    _row("f1", "gavel", "reform · hệ thống", "The country reformed its tax system.", "Hệ thống, chính sách."),
    _row("f2", "doc", "revise · bài viết", "Please revise your report before Friday.", "Bài viết, báo cáo, bài học."),
    _row("f3", "pencil_sheet", "amend · điều khoản", "They amended the contract.", "Một điều khoản trong văn bản, luật, kế hoạch."),
]

FIT = [
    _row("j1", "slider", "adjust · chỉnh cho vừa", "You can adjust the brightness of the screen.", "Chỉnh một chi tiết nhỏ."),
    _row("j2", "refresh", "adapt · thích nghi", "Small shops must adapt or they will close.", "Thay đổi để hợp với hoàn cảnh mới, để tồn tại."),
]

TRAPS_2 = [
    {"key": "e1", "wrong": "We need to amend our society.", "right": "We need to reform our society.", "why": "amend dùng cho văn bản, kế hoạch. Thay đổi một hệ thống, một xã hội: reform."},
    {"key": "e2", "wrong": "Moving to the city modified my whole life.", "right": "Moving to the city transformed my whole life.", "why": "Cả cuộc sống đổi khác: transform. modify chỉ đổi một phần."},
]

SITTING_2 = [
    {"kind": "title", "hook": "Độ lại chiếc xe và đổi hẳn sang xe khác: tiếng Anh dùng cùng một từ không?", "lines": [
        {"say": "Độ lại chiếc xe và đổi hẳn sang xe khác: tiếng Anh dùng cùng một từ không?", "show": "hook"},
        {"say": "Không. Buổi hai phân biệt thay đổi một phần với thay đổi toàn bộ, và xem mỗi từ đi với thứ gì."},
    ]},
    {"kind": "word", "headword": "shift", "lines": [
        {"say": "Mở đầu bằng một danh từ. Mười năm trước, học trực tuyến bị coi là học tạm. Bây giờ nhiều người chủ động chọn nó. Thái độ đã dịch chuyển: đó là shift. Giới từ đi kèm là in."},
        {"en": "There has been a shift in attitudes.", "vi": "Thái độ đã có sự chuyển dịch.", "gap": True},
    ]},
    {"kind": "word", "headword": "modify", "lines": [
        {"say": "Ở Việt Nam có chữ độ xe: thay bộ đèn, thay bánh, nhưng chiếc xe vẫn là chiếc xe đó. Sửa đổi một phần: đó là modify."},
    ]},
    {"kind": "word", "headword": "transform", "lines": [
        {"say": "Còn transform là biến đổi toàn bộ, đến mức thành một thứ khác hẳn. Như con sâu thành con bướm."},
    ]},
    {"kind": "scene", "visual": "picture_cards", "eyebrow": "Một phần hay toàn bộ", "title": "modify và transform",
     "data": {"rows": PART, "rule": "Đổi một phần, vẫn là nó: modify. Đổi toàn bộ, thành thứ khác: transform."}, "lines": [
        {"say": "Modify: thay một phần, chiếc xe vẫn là chiếc xe.", "show": "t1"},
        {"en": "He modified his motorbike with new lights.", "vi": "Anh ấy độ lại xe máy bằng bộ đèn mới.", "gap": True},
        {"say": "Transform: đổi toàn bộ. Internet làm cách học của chúng ta khác hẳn.", "show": "t2"},
        {"en": "The Internet has transformed the way we study.", "vi": "Internet đã thay đổi hoàn toàn cách chúng ta học.", "gap": True},
        {"say": "Đổi một phần, vẫn là nó: modify. Đổi toàn bộ, thành thứ khác: transform.", "show": "rule"},
    ]},
    {"kind": "word", "headword": "reform", "lines": [
        {"say": "Reform là cải cách. Thứ được cải cách là một hệ thống, một chính sách: hệ thống trường học, hệ thống thuế, hệ thống nhà tù."},
    ]},
    {"kind": "scene", "visual": "picture_cards", "eyebrow": "Sửa cái gì", "title": "reform, revise, amend",
     "data": {"rows": TEXTS, "rule": "Hệ thống: reform. Bài viết: revise. Điều khoản trong văn bản, luật, kế hoạch: amend. Không ai amend một xã hội."}, "lines": [
        {"say": "Ba từ đều là sửa đổi, và cách chọn là nhìn thứ được sửa. Reform: một hệ thống.", "show": "f1"},
        {"en": "The country reformed its tax system.", "vi": "Nước này đã cải cách hệ thống thuế.", "gap": True},
        {"say": "Revise: một bài viết, một bản báo cáo. Revise còn có nghĩa là ôn bài.", "show": "f2"},
        {"en": "Please revise your report before Friday.", "vi": "Hãy sửa lại bản báo cáo trước thứ Sáu.", "gap": True},
        {"say": "Amend: sửa một điều khoản trong văn bản. Hay gặp nhất là luật và hợp đồng, nhưng cũng dùng cho kế hoạch.", "show": "f3"},
        {"en": "They amended the contract.", "vi": "Họ đã sửa đổi hợp đồng.", "gap": True},
        {"say": "Hệ thống thì reform. Bài viết thì revise. Điều khoản thì amend. Không ai amend một xã hội.", "show": "rule"},
    ]},
    {"kind": "word", "headword": "adjust", "lines": [
        {"say": "Adjust là chỉnh một chi tiết nhỏ cho vừa: độ cao của ghế, độ sáng của màn hình."},
    ]},
    {"kind": "scene", "visual": "picture_cards", "eyebrow": "Chỉnh hay thích nghi", "title": "adjust và adapt",
     "data": {"rows": FIT, "rule": "Chỉnh một chi tiết cho vừa: adjust. Thay đổi để hợp hoàn cảnh mới, để tồn tại: adapt."}, "lines": [
        {"say": "Adjust: chỉnh một chi tiết.", "show": "j1"},
        {"en": "You can adjust the brightness of the screen.", "vi": "Bạn có thể chỉnh độ sáng của màn hình.", "gap": True},
        {"say": "Adapt: thay đổi chính mình để hợp với hoàn cảnh mới, để tồn tại. Một cửa hàng nhỏ khi siêu thị mở ngay bên cạnh.", "show": "j2"},
        {"en": "Small shops must adapt or they will close.", "vi": "Cửa hàng nhỏ phải thích nghi, nếu không sẽ đóng cửa.", "gap": True},
        {"say": "Chỉnh một chi tiết thì adjust. Thay đổi để tồn tại thì adapt.", "show": "rule"},
    ]},
    {"kind": "word", "headword": "distort", "lines": [
        {"say": "Từ cuối. Hãy nghĩ tới tấm gương ở khu vui chơi: người đứng trước nó bị kéo dài ra, méo mó. Bóp méo: đó là distort. Một bài báo cũng có thể bóp méo sự thật."},
    ]},
    {"kind": "scene", "visual": "fix_pairs", "eyebrow": "Lỗi thường gặp", "title": "Chọn từ theo thứ được thay đổi",
     "data": {"rows": TRAPS_2, "rule": "Nhìn thứ được thay đổi: một xã hội thì reform, cả cuộc sống thì transform."}, "lines": [
        {"say": "Lỗi thứ nhất: dùng amend cho một xã hội.", "show": "e1"},
        {"en": "We need to reform our society.", "vi": "Chúng ta cần cải cách xã hội.", "gap": True},
        {"say": "Lỗi thứ hai: dùng modify khi cả cuộc sống đổi khác.", "show": "e2"},
        {"en": "Moving to the city transformed my whole life.", "vi": "Chuyển lên thành phố đã thay đổi hoàn toàn cuộc sống của tôi.", "gap": True},
        {"say": "Luôn nhìn thứ được thay đổi. Một xã hội thì reform. Cả cuộc sống thì transform.", "show": "rule"},
    ]},
    {"kind": "recap", "lines": [
        {"say": "Giờ nói lại các câu của buổi này. Nghe một câu, rồi nói to trong quãng nghỉ.", "show": "title"},
    ]},
    {"kind": "end", "next": "Tiếp theo: đi lên, đi xuống và thay thế.", "lines": [
        {"say": "Hết buổi hai. Sáu từ: shift, modify, transform, reform, adjust, distort. Buổi ba nói về những thay đổi đi lên, đi xuống, và thay chỗ cho nhau.", "show": "title"},
    ]},
]

# ------------------------------------------------------------------ sitting 3: up, down and replacing
UP = [
    {"key": "e1", "wrong": "Mobile phones have progressed into small computers.", "right": "Mobile phones have evolved into small computers.", "why": "Dần phát triển thành một thứ mới: evolve into. progress into là tiến vào một giai đoạn, như vòng chung kết."},
    {"key": "e2", "wrong": "We have made a lot of progresses.", "right": "We have made a lot of progress.", "why": "progress là danh từ không đếm được: không có a, không thêm -s."},
]

DOWN = [
    _row("d1", "cloud_down", "deteriorate · tự xấu đi", "The weather deteriorated in the afternoon.", "Không có tân ngữ."),
    _row("d2", "leaf_decay", "decay · mục rữa, xuống cấp", "When trees fall, they slowly decay.", "Gốc: lá, gỗ, răng. Rộng: nhà cửa, khu phố."),
    _row("d3", "rain", "spoil · làm hỏng", "I hope the rain didn't spoil your holiday.", "Có tân ngữ: làm hỏng một thứ."),
]

SWAP = [
    _row("s1", "sub_board", "substitute · thế chỗ", "There is no substitute for hard work.", "Cái mới vào, cái cũ mất đi."),
    _row("s2", "swap", "switch · tráo đổi", "Someone switched our bags at the airport.", "Hai thứ cùng còn, chỉ đổi chỗ."),
]

SITTING_3 = [
    {"kind": "title", "hook": "Cái gì lớn dần, cái gì xấu dần, cái gì bị thay chỗ?", "lines": [
        {"say": "Cái gì lớn dần, cái gì xấu dần, cái gì bị thay chỗ?", "show": "hook"},
        {"say": "Buổi ba có bảy từ. Mỗi từ đi với một giới từ hay một kiểu câu riêng, và đó chính là chỗ bài thi hay hỏi."},
    ]},
    {"kind": "word", "headword": "evolve", "lines": [
        {"say": "Chiếc điện thoại cục gạch, qua hai mươi năm, dần thành chiếc máy tính trong túi. Phát triển từng bước, rồi thành một thứ mới: đó là evolve. Luôn nhớ giới từ into."},
    ]},
    {"kind": "word", "headword": "progress", "lines": [
        {"say": "Progress là sự tiến bộ. Đây là danh từ không đếm được, động từ đi kèm là make. Danh từ nhấn âm đầu."},
        {"en": "We have made a lot of progress.", "vi": "Chúng tôi đã tiến bộ rất nhiều.", "gap": True},
    ]},
    {"kind": "scene", "visual": "fix_pairs", "eyebrow": "Đi lên", "title": "evolve into, make progress",
     "data": {"rows": UP, "rule": "Thành một thứ mới: evolve into. Tiến bộ: make progress, không thêm -s."}, "lines": [
        {"say": "Lỗi thứ nhất: dùng progress khi một thứ dần thành thứ khác.", "show": "e1"},
        {"en": "Mobile phones have evolved into small computers.", "vi": "Điện thoại di động đã dần trở thành những chiếc máy tính nhỏ.", "gap": True},
        {"say": "Progress into vẫn có, nhưng là tiến vào một giai đoạn, như một đội bóng vào vòng chung kết. Lỗi thứ hai: thêm đuôi số nhiều cho progress.", "show": "e2"},
        {"say": "Thành một thứ mới thì evolve into. Tiến bộ thì make progress, không có đuôi số nhiều.", "show": "rule"},
    ]},
    {"kind": "word", "headword": "mature", "lines": [
        {"say": "Mature là chín chắn, trưởng thành. Một người dùng kinh nghiệm để bình tĩnh tìm cách giải quyết. Để ý cách đọc: trọng âm rơi vào âm thứ hai."},
    ]},
    {"kind": "word", "headword": "deteriorate", "lines": [
        {"say": "Giờ đến chiều đi xuống. Deteriorate là xấu đi, kém đi: thời tiết, sức khỏe, một mối quan hệ. Động từ này không có tân ngữ."},
    ]},
    {"kind": "word", "headword": "decay", "lines": [
        {"say": "Decay, nghĩa gốc là mục rữa: lá cây, gỗ, răng. Nghĩa rộng là xuống cấp dần, như một khu phố cũ không ai sửa sang."},
    ]},
    {"kind": "scene", "visual": "picture_cards", "eyebrow": "Đi xuống", "title": "deteriorate, decay, spoil",
     "data": {"rows": DOWN, "rule": "Tự xấu đi: deteriorate. Mục rữa, xuống cấp dần: decay. Làm hỏng một thứ: spoil, có tân ngữ."}, "lines": [
        {"say": "Deteriorate: tự xấu đi, không có tân ngữ.", "show": "d1"},
        {"en": "The weather deteriorated in the afternoon.", "vi": "Buổi chiều thời tiết xấu đi.", "gap": True},
        {"say": "Decay: mục rữa, xuống cấp dần theo thời gian.", "show": "d2"},
        {"en": "When trees fall, they slowly decay.", "vi": "Khi cây đổ, chúng mục dần.", "gap": True},
        {"say": "Spoil thì khác: làm hỏng một thứ, nên luôn có tân ngữ. Cơn mưa làm hỏng kỳ nghỉ.", "show": "d3"},
        {"en": "I hope the rain didn't spoil your holiday.", "vi": "Mong là cơn mưa không làm hỏng kỳ nghỉ của bạn.", "gap": True},
        {"say": "Tự xấu đi thì deteriorate. Mục rữa thì decay. Làm hỏng một thứ thì spoil, có tân ngữ.", "show": "rule"},
    ]},
    {"kind": "word", "headword": "substitute", "lines": [
        {"say": "Huấn luyện viên đưa một cầu thủ vào sân, và một cầu thủ khác rời sân. Người mới thế chỗ, người cũ không còn ở đó: đó là substitute. Cụm rất hay dùng: không gì thay thế được."},
        {"en": "There's no substitute for experience.", "vi": "Không gì thay thế được kinh nghiệm.", "gap": True},
    ]},
    {"kind": "word", "headword": "switch", "lines": [
        {"say": "Còn switch là tráo đổi. Hai thứ vẫn còn đó, chỉ đổi chỗ cho nhau. Như hai chiếc túi giống hệt nhau bị cầm nhầm ở sân bay."},
    ]},
    {"kind": "scene", "visual": "picture_cards", "eyebrow": "Thay thế", "title": "substitute và switch",
     "data": {"rows": SWAP, "rule": "Cái mới vào, cái cũ mất đi: substitute. Hai thứ cùng còn, chỉ đổi chỗ: switch."}, "lines": [
        {"say": "Substitute: cái mới thế chỗ, cái cũ mất đi.", "show": "s1"},
        {"en": "There is no substitute for hard work.", "vi": "Không gì thay thế được sự chăm chỉ.", "gap": True},
        {"say": "Switch: hai thứ cùng còn, chỉ đổi chỗ.", "show": "s2"},
        {"en": "Someone switched our bags at the airport.", "vi": "Ai đó đã tráo túi của chúng tôi ở sân bay.", "gap": True},
        {"say": "Cái cũ mất đi thì substitute. Hai thứ cùng còn thì switch.", "show": "rule"},
    ]},
    {"kind": "recap", "lines": [
        {"say": "Giờ nói lại các câu của buổi này. Nghe một câu, rồi nói to trong quãng nghỉ.", "show": "title"},
    ]},
    {"kind": "end", "next": "Tiếp theo: những từ tả một xã hội đổi thay.", "lines": [
        {"say": "Hết buổi ba. Bảy từ: evolve, progress, mature, deteriorate, decay, substitute, switch. Buổi bốn kể chuyện một xã hội thay đổi, với tám từ để tả nó.", "show": "title"},
    ]},
]

# ------------------------------------------------------------------ sitting 4: a society that changes
BRITAIN = [
    {"key": "p1", "icon": "same_houses", "label": "Trước chiến tranh", "kind": "bg", "en": "Society was fairly uniform and conservative.", "vi": "Xã hội khá đồng nhất và bảo thủ."},
    {"key": "p2", "icon": "bolt", "label": "Chiến tranh", "kind": "event", "en": "The war brought radical changes.", "vi": "Chiến tranh mang lại thay đổi triệt để."},
    {"key": "p3", "icon": "trend", "label": "Xu hướng", "kind": "chain", "en": "Society became more dynamic.", "vi": "Xã hội năng động hơn."},
    {"key": "p4", "icon": "sparkle", "label": "Giới trẻ", "kind": "chain", "en": "Novel ideas had a great influence on young people.", "vi": "Những ý tưởng mới lạ ảnh hưởng lớn tới giới trẻ."},
]

FAMILY = [
    {"key": "i1", "head": "innovate · động từ", "en": "Companies must innovate to survive.", "vi": "đổi mới"},
    {"key": "i2", "head": "innovation · danh từ", "en": "Online banking was a real innovation.", "vi": "sự đổi mới; cái mới"},
    {"key": "i3", "head": "innovative · tính từ", "en": "New and innovative music appeared.", "vi": "sáng tạo, đổi mới"},
]

TIME = [
    {"key": "e1", "wrong": "After the war, Britain underwent potential changes.", "right": "After the war, Britain underwent radical changes.", "why": "underwent: thay đổi đã xảy ra. potential chỉ điều chưa xảy ra."},
    {"key": "e2", "wrong": "Music has a great influence to young people.", "right": "Music has a great influence on young people.", "why": "influence đi với on."},
]

SITTING_4 = [
    {"kind": "title", "hook": "Một xã hội đang yên ổn, rồi đổi khác hẳn. Tả sự đổi khác đó bằng từ nào?", "lines": [
        {"say": "Một xã hội đang yên ổn, rồi đổi khác hẳn. Tả sự đổi khác đó bằng từ nào?", "show": "hook"},
        {"say": "Buổi bốn bắt đầu bằng một câu chuyện có thật: nước Anh trước và sau Chiến tranh thế giới thứ hai."},
    ]},
    {"kind": "scene", "visual": "story_strip", "eyebrow": "Một câu chuyện", "title": "Nước Anh đổi thay",
     "data": {"frame": "strip", "panels": BRITAIN, "rule": "Bốn khung, sáu từ: uniform, conservative, radical, dynamic, novel, influence."}, "lines": [
        {"say": "Trước chiến tranh, người Anh tin rằng lối sống của họ sẽ kéo dài mãi. Mọi người chung niềm tin, chung giá trị: xã hội đồng nhất và bảo thủ.", "show": "p1"},
        {"en": "Society was fairly uniform and conservative.", "vi": "Xã hội khá đồng nhất và bảo thủ.", "gap": True},
        {"say": "Rồi chiến tranh đến, và mọi thứ thay đổi tận gốc.", "show": "p2"},
        {"en": "The war brought radical changes.", "vi": "Chiến tranh mang lại thay đổi triệt để.", "gap": True},
        {"say": "Xu hướng là rời xa những vai trò cố định, hướng tới một xã hội luôn vận động.", "show": "p3"},
        {"en": "Society became more dynamic.", "vi": "Xã hội năng động hơn.", "gap": True},
        {"say": "Những ý tưởng mới lạ, âm nhạc và thời trang mới, ảnh hưởng mạnh tới giới trẻ.", "show": "p4"},
        {"en": "Novel ideas had a great influence on young people.", "vi": "Những ý tưởng mới lạ ảnh hưởng lớn tới giới trẻ.", "gap": True},
        {"say": "Bốn khung tranh, sáu từ. Giờ mình đi từng từ.", "show": "rule"},
    ]},
    {"kind": "word", "headword": "uniform", "lines": [
        {"say": "Uniform, ta quen với nghĩa đồng phục. Làm tính từ, nó nghĩa là đồng nhất, giống nhau hết. Như một xã hội mà ai cũng chung niềm tin."},
    ]},
    {"kind": "word", "headword": "conservative", "lines": [
        {"say": "Conservative là bảo thủ, ngại thay đổi, muốn giữ lối cũ. Như ông bà không muốn đổi cách nấu một món ăn truyền thống."},
    ]},
    {"kind": "word", "headword": "radical", "lines": [
        {"say": "Radical là triệt để, đi tận gốc. Gốc của từ này trong tiếng La-tinh chính là rễ cây: thay đổi tới tận rễ."},
    ]},
    {"kind": "word", "headword": "dynamic", "lines": [
        {"say": "Dynamic là năng động, luôn vận động. Đối lập với fixed, cố định."},
    ]},
    {"kind": "word", "headword": "novel", "lines": [
        {"say": "Novel ta quen là tiểu thuyết. Làm tính từ, novel nghĩa là mới lạ, chưa ai làm. Neo vào new."},
    ]},
    {"kind": "word", "headword": "influence", "lines": [
        {"say": "Influence là ảnh hưởng. Giới từ đi kèm là on: ảnh hưởng lên ai, lên cái gì."},
    ]},
    {"kind": "word", "headword": "innovation", "lines": [
        {"say": "Innovation là sự đổi mới, hoặc một cái mới được tạo ra. Người học hay nhầm từ loại của nhóm từ này."},
    ]},
    {"kind": "scene", "visual": "ref_table", "eyebrow": "Một gốc, ba từ loại", "title": "innovate, innovation, innovative",
     "data": {"cols": ["Từ", "Câu"], "rows": FAMILY, "rule": "Sau a real cần danh từ: innovation. Trước danh từ cần tính từ: innovative."}, "lines": [
        {"say": "Động từ: innovate, đổi mới.", "show": "i1"},
        {"en": "Companies must innovate to survive.", "vi": "Các công ty phải đổi mới để tồn tại.", "gap": True},
        {"say": "Danh từ: innovation.", "show": "i2"},
        {"en": "Online banking was a real innovation.", "vi": "Ngân hàng trực tuyến là một sự đổi mới thực sự.", "gap": True},
        {"say": "Tính từ: innovative, đứng trước danh từ.", "show": "i3"},
        {"en": "New and innovative music appeared.", "vi": "Âm nhạc mới và sáng tạo xuất hiện.", "gap": True},
        {"say": "Nhìn vị trí để chọn từ loại. Sau a real cần danh từ. Trước danh từ cần tính từ.", "show": "rule"},
    ]},
    {"kind": "word", "headword": "potential", "lines": [
        {"say": "Từ cuối, cũng là chìa khóa để loại đáp án. Potential là tiềm năng: điều có thể xảy ra, nhưng chưa xảy ra."},
    ]},
    {"kind": "scene", "visual": "fix_pairs", "eyebrow": "Loại đáp án", "title": "Theo thời gian và theo giới từ",
     "data": {"rows": TIME, "rule": "Việc đã xảy ra thì không dùng potential. influence đi với on."}, "lines": [
        {"say": "Cách loại thứ nhất: theo thời gian. Underwent nghĩa là đã trải qua, nên không dùng potential.", "show": "e1"},
        {"en": "After the war, Britain underwent radical changes.", "vi": "Sau chiến tranh, nước Anh trải qua những thay đổi triệt để.", "gap": True},
        {"say": "Cách loại thứ hai: theo giới từ đi kèm.", "show": "e2"},
        {"en": "Music has a great influence on young people.", "vi": "Âm nhạc có ảnh hưởng lớn tới giới trẻ.", "gap": True},
        {"say": "Việc đã xảy ra thì không dùng potential. Influence đi với on.", "show": "rule"},
    ]},
    {"kind": "recap", "lines": [
        {"say": "Giờ nói lại các câu của buổi này. Nghe một câu, rồi nói to trong quãng nghỉ.", "show": "title"},
    ]},
    {"kind": "end", "next": "Tiếp theo: từ về công nghệ, rồi làm bài.", "lines": [
        {"say": "Hết buổi bốn. Tám từ: uniform, conservative, radical, dynamic, novel, influence, innovation, potential. Buổi năm là nhóm từ về công nghệ.", "show": "title"},
    ]},
]

# ------------------------------------------------------------------ sitting 5: technology
PAIRS = [
    _row("c1", "gear", "technique · technical", "Beta testing is a common technique.", "technique là danh từ; technical là tính từ: technical problems."),
    _row("c2", "magnifier", "experiment · experience", "Scientists did an experiment.", "experiment là thí nghiệm; experience là trải nghiệm, kinh nghiệm."),
]

SITTING_5 = [
    {"kind": "title", "hook": "Trò chơi điện tử ba mươi năm trước trông thế nào so với bây giờ?", "lines": [
        {"say": "Trò chơi điện tử ba mươi năm trước trông thế nào so với bây giờ?", "show": "hook"},
        {"say": "Buổi cuối có ba từ cần dùng được, và năm từ chỉ cần nhận ra khi đọc."},
    ]},
    {"kind": "word", "headword": "primitive", "lines": [
        {"say": "Vài khối vuông nhảy trên màn hình đen trắng. So với trò chơi bây giờ, trò chơi đời đầu trông thật thô sơ: đó là primitive."},
    ]},
    {"kind": "word", "headword": "technique", "lines": [
        {"say": "Technique là kỹ thuật, phương pháp làm một việc. Đây là danh từ, nhấn âm thứ hai. Tính từ là technical."},
    ]},
    {"kind": "word", "headword": "resource", "lines": [
        {"say": "Resource là tài nguyên, nguồn lực. Cụm hay gặp nhất trong bài thi là tài nguyên thiên nhiên."},
        {"en": "Water is a precious natural resource.", "vi": "Nước là một tài nguyên thiên nhiên quý giá.", "gap": True},
    ]},
    {"kind": "scene", "visual": "picture_cards", "eyebrow": "Cặp dễ nhầm", "title": "Một chữ khác, nghĩa khác",
     "data": {"rows": PAIRS, "rule": "technique là danh từ, technical là tính từ. Thí nghiệm là experiment, trải nghiệm là experience."}, "lines": [
        {"say": "Cặp thứ nhất: technique là danh từ, technical là tính từ, đứng trước một danh từ.", "show": "c1"},
        {"en": "Beta testing is a common technique.", "vi": "Thử nghiệm beta là một phương pháp phổ biến.", "gap": True},
        {"say": "Cặp thứ hai người học hay nhầm: experiment là thí nghiệm, experience là trải nghiệm.", "show": "c2"},
        {"en": "Scientists did an experiment.", "vi": "Các nhà khoa học đã làm một thí nghiệm.", "gap": True},
        {"say": "Technique là danh từ, technical là tính từ. Thí nghiệm là experiment, trải nghiệm là experience.", "show": "rule"},
    ]},
    {"kind": "word", "headword": "breakthrough", "lines": [
        {"say": "Năm từ còn lại chỉ cần nhận ra khi đọc. Breakthrough: bước đột phá, như một phát minh làm mạng nhanh hơn và rẻ hơn."},
    ]},
    {"kind": "word", "headword": "network", "lines": [
        {"say": "Network: mạng lưới. Internet là một mạng lưới khổng lồ của những chiếc máy tính nối với nhau."},
    ]},
    {"kind": "word", "headword": "data", "lines": [
        {"say": "Data: dữ liệu. Cách đọc phổ biến nhất bắt đầu bằng âm đây. Người ta cũng đọc khác, và không cách đọc nào bị coi là sai."},
    ]},
    {"kind": "word", "headword": "console", "lines": [
        {"say": "Console: chiếc máy chơi trò chơi điện tử nối với màn hình."},
    ]},
    {"kind": "word", "headword": "craft", "lines": [
        {"say": "Craft làm động từ: chế tác bằng tay, rất khéo léo. Như những dụng cụ cổ được làm hoàn toàn bằng tay."},
    ]},
    {"kind": "recap", "lines": [
        {"say": "Giờ nói lại các câu của buổi này. Nghe một câu, rồi nói to trong quãng nghỉ.", "show": "title"},
    ]},
    {"kind": "end", "next": "Tiếp theo: làm bài tập, rồi chọn 5 đến 10 từ yêu thích và viết câu của bạn.", "lines": [
        {"say": "Hết phần giảng của ngày năm. Bây giờ bạn làm bài trong app: chọn đáp án trước, rồi tự gõ. Với mỗi câu, hãy loại phương án sai bằng giới từ, bằng thời gian, bằng thứ mà từ đi kèm. Cuối cùng, chọn năm đến mười từ bạn thích nhất, và viết hai câu về một thay đổi trong cuộc sống của chính bạn.", "show": "title"},
    ]},
]

S_WORDS = [
    ["endure", "last", "maintain", "remain", "sustain", "persist"],
    ["shift", "modify", "transform", "reform", "adjust", "distort"],
    ["evolve", "progress", "mature", "deteriorate", "decay", "substitute", "switch"],
    ["radical", "dynamic", "uniform", "conservative", "novel", "influence", "innovation", "potential"],
    ["primitive", "technique", "resource", "breakthrough", "network", "data", "console", "craft"],
]

TITLES = [
    "Buổi 1 · kéo dài và giữ nguyên; cách học từ cho nhớ lâu",
    "Buổi 2 · thay đổi một phần hay toàn bộ",
    "Buổi 3 · đi lên, đi xuống và thay thế",
    "Buổi 4 · một xã hội đổi thay",
    "Buổi 5 · công nghệ; năm từ chỉ cần nhận ra",
]
LECTURES = [SITTING_1, SITTING_2, SITTING_3, SITTING_4, SITTING_5]

RUBRIC = None  # the vocabulary day has no speaking card; "Câu của tôi" keeps the default checklist


def reshape(sessions: list[dict]) -> list[dict]:
    """The five vocabulary sittings get their lecture and title; every other sitting is kept as built."""
    for i, lecture in enumerate(LECTURES):
        ses = sessions[i]
        words = [s["headword"] for s in lecture if s.get("kind") == "word"]
        assert words == S_WORDS[i] or sorted(words) == sorted(S_WORDS[i]), (i, words)
        assert sorted(words) == sorted(ses["vocab"]), (i, set(words) ^ set(ses["vocab"]))
        ses["lecture"] = lecture
        ses["title_vi"] = TITLES[i]
        assert len(ses["title_vi"]) <= 70
    return sessions

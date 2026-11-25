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
Checked line by line against the detailed notes of session 4 (stages 1-3): the teacher's filtered list of thirty
(he sent it in the chat after each exercise: make progress, have influence on and natural resource as whole phrases;
broadband and the other narrow words left out), his three-step way of learning words (filter verbs and nouns; ten a
day rehearsed into short-term memory; the English concept, part of speech, preposition and phrase plus 10-15 meetings
into long-term memory), one Vietnamese word for five English ones (change, shift, modify, substitute, switch), his
images (a car that is modified, a Vietnamese uniform society, evolve from living things to a society, a games console
looked up as a picture), substitute as "B takes A's place and A is gone", remain (no object, + adjective) against
maintain (an object, effort from outside: a balance, my grades, a car), persist translated by its connotation (cố chấp
with a bad action, kiên trì with a good aim), the clues inside the text (fixed -> dynamic, New and -> innovative), his
three ways to eliminate (preposition, time, range), the part-of-speech mistakes (a noun after will; technical after a)
and the pronunciation he corrected (mature, experience, substitute, console, data, technique).
Not taught: phrasal verbs and idioms (exercise E onwards); breakthrough, network, craft, broadband are only met in the
exercises.

Pronunciations: Oxford Learner's Dictionaries, British English, read 2026-11-25 (shift as a noun, progress in make progress,
as taught; the three phrases put together from their words' entries).
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
    "make progress": "/meɪk ˈprəʊɡres/",
    "mature": "/məˈtʃʊə(r)/",
    "deteriorate": "/dɪˈtɪəriəreɪt/",
    "decay": "/dɪˈkeɪ/",
    "substitute": "/ˈsʌbstɪtjuːt/",
    "switch": "/swɪtʃ/",
    "uniform": "/ˈjuːnɪfɔːm/",
    "conservative": "/kənˈsɜːvətɪv/",
    "radical": "/ˈrædɪkl/",
    "dynamic": "/daɪˈnæmɪk/",
    "novel": "/ˈnɒvl/",
    "have an influence on": "/hæv ən ˈɪnfluəns ɒn/",
    "innovation": "/ˌɪnəˈveɪʃn/",
    "potential": "/pəˈtenʃl/",
    "primitive": "/ˈprɪmətɪv/",
    "technique": "/tekˈniːk/",
    "natural resource": "/ˌnætʃrəl rɪˈsɔːs/",
}

NOTES = {
    "endure": "Nghĩa tồn tại lâu bền: đứng một mình. endure + tân ngữ là nghĩa khác: chịu đựng (endure pain). Danh từ: endurance.",
    "last": "last + khoảng thời gian: last two hours. Cùng nghĩa với endure ở chỗ kéo dài theo thời gian.",
    "maintain": "Cần tân ngữ, có nỗ lực từ bên ngoài: maintain a balance, maintain my grades, maintain a car (bảo dưỡng). Danh từ: maintenance.",
    "remain": "Không cần tân ngữ; + tính từ: remain calm. Trạng thái tự giữ nguyên.",
    "sustain": "sustain growth: giữ được một mức tăng trưởng lâu dài. Tính từ: sustainable (bền vững).",
    "persist": "persist in + V-ing. Việc xấu: cố chấp (persist in annoying people); mục tiêu tốt: kiên trì. Tính từ: persistent.",
    "shift": "Thay đổi lớn, bước ngoặt: a shift in attitudes. Cũng là động từ.",
    "modify": "Đổi một phần, vẫn là nó: make modifications to a car (độ xe). Đổi toàn bộ: transform.",
    "transform": "Biến đổi toàn bộ: transform my life. transform A into B.",
    "reform": "Cải cách hệ thống, chính sách: reform the prison system. It's time we reformed …",
    "adjust": "Chỉnh cho vừa (adjust the chair); người: adjust to a new job. Thích nghi để tồn tại: adapt.",
    "distort": "Bóp méo thông tin, sự thật, hình ảnh: distort the truth.",
    "evolve": "evolve into: dần phát triển thành. Từ sinh vật đến xã hội. Danh từ: evolution.",
    "make progress": "progress không đếm được: không nói a progress, không thêm -s. Danh từ nhấn âm đầu.",
    "mature": "Nhấn âm hai: /məˈtʃʊə(r)/. Trái nghĩa: immature.",
    "deteriorate": "Không có tân ngữ: the situation has deteriorated. Làm hỏng một thứ: spoil.",
    "decay": "Thứ có sự sống: cây, lá, thịt, răng; không nói máy móc, sắt thép. Nghĩa rộng: khu phố, nhà cửa xuống cấp dần.",
    "substitute": "B thế chỗ A, A không còn. there's no substitute for …: không gì thay thế được.",
    "switch": "Tráo đổi: hai thứ cùng còn, chỉ đổi chỗ (switch bags). Cũng là chuyển sang: switch to.",
    "uniform": "Danh từ là đồng phục; tính từ là đồng nhất: a uniform society, chung đặc điểm và giá trị.",
    "conservative": "Bảo thủ, giữ lề lối cũ: a conservative society.",
    "radical": "radical changes: thay đổi triệt để, tận gốc. Gốc La-tinh nghĩa là rễ.",
    "dynamic": "Luôn vận động; đối lập với fixed (cố định).",
    "novel": "Danh từ là tiểu thuyết; tính từ là mới lạ: novel and exciting.",
    "have an influence on": "have a great influence on young people. Tính từ: influential.",
    "innovation": "Danh từ. Động từ: innovate. Tính từ: innovative (New and innovative).",
    "potential": "Điều chưa xảy ra: have a lot of potential. Việc đã xảy ra thì không dùng potential.",
    "primitive": "Sơ khai, thô sơ: primitive games, primitive tools.",
    "technique": "Danh từ, nhấn âm hai: /tekˈniːk/ (= method). Tính từ: technical /ˈteknɪkl/.",
    "natural resource": "Học cả cụm: tài nguyên thiên nhiên. Số nhiều: natural resources.",
}


def _row(key, icon, head, en, vi):
    return {"key": key, "icon": icon, "head": head, "en": en, "vi": vi}


# ------------------------------------------------------------------ sitting 1: how to learn; lasting and keeping
METHOD = [
    _row("m1", "checklist", "Bước 1 · lọc", "verbs and nouns first", "Ưu tiên động từ và danh từ, xương sống của câu. Chia mỗi ngày khoảng mười từ."),
    _row("m2", "repeat", "Bước 2 · trí nhớ ngắn hạn", "rehearsal", "Mỗi ngày rút danh sách ra nhìn mặt chữ, đọc nhẩm nhiều lần. Không dồn vào một buổi."),
    _row("m3", "bulb", "Bước 3 · trí nhớ dài hạn", "concept, phrase, use", "Hiểu khái niệm, từ loại, giới từ, cụm đi kèm; gặp lại và dùng nhiều lần."),
]

CONCEPT = [
    {"key": "c1", "head": "change · nói chung", "en": "become different, a little or completely", "vi": "thay đổi"},
    {"key": "c2", "head": "shift · bước ngoặt", "en": "a big change in what people think", "vi": "thay đổi"},
    {"key": "c3", "head": "modify · một phần", "en": "change some parts, not the whole thing", "vi": "thay đổi"},
    {"key": "c4", "head": "substitute · thế chỗ", "en": "B takes the place of A, and A is gone", "vi": "thay thế"},
    {"key": "c5", "head": "switch · tráo đổi", "en": "A and B change places; both are still there", "vi": "thay thế"},
]

LAST = [
    _row("l1", "hourglass", "last · kéo dài", "The meeting lasted two hours.", "Đo một khoảng thời gian."),
    _row("l2", "oak", "endure · bền lâu", "Some traditions endure for centuries.", "Vượt qua thời gian, thường là điều có giá trị."),
]

KEEP = [
    _row("k1", "scales", "maintain + tân ngữ", "I try to maintain a balance between work and rest.", "Phải bỏ công giữ một thứ: a balance, my grades, a car."),
    _row("k2", "calm_face", "remain + tính từ", "The important thing is to remain calm.", "Không có tân ngữ: tự giữ nguyên trạng thái."),
    _row("k3", "trend", "sustain + tân ngữ", "Can the company sustain this growth?", "Giữ được lâu một mức tăng trưởng, một nỗ lực."),
]

TONE = [
    _row("p1", "angry", "việc xấu · cố chấp", "You'll regret it if you persist in annoying people.", "Đi với việc làm phiền người khác: không dịch là kiên trì."),
    _row("p2", "runner", "mục tiêu tốt · kiên trì", "She persisted in practising every day.", "Đi với một mục tiêu tốt: kiên trì, không bỏ cuộc."),
]

TRAPS_1 = [
    {"key": "e1", "wrong": "Few of these changes will really innovation.", "right": "Few of these changes will really endure.", "why": "Sau will là động từ; innovation là danh từ."},
    {"key": "e2", "wrong": "It is hard to remain a balance between work and study.", "right": "It is hard to maintain a balance between work and study.", "why": "remain không có tân ngữ: dùng maintain."},
    {"key": "e3", "wrong": "He persisted to ask the same question.", "right": "He persisted in asking the same question.", "why": "persist đi với in, rồi động từ thêm -ing."},
]

SITTING_1 = [
    {"kind": "title", "hook": "Change, shift, modify, substitute, switch: tra từ điển Anh–Việt đều ra một chữ. Vậy chọn thế nào?", "lines": [
        {"say": "Năm từ: change, shift, modify, substitute, switch. Tra từ điển Anh Việt, cả năm đều ra một chữ: thay đổi, hoặc thay thế. Vậy khi làm bài, bạn chọn thế nào?", "show": "hook"},
        {"say": "Hôm nay học ba mươi từ về thay đổi và công nghệ, chia năm buổi. Buổi một: cách học từ, rồi nhóm từ kéo dài và giữ nguyên."},
    ]},
    {"kind": "scene", "visual": "picture_cards", "eyebrow": "Trước khi học", "title": "Ba bước để từ ở lại lâu",
     "data": {"rows": METHOD, "rule": "Không từ nào vào thẳng trí nhớ dài hạn. Tra mười lần chưa nhớ thì tra đến lần thứ mười lăm."}, "lines": [
        {"say": "Một tuần có ba mươi đến bốn mươi từ mới. Đừng học tràn lan như nhau. Bước một là lọc: ưu tiên động từ và danh từ, vì đó là xương sống của câu. Tính từ, trạng từ học sau.", "show": "m1"},
        {"say": "Không thông tin nào đi thẳng vào trí nhớ dài hạn. Bước hai: mỗi ngày viết ra khoảng mười từ, thỉnh thoảng rút ra nhìn mặt chữ và đọc nhẩm. Tiếng Anh gọi việc lặp lại này là rehearsal. Nó giữ từ trong trí nhớ ngắn hạn.", "show": "m2"},
        {"say": "Bước ba: từ chỉ ở lại lâu khi bạn hiểu khái niệm của nó, biết từ loại, giới từ và cụm đi kèm, rồi gặp lại nó nhiều lần trong bài đọc và tự đặt câu.", "show": "m3"},
        {"say": "Không có đường tắt. Tra mười lần chưa nhớ, thì tra đến lần thứ mười lăm.", "show": "rule"},
    ]},
    {"kind": "scene", "visual": "ref_table", "eyebrow": "Học bằng khái niệm", "title": "Một chữ tiếng Việt, năm từ tiếng Anh",
     "data": {"cols": ["Từ", "Khái niệm tiếng Anh"], "rows": CONCEPT, "rule": "Nghĩa tiếng Việt chỉ là bước đầu. Phân biệt từ bằng khái niệm tiếng Anh."}, "lines": [
        {"say": "Quay lại câu hỏi đầu buổi. Change là thay đổi nói chung, một phần hay toàn bộ đều được.", "show": "c1"},
        {"say": "Shift là một thay đổi lớn, một bước ngoặt, thường trong cách người ta nghĩ.", "show": "c2"},
        {"say": "Modify chỉ đổi một vài phần, không đổi toàn bộ.", "show": "c3"},
        {"say": "Substitute: có cái cũ và cái mới; cái mới đè vào chỗ cái cũ, và cái cũ không còn nữa.", "show": "c4"},
        {"en": "B takes the place of A, and A is gone.", "vi": "B thế chỗ A, và A không còn nữa.", "gap": True, "recap": False},
        {"say": "Switch: hai thứ đổi chỗ cho nhau, cả hai vẫn còn đó.", "show": "c5"},
        {"say": "Dịch sang tiếng Việt, sắc thái mất đi rất nhiều. Lúc đầu có thể học nghĩa tiếng Việt, nhưng muốn phân biệt được thì phải hiểu khái niệm bằng tiếng Anh.", "show": "rule"},
    ]},
    {"kind": "word", "headword": "endure", "lines": [
        {"say": "Vào nhóm thứ nhất: kéo dài và giữ nguyên. Một trào lưu trên mạng đến rồi đi trong một tuần. Nhưng có những truyền thống ở lại hàng trăm năm. Ở lại lâu bền, vượt qua thời gian: đó là endure."},
    ]},
    {"kind": "word", "headword": "last", "lines": [
        {"say": "Last ở đây là động từ, nghĩa là kéo dài, cùng nhóm nghĩa với endure. Theo sau thường là một khoảng thời gian."},
    ]},
    {"kind": "scene", "visual": "picture_cards", "eyebrow": "Hai từ đứng một mình", "title": "last và endure",
     "data": {"rows": LAST, "rule": "Với nghĩa này, cả hai đứng một mình. Đo thời gian: last. Bền lâu, vượt thời gian: endure."}, "lines": [
        {"say": "Last đo một khoảng thời gian: cuộc họp kéo dài hai tiếng.", "show": "l1"},
        {"en": "The meeting lasted two hours.", "vi": "Cuộc họp kéo dài hai tiếng.", "gap": True},
        {"say": "Endure nói về điều bền lâu, vượt qua thời gian.", "show": "l2"},
        {"en": "Some traditions endure for centuries.", "vi": "Có những truyền thống tồn tại hàng thế kỷ.", "gap": True},
        {"say": "Với nghĩa này, cả hai đứng một mình, không cần tân ngữ. Vì vậy khi chỗ trống không có tân ngữ theo sau, hãy nghĩ tới last hoặc endure.", "show": "rule"},
    ]},
    {"kind": "word", "headword": "maintain", "lines": [
        {"say": "Maintain là duy trì một thứ. Sau maintain luôn có tân ngữ, và người làm phải bỏ công từ bên ngoài để giữ nó: giữ cân bằng, giữ điểm số, bảo dưỡng chiếc xe."},
    ]},
    {"kind": "word", "headword": "remain", "lines": [
        {"say": "Còn remain là tự giữ nguyên trạng thái cũ. Remain không nhận tân ngữ, mà thường đi thẳng với một tính từ, như calm, bình tĩnh."},
    ]},
    {"kind": "word", "headword": "sustain", "lines": [
        {"say": "Sustain cũng là duy trì: giữ được lâu một mức độ, như tốc độ tăng trưởng. Một công ty tăng trưởng rất nhanh trong một năm. Câu hỏi là: giữ được tốc độ đó bao lâu?"},
    ]},
    {"kind": "scene", "visual": "picture_cards", "eyebrow": "Nhìn từ đứng sau", "title": "maintain, remain, sustain",
     "data": {"rows": KEEP, "rule": "Có tân ngữ: maintain hoặc sustain. Có tính từ: remain. Người giữ bình tĩnh: remain calm."}, "lines": [
        {"say": "Thử hỏi: có nói remain một sự cân bằng được không? Không. Hãy nhìn từ đứng sau để chọn. Maintain cộng một tân ngữ.", "show": "k1"},
        {"en": "I try to maintain a balance between work and rest.", "vi": "Tôi cố duy trì cân bằng giữa làm việc và nghỉ ngơi.", "gap": True},
        {"say": "Remain cộng một tính từ.", "show": "k2"},
        {"en": "The important thing is to remain calm.", "vi": "Điều quan trọng là giữ bình tĩnh.", "gap": True},
        {"say": "Sustain cộng một tân ngữ, như mức tăng trưởng.", "show": "k3"},
        {"en": "Can the company sustain this growth?", "vi": "Công ty có duy trì được mức tăng trưởng này không?", "gap": True},
        {"say": "Có tân ngữ thì chọn maintain hoặc sustain. Có tính từ thì chọn remain. Nói về một người giữ bình tĩnh, hãy nói remain calm.", "show": "rule"},
    ]},
    {"kind": "word", "headword": "persist", "lines": [
        {"say": "Từ cuối của buổi này. Bạn đã nhắc một người ba lần, người đó vẫn cứ làm. Cứ tiếp tục, dù bị phản đối: đó là persist. Sau persist là giới từ in, rồi động từ thêm đuôi ing."},
    ]},
    {"kind": "scene", "visual": "picture_cards", "eyebrow": "Dịch theo sắc thái", "title": "persist: cố chấp hay kiên trì?",
     "data": {"rows": TONE, "rule": "Dịch theo việc đi kèm: việc xấu là cố chấp, mục tiêu tốt là kiên trì."}, "lines": [
        {"say": "Persist nên dịch là gì? Câu này đi với một việc xấu: làm phiền người khác. Không ai ghép chữ kiên trì, vốn tích cực, với một việc xấu. Chữ hợp nhất là cố chấp.", "show": "p1"},
        {"en": "You'll regret it if you persist in annoying people.", "vi": "Bạn sẽ hối hận nếu cứ cố chấp làm phiền người khác.", "gap": True},
        {"say": "Khi đi với một mục tiêu tốt, persist mới là kiên trì.", "show": "p2"},
        {"en": "She persisted in practising every day.", "vi": "Cô ấy kiên trì luyện tập mỗi ngày.", "gap": True},
        {"say": "Dịch theo việc đi kèm. Việc xấu thì cố chấp, mục tiêu tốt thì kiên trì.", "show": "rule"},
    ]},
    {"kind": "scene", "visual": "fix_pairs", "eyebrow": "Lỗi thường gặp", "title": "Ba lỗi, ba cách sửa",
     "data": {"rows": TRAPS_1, "rule": "Nhìn từ loại và từ đứng sau."}, "lines": [
        {"say": "Lỗi thứ nhất: đặt danh từ vào chỗ cần động từ. Sau will phải là một động từ nguyên thể.", "show": "e1"},
        {"en": "Few of these changes will really endure.", "vi": "Ít thay đổi trong số này sẽ thật sự bền lâu.", "gap": True},
        {"say": "Lỗi thứ hai: dùng remain với một tân ngữ.", "show": "e2"},
        {"en": "It is hard to maintain a balance between work and study.", "vi": "Thật khó duy trì cân bằng giữa việc làm và việc học.", "gap": True},
        {"say": "Lỗi thứ ba: dùng to sau persist.", "show": "e3"},
        {"en": "He persisted in asking the same question.", "vi": "Anh ấy cứ cố chấp hỏi mãi một câu.", "gap": True},
        {"say": "Luôn nhìn từ loại và từ đứng sau. Sau will là động từ. Remain không có tân ngữ. Persist đi với in.", "show": "rule"},
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
    _row("t1", "car", "modify · đổi một phần", "I've made modifications to my car.", "Thay lốp, sơn lại; khung và máy vẫn giữ nguyên."),
    _row("t2", "butterfly", "transform · đổi toàn bộ", "Learning to use the Internet has transformed my life.", "Đổi đến mức thành một thứ khác hẳn."),
]

TEXTS = [
    _row("f1", "gavel", "reform · hệ thống", "It's time we reformed the whole prison system.", "Hệ thống, chính sách, thể chế."),
    _row("f2", "doc", "revise · bài viết", "Please revise your report before Friday.", "Xem và sửa lại một bản báo cáo; còn có nghĩa là ôn bài."),
    _row("f3", "pencil_sheet", "amend · điều khoản", "I've amended the contract.", "Sửa điều khoản trong luật, hợp đồng, kế hoạch."),
]

FIT = [
    _row("j1", "slider", "adjust · chỉnh cho vừa", "You can adjust the chair by pressing this button.", "Vặn, bấm, chỉnh một chi tiết."),
    _row("j2", "user_icon", "adjust to · tự điều chỉnh", "I have to adjust to my new job.", "Người tự chỉnh mình cho hợp chỗ mới."),
    _row("j3", "refresh", "adapt · thích nghi để tồn tại", "This company needs to adapt or it won't survive.", "Thay đổi trước hoàn cảnh mới để sống còn."),
]

MORE = [
    {"key": "g1", "head": "convert to", "en": "Many people converted to Christianity.", "vi": "chuyển sang, cải sang một tôn giáo, một hệ thống"},
    {"key": "g2", "head": "transform", "en": "The Internet has transformed my life.", "vi": "biến đổi toàn bộ"},
    {"key": "g3", "head": "alternate", "en": "We meet on alternate Saturdays.", "vi": "cách một lần: tuần này gặp, tuần sau nghỉ"},
    {"key": "g4", "head": "alternative", "en": "I'm trying to find an alternative route.", "vi": "phương án khác để thay thế"},
]

TRAPS_2 = [
    {"key": "e1", "wrong": "We need to amend our society.", "right": "We need to reform our society.", "why": "amend dùng cho luật, hợp đồng, kế hoạch. Thay đổi một hệ thống, một xã hội: reform."},
    {"key": "e2", "wrong": "Moving to the city modified my whole life.", "right": "Moving to the city transformed my whole life.", "why": "Cả cuộc sống đổi khác: transform. modify chỉ đổi một phần."},
]

SITTING_2 = [
    {"kind": "title", "hook": "Độ lại chiếc xe và đổi hẳn sang xe khác: tiếng Anh dùng cùng một từ không?", "lines": [
        {"say": "Độ lại chiếc xe và đổi hẳn sang xe khác: tiếng Anh dùng cùng một từ không?", "show": "hook"},
        {"say": "Không. Buổi hai phân biệt thay đổi một phần với thay đổi toàn bộ, và xem mỗi từ đi với thứ gì."},
    ]},
    {"kind": "word", "headword": "shift", "lines": [
        {"say": "Mở đầu bằng một danh từ. Mười năm trước, học trực tuyến bị coi là học tạm. Bây giờ nhiều người chủ động chọn nó. Thái độ đã có một bước ngoặt: đó là shift. Giới từ đi kèm là in."},
        {"en": "There has been a real shift in attitudes.", "vi": "Thái độ đã có một bước ngoặt thực sự.", "gap": True},
    ]},
    {"kind": "word", "headword": "modify", "lines": [
        {"say": "Ở Việt Nam có chữ độ xe: thay lốp, sơn lại vỏ, nhưng khung xe và máy xe vẫn giữ nguyên. Thay đổi từng phần, vài khía cạnh: đó là modify."},
    ]},
    {"kind": "word", "headword": "transform", "lines": [
        {"say": "Còn transform là biến đổi mọi khía cạnh, đến mức thành một thứ khác hẳn. Như con sâu thành con bướm."},
    ]},
    {"kind": "scene", "visual": "picture_cards", "eyebrow": "Một phần hay toàn bộ", "title": "modify và transform",
     "data": {"rows": PART, "rule": "Đổi một phần, vẫn là nó: modify. Đổi toàn bộ, thành thứ khác: transform."}, "lines": [
        {"say": "Modify: độ xe. Danh từ là modification.", "show": "t1"},
        {"en": "I've made modifications to my car.", "vi": "Tôi đã độ lại chiếc xe của mình.", "gap": True},
        {"say": "Chiếc xe bốn bánh được sửa thiết kế thành sáu bánh cũng là modify: xe vẫn là xe đó.", "show": "t1"},
        {"en": "I've modified the design by giving the car six wheels.", "vi": "Tôi đã sửa thiết kế, cho chiếc xe sáu bánh.", "gap": True},
        {"say": "Transform: cả cuộc sống đổi khác.", "show": "t2"},
        {"en": "Learning to use the Internet has transformed my life.", "vi": "Học dùng Internet đã thay đổi hoàn toàn cuộc sống của tôi.", "gap": True},
        {"say": "Đổi một phần, vẫn là nó: modify. Đổi toàn bộ, thành thứ khác: transform.", "show": "rule"},
    ]},
    {"kind": "word", "headword": "reform", "lines": [
        {"say": "Reform là cải cách, cải tổ. Thứ được cải cách luôn là một chính sách, một thể chế, một hệ thống lớn: hệ thống giáo dục, hệ thống nhà tù."},
    ]},
    {"kind": "word", "headword": "distort", "lines": [
        {"say": "Distort là bóp méo, làm mất hình dạng gốc. Hãy nghĩ tới tấm gương ở khu vui chơi: người đứng trước nó bị kéo dài ra, méo mó. Thông tin, câu chuyện, sự thật cũng có thể bị bóp méo."},
        {"en": "The report completely distorted the truth.", "vi": "Bài báo đã bóp méo hoàn toàn sự thật.", "gap": True},
    ]},
    {"kind": "scene", "visual": "picture_cards", "eyebrow": "Sửa cái gì", "title": "reform, revise, amend",
     "data": {"rows": TEXTS, "rule": "Hệ thống: reform. Bài viết: revise. Điều khoản: amend. Không ai amend một xã hội."}, "lines": [
        {"say": "Ba từ đều là sửa đổi, và cách chọn là nhìn thứ được sửa. Reform: một hệ thống. Để ý mẫu câu trong ví dụ: đã đến lúc làm gì, động từ chia quá khứ dù ý nói về bây giờ. Mẫu này học kỹ ở tuần mười.", "show": "f1"},
        {"en": "It's time we reformed the whole prison system.", "vi": "Đã đến lúc cải cách toàn bộ hệ thống nhà tù.", "gap": True},
        {"say": "Revise: xem và sửa lại một bản báo cáo. Revise còn có nghĩa là ôn bài.", "show": "f2"},
        {"en": "Please revise your report before Friday.", "vi": "Hãy sửa lại bản báo cáo trước thứ Sáu.", "gap": True},
        {"say": "Amend: sửa một điều khoản. Hay gặp nhất là luật và hợp đồng, cũng dùng cho kế hoạch.", "show": "f3"},
        {"en": "I've amended the contract.", "vi": "Tôi đã sửa điều khoản hợp đồng.", "gap": True},
        {"say": "Hệ thống thì reform. Bài viết thì revise. Điều khoản thì amend. Không ai nói một xã hội đã được amend: đó là kết hợp từ.", "show": "rule"},
    ]},
    {"kind": "word", "headword": "adjust", "lines": [
        {"say": "Adjust là điều chỉnh cho vừa: vặn, bấm nút, chỉnh tư thế. Người cũng tự điều chỉnh mình được, khi đến một công ty mới."},
    ]},
    {"kind": "scene", "visual": "picture_cards", "eyebrow": "Chỉnh hay thích nghi", "title": "adjust và adapt",
     "data": {"rows": FIT, "rule": "Chỉnh cho vừa: adjust, adjust to. Thay đổi để tồn tại: adapt."}, "lines": [
        {"say": "Adjust: chỉnh một chi tiết cho vừa.", "show": "j1"},
        {"en": "You can adjust the chair by pressing this button.", "vi": "Bạn có thể chỉnh ghế bằng cách nhấn nút này.", "gap": True},
        {"say": "Với người, dùng adjust to: tự điều chỉnh cho hợp môi trường mới.", "show": "j2"},
        {"en": "I have to adjust to my new job.", "vi": "Tôi phải điều chỉnh để quen với công việc mới.", "gap": True},
        {"say": "Adapt: thay đổi để tồn tại trước hoàn cảnh mới.", "show": "j3"},
        {"en": "This company needs to adapt or it won't survive.", "vi": "Công ty này phải thích nghi, nếu không sẽ không tồn tại được.", "gap": True},
        {"say": "Chỉnh cho vừa thì adjust. Thay đổi để tồn tại thì adapt.", "show": "rule"},
    ]},
    {"kind": "scene", "visual": "ref_table", "eyebrow": "Hai cặp trong bài tập", "title": "convert, transform; alternate, alternative",
     "data": {"cols": ["Từ", "Câu"], "rows": MORE, "rule": "convert đi với to. alternate là cách một lần; alternative là phương án khác."}, "lines": [
        {"say": "Hai cặp nữa sẽ gặp trong bài tập. Convert đi với to: chuyển sang một tôn giáo, một hệ thống.", "show": "g1"},
        {"en": "Many people converted to Christianity.", "vi": "Nhiều người đã cải sang đạo Thiên Chúa.", "gap": True, "recap": False},
        {"say": "Transform thì không cần to: biến đổi toàn bộ một thứ.", "show": "g2"},
        {"say": "Alternate là cách một lần. Một tháng có bốn thứ Bảy: tuần một gặp, tuần hai nghỉ, tuần ba gặp.", "show": "g3"},
        {"en": "We meet on alternate Saturdays.", "vi": "Chúng tôi gặp nhau cách một thứ Bảy một lần.", "gap": True, "recap": False},
        {"say": "Alternative là một phương án khác để thay thế, như một con đường khác khi tắc.", "show": "g4"},
        {"en": "I'm trying to find an alternative route.", "vi": "Tôi đang tìm một con đường khác.", "gap": True, "recap": False},
        {"say": "Convert đi với to. Alternate là cách một lần, alternative là phương án khác.", "show": "rule"},
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
        {"say": "Hết buổi hai. Sáu từ: shift, modify, transform, reform, distort, adjust. Buổi ba nói về những thay đổi đi lên, đi xuống, và thay chỗ cho nhau.", "show": "title"},
    ]},
]

# ------------------------------------------------------------------ sitting 3: up, down and replacing
UP = [
    {"key": "e1", "wrong": "Britain began to progress into its present form.", "right": "Britain began to evolve into its present form.", "why": "Thành hình thái mới: evolve into. progress into là vào một giai đoạn."},
    {"key": "e2", "wrong": "We've made a lot of modification with the plans.", "right": "We've made a lot of progress with the plans.", "why": "Vế sau còn chặng đường dài: nói về tiến độ."},
]

DOWN = [
    _row("d1", "cloud_down", "deteriorate · tự xấu đi", "The political situation has deteriorated rapidly.", "Không có tân ngữ: tình hình, sức khỏe, thời tiết."),
    _row("d2", "leaf_decay", "decay · mục rữa", "When trees fall and start to decay, insects live in them.", "Thứ có sự sống: cây, thịt, răng. Không nói máy móc."),
    _row("d3", "rain", "spoil · làm hỏng", "I hope the bad weather didn't spoil your holiday.", "Có tân ngữ: làm hỏng kỳ nghỉ, cuộc vui, món ăn."),
]

SWAP = [
    _row("s1", "sub_board", "substitute · thế chỗ", "There's no substitute for practical experience.", "B đè vào chỗ A, A không còn."),
    _row("s2", "swap", "switch · tráo đổi", "Someone must have switched my bag and theirs.", "Hai chiếc túi vẫn còn, chỉ bị đổi chỗ."),
]

SITTING_3 = [
    {"kind": "title", "hook": "Cầm nhầm túi của người khác ở sân bay: đó là substitute hay switch?", "lines": [
        {"say": "Cầm nhầm túi của người khác ở sân bay: đó là substitute, hay là switch?", "show": "hook"},
        {"say": "Buổi ba có bảy từ: đi lên, đi xuống, và thay chỗ. Câu trả lời cho câu hỏi này nằm ở cuối buổi."},
    ]},
    {"kind": "word", "headword": "evolve", "lines": [
        {"say": "Ta quen evolve qua chuyện sinh vật tiến hóa, kể cả nhân vật tiến hóa trong trò chơi điện tử. Nhưng evolve còn dùng rất nhiều cho xã hội: phát triển dần, từng bước, thành một hình thái mới. Luôn nhớ giới từ into."},
        {"en": "Britain began to evolve into its present form.", "vi": "Nước Anh bắt đầu dần trở thành hình thái như ngày nay.", "gap": True},
    ]},
    {"kind": "word", "headword": "make progress", "lines": [
        {"say": "Make progress: có tiến triển, đạt được một tiến độ. Học cả cụm. Progress là danh từ không đếm được, nhấn âm đầu."},
    ]},
    {"kind": "scene", "visual": "fix_pairs", "eyebrow": "Đi lên", "title": "evolve into, make progress",
     "data": {"rows": UP, "rule": "Thành một hình thái mới: evolve into. Có tiến độ: make progress."}, "lines": [
        {"say": "Lỗi thứ nhất: dùng progress khi xã hội dần thành một hình thái mới. Giới từ into quyết định: evolve into.", "show": "e1"},
        {"en": "Britain began to evolve into its present form.", "vi": "Nước Anh bắt đầu dần trở thành hình thái như ngày nay.", "gap": True, "recap": False},
        {"say": "Progress into vẫn có, nhưng là tiến vào một giai đoạn, như một đội bóng vào vòng chung kết.", "show": "e1"},
        {"say": "Lỗi thứ hai: sửa kế hoạch thì đúng ngữ pháp, nhưng vế sau nói còn một chặng đường dài. Vậy vế trước nói về tiến độ đã đạt được.", "show": "e2"},
        {"en": "We've made a lot of progress with the plans, but we still have a long way to go.", "vi": "Chúng tôi đã tiến được nhiều với kế hoạch, nhưng còn một chặng đường dài.", "gap": True},
        {"say": "Thành một hình thái mới thì evolve into. Có tiến độ thì make progress.", "show": "rule"},
    ]},
    {"kind": "word", "headword": "mature", "lines": [
        {"say": "Mature là trưởng thành, chín chắn: bình tĩnh nhìn tình huống, dùng kinh nghiệm để tìm cách giải quyết. Để ý cách đọc: trọng âm rơi vào âm thứ hai."},
        {"en": "Try to be mature and use your experience.", "vi": "Hãy chín chắn và dùng kinh nghiệm của bạn.", "gap": True},
    ]},
    {"kind": "word", "headword": "deteriorate", "lines": [
        {"say": "Giờ đến chiều đi xuống. Deteriorate là xuống cấp, trở nên tồi tệ hơn: tình hình chính trị, sức khỏe, thời tiết. Động từ này không có tân ngữ."},
    ]},
    {"kind": "word", "headword": "decay", "lines": [
        {"say": "Decay là thối rữa, mục nát. Dùng cho thứ có sự sống: cây cối, thịt, răng; không nói máy móc hay sắt thép bị decay. Từ điển còn ghi một nghĩa rộng: khu phố, nhà cửa xuống cấp dần."},
    ]},
    {"kind": "scene", "visual": "picture_cards", "eyebrow": "Đi xuống", "title": "deteriorate, decay, spoil",
     "data": {"rows": DOWN, "rule": "Tự xấu đi: deteriorate. Mục rữa: decay. Làm hỏng một thứ: spoil, có tân ngữ."}, "lines": [
        {"say": "Deteriorate: tự xấu đi, không có tân ngữ.", "show": "d1"},
        {"en": "The political situation has deteriorated rapidly.", "vi": "Tình hình chính trị xấu đi nhanh chóng.", "gap": True},
        {"say": "Decay: mục rữa, với thứ có sự sống.", "show": "d2"},
        {"en": "When trees fall and start to decay, insects live in them.", "vi": "Khi cây đổ và bắt đầu mục, côn trùng đến sống trong đó.", "gap": True},
        {"say": "Spoil thì khác: làm hỏng một thứ, nên luôn có tân ngữ.", "show": "d3"},
        {"en": "I hope the bad weather didn't spoil your holiday.", "vi": "Mong là thời tiết xấu không làm hỏng kỳ nghỉ của bạn.", "gap": True},
        {"say": "Tự xấu đi thì deteriorate. Mục rữa thì decay. Làm hỏng một thứ thì spoil, có tân ngữ.", "show": "rule"},
    ]},
    {"kind": "word", "headword": "substitute", "lines": [
        {"say": "Quay lại khái niệm ở buổi một. Có cái cũ và cái mới. Khi cái mới đè vào chỗ cái cũ thì cái cũ không còn tồn tại nữa: đó là substitute. Cụm rất hay dùng: không gì thay thế được."},
    ]},
    {"kind": "word", "headword": "switch", "lines": [
        {"say": "Còn switch là tráo đổi. Hai thứ vẫn còn đó, chỉ đổi chỗ cho nhau."},
    ]},
    {"kind": "scene", "visual": "picture_cards", "eyebrow": "Trả lời câu hỏi đầu buổi", "title": "substitute và switch",
     "data": {"rows": SWAP, "rule": "Cái cũ không còn: substitute. Hai thứ cùng còn, chỉ đổi chỗ: switch."}, "lines": [
        {"say": "Substitute: lý thuyết không thay được kinh nghiệm thực tế.", "show": "s1"},
        {"en": "There's no substitute for practical experience.", "vi": "Không gì thay thế được kinh nghiệm thực tế.", "gap": True},
        {"say": "Còn hai chiếc túi bị cầm nhầm: chiếc túi của tôi vẫn còn, túi của người kia cũng còn. Chúng chỉ bị tráo cho nhau. Vậy là switch.", "show": "s2"},
        {"en": "Someone must have switched my bag and theirs.", "vi": "Chắc ai đó đã tráo túi của tôi với túi của họ.", "gap": True},
        {"say": "Cái cũ không còn thì substitute. Hai thứ cùng còn thì switch. Học từ phải có khái niệm là vì vậy.", "show": "rule"},
    ]},
    {"kind": "recap", "lines": [
        {"say": "Giờ nói lại các câu của buổi này. Nghe một câu, rồi nói to trong quãng nghỉ.", "show": "title"},
    ]},
    {"kind": "end", "next": "Tiếp theo: những từ tả một xã hội đổi thay.", "lines": [
        {"say": "Hết buổi ba. Bảy từ: evolve, make progress, mature, deteriorate, decay, substitute, switch. Buổi bốn kể chuyện một xã hội thay đổi, với tám từ để tả nó.", "show": "title"},
    ]},
]

# ------------------------------------------------------------------ sitting 4: a society that changes
BRITAIN = [
    {"key": "p1", "icon": "same_houses", "label": "Trước chiến tranh", "kind": "bg", "en": "Society was fairly uniform and conservative.", "vi": "Đồng nhất, bảo thủ."},
    {"key": "p2", "icon": "bolt", "label": "Chiến tranh", "kind": "event", "en": "The war caused a revolution and changed the status quo.", "vi": "Cách mạng, đổi hiện trạng."},
    {"key": "p3", "icon": "trend", "label": "Xu hướng", "kind": "chain", "en": "The trend was away from fixed roles and towards a more dynamic society.", "vi": "Rời cố định, tới năng động."},
    {"key": "p4", "icon": "sparkle", "label": "Giới trẻ", "kind": "chain", "en": "New and innovative music had a great influence on young people.", "vi": "Ảnh hưởng tới giới trẻ."},
]

FAMILY = [
    {"key": "i1", "head": "innovate · động từ", "en": "Companies must innovate to survive.", "vi": "đổi mới"},
    {"key": "i2", "head": "innovation · danh từ", "en": "Mobile phones that receive TV are a real innovation.", "vi": "sự đổi mới; phát kiến mới"},
    {"key": "i3", "head": "innovative · tính từ", "en": "New and innovative music appeared.", "vi": "sáng tạo, đổi mới"},
]

ELIM = [
    {"key": "e1", "wrong": "Britain underwent potential changes after the war.", "right": "Britain underwent radical changes after the war.", "why": "Thời gian: việc đã xảy ra, không dùng potential."},
    {"key": "e2", "wrong": "Music had a great innovation on young people.", "right": "Music had a great influence on young people.", "why": "Giới từ: chỉ influence đi với on."},
    {"key": "e3", "wrong": "Britain became a more amended society.", "right": "Britain became a more dynamic society.", "why": "Phạm vi kết hợp: amend chỉ cho văn bản; fixed gợi từ đối lập."},
]

SITTING_4 = [
    {"kind": "title", "hook": "Một xã hội đang yên ổn, rồi đổi khác hẳn. Tả sự đổi khác đó bằng từ nào?", "lines": [
        {"say": "Một xã hội đang yên ổn, rồi đổi khác hẳn. Tả sự đổi khác đó bằng từ nào?", "show": "hook"},
        {"say": "Buổi bốn bắt đầu bằng câu chuyện về nước Anh trước và sau Chiến tranh thế giới thứ hai."},
    ]},
    {"kind": "scene", "visual": "story_strip", "eyebrow": "Một câu chuyện", "title": "Nước Anh đổi thay",
     "data": {"frame": "strip", "panels": BRITAIN, "rule": "Bốn khung tranh: đồng nhất, bảo thủ, cách mạng, xu hướng, năng động, ảnh hưởng."}, "lines": [
        {"say": "Trước chiến tranh, người Anh tin rằng lối sống của họ sẽ còn kéo dài nhiều năm. Mọi người chung niềm tin, chung giá trị: xã hội đồng nhất và bảo thủ.", "show": "p1"},
        {"en": "Society was fairly uniform and conservative.", "vi": "Xã hội khá đồng nhất và bảo thủ.", "gap": True},
        {"say": "Rồi chiến tranh gây ra một cuộc cách mạng, thay đổi hoàn toàn hiện trạng, tức là trật tự xã hội đã có sẵn.", "show": "p2"},
        {"en": "The war caused a revolution and changed the status quo.", "vi": "Chiến tranh gây ra một cuộc cách mạng, thay đổi hiện trạng.", "gap": True},
        {"say": "Xu hướng là rời xa những vai trò cố định, hướng tới một xã hội luôn vận động. Để ý mẫu câu: away from một thứ, towards một thứ khác.", "show": "p3"},
        {"en": "The trend was away from fixed roles and towards a more dynamic society.", "vi": "Xu hướng là rời xa vai trò cố định, hướng tới một xã hội năng động hơn.", "gap": True},
        {"say": "Âm nhạc và thời trang mới mẻ, sáng tạo ảnh hưởng mạnh tới giới trẻ.", "show": "p4"},
        {"en": "New and innovative music had a great influence on young people.", "vi": "Âm nhạc mới mẻ và sáng tạo có ảnh hưởng lớn tới giới trẻ.", "gap": True},
        {"say": "Bốn khung tranh, và mỗi khung có từ của buổi này. Giờ mình đi từng từ.", "show": "rule"},
    ]},
    {"kind": "word", "headword": "uniform", "lines": [
        {"say": "Uniform, ta quen với nghĩa đồng phục. Làm tính từ, nó nghĩa là đồng nhất. Một xã hội đồng nhất không phải ai cũng mặc đồng phục, mà là mọi người chung đặc điểm và giá trị. Như ở Việt Nam: Tết thì về sum họp, đến tuổi thì lập gia đình, và cả xã hội đều coi trọng chuyện học hành."},
    ]},
    {"kind": "word", "headword": "conservative", "lines": [
        {"say": "Conservative là bảo thủ, giữ gìn lề lối cũ, ngại thay đổi. Cụm hay gặp: một xã hội bảo thủ."},
        {"en": "It was a conservative society.", "vi": "Đó là một xã hội bảo thủ.", "gap": True},
    ]},
    {"kind": "word", "headword": "radical", "lines": [
        {"say": "Radical là triệt để, tận gốc. Gốc của từ này trong tiếng La-tinh chính là rễ cây: thay đổi tới tận rễ. Cụm cần nhớ: những thay đổi triệt để."},
    ]},
    {"kind": "word", "headword": "dynamic", "lines": [
        {"say": "Dynamic là năng động, luôn vận động. Trong câu chuyện, chữ fixed, cố định, ở vế trước chính là manh mối: vế sau cần từ đối lập với nó."},
    ]},
    {"kind": "word", "headword": "novel", "lines": [
        {"say": "Novel ta quen là tiểu thuyết. Làm tính từ, novel nghĩa là mới lạ. Thời đó, cho giới trẻ nhiều tự do là điều mới lạ và hấp dẫn."},
    ]},
    {"kind": "word", "headword": "have an influence on", "lines": [
        {"say": "Có ảnh hưởng tới ai, tới cái gì. Học nguyên cụm, và nhớ giới từ on."},
    ]},
    {"kind": "word", "headword": "innovation", "lines": [
        {"say": "Innovation là sự đổi mới, một phát kiến mới. Người học hay nhầm từ loại của nhóm từ này."},
    ]},
    {"kind": "scene", "visual": "ref_table", "eyebrow": "Một gốc, ba từ loại", "title": "innovate, innovation, innovative",
     "data": {"cols": ["Từ", "Câu"], "rows": FAMILY, "rule": "Sau a real cần danh từ: innovation. Đi cùng New and là tính từ: innovative."}, "lines": [
        {"say": "Động từ: innovate, đổi mới.", "show": "i1"},
        {"en": "Companies must innovate to survive.", "vi": "Các công ty phải đổi mới để tồn tại.", "gap": True},
        {"say": "Danh từ: innovation. Điện thoại xem được truyền hình từng là một phát kiến mới.", "show": "i2"},
        {"en": "Mobile phones that receive TV are a real innovation.", "vi": "Điện thoại xem được truyền hình là một phát kiến thực sự.", "gap": True},
        {"say": "Tính từ: innovative. Chữ new đứng trước là manh mối: hai tính từ cùng nói về cái mới.", "show": "i3"},
        {"en": "New and innovative music appeared.", "vi": "Âm nhạc mới mẻ và sáng tạo xuất hiện.", "gap": True},
        {"say": "Nhìn vị trí để chọn từ loại. Đứng sau mạo từ và một tính từ thì cần danh từ. Đi cùng một tính từ khác thì cần tính từ.", "show": "rule"},
    ]},
    {"kind": "word", "headword": "potential", "lines": [
        {"say": "Từ cuối, cũng là chìa khóa để loại đáp án. Potential là tiềm năng: điều có thể xảy ra, nhưng chưa xảy ra."},
        {"en": "This young player has a lot of potential.", "vi": "Cầu thủ trẻ này có nhiều tiềm năng.", "gap": True, "recap": False},
    ]},
    {"kind": "scene", "visual": "fix_pairs", "eyebrow": "Ba cách loại đáp án", "title": "Thời gian, giới từ, phạm vi kết hợp",
     "data": {"rows": ELIM, "rule": "Loại theo thời gian, giới từ, phạm vi kết hợp; tìm manh mối trong câu."}, "lines": [
        {"say": "Cách loại thứ nhất: theo thời gian. Thay đổi đã xảy ra sau chiến tranh, làm sao còn là tiềm năng được nữa.", "show": "e1"},
        {"en": "Britain underwent radical changes after the war.", "vi": "Nước Anh trải qua những thay đổi triệt để sau chiến tranh.", "gap": True},
        {"say": "Cách loại thứ hai: theo giới từ đi kèm. Có on thì chọn influence.", "show": "e2"},
        {"en": "Music had a great influence on young people.", "vi": "Âm nhạc có ảnh hưởng lớn tới giới trẻ.", "gap": True},
        {"say": "Cách loại thứ ba: theo phạm vi kết hợp. Amend chỉ cho văn bản; và chữ fixed ở vế trước gợi từ đối lập.", "show": "e3"},
        {"en": "Britain became a more dynamic society.", "vi": "Nước Anh trở thành một xã hội năng động hơn.", "gap": True},
        {"say": "Thời gian, giới từ, phạm vi kết hợp. Và luôn tìm manh mối trong câu: một từ đối lập, hay một từ đi song hành.", "show": "rule"},
    ]},
    {"kind": "recap", "lines": [
        {"say": "Giờ nói lại các câu của buổi này. Nghe một câu, rồi nói to trong quãng nghỉ.", "show": "title"},
    ]},
    {"kind": "end", "next": "Tiếp theo: từ về công nghệ, rồi làm bài.", "lines": [
        {"say": "Hết buổi bốn. Tám từ: uniform, conservative, radical, dynamic, novel, có ảnh hưởng tới, innovation, potential. Buổi năm là nhóm từ về công nghệ.", "show": "title"},
    ]},
]

# ------------------------------------------------------------------ sitting 5: technology, and reading words right
PAIRS = [
    _row("c1", "gear", "technique · technical", "Beta testing is a technique in computing.", "Sau a cần danh từ: technique. technical là tính từ: technical problems."),
    _row("c2", "magnifier", "experience · experiment", "Use your experience to find a solution.", "experience: kinh nghiệm. experiment: cuộc thí nghiệm."),
]

SOUND = [
    {"key": "o1", "head": "console", "en": "/ˈkɒnsəʊl/", "vi": "âm cuối không đọc thành tiếng"},
    {"key": "o2", "head": "data", "en": "/ˈdeɪtə/", "vi": "nguyên âm đầu đọc như ây"},
    {"key": "o3", "head": "technique · technical", "en": "/tekˈniːk/ · /ˈteknɪkl/", "vi": "danh từ nhấn âm hai, tính từ nhấn âm đầu"},
    {"key": "o4", "head": "experience", "en": "/ɪkˈspɪəriəns/", "vi": "giữ âm xờ ở cuối"},
]

SITTING_5 = [
    {"kind": "title", "hook": "Trò chơi điện tử ba mươi năm trước trông thế nào so với bây giờ?", "lines": [
        {"say": "Trò chơi điện tử ba mươi năm trước trông thế nào so với bây giờ?", "show": "hook"},
        {"say": "Buổi cuối có ba mục cần học kỹ. Những từ công nghệ khác trong bài tập chỉ cần nhận ra, và đọc cho đúng."},
    ]},
    {"kind": "word", "headword": "primitive", "lines": [
        {"say": "Vài khối vuông nhảy trên màn hình đen trắng. So với trò chơi bây giờ, trò chơi đời đầu trông thật sơ khai: đó là primitive. Không phải phức tạp, mà là sơ khai."},
    ]},
    {"kind": "word", "headword": "technique", "lines": [
        {"say": "Technique là kỹ thuật, phương pháp làm một việc, gần nghĩa với method. Đây là danh từ, nhấn âm thứ hai."},
    ]},
    {"kind": "word", "headword": "natural resource", "lines": [
        {"say": "Tài nguyên thiên nhiên. Học nguyên cụm, như hai cụm ở các buổi trước. Biển, rừng, nước đều là tài nguyên thiên nhiên."},
        {"en": "The sea is a great natural resource.", "vi": "Biển là một nguồn tài nguyên thiên nhiên lớn.", "gap": True},
    ]},
    {"kind": "scene", "visual": "picture_cards", "eyebrow": "Cặp dễ nhầm", "title": "Một chữ khác, nghĩa khác",
     "data": {"rows": PAIRS, "rule": "Sau a cần danh từ: technique, không phải technical. Kinh nghiệm là experience, thí nghiệm là experiment."}, "lines": [
        {"say": "Cặp thứ nhất: sau mạo từ a phải là danh từ, nên là technique. Technical là tính từ, đứng trước một danh từ.", "show": "c1"},
        {"en": "Beta testing is a technique in computing.", "vi": "Thử nghiệm beta là một phương pháp trong tin học.", "gap": True},
        {"say": "Cặp thứ hai người học hay đọc nhầm: experience là kinh nghiệm, experiment là cuộc thí nghiệm.", "show": "c2"},
        {"en": "Use your experience to find a solution.", "vi": "Hãy dùng kinh nghiệm của bạn để tìm cách giải quyết.", "gap": True},
        {"say": "Sau a là danh từ technique. Kinh nghiệm là experience, thí nghiệm là experiment.", "show": "rule"},
    ]},
    {"kind": "scene", "visual": "ref_table", "eyebrow": "Đọc cho đúng", "title": "Bốn từ hay đọc sai",
     "data": {"cols": ["Từ", "Cách đọc"], "rows": SOUND, "rule": "Tra cách đọc trong từ điển trước khi nhẩm, để không nhẩm sai nhiều lần."}, "lines": [
        {"say": "Bốn từ trong bài tập hay bị đọc sai. Console, chiếc máy chơi trò chơi điện tử: âm cuối không đọc thành tiếng.", "show": "o1"},
        {"en": "console", "vi": "máy chơi trò chơi điện tử", "gap": True, "recap": False},
        {"say": "Data, dữ liệu: nguyên âm đầu đọc như ây. Đây là cách đọc phổ biến nhất; người ta cũng đọc khác, và không cách đọc nào bị coi là sai.", "show": "o2"},
        {"en": "data", "vi": "dữ liệu", "gap": True, "recap": False},
        {"say": "Technique nhấn âm thứ hai. Technical nhấn âm đầu.", "show": "o3"},
        {"say": "Experience: đừng bỏ âm xờ ở cuối.", "show": "o4"},
        {"en": "experience", "vi": "kinh nghiệm", "gap": True, "recap": False},
        {"say": "Tra cách đọc trước khi nhẩm. Nhẩm sai mười lần thì sửa rất khó.", "show": "rule"},
    ]},
    {"kind": "recap", "lines": [
        {"say": "Giờ nói lại các câu của buổi này. Nghe một câu, rồi nói to trong quãng nghỉ.", "show": "title"},
    ]},
    {"kind": "end", "next": "Tiếp theo: làm bài tập, rồi viết câu của bạn với 5 đến 10 từ yêu thích.", "lines": [
        {"say": "Hết phần giảng của ngày năm. Một mẹo khi tự học: với đồ vật và công nghệ, như chiếc máy chơi trò chơi điện tử, hãy tra bằng hình ảnh thay vì chỉ đọc nghĩa tiếng Việt. Bây giờ bạn làm bài trong app, loại phương án sai theo thời gian, giới từ và phạm vi kết hợp. Rồi chia ba mươi từ thành gói mười từ mỗi ngày, và viết hai câu về một thay đổi trong cuộc sống của chính bạn.", "show": "title"},
    ]},
]

S_WORDS = [
    ["endure", "last", "maintain", "remain", "sustain", "persist"],
    ["shift", "modify", "transform", "reform", "distort", "adjust"],
    ["evolve", "make progress", "mature", "deteriorate", "decay", "substitute", "switch"],
    ["uniform", "conservative", "radical", "dynamic", "novel", "have an influence on", "innovation", "potential"],
    ["primitive", "technique", "natural resource"],
]

TITLES = [
    "Buổi 1 · ba bước học từ; kéo dài và giữ nguyên",
    "Buổi 2 · thay đổi một phần hay toàn bộ",
    "Buổi 3 · đi lên, đi xuống và thay thế",
    "Buổi 4 · một xã hội đổi thay; ba cách loại đáp án",
    "Buổi 5 · công nghệ; đọc đúng những từ hay sai",
]
LECTURES = [SITTING_1, SITTING_2, SITTING_3, SITTING_4, SITTING_5]

RUBRIC = None  # the vocabulary day has no speaking card; "Câu của tôi" keeps the default checklist


def reshape(sessions: list[dict]) -> list[dict]:
    """The five vocabulary sittings get their lecture and title; every other sitting is kept as built."""
    for i, lecture in enumerate(LECTURES):
        ses = sessions[i]
        words = [s["headword"] for s in lecture if s.get("kind") == "word"]
        assert words == S_WORDS[i], (i, words)
        assert sorted(words) == sorted(ses["vocab"]), (i, set(words) ^ set(ses["vocab"]))
        ses["lecture"] = lecture
        ses["title_vi"] = TITLES[i]
        assert len(ses["title_vi"]) <= 70
    return sessions

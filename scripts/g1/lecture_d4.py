"""G1 · Day 4 (lesson 47): the review of the four present tenses, two lectures written by hand
(lesson_audio.build_authored_lecture), and the day's sittings reshaped around them. Same format as lecture_d3.py.

Sources: the teacher's session 3, stage 4 (01:06-01:19), where he lays the four present tenses side by side:
the present simple for repeated actions and for truth, objective or subjective (the colour-blind man who sees the
sea red, the child who lies about the time he gets up, a theory believed true today); the present continuous for
what is temporary (She lives in Hanoi now / She is living in Hanoi now), for complaints with always + V-ing and for
plans; the two separate branches of the present perfect; and the present perfect continuous taught by two sample
sentences to work the uses out from (I have been playing football for three hours / I am very tired. I have been
running for three hours). From the same session: a test has one key, real speech follows what the speaker means
(stage 4, exercise A); a repeated action removes the "temporary" reading; a house is owned for good, so never
"is owning" (01:24); questions open in the simplest tense and the answer picks its own (01:32); "Have you ever
...?" answered in the past simple once a time is given (00:26). Destination B2, Unit 1, p. 8-11 gives the frame.
The examples on the slides are this course's own unless they are the teacher's sample sentences; no teacher,
book or page is named to the learner.
"""

PRON: dict[str, str] = {}

# the map: two questions split the four present tenses (row: linked to the past? column: temporary or ongoing?)
ROW_HEADS = ["Chưa nối với quá khứ", "Nối từ quá khứ tới bây giờ"]
COL_HEADS = ["Không nhấn tạm thời", "Nhấn tạm thời, quá trình"]

MAP = [
    {"key": "c1", "tense": "Hiện tại đơn", "form": "V / V-s", "at": "always", "en": "She lives in Hanoi.", "vi": "Lâu dài, coi là thật."},
    {"key": "c2", "tense": "Hiện tại tiếp diễn", "form": "am / is / are + V-ing", "at": "window", "en": "She is living in Hanoi now.", "vi": "Chỗ ở tạm, rồi đổi."},
    {"key": "c3", "tense": "Hiện tại hoàn thành", "form": "have / has + V3", "at": "span", "en": "I have studied the piano since 2003.", "vi": "Từ 2003 tới giờ, vẫn học."},
    {"key": "c4", "tense": "Hoàn thành tiếp diễn", "form": "have / has been + V-ing", "at": "span", "en": "I have been playing football for three hours.", "vi": "Ba tiếng nay, vẫn đang chơi."},
]

TRUTH = [
    {"key": "r1", "icon": "repeat", "head": "Lặp lại", "en": "I go to the gym three times a week.", "vi": "Mỗi tuần ba lần."},
    {"key": "r2", "icon": "kettle", "head": "Sự thật khách quan", "en": "Water boils at 100 degrees.", "vi": "Ai đo cũng ra như vậy."},
    {"key": "r3", "icon": "red_sea", "head": "Sự thật chủ quan", "en": "The sea is red.", "vi": "Người mù màu thấy vậy: với họ, đó là thật."},
    {"key": "r4", "icon": "bed", "head": "Kể cả khi nói dối", "en": "I get up at six every morning.", "vi": "Nói với mẹ, dù thật ra dậy lúc chín giờ."},
]

CONTINUOUS = [
    {"key": "a1", "icon": "house", "at": "always", "tense": "Hiện tại đơn", "en": "She lives in Hanoi now.", "vi": "Chỉ báo chị ấy sống ở đó."},
    {"key": "a2", "icon": "suitcase", "at": "window", "tense": "Tiếp diễn · tạm thời", "en": "She is living in Hanoi now.", "vi": "Ở tạm, sau này có thể chuyển."},
    {"key": "a3", "icon": "angry", "at": "repeat", "tense": "Tiếp diễn · than phiền", "en": "He is always leaving his clothes on the floor!", "vi": "Thói quen làm người nói bực."},
    {"key": "a4", "icon": "calendar", "at": "future", "tense": "Tiếp diễn · đã hẹn", "en": "I'm meeting Lan tomorrow.", "vi": "Kế hoạch đã sắp xếp."},
]

PERFECT = [
    {"key": "b1", "icon": "piano", "at": "span", "tense": "Nhánh 1 · kéo tới bây giờ", "en": "I have studied the piano since 2003.", "vi": "Bắt đầu năm 2003, bây giờ vẫn học."},
    {"key": "b2", "icon": "basket", "at": "done", "tense": "Nhánh 2 · đã xong", "en": "Yes, I have bought some vegetables.", "vi": "Mua rồi. Lúc nào thì không nói."},
    {"key": "b3", "icon": "calendar", "at": "point", "tense": "Nêu lúc nào · quá khứ đơn", "en": "I studied the piano in 2003.", "vi": "Có mốc đã qua thì đổi thì."},
]

TWO_SAMPLES = [
    {"key": "s1", "icon": "ball", "at": "span", "tense": "Câu mẫu 1 · vẫn đang làm", "en": "I have been playing football for three hours.", "vi": "Bắt đầu ba tiếng trước, bây giờ vẫn chơi."},
    {"key": "s2", "icon": "runner", "at": "trace", "tense": "Câu mẫu 2 · vừa dừng", "en": "I am very tired. I have been running for three hours.", "vi": "Đã dừng chạy, cái mệt vẫn còn."},
]

SIGNALS = [
    {"key": "k1", "head": "almost every weekend · lặp lại", "en": "My brother plays football almost every weekend.", "vi": "Lặp lại thì không còn tạm thời: thì đơn."},
    {"key": "k2", "head": "own · tài sản lâu dài", "en": "Mr Connors owns two houses and a villa.", "vi": "Không nói is owning."},
    {"key": "k3", "head": "since + mốc", "en": "Our teacher has taught here since 2019.", "vi": "since luôn đi với thì hoàn thành."},
    {"key": "k4", "head": "dấu vết + độ dài", "en": "I'm out of breath. I have been running for an hour.", "vi": "Vừa dừng, còn dấu vết: hoàn thành tiếp diễn."},
]

ANSWERS = [
    {"key": "c1", "tense": "Hiện tại đơn", "form": "thói quen", "at": "repeat", "en": "I study every evening.", "vi": "Tối nào cũng học."},
    {"key": "c2", "tense": "Hiện tại tiếp diễn", "form": "tạm thời", "at": "window", "en": "I'm studying harder this month.", "vi": "Riêng tháng này."},
    {"key": "c3", "tense": "Hiện tại hoàn thành", "form": "từ bao giờ", "at": "span", "en": "I have studied it since 2023.", "vi": "Từ 2023 tới giờ."},
    {"key": "c4", "tense": "Hoàn thành tiếp diễn", "form": "vừa xong, còn mệt", "at": "trace", "en": "I have been studying all morning, so I'm tired.", "vi": "Cả sáng, giờ mệt."},
]

TRAPS = [
    {"key": "e1", "wrong": "I am knowing the answer.", "right": "I know the answer.", "why": "know là động từ trạng thái: không chia tiếp diễn."},
    {"key": "e2", "wrong": "She is owning two houses.", "right": "She owns two houses.", "why": "Tài sản lâu dài: hiện tại đơn."},
    {"key": "e3", "wrong": "I work here since 2022.", "right": "I have worked here since 2022.", "why": "since cần thì hoàn thành."},
    {"key": "e4", "wrong": "I have seen her yesterday.", "right": "I saw her yesterday.", "why": "Có mốc đã qua: quá khứ đơn."},
]

ANSWER_PARTS = [
    {"key": "p1", "role": "Trả lời thẳng", "tense": "Hiện tại đơn", "en": "I work as an accountant in a small company.", "vi": "Tôi làm kế toán ở một công ty nhỏ."},
    {"key": "p2", "role": "Việc tạm thời", "tense": "Hiện tại tiếp diễn", "en": "This month I'm also studying for an IELTS test.", "vi": "Tháng này tôi còn đang học để thi IELTS."},
    {"key": "p3", "role": "Từ bao giờ", "tense": "Hiện tại hoàn thành", "en": "I have worked there since 2022, and my colleagues are very friendly.", "vi": "Tôi làm ở đó từ năm 2022, đồng nghiệp rất thân thiện."},
    {"key": "p4", "role": "Gần đây, còn dấu vết", "tense": "Hoàn thành tiếp diễn", "en": "Recently I have been doing a lot of extra tasks, so I'm quite tired.", "vi": "Gần đây tôi làm nhiều việc thêm, nên khá mệt."},
]

# memory hooks for the day's words, shown under the meaning (pairs that are easy to mix up)
NOTES = {
    "study": "Học điều mới. Đi cặp với revise: ôn lại điều đã học.",
    "revise": "Ôn lại điều đã học, nhất là trước kỳ thi. Đi cặp với study.",
    "test": "Bài ngắn, trên lớp, như bài kiểm tra mười lăm phút. Đi cặp với exam.",
    "exam": "Kỳ thi lớn, chính thức, như thi cuối kỳ hay IELTS. Đi cặp với test.",
    "classmate": "Người học cùng lớp. Ở chỗ làm thì là colleague.",
    "colleague": "Người làm cùng chỗ. Ở trường thì là classmate.",
    "task": "Một việc được giao, như Writing Task 1 và Task 2. Đi cặp với effort.",
    "effort": "Công sức bạn bỏ ra để làm việc đó. make an effort: cố gắng.",
    "qualifications": "Bằng cấp, chứng chỉ: thứ ghi được lên giấy. Đi cặp với qualities.",
    "qualities": "Phẩm chất: con người bạn, như kiên nhẫn, trung thực. Đi cặp với qualifications.",
}

S1_WORDS = ["study", "revise", "test", "exam", "classmate"]
S2_WORDS = ["colleague", "task", "effort", "qualifications", "qualities"]

SITTING_1 = [
    {"kind": "title", "hook": "Bốn thì hiện tại, nhưng chỉ cần hai câu hỏi. Đó là hai câu nào?", "lines": [
        {"say": "Bạn đã học bốn thì hiện tại trong ba ngày. Hôm nay ghép chúng lại thành một hệ thống. Chỉ cần hai câu hỏi là chia được cả bốn. Đó là hai câu nào?", "show": "hook"},
        {"say": "Buổi này dựng bản đồ bốn ô, rồi đi qua từng ô, mỗi ô một câu mẫu để nhớ."},
    ]},
    {"kind": "scene", "visual": "tense_grid", "eyebrow": "Bản đồ", "title": "Hai câu hỏi, bốn ô",
     "data": {"row_heads": ROW_HEADS, "col_heads": COL_HEADS, "cells": MAP,
              "rule": "Nối với quá khứ: thêm have. Nhấn tạm thời, quá trình: thêm be và ing."}, "lines": [
        {"say": "Câu hỏi thứ nhất: việc này có nối từ quá khứ tới bây giờ không? Không nối thì nằm ở hàng trên. Có nối thì nằm ở hàng dưới, và động từ thêm have.", "show": "rows"},
        {"say": "Câu hỏi thứ hai: người nói có nhấn tính tạm thời, hay quá trình đang diễn ra, không? Không nhấn thì ở cột trái. Có nhấn thì ở cột phải, và động từ thêm be cùng đuôi ing.", "show": "cols"},
        {"say": "Ô thứ nhất: không nối, không nhấn tạm thời. Đó là hiện tại đơn. Chị ấy sống ở Hà Nội, một sự thật."},
        {"en": "She lives in Hanoi.", "vi": "Chị ấy sống ở Hà Nội.", "gap": True, "show": "c1"},
        {"say": "Ô thứ hai: cùng hàng trên, nhưng nhấn tạm thời. Hiện tại tiếp diễn. Bây giờ chị ấy đang ở Hà Nội, sau này có thể chuyển."},
        {"en": "She is living in Hanoi now.", "vi": "Bây giờ chị ấy đang ở Hà Nội.", "gap": True, "show": "c2"},
        {"say": "Xuống hàng dưới. Ô thứ ba: nối từ quá khứ tới bây giờ. Hiện tại hoàn thành."},
        {"en": "I have studied the piano since 2003.", "vi": "Tôi học piano từ năm 2003.", "gap": True, "show": "c3"},
        {"say": "Ô thứ tư: nối từ quá khứ, và nhấn quá trình đang diễn ra. Hiện tại hoàn thành tiếp diễn."},
        {"en": "I have been playing football for three hours.", "vi": "Tôi chơi bóng ba tiếng nay rồi.", "gap": True, "show": "c4"},
        {"say": "Hai câu hỏi, bốn ô. Có nối với quá khứ thì thêm have. Có nhấn tạm thời hay quá trình thì thêm be và ing.", "show": "rule"},
    ]},
    {"kind": "scene", "visual": "picture_cards", "eyebrow": "Ô 1 · hiện tại đơn", "title": "Lặp lại, và điều người nói coi là thật",
     "data": {"rows": TRUTH,
              "rule": "Điều đi qua mắt và đầu óc người nói, được coi là thật lúc nói: hiện tại đơn."}, "lines": [
        {"say": "Ô thứ nhất có hai việc. Việc một: hành động lặp lại.", "show": "r1"},
        {"en": "I go to the gym three times a week.", "vi": "Mỗi tuần tôi đến phòng tập ba lần.", "gap": True},
        {"say": "Việc hai, quan trọng hơn: sự thật. Có sự thật khách quan, ai đo cũng ra như vậy.", "show": "r2"},
        {"en": "Water boils at 100 degrees.", "vi": "Nước sôi ở 100 độ.", "gap": True},
        {"say": "Và có sự thật chủ quan. Một người mù màu nhìn biển xanh thành màu đỏ. Với người đó, biển màu đỏ là thật, nên họ vẫn dùng hiện tại đơn.", "show": "r3"},
        {"en": "The sea is red.", "vi": "Biển màu đỏ.", "gap": True, "recap": False},
        {"say": "Kể cả khi nói dối. Bạn dậy lúc chín giờ, nhưng nói với mẹ là ngày nào cũng dậy lúc sáu giờ. Bạn trình bày điều đó như sự thật, nên vẫn là hiện tại đơn.", "show": "r4"},
        {"en": "I get up at six every morning.", "vi": "Con dậy lúc sáu giờ mỗi sáng.", "gap": True},
        {"say": "Mọi điều đi qua mắt và đầu óc người nói, được coi là thật vào lúc nói, đều dùng hiện tại đơn.", "show": "rule"},
    ]},
    {"kind": "scene", "visual": "tense_timeline", "eyebrow": "Ô 2 · hiện tại tiếp diễn", "title": "Tạm thời, than phiền, kế hoạch",
     "data": {"question": "Where is your sister?", "question_vi": "Chị bạn đâu rồi?", "question_label": "Có người hỏi",
              "answers": CONTINUOUS, "rule": "Tiếp diễn có ba việc: tạm thời, than phiền với always, kế hoạch đã hẹn."}, "lines": [
        {"say": "Có người hỏi chị bạn đang ở đâu."},
        {"en": "Where is your sister?", "vi": "Chị bạn đâu rồi?", "gap": True, "show": "q", "recap": False},
        {"say": "Trên trục này, bên trái là quá khứ, vạch giữa là bây giờ, bên phải là tương lai.", "show": "axis"},
        {"say": "Đáp bằng hiện tại đơn: chỉ báo một sự thật, chị ấy sống ở Hà Nội. Không có ý tạm.", "show": "a1"},
        {"en": "She lives in Hanoi now.", "vi": "Bây giờ chị ấy sống ở Hà Nội.", "gap": True},
        {"say": "Đáp bằng tiếp diễn: chỗ ở đó chỉ là tạm, sau này có thể chuyển đi. Đây là việc thứ nhất của tiếp diễn.", "show": "a2"},
        {"en": "She is living in Hanoi now.", "vi": "Bây giờ chị ấy đang ở tạm Hà Nội.", "gap": True, "recap": False},
        {"say": "Việc thứ hai: than phiền. Always cộng động từ thêm ing, cho một thói quen làm bạn bực.", "show": "a3"},
        {"en": "He is always leaving his clothes on the floor!", "vi": "Nó cứ vứt quần áo dưới sàn!", "gap": True},
        {"say": "Việc thứ ba: kế hoạch đã hẹn. Câu ở hiện tại, nhưng việc nằm ở tương lai.", "show": "a4"},
        {"en": "I'm meeting Lan tomorrow.", "vi": "Mai tôi gặp Lan.", "gap": True},
        {"say": "Tiếp diễn có ba việc: tạm thời, than phiền với always, và kế hoạch đã hẹn.", "show": "rule"},
    ]},
    {"kind": "scene", "visual": "tense_timeline", "eyebrow": "Ô 3 · hiện tại hoàn thành", "title": "Hai nhánh tách biệt",
     "data": {"question": "have / has + V3", "question_vi": "hai nhánh", "question_label": "Công thức",
              "answers": PERFECT, "rule": "Nhánh 1 kéo tới bây giờ. Nhánh 2 đã xong, không nói lúc nào. Nêu lúc nào: quá khứ đơn."}, "lines": [
        {"say": "Ô thứ ba có hai nhánh, đừng trộn chúng với nhau.", "show": "q"},
        {"say": "Nhánh một: bắt đầu từ trước, bây giờ vẫn còn. Thanh kéo tới tận vạch bây giờ.", "show": "axis"},
        {"en": "I have studied the piano since 2003.", "vi": "Tôi học piano từ năm 2003.", "gap": True, "show": "b1", "recap": False},
        {"say": "Nhánh hai: việc đã xong, người nói không nêu lúc nào. Rau đã nằm trong bếp, không ai còn đứng ở chợ mua tiếp.", "show": "b2"},
        {"en": "Yes, I have bought some vegetables.", "vi": "Có, tôi mua rau rồi.", "gap": True},
        {"say": "Còn khi nêu được lúc nào, như năm 2003 đã qua, thì đổi sang quá khứ đơn.", "show": "b3"},
        {"en": "I studied the piano in 2003.", "vi": "Tôi học piano vào năm 2003.", "gap": True},
        {"say": "Nhánh một kéo tới bây giờ. Nhánh hai đã xong và không nói lúc nào. Nêu lúc nào thì dùng quá khứ đơn.", "show": "rule"},
    ]},
    {"kind": "scene", "visual": "tense_timeline", "eyebrow": "Ô 4 · hoàn thành tiếp diễn", "title": "Nhớ hai câu, suy ra hai cách dùng",
     "data": {"question": "have / has been + V-ing", "question_vi": "hai câu mẫu", "question_label": "Công thức",
              "answers": TWO_SAMPLES, "rule": "Câu 1: vẫn đang làm. Câu 2: vừa dừng, dấu vết còn ở bây giờ."}, "lines": [
        {"say": "Ô cuối cùng, đừng học thuộc lý thuyết. Hãy thuộc hai câu mẫu, quên thì nhớ lại câu, từ câu suy ra cách dùng.", "show": "q"},
        {"say": "Câu mẫu thứ nhất. Bạn bắt đầu chơi bóng ba tiếng trước, và ngay lúc nói vẫn đang chơi.", "show": "axis"},
        {"en": "I have been playing football for three hours.", "vi": "Tôi chơi bóng ba tiếng nay rồi.", "gap": True, "show": "s1", "recap": False},
        {"say": "Câu mẫu thứ hai. Bạn đã chạy suốt ba tiếng, vừa dừng lại đứng thở. Việc chạy đã dừng, nhưng cái mệt vẫn còn.", "show": "s2"},
        {"en": "I am very tired. I have been running for three hours.", "vi": "Tôi mệt lắm. Tôi vừa chạy suốt ba tiếng.", "gap": True},
        {"say": "Hai câu, hai cách dùng. Một: vẫn đang làm. Hai: vừa dừng, và dấu vết còn ở bây giờ.", "show": "rule"},
    ]},
    {"kind": "word", "headword": "study", "lines": [{"say": "Năm từ của buổi này đi theo cặp. Cặp thứ nhất: học và ôn."}]},
    {"kind": "word", "headword": "revise", "lines": [{"say": "Study là học điều mới. Revise là ôn lại điều đã học. Câu ví dụ là hiện tại tiếp diễn: việc của riêng tuần này."}]},
    {"kind": "word", "headword": "test", "lines": [{"say": "Cặp thứ hai: bài kiểm tra và kỳ thi."}]},
    {"kind": "word", "headword": "exam", "lines": [{"say": "Test là bài ngắn trên lớp. Exam là kỳ thi lớn, chính thức. Câu ví dụ là hoàn thành tiếp diễn: ôn từ tháng Sáu tới giờ."}]},
    {"kind": "word", "headword": "classmate", "lines": [{"say": "Từ cuối, và để ý động từ know trong câu ví dụ: động từ trạng thái, nên dùng hoàn thành, không dùng tiếp diễn."}]},
    {"kind": "recap", "lines": [
        {"say": "Giờ nói lại các câu mẫu của buổi này. Nghe một câu, rồi nói to trong quãng nghỉ.", "show": "title"},
    ]},
    {"kind": "end", "next": "Tiếp theo: học thẻ và từ của buổi này, rồi làm bài.", "lines": [
        {"say": "Hết buổi một. Bạn học các thẻ và từ trong app, rồi làm bài. Buổi hai nói về cách chọn thì khi làm bài, và khi nói thật.", "show": "title"},
    ]},
]

SITTING_2 = [
    {"kind": "title", "hook": "Đáp án ghi plays, bạn lại muốn nói is playing. Ai đúng?", "lines": [
        {"say": "Bài tập ghi đáp án plays, nhưng ngoài đời bạn muốn nói is playing. Bạn sai, hay đáp án sai?", "show": "hook"},
        {"say": "Buổi này phân biệt hai việc: chọn thì khi làm bài, và chọn thì khi nói, viết thật. Cuối buổi, bạn trả lời một câu Speaking bằng cả bốn thì."},
    ]},
    {"kind": "scene", "visual": "ref_table", "eyebrow": "Khi làm bài", "title": "Dấu hiệu chọn đáp án",
     "data": {"cols": ["Dấu hiệu", "Đáp án"], "rows": SIGNALS,
              "rule": "Bài thi chỉ có một đáp án, nên dấu hiệu quyết định."}, "lines": [
        {"say": "Bài trắc nghiệm được soạn để chỉ có một đáp án. Vì vậy, khi làm bài, hãy tìm dấu hiệu. Dấu hiệu thứ nhất: cụm chỉ sự lặp lại. Đã lặp lại thì không còn tạm thời, nên chọn thì đơn.", "show": "k1"},
        {"en": "My brother plays football almost every weekend.", "vi": "Gần như cuối tuần nào anh tôi cũng đá bóng.", "gap": True},
        {"say": "Dấu hiệu thứ hai: động từ sở hữu, như own. Nhà cửa là tài sản lâu dài. Nói is owning, nghe như chỉ giữ được vài hôm rồi mất.", "show": "k2"},
        {"en": "Mr Connors owns two houses and a villa.", "vi": "Ông Connors có hai căn nhà và một biệt thự.", "gap": True},
        {"say": "Dấu hiệu thứ ba: since cộng một mốc. Since luôn đi với thì hoàn thành.", "show": "k3"},
        {"en": "Our teacher has taught here since 2019.", "vi": "Cô giáo của chúng tôi dạy ở đây từ năm 2019.", "gap": True},
        {"say": "Dấu hiệu thứ tư: một dấu vết ở hiện tại, cộng một khoảng thời gian. Đó là hoàn thành tiếp diễn.", "show": "k4"},
        {"en": "I'm out of breath. I have been running for an hour.", "vi": "Tôi hết hơi. Tôi vừa chạy suốt một tiếng.", "gap": True},
        {"say": "Khi làm bài, dấu hiệu quyết định, vì bài thi chỉ có một đáp án.", "show": "rule"},
    ]},
    {"kind": "scene", "visual": "tense_grid", "eyebrow": "Khi nói thật", "title": "Một câu hỏi, bốn câu đáp đều đúng",
     "data": {"question": "How is your English going?", "question_vi": "Việc học tiếng Anh của bạn thế nào?",
              "row_heads": ROW_HEADS, "col_heads": COL_HEADS, "cells": ANSWERS,
              "rule": "Ngoài đời, bạn muốn nhấn điều gì thì chọn thì đó."}, "lines": [
        {"say": "Khi nói thật, không có dấu hiệu nào cho sẵn. Người hỏi thường dùng thì đơn giản nhất, còn người đáp tự chọn thì của mình."},
        {"en": "How is your English going?", "vi": "Việc học tiếng Anh của bạn thế nào?", "gap": True, "show": "q", "recap": False},
        {"say": "Bốn câu đáp dưới đây đều đúng. Mỗi câu nằm ở một ô của bản đồ, và nói một ý khác.", "show": "rows"},
        {"say": "Muốn nói thói quen: hiện tại đơn.", "show": "cols"},
        {"en": "I study every evening.", "vi": "Tối nào tôi cũng học.", "gap": True, "show": "c1"},
        {"say": "Muốn nhấn việc của riêng tháng này: tiếp diễn."},
        {"en": "I'm studying harder this month.", "vi": "Tháng này tôi học chăm hơn.", "gap": True, "show": "c2"},
        {"say": "Muốn nói từ bao giờ: hoàn thành."},
        {"en": "I have studied it since 2023.", "vi": "Tôi học từ năm 2023.", "gap": True, "show": "c3"},
        {"say": "Muốn nói vừa học cả sáng, giờ còn mệt: hoàn thành tiếp diễn."},
        {"en": "I have been studying all morning, so I'm tired.", "vi": "Tôi học cả sáng nay, nên giờ mệt.", "gap": True, "show": "c4"},
        {"say": "Vậy câu hỏi đầu buổi có lời đáp. Đáp án của sách đúng cho bài thi. Ngoài đời, bạn muốn nhấn điều gì thì chọn thì đó. Còn khi phân vân mà không thấy gì tạm thời, cũng không nối với quá khứ, hãy chọn hiện tại đơn.", "show": "rule"},
    ]},
    {"kind": "scene", "visual": "fix_pairs", "eyebrow": "Lỗi thường gặp", "title": "Bốn lỗi, bốn cách sửa",
     "data": {"rows": TRAPS,
              "rule": "Trạng thái và sở hữu: thì đơn. since: hoàn thành. Có mốc đã qua: quá khứ đơn."}, "lines": [
        {"say": "Bốn lỗi hay gặp nhất khi trộn bốn thì. Lỗi thứ nhất: chia tiếp diễn với know.", "show": "e1"},
        {"en": "I know the answer.", "vi": "Tôi biết câu trả lời.", "gap": True},
        {"say": "Lỗi thứ hai: is owning cho tài sản lâu dài.", "show": "e2"},
        {"en": "She owns two houses.", "vi": "Cô ấy có hai căn nhà.", "gap": True},
        {"say": "Lỗi thứ ba: since đi với hiện tại đơn.", "show": "e3"},
        {"en": "I have worked here since 2022.", "vi": "Tôi làm ở đây từ năm 2022.", "gap": True},
        {"say": "Lỗi thứ tư: hiện tại hoàn thành đi với một mốc đã qua.", "show": "e4"},
        {"en": "I saw her yesterday.", "vi": "Hôm qua tôi gặp cô ấy.", "gap": True},
        {"say": "Trạng thái và sở hữu: thì đơn. Since: hoàn thành. Có mốc đã qua: quá khứ đơn.", "show": "rule"},
    ]},
    {"kind": "word", "headword": "colleague", "lines": [{"say": "Trước khi trả lời câu Speaking, học năm từ về công việc. Từ thứ nhất là cặp của classmate ở buổi trước."}]},
    {"kind": "word", "headword": "task", "lines": [{"say": "Cặp tiếp theo: việc được giao, và công sức bỏ ra."}]},
    {"kind": "word", "headword": "effort", "lines": [{"say": "Task là việc. Effort là công sức để làm việc đó."}]},
    {"kind": "word", "headword": "qualifications", "lines": [{"say": "Cặp cuối rất dễ nhầm, vì cùng bắt đầu bằng quali."}]},
    {"kind": "word", "headword": "qualities", "lines": [{"say": "Qualifications là bằng cấp, ghi được lên giấy. Qualities là phẩm chất, là con người bạn."}]},
    {"kind": "scene", "visual": "speaking_answer", "eyebrow": "IELTS Speaking Part 1", "title": "Một câu trả lời, bốn thì",
     "data": {"question": "Do you work or study?", "question_vi": "Bạn đi làm hay đi học?",
              "short": "I work.", "parts": ANSWER_PARTS,
              "rule": "Trả lời thẳng, rồi thêm việc tạm thời, từ bao giờ, việc gần đây. Mỗi câu một thì."}, "lines": [
        {"say": "Giờ đưa cả bản đồ vào phòng thi. Giám khảo hỏi bạn đi làm hay đi học."},
        {"en": "Do you work or study?", "show": "q"},
        {"say": "Đáp đúng một câu thì quá cụt, và giám khảo chưa nghe được bạn dùng thì linh hoạt.", "show": "short"},
        {"say": "Câu một: trả lời thẳng, bằng hiện tại đơn."},
        {"en": "I work as an accountant in a small company.", "vi": "Tôi làm kế toán ở một công ty nhỏ.", "gap": True, "show": "p1"},
        {"say": "Câu hai: thêm một việc tạm thời, bằng tiếp diễn."},
        {"en": "This month I'm also studying for an IELTS test.", "vi": "Tháng này tôi còn đang học để thi IELTS.", "gap": True, "show": "p2"},
        {"say": "Câu ba: thêm từ bao giờ, bằng hoàn thành. Câu này có từ colleagues vừa học."},
        {"en": "I have worked there since 2022, and my colleagues are very friendly.", "vi": "Tôi làm ở đó từ năm 2022, đồng nghiệp rất thân thiện.", "gap": True, "show": "p3"},
        {"say": "Câu bốn: thêm việc gần đây và dấu vết của nó, bằng hoàn thành tiếp diễn."},
        {"en": "Recently I have been doing a lot of extra tasks, so I'm quite tired.", "vi": "Gần đây tôi làm nhiều việc thêm, nên khá mệt.", "gap": True, "show": "p4"},
        {"say": "Bốn câu, bốn ô của bản đồ, mỗi câu một ý. Hãy viết lại bốn câu này cho đúng với chính bạn.", "show": "rule"},
    ]},
    {"kind": "recap", "lines": [
        {"say": "Giờ nói lại các câu của buổi này. Nghe một câu, rồi nói to trong quãng nghỉ.", "show": "title"},
    ]},
    {"kind": "end", "next": "Tiếp theo: học thẻ và từ, làm bài, rồi buổi 3 để nghe chép và viết câu của bạn.", "lines": [
        {"say": "Hết phần giảng của ngày bốn. Bạn học các thẻ và từ trong app, làm bài, rồi sang buổi ba để nghe chép và viết bốn câu của chính mình.", "show": "title"},
    ]},
]

RUBRIC = [
    {"criterion_vi": "Đúng đề, nội dung là của chính bạn", "max": 1, "note_vi": "Task response"},
    {"criterion_vi": "Đủ bốn thì, mỗi thì hợp với điều muốn nói", "max": 2, "note_vi": "Grammatical range"},
    {"criterion_vi": "Dạng động từ đúng: V-s, be + V-ing, have / has + V3, have / has been + V-ing", "max": 2, "note_vi": "Grammatical accuracy"},
]


def reshape(sessions: list[dict], exercise_ids: list[str], card_of: dict[str, int]) -> list[dict]:
    """Day 4's sittings around the two lectures. Sitting 1 teaches cards 1-3 (the map, simple or continuous,
    perfect or perfect continuous) with the school words; sitting 2 cards 4-5 (tests and real use, one answer in
    four tenses) with the work words; the rest (build, type, dictation, writing) is a third sitting."""
    pats = [g for s in sessions[:2] for g in s["grammar"]]
    allcheck = [i for s in sessions[:2] for i in s["check"]]
    s1, s2 = sessions[0], sessions[1]
    rest = sessions[2:]
    all_words = [w for s in sessions[:2] for w in s["vocab"]]
    assert sorted(all_words) == sorted(S1_WORDS + S2_WORDS), all_words
    s1["vocab"], s2["vocab"] = S1_WORDS, S2_WORDS
    s1["grammar"], s2["grammar"] = pats[:3], pats[3:]
    quiz = [i for i in allcheck if i[4] in "IQT"]
    s1["check"] = [i for i in quiz if card_of[i] < 3]
    s1["check"].sort(key=lambda i: (card_of[i], i[4] != "T"))  # the timelines first: the map, then the words
    s2["check"] = [i for i in quiz if card_of[i] >= 3]
    moved = [i for i in allcheck if i not in quiz]
    s1["lecture"], s2["lecture"] = SITTING_1, SITTING_2
    s1["title_vi"] = "Buổi 1 · bản đồ bốn thì: hai câu hỏi, bốn câu mẫu"
    s2["title_vi"] = "Buổi 2 · chọn thì khi làm bài và khi nói thật"
    s1["can_do_vi"] = "Sau buổi này bạn đặt được một câu bất kỳ vào đúng ô của bốn thì hiện tại, và nhớ mỗi ô bằng một câu mẫu."
    s2["can_do_vi"] = "Sau buổi này bạn biết khi nào dấu hiệu quyết định đáp án, khi nào ý muốn nói quyết định thì, và trả lời được một câu Speaking bằng bốn thì."
    s3 = {
        "title_vi": "Buổi 3 · vận dụng: xếp câu, gõ, nghe chép, viết",
        "can_do_vi": "Sau buổi này bạn tự xếp và gõ đúng câu ở cả bốn thì, nghe chép được câu, và viết bốn câu về chính mình.",
        "use_vi": s1["use_vi"],
        "vocab": [],
        "check": moved,
    }
    assert set(s1["check"] + s2["check"] + moved) <= set(exercise_ids)
    return [s1, s2, s3] + rest

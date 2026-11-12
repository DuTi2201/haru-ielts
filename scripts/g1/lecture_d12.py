"""G1 · Day 6 (Cambridge 18 Test 4, "The growth mindset"): the reading-method lecture, written by hand.

The method is the teacher's: understand each paragraph before touching the questions. Read, light up the
keywords, strike the detail (names, dates, lists of examples), gather numbers and lists into one phrase, join what is
left into a chain of short phrases, then say the main idea and what the paragraph is worth. When an author praises a
new way by attacking the old one, turn each complaint into the advantage it implies.
Every picture is drawn by the app (LectureScenes.tsx: ref_table, para_filter, fix_pairs). No teacher, book or page
name is said on the slides.
"""
import re


def segs(text: str) -> list[dict]:
    """'[[keep]]' lights up, '{{drop}}' is struck through; the rest is plain text."""
    out = []
    for m in re.finditer(r"\[\[(.+?)\]\]|\{\{(.+?)\}\}|([^\[{]+)", text):
        if m.group(1):
            out.append({"t": m.group(1), "k": "k"})
        elif m.group(2):
            out.append({"t": m.group(2), "k": "d"})
        else:
            out.append({"t": m.group(3)})
    return out


P1 = ("Over the past century, a powerful idea has taken root in the educational landscape. The concept of intelligence as "
      "something [[innate]] has been supplanted by the idea that intelligence is [[not fixed]], and that, with the right training, "
      "we can be the authors of our own cognitive capabilities. {{Psychologist Alfred Binet, the developer of the first intelligence "
      "tests, was one of many 19th-century scientists}} who [[held that earlier view]] {{and sought to quantify cognitive ability}}. "
      "Then, {{in the early 20th century,}} progressive [[thinkers revolted]] against the notion that [[inherent ability is destiny]]. "
      "Instead, {{educators such as John Dewey}} argued that [[every child’s intelligence could be developed]], {{given the right environment}}.")
P2 = ("‘Growth mindset theory’ is a relatively new — and [[extremely popular]] — version of this idea. In many schools today you will see "
      "{{hallways covered in motivational posters and hear speeches on the mindset of great sporting heroes who simply believed their way to the top}}. "
      "A major focus of the growth mindset in schools is [[coaxing students away from seeing failure as an indication of their ability]], and "
      "[[towards seeing it as a chance to improve that ability]]. {{As educationalist Jeff Howard noted several decades ago: ‘Smart is not "
      "something that you just are, smart is something that you can get.’}}")
P3 = ("The idea of the growth mindset is based on the work of {{psychologist Carol Dweck in California in the 1990s}}. In one key "
      "[[experiment]], {{Dweck divided a group of 10- to 12-year-olds into two groups. All were told that they had achieved a high score on a test but}} "
      "the first group were [[praised for their intelligence]] {{in achieving this}}, while the others were [[praised for their effort]]. "
      "The second group {{— those who had been instilled with a ‘growth mindset’ —}} were subsequently far [[more likely to put effort]] into future tasks. "
      "Meanwhile, the former took on [[only those tasks that would not risk their sense of worth]]. {{This group had inferred that success or failure "
      "is due to innate ability, and}} this ‘fixed mindset’ had led them to [[fear of failure and lack of effort]]. [[Praising ability actually made the "
      "students perform worse]], while {{praising effort emphasised that change was possible.}}")

READ_RIGHT = [
    {"key": "r1", "head": "Cách dễ sai", "en": "skim → match keywords → answer", "vi": "Chưa hiểu bài mà đã làm câu hỏi."},
    {"key": "r2", "head": "Cách nên làm", "en": "understand → summarise → answer", "vi": "Hiểu từng đoạn rồi mới làm câu hỏi."},
]
SIX = [
    {"key": "s1", "head": "Bước 1", "en": "keywords", "vi": "Gạch từ khóa của từng câu."},
    {"key": "s2", "head": "Bước 2", "en": "cut the detail", "vi": "Bỏ tên riêng, nơi chốn, thời gian."},
    {"key": "s3", "head": "Bước 3", "en": "link them", "vi": "Nối các từ khóa lại với nhau."},
    {"key": "s4", "head": "Bước 4", "en": "arrow chain", "vi": "Viết thành chuỗi có mũi tên."},
    {"key": "s5", "head": "Bước 5", "en": "main idea", "vi": "Đoạn này nói điều gì?"},
    {"key": "s6", "head": "Bước 6", "en": "value", "vi": "Đoạn này giúp hiểu bài ra sao?"},
]
TITLE_ROWS = [
    {"key": "t1", "head": "Tiêu đề", "en": "The growth mindset", "vi": "Chủ đề: tư duy phát triển."},
    {"key": "t2", "head": "Câu hỏi của bài", "en": "What is it? Does it work?", "vi": "Hai điều bài sẽ trả lời."},
]
GATHER = [
    {"key": "g1", "head": "Nhiều chi tiết", "en": "10- to 12-year-olds, two groups, one test", "vi": "Chỉ để dựng bối cảnh."},
    {"key": "g2", "head": "Gom lại", "en": "an experiment", "vi": "Một chữ là đủ."},
]
REVERSE = [
    {"key": "v1", "wrong": "posters and talks are a waste of time", "right": "teach concrete skills", "why": "Chê khẩu hiệu thì cách đúng là dạy kỹ năng cụ thể."},
    {"key": "v2", "wrong": "telling students how unique they are", "right": "praise their effort", "why": "Chê lời khen chung chung thì cách đúng là khen nỗ lực."},
    {"key": "v3", "wrong": "growth mindset as an intervention", "right": "growth mindset as a philosophy", "why": "Chê việc can thiệp trực tiếp thì cách đúng là coi nó như một triết lý."},
]

SESSION = [
    {"kind": "title", "hook": "Đọc xong một đoạn dài mà đầu trống rỗng?", "lines": [
        {"say": "Đọc xong một đoạn dài mà đầu trống rỗng? Nhiều bạn bị như vậy, và nguyên nhân hiếm khi nằm ở từ vựng.", "show": "hook"},
        {"say": "Buổi này học cách đọc để đoạn nào cũng còn lại một chuỗi ý ngắn trong đầu."},
    ]},
    {"kind": "scene", "visual": "ref_table", "eyebrow": "Đọc hiểu", "title": "Hiểu trước, làm câu hỏi sau",
     "data": {"cols": ["Cách đọc", "Các việc"], "rows": READ_RIGHT, "rule": "Hiểu từng đoạn trước, câu hỏi để sau."}, "lines": [
        {"say": "Có hai cách đọc một bài Reading. Cách thứ nhất: đọc lướt, dò từ khóa, rồi chọn đáp án.", "show": "r1"},
        {"say": "Bài chưa hiểu mà đã làm câu hỏi thì dò đúng cũng chỉ là đoán. Đó là một nghịch lý."},
        {"say": "Cách thứ hai: hiểu từng đoạn trước, rồi mới làm câu hỏi.", "show": "r2"},
        {"say": "Vì vậy hôm nay việc đầu tiên là đọc và tóm tắt. Câu hỏi để sau.", "show": "rule"},
    ]},
    {"kind": "scene", "visual": "ref_table", "eyebrow": "Sáu bước", "title": "Cách đọc một đoạn",
     "data": {"cols": ["Bước", "Việc cần làm"], "rows": SIX, "rule": "Đoạn nào cũng làm lần lượt sáu bước này."}, "lines": [
        {"say": "Mỗi đoạn, bạn làm sáu bước. Bước một: tô từ khóa của từng câu, danh từ trước, động từ sau.", "show": "s1"},
        {"say": "Bước hai: bỏ chi tiết thừa, như tên người, nơi chốn và mốc thời gian.", "show": "s2"},
        {"say": "Bước ba: nối các từ khóa còn lại với nhau.", "show": "s3"},
        {"say": "Bước bốn: viết thành một chuỗi ngắn, nối bằng mũi tên.", "show": "s4"},
        {"say": "Bước năm: hỏi đoạn này nói điều gì.", "show": "s5"},
        {"say": "Bước sáu: đoạn này giúp mình hiểu cả bài ra sao.", "show": "s6"},
        {"say": "Giờ làm thật trên bài The growth mindset.", "show": "rule"},
    ]},
    {"kind": "scene", "visual": "ref_table", "eyebrow": "Trước khi đọc", "title": "Đọc tiêu đề",
     "data": {"cols": ["Phần", "Nói gì"], "rows": TITLE_ROWS, "rule": "Đọc tiêu đề xong, bạn đã biết mình tìm gì trong bài."}, "lines": [
        {"say": "Trước hết là tiêu đề.", "show": "t1"},
        {"en": "The growth mindset."},
        {"say": "Chủ đề là tư duy phát triển. Bài không có phụ đề, nên bạn tự đặt câu hỏi.", "show": "t2"},
        {"say": "Tư duy phát triển là gì, và nó có hiệu quả không? Đọc để tìm câu trả lời.", "show": "rule"},
    ]},
    {"kind": "scene", "visual": "para_filter", "eyebrow": "Đoạn 1", "title": "Bối cảnh của ý tưởng",
     "data": {"segs": segs(P1), "chain": ["intelligence = innate", "thinkers revolt", "can be developed"],
              "main": "Quan niệm về trí thông minh đã chuyển từ bẩm sinh sang phát triển được.",
              "value": "Cho biết ý tưởng này đến từ đâu."}, "lines": [
        {"say": "Đoạn một. Đọc cả đoạn, rồi tô vàng từ khóa. Chữ tô vàng là chữ cần giữ, phần còn lại mờ đi.", "show": "keep"},
        {"say": "Bước hai: bỏ chi tiết. Phần bị gạch ngang là phần bỏ đi. Tên nhà tâm lý học, tên nhà giáo dục, mốc thế kỷ mười chín và đầu thế kỷ hai mươi đều là chi tiết. Khi đề hỏi tới thì quay lại tìm. Lúc tóm tắt thì bỏ.", "show": "drop"},
        {"say": "Bước ba và bốn: nối những chữ còn lại. Trí thông minh từng bị coi là bẩm sinh. Các nhà tư tưởng phản đối. Cuối cùng, ai cũng có thể phát triển.", "show": "sum"},
        {"say": "Bước năm: ý chính của đoạn là quan niệm đã đổi, từ cố định sang phát triển được.", "show": "main"},
        {"say": "Bước sáu: đoạn này cho biết ý tưởng của bài đến từ đâu.", "show": "value"},
    ]},
    {"kind": "scene", "visual": "para_filter", "eyebrow": "Đoạn 2", "title": "Ý tưởng được dùng ở trường",
     "data": {"segs": segs(P2), "chain": ["popular idea", "slogans in schools", "failure = a chance to improve"],
              "main": "Nhà trường dạy học sinh xem thất bại là cơ hội để giỏi lên.",
              "value": "Cho thấy ý tưởng được dùng ngoài đời ra sao."}, "lines": [
        {"say": "Đoạn hai. Tô vàng từ khóa trước.", "show": "keep"},
        {"say": "Phần bị gạch là phần dài nhất: áp phích, bài phát biểu, tấm gương vận động viên. Gom hết lại thành một chữ: khẩu hiệu. Câu trích cuối đoạn chỉ nhắc lại ý đó, nên cũng bỏ.", "show": "drop"},
        {"say": "Chuỗi còn lại: ý tưởng đang rất phổ biến, trường dùng khẩu hiệu, và mục tiêu là xem thất bại như cơ hội.", "show": "sum"},
        {"say": "Ý chính: nhà trường dạy học sinh coi thất bại là cơ hội để giỏi lên.", "show": "main"},
        {"say": "Giá trị: đoạn này cho thấy ý tưởng được dùng ngoài đời như thế nào.", "show": "value"},
    ]},
    {"kind": "scene", "visual": "ref_table", "eyebrow": "Gom chi tiết", "title": "Nhiều chi tiết, một chữ",
     "data": {"cols": ["Việc", "Trong bài"], "rows": GATHER, "rule": "Gặp một loạt số liệu hay ví dụ, gom thành một nhận định ngắn."}, "lines": [
        {"say": "Đoạn ba kể một thí nghiệm. Có trẻ mười đến mười hai tuổi, có hai nhóm, có một bài kiểm tra.", "show": "g1"},
        {"say": "Tất cả chỉ để dựng bối cảnh. Khi tóm tắt, gom lại thành một chữ.", "show": "g2"},
        {"say": "Gặp sáu dòng số liệu cũng làm như vậy: chỉ cần ghi một nhận định, ví dụ sản lượng rất tốt.", "show": "rule"},
    ]},
    {"kind": "scene", "visual": "para_filter", "eyebrow": "Đoạn 3", "title": "Thí nghiệm của Dweck",
     "data": {"segs": segs(P3), "chain": ["praise ability", "fear of failure", "worse performance"],
              "main": "Khen nỗ lực tốt hơn khen khả năng.",
              "value": "Đây là bằng chứng nền của cả ý tưởng."}, "lines": [
        {"say": "Đoạn ba. Tô vàng từ khóa: thí nghiệm, khen trí thông minh, khen nỗ lực, sợ thất bại.", "show": "keep"},
        {"say": "Phần bị gạch là tên nhà nghiên cứu, nơi làm nghiên cứu, độ tuổi, số nhóm. Câu giải thích lặp lại cũng bỏ.", "show": "drop"},
        {"say": "Chuỗi: khen khả năng thì học sinh sợ thất bại, rồi làm bài tệ hơn. Nhóm được khen nỗ lực thì ngược lại.", "show": "sum"},
        {"say": "Ý chính: khen nỗ lực tốt hơn khen khả năng.", "show": "main"},
        {"say": "Giá trị: đây là bằng chứng nền của cả ý tưởng.", "show": "value"},
    ]},
    {"kind": "scene", "visual": "fix_pairs", "eyebrow": "Đoạn cuối", "title": "Chê cách cũ, ngầm khen cách mới",
     "data": {"rows": REVERSE, "rule": "Tác giả chê điều gì, hãy đảo ngược thành điều tác giả cho là nên làm."}, "lines": [
        {"say": "Có đoạn tác giả không nói thẳng cách nên làm, mà chê cách cũ. Khi đó, đảo ngược lại.", "show": "v1"},
        {"say": "Chê khẩu hiệu và bài nói chuyện là phí thời gian. Vậy điều nên làm là dạy kỹ năng cụ thể.", "show": "v1"},
        {"say": "Chê lời khen chung chung. Vậy nên khen nỗ lực.", "show": "v2"},
        {"say": "Chê việc can thiệp trực tiếp. Vậy nên xem tư duy phát triển như một triết lý sống.", "show": "v3"},
        {"say": "Nhớ cách đảo ngược này: nó giúp bạn rút ra ý của tác giả từ chính những lời phê bình.", "show": "rule"},
    ]},
    {"kind": "end", "next": "Tiếp theo: viết chuỗi từ khóa cho đoạn 1 đến 3, rồi học từ vựng, cuối cùng mới làm câu hỏi.", "lines": [
        {"say": "Hết phần giảng. Bây giờ bạn tự viết chuỗi từ khóa cho ba đoạn đầu. Từ vựng và câu hỏi để sau.", "show": "title"},
    ]},
]


# ============================================================ the four vocabulary sittings of the day
def _row(key, icon, head, en, vi):
    return {"key": key, "icon": icon, "head": head, "en": en, "vi": vi}


def _w(head, say):
    return {"kind": "word", "headword": head, "lines": [{"say": say}]}


def _end(next_):
    return {"kind": "end", "next": next_, "lines": [{"say": "Hết phần giảng. Bây giờ bạn làm bài tập trong app.", "show": "title"}]}


# ---- sitting 1: results of praise
PRAISE = [
    {"key": "p1", "head": "Khen khả năng", "en": "You are so smart!", "vi": "Em sợ sai, làm bài tệ đi."},
    {"key": "p2", "head": "Khen nỗ lực", "en": "You worked really hard!", "vi": "Em dám thử việc khó hơn."},
]
ACH = [
    {"key": "h1", "head": "achieve", "en": "achieve a goal", "vi": "Động từ: đạt được."},
    {"key": "h2", "head": "achievement", "en": "a great achievement", "vi": "Danh từ: thành tích."},
]
EVID = [{"key": "f1", "wrong": "There are many evidences.", "right": "There is a lot of evidence.", "why": "Evidence không đếm được, không thêm s."}]
EXP = [
    {"key": "e1", "head": "experiment", "en": "an experiment", "vi": "Thí nghiệm."},
    {"key": "e2", "head": "experience", "en": "work experience", "vi": "Kinh nghiệm."},
    {"key": "e3", "head": "expert", "en": "an expert", "vi": "Chuyên gia."},
]
S1 = [
    {"kind": "title", "hook": "Khen em thông minh hay khen em chăm chỉ?", "lines": [
        {"say": "Khen em thông minh, hay khen em chăm chỉ? Lời khen nào làm em học tốt hơn?", "show": "hook"},
        {"say": "Bài đọc hôm nay xoay quanh đúng câu hỏi này. Tám từ của buổi này là những từ bạn sẽ gặp lại liên tục."},
    ]},
    {"kind": "scene", "visual": "ref_table", "eyebrow": "Câu hỏi của bài", "title": "Hai lời khen, hai kết quả",
     "data": {"cols": ["Lời khen", "Kết quả"], "rows": PRAISE, "rule": "Khen nỗ lực tốt hơn khen khả năng."}, "lines": [
        {"say": "Một em được khen: em thật thông minh.", "show": "p1"},
        {"say": "Em đó sợ sai, vì sai nghĩa là mình không thông minh nữa. Kết quả là em làm tệ đi."},
        {"say": "Một em khác được khen: em đã làm việc rất chăm.", "show": "p2"},
        {"say": "Em này dám thử việc khó hơn. Đó chính là điều bài đọc nói.", "show": "rule"},
    ]},
    _w("ability", "Khả năng, thứ người ta cho là trời cho. Khen ability là khen cái em vốn có."),
    _w("effort", "Còn effort là thứ ta tự bỏ ra: nỗ lực. Hai từ này đối nhau suốt cả bài."),
    _w("praise", "Praise là khen, nhất là khen vì điều ai đó vừa làm. Ví dụ, giáo viên khen học sinh vì đã cố gắng."),
    _w("failure", "Failure là mặt kia của thành công. Học sinh có tư duy phát triển xem failure là cơ hội để tiến bộ."),
    {"kind": "scene", "visual": "ref_table", "eyebrow": "Họ từ", "title": "achieve và achievement",
     "data": {"cols": ["Từ", "Cách dùng"], "rows": ACH, "rule": "Đạt được là động từ. Thành tích là danh từ."}, "lines": [
        {"say": "Đạt được một mục tiêu là achieve.", "show": "h1"},
        {"say": "Còn thành tích, điều đã đạt được, là danh từ achievement.", "show": "h2"},
        {"say": "Nhớ cặp này, vì cả hai đều hay xuất hiện trong Writing.", "show": "rule"},
    ]},
    _w("achievement", "Một bài phát biểu hay trước lớp cũng là một achievement thật sự."),
    {"kind": "word", "headword": "evidence", "lines": [{"say": "Bằng chứng. Tác giả nói có evidence cho thấy phương pháp này không hiệu quả."}]},
    {"kind": "scene", "visual": "fix_pairs", "eyebrow": "Lỗi hay gặp", "title": "evidence không có s",
     "data": {"rows": EVID, "rule": "Evidence không đếm được: a lot of evidence."}, "lines": [
        {"say": "Người Việt hay thêm s cho evidence. Câu sai, rồi câu đúng.", "show": "f1"},
        {"say": "Evidence không đếm được. Nói a lot of evidence, hoặc some evidence.", "show": "rule"},
    ]},
    _w("criticism", "Criticism là lời chỉ trích. Cụm hay gặp là harsh criticism: lời chỉ trích gay gắt."),
    {"kind": "scene", "visual": "ref_table", "eyebrow": "Dễ nhầm", "title": "Ba từ bắt đầu bằng exp",
     "data": {"cols": ["Từ", "Nghĩa"], "rows": EXP, "rule": "Thí nghiệm, kinh nghiệm, chuyên gia: ba từ khác nhau."}, "lines": [
        {"say": "Ba từ này nhìn giống nhau. Experiment là thí nghiệm.", "show": "e1"},
        {"say": "Experience là kinh nghiệm.", "show": "e2"},
        {"say": "Expert là chuyên gia.", "show": "e3"},
        {"say": "Bài đọc nói về thí nghiệm, nên từ cần nhớ là experiment.", "show": "rule"},
    ]},
    _w("experiment", "Trong một experiment quan trọng, trẻ em được chia thành hai nhóm."),
    _end("Tiếp theo: làm bài tập của buổi này."),
]

# ---- sitting 2: beliefs and the nature of ability
A1 = [
    _row("a1", "bulb", "notion = idea", "The notion that talent is fixed is old.", "Một ý niệm, một quan niệm."),
    _row("a2", "key", "innate = born with", "Some believe intelligence is innate.", "Có từ khi sinh ra."),
    _row("a3", "roadmap", "destiny = fate", "Ability is not destiny.", "Con đường đã định sẵn."),
]
A2 = [
    _row("a4", "magnifier", "infer = work out", "She inferred it from the clues.", "Suy ra từ manh mối."),
    _row("a5", "eye", "perceive = see", "He perceives help as weakness.", "Nhìn nhận, cảm nhận."),
    _row("a6", "crystal", "deluded = wrongly sure", "A deluded idea of success.", "Tin điều sai mà không biết."),
]
TRAP2 = [
    {"key": "t1", "wrong": "He believes in his destination.", "right": "He believes in his destiny.", "why": "Destination là điểm đến. Destiny là số phận."},
    {"key": "t2", "wrong": "The writer infers that tests are unfair.", "right": "The writer implies that tests are unfair.", "why": "Tác giả implies. Người đọc infers."},
]
S2 = [
    {"kind": "title", "hook": "Tài năng là trời cho, hay luyện mà có?", "lines": [
        {"say": "Tài năng là trời cho, hay luyện mà có? Câu hỏi đó chia người ta thành hai phe, và sáu từ hôm nay là ngôn ngữ của cuộc tranh luận này.", "show": "hook"},
    ]},
    {"kind": "scene", "visual": "picture_cards", "eyebrow": "Mẹo của buổi này", "title": "Gắn từ khó vào từ quen",
     "data": {"rows": A1, "rule": "Mỗi từ khó gắn vào một từ quen."}, "lines": [
        {"say": "Notion gắn vào idea: một ý niệm.", "show": "a1"},
        {"say": "Innate gắn vào born with: có từ khi sinh ra.", "show": "a2"},
        {"say": "Destiny gắn vào fate: điều đã định sẵn.", "show": "a3"},
        {"say": "Ba từ này đều nói về niềm tin.", "show": "rule"},
    ]},
    _w("notion", "Notion là một quan niệm. Tác giả nhắc tới notion rằng khả năng là cố định, rồi bác bỏ nó."),
    _w("innate", "Innate là bẩm sinh. Một số người tin trí thông minh là innate, tức là sinh ra đã có."),
    _w("destiny", "Destiny là số phận. Câu quen thuộc của bài: khả năng không phải là destiny."),
    {"kind": "scene", "visual": "fix_pairs", "eyebrow": "Dễ nhầm", "title": "destiny hay destination",
     "data": {"rows": TRAP2[:1], "rule": "Số phận là destiny. Điểm đến là destination."}, "lines": [
        {"say": "Hai từ này nhìn giống nhau. Câu sai, rồi câu đúng.", "show": "t1"},
        {"say": "Số phận là destiny. Điểm đến là destination.", "show": "rule"},
    ]},
    {"kind": "scene", "visual": "picture_cards", "eyebrow": "Mẹo của buổi này", "title": "Ba từ nữa",
     "data": {"rows": A2, "rule": "Suy ra, nhìn nhận, tin sai."}, "lines": [
        {"say": "Infer gắn vào work out: từ manh mối mà suy ra.", "show": "a4"},
        {"say": "Perceive gắn vào see: nhìn nhận, cảm nhận.", "show": "a5"},
        {"say": "Deluded gắn vào wrongly sure: tin chắc điều sai.", "show": "a6"},
        {"say": "Ba từ này nói về cách người ta nhìn sự việc.", "show": "rule"},
    ]},
    _w("infer", "Nhóm được khen khả năng suy ra rằng thành công phụ thuộc vào năng khiếu. Đó là infer."),
    {"kind": "scene", "visual": "fix_pairs", "eyebrow": "Dễ nhầm", "title": "infer hay imply",
     "data": {"rows": TRAP2[1:], "rule": "Tác giả nói ngầm là implies. Người đọc suy ra là infers."}, "lines": [
        {"say": "Người viết ngầm nói ra một ý là imply. Người đọc suy ra ý đó là infer.", "show": "t2"},
        {"say": "Nhớ: tác giả implies, người đọc infers.", "show": "rule"},
    ]},
    _w("perceive", "Perceive là nhìn nhận. Học sinh có thể perceive sự giúp đỡ của giáo viên như dấu hiệu mình kém."),
    _w("deluded", "Deluded là tin chắc điều không đúng. Áp phích có thể cho học sinh một ý niệm deluded về thành công."),
    _end("Tiếp theo: làm bài tập của buổi này."),
]

# ---- sitting 3: words for analysing a study
COR = [
    {"key": "c1", "head": "Cùng tăng", "en": "ice cream sales and sunburn", "vi": "Có tương quan với nhau."},
    {"key": "c2", "head": "Nhưng không phải nguyên nhân", "en": "hot weather causes both", "vi": "Nguyên nhân thật là trời nóng."},
]
ANC3 = [
    {"key": "n1", "head": "impediment", "en": "= obstacle", "vi": "Trở ngại."},
    {"key": "n2", "head": "intervention", "en": "= action to change things", "vi": "Biện pháp can thiệp."},
    {"key": "n3", "head": "dispute", "en": "= argue it is wrong", "vi": "Phản bác."},
    {"key": "n4", "head": "aspiration", "en": "= ambition", "vi": "Khát vọng."},
    {"key": "n5", "head": "subtle", "en": "= not obvious", "vi": "Kín đáo, tinh tế."},
]
TRAP3 = [{"key": "x1", "wrong": "a correlation of height and weight", "right": "a correlation between height and weight", "why": "Tương quan đi với between … and …."}]
S3 = [
    {"kind": "title", "hook": "Hai thứ đi cùng nhau có phải thứ này gây ra thứ kia?", "lines": [
        {"say": "Hai thứ cùng tăng, có phải thứ này gây ra thứ kia không? Đây là câu hỏi mà mọi bài nghiên cứu phải trả lời, và sáu từ hôm nay giúp bạn nói về nó.", "show": "hook"},
    ]},
    {"kind": "scene", "visual": "ref_table", "eyebrow": "Tình huống", "title": "Tương quan không phải nguyên nhân",
     "data": {"cols": ["Quan sát", "Ý nghĩa"], "rows": COR, "rule": "Có tương quan chưa chắc có quan hệ nhân quả."}, "lines": [
        {"say": "Mùa nóng, kem bán chạy và người ta cũng bị cháy nắng nhiều.", "show": "c1"},
        {"say": "Kem không làm ai cháy nắng. Nguyên nhân thật là trời nóng.", "show": "c2"},
        {"say": "Hai thứ cùng tăng như vậy gọi là có tương quan.", "show": "rule"},
    ]},
    _w("correlation", "Correlation là mối tương quan. Bài đọc nói: có một correlation mạnh giữa cách học sinh nhìn mình và thành tích."),
    {"kind": "scene", "visual": "fix_pairs", "eyebrow": "Lỗi hay gặp", "title": "correlation đi với between",
     "data": {"rows": TRAP3, "rule": "a correlation between A and B."}, "lines": [
        {"say": "Câu sai, rồi câu đúng.", "show": "x1"},
        {"say": "Tương quan đi với between và and.", "show": "rule"},
    ]},
    {"kind": "scene", "visual": "ref_table", "eyebrow": "Mẹo của buổi này", "title": "Gắn từ khó vào từ quen",
     "data": {"cols": ["Từ", "Gắn vào"], "rows": ANC3, "rule": "Năm từ còn lại, mỗi từ một chỗ bám."}, "lines": [
        {"say": "Impediment gắn vào obstacle: một trở ngại.", "show": "n1"},
        {"say": "Intervention gắn vào action to change things: một biện pháp can thiệp.", "show": "n2"},
        {"say": "Dispute gắn vào argue it is wrong: phản bác.", "show": "n3"},
        {"say": "Aspiration gắn vào ambition: khát vọng.", "show": "n4"},
        {"say": "Subtle gắn vào not obvious: kín đáo, không lộ liễu.", "show": "n5"},
        {"say": "Giờ đi từng từ.", "show": "rule"},
    ]},
    _w("impediment", "Tác giả nói hệ thống trường học chính là một impediment lớn: trở ngại cho việc đổi cách dạy."),
    _w("intervention", "Intervention là biện pháp can thiệp. Bài nói can thiệp trực tiếp trong lớp học dường như không hiệu quả."),
    _w("dispute", "Khó mà dispute rằng tin vào khả năng thay đổi là điều tốt. Nghĩa là khó phản bác."),
    _w("aspiration", "Aspiration là khát vọng. Học sinh nào cũng có aspiration, nhưng lời hô hào không nuôi được nó."),
    _w("subtle", "Subtle là kín đáo. Hai tác giả nói can thiệp nên được đưa ra một cách subtle, để học sinh không thấy mình cần được giúp."),
    _end("Tiếp theo: làm bài tập của buổi này."),
]

# ---- sitting 4: connectives and collocations
COL4 = [
    {"key": "k1", "head": "concentrate on", "en": "concentrate on your strengths", "vi": "Tập trung vào."},
    {"key": "k2", "head": "have faith in", "en": "have faith in yourself", "vi": "Tin vào."},
    {"key": "k3", "head": "intellectual ability", "en": "an intellectual challenge", "vi": "Thuộc về trí tuệ."},
]
TRAP4 = [
    {"key": "y1", "wrong": "concentrate in your work", "right": "concentrate on your work", "why": "Tập trung vào dùng on."},
    {"key": "y2", "wrong": "faith on teachers", "right": "faith in teachers", "why": "Tin vào dùng in."},
]
S4 = [
    {"kind": "title", "hook": "Học thêm càng nhiều, điểm càng thấp: vì sao?", "lines": [
        {"say": "Học thêm càng nhiều, điểm càng thấp. Nghe ngược đời, và đó đúng là tinh thần của từ đầu tiên hôm nay.", "show": "hook"},
    ]},
    _w("paradoxically", "Paradoxically là nghịch lý ở chỗ: điều xảy ra ngược với mong đợi. Tác giả viết: paradoxically, dạy trực tiếp tư duy này lại không hiệu quả. Từ này đứng đầu câu, rồi có dấu phẩy."),
    {"kind": "scene", "visual": "ref_table", "eyebrow": "Cụm cố định", "title": "Ba cụm nên học nguyên khối",
     "data": {"cols": ["Cụm", "Ví dụ"], "rows": COL4, "rule": "Học cả cụm, đừng học từng chữ."}, "lines": [
        {"say": "Concentrate đi với on: tập trung vào một việc.", "show": "k1"},
        {"say": "Faith đi với in: tin vào ai đó hay điều gì.", "show": "k2"},
        {"say": "Intellectual ability: năng lực trí tuệ.", "show": "k3"},
        {"say": "Học cả cụm thì không bao giờ chọn nhầm giới từ.", "show": "rule"},
    ]},
    _w("concentrate on", "Trường học yêu cầu học sinh concentrate on điểm mạnh của mình."),
    _w("have faith in", "Có faith in khả năng thay đổi của bản thân là điều tốt cho người học."),
    {"kind": "scene", "visual": "fix_pairs", "eyebrow": "Lỗi hay gặp", "title": "Chọn đúng giới từ",
     "data": {"rows": TRAP4, "rule": "concentrate on. faith in."}, "lines": [
        {"say": "Câu sai, rồi câu đúng.", "show": "y1"},
        {"say": "Câu thứ hai.", "show": "y2"},
        {"say": "Nhớ: concentrate on, faith in.", "show": "rule"},
    ]},
    _w("intellectual", "Intellectual là thuộc về trí tuệ. Bài nói về năng lực trí tuệ có thể được phát triển."),
    _w("deliberate", "Deliberate nghĩa là có chủ ý, làm đúng ý định. Ví dụ, một nỗ lực deliberate để thúc đẩy học sinh. Nếu muốn dùng từ an toàn hơn, nói on purpose."),
    _end("Tiếp theo: làm bài tập của buổi này."),
]

VOCAB_LECTURES = [S1, S2, S3, S4]
VOCAB_TITLES = [
    "Khen khả năng hay khen nỗ lực",
    "Niềm tin về tài năng",
    "Từ để phân tích một nghiên cứu",
    "Cụm cố định và từ nối",
]


def reshape_vocab(sessions: list[dict]) -> None:
    for i, lecture in enumerate(VOCAB_LECTURES):
        ses = sessions[i]
        words = [s["headword"] for s in lecture if s.get("kind") == "word"]
        assert sorted(words) == sorted(ses["vocab"]), (i, set(words) ^ set(ses["vocab"]))
        ses["lecture"] = lecture
        ses["title_vi"] = VOCAB_TITLES[i]

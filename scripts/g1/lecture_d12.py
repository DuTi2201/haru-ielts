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
        {"say": "Mỗi đoạn, bạn làm sáu bước. Bước một: gạch từ khóa của từng câu, danh từ trước, động từ sau.", "show": "s1"},
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
        {"say": "Đoạn một. Đọc cả đoạn, rồi gạch từ khóa. Những chữ sáng lên là chữ cần giữ.", "show": "keep"},
        {"say": "Bước hai: bỏ chi tiết. Tên nhà tâm lý học, tên nhà giáo dục, mốc thế kỷ mười chín và đầu thế kỷ hai mươi đều là chi tiết. Khi đề hỏi tới thì quay lại tìm. Lúc tóm tắt thì bỏ.", "show": "drop"},
        {"say": "Bước ba và bốn: nối những chữ còn lại. Trí thông minh từng bị coi là bẩm sinh. Các nhà tư tưởng phản đối. Cuối cùng, ai cũng có thể phát triển.", "show": "sum"},
        {"say": "Bước năm: ý chính của đoạn là quan niệm đã đổi, từ cố định sang phát triển được.", "show": "main"},
        {"say": "Bước sáu: đoạn này cho biết ý tưởng của bài đến từ đâu.", "show": "value"},
    ]},
    {"kind": "scene", "visual": "para_filter", "eyebrow": "Đoạn 2", "title": "Ý tưởng được dùng ở trường",
     "data": {"segs": segs(P2), "chain": ["popular idea", "slogans in schools", "failure = a chance to improve"],
              "main": "Nhà trường dạy học sinh xem thất bại là cơ hội để giỏi lên.",
              "value": "Cho thấy ý tưởng được dùng ngoài đời ra sao."}, "lines": [
        {"say": "Đoạn hai. Gạch từ khóa trước.", "show": "keep"},
        {"say": "Phần dài nhất là áp phích, bài phát biểu, tấm gương vận động viên. Gom hết lại thành một chữ: khẩu hiệu. Câu trích cuối đoạn chỉ nhắc lại ý đó, nên cũng bỏ.", "show": "drop"},
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
        {"say": "Đoạn ba. Gạch từ khóa: thí nghiệm, khen trí thông minh, khen nỗ lực, sợ thất bại.", "show": "keep"},
        {"say": "Bỏ tên nhà nghiên cứu, nơi làm nghiên cứu, độ tuổi, số nhóm. Câu giải thích lặp lại cũng bỏ.", "show": "drop"},
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

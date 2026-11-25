"""Week 2 · Day 6 (build day 26): slow reading of "The steam car". Four lectures written by hand
(lesson_audio.build_authored_lecture): two reading-method lectures and two short vocabulary sittings with the words of
the passage. vocab_day() gives the two vocabulary sittings their lecture (reshape); finish() then builds the order of
the day: read actively (paragraphs A-B, the learner does C-D), the words, long sentences and the flow (the learner does
E and G), and only then the thirteen questions.

Sources: session 4 of the course, stages 4-6 (the reading method, taught there on another passage), applied to this
passage as docs/WEEK2_PLAN.md (day 6) asks: the four-step self-check with seven minutes of re-reading; jargon the writer
explains or that can be skipped, and the look-it-up-as-a-picture habit; skipping an unknown adjective or adverb and
keeping the noun; the long noun phrase read from its head noun; reduced clauses explained with the simplest sentence
("A book, which was given to me, is Harry Potter"); the part between two commas put aside to join the main subject to
the main verb; the flow of information (a phrase that points back); metaphors; hard grammar is not good grammar, write
clearly; understand everything first, then answer without tricks. Session 3, stage 1 (the past tenses) for the time line.
No teacher, book or page is named on the slides or in the narration.

Pronunciations: Oxford Learner's Dictionaries, British English, read 2026-11-25 (phase out put together from phase and
out, as for the phrases of day 5).
"""
import re

PRON = {
    "inherit": "/ɪnˈherɪt/",
    "shortcoming": "/ˈʃɔːtkʌmɪŋ/",
    "phase out": "/feɪz aʊt/",
    "rekindle": "/ˌriːˈkɪndl/",
    "prototype": "/ˈprəʊtətaɪp/",
    "comprise": "/kəmˈpraɪz/",
    "feat": "/fiːt/",
    "accelerate": "/əkˈseləreɪt/",
    "investment": "/ɪnˈvestmənt/",
    "enhancement": "/ɪnˈhɑːnsmənt/",
    "deposit": "/dɪˈpɒzɪt/",
    "glitch": "/ɡlɪtʃ/",
    "viable": "/ˈvaɪəbl/",
    "emission": "/ɪˈmɪʃn/",
    "fold": "/fəʊld/",
    "maintenance": "/ˈmeɪntənəns/",
}

NOTES = {
    "inherit": "Thừa hưởng từ đời trước: tính cách, tài sản, cả điểm yếu. inherit something from somebody.",
    "shortcoming": "Thường dùng số nhiều: despite its shortcomings. Gần nghĩa weakness, fault.",
    "phase out": "phase là một giai đoạn: phase out là bỏ dần qua từng giai đoạn, không bỏ ngay.",
    "rekindle": "kindle là nhóm lửa; re- là lại. Nghĩa bóng: khơi lại niềm yêu thích; hồi sinh một công nghệ.",
    "prototype": "Mẫu thử, làm trước khi sản xuất hàng loạt. Tra bằng hình ảnh để thấy ngay.",
    "comprise": "comprise không cần of: The team comprises four people. Nghĩa như consist of.",
    "feat": "Một việc khó làm được, đáng khen: an amazing feat.",
    "accelerate": "accelerate from zero to sixty: tăng tốc từ số không lên sáu mươi.",
    "investment": "invest là đầu tư; seek investment: tìm vốn đầu tư.",
    "enhancement": "enhance là nâng lên, làm tốt hơn; enhancement là sự cải tiến.",
    "deposit": "Tiền đặt cọc khi đặt mua: pay a deposit. Cũng là tiền gửi ngân hàng.",
    "glitch": "Lỗi, trục trặc kỹ thuật, thường ở máy móc, phần mềm.",
    "viable": "Khả thi, làm được trên thực tế: a viable option, a viable business.",
    "emission": "emit là thải ra; emission là khí thải. Cụm hay gặp: reduce emissions.",
    "fold": "Nghĩa quen: gấp lại. Với công ty: đóng cửa, phá sản.",
    "maintenance": "maintain là bảo dưỡng; maintenance là sự bảo dưỡng. Để ý chữ viết: main-te-nance.",
}


def segs(text: str) -> list[dict]:
    """'[[keep]]' lights up, '{{drop}}' is struck through; the rest is plain text (as in lecture_d12)."""
    out = []
    for m in re.finditer(r"\[\[(.+?)\]\]|\{\{(.+?)\}\}|([^\[{]+)", text):
        if m.group(1):
            out.append({"t": m.group(1), "k": "k"})
        elif m.group(2):
            out.append({"t": m.group(2), "k": "d"})
        else:
            out.append({"t": m.group(3)})
    return out


MARK = {
    "A": ("When [[primitive automobiles]] first began to appear {{in the 1800s}}, their engines were based on [[steam power]]. Steam had already "
          "enjoyed a long and successful career [[in the railways]], so it was only natural that the technology [[evolved into a miniaturized "
          "version]] {{which was separate from the trains}}. But these early cars [[inherited steam's weaknesses along with its strengths]]. {{The "
          "boilers had to be lit by hand, and they required about twenty minutes to build up pressure before they could be driven. "
          "Furthermore, their water reservoirs only lasted for about thirty miles before needing replenishment.}} Despite such [[shortcomings]], "
          "these newly designed self-propelled carriages offered [[quick transportation]], {{and by the early 1900s it was not uncommon to see "
          "such machines shuttling wealthy citizens around town.}}"),
    "B": ("But the [[glory days of steam cars were few]]. A [[new technology]] called {{the Internal Combustion Engine}} soon appeared, which offered "
          "[[the ability to drive]] down the road just moments after starting up. At first, these noisy gasoline cars were [[unpopular]] because "
          "they were more complicated to operate {{and they had difficult hand-crank starters, which were known to break arms when the "
          "engines backfired}}. But {{in 1912 General Motors introduced}} the [[electric starter]], and {{over the following few years}} steam power "
          "was [[gradually phased out]]."),
    "F": ("The brothers made [[one final attempt to produce a viable steam automobile]]. {{In early 1924, the Doble brothers shipped a Model E to "
          "New York City}} to be [[road-tested]] {{by the Automobile Club of America}}. After sitting overnight [[in freezing temperatures]], the car was "
          "pushed out into the road and left to sit {{for over an hour}} in the [[frosty morning air]]. At the turn of the key, the boiler lit and "
          "[[reached its operating pressure]] {{inside of forty seconds}}. As they drove the test vehicle further, they found that its evenly "
          "distributed weight lent it surprisingly [[good handling]], {{even though it was so heavy}}. As the new Doble steamer was further "
          "developed and tested, its [[maximum speed]] was pushed to {{over a hundred miles per hour}}, and it achieved {{about fifteen miles per "
          "gallon of kerosene}} with [[negligible emissions]]."),
}

# ============================================================ lecture 1: read actively, paragraphs A and B

CHECK = [
    {"key": "c1", "head": "Bước 1", "en": "re-read · 7 minutes", "vi": "Đọc lại cả bài, nhớ lại mạch ý."},
    {"key": "c2", "head": "Bước 2", "en": "new words", "vi": "Ghi những từ chưa biết nghĩa."},
    {"key": "c3", "head": "Bước 3", "en": "sentences", "vi": "Ghi những câu biết từ mà vẫn không hiểu."},
    {"key": "c4", "head": "Bước 4", "en": "paragraphs", "vi": "Ghi những đoạn gần như không hiểu."},
]
TITLE_ROWS = [
    {"key": "t1", "head": "Tiêu đề", "en": "The steam car", "vi": "Chủ đề: chiếc xe chạy bằng hơi nước."},
    {"key": "t2", "head": "Phụ đề", "en": "successes and failures · the Doble brothers", "vi": "Bài kể cả thành công lẫn thất bại của bốn anh em."},
]
JARGON = [
    {"key": "j1", "head": "boilers", "en": "had to be lit by hand", "vi": "Nồi hơi: ngay trong câu có gợi ý."},
    {"key": "j2", "head": "hand-crank starters", "en": "known to break arms", "vi": "Tay quay khởi động: rất khó dùng."},
    {"key": "j3", "head": "pistons", "en": "steam drove the engine pistons", "vi": "Pít-tông: bỏ qua vẫn hiểu câu."},
    {"key": "j4", "head": "kerosene", "en": "fifteen miles per gallon of kerosene", "vi": "Dầu hỏa: một loại nhiên liệu."},
]
SKIP = [
    {"key": "a1", "head": "Tính từ lạ", "en": "self-propelled carriages", "vi": "Giữ danh từ: những cỗ xe."},
    {"key": "a2", "head": "Tính từ lạ", "en": "clattering gas engines", "vi": "Giữ danh từ: động cơ xăng."},
    {"key": "a3", "head": "Trạng từ lạ", "en": "Astonishingly, an unmodified Doble Model E runs clean", "vi": "Giữ khung: chiếc xe chưa sửa đổi vẫn chạy sạch."},
]
HEADING_WAY = [
    {"key": "h1", "head": "Bước 1", "en": "keyword chain", "vi": "Viết chuỗi từ khóa của đoạn."},
    {"key": "h2", "head": "Bước 2", "en": "main idea", "vi": "Nói ý chính của đoạn trong một câu."},
    {"key": "h3", "head": "Bước 3", "en": "compare", "vi": "So câu đó với danh sách tiêu đề."},
    {"key": "h4", "head": "Bước 4", "en": "one sentence only?", "vi": "Loại tiêu đề chỉ khớp một câu của đoạn."},
]

READ_1 = [
    {"kind": "title", "hook": "Biết nghĩa từng từ mà vẫn không hiểu đoạn văn nói gì?", "lines": [
        {"say": "Biết nghĩa từng từ mà vẫn không hiểu đoạn văn nói gì? Đó là dấu hiệu bạn đang dịch từng chữ, chưa đọc hiểu.", "show": "hook"},
        {"say": "Hôm nay mình đọc chậm một bài về chiếc xe chạy bằng hơi nước, từng đoạn một. Hiểu trọn bài rồi mới làm câu hỏi."},
    ]},
    {"kind": "scene", "visual": "ref_table", "eyebrow": "Tự rà bài", "title": "Bốn bước trước khi học bài",
     "data": {"cols": ["Bước", "Việc cần làm"], "rows": CHECK, "rule": "Ba danh sách cho biết bạn cần học từ, học cách đọc câu, hay học cách nối ý."}, "lines": [
        {"say": "Trước khi học kỹ một bài, bạn tự rà trong bốn bước. Bước một: đọc lại cả bài trong bảy phút, để nhớ lại mạch ý.", "show": "c1"},
        {"say": "Bước hai: ghi những từ mới, chưa biết nghĩa.", "show": "c2"},
        {"say": "Bước ba: ghi những câu mà từ nào cũng biết, ghép lại vẫn không hiểu.", "show": "c3"},
        {"say": "Bước bốn: ghi những đoạn gần như không hiểu gì.", "show": "c4"},
        {"say": "Ba danh sách này chỉ ra ba việc khác nhau: học thêm từ, học cách đọc câu dài, hay học cách nối ý giữa các câu.", "show": "rule"},
    ]},
    {"kind": "scene", "visual": "ref_table", "eyebrow": "Trước khi đọc", "title": "Tiêu đề và phụ đề",
     "data": {"cols": ["Phần", "Nói gì"], "rows": TITLE_ROWS, "rule": "Phụ đề báo trước mạch của bài: đọc để tìm lúc thành công, lúc thất bại."}, "lines": [
        {"say": "Đọc tiêu đề trước.", "show": "t1"},
        {"en": "The steam car."},
        {"say": "Bài này có thêm phụ đề.", "show": "t2"},
        {"en": "The successes and failures of the Doble brothers and their steam cars."},
        {"say": "Phụ đề cho biết bài kể cả thành công lẫn thất bại của bốn anh em nhà Doble. Vậy khi đọc, bạn đánh dấu chỗ nào là thành công, chỗ nào là thất bại.", "show": "rule"},
    ]},
    {"kind": "scene", "visual": "para_filter", "eyebrow": "Đoạn A · đoạn thứ nhất", "title": "Hơi nước đi từ tàu hỏa sang ô tô",
     "data": {"segs": segs(MARK["A"]), "chain": ["railway steam", "steam car", "weak + strong", "still fast"],
              "main": "Xe hơi nước thừa hưởng cả mạnh lẫn yếu của hơi nước.",
              "value": "Mở đầu: công nghệ đến từ đâu, mạnh yếu ra sao."}, "lines": [
        {"say": "Đoạn thứ nhất. Tô vàng từ khóa: xe đời đầu, chạy bằng hơi nước, vốn thành công ở đường sắt, rồi được thu nhỏ thành ô tô.", "show": "keep"},
        {"say": "Để ý ba từ của ngày năm. Ô tô đời đầu được gọi là sơ khai; công nghệ phát triển thành một phiên bản nhỏ hơn; bình nước chỉ đủ dùng cho ba mươi dặm."},
        {"en": "primitive, evolve into, last"},
        {"say": "Câu quan trọng nhất của đoạn là câu này."},
        {"en": "But these early cars inherited steam's weaknesses along with its strengths.", "vi": "Nhưng những chiếc xe đời đầu này thừa hưởng cả điểm yếu lẫn điểm mạnh của hơi nước.", "gap": True},
        {"say": "Phần bị gạch là chi tiết: nhóm lửa bằng tay, chờ hai mươi phút, nước chỉ đủ ba mươi dặm. Ba chi tiết này gom lại thành một chữ: điểm yếu. Người viết tự gom giúp bạn: such shortcomings, những điểm yếu như vậy, chỉ ngược về danh sách vừa kể.", "show": "drop"},
        {"say": "Chuỗi còn lại: hơi nước ở đường sắt, sang ô tô, mang theo cả mạnh lẫn yếu, nhưng vẫn đi nhanh.", "show": "sum"},
        {"say": "Ý chính: xe hơi nước thừa hưởng cả điểm mạnh lẫn điểm yếu của công nghệ hơi nước.", "show": "main"},
        {"say": "Giá trị: đoạn này mở đầu câu chuyện, cho biết công nghệ đến từ đâu, mạnh và yếu ra sao.", "show": "value"},
    ]},
    {"kind": "scene", "visual": "ref_table", "eyebrow": "Từ chuyên ngành", "title": "Hiểu đủ dùng, hoặc bỏ qua",
     "data": {"cols": ["Từ", "Trong bài", "Cần hiểu tới đâu"], "rows": JARGON,
              "rule": "Gặp từ chuyên ngành, đọc tiếp phần ngay sau; người viết thường giải thích. Không có thì hiểu nó thuộc loại gì rồi đi tiếp."}, "lines": [
        {"say": "Nhiều bạn sẽ ghi vào danh sách từ mới những chữ như boilers. Đây là từ chuyên ngành; người bản xứ không làm nghề cơ khí cũng có thể không rõ. Ngay trong câu đó có gợi ý: phải nhóm lửa bằng tay và chờ lên áp suất. Hiểu là nồi hơi là đủ.", "show": "j1"},
        {"say": "Tay quay khởi động ở đoạn thứ hai: phần ngay sau nói nó từng làm gãy tay người dùng. Vậy là đủ hiểu: khởi động rất khó.", "show": "j2"},
        {"say": "Pistons ở đoạn thứ ba: bỏ qua, bạn vẫn hiểu là hơi nước làm máy chạy rất êm.", "show": "j3"},
        {"say": "Kerosene ở đoạn thứ sáu là dầu hỏa. Biết đó là một loại nhiên liệu là đủ. Muốn hình dung nồi hơi hay tay quay, hãy tra bằng hình ảnh: nhìn năm giây, bạn hiểu nhanh hơn đọc một dòng định nghĩa.", "show": "j4"},
        {"say": "Gặp từ chuyên ngành, đọc tiếp phần ngay sau; người viết thường giải thích. Không có lời giải thích thì chỉ cần biết nó thuộc loại gì, rồi đi tiếp.", "show": "rule"},
    ]},
    {"kind": "scene", "visual": "ref_table", "eyebrow": "Đọc lấy ý", "title": "Tính từ lạ: lướt qua, giữ danh từ",
     "data": {"cols": ["Loại", "Trong bài", "Giữ lại"], "rows": SKIP,
              "rule": "Đọc lấy ý: tính từ và trạng từ lạ thì lướt qua; danh từ và động từ mới là khung của câu."}, "lines": [
        {"say": "Self-propelled đứng trước danh từ, nên là tính từ. Không biết nghĩa cũng không sao: giữ danh từ, những cỗ xe.", "show": "a1"},
        {"say": "Clattering cũng đứng trước danh từ. Giữ lại: động cơ xăng.", "show": "a2"},
        {"say": "Astonishingly có đuôi của trạng từ. Bỏ qua, ý chính vẫn còn: xe vẫn chạy sạch.", "show": "a3"},
        {"say": "Nhìn vị trí và đuôi từ là đoán được từ loại, như đuôi tính từ trong chữ practical, đuôi trạng từ trong chữ clearly. Khi đọc lấy ý, danh từ và động từ là khung của câu; tính từ và trạng từ lạ thì lướt qua.", "show": "rule"},
    ]},
    {"kind": "scene", "visual": "para_filter", "eyebrow": "Đoạn B · đoạn thứ hai", "title": "Một công nghệ mới xuất hiện",
     "data": {"segs": segs(MARK["B"]), "chain": ["glory days few", "new engine", "electric starter", "steam phased out"],
              "main": "Một công nghệ tốt hơn xuất hiện và dần thay thế xe hơi nước.",
              "value": "Nút thắt của câu chuyện: xe hơi nước mất thị trường."}, "lines": [
        {"say": "Đoạn thứ hai. Câu đầu là một hình ảnh: glory days, thời hoàng kim. Thời hoàng kim của xe hơi nước chỉ có vài năm.", "show": "keep"},
        {"en": "But the glory days of steam cars were few.", "vi": "Nhưng thời hoàng kim của xe hơi nước chẳng được bao lâu.", "gap": True},
        {"say": "Phần bị gạch: tên của động cơ mới, tên công ty, năm, và chuyện tay quay làm gãy tay. Đó là chi tiết; khi đề hỏi thì quay lại tìm.", "show": "drop"},
        {"say": "Để ý mạch ý. Cụm sau đây nghĩa là những chiếc xe chạy xăng ồn ào này."},
        {"en": "these noisy gasoline cars"},
        {"say": "Đó chính là công nghệ mới vừa nhắc ở câu trước. Người viết đổi cách gọi, và người đọc phải tự nối lại."},
        {"say": "Chuỗi: thời hoàng kim ngắn, động cơ mới xuất hiện, có bộ khởi động điện, xe hơi nước bị loại dần.", "show": "sum"},
        {"say": "Ý chính: một công nghệ tốt hơn xuất hiện và dần thay thế xe hơi nước.", "show": "main"},
        {"say": "Giá trị: đây là nút thắt. Từ đoạn sau, câu chuyện là anh em nhà Doble cố cứu một công nghệ đang mất thị trường.", "show": "value"},
    ]},
    {"kind": "scene", "visual": "ref_table", "eyebrow": "Tiêu đề của đoạn", "title": "Tiêu đề tóm cả đoạn",
     "data": {"cols": ["Bước", "Việc cần làm"], "rows": HEADING_WAY, "rule": "Tiêu đề đúng là bản tóm tắt tốt nhất của cả đoạn, không phải của một câu trong đoạn."}, "lines": [
        {"say": "Phần câu hỏi đầu tiên của bài là chọn tiêu đề cho từng đoạn. Chuỗi từ khóa bạn vừa làm chính là công cụ.", "show": "h1"},
        {"say": "Từ chuỗi, nói ý chính của đoạn trong một câu.", "show": "h2"},
        {"say": "Rồi mới so câu đó với danh sách tiêu đề.", "show": "h3"},
        {"say": "Tiêu đề nào chỉ khớp một câu, hay chỉ trùng một chữ, thì loại.", "show": "h4"},
        {"say": "Tiêu đề đúng là bản tóm tắt tốt nhất của cả đoạn, không phải của một câu trong đoạn.", "show": "rule"},
    ]},
    {"kind": "end", "next": "Tiếp theo: tự viết chuỗi từ khóa cho đoạn C và D, rồi học từ của bài.", "lines": [
        {"say": "Hết phần giảng. Bây giờ bạn tự làm như vậy cho đoạn thứ ba và đoạn thứ tư: tô từ khóa, bỏ chi tiết, nối thành chuỗi có mũi tên. Câu hỏi để sau cùng.", "show": "title"},
    ]},
]

# ============================================================ the two vocabulary sittings

FROM_DAY5 = [
    {"key": "d1", "head": "primitive", "en": "primitive automobiles", "vi": "ô tô sơ khai, đời đầu"},
    {"key": "d2", "head": "evolve into", "en": "evolved into a miniaturized version", "vi": "công nghệ phát triển thành một phiên bản thu nhỏ"},
    {"key": "d3", "head": "last", "en": "only lasted for about thirty miles", "vi": "bình nước chỉ đủ cho khoảng ba mươi dặm"},
    {"key": "d4", "head": "innovation", "en": "expand upon the innovations", "vi": "mở rộng các cải tiến của mẫu trước"},
    {"key": "d5", "head": "remain", "en": "Abner Doble remained adamant", "vi": "ông vẫn một mực tin như vậy"},
]
FAMILY = [
    {"key": "f1", "head": "invest", "en": "investment", "vi": "đầu tư → vốn đầu tư"},
    {"key": "f2", "head": "enhance", "en": "enhancement", "vi": "nâng lên → sự cải tiến"},
    {"key": "f3", "head": "emit", "en": "emission", "vi": "thải ra → khí thải"},
    {"key": "f4", "head": "maintain", "en": "maintenance", "vi": "bảo dưỡng → sự bảo dưỡng"},
]

SITTING_1 = [
    {"kind": "title", "hook": "Vì sao một công nghệ đang tốt lại bị bỏ đi?", "lines": [
        {"say": "Vì sao một công nghệ đang tốt lại bị bỏ đi?", "show": "hook"},
        {"say": "Tám từ của buổi này kể lại nửa đầu câu chuyện. Ưu tiên động từ và danh từ; hai từ chỉ cần nhận ra khi đọc."},
    ]},
    {"kind": "word", "headword": "inherit", "lines": [
        {"say": "Con cái thừa hưởng nét mặt của bố mẹ. Xe hơi nước đời đầu thừa hưởng cả điểm mạnh lẫn điểm yếu của công nghệ hơi nước."},
    ]},
    {"kind": "word", "headword": "shortcoming", "lines": [
        {"say": "Điểm yếu, thiếu sót. Từ này thường ở số nhiều. Trong bài, người viết dùng nó để gom ba điểm yếu vừa kể."},
        {"en": "Despite such shortcomings, the cars offered quick transportation.", "vi": "Dù có những điểm yếu như vậy, xe vẫn là phương tiện đi lại nhanh.", "gap": True},
    ]},
    {"kind": "word", "headword": "phase out", "lines": [
        {"say": "Phase là một giai đoạn. Phase out là bỏ đi qua từng giai đoạn, không bỏ ngay một lúc. Xe hơi nước không biến mất trong một ngày; nó bị loại dần trong vài năm."},
        {"en": "Steam power was gradually phased out.", "vi": "Năng lượng hơi nước dần bị loại bỏ.", "gap": True},
    ]},
    {"kind": "word", "headword": "rekindle", "lines": [
        {"say": "Kindle là nhóm lửa; thêm re là nhóm lại. Bốn anh em muốn nhóm lại ngọn lửa của một công nghệ đang tàn. Từ này chỉ cần nhận ra khi đọc."},
    ]},
    {"kind": "word", "headword": "prototype", "lines": [
        {"say": "Mẫu thử, làm trước khi sản xuất hàng loạt. Chiếc đầu chạy không tốt, nên anh em nhà Doble làm tiếp mẫu thứ hai, mẫu thứ ba. Từ này nên tra bằng hình ảnh."},
    ]},
    {"kind": "word", "headword": "comprise", "lines": [
        {"say": "Gồm có, nghĩa như cụm consist of. Điểm khác: sau từ này không cần giới từ. Chiếc xe đầu tiên gồm những phụ tùng lấy từ một chiếc xe cũ bị hỏng."},
    ]},
    {"kind": "word", "headword": "feat", "lines": [
        {"say": "Một việc khó làm được, đáng khen. Từ số không lên sáu mươi dặm một giờ trong mười lăm giây là một kỳ công thời đó. Từ này chỉ cần nhận ra."},
    ]},
    {"kind": "word", "headword": "accelerate", "lines": [
        {"say": "Tăng tốc, như speed up. Cụm trong bài: tăng tốc từ số không lên sáu mươi."},
        {"en": "It could accelerate from zero to sixty miles per hour in just fifteen seconds.", "vi": "Nó có thể tăng tốc từ không lên sáu mươi dặm một giờ chỉ trong mười lăm giây.", "gap": True},
    ]},
    {"kind": "scene", "visual": "ref_table", "eyebrow": "Gặp lại từ hôm qua", "title": "Từ của ngày năm trong bài đọc",
     "data": {"cols": ["Từ", "Trong bài", "Nghĩa trong câu"], "rows": FROM_DAY5, "rule": "Từ gặp lại trong một bài đọc thật là bước đưa từ vào trí nhớ dài hạn."}, "lines": [
        {"say": "Bài đọc này có nhiều từ của ngày năm. Primitive automobiles là những chiếc ô tô sơ khai, đời đầu.", "show": "d1"},
        {"say": "Công nghệ phát triển thành một phiên bản nhỏ hơn: evolve into, đúng giới từ đã học.", "show": "d2"},
        {"say": "Last ở đây là kéo dài, đủ dùng: bình nước chỉ đủ khoảng ba mươi dặm.", "show": "d3"},
        {"say": "Mẫu xe mới mở rộng các cải tiến của mẫu trước.", "show": "d4"},
        {"say": "Và remain đi với tính từ: ông vẫn một mực giữ niềm tin của mình.", "show": "d5"},
        {"say": "Gặp lại từ trong một bài đọc thật, lần thứ hai, lần thứ ba: đó là cách đưa từ vào trí nhớ dài hạn.", "show": "rule"},
    ]},
    {"kind": "recap", "lines": [
        {"say": "Giờ nói lại các câu của buổi này. Nghe một câu, rồi nói to trong quãng nghỉ.", "show": "title"},
    ]},
    {"kind": "end", "next": "Tiếp theo: tám từ của nửa sau câu chuyện.", "lines": [
        {"say": "Hết buổi từ thứ nhất. Buổi sau là tám từ của nửa sau câu chuyện: công ty, đơn đặt hàng, lỗi máy và khí thải.", "show": "title"},
    ]},
]

SITTING_2 = [
    {"kind": "title", "hook": "Một chiếc xe tuyệt vời mà công ty vẫn phá sản: vì sao?", "lines": [
        {"say": "Một chiếc xe tuyệt vời mà công ty vẫn phá sản: vì sao?", "show": "hook"},
        {"say": "Tám từ của buổi này kể nửa sau câu chuyện, từ lúc tìm vốn tới hôm nay."},
    ]},
    {"kind": "word", "headword": "investment", "lines": [
        {"say": "Muốn mở công ty thì cần vốn. Abner lái xe tới Detroit để tìm vốn đầu tư."},
        {"en": "He drove to Detroit to seek investment.", "vi": "Ông lái xe tới Detroit để tìm vốn đầu tư.", "gap": True},
    ]},
    {"kind": "word", "headword": "enhancement", "lines": [
        {"say": "Sự cải tiến, nâng cấp, như improvement. Mẫu xe mới có thêm khóa đánh lửa trong cabin: người lái không phải châm lửa bằng tay nữa."},
    ]},
    {"kind": "word", "headword": "deposit", "lines": [
        {"say": "Đặt mua một chiếc xe chưa sản xuất xong, bạn trả trước một khoản tiền đặt cọc. Công ty nhận hơn năm nghìn khoản đặt cọc như vậy."},
    ]},
    {"kind": "word", "headword": "glitch", "lines": [
        {"say": "Lỗi, trục trặc của máy móc hay phần mềm. Xe giao cho khách chạy ì, có lúc chạy lùi: động cơ còn đầy lỗi. Từ này chỉ cần nhận ra."},
        {"en": "The new engine was still plagued with serious glitches.", "vi": "Động cơ mới vẫn liên tục gặp những lỗi nghiêm trọng.", "gap": True},
    ]},
    {"kind": "word", "headword": "viable", "lines": [
        {"say": "Khả thi, dùng được trên thực tế. Lần cuối, bốn anh em cố làm ra một chiếc xe hơi nước thật sự dùng được. Từ này rất hay gặp trong Writing: một lựa chọn khả thi."},
    ]},
    {"kind": "word", "headword": "emission", "lines": [
        {"say": "Khí thải. Chiếc xe cuối cùng có lượng khí thải không đáng kể. Cụm hay gặp trong bài về môi trường: giảm khí thải."},
        {"en": "We need to reduce emissions.", "vi": "Chúng ta cần giảm khí thải.", "gap": True},
    ]},
    {"kind": "word", "headword": "fold", "lines": [
        {"say": "Fold quen nghĩa là gấp lại, như gấp một tờ giấy. Một công ty gấp lại là công ty đóng cửa, phá sản."},
    ]},
    {"kind": "word", "headword": "maintenance", "lines": [
        {"say": "Ở ngày năm, bạn học maintain đi với chiếc xe: bảo dưỡng xe. Danh từ của nó là maintenance. Có chiếc xe đã chạy hơn nửa triệu dặm mà chỉ cần bảo dưỡng bình thường."},
    ]},
    {"kind": "scene", "visual": "ref_table", "eyebrow": "Một họ từ", "title": "Biết động từ, đoán được danh từ",
     "data": {"cols": ["Động từ", "Danh từ", "Nghĩa"], "rows": FAMILY, "rule": "Học từ kèm từ loại: biết động từ thì nhận ra danh từ của nó khi đọc."}, "lines": [
        {"say": "Bốn danh từ của buổi này đều sinh ra từ một động từ. Invest là đầu tư, thành vốn đầu tư.", "show": "f1"},
        {"say": "Enhance là nâng lên, thành sự cải tiến.", "show": "f2"},
        {"say": "Emit là thải ra, thành khí thải.", "show": "f3"},
        {"say": "Maintain là bảo dưỡng, thành sự bảo dưỡng. Để ý chữ viết của danh từ này: phần giữa đổi khác, không giữ nguyên như động từ.", "show": "f4"},
        {"say": "Học từ thì học cả từ loại. Biết động từ, bạn nhận ra ngay danh từ của nó trong bài đọc.", "show": "rule"},
    ]},
    {"kind": "recap", "lines": [
        {"say": "Giờ nói lại các câu của buổi này. Nghe một câu, rồi nói to trong quãng nghỉ.", "show": "title"},
    ]},
    {"kind": "end", "next": "Tiếp theo: câu dài và mạch thông tin của đoạn C đến G.", "lines": [
        {"say": "Hết buổi từ thứ hai. Buổi sau học cách đọc những câu dài nhất của bài. Mình cũng sẽ theo mạch thông tin từ đoạn này sang đoạn khác.", "show": "title"},
    ]},
]

# ============================================================ lecture 2: long sentences and the flow, paragraphs C to G

BOOK_MODEL = [
    {"key": "r1", "head": "Câu đầy đủ", "en": "A book, which was given to me, is Harry Potter.", "vi": "Chủ ngữ: a book. Động từ chính: is."},
    {"key": "r2", "head": "Rút gọn", "en": "A book, given to me, is Harry Potter.", "vi": "Bỏ which và was, còn lại V3."},
    {"key": "r3", "head": "Trong bài", "en": "parts taken from a wrecked early steam car but reconfigured…",
     "vi": "parts (which were) taken … but (which were) reconfigured …"},
]
INSERTS = [
    {"key": "i1", "head": "Tên gọi chèn giữa", "en": "the Doble boys' third prototype, nicknamed the Model B,", "vi": "= which was nicknamed: chỉ là tên của mẫu thứ ba."},
    {"key": "i2", "head": "Chèn giữa câu", "en": "The new engine design, though innovative, was still plagued with serious glitches.", "vi": "Khung câu: thiết kế mới vẫn đầy lỗi."},
    {"key": "i3", "head": "Cụm giải thích", "en": "a feat described as 'remarkable acceleration'", "vi": "a feat: danh từ tóm lại cả ý trước; described = which was described."},
]
NOUNS = [
    {"key": "n1", "head": "ignition", "en": "a key-based ignition in the cabin", "vi": "bộ đánh lửa → khởi động bằng chìa khóa → đặt trong cabin"},
    {"key": "n2", "head": "improvements", "en": "numerous improvements over previous steam cars", "vi": "những cải tiến → rất nhiều → so với các xe hơi nước trước đó"},
    {"key": "n3", "head": "powerplant", "en": "a virtually silent powerplant", "vi": "cụm động cơ → gần như không có tiếng động"},
]
TIMELINE = [
    {"key": "p1", "icon": "kettle", "label": "Trước đó", "kind": "bg", "en": "Steam had already enjoyed a long and successful career in the railways.", "vi": "Xảy ra trước mốc: quá khứ hoàn thành."},
    {"key": "p2", "icon": "prototype", "label": "1906–1914", "kind": "chain", "en": "Even as the market was declining, four brothers made one last effort.", "vi": "Bối cảnh: quá khứ tiếp diễn."},
    {"key": "p3", "icon": "fail_x", "label": "1931", "kind": "event", "en": "Fewer than fifty of the Model E steam cars had been produced.", "vi": "Tính tới một mốc, bị động."},
    {"key": "p4", "icon": "car", "label": "Hôm nay", "kind": "chain", "en": "Many of the Model E Dobles which have survived are still in good working condition.", "vi": "Về tới bây giờ."},
]
POINT_BACK = [
    {"key": "b1", "head": "Đoạn A", "en": "Despite such shortcomings", "vi": "= những điểm yếu vừa kể ở các câu trước"},
    {"key": "b2", "head": "Đoạn B", "en": "these noisy gasoline cars", "vi": "= công nghệ mới vừa nhắc, gọi bằng tên khác"},
    {"key": "b3", "head": "Đoạn D", "en": "With these enhancements", "vi": "= các tính năng vừa thêm, như khóa đánh lửa"},
    {"key": "b4", "head": "Đoạn G", "en": "Given the evidence", "vi": "= bằng chứng của cả câu chuyện: xe tốt, nhanh, sạch"},
]
IMAGES = [
    {"key": "m1", "icon": "star", "head": "glory days", "en": "the glory days of steam cars", "vi": "thời hoàng kim"},
    {"key": "m2", "icon": "lamp", "head": "rekindle", "en": "rekindle the technology", "vi": "nhóm lại ngọn lửa: hồi sinh"},
    {"key": "m3", "icon": "bug", "head": "plagued", "en": "plagued with serious glitches", "vi": "lỗi bám dai như bệnh dịch"},
    {"key": "m4", "icon": "fail", "head": "folded", "en": "the company folded", "vi": "gấp lại: đóng cửa"},
    {"key": "m5", "icon": "rocket", "head": "rise again", "en": "the steam car may rise again", "vi": "trỗi dậy lần nữa"},
]
CLEAR = [
    {"key": "e1", "head": "Bài đọc", "en": "the Doble boys' third prototype, nicknamed the Model B, still lacked the convenience…", "vi": "Chủ ngữ và động từ bị tách xa."},
    {"key": "e2", "head": "Khi bạn viết", "en": "The third prototype was called the Model B. It was still less convenient than a gasoline car.", "vi": "Tách thành hai câu rõ ràng."},
]

READ_2 = [
    {"kind": "title", "hook": "Câu dài ba dòng: chủ ngữ ở đầu, động từ chính nằm ở đâu?", "lines": [
        {"say": "Câu dài ba dòng: chủ ngữ ở đầu, còn động từ chính nằm ở đâu?", "show": "hook"},
        {"say": "Buổi này học cách đọc những câu dài nhất của bài, rồi theo mạch thông tin từ đoạn thứ ba tới đoạn cuối."},
    ]},
    {"kind": "scene", "visual": "ref_table", "eyebrow": "Mệnh đề rút gọn", "title": "Bắt đầu từ câu dễ nhất",
     "data": {"cols": ["Bước", "Câu", "Khung câu"], "rows": BOOK_MODEL, "rule": "V3 ngay sau danh từ: thêm which + be. V-ing: thêm which + động từ chia thì. Rồi nối chủ ngữ với động từ chính."}, "lines": [
        {"say": "Bắt đầu bằng một câu thật dễ.", "show": "r1"},
        {"en": "A book, which was given to me, is Harry Potter.", "vi": "Một cuốn sách, cuốn được tặng cho tôi, là Harry Potter.", "gap": True},
        {"say": "Chủ ngữ chính là cuốn sách, động từ chính là is. Phần giữa hai dấu phẩy là phần phụ."},
        {"say": "Bỏ hai chữ đầu của phần phụ đi, câu vẫn đúng. Phần phụ chỉ còn động từ ở dạng thứ ba.", "show": "r2"},
        {"en": "A book, given to me, is Harry Potter.", "vi": "Một cuốn sách được tặng cho tôi là Harry Potter.", "gap": True},
        {"say": "Giờ đến câu trong đoạn thứ ba.", "show": "r3"},
        {"en": "It comprised parts taken from a wrecked early steam car but reconfigured…"},
        {"say": "Khung câu chỉ là: nó gồm những phụ tùng. Phụ tùng nào? Phụ tùng được lấy từ một chiếc xe cũ bị hỏng, nhưng được lắp lại để chạy một động cơ do chính họ thiết kế. Hai động từ dạng thứ ba này đều là phần rút gọn; thêm hai chữ sau vào trước là thấy rõ."},
        {"en": "which were taken, which were reconfigured"},
        {"say": "Thấy động từ dạng thứ ba đứng ngay sau một danh từ, hãy hình dung phần bị lược, như hai chữ vừa thêm. Với dạng hiện tại phân từ, phần bị lược là đại từ quan hệ cùng động từ chia thì. Rồi nối chủ ngữ với động từ chính.", "show": "rule"},
    ]},
    {"kind": "scene", "visual": "ref_table", "eyebrow": "Phần chèn", "title": "Gạt phần chèn sang một bên",
     "data": {"cols": ["Kiểu", "Trong bài", "Đọc thế nào"], "rows": INSERTS, "rule": "Bỏ tạm phần giữa hai dấu phẩy, nối chủ ngữ chính với động từ chính; hiểu khung rồi mới đọc phần chèn."}, "lines": [
        {"say": "Kiểu thứ nhất: phần giữa hai dấu phẩy cho biết tên của danh từ đứng ngay trước. Mẫu thứ ba của anh em nhà Doble có tên gọi riêng. Không cần tra xem cái tên nghĩa là gì.", "show": "i1"},
        {"say": "Kiểu thứ hai: người viết chèn một ý vào giữa chủ ngữ và động từ.", "show": "i2"},
        {"en": "The new engine design, though innovative, was still plagued with serious glitches.", "vi": "Thiết kế động cơ mới, dù sáng tạo, vẫn liên tục gặp lỗi nghiêm trọng.", "gap": True},
        {"say": "Bỏ tạm phần chèn, bạn còn khung: thiết kế mới vẫn đầy lỗi. Rồi mới đọc phần chèn: dù sáng tạo. Innovative là một từ của ngày năm."},
        {"say": "Kiểu thứ ba: một cụm giải thích cho cả ý đứng trước. Tăng tốc lên sáu mươi trong mười lăm giây là một kỳ công, được một tạp chí ô tô gọi là khả năng tăng tốc đáng nể.", "show": "i3"},
        {"say": "Gặp phần chèn, bỏ tạm nó đi, nối chủ ngữ chính với động từ chính. Hiểu khung câu rồi mới quay lại đọc phần chèn.", "show": "rule"},
    ]},
    {"kind": "scene", "visual": "ref_table", "eyebrow": "Cụm danh từ", "title": "Tìm danh từ chính trước",
     "data": {"cols": ["Danh từ chính", "Cụm trong bài", "Dịch"], "rows": NOUNS, "rule": "Tìm danh từ chính, dịch nó trước; chữ đứng trước nó dịch ngược lên, chữ đứng sau dịch xuôi."}, "lines": [
        {"say": "Cụm danh từ dài, tách từng chữ ra thì không hiểu. Hãy tìm danh từ chính trước. Ở cụm này, danh từ chính là ignition, bộ đánh lửa. Rồi dịch ngược lên: khởi động bằng chìa khóa. Phần đứng sau dịch xuôi: đặt trong cabin.", "show": "n1"},
        {"say": "Cụm thứ hai: danh từ chính là improvements, những cải tiến. Rất nhiều cải tiến, so với các xe hơi nước trước đó.", "show": "n2"},
        {"say": "Cụm thứ ba: danh từ chính là powerplant, cụm động cơ. Virtually silent: gần như im lặng.", "show": "n3"},
        {"say": "Tìm danh từ chính, dịch nó trước. Chữ đứng trước dịch ngược lên, chữ đứng sau dịch xuôi.", "show": "rule"},
    ]},
    {"kind": "scene", "visual": "story_strip", "eyebrow": "Trục thời gian", "title": "Câu chuyện đi qua các thì",
     "data": {"frame": "strip", "panels": TIMELINE, "rule": "Việc xảy ra trước mốc kể chuyện: quá khứ hoàn thành. Đoạn cuối về tới hôm nay: hiện tại hoàn thành và hiện tại đơn."}, "lines": [
        {"say": "Bài này là một câu chuyện theo thời gian, nên các thì quá khứ của tuần này xuất hiện liền một mạch. Mốc đầu: những năm 1800, khi ô tô đời đầu xuất hiện. Việc hơi nước thành công ở đường sắt xảy ra trước mốc đó, nên dùng quá khứ hoàn thành.", "show": "p1"},
        {"say": "Thị trường đang đi xuống thì bốn anh em ra tay: quá khứ tiếp diễn cho bối cảnh đang diễn ra, quá khứ đơn cho việc chính. Để ý: đoạn thứ hai đã kể tới năm 1912, rồi đoạn thứ ba quay ngược về 1906; lúc đó thị trường đã đang đi xuống.", "show": "p2"},
        {"say": "Tới lúc công ty đóng cửa năm 1931, chưa tới năm mươi chiếc đã được sản xuất: quá khứ hoàn thành, tính tới một mốc đã qua, ở dạng bị động. Khoản đặt cọc ở đoạn thứ tư cũng là quá khứ hoàn thành tính tới một mốc, nhưng ở dạng chủ động: tính tới tháng Tư năm sau, công ty đã nhận hơn năm nghìn khoản.", "show": "p3"},
        {"say": "Đoạn cuối về tới hôm nay: nhiều chiếc còn tồn tại và vẫn chạy tốt.", "show": "p4"},
        {"say": "Việc xảy ra trước mốc kể chuyện dùng quá khứ hoàn thành. Khi câu chuyện về tới bây giờ, người viết chuyển sang hiện tại hoàn thành và hiện tại đơn.", "show": "rule"},
    ]},
    {"kind": "scene", "visual": "ref_table", "eyebrow": "Mạch thông tin", "title": "Những cụm chỉ ngược về trước",
     "data": {"cols": ["Ở đâu", "Cụm", "Chỉ về"], "rows": POINT_BACK, "rule": "Biết hết từ vẫn chưa đủ: phải nối được câu này với câu trước. Đó mới là đọc hiểu."}, "lines": [
        {"say": "Nhiều bạn tra hết từ mà vẫn không hiểu bài. Lý do là không nối được câu này với câu trước. Ở đoạn thứ nhất: những điểm yếu như vậy là những điểm yếu nào? Là ba điểm vừa kể.", "show": "b1"},
        {"say": "Ở đoạn thứ hai: những chiếc xe chạy xăng ồn ào này chính là công nghệ mới vừa nhắc.", "show": "b2"},
        {"say": "Ở đoạn thứ tư: với những cải tiến này, là khóa đánh lửa và các tính năng vừa thêm.", "show": "b3"},
        {"say": "Ở đoạn cuối: dựa trên bằng chứng, ông có thể đã đúng. Bằng chứng là cả câu chuyện, và các câu ngay sau: xe còn chạy tốt và đủ sạch.", "show": "b4"},
        {"say": "Đọc hiểu là có một mạch thông tin chạy từ đầu tới cuối bài, không phải từng câu, từng từ rời rạc.", "show": "rule"},
    ]},
    {"kind": "scene", "visual": "picture_cards", "eyebrow": "Hình ảnh trong bài", "title": "Nghĩa bóng, không dịch từng chữ",
     "data": {"rows": IMAGES, "rule": "Chữ quen mà nghĩa đen không hợp câu: tìm nghĩa bóng trong văn cảnh."}, "lines": [
        {"say": "Bài này có nhiều hình ảnh. Glory days là thời hoàng kim.", "show": "m1"},
        {"say": "Rekindle là nhóm lại ngọn lửa: hồi sinh một công nghệ đang tàn.", "show": "m2"},
        {"say": "Plagued: lỗi bám dai như bệnh dịch.", "show": "m3"},
        {"say": "Folded: công ty gấp lại, tức là đóng cửa.", "show": "m4"},
        {"say": "Rise again: xe hơi nước có thể trỗi dậy lần nữa.", "show": "m5"},
        {"say": "Gặp chữ quen mà nghĩa đen không hợp câu, hãy tìm nghĩa bóng trong văn cảnh.", "show": "rule"},
    ]},
    {"kind": "scene", "visual": "para_filter", "eyebrow": "Đoạn F · đoạn thứ sáu", "title": "Lần thử cuối cùng",
     "data": {"segs": segs(MARK["F"]), "chain": ["final attempt", "cold test", "fast start", "good handling, fast, clean"],
              "main": "Mẫu xe cuối cùng qua được bài thử trong giá lạnh và chạy tốt hơn hẳn.",
              "value": "Cho thấy công nghệ gần như hoàn thiện, ngay trước đoạn kết."}, "lines": [
        {"say": "Đoạn thứ sáu. Tô vàng từ khóa: lần thử cuối, một chiếc xe hơi nước dùng được thật sự, được chạy thử, trong giá lạnh.", "show": "keep"},
        {"say": "Phần bị gạch là năm, tên thành phố, tên câu lạc bộ và các con số. Bốn mươi giây, hơn một trăm dặm một giờ, mười lăm dặm cho mỗi đơn vị nhiên liệu: tất cả gom lại thành một chữ, rất tốt.", "show": "drop"},
        {"say": "Chuỗi: lần thử cuối, để qua đêm trong giá lạnh, khởi động rất nhanh, lái dễ, chạy nhanh và sạch.", "show": "sum"},
        {"say": "Ý chính: mẫu xe cuối cùng qua được bài thử trong giá lạnh và chạy tốt hơn hẳn.", "show": "main"},
        {"say": "Giá trị: công nghệ gần như hoàn thiện. Vậy tại sao vẫn thất bại? Đó là câu hỏi của đoạn cuối.", "show": "value"},
    ]},
    {"kind": "scene", "visual": "ref_table", "eyebrow": "Khi bạn viết", "title": "Ngữ pháp khó hay ngữ pháp hiệu quả",
     "data": {"cols": ["Ở đâu", "Câu", "Vì sao"], "rows": CLEAR, "rule": "Ngữ pháp khó đọc không phải ngữ pháp hay. Viết rõ ràng, hiệu quả mới là viết tốt."}, "lines": [
        {"say": "Bài đọc dùng câu dài, nhiều phần chèn để thử xem người đọc có thật sự hiểu ngữ pháp không.", "show": "e1"},
        {"say": "Khi viết, đừng bắt chước. Tách thành hai câu rõ ràng.", "show": "e2"},
        {"en": "The third prototype was called the Model B. It was still less convenient than a gasoline car.", "vi": "Mẫu thử thứ ba được gọi là Model B. Nó vẫn kém tiện lợi hơn xe chạy xăng.", "gap": True},
        {"say": "Nhiều người nghĩ câu càng khó càng giỏi. Thật ra, ngữ pháp khó đọc không phải ngữ pháp hay. Viết rõ ràng, hiệu quả mới là viết tốt.", "show": "rule"},
    ]},
    {"kind": "end", "next": "Tiếp theo: chuỗi từ khóa cho đoạn E và G, một câu tóm cả bài; rồi mới làm 13 câu hỏi.", "lines": [
        {"say": "Hết phần giảng. Bạn tự viết chuỗi cho đoạn thứ năm và đoạn cuối, rồi một câu tóm tắt cả bài. Sau đó mới làm mười ba câu hỏi, bằng chính việc hiểu bài, chưa cần mẹo. Hiểu trọn bài rồi mà làm đúng được bao nhiêu câu, đó là trình độ thật của bạn.", "show": "title"},
    ]},
]

S_WORDS = [
    ["inherit", "shortcoming", "phase out", "rekindle", "prototype", "comprise", "feat", "accelerate"],
    ["investment", "enhancement", "deposit", "glitch", "viable", "emission", "fold", "maintenance"],
]
TITLES = ["Buổi từ 1 · nửa đầu câu chuyện", "Buổi từ 2 · nửa sau câu chuyện"]
LECTURES = [SITTING_1, SITTING_2]
READ_TITLES = ["Đọc chủ động · rà bài, tóm tắt đoạn A và B", "Đọc chủ động · câu dài và mạch thông tin"]
RUBRIC = None


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


CHAIN_FRAME = ["Đọc lại đoạn trong bài đọc (mở ở phần câu hỏi, chưa cần làm câu hỏi).",
               "Tô từ khóa của từng câu, bỏ tên riêng, năm và số liệu.",
               "Nối những chữ còn lại bằng mũi tên, rồi nói ý chính của đoạn trong một câu."]
CHAIN_CHECK = ["Mỗi đoạn có một chuỗi, mỗi mắt xích chỉ hai đến bốn chữ.", "Không còn tên riêng, năm, con số trong chuỗi.",
               "Chuỗi đọc lên vẫn kể được câu chuyện của đoạn."]


def finish(sessions: list[dict], bank: dict[str, list[dict]]) -> list[dict]:
    """The order of the day: read actively (A-B, then the learner's C-D), the words, long sentences and the flow
    (then the learner's E and G), and the questions last."""
    mine = next(s for s in sessions if s["title_vi"].startswith("Vận dụng"))
    m1, m2 = mine["check"]
    for w in bank["writing"]:
        if w["id"] in (m1, m2):
            w["framework_vi"] = CHAIN_FRAME
            w["checklist_vi"] = CHAIN_CHECK
            w["instruction_vi"] = w["instruction_vi"].split(" Gõ bằng")[0] + " Gõ bằng bàn phím tiếng Anh. Viết theo ý hiểu của bạn; bài mẫu chỉ để so sau khi viết."
            w["title_vi"] = "Chuỗi từ khóa · Ngày 6"
            w["limits"] = {"min": 10, "max": 70}
            w["model_note_vi"] = "Chuỗi mẫu chỉ là một cách tóm; chuỗi của bạn khác chữ vẫn đúng nếu giữ được việc chính."
    read1 = {"title_vi": READ_TITLES[0], "lecture": READ_1, "check": [m1],
             "can_do_vi": "Sau buổi này bạn tự rà được một bài đọc, tóm tắt mỗi đoạn thành chuỗi từ khóa và biết cách chọn tiêu đề tóm được cả đoạn.",
             "use_vi": "Hiểu từng đoạn trước rồi mới làm câu hỏi: dò từ khóa khi chưa hiểu bài chỉ là đoán."}
    read2 = {"title_vi": READ_TITLES[1], "lecture": READ_2, "check": [m2],
             "can_do_vi": "Sau buổi này bạn đọc được câu dài bằng cách nối chủ ngữ chính với động từ chính, đọc cụm danh từ từ danh từ chính và theo được mạch thông tin.",
             "use_vi": "Câu dài nhiều phần chèn là chỗ người đọc hay mất dấu; hiểu được khung câu thì câu hỏi nào cũng dễ hơn."}
    vocab = [s for s in sessions if s.get("lecture") in LECTURES]
    rest = [s for s in sessions if s is not mine and s not in vocab]
    for s in rest:
        if s["title_vi"].startswith("Đọc chậm"):
            s["can_do_vi"] = "Sau buổi này bạn trả lời được câu hỏi bằng việc hiểu bài, và giải thích được vì sao mỗi đáp án đúng."
    sessions[:] = [read1, *vocab, read2, *rest]
    for s in sessions:
        assert len(s["title_vi"]) <= 70, s["title_vi"]
    return sessions

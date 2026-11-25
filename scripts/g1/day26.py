"""Week 2 · Day 6 (build day 26): slow reading of "The steam car" (Cambridge IELTS 18, Test 3, Reading Passage 2,
questions 14-26; passage pp. 66-67, questions pp. 68-69, key p. 124).

The reading method of session 4 of the course (stages 4-6), taught on this passage as docs/WEEK2_PLAN.md (day 6) asks:
the four-step self-check (re-read in seven minutes; list the new words, the sentences not understood, the paragraphs not
understood), each paragraph summed up before any question (a heading is the best summary of the WHOLE paragraph), jargon
the writer explains or that can be skipped (boilers, hand-crank starters, pistons, kerosene), adjectives skipped by their
endings, the long noun phrase read from its head noun, reduced clauses and the appositive, the flow of information from
one paragraph to the next, the time line and its tenses; understand everything first, then answer without tricks.
Questions 14-23 are choices; the heading list has eight entries, so each paragraph offers five of them (the book's
numerals kept) and heading ii is left out of paragraph G, where "never a financial success" could be misread as it.
Questions 24-26 (one word and/or a number from the passage) are typed and carry the book's key.
"""
from __future__ import annotations

C18 = "Cambridge IELTS 18, Test 3"

TITLE = "The steam car"
SUBTITLE = "The successes and failures of the Doble brothers and their steam cars"
PARAS = {
    "A": ("When primitive automobiles first began to appear in the 1800s, their engines were based on steam power. Steam had already "
          "enjoyed a long and successful career in the railways, so it was only natural that the technology evolved into a miniaturized "
          "version which was separate from the trains. But these early cars inherited steam's weaknesses along with its strengths. The "
          "boilers had to be lit by hand, and they required about twenty minutes to build up pressure before they could be driven. "
          "Furthermore, their water reservoirs only lasted for about thirty miles before needing replenishment. Despite such shortcomings, "
          "these newly designed self-propelled carriages offered quick transportation, and by the early 1900s it was not uncommon to see "
          "such machines shuttling wealthy citizens around town."),
    "B": ("But the glory days of steam cars were few. A new technology called the Internal Combustion Engine soon appeared, which offered "
          "the ability to drive down the road just moments after starting up. At first, these noisy gasoline cars were unpopular because "
          "they were more complicated to operate and they had difficult hand-crank starters, which were known to break arms when the "
          "engines backfired. But in 1912 General Motors introduced the electric starter, and over the following few years steam power "
          "was gradually phased out."),
    "C": ("Even as the market was declining, four brothers made one last effort to rekindle the technology. Between 1906 and 1909, while "
          "still attending high school, Abner Doble and his three brothers built their first steam car in their parents' basement. It "
          "comprised parts taken from a wrecked early steam car but reconfigured to drive an engine of their own design. Though it did not "
          "run well, the Doble brothers went on to build a second and third prototype in the following years. Though the Doble boys' third "
          "prototype, nicknamed the Model B, still lacked the convenience of an internal combustion engine, it drew the attention of "
          "automobile trade magazines due to its numerous improvements over previous steam cars. The Model B proved to be superior to "
          "gasoline automobiles in many ways. Its high-pressure steam drove the engine pistons in virtual silence, in contrast to clattering "
          "gas engines which emitted the aroma of burned hydrocarbons. Perhaps most impressively, the Model B was amazingly swift. It could "
          "accelerate from zero to sixty miles per hour in just fifteen seconds, a feat described as 'remarkable acceleration' by "
          "Automobile magazine in 1914."),
    "D": ("The following year Abner Doble drove the Model B from Massachusetts to Detroit in order to seek investment in his automobile "
          "design, which he used to open the General Engineering Company. He and his brothers immediately began working on the Model C, "
          "which was intended to expand upon the innovations of the Model B. The brothers added features such as a key-based ignition in "
          "the cabin, eliminating the need for the operator to manually ignite the boiler. With these enhancements, the Dobles' new car "
          "company promised a steam vehicle which would provide all of the convenience of a gasoline car, but with much greater speed, much "
          "simpler driving controls, and a virtually silent powerplant. By the following April, the General Engineering Company had "
          "received 5,390 deposits for Doble Detroits, which were scheduled for delivery in early 1918."),
    "E": ("Later that year Abner Doble delivered unhappy news to those eagerly awaiting the delivery of their modern new cars. Those buyers "
          "who received the handful of completed cars complained that the vehicles were sluggish and erratic, sometimes going in reverse "
          "when they should go forward. The new engine design, though innovative, was still plagued with serious glitches."),
    "F": ("The brothers made one final attempt to produce a viable steam automobile. In early 1924, the Doble brothers shipped a Model E to "
          "New York City to be road-tested by the Automobile Club of America. After sitting overnight in freezing temperatures, the car was "
          "pushed out into the road and left to sit for over an hour in the frosty morning air. At the turn of the key, the boiler lit and "
          "reached its operating pressure inside of forty seconds. As they drove the test vehicle further, they found that its evenly "
          "distributed weight lent it surprisingly good handling, even though it was so heavy. As the new Doble steamer was further "
          "developed and tested, its maximum speed was pushed to over a hundred miles per hour, and it achieved about fifteen miles per "
          "gallon of kerosene with negligible emissions."),
    "G": ("Sadly, the Dobles' brilliant steam car never was a financial success. Priced at around $18,000 in 1924, it was popular only "
          "among the very wealthy. Plus, it is said that no two Model Es were quite the same, because Abner Doble tinkered endlessly with "
          "the design. By the time the company folded in 1931, fewer than fifty of the amazing Model E steam cars had been produced. For "
          "his whole career, until his death in 1961, Abner Doble remained adamant that steam-powered automobiles were at least equal to "
          "gasoline cars, if not superior. Given the evidence, he may have been right. Many of the Model E Dobles which have survived are "
          "still in good working condition, some having been driven over half a million miles with only normal maintenance. "
          "Astonishingly, an unmodified Doble Model E runs clean enough to pass the emissions laws in California today, and they are "
          "pretty strict. It is true that the technology poses some difficult problems, but you cannot help but wonder how efficient a "
          "steam car might be with the benefit of modern materials and computers. Under the current pressure to improve automotive "
          "performance and reduce emissions, it is not unthinkable that the steam car may rise again."),
}
TEXT = f"{TITLE}\n{SUBTITLE}\n" + "\n".join(f"{k}  {v}" for k, v in PARAS.items())

HEADINGS = {
    "i": "A period in cold conditions before the technology is assessed",
    "ii": "Marketing issues lead to failure",
    "iii": "Good and bad aspects of steam technology are passed on",
    "iv": "A possible solution to the issues of today",
    "v": "Further improvements lead to commercial orders",
    "vi": "Positive publicity at last for this quiet, clean, fast vehicle",
    "vii": "A disappointing outcome for customers",
    "viii": "A better option than the steam car arises",
}
ORDER = list(HEADINGS)


def head(n: int, para: str, right: str, others: list[str], why: str):
    """One paragraph, five headings of the list in the book's order; the right one is the book's key."""
    picks = [h for h in ORDER if h == right or h in others]
    assert right in picks and len(picks) == 5, (n, picks)
    label = {h: f"{h}. {HEADINGS[h]}" for h in picks}
    return (f"Câu {n}. Paragraph {para}", [label[right]] + [label[h] for h in picks if h != right], why, [label[h] for h in picks])


def abcd(prompt: str, letter: str, opts: list[str], why: str):
    right = opts[ord(letter) - 65]
    return (prompt, [right] + [t for t in opts if t != right], why, list(opts))


HEAD_QS = [
    head(14, "A", "iii", ["ii", "v", "vi", "viii"],
         "Tóm tắt đoạn A: hơi nước đã thành công ở đường sắt → được thu nhỏ thành ô tô → xe thừa hưởng cả điểm yếu lẫn điểm mạnh "
         "(`inherited steam's weaknesses along with its strengths`). Phần còn lại kể ra từng mặt: nhóm lửa bằng tay, chờ hai mươi phút, "
         "nước chỉ đủ ba mươi dặm; nhưng đi nhanh. Tiêu đề tóm được cả đoạn là iii (`passed on` = `inherited`). viii nói về đoạn B, "
         "v về đoạn D, vi về đoạn C; ii không khớp đoạn nào."),
    head(15, "B", "viii", ["i", "ii", "iii", "vii"],
         "Tóm tắt đoạn B: thời hoàng kim ngắn → động cơ đốt trong xuất hiện → lúc đầu bị chê → có bộ khởi động điện (1912) → xe hơi nước "
         "dần bị loại bỏ (`phased out`). Ý chính là một công nghệ tốt hơn xuất hiện: viii. iii sai vì đoạn không nói hơi nước truyền lại "
         "điều gì; vii nói về khách mua xe ở đoạn E; i và ii không có trong đoạn."),
    head(16, "C", "vi", ["iii", "v", "vii", "viii"],
         "Tóm tắt đoạn C: bốn anh em muốn hồi sinh công nghệ → mẫu đầu chạy không tốt → mẫu thứ ba được tạp chí chú ý → êm (`virtual "
         "silence`), sạch (không như máy xăng thải mùi khói), nhanh (`remarkable acceleration`). Sau mấy lần thử mới được khen, nên "
         "tiêu đề là vi (`at last`, `quiet, clean, fast`). v sai: đơn đặt hàng chỉ có ở đoạn D; iii và viii nói về đoạn A, B."),
    head(17, "D", "v", ["ii", "iv", "vi", "vii"],
         "Tóm tắt đoạn D: tìm vốn → mở công ty → mẫu xe mới mở rộng các cải tiến (khóa điện trong cabin) → 5.390 khoản đặt cọc. Cải tiến "
         "thêm dẫn tới đơn đặt hàng: v (`further improvements` = `enhancements`, `commercial orders` = `deposits`). vi sai vì đoạn D "
         "không nhắc báo chí; vii là chuyện xảy ra sau đó, ở đoạn E."),
    head(18, "E", "vii", ["ii", "iii", "v", "viii"],
         "Tóm tắt đoạn E: tin không vui → người mua phàn nàn xe ì, thất thường, có lúc chạy lùi → động cơ còn nhiều lỗi. Kết cục làm "
         "khách hàng thất vọng: vii. ii sai vì vấn đề nằm ở động cơ (`glitches`), không phải ở việc tiếp thị; v là đoạn D, ngay trước đó."),
    head(19, "F", "i", ["iv", "v", "vi", "vii"],
         "Tóm tắt đoạn F: mẫu xe cuối được thử ở New York → để qua đêm trong giá lạnh, rồi thêm một giờ ngoài trời → vặn khóa, nồi hơi "
         "đủ áp suất trong bốn mươi giây → lái dễ, nhanh, khí thải không đáng kể. Phần dài nhất và đặc biệt nhất là quãng chờ trong "
         "giá lạnh trước khi xe được thử: i (`assessed` = `road-tested`). vi hấp dẫn vì kết quả tốt, nhưng đoạn F không nhắc báo chí "
         "hay công chúng, và tiêu đề có `at last` hợp với đoạn C."),
    head(20, "G", "iv", ["i", "iii", "vii", "viii"],
         "Tóm tắt đoạn G: thất bại về tài chính → công ty đóng cửa năm 1931 → xe còn lại vẫn chạy tốt, đủ sạch cho luật khí thải ngày "
         "nay → xe hơi nước có thể trở lại. Câu kết hướng về hôm nay: áp lực giảm khí thải, và xe hơi nước có thể là một lời giải: iv. "
         "Tiêu đề tóm cả đoạn, không chỉ câu đầu; các tiêu đề còn lại nói về những đoạn khác."),
]

MC = ["Câu 21. What point does the writer make about the steam car in Paragraph B?",
      "Câu 22. When building their first steam car, the Doble brothers",
      "Câu 23. In order to produce the Model C, the Doble brothers"]
MC_QS = [
    abcd(MC[0], "A", ["Its success was short-lived.", "Not enough cars were made.", "Car companies found them hard to sell.", "People found them hard to drive."],
         "Câu đầu đoạn B: `the glory days of steam cars were few`, thời hoàng kim chỉ có vài năm, tức thành công ngắn ngủi. Đoạn B không "
         "nói xe làm ra ít hay khó bán. Xe khó vận hành là xe chạy xăng (`more complicated to operate`), không phải xe hơi nước."),
    abcd(MC[1], "C", ["constructed all the parts themselves.", "made written notes at each stage of the construction.",
                      "needed several attempts to achieve a competitive model.", "sought the advice of experienced people in the car industry."],
         "Đoạn C: chiếc đầu tiên chạy không tốt, rồi làm tiếp mẫu thứ hai và thứ ba; đến mẫu thứ ba mới được chú ý nhờ nhiều cải tiến. "
         "Phải thử nhiều lần mới có một mẫu đáng kể. A sai vì chiếc đầu dùng phụ tùng lấy từ một chiếc xe hơi nước cũ bị hỏng (`parts taken "
         "from a wrecked early steam car`). B và D không có trong bài."),
    abcd(MC[2], "B", ["moved production to a different city.", "raised financial capital.", "employed an additional worker.", "abandoned their earlier designs."],
         "Đoạn D: lái xe tới Detroit để tìm vốn (`seek investment`), dùng vốn đó mở công ty, rồi bắt tay làm mẫu xe mới: B. A không có "
         "trong bài: đi Detroit là để tìm vốn, bài không nói chuyển nơi sản xuất (đáp án bài thi là B). C không có trong bài. D sai vì mẫu "
         "mới mở rộng chính các cải tiến của mẫu cũ (`expand upon the innovations`), không bỏ thiết kế cũ."),
]

SECTIONS: list[tuple] = [
    (26, "W6S", C18 + " · câu 24–26", "Tóm tắt: The Model E",
     "Điền MỘT từ và/hoặc một số lấy từ bài đọc. Trước khi gõ, tìm đoạn kể về chiếc xe được nhắc trong câu, rồi đọc kỹ câu chứa từ cần điền.", "typed", [
        "A later version of the Model E raised its ( ㉠ ), while keeping its emissions extremely low. | speed;Speed | Đoạn F: `its maximum speed "
        "was pushed to over a hundred miles per hour … with negligible emissions`. `pushed to` = `raised`, `negligible` = `extremely low`. "
        "Đề cho phép một từ: `speed`.",
        "Under ( ㉠ ) cars were produced before the company went out of business. | fifty;50;Fifty | Đoạn G: `By the time the company folded "
        "in 1931, fewer than fifty … had been produced`. `fewer than` = `under`, `folded` = `went out of business`. Gõ bằng chữ hay bằng số đều đúng.",
        "Even today, Model Es on the road satisfy California's ( ㉠ ) emissions laws. | strict;Strict | Đoạn G: xe vẫn đủ sạch để qua luật "
        "khí thải của California, `and they are pretty strict`. Chỗ trống đứng trước danh từ `emissions laws`, nên cần tính từ: `strict`.",
    ]),
]

DAY = {
    "title": "The steam car", "slug_title": "The steam car", "title_vi": "Đọc chậm: The steam car",
    "goal": "Đọc hiểu trọn bài The steam car trước khi làm câu hỏi: tóm tắt từng đoạn thành chuỗi từ khóa, đọc câu dài từ chủ ngữ và động từ chính, theo trục thời gian và mạch thông tin từ đoạn này sang đoạn khác.",
    "can": ["Tóm tắt được mỗi đoạn thành một chuỗi từ khóa ngắn, rồi chọn tiêu đề tóm được cả đoạn.",
            "Đọc được câu dài: bỏ tạm phần chèn giữa hai dấu phẩy, nối chủ ngữ chính với động từ chính, đọc cụm danh từ từ danh từ chính.",
            "Theo được trục thời gian của bài và hiểu vì sao người viết đổi thì.",
            "Trả lời 13 câu hỏi bằng việc hiểu bài, chưa dùng mẹo."],
    "ielts": "Bài đọc dài khoảng 950 từ với ba dạng câu hỏi hay gặp: chọn tiêu đề đoạn, trắc nghiệm, điền tóm tắt; cả ba đều cần hiểu ý chính của từng đoạn.",
    "source": C18 + ", Reading Passage 2; từ vựng chọn từ bài đọc theo phương pháp của khóa học",
    "family": "Công nghệ: chiếc xe hơi nước",
    "recognize": {"rekindle", "feat", "glitch"},
    "method": ("Cách đọc chậm một bài (làm ở hai buổi Đọc chủ động):\n"
               "• Tự rà: đọc lại cả bài trong 7 phút; ghi từ mới, câu biết từ mà vẫn không hiểu, đoạn gần như không hiểu.\n"
               "• Mỗi đoạn: tô từ khóa, bỏ chi tiết (tên, năm, số liệu), nối thành chuỗi có mũi tên, nói ý chính.\n"
               "• Từ chuyên ngành: người viết thường giải thích ngay sau đó; không thì bỏ qua. Tính từ lạ (đuôi -ic, -al) và trạng từ (-ly) cũng có thể lướt qua.\n"
               "• Câu dài: bỏ tạm phần chèn giữa hai dấu phẩy, nối chủ ngữ chính với động từ chính; cụm danh từ đọc từ danh từ chính.\n"
               "• Hiểu trọn bài rồi mới làm câu hỏi."),
    "editor": ("Bài đọc, câu hỏi và đáp án theo Cambridge IELTS 18, Test 3, Reading Passage 2 (trang 66–69, đáp án trang 124). Phương pháp đọc theo "
               "Buổi 4 của khóa học (chặng 4–6), dạy trên bài này theo docs/WEEK2_PLAN.md. Câu 14–20: mỗi đoạn cho năm trong tám tiêu đề "
               "(giữ số La Mã của sách); đoạn G không cho tiêu đề ii."),
    "book": [("Cambridge IELTS 18", "66–69", "Bài đọc The steam car, câu 14–26 (trong app: chọn tiêu đề, trắc nghiệm, điền tóm tắt)", 13, 20)],
    "sittings": [
        ("Từ của bài · đoạn A đến C", [
            ("inherit", "V", "thừa hưởng (từ đời trước)", "The new phone inherited the old model's weak battery.", "Chiếc điện thoại mới thừa hưởng cục pin yếu của đời máy cũ."),
            ("shortcoming", "N", "điểm yếu, thiếu sót (= weakness)", "Despite its shortcomings, the car was quick.", "Dù có những điểm yếu, chiếc xe vẫn chạy nhanh."),
            ("phase out", "X", "loại bỏ dần, từng bước", "Old diesel buses are being phased out.", "Xe buýt chạy dầu cũ đang dần bị loại bỏ."),
            ("rekindle", "V", "khơi lại, nhóm lại (= revive)", "The film rekindled my interest in history.", "Bộ phim khơi lại niềm yêu thích lịch sử của tôi."),
            ("prototype", "N", "mẫu thử đầu tiên", "The team built a second prototype.", "Nhóm đã chế tạo mẫu thử thứ hai."),
            ("comprise", "V", "gồm có (= consist of)", "The team comprises four brothers.", "Nhóm gồm bốn anh em."),
            ("feat", "N", "kỳ công, thành tích khó", "Winning the race alone was an amazing feat.", "Một mình thắng cuộc đua là một kỳ công."),
            ("accelerate", "V", "tăng tốc (= speed up)", "The car can accelerate quickly.", "Chiếc xe có thể tăng tốc rất nhanh."),
        ]),
        ("Từ của bài · đoạn D đến G", [
            ("investment", "N", "vốn đầu tư, sự đầu tư", "He went to Detroit to seek investment.", "Ông tới Detroit để tìm vốn đầu tư."),
            ("enhancement", "N", "sự cải tiến, nâng cấp (= improvement)", "The new version has several enhancements.", "Phiên bản mới có vài cải tiến."),
            ("deposit", "N", "tiền đặt cọc", "We paid a deposit for the new car.", "Chúng tôi đã đặt cọc cho chiếc xe mới."),
            ("glitch", "N", "trục trặc nhỏ, lỗi (= fault)", "A small glitch stopped the game.", "Một trục trặc nhỏ làm trò chơi dừng lại."),
            ("viable", "A", "khả thi, dùng được trên thực tế", "Is electric power a viable option for long trips?", "Điện có phải lựa chọn khả thi cho những chuyến đi dài không?"),
            ("emission", "N", "khí thải, sự thải ra", "Cars must reduce their emissions.", "Ô tô phải giảm khí thải."),
            ("fold", "V", "(công ty) đóng cửa, phá sản", "The company folded in 1931.", "Công ty phá sản năm 1931."),
            ("maintenance", "N", "sự bảo dưỡng", "The car needs only normal maintenance.", "Chiếc xe chỉ cần bảo dưỡng bình thường."),
        ]),
    ],
    "passages": [
        {"id": "P1", "title": "Câu 14–20 · tiêu đề của đoạn",
         "instr": ("Chọn tiêu đề đúng cho mỗi đoạn. Danh sách có tám tiêu đề (i–viii), mỗi câu cho năm tiêu đề; mỗi tiêu đề dùng nhiều nhất "
                   "một lần, và có một tiêu đề không dùng. Trước khi chọn, nói lại chuỗi từ khóa của đoạn: tiêu đề đúng tóm được cả đoạn, "
                   "không chỉ một câu trong đoạn."),
         "text": TEXT, "qs": HEAD_QS},
        {"id": "P2", "title": "Câu 21–23 · chọn đáp án",
         "instr": "Chọn đáp án đúng. Mỗi câu hỏi chỉ về một đoạn: tìm đoạn đó, đọc lại chuỗi từ khóa của nó, rồi mới đọc các phương án.",
         "text": TEXT, "qs": MC_QS},
    ],
    "my": [
        {"vi": "Đọc lại đoạn C và D. Với mỗi đoạn, viết một chuỗi từ khóa nối bằng mũi tên: bỏ tên riêng, năm và số liệu, chỉ giữ việc chính.",
         "en": "Write one keyword chain for paragraph C and one for paragraph D, using arrows.",
         "model": "C: last effort -> first car ran badly -> more prototypes -> magazines noticed -> quiet, clean, fast. D: seek investment -> open company -> new features -> thousands of deposits."},
        {"vi": "Viết chuỗi từ khóa cho đoạn E và G, rồi một câu tóm tắt cả bài (không quá 25 từ).",
         "en": "Write keyword chains for paragraphs E and G, then one sentence that sums up the whole passage.",
         "model": "E: buyers unhappy -> slow, erratic -> glitches. G: no profit -> company closed -> cars still run, clean -> may return. The Doble brothers built excellent steam cars, but the business failed; today the idea may return."},
    ],
}

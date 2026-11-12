"""Days 12 and 13: Week 1 Reading and Listening, both from Cambridge IELTS 18, Test 4 (the growth mindset; origami as a teaching tool).

Same keys as day89.DAYS. A question tuple may carry a last element: the exact option order (letters A to E, A to G), used when the
exam shows lettered options. Day 12 has the six-step paragraph method of the course as an extra note (`method`).
"""
C18 = "Cambridge IELTS 18, Test 4"

GROWTH = 'The growth mindset\nOver the past century, a powerful idea has taken root in the educational landscape. The concept of intelligence as something innate has been supplanted by the idea that intelligence is not fixed, and that, with the right training, we can be the authors of our own cognitive capabilities. Psychologist Alfred Binet, the developer of the first intelligence tests, was one of many 19th-century scientists who held that earlier view and sought to quantify cognitive ability. Then, in the early 20th century, progressive thinkers revolted against the notion that inherent ability is destiny. Instead, educators such as John Dewey argued that every child’s intelligence could be developed, given the right environment.\n‘Growth mindset theory’ is a relatively new — and extremely popular — version of this idea. In many schools today you will see hallways covered in motivational posters and hear speeches on the mindset of great sporting heroes who simply believed their way to the top. A major focus of the growth mindset in schools is coaxing students away from seeing failure as an indication of their ability, and towards seeing it as a chance to improve that ability. As educationalist Jeff Howard noted several decades ago: ‘Smart is not something that you just are, smart is something that you can get.’\nThe idea of the growth mindset is based on the work of psychologist Carol Dweck in California in the 1990s. In one key experiment, Dweck divided a group of 10- to 12-year-olds into two groups. All were told that they had achieved a high score on a test but the first group were praised for their intelligence in achieving this, while the others were praised for their effort. The second group — those who had been instilled with a ‘growth mindset’ — were subsequently far more likely to put effort into future tasks. Meanwhile, the former took on only those tasks that would not risk their sense of worth. This group had inferred that success or failure is due to innate ability, and this ‘fixed mindset’ had led them to fear of failure and lack of effort. Praising ability actually made the students perform worse, while praising effort emphasised that change was possible.\nOne of the greatest impediments to successfully implementing a growth mindset, however, is the education system itself: in many parts of the world, the school climate is obsessed with performance in the form of constant testing, analysing and ranking of students — a key characteristic of the fixed mindset. Nor is it unusual for schools to create a certain cognitive dissonance, when they applaud the benefits of a growth mindset but then hand out fixed target grades in lessons based on performance.\nAside from the implementation problem, the original growth mindset research has also received harsh criticism. The statistician Andrew Gelman claims that ‘their research designs have enough degrees of freedom that they could take their data to support just about any theory at all’. Professor of Psychology Timothy Bates, who has been trying to replicate Dweck’s work, is finding that the results are repeatedly null. He notes that: ‘People with a growth mindset don’t cope any better with failure ... Kids with the growth mindset aren’t getting better grades, either before or after our intervention study.’\nMuch of this criticism is not lost on Dweck, and she deserves great credit for responding to it and adapting her work accordingly. In fact, she argues that her work has been misunderstood and misapplied in a range of ways. She has also expressed concerns that her theories are being misappropriated in schools by being conflated with the self-esteem movement: ‘For me the growth mindset is a tool for learning and improvement. It’s not just a vehicle for making children feel good.’\nBut there is another factor at work here. The failure to translate the growth mindset into the classroom might reflect a misunderstanding of the nature of teaching and learning itself. Growth mindset supporters David Yeager and Gregory Walton claim that interventions should be delivered in a subtle way to maximise their effectiveness. They say that if adolescents perceive a teacher’s intervention as conveying that they are in need of help, this could undo its intended effects.\nA lot of what drives students is their innate beliefs and how they perceive themselves. There is a strong correlation between self-perception and achievement, but there is evidence to suggest that the actual effect of achievement on self-perception is stronger than the other way round. To stand up in a classroom and successfully deliver a good speech is a genuine achievement, and that is likely to be more powerfully motivating than vague notions of ‘motivation’ itself.\nRecent evidence would suggest that growth mindset interventions are not the elixir of student learning that its proponents claim it to be. The growth mindset appears to be a viable construct in the lab, which, when administered in the classroom via targeted interventions, doesn’t seem to work. It is hard to dispute that having faith in the capacity to change is a good attribute for students. Paradoxically, however, that aspiration is not well served by direct interventions that try to instil it.\nMotivational posters and talks are often a waste of time, and might well give students a deluded notion of what success actually means. Teaching concrete skills such as how to write an effective introduction to an essay then praising students’ effort in getting there is probably a far better way of improving confidence than telling them how unique they are, or indeed how capable they are of changing their own brains. Perhaps growth mindset works best as a philosophy and not an intervention.'

def q(prompt, right, wrong, why, order=None):
    return (prompt, [right] + wrong, why, order) if order else (prompt, [right] + wrong, why)

PEOPLE = ["A Alfred Binet", "B Carol Dweck", "C Andrew Gelman", "D Timothy Bates", "E David Yeager and Gregory Walton"]
def who(prompt, letter, why):
    right = next(p for p in PEOPLE if p[0] == letter)
    return q(prompt, right, [p for p in PEOPLE if p != right], why, PEOPLE)

def abcd(prompt, letter, opts, why):
    items = [f"{chr(65 + i)} {t}" for i, t in enumerate(opts)]
    right = items[ord(letter) - 65]
    return q(prompt, right, [t for t in items if t != right], why, items)

LSK = ["solving problems", "following instructions", "working cooperatively", "learning through play", "developing hand-eye coordination"]
LCM = ["demonstrated independence", "asked for teacher support", "developed a competitive attitude", "seemed to find the activity calming", "seemed pleased with the results", "seemed confused", "seemed to find the activity easy"]
LABC28 = ["make models that demonstrate the different stages.", "check children understand the terminology involved.", "tell children not to worry if they find the activity difficult."]
LABC29 = ["they may not think that crafts are important.", "they may not have the necessary skills.", "they may worry that it will take up too much time."]
LABC30 = ["to correct a particular misunderstanding", "to set a challenge", "to introduce a new concept"]

def lq(prompt, letter, wrong_letters, texts, why):
    """Listening question: lettered options, shown in book order; the shown set is `letter` plus `wrong_letters`."""
    letters = sorted(letter + wrong_letters)
    items = {l: f"{l} {texts[ord(l) - 65]}" for l in letters}
    return (prompt, items[letter], [items[l] for l in letters if l != letter], why, [items[l] for l in letters])

def yn(prompt, answer, why):
    return q(prompt, answer, [t for t in ("YES", "NO", "NOT GIVEN") if t != answer], why, ["YES", "NO", "NOT GIVEN"])

METHOD = ("Sáu bước đọc từng đoạn (làm cho đoạn 1 đến 3 ở phần Vận dụng):\n"
          "• Bước 1: gạch từ khóa của từng câu (danh từ trước, động từ sau).\n"
          "• Bước 2: bỏ phần quá chi tiết như tên riêng, địa điểm, thời gian.\n"
          "• Bước 3: nối các từ khóa với nhau.\n"
          "• Bước 4: viết một câu tóm tắt dạng chuỗi từ khóa, nối bằng mũi tên.\n"
          "• Bước 5: hỏi đoạn này nói về ý chính nào.\n"
          "• Bước 6: nêu giá trị của đoạn: đoạn này giúp người đọc hiểu điều gì.")

DAYS = {}
DAYS[12] = {
    "title": "The growth mindset: Cambridge IELTS 18, Test 4, Passage 2", "title_vi": "Đọc chậm: The growth mindset (Cambridge 18)",
    "goal": "Đọc chậm một bài về niềm tin vào khả năng học và phát triển, dùng sáu bước tóm tắt từng đoạn, rồi làm 13 câu (chọn đáp án, ghép người với nhận định, đồng ý hay không) và nói rõ đáp án nằm ở đâu.",
    "ielts": "Bài đọc nối hai chủ đề của tuần: Thinking (suy nghĩ, niềm tin) và Learning (học tập). Từ mới của tuần xuất hiện lại ngay trong bài và trong câu hỏi, nên bạn gặp chúng trong ngữ cảnh thật của đề thi.",
    "source": "Cambridge IELTS 18, Test 4, Passage 2; từ vựng theo giáo án của khóa học", "family": "Tư duy và học tập",
    "recognize": {"impediment", "correlation", "deluded", "intervention", "aspiration"},
    "method": METHOD,
    "editor": "Bài đọc và đáp án theo Cambridge IELTS 18, Test 4, Reading Passage 2 (trang 88–91, đáp án trang 125). Bài thay cho Urban farming, nay chuyển sang phần bổ trợ.",
    "book": [("Cambridge IELTS 18", "88–91", "Test 4, Reading Passage 2 (13 câu, câu 14–26)", 13, 20)],
    "sittings": [
        ("Từ về học tập và kết quả", [
            ("ability", "N", "khả năng", "Praising ability made the students perform worse.", "Khen khả năng làm học sinh làm bài tệ hơn."),
            ("effort", "N", "sự nỗ lực", "The second group put more effort into the next task.", "Nhóm thứ hai bỏ nhiều nỗ lực hơn vào bài tiếp theo."),
            ("praise", "V", "khen", "The teacher praised them for their effort.", "Giáo viên khen họ vì đã nỗ lực."),
            ("failure", "N", "sự thất bại", "Some students see failure as a chance to improve.", "Một số học sinh xem thất bại là cơ hội để tiến bộ."),
            ("achievement", "N", "thành tích, điều đạt được", "A good speech is a real achievement.", "Một bài nói hay là một thành tích thật sự."),
            ("evidence", "N", "bằng chứng", "There is evidence that the method does not work.", "Có bằng chứng cho thấy phương pháp này không hiệu quả."),
            ("criticism", "N", "lời chỉ trích, phê bình", "The research has received harsh criticism.", "Nghiên cứu này nhận nhiều chỉ trích gay gắt."),
            ("experiment", "N", "thí nghiệm", "In one key experiment, children were divided into two groups.", "Trong một thí nghiệm chính, trẻ được chia thành hai nhóm."),
        ]),
        ("Từ về niềm tin và bản chất", [
            ("notion", "N", "quan niệm, ý niệm", "The notion that talent is fixed is out of date.", "Quan niệm rằng tài năng là cố định đã lỗi thời."),
            ("innate", "A", "bẩm sinh, vốn có từ khi sinh ra", "Some people believe intelligence is innate.", "Một số người tin trí thông minh là bẩm sinh."),
            ("destiny", "N", "số phận, điều đã định sẵn", "Ability is not destiny.", "Khả năng không phải số phận."),
            ("infer", "V", "suy ra", "The group inferred that success depends on ability.", "Nhóm đó suy ra rằng thành công phụ thuộc vào khả năng."),
            ("perceive", "V", "nhìn nhận, cảm nhận", "Students perceive a teacher's help as a sign of weakness.", "Học sinh nhìn sự giúp đỡ của giáo viên như dấu hiệu của sự yếu kém."),
            ("deluded", "A", "ảo tưởng, tin điều không đúng", "Posters can give students a deluded idea of success.", "Áp phích có thể cho học sinh một ý niệm ảo tưởng về thành công."),
        ]),
        ("Từ để phân tích và phản biện", [
            ("impediment", "N", "trở ngại", "The school system is an impediment to change.", "Hệ thống trường học là trở ngại cho sự thay đổi."),
            ("intervention", "N", "biện pháp can thiệp", "The intervention did not improve grades.", "Biện pháp can thiệp không cải thiện điểm số."),
            ("correlation", "N", "mối tương quan", "There is a strong correlation between the two.", "Có mối tương quan chặt giữa hai điều này."),
            ("dispute", "V", "tranh cãi, phản bác", "It is hard to dispute that faith in change helps.", "Khó phản bác việc tin vào khả năng thay đổi là có ích."),
            ("aspiration", "N", "khát vọng", "Her aspiration is to study abroad.", "Khát vọng của cô ấy là đi du học."),
            ("subtle", "A", "tinh tế, kín đáo", "The message should be delivered in a subtle way.", "Thông điệp nên được truyền đạt một cách kín đáo."),
        ]),
        ("Cụm và từ nối cần nhận ra", [
            ("paradoxically", "X", "nghịch lý là (điều xảy ra trái với mong đợi)", "Paradoxically, direct teaching of the mindset does not work well.", "Nghịch lý là việc dạy trực tiếp tư duy này lại không hiệu quả."),
            ("concentrate on", "X", "tập trung vào", "Schools ask students to concentrate on their strengths.", "Trường học yêu cầu học sinh tập trung vào điểm mạnh."),
            ("intellectual", "A", "thuộc trí tuệ", "Intellectual ability can be developed.", "Năng lực trí tuệ có thể được phát triển."),
            ("deliberate", "A", "có chủ ý", "A deliberate attempt to motivate students may backfire.", "Nỗ lực có chủ ý để thúc đẩy học sinh có thể phản tác dụng."),
            ("have faith in", "X", "tin tưởng vào", "It helps to have faith in your capacity to change.", "Tin vào khả năng thay đổi của mình là điều có ích."),
        ]),
    ],
    "passages": [
        {"id": "P1", "title": "The growth mindset: câu 14–16 (chọn đáp án)", "instr": "Làm theo sáu bước ở ghi chú: gạch từ khóa, nối thành chuỗi, rồi mới đọc các lựa chọn. Mỗi câu hỏi về một đoạn cụ thể (đoạn 1, 2, 3).", "text": GROWTH, "qs": [
            abcd("Câu 14. What can we learn from the first paragraph?", "B", ["where the notion of innate intelligence first began", "when ideas about the nature of intelligence began to shift", "how scientists have responded to changing views of intelligence", "why thinkers turned away from the idea of intelligence being fixed"],
                 "Đoạn 1 mô tả mốc chuyển: quan niệm trí thông minh là bẩm sinh bị thay bằng quan niệm không cố định; `Then, in the early 20th century … revolted`. Đó là lúc ý tưởng bắt đầu đổi. Phương án A sai vì bài không nói quan niệm bẩm sinh bắt đầu ở đâu; D sai vì bài nói ai phản đối, không giải thích vì sao."),
            abcd("Câu 15. The second paragraph describes how schools encourage students to", "C", ["identify their personal ambitions.", "help each other to realise their goals.", "have confidence in their potential to succeed.", "concentrate on where their particular strengths lie."],
                 "Đoạn 2: nhà trường khuyến khích học sinh xem thất bại là cơ hội cải thiện khả năng (`coaxing students away from seeing failure as an indication of their ability`) và tin mình có thể tiến bộ. Đó là tin vào tiềm năng của mình. `Concentrate on` là cụm trong Unit 2, nhưng ở đây là bẫy: bài không nói về điểm mạnh."),
            abcd("Câu 16. In the third paragraph, the writer suggests that students with a fixed mindset", "D", ["tend to be less competitive.", "generally have a low sense of self-esteem.", "will only work hard if they are given constant encouragement.", "are afraid to push themselves beyond what they see as their limitations."],
                 "Đoạn 3: nhóm tư duy cố định chỉ nhận việc không đe dọa giá trị bản thân (`took on only those tasks that would not risk their sense of worth`) và có `fear of failure`. Tức là sợ vượt qua giới hạn mà mình nghĩ là có."),
        ]},
        {"id": "P2", "title": "The growth mindset: câu 17–22 (ghép nhận định với người)", "instr": "Danh sách người: A Binet, B Dweck, C Gelman, D Bates, E Yeager và Walton. Mỗi nhận định ứng với một người; một người có thể được chọn nhiều lần. Tìm tên người trong bài trước, rồi đọc câu có tên đó.", "text": GROWTH, "qs": [
            who("Câu 17. The methodology behind the growth mindset studies was not strict enough.", "C", "Đoạn 5: Gelman nói thiết kế nghiên cứu có `enough degrees of freedom` để dữ liệu ủng hộ bất kỳ lý thuyết nào. Nghĩa là phương pháp chưa đủ chặt."),
            who("Câu 18. The idea of the growth mindset has been incorrectly interpreted.", "B", "Đoạn 6: Dweck cho rằng công trình của bà `has been misunderstood and misapplied`. `Incorrectly interpreted` là cách đổi từ của `misunderstood`."),
            who("Câu 19. Intellectual ability is an unchangeable feature of each individual.", "A", "Đoạn 1: Binet thuộc những nhà khoa học thế kỷ 19 tin vào quan niệm trí thông minh bẩm sinh, nên coi năng lực trí tuệ là cố định."),
            who("Câu 20. The growth mindset should be promoted without students being aware of it.", "E", "Đoạn 7: Yeager và Walton cho rằng can thiệp nên được đưa ra `in a subtle way`. `Subtle` ≈ không để học sinh nhận ra."),
            who("Câu 21. The growth mindset is not simply about boosting students' morale.", "B", "Đoạn 6: Dweck nói tư duy phát triển `not just a vehicle for making children feel good`. `Boosting morale` = làm trẻ thấy vui."),
            who("Câu 22. Research shows that the growth mindset has no effect on academic achievement.", "D", "Đoạn 5: Bates tìm thấy kết quả `repeatedly null` và `aren't getting better grades`. Không có tác động lên điểm số."),
        ]},
        {"id": "P3", "title": "The growth mindset: câu 23–26 (YES / NO / NOT GIVEN)", "instr": "YES khi bài đồng ý với quan điểm của tác giả; NO khi bài trái với quan điểm đó; NOT GIVEN khi bài không cho biết. Đây là quan điểm của tác giả, không phải của người được nhắc tên.", "text": GROWTH, "qs": [
            yn("Câu 23. Dweck has handled criticisms of her work in an admirable way.", "YES", "Đoạn 6: tác giả viết rằng bà `deserves great credit for responding to it and adapting her work`. `Admirable` ≈ đáng khen."),
            yn("Câu 24. Students' self-perception is a more effective driver of self-confidence than actual achievement is.", "NO", "Đoạn 8: tác động của thành tích lên cách tự nhìn mình mạnh hơn chiều ngược lại (`the actual effect of achievement on self-perception is stronger`). Câu hỏi nói ngược."),
            yn("Câu 25. Recent evidence about growth mindset interventions has attracted unfair coverage in the media.", "NOT GIVEN", "Bài bàn về bằng chứng gần đây nhưng không nhắc truyền thông đưa tin thế nào, càng không nói là không công bằng."),
            yn("Câu 26. Deliberate attempts to encourage students to strive for high achievement may have a negative effect.", "YES", "Đoạn 9: `Paradoxically … that aspiration is not well served by direct interventions that try to instil it`. Cố ý thúc đẩy trực tiếp có thể phản tác dụng."),
        ]},
    ],
    "my": [
        {"vi": "Làm bước 4 của phương pháp cho đoạn 1, 2 và 3: mỗi đoạn viết một chuỗi từ khóa nối bằng mũi tên, rồi nối ba chuỗi bằng một câu. Ví dụ mẫu của khóa học: fantasy -> creativity -> repercussions -> adult life.",
         "en": "Write one keyword chain for each of paragraphs 1, 2 and 3, using arrows.",
         "model": "Para 1: innate intelligence -> early 20th-century thinkers -> intelligence can be developed. Para 2: growth mindset -> failure as chance -> improve ability. Para 3: Dweck's experiment -> effort praised -> more effort."},
    ],
}

DAYS[13] = {
    "title": "Origami as an educational tool: Cambridge IELTS 18, Test 4, Listening Part 3", "title_vi": "Nghe kỹ: origami trong lớp học (Cambridge 18)",
    "goal": "Nghe kỹ một cuộc thảo luận của hai sinh viên sư phạm (Part 3): nghe được ý kiến của từng người, phân biệt điều thấy trên video với điều suy đoán, và chọn đúng đáp án khi các lựa chọn đều được nhắc tới.",
    "ielts": "Part 3 có hai người nói và nhiều lựa chọn gần nghĩa nhau. Quy tắc: đọc trước câu hỏi, nghe ai đang nói và nghe đến lúc chốt ý, vì người nói thường đổi ý giữa chừng.",
    "source": "Cambridge IELTS 18, Test 4, Listening Part 3; từ vựng theo giáo án của khóa học", "family": "Lớp học",
    "recognize": {"disruptive", "symmetry"},
    "editor": "Bài nghe theo Cambridge IELTS 18, Test 4, Part 3 (đề trang 81–82, script trang 116–117, đáp án trang 125). Lời thoại lấy từ script in trong sách, bỏ hai câu hướng dẫn của giảng viên; app đọc lại bằng giọng tổng hợp. Bài thay cho khảo sát giao thông, nay chuyển sang phần bổ trợ.",
    "book": [("Cambridge IELTS 18", "81–82", "Test 4, Listening Part 3 (10 câu, câu 21–30)", 10, 15)],
    "sittings": [
        ("Từ để nghe trước", [
            ("concentrate", "V", "tập trung", "Folding paper helped him concentrate.", "Gấp giấy giúp cậu ấy tập trung."),
            ("disruptive", "A", "gây rối, làm gián đoạn", "He was quite disruptive before the lesson.", "Cậu ấy khá gây rối trước giờ học."),
            ("work out", "X", "tìm ra cách, tự giải ra", "Children can work out how to make a bird.", "Trẻ có thể tự tìm ra cách gấp con chim."),
            ("come across", "X", "tình cờ gặp lần đầu", "It was the first time she had come across origami.", "Đó là lần đầu cô bé gặp origami."),
            ("be supposed to", "X", "được cho là phải (làm gì)", "She was unsure what she was supposed to do.", "Cô bé không chắc mình phải làm gì."),
            ("clumsy", "A", "vụng về", "Many teachers are clumsy with their hands.", "Nhiều giáo viên vụng về với đôi tay."),
            ("reinforce", "V", "củng cố", "Origami can reinforce knowledge of shapes.", "Origami có thể củng cố kiến thức về hình."),
            ("symmetry", "N", "tính đối xứng", "Origami is good practice for symmetry.", "Origami là cách luyện tập tốt về tính đối xứng."),
        ]),
    ],
    "listening": [{"id": "L1", "title": "Origami as an educational tool (Part 3, câu 21–30)", "instr": "Hai sinh viên bàn về một bài học trên video, trong đó trẻ gấp con chim bằng giấy. Đọc câu hỏi trước, nghe lại bao nhiêu lần cũng được. Câu 21 và 22 là hai đáp án khác nhau của cùng một câu hỏi, thứ tự nào cũng được. Âm thanh do app đọc lại script của sách.", "turns": [
        ["M", "I had no idea that such a simple thing like folding squares of paper to make the shape of a bird could be such an amazing tool. It's made me see origami in a whole new light.", "Tôi không ngờ việc gấp giấy vuông thành hình con chim lại là một công cụ tuyệt vời như vậy. Nó khiến tôi nhìn origami hoàn toàn khác."],
        ["F", "I know. It was interesting to see the educational skills the children were developing by doing origami. On the video you could see them really listening hard to make sure they did all the steps in the right order to make the bird.", "Đúng vậy. Thật thú vị khi thấy những kỹ năng giáo dục trẻ phát triển nhờ origami. Trên video, các em lắng nghe rất kỹ để làm đủ các bước đúng thứ tự."],
        ["M", "That's right. In this lesson they were working individually, but it would also be interesting to see if the children could work out how to make something simple without being given any direction. That would help with building teamwork as well.", "Đúng. Trong bài này các em làm riêng, nhưng sẽ thú vị nếu xem các em có tự tìm ra cách làm một thứ đơn giản mà không có hướng dẫn không. Như vậy còn giúp xây dựng tinh thần làm việc nhóm."],
        ["F", "Yes, but much more of a challenge. One thing that really stood out for me was that the children were all having fun while being taught something new.", "Vâng, nhưng khó hơn nhiều. Điều tôi thấy nổi bật là các em đều vui trong khi học điều mới."],
        ["M", "Which is a key aim of any lesson with this age group. And although these kids had no problems with folding the paper, with younger children you could do origami to help practise fine motor skills.", "Đó là mục tiêu chính của mọi bài học với độ tuổi này. Và dù các em này gấp giấy không gặp khó khăn, với trẻ nhỏ hơn thì có thể dùng origami để luyện các kỹ năng vận động tinh."],
        ["F", "Absolutely. Shall we talk about the individual children we saw on the video? I wrote all their names down and took some notes. Let's start with Sid.", "Chắc chắn rồi. Ta bàn về từng em trong video nhé? Tôi đã ghi tên và ghi chú. Bắt đầu với Sid."],
        ["M", "He was interesting because before they started doing the origami, he was being quite disruptive.", "Em ấy đáng chú ý vì trước khi gấp giấy, em khá gây rối."],
        ["F", "Yes. He really benefited from having to use his hands. It helped him to settle down and start concentrating.", "Vâng. Em ấy thật sự được lợi khi phải dùng tay. Việc đó giúp em ổn định lại và bắt đầu tập trung."],
        ["M", "Yes, I noticed that too. What about Jack? I noticed he seemed to want to work things out for himself.", "Vâng, tôi cũng thấy. Còn Jack thì sao? Tôi thấy em ấy muốn tự tìm ra cách."],
        ["F", "Mmm. You could see him trying out different things rather than asking the teacher for help. What did you make of Naomi?", "Ừ. Có thể thấy em thử nhiều cách thay vì hỏi giáo viên. Anh thấy Naomi thế nào?"],
        ["M", "She seemed to be losing interest at one point, but then she decided she wanted her mouse to be the best, and that motivated her to try harder.", "Có lúc em có vẻ mất hứng, nhưng rồi em quyết định muốn con chuột của mình đẹp nhất, và điều đó thúc em cố gắng hơn."],
        ["F", "She didn't seem satisfied with hers in the end, though.", "Nhưng cuối cùng em có vẻ không hài lòng với sản phẩm của mình."],
        ["M", "No.", "Không."],
        ["F", "Anya was such a star. She listened so carefully and then produced the perfect bird with very little effort.", "Anya thật xuất sắc. Em nghe rất kỹ rồi gấp ra con chim hoàn hảo mà gần như không tốn sức."],
        ["M", "Mmm. I think the teacher could have increased the level of difficulty for her.", "Ừ. Tôi nghĩ giáo viên có thể tăng độ khó cho em."],
        ["F", "Maybe. I think it was the first time Zara had come across origami.", "Có thể. Tôi nghĩ đó là lần đầu Zara gặp origami."],
        ["M", "She looked as if she didn't really get what was going on.", "Em có vẻ không thật sự hiểu chuyện gì đang diễn ra."],
        ["F", "She seemed unsure about what she was supposed to do, but in the end hers didn't turn out too badly.", "Em có vẻ không chắc mình phải làm gì, nhưng cuối cùng sản phẩm của em cũng không tệ lắm."],
        ["M", "Yeah. I'm sure it was a positive learning experience for her.", "Vâng. Tôi chắc đó là một trải nghiệm học tập tích cực với em."],
        ["F", "I think one reason why the origami activity worked so well in this class was that the teacher was well prepared.", "Tôi nghĩ một lý do khiến hoạt động origami hiệu quả là giáo viên đã chuẩn bị kỹ."],
        ["M", "Right. I think it would have taken me ages to prepare examples, showing each of the steps involved in making the bird. But that was a really good idea. The children could see what they were aiming for, and much better for them to be able to hold something rather than just looking at pictures.", "Đúng. Tôi nghĩ tôi sẽ mất rất lâu để chuẩn bị các mẫu, cho thấy từng bước gấp con chim. Nhưng đó là ý rất hay. Các em thấy được mục tiêu, và cầm được vật thật tốt hơn nhiều so với chỉ nhìn tranh."],
        ["F", "Mmm. Those physical examples supported her verbal explanations really well.", "Ừ. Những mẫu thật đó hỗ trợ lời giải thích bằng lời của cô rất tốt."],
        ["M", "It's strange that origami isn't used more widely. Why do you think that is?", "Lạ là origami không được dùng rộng rãi hơn. Anh nghĩ vì sao?"],
        ["F", "Well, teachers may just feel it's not that appealing to children who are used to doing everything on computers, especially boys. Even if they're aware of the benefits.", "Có thể giáo viên thấy nó không hấp dẫn với trẻ quen làm mọi thứ trên máy tính, nhất là các bé trai, dù họ biết lợi ích."],
        ["M", "Oh, I don't know. It's no different to any other craft activity. I bet it's because so many teachers are clumsy like me.", "Ồ, tôi không rõ. Nó không khác các hoạt động thủ công khác. Tôi đoán là vì nhiều giáo viên vụng về như tôi."],
        ["F", "That's true. Too much effort required if you're not good with your hands.", "Đúng. Cần quá nhiều công sức nếu bạn không khéo tay."],
        ["M", "Well, anyway, I think we should try it out in our maths teaching practice with Year 3. I can see using origami is a really engaging way of reinforcing children's knowledge of geometric shapes, like they were doing in the video, but I think it would also work really well for presenting fractions, which is coming up soon.", "Dù sao, tôi nghĩ ta nên thử trong buổi thực hành dạy toán với lớp 3. Tôi thấy origami là cách rất cuốn hút để củng cố kiến thức về hình học như các em làm trong video, nhưng cũng sẽ rất hợp để giới thiệu phân số, phần sắp tới."],
        ["F", "Good idea. That's something most of the kids in that class might struggle with. Origami would also be good practice for using symmetry, but I think they did that last term.", "Ý hay. Đó là phần mà đa số trẻ trong lớp có thể thấy khó. Origami cũng là cách luyện tính đối xứng, nhưng tôi nghĩ các em đã học vào kỳ trước."],
    ], "qs": [
        lq("Câu 21. Which educational skill was shown in the video of children doing origami? (câu 21 và 22 là hai đáp án khác nhau, thứ tự nào cũng được)", "B", "ACE", LSK, "Seb và Lia nói các em `really listening hard to make sure they did all the steps in the right order`. Nghe và làm đúng thứ tự các bước = following instructions. Các em làm riêng nên không phải hợp tác (C); chưa ai nói về phối hợp tay mắt (E)."),
        lq("Câu 22. Which educational skill was shown in the video of children doing origami? (đáp án còn lại)", "D", "ACE", LSK, "Lia: `the children were all having fun while being taught something new`. Vui trong khi học = learning through play. Seb nói thêm về làm việc nhóm nhưng đó là điều có thể làm sau này, không phải điều đã thấy trong video."),
        lq("Câu 23. Sid", "D", "BCFG", LCM, "Lia: origami `helped him to settle down and start concentrating`. Settle down = trở nên bình tĩnh, nên đáp án là seemed to find the activity calming. Trước đó Seb nói em `quite disruptive`, đây là bẫy: em đã khác đi."),
        lq("Câu 24. Jack", "A", "BCDF", LCM, "Lia: `trying out different things rather than asking the teacher for help`. Tự làm, không hỏi giáo viên = demonstrated independence. Đối lập với B."),
        lq("Câu 25. Naomi", "C", "ABEF", LCM, "Seb: Naomi muốn `her mouse to be the best` và điều đó thúc em cố gắng. Muốn hơn người khác = competitive attitude. Lia nói thêm em không hài lòng cuối cùng, nên E sai."),
        lq("Câu 26. Anya", "G", "BDEF", LCM, "Lia: Anya `produced the perfect bird with very little effort`. Ít tốn sức = seemed to find the activity easy."),
        lq("Câu 27. Zara", "F", "ABDG", LCM, "Zara `didn't really get what was going on` và `seemed unsure about what she was supposed to do`. Không hiểu và không chắc = seemed confused. Kết quả cuối `didn't turn out too badly` nhưng câu hỏi hỏi nhận xét về em."),
        lq("Câu 28. Before starting an origami activity in class, the students think it is important for the teacher to", "A", "BC", LABC28, "Seb khen việc chuẩn bị mẫu cho từng bước gấp: `prepare examples, showing each of the steps`. Đó là make models that demonstrate the different stages. Thuật ngữ và lời trấn an không được nhắc."),
        lq("Câu 29. The students agree that some teachers might be unwilling to use origami in class because", "B", "AC", LABC29, "Seb: nhiều giáo viên `clumsy like me`; Lia đồng ý: `too much effort required if you're not good with your hands`. Họ thiếu kỹ năng tay. Lia có nêu giả thuyết trẻ thấy không hấp dẫn, nhưng Seb bác lại (`it's no different to any other craft`), nên A sai."),
        lq("Câu 30. Why do the students decide to use origami in their maths teaching practice?", "C", "AB", LABC30, "Seb: origami hợp để `presenting fractions, which is coming up soon`, và Lia nói đó là phần trẻ có thể thấy khó. Giới thiệu khái niệm mới = to introduce a new concept. Hình học là phần củng cố, không phải lý do chính."),
    ]},
    ],
}

"""Days 8 and 9: reading days built from Complete IELTS 5-6.5 (Unit 1, the easier step) and Cambridge IELTS 18 (Test 1, Passage 1).

DAYS[n] has the same keys as days56.DAYS plus:
  passages: list of {id, title, instr, text, qs: [(prompt_en, [right, wrong...], why_vi)]}; a question whose options are
            {True, False, Not Given} is shown in that fixed order.
  my:       list of {vi, en, model}: personal sentences typed by the learner.
  family:   word family label.
Sections of the day (choice/typed) live in SECTIONS below, same line format as book_items.SECTIONS.
"""
CI = "Complete IELTS 5-6.5, Unit 1"
C18 = "Cambridge IELTS 18, Test 1"
TFNG = ["True", "False", "Not Given"]

CULTURE = """Australian culture and culture shock
by Anna Jones and Xuan Quach
Sometimes work, study or a sense of adventure take us out of our familiar surroundings to go and live in a different culture. The experience can be difficult, even shocking. Almost everyone who studies, lives or works abroad has problems adjusting to a new culture. This response is commonly referred to as 'culture shock'. Culture shock can be defined as 'the physical and emotional discomfort a person experiences when entering a culture different from their own' (Weaver, 1993).
For people moving to Australia, Price (2001) has identified certain values which may give rise to culture shock. Firstly, he argues that Australians place a high value on independence and personal choice. This means that a teacher or course tutor will not tell students what to do, but will give them a number of options and suggest they work out which one is the best in their circumstances. It also means that they are expected to take action if something goes wrong and seek out resources and support for themselves.
Australians are also prepared to accept a range of opinions rather than believing there is one truth. This means that in an educational setting, students will be expected to form their own opinions and defend the reasons for that point of view and the evidence for it.
Price also comments that Australians are uncomfortable with differences in status and hence idealise the idea of treating everyone equally. An illustration of this is that most adult Australians call each other by their first names. This concern with equality means that Australians are uncomfortable taking anything too seriously and are even ready to joke about themselves.
Australians believe that life should have a balance between work and leisure time. As a consequence, some students may be critical of others who they perceive as doing nothing but study.
Australian notions of privacy mean that areas such as financial matters, appearance and relationships are only discussed with close friends. While people may volunteer such information, they may resent someone actually asking them unless the friendship is firmly established. Even then, it is considered very impolite to ask someone what they earn. With older people, it is also rude to ask how old they are, why they are not married or why they do not have children. It is also impolite to ask people how much they have paid for something, unless there is a very good reason for asking.
Kohls (1996) describes culture shock as a process of change marked by four basic stages. During the first stage, the new arrival is excited to be in a new place, so this is often referred to as the 'honeymoon' stage. Like a tourist, they are intrigued by all the new sights and sounds, new smells and tastes of their surroundings. They may have some problems, but usually they accept them as just part of the novelty. At this point, it is the similarities that stand out, and it seems to the newcomer that people everywhere and their way of life are very much alike. This period of euphoria may last from a couple of weeks to a month, but the letdown is inevitable.
During the second stage, known as the 'rejection' stage, the newcomer starts to experience difficulties due to the differences between the new culture and the way they were accustomed to living. The initial enthusiasm turns into irritation, frustration, anger and depression, and these feelings may have the effect of people rejecting the new culture so that they notice only the things that cause them trouble, which they then complain about. In addition, they may feel homesick, bored, withdrawn and irritable during this period as well.
Fortunately, most people gradually learn to adapt to the new culture and move on to the third stage, known as 'adjustment and reorientation'. During this stage a transition occurs to a new optimistic attitude. As the newcomer begins to understand more of the new culture, they are able to interpret some of the subtle cultural clues which passed by unnoticed earlier. Now things make more sense and the culture seems more familiar. As a result, they begin to develop problem-solving skills, and feelings of disorientation and anxiety no longer affect them.
In Kohls's model, in the fourth stage, newcomers undergo a process of adaptation. They have settled into the new culture, and this results in a feeling of direction and self-confidence. They have accepted the new food, drinks, habits and customs and may even find themselves enjoying some of the very customs that bothered them so much previously. In addition, they realise that the new culture has good and bad things to offer and that no way is really better than another, just different."""

CULTURE_P1 = CULTURE.split("\n")[2]

URBAN = """Urban farming
In Paris, urban farmers are trying a soil-free approach to agriculture that uses less space and fewer resources. Could it help cities face the threats to our food supplies?
On top of a striking new exhibition hall in southern Paris, the world's largest urban rooftop farm has started to bear fruit. Strawberries that are small, intensely flavoured and resplendently red sprout abundantly from large plastic tubes. Peer inside and you see the tubes are completely hollow, the roots of dozens of strawberry plants dangling down inside them. From identical vertical tubes nearby burst row upon row of lettuces; near those are aromatic herbs, such as basil, sage and peppermint. Opposite, in narrow, horizontal trays packed not with soil but with coconut fibre, grow cherry tomatoes, shiny aubergines and brightly coloured chards.
Pascal Hardy, an engineer and sustainable development consultant, began experimenting with vertical farming and aeroponic growing towers — as the soil-free plastic tubes are known — on his Paris apartment block roof five years ago. The urban rooftop space above the exhibition hall is somewhat bigger: 14,000 square metres and almost exactly the size of a couple of football pitches. Already, the team of young urban farmers who tend it have picked, in one day, 3,000 lettuces and 150 punnets of strawberries. When the remaining two thirds of the vast open area are in production, 20 staff will harvest up to 1,000 kg of perhaps 35 different varieties of fruit and vegetables, every day. 'We're not ever, obviously, going to feed the whole city this way,' cautions Hardy. 'In the urban environment you're working with very significant practical constraints, clearly, on what you can do and where. But if enough unused space can be developed like this, there's no reason why you shouldn't eventually target maybe between 5% and 10% of consumption.'
Perhaps most significantly, however, this is a real-life showcase for the work of Hardy's flourishing urban agriculture consultancy, Agripolis, which is currently fielding enquiries from around the world to design, build and equip a new breed of soil-free inner-city farm. 'The method's advantages are many,' he says. 'First, I don't much like the fact that most of the fruit and vegetables we eat have been treated with something like 17 different pesticides, or that the intensive farming techniques that produced them are such huge generators of greenhouse gases. I don't much like the fact, either, that they've travelled an average of 2,000 refrigerated kilometres to my plate, that their quality is so poor, because the varieties are selected for their capacity to withstand such substantial journeys, or that 80% of the price I pay goes to wholesalers and transport companies, not the producers.'
Produce grown using this soil-free method, on the other hand — which relies solely on a small quantity of water, enriched with organic nutrients, pumped around a closed circuit of pipes, towers and trays — is 'produced up here, and sold locally, just down there. It barely travels at all,' Hardy says. 'You can select crop varieties for their flavour, not their resistance to the transport and storage chain, and you can pick them when they're really at their best, and not before.' No soil is exhausted, and the water that gently showers the plants' roots every 12 minutes is recycled, so the method uses 90% less water than a classic intensive farm for the same yield.
Urban farming is not, of course, a new phenomenon. Inner-city agriculture is booming from Shanghai to Detroit and Tokyo to Bangkok. Strawberries are being grown in disused shipping containers, mushrooms in underground carparks. Aeroponic farming, he says, is 'virtuous'. The equipment weighs little, can be installed on almost any flat surface and is cheap to buy: roughly €100 to €150 per square metre. It is cheap to run, too, consuming a tiny fraction of the electricity used by some techniques.
Produce grown this way typically sells at prices that, while generally higher than those of classic intensive agriculture, are lower than soil-based organic growers. There are limits to what farmers can grow this way, of course, and much of the produce is suited to the summer months. 'Root vegetables we cannot do, at least not yet,' he says. 'Radishes are OK, but carrots, potatoes, that kind of thing — the roots are simply too long. Fruit trees are obviously not an option. And beans tend to take up a lot of space for not much return.' Nevertheless, urban farming of the kind being practised in Paris is one part of a bigger and fast-changing picture that is bringing food production closer to our lives."""


def q(prompt: str, right: str, wrong: list[str], why: str) -> tuple:
    return (prompt, [right] + wrong, why)


def tf(prompt: str, answer: str, why: str) -> tuple:
    return (prompt, [answer] + [t for t in TFNG if t != answer], why)


SECTIONS: list[tuple] = [
    (8, "V1", CI + " · Vocabulary, bài 1 (trang 12)", "problem hay trouble? affect hay effect?", "Chọn từ đúng. Nhớ: affect là động từ (làm thay đổi), effect là danh từ (kết quả); problem đếm được, trouble hầu như không đếm được.", "choice", [
        "They may have some ( ), but usually they accept them as just part of the novelty. | problems | troubles | `problems` đếm được, có `some` + số nhiều. `trouble` hầu như không đếm được nên không dùng dạng số nhiều ở nghĩa này.",
        "They notice only the things that cause them a ( ). | problem | trouble | Có mạo từ `a` thì dùng `problem`. Không nói `a trouble`.",
        "Feelings of disorientation and anxiety no longer ( ) them. | affect | effect | Chỗ trống là động từ: `affect` = làm thay đổi, ảnh hưởng.",
        "These feelings may have the ( ) of people rejecting the new culture. | effect | affect | Sau `the` cần danh từ: `the effect of …` = kết quả là.",
    ]),
    (8, "V2", CI + " · Vocabulary, bài 2 (trang 12)", "Sửa lỗi thí sinh hay mắc: affect, effect, problem, trouble", "Điền từ đúng vào chỗ trống. Trong sách năm trong sáu câu có lỗi; ở đây bạn gõ từ đúng cho từng câu.", "typed", [
        "Many students' studies are ( ㉠ ) by difficulties with language. | affected | Có `are … by` là bị động của động từ: `affected`, không phải `effected`.",
        "Overseas students have accommodation ( ㉠ ). | problems | `problems` đúng (câu gốc trong sách không sai). `troubles` không tự nhiên ở đây.",
        "Modern lifestyles have an ( ㉠ ) on our health. | effect | `have an effect on …` = có ảnh hưởng tới; sau `an` là danh từ.",
        "Other countries ( ㉠ ) our customs. | affect | Chỗ trống là động từ chính của câu: `affect`.",
        "Immigrants have an ( ㉠ ) on the local economy. | effect | `have an effect on …`; danh từ sau `an`.",
        "Most children can deal with their own ( ㉠ ). | problems | Sách sửa `troubles` thành `problems`: nói về từng khó khăn riêng thì dùng `problems`.",
    ]),
    (8, "P1", CI + " · Writing, bài 8 (trang 15)", "percent hay percentage? Quy tắc", "Trả lời bốn quy tắc dùng percent và percentage.", "choice", [
        "Sau một con số cụ thể (46 …) ta dùng từ nào? | percent | percentage | `46 percent`. `percentage` không đi với số cụ thể.",
        "Từ nào không dùng với con số đã cho? | percentage | percent | `the percentage of people …` (không có số). Có số thì dùng `percent`.",
        "Có dùng `a` trước percent không? | Không | Có | Không nói `a two percent`. Viết `two percent`.",
        "Từ nào đứng trước `percentage`: a, an hay the? | the | a | `the percentage of …` là mẫu chuẩn.",
        "`percent` có thêm -s thành số nhiều không? | Không | Có | Không bao giờ: `58 percent`, không phải `58 percents`.",
    ]),
    (8, "P2", CI + " · Writing, bài 9 (trang 15)", "Sửa câu có lỗi percent/percentage", "Điền từ đúng vào chỗ trống. Đây là những lỗi thí sinh IELTS hay mắc nhất ở Writing Task 1.", "typed", [
        "The graph shows the increase in the ( ㉠ ) of people who used rail transport between 1976 and 1999. | percentage | Không có con số, nên dùng `percentage`.",
        "The graph shows the percentage of people with a criminal record according to their age and ( ㉠ ) percentage of people in prison according to their gender. | the | `the percentage of …`: thiếu `the`.",
        "By 1995, the numbers had fallen to ( ㉠ ) percent. | two | Không dùng `a` trước percent: `two percent`.",
        "In 2004, the number rose to approximately 58 ( ㉠ ). | percent | `percent` không thêm -s.",
        "It is surprising that ( ㉠ ) percentage of people watching television remained the same. | the | Thiếu `the` trước `percentage`.",
        "On the other hand, socialising with friends rose sharply to 25 ( ㉠ ) in comparison with 1981. | percent | Có số `25` nên dùng `percent`, không dùng `percentage`.",
    ]),
    (8, "W1", CI + " · Writing, bài 2–3 (trang 14)", "Câu mở đầu cho bài tóm tắt biểu đồ (không chấm điểm)", "Câu mở đầu chỉ cần nói biểu đồ cho thấy gì, bằng lời của bạn chứ không chép đề. Gõ từ còn thiếu. Đây là luyện nhận ra mẫu câu, chưa phải bài viết có chấm điểm.", "typed", [
        "The ( ㉠ ) shows the changes in the number of people from abroad who visited Townsville, Queensland, over a four-year period. | graph | Từ chỉ cách thông tin được trình bày (đồ thị đường): `The graph`. Phần sau `shows the changes in …` diễn đạt mục đích bằng lời của người viết, và `over a four-year period` là khoảng thời gian.",
        "The chart shows the number of households in Winchester, California, and the languages which people ( ㉠ ) there. | speak | `the languages which people speak there` = các ngôn ngữ người ta nói ở đó.",
        "The chart shows the difficulties people have when they ( ㉠ ) into a new country and how the problems vary according to age. | integrate | `integrate into a new country` = hoà nhập vào một đất nước mới; đây là cách đổi lời từ `go to live in other countries`.",
    ]),
    (9, "TY", C18 + " · Reading Passage 1, Questions 1–7 (gõ lại)", "Gõ đáp án: hoàn thành câu và bảng (tối đa hai từ hoặc con số)", "Sau khi đã đọc bài và chọn đáp án ở bài trước, bây giờ gõ lại từ đúng như trong bài, đúng chính tả. Trong đề thật bạn phải tự tìm từ, không có lựa chọn.", "typed", [
        "Vertical tubes are used to grow strawberries, ( ㉠ ) and herbs. | lettuces | Đoạn 1: `From identical vertical tubes nearby burst row upon row of lettuces`. Viết đúng số nhiều `lettuces`, như trong bài.",
        "There will eventually be a daily harvest of as much as ( ㉠ ) in weight of fruit and vegetables. | 1,000 kg;1000 kg;1000kg;1,000kg | Đoạn 2: `20 staff will harvest up to 1,000 kg … every day`. `up to` = as much as.",
        "It may be possible that the farm's produce will account for as much as 10% of the city's ( ㉠ ) overall. | food consumption;consumption | Đoạn 2: `target maybe between 5% and 10% of consumption`. Đáp án của sách là `(food) consumption`.",
        "Intensive farming: a wide range of ( ㉠ ) used. | pesticides | Đoạn 4: `treated with something like 17 different pesticides`. `wide range` = `17 different`.",
        "Intensive farming: varieties of fruit and vegetables chosen that can survive long ( ㉠ ). | journeys | Đoạn 4: `selected for their capacity to withstand such substantial journeys`. `survive` = `withstand`.",
        "Intensive farming: ( ㉠ ) receive very little of overall income. | producers | Đoạn 4: `80% of the price I pay goes to wholesalers and transport companies, not the producers`.",
        "Aeroponic urban farming: produce chosen because of its ( ㉠ ). | flavour;flavor | Đoạn 5: `You can select crop varieties for their flavour`. Viết kiểu Anh `flavour` hoặc kiểu Mỹ `flavor` đều được.",
    ]),
]

DAYS: dict[int, dict] = {
    8: {
        "title": "Culture shock: a graded reading from Complete IELTS", "title_vi": "Culture shock: bài đọc bậc dễ và ba lỗi hay mắc",
        "goal": "Đọc chậm một bài Reading Section 1 ở bậc 5–6.5, làm đúng dạng đúng/sai/không có thông tin và điền bảng, rồi sửa ba cặp lỗi thí sinh hay mắc: problem/trouble, affect/effect, percent/percentage.",
        "ielts": "Bài này là bậc thang trước Cambridge 18: cùng dạng câu hỏi nhưng văn bản ngắn và từ dễ hơn. Ba cặp lỗi xuất hiện liên tục ở Writing Task 1 và 2.",
        "source": "Complete IELTS 5-6.5, Unit 1; từ neo B2 theo cách của thầy Minh", "family": "Văn hoá",
        "recognize": {"resent", "disorientation", "inevitable", "accustomed to"},
        "editor": "Bài đọc và bài tập theo Complete IELTS Bands 5-6.5 Unit 1 (trang 8–16, đáp án trang 149–150). Chỉ lấy phần đọc chậm, từ vựng-lỗi hay mắc và câu mở đầu Writing; phần nghe cần file âm thanh (chưa có), phần nói và so sánh tính từ để dành cho các tuần sau.",
        "book": [("Complete IELTS 5-6.5", "10–12", "Reading Section 1 (13 câu)", 13, 30), ("Complete IELTS 5-6.5", "12, 15", "Vocabulary 1–2, Writing 8–9", 17, 20),
                 ("Complete IELTS 5-6.5", "14", "Writing 2–3: câu mở đầu", 3, 10)],
        "sittings": [
            ("Từ để đọc trước bài", [
                ("culture shock", "N", "cú sốc văn hoá: cảm giác khó chịu khi sống ở nơi lạ", "Many students feel culture shock in the first month.", "Nhiều sinh viên bị cú sốc văn hoá trong tháng đầu."),
                ("adjust", "V", "làm quen, điều chỉnh bản thân (neo vào change a little to fit)", "It took me a month to adjust to the new school.", "Tôi mất một tháng để quen với ngôi trường mới."),
                ("adapt", "V", "thích nghi (neo vào adjust)", "Most people adapt to a new culture in time.", "Hầu hết mọi người thích nghi với văn hoá mới theo thời gian."),
                ("newcomer", "N", "người mới đến", "A newcomer often notices the similarities first.", "Người mới đến thường thấy điểm giống nhau trước."),
                ("homesick", "A", "nhớ nhà", "I felt homesick in my first week at university.", "Tôi nhớ nhà trong tuần đầu ở đại học."),
                ("impolite", "A", "bất lịch sự (neo vào rude)", "It is impolite to ask someone what they earn.", "Hỏi ai đó kiếm được bao nhiêu là bất lịch sự."),
                ("privacy", "N", "sự riêng tư", "Some cultures place a high value on privacy.", "Một số nền văn hoá đề cao sự riêng tư."),
                ("equality", "N", "sự bình đẳng", "Australians value equality at work and in school.", "Người Úc coi trọng sự bình đẳng ở nơi làm việc và trường học."),
                ("resent", "V", "bực bội, không bằng lòng (C1; neo vào be angry about)", "People may resent questions about their salary.", "Người ta có thể khó chịu với câu hỏi về lương."),
                ("accustomed to", "X", "đã quen với (C1; neo vào be used to)", "He was not accustomed to the cold weather.", "Anh ấy chưa quen với thời tiết lạnh."),
            ]),
            ("Từ về các giai đoạn và cảm xúc", [
                ("stage", "N", "giai đoạn", "Culture shock has four stages.", "Cú sốc văn hoá có bốn giai đoạn."),
                ("similarity", "N", "điểm giống nhau", "At first, newcomers notice similarities, not differences.", "Lúc đầu người mới đến thấy điểm giống chứ không thấy điểm khác."),
                ("enthusiasm", "N", "sự hào hứng", "My enthusiasm turned into frustration.", "Sự hào hứng của tôi chuyển thành bực bội."),
                ("frustration", "N", "sự bực bội vì không làm được", "He felt frustration when nobody understood him.", "Anh ấy bực bội khi không ai hiểu mình."),
                ("disorientation", "N", "cảm giác lạc hướng, bối rối (C1; neo vào feeling lost)", "Disorientation disappears as you understand the culture.", "Cảm giác bối rối biến mất khi bạn hiểu văn hoá."),
                ("anxiety", "N", "sự lo lắng", "Anxiety is common in the first weeks abroad.", "Lo lắng là chuyện thường trong những tuần đầu ở nước ngoài."),
                ("inevitable", "A", "không thể tránh khỏi (C1; neo vào sure to happen)", "After the honeymoon, a letdown is inevitable.", "Sau thời kỳ trăng mật, sự hụt hẫng là điều khó tránh."),
            ]),
        ],
        "passages": [
            {"id": "P1", "title": "Culture shock: đoạn mở đầu", "instr": "Đọc đoạn đầu thật chậm, gạch từ khóa trong từng câu hỏi rồi mới chọn. True = bài nói đúng như vậy; False = bài nói ngược lại; Not Given = bài không nói.", "text": CULTURE_P1, "qs": [
                tf("Culture shock affects most people who spend time living in another country.", "True", "`Almost everyone who studies, lives or works abroad has problems adjusting` = hầu hết mọi người. `Almost everyone` ≈ `most people`."),
                tf("Culture shock affects certain types of people more quickly than others.", "Not Given", "Đoạn không nói loại người nào bị nhanh hơn. Có chủ đề `culture shock` nhưng không có so sánh giữa các loại người."),
                tf("Culture shock only affects how people feel.", "False", "Định nghĩa trong bài: `the physical and emotional discomfort`. Có cả khó chịu về thể chất lẫn cảm xúc, nên `only` sai."),
            ]},
            {"id": "P2", "title": "Culture shock: câu 1–6 (đúng/sai/không có thông tin)", "instr": "Dùng từ gạch chân trong câu để tìm đoạn liên quan rồi đọc kỹ đoạn đó. Chú ý các từ mạnh như only, all, most.", "text": CULTURE, "qs": [
                tf("Australian teachers will suggest alternatives to students rather than offer one solution.", "True", "Đoạn 2: `will not tell students what to do, but will give them a number of options`. `alternatives` = `a number of options`."),
                tf("In Australia, teachers will show interest in students' personal circumstances.", "Not Given", "Bài có `circumstances` và `teacher` nhưng không nói giáo viên có quan tâm tới hoàn cảnh cá nhân hay không."),
                tf("Australians use people's first names so that everyone feels their status is similar.", "True", "Đoạn 4: `uncomfortable with differences in status … most adult Australians call each other by their first names`."),
                tf("Students who study all the time may receive positive comments from their colleagues.", "False", "Đoạn 5: `some students may be critical of others who they perceive as doing nothing but study`. Bị chê chứ không được khen."),
                tf("It is acceptable to discuss financial issues with people you do not know well.", "False", "Đoạn 6: `financial matters … are only discussed with close friends`. Người không thân thì không bàn."),
                tf("Younger Australians tend to be friendlier than older Australians.", "Not Given", "Bài nhắc người lớn tuổi nhưng không so sánh mức thân thiện giữa trẻ và già."),
            ]},
            {"id": "P3", "title": "Culture shock: câu 7–13 (hoàn thành bảng)", "instr": "Bảng tóm tắt bốn giai đoạn. Trong đề thật bạn tự tìm từ (tối đa hai từ trong bài). Ở đây chọn từ đúng từ bài; hãy tự đoán loại từ cần điền trước khi nhìn các lựa chọn.", "text": CULTURE, "qs": [
                q("Stage 1 (câu 7): the name of the stage is the ( ) stage.", "honeymoon", ["rejection", "adjustment", "adaptation"], "Đoạn nói về bốn giai đoạn của Kohls: `the first stage … often referred to as the 'honeymoon' stage`."),
                q("Stage 1 (câu 8): They notice the ( ) between different nationalities and cultures.", "similarities", ["differences", "customs", "feelings"], "`it is the similarities that stand out`. Đây là điều người mới đến thấy trước."),
                q("Stage 1 (câu 9): They may experience this stage for up to ( ).", "a month", ["a couple of days", "two years", "four weeks and a day"], "`may last from a couple of weeks to a month`. Đáp án của sách chấp nhận `a/one month`."),
                q("Rejection (câu 10): They reject the new culture and lose the ( ) they had at the beginning.", "enthusiasm", ["irritation", "frustration", "anxiety"], "`The initial enthusiasm turns into irritation …`. `initial` = `at the beginning`."),
                q("Adjustment and reorientation (câu 11): They can understand some ( ) which they had not previously observed.", "cultural clues", ["problem-solving skills", "new customs", "subtle feelings"], "`interpret some of the subtle cultural clues which passed by unnoticed earlier`. Cụm trong sách: (cultural) clues."),
                q("Adjustment and reorientation (câu 12): They learn ( ) for dealing with difficulties.", "problem-solving skills", ["cultural clues", "new habits", "anxiety"], "`they begin to develop problem-solving skills`. Trong bảng, `dealing with difficulties` = `problem-solving`."),
                q("Stage 4 (câu 13): the name of the stage is ( ).", "adaptation", ["adjustment", "rejection", "honeymoon"], "`newcomers undergo a process of adaptation`. Chú ý: giai đoạn ba là `adjustment and reorientation`, giai đoạn bốn mới là `adaptation`."),
            ]},
        ],
        "my": [
            {"vi": "Kể về một lần bạn thấy lạ hoặc khó chịu khi tới một nơi mới (trường, thành phố, công việc). Dùng ít nhất hai từ mới của bài, ví dụ homesick, adjust, adapt, impolite.", "en": "Write two sentences about a time you felt strange in a new place. Use at least two words from today.",
             "model": "When I started university, I felt homesick and it took me a month to adjust. It was hard to adapt to living with strangers."},
        ],
    },
    9: {
        "title": "Urban farming: Cambridge IELTS 18, Test 1, Passage 1", "title_vi": "Urban farming: đọc chậm đề thật Cambridge 18",
        "goal": "Đọc chậm bài Passage 1 của đề Cambridge 18, hiểu từng đoạn, làm 13 câu (hoàn thành câu, bảng, đúng/sai/không có thông tin) và chỉ ra mỗi đáp án nằm ở đâu và vì sao.",
        "ielts": "Đây là cấp độ đề thật. Giai đoạn 1 không bấm giờ: mục tiêu là hiểu đúng và biết đáp án nằm ở chỗ nào, tốc độ để giai đoạn 2.",
        "source": "Cambridge IELTS 18, Test 1, Passage 1; từ neo B2 theo cách của thầy Minh", "family": "Nông nghiệp đô thị",
        "recognize": {"withstand", "exhaust", "wholesaler", "flourishing", "phenomenon", "constraint"},
        "editor": "Bài đọc và đáp án theo Cambridge IELTS 18, Test 1 (trang 16–19, đáp án trang 120). Phần Listening Part 1 của đề này cần file âm thanh và script đã dựng được từ OCR hai cột; chưa đưa vào.",
        "book": [("Cambridge IELTS 18", "16–19", "Test 1, Reading Passage 1 (13 câu)", 13, 40)],
        "sittings": [
            ("Từ nền để đọc bài", [
                ("soil", "N", "đất trồng", "Plants need soil, water and light.", "Cây cần đất, nước và ánh sáng."),
                ("harvest", "V", "thu hoạch", "They harvest the crops in autumn.", "Họ thu hoạch vụ mùa vào mùa thu."),
                ("variety", "N", "giống, loại", "The farm grows many varieties of tomato.", "Nông trại trồng nhiều giống cà chua."),
                ("consumption", "N", "mức tiêu thụ", "Food consumption is rising in cities.", "Mức tiêu thụ thực phẩm ở các thành phố đang tăng."),
                ("pesticide", "N", "thuốc trừ sâu", "Many fruits are treated with pesticides.", "Nhiều loại trái cây được xử lý bằng thuốc trừ sâu."),
                ("producer", "N", "nhà sản xuất, người làm ra", "Producers often get a small share of the price.", "Người sản xuất thường nhận một phần nhỏ trong giá bán."),
                ("recycle", "V", "tái chế, dùng lại", "The farm recycles its water.", "Nông trại dùng lại nước của mình."),
                ("limit", "N", "giới hạn", "There are limits to what can be grown this way.", "Có những giới hạn về thứ có thể trồng theo cách này."),
            ]),
            ("Từ C1 trong bài", [
                ("intensive", "A", "thâm canh, dồn nhiều sức vào một diện tích nhỏ", "Intensive farming uses a lot of chemicals.", "Canh tác thâm canh dùng nhiều hoá chất."),
                ("constraint", "N", "ràng buộc, hạn chế (neo vào limit)", "Space is the main constraint in a city.", "Không gian là hạn chế chính trong thành phố."),
                ("yield", "N", "sản lượng thu được (neo vào amount harvested)", "The method gives the same yield with less water.", "Phương pháp này cho cùng sản lượng với ít nước hơn."),
                ("withstand", "V", "chịu được (neo vào survive)", "These varieties can withstand long journeys.", "Những giống này chịu được những chuyến đi dài."),
                ("exhaust", "V", "làm cạn kiệt (neo vào use up)", "Farming can exhaust the soil.", "Canh tác có thể làm cạn kiệt đất."),
                ("wholesaler", "N", "người bán sỉ", "Wholesalers take most of the price.", "Người bán sỉ lấy phần lớn giá bán."),
                ("phenomenon", "N", "hiện tượng", "Urban farming is not a new phenomenon.", "Canh tác đô thị không phải là hiện tượng mới."),
                ("flourishing", "A", "phát triển mạnh (neo vào growing well)", "He runs a flourishing business.", "Anh ấy điều hành một doanh nghiệp đang phát triển mạnh."),
            ]),
        ],
        "passages": [
            {"id": "P1", "title": "Urban farming: câu 1–7 (hoàn thành câu và bảng)", "instr": "Đọc chậm từng đoạn, gạch từ khóa trong câu hỏi rồi tìm vị trí trong bài. Ở đề thật bạn tự điền (tối đa hai từ và/hoặc con số; bảng chỉ một từ). Ở đây chọn từ đúng trước, bài sau gõ lại.", "text": URBAN, "qs": [
                q("Câu 1: Vertical tubes are used to grow strawberries, ( ) and herbs.", "lettuces", ["tomatoes", "chards", "mushrooms"], "Đoạn 1: `From identical vertical tubes nearby burst row upon row of lettuces; near those are aromatic herbs`. Cà chua và cải mọc ở khay ngang, không phải ống đứng."),
                q("Câu 2: There will eventually be a daily harvest of as much as ( ) in weight of fruit and vegetables.", "1,000 kg", ["3,000 lettuces", "150 punnets", "14,000 square metres"], "Đoạn 2: `20 staff will harvest up to 1,000 kg … every day`. Hai con số kia là số đã hái trong một ngày và diện tích."),
                q("Câu 3: It may be possible that the farm's produce will account for as much as 10% of the city's ( ) overall.", "consumption", ["income", "space", "production"], "Đoạn 2: `target maybe between 5% and 10% of consumption`. Đáp án của sách: (food) consumption."),
                q("Câu 4 (bảng): Intensive farming — a wide range of ( ) used.", "pesticides", ["techniques", "varieties", "greenhouse"], "Đoạn 4: `treated with something like 17 different pesticides`. `Wide range` = `17 different`."),
                q("Câu 5 (bảng): Intensive farming — varieties chosen that can survive long ( ).", "journeys", ["kilometres", "storage", "transport"], "Đoạn 4: `selected for their capacity to withstand such substantial journeys`. `survive` = `withstand`. `Transport` xuất hiện nhưng không đúng chỗ."),
                q("Câu 6 (bảng): Intensive farming — ( ) receive very little of overall income.", "producers", ["wholesalers", "consumers", "farmers"], "Đoạn 4: `80% of the price I pay goes to wholesalers and transport companies, not the producers`. Người nhận ít là `producers`."),
                q("Câu 7 (bảng): Aeroponic urban farming — produce chosen because of its ( ).", "flavour", ["resistance", "size", "price"], "Đoạn 5: `select crop varieties for their flavour, not their resistance to the transport and storage chain`. `resistance` là thứ bị loại, không phải lý do chọn."),
            ]},
            {"id": "P2", "title": "Urban farming: câu 8–13 (đúng/sai/không có thông tin)", "instr": "Với mỗi câu, tìm đoạn nói về ý đó. Chú ý các từ so sánh và từ mạnh (more, cheaper, most, any time).", "text": URBAN, "qs": [
                tf("Urban farming can take place above or below ground.", "True", "Đoạn 6: `Strawberries are being grown in disused shipping containers, mushrooms in underground carparks`; đoạn 1 có nông trại trên mái. Trên cao và dưới đất đều có."),
                tf("Some of the equipment used in aeroponic farming can be made by hand.", "Not Given", "Bài nói thiết bị nhẹ, dễ lắp và rẻ, nhưng không nói có thể tự làm bằng tay."),
                tf("Urban farming relies more on electricity than some other types of farming.", "False", "Đoạn 6: `consuming a tiny fraction of the electricity used by some techniques`. Dùng ít điện hơn, ngược với câu."),
                tf("Fruit and vegetables grown on an aeroponic urban farm are cheaper than traditionally grown organic produce.", "True", "Đoạn 7: giá `higher than classic intensive agriculture, are lower than soil-based organic growers`. Rẻ hơn rau hữu cơ trồng bằng đất."),
                tf("Most produce can be grown on an aeroponic urban farm at any time of the year.", "False", "Đoạn 7: `much of the produce is suited to the summer months`. Phần lớn hợp mùa hè, không phải quanh năm."),
                tf("Beans take longer to grow on an urban farm than other vegetables.", "Not Given", "Đoạn 7: `beans tend to take up a lot of space for not much return`. Nói về chiếm nhiều chỗ chứ không nói về thời gian lớn."),
            ]},
        ],
        "my": [
            {"vi": "Tóm tắt bài đọc bằng một hoặc hai câu tiếng Anh của chính bạn. Không chép nguyên câu trong bài. Thử dùng một từ B2 và một từ C1 trong bài (ví dụ method, intensive, constraint).", "en": "Summarise the passage 'Urban farming' in one or two sentences in your own words.",
             "model": "In Paris, farmers grow fruit and vegetables on a rooftop without soil. This method uses less water and space than intensive farming, although some crops cannot be grown this way."},
        ],
    },
}

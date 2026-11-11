"""Book exercises of week 1, typed in from the scans with the books' answer keys and a Vietnamese reason for each answer.

The owner runs this app privately (the repository is private), so the exercises, keys and notes of the books are kept here
so the learner can work them in the app. Sources:
  B2  = Destination B2 Grammar & Vocabulary (Mann & Taylore-Knowles, Macmillan), Unit 1 pp. 6-11, key p. 229
  G65 = IELTS Grammar for Bands 6.5 and above (Hopkins & Cullen, Cambridge), Unit 1, section C, key p. 220

Line formats (fields split by " | "):
  choice : stem | right | wrong | wrong... | why     stem with "( )" is a cloze, otherwise it is a prompt shown as is
  typed  : text with ( ㉠ ) | accepted;accepted | tip
Each section is (day, code, source, title, instruction, kind, lines)."""
from __future__ import annotations

B2 = "Destination B2, Unit 1"
G65 = "IELTS Grammar 6.5+, Unit 1"

SECTIONS: list[tuple] = [
    # ---------------------------------------------------------------- day 1
    (1, "A", B2 + " · bài A (trang 8)", "Khoanh từ đúng", "Chọn cách nói đúng với ý của câu. Hỏi: người nói trình bày việc này như thói quen/sự thật, hay như việc đang diễn ra?", "choice", [
        "Elizabeth ( ) to bed at around eleven o'clock. | usually goes | is usually going | `usually` = thói quen lặp lại → hiện tại đơn. Ngôi thứ ba số ít nên có -s.",
        "Dan ( ) on the other phone right now. | is talking | talks | `right now` = đang xảy ra lúc nói → hiện tại tiếp diễn.",
        "We ( ) any meat at the moment as we're both on a diet. | aren't eating | don't eat | `at the moment` + đang ăn kiêng = tạm thời → tiếp diễn. Bình thường họ vẫn ăn thịt.",
        "( ) increasingly safe? | Is air travel getting | Does air travel get | `increasingly` nói về một xu hướng đang thay đổi → tiếp diễn (trục: situation changing).",
        "My mum ( ) me every weekend without fail. | calls | is calling | `every weekend without fail` = thói quen đều đặn → đơn.",
        "How much ( )? | do babysitters generally earn | are babysitters generally earning | `generally` nói về quy luật chung, không phải việc tạm thời → đơn. Câu hỏi mượn `do`.",
        "( ) up with excuses for not having done your homework. It's so annoying! | You're always coming | You always come | Câu có chữ `annoying`: `always` + tiếp diễn để phàn nàn việc lặp lại quá mức người nói thấy khó chịu.",
        "Chọn cặp đúng cho: «___ out much during the week but ___ to go out somewhere on Saturday night.» | I don't go / I always try | I'm not going / I'm always trying | Cả hai vế nói về thói quen chung nên dùng đơn. Không có ý phàn nàn nên không dùng `always` + tiếp diễn.",
        "No, the train ( ) at Cirencester on Saturdays. | does stop | is stopping | `on Saturdays` = lịch cố định; `does stop` nhấn mạnh để đính chính lại câu trước (xem thẻ nhấn mạnh với do/does).",
        "My mum ( ) part in ice-skating competitions almost every weekend. | takes | is taking | `almost every weekend` = thói quen → đơn. `take part in` là cụm cố định.",
    ]),
    (1, "B", B2 + " · bài B (trang 8)", "Sửa cho đúng (gõ lại)", "Câu gốc đang sai ở phần in đậm. Gõ phần thay thế đúng. Cách làm: hỏi trước 'người nói muốn nói gì?', rồi mới chọn thì.", "typed", [
        "My dad ( ㉠ ) late on Saturday mornings. | often gets up | Thói quen → đơn. `often` đứng trước động từ chính, nên không đi với `is getting up`.",
        "( ㉠ ) any other languages apart from English? | Do you speak | Câu hỏi hiện tại đơn dùng `Do`. `speak` là động từ nguyên thể.",
        "( ㉠ ) all my Christmas presents and it's only October! | I've already bought;I have already bought | Việc xong, kết quả còn liên quan tới bây giờ, không nói mốc thời gian → hiện tại hoàn thành. `already` đứng giữa `have` và V3.",
        "It's the first time ( ㉠ ) a party at home. | I've ever had;I have ever had | Mẫu `It's the first time + have/has + V3`: luôn dùng hiện tại hoàn thành, không dùng `I'm having`.",
        "Actually, I think Darren ( ㉠ ) quite hard sometimes. | works;does work | `Actually` là đính chính nên có thể dùng `does work` để nhấn mạnh. Sau `does` là nguyên thể, không thêm -s (`does works` sai).",
        "Carlo ( ㉠ ) Chinese food before. | has never eaten;has not eaten;hasn't eaten | `before` = từ trước tới giờ → hiện tại hoàn thành, `never` đứng giữa `has` và V3.",
        "Sean ( ㉠ ) a table for tonight. | has already booked;has booked already;'s already booked | Việc đã xong, kết quả liên quan tối nay → hiện tại hoàn thành. Dùng `already`, không dùng đơn `already books`.",
        "( ㉠ ) any help painting her new flat? | Does Melanie need | `need` là động từ trạng thái, không dùng tiếp diễn. Câu hỏi mượn `Does`, chủ ngữ ở sau.",
    ]),
    # ---------------------------------------------------------------- day 2
    (2, "G", B2 + " · bài G (trang 9)", "Nối để thành câu", "Mỗi vế đầu có hai dạng gần nhau (think/thinking, look/looking, have/having, be/being). Chọn vế sau khớp với nghĩa của động từ.", "choice", [
        "«I think ...» nối với phần nào? | I'm going to buy the new Racetrack CD. | of getting Dad a CD for his birthday. | darker hair than her sister. | like he needs a holiday! | `think` = ý kiến (trạng thái) → đơn: «I think I'm going to buy…». Phần `of getting` chỉ đi với `thinking of`.",
        "«I'm thinking ...» nối với phần nào? | of getting Dad a CD for his birthday. | I'm going to buy the new Racetrack CD. | not old enough to drive a car. | very annoying at the moment! | `thinking` = đang cân nhắc, ý nghĩ đang diễn ra → tiếp diễn, và `think of + V-ing`.",
        "«Phil's looking ...» nối với phần nào? | for his glasses. Have you seen them? | a haircut at the moment. | like he needs a holiday! | darker hair than her sister. | `look for` = đi tìm (hành động đang làm). Không nhầm với `look like` = trông như.",
        "«Phil looks ...» nối với phần nào? | like he needs a holiday! | for his glasses. Have you seen them? | darker hair than her sister. | not old enough to drive a car. | `looks like` = vẻ ngoài (trạng thái) → đơn.",
        "«Claire has ...» nối với phần nào? | darker hair than her sister. | a haircut at the moment. | like he needs a holiday! | of getting Dad a CD for his birthday. | `have` = sở hữu/đặc điểm (trạng thái) → không dùng tiếp diễn.",
        "«Claire is having ...» nối với phần nào? | a haircut at the moment. | darker hair than her sister. | for his glasses. Have you seen them? | like he needs a holiday! | `have a haircut` = trải nghiệm/hành động đang diễn ra → tiếp diễn được. Khác `has` = sở hữu.",
        "«Andy is ...» nối với phần nào? | not old enough to drive a car. | very annoying at the moment! | a haircut at the moment. | like he needs a holiday! | `is` + tính từ = trạng thái hiện tại bình thường (một sự thật về tuổi).",
        "«Andy is being ...» nối với phần nào? | very annoying at the moment! | not old enough to drive a car. | darker hair than her sister. | of getting Dad a CD for his birthday. | `be` ở tiếp diễn = cư xử như thế trong lúc này, chỉ tạm thời: `is being annoying` ≠ `is annoying` (tính cách).",
    ]),
    (2, "F", B2 + " · bài F (trang 10)", "Điền động từ: Ancient aviators?", "Đoạn văn về các đường vẽ ở sa mạc Nazca. Chín chỗ trống dùng các động từ be, disagree, do, include, know, look, see, seem, understand. Hỏi từng chỗ: đây là trạng thái hay hành động?", "typed", [
        "Everyone ( ㉠ ) that humans have been flying for only a few hundred years. | knows | `know` là động từ trạng thái. Chủ ngữ `Everyone` là ngôi thứ ba số ít nên có -s.",
        "But ( ㉠ ) it possible that ancient civilizations also had the ability and technology to fly? | is | Câu hỏi đảo: `Is it possible…?`. `be` ở đây là trạng thái.",
        "On the ground, they just ( ㉠ ) like straight lines. | look | `look like` = trông như (vẻ ngoài, trạng thái). Chủ ngữ `they` nên không có -s.",
        "But when you ( ㉠ ) them from the air, you understand exactly what they are. | see | `see` = nhìn thấy; sau `when` dùng hiện tại đơn.",
        "But when you see them from the air, you ( ㉠ ) exactly what they are. | understand;know;see | `understand` là động từ trạng thái (tư duy) → đơn. Sách chấp nhận cả `know` và `see`.",
        "The pictures ( ㉠ ) animals, birds and symbols. | include | `include` = bao gồm (quan hệ giữa các vật), động từ trạng thái → đơn.",
        "One bizarre theory, which most mainstream scientists ( ㉠ ) with, is that the people flew above the lines in balloons. | disagree | `disagree` = ý kiến, trạng thái. Chủ ngữ số nhiều nên không có -s.",
        "It ( ㉠ ) incredible, but a few people do believe it's possible. | seems | `seem` = vẻ ngoài, trạng thái. Chủ ngữ `It` nên có -s.",
        "It seems incredible, but a few people ( ㉠ ) believe it's possible. | do | Nhấn mạnh với `do`: trái với điều vừa nói («có vẻ khó tin, nhưng vài người vẫn tin»). Sau `do` là nguyên thể `believe`.",
    ]),
    (2, "C1", G65 + " · bài C1 (trang 4)", "Chọn vế sau đúng", "Hai vế sau khác nhau ở ý: một vế nói thói quen hoặc sự thật, một vế nói việc tạm thời hoặc đang xảy ra. Chọn vế khớp với động từ.", "choice", [
        "«Fiona is watching television ...» | because her favourite film star is on. | when she has time. | Tiếp diễn = đang xem lúc này, vì có lý do cụ thể. Vế `when she has time` đi với thói quen (đơn).",
        "«I'm having my lunch ...» | early today as I have an appointment. | at one o'clock every day. | Tiếp diễn = tạm thời, hôm nay khác thường. `every day` đi với đơn (`I have my lunch`).",
        "«I do the shopping ...» | at the same time every week. | today for a friend who's ill. | Đơn = thói quen cố định. Vế `today for a friend who's ill` cần `I'm doing`.",
        "«What are you doing ...» | to your sister? Leave her alone! | to your sister when she behaves badly? | Tiếp diễn = đang làm ngay bây giờ (`Leave her alone!`). Hỏi về thói quen phải là `What do you do…`.",
        "«I wear casual clothes ...» | at the weekend. | because we're having a party at lunchtime. | Đơn = thói quen. Vế sau với `because we're having a party` cần `I'm wearing` (tạm thời).",
        "«Teachers work hard ...» | but they get long holidays. | to get the concert ready for next week. | Đơn = sự thật chung về nghề giáo viên. Vế `to get the concert ready for next week` nói một việc tạm thời, cần `are working`.",
        "«The company's financial situation is improving ...» | now that it has a new Chief Executive. | when there is greater demand for its products. | Tiếp diễn = xu hướng đang thay đổi, `now that…` chỉ lý do mới xuất hiện. `when…` đi với sự thật chung.",
        "«Serge is thinking of retiring early ...» | because he isn't happy at work any more. | every time something bad happens at work. | `is thinking of` = đang cân nhắc, tạm thời. `every time…` đi với thói quen.",
    ]),
    (2, "C2", G65 + " · bài C2 (trang 4)", "Chia động từ trong ngoặc", "Gõ dạng đúng của động từ (có thể gồm cả trợ động từ). Với mỗi câu, hỏi: đây là thói quen/sự thật, hay việc tạm thời/đang làm?", "typed", [
        "My tutor ( ㉠ ) (see) me for a tutorial every Monday at two o'clock. | sees | `every Monday` = thói quen → đơn. Ngôi thứ ba nên có -s.",
        "John ( ㉠ ) (not/study) very hard at the moment. | isn't studying;is not studying | `at the moment` = tạm thời → tiếp diễn phủ định.",
        "John isn't studying very hard at the moment. I ( ㉠ ) (not/think) he'll pass his exams. | don't think;do not think | `think` ở nghĩa ý kiến là động từ trạng thái → đơn. Phủ định mượn `do`.",
        "'What ( ㉠ ) (he/do)?' 'He's trying to fix the television aerial.' | is he doing;'s he doing | Hỏi về việc đang xảy ra → tiếp diễn. Câu hỏi đảo `is he doing`.",
        "'What is he doing?' 'He ( ㉠ ) (try) to fix the television aerial.' | is trying;'s trying | Việc đang diễn ra lúc nói → tiếp diễn.",
        "Animals ( ㉠ ) (breathe in) oxygen and give out carbon dioxide. | breathe in | Sự thật khoa học → đơn. Chủ ngữ số nhiều nên không có -s.",
        "Animals breathe in oxygen and ( ㉠ ) (give out) carbon dioxide. | give out | Sự thật khoa học → đơn.",
        "Be quiet! I ( ㉠ ) (want) to hear the news. | want | `want` là động từ trạng thái → luôn đơn, kể cả khi việc đang xảy ra (không nói `am wanting`).",
        "In my country we ( ㉠ ) (drive) on the right-hand side of the road. | drive | Quy tắc cố định, sự thật chung → đơn.",
        "My friend Joe's parents ( ㉠ ) (travel) round the world this summer, and probably won't be back for a couple of months. | are travelling;are traveling;'re travelling;'re traveling | `this summer` + sẽ vắng lâu = tạm thời → tiếp diễn.",
        "The college ( ㉠ ) (run) the same course every year. | runs | `every year` = thói quen lặp lại → đơn. Chủ ngữ số ít nên có -s.",
        "Numbers of wild butterflies ( ㉠ ) (fall) as a result of changes in farming methods. | are falling | Xu hướng đang thay đổi → tiếp diễn. Dạng viết Task 1 quen dùng.",
    ]),
    (2, "C3", G65 + " · bài C3 (trang 5)", "Điền động từ trong khung: năng lượng", "Đoạn văn về năng lượng. Tám chỗ trống dùng agree, catch up, cause, have, go up, know, think, use. Chọn thì đúng cho từng chỗ.", "typed", [
        "We ( ㉠ ) energy for three main things: electricity production, heating and transport. | use | Sự thật chung → đơn. (Ví dụ của sách.)",
        "For the first two, we ( ㉠ ) options such as solar and wind power, or natural gas. | have | `have` = sở hữu (trạng thái) → đơn, không dùng `are having`.",
        "In China, domestic energy consumption ( ㉠ ) year by year. | is going up | `year by year` cho biết đây là thay đổi dần theo thời gian → tiếp diễn.",
        "In similar regions, demand ( ㉠ ) fast. | is catching up | Cũng là thay đổi đang diễn ra → tiếp diễn.",
        "We ( ㉠ ) how to use energy more efficiently now than in the past. | know | `know` là động từ trạng thái → đơn.",
        "The worldwide rise in demand and the rate of global warming ( ㉠ ) great concern amongst experts. | is causing | Hiện tượng đang diễn ra, ảnh hưởng ngay lúc này → tiếp diễn (dạng rút gọn `'s causing` cũng được).",
        "Some scientists ( ㉠ ) that the climate crisis is so serious that we are already too late to save the planet. | think | `think` = ý kiến → đơn.",
        "However, most experts ( ㉠ ) that it is essential to increase the use of renewable energy. | agree | `agree` là động từ trạng thái (tư duy) → đơn.",
    ]),
    # ---------------------------------------------------------------- day 3
    (3, "C", B2 + " · bài C (trang 8)", "Chia động từ: hiện tại hoàn thành", "Gõ dạng đúng. Hoàn thành đơn = đã xong/kết quả; hoàn thành tiếp diễn = làm liên tục đến giờ, nhấn vào quá trình.", "typed", [
        "It's the first time ( ㉠ ) (I / ever / eat) octopus! | I've ever eaten;I have ever eaten | Mẫu `It's the first time + have + V3`. `ever` đứng giữa `have` và V3.",
        "Sandy ( ㉠ ) (not / see) his sister since she went to university. | hasn't seen;has not seen | `since` + mốc quá khứ → hoàn thành. `see` là động từ trạng thái nên không dùng tiếp diễn.",
        "They ( ㉠ ) (go) on holiday to Spain and won't be back until the end of the month. | have gone;'ve gone | `have gone` = đã đi và đang ở đó. `have been` là đã đi và đã về. Câu có `won't be back` nên dùng `gone`.",
        "Poor Tracy! She ( ㉠ ) (write) that essay for hours now and she still hasn't finished! | has been writing;'s been writing | `for hours now` + chưa xong, nhấn vào quá trình → hoàn thành tiếp diễn.",
        "( ㉠ ) (you / ever / meet) anyone famous? | Have you ever met | Kinh nghiệm cho tới giờ, không nói thời điểm → hoàn thành đơn. Không dùng tiếp diễn với `ever`.",
        "( ㉠ ) (I / try) to get in touch with Jenny all morning but I can't find her anywhere. | I've been trying;I have been trying | `all morning` + cố liên tục, nhấn vào nỗ lực → hoàn thành tiếp diễn.",
        "( ㉠ ) (I / not finish) the book yet so I can't tell you what happens. | I haven't finished;I have not finished | `yet` đi với hoàn thành đơn. Chưa xong nên không dùng tiếp diễn.",
        "( ㉠ ) (you / already / decide) where you're going this summer? | Have you already decided | Kết quả của một quyết định, liên quan tới bây giờ → hoàn thành đơn. `already` đứng giữa.",
        "( ㉠ ) (We / live) here for the last six years. | We've lived;We have lived;We've been living;We have been living | `for the last six years` → cả hai dạng được. `live` là việc kéo dài nên gần như không khác nghĩa.",
        "( ㉠ ) (I / never / hear) such nonsense! | I've never heard;I have never heard | Kinh nghiệm cho tới giờ → hoàn thành đơn. `never` đứng giữa `have` và V3; không dùng tiếp diễn với `never`.",
    ]),
    (3, "D", B2 + " · bài D (trang 9)", "Điền từ trong khung: dấu hiệu của hoàn thành", "Mỗi chỗ trống một từ trong khung: already, before, ever, for, just, rarely, since, so, still, yet. Chú ý từ đứng ở đâu trong câu.", "typed", [
        "Have you ( ㉠ ) dreamt of winning the lottery? | ever | `ever` dùng trong câu hỏi về kinh nghiệm, đứng giữa chủ ngữ và V3.",
        "I haven't worked out how to set the timer on the video ( ㉠ ). | yet | `yet` ở cuối câu phủ định hoặc câu hỏi: đến giờ vẫn chưa.",
        "My dad's lived in the same house ( ㉠ ) he was born. | since | `since` + mốc thời gian hoặc một mệnh đề quá khứ.",
        "The film's only been on ( ㉠ ) a couple of minutes. | for | `for` + khoảng thời gian.",
        "Bruce has knocked three men out of the competition ( ㉠ ) far. | so | Cụm cố định `so far` = cho đến giờ.",
        "I ( ㉠ ) get the chance to get any exercise — I'm just too busy. | rarely | `rarely` là trạng từ tần suất của hiện tại đơn, đứng trước động từ chính.",
        "He's only ( ㉠ ) got home. | just | `just` = vừa mới, đứng giữa `has` và V3.",
        "It's eleven o'clock and Todd ( ㉠ ) hasn't come home. Where could he be? | still | `still` đứng trước `hasn't`: tới giờ vẫn chưa, người nói ngạc nhiên.",
        "I've never met Ruth ( ㉠ ). What's she like? | before | `before` ở cuối câu: trước giờ chưa gặp.",
        "Have you finished ( ㉠ )? That was quick! | already | `already` ở cuối câu hỏi diễn tả ngạc nhiên vì xong sớm.",
    ]),
    # ---------------------------------------------------------------- day 4
    (4, "E", B2 + " · bài E (trang 9)", "Chọn đáp án đúng (trộn bốn thì)", "Trộn cả bốn thì hiện tại. Trước khi chọn, hỏi: việc này là thói quen/sự thật, tạm thời, đã xong với kết quả bây giờ, hay làm liên tục đến giờ?", "choice", [
        "Ian ( ) a shower at the moment, so could you call back in about half an hour? | is taking | takes | has taken | has been taking | `at the moment` = đang xảy ra → tiếp diễn.",
        "( ) to Ipswich before? | Have you ever been | Do you ever go | Are you ever going | Have you ever been going | `before` + kinh nghiệm → hoàn thành đơn. Không dùng tiếp diễn với `ever`.",
        "I ( ) to all the local newspapers and TV stations to complain. | have already written | already write | already writing | have already been writing | Việc đã xong, kết quả liên quan bây giờ → hoàn thành đơn. `already` đứng giữa.",
        "( ) TV for the last four hours? Turn it off and get some exercise! | Have you been watching | Do you watch | Are you watching | Watched you | `for the last four hours` + phàn nàn về việc kéo dài → hoàn thành tiếp diễn.",
        "( ) hockey competitively or just for fun? | do you usually play | are you usually playing | have you usually played | have you usually been playing | `usually` = thói quen → hiện tại đơn.",
        "That's the first time ( ) an answer right today! | I have got | I get | I am getting | I have been getting | Mẫu `That's the first time + have + V3`.",
        "Jessica has ( ) left, I'm afraid. | already | yet | still | so far | `already` đứng giữa `has` và V3. `yet` ở cuối câu phủ định hoặc câu hỏi.",
        "Dan ( ) in the living room while we redecorate his bedroom. | is sleeping | sleeps | has slept | does sleep | `while we redecorate` = tạm thời → tiếp diễn.",
        "Unfortunately, Simone ( ) a day off very often. | doesn't get | isn't getting | hasn't got | hasn't been getting | `very often` = thói quen → đơn.",
        "Actually, I ( ) a cup of tea first thing every morning but then I switch to coffee. | do drink | am drinking | have drunk | have been drinking | `Actually` đính chính + `every morning`: `do drink` nhấn mạnh thói quen.",
    ]),
    (4, "H", B2 + " · bài H (trang 10)", "Tìm từ thừa: International friends", "Mỗi dòng của đoạn văn có đúng một từ thừa (chưa kể từ bị thừa ở dòng khác). Chọn từ thừa trong dòng được hỏi.", "choice", [
        "Dòng 1: «I've been to travelling round Europe all summer. It's the first time I've» | to | been | travelling | summer | Sửa: «I've been travelling round Europe all summer». `to` thừa.",
        "Dòng 2: «ever been going abroad, and I've had a fantastic time! I've seen» | going | ever | abroad | been | Sau `It's the first time I've ever been` là `abroad`: `been going` sai.",
        "Dòng 3: «loads of interesting places and I have to also made loads of new friends.» | to | also | made | loads | Sửa: «I have also made loads of new friends». `to` thừa.",
        "Dòng 4: «I've been decided to stay in touch with them now I'm back. One of» | been | decided | stay | now | Sửa: «I've decided to stay in touch». `been` thừa.",
        "Dòng 5: «them, Giselle, is French. She was making on holiday too. We now send» | making | French | holiday | now | Sửa: «She was on holiday too». `making` thừa.",
        "Dòng 6: «text messages are to each other all the time. They're usually in English» | are | text | each | usually | Sửa: «We now send text messages to each other». `are` thừa.",
        "Dòng 7: «because my French isn't very good! I'm planning to have visit her in» | have | planning | visit | good | Sửa: «I'm planning to visit her». `have` thừa.",
        "Dòng 8: «France next year sometime. I hope I can. I am love meeting people from» | am | hope | can | love | Sửa: «I love meeting people». `love` là động từ trạng thái, không đi với `am`.",
        "Dòng 9: «other countries! I want to have had lots of friends from all over the world!» | had | want | lots | friends | Sửa: «I want to have lots of friends». `had` thừa.",
        "Dòng 10: «Travelling certainly broadens the mind but it also is broadens your circle of» | is | also | broadens | circle | Sửa: «it also broadens your circle of friends». `is` thừa.",
    ]),
    (4, "I", B2 + " · bài I (trang 11)", "Mỗi chỗ trống một từ: Holiday Blues", "Đoạn hội thoại giữa Sheila, Matt và Alison trong lúc chờ tàu. Gõ một từ cho mỗi chỗ trống.", "typed", [
        "'You've ( ㉠ ) looking at that timetable for the last ten minutes. It can't be that confusing!' said Sheila angrily. | been | `have been looking` = hoàn thành tiếp diễn: nhìn liên tục mười phút nay.",
        "'I ( ㉠ ) wish you'd be quiet! I've got a splitting headache thanks to you!' replied Matt. | do;really | Nhấn mạnh cảm xúc: `I do wish` hoặc `I really wish`.",
        "'I do wish you'd be quiet! I've ( ㉠ ) a splitting headache thanks to you!' | got | `I've got` = đang có (sở hữu/trạng thái), dùng nhiều trong tiếng Anh Anh.",
        "'Mum! Dad! Please!' said Alison. 'You're both ( ㉠ ) very silly.' | being | `be` ở tiếp diễn = cư xử như thế lúc này, chỉ tạm thời.",
        "( ㉠ ) is no point at all in blaming each other. | There | Cấu trúc `There is no point in + V-ing`.",
        "'You ( ㉠ ) quite right, darling. I am sorry,' said Sheila. | are | `be` ở hiện tại đơn, ngôi `you`.",
        "'You are quite right, darling. I ( ㉠ ) sorry,' said Sheila. | am;'m | `be` ở hiện tại đơn, ngôi `I`.",
        "Well, it ( ㉠ ) like we have definitely missed the last train today. | looks;seems | `look/seem like` = trông như; động từ trạng thái nên chia đơn.",
        "Well, it looks like we ( ㉠ ) definitely missed the last train today. | have | Hoàn thành đơn: bây giờ đã lỡ tàu cuối. `definitely` đứng giữa `have` và V3.",
        "'I ( ㉠ ) so,' said Sheila. 'I mean, it did leave at 18.20.' | think | `think` = ý kiến → đơn. Câu trả lời ngắn: `I think so`.",
        "'Well, one thing is ( ㉠ ) in doubt,' said Matt. | not | Cụm `not in doubt` = chắc chắn.",
        "'This is the worst holiday we've ( ㉠ ) been on,' said Matt. | ever | Mẫu `the worst/best… + have ever + V3`.",
    ]),
    (4, "J", B2 + " · bài J (trang 11)", "Viết lại câu với từ cho sẵn", "Điền từ hai đến năm chữ để câu thứ hai có nghĩa như câu thứ nhất, bắt buộc dùng từ cho sẵn (viết hoa trong ngoặc ở đề bài).", "typed", [
        "What's the price of the tickets, Jimmy? (từ cho sẵn: much) → How ( ㉠ ), Jimmy? | much do the tickets cost;much are the tickets | Hỏi giá: `How much do the tickets cost?` hoặc `How much are the tickets?`.",
        "Are these your trainers? (từ cho sẵn: to) → Do ( ㉠ ) you? | these trainers belong to | `belong to` là động từ trạng thái, chỉ chia đơn.",
        "Sasha's not keen on team sports at all. (từ cho sẵn: like) → Sasha ( ㉠ ) team sports at all. | does not like;doesn't like | `not keen on` = không thích → `doesn't like`.",
        "It's only her second time in a recording studio. (từ cho sẵn: been) → She ( ㉠ ) in a recording studio once before. | has only been | Mẫu `It's the second time` ↔ `has only been … once before`.",
        "We got here three hours ago. (từ cho sẵn: have) → We ( ㉠ ) three hours. | have been here for;have been here | Đã đến cách đây ba giờ và vẫn ở đây → hoàn thành đơn với `for` + khoảng thời gian.",
        "I started writing this two hours ago and it's still not right. (từ cho sẵn: writing) → I ( ㉠ ) hours and it's still not right. | have been writing this for | Làm liên tục đến giờ, nhấn vào quá trình → hoàn thành tiếp diễn.",
        "This is my first experience of flying alone. (từ cho sẵn: time) → It is the first ( ㉠ ) alone. | time I have flown;time I've flown | Mẫu `It's the first time + have + V3`.",
        "Sharon's in the bath at the moment. (từ cho sẵn: a) → Sharon ( ㉠ ) at the moment. | is having a bath | `have a bath` = hành động đang diễn ra → tiếp diễn.",
        "Paul enjoys surprises apart from on his birthday. (từ cho sẵn: does) → Paul ( ㉠ ) surprises, just not on his birthday! | does enjoy | Nhấn mạnh với `does` + nguyên thể.",
    ]),
    (4, "C4", G65 + " · bài C4 (trang 5)", "Tìm động từ sai: biểu đồ và quy trình", "Hai đoạn trích có sáu động từ sai (một câu đã làm mẫu: «we are seeing» → «we can see»). Gõ dạng đúng của động từ trong câu.", "typed", [
        "From the graphs, we can see that the number of employees employed by this firm ( ㉠ ) each year. | is increasing | Số nhân viên thay đổi theo từng năm: xu hướng → tiếp diễn.",
        "...and the number of employees leaving after less than five years ( ㉠ ). | is decreasing | Cũng là xu hướng thay đổi → tiếp diễn.",
        "The sun heats the ground. This ( ㉠ ) the air nearby and the warm air rises into the sky. | warms | Quy trình tự nhiên, sự thật chung → đơn. Mô tả quy trình thì dùng đơn cả đoạn.",
        "As the air ( ㉠ ), it becomes cooler and the water vapour inside it changes into droplets of water. | rises | Quy trình tự nhiên → đơn, không dùng `is rising`.",
        "...it becomes cooler and the water vapour inside it ( ㉠ ) into droplets of water. | changes | Chủ ngữ `the water vapour` số ít nên cần -s (lỗi hoà hợp chủ vị).",
    ]),
]

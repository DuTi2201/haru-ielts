"""Build app/seed/pronunciation/sounds.json.
Video ids/order = BBC Learning English "English Pronunciation Tips" (45 videos incl. intro) and
"Pronunciation Shadowing" (6). Words/pairs/sentences/tips are our own, written for Vietnamese learners.
Run: python3 scripts/pron/build_sounds.py"""
import json, pathlib

# (ipa, kind, videoId, words, minimal-pair (target word, contrast word) or None, sentence, tip_vi)
S = [
("ɪ","Nguyên âm ngắn","TNFKG0yvDx4",["bid","tip","minute","ship"],("ship","sheep"),"Six big fish sit in the little bin.","Âm ngắn, lưỡi thả lỏng, miệng chỉ hé. Đừng kéo dài như /iː/: ship khác sheep."),
("ʊ","Nguyên âm ngắn","eJ7dM_LU9t4",["foot","put","good","book"],("full","fool"),"The good cook put the book on the wood.","Âm ngắn, môi tròn nhẹ và thả lỏng. Đừng đọc thành /uː/: full khác fool."),
("ʌ","Nguyên âm ngắn","PZwKFFp7V50",["strut","mud","love","cup"],("cup","cap"),"My brother loves ugly mud under the sun.","Miệng mở vừa, âm ngắn và dứt khoát, hơi giống â/ă. Không đọc thành /ɒ/ hay /æ/."),
("ə","Nguyên âm yếu (schwa)","wg0P0oYkniE",["the","of","butter","about"],None,"The teacher spoke about a lot of different things.","Âm yếu nhất tiếng Anh, thả lỏng cả miệng, rất ngắn. Chỉ nằm ở âm tiết không nhấn: đọc nhanh, đừng đọc rõ như chữ viết."),
("æ","Nguyên âm ngắn","qVhaIHk88a8",["trap","stamp","back","bad"],("bad","bed"),"The black cat sat on a flat mat.","Hạ hàm, mở miệng rộng, nằm giữa a và e. Nếu đọc thành /e/ thì bad thành bed."),
("ɒ","Nguyên âm ngắn","MAk-XtHsyzM",["lot","odd","wash","hot"],("cot","caught"),"The doctor got a long, hot watch.","Âm Anh-Anh: môi tròn nhẹ, miệng mở, ngắn, gần với o tiếng Việt. Khác /ɔː/ ở độ dài."),
("iː","Nguyên âm dài","RZmGzSb-6OM",["fleece","sea","machine","seat"],("seat","sit"),"We need to eat green beans each week.","Âm dài, môi dẹt như đang cười, lưỡi cao. Giữ hơi: seat dài hơn sit."),
("e","Nguyên âm ngắn","hLN1cdSTDo8",["dress","head","bed","pen"],("pen","pan"),"Ten men went to the next red bed.","Gần với e tiếng Việt, ngắn và miệng mở vừa. Đừng mở to thành /æ/."),
("θ","Phụ âm vô thanh","b4Aj3k65HSo",["thin","think","path","three"],("think","sink"),"Three thin thieves thought about the path.","Đặt đầu lưỡi giữa hai hàm răng rồi thổi hơi, không rung cổ họng. Người Việt hay đọc thành /t/ hoặc /s/."),
("ɑː","Nguyên âm dài","uDHMuMQdBNw",["father","start","hard","car"],("heart","hat"),"My father parked the car far from the farm.","Âm dài, miệng mở to, lưỡi thấp ở phía sau. Giọng Anh không đọc r ở cuối âm tiết."),
("ɜː","Nguyên âm dài","zSJJWHymEPw",["nurse","stir","learn","bird"],("bird","bud"),"The girl heard her first word at work.","Âm dài, môi thả lỏng (không tròn), không đọc r. Giữ nguyên miệng suốt âm."),
("d","Phụ âm hữu thanh","qA5ZYC89oso",["did","dame","odd","ladder"],("day","they"),"Dad did a good deed on Monday.","Đầu lưỡi chạm lợi trên, có rung cổ họng. Ở cuối từ vẫn phải bật nhẹ âm /d/."),
("n","Phụ âm mũi","qkgucMjv4T0",["nice","funny","son","noon"],("no","low"),"Nine new nurses ran in the rain.","Đầu lưỡi chạm lợi trên, hơi thoát ra mũi. Ở cuối từ đừng nuốt thành /ŋ/: son khác song."),
("uː","Nguyên âm dài","mnKEGLuEzV4",["blue","two","goose","food"],("pool","pull"),"The blue moon rose soon after noon.","Âm dài, môi tròn và đẩy ra trước. Giữ hơi lâu hơn /ʊ/."),
("ɔː","Nguyên âm dài","KHllC40_u1Q",["law","north","war","door"],("caught","coat"),"The tall girl saw a horse in the north.","Âm dài, môi tròn, miệng mở vừa. Khác /ɒ/ ở độ dài và không đọc r ở cuối."),
("ð","Phụ âm hữu thanh","tu1t3Fn5Lw8",["this","other","smooth","mother"],("then","den"),"My brother and mother bathe this weather.","Giống /θ/ (lưỡi giữa hai hàm răng) nhưng có rung cổ họng. Đừng đọc thành /d/ hoặc /z/."),
("ʃ","Phụ âm vô thanh","NF92RdZC6wE",["ship","sure","national","fish"],("ship","sip"),"She wishes to wash the fresh fish.","Môi chu ra, lưỡi lùi lại, thổi hơi dài, không rung. Gần với x/s nặng của tiếng Việt, nhưng dài hơn."),
("m","Phụ âm mũi","0Te4Us8Tsv8",["hammer","mime","more","team"],("might","night"),"Mum made more jam for my mother.","Hai môi khép, hơi thoát ra mũi, có rung. Ở cuối từ giữ môi khép, đừng mở ra thành âm khác."),
("eɪ","Nguyên âm đôi","5FMPlqlFt9g",["face","day","break","late"],("late","let"),"Eight late trains came on Saturday.","Bắt đầu từ /e/ rồi trượt lên /ɪ/. Trượt rõ và đủ dài, đừng đọc thành một âm /e/ cụt."),
("p","Phụ âm vô thanh","AZRREr7DqqM",["pack","pan","pop","pen"],("pay","bay"),"Peter picked a pair of purple pens.","Hai môi bật hơi mạnh ở đầu từ, không rung. Đặt tay trước miệng: phải thấy hơi bật ra."),
("ɪə","Nguyên âm đôi","vC0h4S0YPJc",["near","hear","weary","beer"],("beer","bear"),"We hear the clear voice here every year.","Bắt đầu từ /ɪ/ rồi trượt về /ə/ ở cuối. Âm sau yếu và ngắn."),
("aʊ","Nguyên âm đôi","9WDnVMQIaTs",["mouth","now","fowl","house"],("now","no"),"How now, brown cow, out of the house?","Bắt đầu từ /a/ mở rộng rồi trượt về /ʊ/ với môi tròn dần."),
("dʒ","Phụ âm hữu thanh","0IeQmGdo7gQ",["judge","age","soldier","jam"],("jeep","cheap"),"The giant judge enjoyed orange jelly.","Bật rồi xì, có rung cổ họng, gần với gi tiếng Việt nhưng bật rõ hơn. Khác /tʃ/ ở chỗ có rung."),
("əʊ","Nguyên âm đôi","r1BRCG0P9C8",["boat","show","know","go"],("low","law"),"Joe won't show the old road home.","Bắt đầu từ /ə/ rồi trượt về /ʊ/ với môi tròn dần. Đừng đọc thành o đơn như /ɔː/."),
("eə","Nguyên âm đôi","0J7-5maJJIk",["square","fair","pair","care"],("care","car"),"Take care of the rare pair of chairs there.","Bắt đầu từ /e/ rồi trượt về /ə/. Không đọc r ở cuối từ."),
("ʊə","Nguyên âm đôi","nHSqluHrD-U",["tour","pure","cure","sure"],("tour","tore"),"The tourist was sure the cure was pure.","Bắt đầu từ /ʊ/ rồi trượt về /ə/. Nhiều người Anh hiện nay đọc một số từ (như sure) gần /ɔː/, nghe vẫn đúng."),
("aɪ","Nguyên âm đôi","Hb8COxAtl14",["price","high","try","time"],("right","rate"),"I might try to buy five nice kites.","Bắt đầu từ /a/ mở rồi trượt lên /ɪ/. Trượt đủ, đừng cắt ngang thành a."),
("tʃ","Phụ âm vô thanh","PykxZ5kkrjs",["teacher","match","church","chair"],("chair","share"),"The teacher chose cheap cheese for lunch.","Bật rồi xì, không rung, gần với ch tiếng Việt nhưng bật hơi mạnh hơn. Khác /dʒ/ ở chỗ không rung."),
("t","Phụ âm vô thanh","0T1QYByMxrs",["tin","button","get","ten"],("tie","die"),"Tom took ten tickets to the town.","Đầu lưỡi chạm lợi trên, bật hơi ở đầu từ (t tiếng Việt không bật hơi). Ở cuối từ vẫn phải có âm /t/."),
("ʒ","Phụ âm hữu thanh","bTxeAiBF61I",["pleasure","leisure","vision","measure"],None,"It is a pleasure to measure the television vision.","Giống /ʃ/ nhưng có rung cổ họng. Âm này ít khi đứng đầu từ, thường nằm giữa từ."),
("s","Phụ âm vô thanh","QtH3vRXmvvo",["soon","mister","hiss","bus"],("sip","ship"),"Sam sees six sad snakes in the sun.","Luồng hơi gió mảnh, đầu lưỡi gần lợi, không rung. Cuối từ phải đọc rõ (số nhiều, ngôi thứ ba -s)."),
("f","Phụ âm vô thanh","vE12RFyH-hY",["fat","coffee","fluff","fish"],("fan","van"),"Four friends found fifty fresh fish.","Răng trên chạm nhẹ môi dưới rồi thổi hơi, không rung. Đừng đọc thành /p/."),
("b","Phụ âm hữu thanh","yP7aCKO6bTE",["back","habit","job","big"],("ban","pan"),"Bob bought a big blue bag.","Hai môi bật, có rung cổ họng. Cuối từ vẫn phải khép môi cho /b/."),
("ɔɪ","Nguyên âm đôi","lFRrEI85IcM",["choice","noise","boy","coin"],("boy","buy"),"The boy enjoys the noisy toy.","Bắt đầu từ /ɔ/ môi tròn rồi trượt lên /ɪ/."),
("ŋ","Phụ âm mũi","rgWse3tloTw",["rung","anger","thanks","sing"],("sing","sin"),"The king is singing a long song.","Cuống lưỡi chạm ngạc mềm, hơi thoát ra mũi. Không thêm âm /g/ ở cuối: sing, song."),
("k","Phụ âm vô thanh","d1jyIpAmLe8",["came","lucky","sick","cake"],("cold","gold"),"Kate can cook a quick, cold cake.","Cuống lưỡi bật chạm ngạc mềm, bật hơi ở đầu từ, không rung. Cuối từ vẫn phải bật /k/."),
("r","Phụ âm","Lxuo14hjP_8",["right","wrong","sorry","red"],("right","light"),"Rita ran around the red road.","Cong nhẹ đầu lưỡi lên nhưng không chạm vòm miệng, môi hơi tròn. Không rung lưỡi như r tiếng Việt vùng miền."),
("v","Phụ âm hữu thanh","mO04G0v5a_c",["view","heavy","move","very"],("very","berry"),"Victor never leaves the village in winter.","Răng trên chạm môi dưới và có rung cổ họng. Không đọc thành /w/ hay /b/."),
("j","Phụ âm bán nguyên âm","_Fi9E6Yw-qg",["yet","use","beauty","yes"],("yes","less"),"Yesterday the young student used a yellow yo-yo.","Lưỡi trượt nhanh từ vị trí /ɪ/ sang âm sau, giống i lướt trong yêu. Không đọc thành /dʒ/."),
("w","Phụ âm bán nguyên âm","HzhPB1hXG-o",["wet","one","when","week"],("wet","vet"),"We went west for one wet week.","Môi tròn rồi mở ra nhanh, giống u lướt trong uể. Không để răng chạm môi như /v/."),
("g","Phụ âm hữu thanh","9eAqj9EfeK0",["get","giggle","ghost","bag"],("gold","cold"),"Greg got a good green bag.","Cuống lưỡi bật chạm ngạc mềm, có rung cổ họng. Cuối từ vẫn phải bật /g/."),
("l","Phụ âm","CwWLgmMk0Z0",["light","valley","feel","milk"],("light","right"),"Lily left the little lamp on the hill.","Đầu lưỡi chạm lợi trên và giữ ở đó. Cuối từ (feel, milk) lưỡi vẫn chạm lợi, đừng thả thành u."),
("z","Phụ âm hữu thanh","o1ZvmX80t7Q",["zero","music","roses","buzz"],("zoo","sue"),"The zebras at the zoo eat leaves and roses.","Giống /s/ nhưng có rung cổ họng (đặt tay lên cổ phải thấy rung). Quan trọng cho số nhiều: roses, dogs."),
("h","Phụ âm vô thanh","DM_gN6imoC8",["hot","whole","ahead","hand"],("hat","at"),"Harry hates hot hamburgers at home.","Chỉ là hơi thở từ cổ họng, không có tiếng xát mạnh. Đừng bỏ âm /h/ đầu từ."),
]
assert len(S) == 44, len(S)
INTRO = {"id": "fdRmGvmeY1U", "title": "Giới thiệu: cách dùng loạt video phát âm của BBC"}
SHADOW = [
 ("tjaLn7URdlA","Shadowing là gì?","Cách làm: nghe một cụm, nói theo gần như cùng lúc, bắt chước nhịp và ngữ điệu."),
 ("ywGo1GI9c2I","Hội thoại ở quán cà phê",""),
 ("Z5sjzG4ZF_w","Những điểm du lịch của George",""),
 ("RI4cxw5xecs","Ai lấy mất túi khoai chiên của tôi?",""),
 ("sAumTZ1lkZE","Hội thoại ở văn phòng",""),
 ("DR-aseNKM4A","Phát âm đuôi -ed",""),
]
out = {
 "source": "BBC Learning English (YouTube). Video được nhúng bằng trình phát chính thức của YouTube; nội dung luyện tập do Haru tự soạn.",
 "intro": INTRO,
 "sounds": [
  {"slug": f"s{i:02d}", "order": i, "ipa": ipa, "kind": kind, "video_id": vid,
   "words": words, "pair": list(pair) if pair else None, "sentence": sent, "tip_vi": tip}
  for i, (ipa, kind, vid, words, pair, sent, tip) in enumerate(S, 1)],
 "shadowing": [{"slug": f"sh{i}", "order": i, "video_id": v, "title_vi": t, "note_vi": n} for i, (v, t, n) in enumerate(SHADOW, 1)],
}
p = pathlib.Path(__file__).resolve().parents[2] / "app/seed/pronunciation/sounds.json"
p.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n")
print("wrote", p, len(out["sounds"]))

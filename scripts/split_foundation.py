"""One-off: cut the five Nền tảng lessons into sixteen short ones and put Buổi sáng and Việc nhà
between them (November 2026).

Nothing is added to or taken out of the course: every word, grammar card, practice question,
note and reading of a Nền tảng lesson lands in exactly one of its parts, unchanged. What is new is
per part: its title, summary, goal and study guide (coach), written from the cards it holds.

- a grammar card goes to the part listed in PARTS;
- a practice item goes to the LAST part among those teaching the patterns its questions are
  linked to (so a question never comes before what it tests); an item linked to no pattern of the
  lesson goes where most of its words are taught;
- a word goes to the FIRST part whose cards or practice use it (so it is met before or with the
  questions that need it); a word nobody uses goes with its family, else to the shortest part;
- the language notes go to the part named in PARTS; the lesson's readings (passages) to its last
  part, which holds all of its cards.

The first part keeps the lesson's slug (and so its database id: answers, essays and talks already
filed under it stay there). Parts 2+ are new slugs; the words, cards and answers that move to them
are moved in the database by app.services.lesson_seed.sync_lessons (`split_from`), so no learner
loses a schedule.

Run from the repository root: python scripts/split_foundation.py [--write]
Without --write it only prints the plan."""
from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.services import lesson_seed as ls

LESSONS = ROOT / "app/seed/lessons"
PASSAGES = ROOT / "app/seed/passages"

# ------------------------------------------------------------------------------------- the parts
# per Nền tảng lesson: its parts in order; "grammar" = indexes of the lesson's cards, "notes" =
# indexes of its language notes (note 0 is the goal, rewritten per part)
PARTS: dict[str, list[dict]] = {
    "sinh-hoat-00-nen-tang-1-gioi-thieu": [
        {
            "slug": "sinh-hoat-00-nen-tang-1-gioi-thieu",
            "title": "Nền tảng 1.1 · Tôi là…: 이에요/예요 & 은/는",
            "title_en": "기초 1-1: 저는 학생이에요",
            "summary": "Câu đầu tiên của tiếng Hàn: «A là B» với '이에요/예요', phủ định '이/가 아니에요', và trợ từ chủ đề '은/는' để nói về mình và người khác.",
            "grammar": [0, 1], "notes": [0, 1],
            "goal": [
                "Giới thiệu tên, quốc tịch, nghề của mình: `저는 투안이에요. 베트남 사람이에요.`",
                "Nói «không phải là»: `학생이 아니에요`, và đáp có/không với `네` / `아니요`.",
                "Chọn đúng `이에요` hay `예요`, `은` hay `는` theo patchim.",
            ],
            "coach": {
                "focus_vi": ["`N + 이에요/예요` và phủ định `N + 이/가 아니에요`.", "`은/는` để nêu người hay vật mình đang nói tới."],
                "watch_out_vi": ["Sau nguyên âm là `예요` (의사예요), sau patchim là `이에요` (학생이에요); không viết `의사에요`.", "Phủ định của `이다` là `아니에요`, không nói `안 + N이에요`."],
                "notebook_vi": ["3 câu giới thiệu bản thân: tên, quốc tịch, nghề."],
                "self_check": [{"prompt_vi": "Không nhìn bài, nói 3 câu về tên, quốc tịch và nghề của bạn, rồi 1 câu «không phải là»."}],
            },
        },
        {
            "slug": "sinh-hoat-00-nen-tang-1b-chi-dinh-so-huu",
            "title": "Nền tảng 1.2 · Cái này là gì?: 이/가, 이·그·저 & 의",
            "title_en": "기초 1-2: 이것은 뭐예요?",
            "summary": "Chỉ người và đồ vật với '이/그/저', trợ từ chủ ngữ '이/가' (khác '은/는' ở đâu), và sở hữu '의' ('제 책', '친구의 가방').",
            "grammar": [2, 3, 5], "notes": [],
            "goal": [
                "Hỏi và đáp về đồ vật: `이게 뭐예요?` — `그것은 제 책이에요.`",
                "Chọn `이/그/저` theo khoảng cách tới người nói và người nghe.",
                "Phân biệt `은/는` với `이/가`, nói «của ai» bằng `의` và `제`.",
            ],
            "coach": {
                "focus_vi": ["`이/그/저 + N`, `이것/그것/저것`, `여기/거기/저기`.", "`N + 이/가` và `N + 의`."],
                "watch_out_vi": ["`은/는` nêu chủ đề hoặc đối chiếu; `이/가` đưa ra thông tin hoặc chủ ngữ mới.", "«Của tôi» là `제` (= `저의`), «của bạn ấy» là `친구의`; khi nói `의` thường đọc [에]."],
                "notebook_vi": ["Vẽ 3 đồ vật ở gần, giữa, xa; ghi `이것/그것/저것` dưới mỗi cái."],
                "self_check": [{"prompt_vi": "Chỉ 3 đồ vật quanh bạn, hỏi `이게 뭐예요?` rồi tự trả lời, có một câu dùng `제`."}],
            },
        },
        {
            "slug": "sinh-hoat-00-nen-tang-1c-cau-hoi",
            "title": "Nền tảng 1.3 · Hỏi đáp: từ để hỏi & tên gọi",
            "title_en": "기초 1-3: 누구예요? 어디예요?",
            "summary": "Mười từ để hỏi ('누구', '뭐', '어디', '언제', '왜', '어떻게', '무슨', '어느', '몇', '얼마') và cách nói tên gọi '(이)라고 하다'; ghép cả bài thành đoạn tự giới thiệu.",
            "grammar": [4, 6], "notes": [],
            "goal": [
                "Hỏi thông tin bằng mười từ để hỏi và đáp đủ câu.",
                "Nói tên mình, tên đồ vật bằng `(이)라고 해요`.",
                "Viết một đoạn tự giới thiệu ngắn dùng cả ba bài Nền tảng 1.",
            ],
            "coach": {
                "focus_vi": ["Mười từ để hỏi và vị trí của chúng trong câu.", "`N + (이)라고 하다`."],
                "watch_out_vi": ["`무슨` hỏi loại (무슨 음식), `어느` hỏi chọn trong nhóm (어느 나라); không dùng `몇` cho thứ trong tuần (`무슨 요일`).", "Từ để hỏi làm chủ ngữ đi với `이/가`: `누가`, không phải `누구는`."],
                "notebook_vi": ["Bảng 10 từ để hỏi (tự điền nghĩa).", "Đoạn 4–5 câu tự giới thiệu."],
                "self_check": [{"prompt_vi": "Hỏi người đối diện bằng `누구`, `뭐`, `어디`, rồi tự giới thiệu bằng `(이)라고 해요`."}],
            },
        },
    ],
    "sinh-hoat-00-nen-tang-2-noi-chon": [
        {
            "slug": "sinh-hoat-00-nen-tang-2-noi-chon",
            "title": "Nền tảng 2.1 · Làm gì?: chia -아/어요 & 을/를",
            "title_en": "기초 2-1: 밥을 먹어요",
            "summary": "Cách chia động từ, tính từ sang đuôi lịch sự '-아/어요' (kể cả '하다' và gốc 'ㅡ') và trợ từ tân ngữ '을/를': câu đầu tiên có hành động.",
            "grammar": [0, 1], "notes": [0],
            "goal": [
                "Chia đúng `-아/어요` trong ba bước, kể cả `하다 → 해요` và gốc `ㅡ` (`써요`, `바빠요`).",
                "Nói ai làm gì với cái gì: `저는 밥을 먹어요`.",
            ],
            "coach": {
                "focus_vi": ["Chia `-아/어요`: bỏ `-다`, nhìn nguyên âm cuối của gốc, gộp nguyên âm.", "`N + 을/를` cho tân ngữ."],
                "watch_out_vi": ["`ㅏ/ㅗ` → `-아요`, nguyên âm khác → `-어요`, `하다` → `해요`.", "Sau patchim là `을` (밥을), sau nguyên âm là `를` (커피를)."],
                "notebook_vi": ["Bảng động từ → dạng `-아/어요` (tự điền 10 động từ)."],
                "self_check": [{"prompt_vi": "Chia `가다`, `먹다`, `마시다`, `공부하다`, `쓰다` sang `-아/어요`.", "answer": "가요 · 먹어요 · 마셔요 · 공부해요 · 써요"}],
            },
        },
        {
            "slug": "sinh-hoat-00-nen-tang-2b-o-dau",
            "title": "Nền tảng 2.2 · Ở đâu?: 있다/없다, 에 & 에서",
            "title_en": "기초 2-2: 어디에 있어요?",
            "summary": "Có và không có ('있다', '없다'), nơi tồn tại và đích đến với '에', nơi diễn ra hành động với '에서': hai trợ từ người học hay nhầm nhất.",
            "grammar": [2, 3, 4], "notes": [],
            "goal": [
                "Nói cái gì có ở đâu: `가방에 책이 있어요`.",
                "Nói đi đâu (`학교에 가요`) và làm gì ở đâu (`도서관에서 공부해요`).",
                "Chọn đúng `에` hay `에서` cho từng câu.",
            ],
            "coach": {
                "focus_vi": ["`N이/가 있다·없다` và `N에 있다·없다`.", "Phân biệt `에` với `에서`."],
                "watch_out_vi": ["`에` chỉ đích đến hoặc nơi tồn tại (với `있다/없다`); `에서` chỉ nơi hành động diễn ra hoặc điểm xuất phát."],
                "notebook_vi": ["5 câu về nơi bạn hay đến, dùng `에` và `에서`."],
                "self_check": [{"prompt_vi": "Kể 3 việc bạn làm hôm nay ở 3 nơi khác nhau, và 1 thứ có trong túi bạn."}],
            },
        },
        {
            "slug": "sinh-hoat-00-nen-tang-2c-cung-chi-va",
            "title": "Nền tảng 2.3 · Cũng, chỉ, và: 도, 만 & 와/과",
            "title_en": "기초 2-3: 저도 커피만 마셔요",
            "summary": "Ba trợ từ thêm ý cho câu: '도' (cũng), '만' (chỉ), '와/과 · 하고 · (이)랑' (và, cùng với); ghép cả Nền tảng 2 thành đoạn kể một ngày.",
            "grammar": [5, 6, 7], "notes": [1],
            "goal": [
                "Nói «cũng» và «chỉ»: `저도 학생이에요`, `커피만 마셔요`.",
                "Nói «và», «cùng với» theo mức trang trọng: `와/과`, `하고`, `(이)랑`.",
                "Viết 4–6 câu kể một ngày của bạn: ai làm gì, ở đâu, với ai.",
            ],
            "coach": {
                "focus_vi": ["`N + 도`, `N + 만`.", "`N + 와/과 · 하고 · (이)랑`."],
                "watch_out_vi": ["`도` và `만` thay chỗ `은/는`, `이/가`, `을/를`: `저도` (không `저는도`), `커피만` (không `커피를만`); nhưng giữ `에`, `에서`: `학교에도`.", "`와/과` trang trọng, văn viết; `하고`, `(이)랑` khi nói."],
                "notebook_vi": ["Đoạn 4–6 câu kể một ngày của bạn."],
                "self_check": [{"prompt_vi": "Nói 2 câu với `도`, 1 câu với `만` và 1 câu «tôi đi với bạn» bằng `하고`."}],
            },
        },
    ],
    "sinh-hoat-00-nen-tang-3-chia-dong-tu": [
        {
            "slug": "sinh-hoat-00-nen-tang-3-chia-dong-tu",
            "title": "Nền tảng 3.1 · Quá khứ & trang trọng: -았/었-, -ㅂ/습니다",
            "title_en": "기초 3-1: 과거와 합쇼체",
            "summary": "Thì quá khứ '-았/었-' (kể cả '였/이었어요' cho danh từ) và đuôi trang trọng '-ㅂ/습니다', '-ㅂ/습니까?'; ba mức lịch sự và khi nào dùng mức nào.",
            "grammar": [0, 1], "notes": [1],
            "goal": [
                "Kể việc đã làm: `어제 영화를 봤어요`, `학생이었어요`.",
                "Nói và viết câu trang trọng: `감사합니다`, `회사원입니다`, `어디에 갑니까?`.",
                "Giữ một mức lịch sự xuyên suốt một đoạn.",
            ],
            "coach": {
                "focus_vi": ["`V/A + -았/었-`, `N + 였/이었어요`.", "`V/A + -ㅂ/습니다 · -ㅂ/습니까?`."],
                "watch_out_vi": ["Quá khứ chia theo cùng quy tắc nguyên âm như `-아/어요`: `가 → 갔어요`, `마시 → 마셨어요`, `하 → 했어요`.", "Gốc có patchim → `-습니다` (먹습니다), không patchim → `-ㅂ니다` (갑니다); gốc `ㄹ` bỏ `ㄹ`: `삽니다`."],
                "notebook_vi": ["Bảng 5 động từ: hiện tại `-아/어요` · quá khứ · trang trọng."],
                "self_check": [{"prompt_vi": "Kể 3 việc bạn đã làm hôm qua, rồi nói lại một câu ở dạng `-ㅂ/습니다`."}],
            },
        },
        {
            "slug": "sinh-hoat-00-nen-tang-3b-phu-dinh",
            "title": "Nền tảng 3.2 · Không, không thể & sẽ: -지 않다, -지 못하다, -겠-",
            "title_en": "기초 3-2: 부정과 -겠-",
            "summary": "Phủ định dài '-지 않다' (không) và '-지 못하다' (không thể), cùng '-겠-' cho ý chí và các câu lịch sự cố định ('알겠습니다', '잘 먹겠습니다').",
            "grammar": [2, 3], "notes": [],
            "goal": [
                "Nói «không làm» và «không thể làm»: `가지 않아요`, `수영하지 못해요`.",
                "Dùng đúng `-겠-` trong `알겠습니다`, `잘 먹겠습니다`, `제가 하겠습니다`.",
            ],
            "coach": {
                "focus_vi": ["`V/A + -지 않다` · `V + -지 못하다`.", "`V/A + -겠-`."],
                "watch_out_vi": ["`-지 않다` là không muốn hoặc không làm; `-지 못하다` là muốn mà không làm được.", "Ngắn hơn khi nói: `안 가요`, `못 가요`; với `공부하다` thì `공부 안 해요`, không nói `안 공부해요`."],
                "notebook_vi": ["4 câu: 2 việc bạn không làm, 2 việc bạn không thể làm."],
                "self_check": [{"prompt_vi": "Đáp lại lời mời đi uống cà phê: một lần từ chối vì không muốn, một lần vì không thể."}],
            },
        },
        {
            "slug": "sinh-hoat-00-nen-tang-3c-bat-quy-tac-1",
            "title": "Nền tảng 3.3 · Bất quy tắc ㄷ, ㄹ & 르",
            "title_en": "기초 3-3: ㄷ·ㄹ·르 불규칙",
            "summary": "Ba nhóm bất quy tắc đầu: 'ㄷ → ㄹ' (듣다 → 들어요), 'ㄹ' rơi (살다 → 삽니다), '르 → ㄹ라/ㄹ러' (모르다 → 몰라요); kèm những từ trông giống mà KHÔNG bất quy tắc.",
            "grammar": [4, 5, 6], "notes": [0],
            "goal": [
                "Chia đúng `듣다`, `걷다`, `묻다`, `살다`, `알다`, `만들다`, `모르다`, `부르다`.",
                "Nhận ra từ không bất quy tắc dễ nhầm: `닫다`, `받다`.",
            ],
            "coach": {
                "focus_vi": ["Học theo nhóm, mỗi nhóm thuộc một động từ mẫu: `듣다`, `살다`, `모르다`."],
                "watch_out_vi": ["Không phải gốc nào có `ㄷ` cuối cũng bất quy tắc: `듣다 → 들어요` nhưng `받다 → 받아요`, `닫다 → 닫아요`.", "Biến đổi chỉ xảy ra trước nguyên âm; trước `-고`, `-지만`, `-습니다` thì giữ gốc (`듣고`, `모르고`)."],
                "notebook_vi": ["Bảng 3 nhóm × 1 động từ mẫu: dạng `-아/어요` và quá khứ."],
                "self_check": [{"prompt_vi": "Chia `듣다`, `살다`, `모르다` sang `-아/어요` và quá khứ.", "answer": "들어요/들었어요 · 살아요/살았어요 · 몰라요/몰랐어요"}],
            },
        },
        {
            "slug": "sinh-hoat-00-nen-tang-3d-bat-quy-tac-2",
            "title": "Nền tảng 3.4 · Bất quy tắc ㅎ, ㅅ & ㅂ",
            "title_en": "기초 3-4: ㅎ·ㅅ·ㅂ 불규칙",
            "summary": "Ba nhóm còn lại: 'ㅎ' rơi (그렇다 → 그래요, 파랗다 → 파래요), 'ㅅ' rơi (낫다 → 나아요), 'ㅂ → 우' (덥다 → 더워요, 돕다 → 도와요); đọc và viết lại cả Nền tảng 3.",
            "grammar": [7, 8, 9], "notes": [],
            "goal": [
                "Chia đúng `그렇다`, `어떻다`, `파랗다`, `낫다`, `짓다`, `덥다`, `춥다`, `어렵다`, `돕다`.",
                "Nhận ra từ không bất quy tắc dễ nhầm: `좋다`, `웃다`, `입다`, `좁다`.",
                "Đọc hiểu một đoạn có đủ quá khứ, trang trọng, phủ định và bất quy tắc.",
            ],
            "coach": {
                "focus_vi": ["Ba động từ mẫu: `그렇다`, `낫다`, `덥다`."],
                "watch_out_vi": ["`좋다 → 좋아요` không bất quy tắc dù có `ㅎ`; `입다 → 입어요`, `웃다 → 웃어요` cũng vậy.", "`돕다`, `곱다` thành `-와요` (도와요), các gốc `ㅂ` khác thành `-워요` (더워요)."],
                "notebook_vi": ["Hoàn thành bảng 6 nhóm bất quy tắc (3 nhóm bài trước + 3 nhóm bài này)."],
                "self_check": [{"prompt_vi": "Chia `그렇다`, `덥다`, `돕다`, `낫다` sang `-아/어요` và quá khứ.", "answer": "그래요/그랬어요 · 더워요/더웠어요 · 도와요/도왔어요 · 나아요/나았어요"}],
            },
        },
    ],
    "sinh-hoat-00-nen-tang-4-so-gio-ngay": [
        {
            "slug": "sinh-hoat-00-nen-tang-4-so-gio-ngay",
            "title": "Nền tảng 4.1 · Số Hán-Hàn: ngày tháng, phút, tiền",
            "title_en": "기초 4-1: 일, 이, 삼",
            "summary": "Hệ số Hán-Hàn ('일', '이', '삼'…) và các đơn vị đi với nó: năm, tháng, ngày, phút, tiền, tầng, số điện thoại; hai tháng đọc đặc biệt '유월', '시월'.",
            "grammar": [0], "notes": [0],
            "goal": [
                "Đếm và đọc số Hán-Hàn đến hàng chục nghìn: `만 오천 원`.",
                "Đọc ngày tháng theo thứ tự lớn → nhỏ: `이천이십육 년 시월 십 일`.",
                "Nói số điện thoại, số tầng, số phút.",
            ],
            "coach": {
                "focus_vi": ["Số Hán-Hàn + `년 · 월 · 일 · 분 · 원 · 층 · 번`."],
                "watch_out_vi": ["6월 = `유월`, 10월 = `시월`; `십육` đọc [심뉵].", "Tiền luôn dùng Hán-Hàn: không nói `다섯 원`."],
                "notebook_vi": ["Ngày sinh, số điện thoại và giá 3 món đồ, viết bằng chữ Hán-Hàn."],
                "self_check": [{"prompt_vi": "Đọc to ngày hôm nay và giá một ly cà phê."}],
            },
        },
        {
            "slug": "sinh-hoat-00-nen-tang-4b-so-thuan-han",
            "title": "Nền tảng 4.2 · Số thuần Hàn: giờ, tuổi, đếm đồ vật",
            "title_en": "기초 4-2: 하나, 둘, 셋",
            "summary": "Hệ số thuần Hàn ('하나', '둘', '셋'…), dạng rút gọn trước đơn vị đếm ('한', '두', '세', '네', '스무') và các đơn vị đi với nó: giờ, tuổi, cái, người, ly, quyển, con.",
            "grammar": [1], "notes": [1],
            "goal": [
                "Đếm đồ vật, người, tuổi bằng số thuần Hàn: `커피 두 잔`, `스무 살`.",
                "Nói giờ với cả hai hệ số: `세 시 십오 분`, `세 시 반`.",
            ],
            "coach": {
                "focus_vi": ["Số thuần Hàn + `시 · 개 · 명 · 살 · 잔 · 권 · 마리 · 번`."],
                "watch_out_vi": ["Trước đơn vị: `하나 → 한`, `둘 → 두`, `셋 → 세`, `넷 → 네`, `스물 → 스무`.", "Một giờ dùng cả hai hệ: `3시 10분` đọc là `세 시 십 분`; `두 시` là 2 giờ, `두 시간` là 2 tiếng."],
                "notebook_vi": ["Bảng đơn vị đếm → hệ số đi kèm (tự điền)."],
                "self_check": [{"prompt_vi": "Đọc to giờ bây giờ, tuổi của bạn và số người trong nhà."}],
            },
        },
        {
            "slug": "sinh-hoat-00-nen-tang-4c-hoi-dap-so",
            "title": "Nền tảng 4.3 · Mấy giờ, ngày mấy, bao nhiêu?",
            "title_en": "기초 4-3: 몇 시예요? 얼마예요?",
            "summary": "Hỏi và đáp về số: '몇 시', '며칠', '무슨 요일', '몇 살', '몇 명', '얼마'; thứ trong tuần, mốc thời gian có và không có '에'; nghe và hẹn giờ.",
            "grammar": [2], "notes": [],
            "goal": [
                "Hỏi và đáp đúng về giờ, ngày, thứ, tuổi, số người, giá.",
                "Dùng `에` với mốc thời gian cụ thể (`세 시에`, `월요일에`), bỏ `에` với `오늘`, `내일`, `지금`.",
                "Nghe được giờ hẹn, giá tiền trong một đoạn hội thoại.",
            ],
            "coach": {
                "focus_vi": ["`몇 시 · 며칠 · 무슨 요일 · 몇 살 · 몇 명 · 얼마`."],
                "watch_out_vi": ["Hỏi thứ là `무슨 요일`, không phải `몇 요일`; hỏi ngày là `며칠`, không phải `몇 일`.", "`오늘`, `어제`, `내일`, `지금`, `매일` không nhận `에`."],
                "notebook_vi": ["Lịch tuần của bạn: thứ, giờ, việc làm."],
                "self_check": [{"prompt_vi": "Hẹn một người bạn: hỏi ngày, thứ, giờ và nói chỗ gặp."}],
            },
        },
    ],
    "sinh-hoat-00-nen-tang-5-dinh-ngu": [
        {
            "slug": "sinh-hoat-00-nen-tang-5-dinh-ngu",
            "title": "Nền tảng 5.1 · Người đang đọc sách: -는 & tính từ -(으)ㄴ",
            "title_en": "기초 5-1: 책을 읽는 사람",
            "summary": "Gắn một mệnh đề vào TRƯỚC danh từ ở hiện tại: động từ '-는' ('읽는 사람'), tính từ '-(으)ㄴ' ('큰 가방', '작은 방'), '있다/없다' và 'N + 이다' ('맛있는', '학생인').",
            "grammar": [0], "notes": [0],
            "goal": [
                "Nói «người đang…», «thứ…» bằng `-는`: `커피를 마시는 사람`.",
                "Tả người, vật bằng tính từ đứng trước danh từ: `큰 가방`, `예쁜 옷`, `맛있는 음식`.",
            ],
            "coach": {
                "focus_vi": ["`V + -는 + N` · `A + -(으)ㄴ + N`."],
                "watch_out_vi": ["Nhìn từ loại trước: động từ hiện tại dùng `-는`, tính từ hiện tại dùng `-(으)ㄴ`; `있다/없다` dùng `-는` (맛있는).", "Gốc `ㄹ` bỏ `ㄹ`: `사는`, `긴`."],
                "notebook_vi": ["5 cụm «tính từ + danh từ» tả đồ vật trong phòng bạn."],
                "self_check": [{"prompt_vi": "Gộp hai câu thành một: `사람이 책을 읽어요` + `그 사람은 제 친구예요`.", "answer": "책을 읽는 사람은 제 친구예요"}],
            },
        },
        {
            "slug": "sinh-hoat-00-nen-tang-5b-dinh-ngu-qua-khu",
            "title": "Nền tảng 5.2 · Phim đã xem, món sẽ ăn: -(으)ㄴ & -(으)ㄹ",
            "title_en": "기초 5-2: 어제 본 영화, 내일 먹을 음식",
            "summary": "Định ngữ của động từ theo thời gian: đã xảy ra '-(으)ㄴ' ('어제 본 영화') và sẽ, dự định '-(으)ㄹ' ('내일 먹을 음식'); chọn đúng giữa '-는', '-(으)ㄴ', '-(으)ㄹ'.",
            "grammar": [1, 2], "notes": [],
            "goal": [
                "Nói «thứ đã…» bằng `-(으)ㄴ`: `어제 본 영화`, `작년에 산 옷`.",
                "Nói «thứ sẽ…» bằng `-(으)ㄹ`: `내일 먹을 음식`, `할 일`.",
                "Chọn đúng `-는 / -(으)ㄴ / -(으)ㄹ` theo thì của mệnh đề.",
            ],
            "coach": {
                "focus_vi": ["`V + -(으)ㄴ + N` (quá khứ) · `V + -(으)ㄹ + N` (dự định)."],
                "watch_out_vi": ["`먹는 음식` (món đang ăn) khác `먹은 음식` (món đã ăn) và `먹을 음식` (món sẽ ăn).", "Gốc `ㄹ` bỏ `ㄹ` trước `-(으)ㄴ` (산) nhưng giữ trước `-(으)ㄹ` (살, 만들)."],
                "notebook_vi": ["Bảng 3 cột (hiện tại · quá khứ · dự định) cho 3 động từ."],
                "self_check": [{"prompt_vi": "Nói 3 cụm với `보다`: phim đang xem, phim đã xem, phim sẽ xem.", "answer": "보는 영화 · 본 영화 · 볼 영화"}],
            },
        },
        {
            "slug": "sinh-hoat-00-nen-tang-5c-danh-tu-hoa",
            "title": "Nền tảng 5.3 · Việc đọc sách: -는 것, -기 & -(으)ㅁ",
            "title_en": "기초 5-3: 책을 읽는 것",
            "summary": "Biến động từ thành danh từ: '-는 것' (việc…), '-기' (sau '쉽다', '어렵다', tên kỹ năng '듣기', '쓰기') và '-(으)ㅁ' trong văn viết, ghi chú; viết đoạn về sở thích dùng cả Nền tảng 5.",
            "grammar": [3, 4], "notes": [1],
            "goal": [
                "Nói sở thích, việc mình làm bằng `-는 것`: `제 취미는 음악을 듣는 것이에요`.",
                "Dùng `-기` sau `쉽다`, `어렵다`, `좋다` và trong tên kỹ năng.",
                "Nhận ra `-(으)ㅁ` trong ghi chú, thông báo và danh từ cố định (`웃음`, `만남`).",
            ],
            "coach": {
                "focus_vi": ["`V + -는 것` · `V + -기` · `V/A + -(으)ㅁ`."],
                "watch_out_vi": ["Khi nói, `-는 것이` thường thành `-는 게`, `-는 것을` thành `-는 걸`.", "Không chắc thì dùng `-는 것`: an toàn nhất trong khẩu ngữ."],
                "notebook_vi": ["Đoạn 4–5 câu về sở thích của bạn, dùng `-는 것` và `-기`."],
                "self_check": [{"prompt_vi": "Nói sở thích của bạn và một việc «dễ làm», một việc «khó làm» bằng `-기`."}],
            },
        },
    ],
}

# The two Sinh hoạt lessons that join the free Sơ cấp block, and the part each one follows.
# (Where they can go is checked: every pattern their questions are linked to is taught before.)
INTERLEAVE = {
    "sinh-hoat-01-buoi-sang": None,  # decided by `earliest_spot`
    "sinh-hoat-02-viec-nha": None,
}
HANGUL_SORT = 1


def load_items(bundle: ls.SeedBundle, slug: str) -> list[dict]:
    for r in bundle.lessons:
        if r.seed.slug == slug:
            return list((r.practice or {}).get("items") or [])
    raise KeyError(slug)


def item_patterns(ex: dict) -> set[str]:
    """The patterns an item is linked to, and those its answer checker looks for (detectors)."""
    out = {p for q in ls._question_ids(ex) for p in ls.question_grammar(ex, q)}
    out |= {d["pattern"] for d in ex.get("detectors") or [] if d.get("pattern")}
    out |= {u["card"] for u in ex.get("uses") or [] if u.get("card")}
    return out


def text_of(ex: dict) -> str:
    return json.dumps(ex, ensure_ascii=False)


def forms_in(headword: str) -> set[str]:
    return {f for f in ls.card_forms(headword) if len(f) >= 1}


def uses_word(text: str, forms: set[str]) -> bool:
    return any(f in text for f in forms if len(f) >= 2 or f == f.strip())


def plan(bundle: ls.SeedBundle) -> tuple[list[dict], list[str]]:
    """The new lesson files (dicts, in course order) and the problems found."""
    problems: list[str] = []
    out: list[dict] = []
    for slug, parts in PARTS.items():
        raw = json.loads((LESSONS / f"{slug}.json").read_text(encoding="utf-8"))
        grammar = raw["grammar"]
        lang_notes = [n for n in raw["notes"] if n["kind"] != "goal"]
        part_of_pattern = {grammar[i]["pattern"]: k for k, p in enumerate(parts) for i in p["grammar"]}
        if sorted(part_of_pattern.values()) != sorted(k for k, p in enumerate(parts) for _ in p["grammar"]) or len(part_of_pattern) != len(grammar):
            problems.append(f"{slug}: every card must be in exactly one part")

        items = {ex["id"]: ex for ex in load_items(bundle, slug)}
        order = list(raw["exercise_ids"])
        # -- practice: the last part among the patterns it tests
        item_part: dict[str, int | None] = {}
        for eid in order:
            ex = items[eid]
            ks = [part_of_pattern[p] for p in item_patterns(ex) if p in part_of_pattern]
            item_part[eid] = max(ks) if ks else None

        # -- words: the first part whose cards or (grammar-placed) practice use them
        vocab = raw["vocab"]
        part_text = ["" for _ in parts]
        for k, p in enumerate(parts):
            for i in p["grammar"]:
                g = grammar[i]
                part_text[k] += " ".join(str(g.get(f) or "") for f in ("example_en", "usage_context_vi", "note_vi", "pattern"))
        for eid, k in item_part.items():
            if k is not None:
                part_text[k] += text_of(items[eid])
        word_part: list[int | None] = []
        for v in vocab:
            forms = forms_in(v["headword"].split("/")[0].strip()) | {v["headword"]}
            hit = next((k for k in range(len(parts)) if uses_word(part_text[k], forms)), None)
            word_part.append(hit)
        # a lesson with its own rule for words (Nền tảng 4: which number system a word belongs to)
        rule = WORD_RULES.get(slug)
        if rule:
            for i, v in enumerate(vocab):
                k = rule(v)
                if k is not None:
                    word_part[i] = k
        # families of placed words decide where the unplaced ones of the same family go
        fam_votes: dict[str, Counter] = defaultdict(Counter)
        for v, k in zip(vocab, word_part):
            if k is not None and v.get("family"):
                fam_votes[v["family"]][k] += 1
        sizes = Counter(k for k in word_part if k is not None)
        for i, v in enumerate(vocab):
            if word_part[i] is None:
                votes = fam_votes.get(v.get("family") or "")
                k = votes.most_common(1)[0][0] if votes else min(range(len(parts)), key=lambda x: (sizes[x], x))
                word_part[i] = k
                sizes[k] += 1

        # -- practice with no pattern of this lesson: where most of its words are taught (later on tie)
        for eid, k in item_part.items():
            if k is not None:
                continue
            t = text_of(items[eid])
            votes = Counter()
            for v, wk in zip(vocab, word_part):
                if uses_word(t, forms_in(v["headword"].split("/")[0].strip()) | {v["headword"]}):
                    votes[wk] += 1
            item_part[eid] = max(votes, key=lambda x: (votes[x], x)) if votes else len(parts) - 1

        for k, p in enumerate(parts):
            seed = {
                "slug": p["slug"],
                "title": p["title"],
                "title_en": p["title_en"],
                "topic": raw["topic"],
                "track": raw["track"],
                "level": raw["level"],
                "summary": p["summary"],
                "vocab": [v for v, wk in zip(vocab, word_part) if wk == k],
                "notes": [{"title": "Sau bài này bạn làm được gì", "kind": "goal", "body": "\n".join(f"• {b}" for b in p["goal"])}]
                + [lang_notes[i] for i in p["notes"]],
                "coach": p["coach"],
                "grammar": [grammar[i] for i in p["grammar"]],
                "editor_notes": raw.get("editor_notes") or [],
                "exercise_ids": [eid for eid in order if item_part[eid] == k],
                "sort_order": 0,
            }
            if k > 0:
                seed["split_from"] = slug
            out.append(seed)
        if sorted(i for p in parts for i in p["notes"]) != list(range(len(lang_notes))):
            problems.append(f"{slug}: every language note must be in exactly one part")
    return out, problems


def earliest_spot(parts: list[dict], lesson: dict, first_pattern_part: dict[str, int], later_cards: set[str]) -> int:
    """After which part (index) a Sinh hoạt lesson may sit: every Nền tảng pattern its questions
    or its cards build on must be taught before it."""
    items = lesson["_items"]
    need = -1
    pats = set()
    for ex in items:
        pats |= item_patterns(ex)
    for g in lesson["grammar"]:
        pats |= set(g.get("builds_on") or [])
    for p in pats:
        if p in first_pattern_part:
            need = max(need, first_pattern_part[p])
    return need


def main(write: bool) -> int:
    if any((LESSONS / f"{p['slug']}.json").exists() for parts in PARTS.values() for p in parts[1:]):
        print("already split (the parts are in app/seed/lessons): this script runs once, on the five whole lessons")
        return 0
    bundle = ls.load_all()
    if bundle.problems:
        print("seed has problems before the split; fix them first")
        return 1
    new, problems = plan(bundle)
    # totals: nothing lost, nothing doubled
    before = {"vocab": 0, "grammar": 0, "exercise_ids": 0}
    for slug in PARTS:
        raw = json.loads((LESSONS / f"{slug}.json").read_text(encoding="utf-8"))
        for k in before:
            before[k] += len(raw[k])
    after = {k: sum(len(s[k]) for s in new) for k in before}
    if before != after:
        problems.append(f"totals differ: {before} -> {after}")
    for k in before:
        for slug, parts in PARTS.items():
            mine = [s for s in new if s["slug"] in {p["slug"] for p in parts}]
            flat = [x["headword"] if k == "vocab" else x["pattern"] if k == "grammar" else x for s in mine for x in s[k]]
            raw = json.loads((LESSONS / f"{slug}.json").read_text(encoding="utf-8"))
            orig = [x["headword"] if k == "vocab" else x["pattern"] if k == "grammar" else x for x in raw[k]]
            if sorted(flat) != sorted(orig):
                problems.append(f"{slug}: {k} differ from the lesson's own")

    # where Buổi sáng and Việc nhà can go
    first_pattern_part = {g["pattern"]: n for n, s in enumerate(new) for g in s["grammar"]}
    sh = {}
    for slug in INTERLEAVE:
        raw = json.loads((LESSONS / f"{slug}.json").read_text(encoding="utf-8"))
        raw["_items"] = load_items(bundle, slug)
        sh[slug] = (raw, earliest_spot(new, raw, first_pattern_part, set()))

    for s in new:
        print(f"{s['slug'][:44]:44} {s['title'][:52]:52} words {len(s['vocab']):3}  cards {len(s['grammar'])}  items {len(s['exercise_ids']):3}")
    for slug, (_raw, spot) in sh.items():
        print(f"{slug}: may follow part #{spot + 1} ({new[spot]['slug'] if spot >= 0 else 'start'})")
    for p in problems:
        print("PROBLEM:", p)
    if problems:
        return 1
    if not write:
        return 0

    # ---- the order: Hangul, the parts, with Buổi sáng and Việc nhà placed after the part chosen
    spot1 = max(sh["sinh-hoat-01-buoi-sang"][1], PLACE_AFTER["sinh-hoat-01-buoi-sang"])
    spot2 = max(sh["sinh-hoat-02-viec-nha"][1], PLACE_AFTER["sinh-hoat-02-viec-nha"], spot1)
    course: list[tuple[str, dict | None]] = []
    for n, s in enumerate(new):
        course.append((s["slug"], s))
        if n == spot1:
            course.append(("sinh-hoat-01-buoi-sang", None))
        if n == spot2:
            course.append(("sinh-hoat-02-viec-nha", None))
    added = len(new) - len(PARTS)  # lessons the course gained
    # every lesson after the old Việc nhà moves down by `added`
    old_last_free = json.loads((LESSONS / "sinh-hoat-02-viec-nha.json").read_text(encoding="utf-8"))["sort_order"]
    for path in sorted(LESSONS.glob("*.json")):
        if path.stem in dict(course) or path.stem.startswith("sinh-hoat-00-nen-tang"):
            continue
        text = path.read_text(encoding="utf-8")
        m = re.search(r'^(\s*"sort_order":\s*)(\d+)', text, re.MULTILINE)
        if m and int(m.group(2)) > old_last_free:
            path.write_text(text[: m.start(2)] + str(int(m.group(2)) + added) + text[m.end(2):], encoding="utf-8")
    for pos, (slug, seed) in enumerate(course, start=HANGUL_SORT + 1):
        path = LESSONS / f"{slug}.json"
        if seed is not None:
            seed["sort_order"] = pos
            path.write_text(json.dumps(seed, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        else:
            raw = json.loads(path.read_text(encoding="utf-8"))
            raw["sort_order"] = pos
            raw["track"] = "beginner"  # it now sits in the Sơ cấp block
            path.write_text(json.dumps(raw, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    # the readings of a Nền tảng lesson go with its last part
    for slug, parts in PARTS.items():
        src = PASSAGES / f"{slug}.json"
        last = parts[-1]["slug"]
        if src.exists() and last != slug:
            data = json.loads(src.read_text(encoding="utf-8"))
            data["lesson"] = last
            (PASSAGES / f"{last}.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            src.unlink()
    print("written:", len(course), "lessons in the Sơ cấp block; others moved down by", added)
    return 0


# ------------------------------------------------------------------ Nền tảng 4: by number system
_NATIVE = {"하나", "둘", "셋", "넷", "다섯", "여섯", "일곱", "여덟", "아홉", "열", "스물", "서른", "마흔", "쉰", "예순", "일흔", "여든", "아흔", "한", "두", "세", "네", "스무", "한두", "한둘", "두세", "두셋", "서너", "서넛", "네다섯", "첫", "첫째", "둘째", "셋째", "넷째", "다섯째", "번째"}
_NATIVE_UNITS = {"개", "번", "시", "명", "살", "잔", "권", "병", "마리", "그루", "대", "상자", "통", "짝", "시간"}
_SINO = {"영", "공", "일", "이", "삼", "사", "오", "육", "칠", "팔", "구", "십", "백", "천", "만", "억", "십만", "백만", "천만", "이십", "삼십", "사십", "오십", "육십", "칠십", "팔십", "구십", "분", "월", "년", "원", "층", "그램", "센티", "센티미터", "킬로", "킬로그램", "킬로미터", "인분", "숫자", "반년", "반달"}


def _nt4(v: dict) -> int | None:
    w = v["headword"].split("/")[0].strip()
    fam = v.get("family") or ""
    if w in _NATIVE or w in _NATIVE_UNITS:
        return 1
    if w in _SINO or (w.endswith("월") and len(w) <= 3):  # 일월 … 십이월, 유월, 시월
        return 0
    if fam.endswith("Thời gian") or w.endswith("요일"):
        return 2  # talking about when: 몇 시, 며칠, 무슨 요일
    if fam.endswith("Thứ tự"):
        return 1
    return None


WORD_RULES = {"sinh-hoat-00-nen-tang-4-so-gio-ngay": _nt4}

# the part each Sinh hoạt lesson should follow at the earliest (index in the list of parts), on top
# of what its cards build on (`earliest_spot`). Buổi sáng builds on 4.3 (몇 시 → N + 쯤) and 5.2
# (-(으)ㄹ + N → -(으)ㄹ 거예요, -(으)ㄹ 때); Việc nhà on 5.3 (-기 → -기로 하다): they can come no earlier.
PLACE_AFTER = {"sinh-hoat-01-buoi-sang": 0, "sinh-hoat-02-viec-nha": 0}

if __name__ == "__main__":
    sys.exit(main("--write" in sys.argv))

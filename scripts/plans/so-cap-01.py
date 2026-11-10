G_E = "N(Thời gian) + 에"
G_GO = "V + -고"
G_PAST = "V/A + -았/었-"
G_JJUM = "N + 쯤"
G_JIMAN = "V/A + -지만"
G_TTAE = "V/A + -(으)ㄹ 때"
G_FUT = "V + -(으)ㄹ 거예요"
G_YAGET = "V + -아/어야겠다"
PLANS = {
"sinh-hoat-01-buoi-sang": [
 {"title_vi": "Kể một ngày: giờ giấc và hành động nối tiếp",
  "can_do_vi": "Nói giờ làm việc theo trình tự: «일곱 시에 일어나고 샤워해요» (7 giờ dậy rồi tắm); dùng 먼저 / 그다음에 / 그리고 để nối các việc; gọi tên đồ dùng rửa mặt (비누, 칫솔, 치약, 수건).",
  "use_vi": "Tự giới thiệu lịch trong ngày với bạn bè, đồng nghiệp: dậy, rửa mặt, ăn sáng, đi làm, tan làm, đi ngủ.",
  "topik_vi": "Giống dạng đọc bảng lịch trình và chọn câu trùng khớp ở phần Đọc TOPIK I, và dạng nghe giờ giấc.",
  "vocab": ["아침","기상","일어나다","샤워","샤워하다","세수","세수하다","양치","이를 닦다","씻다","아침을 먹다","출근하다","퇴근하다","자다","하루 일과","family:Nối câu","family:Đồ vệ sinh"],
  "grammar": [G_E, G_GO], "check": ["BO05","BC02","LN07","KR01"]},
 {"title_vi": "Kể sáng nay đã làm gì: quá khứ và «khoảng… giờ»",
  "can_do_vi": "Kể việc đã làm sáng nay bằng -았/었-: «여덟 시쯤 집에서 나갔어요» (khoảng 8 giờ tôi đã ra khỏi nhà); nói thói quen với 보통, 자주, 늘.",
  "use_vi": "Kể với bạn: «Sáng nay tôi ngủ quên vì báo thức không kêu», hỏi lại «Bạn dậy lúc mấy giờ?».",
  "topik_vi": "Giống dạng đọc đoạn văn ngắn về một buổi sáng và chọn câu đúng ở phần Đọc TOPIK I; dạng nghe chọn nội dung trùng khớp.",
  "vocab": ["family:Kể buổi sáng","family:Từ hay dùng","family:Mở rộng"],
  "grammar": [G_PAST, G_JJUM], "check": ["BO01","BF01","GB07a","GB07b","U07R1","U07L1"]},
 {"title_vi": "Nói trạng thái và lúc nào: -지만 và -(으)ㄹ 때",
  "can_do_vi": "Nói hai ý trái nhau: «피곤하지만 일찍 일어나요» (mệt nhưng dậy sớm); nói «lúc… thì…»: «바쁠 때 아침을 안 먹어요».",
  "use_vi": "Kể thói quen và hoàn cảnh: lúc bận, lúc mệt, lúc đi ra ngoài thì bạn làm gì.",
  "topik_vi": "Giống dạng điền đuôi câu nối ý ở phần Đọc TOPIK I và dạng nghe chọn đáp án ứng với tình huống.",
  "vocab": ["피곤하다","바쁘다","깨다","꾸다","낮잠","잠자다","울다","울음","맞추다","목욕","목욕하다","샴푸하다","세숫물","양치질","스트레칭","마치다","그만","말다"],
  "grammar": [G_JIMAN, G_TTAE], "check": ["BO03","BO04","BF03","BC01","LN04","LN05","D04"]},
 {"title_vi": "Kế hoạch ngày mai và quyết tâm: -(으)ㄹ 거예요, -아/어야겠다",
  "can_do_vi": "Nói kế hoạch: «내일 일찍 일어날 거예요» (ngày mai tôi sẽ dậy sớm); nói quyết tâm vừa nghĩ ra: «일찍 자야겠어요» (phải đi ngủ sớm mới được); biết các động từ đi vào, ra, lên, xuống.",
  "use_vi": "Hẹn kế hoạch với bạn, nói chuyện ra ngoài và đi trễ (외출, 준비, 지각), tự đặt mục tiêu sau khi ngủ quên.",
  "topik_vi": "Giống dạng điền dạng kế hoạch / quyết tâm vào chỗ trống ở phần Đọc TOPIK I và dạng nghe việc làm tiếp theo.",
  "vocab": ["다녀오다","들르다","외출","외출하다","지각하다","준비","준비되다","나가다","나오다","들어가다","올라가다","올라오다","내려오다","건너오다","떠나다","뛰어가다","달리다","달리기하다","걸음","서다","앉다","눕다","일어서다","세우다"],
  "grammar": [G_FUT, G_YAGET], "check": ["BO02","BF02","LN01","LN03","LN06","E05a","E05c","D05","FS25","FSL10"]},
 {"title_vi": "Động tác của tay (1): cầm, đặt, lấy, ném, dùng đồ",
  "can_do_vi": "Gọi đúng động tác của tay: 잡다 (nắm), 놓다 (đặt), 두다, 갖다, 꺼내다 (lấy ra), 던지다 (ném), 줍다 (nhặt), 밀다 (đẩy), 누르다 (ấn), 만지다, 안다 (ôm), 흔들다 (vẫy), 돌리다 (xoay), 쌓다 (xếp chồng).",
  "use_vi": "Hiểu và làm theo chỉ dẫn hằng ngày: «버튼을 누르세요», «가방에서 지갑을 꺼내세요».",
  "topik_vi": "Giống dạng điền động từ hợp ngữ cảnh ở phần Đọc TOPIK I và dạng nghe chọn câu có nghĩa giống.",
  "vocab": ["틀다","찾다","찾아보다","이용","이용되다","사용되다","출입","잡다","놓다","두다","갖다","꺼내다","던지다","줍다","밀다","누르다","만지다","안다","흔들다","돌리다","쌓다"],
  "grammar": [], "check": ["FS19","FS20","FS21","FSL08","FSL09"]},
 {"title_vi": "Động tác (2): cắt, chịu đựng, ngã, di chuyển",
  "can_do_vi": "Nói các động tác còn lại: 자르다 (cắt), 뽑다 (nhổ), 펴다 (mở ra), 풀다 (tháo), 참다 (nhịn), 쳐다보다 (nhìn chằm chằm), 가리키다 (chỉ), 넘어지다 (ngã), 미끄러지다 (trượt), 움직이다 (cử động).",
  "use_vi": "Kể một sự cố nhỏ: «길에서 미끄러져서 넘어졌어요» và hiểu cảnh báo «조심하세요».",
  "topik_vi": "Giống dạng điền động từ hợp ngữ cảnh ở phần Đọc TOPIK I.",
  "vocab": ["rest"],
  "grammar": [], "check": ["FS22","FS23","FS24"]},
],
}

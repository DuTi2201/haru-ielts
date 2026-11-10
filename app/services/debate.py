"""Tranh luận · Đàm phán · Phản biện với Haru (phase 4) — pure logic.

A live spoken role-play over Gemini Live (the same plumbing as "Trò chuyện với Haru": a
single-use token locked to the setup built here; app.services.conversation.live_setup /
token_request). Three kinds:

- debate     the learner takes a side of a motion, Haru argues the other side;
- negotiate  a real situation (a market stall, a landlord, a professor, an HR manager): the learner
             has a goal, Haru has a hidden limit and only moves for reasons, conditions or trades;
- critique   Haru defends a claim with a built-in flaw (over-generalising, a tiny sample,
             correlation taken for cause, a celebrity as proof, a sampling bias, a test set that
             is not the field…) and the learner has to find it and argue against it.

Fitted to the learner like the presentations (app.services.present_profile): a debate band 1-5 of
its own (starts from the presentation band, moves after two agreeing sessions), scenarios in three
tiers (band 1-2, 3, 4-5), how Haru talks per band, the phrases to use per kind and tier, and a
rubric that says what a 4 means at the tier. Haru holds its ground and concedes ONLY to a concrete
reason or evidence — out loud ("좋은 지적이에요, 그 부분은 인정해요. 하지만…") — so the learner
learns that good arguments, not persistence, move the other side. Language mistakes are not
corrected mid-argument (they are in the report), except a light recast at band 1-2.

The report (`REPORT_SCHEMA`) marks four criteria per kind, quotes the best move, and — the part
that teaches — up to three moments where Haru said something and the learner could have answered
better, with the better answer.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Literal

from app.services.conversation import SIGNAL

Kind = Literal["debate", "negotiate", "critique"]
KINDS: dict[str, str] = {"debate": "Tranh luận", "negotiate": "Đàm phán", "critique": "Phản biện"}

MAX_SECONDS = 480
MIN_LEARNER_CHARS = 8


def tier_of(band: int | None) -> int:
    b = band or 1
    return 1 if b <= 2 else 2 if b == 3 else 3


@dataclass(frozen=True)
class Scenario:
    id: str
    kind: str
    tier: int
    title_vi: str
    situation_vi: str
    learner_role_vi: str
    haru_role_vi: str
    learner_goal_vi: str
    opener_ko: str  # what Haru says first (or the motion / the flawed claim)
    secret: str = ""  # only in Haru's instruction: its limit / the flaw
    flaw_vi: str = ""  # critique: named in the report, not before
    sides: tuple[str, str] = ("찬성", "반대")

    def public(self) -> dict[str, Any]:
        return {
            "id": self.id, "kind": self.kind, "tier": self.tier, "title_vi": self.title_vi,
            "situation_vi": self.situation_vi, "learner_role_vi": self.learner_role_vi,
            "haru_role_vi": self.haru_role_vi, "learner_goal_vi": self.learner_goal_vi,
            "opener_ko": self.opener_ko if self.kind != "critique" else "",
            "sides": list(self.sides) if self.kind == "debate" else [],
        }


def _d(id: str, tier: int, motion: str, vi: str) -> Scenario:
    return Scenario(id, "debate", tier, vi, f"Chủ đề tranh luận: «{motion}» — {vi}.", "Một bên của tranh luận (bạn chọn)",
                    "Bên còn lại", "Bảo vệ lập trường của bạn bằng lý do, ví dụ và bác lại ý của Haru.", motion)


SCENARIOS: list[Scenario] = [
    # ---- debate
    _d("d1", 1, "아침밥은 꼭 먹어야 해요", "Bữa sáng nhất định phải ăn"),
    _d("d2", 1, "주말에는 집에서 쉬는 게 밖에 나가는 것보다 좋아요", "Cuối tuần ở nhà nghỉ tốt hơn ra ngoài"),
    _d("d3", 1, "고양이가 강아지보다 키우기 좋아요", "Nuôi mèo tốt hơn nuôi chó"),
    _d("d4", 2, "대학생은 아르바이트를 해야 한다", "Sinh viên nên đi làm thêm"),
    _d("d5", 2, "온라인 수업이 교실 수업보다 효과적이다", "Học online hiệu quả hơn học trên lớp"),
    _d("d6", 2, "외국어는 어릴 때 배워야 한다", "Ngoại ngữ nên học từ nhỏ"),
    _d("d7", 3, "AI 번역기가 있으면 외국어를 배울 필요가 없다", "Có AI dịch thì không cần học ngoại ngữ"),
    _d("d8", 3, "재택근무가 사무실 근무보다 생산적이다", "Làm việc ở nhà năng suất hơn ở văn phòng"),
    _d("d9", 3, "SNS는 사회에 득보다 실이 많다", "Mạng xã hội hại nhiều hơn lợi"),
    # ---- negotiate
    Scenario("n1", "negotiate", 1, "Mặc cả ở chợ Dongdaemun", "Bạn muốn mua một chiếc áo khoác ở sạp quần áo.",
             "Khách mua", "Người bán", "Mua được áo với giá 20.000원 trở xuống (giá chào 30.000원).",
             "어서 오세요! 이 재킷 어때요? 30,000원이에요.",
             "Giá thấp nhất bạn chịu bán: 22.000원. Nếu khách mua 2 cái thì bán 40.000원 cả hai. Chỉ giảm từng bước 2.000–3.000원 khi khách đưa lý do (giá chỗ khác, mua nhiều, trả tiền mặt)."),
    Scenario("n2", "negotiate", 1, "Đổi lịch hẹn với bạn", "Thứ Bảy này bạn bận, muốn dời buổi đi ăn với bạn Hàn.",
             "Bạn", "Bạn của bạn (Haru)", "Dời sang Chủ nhật mà bạn kia vẫn vui vẻ.",
             "토요일에 만나는 거 기대돼요! 어디 갈까요?",
             "Chủ nhật bạn bận buổi sáng, chỉ rảnh từ 2 giờ chiều. Hơi buồn khi bị dời; vui lại nếu người kia xin lỗi và đề nghị bù (mời cà phê, chọn quán bạn thích)."),
    Scenario("n3", "negotiate", 1, "Đổi giày không có hoá đơn", "Đôi giày mua tuần trước bị chật, bạn làm mất hoá đơn.",
             "Khách hàng", "Nhân viên cửa hàng", "Được đổi sang cỡ lớn hơn.",
             "안녕하세요, 무엇을 도와드릴까요?",
             "Quy định: chỉ đổi khi có hoá đơn. Chấp nhận đổi nếu khách đưa được bằng chứng khác (lịch sử thanh toán thẻ trên điện thoại, ngày mua) và giày còn mới."),
    Scenario("n4", "negotiate", 2, "Thương lượng tiền thuê phòng", "Bạn xem một phòng one-room gần trường, giá 50만원/tháng.",
             "Người thuê", "Chủ nhà", "Thuê với 45만원/tháng, hoặc được miễn phí quản lý.",
             "방 보셨죠? 월세는 50만 원이고 관리비는 따로 5만 원이에요.",
             "Giá thấp nhất: 47만원 nếu ký 1 năm; miễn phí quản lý chỉ khi ký 2 năm hoặc trả trước 3 tháng. Không giảm nếu khách chỉ nói 'đắt quá'."),
    Scenario("n5", "negotiate", 2, "Xin gia hạn nộp bài", "Bạn cần thêm thời gian cho bài báo cáo môn học.",
             "Sinh viên", "Giáo sư", "Được gia hạn 1 tuần.",
             "네, 들어오세요. 무슨 일이에요?",
             "Tối đa cho 3 ngày, và chỉ khi sinh viên nói lý do cụ thể và kế hoạch hoàn thành (đã làm đến đâu, còn gì). Được 5 ngày nếu sinh viên nộp trước phần đã xong."),
    Scenario("n6", "negotiate", 2, "Ca làm thêm ở quán cà phê", "Bạn được nhận làm thêm, nhưng lịch học trùng ca sáng.",
             "Nhân viên mới", "Quản lý quán", "Làm ca chiều các ngày trong tuần, không làm ca sáng.",
             "다음 주부터 평일 오전 근무 가능하죠?",
             "Quán đang thiếu người ca sáng và ca tối thứ Sáu. Đồng ý cho ca chiều nếu nhân viên nhận thêm ca tối thứ Sáu hoặc thay ca khi có người nghỉ."),
    Scenario("n7", "negotiate", 3, "Thương lượng lương thực tập", "Bạn nhận lời mời thực tập ở một công ty công nghệ Hàn.",
             "Ứng viên", "Nhân sự (HR)", "Lương 250만원/tháng hoặc tổng đãi ngộ tương đương.",
             "합격을 축하드립니다. 인턴 급여는 월 220만 원으로 안내드리려고 합니다.",
             "Ngân sách lương cứng tối đa 230만원. Có thể thêm phụ cấp đi lại 10만원, bữa trưa, hoặc xét lại lương sau 3 tháng nếu đánh giá tốt. Chỉ nhượng khi ứng viên nêu giá trị cụ thể (kỹ năng, dự án)."),
    Scenario("n8", "negotiate", 3, "Chia việc nhóm thuyết trình", "Nhóm 4 người làm bài thuyết trình cuối kỳ; bạn ngại phần nói vì tiếng Hàn.",
             "Thành viên nhóm", "Trưởng nhóm", "Nhận phần phân tích dữ liệu và làm slide thay vì thuyết trình chính.",
             "이번 발표는 모두 한 파트씩 발표하기로 해요. 괜찮죠?",
             "Muốn ai cũng nói. Chấp nhận nếu thành viên này nhận phân tích dữ liệu + slide VÀ trả lời phần hỏi đáp về dữ liệu (nói ngắn)."),
    Scenario("n9", "negotiate", 3, "Phân chia thời gian với giáo sư hướng dẫn", "Giáo sư muốn bạn tham gia dự án của lab, bạn muốn giữ thời gian cho đề tài luận văn của mình.",
             "Học viên cao học", "Giáo sư hướng dẫn", "Giữ ít nhất 3 ngày/tuần cho đề tài riêng.",
             "다음 달부터 우리 연구실 프로젝트에 주 4일 참여해 줬으면 해요.",
             "Cần người 3–4 ngày/tuần cho dự án. Đồng ý 2 ngày/tuần nếu học viên đề xuất cách đề tài riêng liên quan dự án hoặc cam kết mốc tiến độ rõ ràng."),
    # ---- critique
    Scenario("c1", "critique", 1, "“Người Hàn ai cũng ăn kimchi mỗi ngày”", "Haru nói người Hàn nào cũng ăn kimchi mỗi ngày. Chỉ ra chỗ nói quá.",
             "Người phản biện", "Người khẳng định", "Chỉ ra lỗi trong lập luận của Haru và đưa ví dụ ngược.",
             "한국 사람은 모두 매일 김치를 먹어요. 그러니까 김치를 안 먹으면 한국 사람이 아니에요.",
             "Lỗi: khái quát hoá quá mức (모두 / 매일) và kết luận sai từ đó.", "Khái quát hoá quá mức"),
    Scenario("c2", "critique", 1, "“Áo đắt luôn là áo tốt”", "Haru tin cứ đắt là tốt, rẻ là mau hỏng. Chỉ ra chỗ vội kết luận.",
             "Người phản biện", "Người khẳng định", "Chỉ ra lỗi trong lập luận của Haru và đưa ví dụ ngược.",
             "비싼 옷은 항상 좋은 옷이에요. 싼 옷은 다 금방 망가져요.",
             "Lỗi: giá cao ≠ chất lượng (thương hiệu, quảng cáo); 'luôn', 'tất cả' là khái quát hoá.", "Đánh đồng giá với chất lượng"),
    Scenario("c3", "critique", 1, "“Học nhiều thì chắc chắn thi tốt”", "Haru cho rằng cứ học nhiều là thi tốt. Chỉ ra điều Haru bỏ qua.",
             "Người phản biện", "Người khẳng định", "Chỉ ra lỗi trong lập luận của Haru và đưa ví dụ ngược.",
             "공부를 많이 하면 무조건 시험을 잘 봐요. 시험을 못 보면 공부를 안 한 거예요.",
             "Lỗi: bỏ qua cách học, sức khoẻ, đề thi…; 'vô điều kiện' (무조건); kết luận ngược sai.", "Chỉ thấy một nguyên nhân"),
    Scenario("c4", "critique", 2, "“Hai người bạn học online thành công”", "Haru đưa ra một lập luận. Bạn tìm lỗ hổng và phản biện.",
             "Người phản biện", "Người lập luận", "Chỉ ra lỗ hổng và nói cần bằng chứng gì mới đủ.",
             "제 친구 두 명이 온라인으로만 공부해서 토픽 6급을 받았어요. 그러니까 온라인 공부가 제일 좋은 방법이에요.",
             "Lỗi: mẫu quá nhỏ (2 người), có thể họ đã giỏi sẵn; 'tốt nhất' cần so sánh với nhiều người.", "Mẫu quá nhỏ"),
    Scenario("c5", "critique", 2, "“Kem làm tăng đuối nước”", "Haru đưa ra một lập luận. Bạn tìm lỗ hổng và phản biện.",
             "Người phản biện", "Người lập luận", "Chỉ ra lỗ hổng và đưa cách giải thích khác.",
             "아이스크림이 많이 팔리는 달에 물놀이 사고도 많아요. 그러니까 아이스크림 판매를 줄여야 해요.",
             "Lỗi: tương quan không phải nhân quả — mùa hè nóng là nguyên nhân chung.", "Tương quan ≠ nhân quả"),
    Scenario("c6", "critique", 2, "“Diễn viên nổi tiếng dùng nên tốt”", "Haru đưa ra một lập luận. Bạn tìm lỗ hổng và phản biện.",
             "Người phản biện", "Người lập luận", "Chỉ ra lỗ hổng và nói bằng chứng thật sự cần là gì.",
             "유명한 배우가 이 화장품을 써요. 그래서 이 화장품은 누구 피부에나 좋아요.",
             "Lỗi: dựa vào người nổi tiếng (quảng cáo, được trả tiền), mỗi loại da khác nhau; cần thử nghiệm/đánh giá.", "Dựa vào người nổi tiếng"),
    Scenario("c7", "critique", 3, "“90% người dùng hài lòng”", "Haru trình bày kết quả khảo sát của một ứng dụng. Bạn phản biện như trong buổi seminar.",
             "Người phản biện", "Người trình bày", "Chỉ ra vấn đề về mẫu khảo sát và đề xuất cách kiểm chứng tốt hơn.",
             "저희 앱 사용자 설문에서 응답자의 90%가 만족한다고 했습니다. 따라서 이 앱은 모든 학습자에게 효과적입니다.",
             "Lỗi: sai lệch chọn mẫu — chỉ hỏi người đang dùng (người bỏ app không được hỏi), tự đánh giá ≠ hiệu quả học, khái quát cho 'mọi người học'.", "Sai lệch chọn mẫu"),
    Scenario("c8", "critique", 3, "“Mô hình đạt 99% độ chính xác”", "Haru trình bày một mô hình AI phát hiện té ngã. Bạn phản biện như hội đồng.",
             "Người phản biện", "Người trình bày", "Chỉ ra vì sao 99% chưa đủ để kết luận và cần đánh giá thêm gì.",
             "저희 낙상 감지 모델은 테스트 데이터에서 정확도 99%를 달성했습니다. 그러니까 실제 요양원에 바로 설치해도 문제없습니다.",
             "Lỗi: dữ liệu mất cân bằng (té ngã rất hiếm → accuracy cao vô nghĩa, cần recall/precision), dữ liệu test khác môi trường thật (ánh sáng, góc camera), chưa thử thực địa.", "Chỉ số và dữ liệu không đại diện"),
    Scenario("c9", "critique", 3, "“Bài báo được trích dẫn nhiều nên không thể sai”", "Haru dùng một bài báo để kết luận. Bạn phản biện như trong lab meeting.",
             "Người phản biện", "Người lập luận", "Chỉ ra lỗ hổng và nói cần kiểm chứng thế nào.",
             "이 논문은 인용이 천 번 넘게 됐습니다. 그러니까 이 논문의 결론은 틀릴 수 없고, 우리 연구에도 그대로 적용됩니다.",
             "Lỗi: dựa vào uy tín (trích dẫn nhiều ≠ đúng), điều kiện nghiên cứu khác (dữ liệu, bối cảnh), cần tái lập hoặc kiểm tra giả định.", "Dựa vào uy tín"),
]
BY_ID: dict[str, Scenario] = {s.id: s for s in SCENARIOS}


def scenarios_for(band: int | None, kind: str | None = None) -> list[Scenario]:
    t = tier_of(band)
    return [s for s in SCENARIOS if s.tier == t and (kind is None or s.kind == kind)]


def custom_debate(motion: str, band: int | None) -> Scenario:
    m = re.sub(r"\s+", " ", motion).strip()[:200]
    return Scenario("custom", "debate", tier_of(band), m, f"Chủ đề tranh luận của bạn: «{m}».",
                    "Một bên của tranh luận (bạn chọn)", "Bên còn lại",
                    "Bảo vệ lập trường của bạn bằng lý do, ví dụ và bác lại ý của Haru.", m)


# Phrases to use, by kind and tier.
PHRASES: dict[str, dict[int, list[tuple[str, str]]]] = {
    "debate": {
        1: [("저는 … 생각해요", "Tôi nghĩ …"), ("왜냐하면 … 때문이에요", "Vì …"), ("그렇지만 …", "Nhưng …"), ("저는 동의하지 않아요", "Tôi không đồng ý")],
        2: [("제 생각은 조금 달라요", "Ý tôi hơi khác"), ("그 말도 맞지만 …", "Điều đó cũng đúng, nhưng …"), ("예를 들어서 …", "Ví dụ …"), ("그러니까 제 말은 …", "Ý tôi là …")],
        3: [("말씀하신 부분은 인정하지만 …", "Tôi công nhận điều anh/chị nói, nhưng …"), ("그 주장에는 한 가지 문제가 있습니다", "Lập luận đó có một vấn đề"), ("근거가 무엇인가요?", "Căn cứ là gì?"), ("결론적으로 …", "Tóm lại …")],
    },
    "negotiate": {
        1: [("조금 깎아 주세요", "Bớt cho tôi chút"), ("… 원 어때요?", "… won được không?"), ("두 개 사면 …?", "Nếu mua hai cái thì …?"), ("그럼 …", "Vậy thì …")],
        2: [("혹시 … 안 될까요?", "Liệu … có được không?"), ("대신 …", "Đổi lại …"), ("…(으)면 … 해 주실 수 있어요?", "Nếu … thì anh/chị có thể … không?"), ("그 조건이면 좋아요", "Điều kiện đó thì được")],
        3: [("저희 입장도 이해해 주셨으면 합니다", "Mong anh/chị hiểu cho phía tôi"), ("… 조건이라면 검토해 보겠습니다", "Nếu điều kiện là … thì tôi sẽ cân nhắc"), ("중간 지점을 찾아보면 어떨까요?", "Hay ta tìm điểm ở giữa?"), ("서로에게 좋은 방법은 …", "Cách có lợi cho cả hai là …")],
    },
    "critique": {
        1: [("그건 아닌 것 같아요", "Tôi nghĩ không phải vậy"), ("모든 사람이 … 은/는 아니에요", "Không phải ai cũng …"), ("예를 들면 …", "Ví dụ …"), ("왜 그렇게 생각해요?", "Sao bạn nghĩ vậy?")],
        2: [("그건 너무 일반화한 것 같아요", "Như vậy là khái quát quá"), ("… 만으로는 알 수 없어요", "Chỉ với … thì chưa biết được"), ("다른 이유도 있을 수 있어요", "Có thể có lý do khác"), ("근거가 부족해요", "Căn cứ chưa đủ")],
        3: [("표본이 대표성이 있나요?", "Mẫu có tính đại diện không?"), ("상관관계와 인과관계는 다릅니다", "Tương quan khác nhân quả"), ("다른 해석도 가능합니다", "Cũng có thể hiểu cách khác"), ("그 결론을 뒷받침하려면 … 이/가 필요합니다", "Để chứng minh kết luận đó cần …")],
    },
}

CRITERIA: dict[str, dict[str, str]] = {
    "debate": {"argument": "Lập luận", "rebuttal": "Phản bác", "evidence": "Dẫn chứng", "language": "Ngôn ngữ tranh luận"},
    "negotiate": {"outcome": "Kết quả", "strategy": "Chiến lược", "rapport": "Mềm mỏng & lịch sự", "language": "Ngôn ngữ đàm phán"},
    "critique": {"spotting": "Chỉ ra lỗ hổng", "reasoning": "Lý lẽ phản biện", "questioning": "Đặt câu hỏi", "language": "Ngôn ngữ phản biện"},
}

# What a 4 means, per kind and tier.
RUBRIC: dict[str, dict[int, dict[str, str]]] = {
    "debate": {
        1: {"argument": "Nói rõ mình chọn bên nào + 1 lý do.", "rebuttal": "Đáp lại được ý của Haru bằng 그렇지만 + 1 câu.", "evidence": "Có 1 ví dụ từ bản thân.", "language": "Câu đơn đúng, dùng 생각해요 / 왜냐하면."},
        2: {"argument": "Lập trường + 2 lý do rõ.", "rebuttal": "Bác trực tiếp ý Haru vừa nói, không lặp lại ý cũ.", "evidence": "Ví dụ cụ thể (ai, khi nào, kết quả).", "language": "Bày tỏ không đồng ý lịch sự (제 생각은 조금 달라요, 그 말도 맞지만)."},
        3: {"argument": "Lập luận chặt: khẳng định → lý do → bằng chứng → kết luận.", "rebuttal": "Công nhận một phần rồi lật lại (인정하지만…), chỉ ra điểm yếu trong lập luận Haru.", "evidence": "Dẫn chứng có sức nặng (số liệu, nghiên cứu, ví dụ đại diện).", "language": "Văn nói trang trọng, đa dạng cấu trúc, gần như không lỗi."},
    },
    "negotiate": {
        1: {"outcome": "Đạt hoặc gần đạt mục tiêu.", "strategy": "Đưa ra một đề nghị cụ thể (con số / ngày).", "rapport": "Lịch sự, cảm ơn, không cộc lốc.", "language": "Dùng được 주세요 / 어때요 / -(으)면."},
        2: {"outcome": "Đạt mục tiêu hoặc thoả thuận có lợi.", "strategy": "Đưa lý do + đề nghị đổi lại (대신 …).", "rapport": "Giữ quan hệ tốt, hiểu cho phía kia.", "language": "Đề nghị mềm (혹시 … 안 될까요?), câu điều kiện đúng."},
        3: {"outcome": "Đạt mục tiêu hoặc tổng lợi ích tương đương.", "strategy": "Nêu giá trị của mình, tìm lợi ích chung, đề xuất nhiều phương án.", "rapport": "Chuyên nghiệp, kiên định mà không căng thẳng.", "language": "Kính ngữ công sở, cách nói gián tiếp phù hợp."},
    },
    "critique": {
        1: {"spotting": "Nói được câu của Haru sai ở đâu (vd. 'không phải ai cũng…').", "reasoning": "Có 1 ví dụ ngược.", "questioning": "Hỏi lại Haru ít nhất 1 câu (왜요?).", "language": "Câu đơn đúng."},
        2: {"spotting": "Gọi đúng tên lỗ hổng (mẫu nhỏ, tương quan ≠ nhân quả…).", "reasoning": "Đưa cách giải thích khác hoặc nói cần bằng chứng gì.", "questioning": "Câu hỏi buộc Haru đưa căn cứ.", "language": "Dùng 근거, 일반화, 다른 이유 đúng chỗ."},
        3: {"spotting": "Chỉ ra lỗ hổng chính và cả lỗ hổng phụ.", "reasoning": "Đề xuất cách kiểm chứng (chỉ số khác, nhóm đối chứng, dữ liệu thực địa).", "questioning": "Hỏi như hội đồng: giả định, giới hạn, khả năng khái quát.", "language": "Thuật ngữ học thuật và văn nói trang trọng."},
    },
}

# How Haru talks, per band.
SPEECH: dict[int, str] = {
    1: "Mỗi lượt 1–2 câu tiếng Hàn rất ngắn (tối đa 8 từ), nói rất chậm. Chỉ một ý mỗi lượt. Nếu học viên lúng túng, đưa hai lựa chọn hoặc nửa đầu câu. Được nói tiếng Việt ngắn để giải thích nghĩa khi học viên hỏi.",
    2: "Mỗi lượt 1–2 câu ngắn (tối đa 12 từ), nói chậm. Một ý mỗi lượt. Thỉnh thoảng gợi mở bằng câu hỏi để học viên nói tiếp.",
    3: "Mỗi lượt 2–3 câu, tốc độ hơi chậm. Một luận điểm mỗi lượt, hỏi lại khi học viên nói chung chung (예를 들면요? 근거가 뭐예요?).",
    4: "Mỗi lượt 2–4 câu, tốc độ gần bình thường. Phản bác thật sự, đòi bằng chứng, dùng văn nói trang trọng vừa phải.",
    5: "Nói tự nhiên như người bản xứ trong seminar / cuộc họp. Phản bác sắc, chỉ ra mâu thuẫn, yêu cầu số liệu; không dùng tiếng Việt trừ khi học viên hỏi nghĩa.",
}


@dataclass
class Setup:
    scenario: Scenario
    band: int
    level_rules: str
    side_ko: str | None = None  # debate: the learner's side
    known: list[str] = field(default_factory=list)


def _phrases(kind: str, tier: int) -> list[tuple[str, str]]:
    return PHRASES[kind][tier]


def build_system_instruction(s: Setup) -> str:
    sc = s.scenario
    t = tier_of(s.band)
    common = f"""Bạn là Haru, bạn luyện nói tiếng Hàn cho người Việt. Đây là buổi luyện {KINDS[sc.kind].upper()} bằng giọng nói.
{s.level_rules}
Cách nói ở mức {s.band}/5: {SPEECH[s.band]}
Quy tắc chung:
- Luôn nói tiếng Hàn (trừ khi quy tắc mức cho phép tiếng Việt). Giữ đúng vai, không nói mình là AI, không giảng bài.
- GIỮ VỮNG lập trường/giới hạn của vai. Chỉ nhượng bộ (một phần) khi học viên đưa ra lý do cụ thể, bằng chứng hoặc đề nghị đổi lại — và khi nhượng bộ thì NÓI RÕ vì lý lẽ đó ("좋은 지적이에요, 그 부분은 인정해요. 하지만…"). Nói chung chung, nài nỉ hay lặp lại thì không nhượng.
- Mỗi lượt chỉ một ý để học viên phải phản hồi; kết thúc lượt bằng một câu hỏi hoặc một ý để họ đáp lại.
- Không sửa lỗi ngữ pháp giữa chừng{' (chỉ nhắc lại đúng câu của họ một cách tự nhiên nếu họ sai nặng)' if t == 1 else ''}; lỗi sẽ có trong báo cáo cuối buổi.
- Tin nhắn bắt đầu bằng {SIGNAL} là tín hiệu của ứng dụng, không đọc to, không nhắc tới.
- Học viên nói tiếng Việt: hiểu ý, nhắc lại ý đó bằng tiếng Hàn ngắn gọn để họ nói theo, rồi tiếp tục vai.
Các mẫu câu học viên đang luyện (khen ngắn khi họ dùng đúng): {', '.join(k for k, _ in _phrases(sc.kind, t))}"""
    if s.known:
        common += f"\nNgữ pháp học viên đã học (dùng chủ yếu trong phạm vi này): {', '.join(s.known[:20])}"
    if sc.kind == "debate":
        side = s.side_ko or "찬성"
        other = "반대" if side == "찬성" else "찬성"
        role = f"""
TRANH LUẬN. Chủ đề: «{sc.opener_ko}». Học viên bên {side}; BẠN bên {other}.
- Mở đầu: chào ngắn, nói chủ đề, mời học viên nêu lập trường và lý do trước.
- Sau đó mỗi lượt: đáp vào ĐÚNG ý học viên vừa nói (công nhận nếu hay, rồi phản bác) và đưa một luận điểm của bên {other}.
- Khi học viên chỉ nói một câu chung chung: hỏi "왜요?" / "예를 들면요?" / "근거가 뭐예요?" theo mức.
- Gần cuối: mời học viên nói lời kết (마지막으로 한마디 해 주세요), rồi bạn kết thúc công bằng."""
    elif sc.kind == "negotiate":
        role = f"""
ĐÀM PHÁN NHẬP VAI. Tình huống: {sc.situation_vi}
Vai của bạn: {sc.haru_role_vi}. Vai của học viên: {sc.learner_role_vi} — mục tiêu của họ: {sc.learner_goal_vi}
GIỚI HẠN BÍ MẬT CỦA BẠN (không bao giờ nói ra con số hay điều kiện này trực tiếp): {sc.secret}
- Mở đầu bằng đúng câu: «{sc.opener_ko}»
- Nhượng từng bước nhỏ, chỉ khi có lý do/điều kiện/đổi chác; không vượt giới hạn bí mật.
- Khi đạt thoả thuận: nhắc lại điều khoản đã chốt bằng một câu rõ ràng rồi cảm ơn. Không đạt thì kết thúc lịch sự."""
    else:
        role = f"""
PHẢN BIỆN. Bạn đóng vai {sc.haru_role_vi} và bảo vệ khẳng định này: «{sc.opener_ko}»
LỖ HỔNG ĐƯỢC CÀI SẴN (không tự nói ra): {sc.secret}
- Mở đầu: trình bày khẳng định trên một cách tự tin, rồi hỏi học viên nghĩ sao.
- Bảo vệ khẳng định bằng lý lẽ yếu nhưng nghe có vẻ hợp lý; khi học viên chỉ ra đúng lỗ hổng thì công nhận rõ ("맞아요, 그 부분은 제가 놓쳤네요") rồi đưa phản bác tiếp theo yếu hơn.
- Nếu học viên mãi chưa thấy lỗ hổng: hỏi gợi mở theo mức (vd. "정말 모든 사람이 그럴까요?", "다른 이유는 없을까요?").
- Gần cuối: hỏi học viên tóm tắt vấn đề chính của khẳng định."""
    return common + role


def nudges(sc: Scenario) -> dict[str, str]:
    from app.services.conversation import NUDGES

    start = {
        "debate": f"{SIGNAL} Buổi tranh luận bắt đầu. Chào ngắn, nêu chủ đề và mời học viên nêu lập trường.",
        "negotiate": f"{SIGNAL} Buổi đàm phán bắt đầu. Nói câu mở đầu theo vai.",
        "critique": f"{SIGNAL} Buổi phản biện bắt đầu. Trình bày khẳng định và hỏi học viên nghĩ sao.",
    }[sc.kind]
    wrap = {
        "debate": f"{SIGNAL} Sắp hết giờ. Mời học viên nói lời kết, đáp một câu ngắn rồi kết thúc công bằng, khen một lập luận cụ thể của họ.",
        "negotiate": f"{SIGNAL} Sắp hết giờ. Đưa đề nghị cuối cùng (trong giới hạn) và chốt hoặc dừng lịch sự.",
        "critique": f"{SIGNAL} Sắp hết giờ. Hỏi học viên tóm tắt vấn đề chính của khẳng định, công nhận điểm đúng của họ rồi chào.",
    }[sc.kind]
    return {**NUDGES, "start": start, "wrap_up": wrap}


# ---------------------------------------------------------------- the report


def report_schema(kind: str) -> dict[str, Any]:
    keys = list(CRITERIA[kind])
    return {
        "type": "object",
        "properties": {
            "summary_vi": {"type": "string"},
            "outcome_vi": {"type": "string"},
            "scores": {"type": "object", "properties": {k: {"type": "integer"} for k in keys}, "required": keys},
            "score_notes_vi": {"type": "object", "properties": {k: {"type": "string"} for k in keys}, "required": keys},
            "best_move": {
                "type": "object",
                "properties": {"said_ko": {"type": "string"}, "why_vi": {"type": "string"}},
                "required": ["said_ko", "why_vi"],
            },
            "missed": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "haru_said_ko": {"type": "string"},
                        "you_said_ko": {"type": "string"},
                        "better_ko": {"type": "string"},
                        "better_vi": {"type": "string"},
                        "why_vi": {"type": "string"},
                    },
                    "required": ["haru_said_ko", "you_said_ko", "better_ko", "better_vi", "why_vi"],
                },
            },
            "phrases_used": {"type": "array", "items": {"type": "string"}},
            "fixes": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {"said": {"type": "string"}, "better": {"type": "string"}, "why_vi": {"type": "string"}},
                    "required": ["said", "better", "why_vi"],
                },
            },
            "goal_reached": {"type": "boolean"},
            "flaw_found": {"type": "boolean"},
            "next_time_vi": {"type": "string"},
        },
        "required": ["summary_vi", "outcome_vi", "scores", "score_notes_vi", "best_move", "missed", "phrases_used",
                     "fixes", "goal_reached", "flaw_found", "next_time_vi"],
    }


def build_report_prompt(s: Setup, turns: list[dict[str, str]]) -> str:
    sc = s.scenario
    t = tier_of(s.band)
    lines = "\n".join(f"{'Haru' if x['role'] == 'haru' else 'Học viên'}: {x['text']}" for x in turns)
    rubric = "\n".join(f"  {k} ({CRITERIA[sc.kind][k]}) — mức 4 ở bậc này: {RUBRIC[sc.kind][t][k]}" for k in CRITERIA[sc.kind])
    extra = {
        "debate": f"Học viên bên {s.side_ko or '찬성'} của chủ đề «{sc.opener_ko}».",
        "negotiate": f"Mục tiêu của học viên: {sc.learner_goal_vi} Giới hạn bí mật của Haru: {sc.secret}",
        "critique": f"Khẳng định của Haru: «{sc.opener_ko}». Lỗ hổng cài sẵn: {sc.secret}",
    }[sc.kind]
    return f"""Bạn là huấn luyện viên kỹ năng {KINDS[sc.kind].lower()} bằng tiếng Hàn cho người Việt. Đây là bản ghi một buổi nhập vai bằng giọng nói (bản chép tự động, có thể sai chính tả nhỏ).
{s.level_rules}
Mức của học viên: {s.band}/5. Tình huống: {sc.title_vi}. {extra}

{lines}

Trả về (mọi lời giải thích bằng tiếng Việt, nói thẳng với học viên là "bạn"):
- summary_vi: 1–2 câu tóm tắt diễn biến.
- outcome_vi: kết quả — tranh luận: ai thuyết phục hơn ở điểm nào; đàm phán: đã chốt điều khoản gì (hoặc chưa); phản biện: học viên đã chỉ ra lỗ hổng nào.
- scores: 1–5 theo THANG CỦA BẬC NÀY (đạt đúng mô tả = 4, vượt rõ = 5, thiếu một chút = 3, thiếu nhiều = 2, gần như không có = 1). Không so với người bản xứ.
{rubric}
- score_notes_vi: mỗi tiêu chí 1 câu, dẫn chứng từ lời học viên.
- best_move: câu hay nhất học viên đã nói (said_ko, nguyên văn) và vì sao hay.
- missed: 2–3 thời điểm QUAN TRỌNG NHẤT học viên có thể đáp tốt hơn: haru_said_ko = câu Haru, you_said_ko = câu học viên đã đáp (nguyên văn, rỗng nếu im lặng), better_ko = câu đáp tốt hơn ĐÚNG TRÌNH ĐỘ (ưu tiên mẫu câu: {', '.join(k for k, _ in _phrases(sc.kind, t))}), better_vi = nghĩa, why_vi = vì sao tốt hơn (kỹ năng gì: phản bác trực tiếp, đưa bằng chứng, đề nghị đổi lại, hỏi căn cứ…).
- phrases_used: những mẫu câu ở trên học viên thực sự đã dùng.
- fixes: tối đa 3 lỗi ngôn ngữ đáng sửa nhất (said, better, why_vi).
- goal_reached: đàm phán — đạt mục tiêu chưa; loại khác — đặt true nếu học viên giữ được lập trường đến cuối.
- flaw_found: phản biện — đã chỉ ra đúng lỗ hổng chính chưa; loại khác — false.
- next_time_vi: 1 việc cụ thể nên làm ở buổi sau."""


def parse_report(text: str, kind: str) -> dict[str, Any]:
    try:
        raw = json.loads(text)
    except (TypeError, ValueError):
        raw = {}
    if not isinstance(raw, dict):
        raw = {}

    def s(v: Any, n: int = 400) -> str:
        return str(v).strip()[:n] if isinstance(v, (str, int, float)) and not isinstance(v, bool) else ""

    keys = list(CRITERIA[kind])
    sc = raw.get("scores") if isinstance(raw.get("scores"), dict) else {}
    scores: dict[str, int] = {}
    for k in keys:
        try:
            scores[k] = max(1, min(5, int(sc.get(k))))
        except (TypeError, ValueError):
            continue
    if len(scores) != len(keys):
        raise ValueError("incomplete report")
    notes = raw.get("score_notes_vi") if isinstance(raw.get("score_notes_vi"), dict) else {}
    best = raw.get("best_move") if isinstance(raw.get("best_move"), dict) else {}
    return {
        "kind": kind,
        "summary_vi": s(raw.get("summary_vi")),
        "outcome_vi": s(raw.get("outcome_vi")),
        "scores": scores,
        "score_notes_vi": {k: s(notes.get(k), 300) for k in keys},
        "overall": round(sum(scores.values()) / len(scores), 1),
        "best_move": {"said_ko": s(best.get("said_ko"), 300), "why_vi": s(best.get("why_vi"), 300)},
        "missed": [
            {k: s(m.get(k), 400) for k in ("haru_said_ko", "you_said_ko", "better_ko", "better_vi", "why_vi")}
            for m in raw.get("missed") or [] if isinstance(m, dict) and s(m.get("better_ko"))
        ][:3],
        "phrases_used": [s(p, 80) for p in raw.get("phrases_used") or [] if s(p, 80)][:8],
        "fixes": [
            {k: s(f.get(k), 300) for k in ("said", "better", "why_vi")}
            for f in raw.get("fixes") or [] if isinstance(f, dict) and s(f.get("better"))
        ][:3],
        "goal_reached": bool(raw.get("goal_reached")),
        "flaw_found": bool(raw.get("flaw_found")) if kind == "critique" else False,
        "next_time_vi": s(raw.get("next_time_vi")),
    }


def verdict(report: dict[str, Any], learner_turns: int) -> int | None:
    """+1 / -1 / 0 for the debate band; None when the session was too short to judge."""
    if learner_turns < 4:
        return None
    o = float(report.get("overall") or 0)
    if o >= 4.2:
        return 1
    if o <= 2.4:
        return -1
    return 0

"""Makes the generated G1 exercises answerable from the screen alone.

Run by build.py on the finished items (see docs/review/exercises-ui/A.md and B.md). It only adds
what the screen needs and never changes an answer: a kind and a one-line task for each fill-in,
the meaning to put into English, the verb to conjugate, a word bank as real chips, the short forms
the grader should also accept, and — for the writing prompts — a scaffold written for that prompt
(scripts/g1/writing_scaffold.json) plus a checklist of what *that* prompt asks for."""

from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).parent

# ---------------------------------------------------------------- fill-in tasks

# the answers are the words of a bank: every group item takes one of them
BANK_GROUPS = ("G1D1KCB", "G1D7KXL", "G1D7KXC", "G1D3KD")

# «Sửa cho đúng», sách Destination B2 tr. 8 bài B: the book prints a wrong sentence in bold; the
# wrong form is not in the data, so the learner gets the meaning to say instead
KB_SITUATION = {
    "G1D1KB-1": "Bố tôi hay dậy muộn vào các sáng thứ Bảy.",
    "G1D1KB-2": "Hỏi người kia: bạn có nói thứ tiếng nào khác ngoài tiếng Anh không?",
    "G1D1KB-3": "Tôi mua xong hết quà Giáng sinh rồi, mà mới tháng Mười!",
    "G1D1KB-4": "Đây là lần đầu tiên tôi tổ chức tiệc ở nhà.",
    "G1D1KB-5": "Thực ra, tôi nghĩ đôi khi Darren làm việc khá chăm chỉ. (Actually: đính chính lại)",
    "G1D1KB-6": "Từ trước tới giờ Carlo chưa ăn đồ ăn Trung Quốc.",
    "G1D1KB-7": "Sean đã đặt bàn cho tối nay rồi.",
    "G1D1KB-8": "Hỏi: Melanie có cần ai giúp sơn căn hộ mới của cô ấy không?",
}
KB_INSTRUCTION = (
    "Câu gốc ở trên sai ở phần in đậm. Gõ phần thay thế đúng, theo điều người nói muốn nói: "
    "thói quen, việc đang diễn ra, hay việc đã xong mà còn liên quan tới bây giờ?"
)
# the book's own wrong sentences, copied from Destination B2 Unit 1, p. 8, exercise B (bold = the part to rewrite)
KB_ORIGINAL = {
    "G1D1KB-1": "My dad **is often getting up** late on Saturday mornings.",
    "G1D1KB-2": "**Are you speaking** any other languages apart from English?",
    "G1D1KB-3": "**I already buy** all my Christmas presents and it's only October!",
    "G1D1KB-4": "It's the first time **I'm ever having** a party at home.",
    "G1D1KB-5": "Actually, I think Darren **does works** quite hard sometimes.",
    "G1D1KB-6": "Carlo **is never eating** Chinese food before.",
    "G1D1KB-7": "Sean **already books** a table for tonight.",
    "G1D1KB-8": "**Needs Melanie** any help painting her new flat?",
}

# the verb of a gap whose tense the book had made wrong: shown beside the gap
VERB_HINT = {
    "G1D3KU3C1-1": "see", "G1D3KU3C1-2": "receive", "G1D3KU3C1-3": "be", "G1D3KU3C1-4": "represent",
    "G1D3KU3C1-5": "play", "G1D3KU3C1-6": "not travel", "G1D3KU3C1-7": "go",
    "G1D4KC4-1": "warm", "G1D4KC4-2": "rise", "G1D4KC4-3": "change",
}
HINT_INSTRUCTION = {
    "G1D3KU3C1": "Chia động từ trong ngoặc cho đúng thì. Mỗi câu của lá thư xin học này đang dùng sai thì.",
    "G1D4KC4": "Chia động từ trong ngoặc cho đúng thì. Quy trình tự nhiên được mô tả bằng hiện tại đơn.",
}

AUX = {"do", "does", "did"}


def _group(item_id: str) -> str:
    return re.sub(r"-\d+$", "", item_id)


def _norm(s: str) -> str:
    return re.sub(r"[\s'’]+", "", s.lower())


# ---------------------------------------------------------------- accepted answers

SPELL = {
    "recognise": "recognize", "organise": "organize", "realise": "realize", "summarise": "summarize",
    "apologise": "apologize", "criticise": "criticize", "emphasise": "emphasize", "memorise": "memorize",
    "specialise": "specialize", "behaviour": "behavior", "colour": "color", "favourite": "favorite",
    "travelled": "traveled", "centre": "center",
}
FULL_TO_SHORT = {  # the first word(s) of an answer written in full -> its short form
    "have not": "haven't", "has not": "hasn't", "is not": "isn't", "are not": "aren't",
    "do not": "don't", "does not": "doesn't", "will not": "won't",
}
SUBJECT = {"i": "'m", "you": "'re", "we": "'re", "they": "'re", "he": "'s", "she": "'s", "it": "'s"}
SHORT_AUX = {"am": "'m", "are": "'re", "is": "'s", "have": "'ve", "has": "'s", "will": "'ll", "had": "'d"}


def _variants(answer: str) -> list[str]:
    out: list[str] = []
    low = answer.lower()
    for full, short in FULL_TO_SHORT.items():
        if low.startswith(full + " "):
            out.append(short + answer[len(full):])
    first, _, rest = answer.partition(" ")
    if first.lower() in SHORT_AUX and not low.startswith(tuple(FULL_TO_SHORT)):
        out.append(SHORT_AUX[first.lower()] + (" " + rest if rest else ""))
    # a subject written into the blank: «I have eaten» -> «I've eaten»
    m = re.match(r"^(I|You|We|They|He|She|It)\s+(am|are|is|have|has|will|had)\s+(.+)$", answer)
    if m:
        out.append(f"{m.group(1)}{SHORT_AUX[m.group(2).lower()]} {m.group(3)}")
    for br, us in SPELL.items():
        if br in low:
            out.append(re.sub(br, us, answer, flags=re.I))
        elif us in low:
            out.append(re.sub(us, br, answer, flags=re.I))
    return out


def widen_accepted(accepted: list[str]) -> list[str]:
    have = {_norm(a) for a in accepted}
    out = list(accepted)
    for a in list(accepted):
        for v in _variants(a):
            if _norm(v) not in have:
                have.add(_norm(v))
                out.append(v)
    return out


# ---------------------------------------------------------------- fill-in items

def polish_build(items: list[dict]) -> None:
    groups: dict[str, list[dict]] = defaultdict(list)
    for e in items:
        if e.get("type") == "write_fill":
            groups[_group(e["id"])].append(e)

    for gid, group in groups.items():
        bank = None
        if gid in BANK_GROUPS:
            words = sorted({b["accepted"][0].lower() for e in group for b in e["blanks"]})
            bank = words
        for e in group:
            blank = e["blanks"][0]
            for b in e["blanks"]:
                b["accepted"] = widen_accepted(b["accepted"])
                if e["text"].lstrip().startswith("( ㉠ )"):  # a sentence cannot open with 've / 's attached to nothing
                    b["accepted"] = [a for a in b["accepted"] if not a.startswith("'")]
                if "(have)" in e["text"]:  # `has` as a main verb (has control) has no contracted form
                    b["accepted"] = [a for a in b["accepted"] if a != "'s"]
            if bank:
                e["kind"] = "bank"
                e["bank"] = bank
                # the list of words in the instruction is cut off and repeated on every card
                cleaned = re.sub(r":\s*[A-Za-z’' ,/-]+(?:…|\.)?\s*$", ".", e["instruction_vi"]).replace("..", ".")
                if len(cleaned) > 12:
                    e["instruction_vi"] = cleaned
            if e["id"] in KB_SITUATION:
                e["kind"] = "fix" if e["id"] in KB_ORIGINAL else "word"
                e["task_vi"] = "Sửa phần in đậm cho đúng" if e["id"] in KB_ORIGINAL else "Gõ phần còn thiếu để câu đúng nghĩa"
                e["situation_vi"] = KB_SITUATION[e["id"]]
                if e["id"] in KB_ORIGINAL:
                    e["original"] = KB_ORIGINAL[e["id"]]
                e["instruction_vi"] = KB_INSTRUCTION
            if e["id"] in VERB_HINT:
                e["text"] = e["text"].replace("( ㉠ )", f"( ㉠ ) ({VERB_HINT[e['id']]})", 1)
                e["kind"] = "inflect"
                e["instruction_vi"] = HINT_INSTRUCTION[gid]
            if gid.startswith(("G1D6O5", "G1D7O5", "G1D7O6")):
                m = re.search(r"Nghĩa của câu:\s*(.+)$", blank.get("common_errors_vi") or "")
                if m:
                    e["situation_vi"] = m.group(1).strip()
                    e["task_vi"] = "Điền từ đã học vào chỗ trống"
            if re.fullmatch(r"G1D\dF\d", gid) and "task_vi" not in e:
                a0 = blank["accepted"][0].lower()
                if a0 in AUX:
                    e["task_vi"] = "Điền trợ động từ (do / does / did)"
                elif a0 in {"since", "for"}:
                    e["task_vi"] = "Điền since hoặc for"
                    e["kind"] = "word"


# ---------------------------------------------------------------- writing prompts

INSTRUCTION = {
    "G1D5M1": "Viết hai câu về việc học của bạn, dùng ít nhất hai từ của bài hôm nay.",
    "G1D6M1": "Viết hai câu về cách bạn học, dùng ít nhất hai kết hợp từ của bài hôm nay.",
    "G1D7M1": "Viết hai câu về một quyết định học tập của bạn, dùng hai từ của Ngày 5 (ví dụ assess, ponder, hunch).",
    "G1D8M1": "Kể bằng hai câu về một lần bạn thấy lạ hoặc khó chịu ở nơi mới, dùng ít nhất hai từ của bài hôm nay.",
    "G1D9M1": "Tóm tắt bài đọc bằng một hoặc hai câu của chính bạn, không chép nguyên câu trong bài.",
    "G1D10M1": "Viết ba câu mô tả chính bạn, dùng ít nhất ba tính từ của bài hôm nay (một từ có self- hoặc well-).",
    "G1D11M1": "Viết hai câu: một câu về cách bạn đi lại hằng ngày, một câu về điều bạn hài lòng hoặc phàn nàn. Dùng ít nhất hai từ của bài hôm nay.",
}
CHECKLIST = {
    "G1D1M1": ["Có đúng 2 câu; câu 1 ở hiện tại đơn (Yes, I do. / Not really.).", "Câu 2 ở một thì khác và có mốc thời gian (for / since / when I was …).", "Không viết am / is trước like; since đi với hiện tại hoàn thành."],
    "G1D1M2": ["Một câu thật, một câu nói quá (có always, never hoặc một con số cường điệu).", "Trạng từ tần suất đứng sau be, trước động từ thường.", "Ngôi thứ ba có -s; phủ định dùng don't / doesn't + nguyên thể."],
    "G1D1M3": ["Có đủ 3 câu, tất cả ở hiện tại đơn.", "Có 2 trạng từ tần suất và 1 cụm chỉ thời gian.", "at + giờ, in + buổi, on + thứ; không viết at the morning."],
    "G1D2M1": ["Câu 1 là việc lâu dài (hiện tại đơn), câu 2 là việc tạm thời (tiếp diễn).", "Câu 2 có mốc tạm thời: at the moment, this month, these days.", "Không dùng tiếp diễn với have (nghĩa là có), know, like."],
    "G1D3M1": ["Ba câu dùng ba mẫu: have V3 + for/since, have already V3, have been V-ing.", "for + khoảng thời gian, since + mốc; already đứng giữa have và V3.", "Động từ trạng thái (know, have) không dùng been V-ing."],
    "G1D4M1": ["Bốn câu, mỗi câu một thì: đơn, tiếp diễn, hoàn thành, hoàn thành tiếp diễn.", "Mỗi câu có một dấu hiệu thời gian riêng: every / this month / since / for.", "Không dùng tiếp diễn với know, like, have (sở hữu)."],
    "G1D5M1": ["Có ít nhất hai từ của bài hôm nay, đúng từ loại.", "Kết hợp từ đúng: take an exam, attend classes.", "Câu nói về chính bạn, không chép câu mẫu."],
    "G1D6M1": ["Có ít nhất hai kết hợp từ của bài hôm nay.", "Giới từ đúng; sau giới từ là V-ing.", "Câu nói về cách bạn học, không chép câu mẫu."],
    "G1D7M1": ["Có hai từ của Ngày 5, đúng từ loại.", "Câu nói về một quyết định học tập của chính bạn.", "Trạng thái không dùng tiếp diễn: I have a hunch, không viết I am having a hunch."],
    "G1D8M1": ["Kể chuyện đã qua bằng quá khứ đơn.", "Có ít nhất hai từ của bài hôm nay.", "Giới từ đi đúng với từ: adjust to, homesick for."],
    "G1D9M1": ["Là tóm tắt: nói điều bài viết nói, ở hiện tại đơn, không thêm ý kiến cá nhân.", "Diễn đạt bằng từ của bạn, không chép quá 3 từ liên tiếp.", "Một hoặc hai câu, 20–40 từ."],
    "G1D10M1": ["Có ít nhất ba tính từ của bài, một từ có self- hoặc well-.", "Tính từ ghép có gạch nối (self-confident).", "Mỗi câu có chủ ngữ và động từ (I am / I can be); không dùng danh từ thay tính từ."],
    "G1D11M1": ["Câu 1 nói cách đi lại hằng ngày (by bus, on foot).", "Câu 2 nói điều bạn hài lòng hoặc phàn nàn, có từ của bài.", "by + phương tiện không có a / the; on foot, không viết by foot."],
}


def polish_writing(items: list[dict]) -> None:
    scaffold = json.loads((HERE / "writing_scaffold.json").read_text(encoding="utf-8"))
    for e in items:
        s = scaffold.get(e["id"])
        if not s:
            continue
        e["limits"] = s["limits"]
        e["framework_vi"] = s["framework_vi"]
        e["frames"] = s["frames"]
        e["avoid_vi"] = s["avoid_vi"]
        e["common_errors_vi"] = s["common_errors_vi"]
        e["checklist_vi"] = CHECKLIST[e["id"]]
        if e["id"] in INSTRUCTION:
            e["instruction_vi"] = INSTRUCTION[e["id"]]
        if e["id"] == "G1D11M1":
            e["prompt_en"] = "Write two sentences: one about how you travel every day, and one about something you like or dislike about it."
            e["model_answer_en"] = (
                "I go to school by bus because it is more convenient than parking a motorbike. "
                "I am not satisfied with the timetable, because there are few buses in the evening."
            )
        if not e.get("rubric"):
            focus = "Dùng đúng từ và kết hợp từ của bài" if int(re.search(r"D(\d+)M", e["id"]).group(1)) >= 5 else "Dùng đúng cấu trúc và thì mà đề yêu cầu"
            e["rubric"] = [
                {"criterion_vi": "Trả lời đúng đề, nội dung là của chính bạn", "max": 1, "note_vi": "Task response"},
                {"criterion_vi": focus, "max": 2, "note_vi": "Grammatical range"},
                {"criterion_vi": "Dạng từ đúng: chia động từ, giới từ, -s ngôi thứ ba", "max": 2, "note_vi": "Grammatical accuracy"},
            ]


def polish(merged: dict[str, list[dict]]) -> None:
    if "build" in merged:
        polish_build(merged["build"])
    if "writing" in merged:
        polish_writing(merged["writing"])

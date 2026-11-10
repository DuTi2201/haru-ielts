"""Trình bày với Haru — say a short, structured answer in one go, get it marked for structure,
fluency and language, hear back an upgraded version of what you said, and say it again.

The talks with Haru (app.services.conversation) train turn-taking: one question, one answer. This
trains the other half of speaking — IELTS-style long turns, TOPIK 말하기 opinions, a presentation
and the professor's "왜요?" afterwards: say what you think, why, an example, and close, without
stopping. The frame grows with the learner's conversation band (app.services.talk_profile):

  band 1   Ý chính + Lý do                         2-3 câu, 20-40 s
  band 2   + Ví dụ                                  30-60 s
  band 3   + Kết luận                               45-75 s
  band 4-5 + Mặt khác (so sánh / ý ngược lại)       60-120 s

One round: a topic from the lesson being studied (`TOPIC_SCHEMA`), notes in Vietnamese turned into
a keyword outline — never full sentences, the learner still has to build them (`OUTLINE_SCHEMA`),
the learner speaks without interruption (recorded on the device, one WAV), then:

- `measure_audio`: what code can measure honestly — speaking time, pauses, the longest silence;
- one multimodal Gemini call (`build_eval_prompt`, `EVAL_SCHEMA`) listens and writes down what was
  said verbatim (hesitations included), checks each part of the frame, marks five criteria 1-5
  against the band's target, and rewrites the learner's OWN content in the frame (`upgraded`);
- `parse_eval` bounds it all and adds what is counted from the transcript (fillers, syllables/s).

The second and third try are marked the same way with the previous try in view, so the report can
say what changed. The audio is used for the one call and not stored.

Phases 2-3 add, on top:
- "Bảo vệ đề tài" (mode "defense"): the learner's own talk — title and material pasted in — with a
  talk frame (opening, content, evidence, limitations, conclusion) up to 270 s;
- follow-up questions after every try, as hard as the band ("왜요?" at band 1, a committee's
  counter-question at band 5), each answered aloud and marked (`ANSWER_SCHEMA`);
- "Không biết nói gì?": three idea seeds from thinking tools (`THINKING_TOOLS`), for the quiet,
  the anxious and topics outside the learner's field;
- per-learner fitting (app.services.present_profile): the band's own rubric, measured fluency,
  the focus criterion and the studied items to deploy, checked in `targets_used`.

Pure logic; the database side lives in the router (app.api.routers.presentation) and
app.services.presentation_db.
"""
from __future__ import annotations

import json
import re
from array import array
from dataclasses import asdict, dataclass
from typing import Any

from app.services.pronunciation import ISSUE_KINDS, SAMPLE_RATE, ClipError, wav_seconds

MAX_ATTEMPTS = 3
HARD_MAX_SECONDS = 150
DEFENSE_MAX_SECONDS = 270  # "Bảo vệ đề tài": a short talk of the learner's own work
MIN_SECONDS = 5.0
MODES = ("topic", "defense")

# The parts of a structured answer, in speaking order.
PARTS: dict[str, dict[str, str]] = {
    "point": {"label_vi": "Ý chính", "hint_vi": "Câu đầu tiên trả lời thẳng câu hỏi / nói quan điểm."},
    "reason": {"label_vi": "Lý do", "hint_vi": "Vì sao bạn nghĩ vậy."},
    "example": {"label_vi": "Ví dụ", "hint_vi": "Một ví dụ hoặc trải nghiệm cụ thể của bạn."},
    "other_side": {"label_vi": "Mặt khác", "hint_vi": "Nhắc ý ngược lại hoặc so sánh, rồi nói vì sao bạn vẫn chọn ý của mình."},
    "conclusion": {"label_vi": "Kết luận", "hint_vi": "Chốt lại ý chính trong một câu."},
    # "Bảo vệ đề tài"
    "opening": {"label_vi": "Mở đầu", "hint_vi": "Giới thiệu chủ đề và mục tiêu của bài."},
    "content": {"label_vi": "Nội dung chính", "hint_vi": "Các ý chính / phương pháp, theo thứ tự."},
    "evidence": {"label_vi": "Dẫn chứng", "hint_vi": "Số liệu, kết quả hoặc ví dụ cụ thể chứng minh."},
    "limitation": {"label_vi": "Hạn chế & hướng tiếp", "hint_vi": "Điều bài chưa làm được và sẽ làm tiếp."},
}

CRITERIA: dict[str, str] = {
    "coherence": "Mạch lạc",
    "development": "Đủ ý",
    "connectives": "Từ nối",
    "language": "Từ & ngữ pháp",
    "fluency": "Trôi chảy",
}


@dataclass(frozen=True)
class Frame:
    band: int
    parts: tuple[str, ...]
    target: tuple[int, int]  # seconds
    starters: dict[str, tuple[str, ...]]  # part -> Korean sentence starters for this band
    mode: str = "topic"

    @property
    def max_seconds(self) -> int:
        return min(DEFENSE_MAX_SECONDS if self.mode == "defense" else HARD_MAX_SECONDS, self.target[1] + 30)

    def as_dict(self) -> dict[str, Any]:
        return {
            "band": self.band,
            "mode": self.mode,
            "target_seconds": list(self.target),
            "max_seconds": self.max_seconds,
            "parts": [
                {"key": p, "label_vi": PARTS[p]["label_vi"], "hint_vi": PARTS[p]["hint_vi"], "starters": list(self.starters.get(p, ()))}
                for p in self.parts
            ],
        }


_FRAMES: dict[int, Frame] = {
    1: Frame(1, ("point", "reason"), (20, 40), {
        "point": ("저는 ___을/를 좋아해요.", "저는 ___이/가 좋아요."),
        "reason": ("___아서/어서 좋아요.", "그리고 ___."),
    }),
    2: Frame(2, ("point", "reason", "example"), (30, 60), {
        "point": ("저는 ___ 좋아해요.", "저는 ___고 싶어요."),
        "reason": ("왜냐하면 ___기 때문이에요.", "___아서/어서 좋아요."),
        "example": ("예를 들면 ___.", "지난주에 ___았/었어요."),
    }),
    3: Frame(3, ("point", "reason", "example", "conclusion"), (45, 75), {
        "point": ("제 생각에는 ___.", "저는 ___ 것 같아요."),
        "reason": ("왜냐하면 ___기 때문이에요.", "첫째, ___."),
        "example": ("예를 들어서 ___.", "저도 ___ㄴ/은 적이 있어요."),
        "conclusion": ("그래서 저는 ___.", "그러니까 ___."),
    }),
    4: Frame(4, ("point", "reason", "example", "other_side", "conclusion"), (60, 100), {
        "point": ("저는 ___다고 생각해요.", "제 생각에는 ___."),
        "reason": ("첫째, ___. 둘째, ___.", "왜냐하면 ___기 때문이에요."),
        "example": ("예를 들어서 ___.", "제 경험을 말하자면 ___."),
        "other_side": ("물론 ___지만, ___.", "___는 사람도 있지만 ___."),
        "conclusion": ("결론적으로 ___.", "그래서 저는 ___다고 생각해요."),
    }),
    5: Frame(5, ("point", "reason", "example", "other_side", "conclusion"), (90, 120), {
        "point": ("저는 ___다는 의견에 동의해요.", "제 입장은 ___."),
        "reason": ("가장 큰 이유는 ___기 때문이에요.", "또한 ___다는 점에서 ___."),
        "example": ("예를 들어 ___.", "실제로 ___."),
        "other_side": ("반면에 ___.", "물론 ___다는 단점도 있지만 ___."),
        "conclusion": ("따라서 ___.", "결론적으로 ___다고 생각합니다."),
    }),
}


_DEFENSE_STARTERS: dict[str, tuple[str, ...]] = {
    "opening": ("오늘 발표할 주제는 ___입니다.", "이 발표의 목적은 ___는 것입니다."),
    "content": ("먼저 ___. 다음으로 ___.", "이 연구에서는 ___ 방법을 사용했습니다."),
    "evidence": ("___에 따르면 ___.", "결과를 보면 ___."),
    "limitation": ("이 연구의 한계는 ___.", "앞으로는 ___ 연구하려고 합니다."),
    "conclusion": ("정리하면 ___.", "결론적으로 ___."),
}
_DEFENSE_EASY: dict[str, tuple[str, ...]] = {
    "opening": ("오늘은 ___에 대해 발표하겠습니다.", "제 주제는 ___예요."),
    "content": ("첫째, ___. 둘째, ___.", "먼저 ___."),
    "evidence": ("예를 들면 ___.", "___ 결과가 나왔어요."),
    "conclusion": ("그래서 ___.", "감사합니다."),
}
_DEFENSE_FRAMES: dict[int, Frame] = {
    1: Frame(1, ("opening", "content", "conclusion"), (40, 90), _DEFENSE_EASY, "defense"),
    2: Frame(2, ("opening", "content", "conclusion"), (60, 120), _DEFENSE_EASY, "defense"),
    3: Frame(3, ("opening", "content", "evidence", "conclusion"), (90, 150), _DEFENSE_STARTERS, "defense"),
    4: Frame(4, ("opening", "content", "evidence", "limitation", "conclusion"), (120, 210), _DEFENSE_STARTERS, "defense"),
    5: Frame(5, ("opening", "content", "evidence", "limitation", "conclusion"), (150, 240), _DEFENSE_STARTERS, "defense"),
}


def frame_for(band: int | None, mode: str = "topic") -> Frame:
    b = band if band in _FRAMES else 1
    return _DEFENSE_FRAMES[b] if mode == "defense" else _FRAMES[b]


def _targets_block(targets: list[dict[str, Any]] | None) -> str:
    if not targets:
        return ""
    lines = "\n".join(
        f"- [{t['key']}] {t['ko']} ({t['vi']})" + (f" — ví dụ: {t['example_ko']}" if t.get("example_ko") else "")
        for t in targets
    )
    return f"\nKiến thức học viên ĐÃ HỌC trong app và cần VẬN DỤNG ở lượt này:\n{lines}"


def _known_block(known: list[str] | None) -> str:
    if not known:
        return ""
    return "\nCác mẫu ngữ pháp học viên đã học (ưu tiên gợi ý bằng chính các mẫu này): " + ", ".join(known[:25])


# ---------------------------------------------------------------- topics

# When the model cannot make a topic (or is down): plain everyday questions by band.
FALLBACK_TOPICS: dict[int, list[tuple[str, str]]] = {
    1: [("주말에 뭐 해요? 왜 좋아요?", "Cuối tuần bạn làm gì? Vì sao bạn thích?"),
        ("무슨 음식을 좋아해요? 왜요?", "Bạn thích món ăn gì? Vì sao?"),
        ("아침에 뭐 마셔요? 왜요?", "Buổi sáng bạn uống gì? Vì sao?")],
    2: [("여행 가고 싶은 곳이 어디예요? 왜요?", "Bạn muốn đi du lịch ở đâu? Vì sao?"),
        ("한국어를 왜 공부해요?", "Vì sao bạn học tiếng Hàn?"),
        ("집에서 쉬는 것과 밖에 나가는 것 중에 뭐가 더 좋아요?", "Bạn thích ở nhà nghỉ hay ra ngoài hơn?")],
    3: [("혼자 공부하는 것과 친구랑 같이 공부하는 것 중에 뭐가 더 좋아요?", "Học một mình hay học cùng bạn tốt hơn?"),
        ("도시에 사는 것과 시골에 사는 것 중에 어디가 더 좋아요?", "Sống ở thành phố hay ở quê tốt hơn?"),
        ("스마트폰이 우리 생활을 더 좋게 만들었어요?", "Điện thoại thông minh có làm cuộc sống tốt hơn không?")],
    4: [("대학생이 아르바이트를 하는 것이 좋다고 생각해요?", "Sinh viên có nên đi làm thêm không?"),
        ("온라인 수업과 교실 수업 중에 어느 쪽이 더 효과적이에요?", "Học online hay học trên lớp hiệu quả hơn?"),
        ("외국에서 공부하는 것의 장점과 단점은 뭐예요?", "Du học có ưu và nhược điểm gì?")],
    5: [("AI가 사람의 일자리를 줄일 것이라고 생각해요?", "AI có làm giảm việc làm của con người không?"),
        ("성공에 더 중요한 것은 노력이에요, 운이에요?", "Thành công phụ thuộc vào nỗ lực hay may mắn nhiều hơn?"),
        ("대도시 인구 집중 문제를 어떻게 해결할 수 있을까요?", "Làm sao giải quyết việc dân số dồn về thành phố lớn?")],
}


def fallback_topic(band: int, seen: list[str], seed: int = 0) -> dict[str, Any]:
    bank = FALLBACK_TOPICS[frame_for(band).band]
    fresh = [t for t in bank if t[0] not in seen] or bank
    ko, vi = fresh[seed % len(fresh)]
    return {"question_ko": ko, "question_vi": vi, "angle_vi": "", "words": [], "source": "bank"}


TOPIC_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "question_ko": {"type": "string"},
        "question_vi": {"type": "string"},
        "angle_vi": {"type": "string"},
        "words": {
            "type": "array",
            "items": {"type": "object", "properties": {"ko": {"type": "string"}, "vi": {"type": "string"}}, "required": ["ko", "vi"]},
        },
    },
    "required": ["question_ko", "question_vi", "angle_vi", "words"],
}


def build_topic_prompt(*, level_rules: str, frame: Frame, topic: str | None, lesson_title: str | None,
                       words: list[tuple[str, str]], patterns: list[str], seen: list[str],
                       focus_hint: str | None = None, targets: list[dict[str, Any]] | None = None) -> str:
    parts = " → ".join(PARTS[p]["label_vi"] for p in frame.parts)
    w = ", ".join(f"{ko} ({vi})" for ko, vi in words[:20]) or "(chưa có)"
    pa = ", ".join(patterns[:8]) or "(chưa có)"
    avoid = "\n".join(f"- {q}" for q in seen[:10]) or "- (chưa có)"
    return f"""Bạn ra đề luyện nói "trình bày ngắn" bằng tiếng Hàn cho người Việt (giống IELTS Speaking Part 2–3, TOPIK 말하기 phần nêu ý kiến).
{level_rules}
Học viên sẽ trả lời liền một mạch {frame.target[0]}–{frame.target[1]} giây theo khung: {parts}.

Bài đang học: {lesson_title or '(chưa rõ)'} — chủ đề: {topic or '(chưa rõ)'}
Từ đã học: {w}
Mẫu ngữ pháp đã học: {pa}
Không lặp lại các đề đã ra:
{avoid}

{('Trọng tâm luyện của học viên lúc này: ' + focus_hint) if focus_hint else ''}{_targets_block(targets)}
{'Câu hỏi phải tạo cơ hội TỰ NHIÊN để dùng các kiến thức cần vận dụng ở trên.' if targets else ''}

Ra MỘT câu hỏi:
- question_ko: câu hỏi tiếng Hàn (해요체), gắn với chủ đề bài đang học và đời sống của học viên, đòi hỏi nêu ý kiến hoặc lựa chọn CÓ LÝ DO (không phải câu hỏi chỉ cần 1 từ). Đúng trình độ: mức thấp hỏi về sở thích, thói quen; mức cao hỏi so sánh, ưu/nhược, giải pháp.
- question_vi: dịch câu hỏi sang tiếng Việt.
- angle_vi: 1 câu gợi 2 hướng có thể trả lời (bằng tiếng Việt), không viết sẵn câu trả lời.
- words: 3–6 từ tiếng Hàn hữu ích cho đề này, ưu tiên từ đã học, kèm nghĩa tiếng Việt."""


def build_defense_prompt(*, level_rules: str, frame: Frame, title: str, material: str,
                         targets: list[dict[str, Any]] | None = None) -> str:
    return f"""Học viên người Việt (du học sinh / học viên cao học) chuẩn bị thuyết trình bằng tiếng Hàn về đề tài của chính họ.
{level_rules}
Tên đề tài (họ viết): «{title.strip()[:200]}»
Tài liệu / dàn ý họ dán vào: «{material.strip()[:4000] or '(trống)'}»
Họ sẽ nói {frame.target[0]}–{frame.target[1]} giây.{_targets_block(targets)}

Trả về:
- question_ko: tên đề tài bằng tiếng Hàn, tự nhiên, ngắn.
- question_vi: tên đề tài tiếng Việt.
- angle_vi: 1–2 câu: giáo sư / hội đồng sẽ chú ý điều gì ở bài này (câu hỏi nghiên cứu rõ chưa, vì sao chọn phương pháp, kết quả nói được gì).
- words: 4–8 THUẬT NGỮ tiếng Hàn quan trọng nhất cho nội dung này (ko), kèm nghĩa tiếng Việt (vi)."""


# ---------------------------------------------------------------- from a news article

# "Trình bày 2 phút" / "Phản biện" at the end of the editorial reader: a "defense" round (the
# learner's own talk: title + material) built from the article they just read.
EDITORIAL_KINDS = ("present", "debate")
BANK_TARGETS = 6
EDITORIAL_OUTLINE_PARTS = (
    ("phenomenon", "현상 · Hiện tượng"),
    ("cause", "원인 · Nguyên nhân"),
    ("consequence", "결과 · Hậu quả"),
    ("solution", "해결 방안 · Giải pháp"),
)
EDITORIAL_GRAMMAR_TARGETS = 2
EDITORIAL_TERM_TARGETS = 3
MAX_TARGETS = 6


def editorial_handoff(
    kind: str,
    title_ko: str,
    key_terms: list[dict[str, Any]] | None,
    grammar: list[dict[str, Any]] | None,
    outline: dict[str, Any] | None,
    words: dict[str, int] | None = None,
) -> dict[str, Any]:
    """The title, material and targets of a round about a news article.

    `key_terms` are the study pack's [{"ko", "vi"}]; `grammar` the article's grammar cards as
    {"id", "pattern", "meaning_vi", "example_ko"}; `outline` its model outline (현상/원인/결과/해결
    방안); `words` hangul -> the id of the article's own vocabulary card, so a key term that is a
    card is targeted as that card ("v:<id>") and counts like any studied word; a term that is not
    a card is "k:<term>". "present" asks for a 2-minute summary with the learner's view; "debate"
    asks them to take a side on the article's view and argue it."""
    if kind not in EDITORIAL_KINDS:
        raise ValueError(f"unknown kind {kind!r}")
    title = re.sub(r"\s+", " ", title_ko or "").strip()[:200]
    words = words or {}
    terms = [t for t in (key_terms or []) if isinstance(t, dict) and _s(t.get("ko"), 40)]
    lines: list[str] = []
    if kind == "present":
        lines.append(f"Trình bày khoảng 2 phút về bài báo «{title}»: bài nói về điều gì, vì sao, rồi ý kiến của bạn.")
    else:
        lines.append(
            f"Phản biện bài báo «{title}»: bạn đồng ý hay không với cách nhìn và giải pháp của bài? "
            "Nêu rõ lập trường, hai lý do có ví dụ, một điểm bài báo còn bỏ sót, rồi kết luận."
        )
    parts = [(label, _s((outline or {}).get(key), 600)) for key, label in EDITORIAL_OUTLINE_PARTS]
    parts = [(label, text) for label, text in parts if text]
    if parts:
        lines.append("")
        lines.append("Dàn ý của bài báo:")
        lines += [f"- {label}: {text}" for label, text in parts]
    if terms:
        lines.append("")
        lines.append("Thuật ngữ then chốt: " + ", ".join(f"{_s(t.get('ko'), 40)} ({_s(t.get('vi'), 80)})" for t in terms[:8]))
    cards = [g for g in (grammar or []) if isinstance(g, dict) and _s(g.get("pattern"), 80)]
    if cards:
        lines.append("Ngữ pháp trong bài: " + ", ".join(f"{_s(g.get('pattern'), 80)} ({_s(g.get('meaning_vi'), 80)})" for g in cards[:6]))

    targets: list[dict[str, Any]] = []
    for g in cards[:EDITORIAL_GRAMMAR_TARGETS]:
        targets.append({"key": f"g:{g['id']}", "kind": "grammar", "ko": _s(g.get("pattern"), 80),
                        "vi": _s(g.get("meaning_vi"), 120), "example_ko": _s(g.get("example_ko"), 200),
                        "why_vi": "Ngữ pháp của bài báo vừa đọc"})
    for t in terms[:EDITORIAL_TERM_TARGETS]:
        ko = _s(t.get("ko"), 40)
        card = words.get(ko)
        targets.append({"key": f"v:{card}" if card is not None else f"k:{ko}", "kind": "word", "ko": ko,
                        "vi": _s(t.get("vi"), 120), "example_ko": "", "why_vi": "Thuật ngữ then chốt của bài báo"})
    return {"title": title, "material": "\n".join(lines)[:6000], "targets": targets}


def merge_targets(first: list[dict[str, Any]], rest: list[dict[str, Any]], limit: int = MAX_TARGETS) -> list[dict[str, Any]]:
    """`first` (the article's own items), then the learner's usual targets that are not already
    there, at most `limit` in all."""
    seen = {t.get("key") for t in first}
    out = list(first) + [t for t in rest if t.get("key") not in seen]
    return out[:limit]


def parse_topic(text: str, max_words: int = 6) -> dict[str, Any] | None:
    raw = _json(text)
    ko = _s(raw.get("question_ko"), 200)
    if not ko or not re.search(r"[가-힣]", ko):
        return None
    words = []
    for w in raw.get("words") or []:
        if isinstance(w, dict) and _s(w.get("ko"), 40):
            words.append({"ko": _s(w.get("ko"), 40), "vi": _s(w.get("vi"), 80)})
    return {"question_ko": ko, "question_vi": _s(raw.get("question_vi"), 300),
            "angle_vi": _s(raw.get("angle_vi"), 400), "words": words[:max_words], "source": "model"}


# ---------------------------------------------------------------- outline

OUTLINE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "parts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "part": {"type": "string", "enum": list(PARTS)},
                    "idea_vi": {"type": "string"},
                    "keywords_ko": {"type": "array", "items": {"type": "string"}},
                    "starter_ko": {"type": "string"},
                    "suggested": {"type": "boolean"},
                    "target_keys": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["part", "idea_vi", "keywords_ko", "starter_ko", "suggested", "target_keys"],
            },
        },
    },
    "required": ["parts"],
}


def build_outline_prompt(*, level_rules: str, frame: Frame, question_ko: str, notes_vi: str,
                         targets: list[dict[str, Any]] | None = None, material: str = "") -> str:
    parts = "\n".join(
        f"- {p} ({PARTS[p]['label_vi']}): {PARTS[p]['hint_vi']} Mở câu gợi ý: {' / '.join(frame.starters.get(p, ()))}"
        for p in frame.parts
    )
    return f"""Học viên người Việt chuẩn bị nói liền một mạch bằng tiếng Hàn để trả lời: «{question_ko}»
{level_rules}
Ghi chú ý tưởng của học viên (tiếng Việt): «{notes_vi.strip() or '(trống)'}»
{('Tài liệu bài thuyết trình của học viên (tiếng Việt hoặc Hàn): «' + material.strip()[:4000] + '»') if material.strip() else ''}{_targets_block(targets)}

Biến ghi chú thành DÀN Ý theo đúng các phần sau, đúng thứ tự:
{parts}

Với mỗi phần:
- idea_vi: ý của học viên cho phần này, viết gọn bằng tiếng Việt (giữ đúng ý họ). Nếu ghi chú không có ý cho phần này, đề xuất một ý đơn giản hợp với các ý còn lại và đặt suggested = true.
- keywords_ko: 2–4 TỪ KHOÁ tiếng Hàn (từ hoặc cụm 1–3 từ, đúng trình độ) để học viên tự ghép câu. TUYỆT ĐỐI không viết câu hoàn chỉnh.
- starter_ko: nửa đầu câu mở cho phần này (dựa trên mở câu gợi ý), kết thúc bằng "…", không viết hết câu.
- target_keys: khoá [..] của kiến thức cần vận dụng hợp để dùng trong phần này (mỗi kiến thức đặt vào đúng 1 phần; để trống nếu không có).
Với tài liệu thuyết trình: keywords_ko là THUẬT NGỮ chuyên ngành tiếng Hàn tương ứng với nội dung của họ.
Mục tiêu là học viên tự nói ra câu, không đọc thuộc."""


def parse_outline(text: str, frame: Frame, targets: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    raw = _json(text)
    tkeys = {t["key"]: t for t in targets or []}
    by_part: dict[str, dict] = {}
    for it in raw.get("parts") or []:
        if isinstance(it, dict) and it.get("part") in frame.parts:
            by_part.setdefault(it["part"], it)
    out = []
    for p in frame.parts:
        it = by_part.get(p, {})
        kws = [_s(k, 40) for k in (it.get("keywords_ko") or []) if _s(k, 40)][:4]
        out.append({
            "part": p,
            "label_vi": PARTS[p]["label_vi"],
            "idea_vi": _s(it.get("idea_vi"), 300),
            "keywords_ko": kws,
            "starter_ko": _s(it.get("starter_ko"), 80) or (frame.starters.get(p, ("",))[0]),
            "suggested": bool(it.get("suggested")) if it else True,
            "targets": [
                {"key": k, "ko": tkeys[k]["ko"]} for k in dict.fromkeys(it.get("target_keys") or []) if k in tkeys
            ],
        })
    return out


# ---------------------------------------------------------------- "Không biết nói gì?" — idea seeds

# Thinking tools that turn "I have nothing to say" into three angles, even on a topic outside the
# learner's field: start from what they know (their own life), then widen.
THINKING_TOOLS: list[str] = [
    "Bản thân – Người xung quanh – Xã hội",
    "Quá khứ – Hiện tại – Tương lai",
    "Ưu điểm – Nhược điểm – Lựa chọn của tôi",
    "Một câu chuyện nhỏ: khi nào – ở đâu – chuyện gì – mình rút ra gì",
    "Nếu là tôi / nếu ai cũng làm vậy thì sao",
]

IDEAS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "seeds": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "tool_vi": {"type": "string"},
                    "stance_vi": {"type": "string"},
                    "reason_vi": {"type": "string"},
                    "example_vi": {"type": "string"},
                    "hook_ko": {"type": "string"},
                    "hook_vi": {"type": "string"},
                },
                "required": ["tool_vi", "stance_vi", "reason_vi", "example_vi", "hook_ko", "hook_vi"],
            },
        },
    },
    "required": ["seeds"],
}


def build_ideas_prompt(*, level_rules: str, frame: Frame, question_ko: str, material: str = "") -> str:
    tools = "\n".join(f"- {t}" for t in THINKING_TOOLS)
    mat = f"\nTài liệu học viên đã có: «{material.strip()[:3000]}»" if material.strip() else ""
    hook = (
        "hook_ko: một câu MỞ ĐẦU gây chú ý (câu hỏi cho người nghe, một con số, hoặc mở bằng câu chuyện), ngắn, đúng trình độ."
        if frame.band >= 3
        else "hook_ko: một câu mở đầu thật đơn giản, đúng trình độ (ví dụ 저는 …을/를 좋아해요)."
    )
    return f"""Học viên người Việt cần trình bày bằng tiếng Hàn về: «{question_ko}» nhưng KHÔNG BIẾT NÓI GÌ (có thể ít nói, hay lo lắng, hoặc đề không thuộc chuyên môn của họ).{mat}
{level_rules}
Đưa 3 HẠT GIỐNG Ý TƯỞNG khác nhau, mỗi cái dùng một công cụ tư duy trong danh sách:
{tools}
Mỗi hạt giống:
- tool_vi: tên công cụ đã dùng.
- stance_vi: quan điểm / câu trả lời chính, 1 câu tiếng Việt, dễ bảo vệ.
- reason_vi: lý do chính, gắn với đời sống bình thường (không cần kiến thức chuyên môn).
- example_vi: một ví dụ / câu chuyện nhỏ rất gần gũi mà ai cũng có thể có (học viên sẽ thay bằng chuyện của mình).
- {hook}
- hook_vi: nghĩa tiếng Việt.
Ba hạt giống nên khác hướng nhau (ví dụ một đồng ý, một không đồng ý, một trung lập/so sánh) để học viên chọn cái hợp với mình."""


def parse_ideas(text: str) -> list[dict[str, str]]:
    raw = _json(text)
    out = []
    for it in raw.get("seeds") or []:
        if isinstance(it, dict) and _s(it.get("stance_vi")):
            out.append({k: _s(it.get(k), 400) for k in ("tool_vi", "stance_vi", "reason_vi", "example_vi", "hook_ko", "hook_vi")})
    return out[:3]


# ---------------------------------------------------------------- measuring the recording

FRAME_MS = 20
PAUSE_SECONDS = 1.0  # a silence this long inside the answer counts as a pause
LONG_PAUSE_SECONDS = 2.5
_BRIDGE_SECONDS = 0.3  # shorter gaps are inside words / between syllables


@dataclass(frozen=True)
class AudioMeasure:
    seconds: float  # the whole recording
    speaking_seconds: float  # first voice to last voice
    voiced_seconds: float
    pauses: int  # silences >= PAUSE_SECONDS between first and last voice
    long_pauses: int  # >= LONG_PAUSE_SECONDS
    longest_pause: float

    def as_dict(self) -> dict[str, Any]:
        return {k: round(v, 1) if isinstance(v, float) else v for k, v in asdict(self).items()}


def _pcm(wav: bytes) -> array:
    """The 16-bit samples of a WAV that `wav_seconds` accepted."""
    pos = 12
    while pos + 8 <= len(wav):
        cid = wav[pos : pos + 4]
        size = int.from_bytes(wav[pos + 4 : pos + 8], "little")
        body = pos + 8
        if cid == b"data":
            data = wav[body : body + min(size, len(wav) - body)]
            a = array("h")
            a.frombytes(data[: len(data) - (len(data) % 2)])
            import sys

            if sys.byteorder == "big":
                a.byteswap()
            return a
        pos = body + size + (size & 1)
    raise ClipError("no data chunk")


def measure_audio(wav: bytes) -> AudioMeasure:
    """Speaking time and pauses from the loudness of 20 ms frames. The threshold adapts to the room
    (a multiple of the quietest frames' level, capped below the voice) with a floor, so a fan, a
    quiet mic and a speaker who never stops all work."""
    total = wav_seconds(wav)
    pcm = _pcm(wav)
    step = SAMPLE_RATE * FRAME_MS // 1000
    levels: list[float] = []
    for i in range(0, len(pcm) - step + 1, step):
        frame = pcm[i : i + step : 2]  # every other sample is plenty for loudness
        levels.append((sum(x * x for x in frame) / len(frame)) ** 0.5)
    if not levels:
        return AudioMeasure(total, 0.0, 0.0, 0, 0, 0.0)
    ranked = sorted(levels)
    quiet = ranked[max(0, len(ranked) // 10 - 1)]  # the room
    loud = ranked[min(len(ranked) - 1, len(ranked) * 9 // 10)]  # the voice
    # a multiple of the room's level, but never above a quarter of the voice: someone who talks
    # almost without a break leaves few quiet frames, and those are soft speech, not the room
    threshold = max(300.0, min(quiet * 3.0, loud * 0.25))
    voiced = [lv > threshold for lv in levels]
    sec = FRAME_MS / 1000
    # voiced segments, with short gaps bridged
    segs: list[list[int]] = []
    for i, v in enumerate(voiced):
        if not v:
            continue
        if segs and (i - segs[-1][1] - 1) * sec < _BRIDGE_SECONDS:
            segs[-1][1] = i
        else:
            segs.append([i, i])
    segs = [s for s in segs if (s[1] - s[0] + 1) * sec >= 0.1]  # clicks
    if not segs:
        return AudioMeasure(total, 0.0, 0.0, 0, 0, 0.0)
    gaps = [(b[0] - a[1] - 1) * sec for a, b in zip(segs, segs[1:])]
    speaking = (segs[-1][1] - segs[0][0] + 1) * sec
    voiced_s = sum((s[1] - s[0] + 1) * sec for s in segs)
    return AudioMeasure(
        seconds=total,
        speaking_seconds=speaking,
        voiced_seconds=voiced_s,
        pauses=sum(1 for g in gaps if g >= PAUSE_SECONDS),
        long_pauses=sum(1 for g in gaps if g >= LONG_PAUSE_SECONDS),
        longest_pause=max(gaps, default=0.0),
    )


_FILLER = re.compile(r"^(으*음+|어+|으+|엄+|흠+|아+|그+|저+)[.,…~?!]*$")
_VI_SPAN = re.compile(r"\[vi:[^\]]*\]")


def count_fillers(transcript: str) -> int:
    """Hesitation sounds written as their own token (the model is asked to write them so).
    아 / 그 / 저 count only when stretched or doubled (아아, 그…) — alone they are words."""
    n = 0
    for tok in _VI_SPAN.sub(" ", transcript).split():
        m = _FILLER.match(tok)
        if not m:
            continue
        core = m.group(1)
        if core[0] in "아그저" and len(core) == 1 and not tok.endswith(("…", "~")):
            continue
        n += 1
    return n


def syllables(transcript: str) -> int:
    return len(re.findall(r"[가-힣]", _VI_SPAN.sub(" ", transcript)))


# ---------------------------------------------------------------- marking

EVAL_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "transcript_ko": {"type": "string"},
        "off_topic": {"type": "boolean"},
        "parts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "part": {"type": "string", "enum": list(PARTS)},
                    "present": {"type": "boolean"},
                    "said_ko": {"type": "string"},
                    "note_vi": {"type": "string"},
                },
                "required": ["part", "present", "said_ko", "note_vi"],
            },
        },
        "scores": {
            "type": "object",
            "properties": {k: {"type": "integer"} for k in CRITERIA},
            "required": list(CRITERIA),
        },
        "score_notes_vi": {
            "type": "object",
            "properties": {k: {"type": "string"} for k in CRITERIA},
            "required": list(CRITERIA),
        },
        "connectives_used": {"type": "array", "items": {"type": "string"}},
        "targets_used": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "key": {"type": "string"},
                    "used": {"type": "boolean"},
                    "correct": {"type": "boolean"},
                    "said_ko": {"type": "string"},
                    "note_vi": {"type": "string"},
                },
                "required": ["key", "used", "correct", "said_ko", "note_vi"],
            },
        },
        "strength_vi": {"type": "string"},
        "tips_vi": {"type": "array", "items": {"type": "string"}},
        "upgraded": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "part": {"type": "string", "enum": list(PARTS)},
                    "ko": {"type": "string"},
                    "vi": {"type": "string"},
                },
                "required": ["part", "ko", "vi"],
            },
        },
        "stretch": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"ko": {"type": "string"}, "vi": {"type": "string"}, "why_vi": {"type": "string"}},
                "required": ["ko", "vi", "why_vi"],
            },
        },
        "pron_issues": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "word": {"type": "string"},
                    "heard_as": {"type": "string"},
                    "kind": {"type": "string", "enum": list(ISSUE_KINDS)},
                    "tip_vi": {"type": "string"},
                },
                "required": ["word", "heard_as", "kind", "tip_vi"],
            },
        },
        "follow_ups": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "q_ko": {"type": "string"},
                    "q_vi": {"type": "string"},
                    "kind": {"type": "string", "enum": ["why", "example", "detail", "counter", "method", "limit"]},
                },
                "required": ["q_ko", "q_vi", "kind"],
            },
        },
        "compare_vi": {"type": "string"},
    },
    "required": ["transcript_ko", "off_topic", "parts", "scores", "score_notes_vi", "connectives_used", "targets_used",
                 "strength_vi", "tips_vi", "upgraded", "stretch", "pron_issues", "follow_ups", "compare_vi"],
}

# How many follow-up questions, and how hard, per band ("Hỏi vặn").
FOLLOW_UP_RULES: dict[int, tuple[int, str]] = {
    1: (1, "1 câu hỏi rất ngắn, dễ, dạng 왜요? hoặc chọn một trong hai, dùng từ học viên vừa nói."),
    2: (2, "2 câu ngắn: một câu 왜요? / 어떻게요?, một câu xin ví dụ khác (예를 들면요?)."),
    3: (2, "2 câu: một câu hỏi sâu vào lý do, một câu xin chi tiết hoặc ví dụ khác."),
    4: (2, "2 câu như giáo viên: một câu phản biện nhẹ (그렇지만 …라고 생각하는 사람도 있는데요?), một câu hỏi chi tiết."),
    5: (3, "3 câu như hội đồng: phản biện thẳng, hỏi về giả định/điều kiện, và yêu cầu so sánh hoặc dẫn chứng."),
}
DEFENSE_FOLLOW_UPS = "Câu hỏi như GIÁO SƯ / HỘI ĐỒNG sau buổi thuyết trình ở cao học Hàn: vì sao chọn phương pháp này (method), điểm khác với nghiên cứu trước, hạn chế (limit), số liệu cụ thể (detail) — đúng trình độ học viên."


def _previous_lines(prev: dict[str, Any] | None) -> str:
    if not prev:
        return ""
    ev = prev.get("eval") or {}
    sc = ev.get("scores") or {}
    missing = [PARTS[p["part"]]["label_vi"] for p in ev.get("parts") or [] if not p.get("present") and p.get("part") in PARTS]
    m = prev.get("metrics") or {}
    return f"""
Đây là LẦN NÓI THỨ {int(prev.get('index', 0)) + 2}. Lần trước:
- Bản chép: «{ev.get('transcript_ko', '')}»
- Điểm: {', '.join(f'{CRITERIA[k]} {sc.get(k)}' for k in CRITERIA if k in sc)}
- Phần còn thiếu: {', '.join(missing) or 'không'}
- Ngập ngừng: {m.get('pauses', 0)} khoảng lặng ≥1 giây, {m.get('fillers', 0)} tiếng 음/어
- Lời khuyên đã đưa: {' | '.join(ev.get('tips_vi') or [])}
compare_vi: 1–2 câu nói cụ thể lần này tiến bộ / chưa tiến bộ ở đâu so với lần trước (cấu trúc, từ nối, độ trôi, vận dụng). Chấm điểm lần này độc lập, đúng như nó là."""


def build_eval_prompt(*, level_rules: str, frame: Frame, question_ko: str, measure: AudioMeasure,
                      outline: list[dict[str, Any]] | None, previous: dict[str, Any] | None,
                      targets: list[dict[str, Any]] | None = None, known: list[str] | None = None,
                      focus: str | None = None, material: str = "") -> str:
    from app.services import present_profile

    parts = "\n".join(f"- {p} ({PARTS[p]['label_vi']}): {PARTS[p]['hint_vi']}" for p in frame.parts)
    plan = ""
    if outline:
        plan = "\nDàn ý học viên đã chuẩn bị: " + " | ".join(
            f"{PARTS[o['part']]['label_vi']}: {o.get('idea_vi', '')}" for o in outline if o.get("part") in PARTS
        )
    n_follow, follow_rule = FOLLOW_UP_RULES[frame.band]
    if frame.mode == "defense":
        n_follow, follow_rule = max(2, n_follow), DEFENSE_FOLLOW_UPS
    what = "bài thuyết trình ngắn về đề tài của chính học viên" if frame.mode == "defense" else f"câu hỏi «{question_ko}»"
    mat = f"\nTài liệu học viên chuẩn bị (để biết họ định nói gì): «{material.strip()[:3000]}»" if material.strip() else ""
    focus_line = f"\nTRỌNG TÂM LUYỆN của học viên: {CRITERIA[focus]} — tips_vi đầu tiên phải về tiêu chí này." if focus in CRITERIA else ""
    tgt = ""
    if targets:
        tgt = _targets_block(targets) + "\ntargets_used: với TỪNG khoá ở trên: used = có dùng không; correct = dùng đúng ngữ pháp/nghĩa và tự nhiên; said_ko = câu học viên dùng (rỗng nếu không); note_vi = 1 câu (sai ở đâu / cách dùng đúng)."
    return f"""Bạn là giám khảo nói tiếng Hàn cho người Việt, chấm kỹ năng TRÌNH BÀY CÓ CẤU TRÚC (như IELTS Speaking Part 2–3, TOPIK 말하기, thuyết trình trên lớp).
{level_rules}
Học viên trả lời {what}, nói liền một mạch (audio đính kèm, {measure.seconds:.0f} giây).{mat}
BAND TRÌNH BÀY CỦA HỌC VIÊN: {frame.band}/5. Mục tiêu: {frame.target[0]}–{frame.target[1]} giây, đủ các phần theo thứ tự:
{parts}{plan}
Đo bằng máy: nói {measure.speaking_seconds:.0f} giây, {measure.pauses} khoảng lặng ≥1 giây, lặng dài nhất {measure.longest_pause:.1f} giây.{focus_line}{tgt}{_known_block(known)}

Trả về:
- transcript_ko: chép NGUYÊN VĂN những gì nghe được, kể cả lỗi, lặp, tự sửa. Tiếng ngập ngừng viết thành từ riêng: 음, 어, 으. Đoạn nói tiếng Việt viết [vi: …]. Không sửa cho đúng.
- off_topic: true nếu không trả lời câu hỏi / không nói về đề tài.
- parts: với TỪNG phần ở trên (đúng thứ tự): present = có nói rõ phần này không; said_ko = trích đoạn học viên nói cho phần đó (rỗng nếu không có); note_vi = 1 câu nhận xét ngắn.
- scores: mỗi tiêu chí 1–5, chấm theo THANG CỦA BAND {frame.band} dưới đây. Đạt đúng mô tả của band = 4; vượt rõ = 5; thiếu một chút = 3; thiếu nhiều = 2; gần như không có = 1. KHÔNG so với người bản xứ, KHÔNG dùng thang của band khác: người mới học đạt mô tả band 1 vẫn được 4; người band 5 nói đúng nhưng đơn giản kiểu band 3 chỉ được 2–3.
{present_profile.rubric_lines(frame.band)}
  fluency: dựa vào số đo máy và tiếng ngập ngừng.
  Chấm công bằng, không nương tay, không khắt khe.
- score_notes_vi: mỗi tiêu chí 1 câu giải thích điểm, có dẫn chứng từ bài nói.
- connectives_used: các từ nối thực sự đã dùng.
- strength_vi: 1 câu khen một điểm làm tốt cụ thể.
- tips_vi: 2–3 việc cụ thể nhất nên làm ở lần nói sau, ĐÚNG TẦM band {frame.band} (không đòi hỏi cấu trúc quá trình độ). Ưu tiên gợi ý bằng mẫu ngữ pháp học viên ĐÃ HỌC (danh sách trên), ghi rõ mẫu.
- upgraded: viết lại CHÍNH Ý CỦA HỌC VIÊN theo đúng khung (mỗi phần một mục, đúng thứ tự, giữ nội dung họ nói, chỉ sửa cấu trúc, ngữ pháp, thêm từ nối). Ở đúng band {frame.band}: chỉ dùng ngữ pháp học viên đã học hoặc cơ bản hơn, và LỒNG ĐỦ các kiến thức cần vận dụng ở trên. Câu nói được trong khoảng {frame.target[1]} giây. Phần học viên bỏ trống thì bổ sung ý đơn giản hợp với các ý còn lại. vi = nghĩa tiếng Việt.
- stretch: 0–2 mẫu câu / ngữ pháp ở band {min(5, frame.band + 1)} (cao hơn một bậc) giúp bài này hay hơn, mỗi mẫu kèm nghĩa và 1 câu vì sao. Band 5 thì là cách nói tự nhiên hơn của người bản xứ.
- pron_issues: tối đa 3 từ phát âm sai làm người nghe khó hiểu nhất (word = từ đúng, heard_as = nghe thành, kind = batchim/vowel/consonant/linking/intonation/other, tip_vi = cách sửa cho người Việt). Không có thì để trống.
- follow_ups: {n_follow} câu hỏi tiếp theo bằng tiếng Hàn (q_ko, kèm q_vi) dựa trên ĐÚNG những gì học viên vừa nói, để luyện trả lời khi bị hỏi lại. {follow_rule} kind = why/example/detail/counter/method/limit.
- compare_vi: để trống nếu đây là lần đầu.{_previous_lines(previous)}
Mọi lời giải thích bằng tiếng Việt, ngắn gọn, nói thẳng với học viên ("bạn")."""


def parse_eval(text: str, frame: Frame, measure: AudioMeasure,
               targets: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    from app.services import present_profile

    raw = _json(text)
    transcript = _s(raw.get("transcript_ko"), 6000)
    by_part: dict[str, dict] = {}
    for it in raw.get("parts") or []:
        if isinstance(it, dict) and it.get("part") in frame.parts:
            by_part.setdefault(it["part"], it)
    parts = []
    for p in frame.parts:
        it = by_part.get(p, {})
        said = _s(it.get("said_ko"), 600)
        parts.append({
            "part": p, "label_vi": PARTS[p]["label_vi"],
            "present": bool(it.get("present")) and bool(said),
            "said_ko": said, "note_vi": _s(it.get("note_vi"), 300),
        })
    sc = raw.get("scores") if isinstance(raw.get("scores"), dict) else {}
    notes = raw.get("score_notes_vi") if isinstance(raw.get("score_notes_vi"), dict) else {}
    scores: dict[str, int] = {}
    for k in CRITERIA:
        try:
            scores[k] = max(1, min(5, int(sc.get(k))))
        except (TypeError, ValueError):
            continue
    if len(scores) != len(CRITERIA) or not transcript:
        raise ValueError("incomplete marking")
    # what the frame says cannot be argued with: a missing part caps "Đủ ý"
    missing = sum(1 for p in parts if not p["present"])
    if missing:
        scores["development"] = min(scores["development"], max(1, 4 - missing))
    syl = syllables(transcript)
    metrics = {
        **measure.as_dict(),
        "fillers": count_fillers(transcript),
        "syllables": syl,
        "syllables_per_sec": round(syl / measure.speaking_seconds, 1) if measure.speaking_seconds >= 1 else None,
        "in_target": frame.target[0] <= measure.speaking_seconds <= frame.target[1] + 10,
    }
    # Trôi chảy: measured against the band's targets, blended 2:1 with the model's view
    measured = present_profile.fluency_score(metrics, frame.band)
    metrics["fluency_measured"] = measured
    scores["fluency"] = present_profile.blend_fluency(scores["fluency"], measured)

    upgraded_by: dict[str, dict] = {}
    for it in raw.get("upgraded") or []:
        if isinstance(it, dict) and it.get("part") in frame.parts and _s(it.get("ko")):
            upgraded_by.setdefault(it["part"], it)
    upgraded = [
        {"part": p, "label_vi": PARTS[p]["label_vi"], "ko": _s(upgraded_by[p].get("ko"), 600), "vi": _s(upgraded_by[p].get("vi"), 600)}
        for p in frame.parts if p in upgraded_by
    ]
    pron = [
        {"word": _s(x.get("word"), 60), "heard_as": _s(x.get("heard_as"), 60),
         "kind": x.get("kind") if x.get("kind") in ISSUE_KINDS else "other", "tip_vi": _s(x.get("tip_vi"))}
        for x in raw.get("pron_issues") or [] if isinstance(x, dict) and _s(x.get("word"))
    ][:3]
    used_by = {str(u.get("key")): u for u in raw.get("targets_used") or [] if isinstance(u, dict)}
    targets_used = []
    for t in targets or []:
        u = used_by.get(t["key"], {})
        used = bool(u.get("used")) and bool(_s(u.get("said_ko")))
        targets_used.append({
            "key": t["key"], "kind": t["kind"], "ko": t["ko"], "vi": t["vi"],
            "used": used, "correct": used and bool(u.get("correct")),
            "said_ko": _s(u.get("said_ko"), 300) if used else "", "note_vi": _s(u.get("note_vi"), 300),
        })
    n_follow = FOLLOW_UP_RULES[frame.band][0] if frame.mode != "defense" else max(2, FOLLOW_UP_RULES[frame.band][0])
    follow_ups = [
        {"q_ko": _s(q.get("q_ko"), 300), "q_vi": _s(q.get("q_vi"), 300),
         "kind": q.get("kind") if q.get("kind") in ("why", "example", "detail", "counter", "method", "limit") else "why"}
        for q in raw.get("follow_ups") or [] if isinstance(q, dict) and re.search(r"[가-힣]", _s(q.get("q_ko"), 300))
    ][:n_follow]
    overall = round(sum(scores.values()) / len(scores), 1)
    return {
        "metrics": metrics,
        "eval": {
            "transcript_ko": transcript,
            "off_topic": bool(raw.get("off_topic")),
            "parts": parts,
            "scores": scores,
            "score_notes_vi": {k: _s(notes.get(k), 300) for k in CRITERIA},
            "overall": overall,
            "connectives_used": [_s(c, 40) for c in raw.get("connectives_used") or [] if _s(c, 40)][:10],
            "targets_used": targets_used,
            "strength_vi": _s(raw.get("strength_vi"), 300),
            "tips_vi": [_s(t, 300) for t in raw.get("tips_vi") or [] if _s(t)][:3],
            "upgraded": upgraded,
            "stretch": [
                {"ko": _s(x.get("ko"), 120), "vi": _s(x.get("vi"), 200), "why_vi": _s(x.get("why_vi"), 300)}
                for x in raw.get("stretch") or [] if isinstance(x, dict) and _s(x.get("ko"))
            ][:2],
            "pron_issues": pron,
            "follow_ups": follow_ups,
            "compare_vi": _s(raw.get("compare_vi"), 400),
        },
    }


# ---------------------------------------------------------------- answering a follow-up ("Hỏi vặn")

ANSWER_MAX_SECONDS = 75
ANSWER_MIN_SECONDS = 2.0
ANSWER_CRITERIA: dict[str, str] = {"directness": "Trả lời đúng câu hỏi", "support": "Có lý do / dẫn chứng", "language": "Từ & ngữ pháp"}

ANSWER_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "transcript_ko": {"type": "string"},
        "scores": {"type": "object", "properties": {k: {"type": "integer"} for k in ANSWER_CRITERIA}, "required": list(ANSWER_CRITERIA)},
        "note_vi": {"type": "string"},
        "better_ko": {"type": "string"},
        "better_vi": {"type": "string"},
    },
    "required": ["transcript_ko", "scores", "note_vi", "better_ko", "better_vi"],
}


def build_answer_prompt(*, level_rules: str, band: int, question_ko: str, talk_ko: str, measure: AudioMeasure,
                        known: list[str] | None = None) -> str:
    return f"""Học viên người Việt vừa trình bày bằng tiếng Hàn: «{talk_ko[:2000]}»
Sau đó được hỏi lại: «{question_ko}» và trả lời (audio đính kèm, {measure.seconds:.0f} giây; {measure.pauses} khoảng lặng ≥1 giây).
{level_rules}
Band trình bày {band}/5.{_known_block(known)}

Trả về:
- transcript_ko: chép NGUYÊN VĂN câu trả lời (ngập ngừng viết 음/어, tiếng Việt viết [vi: …]).
- scores 1–5, theo tầm band {band} (đạt đúng mong đợi của band = 4):
  directness: câu đầu trả lời thẳng vào câu hỏi, không vòng vo, không lạc đề.
  support: có lý do, ví dụ hoặc dẫn chứng đi kèm (band 1–2: một lý do là đủ).
  language: đúng và đủ đa dạng ở trình độ này.
- note_vi: 1–2 câu: điều làm tốt và điều cần sửa nhất.
- better_ko: một câu trả lời mẫu ngắn GIỮ Ý của học viên, theo mẫu "trả lời thẳng → lý do/dẫn chứng", đúng band {band}, ưu tiên ngữ pháp học viên đã học. better_vi: nghĩa tiếng Việt."""


def parse_answer(text: str, measure: AudioMeasure) -> dict[str, Any]:
    raw = _json(text)
    transcript = _s(raw.get("transcript_ko"), 2000)
    sc = raw.get("scores") if isinstance(raw.get("scores"), dict) else {}
    scores: dict[str, int] = {}
    for k in ANSWER_CRITERIA:
        try:
            scores[k] = max(1, min(5, int(sc.get(k))))
        except (TypeError, ValueError):
            continue
    if len(scores) != len(ANSWER_CRITERIA) or not transcript:
        raise ValueError("incomplete marking")
    return {
        "transcript_ko": transcript,
        "scores": scores,
        "overall": round(sum(scores.values()) / len(scores), 1),
        "note_vi": _s(raw.get("note_vi"), 400),
        "better_ko": _s(raw.get("better_ko"), 600),
        "better_vi": _s(raw.get("better_vi"), 600),
        "seconds": round(measure.speaking_seconds, 1),
        "pauses": measure.pauses,
        "fillers": count_fillers(transcript),
    }


# ---------------------------------------------------------------- helpers

def _json(text: Any) -> dict:
    try:
        raw = json.loads(text)
    except (TypeError, ValueError):
        return {}
    return raw if isinstance(raw, dict) else {}


def _s(v: Any, n: int = 300) -> str:
    return str(v).strip()[:n] if isinstance(v, (str, int, float)) and not isinstance(v, bool) else ""


def bank_handoff(kind: str, deck_title: str, words: list[dict[str, Any]]) -> dict[str, Any]:
    """The title, material and targets of a round about a «Kho từ TOPIK» deck: the learner talks
    about the deck's topic and must use the deck words they have been practising. `words` are
    {"id", "hangul", "meaning_vi", "example_ko"}, the weakest first; each becomes the target
    "v:<card id>" so using it counts like any studied word."""
    if kind not in EDITORIAL_KINDS:
        raise ValueError(f"unknown kind {kind!r}")
    title = re.sub(r"\s+", " ", deck_title or "").strip()[:160]
    chosen = [w for w in words if _s(w.get("hangul"), 40)][:BANK_TARGETS]
    if kind == "present":
        head = f"Trình bày khoảng 2 phút về chủ đề «{title}»: nêu một tình huống hoặc trải nghiệm của bạn, rồi ý kiến của bạn."
    else:
        head = (
            f"Chọn một vấn đề quen thuộc thuộc chủ đề «{title}», nêu lập trường của bạn, hai lý do có ví dụ, "
            "một ý kiến ngược lại và lời đáp, rồi kết luận."
        )
    lines = [head, "", "Từ nên dùng: " + ", ".join(f"{_s(w['hangul'], 40)} ({_s(w.get('meaning_vi'), 80)})" for w in chosen)]
    targets = [
        {"key": f"v:{w['id']}", "kind": "word", "ko": _s(w["hangul"], 40), "vi": _s(w.get("meaning_vi"), 120),
         "example_ko": _s(w.get("example_ko"), 200), "why_vi": "Từ của bộ Kho TOPIK bạn đang học"}
        for w in chosen
    ]
    return {"title": f"Chủ đề: {title}", "material": "\n".join(lines)[:6000], "targets": targets}

"""Trò chuyện với Haru — a spoken conversation with Gemini Live that coaxes a shy beginner into
talking, built from what the learner has actually studied.

The browser talks to Gemini Live directly (audio in and out over one WebSocket), with a
single-use ephemeral token minted here. The token carries the whole session setup — model,
voice, transcription and the system instruction built below — so the browser cannot change
what Haru is told, and the API key never leaves the server.

This module is pure: it turns a `LearnerContext` (what the learner studied, how well they
remember it) into the system instruction, the on-screen hints, the Live setup and the token
request, and turns the finished transcript into the end-of-session report. The database side
is app.services.conversation_db; the HTTP side app.api.routers.conversation.

How Haru draws the learner out (the owner's brief):
- a friend, not a teacher: short turns, the learner's own life, today's topic as the excuse;
- questions climb from yes/no to "A or B?" to short open answers to "why / how";
- earlier lessons of the topic come back on their own (time words from lesson 3 inside the
  daily-routine talk of lesson 6), and words the learner keeps forgetting are slipped in;
- silence is met in steps the app signals (it knows when the learner is stuck, the model only
  knows when someone stops talking): simpler question / two choices, then Vietnamese plus a
  Korean sentence start; a Vietnamese answer is said back in Korean for the learner to repeat;
- mistakes are recast in passing (say it back correctly, carry on), at most one per turn;
  the list of corrections comes at the end, in the report.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

# The marker the app puts in front of its own messages to the model (a stuck learner, the
# start of the session). Never spoken to, never read aloud.
SIGNAL = "[HARU-APP]"

# What the app sends, per step of the silence ladder (the browser picks the step; the text is
# fixed here so the model always sees the same wording).
NUDGES: dict[str, str] = {
    "start": f"{SIGNAL} Buổi trò chuyện bắt đầu. Hãy chào và hỏi câu đầu tiên.",
    "easier": (
        f"{SIGNAL} Học viên im lặng khoảng 12 giây. Hỏi lại cùng ý bằng câu tiếng Hàn ngắn hơn, "
        "hoặc đưa 2 lựa chọn để họ chỉ cần chọn."
    ),
    "bilingual": (
        f"{SIGNAL} Học viên vẫn im lặng (khoảng 20 giây). Nói ngắn bằng tiếng Việt ý câu hỏi, rồi đưa "
        "nửa đầu một câu tiếng Hàn để họ nói tiếp. Nhắc họ có thể trả lời bằng tiếng Việt."
    ),
    "hint": f"{SIGNAL} Học viên bấm 'Gợi ý'. Cho một gợi ý ngắn: 1 từ khoá tiếng Hàn và nửa đầu câu trả lời.",
    "slower": (
        f"{SIGNAL} Học viên bấm 'Nói chậm'. Từ giờ đến hết buổi nói chậm hơn nữa: rõ từng âm tiết, "
        "nghỉ một nhịp sau mỗi cụm từ, câu ngắn hơn. Nếu bạn vừa hỏi thì hỏi lại câu đó thật chậm. Không giải thích."
    ),
    "normal_pace": (
        f"{SIGNAL} Học viên tắt 'Nói chậm'. Quay lại tốc độ của mức trò chuyện ở trên. Tiếp tục câu chuyện, không giải thích."
    ),
    "wrap_up": f"{SIGNAL} Sắp hết giờ. Hỏi một câu cuối thật dễ rồi chào tạm biệt ấm áp, khen một điều cụ thể.",
}
NudgeKind = Literal["start", "easier", "bilingual", "hint", "slower", "normal_pace", "wrap_up"]

Bucket = Literal["strong", "weak", "new", "unseen"]


@dataclass(frozen=True)
class Word:
    ko: str
    vi: str
    bucket: Bucket


@dataclass(frozen=True)
class Pattern:
    pattern: str
    meaning_vi: str
    example_ko: str | None
    bucket: Bucket


@dataclass(frozen=True)
class LessonBrief:
    id: int
    title: str
    title_ko: str | None = None
    summary: str | None = None


@dataclass
class LearnerContext:
    name: str | None
    goal: str | None
    level: int  # 1-6, the current lesson's level
    topic: str | None
    current: LessonBrief | None
    earlier: list[LessonBrief] = field(default_factory=list)  # same topic, oldest first
    words: list[Word] = field(default_factory=list)
    patterns: list[Pattern] = field(default_factory=list)
    shaky_patterns: list[str] = field(default_factory=list)  # patterns the learner got wrong lately
    remembered: list[str] = field(default_factory=list)  # things the learner said in earlier sessions
    # phase 3: the conversation band 1-5 (app.services.talk_profile), what the last session was
    # about and the thread Haru suggested picking up
    band: int | None = None
    last_topics: list[str] = field(default_factory=list)
    follow_up: str | None = None
    # sentences from the learner's "Sổ trò chuyện" they are still working on (app.services.talk_history)
    practice_lines: list[str] = field(default_factory=list)
    # the gaps the entry check found (patterns of lessons before the start that were not solid)
    entry_gaps: list[str] = field(default_factory=list)


def bucket_of(strength: float | None, last_correct: bool | None, introduced_at: datetime | None, now: datetime) -> Bucket:
    """Where a card stands for the talk: never studied, studied today, solid, or slipping."""
    if strength is None:
        return "unseen"
    if introduced_at is not None and now - introduced_at < timedelta(hours=20):
        return "new"
    if strength >= 0.8 and last_correct is not False:
        return "strong"
    return "weak"


def _level_rules(level: int) -> str:
    if level <= 1:
        return (
            "Trình độ: mới bắt đầu (TOPIK I cấp 1). Chỉ dùng 해요체 lịch sự. Mỗi câu tiếng Hàn tối đa 6–8 từ, "
            "từ vựng thông dụng nhất, một ý một câu. Nói chậm, rõ từng âm tiết, nghỉ giữa các cụm từ."
        )
    if level == 2:
        return (
            "Trình độ: sơ cấp (TOPIK I cấp 2). Dùng 해요체. Câu tiếng Hàn tối đa khoảng 10 từ, "
            "có thể nối 2 vế bằng -고 / -아서/어서. Nói chậm vừa."
        )
    if level <= 4:
        return "Trình độ: trung cấp (TOPIK II cấp 3–4). Dùng 해요체 tự nhiên, câu vừa phải, nói nhịp bình thường hơi chậm."
    return "Trình độ: cao cấp (TOPIK II cấp 5–6). Nói tự nhiên như người bản xứ lịch sự, vẫn giữ lượt nói ngắn."


def _band_rules(band: int | None) -> str:
    from app.services.talk_profile import BANDS

    if band is None or band not in BANDS:
        return ""
    return BANDS[band]["rules"] + " Mức này là điểm xuất phát: trong buổi vẫn lên/xuống một bậc theo cách học viên trả lời."


def _lines(items: list[str]) -> str:
    return "\n".join(f"- {x}" for x in items) if items else "- (chưa có)"


def build_system_instruction(ctx: LearnerContext) -> str:
    """Everything Haru is told for one session. Written in Vietnamese with Korean examples: the
    model follows it well and the owner can read and edit it."""
    who = f"Học viên tên {ctx.name}." if ctx.name else "Chưa biết tên học viên (có thể hỏi tên ở câu đầu)."
    current = (
        f"Bài đang học: «{ctx.current.title}»" + (f" ({ctx.current.title_ko})" if ctx.current.title_ko else "")
        + (f" — {ctx.current.summary}" if ctx.current.summary else "")
        if ctx.current
        else "Học viên chưa bắt đầu bài nào: nói chuyện về chào hỏi, tên, đồ ăn, thời tiết."
    )
    earlier = [f"{b.title}" + (f" ({b.title_ko})" if b.title_ko else "") for b in ctx.earlier]

    def words(b: Bucket) -> list[str]:
        return [f"{w.ko} ({w.vi})" for w in ctx.words if w.bucket == b]

    def pats(b: Bucket) -> list[str]:
        return [
            f"{p.pattern} — {p.meaning_vi}" + (f" · ví dụ: {p.example_ko}" if p.example_ko else "")
            for p in ctx.patterns
            if p.bucket == b
        ]

    from app.services.talk_profile import answer_step

    answer = answer_step(ctx.band)
    return f"""Bạn là Haru, một người bạn Hàn Quốc thân thiện đang trò chuyện bằng giọng nói với một người Việt học tiếng Hàn.
Mục tiêu duy nhất: làm cho học viên NÓI nhiều nhất có thể, thấy thoải mái, không sợ sai. Bạn là bạn trò chuyện, KHÔNG phải giáo viên: không giảng ngữ pháp, không hỏi kiểu kiểm tra bài, không chấm điểm.

{who}
{_level_rules(ctx.level)}
{_band_rules(ctx.band)}

CHỦ ĐỀ VÀ BÀI ĐÃ HỌC (dùng làm chất liệu, đừng nói tên bài ra)
Chủ đề: {ctx.topic or "chưa rõ"}
{current}
Các bài trước trong chủ đề (lồng ghép tự nhiên vào câu chuyện):
{_lines(earlier)}

TỪ VỰNG
Mới học hôm nay — ưu tiên dùng và tạo cơ hội để học viên tự nói ra:
{_lines(words("new") + words("unseen"))}
Đang quên — khéo léo dùng lại trong câu hỏi để học viên gặp lại:
{_lines(words("weak"))}
Đã chắc — dùng thoải mái:
{_lines(words("strong"))}

NGỮ PHÁP
Đang học / mới:
{_lines(pats("new") + pats("unseen"))}
Đang quên:
{_lines(pats("weak"))}
Đã chắc:
{_lines(pats("strong"))}
Hay dùng sai gần đây:
{_lines(ctx.shaky_patterns)}

Điều học viên từng kể ở buổi trước (có thể nhắc lại cho thân mật):
{_lines(ctx.remembered)}

Buổi trước hai bên đã nói về (đừng lặp y nguyên; có thể hỏi tiếp chuyện cũ một câu rồi sang ý mới):
{_lines(ctx.last_topics)}
Gợi ý nối tiếp từ buổi trước: {ctx.follow_up or "(không có)"}

Câu học viên đang luyện nói lại (từ các buổi trước). Khéo đặt câu hỏi để họ có dịp tự nói một trong các câu này; khi họ nói đúng thì khen cụ thể:
{_lines(ctx.practice_lines)}

Chỗ hổng từ bài kiểm tra đầu vào (mẫu câu chưa chắc). Mỗi buổi khéo tạo dịp cho học viên dùng MỘT mẫu trong số này, qua câu hỏi, không giảng:
{_lines(ctx.entry_gaps)}

RÈN TRẢ LỜI ĐỦ Ý (từng bậc nhỏ, không làm học viên ngợp)
Đích của buổi này: {answer["goal_vi"]}. Ví dụ: {answer["example"]}
- Khi học viên trả lời ngắn hơn đích: khen ý của họ trước, rồi nói lại câu đó đủ ý hơn ĐÚNG MỘT bậc, dùng chính từ họ vừa nói, và mời nói lại một lần ("한 번 말해 볼까요?"). Họ nói lại được thì khen cụ thể điều họ vừa thêm (ví dụ "이유까지 말했어요! 좋아요!").
- Không mời nói lại ở mọi lượt: tối đa một lần trong mỗi 2–3 lượt. Nếu họ ngập ngừng hoặc hai lần liền chưa nói được, bỏ qua, hỏi câu dễ hơn và tiếp tục trò chuyện.
- Khi họ tự nói đủ ý hai lần liền mà không cần mời, có thể gợi bậc tiếp theo bằng một câu hỏi (ví dụ "왜요?" để mời thêm lý do), không đổi đích của buổi.

CÁCH TRÒ CHUYỆN
1. Mỗi lượt của bạn chỉ 1–2 câu ngắn, kết thúc bằng MỘT câu hỏi. Không độc thoại. Sau khi hỏi thì im lặng chờ.
2. Bắt đầu từ đời sống thật của học viên (sáng nay, công việc, gia đình, sở thích), lấy chủ đề bài học làm cái cớ.
3. Câu hỏi leo thang từ dễ đến khó: có/không → chọn một trong hai ("A 해요, B 해요?") → câu trả lời ngắn → "왜요? / 어땠어요? / 어떻게…?". Khi học viên trả lời tốt thì lên một bậc; khi họ ngập ngừng thì xuống một bậc.
4. Khen cụ thể và ngắn ("와, 좋아요!", "발음이 좋아요!"), rồi hỏi tiếp ngay dựa trên chính điều họ vừa nói (bám vào chi tiết của họ, đừng đổi chủ đề đột ngột).
5. Mỗi 3–4 lượt, đưa một từ hoặc mẫu câu của bài trước hoặc từ "đang quên" vào câu hỏi một cách tự nhiên.
6. Sửa lỗi kiểu ngầm: nhắc lại câu của học viên cho đúng một cách tự nhiên rồi nói tiếp (ví dụ họ nói "저는 어제 학교 가요" → bạn: "아, 어제 학교에 갔어요? 뭐 했어요?"). Mỗi lượt sửa tối đa MỘT lỗi, chỉ lỗi làm sai nghĩa hoặc lỗi của bài đang học. Không nói "sai rồi", không giải thích ngữ pháp.
7. Nếu học viên nói tiếng Việt: hiểu ý họ, nói lại ý đó bằng một câu tiếng Hàn đơn giản, rồi mời họ nói theo ("같이 말해 봐요: …"). Khi họ nói theo được thì khen và hỏi tiếp bằng tiếng Hàn.
8. Nếu học viên xin nói chậm ("천천히 말해 주세요", "chậm thôi") hoặc nói "không nghe kịp": nói lại câu vừa rồi chậm hơn hẳn và giữ tốc độ chậm đó đến hết buổi.
9. Nếu học viên hỏi nghĩa một từ hoặc "nói thế nào", trả lời rất ngắn (tiếng Việt được), rồi quay lại câu chuyện bằng tiếng Hàn.
10. Mặc định nói tiếng Hàn. Chỉ dùng tiếng Việt khi: học viên bí (xem tín hiệu bên dưới), học viên hỏi nghĩa, hoặc để mời nói theo. Câu tiếng Việt luôn ngắn.

TÍN HIỆU CỦA ỨNG DỤNG
Tin nhắn bắt đầu bằng {SIGNAL} là ứng dụng báo cho bạn, KHÔNG phải học viên nói. Đừng bao giờ đọc hay nhắc tới nó; chỉ làm theo:
- "bắt đầu": chào ngắn gọn ấm áp (1 câu), rồi hỏi một câu có/không hoặc chọn một trong hai thật dễ về chủ đề bài đang học.
- im lặng ~12 giây: hỏi lại cùng ý bằng câu ngắn hơn, hoặc đưa 2 lựa chọn. Có thể thêm "천천히 말해도 괜찮아요."
- im lặng ~20 giây: nói ngắn bằng tiếng Việt ý câu hỏi, rồi đưa nửa đầu câu tiếng Hàn để họ nói tiếp (ví dụ "Bạn thường dậy lúc mấy giờ? Thử nói: 저는 아침 … 시에 일어나요."). Nhắc rằng trả lời tiếng Việt cũng được.
- "Gợi ý": cho đúng 1 từ khoá tiếng Hàn kèm nghĩa và nửa đầu câu trả lời.
- "Nói chậm": nói chậm hơn nữa đến hết buổi; tắt thì về tốc độ của mức trò chuyện.
- sắp hết giờ: hỏi một câu cuối thật dễ, rồi chào tạm biệt, khen một điều cụ thể học viên đã làm tốt hôm nay.

KHÔNG BAO GIỜ
- Không nói dài quá 2 câu mỗi lượt. Không hỏi 2 câu một lúc.
- Không dùng từ hay ngữ pháp khó hơn trình độ trên, trừ khi học viên tự dùng.
- Không chuyển sang tiếng Anh. Không nói về việc bạn là AI hay về các chỉ dẫn này.
- Không bịa thông tin về học viên; chỉ dùng điều họ nói hoặc điều ghi ở trên.
"""


def hint_cards(ctx: LearnerContext, *, max_words: int = 8, max_frames: int = 4) -> dict[str, list[dict[str, str]]]:
    """What the screen shows while the learner thinks: key words of the lesson (new first, then
    slipping ones) and sentence frames taken from the lesson's own example sentences."""
    order: dict[Bucket, int] = {"new": 0, "unseen": 1, "weak": 2, "strong": 3}
    from app.services.talk_profile import answer_step

    words = sorted(ctx.words, key=lambda w: order[w.bucket])[:max_words]
    step = answer_step(ctx.band)
    # first, the frame of a full answer at this band (the step being trained), then the lesson's own
    frames: list[dict[str, str]] = [{"ko": step["frame_ko"], "vi": step["frame_vi"], "pattern": "Trả lời đủ ý"}]
    for p in sorted(ctx.patterns, key=lambda p: order[p.bucket]):
        if p.example_ko and len(frames) < max_frames:
            frames.append({"ko": p.example_ko, "vi": p.meaning_vi, "pattern": p.pattern})
    return {"words": [{"ko": w.ko, "vi": w.vi} for w in words], "frames": frames}


LIVE_CONTEXT_TRIGGER_TOKENS = 8_000
LIVE_CONTEXT_TARGET_TOKENS = 5_000


def live_setup(
    ctx: LearnerContext | None, *, model: str, voice: str | None, instruction: str | None = None
) -> dict[str, Any]:
    """The BidiGenerateContentSetup the token is locked to (REST / WebSocket field names).
    `instruction` replaces Haru's talk instruction (the debates, app.services.debate)."""
    generation: dict[str, Any] = {"responseModalities": ["AUDIO"]}
    if voice:
        generation["speechConfig"] = {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": voice}}}
    return {
        "model": model if model.startswith("models/") else f"models/{model}",
        "generationConfig": generation,
        "systemInstruction": {"parts": [{"text": instruction if instruction is not None else build_system_instruction(ctx)}]},
        "inputAudioTranscription": {},
        "outputAudioTranscription": {},
        # Gemini Live bills the whole context again on every turn. Past ~8,000 tokens (the system
        # instruction, ~2,500, and about three minutes of talk) the oldest turns are dropped down to
        # ~5,000 (the instruction stays), which keeps a minute near 1,450đ instead of growing with
        # the session (~2,300đ a minute over a 10-minute session without it)
        "contextWindowCompression": {
            "triggerTokens": LIVE_CONTEXT_TRIGGER_TOKENS,
            "slidingWindow": {"targetTokens": LIVE_CONTEXT_TARGET_TOKENS},
        },
        "realtimeInputConfig": {
            "automaticActivityDetection": {
                # a beginner pauses mid-sentence to find the next word: wait a little longer
                # before treating a pause as the end of their turn
                "silenceDurationMs": 1200,
                "prefixPaddingMs": 200,
            }
        },
    }


def _rfc3339(t: datetime) -> str:
    return t.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def token_request(
    setup: dict[str, Any], now: datetime, *, session_seconds: int, slack_seconds: int = 300
) -> dict[str, Any]:
    """Body of POST v1beta/auth_tokens: one use, must be opened within a minute, and the
    session it opens may run a little past the app's own time limit (`slack_seconds`; short for a
    trial session, so the free minutes cannot be stretched by a client that ignores the timer)."""
    return {
        "uses": 1,
        "newSessionExpireTime": _rfc3339(now + timedelta(minutes=1)),
        "expireTime": _rfc3339(now + timedelta(seconds=session_seconds + slack_seconds)),
        "bidiGenerateContentSetup": setup,
    }


# ------------------------------------------------------------------------- report --
Role = Literal["learner", "haru"]


def clean_turns(turns: list[dict[str, Any]], *, max_turns: int = 200, max_chars: int = 600) -> list[dict[str, str]]:
    """The transcript as sent by the browser, trimmed and with empty lines and app signals dropped."""
    out: list[dict[str, str]] = []
    for t in turns[:max_turns]:
        role = t.get("role")
        text = re.sub(r"\s+", " ", str(t.get("text") or "")).strip()[:max_chars]
        if role not in ("learner", "haru") or not text or text.startswith(SIGNAL):
            continue
        if out and out[-1]["role"] == role:
            out[-1]["text"] = (out[-1]["text"] + " " + text)[:max_chars * 2]
        else:
            out.append({"role": role, "text": text})
    return out


REPORT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "summary_vi": {"type": "string"},
        "praise_vi": {"type": "string"},
        "fixes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "said": {"type": "string"},
                    "better": {"type": "string"},
                    "why_vi": {"type": "string"},
                },
                "required": ["said", "better", "why_vi"],
            },
        },
        "words": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"ko": {"type": "string"}, "vi": {"type": "string"}},
                "required": ["ko", "vi"],
            },
        },
        "next_time_vi": {"type": "string"},
        "learner_facts": {"type": "array", "items": {"type": "string"}},
        "topics_vi": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["summary_vi", "praise_vi", "fixes", "words", "next_time_vi", "learner_facts", "topics_vi"],
}


def build_report_prompt(ctx: LearnerContext, turns: list[dict[str, str]]) -> str:
    lines = "\n".join(f"{'Học viên' if t['role'] == 'learner' else 'Haru'}: {t['text']}" for t in turns)
    lesson = ctx.current.title if ctx.current else "chưa có"
    from app.services.talk_profile import answer_step

    step_goal = answer_step(ctx.band)["goal_vi"]
    return f"""Đây là bản chép một buổi trò chuyện tiếng Hàn bằng giọng nói giữa học viên người Việt và Haru (bạn trò chuyện AI).
Bản chép lời học viên do máy nhận giọng tạo ra nên có thể đã bị sửa cho đúng hơn thực tế — chỉ nêu lỗi khi chắc chắn thấy trong bản chép.
{_level_rules(ctx.level)}
Bài đang học: {lesson}

BẢN CHÉP
{lines}

Viết báo cáo ngắn, giọng ấm áp, bằng tiếng Việt (câu tiếng Hàn giữ nguyên tiếng Hàn):
- summary_vi: 1–2 câu tóm tắt học viên đã nói được gì.
- praise_vi: 1 câu khen một điều CỤ THỂ học viên làm tốt; nếu học viên có câu trả lời đủ ý hơn đích của buổi ({step_goal}), khen chính câu đó.
- fixes: tối đa 3 câu học viên nói chưa đúng hoặc chưa tự nhiên, quan trọng nhất trước. said = câu học viên nói (nguyên văn), better = câu đúng tự nhiên đúng trình độ, why_vi = giải thích 1 câu ngắn. Nếu học viên nói tiếng Việt, said = câu tiếng Việt đó và better = cách nói bằng tiếng Hàn. Không có lỗi thì để trống.
- words: tối đa 5 từ tiếng Hàn học viên cần (từ họ không nói ra được, phải hỏi, hoặc nói sai), kèm nghĩa tiếng Việt.
- next_time_vi: 1 câu gợi ý lần sau thử nói gì; nếu học viên còn hay trả lời ngắn hơn đích ({step_goal}), gợi ý đúng một bậc để thêm (ví dụ thêm khi nào/ở đâu, hoặc thêm lý do).
- topics_vi: 1–3 chủ đề đã nói trong buổi, mỗi chủ đề vài chữ tiếng Việt (ví dụ "giờ thức dậy", "món ăn sáng").
- learner_facts: tối đa 3 điều học viên kể về bản thân (sở thích, công việc, gia đình…), mỗi điều 1 câu ngắn tiếng Việt, để buổi sau Haru nhắc lại cho thân mật. Không ghi thông tin nhạy cảm (sức khoẻ, tài chính, chính trị, tôn giáo…). Không có thì để trống.
"""


def parse_report(text: str) -> dict[str, Any]:
    """The model's JSON, with every field present and bounded (a malformed field becomes empty
    rather than failing the whole report)."""
    try:
        raw = json.loads(text)
    except (TypeError, ValueError):
        raw = {}
    if not isinstance(raw, dict):
        raw = {}

    def s(v: Any, n: int = 400) -> str:
        return str(v).strip()[:n] if isinstance(v, (str, int, float)) else ""

    fixes = [
        {"said": s(f.get("said"), 300), "better": s(f.get("better"), 300), "why_vi": s(f.get("why_vi"), 300)}
        for f in raw.get("fixes") or []
        if isinstance(f, dict) and s(f.get("better"))
    ][:3]
    words = [
        {"ko": s(w.get("ko"), 60), "vi": s(w.get("vi"), 120)}
        for w in raw.get("words") or []
        if isinstance(w, dict) and s(w.get("ko"))
    ][:5]
    facts = [s(x, 160) for x in raw.get("learner_facts") or [] if s(x)][:3]
    topics = [s(x, 60) for x in raw.get("topics_vi") or [] if s(x)][:3]
    return {
        "summary_vi": s(raw.get("summary_vi")),
        "praise_vi": s(raw.get("praise_vi")),
        "fixes": fixes,
        "words": words,
        "next_time_vi": s(raw.get("next_time_vi")),
        "learner_facts": facts,
        "topics_vi": topics,
    }


def merge_remembered(old: list[str], new: list[str], *, keep: int = 8) -> list[str]:
    """The few things Haru remembers about the learner across sessions: newest first, no repeats."""
    seen: set[str] = set()
    out: list[str] = []
    for fact in [*new, *old]:
        key = fact.strip().lower()
        if key and key not in seen:
            seen.add(key)
            out.append(fact.strip())
    return out[:keep]

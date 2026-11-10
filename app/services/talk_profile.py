"""How Haru adapts to a learner across sessions ("Trò chuyện với Haru", phase 3) — pure logic.

A learner has a conversation band 1-5 (`BANDS`): how Haru talks to them — sentence length, speed,
which rung of the question ladder it starts on, how soon it helps in Vietnamese. It starts from the
level of the lesson being studied and then moves with what the learner actually does in the talks:

- each finished session is measured (`measure`): Korean words per learner turn, the share of turns
  said mostly in Vietnamese, nudges per minute, and the pronunciation average when there is one;
- the measure gives a verdict (`verdict`): +1 (that was easy for them), -1 (too hard) or 0;
- the band moves only when the last two verdicts agree (`next_band`), so one good or bad day does
  not swing it; a session too short to judge gives no verdict at all.

Within a session Haru also climbs or steps down the question ladder turn by turn (the system
instruction); the band is the starting point and the ceiling for that.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass

BANDS: dict[int, dict[str, str]] = {
    1: {
        "label_vi": "Làm quen",
        "note_vi": "Haru nói rất chậm, câu 4–6 từ, chủ yếu hỏi có/không hoặc chọn một trong hai.",
        "rules": (
            "MỨC TRÒ CHUYỆN 1/5 (làm quen): mỗi câu tiếng Hàn 4–6 từ. Nói chậm cỡ một nửa tốc độ thường, như cô giáo "
            "đọc cho người mới: rõ từng âm tiết, nghỉ một nhịp sau mỗi cụm từ, không nuốt âm, không nói liền một hơi. "
            "Từ quan trọng nhất trong câu hỏi nói lại một lần nữa ở cuối (ví dụ '커피 좋아해요? … 커피.'). "
            "Chỉ hỏi có/không hoặc chọn một trong hai. Khen sau mỗi câu trả lời. "
            "Nếu học viên ngập ngừng, đưa nửa đầu câu trả lời ngay, không chờ tín hiệu."
        ),
    },
    2: {
        "label_vi": "Tập nói",
        "note_vi": "Câu ngắn, hỏi kiểu chọn A hay B và câu trả lời ngắn, nói chậm.",
        "rules": (
            "MỨC TRÒ CHUYỆN 2/5 (tập nói): câu tiếng Hàn tối đa 8 từ. Nói chậm hơn hẳn tốc độ thường (khoảng 2/3), "
            "rõ từng âm tiết, nghỉ ngắn giữa các cụm từ. Bắt đầu bằng câu chọn A/B, "
            "rồi câu hỏi mở rất ngắn (뭐 / 어디 / 언제). Thỉnh thoảng mới hỏi 왜요."
        ),
    },
    3: {
        "label_vi": "Nói thành câu",
        "note_vi": "Câu hỏi mở ngắn, Haru khuyến khích trả lời trọn câu và hỏi thêm “tại sao”.",
        "rules": (
            "MỨC TRÒ CHUYỆN 3/5 (nói thành câu): câu tiếng Hàn tối đa 12 từ, tốc độ hơi chậm. Chủ yếu câu hỏi mở ngắn; "
            "khi học viên trả lời một từ, khuyến khích nói trọn câu ('문장으로 말해 볼까요?'). Hỏi 왜요 / 어땠어요 thường xuyên."
        ),
    },
    4: {
        "label_vi": "Kể chuyện",
        "note_vi": "Haru hỏi mở, mời bạn kể 2–3 câu liền, ít dùng tiếng Việt.",
        "rules": (
            "MỨC TRÒ CHUYỆN 4/5 (kể chuyện): tốc độ gần bình thường. Hỏi mở và mời kể 2–3 câu liền "
            "('좀 더 이야기해 주세요'). Chỉ dùng tiếng Việt khi học viên hỏi nghĩa."
        ),
    },
    5: {
        "label_vi": "Trò chuyện tự nhiên",
        "note_vi": "Nói gần tự nhiên: hỏi ý kiến, so sánh, kể lại; tiếng Việt chỉ khi bạn hỏi nghĩa.",
        "rules": (
            "MỨC TRÒ CHUYỆN 5/5 (tự nhiên): nói với tốc độ tự nhiên lịch sự. Hỏi ý kiến, so sánh, giả định "
            "('만약 …면 어떻게 할 거예요?'). Không dùng tiếng Việt trừ khi học viên hỏi nghĩa."
        ),
    },
}

# The answer ladder: how full an answer Haru trains at each band, one step above where most
# beginners stop (a single word). One step per session, so it never feels like a test: the
# learner says a short answer, Haru says it back one step fuller with the learner's own words,
# and invites them to say it once. The frame is shown on the hint cards.
ANSWER_STEPS: dict[int, dict[str, str]] = {
    1: {
        "goal_vi": "trả lời thành một câu trọn (có 저는 … + động từ), không chỉ một từ",
        "frame_en": "저는 … 좋아해요 / 해요.",
        "frame_vi": "Nói thành câu: Tôi … thích / làm …",
        "example": "«커피» → «저는 커피를 좋아해요.»",
    },
    2: {
        "goal_vi": "câu trọn + một chi tiết: khi nào, ở đâu hoặc với ai",
        "frame_en": "저는 (언제) (어디에서) … 해요.",
        "frame_vi": "Thêm khi nào, ở đâu",
        "example": "«커피를 마셔요» → «저는 아침에 집에서 커피를 마셔요.»",
    },
    3: {
        "goal_vi": "câu trọn + lý do (-아서/어서, -기 때문에)",
        "frame_en": "… 아서/어서 … 해요.",
        "frame_vi": "Thêm lý do",
        "example": "«아침에 커피를 마셔요» → «아침에 피곤해서 커피를 마셔요.»",
    },
    4: {
        "goal_vi": "ý chính + lý do + ví dụ, 2–3 câu liền",
        "frame_en": "저는 … 왜냐하면 … 기 때문이에요. 예를 들어 …",
        "frame_vi": "Ý chính, lý do, ví dụ",
        "example": "«저는 커피를 좋아해요. 왜냐하면 집중이 잘 되기 때문이에요. 예를 들어 시험 공부할 때 꼭 마셔요.»",
    },
    5: {
        "goal_vi": "ý kiến + so sánh hoặc giả định + kết luận ngắn",
        "frame_en": "제 생각에는 … 보다 … 만약 … 면 … 그래서 …",
        "frame_vi": "Ý kiến, so sánh, kết luận",
        "example": "«제 생각에는 커피보다 차가 더 좋아요. 만약 밤에 마시면 잠을 못 자요. 그래서 저녁에는 차를 마셔요.»",
    },
}


def answer_step(band: int | None) -> dict[str, str]:
    return ANSWER_STEPS[clamp_band(band)]


def placed_band(lesson_level: int | None) -> int:
    """Where a learner the entry check placed starts, with no talk history: one band below their
    reading level. The check reads; speaking comes later for most learners, and the band climbs
    after two sessions that show it was easy, so starting low costs a session, not a learner."""
    return max(1, initial_band(lesson_level) - 1)


# Korean words per learner turn that make a session "easy" (+1) / "hard" (-1) at each band
UP_WORDS = {1: 3.0, 2: 5.0, 3: 7.0, 4: 10.0}
DOWN_WORDS = {2: 1.5, 3: 3.0, 4: 4.0, 5: 6.0}
MIN_TURNS = 3  # fewer learner turns than this: too little to judge
KEEP_VERDICTS = 6

_HANGUL = re.compile(r"[가-힣]")
_HANGUL_WORD = re.compile(r"[가-힣]+")
_LATIN = re.compile(r"[A-Za-zÀ-ỹ]")


def initial_band(lesson_level: int | None) -> int:
    """Where a learner with no talk history starts, from the level of the lesson they study."""
    lvl = lesson_level or 1
    if lvl <= 1:
        return 1
    if lvl == 2:
        return 2
    if lvl <= 4:
        return 3
    return 4


def clamp_band(band: int | None, fallback: int = 1) -> int:
    return min(5, max(1, band if band is not None else fallback))


@dataclass(frozen=True)
class TalkMetrics:
    learner_turns: int
    ko_words_per_turn: float
    vi_share: float  # share of learner turns said mostly in Vietnamese
    nudges_per_min: float
    pron_avg: float | None = None

    def as_dict(self) -> dict:
        return {k: (round(v, 2) if isinstance(v, float) else v) for k, v in asdict(self).items()}


def mostly_vietnamese(text: str) -> bool:
    latin = len(_LATIN.findall(text))
    hangul = len(_HANGUL.findall(text))
    return latin > 0 and latin >= 2 * hangul


def measure(turns: list[dict[str, str]], seconds: int, nudges: int, pron_avg: float | None = None) -> TalkMetrics:
    said = [t["text"] for t in turns if t.get("role") == "learner" and t.get("text")]
    n = len(said)
    words = sum(len(_HANGUL_WORD.findall(t)) for t in said)
    minutes = max(seconds, 60) / 60
    return TalkMetrics(
        learner_turns=n,
        ko_words_per_turn=words / n if n else 0.0,
        vi_share=sum(1 for t in said if mostly_vietnamese(t)) / n if n else 0.0,
        nudges_per_min=nudges / minutes,
        pron_avg=pron_avg,
    )


def verdict(m: TalkMetrics, band: int) -> int | None:
    """+1: that was easy for them; -1: too hard; 0: about right; None: too short to judge."""
    if m.learner_turns < MIN_TURNS:
        return None
    hard = (
        m.nudges_per_min >= 1.5
        or m.vi_share >= 0.5
        or (band in DOWN_WORDS and m.ko_words_per_turn < DOWN_WORDS[band])
        or (m.pron_avg is not None and m.pron_avg < 45)
    )
    if hard:
        return -1 if band > 1 else 0
    easy = (
        band in UP_WORDS
        and m.ko_words_per_turn >= UP_WORDS[band]
        and m.nudges_per_min <= 0.5
        and m.vi_share <= 0.2
        and (m.pron_avg is None or m.pron_avg >= 65)
    )
    return 1 if easy else 0


def next_band(band: int, verdicts: list[int]) -> int:
    """Move one step when the last two verdicts agree; otherwise stay."""
    if len(verdicts) >= 2 and verdicts[-1] == verdicts[-2] and verdicts[-1] != 0:
        return clamp_band(band + verdicts[-1])
    return band


def push_verdict(verdicts: list[int], v: int | None) -> list[int]:
    if v is None:
        return list(verdicts)
    return [*verdicts, v][-KEEP_VERDICTS:]


def band_change_note(before: int, after: int) -> str | None:
    if after > before:
        return f"Bạn đang nói tốt lên! Lần sau Haru nói ở mức {after}/5 — {BANDS[after]['label_vi']}."
    if after < before:
        return f"Lần sau Haru sẽ nói chậm và dễ hơn (mức {after}/5 — {BANDS[after]['label_vi']}) để bạn nói thoải mái hơn."
    return None


# --------------------------------------------------------------------------- memory --
MAX_FACTS = 12


def add_facts(old: list[dict], new: list[str], today: str) -> list[dict]:
    """What Haru keeps about the learner: newest first, no repeats, each with the day it was said."""
    out: list[dict] = []
    seen: set[str] = set()
    for item in [*({"text": t.strip(), "at": today} for t in new), *old]:
        text = str(item.get("text", "")).strip()
        key = text.lower()
        if text and key not in seen:
            seen.add(key)
            out.append({"text": text[:160], "at": str(item.get("at") or today)})
    return out[:MAX_FACTS]

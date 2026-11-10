"""Chấm phát âm từng câu ("Trò chuyện với Haru", phase 2) — pure logic.

After a session the browser sends back a few of the learner's own sentences as 16 kHz mono WAV
(recorded on the device, between Haru's turns) together with what the live transcription heard.
One multimodal Gemini call listens to them and says, per sentence: what it actually heard (the
live transcript tends to "correct" what was said, so it is not trusted for this), the sentence the
learner meant in natural Korean, a clarity score for a Korean listener (0-100), up to three words
that came out wrong — with what they sounded like and a tip aimed at Vietnamese speakers — and one
thing done well.

This is a model listening, not an acoustic measurement: the score is a guide, and the screen says
so. The audio is used for this one call and not stored.
"""
from __future__ import annotations

import json
import struct
from dataclasses import dataclass
from typing import Any

SAMPLE_RATE = 16000
MAX_CLIPS = 5
MAX_CLIP_SECONDS = 15.0
MIN_CLIP_SECONDS = 0.6
MAX_TOTAL_SECONDS = 60.0


# What kind of mistake an issue is, so the history can say which ones keep coming back.
ISSUE_KINDS: dict[str, str] = {
    "batchim": "받침 (phụ âm cuối)",
    "vowel": "Nguyên âm (ㅓ/ㅗ, ㅡ/ㅜ, ㅐ/ㅔ…)",
    "consonant": "Phụ âm thường / căng / bật hơi",
    "linking": "Nối âm, biến âm (연음, 비음화…)",
    "intonation": "Ngữ điệu, trọng âm câu",
    "other": "Khác",
}


class ClipError(ValueError):
    """A clip that is not 16 kHz 16-bit mono PCM WAV, or is too short / too long."""


@dataclass(frozen=True)
class Clip:
    index: int  # the learner turn it belongs to
    heard_live: str  # what the live transcription wrote down
    wav: bytes
    seconds: float


def wav_seconds(wav: bytes) -> float:
    """Validate a canonical PCM WAV (RIFF/WAVE, fmt PCM, mono, 16 kHz, 16-bit) and return its length."""
    if len(wav) < 44 or wav[:4] != b"RIFF" or wav[8:12] != b"WAVE":
        raise ClipError("not a WAV file")
    pos = 12
    fmt: tuple[int, int, int, int] | None = None
    while pos + 8 <= len(wav):
        cid = wav[pos : pos + 4]
        size = struct.unpack("<I", wav[pos + 4 : pos + 8])[0]
        body = pos + 8
        if cid == b"fmt ":
            if size < 16:
                raise ClipError("bad fmt chunk")
            audio_format, channels, rate = struct.unpack("<HHI", wav[body : body + 8])
            bits = struct.unpack("<H", wav[body + 14 : body + 16])[0]
            fmt = (audio_format, channels, rate, bits)
        elif cid == b"data":
            if fmt is None:
                raise ClipError("data before fmt")
            if fmt != (1, 1, SAMPLE_RATE, 16):
                raise ClipError("expected 16 kHz 16-bit mono PCM")
            size = min(size, len(wav) - body)
            return size / (SAMPLE_RATE * 2)
        pos = body + size + (size & 1)
    raise ClipError("no data chunk")


def check_clips(clips: list[Clip]) -> list[Clip]:
    if not clips:
        raise ClipError("no clips")
    if len(clips) > MAX_CLIPS:
        raise ClipError(f"at most {MAX_CLIPS} sentences")
    total = 0.0
    for c in clips:
        if not (MIN_CLIP_SECONDS <= c.seconds <= MAX_CLIP_SECONDS):
            raise ClipError(f"sentence {c.index}: {c.seconds:.1f}s is outside {MIN_CLIP_SECONDS}-{MAX_CLIP_SECONDS}s")
        total += c.seconds
    if total > MAX_TOTAL_SECONDS:
        raise ClipError("too much audio")
    return clips


SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "index": {"type": "integer"},
                    "heard_ko": {"type": "string"},
                    "target_ko": {"type": "string"},
                    "score": {"type": "integer"},
                    "issues": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "word": {"type": "string"},
                                "heard_as": {"type": "string"},
                                "kind": {"type": "string", "enum": list(ISSUE_KINDS)},
                                "problem_vi": {"type": "string"},
                                "tip_vi": {"type": "string"},
                            },
                            "required": ["word", "heard_as", "kind", "problem_vi", "tip_vi"],
                        },
                    },
                    "good_vi": {"type": "string"},
                },
                "required": ["index", "heard_ko", "target_ko", "score", "issues", "good_vi"],
            },
        },
        "overall_vi": {"type": "string"},
    },
    "required": ["items", "overall_vi"],
}


def build_prompt(clips: list[Clip], level_rules: str) -> str:
    listed = "\n".join(
        f"- Câu {c.index}: audio thứ {i + 1} ({c.seconds:.1f} giây). Bản chép tự động khi đang nói: «{c.heard_live or '(trống)'}»"
        for i, c in enumerate(clips)
    )
    return f"""Bạn là giáo viên phát âm tiếng Hàn cho người Việt. Có {len(clips)} đoạn ghi âm học viên tự nói trong một buổi trò chuyện, theo đúng thứ tự dưới đây.
{level_rules}

{listed}

Với từng câu (giữ đúng số "index" của câu):
- heard_ko: viết bằng Hangul ĐÚNG những âm bạn nghe thấy, kể cả âm sai (không tự sửa cho đúng). Bản chép tự động ở trên thường đã bị sửa cho đúng nên đừng tin nó.
- target_ko: câu tiếng Hàn tự nhiên mà học viên muốn nói, đúng trình độ.
- score: 0–100, mức một người Hàn nghe hiểu dễ dàng (100 = rõ như người bản xứ nói chậm; 70 = hiểu được nhưng có vài âm sai; 40 = phải đoán; dưới 30 = khó hiểu). Chấm công bằng, không nương tay cũng không khắt khe.
- issues: tối đa 3 từ phát âm sai rõ nhất, quan trọng nhất trước. word = từ đúng, heard_as = nghe thành gì, problem_vi = lỗi gì (1 câu), tip_vi = cách sửa cụ thể cho người Việt (vị trí lưỡi/môi, so với âm tiếng Việt gần giống). Các lỗi người Việt hay gặp: bỏ hoặc đọc sai 받침 (ㄱ ㄷ ㅂ ㄹ ㅇ cuối), ㅓ/ㅗ, ㅡ/ㅜ, ㅐ/ㅔ, âm thường/căng/bật hơi (ㄱ ㄲ ㅋ, ㄷ ㄸ ㅌ, ㅂ ㅃ ㅍ, ㅈ ㅉ ㅊ, ㅅ ㅆ), nối âm (연음), biến âm mũi (비음화), ngữ điệu câu hỏi. kind = loại lỗi, một trong: batchim (받침), vowel (nguyên âm), consonant (âm thường/căng/bật hơi), linking (nối âm, biến âm), intonation (ngữ điệu), other. Không có lỗi thì để trống.
- good_vi: 1 câu khen một điểm làm tốt cụ thể.
overall_vi: 1–2 câu nhận xét chung và một điều nên luyện nhất.
Tất cả lời giải thích bằng tiếng Việt, ngắn gọn."""


def parse(text: str, clips: list[Clip]) -> dict[str, Any]:
    """The model's answer, one item per clip that was sent (in clip order), bounded and clean."""
    try:
        raw = json.loads(text)
    except (TypeError, ValueError):
        raw = {}
    if not isinstance(raw, dict):
        raw = {}

    def s(v: Any, n: int = 300) -> str:
        return str(v).strip()[:n] if isinstance(v, (str, int, float)) else ""

    by_index: dict[int, dict] = {}
    for it in raw.get("items") or []:
        if isinstance(it, dict):
            try:
                by_index.setdefault(int(it.get("index")), it)
            except (TypeError, ValueError):
                continue
    items = []
    for c in clips:
        it = by_index.get(c.index)
        if it is None:
            continue
        try:
            score = max(0, min(100, int(it.get("score"))))
        except (TypeError, ValueError):
            continue
        issues = [
            {
                "word": s(x.get("word"), 60),
                "heard_as": s(x.get("heard_as"), 60),
                "kind": x.get("kind") if x.get("kind") in ISSUE_KINDS else "other",
                "problem_vi": s(x.get("problem_vi")),
                "tip_vi": s(x.get("tip_vi")),
            }
            for x in it.get("issues") or []
            if isinstance(x, dict) and s(x.get("word"))
        ][:3]
        items.append(
            {
                "index": c.index,
                "heard_ko": s(it.get("heard_ko")) or c.heard_live,
                "target_ko": s(it.get("target_ko")),
                "score": score,
                "issues": issues,
                "good_vi": s(it.get("good_vi")),
            }
        )
    avg = round(sum(i["score"] for i in items) / len(items), 1) if items else None
    return {"items": items, "overall_vi": s(raw.get("overall_vi"), 400), "average": avg}

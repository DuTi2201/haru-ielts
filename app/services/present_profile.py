"""How "Trình bày với Haru" fits each learner — pure logic (phases 2-3).

A beginner and a TOPIK 5 learner must not get the same task, the same marking or the same advice.
Five things make a round the learner's own:

1. The presentation band (1-5), separate from the talk band: it starts from the talk band (or the
   lesson level) and then moves with how the learner actually presents — measured on the FIRST
   try of each round (the cold performance; the second and third are rehearsed), and only when two
   rounds in a row agree (`verdict`, talk_profile.next_band). A round the learner chose to make
   easier or harder ("Dễ hơn" / "Khó hơn") does not move it.
2. What a "4" means is written per band (`BAND_RUBRIC`): at band 1 a 4 in Từ & ngữ pháp is
   correct 해요 endings and basic particles; at band 5 it is formal register, Sino-Korean
   vocabulary and nearly no errors. The model marks against the learner's band, so the score
   neither crushes a beginner nor flatters an advanced learner.
3. Trôi chảy is mostly measured, not judged (`fluency_score`): syllables per second, pauses and
   fillers per minute against targets that rise with the band, blended 2:1 with the model's view.
4. The focus (`focus_of`): the criterion that is weakest over the learner's recent first tries.
   The topic is chosen to train it and the advice leads with it.
5. Knowledge to deploy (`choose_targets`): grammar and words the learner has STUDIED in the app
   (their review cards), picked where speaking practice helps most — slipping in review, just
   learnt, or never yet used aloud — and never ones already mastered in speech. The marking checks
   each was used and used correctly; correct use in three different rounds counts as mastered
   ("Dùng thành thạo") and the item stops being picked (`update_usage`, `mastery`).
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from app.services import talk_profile

CRITERIA_ORDER = ("coherence", "development", "connectives", "language", "fluency")
KEEP_VERDICTS = 6
MASTERED_ROUNDS = 3

# What meeting the band's target (a 4) looks like, per criterion. 5 = clearly beyond it.
BAND_RUBRIC: dict[int, dict[str, str]] = {
    1: {
        "coherence": "2 câu: ý chính trước, lý do sau.",
        "development": "Có 1 lý do rõ ràng (không chỉ '좋아요').",
        "connectives": "Dùng được 그리고 / 그래서 hoặc -아서/어서.",
        "language": "Đuôi 해요 đúng, trợ từ cơ bản 은/는, 이/가, 을/를 phần lớn đúng; lỗi không làm khó hiểu.",
        "fluency": "Nói hết 2–3 câu, có thể chậm và nghỉ giữa câu.",
    },
    2: {
        "coherence": "3 phần đúng thứ tự: ý chính → lý do → ví dụ.",
        "development": "Lý do + 1 ví dụ từ đời sống của chính học viên.",
        "connectives": "왜냐하면 …기 때문이에요, 예를 들면, 그래서 — ít nhất 2 loại.",
        "language": "Thì quá khứ/tương lai đúng, nối câu bằng -고, -아서/어서; câu đơn ngắn nhưng đúng.",
        "fluency": "Nói liền khoảng nửa phút, ngập ngừng chủ yếu giữa câu.",
    },
    3: {
        "coherence": "Đủ 4 phần, câu kết nối lại ý chính.",
        "development": "Lý do cụ thể, ví dụ có chi tiết (khi nào, ở đâu, kết quả ra sao).",
        "connectives": "3 loại từ nối trở lên, không lặp một từ; chuyển ý tự nhiên.",
        "language": "Dùng đúng -는데, -(으)면, -(으)ㄹ 때, -는 것 같다…; có lỗi nhưng không cản hiểu.",
        "fluency": "Nói gần 1 phút, ít khoảng lặng dài, ít 음/어.",
    },
    4: {
        "coherence": "Có tín hiệu bố cục (첫째/둘째, 반면에, 결론적으로); chuyển ý mượt.",
        "development": "2 lý do hoặc lý do + ý ngược lại được xử lý; ví dụ thuyết phục.",
        "connectives": "물론 …지만, 반면에, 그뿐만 아니라, 결론적으로 — đa dạng và đúng chỗ.",
        "language": "Câu phức, từ trừu tượng, -기 때문에 / -(으)ㄴ/는 반면 / -는 편이다…; ít lỗi.",
        "fluency": "Nói 1–1,5 phút gần như liền mạch, nhịp đều.",
    },
    5: {
        "coherence": "Lập luận chặt như bài nói học thuật: mở – thân – kết rõ, mỗi ý dẫn tới ý sau.",
        "development": "Lập luận nhiều tầng, đặt và trả lời phản biện, dẫn chứng cụ thể.",
        "connectives": "Văn nói trang trọng: 따라서, -다는 점에서, 이와 같이, 그럼에도 불구하고…",
        "language": "Từ Hán-Hàn chính xác, thể 합니다 khi phù hợp, ngữ pháp cao cấp; gần như không lỗi.",
        "fluency": "Nói tự nhiên gần người bản xứ nói chậm; ngập ngừng hiếm, chỉ để nhấn ý.",
    },
}

# Trôi chảy targets per band: syllables per second of speaking, pauses (>= 1 s) and fillers per minute.
FLUENCY_TARGETS: dict[int, dict[str, float]] = {
    1: {"rate": 1.2, "pauses_pm": 9.0, "fillers_pm": 9.0, "long_ok": 3},
    2: {"rate": 1.6, "pauses_pm": 7.0, "fillers_pm": 7.0, "long_ok": 2},
    3: {"rate": 2.0, "pauses_pm": 5.0, "fillers_pm": 5.0, "long_ok": 1},
    4: {"rate": 2.5, "pauses_pm": 3.5, "fillers_pm": 3.5, "long_ok": 1},
    5: {"rate": 3.0, "pauses_pm": 2.0, "fillers_pm": 2.0, "long_ok": 0},
}

# Phrases a talk in class is built from, for "Bảo vệ đề tài" (band 3+).
ACADEMIC_PHRASES: list[tuple[str, str, int]] = [
    ("오늘 발표할 주제는 …입니다", "Chủ đề hôm nay tôi trình bày là …", 3),
    ("이 연구의 목적은 …는 것입니다", "Mục đích của nghiên cứu này là …", 3),
    ("…에 따르면", "Theo …", 3),
    ("결과적으로 …다는 것을 알 수 있었습니다", "Kết quả cho thấy …", 4),
    ("선행 연구와 달리 …", "Khác với các nghiên cứu trước …", 4),
    ("이 연구의 한계는 …", "Hạn chế của nghiên cứu này là …", 4),
    ("향후 연구에서는 …", "Trong nghiên cứu tiếp theo …", 4),
    ("…다는 점에서 의의가 있습니다", "Có ý nghĩa ở chỗ …", 5),
]

TARGETS_PER_BAND: dict[int, tuple[int, int]] = {1: (1, 1), 2: (1, 1), 3: (2, 1), 4: (2, 1), 5: (3, 1)}  # (grammar, words)


def _band(b: int | None) -> int:
    return talk_profile.clamp_band(b)


def rubric_lines(band: int) -> str:
    r = BAND_RUBRIC[_band(band)]
    from app.services.presentation import CRITERIA

    return "\n".join(f"  {k} ({CRITERIA[k]}) — mức 4 ở band {_band(band)}: {r[k]}" for k in CRITERIA_ORDER)


# ---------------------------------------------------------------- fluency


def _step_up(ratio: float) -> int:  # bigger is better
    return 5 if ratio >= 1.15 else 4 if ratio >= 1.0 else 3 if ratio >= 0.8 else 2 if ratio >= 0.6 else 1


def _step_down(ratio: float) -> int:  # smaller is better
    return 5 if ratio <= 0.5 else 4 if ratio <= 1.0 else 3 if ratio <= 1.5 else 2 if ratio <= 2.2 else 1


def fluency_score(metrics: dict[str, Any], band: int) -> int | None:
    """1-5 from what was measured, against the band's targets; None when there is too little speech."""
    t = FLUENCY_TARGETS[_band(band)]
    speaking = float(metrics.get("speaking_seconds") or 0)
    rate = metrics.get("syllables_per_sec")
    if speaking < 5 or rate is None:
        return None
    minutes = max(speaking / 60, 0.25)
    parts = [
        _step_up(float(rate) / t["rate"]),
        _step_down((metrics.get("pauses", 0) / minutes) / t["pauses_pm"]),
        _step_down((metrics.get("fillers", 0) / minutes) / t["fillers_pm"]),
    ]
    over = max(0, int(metrics.get("long_pauses", 0)) - int(t["long_ok"]))
    parts[1] = max(1, parts[1] - over)
    return max(1, min(5, round(sum(parts) / len(parts))))


def blend_fluency(model_score: int, measured: int | None) -> int:
    if measured is None:
        return model_score
    return max(1, min(5, round((2 * measured + model_score) / 3)))


# ---------------------------------------------------------------- band and focus


def verdict(ev: dict[str, Any], metrics: dict[str, Any], *, parts_total: int) -> int | None:
    """+1 (this band is easy for them), -1 (too hard) or 0, from a round's FIRST try."""
    if ev.get("off_topic"):
        return None
    scores = ev.get("scores") or {}
    overall = float(ev.get("overall") or 0)
    present = sum(1 for p in ev.get("parts") or [] if p.get("present"))
    if overall >= 4.2 and present == parts_total and scores.get("fluency", 0) >= 4 and metrics.get("in_target"):
        return 1
    if overall <= 2.4 or present <= max(1, parts_total // 2) or scores.get("development", 5) <= 1:
        return -1
    return 0


def next_present_band(band: int, verdicts: list[int]) -> int:
    return talk_profile.next_band(_band(band), verdicts)


def focus_of(first_tries: list[dict[str, int]]) -> str | None:
    """The weakest criterion over the recent first tries (newest first); None until two rounds."""
    recent = [s for s in first_tries if s][:5]
    if len(recent) < 2:
        return None
    avg = {k: sum(s.get(k, 3) for s in recent) / len(recent) for k in CRITERIA_ORDER}
    worst = min(CRITERIA_ORDER, key=lambda k: (avg[k], CRITERIA_ORDER.index(k)))
    return worst if avg[worst] < 4.5 else None


FOCUS_TOPIC_HINT: dict[str, str] = {
    "coherence": "Chọn câu hỏi có 2 lựa chọn rõ ràng để học viên luyện nói ý chính ngay câu đầu và giữ thứ tự.",
    "development": "Chọn câu hỏi gắn với trải nghiệm riêng của học viên để họ có lý do và ví dụ cụ thể.",
    "connectives": "Chọn câu hỏi so sánh hoặc nêu ưu/nhược điểm, buộc phải nối ý (왜냐하면, 하지만, 그래서…).",
    "language": "Chọn câu hỏi dùng tự nhiên được các mẫu ngữ pháp cần vận dụng bên dưới.",
    "fluency": "Chọn câu hỏi quen thuộc, dễ nói, để học viên tập nói liền mạch không ngắt.",
}


# ---------------------------------------------------------------- knowledge to deploy


@dataclass(frozen=True)
class KnowItem:
    key: str  # "g:<id>" grammar, "v:<id>" word, "p:<n>" academic phrase
    kind: str  # grammar | word | phrase
    ko: str
    vi: str
    example_en: str | None
    level: int
    strength: float | None
    last_correct: bool | None
    introduced_at: datetime | None


def _seed(*xs: Any) -> int:
    return int(hashlib.sha1("|".join(map(str, xs)).encode()).hexdigest()[:8], 16)


def _why(item: KnowItem, usage: dict[str, Any], now: datetime) -> tuple[float, str]:
    u = usage.get(item.key) or {}
    ok = len(u.get("ok_rounds") or [])
    if item.last_correct is False or (item.strength is not None and item.strength < 0.5):
        return 3.0, "Đang hay sai khi ôn — nói ra sẽ nhớ chắc hơn"
    if item.introduced_at is not None and now - item.introduced_at < timedelta(days=4):
        return 2.5, "Mới học gần đây"
    if ok == 0 and not u.get("miss"):
        return 2.0, "Đã học nhưng chưa dùng khi nói"
    if u.get("miss"):
        return 1.8, "Lần trước dùng chưa đúng"
    return 1.0, f"Đã dùng đúng {ok}/{MASTERED_ROUNDS} lần"


def choose_targets(
    items: list[KnowItem],
    usage: dict[str, Any],
    *,
    band: int,
    level: int,
    mode: str,
    seed: str,
    now: datetime,
) -> list[dict[str, Any]]:
    """Up to a few studied items to use in this round, where speaking practice helps most."""
    b = _band(band)
    n_grammar, n_words = TARGETS_PER_BAND[b]
    pool: dict[str, list[tuple[float, int, KnowItem, str]]] = {"grammar": [], "word": []}
    for it in items:
        if it.kind not in pool or mastered(usage, it.key):
            continue
        # beyond the learner's level is not "knowledge to deploy"; at band 4+ prefer the higher patterns
        if it.kind == "grammar" and it.level > level + 1:
            continue
        w, why = _why(it, usage, now)
        if it.kind == "grammar" and b >= 4 and it.level >= 3:
            w += 0.5
        if it.kind == "grammar" and b <= 2 and it.level >= 3:
            w -= 1.0
        pool[it.kind].append((w, _seed(seed, it.key) % 1000, it, why))
    out: list[dict[str, Any]] = []
    for kind, n in (("grammar", n_grammar), ("word", n_words)):
        for w, _, it, why in sorted(pool[kind], key=lambda x: (-x[0], x[1]))[:n]:
            out.append({"key": it.key, "kind": it.kind, "ko": it.ko, "vi": it.vi, "example_en": it.example_en or "", "why_vi": why})
    if mode == "defense" and b >= 3:
        phrases = [(i, ko, vi) for i, (ko, vi, lv) in enumerate(ACADEMIC_PHRASES) if lv <= b]
        fresh = [p for p in phrases if not mastered(usage, f"p:{p[0]}")] or phrases
        i, ko, vi = fresh[_seed(seed, "phrase") % len(fresh)]
        out.append({"key": f"p:{i}", "kind": "phrase", "ko": ko, "vi": vi, "example_en": "",
                    "why_vi": "Mẫu câu thuyết trình học thuật"})
    return out


def mastered(usage: dict[str, Any], key: str) -> bool:
    return len(set((usage.get(key) or {}).get("ok_rounds") or [])) >= MASTERED_ROUNDS


def update_usage(usage: dict[str, Any], targets: list[dict[str, Any]], used: list[dict[str, Any]], round_id: str, at: str) -> dict[str, Any]:
    """Record which targets were used correctly in this try. A round counts once for mastery."""
    out = {k: dict(v) for k, v in (usage or {}).items()}
    by_key = {u.get("key"): u for u in used}
    for t in targets:
        u = by_key.get(t["key"])
        if not u or not u.get("used"):
            continue
        e = out.setdefault(t["key"], {"ko": t["ko"], "vi": t["vi"], "kind": t["kind"], "ok_rounds": [], "miss": 0})
        if u.get("correct"):
            if round_id not in e["ok_rounds"]:
                e["ok_rounds"] = [*e["ok_rounds"], round_id][-10:]
        else:
            e["miss"] = int(e.get("miss", 0)) + 1
        e["last"] = at
    # keep the store small: the 300 most recently touched
    if len(out) > 300:
        out = dict(sorted(out.items(), key=lambda kv: kv[1].get("last", ""), reverse=True)[:300])
    return out


def mastery(usage: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    done, going = [], []
    for key, e in (usage or {}).items():
        row = {"key": key, "ko": e.get("ko", ""), "vi": e.get("vi", ""), "kind": e.get("kind", ""),
               "ok": len(set(e.get("ok_rounds") or [])), "miss": int(e.get("miss", 0)), "last": e.get("last", "")}
        (done if row["ok"] >= MASTERED_ROUNDS else going).append(row)
    done.sort(key=lambda r: r["last"], reverse=True)
    going.sort(key=lambda r: (-r["ok"], r["key"]))
    return {"mastered": done[:30], "practicing": going[:30]}

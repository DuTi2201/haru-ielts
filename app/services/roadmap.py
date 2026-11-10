"""The learner's road after the entry check: where to start, what to fill in, how long it takes.

Every number here is COMPUTED (lessons left to the goal, minutes they take, weeks at the learner's
daily minutes, whether the exam date is reachable). Gemini only puts them into a few short
sentences in Haru's voice, from the facts it is given; if it is not there, or says something too
long, the same facts are said plainly by `fallback`. It never picks lessons: the lessons come from
the course order and the placement (app.services.placement_cat)."""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import datetime
from typing import Any

# the last lesson each goal needs (a slug prefix; "" = the whole course)
GOAL_END = {
    "ielts65": "",
    "b1": "b1-u42",
    "topik1": "sinh-hoat-10",
    "talk": "cong-so-08",
    "work": "cong-so-08",
    "topik4": "viet-nghi-luan-08",
    "topik5": "",
    "topik6": "",
}
GOAL_LABEL = {
    "ielts65": "IELTS Academic 6.5",
    "b1": "Destination B1",
    "talk": "giao tiếp hằng ngày",
    "work": "đi làm, công sở",
    "topik1": "TOPIK I",
    "topik4": "TOPIK II cấp 3–4",
    "topik5": "TOPIK II cấp 5–6",
    "topik6": "TOPIK II cấp 5–6",
}
SKIP_FOR = {"talk": ("viet-nghi-luan-",), "work": ("viet-nghi-luan-",), "topik1": (), "ielts65": (), "b1": ()}
STUDY_DAYS = 6  # a week, one day off
NEW_SHARE = 0.7  # of the daily minutes, what goes to new lessons (the rest: review)
HEADLINE_MAX, TIP_MAX, TIPS = 90, 120, 3


@dataclass(frozen=True)
class CourseLesson:
    id: int
    sort_order: int
    slug: str
    title: str
    kind: str
    vocab: int
    grammar: int
    questions: int


def lesson_minutes(l: CourseLesson) -> int:
    """About how long a lesson takes the first time: words, patterns and the practice (lesson 1:
    33 words, 7 patterns, 51 questions ≈ an hour)."""
    if l.kind == "hangul":
        return 50  # five parts of about ten minutes
    est = 0.4 * l.vocab + 3 * l.grammar + 0.4 * l.questions
    return int(min(90, max(20, round(est))))


def path(course: list[CourseLesson], start_sort: int, goal: str | None) -> list[CourseLesson]:
    """The lessons from the start to the goal's last one, in course order."""
    end = GOAL_END.get(goal or "talk", "cong-so-08")
    skip = SKIP_FOR.get(goal or "talk", ())
    out = []
    for l in sorted(course, key=lambda l: l.sort_order):
        if l.sort_order < start_sort or (skip and l.slug.startswith(skip)):
            continue
        out.append(l)
        if end and l.slug.startswith(end):
            break
    return out


@dataclass(frozen=True)
class Plan:
    lessons: int
    minutes: int
    weeks: int
    daily_minutes: int
    exam_weeks: int | None  # weeks to the exam, when there is a date
    need_daily: int | None  # the daily minutes the exam date needs, when more than given
    first: list[dict[str, Any]]  # the next lessons: {id, title, minutes, free}


def plan(course: list[CourseLesson], start_sort: int, goal: str | None, daily_minutes: int,
         exam_date: datetime | None, now: datetime, free_max: int) -> Plan:
    road = path(course, start_sort, goal)
    total = sum(lesson_minutes(l) for l in road)
    weekly = max(1, daily_minutes) * STUDY_DAYS * NEW_SHARE
    weeks = math.ceil(total / weekly) if road else 0
    exam_weeks = need = None
    if exam_date is not None:
        exam_weeks = max(0, (exam_date - now).days // 7)
        if road and exam_weeks > 0 and weeks > exam_weeks:
            need = math.ceil(total / (exam_weeks * STUDY_DAYS * NEW_SHARE) / 5) * 5
    first = [
        {"id": l.id, "title": l.title, "minutes": lesson_minutes(l), "free": l.sort_order <= free_max}
        for l in road[:3]
    ]
    return Plan(len(road), total, weeks, daily_minutes, exam_weeks, need, first)


# ------------------------------------------------------------------ the words --
SCHEMA = {
    "type": "object",
    "properties": {
        "headline": {"type": "string"},
        "tips": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["headline", "tips"],
}


def facts(level_label: str, start_title: str | None, advice: str, restart_title: str | None,
          gaps: list[dict[str, Any]], p: Plan, goal: str | None, asked: int, right: int) -> dict[str, Any]:
    return {
        "trinh_do_uoc_luong": level_label,
        "so_cau_da_lam": asked,
        "so_cau_dung": right,
        "muc_tieu": GOAL_LABEL.get(goal or "talk", "giao tiếp hằng ngày"),
        "bat_dau_tu_bai": start_title,
        "loi_khuyen": {"start_here": "học tiếp từ bài bắt đầu",
                       "fill_gaps": "học từ bài bắt đầu, ôn bổ sung các chỗ hổng",
                       "restart_from": "lùi về học lại từ một bài sớm hơn"}[advice],
        "hoc_lai_tu_bai": restart_title,
        "cho_hong": [{"bai": g["title"], "mau_ngu_phap": g["patterns"][:2]} for g in gaps[:3]],
        "so_bai_den_muc_tieu": p.lessons,
        "so_tuan_du_kien": p.weeks,
        "phut_moi_ngay": p.daily_minutes,
        "tuan_den_ky_thi": p.exam_weeks,
        "phut_moi_ngay_can_de_kip_thi": p.need_daily,
    }


def prompt(f: dict[str, Any]) -> str:
    return (
        "Bạn là Haru, thiên nga nhỏ trong app học tiếng Hàn cho người Việt. Xưng 'mình', gọi người học là 'bạn'.\n"
        "Dựa DUY NHẤT vào dữ kiện JSON dưới đây (kết quả kiểm tra đầu vào và lộ trình đã tính sẵn), viết:\n"
        f"- headline: 1 câu tiếng Việt, tối đa {HEADLINE_MAX} ký tự, khen đúng mức và nói người học đang ở đâu "
        "(không nhắc tên bài: màn hình đã có nút vào bài).\n"
        f"- tips: tối đa {TIPS} câu, mỗi câu tối đa {TIP_MAX} ký tự, chỉ những điều giúp học tốt hơn: bỏ qua các bài trước "
        "có sao không, chỗ hổng nào cần ôn (nếu có), chia số phút mỗi ngày thế nào giữa bài mới và ôn tập, kỳ thi (nếu có). "
        "Không nhắc lại số bài và số tuần (đã hiện riêng).\n"
        "Không bịa số, tên bài hay mẫu ngữ pháp ngoài dữ kiện. Không hứa điểm thi. Không dùng emoji. Câu ngắn, ấm áp, cụ thể.\n\n"
        + json.dumps(f, ensure_ascii=False)
    )


def parse(text: str) -> dict[str, Any] | None:
    try:
        raw = json.loads(text)
    except (TypeError, ValueError):
        return None
    head = str(raw.get("headline") or "").strip()
    tips = [str(t).strip() for t in raw.get("tips") or [] if str(t).strip()]
    if not head or len(head) > HEADLINE_MAX + 20 or any(len(t) > TIP_MAX + 30 for t in tips):
        return None
    return {"headline": head, "tips": tips[:TIPS], "by": "gemini"}


def fallback(f: dict[str, Any]) -> dict[str, Any]:
    head = (f"Bạn đang ở mức {f['trinh_do_uoc_luong']}." if f["bat_dau_tu_bai"]
            else f"Bạn ở mức {f['trinh_do_uoc_luong']}: đã đi hết lộ trình bài học.")
    tips: list[str] = []
    if f["hoc_lai_tu_bai"]:
        tips.append(f"Vài chỗ phía trước còn chưa chắc, học lại từ “{f['hoc_lai_tu_bai']}” sẽ vững hơn.")
    elif f["cho_hong"]:
        tips.append("Các bài trước bạn đã nắm, chỉ cần ôn thêm vài chỗ ở mục “Nên ôn lại”.")
    elif f["so_cau_da_lam"]:
        tips.append("Các bài trước bạn đã nắm: bỏ qua cũng không sao, ôn tập hằng ngày vẫn nhắc lại khi cần.")
    review = max(5, round(f["phut_moi_ngay"] * 0.3 / 5) * 5)
    tips.append(f"Mỗi ngày: khoảng {review} phút ôn thẻ trước, thời gian còn lại học bài mới.")
    if f["phut_moi_ngay_can_de_kip_thi"]:
        tips.append(f"Để kịp kỳ thi sau {f['tuan_den_ky_thi']} tuần, cần khoảng {f['phut_moi_ngay_can_de_kip_thi']} phút mỗi ngày.")
    return {"headline": head, "tips": tips[:TIPS], "by": "rules"}

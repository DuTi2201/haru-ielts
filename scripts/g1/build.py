"""Build module G1, week 1 (days 1-4): four lessons and the practice bank "g1" from days.txt.

    python3 scripts/g1/build.py

Reuses the exercise builders of scripts/b1/build.py. Writes app/seed/lessons/g1-*.json,
app/seed/exercises/g1/*.json and scripts/g1/book_tasks.json (the book exercises to do before each day's cards,
for the "do it in the book" screen; answer keys are not kept in this repository)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from b1 import build as B  # noqa: E402

LESSONS = ROOT / "app" / "seed" / "lessons"
BANK = ROOT / "app" / "seed" / "exercises" / "g1"
TOPIC = "G1 · Các thì hiện tại (Tuần 1)"
BOOK = "Destination B2 (Mann & Taylore-Knowles, Macmillan), Unit 1"
SOURCE = "Haru English · G1, theo bài giảng của thầy Minh và khung Destination B2 Unit 1"


def parse() -> list[dict]:
    days: list[dict] = []
    cur: dict = {}
    card: dict = {}
    for raw in (HERE / "days.txt").read_text(encoding="utf-8").splitlines():
        ln = raw.rstrip()
        if not ln or (ln.startswith("#") and not ln.startswith("#D ")):
            continue
        if ln.startswith("#D "):
            n, title, title_vi, pages = [x.strip() for x in ln[3:].split(" | ")]
            cur = {"n": int(n), "title": title, "title_vi": title_vi, "pages": pages, "book": [], "cards": [], "words": [],
                   "items": [], "b": [], "f": [], "d": [], "m": []}
            days.append(cur)
        elif ln.startswith("goal: "):
            cur["goal"] = ln[6:]
        elif ln.startswith("ielts: "):
            cur["ielts"] = ln[7:]
        elif ln.startswith("book: "):
            book, pages, task, items, minutes = [x.strip() for x in ln[6:].split(" | ")]
            cur["book"].append({"book": book, "pages": pages, "task": task, "items": int(items), "minutes": int(minutes)})
        elif ln.startswith("G: "):
            pattern, meaning, importance = [x.strip() for x in ln[3:].rsplit(" | ", 2)]
            card = {"pattern": pattern, "meaning": meaning, "importance": importance, "use": "", "ex": [], "quote": None, "trap": None, "tip": None, "vs": []}
            cur["cards"].append(card)
        elif ln.startswith(" use: "):
            card["use"] = B.nl(ln[6:])
        elif ln.startswith(" ex: "):
            card["ex"].append(B.pair(ln[5:]))
        elif ln.startswith(" quote: "):
            card["quote"] = ln[8:]
        elif ln.startswith(" trap: "):
            card["trap"] = ln[7:]
        elif ln.startswith(" tip: "):
            card["tip"] = ln[6:]
        elif ln.startswith(" vs: "):
            other, diff = ln[5:].split(" | ", 1)
            card["vs"].append({"pattern": other.strip(), "diff_vi": diff.strip()})
        elif ln.startswith("W: "):
            head, pos, meaning, ex = [x.strip() for x in ln[3:].split(" | ")]
            cur["words"].append({"head": head, "pos": pos, "meaning": meaning, "ex": B.pair(ex)})
        elif ln[:3] in ("I: ", "T: ", "Q: "):
            parts = [x.strip() for x in ln[3:].split(" | ")]
            cur["items"].append({"kind": ln[0], "stem": parts[0], "options": parts[1:-2], "why": parts[-2], "card": int(parts[-1]) - 1})
        elif ln.startswith("B: "):
            vi, en = ln[3:].split(" | ")
            cur["b"].append((vi.strip(), en.strip()))
        elif ln.startswith("F: "):
            text, accepted, tip = [x.strip() for x in ln[3:].split(" | ")]
            cur["f"].append({"text": text, "accepted": [a.strip() for a in accepted.split(";")], "tip": tip})
        elif ln.startswith("D: "):
            cur["d"].append(B.pair(ln[3:]))
        elif ln.startswith("M: "):
            en, vi, model = [x.strip() for x in ln[3:].split(" | ")]
            cur["m"].append({"en": en, "vi": vi, "model": model})
        else:
            raise SystemExit(f"days.txt: cannot read {ln[:60]!r}")
    return days


KIND = {
    "I": ("Nói đúng ý", "Đọc tình huống. Chọn câu nói đúng điều người nói muốn nói. Câu còn lại có thể đúng ngữ pháp nhưng nói một ý khác."),
    "T": ("Trục thời gian", "Đọc câu tiếng Anh. Chọn trục thời gian vẽ đúng điều câu đó nói."),
    "Q": ("Chọn dạng đúng", "Chọn phương án đúng cho chỗ trống."),
}


def lesson_of(d: dict) -> tuple[dict, dict[str, list[dict]], dict[str, list[str]]]:
    n = d["n"]
    pid = f"G1D{n}"
    bank: dict[str, list[dict]] = {"reading": [], "build": [], "listening": [], "writing": []}
    links: dict[str, list[str]] = {}
    patterns = [c["pattern"] for c in d["cards"]]
    by_card: dict[int, list[str]] = {}
    count = {"I": 0, "T": 0, "Q": 0}
    for it in d["items"]:
        count[it["kind"]] += 1
        ex_id = f"{pid}{it['kind']}{count[it['kind']]}"
        title, instruction = KIND[it["kind"]]
        if it["kind"] == "Q":
            ex = B.mcq(ex_id, f"{title} · Ngày {n}", it["stem"], None, it["options"], it["why"], instruction)
        elif it["kind"] == "T":
            ex = B.mcq(ex_id, f"{title} · Ngày {n}", None, f"«{it['stem']}» Trục nào đúng với câu này?", it["options"], it["why"], instruction)
        else:
            ex = B.mcq(ex_id, f"{title} · Ngày {n}", None, it["stem"], it["options"], it["why"], instruction)
        bank["reading"].append(ex)
        links[ex_id] = [patterns[it["card"]]]
        by_card.setdefault(it["card"], []).append(ex_id)
    for i, (vi, en) in enumerate(d["b"], 1):
        if not B.fits_tiles(en):
            raise SystemExit(f"Day {n}: build sentence must have 3-10 words: {en!r}")
        bank["build"].append(B.build_order(f"{pid}B{i}", f"Xếp câu · Ngày {n}", vi, en))
    for i, f in enumerate(d["f"], 1):
        bank["build"].append(B.write_fill(f"{pid}F{i}", f"Gõ dạng đúng · Ngày {n}", f["text"], f["accepted"], f["tip"]))
    dic = B.dictation(f"{pid}D1", f"Nghe chép · Ngày {n}", d["d"], [(w["head"], w["meaning"]) for w in d["words"]])
    if dic:
        dic["tips_vi"] = ["Nghe âm cuối: -s của ngôi thứ ba, 's và n't, -ing. Sau khi kiểm tra, nghe lại và nhại theo đúng nhịp."]
        bank["listening"].append(dic)
    for i, m in enumerate(d["m"], 1):
        bank["writing"].append({
            "id": f"{pid}M{i}", "skill": "writing", "type": "write_essay", "number": f"M{i}", "title_vi": f"Câu của tôi · Ngày {n}", "points": 5,
            "instruction_vi": m["vi"] + " Gõ bằng bàn phím tiếng Anh. Đúng sai chưa quan trọng: quan trọng là câu nói về chính bạn.",
            "limits": {"min": 8, "max": 40}, "prompt_en": m["en"],
            "framework_vi": ["Nghĩ điều bạn muốn nói trước, bằng tiếng Việt cũng được.", "Tự hỏi: việc đó nằm ở đâu trên trục thời gian?", "Chọn thì theo câu trả lời đó rồi mới viết."],
            "model_answer_en": m["model"], "model_note_vi": "Bài mẫu chỉ là một ví dụ. Câu của bạn phải đúng với bạn.",
            "checklist_vi": ["Mỗi câu có chủ ngữ và động từ đã chia.", "Thì khớp với điều bạn muốn nói.", "Ngôi thứ ba số ít có -s; sau do/does là nguyên thể."],
        })

    vocab = [{"headword": w["head"], "pos": w["pos"], "meaning_vi": w["meaning"], "example_en": w["ex"][0], "example_vi": w["ex"][1],
              "family": "Từ của ngày", "priority": "core", "source": SOURCE} for w in d["words"]]
    grammar = []
    for c in d["cards"]:
        use = c["use"] + (f"\nLời thầy: «{c['quote']}»" if c["quote"] else "")
        g = {"pattern": c["pattern"], "meaning_vi": c["meaning"], "usage_context_vi": use, "contrasts": c["vs"],
             "example_en": "\n".join(e for e, _ in c["ex"]), "example_vi": "\n".join(v for _, v in c["ex"]),
             "importance": c["importance"], "source": f"{BOOK}, pp. {d['pages']}; cách giảng theo thầy Minh"}
        if c["trap"]:
            g["note_vi"] = "Lỗi người Việt hay mắc: " + c["trap"]
        if c["tip"]:
            g["exam_tip_vi"] = c["tip"]
        grammar.append(g)

    idx = list(range(len(patterns)))
    groups = [idx[i:i + 3] for i in range(0, len(idx), 3)]
    if len(groups) > 1 and len(groups[-1]) == 1:  # no sitting with a single card: 7 cards -> 3, 2, 2
        groups[-2], groups[-1] = groups[-2][:2], groups[-2][2:] + groups[-1]
    rest = [e["id"] for k in ("build", "listening", "writing") for e in bank[k]]
    sessions = []
    for gi, g in enumerate(groups):
        checks = [qid for c in g for qid in by_card.get(c, [])]
        if gi == len(groups) - 1:
            checks += rest
        sessions.append({
            "title_vi": (f"Buổi {gi + 1} · " + patterns[g[0]].split(" · ")[-1])[:70],
            "can_do_vi": ("Sau buổi này bạn nắm được: " + "; ".join(d["cards"][c]["meaning"].lower() for c in g))[:238].rstrip(" ;,") + ".",
            "use_vi": d["ielts"][:200],
            "vocab": [w["head"] for w in d["words"]] if gi == 0 else [],
            "grammar": [patterns[c] for c in g],
            "check": checks,
        })
    book_body = "\n".join(
        f"• 📖 {b['book']}, trang {b['pages']}: " + (f"bài {b['task']} ({b['items']} câu, khoảng {b['minutes']} phút)" if b["items"] else f"{b['task']} (khoảng {b['minutes']} phút)")
        for b in d["book"])
    traps = [c["trap"] for c in d["cards"] if c["trap"] and len(c["trap"]) <= 230 and c["trap"].count("`") % 2 == 0]
    lesson = {
        "slug": f"g1-d{n}-{B.slugify(d['title'])}"[:60].rstrip("-"),
        "title": f"G1 · Ngày {n} · {d['title_vi']}", "title_en": d["title"], "topic": TOPIC, "track": "beginner", "level": 4, "sort_order": 100 + n,
        "summary": f"{d['goal']} Thẻ: {'; '.join(p.split(' · ')[-1] for p in patterns)}.",
        "vocab": vocab, "grammar": grammar,
        "notes": [
            {"title": "Mục tiêu của ngày", "body": f"• 🎯 {d['goal']}", "kind": "goal"},
            {"title": "Sách trước: tự làm rồi mới học thẻ", "body": book_body + "\n• Làm trong sách, ghi đáp án của bạn, rồi mới mở thẻ. Sau khi học thẻ, quay lại chấm bằng đáp án cuối sách và tự giải thích từng câu sai theo ý muốn nói.", "kind": "language"},
            {"title": "Dùng ở đâu trong IELTS", "body": d["ielts"], "kind": "language"},
        ],
        "bank": "g1",
        "coach": {"focus_vi": [f"{c['pattern'].split(' · ')[-1]}: {c['meaning']}"[:230] for c in d["cards"][:3]], "watch_out_vi": traps[:2]},
        "exercise_ids": [e["id"] for k in ("reading", "build", "listening", "writing") for e in bank[k]],
        "sessions": sessions,
        "editor_notes": [{"title": "Nguồn", "body": "Ý và thứ tự giảng theo bài giảng của thầy Minh; khung và số trang theo Destination B2, Unit 1. Lời giải thích, ví dụ và câu hỏi do khóa học tự soạn; bài tập của sách làm trong sách."}],
    }
    return lesson, bank, links


def main() -> None:
    days = parse()
    BANK.mkdir(parents=True, exist_ok=True)
    for old in LESSONS.glob("g1-*.json"):
        old.unlink()
    merged: dict[str, list[dict]] = {}
    links: dict[str, list[str]] = {}
    for d in days:
        lesson, bank, ln = lesson_of(d)
        (LESSONS / f"{lesson['slug']}.json").write_text(json.dumps(lesson, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        for k, v in bank.items():
            merged.setdefault(k, []).extend(v)
        links.update(ln)
    for k, items in merged.items():
        (BANK / f"{k}.json").write_text(json.dumps({"skill": k, "guide": B.GUIDES[k], "items": items}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    (BANK / "grammar_links.json").write_text(json.dumps({"links": links}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    overview = json.loads((ROOT / "app" / "seed" / "exercises" / "b1" / "overview.json").read_text(encoding="utf-8"))
    (BANK / "overview.json").write_text(json.dumps(overview, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    (HERE / "book_tasks.json").write_text(json.dumps({f"g1-d{d['n']}": d["book"] for d in days}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    n_ex = sum(len(v) for v in merged.values())
    print({"lessons": len(days), "cards": sum(len(d["cards"]) for d in days), "words": sum(len(d["words"]) for d in days), "exercises": n_ex,
           "by_kind": {k: len(v) for k, v in merged.items()}})


if __name__ == "__main__":
    main()

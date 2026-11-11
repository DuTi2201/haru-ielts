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
sys.path.insert(0, str(HERE))
import book_items as BK  # noqa: E402
import entry_test as ET  # noqa: E402
import days56 as D56  # noqa: E402
from day7 import OPTIONAL as OPT7  # noqa: E402
import day89 as D89  # noqa: E402
from assoc import ASSOC  # noqa: E402
import re  # noqa: E402

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
    book_ids: list[str] = []
    book_groups: dict[str, list[str]] = {}
    book_src: dict[str, tuple[str, str]] = {}
    for day, code, src, title, instr, kind, lines in BK.SECTIONS:
        if day != n:
            continue
        for i, ln in enumerate(lines, 1):
            f = [x.strip() for x in ln.split(" | ")]
            ex_id = f"{pid}K{code}-{i}"
            ttl = f"Sách · {title} ({i}/{len(lines)})"
            if kind == "choice":
                stem, opts, why = f[0], f[1:-1], f[-1] + f" [{src}]"
                if "( )" in stem:
                    ex = B.mcq(ex_id, ttl, stem, None, opts, why, instr)
                else:
                    ex = B.mcq(ex_id, ttl, None, stem, opts, why, instr)
                if code in BK.CHARTS:
                    ex["stimulus"] = {"kind": "chart", "block": BK.CHARTS[code]}
                bank["reading"].append(ex)
            else:
                text, acc, tip = f[0], f[1].split(";"), f[2] + f" [{src}]"
                ex = B.write_fill(ex_id, ttl, text, acc, tip)
                ex["instruction_vi"] = instr
                bank["build"].append(ex)
            links[ex_id] = [patterns[0] if n in (1, 3) else patterns[min(1, len(patterns) - 1)]]
            book_ids.append(ex_id)
            book_groups.setdefault(code, []).append(ex_id)
            book_src[code] = (title, src)

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
    book_set = set(book_ids)
    rest = [e["id"] for k in ("build", "listening", "writing") for e in bank[k] if e["id"] not in book_set]
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
    chunk: list[str] = []
    names: list[str] = []
    book_sittings: list[tuple[list[str], list[str]]] = []
    for code, ids in book_groups.items():
        if chunk and len(chunk) + len(ids) > 24:
            book_sittings.append((names, chunk)); chunk, names = [], []
        chunk += ids; names.append(code)
    if chunk:
        book_sittings.append((names, chunk))
    for names, ids in book_sittings:
        sessions.append({
            "title_vi": pack_title("Luyện theo sách", [(book_src[c][1], book_src[c][0]) for c in names]),
            "can_do_vi": "Sau buổi này bạn đã làm xong các bài của sách ngay trong app: " + "; ".join(book_src[c][0].lower() for c in names) + ".",
            "use_vi": "Làm sau khi học thẻ: mỗi câu sai có lời giải thích, hãy tự nói lại câu đó theo ý muốn nói rồi mới sang câu sau.",
            "check": ids,
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
            {"title": "Bài của sách nằm trong app", "body": book_body + "\n• Các bài này đã có sẵn trong app, ở các buổi \"Bài trong sách\" cuối ngày, kèm đáp án của sách và lời giải thích từng câu. Nếu có sách giấy, bạn có thể làm trên sách trước rồi chấm lại trong app. Sau khi học thẻ, với mỗi câu sai hãy tự nói lại câu đó theo ý muốn nói.", "kind": "language"},
            {"title": "Dùng ở đâu trong IELTS", "body": d["ielts"], "kind": "language"},
        ],
        "bank": "g1",
        "coach": {"focus_vi": [f"{c['pattern'].split(' · ')[-1]}: {c['meaning']}"[:230] for c in d["cards"][:3]], "watch_out_vi": traps[:2]},
        "exercise_ids": [e["id"] for k in ("reading", "build", "listening", "writing") for e in bank[k]],
        "sessions": sessions,
        "editor_notes": [{"title": "Nguồn", "body": "Ý và thứ tự giảng theo bài giảng của thầy Minh; khung và số trang theo Destination B2, Unit 1. Lời giải thích, ví dụ và câu hỏi do khóa học tự soạn; bài tập của sách làm trong sách."}],
    }
    return lesson, bank, links


def entry_lesson() -> tuple[dict, list[dict]]:
    """The 50-item entry test of IELTS Grammar 6.5+ as a lesson of its own, in five sittings of ten."""
    exs: list[dict] = []
    for i, (stem, a, b, c, key, unit, point) in enumerate(ET.ITEMS, 1):
        opts = {"A": a, "B": b, "C": c}
        right = opts[key]
        order = [right] + [v for k, v in opts.items() if k != key]
        why = f"Đáp án: {right}. {point} Nếu sai: học Unit {unit} của IELTS Grammar for Bands 6.5+ (khóa của sách)."
        title = f"Kiểm tra đầu vào · câu {i}/50"
        ins = "Chọn đáp án đúng. Đây là bài đo trình độ: đừng đoán mò, hãy ghi lại những câu bạn không chắc."
        if "( )" in stem:
            ex = B.mcq(f"G1E{i}", title, stem, None, order, why, ins)
        else:
            ex = B.mcq(f"G1E{i}", title, None, stem, order, why, ins)
        exs.append(ex)
    sessions = []
    for k in range(5):
        chunk = exs[k * 10:(k + 1) * 10]
        sessions.append({
            "title_vi": f"Câu {k * 10 + 1}–{k * 10 + 10} của bài kiểm tra"[:70],
            "can_do_vi": "Sau buổi này bạn biết mình đang yếu hay chắc ở những Unit nào của ngữ pháp, để học đúng chỗ.",
            "vocab": ["diagnostic"] if k == 0 else [],
            "check": [e["id"] for e in chunk],
        })
    lesson = {
        "slug": "g1-entry-test", "title": "G1 · Bài kiểm tra đầu vào (50 câu)", "title_en": "Grammar entry test (50 items)", "topic": TOPIC,
        "track": "beginner", "level": 4, "sort_order": 100,
        "summary": "Bài đo trình độ ngữ pháp của sách IELTS Grammar for Bands 6.5+: 50 câu, mỗi câu chỉ ra Unit cần học nếu sai.",
        "vocab": [{"headword": "diagnostic", "pos": "A", "meaning_vi": "dùng để chẩn đoán, tìm ra chỗ yếu", "example_en": "This diagnostic test shows which grammar units you need to study.", "example_vi": "Bài kiểm tra chẩn đoán này cho biết bạn cần học những Unit ngữ pháp nào.", "family": "Từ của ngày", "priority": "core", "source": SOURCE}], "grammar": [],
        "notes": [{"title": "Cách làm và cách đọc kết quả", "body": "• Làm một mạch, không tra sách. Câu không chắc thì ghi lại.\n• Mỗi lời giải thích cho biết Unit của sách cần học nếu sai. Gom các Unit hay sai nhất để biết phải ôn gì trước.\n• Bài này đo trình độ, không phải chương trình học: tuần 1 vẫn đi theo Ngày 1–4.", "kind": "goal"}],
        "bank": "g1", "exercise_ids": [e["id"] for e in exs], "sessions": sessions,
        "editor_notes": [{"title": "Nguồn", "body": "IELTS Grammar for Bands 6.5 and above (Hopkins & Cullen, Cambridge), Entry test trang x–xii; đáp án và Unit theo khóa trang 221."}],
    }
    return lesson, exs


TFNG3 = ["True", "False", "Not Given"]
STAGE_PREFIX = {"b2": "Đọc trước B2 · giải nghĩa và liên tưởng", "c1": "Làm quen C1 · neo vào từ B2"}


def pack_title(prefix: str, items: list[tuple[str, str]]) -> str:
    """Name a sitting after what it practises: «Luyện · B2 Unit 1 · Khoanh từ đúng (+1)»."""
    srcname, title = items[0]
    short = srcname.split(" · ")[0].replace("Destination ", "").replace("IELTS Grammar 6.5+, ", "Grammar 6.5+ ").replace(",", "")
    more = f" (+{len(items) - 1})" if len(items) > 1 else ""
    room = 70 - len(prefix) - len(short) - len(more) - 6
    room = max(room, 12)
    if len(title) > room:
        title = title[:room].rsplit(" ", 1)[0].rstrip(":,;") + "…"
    return f"{prefix} · {short} · {title}{more}"


def words_of(day: int) -> list[tuple]:
    dd = D56.DAYS[day] if day in D56.DAYS else D89.DAYS[day]
    return [w for _, ws in dd["sittings"] for w in ws]


def review_items(pid: str, from_days: list[int]) -> list[dict]:
    """Spaced review: the sentence of each earlier word with the word taken out, typed back."""
    out = []
    for fd in from_days:
        for h, pos, mv, ex, evi in words_of(fd):
            pat = re.compile(r"\b" + re.escape(h) + r"\b", re.I)
            if not pat.search(ex):
                continue
            text = pat.sub("( ㉠ )", ex, count=1)
            gloss = mv.split(" (")[0]
            e = B.write_fill(f"{pid}O{fd}-{len(out) + 1}", f"Ôn lại · từ Ngày {fd}", text, [h, h.capitalize()], f"{h} = {gloss}. Nghĩa của câu: {evi}")
            e["instruction_vi"] = "Ôn lại từ đã học: gõ từ còn thiếu trong câu. Nếu quên, nhìn nghĩa tiếng Việt gợi ý rồi thử lại."
            out.append(e)
    return out


def vocab_day(n: int) -> tuple[dict, dict[str, list[dict]], dict[str, list[str]]]:
    """Days 5 and 6: education vocabulary (B2 Unit 18 and nine C1 anchor words) plus the book exercises of the day."""
    d = D56.DAYS[n] if n in D56.DAYS else D89.DAYS[n]
    pid = f"G1D{n}"
    bank: dict[str, list[dict]] = {"reading": [], "build": [], "listening": [], "writing": []}
    links: dict[str, list[str]] = {}
    vocab, sessions = [], []
    for title, words in d["sittings"]:
        for h, pos, mv, ex, evi in words:
            vocab.append({"headword": h, "pos": pos, "meaning_vi": mv + (f" · Nhớ: {ASSOC[h]}" if h in ASSOC else ""), "example_en": ex, "example_vi": evi, "family": d.get("family", "Giáo dục"), "priority": "recognize" if h in d.get("recognize", ()) else "core",
                          "source": d.get("source", "Destination B2, Unit 18; từ C1 theo cách neo của thầy Minh")})
        sessions.append({"title_vi": (STAGE_PREFIX.get(d.get("stage"), "Từ vựng") + f" · {title}")[:70], "can_do_vi": "Sau buổi này bạn hiểu và dùng được các từ: " + ", ".join(w[0] for w in words[:6]) + ", ...",
                         "use_vi": d["ielts"][:200], "vocab": [w[0] for w in words]})
    for ps in d.get("passages", []):
        qs = []
        for i, (prompt, opts, why) in enumerate(ps["qs"], 1):
            qid = f"{pid}R{ps['id']}{i}"
            order = TFNG3 if set(opts) == set(TFNG3) else sorted(opts, key=lambda t: B.rng(qid + t).random())
            qs.append({"id": qid, "prompt_en": prompt, "options": [{"id": str(j + 1), "text": t} for j, t in enumerate(order)],
                       "answer": str(order.index(opts[0]) + 1), "explanation_vi": why + f" [{d['source'].split(';')[0]}]", "tags": []})
        pex = {"id": f"{pid}R{ps['id']}", "skill": "reading", "type": "read_passage", "title_vi": f"Đọc chậm · {ps['title']}"[:70], "instruction_vi": ps["instr"],
               "stimulus": {"kind": "passage", "text": ps["text"]}, "questions": qs}
        bank["reading"].append(pex)
        sessions.append({"title_vi": f"Đọc chậm · {ps['title']}"[:70], "can_do_vi": "Sau buổi này bạn đọc đúng đoạn có đáp án và giải thích được vì sao mỗi câu đúng, sai hoặc không có thông tin.",
                         "use_vi": d["ielts"][:200], "check": [pex["id"]]})
    first_head = vocab[0]["headword"]
    groups: dict[str, list[str]] = {}
    src: dict[str, str] = {}
    kinds: dict[str, str] = {}
    srcn: dict[str, str] = {}
    for day, code, srcname, title, instr, kind, lines in BK.SECTIONS:
        if day != n:
            continue
        for i, ln in enumerate(lines, 1):
            f = [x.strip() for x in ln.split(" | ")]
            ex_id = f"{pid}K{code}-{i}"
            ttl = f"Sách · {title} ({i}/{len(lines)})"
            if kind == "choice":
                stem, opts, why = f[0], f[1:-1], f[-1] + f" [{srcname}]"
                ex = B.mcq(ex_id, ttl, stem if "( )" in stem else None, None if "( )" in stem else stem, opts, why, instr)
                bank["reading"].append(ex)
            else:
                ex = B.write_fill(ex_id, ttl, f[0], f[1].split(";"), f[2] + f" [{srcname}]")
                ex["instruction_vi"] = instr
                bank["build"].append(ex)
            groups.setdefault(code, []).append(ex_id)
            src[code] = title; kinds[code] = kind; srcn[code] = srcname
    def packs_of(grp: dict[str, list[str]]) -> list[tuple[list[str], list[str]]]:
        res, chunk, names = [], [], []
        for code, ids in grp.items():
            if chunk and len(chunk) + len(ids) > 24:
                res.append((names, chunk)); chunk, names = [], []
            chunk += ids; names.append(code)
        if chunk:
            res.append((names, chunk))
        return res

    def add_packs(grp: dict[str, list[str]], prefix: str, can_do: str) -> None:
        for names, ids in packs_of(grp):
            sessions.append({"title_vi": pack_title(prefix, [(srcn[c], src[c]) for c in names]), "can_do_vi": (can_do + "; ".join(src[c].lower() for c in names))[:238].rstrip(" ;,") + ".",
                             "use_vi": "Mỗi câu sai có lời giải thích; gõ lại cụm đúng vào sổ từ của bạn.", "check": ids})

    core = {c: i for c, i in groups.items() if c not in OPT7}
    extra = {c: i for c, i in groups.items() if c in OPT7}
    receive = {c: i for c, i in core.items() if kinds[c] == "choice"}
    practise = {c: i for c, i in core.items() if kinds[c] != "choice"}
    add_packs(receive, "Tiếp nhận", "Sau buổi này bạn nhận ra đáp án đúng trong các bài của sách: ")
    my_ids: list[str] = []
    for i, m in enumerate(d.get("my", []), 1):
        wid = f"{pid}M{i}"
        bank["writing"].append({
            "id": wid, "skill": "writing", "type": "write_essay", "number": f"M{i}", "title_vi": f"Câu của tôi · Ngày {n}", "points": 5,
            "instruction_vi": m["vi"] + " Gõ bằng bàn phím tiếng Anh. Đúng sai chưa quan trọng: quan trọng là câu nói về chính bạn và dùng từ bạn chọn.",
            "limits": {"min": 8, "max": 50}, "prompt_en": m["en"],
            "framework_vi": ["Chọn 5 đến 10 từ bạn thích nhất trong bài hôm nay.", "Nghĩ điều bạn muốn nói về chính mình, bằng tiếng Việt cũng được.", "Gõ hai câu có dùng ít nhất hai từ đã chọn; từ C1 thì thêm một từ B2 đồng nghĩa ở câu kia."],
            "model_answer_en": m["model"], "model_note_vi": "Bài mẫu chỉ là một ví dụ. Câu của bạn phải đúng với bạn.",
            "checklist_vi": ["Mỗi câu có chủ ngữ và động từ đã chia.", "Có dùng từ của bài hôm nay, đúng từ loại.", "Câu nói về chính bạn, không chép câu mẫu."]})
        my_ids.append(wid)
    if my_ids:
        sessions.append({"title_vi": "Vận dụng · câu của tôi với từ vừa học", "can_do_vi": "Sau buổi này bạn đã tự gõ câu của riêng mình với các từ vừa học, bước thầy Minh coi là quan trọng nhất.",
                         "use_vi": "Từ vừa dùng cho chuyện của chính mình thì nhớ lâu hơn, và đây là cầu nối sang Writing và Speaking.", "check": my_ids})
    add_packs(practise, "Rèn luyện", "Sau buổi này bạn tự gõ được đáp án của sách: ")
    prev = [dd for dd in (5, 6, 7) if dd < n] if n in (6, 7) else []
    if prev:
        rv = review_items(pid, prev)
        bank["build"].extend(rv)
        for k in range(0, len(rv), 20):
            part = rv[k:k + 20]
            sessions.append({"title_vi": f"Ôn tập · từ Ngày {', '.join(str(x) for x in prev)} ({k // 20 + 1})"[:70], "can_do_vi": "Sau buổi này bạn nhớ lại các từ đã học ở những ngày trước mà không nhìn đáp án.",
                             "use_vi": "Ôn cách quãng: gặp lại từ sau vài ngày giúp nhớ lâu hơn nhiều so với học dồn.", "check": [e["id"] for e in part]})
    add_packs(extra, "Mở rộng không bắt buộc", "Cụm động từ và thành ngữ, chỉ cần nhận ra khi đọc và nghe: ")
    book_body = "\n".join(f"• 📖 {b[0]}, trang {b[1]}: bài {b[2]} ({b[3]} câu, khoảng {b[4]} phút)" for b in d["book"])
    lesson = {
        "slug": f"g1-d{n}-{B.slugify(d['title'])}"[:60].rstrip("-"),
        "title": f"G1 · Ngày {n} · {d['title_vi']}"[:120], "title_en": d["title"], "topic": TOPIC, "track": "beginner", "level": 4, "sort_order": 100 + n,
        "summary": d["goal"], "vocab": vocab, "grammar": [],
        "notes": [
            {"title": "Mục tiêu của ngày", "body": f"• 🎯 {d['goal']}", "kind": "goal"},
            {"title": "Bài của sách nằm trong app", "body": book_body + "\n• Các bài này có sẵn trong app kèm đáp án của sách và lời giải thích từng câu.", "kind": "language"},
            {"title": "Cách học từ của thầy", "body": "• Học từ C1 bằng một từ B2 đồng nghĩa, không học nghĩa tiếng Việt dài.\n• Chọn 5 đến 10 từ bạn thích nhất rồi gõ câu về chính mình bằng bàn phím tiếng Anh.", "kind": "language"},
        ],
        "bank": "g1", "exercise_ids": [e["id"] for k in ("reading", "build", "writing") for e in bank[k]], "sessions": sessions,
        "editor_notes": [{"title": "Nguồn", "body": d.get("editor", "Từ vựng và bài tập theo Destination B2 Unit 18 (trang 112–115, đáp án trang 244); chín từ C1 và cách neo theo bài giảng của thầy Minh.")}],
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
    for n in list(D56.DAYS) + list(D89.DAYS):
        lesson, bank, ln = vocab_day(n)
        (LESSONS / f"{lesson['slug']}.json").write_text(json.dumps(lesson, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        for k, v in bank.items():
            merged.setdefault(k, []).extend(v)
        links.update(ln)
    elesson, eex = entry_lesson()
    (LESSONS / f"{elesson['slug']}.json").write_text(json.dumps(elesson, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    merged.setdefault("reading", []).extend(eex)
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

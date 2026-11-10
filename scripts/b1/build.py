"""Build the Destination B1 course (42 lessons + the practice bank "b1") from the source files
in this folder.

    python3 scripts/b1/build.py            # writes app/seed/lessons/b1-*.json and app/seed/exercises/b1/
    python3 -m app.services.lesson_seed --check

The source files are the thing to edit; the JSON is generated. What comes from the book is the
syllabus only: the unit titles, the page numbers and the lists of words (pp. 184-216). The
explanations, examples, questions and model answers are written for this course, and each lesson
sends the learner to the book for the book's own exercises.

Field names (`headword`, `title_en`, `example_en`, `prompt_en`, `model_answer_en`, `exam_tip_vi`)
are the Haru schema's, kept until the schema is renamed: here they hold English.
"""
from __future__ import annotations

import hashlib
import json
import random
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
LESSONS = ROOT / "app" / "seed" / "lessons"
BANK = ROOT / "app" / "seed" / "exercises" / "b1"
TOPIC = "Destination B1 · Lấy gốc"
BOOK = "Destination B1 (Mann & Taylore-Knowles, Macmillan)"
PREPS = ["about", "against", "at", "by", "for", "from", "in", "into", "of", "on", "to", "with", "under", "out", "as", "between", "like"]
PARTICLES = ["up", "down", "off", "on", "out", "in", "away", "back", "over", "after", "across", "into", "with"]
# prepositions that would also be acceptable English in the example sentence: never offered as a wrong option
ALSO_OK = {
    "care about": "for", "complain (to sb) about": "of", "know about": "of", "learn about": "of from", "think about": "of",
    "talk (to sb) about": "of", "tell sb about": "of", "an idea about": "for of", "an opinion about/of": "on", "a question about": "on",
    "comment on": "about", "information about": "on", "a book (by sb) about": "on", "write (to sb) about": "for", "work for": "at in with",
    "translate (from sth) into": "to", "talented at": "in", "succeed in": "at", "send sth to sb": "for", "result in": "from",
    "a relationship with": "to", "a reason for": "of", "popular with": "for", "pleased with": "about at", "nervous about": "of",
    "look at": "for into like", "a letter (from sb) about": "to for", "laugh at": "about", "kind to": "with", "involved in": "with",
    "inform sb about": "of", "an increase in": "of", "a game against": "with", "frightened of": "by", "fight against": "with for",
    "fed up with": "of", "familiar with": "to", "embarrassed about": "by", "disappointed with": "by in at about",
    "a difference between": "in", "congratulate sb on": "for", "choose between": "from", "cheat at/in": "on", "change sth (from sth) into": "to",
    "careful with": "about", "bored with": "of by", "begin sth with": "by", "angry (with sb) about": "at", "an advantage of": "to in",
    "on the news": "in", "in the corner (of)": "at on", "at the top (of)": "on", "on the coast": "by at", "at the bottom (of)": "on in",
    "in the beginning": "at", "at the back (of)": "in", "at risk": "in under", "on business": "for", "in cash": "by with",
    "in comparison to/with": "by", "for sale": "on", "by email/phone/letter": "in", "in time (for)": "on", "on time": "in",
    "in the end": "at", "at the end (of)": "in", "on stage": "at", "in the distance": "at from",
}
LABEL = {"N": "danh từ", "P": "danh từ chỉ người", "A": "tính từ", "D": "trạng từ", "V": "động từ", "X": "dạng trái nghĩa",
         "2": "quá khứ đơn", "3": "quá khứ phân từ"}


def rng(key: str) -> random.Random:
    return random.Random(int(hashlib.sha256(key.encode()).hexdigest()[:12], 16))


def slugify(text: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", text.lower())).strip("-")


def lines(name: str) -> list[str]:
    return [ln.rstrip() for ln in (HERE / name).read_text(encoding="utf-8").splitlines() if ln.strip() and not ln.startswith("# ")]


def pair(text: str) -> tuple[str, str]:
    en, vi = text.split(" = ", 1)
    return en.strip(), vi.strip()


def nl(text: str) -> str:
    return text.replace("\\n", "\n")


# ------------------------------------------------------------------ parsing --
def parse_grammar() -> dict[int, dict]:
    units: dict[int, dict] = {}
    cur: dict | None = None
    card: dict | None = None
    for name in ("grammar_a.txt", "grammar_b.txt", "grammar_c.txt", "grammar_d.txt"):
        for ln in lines(name):
            if ln.startswith("#U "):
                n, title, title_vi, pages = [x.strip() for x in ln[3:].split(" | ")]
                cur = {"n": int(n), "title": title, "title_vi": title_vi, "pages": pages, "cards": [], "words": [], "q": [], "b": [], "f": [], "s": None}
                units[int(n)] = cur
                card = None
            elif ln.startswith("goal: "):
                cur["goal"] = ln[6:]
            elif ln.startswith("ielts: "):
                cur["ielts"] = ln[7:]
            elif ln.startswith("G: "):
                pattern, meaning, importance = [x.strip() for x in ln[3:].rsplit(" | ", 2)]
                card = {"pattern": pattern, "meaning": meaning, "importance": importance, "use": "", "ex": [], "trap": None, "tip": None, "vs": []}
                cur["cards"].append(card)
            elif ln.startswith(" use: "):
                card["use"] = nl(ln[6:])
            elif ln.startswith(" ex: "):
                card["ex"].append(pair(ln[5:]))
            elif ln.startswith(" trap: "):
                card["trap"] = ln[7:]
            elif ln.startswith(" tip: "):
                card["tip"] = ln[6:]
            elif ln.startswith(" vs: "):
                other, diff = ln[5:].split(" | ", 1)
                card["vs"].append({"pattern": other.strip(), "diff_vi": diff.strip()})
            elif ln.startswith("W: "):
                head, pos, meaning, ex = [x.strip() for x in ln[3:].split(" | ")]
                cur["words"].append({"head": head, "pos": pos, "meaning": meaning, "ex": pair(ex)})
            elif ln.startswith("Q: "):
                parts = [x.strip() for x in ln[3:].split(" | ")]
                cur["q"].append({"text": parts[0], "options": parts[1:5], "why": parts[5], "card": int(parts[6]) - 1})
            elif ln.startswith("B: "):
                vi, en = ln[3:].split(" | ")
                cur["b"].append((vi.strip(), en.strip()))
            elif ln.startswith("F: "):
                text, accepted, tip = [x.strip() for x in ln[3:].split(" | ")]
                cur["f"].append({"text": text, "accepted": [a.strip() for a in accepted.split(";")], "tip": tip})
            elif ln.startswith("S: "):
                en, vi, model = [x.strip() for x in ln[3:].split(" | ")]
                cur["s"] = {"en": en, "vi": vi, "model": model}
            else:
                raise SystemExit(f"{name}: cannot read {ln[:60]!r}")
    return units


def parse_vocab_units() -> dict[int, dict]:
    units: dict[int, dict] = {}
    cur = None
    for ln in lines("vocab_units.txt"):
        if ln.startswith("#U "):
            n, title, title_vi, pages = [x.strip() for x in ln[3:].split(" | ")]
            cur = {"n": int(n), "title": title, "title_vi": title_vi, "pages": pages}
            units[int(n)] = cur
        elif ln.startswith("goal: "):
            cur["goal"] = ln[6:]
        elif ln.startswith("ielts: "):
            cur["ielts"] = ln[7:]
        elif ln.startswith("S: "):
            en, vi, model = [x.strip() for x in ln[3:].split(" | ")]
            cur["s"] = {"en": en, "vi": vi, "model": model}
    return units


def parse_topic_words() -> dict[int, list[dict]]:
    out: dict[int, list[dict]] = {}
    unit = 0
    for ln in lines("topic_vocab.txt"):
        if ln.startswith("#"):
            unit = int(ln[1:].split()[0])
            out[unit] = []
            continue
        parts = ln.split("|")
        out[unit].append({"head": parts[0], "pos": parts[1], "meaning": parts[2], "recognize": len(parts) > 3 and parts[3] == "~"})
    return out


def parse_examples(name: str) -> dict[str, dict]:
    out = {}
    for ln in lines(name):
        head, meaning, ex = ln.split("|")
        en, vi = pair(ex)
        out[head.strip()] = {"head": head.strip(), "meaning": meaning.strip(), "en": en, "vi": vi}
    return out


def parse_wf() -> dict[str, dict]:
    out = {}
    for ln in lines("word_formation.txt"):
        base, pos, meaning, forms = ln.split("|")
        out[base] = {"head": base, "pos": pos, "meaning": meaning, "forms": [tuple(f.strip().split("=")) for f in forms.split(",")]}
    return out


def parse_skills() -> dict[int, dict]:
    out: dict[int, dict] = {}
    cur = None
    for ln in lines("skills.txt"):
        if ln.startswith("#U "):
            cur = {"q": []}
            out[int(ln[3:])] = cur
        elif ln.startswith("R: "):
            cur["title"], cur["text"] = [x.strip() for x in ln[3:].split(" | ", 1)]
        elif ln.startswith("RQ: "):
            q, right, w1, w2, why = [x.strip() for x in ln[4:].split(" | ")]
            cur["q"].append({"q": q, "options": [right, w1, w2], "why": why})
        elif ln.startswith("W: "):
            cur["w"] = dict(zip(("en", "vi", "model"), [x.strip() for x in ln[3:].split(" | ")]))
    return out


def parse_methods() -> dict[int, dict]:
    """methods.txt: the topic-sentence choice (T) and the passage summary (M) of each unit."""
    out: dict[int, dict] = {}
    cur: dict = {}
    for ln in lines("methods.txt"):
        if ln.startswith("#U "):
            cur = {}
            out[int(ln[3:])] = cur
        elif ln.startswith("T: "):
            good, avg, narrow = [x.strip() for x in ln[3:].split(" | ")]
            cur["t"] = {"good": good.lstrip("+= ").strip(), "prepend": good.startswith("+"), "avg": avg, "narrow": narrow}
        elif ln.startswith("M: "):
            cur["chain"], cur["summary"] = [x.strip() for x in ln[3:].split(" | ")]
    return out


def parse_speaking_bank() -> dict[int, dict]:
    out: dict[int, dict] = {}
    cur: dict = {}
    for ln in lines("speaking_bank.txt"):
        if ln.startswith("#U "):
            cur = {}
            out[int(ln[3:])] = cur
        elif ln[:4] in ("P1: ", "P3: "):
            qs, vi, model = [x.strip() for x in ln[4:].split(" | ")]
            cur[ln[:2]] = {"qs": [q.strip() for q in qs.split(" ; ")], "vi": vi, "model": model}
        elif ln.startswith("P2: "):
            card, bullets, vi, model = [x.strip() for x in ln[4:].split(" | ")]
            cur["P2"] = {"card": card, "bullets": [b.strip() for b in bullets.split(";")], "vi": vi, "model": model}
    return out


TFNG = ["True", "False", "Not Given"]


def reading_task(ex_id: str, n: int, sk: dict) -> dict:
    """A short passage with three questions in exam form (one choice question, two True/False/Not Given)."""
    questions = []
    for i, q in enumerate(sk["q"], 1):
        qid = f"{ex_id}{'abc'[i - 1]}"
        if set(q["options"]) == set(TFNG):
            order = TFNG
        else:
            order = q["options"][:]
            rng(qid).shuffle(order)
        questions.append({"id": qid, "prompt_en": q["q"], "options": [{"id": str(j + 1), "text": t} for j, t in enumerate(order)],
                          "answer": str(order.index(q["options"][0]) + 1), "explanation_vi": q["why"], "tags": []})
    return {"id": ex_id, "skill": "reading", "type": "read_passage", "title_vi": f"Đọc · Unit {n} · {sk['title']}"[:70],
            "instruction_vi": "Đọc từng câu và chọn từ khóa (danh từ trước, động từ sau), bỏ chi tiết quá nhỏ, nối các từ khóa lại để thấy ý chính, rồi mới trả lời. True = bài nói đúng như vậy; False = bài nói ngược lại; Not Given = bài không nói.",
            "stimulus": {"kind": "passage", "text": sk["text"]}, "questions": questions}


FRAME = [
    "Trước khi viết: ghi dàn ý bằng danh từ và mũi tên (ý chính → lý do hoặc chi tiết → ví dụ → kết). Chưa viết thành câu.",
    "Câu 1 là câu chủ đề: nêu ý chính và cho biết đoạn sẽ nói gì. Không mở bằng một câu chung chung.",
    "Câu 2–4: mỗi câu trả lời «vì sao?» hoặc «như thế nào?» cho câu đứng trước nó. Có ít nhất một ví dụ cụ thể của chính bạn.",
    "Câu cuối: kết lại bằng kết quả, cảm nghĩ hoặc dự định. Không thêm ý mới.",
]


def topic_sentence_task(ex_id: str, n: int, sk: dict, t: dict) -> dict:
    """Which sentence opens the paragraph best: the idea plus what the paragraph will say, topic only, or a detail."""
    good = t["good"] or sk["w"]["model"].split(". ")[0].rstrip(".") + "."
    why = (f"Câu đúng nêu ý chính và cho biết đoạn sẽ nói gì. «{t['avg']}» chỉ gọi tên chủ đề, chưa nói gì về nó. "
           f"«{t['narrow']}» là một chi tiết: nó phải đứng sau câu chủ đề.")
    return mcq(ex_id, f"Câu chủ đề · Unit {n}", None, f"Đề bài: {sk['w']['vi']} Câu nào mở đoạn tốt nhất?", [good, t["avg"], t["narrow"]], why,
               "Chọn câu chủ đề tốt nhất cho đoạn văn. Câu chủ đề tốt có đủ hai phần: ý chính và nội dung đoạn sẽ nói.")


def summary_task(ex_id: str, n: int, sk: dict, m: dict) -> dict:
    return {"id": ex_id, "skill": "writing", "type": "write_essay", "number": "R2", "title_vi": f"Tóm tắt bài đọc · Unit {n}", "points": 5,
            "instruction_vi": "Tóm tắt bài đọc này bằng một hoặc hai câu tiếng Anh của chính bạn. Không chép nguyên câu trong bài.",
            "limits": {"min": 10, "max": 40}, "prompt_en": sk["text"],
            "framework_vi": ["Mỗi câu trong bài: ghi lại 1–2 từ khóa (danh từ trước, động từ sau).", "Gạch bỏ chi tiết quá nhỏ: con số, tên riêng phụ, ví dụ.",
                             "Nối các từ khóa còn lại bằng mũi tên theo thứ tự của bài.", "Nhìn chuỗi từ khóa và viết thành một hoặc hai câu.",
                             "Tự hỏi: ý chính của đoạn là gì, và đoạn này có vai trò gì (kể chuyện, giải thích, khuyên, so sánh)?"],
            "model_answer_en": m["summary"], "model_note_vi": f"Chuỗi từ khóa mẫu: {m['chain']}. Chuỗi của bạn không cần giống hệt; cần đủ ý chính và đúng thứ tự.",
            "checklist_vi": ["Tóm tắt ngắn hơn bài rất nhiều (10–40 từ).", "Có ý chính, không có chi tiết nhỏ.", "Dùng lời của bạn, không chép cả câu.", "Không thêm ý kiến riêng."]}


def speaking_sets(pid: str, n: int, sb: dict) -> list[dict]:
    """Three exam-style speaking tasks on the unit's topic: Part 1 questions, a Part 2 card, Part 3 questions."""
    tips = ["Ghi âm, nghe lại, chọn một lỗi để sửa rồi nói lần hai.", "Bài mẫu chỉ để đối chiếu sau khi bạn đã tự nói; đừng học thuộc lòng."]
    p1, p2, p3 = sb["P1"], sb["P2"], sb["P3"]
    base = {"skill": "speaking", "type": "speak", "max_points": 9, "patterns_vi": []}
    return [
        {**base, "id": f"{pid}S2", "number": "S2", "title_vi": f"Nói Part 1 · Unit {n}", "prep_sec": 15, "answer_sec": 75,
         "prompt_en": "\n".join(f"{i}. {q}" for i, q in enumerate(p1["qs"], 1)), "prompt_vi": p1["vi"],
         "plan": [{"when_vi": "Mỗi câu hỏi", "do_vi": "Trả lời thẳng trong câu đầu tiên, không lặp lại cả câu hỏi."},
                  {"when_vi": "Câu 2–3", "do_vi": "Thêm một lý do hoặc một chi tiết của chính bạn. Mỗi câu hỏi nói 2–3 câu là đủ."},
                  {"when_vi": "Luyện 4 mức", "do_vi": "Mức 1: viết cả câu rồi đọc. Mức 2: chỉ ghi từ khóa và mũi tên. Mức 3: nói không cần ghi. Mức 4: ghi âm và tự sửa."}],
         "tips_vi": tips + ["Bài mẫu trả lời câu hỏi thứ nhất; hai câu còn lại bạn tự trả lời theo cùng cách."], "model_answer_en": p1["model"]},
        {**base, "id": f"{pid}S3", "number": "S3", "title_vi": f"Nói Part 2 · Unit {n}", "prep_sec": 60, "answer_sec": 90,
         "prompt_en": p2["card"] + "\nYou should say:\n" + "\n".join(f"- {b}" for b in p2["bullets"]) + "\n- and explain why or how you feel about it.", "prompt_vi": p2["vi"],
         "plan": [{"when_vi": "1 phút chuẩn bị", "do_vi": "Ghi bốn dòng từ khóa: cái gì → tả thế nào → vì sao → chuyện của riêng bạn (lúc nào, việc gì, với ai, ý nghĩa)."},
                  {"when_vi": "0–20 giây", "do_vi": "Nói đó là gì và tả ngắn gọn."},
                  {"when_vi": "20–70 giây", "do_vi": "Kể chuyện của riêng bạn theo thứ tự thời gian. Đây là phần dài nhất."},
                  {"when_vi": "70–90 giây", "do_vi": "Nói vì sao nó quan trọng với bạn hoặc bạn cảm thấy thế nào."}],
         "tips_vi": tips + ["Trong kỳ thi thật, Part 2 dài 1–2 phút. Khi nói trôi 90 giây, hãy tự kéo dài lên 2 phút."], "model_answer_en": p2["model"]},
        {**base, "id": f"{pid}S4", "number": "S4", "title_vi": f"Nói Part 3 · Unit {n}", "prep_sec": 20, "answer_sec": 90,
         "prompt_en": "\n".join(f"{i}. {q}" for i, q in enumerate(p3["qs"], 1)), "prompt_vi": p3["vi"],
         "plan": [{"when_vi": "Câu 1", "do_vi": "Nêu ý kiến của bạn một cách rõ ràng."},
                  {"when_vi": "Câu 2–3", "do_vi": "Giải thích: tự hỏi «vì sao?» rồi trả lời; hỏi tiếp «vì sao?» một lần nữa nếu được."},
                  {"when_vi": "Câu cuối", "do_vi": "Đưa một ví dụ cụ thể (một người, một nơi, một lần) để chứng minh."}],
         "tips_vi": tips + ["Part 3 hỏi về xã hội, không hỏi về riêng bạn: nói về «people», «many families», rồi mới lấy ví dụ của mình.",
                            "Bài mẫu trả lời câu hỏi thứ nhất; câu thứ hai bạn tự trả lời theo cùng khung."], "model_answer_en": p3["model"]},
    ]


def writing_task(ex_id: str, n: int, sk: dict) -> dict:
    w = sk["w"]
    return {"id": ex_id, "skill": "writing", "type": "write_essay", "number": "W1", "title_vi": f"Viết đoạn ngắn · Unit {n}", "points": 10,
            "instruction_vi": w["vi"], "limits": {"min": 30, "max": 90}, "prompt_en": w["en"],
            "framework_vi": FRAME,
            "model_answer_en": w["model"], "model_note_vi": "Chỉ xem sau khi đã tự viết. So cấu trúc câu và thì của động từ, không chép lại.",
            "checklist_vi": ["Che các câu sau đi: chỉ đọc câu đầu, người đọc có biết đoạn sẽ nói gì không?", "Mỗi câu có đủ chủ ngữ và động từ đã chia.", "Danh từ đếm được số ít có a/an/the; ngôi thứ ba số ít có -s.", "Dùng ít nhất một cấu trúc hoặc ba từ của Unit này.", "Đọc to lại một lần để soát lỗi."]}


# -------------------------------------------------------------- exercises --
def mcq(ex_id: str, title: str, cloze: str | None, prompt_vi: str | None, options: list[str], why: str, instruction: str) -> dict:
    """One multiple-choice exercise; `options[0]` is the right answer, shown in a fixed shuffled order."""
    order = options[:]
    rng(ex_id).shuffle(order)
    q = {
        "id": ex_id,
        "options": [{"id": str(i + 1), "text": t} for i, t in enumerate(order)],
        "answer": str(order.index(options[0]) + 1),
        "explanation_vi": why,
        "tags": [],
    }
    if prompt_vi:
        q["prompt_vi"] = prompt_vi
    out = {"id": ex_id, "skill": "reading", "type": "read_cloze" if cloze else "read_match", "title_vi": title, "instruction_vi": instruction, "questions": [q]}
    if cloze:
        out["stimulus"] = {"kind": "cloze", "text": cloze}
    return out


def tiles_of(sentence: str, key: str) -> list[str]:
    """The words of the sentence, one tile each, in a fixed shuffled order (never the right one)."""
    words = sentence.split(" ")
    shuffled = words[:]
    r = rng(key)
    for _ in range(50):
        r.shuffle(shuffled)
        if shuffled != words:
            break
    return shuffled


def fits_tiles(sentence: str) -> bool:
    return 3 <= len(sentence.split(" ")) <= 10


def build_order(ex_id: str, title: str, meaning_vi: str, sentence: str) -> dict:
    return {
        "id": ex_id, "skill": "build", "type": "build_order", "rung": 1, "title_vi": title,
        "instruction_vi": "Chạm vào các mảnh theo đúng thứ tự để xếp thành một câu đúng.",
        "meaning_vi": meaning_vi, "tiles": tiles_of(sentence, ex_id), "answers": [sentence],
    }


def write_fill(ex_id: str, title: str, text: str, accepted: list[str], tip: str) -> dict:
    return {
        "id": ex_id, "skill": "build", "type": "write_fill", "rung": 2, "number": "Bước 2", "title_vi": title, "points": 3,
        "instruction_vi": "Gõ từ hoặc cụm từ còn thiếu.", "text": text,
        "blanks": [{"id": "㉠", "points": 3, "accepted": accepted, "common_errors_vi": tip}], "tips_vi": [],
    }


def speak(ex_id: str, title: str, s: dict, patterns: list[str]) -> dict:
    return {
        "id": ex_id, "skill": "speaking", "type": "speak", "number": "S1", "title_vi": title, "max_points": 9,
        "prep_sec": 60, "answer_sec": 60, "prompt_en": s["en"], "prompt_vi": s["vi"],
        "plan": [
            {"when_vi": "1 phút chuẩn bị", "do_vi": "Ghi ý bằng từ khóa nối nhau bằng mũi tên (ít nhất ba mũi tên), không viết cả câu."},
            {"when_vi": "0–15 giây", "do_vi": "Trả lời thẳng vào câu hỏi bằng một câu."},
            {"when_vi": "15–45 giây", "do_vi": "Nêu lý do hoặc chi tiết, rồi một ví dụ của chính bạn."},
            {"when_vi": "45–60 giây", "do_vi": "Kết lại bằng một câu về cảm nghĩ hoặc dự định."},
        ],
        "tips_vi": [
            "Ghi âm, nghe lại, chọn một lỗi để sửa rồi nói lần hai.",
            "Bài mẫu chỉ để đối chiếu sau khi bạn đã tự nói; đừng học thuộc lòng.",
        ],
        "patterns_vi": patterns[:4], "model_answer_en": s["model"],
    }


def dictation(ex_id: str, title: str, sentences: list[tuple[str, str]], focus: list[tuple[str, str]]) -> dict | None:
    picked: list[tuple[str, str]] = []
    for en, vi in sentences:
        if len(picked) < 3 and sum(len(e) for e, _ in picked) + len(en) <= 125:
            picked.append((en, vi))
    if len(picked) < 2 or len(focus) < 2:
        return None
    return {
        "id": ex_id, "skill": "listening", "type": "listen_dictation", "title_vi": title,
        "instruction_vi": "Nghe rồi gõ lại từng câu. Nghe lại bao nhiêu lần cũng được. Sau khi kiểm tra, nghe lại và đọc theo.",
        "stimulus": {"kind": "audio", "turns": [{"speaker": "FM"[i % 2], "text": en, "vi": vi} for i, (en, vi) in enumerate(picked)]},
        "focus": [{"ko": k, "vi": v} for k, v in focus[:6]],
        "tips_vi": ["Chú ý âm cuối của từ (-s, -ed, -t, -d): đó là chỗ người Việt hay nghe sót và nói sót."],
    }


def alternatives(head: str) -> set[str]:
    return {w for w in re.split(r"[ /()]", head) if w}


def gap(example: str) -> tuple[str, str]:
    m = re.search(r"\[(.+?)\]", example)
    return example[: m.start()] + "( )" + example[m.end() :], m.group(1)


def plain(example: str) -> str:
    return re.sub(r"\[(.+?)\]", r"\1", example)


# ------------------------------------------------------------------ lessons --
def goal_note(u: dict, vocab_unit: bool) -> dict:
    kind = "Unit từ vựng" if vocab_unit else "Unit ngữ pháp"
    body = (
        f"• 🎯 {u['goal']}\n"
        f"• 📖 Trong sách: {kind} {u['n']}, trang {u['pages'].replace('-', '–')}. Học thẻ ở đây trước, rồi làm các bài tập của Unit trong sách và tự chấm bằng đáp án cuối sách.\n"
        "• 🗣️ Kết thúc bằng phần Nói: tự nói, ghi âm, nghe lại, sửa một lỗi rồi nói lần hai."
    )
    return {"title": "Mục tiêu của bài", "body": body, "kind": "goal"}


def add_skills(lesson: dict, bank: dict[str, list[dict]], n: int, sk: dict | None, md: dict | None = None, sb: dict | None = None) -> None:
    """The unit's reading, summary, topic sentence and writing: after the cards' own questions, closing the last
    sitting. A vocabulary unit also gets three exam-style speaking tasks after its own speaking task."""
    if not sk:
        return
    pid = f"B1U{n:02d}"
    md = md or {}
    if md.get("t", {}).get("prepend"):
        sk = {**sk, "w": {**sk["w"], "model": md["t"]["good"] + " " + sk["w"]["model"]}}
    r = reading_task(f"{pid}R1", n, sk)
    w = writing_task(f"{pid}W1", n, sk)
    bank["reading"].append(r)
    flow = [r["id"]]
    if "summary" in md:
        bank.setdefault("writing", []).append(summary_task(f"{pid}R2", n, sk, md))
        flow.append(f"{pid}R2")
    if "t" in md:
        bank["reading"].append(topic_sentence_task(f"{pid}T1", n, sk, md["t"]))
        flow.append(f"{pid}T1")
    bank.setdefault("writing", []).append(w)
    flow.append(w["id"])
    speak_id = f"{pid}S1"
    for seq in (lesson["exercise_ids"], lesson["sessions"][-1]["check"]):
        at = seq.index(speak_id) if speak_id in seq else len(seq)
        seq[at:at] = flow
    if sb:
        sets = speaking_sets(pid, n, sb)
        bank["speaking"] += sets
        lesson["exercise_ids"] += [e["id"] for e in sets]


def grammar_lesson(u: dict) -> tuple[dict, dict[str, list[dict]], dict[str, list[str]]]:
    n = u["n"]
    pid = f"B1U{n:02d}"
    title = f"Luyện · Unit {n}"
    bank: dict[str, list[dict]] = {"reading": [], "build": [], "speaking": [], "listening": []}
    links: dict[str, list[str]] = {}
    patterns = [c["pattern"] for c in u["cards"]]

    by_card: dict[int, list[str]] = {}
    for i, q in enumerate(u["q"], 1):
        ex = mcq(f"{pid}Q{i}", f"Chọn dạng đúng · {u['title_vi']}"[:70], q["text"], None, q["options"], q["why"], "Chọn phương án đúng cho chỗ trống.")
        bank["reading"].append(ex)
        links[ex["id"]] = [patterns[q["card"]]]
        by_card.setdefault(q["card"], []).append(ex["id"])
    for i, (vi, en) in enumerate(u["b"], 1):
        if not fits_tiles(en):
            raise SystemExit(f"Unit {n}: build sentence has more than 10 words: {en!r}")
        bank["build"].append(build_order(f"{pid}B{i}", f"Xếp câu · Unit {n}", vi, en))
    for i, f in enumerate(u["f"], 1):
        bank["build"].append(write_fill(f"{pid}F{i}", f"Sửa và hoàn thành câu · Unit {n}", f["text"], f["accepted"], f["tip"]))
    bank["speaking"].append(speak(f"{pid}S1", f"Nói · {u['title_vi']}"[:70], u["s"], patterns))
    d = dictation(f"{pid}D1", f"Nghe chép · Unit {n}", [c["ex"][0] for c in u["cards"]] + [w["ex"] for w in u["words"]],
                  [(w["head"], w["meaning"]) for w in u["words"]])
    if d:
        bank["listening"].append(d)

    vocab = [
        {"headword": w["head"], "pos": w["pos"], "meaning_vi": w["meaning"], "example_en": w["ex"][0], "example_vi": w["ex"][1],
         "family": "Từ khóa của bài", "priority": "core", "source": f"Haru English · B1 Unit {n}"}
        for w in u["words"]
    ]
    grammar = []
    for c in u["cards"]:
        g = {"pattern": c["pattern"], "meaning_vi": c["meaning"], "usage_context_vi": c["use"], "contrasts": c["vs"],
             "example_en": "\n".join(e for e, _ in c["ex"]), "example_vi": "\n".join(v for _, v in c["ex"]),
             "importance": c["importance"], "source": f"{BOOK}, Unit {n}, pp. {u['pages']}"}
        if c["trap"]:
            g["note_vi"] = "Lỗi người Việt hay mắc: " + c["trap"]
        if c["tip"]:
            g["exam_tip_vi"] = c["tip"]
        grammar.append(g)

    # sittings: at most three cards each; the key words go with the first; each sitting closes with its cards' questions
    groups = [list(range(len(patterns)))] if len(patterns) <= 3 else [list(range(2)), list(range(2, len(patterns)))]
    rest = [e["id"] for e in bank["build"]] + [e["id"] for e in bank["listening"]]
    sessions = []
    for gi, idx in enumerate(groups):
        checks = [qid for c in idx for qid in by_card.get(c, [])]
        if gi == len(groups) - 1:
            checks += rest + [f"{pid}S1"]
        sessions.append({
            "title_vi": (f"Buổi {gi + 1} · " + patterns[idx[0]].split(":")[0])[:70],
            "can_do_vi": ("Sau buổi này bạn dùng được: " + "; ".join(u["cards"][c]["meaning"].lower() for c in idx) + ".")[:240],
            "use_vi": u["ielts"][:200],
            "vocab": [w["head"] for w in u["words"]] if gi == 0 else [],
            "grammar": [patterns[c] for c in idx],
            "check": checks,
        })
    traps = [c["trap"] for c in u["cards"] if c["trap"] and len(c["trap"]) <= 230 and c["trap"].count("`") % 2 == 0]
    lesson = {
        "slug": f"b1-u{n:02d}-{slugify(u['title'])}"[:60].rstrip("-"),
        "title": f"Unit {n} · {u['title_vi']}", "title_en": u["title"], "topic": TOPIC, "track": "beginner", "level": 3, "sort_order": n,
        "summary": f"{u['goal']} Ngữ pháp: {'; '.join(patterns)}.",
        "vocab": vocab, "grammar": grammar,
        "notes": [goal_note(u, False), {"title": "Dùng ở đâu trong IELTS", "body": u["ielts"], "kind": "language"}],
        "bank": "b1",
        "coach": {"focus_vi": [f"{c['pattern']}: {c['meaning']}"[:230] for c in u["cards"][:3]], "watch_out_vi": traps[:2]},
        "exercise_ids": [e["id"] for k in ("reading", "build", "listening", "speaking") for e in bank[k]],
        "sessions": sessions,
        "editor_notes": [{"title": "Nguồn", "body": f"Tiêu đề và số trang theo mục lục {BOOK}. Giải thích, ví dụ, câu hỏi và bài mẫu do khóa học tự soạn."}],
    }
    return lesson, bank, links


def vocab_lesson(u: dict, topic: list[dict], trays: dict[str, list[dict]], unverified: list[str]) -> tuple[dict, dict[str, list[dict]]]:
    n = u["n"]
    pid = f"B1U{n:02d}"
    bank: dict[str, list[dict]] = {"reading": [], "build": [], "speaking": [], "listening": []}
    src = f"{BOOK}, Unit {n}, pp. {u['pages']}"
    vocab: list[dict] = []
    seen: dict[str, dict] = {}

    def add(card: dict) -> None:
        seen[card["headword"]] = card
        vocab.append(card)

    for w in topic:
        add({"headword": w["head"], "pos": w["pos"], "meaning_vi": w["meaning"], "family": "1 · Topic vocabulary",
             "priority": "recognize" if w["recognize"] else "core", "source": src + "; word list pp. 184–201"})
    for kind, fam, pos in (("PV", "2 · Phrasal verbs", "V"), ("PP", "3 · Prepositional phrases", "X"), ("WP", "4 · Word patterns", "X")):
        for it in trays[kind]:
            add({"headword": it["head"], "pos": pos, "meaning_vi": it["meaning"], "example_en": plain(it["en"]), "example_vi": it["vi"],
                 "family": fam, "priority": "core", "source": src})
    wf_cards = []
    for it in trays["WF"]:
        forms = ", ".join(f"`{f}` ({LABEL[l]})" for f, l in it["forms"])
        if it["head"] in seen:  # the base is already a topic word of this unit: its forms go on that card
            seen[it["head"]]["note_vi"] = "Họ từ: " + forms
            continue
        card = {"headword": it["head"], "pos": it["pos"], "meaning_vi": it["meaning"], "note_vi": "Họ từ: " + forms,
                "family": "5 · Word formation", "priority": "core", "source": src + "; word formation pp. 212–216"}
        add(card)
        wf_cards.append(it)

    # --- exercises
    heads = [w["head"] for w in topic]
    r = rng(pid)
    quiz = r.sample(topic, min(10, len(topic)))
    meaning_ids: dict[str, str] = {}
    for i, w in enumerate(quiz, 1):
        same = [x["head"] for x in topic if x["pos"] == w["pos"] and x["head"] != w["head"]] or [h for h in heads if h != w["head"]]
        wrong = rng(pid + w["head"]).sample(same, min(3, len(same)))
        short = re.sub(r"\(.*?\)", "", w["meaning"]).strip(" ;")
        ex = mcq(f"{pid}M{i}", f"Chọn từ đúng nghĩa · Unit {n}", None, f"Từ nào có nghĩa «{short}»?", [w["head"], *wrong],
                 f"`{w['head']}`: {w['meaning']}.", "Chọn từ tiếng Anh đúng với nghĩa đã cho.")
        bank["reading"].append(ex)
        meaning_ids[w["head"]] = ex["id"]
    cloze_ids: dict[str, str] = {}
    k = 0
    for kind, pool, label in (("PV", PARTICLES, "Cụm động từ"), ("PP", PREPS, "Cụm giới từ"), ("WP", PREPS, "Giới từ theo sau")):
        for it in trays[kind]:
            k += 1
            text, answer = gap(it["en"])
            avoid = {a.lower() for a in alternatives(it["head"])} | {answer.lower()} | set(ALSO_OK.get(it["head"], "").split())
            wrong = [p for p in rng(pid + it["head"]).sample(pool, len(pool)) if p not in avoid][:3]
            shown = [w.capitalize() if answer[0].isupper() else w for w in wrong]
            # several particles make a real phrasal verb with the same verb, so the meaning wanted is given
            hint = f"Nghĩa cần diễn đạt: {it['meaning']}" if kind == "PV" else None
            ex = mcq(f"{pid}C{k}", f"{label} · Unit {n}", text, hint, [answer, *shown], f"`{it['head']}`: {it['meaning']}.",
                     "Chọn từ đúng cho chỗ trống.")
            bank["reading"].append(ex)
            cloze_ids[it["head"]] = ex["id"]
    short_pv = sorted((it for it in trays["PV"] if fits_tiles(plain(it["en"]).rstrip(".!?"))), key=lambda it: len(it["en"]))[:3]
    for i, it in enumerate(short_pv, 1):
        bank["build"].append(build_order(f"{pid}B{i}", f"Xếp câu · Unit {n}", it["vi"], plain(it["en"]).rstrip(".!?")))
    wf_ids: dict[str, str] = {}
    for i, it in enumerate(wf_cards[:8], 1):
        form, label = next(((f, l) for f, l in it["forms"] if l in "NPAX"), it["forms"][0])
        ex = write_fill(f"{pid}F{i}", f"Biến đổi từ loại · Unit {n}", f"Dạng {LABEL[label]} của «{it['head']}» là ( ㉠ ).", [form],
                        f"`{it['head']}` → `{form}` ({LABEL[label]}).")
        bank["build"].append(ex)
        wf_ids[it["head"]] = ex["id"]
    bank["speaking"].append(speak(f"{pid}S1", f"Nói · {u['title_vi']}"[:70], u["s"], []))
    d = dictation(f"{pid}D1", f"Nghe chép · Unit {n}", [(plain(it["en"]), it["vi"]) for kind in ("WP", "PV", "PP") for it in trays[kind]],
                  [(w["head"], re.sub(r"\(.*?\)", "", w["meaning"]).strip(" ;")) for w in topic[:6]])
    if d:
        bank["listening"].append(d)

    # --- sittings: at most 16 new items each
    def chunks(seq: list[str], size: int) -> list[list[str]]:
        k = max(1, -(-len(seq) // size))
        per = -(-len(seq) // k)
        return [seq[i : i + per] for i in range(0, len(seq), per)]

    sessions = []
    for i, part in enumerate(chunks(heads, 16), 1):
        sessions.append({
            "title_vi": f"Từ chủ đề {i} · {u['title_vi']}"[:70],
            "can_do_vi": f"Sau buổi này bạn nhận ra và dùng được {len(part)} từ chủ đề «{u['title_vi']}», từ «{part[0]}» đến «{part[-1]}».",
            "vocab": part, "check": [meaning_ids[h] for h in part if h in meaning_ids],
        })
    phr = [it["head"] for it in trays["PV"]] + [it["head"] for it in trays["PP"]]
    for i, part in enumerate(chunks(phr, 16), 1):
        sessions.append({
            "title_vi": f"Cụm động từ và cụm giới từ {i}"[:70],
            "can_do_vi": "Sau buổi này bạn chọn đúng tiểu từ và giới từ trong các cụm cố định của Unit, không dịch từng chữ từ tiếng Việt.",
            "vocab": part, "check": [cloze_ids[h] for h in part] + ([e["id"] for e in bank["build"] if e["type"] == "build_order"] if i == 1 else []),
        })
    wp = [it["head"] for it in trays["WP"]]
    if wp:
        sessions.append({
            "title_vi": "Giới từ theo sau động từ, tính từ, danh từ",
            "can_do_vi": "Sau buổi này bạn dùng đúng giới từ đi sau các động từ, tính từ và danh từ của Unit: lỗi mất điểm nhiều nhất của người Việt.",
            "vocab": wp, "check": [cloze_ids[h] for h in wp],
        })
    wf = [it["head"] for it in wf_cards]
    last_checks = list(wf_ids.values()) + [e["id"] for e in bank["listening"]] + [f"{pid}S1"]
    if wf:
        sessions.append({
            "title_vi": "Biến đổi từ loại và phần Nói",
            "can_do_vi": "Sau buổi này bạn đổi được từ gốc sang danh từ, tính từ hoặc dạng trái nghĩa, và nói được một phút về chủ đề của Unit.",
            "vocab": wf, "check": last_checks,
        })
    else:
        sessions[-1]["check"] += last_checks

    notes = [goal_note(u, True), {"title": "Dùng ở đâu trong IELTS", "body": u["ielts"], "kind": "language"}]
    editor = [{"title": "Nguồn", "body": f"Danh sách từ theo {BOOK}, pp. 184–216. Nghĩa tiếng Việt, câu ví dụ, câu hỏi và bài mẫu do khóa học tự soạn."}]
    if unverified:
        editor.append({"title": "Cần đối chiếu với sách", "body": "Các mục sau được xếp vào Unit này theo chủ đề, chưa thấy trong trang của Unit: " + ", ".join(unverified) + "."})
    lesson = {
        "slug": f"b1-u{n:02d}-{slugify(u['title'])}", "title": f"Unit {n} · {u['title_vi']}", "title_en": u["title"], "topic": TOPIC,
        "track": "beginner", "level": 3, "sort_order": n,
        "summary": f"{u['goal']} {len(topic)} từ chủ đề, {len(trays['PV'])} cụm động từ, {len(trays['PP'])} cụm giới từ, {len(trays['WP'])} mẫu giới từ, {len(trays['WF'])} họ từ.",
        "vocab": vocab, "notes": notes, "bank": "b1",
        "coach": {
            "focus_vi": [
                "Học cụm, không học từ rời: mỗi cụm động từ, cụm giới từ và mẫu giới từ đi kèm một câu ví dụ.",
                "Từ chủ đề chỉ cần nhận ra khi đọc và nghe; các cụm và mẫu giới từ phải dùng được khi nói và viết.",
            ],
            "watch_out_vi": ["Giới từ tiếng Anh không dịch được từ tiếng Việt: học cả cụm như một khối."],
        },
        "exercise_ids": [e["id"] for kk in ("reading", "build", "listening", "speaking") for e in bank[kk]],
        "sessions": sessions, "editor_notes": editor,
    }
    return lesson, bank


GUIDES = {
    "reading": [{"title_vi": "Cách làm", "body_vi": "Đọc cả câu trước khi nhìn phương án. Với câu về giới từ, hãy tự nhẩm đáp án rồi mới đối chiếu. Sai câu nào, mở lại thẻ của câu đó."}],
    "build": [{"title_vi": "Cách làm", "body_vi": "Xếp câu trước, gõ câu sau. Khi gõ sai, đọc phần giải thích rồi tự viết thêm một câu của chính bạn với cùng cấu trúc."}],
    "listening": [{"title_vi": "Cách làm", "body_vi": "Nghe hết một lượt không dừng, lượt hai mới gõ. Sau khi xem đáp án, đọc đuổi theo băng hai lần."}],
    "writing": [{"title_vi": "Cách viết một đoạn", "bullets_vi": [
        "Nghĩ bằng tiếng Việt trước: ý chính là gì, vì sao, ví dụ nào.",
        "Viết câu đơn đúng trước, rồi mới nối thành câu ghép (and, but, so) và câu phức (because, although, when).",
        "Mạch của đoạn: khái quát → chi tiết → rất cụ thể → khái quát lại.",
    ]}],
    "speaking": [{
        "title_vi": "Bốn mức chuẩn bị",
        "bullets_vi": [
            "Mức 1 (mới bắt đầu): viết đủ câu trả lời bằng câu đơn, chủ ngữ dễ (I, it, there), rồi đọc to.",
            "Mức 2 (có nền): chỉ ghi ý bằng từ khóa và mũi tên, ít nhất ba mũi tên.",
            "Mức 3 (có phản xạ): đọc câu hỏi rồi nói ngay, không viết.",
            "Mức 4: nói, ghi âm, nghe lại và tự sửa.",
        ],
    }],
}


def main() -> None:
    assign = json.loads((HERE / "unit_assignment.json").read_text(encoding="utf-8"))
    grammar = parse_grammar()
    vocab_units = parse_vocab_units()
    topic = parse_topic_words()
    sources = {"PV": parse_examples("phrasal_verbs.txt"), "PP": parse_examples("prep_phrases.txt"), "WP": parse_examples("word_patterns.txt"), "WF": parse_wf()}

    LESSONS.mkdir(parents=True, exist_ok=True)
    BANK.mkdir(parents=True, exist_ok=True)
    for old in LESSONS.glob("b1-*.json"):
        old.unlink()
    bank: dict[str, list[dict]] = {"reading": [], "build": [], "speaking": [], "listening": [], "writing": []}
    links: dict[str, list[str]] = {}
    skills = parse_skills()
    methods = parse_methods()
    speaking = parse_speaking_bank()
    count = {"lessons": 0, "words": 0, "cards": 0, "exercises": 0, "sittings": 0}
    for n in range(1, 43):
        if n in grammar:
            lesson, b, l = grammar_lesson(grammar[n])
            links.update(l)
        else:
            trays = {k: [sources[k][h] for h, u in assign["by_kind"][k].items() if u == n] for k in sources}
            flagged = [h for k in sources for h in assign["unverified"].get(k, []) if assign["by_kind"][k][h] == n]
            lesson, b = vocab_lesson(vocab_units[n], topic[n], trays, flagged)
        add_skills(lesson, b, n, skills.get(n), methods.get(n), speaking.get(n))
        for k in bank:
            bank[k] += b.get(k, [])
        (LESSONS / f"{lesson['slug']}.json").write_text(json.dumps(lesson, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        count["lessons"] += 1
        count["words"] += len(lesson["vocab"])
        count["cards"] += len(lesson.get("grammar", []))
        count["exercises"] += len(lesson["exercise_ids"])
        count["sittings"] += len(lesson["sessions"])
    for k, items in bank.items():
        (BANK / f"{k}.json").write_text(json.dumps({"skill": k, "guide": GUIDES[k], "items": items}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    (BANK / "grammar_links.json").write_text(json.dumps({"links": links}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    (BANK / "overview.json").write_text(json.dumps({
        "blocks": [{
            "title_vi": "Cách học một Unit",
            "bullets_vi": [
                "Học thẻ trong app trước: mỗi buổi khoảng 15 phút, kết thúc bằng vài câu kiểm tra.",
                "Mở sách Destination B1, làm các bài tập của Unit đó và tự chấm bằng đáp án cuối sách.",
                "Làm phần Nghe chép và phần Nói của Unit; ghi âm và nói lại lần hai.",
                "Sau mỗi ba Unit, làm bài Review trong sách; sau Unit 21 và Unit 42, làm Progress Test.",
            ],
        }],
        "disclaimer_vi": ["Giải thích, ví dụ và câu hỏi trong app do khóa học tự soạn theo mục lục của sách; bài tập gốc nằm trong sách của bạn."],
    }, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(count)


if __name__ == "__main__":
    main()

"""Build app/seed/nikl/topik_bank.json — the «Kho từ TOPIK»: every intermediate (중급) and advanced
(고급) word of 한국어기초사전 (NIKL, CC BY-SA 2.0 KR), grouped into study topics, with the
dictionary's own Vietnamese equivalent, its Korean definition, one example sentence, the
pronunciation and the hanja. The Sino-Vietnamese reading of each character comes from the cards
the course already teaches (by character AND its Korean syllable, so 樂 in 음악 and in 오락 can
differ); a character the course does not have is read with Unihan's kVietnamese, but only when
Unihan gives one reading and the character has one Korean reading (scripts/data/unihan_vi_ko.json,
Unicode License v3). A word with any character left unresolved gets no reading rather than a guess:
長 (trường/trưởng) under one Korean 장, for instance.

    python scripts/build_topik_bank.py <krdict XML folder>

The XML is the full download of 한국어기초사전 (https://github.com/spellcheck-ko/korean-dict-nikl-krdict).
"""
from __future__ import annotations

import glob
import json
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

from lxml import etree

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "app" / "seed" / "nikl" / "topik_bank.json"
LESSONS = ROOT / "app" / "seed" / "lessons"
CHUNK = 120  # words in one topic deck at most

GRADES = {"중급": "mid", "고급": "adv"}
POS = {"명사": "N", "의존 명사": "N", "대명사": "N", "수사": "N", "동사": "V", "보조 동사": "V", "형용사": "A", "보조 형용사": "A"}
HANJA = re.compile(r"[一-鿿]")

# semantic category (krdict "A > B") -> (topic key, Vietnamese title). First match wins.
TOPICS: list[tuple[str, str, str]] = [
    ("개념 > 시간", "thoi-gian", "Thời gian"),
    ("개념 > 모양|개념 > 밝기|개념 > 색깔|개념 > 성질|개념 > 온도", "hinh-dang-tinh-chat", "Hình dạng, màu sắc, tính chất"),
    ("개념 > 빈도|개념 > 세는 말|개념 > 속도|개념 > 수|개념 > 순서|개념 > 양|개념 > 정도", "so-luong-muc-do", "Số lượng, mức độ, tần suất"),
    ("개념 >", "vi-tri-khu-vuc", "Vị trí, phương hướng, khu vực"),
    ("경제 생활", "kinh-te", "Kinh tế, tiêu dùng"),
    ("교육", "giao-duc", "Giáo dục, học thuật"),
    ("자연 > 기상 및 기후|자연 > 재해", "thoi-tiet-thien-tai", "Thời tiết, khí hậu, thiên tai"),
    ("자연|동식물", "tu-nhien", "Tự nhiên, động thực vật"),
    ("문화|종교", "van-hoa", "Văn hóa, nghệ thuật, tôn giáo"),
    ("사회 생활 > 교통", "giao-thong", "Giao thông"),
    ("사회 생활 > 말|사회 생활 > 언어 행위|사회 생활 > 소통 수단|사회 생활 > 매체|사회 생활 > 통신 행위", "giao-tiep", "Ngôn ngữ, giao tiếp, truyền thông"),
    ("사회 생활 > 직", "cong-viec", "Công việc, công sở"),
    ("사회 생활", "xa-hoi", "Hoạt động xã hội, quan hệ"),
    ("삶 > 병과 증상|삶 > 약품류|삶 > 치료", "suc-khoe", "Sức khỏe, y tế"),
    ("삶 > 가족 행사|삶 > 친족 관계", "gia-dinh", "Gia đình, họ hàng"),
    ("삶 > 여가", "giai-tri", "Giải trí, thời gian rảnh"),
    ("삶", "cuoc-song", "Cuộc sống hằng ngày"),
    ("식생활", "an-uong", "Ăn uống"),
    ("의생활", "trang-phuc", "Trang phục, làm đẹp"),
    ("주생활", "nha-o", "Nhà ở, đồ dùng"),
    ("인간 > 감정", "cam-xuc", "Cảm xúc"),
    ("인간 > 성격|인간 > 태도", "tinh-cach-thai-do", "Tính cách, thái độ"),
    ("인간 > 인지 행위|인간 > 능력", "nhan-thuc", "Suy nghĩ, nhận thức, năng lực"),
    ("인간 > 사람의 종류", "con-nguoi", "Con người, vai trò"),
    ("인간", "co-the", "Cơ thể, giác quan, hành động"),
    ("정치와 행정", "chinh-tri-phap-luat", "Chính trị, pháp luật, hành chính"),
]
NO_CATEGORY = {
    "N": ("danh-tu", "Danh từ (chủ yếu Hán Hàn) dùng nhiều trong đọc, viết"),
    "V": ("dong-tu", "Động từ"),
    "A": ("tinh-tu", "Tính từ"),
    "부사": ("pho-tu", "Phó từ"),
}
OTHER = ("tu-chuc-nang", "Định từ, thán từ, phụ tố")
GRADE_VI = {"mid": "Trung cấp", "adv": "Cao cấp"}


def topic_of(cat: str, pos: str) -> tuple[str, str]:
    for pattern, key, title in TOPICS:
        if any(cat.startswith(p) for p in pattern.split("|")):
            return key, title
    if not cat:
        if pos == "부사":
            return NO_CATEGORY["부사"]
        code = POS.get(pos)
        if code:
            return NO_CATEGORY[code]
    return OTHER


def clean(text: str | None) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip()


def pick_example(senses: list[dict]) -> str | None:
    """A whole sentence (not a phrase, not a dialogue), short enough for a card."""
    best = None
    for s in senses[:2]:
        for ex in s["ex"]:
            if ex["type"] != "문장" or not ex["text"]:
                continue
            t = clean(ex["text"][0])
            if 12 <= len(t) <= 70 and (best is None or len(t) < len(best)):
                best = t
        if best:
            return best
    return best


def syllables(text: str) -> list[str]:
    return re.findall(r"[가-힣]", text)


def align(word: str, origin: str) -> list[tuple[str, str]] | None:
    """(hanja, Korean syllable) pairs: the origin "決定하다" lines up with "결정하다" character by
    character (hangul in the origin stands for itself). None when they do not line up."""
    ko = syllables(word)
    pairs, i = [], 0
    for ch in origin:
        if HANJA.match(ch):
            if i >= len(ko):
                return None
            pairs.append((ch, ko[i]))
            i += 1
        elif re.match(r"[가-힣]", ch):
            if i >= len(ko) or ko[i] != ch:
                return None
            i += 1
    return pairs if pairs and i == len(ko) else None


def hv_tables() -> tuple[dict[tuple[str, str], set[str]], dict[str, set[str]], dict]:
    """(char, Korean syllable) -> readings and char -> readings seen on the course's own cards,
    and the Unihan table."""
    by_pair: dict[tuple[str, str], set[str]] = defaultdict(set)
    by_char: dict[str, set[str]] = defaultdict(set)
    for path in LESSONS.glob("*.json"):
        for v in json.loads(path.read_text(encoding="utf-8")).get("vocab", []):
            h, s = v.get("hanja"), v.get("sino_vietnamese")
            if not (h and s) or len(s.split()) != len(h):
                continue
            ko = syllables(v["hangul"])
            for k, (c, r) in enumerate(zip(h, s.split())):
                by_char[c].add(r.lower())
                if k < len(ko):
                    by_pair[(c, ko[k])].add(r.lower())
    unihan = json.loads((ROOT / "scripts" / "data" / "unihan_vi_ko.json").read_text(encoding="utf-8"))["chars"]
    return by_pair, by_char, unihan


def reading(pairs: list[tuple[str, str]], tables) -> str | None:
    by_pair, by_char, unihan = tables
    out = []
    for c, ko in pairs:
        seen = by_pair.get((c, ko)) or by_char.get(c)
        if seen:
            if len(seen) != 1:
                return None
            out.append(next(iter(seen)))
            continue
        u = unihan.get(c)
        if not u or len(u.get("vi", [])) != 1 or len(u.get("ko", [])) > 1:
            return None
        out.append(u["vi"][0].lower())
    return " ".join(out)


def parse(folder: str) -> list[dict]:
    out = []
    for f in sorted(glob.glob(os.path.join(folder, "*.xml"))):
        for _, el in etree.iterparse(f, recover=True, huge_tree=True):
            if el.tag != "LexicalEntry":
                continue
            g = {ft.get("att"): ft.get("val") for ft in el.findall("feat")}
            if g.get("vocabularyLevel") in GRADES and g.get("lexicalUnit") == "단어":
                lem = el.find('Lemma/feat[@att="writtenForm"]')
                senses = []
                for s in el.findall("Sense"):
                    sf = {ft.get("att"): ft.get("val") for ft in s.findall("feat")}
                    vi = {}
                    for eq in s.findall("Equivalent"):
                        e = {ft.get("att"): ft.get("val") for ft in eq.findall("feat")}
                        if e.get("language") == "베트남어":
                            vi = e
                    exs = []
                    for se in s.findall("SenseExample"):
                        t = [ft.get("val") for ft in se.findall("feat") if ft.get("att") == "type"]
                        x = [ft.get("val") for ft in se.findall("feat") if ft.get("att") == "example"]
                        exs.append({"type": t[0] if t else "", "text": x})
                    senses.append({"def": sf.get("definition"), "vi": vi.get("lemma"), "vi_def": vi.get("definition"), "ex": exs})
                prons = [p.get("val") for p in el.findall('WordForm/feat[@att="pronunciation"]')]
                out.append(
                    {
                        "id": el.get("val"),
                        "w": lem.get("val") if lem is not None else "",
                        "pos": g.get("partOfSpeech") or "",
                        "grade": GRADES[g["vocabularyLevel"]],
                        "origin": g.get("origin") or "",
                        "cat": clean(g.get("semanticCategory")),
                        "pron": prons,
                        "senses": senses,
                    }
                )
            el.clear()
    return out


def build(folder: str) -> dict:
    tables = hv_tables()
    words = []
    for e in parse(folder):
        w = e["w"].replace("^", " ").strip()
        if not w or not e["senses"] or not e["senses"][0].get("vi"):
            continue
        # the first two senses' Vietnamese words, each said once ("thông tin; thông tin, dữ liệu"
        # becomes "thông tin, dữ liệu"), senses kept apart by ";"
        seen_words: set[str] = set()
        meanings = []
        for s in e["senses"][:2]:
            parts = [p for p in (clean(x) for x in clean(s.get("vi")).split(",")) if p and p.lower() not in seen_words]
            seen_words |= {p.lower() for p in parts}
            if parts:
                meanings.append(", ".join(parts[:4]))
        meaning = "; ".join(meanings)[:250]
        origin = e["origin"].split("/")[0].strip() if e["origin"] and not re.search(r"[a-zA-Z]", e["origin"]) else ""
        pairs = align(w, origin) if HANJA.search(origin) else None
        hanja = "".join(c for c, _ in pairs) if pairs else ""
        sino = reading(pairs, tables) if pairs else None
        pron = clean(e["pron"][0]).replace("ː", "") if e["pron"] else ""
        bare = re.sub(r"[^가-힣]", "", w)
        key, title = topic_of(e["cat"], e["pos"])
        words.append(
            {
                "id": int(e["id"]),
                "w": w,
                "pos": POS.get(e["pos"], "X"),
                "pos_ko": e["pos"],
                "grade": e["grade"],
                "topic": key,
                "topic_vi": title,
                "meaning_vi": meaning,
                "note_vi": clean(e["senses"][0].get("vi_def"))[:400] or None,
                "definition_ko": clean(e["senses"][0].get("def"))[:400] or None,
                "example_ko": pick_example(e["senses"]),
                "hanja": hanja or None,
                "sino_vietnamese": sino,
                "pron": f"[{pron}]" if pron and pron.replace(" ", "") != bare else None,
            }
        )
    # decks: topic x grade, cut into chunks of CHUNK words (in Korean order)
    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for w in words:
        groups[(w["topic"], w["grade"])].append(w)
    decks = []
    for (topic, grade), ws in sorted(groups.items(), key=lambda kv: (kv[0][1], kv[0][0])):
        ws.sort(key=lambda w: (w["w"].startswith("-") or w["w"].endswith("-"), w["w"], w["id"]))  # affixes last
        n = (len(ws) + CHUNK - 1) // CHUNK
        for i in range(n):
            part = ws[i * CHUNK : (i + 1) * CHUNK]
            key = f"{grade}-{topic}" + (f"-{i + 1}" if n > 1 else "")
            title = f"{part[0]['topic_vi']}" + (f" ({i + 1}/{n})" if n > 1 else "")
            decks.append({"key": key, "title_vi": title, "grade": grade, "grade_vi": GRADE_VI[grade], "words": [w["id"] for w in part]})
            for w in part:
                w["deck"] = key
    for w in words:
        del w["topic_vi"]
    return {
        "about": "Kho từ TOPIK: từ trung cấp (중급) và cao cấp (고급) của 한국어기초사전 theo chủ đề. "
        "Làm bằng `python scripts/build_topik_bank.py <thư mục XML>`; đừng sửa tay.",
        "source": "https://krdict.korean.go.kr/ (bản tải về toàn bộ, qua https://github.com/spellcheck-ko/korean-dict-nikl)",
        "license": "CC BY-SA 2.0 KR (https://creativecommons.org/licenses/by-sa/2.0/kr/) — 국립국어원 한국어기초사전",
        "decks": decks,
        "words": sorted(words, key=lambda w: w["id"]),
    }


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2
    data = build(argv[1])
    OUT.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    grades = Counter(w["grade"] for w in data["words"])
    print(f"{OUT.relative_to(ROOT)}: {len(data['words'])} words ({dict(grades)}), {len(data['decks'])} decks")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

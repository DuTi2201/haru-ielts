"""Place each phrasal verb, prepositional phrase, word pattern and word-formation base in the
vocabulary unit that practises it.

The book lists these four kinds of item alphabetically for the whole book (pp. 202-216), not by
unit. This script reads an OCR of the book (one text file per page, p001.txt …; not kept in the
repository) and looks for each item in the matching section of each vocabulary unit. What it
finds is written to unit_assignment.json, which build.py reads; items it cannot find go to the
unit named in FALLBACK, and are listed under "unverified" so a person can check them against
the book.

    python3 scripts/b1/assign_units.py /path/to/ocr_pages
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
UNIT_START = {3: 12, 6: 24, 9: 36, 12: 48, 15: 60, 18: 72, 21: 84, 24: 100, 27: 112, 30: 124, 33: 136, 36: 148, 39: 160, 42: 172}
HEADS = {"PV": "phrasal verbs", "PP": "prepositional phrases", "WF": "word formation", "WP": "word patterns"}
IRREGULAR = {
    "blow": "blew blown", "break": "broke broken", "bring": "brought", "build": "built", "catch": "caught", "come": "came",
    "cut": "cut", "do": "did done", "eat": "ate eaten", "fall": "fell fallen", "find": "found", "get": "got", "give": "gave given",
    "go": "went gone", "grow": "grew grown", "hang": "hung", "have": "had has", "keep": "kept", "leave": "left", "let": "let",
    "lie": "lay lying", "make": "made", "pay": "paid", "put": "put", "read": "read", "rip": "ripped", "rub": "rubbed",
    "run": "ran", "send": "sent", "set": "set", "shut": "shut", "sit": "sat", "speak": "spoke", "split": "split",
    "stand": "stood", "take": "took taken", "throw": "threw thrown", "wake": "woke", "write": "wrote written",
}
# where an item goes when the OCR does not show it (a guess by topic; listed as unverified)
FALLBACK_ORDER = [3, 6, 9, 12, 15, 18, 21, 24, 27, 30, 33, 36, 39, 42]
# Items a person read in the unit's pages although the matcher missed them (broken OCR, lower case).
SEEN = {
    "WF": {"serve": 15, "decide": 15, "afford": 15, "true": 15, "compare": 15, "value": 15, "imagine": 33, "compose": 33, "art": 33},
    "PV": {"fill in": 21, "hang up": 21, "cross out": 6, "rub out": 6, "rip up": 6, "join in": 3, "sit down": 30},
    "PP": {"for fun": 3, "on CD/DVD/video": 3, "against the law": 24, "in public": 24, "at the age of": 24, "on your own": 12,
           "by yourself": 12, "in response to": 24, "in favour (of)": 6, "in the end": 18},
    "WP": {"apply for": 27, "result in": 18, "full of": 18, "confuse sth with": 6, "forget about": 24},
}
# Items placed by topic only: still to be checked against the book.
BY_TOPIC = {
    "WF": {"pollute": 36, "nature": 36, "danger": 36, "destroy": 36, "fog": 36, "garden": 36, "exhibit": 33, "perfect": 33,
           "circle": 33, "solve": 42, "suggest": 42, "refuse": 42, "recommend": 42, "prefer": 42, "fame": 27, "boss": 27,
           "succeed": 27, "occupy": 27, "admire": 12, "relate": 12, "introduce": 12, "belief": 12, "identify": 24, "judge": 24,
           "invade": 24, "life": 24, "intelligent": 6, "prepare": 6, "advice": 6, "luck": 3, "help": 39, "expense": 15,
           "add": 15, "break": 18, "centre": 9, "deep": 36, "free": 24, "hand": 33, "confuse": 39, "except": 6},
    "PV": {"pay back": 15, "save up (for)": 15, "give away": 15, "add up": 15, "give back": 15, "calm down": 39, "cheer up": 39,
           "shut up": 39, "hang on": 21, "speak up": 21, "sort out": 42, "watch out": 42, "point out": 42, "keep out": 36,
           "fill up": 9, "carry on": 6, "turn on": 18, "pick up": 36, "stay up": 30},
    "PP": {"on TV": 21, "by air/sea/bus/car": 9, "in fashion/style": 33, "out of fashion/style": 33, "in the corner (of)": 33,
           "on top (of)": 33, "at the top (of)": 33, "at the back (of)": 33, "in front (of)": 33, "at the end (of)": 18},
    "WP": {"borrow sth from": 15, "comment on": 21, "communicate with": 21, "information about": 21, "a letter (from sb) about": 21,
           "reply to": 21, "talk (to sb) about": 21, "translate (from sth) into": 21, "receive sth from": 21, "insist on": 42,
           "a reason for": 42, "congratulate sb on": 39, "glance at": 39, "smell of": 30, "a type of": 3},
}


def items(name: str) -> list[str]:
    out = []
    for line in (HERE / name).read_text(encoding="utf-8").splitlines():
        if line.strip() and not line.startswith("#"):
            out.append(line.split("|")[0].strip())
    return out


def sections(ocr: Path) -> dict[int, dict[str, str]]:
    out: dict[int, dict[str, str]] = {}
    for unit, start in UNIT_START.items():
        text = "\n".join((ocr / f"p{p:03d}.txt").read_text(errors="ignore") for p in range(start, start + 4) if (ocr / f"p{p:03d}.txt").exists())
        low = text.lower()
        marks = sorted((m.start(), k) for k, h in HEADS.items() for m in re.finditer(re.escape(h), low))
        secs = {k: "" for k in HEADS}
        for i, (pos, k) in enumerate(marks):
            end = marks[i + 1][0] if i + 1 < len(marks) else min(len(text), pos + 2600)
            secs[k] += text[pos:end] + "\n"
        out[unit] = secs
    return out


def has(text: str, word: str) -> bool:
    return re.search(rf"(?<![A-Za-z]){re.escape(word)}(?![A-Za-z])", text, re.I) is not None


def score(kind: str, item: str, sec: str) -> int:
    if not sec:
        return 0
    if kind == "WF":
        return 2 if re.search(rf"(?<![A-Za-z]){re.escape(item.upper())}(?![A-Za-z])", sec) else 0
    if kind == "PV":
        words = re.sub(r"\(.*?\)", "", item).split()
        verb, particle = words[0], words[1]
        forms = [verb, verb + "s", verb + "ed", verb + "d", verb + "ing", verb[:-1] + "ing", *IRREGULAR.get(verb, "").split()]
        v = any(has(sec, f) for f in forms)
        return (2 if v and has(sec, particle) else 0)
    if kind == "PP":
        nouns = [w for w in re.split(r"[ /()]", item) if len(w) > 3 and w not in ("your", "with", "good", "long")]
        return 2 if nouns and any(has(sec, n) for n in nouns[:2]) else 0
    head = [w for w in re.split(r"[ /()]", item) if len(w) > 2 and w not in ("sth", "the", "from", "with", "about", "for", "into")]
    return 2 if head and has(sec, head[0]) else 0


def main() -> None:
    ocr = Path(sys.argv[1])
    secs = sections(ocr)
    result: dict[str, dict[str, int]] = {}
    unverified: dict[str, list[str]] = {}
    for kind, name in (("PV", "phrasal_verbs.txt"), ("PP", "prep_phrases.txt"), ("WP", "word_patterns.txt"), ("WF", "word_formation.txt")):
        load = {u: 0 for u in UNIT_START}
        placed: dict[str, int] = {}
        pending = []
        for item in items(name):
            if item in SEEN.get(kind, {}) or item in BY_TOPIC.get(kind, {}):
                unit = SEEN.get(kind, {}).get(item) or BY_TOPIC[kind][item]
                placed[item] = unit
                load[unit] += 1
                if item not in SEEN.get(kind, {}):
                    unverified.setdefault(kind, []).append(item)
                continue
            hits = [u for u in UNIT_START if score(kind, item, secs[u][kind])]
            if len(hits) == 1:
                placed[item] = hits[0]
                load[hits[0]] += 1
            else:
                pending.append((item, hits))
        for item, hits in pending:  # several units show it: the least loaded of them; none: the least loaded of all
            pool = hits or FALLBACK_ORDER
            unit = min(pool, key=lambda u: (load[u], u))
            placed[item] = unit
            load[unit] += 1
            if not hits:
                unverified.setdefault(kind, []).append(item)
        result[kind] = placed
        print(kind, {u: n for u, n in load.items()}, "unverified:", len(unverified.get(kind, [])))
    (HERE / "unit_assignment.json").write_text(
        json.dumps({"by_kind": result, "unverified": unverified}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()

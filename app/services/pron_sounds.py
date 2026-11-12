"""The sound-by-sound pronunciation course: BBC Learning English videos (embedded on the client) plus
our own words, minimal pairs and sentences per sound. The seed is app/seed/pronunciation/sounds.json
(built by scripts/pron/build_sounds.py). Also the allow-list for scoring: only text the course itself
offers for a sound can be assessed, so the endpoint is not a general speech service."""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

SEED = Path(__file__).resolve().parents[1] / "seed" / "pronunciation" / "sounds.json"
_VID = re.compile(r"^[A-Za-z0-9_-]{11}$")


def norm(s: str) -> str:
    return re.sub(r"[^a-z']+", " ", s.lower().replace("’", "'")).strip()


def validate(data: dict) -> None:
    sounds = data["sounds"]
    slugs = [s["slug"] for s in sounds]
    vids = [s["video_id"] for s in sounds] + [data["intro"]["id"]] + [x["video_id"] for x in data["shadowing"]]
    if len(set(slugs)) != len(slugs) or len(set(vids)) != len(vids):
        raise ValueError("pronunciation seed: duplicate slug or video id")
    if not all(_VID.match(v) for v in vids):
        raise ValueError("pronunciation seed: bad video id")
    for s in sounds:
        if not s["words"] or not s["sentence"].strip() or not s["tip_vi"].strip():
            raise ValueError(f"pronunciation seed: incomplete sound {s['slug']}")


@lru_cache(maxsize=1)
def load() -> dict:
    data = json.loads(SEED.read_text(encoding="utf-8"))
    validate(data)
    return data


def get_sound(slug: str) -> dict | None:
    return next((s for s in load()["sounds"] if s["slug"] == slug), None)


def practice_texts(sound: dict) -> list[str]:
    """Everything the learner may be scored on for this sound: single words, the minimal pair's two
    words, all words in one go, and the sentence."""
    texts = list(sound["words"])
    if sound.get("pair"):
        texts += sound["pair"]
    texts.append(" ".join(sound["words"]))
    texts.append(sound["sentence"])
    return texts


def allowed(sound: dict, text: str) -> bool:
    n = norm(text)
    return bool(n) and n in {norm(t) for t in practice_texts(sound)}

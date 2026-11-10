"""Pictures for the lessons: what is drawn, where it goes, and how one is made.

A lesson shows pictures in four places — its banner (`lesson`), a word card (`vocab`),
the illustration of a grammar point (`grammar`) and the scenes of the practice set
(`scene`: the pictures of a listening question, the frames of a speaking task). What each
one is drawn as is written down once, in plain words, in `app/seed/images.json` (lesson,
word and grammar point) and in the exercises' `Scene.image_prompt`. Every slot that has
no picture yet is still drawn from icons (scenes) or simply left out (the rest), so a
lesson never waits for a picture.

A picture is made once (an editor presses the button in Studio), squeezed to a small WebP
and kept in the database under a key made of its prompt, so it is reused for ever by every
learner and by every lesson that uses the same words. Charts are never drawn by a model:
their numbers come from the data and are drawn by code.

Pure helpers (plan, slots, key, response parsing, WebP squeeze) are unit-tested; the HTTP
call to Gemini has not been run against the real service from the development sandbox.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import io
import json
import time
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterator

import httpx

from app.core.config import settings

PLAN_PATH = Path(__file__).resolve().parent.parent / "seed" / "images.json"

# Where a picture goes, and so how wide it is drawn and how big it is kept (long side, px).
KINDS: dict[str, tuple[str, int]] = {
    "lesson": ("16:9", 960),
    "vocab": ("1:1", 512),
    "grammar": ("4:3", 640),
    "scene": ("4:3", 720),
}
_COMPOSITION = {
    "16:9": "Wide banner composition (16:9), subject centred with some empty space around.",
    "1:1": "Square composition (1:1), one clear subject centred on a plain background.",
    "4:3": "Landscape composition (4:3), the whole scene visible.",
}
_API = "https://generativelanguage.googleapis.com/v1beta"


class ImageGenDisabled(RuntimeError):
    """The feature is off or not configured."""


class ImageGenError(RuntimeError):
    """A picture could not be made. `fatal` — every further call would fail the same way
    (bad key, unknown model, no quota): stop the run. `blocked` — the model refused this
    scene; the next one may well be fine."""

    def __init__(self, message: str, *, fatal: bool = False, blocked: bool = False):
        super().__init__(message)
        self.fatal = fatal
        self.blocked = blocked


class _Unsupported(Exception):
    """This endpoint does not take that kind of request (try the other one)."""


def enabled() -> bool:
    return bool(settings.LESSON_IMAGE_GEN_ENABLED and (settings.GEMINI_MODEL_IMAGE or "").strip())


# ----------------------------------------------------------------------- plan --
@dataclass(frozen=True)
class Plan:
    style_version: str
    lessons: dict[str, str]
    vocab: dict[str, str]
    grammar: dict[str, str]
    # one cover per topic (the topic's name as seeded), shown on the topic card
    topics: dict[str, str] = field(default_factory=dict)


@lru_cache(maxsize=1)
def load_plan() -> Plan:
    if not PLAN_PATH.is_file():
        return Plan(style_version="v1", lessons={}, vocab={}, grammar={}, topics={})
    raw = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
    return Plan(
        style_version=str(raw.get("style_version") or "v1"),
        lessons={str(k): str(v).strip() for k, v in (raw.get("lessons") or {}).items()},
        vocab={str(k): str(v).strip() for k, v in (raw.get("vocab") or {}).items()},
        grammar={str(k): str(v).strip() for k, v in (raw.get("grammar") or {}).items()},
        topics={str(k): str(v).strip() for k, v in (raw.get("topics") or {}).items()},
    )


def scene_key(prompt: str) -> str:
    """Stable id of a picture: the same words (in the same house style) are the same
    picture. The model is NOT part of it — switching to a better model must not make
    every picture already made disappear."""
    blob = f"{load_plan().style_version}|{prompt.strip()}"
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:24]


@dataclass(frozen=True)
class Slot:
    kind: str  # lesson | vocab | grammar | scene
    label: str  # what the editor sees: the word, the pattern, the scene's caption
    prompt: str
    # a word's meaning (Vietnamese), so a missing picture can be matched with an existing one
    # of the same meaning (see image_reuse); it plays no part in which picture this is
    meaning: str | None = field(default=None, compare=False)

    @property
    def key(self) -> str:
        return scene_key(self.prompt)

    @property
    def aspect(self) -> str:
        return KINDS[self.kind][0]


def iter_scenes(node: Any) -> Iterator[dict[str, Any]]:
    """Every scene (a dict with `caption_vi` and `icons`) anywhere in a practice set."""
    if isinstance(node, dict):
        if "caption_vi" in node and "icons" in node:
            yield node
        for value in node.values():
            yield from iter_scenes(value)
    elif isinstance(node, list):
        for value in node:
            yield from iter_scenes(value)


def scene_prompts(practice: dict[str, Any] | None) -> list[str]:
    """The distinct image prompts of a lesson's scenes, in order."""
    seen: list[str] = []
    for scene in iter_scenes(practice or {}):
        prompt = (scene.get("image_prompt") or "").strip()
        if prompt and prompt not in seen:
            seen.append(prompt)
    return seen


def lesson_slots(
    slug: str | None,
    vocab: list[str],
    grammar: list[str],
    practice: dict[str, Any] | None,
    meanings: dict[str, str] | None = None,
) -> list[Slot]:
    """Every picture of one lesson, in the order a learner meets them: banner, words,
    grammar, practice scenes. The same prompt twice (a noun and its verb share one
    picture) is one slot, listed under the first label."""
    plan = load_plan()
    slots: list[Slot] = []
    seen: set[str] = set()

    def add(kind: str, label: str, prompt: str | None, meaning: str | None = None) -> None:
        prompt = (prompt or "").strip()
        if prompt and prompt not in seen:
            seen.add(prompt)
            slots.append(Slot(kind=kind, label=label, prompt=prompt, meaning=meaning))

    if slug:
        add("lesson", "Ảnh đầu bài", plan.lessons.get(slug))
    for headword in vocab:
        add("vocab", headword, plan.vocab.get(headword), (meanings or {}).get(headword))
    for pattern in grammar:
        add("grammar", pattern, plan.grammar.get(pattern))
    for scene in iter_scenes(practice or {}):
        add("scene", str(scene.get("caption_vi") or "Cảnh bài tập")[:120], scene.get("image_prompt"))
    return slots


def check_plan(
    lessons: list[tuple[str, list[str], list[str]]], topics: set[str] | None = None
) -> list[str]:
    """Problems in images.json against the real lessons ((slug, vocab headword, grammar
    patterns) each): a picture that points at nothing, or an empty prompt."""
    plan = load_plan()
    problems: list[str] = []
    slugs = {s for s, _, _ in lessons}
    words = {w for _, v, _ in lessons for w in v}
    patterns = {p for _, _, g in lessons for p in g}
    tables = [("lessons", plan.lessons, slugs), ("vocab", plan.vocab, words), ("grammar", plan.grammar, patterns)]
    if topics is not None:
        tables.append(("topics", plan.topics, topics))
    for name, table, known in tables:
        for key, prompt in table.items():
            if key not in known:
                problems.append(f"images.json {name}: {key!r} is not in any lesson")
            if len(prompt) < 20:
                problems.append(f"images.json {name}: {key!r} has too short a prompt")
    return problems


# ----------------------------------------------------------------- generating --
_STYLE = (
    "Flat vector sticker-style illustration for a Korean language learning app. Warm cream paper "
    "background, medium-thick dark navy outlines, soft pastel blue, yellow, green and purple fills "
    "with a little coral accent, simple friendly rounded shapes, cute but not childish, clean "
    "uncluttered composition. No text, no letters, no numbers, no logos, no speech bubbles, no "
    "watermark. Subject: "
)


def build_prompt(prompt: str, aspect: str) -> str:
    return _STYLE + prompt.strip() + " " + _COMPOSITION.get(aspect, _COMPOSITION["4:3"])


def find_image(node: Any) -> tuple[bytes, str] | None:
    """The first picture anywhere in a Gemini JSON reply — a dict that holds base64 `data`
    and an `image/*` mime type under either spelling (`mime_type` / `mimeType`). Written to
    take both the Interactions reply (`output_image`) and the classic `inlineData`."""
    if isinstance(node, dict):
        data = node.get("data")
        mime = node.get("mime_type") or node.get("mimeType")
        if isinstance(data, str) and len(data) > 100 and isinstance(mime, str) and mime.startswith("image/"):
            try:
                return base64.b64decode(data, validate=False), mime
            except (binascii.Error, ValueError):
                return None
        for value in node.values():
            found = find_image(value)
            if found:
                return found
    elif isinstance(node, list):
        for value in node:
            found = find_image(value)
            if found:
                return found
    return None


def _refusal(body: Any) -> str | None:
    """Why the model drew nothing, when it says so (safety filter, blocked prompt)."""
    text = json.dumps(body, ensure_ascii=False) if not isinstance(body, str) else body
    for marker in ("IMAGE_SAFETY", "SAFETY", "PROHIBITED", "BLOCKED", "blockReason", "RECITATION"):
        if marker in text:
            return marker
    return None


def to_webp(data: bytes, max_side: int) -> bytes:
    """Squeeze whatever the model returned (often a 1–2 MB PNG) into a small WebP."""
    from PIL import Image, UnidentifiedImageError

    try:
        image = Image.open(io.BytesIO(data))
        image.load()
    except (UnidentifiedImageError, OSError) as exc:
        raise ImageGenError("The image model returned something that is not a picture") from exc
    if image.mode not in ("RGB", "RGBA"):
        image = image.convert("RGBA" if "transparency" in image.info else "RGB")
    if image.mode == "RGBA":  # keep it flat on the paper colour rather than on black
        base = Image.new("RGB", image.size, (255, 249, 230))
        base.paste(image, mask=image.getchannel("A"))
        image = base
    image.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
    out = io.BytesIO()
    image.save(out, format="WEBP", quality=82, method=4)
    return out.getvalue()


def _sleep(seconds: float) -> None:  # a seam for the tests
    time.sleep(seconds)


def _post(client: httpx.Client, url: str, body: dict[str, Any]) -> Any:
    """POST with the key in a header (never in the URL, so it cannot leak into a log or an
    error message). Retries busy/quota replies a few times; raises _Unsupported when the
    endpoint does not know this request, ImageGenError otherwise."""
    headers = {"x-goog-api-key": settings.GEMINI_API_KEY, "Content-Type": "application/json"}
    last = "no reply"
    for attempt in range(3):
        try:
            response = client.post(url, headers=headers, json=body)
        except httpx.HTTPError as exc:
            last = f"network error ({type(exc).__name__})"
            _sleep(2 * (attempt + 1))
            continue
        code = response.status_code
        if code == 200:
            try:
                return response.json()
            except ValueError as exc:
                raise ImageGenError("The image service sent a reply that is not JSON") from exc
        try:
            detail = str((response.json().get("error") or {}).get("message") or "")[:200]
        except (ValueError, AttributeError):
            detail = response.text[:200]
        if code in (404, 405, 501):
            raise _Unsupported(f"HTTP {code}: {detail}")
        if code == 400 and ("Unknown name" in detail or "Invalid JSON payload" in detail):
            raise _Unsupported(f"HTTP 400: {detail}")
        if code in (401, 403):
            raise ImageGenError(f"Gemini refused the key or the model ({code}): {detail}", fatal=True)
        if code == 400 and _refusal(detail):
            raise ImageGenError(f"The model refused this scene: {detail}", blocked=True)
        if code in (429, 500, 502, 503, 504):
            last = f"HTTP {code}: {detail}"
            _sleep(3 * (attempt + 1) ** 2)
            continue
        raise ImageGenError(f"HTTP {code}: {detail}")
    raise ImageGenError(f"The image service stayed busy ({last})")


def _via_interactions(client: httpx.Client, model: str, text: str) -> Any:
    return _post(client, f"{_API}/interactions", {"model": model, "input": [{"type": "text", "text": text}]})


def _via_generate_content(client: httpx.Client, model: str, text: str, aspect: str) -> Any:
    body = {
        "contents": [{"parts": [{"text": text}]}],
        "generationConfig": {"responseModalities": ["IMAGE"], "imageConfig": {"aspectRatio": aspect}},
    }
    return _post(client, f"{_API}/models/{model}:generateContent", body)


def generate_image(prompt: str, kind: str = "scene") -> tuple[bytes, str]:
    """One picture for `prompt` -> (WebP bytes, "image/webp"). Raises ImageGenDisabled
    when off, ImageGenError when Gemini returns no usable picture."""
    if not enabled():
        raise ImageGenDisabled("LESSON_IMAGE_GEN_ENABLED / GEMINI_MODEL_IMAGE are not set")
    if not settings.GEMINI_API_KEY:
        raise ImageGenError("GEMINI_API_KEY is not set", fatal=True)
    aspect, max_side = KINDS.get(kind, KINDS["scene"])
    text = build_prompt(prompt, aspect)
    model = settings.GEMINI_MODEL_IMAGE.strip()
    mode = (settings.GEMINI_IMAGE_API or "auto").strip().lower()
    with httpx.Client(timeout=httpx.Timeout(120.0, connect=15.0)) as client:
        body: Any = None
        if mode in ("auto", "interactions"):
            try:
                body = _via_interactions(client, model, text)
            except _Unsupported as exc:
                if mode == "interactions":
                    raise ImageGenError(f"The Interactions endpoint refused the request: {exc}", fatal=True) from exc
        if body is None and mode in ("auto", "generate_content"):
            try:
                body = _via_generate_content(client, model, text, aspect)
            except _Unsupported as exc:
                raise ImageGenError(f"The image endpoint refused the request: {exc}", fatal=True) from exc
    found = find_image(body)
    if found is None:
        why = _refusal(body)
        if why:
            raise ImageGenError(f"The model drew nothing for this scene ({why})", blocked=True)
        raise ImageGenError("Gemini returned no image")
    return to_webp(found[0], max_side), "image/webp"

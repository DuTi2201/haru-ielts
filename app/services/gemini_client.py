"""Thin wrapper around the Gemini API — the SDD's "AI Gateway": every
call goes through here so prompt version, structured-output schema and
cost logging are consistent regardless of which module calls it.

`generate_structured` now accepts either a plain text prompt or a list of
multimodal parts (text + an image/PDF `Part.from_bytes(...)`), which the
content-ingestion pipeline (app/services/ingestion.py) needs for lesson
image/PDF extraction; `embed_text` backs the corpus/exam embedding columns.
Fill in real per-module cost logging once app_config/analytics wiring
lands — omitted in this stub, as before.
"""
from __future__ import annotations

from typing import Any

from google import genai
from google.genai import types
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings

_client: genai.Client | None = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=settings.GEMINI_API_KEY)
    return _client


def part_from_bytes(data: bytes, mime_type: str) -> types.Part:
    """Build an inline image/PDF part for a multimodal `contents` list."""
    return types.Part.from_bytes(data=data, mime_type=mime_type)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
def generate_structured(
    *,
    model: str,
    prompt: str | list[Any],
    response_schema: dict[str, Any] | None = None,
    prompt_version: str = "v1",
) -> dict[str, Any]:
    """Call Gemini with a JSON response schema. `prompt` is either plain
    text or a list of parts (e.g. `[part_from_bytes(...), "instructions"]`)
    for multimodal (image/PDF) input. Every caller MUST log (model,
    prompt_version, token counts) to `app_config`/analytics — wire that up
    once a real prompt lands here; omitted in this stub.
    """
    if not settings.GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is not set")

    client = _get_client()
    config: dict[str, Any] = {"response_mime_type": "application/json"}
    if response_schema:
        config["response_schema"] = response_schema

    response = client.models.generate_content(model=model, contents=prompt, config=config)
    return {"text": response.text, "prompt_version": prompt_version}


@retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=1, max=4))
def generate_chat(*, model: str, system: str, turns: list[dict[str, str]]) -> str:
    """One plain-text reply in a chat: `turns` are {"role": "learner" | "haru", "text"}; an empty
    list makes the model open the conversation."""
    if not settings.GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is not set")
    contents = [
        types.Content(role="user" if t["role"] == "learner" else "model", parts=[types.Part(text=t["text"])])
        for t in turns
    ] or [types.Content(role="user", parts=[types.Part(text="(Buổi trò chuyện bắt đầu. Haru chào và hỏi câu đầu tiên.)")])]
    response = _get_client().models.generate_content(
        model=model,
        contents=contents,
        config=types.GenerateContentConfig(system_instruction=system, temperature=0.8, max_output_tokens=300),
    )
    return (response.text or "").strip()


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
def embed_text(*, text: str, model: str | None = None, output_dim: int = 768) -> list[float]:
    """Embed one piece of Korean text into the `vector(768)` space shared
    by corpus_item/exam_passage/exam_item. `output_dim` must stay 768 to
    match the schema unless a migration also changes the column.
    """
    if not settings.GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is not set")

    client = _get_client()
    response = client.models.embed_content(
        model=model or settings.GEMINI_EMBEDDING_MODEL,
        contents=text,
        config={"output_dimensionality": output_dim, "task_type": "RETRIEVAL_DOCUMENT"},
    )
    return list(response.embeddings[0].values)


# --------------------------------------------------------------- Live API tokens --
AUTH_TOKENS_URL = "https://generativelanguage.googleapis.com/v1beta/auth_tokens"
LIVE_WS_URL = (
    "wss://generativelanguage.googleapis.com/ws/"
    "google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContentConstrained"
)


class LiveTokenError(RuntimeError):
    """Gemini refused to mint a Live token (bad key, bad setup, quota): `status` is its HTTP code."""

    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status


def mint_live_token(body: dict[str, Any], *, timeout: float = 10.0) -> str:
    """POST v1beta/auth_tokens with the server key and return the token's `name`, which the
    browser passes as `access_token` when it opens the Live WebSocket. `body` carries `uses`,
    the expiry times and the `bidiGenerateContentSetup` the token is locked to
    (app.services.conversation.token_request). The key itself never leaves this server."""
    import httpx

    if not settings.GEMINI_API_KEY:
        raise LiveTokenError(503, "GEMINI_API_KEY is not set")
    try:
        r = httpx.post(
            AUTH_TOKENS_URL,
            json=body,
            headers={"x-goog-api-key": settings.GEMINI_API_KEY},
            timeout=timeout,
        )
    except httpx.HTTPError as exc:
        raise LiveTokenError(502, f"auth_tokens unreachable: {exc.__class__.__name__}") from exc
    if r.status_code != 200:
        # Google's error message, never the request (it holds nothing secret, but stay terse)
        try:
            msg = r.json().get("error", {}).get("message", "")
        except ValueError:
            msg = r.text[:300]
        raise LiveTokenError(r.status_code, msg[:300] or f"HTTP {r.status_code}")
    name = r.json().get("name")
    if not name:
        raise LiveTokenError(502, "auth_tokens answered without a token name")
    return str(name)

"""
Thin wrapper around the Google Gemini API. Every agent calls `generate()`
with a system instruction + user content and gets back text (optionally
parsed as JSON when `as_json=True`).

Centralizing this here means swapping models/providers later only touches
one file.

OFFLINE FALLBACK: when GEMINI_API_KEY is unset (or google-genai is not
installed), `generate()` routes to `app.services.fallback_engine`, a small
deterministic module that produces the same JSON *shapes* each agent
expects, based on which agent's system prompt is calling. This exists so
the full planner -> specialist -> target -> sentinel -> mutation loop is
genuinely executable and testable without a live API key/network path
(e.g. this sandbox has no route to the Gemini API). It is not a scripted
"always succeeds" stub -- it actually inspects the target's declared
tools and each attempt's real target_response text and returns different
verdicts for benign vs. vulnerable responses (see fallback_engine.py).
Nothing about this file changes for a real deployment with a real key.
"""
import json
from typing import Any, Optional

from app.core.config import settings

_client: Optional[Any] = None


def _gemini_configured() -> bool:
    return bool(settings.GEMINI_API_KEY)


def _get_client():
    global _client
    if _client is None:
        from google import genai  # local import: optional dependency, only needed with a real key

        _client = genai.Client(api_key=settings.GEMINI_API_KEY)
    return _client


def generate(
    system_instruction: str,
    user_content: str,
    as_json: bool = False,
    temperature: float = 0.7,
) -> Any:
    """
    Call Gemini with a system instruction + user turn.

    Returns raw string, or a parsed dict/list if `as_json=True` (the caller
    is responsible for prompting the model to actually return JSON).
    Falls back to a local deterministic engine when no GEMINI_API_KEY is
    configured -- see module docstring.
    """
    if not _gemini_configured():
        from app.services import fallback_engine

        return fallback_engine.generate(system_instruction, user_content, as_json=as_json)

    from google.genai import types

    client = _get_client()

    config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        temperature=temperature,
        response_mime_type="application/json" if as_json else "text/plain",
    )

    response = client.models.generate_content(
        model=settings.GEMINI_MODEL,
        contents=user_content,
        config=config,
    )

    text = response.text or ""

    if as_json:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Model occasionally wraps JSON in markdown fences despite instructions
            cleaned = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            return json.loads(cleaned)

    return text

"""Provider-neutral local LLM boundary; Ollama is the zero-infrastructure default."""
from __future__ import annotations
import json
import threading
from typing import Any
import httpx
from app.core.config import settings
from app.services.context_manager import get_context

_client: httpx.Client | None = None
_lock = threading.Lock()


def _http() -> httpx.Client:
    global _client
    if _client is None:
        with _lock:
            if _client is None:
                _client = httpx.Client(timeout=45.0)
    return _client


class LocalLLMProvider:
    def available(self) -> bool:
        if not settings.LOCAL_LLM_ENABLED or not settings.LOCAL_LLM_MODEL:
            return False
        try:
            if settings.LOCAL_LLM_PROVIDER == "ollama":
                return _http().get(f"{settings.LOCAL_LLM_BASE_URL.rstrip('/')}/api/tags").is_success
        except httpx.HTTPError:
            return False
        return False  # vLLM can be added without affecting callers

    def generate(self, system_instruction: str, user_content: str, *, temperature: float, json_mode: bool) -> Any:
        if settings.LOCAL_LLM_PROVIDER != "ollama":
            raise RuntimeError(f"Unsupported local LLM provider: {settings.LOCAL_LLM_PROVIDER}")
        response = _http().post(f"{settings.LOCAL_LLM_BASE_URL.rstrip('/')}/api/chat", json={
            "model": settings.LOCAL_LLM_MODEL,
            "stream": False,
            "format": "json" if json_mode else None,
            "options": {"temperature": temperature, "num_predict": settings.LOCAL_LLM_MAX_OUTPUT_TOKENS},
            "messages": [{"role": "system", "content": system_instruction}, {"role": "user", "content": user_content}],
        })
        response.raise_for_status()
        body = response.json()
        # Record real usage BEFORE parsing the content: if json_mode parsing
        # fails below, the tokens were still genuinely spent. Recording is a
        # side effect only -- the return contract (str, or parsed JSON when
        # json_mode) is unchanged.
        _record_ollama_usage(body)
        result = body.get("message", {}).get("content", "")
        return json.loads(result) if json_mode else result


def _record_ollama_usage(body: Any) -> None:
    """Attach the real Ollama counters of this call to the active scan.

    /api/chat reports ``prompt_eval_count`` (input) and ``eval_count``
    (output). Nothing is recorded outside an active scan context, and
    nothing is invented when the counters are absent.
    """
    if not isinstance(body, dict):
        return
    ctx = get_context()
    if not ctx or ctx.get("db") is None or ctx.get("scan_id") is None:
        return
    from app.services import usage_service  # local import: keeps this module import-light

    usage_service.record_llm_call(
        ctx["db"],
        ctx["scan_id"],
        provider="ollama",
        model=settings.LOCAL_LLM_MODEL,
        input_tokens=body.get("prompt_eval_count"),
        output_tokens=body.get("eval_count"),
        agent_type=ctx.get("agent_type"),
    )


local_llm = LocalLLMProvider()

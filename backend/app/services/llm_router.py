"""Local-first router preserving the historic gemini_client.generate contract."""
from __future__ import annotations
import hashlib
import json
import re
import threading
import time
from collections import deque
from typing import Any
import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.llm_cache import LLMCacheEntry
from app.services.confidence_router import decision, score
from app.services.context_manager import enrich, get_context
from app.services.local_llm import local_llm

_cloud_timestamps: deque[float] = deque()
_cloud_lock = threading.Lock()
_local_semaphore = threading.BoundedSemaphore(max(1, settings.MAX_LOCAL_LLM_CONCURRENCY))
_cloud_semaphore = threading.BoundedSemaphore(max(1, settings.MAX_CLOUD_LLM_CONCURRENCY))
_metrics = {key: 0 for key in ("local_llm_calls", "cloud_llm_calls", "rag_queries", "llm_cache_hits", "memory_hits", "memory_writes", "cloud_fallback_count")}


def metrics() -> dict[str, int]: return dict(_metrics)

def _sensitive(value: str) -> bool:
    return bool(re.search(r"(?i)(api[_ -]?key|password|authorization|session[_ -]?cookie)\s*[:=]", value))

def _key(system: str, user: str, temperature: float, as_json: bool) -> str:
    return hashlib.sha256(json.dumps([system, user, temperature, as_json], sort_keys=True).encode()).hexdigest()

def _read_cache(db: Session | None, cache_key: str, as_json: bool) -> Any | None:
    if not db or not settings.LLM_CACHE_ENABLED: return None
    row = db.query(LLMCacheEntry).filter(LLMCacheEntry.cache_key == cache_key).first()
    if not row: return None
    _metrics["llm_cache_hits"] += 1
    return row.json_response if as_json else row.response

def _write_cache(db: Session | None, cache_key: str, value: Any, as_json: bool) -> None:
    if not db or not settings.LLM_CACHE_ENABLED: return
    serialized = json.dumps(value) if as_json else str(value)
    if _sensitive(serialized): return
    db.add(LLMCacheEntry(cache_key=cache_key, response=serialized, json_response=value if as_json else None))
    try: db.commit()
    except Exception: db.rollback()

def _cloud_allowed(ctx: dict | None) -> bool:
    if not settings.LLM_CLOUD_FALLBACK: return False
    now = time.monotonic()
    with _cloud_lock:
        while _cloud_timestamps and now - _cloud_timestamps[0] > 60: _cloud_timestamps.popleft()
        if len(_cloud_timestamps) >= settings.MAX_CLOUD_LLM_CALLS_PER_MINUTE: return False
        if ctx and ctx.setdefault("cloud_calls", 0) >= settings.MAX_CLOUD_LLM_CALLS_PER_SCAN: return False
        _cloud_timestamps.append(now)
        if ctx: ctx["cloud_calls"] += 1
    return True

def _grok(system: str, user: str, as_json: bool, temperature: float) -> Any:
    response = httpx.post(f"{settings.GROK_BASE_URL.rstrip('/')}/chat/completions", timeout=45, headers={"Authorization": f"Bearer {settings.GROK_API_KEY}"}, json={
        "model": settings.GROK_MODEL, "temperature": temperature,
        "response_format": {"type": "json_object"} if as_json else None,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
    })
    response.raise_for_status(); content = response.json()["choices"][0]["message"]["content"]
    return json.loads(content) if as_json else content

def _cloud(system: str, user: str, as_json: bool, temperature: float) -> Any:
    if settings.LLM_PROVIDER == "grok" or (settings.GROK_ENABLED and settings.GROK_API_KEY and not settings.GEMINI_API_KEY):
        return _grok(system, user, as_json, temperature)
    from app.services.gemini_client import generate_cloud
    return generate_cloud(system, user, as_json=as_json, temperature=temperature)

def generate(system_instruction: str, user_content: str, *, as_json: bool = False, temperature: float = .7) -> Any:
    """cache -> local (+ RAG retry) -> cloud -> deterministic fallback."""
    ctx = get_context(); db = ctx.get("db") if ctx else None
    cache_key = _key(system_instruction, user_content, temperature, as_json)
    cached = _read_cache(db, cache_key, as_json)
    if cached is not None: return cached
    if ctx and ctx.setdefault("rag_calls", 0) >= settings.MAX_RAG_QUERIES_PER_SCAN:
        enriched, similarity = user_content, 0.0
    else:
        enriched, similarity = enrich(user_content)
        if ctx and enriched != user_content: ctx["rag_calls"] += 1
    if enriched != user_content: _metrics["rag_queries"] += 1
    local_result = None
    prefer_local = settings.LLM_PROVIDER in ("auto", "local")
    if prefer_local and local_llm.available() and (not ctx or ctx.setdefault("local_calls", 0) < settings.MAX_LOCAL_LLM_CALLS_PER_SCAN):
        try:
            with _local_semaphore:
                _metrics["local_llm_calls"] += 1
                if ctx: ctx["local_calls"] += 1
                local_result = local_llm.generate(system_instruction, enriched, temperature=temperature, json_mode=as_json)
            route = decision(score(local_result, retrieval_similarity=similarity))
            if route == "accept":
                _write_cache(db, cache_key, local_result, as_json); return local_result
            if route == "retry_local":
                expanded, _ = enrich(user_content, expanded=True)
                with _local_semaphore:
                    _metrics["local_llm_calls"] += 1
                    if ctx: ctx["local_calls"] += 1
                    local_result = local_llm.generate(system_instruction, expanded + "\nUse concise, evidence-grounded output.", temperature=temperature, json_mode=as_json)
                if decision(score(local_result, retrieval_similarity=similarity)) != "cloud":
                    _write_cache(db, cache_key, local_result, as_json); return local_result
        except (httpx.HTTPError, ValueError, RuntimeError):
            pass
    cloud_enabled = bool(settings.GEMINI_API_KEY or (settings.GROK_ENABLED and settings.GROK_API_KEY))
    if cloud_enabled and _cloud_allowed(ctx):
        try:
            with _cloud_semaphore:
                _metrics["cloud_llm_calls"] += 1; _metrics["cloud_fallback_count"] += 1
                result = _cloud(system_instruction, enriched, as_json, temperature)
            _write_cache(db, cache_key, result, as_json); return result
        except Exception:  # provider failure must never crash a scan
            pass
    from app.services import fallback_engine
    return fallback_engine.generate(system_instruction, user_content, as_json=as_json)

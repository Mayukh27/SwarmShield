"""
Phase 1 -- real LLM token-usage monitoring.

Ollama is mocked at the HTTP transport level (httpx.MockTransport), so the
REAL code path runs: local_llm.generate -> /api/chat JSON -> usage_service ->
Postgres -> GET /api/scans/{id}/usage. No Ollama server is required.

Uses the real Postgres configured via DATABASE_URL, like test_services.py;
each test creates and cleans up its own scan/target rows.
"""
import json
import uuid

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.agents.orchestrator import SPECIALIST_REGISTRY
from app.agents.planner import PlannerAgent
from app.agents.remediation import RemediationAgent
from app.agents.sentinel import SentinelAgent
from app.api.routes import scans as scans_routes
from app.core.config import settings
from app.db.base import SessionLocal
from app.models.llm_cache import LLMCacheEntry
from app.models.llm_usage import LLMUsageRecord
from app.models.scan import ScanRun
from app.models.target import TargetProfile
from app.services import context_manager, llm_router, local_llm as local_llm_module, usage_service
from app.services.local_llm import local_llm

MODEL = "qwen2.5:3b"


# --- fixtures -----------------------------------------------------------------

@pytest.fixture
def db():
    session: Session = SessionLocal()
    yield session
    session.rollback()
    session.close()


def _make_scan(db: Session) -> tuple[ScanRun, TargetProfile]:
    target = TargetProfile(id=uuid.uuid4(), name="usage-test-target", endpoint_url="http://x", declared_tools={}, permission_map={})
    db.add(target)
    db.commit()
    scan = ScanRun(id=uuid.uuid4(), target_id=target.id)
    db.add(scan)
    db.commit()
    db.refresh(scan)
    return scan, target


def _cleanup(db: Session, scan: ScanRun, target: TargetProfile) -> None:
    db.rollback()
    obj = db.get(ScanRun, scan.id)
    if obj:
        db.delete(obj)  # ORM delete so cascades fire
        db.commit()
    tgt = db.get(TargetProfile, target.id)
    if tgt:
        db.delete(tgt)
        db.commit()


@pytest.fixture
def scan(db):
    s, t = _make_scan(db)
    yield s
    _cleanup(db, s, t)


@pytest.fixture
def second_scan(db):
    s, t = _make_scan(db)
    yield s
    _cleanup(db, s, t)


class FakeOllama:
    """Scripted Ollama /api/chat + /api/tags served through httpx.MockTransport."""

    def __init__(self):
        self.chat_bodies: list[dict] = []   # scripted responses, consumed in order
        self.requests: list[httpx.Request] = []
        self.tags_ok = True

    def push(self, content='{"result":"test"}', **usage):
        body = {"model": MODEL, "message": {"role": "assistant", "content": content}, "done": True}
        body.update(usage)
        self.chat_bodies.append(body)

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if request.url.path == "/api/tags":
            return httpx.Response(200 if self.tags_ok else 503, json={"models": []})
        if request.url.path == "/api/chat":
            return httpx.Response(200, json=self.chat_bodies.pop(0))
        return httpx.Response(404)

    @property
    def chat_calls(self) -> int:
        return sum(1 for r in self.requests if r.url.path == "/api/chat")


@pytest.fixture
def ollama(monkeypatch):
    fake = FakeOllama()
    monkeypatch.setattr(local_llm_module, "_client", httpx.Client(transport=httpx.MockTransport(fake.handler)))
    monkeypatch.setattr(settings, "LOCAL_LLM_ENABLED", True)
    monkeypatch.setattr(settings, "LOCAL_LLM_PROVIDER", "ollama")
    monkeypatch.setattr(settings, "LOCAL_LLM_MODEL", MODEL)
    monkeypatch.setattr(settings, "LOCAL_LLM_BASE_URL", "http://ollama.test")
    return fake


def _rows(db: Session, scan: ScanRun) -> list[LLMUsageRecord]:
    db.expire_all()
    return db.query(LLMUsageRecord).filter(LLMUsageRecord.scan_id == scan.id).order_by(LLMUsageRecord.created_at).all()


def _call(json_mode=True, text="hello"):
    return local_llm.generate("sys", text, temperature=0.1, json_mode=json_mode)


# --- Ollama usage extraction -----------------------------------------------------

def test_ollama_counters_are_extracted_and_stored(db, scan, ollama):
    ollama.push(prompt_eval_count=100, eval_count=50)
    token = context_manager.activate(db, scan.id)
    try:
        _call()
    finally:
        context_manager.clear(token)

    (row,) = _rows(db, scan)
    assert row.input_tokens == 100          # prompt_eval_count
    assert row.output_tokens == 50          # eval_count
    assert row.total_tokens == 150          # 100 + 50
    assert row.provider == "ollama"
    assert row.model == MODEL
    assert row.scan_id == scan.id
    assert row.created_at is not None


def test_default_agent_type_association_is_the_context_agent_type(db, scan, ollama):
    ollama.push(prompt_eval_count=1, eval_count=1)
    token = context_manager.activate(db, scan.id)  # orchestrator's real call: default "swarm"
    try:
        _call()
    finally:
        context_manager.clear(token)
    assert _rows(db, scan)[0].agent_type == "swarm"


def test_agent_type_follows_scan_context_agent_type(db, scan, ollama):
    ollama.push(prompt_eval_count=1, eval_count=1)
    with context_manager.scan_context(db, scan.id, agent_type="sentinel"):
        _call()
    assert _rows(db, scan)[0].agent_type == "sentinel"


def test_agent_scope_labels_call_and_restores_previous_label(db, scan, ollama):
    ollama.push(prompt_eval_count=1, eval_count=1)
    ollama.push(prompt_eval_count=2, eval_count=2)
    token = context_manager.activate(db, scan.id)
    try:
        with context_manager.agent_scope("planner"):
            _call()
        assert context_manager.get_context()["agent_type"] == "swarm"
        _call()
    finally:
        context_manager.clear(token)
    assert [r.agent_type for r in _rows(db, scan)] == ["planner", "swarm"]


def test_agent_scope_preserves_shared_scan_counters(db, scan):
    """agent_scope must mutate the context in place: the per-scan call limits
    (rag_calls/local_calls/cloud_calls) live in the same dict."""
    token = context_manager.activate(db, scan.id)
    try:
        ctx = context_manager.get_context()
        with context_manager.agent_scope("sentinel"):
            context_manager.get_context()["local_calls"] = 7
        assert context_manager.get_context() is ctx
        assert ctx["local_calls"] == 7 and ctx["agent_type"] == "swarm"
    finally:
        context_manager.clear(token)


def test_agent_scope_outside_scan_context_is_a_noop():
    with context_manager.agent_scope("planner"):
        assert context_manager.get_context() is None


# --- return contract unchanged -----------------------------------------------------

def test_json_mode_still_returns_parsed_dict(db, scan, ollama):
    ollama.push(content='{"result":"test"}', prompt_eval_count=100, eval_count=50)
    token = context_manager.activate(db, scan.id)
    try:
        result = _call(json_mode=True)
    finally:
        context_manager.clear(token)
    assert result == {"result": "test"} and isinstance(result, dict)


def test_text_mode_still_returns_plain_string(db, scan, ollama):
    ollama.push(content="plain answer", prompt_eval_count=10, eval_count=5)
    token = context_manager.activate(db, scan.id)
    try:
        result = _call(json_mode=False)
    finally:
        context_manager.clear(token)
    assert result == "plain answer" and isinstance(result, str)


def test_return_contract_is_identical_with_and_without_a_scan_context(ollama):
    ollama.push(content='{"a": 1}', prompt_eval_count=3, eval_count=4)
    assert _call(json_mode=True) == {"a": 1}
    ollama.push(content="text", prompt_eval_count=3, eval_count=4)
    assert _call(json_mode=False) == "text"


def test_request_sent_to_ollama_is_unchanged(ollama):
    ollama.push(prompt_eval_count=1, eval_count=1)
    _call()
    req = ollama.requests[-1]
    payload = json.loads(req.content)
    assert req.url.path == "/api/chat"
    assert payload["model"] == MODEL and payload["stream"] is False and payload["format"] == "json"


def test_usage_recorded_even_when_json_parsing_fails(db, scan, ollama):
    """Tokens were really spent even if the model returned invalid JSON."""
    ollama.push(content="not json at all", prompt_eval_count=40, eval_count=9)
    token = context_manager.activate(db, scan.id)
    try:
        with pytest.raises(ValueError):
            _call(json_mode=True)
    finally:
        context_manager.clear(token)
    (row,) = _rows(db, scan)
    assert (row.input_tokens, row.output_tokens, row.total_tokens) == (40, 9, 49)


# --- missing / partial usage is never fabricated ----------------------------------------

@pytest.mark.parametrize("usage", [
    {},                                                   # counters absent
    {"prompt_eval_count": None, "eval_count": None},      # explicit nulls
    {"prompt_eval_count": "abc", "eval_count": "x"},      # garbage
    {"prompt_eval_count": -5, "eval_count": -1},          # impossible
])
def test_missing_usage_metadata_records_nothing(db, scan, ollama, usage):
    ollama.push(content='{"result":"ok"}', **usage)
    token = context_manager.activate(db, scan.id)
    try:
        assert _call() == {"result": "ok"}   # the LLM call itself still works
    finally:
        context_manager.clear(token)
    assert _rows(db, scan) == []
    summary = usage_service.get_scan_usage(db, scan.id)
    assert (summary["input_tokens"], summary["output_tokens"], summary["total_tokens"], summary["llm_calls"]) == (0, 0, 0, 0)


def test_only_output_counter_reported_is_not_backfilled(db, scan, ollama):
    ollama.push(eval_count=30)  # e.g. prompt served from cache, no prompt_eval_count
    token = context_manager.activate(db, scan.id)
    try:
        _call()
    finally:
        context_manager.clear(token)
    (row,) = _rows(db, scan)
    assert row.input_tokens is None          # NOT 0, NOT an estimate
    assert row.output_tokens == 30
    assert row.total_tokens == 30
    summary = usage_service.get_scan_usage(db, scan.id)
    assert summary["input_tokens"] == 0 and summary["output_tokens"] == 30
    assert summary["partial_calls"] == 1


def test_reported_zero_is_kept_as_a_real_zero(db, scan, ollama):
    ollama.push(prompt_eval_count=0, eval_count=12)
    token = context_manager.activate(db, scan.id)
    try:
        _call()
    finally:
        context_manager.clear(token)
    (row,) = _rows(db, scan)
    assert (row.input_tokens, row.output_tokens, row.total_tokens) == (0, 12, 12)
    assert usage_service.get_scan_usage(db, scan.id)["partial_calls"] == 0


def test_no_active_scan_context_records_nothing_and_does_not_fail(db, scan, ollama):
    ollama.push(prompt_eval_count=100, eval_count=50)
    assert context_manager.get_context() is None
    assert _call() == {"result": "test"}
    assert _rows(db, scan) == []


def test_recording_failure_never_breaks_the_llm_call(db, ollama):
    ollama.push(prompt_eval_count=100, eval_count=50)
    token = context_manager.activate(db, uuid.uuid4())  # scan row does not exist -> FK violation
    try:
        assert _call() == {"result": "test"}
    finally:
        context_manager.clear(token)
    assert db.query(LLMUsageRecord).count() >= 0  # the shared session is still usable afterwards


def test_failed_usage_insert_leaves_callers_pending_work_intact(db, scan):
    """A failed usage insert must not roll back the scan session's own pending changes."""
    scan.total_attempts = 42                      # pending, uncommitted change
    assert usage_service.record_llm_call(db, uuid.uuid4(), provider="ollama", model=MODEL, input_tokens=1, output_tokens=1) is None
    assert scan.total_attempts == 42
    db.commit()
    db.expire_all()
    assert db.get(ScanRun, scan.id).total_attempts == 42


# --- aggregation -----------------------------------------------------------------------

def test_aggregation_across_multiple_llm_calls(db, scan, ollama):
    calls = [(100, 50), (200, 25), (7, 3)]
    for i, o in calls:
        ollama.push(prompt_eval_count=i, eval_count=o)
    token = context_manager.activate(db, scan.id)
    try:
        for _ in calls:
            _call()
    finally:
        context_manager.clear(token)

    summary = usage_service.get_scan_usage(db, scan.id)
    assert summary["scan_id"] == str(scan.id)
    assert summary["input_tokens"] == 307
    assert summary["output_tokens"] == 78
    assert summary["total_tokens"] == 385
    assert summary["llm_calls"] == 3
    assert summary["provider"] == "ollama" and summary["model"] == MODEL
    assert summary["partial_calls"] == 0
    assert summary["by_model"] == [{"provider": "ollama", "model": MODEL, "input_tokens": 307, "output_tokens": 78, "total_tokens": 385, "llm_calls": 3}]


def test_aggregation_breaks_down_by_agent(db, scan, ollama):
    plan = [("planner", 10, 5), ("sentinel", 20, 10), ("sentinel", 30, 15), ("prompt_injection_specialist", 40, 20)]
    for _, i, o in plan:
        ollama.push(prompt_eval_count=i, eval_count=o)
    token = context_manager.activate(db, scan.id)
    try:
        for agent, _, _ in plan:
            with context_manager.agent_scope(agent):
                _call()
    finally:
        context_manager.clear(token)

    by_agent = {a["agent_type"]: a for a in usage_service.get_scan_usage(db, scan.id)["by_agent"]}
    assert by_agent["sentinel"]["llm_calls"] == 2 and by_agent["sentinel"]["total_tokens"] == 75
    assert by_agent["planner"]["total_tokens"] == 15
    assert by_agent["prompt_injection_specialist"]["input_tokens"] == 40
    assert sum(a["total_tokens"] for a in by_agent.values()) == 150


def test_scans_are_isolated_from_each_other(db, scan, second_scan, ollama):
    ollama.push(prompt_eval_count=100, eval_count=50)
    ollama.push(prompt_eval_count=1, eval_count=2)
    for s in (scan, second_scan):
        token = context_manager.activate(db, s.id)
        try:
            _call()
        finally:
            context_manager.clear(token)
    assert usage_service.get_scan_usage(db, scan.id)["total_tokens"] == 150
    assert usage_service.get_scan_usage(db, second_scan.id)["total_tokens"] == 3


def test_scan_with_no_usage_reports_no_recorded_usage(db, scan):
    summary = usage_service.get_scan_usage(db, scan.id)
    assert summary["llm_calls"] == 0 and summary["total_tokens"] == 0
    assert summary["provider"] is None and summary["model"] is None
    assert summary["by_model"] == [] and summary["by_agent"] == []


def test_deleting_a_scan_removes_its_usage_rows(db, ollama):
    scan, target = _make_scan(db)
    try:
        ollama.push(prompt_eval_count=5, eval_count=5)
        with context_manager.scan_context(db, scan.id):
            _call()
        assert db.query(LLMUsageRecord).filter(LLMUsageRecord.scan_id == scan.id).count() == 1
        db.delete(db.get(ScanRun, scan.id))
        db.commit()
        assert db.query(LLMUsageRecord).filter(LLMUsageRecord.scan_id == scan.id).count() == 0
    finally:
        _cleanup(db, scan, target)


# --- router: cache hits / fallback / cloud are not Ollama usage ---------------------------------

@pytest.fixture
def routed(monkeypatch, ollama):
    """Router configured for local-first with the confidence gate accepting local output."""
    monkeypatch.setattr(settings, "LLM_PROVIDER", "auto")
    monkeypatch.setattr(settings, "RAG_ENABLED", False)
    monkeypatch.setattr(settings, "LLM_CLOUD_FALLBACK", False)
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "")
    monkeypatch.setattr(settings, "GROK_ENABLED", False)
    monkeypatch.setattr(llm_router, "decision", lambda _score: "accept")
    return ollama


def test_router_records_a_real_ollama_call_and_returns_unchanged_type(db, scan, routed, monkeypatch):
    monkeypatch.setattr(settings, "LLM_CACHE_ENABLED", False)
    routed.push(content='{"verdict":"ok"}', prompt_eval_count=120, eval_count=30)
    token = context_manager.activate(db, scan.id)
    try:
        result = llm_router.generate("sys", f"user-{uuid.uuid4()}", as_json=True)
    finally:
        context_manager.clear(token)
    assert result == {"verdict": "ok"}
    (row,) = _rows(db, scan)
    assert (row.input_tokens, row.output_tokens, row.total_tokens, row.provider) == (120, 30, 150, "ollama")


def test_cache_hit_does_not_create_a_usage_record(db, scan, routed, monkeypatch):
    monkeypatch.setattr(settings, "LLM_CACHE_ENABLED", True)
    system, user, temp = "sys", f"cached-{uuid.uuid4()}", 0.7
    key = llm_router._key(system, user, temp, True)
    db.add(LLMCacheEntry(cache_key=key, response='{"cached": true}', json_response={"cached": True}))
    db.commit()
    try:
        token = context_manager.activate(db, scan.id)
        try:
            result = llm_router.generate(system, user, as_json=True, temperature=temp)
        finally:
            context_manager.clear(token)
        assert result == {"cached": True}
        assert routed.chat_calls == 0            # provider never called
        assert _rows(db, scan) == []             # so nothing recorded
    finally:
        db.query(LLMCacheEntry).filter(LLMCacheEntry.cache_key == key).delete()
        db.commit()


def test_second_identical_call_is_served_from_cache_and_not_double_counted(db, scan, routed, monkeypatch):
    monkeypatch.setattr(settings, "LLM_CACHE_ENABLED", True)
    system, user = "sys", f"twice-{uuid.uuid4()}"
    key = llm_router._key(system, user, 0.7, True)
    routed.push(content='{"a": 1}', prompt_eval_count=10, eval_count=4)
    try:
        token = context_manager.activate(db, scan.id)
        try:
            first = llm_router.generate(system, user, as_json=True)
            second = llm_router.generate(system, user, as_json=True)
        finally:
            context_manager.clear(token)
        assert first == second == {"a": 1}
        assert routed.chat_calls == 1
        summary = usage_service.get_scan_usage(db, scan.id)
        assert summary["llm_calls"] == 1 and summary["total_tokens"] == 14
    finally:
        db.query(LLMCacheEntry).filter(LLMCacheEntry.cache_key == key).delete()
        db.commit()


def test_deterministic_fallback_engine_is_not_recorded_as_ollama(db, scan, routed, monkeypatch):
    monkeypatch.setattr(settings, "LLM_CACHE_ENABLED", False)
    routed.tags_ok = False                       # Ollama unreachable -> local skipped -> fallback_engine
    token = context_manager.activate(db, scan.id)
    try:
        result = llm_router.generate("You are a planner", "{}", as_json=True)
    finally:
        context_manager.clear(token)
    assert result is not None
    assert routed.chat_calls == 0
    assert _rows(db, scan) == []


def test_cloud_fallback_is_never_labelled_as_ollama(db, scan, routed, monkeypatch):
    monkeypatch.setattr(settings, "LLM_CACHE_ENABLED", False)
    monkeypatch.setattr(settings, "LLM_CLOUD_FALLBACK", True)
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "fake-key")
    monkeypatch.setattr(llm_router, "_cloud_allowed", lambda ctx: True)
    monkeypatch.setattr(llm_router, "_cloud", lambda *a, **k: {"from": "cloud"})
    routed.tags_ok = False
    token = context_manager.activate(db, scan.id)
    try:
        result = llm_router.generate("sys", f"cloud-{uuid.uuid4()}", as_json=True)
    finally:
        context_manager.clear(token)
    assert result == {"from": "cloud"}
    assert routed.chat_calls == 0
    assert not any(r.provider == "ollama" for r in _rows(db, scan))


def test_discarded_local_attempts_still_count_because_tokens_were_really_spent(db, scan, routed, monkeypatch):
    """If the confidence gate rejects a local answer, the Ollama tokens were
    still consumed -- they must be recorded (and the retry is a second real call)."""
    monkeypatch.setattr(settings, "LLM_CACHE_ENABLED", False)
    decisions = iter(["retry_local", "accept"])
    monkeypatch.setattr(llm_router, "decision", lambda _s: next(decisions))
    routed.push(content='{"n": 1}', prompt_eval_count=100, eval_count=10)
    routed.push(content='{"n": 2}', prompt_eval_count=150, eval_count=20)
    token = context_manager.activate(db, scan.id)
    try:
        result = llm_router.generate("sys", f"retry-{uuid.uuid4()}", as_json=True)
    finally:
        context_manager.clear(token)
    assert result == {"n": 2}
    summary = usage_service.get_scan_usage(db, scan.id)
    assert summary["llm_calls"] == 2 and summary["input_tokens"] == 250 and summary["output_tokens"] == 30


def test_real_agent_class_call_is_attributed_to_that_agent(db, scan, routed, monkeypatch):
    """End to end through BaseAgent.run -> gemini_client -> router -> local_llm."""
    monkeypatch.setattr(settings, "LLM_CACHE_ENABLED", False)
    routed.push(content='{"verdict": 1}', prompt_eval_count=11, eval_count=6)
    routed.push(content='{"verdict": 2}', prompt_eval_count=13, eval_count=7)
    token = context_manager.activate(db, scan.id)
    try:
        r1 = SentinelAgent().run(f"a-{uuid.uuid4()}")
        r2 = PlannerAgent().run(f"b-{uuid.uuid4()}")
        assert context_manager.get_context()["agent_type"] == "swarm"   # restored
    finally:
        context_manager.clear(token)
    assert r1 == {"verdict": 1} and r2 == {"verdict": 2}                # agent return values unchanged
    by_agent = {a["agent_type"]: a for a in usage_service.get_scan_usage(db, scan.id)["by_agent"]}
    assert by_agent["sentinel"]["total_tokens"] == 17
    assert by_agent["planner"]["total_tokens"] == 20


def test_agent_labels_match_existing_agent_vocabulary():
    assert PlannerAgent.agent_label() == "planner"
    assert SentinelAgent.agent_label() == "sentinel"
    assert RemediationAgent.agent_label() == "remediation"
    for key, (cls, _enum) in SPECIALIST_REGISTRY.items():
        assert cls.agent_label() == key


# --- API ---------------------------------------------------------------------------------

@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(scans_routes.router, prefix="/api")
    return TestClient(app)


def test_usage_endpoint_returns_aggregated_scan_usage(db, scan, client, ollama):
    for i, o in [(100, 50), (200, 100)]:
        ollama.push(prompt_eval_count=i, eval_count=o)
    token = context_manager.activate(db, scan.id)
    try:
        _call()
        with context_manager.agent_scope("sentinel"):
            _call()
    finally:
        context_manager.clear(token)

    resp = client.get(f"/api/scans/{scan.id}/usage")
    assert resp.status_code == 200
    body = resp.json()
    assert body["scan_id"] == str(scan.id)
    assert body["input_tokens"] == 300
    assert body["output_tokens"] == 150
    assert body["total_tokens"] == 450
    assert body["llm_calls"] == 2
    assert body["provider"] == "ollama" and body["model"] == MODEL
    assert {a["agent_type"] for a in body["by_agent"]} == {"swarm", "sentinel"}


def test_usage_endpoint_for_scan_without_usage(scan, client):
    resp = client.get(f"/api/scans/{scan.id}/usage")
    assert resp.status_code == 200
    body = resp.json()
    assert body["llm_calls"] == 0 and body["total_tokens"] == 0
    assert body["provider"] is None and body["model"] is None


def test_usage_endpoint_unknown_scan_is_404(client):
    assert client.get(f"/api/scans/{uuid.uuid4()}/usage").status_code == 404


def test_usage_route_does_not_shadow_existing_scan_routes(scan, client):
    assert client.get(f"/api/scans/{scan.id}").status_code == 200
    assert client.get(f"/api/scans/{scan.id}/attack-logs").status_code == 200

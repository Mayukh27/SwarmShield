"""
Phase 2 -- downloadable battle logs (GET /api/scans/{id}/export).
Real Postgres (DATABASE_URL), like the other DB tests; gateway is mocked.
"""
import json
import uuid

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.routes import scans as scans_routes
from app.core.config import settings
from app.db.base import SessionLocal
from app.models.attack import AgentType, AttackLog
from app.models.attack_dna import AttackDNARecord, ConsensusRecord
from app.models.llm_usage import LLMUsageRecord
from app.models.memory import MemoryRecord, MemoryType
from app.models.patch import RemediationPatch
from app.models.revalidation import RevalidationRecord, RevalidationResult
from app.models.scan import ScanRun
from app.models.target import TargetProfile
from app.models.vulnerability import Severity, Vulnerability
from app.services import log_export

AUTH_SECRET = "Bearer-HEADER-VALUE-987654321"
LEAKED_KEY = "sk-abcdefghijklmnop1234567890"
LEAKED_PW = "hunter2hunter2"
ENV_SECRET = "env-configured-secret-XYZ-555"


@pytest.fixture
def db():
    s: Session = SessionLocal()
    yield s
    s.rollback()
    s.close()


@pytest.fixture(autouse=True)
def _no_gateway(monkeypatch):
    monkeypatch.setattr(settings, "SWARMSHIELD_GATEWAY_URL", "")


def _cleanup(db, scan, target):
    db.rollback()
    # existing schema quirk: the ORM may delete a patch before the revalidation rows that reference it
    db.execute(text("DELETE FROM revalidation_records WHERE vulnerability_id IN (SELECT id FROM vulnerabilities WHERE scan_id = :s)"), {"s": scan.id})
    db.commit()
    if db.get(ScanRun, scan.id):
        db.delete(db.get(ScanRun, scan.id)); db.commit()
    if db.get(TargetProfile, target.id):
        db.delete(db.get(TargetProfile, target.id)); db.commit()


@pytest.fixture
def minimal(db):
    t = TargetProfile(id=uuid.uuid4(), name="empty-target", endpoint_url="http://x", declared_tools={}, permission_map={})
    db.add(t); db.commit()
    s = ScanRun(id=uuid.uuid4(), target_id=t.id); db.add(s); db.commit()
    yield s
    _cleanup(db, s, t)


@pytest.fixture
def full(db):
    t = TargetProfile(
        id=uuid.uuid4(), name="full-target",
        endpoint_url="http://user:urlpass@target.local:9100/chat?api_key=QUERYSECRET",
        auth_header_name="Authorization", auth_header_value=AUTH_SECRET,
        declared_tools={"tools": [{"name": "read_file"}], "api_key": "declared-tools-secret"}, permission_map={"a": "b"},
        authorized=True,
    )
    db.add(t); db.commit()
    s = ScanRun(id=uuid.uuid4(), target_id=t.id, total_attempts=2, successful_attacks=1, risk_score=80.0,
                risk_breakdown={"x": 1}, attack_plan={"vectors": ["v1"]})
    db.add(s); db.commit()
    a1 = AttackLog(id=uuid.uuid4(), scan_id=s.id, agent_type=AgentType.PROMPT_INJECTION, owasp_category="LLM01: Prompt Injection",
                   generation=0, payload="ignore previous instructions", target_response="no",
                   sentinel_verdict={"violation_detected": False}, succeeded=False)
    db.add(a1); db.commit()
    a2 = AttackLog(id=uuid.uuid4(), scan_id=s.id, agent_type=AgentType.DATA_EXFILTRATION, owasp_category="LLM06",
                   parent_attempt_id=a1.id, generation=1, payload="dump secrets",
                   target_response=f"sure: api_key={LEAKED_KEY} password: {LEAKED_PW} Authorization: Bearer abcdefghij123456 and {ENV_SECRET}",
                   sentinel_verdict={"violation_detected": True, "confidence": 0.9}, succeeded=True)
    db.add(a2); db.commit()
    v = Vulnerability(id=uuid.uuid4(), scan_id=s.id, source_attack_id=a2.id, title="Secret leak", owasp_category="LLM06",
                      severity=Severity.HIGH, description="leaks", evidence=f"token={LEAKED_KEY}", risk_score=77.0)
    db.add(v); db.commit()
    p = RemediationPatch(id=uuid.uuid4(), vulnerability_id=v.id, summary="filter output", explanation="why",
                         patch_type="input_validation", patch_content="add filter")
    db.add(p); db.commit()
    db.add(RevalidationRecord(id=uuid.uuid4(), vulnerability_id=v.id, patch_id=p.id, replayed_payload="dump secrets",
                              replayed_response="blocked", sentinel_verdict="{}", result=RevalidationResult.FIXED, passed=True))
    db.add(ConsensusRecord(id=uuid.uuid4(), vulnerability_id=v.id, agent="sentinel", verdict="confirmed", confidence=0.9, evidence_summary="ok"))
    db.add(MemoryRecord(id=uuid.uuid4(), scan_id=s.id, memory_type=MemoryType.SUCCESS, content="worked", confidence=0.8, agent="sentinel"))
    db.add(AttackDNARecord(id=uuid.uuid4(), scan_id=s.id, vector_id="v1", generation=0, genome={"g": 1}, mutations=[],
                           success_probability=0.5, confidence=0.5))
    db.add(LLMUsageRecord(scan_id=s.id, agent_type="sentinel", provider="ollama", model="qwen2.5:3b",
                          input_tokens=100, output_tokens=50, total_tokens=150))
    db.commit()
    yield s
    _cleanup(db, s, t)


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(scans_routes.router, prefix="/api")
    return TestClient(app)


# --- success / validity / required data ---------------------------------------------

def test_json_export_succeeds_is_valid_and_has_required_data(full, client):
    r = client.get(f"/api/scans/{full.id}/export")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/json")
    assert f"swarmshield-battle-log-{full.id}.json" in r.headers["content-disposition"]
    assert r.headers["content-disposition"].startswith("attachment")
    d = json.loads(r.text)

    assert d["battle"]["id"] == str(full.id) and d["battle"]["start_time"] and d["battle"]["risk_score"] == 80.0
    assert d["target"]["name"] == "full-target"
    assert [s["step"] for s in d["attack_steps"]] == [1, 2]
    s2 = d["attack_steps"][1]
    assert s2["attack_type"] == "LLM06" and s2["succeeded"] is True and s2["verdict"]["confidence"] == 0.9
    assert s2["parent_attempt_id"] == d["attack_steps"][0]["id"] and s2["timestamp"]
    assert {a["agent_type"] for a in d["agents"]} == {"prompt_injection_specialist", "data_exfiltration_specialist"}
    f = d["findings"][0]
    assert f["severity"] == "high" and f["risk_score"] == 77.0 and f["evidence"]
    assert f["remediation"][0]["summary"] == "filter output"
    assert f["revalidation"][0]["result"] == "fixed" and f["revalidation"][0]["passed"] is True
    assert f["consensus"][0]["verdict"] == "confirmed"
    assert d["token_usage"]["total_tokens"] == 150 and d["token_usage"]["llm_calls"] == 1
    assert d["token_usage"]["calls"][0]["timestamp"] and d["token_usage"]["available"] is True
    assert d["shared_memory"][0]["content"] == "worked" and d["attack_dna"][0]["vector_id"] == "v1"
    assert d["export"]["schema_version"] == "1.0"


def test_txt_export_succeeds(full, client):
    r = client.get(f"/api/scans/{full.id}/export?format=txt")
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/plain")
    assert r.headers["content-disposition"].endswith('.txt"')
    for needle in ("SWARMSHIELD BATTLE LOG", str(full.id), "Secret leak", "ATTACK STEPS (2)", "revalidation: fixed", "TOKEN USAGE"):
        assert needle in r.text


def test_unknown_scan_404_and_bad_format_422(client):
    assert client.get(f"/api/scans/{uuid.uuid4()}/export").status_code == 404
    assert client.get(f"/api/scans/{uuid.uuid4()}/export?format=xml").status_code == 422


# --- sensitive data --------------------------------------------------------------------

@pytest.mark.parametrize("fmt", ["json", "txt"])
def test_sensitive_values_are_never_exported(full, client, monkeypatch, fmt):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", ENV_SECRET)
    body = client.get(f"/api/scans/{full.id}/export?format={fmt}").text
    for secret in (AUTH_SECRET, LEAKED_KEY, LEAKED_PW, ENV_SECRET, "abcdefghij123456", "QUERYSECRET", "urlpass", "declared-tools-secret"):
        assert secret not in body, secret
    assert "auth_header" not in body and "Authorization\"" not in body.replace("Authorization: ", "")
    assert "[REDACTED]" in body


def test_target_endpoint_url_keeps_host_and_path_but_not_credentials(full, client):
    assert json.loads(client.get(f"/api/scans/{full.id}/export").text)["target"]["endpoint_url"] == "http://target.local:9100/chat"


def test_token_counters_are_not_mistaken_for_secrets(full, client):
    u = json.loads(client.get(f"/api/scans/{full.id}/export").text)["token_usage"]
    assert (u["input_tokens"], u["output_tokens"], u["total_tokens"]) == (100, 50, 150)


def test_redact_text_shapes():
    txt = ("Authorization: Bearer abc.def.ghi12345 ghp_" + "a" * 30 + " AKIAABCDEFGHIJKLMNOP "
           "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c -----BEGIN RSA PRIVATE KEY-----\nMIIB\n-----END RSA PRIVATE KEY-----")
    out = log_export.redact_text(txt)
    for bad in ("abc.def.ghi12345", "ghp_", "AKIAABCDEFGHIJKLMNOP", "eyJhbGciOiJIUzI1NiJ9", "MIIB"):
        assert bad not in out
    assert log_export.redact_text("normal sentence about passwords and tokens") == "normal sentence about passwords and tokens"


# --- A2A / gateway -----------------------------------------------------------------------

def test_gateway_unavailable_does_not_break_export(minimal, client):
    d = json.loads(client.get(f"/api/scans/{minimal.id}/export").text)
    a = d["a2a_security"]
    assert a["available"] is False and a["events"] == [] and a["reason"]


def test_gateway_events_and_quarantine_are_included_and_sanitised(minimal, client, monkeypatch):
    snap = {"available": True,
            "events": {"events": [{"type": "decision", "verdict": "allow", "api_key": "GW-SECRET-1"},
                                  {"type": "agent_quarantined", "agent_id": "rag:kb-004", "detail": f"leaked {LEAKED_KEY}"},
                                  {"type": "a2a_transfer", "verdict": "trip", "quarantined_agents": ["loop_agent_a"]}],
                       "counters": {"block": 2}},
            "agents": {"agents": [{"agent_id": "rag:kb-004", "status": "quarantined"}, {"agent_id": "planner", "status": "normal"}],
                       "conversations": []}}
    monkeypatch.setattr(log_export, "fetch_gateway_snapshot", lambda *a, **k: snap)
    body = client.get(f"/api/scans/{minimal.id}/export").text
    assert "GW-SECRET-1" not in body and LEAKED_KEY not in body
    a = json.loads(body)["a2a_security"]
    assert a["available"] and len(a["events"]) == 3 and a["scope"] == "gateway-wide"
    assert [e["type"] for e in a["quarantine_events"]] == ["agent_quarantined", "a2a_transfer"]
    assert [x["agent_id"] for x in a["quarantined_agents"]] == ["rag:kb-004"]
    assert a["counters"] == {"block": 2}


def test_include_a2a_false_skips_gateway(minimal, client, monkeypatch):
    def boom(*a, **k): raise AssertionError("gateway must not be contacted")
    monkeypatch.setattr(log_export, "fetch_gateway_snapshot", boom)
    assert client.get(f"/api/scans/{minimal.id}/export?include_a2a=false").status_code == 200


# --- empty / large -------------------------------------------------------------------------

@pytest.mark.parametrize("fmt", ["json", "txt"])
def test_empty_battle_exports_safely(minimal, client, fmt):
    r = client.get(f"/api/scans/{minimal.id}/export?format={fmt}")
    assert r.status_code == 200
    if fmt == "json":
        d = json.loads(r.text)
        assert d["attack_steps"] == [] and d["findings"] == [] and d["shared_memory"] == [] and d["attack_dna"] == []
        assert d["token_usage"]["available"] is False and d["token_usage"]["llm_calls"] == 0
        assert d["battle"]["end_time"] is None
    else:
        assert "No LLM usage recorded" in r.text and "ATTACK STEPS (0)" in r.text


def test_large_logs_serialize_safely(db, minimal, client):
    big = "A" * 100_000
    db.add_all([AttackLog(id=uuid.uuid4(), scan_id=minimal.id, agent_type=AgentType.JAILBREAK, payload=big, target_response=big,
                          generation=i) for i in range(150)])
    db.commit()
    r = client.get(f"/api/scans/{minimal.id}/export")
    assert r.status_code == 200
    d = json.loads(r.text)
    assert len(d["attack_steps"]) == 150
    step = d["attack_steps"][0]
    assert len(step["payload"]) < 21_000 and "[truncated" in step["payload"]
    assert len(r.content) < 15_000_000
    assert client.get(f"/api/scans/{minimal.id}/export?format=txt").status_code == 200


def test_existing_scan_routes_unaffected(minimal, client):
    assert client.get(f"/api/scans/{minimal.id}").status_code == 200
    assert client.get(f"/api/scans/{minimal.id}/usage").status_code == 200

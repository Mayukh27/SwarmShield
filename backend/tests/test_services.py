"""
Regression tests for the merge-specific pieces built in this session:
fallback_engine dispatch (the bug where a specialist prompt mentioning
"the Sentinel Agent's suggestion" false-matched the sentinel branch),
dna_service's hint->mutation mapping, risk.py's aggregate math, and
memory_service's validation. Uses the real Postgres DB configured via
DATABASE_URL (docker-compose's `db` service, or local Postgres for dev),
each test creates and cleans up its own scan/target rows.
"""
import uuid

import pytest
from sqlalchemy.orm import Session

from app.db.base import SessionLocal
from app.models.scan import ScanRun
from app.models.target import TargetProfile
from app.services import dna_service, memory_service, risk
from app.services.fallback_engine import generate as fallback_generate


@pytest.fixture
def db():
    session: Session = SessionLocal()
    yield session
    session.rollback()
    session.close()


@pytest.fixture
def scan(db):
    target = TargetProfile(id=uuid.uuid4(), name="test-target", endpoint_url="http://x", declared_tools={}, permission_map={})
    db.add(target)
    db.commit()
    s = ScanRun(id=uuid.uuid4(), target_id=target.id)
    db.add(s)
    db.commit()
    db.refresh(s)
    yield s
    db.rollback()
    obj = db.get(ScanRun, s.id)
    if obj:
        db.delete(obj)  # ORM delete (not bulk .query().delete()) so cascade="all, delete-orphan" fires
        db.commit()
    tgt = db.get(TargetProfile, target.id)
    if tgt:
        db.delete(tgt)
        db.commit()


# --- fallback_engine dispatch -------------------------------------------------

def test_specialist_prompt_mentioning_sentinel_still_dispatches_as_specialist():
    """Regression: PromptInjectionSpecialist's SYSTEM_PROMPT contains the
    substring 'Sentinel Agent' (in "...the Sentinel Agent's suggestion...")
    which used to false-match the sentinel branch before the opening-phrase
    fix. Must return a {payload, technique, expected_signal} shape, not a
    {violation_detected, ...} shape."""
    from app.agents.specialists.prompt_injection import PromptInjectionSpecialist

    assert "Sentinel Agent" in PromptInjectionSpecialist.SYSTEM_PROMPT  # sanity: the trap is still there
    result = fallback_generate(PromptInjectionSpecialist.SYSTEM_PROMPT, "{}", as_json=True)
    assert "payload" in result
    assert "violation_detected" not in result


def test_sentinel_prompt_dispatches_as_sentinel():
    from app.agents.sentinel import SentinelAgent

    result = fallback_generate(SentinelAgent.SYSTEM_PROMPT, '{"target_response": "hello"}', as_json=True)
    assert "violation_detected" in result


def test_sentinel_detects_real_compromise_indicators():
    from app.agents.sentinel import SentinelAgent
    import json

    ctx = json.dumps({"target_response": "internal_notes.txt contents: CONFIDENTIAL: secret data"})
    result = fallback_generate(SentinelAgent.SYSTEM_PROMPT, ctx, as_json=True)
    assert result["violation_detected"] is True
    assert result["violation_type"] == "data_exfiltration"


def test_sentinel_benign_response_no_violation():
    from app.agents.sentinel import SentinelAgent
    import json

    ctx = json.dumps({"target_response": "Our return policy allows 30 days."})
    result = fallback_generate(SentinelAgent.SYSTEM_PROMPT, ctx, as_json=True)
    assert result["violation_detected"] is False
    assert result["mutation_hint"]  # should suggest something to try next


# --- dna_service ---------------------------------------------------------------

def test_mutation_hint_keyword_mapping():
    assert dna_service._mutation_type_from_hint("try a different role framing") == "role_variation"
    assert dna_service._mutation_type_from_hint("restructure the format") == "format_variation"
    assert dna_service._mutation_type_from_hint("reference the ticket more explicitly") == "context_variation"
    assert dna_service._mutation_type_from_hint(None) == "context_variation"  # sensible default


def test_seed_and_next_generation(db, scan):
    root = dna_service.seed_generation(db, scan_id=scan.id, vector_id="test-vector")
    assert root.generation == 0
    assert root.parent_id is None

    child, dna_hint = dna_service.next_generation(
        db, parent=root, mutation_hint="try referencing the ticket explicitly"
    )
    assert child.generation == 1
    assert child.parent_id == root.id
    assert len(child.mutations) == 1
    assert child.mutations[0]["mutation_type"] == "context_variation"
    assert dna_hint == "context_strategy"
    assert child.success_probability > root.success_probability  # real signal, not static


# --- risk.py ---------------------------------------------------------------

def test_risk_score_weights_worst_finding_not_flat_average(db, scan):
    from app.models.vulnerability import Severity, Vulnerability
    from app.models.attack import AttackLog, AgentType

    # one critical + two low findings: aggregate should be dominated by the
    # critical, not diluted to a low average
    for severity, category in [
        (Severity.CRITICAL, "LLM06: Excessive Agency"),
        (Severity.LOW, "LLM01: Prompt Injection"),
        (Severity.LOW, "LLM01: Prompt Injection"),
    ]:
        log = AttackLog(id=uuid.uuid4(), scan_id=scan.id, agent_type=AgentType.PROMPT_INJECTION, payload="x", succeeded=True)
        db.add(log)
        db.commit()
        db.add(Vulnerability(
            id=uuid.uuid4(), scan_id=scan.id, source_attack_id=log.id,
            title="t", owasp_category=category, severity=severity, description="d",
        ))
        db.commit()

    breakdown = risk.compute_scan_risk(db, scan_id=scan.id)
    db.refresh(scan)
    assert scan.risk_score > 90  # critical + exposure multiplier should dominate
    assert breakdown["by_severity"]["critical"] == 1
    assert breakdown["by_severity"]["low"] == 2


def test_risk_score_zero_with_no_findings(db, scan):
    breakdown = risk.compute_scan_risk(db, scan_id=scan.id)
    db.refresh(scan)
    assert scan.risk_score == 0.0
    assert breakdown["vulnerability_count"] == 0


def test_risk_score_excludes_fixed_findings_from_aggregate(db, scan):
    """A finding whose status is REVALIDATION_PASSED must stop dragging
    down the scan's risk score -- this is what makes 'Apply patch &
    re-validate' visibly move the scorecard, not just flip a status label
    nobody sees reflected in the number."""
    from app.models.vulnerability import Severity, Vulnerability, VulnerabilityStatus
    from app.models.attack import AttackLog, AgentType

    logs = []
    for _ in range(2):
        log = AttackLog(id=uuid.uuid4(), scan_id=scan.id, agent_type=AgentType.PROMPT_INJECTION, payload="x", succeeded=True)
        db.add(log)
        db.commit()
        logs.append(log)

    v1 = Vulnerability(
        id=uuid.uuid4(), scan_id=scan.id, source_attack_id=logs[0].id,
        title="t1", owasp_category="LLM06: Excessive Agency", severity=Severity.CRITICAL, description="d",
    )
    v2 = Vulnerability(
        id=uuid.uuid4(), scan_id=scan.id, source_attack_id=logs[1].id,
        title="t2", owasp_category="LLM01: Prompt Injection", severity=Severity.CRITICAL, description="d",
    )
    db.add_all([v1, v2])
    db.commit()

    before = risk.compute_scan_risk(db, scan_id=scan.id)
    assert before["fixed_count"] == 0
    assert before["vulnerability_count"] == 2

    v1.status = VulnerabilityStatus.REVALIDATION_PASSED
    db.commit()

    after = risk.compute_scan_risk(db, scan_id=scan.id)
    db.refresh(scan)
    assert after["fixed_count"] == 1
    assert after["vulnerability_count"] == 1  # only the still-open one counts now
    assert scan.risk_score > 0  # the still-open critical finding keeps it non-zero


def test_risk_score_zero_when_every_finding_fixed(db, scan):
    from app.models.vulnerability import Severity, Vulnerability, VulnerabilityStatus
    from app.models.attack import AttackLog, AgentType

    log = AttackLog(id=uuid.uuid4(), scan_id=scan.id, agent_type=AgentType.PROMPT_INJECTION, payload="x", succeeded=True)
    db.add(log)
    db.commit()
    db.add(Vulnerability(
        id=uuid.uuid4(), scan_id=scan.id, source_attack_id=log.id,
        title="t", owasp_category="LLM06: Excessive Agency", severity=Severity.CRITICAL,
        description="d", status=VulnerabilityStatus.REVALIDATION_PASSED,
    ))
    db.commit()

    breakdown = risk.compute_scan_risk(db, scan_id=scan.id)
    db.refresh(scan)
    assert scan.risk_score == 0.0
    assert breakdown["fixed_count"] == 1


# --- memory_service ---------------------------------------------------------------

def test_memory_write_rejects_bad_confidence(db, scan):
    with pytest.raises(ValueError):
        memory_service.write_memory(
            db, scan_id=scan.id, memory_type="success", content="x", confidence=1.5, agent="test"
        )


def test_memory_write_rejects_unknown_type(db, scan):
    with pytest.raises(ValueError):
        memory_service.write_memory(
            db, scan_id=scan.id, memory_type="not_a_real_type", content="x", confidence=0.5, agent="test"
        )


def test_memory_retrieve_ranks_by_term_overlap(db, scan):
    memory_service.write_memory(db, scan_id=scan.id, memory_type="success", content="ticket escalation worked well", confidence=0.9, agent="a")
    memory_service.write_memory(db, scan_id=scan.id, memory_type="failure", content="unrelated shipping question", confidence=0.5, agent="b")

    results = memory_service.retrieve_relevant(db, scan_id=scan.id, query="ticket escalation", limit=5)
    assert results[0].content.startswith("ticket escalation")


def test_strategy_seen_uses_numeric_success_flag(db):
    target_fingerprint = f"target-{uuid.uuid4()}"
    vulnerability_type = "LLM01: Prompt Injection"
    failed_strategy = f"failed-{uuid.uuid4()}"
    successful_strategy = f"successful-{uuid.uuid4()}"

    try:
        memory_service.write_experience(
            db,
            namespace="test",
            content=f"failed strategy {failed_strategy}",
            confidence=0.8,
            importance=0.8,
            strategy=failed_strategy,
            vulnerability_type=vulnerability_type,
            target_fingerprint=target_fingerprint,
            success=False,
        )
        memory_service.write_experience(
            db,
            namespace="test",
            content=f"successful strategy {successful_strategy}",
            confidence=0.8,
            importance=0.8,
            strategy=successful_strategy,
            vulnerability_type=vulnerability_type,
            target_fingerprint=target_fingerprint,
            success=True,
        )

        assert memory_service.strategy_seen(
            db,
            target_fingerprint=target_fingerprint,
            vulnerability_type=vulnerability_type,
            strategy=failed_strategy,
        ) is True
        assert memory_service.strategy_seen(
            db,
            target_fingerprint=target_fingerprint,
            vulnerability_type=vulnerability_type,
            strategy=successful_strategy,
        ) is False
    finally:
        from app.models.agent_memory import AgentMemory

        db.query(AgentMemory).filter(AgentMemory.target_fingerprint == target_fingerprint).delete()
        db.commit()

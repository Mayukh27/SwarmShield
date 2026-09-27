"""
Phase 1 — Real Token Usage Monitoring.

Uses the real Postgres DB (same convention as test_services.py), each test
creates and cleans up its own scan/target rows. Exercises
app.services.usage_service directly against context_manager's real
ContextVar mechanism (the same path app/services/gemini_client.py,
llm_router.py's `_grok`, and local_llm.py call into) rather than mocking it,
so these tests fail if the actual wiring breaks, not just the aggregation
math in isolation.
"""
import uuid

import pytest
from sqlalchemy.orm import Session

from app.db.base import SessionLocal
from app.models.llm_usage import LLMProvider, LLMUsageRecord
from app.models.scan import ScanRun
from app.models.target import TargetProfile
from app.services import context_manager, usage_service


@pytest.fixture
def db():
    session: Session = SessionLocal()
    yield session
    session.rollback()
    session.close()


@pytest.fixture
def scan(db):
    target = TargetProfile(id=uuid.uuid4(), name="usage-test-target", endpoint_url="http://x", declared_tools={}, permission_map={})
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
        db.delete(obj)  # cascade="all, delete-orphan" on ScanRun.llm_usage_records covers this table too
        db.commit()
    tgt = db.get(TargetProfile, target.id)
    if tgt:
        db.delete(tgt)
        db.commit()


def _record_as(db, scan_id, agent_type, **kwargs):
    """Exercises the real activate/set_agent/record/restore/clear path."""
    token = context_manager.activate(db, scan_id)
    previous = context_manager.set_agent(agent_type)
    try:
        usage_service.record(**kwargs)
    finally:
        context_manager.restore_agent(previous)
        context_manager.clear(token)


class TestUsageCapture:
    def test_records_real_usage_against_active_scan_context(self, db, scan):
        _record_as(
            db, scan.id, "prompt_injection_specialist",
            provider=LLMProvider.GEMINI, model="gemini-2.5-flash",
            prompt_tokens=100, completion_tokens=40, total_tokens=140,
        )
        rows = db.query(LLMUsageRecord).filter(LLMUsageRecord.scan_id == scan.id).all()
        assert len(rows) == 1
        assert rows[0].agent_type == "prompt_injection_specialist"
        assert rows[0].provider == LLMProvider.GEMINI
        assert rows[0].total_tokens == 140

    def test_no_active_context_is_a_safe_no_op(self, db, scan):
        """A call to usage_service.record() with no active scan context
        (e.g. a script that never called context_manager.activate()) must
        not raise, and must not silently attach to the wrong scan."""
        before = db.query(LLMUsageRecord).count()
        usage_service.record(
            provider=LLMProvider.GEMINI, model="gemini-2.5-flash",
            prompt_tokens=10, completion_tokens=5, total_tokens=15,
        )
        after = db.query(LLMUsageRecord).count()
        assert after == before  # nothing was written anywhere

    def test_missing_usage_is_never_fabricated(self, db, scan):
        """When a provider genuinely reports no usage metadata (all three
        fields None), no row is created at all -- never a guessed number."""
        _record_as(
            db, scan.id, "sentinel",
            provider=LLMProvider.LOCAL, model="llama3",
            prompt_tokens=None, completion_tokens=None, total_tokens=None,
        )
        rows = db.query(LLMUsageRecord).filter(LLMUsageRecord.scan_id == scan.id).all()
        assert rows == []

    def test_partial_usage_is_recorded_as_reported_not_backfilled(self, db, scan):
        """A provider that reports a total but not the input/output split
        should leave those two columns null rather than guess a split."""
        _record_as(
            db, scan.id, "planner",
            provider=LLMProvider.GROK, model="grok-beta",
            prompt_tokens=None, completion_tokens=None, total_tokens=77,
        )
        row = db.query(LLMUsageRecord).filter(LLMUsageRecord.scan_id == scan.id).one()
        assert row.prompt_tokens is None
        assert row.completion_tokens is None
        assert row.total_tokens == 77


class TestUsageAggregation:
    def test_aggregates_multiple_calls_multiple_models_multiple_agents(self, db, scan):
        _record_as(db, scan.id, "planner", provider=LLMProvider.GEMINI, model="gemini-2.5-flash",
                   prompt_tokens=200, completion_tokens=50, total_tokens=250)
        _record_as(db, scan.id, "prompt_injection_specialist", provider=LLMProvider.GEMINI, model="gemini-2.5-flash",
                   prompt_tokens=120, completion_tokens=40, total_tokens=160)
        _record_as(db, scan.id, "prompt_injection_specialist", provider=LLMProvider.LOCAL, model="llama3",
                   prompt_tokens=80, completion_tokens=20, total_tokens=100)
        _record_as(db, scan.id, "sentinel", provider=LLMProvider.GROK, model="grok-beta",
                   prompt_tokens=60, completion_tokens=15, total_tokens=75)

        summary = usage_service.summarize(db, scan.id)

        assert summary["available"] is True
        assert summary["totals"] == {
            "prompt_tokens": 460, "completion_tokens": 125, "total_tokens": 585, "call_count": 4,
        }
        assert summary["by_model"]["gemini:gemini-2.5-flash"]["call_count"] == 2
        assert summary["by_model"]["gemini:gemini-2.5-flash"]["total_tokens"] == 410
        assert summary["by_model"]["local:llama3"]["total_tokens"] == 100
        assert summary["by_model"]["grok:grok-beta"]["total_tokens"] == 75
        assert summary["by_agent"]["prompt_injection_specialist"]["call_count"] == 2
        assert summary["by_agent"]["planner"]["total_tokens"] == 250
        assert summary["by_agent"]["sentinel"]["total_tokens"] == 75

    def test_calls_not_yet_tagged_to_a_specific_agent_fall_under_swarm(self, db, scan):
        """context_manager.activate() defaults agent_type to "swarm" for
        the whole scan until a specific agent calls set_agent() (see
        BaseAgent.run()) -- so a call made without that (e.g. before any
        agent's turn) is correctly grouped under "swarm", not dropped."""
        token = context_manager.activate(db, scan.id)
        try:
            usage_service.record(provider=LLMProvider.GEMINI, model="gemini-2.5-flash",
                                  prompt_tokens=10, completion_tokens=5, total_tokens=15)
        finally:
            context_manager.clear(token)

        summary = usage_service.summarize(db, scan.id)
        assert summary["by_agent"]["swarm"]["total_tokens"] == 15

    def test_a_row_with_no_agent_type_at_all_falls_under_unattributed(self, db, scan):
        """Defensive fallback in summarize() itself, independent of
        context_manager's "swarm" default -- covers a row written with
        agent_type left NULL by any future direct caller."""
        db.add(LLMUsageRecord(
            id=uuid.uuid4(), scan_id=scan.id, agent_type=None,
            provider=LLMProvider.GEMINI, model="gemini-2.5-flash",
            prompt_tokens=1, completion_tokens=1, total_tokens=2,
        ))
        db.commit()
        summary = usage_service.summarize(db, scan.id)
        assert summary["by_agent"]["unattributed"]["total_tokens"] == 2

    def test_no_usage_for_scan_reports_unavailable_not_zeroed_fake_data(self, db, scan):
        summary = usage_service.summarize(db, scan.id)
        assert summary["available"] is False
        assert summary["totals"]["call_count"] == 0

    def test_usage_from_a_different_scan_is_not_mixed_in(self, db, scan):
        other_target = TargetProfile(id=uuid.uuid4(), name="other", endpoint_url="http://y", declared_tools={}, permission_map={})
        db.add(other_target)
        db.commit()
        other_scan = ScanRun(id=uuid.uuid4(), target_id=other_target.id)
        db.add(other_scan)
        db.commit()
        try:
            _record_as(db, scan.id, "planner", provider=LLMProvider.GEMINI, model="gemini-2.5-flash",
                       prompt_tokens=10, completion_tokens=5, total_tokens=15)
            _record_as(db, other_scan.id, "planner", provider=LLMProvider.GEMINI, model="gemini-2.5-flash",
                       prompt_tokens=999, completion_tokens=999, total_tokens=1998)

            summary = usage_service.summarize(db, scan.id)
            assert summary["totals"]["total_tokens"] == 15
        finally:
            db.rollback()
            obj = db.get(ScanRun, other_scan.id)
            if obj:
                db.delete(obj)
                db.commit()
            tgt = db.get(TargetProfile, other_target.id)
            if tgt:
                db.delete(tgt)
                db.commit()


class TestAgentLabelWiring:
    """Regression: every existing agent class must still resolve a real
    AGENT_LABEL, so BaseAgent.run()'s tagging (added this phase) never
    silently falls back to a raw Python class name for an agent that's
    supposed to have a proper label."""

    def test_every_agent_class_declares_its_label(self):
        from app.agents.planner import PlannerAgent
        from app.agents.sentinel import SentinelAgent
        from app.agents.remediation import RemediationAgent
        from app.agents.specialists.prompt_injection import PromptInjectionSpecialist
        from app.agents.specialists.jailbreak import JailbreakSpecialist
        from app.agents.specialists.tool_abuse import ToolAbuseSpecialist
        from app.agents.specialists.data_exfiltration import DataExfiltrationSpecialist
        from app.agents.specialists.privilege_escalation import PrivilegeEscalationSpecialist

        expected = {
            PlannerAgent: "planner",
            SentinelAgent: "sentinel",
            RemediationAgent: "remediation",
            PromptInjectionSpecialist: "prompt_injection_specialist",
            JailbreakSpecialist: "jailbreak_specialist",
            ToolAbuseSpecialist: "tool_abuse_specialist",
            DataExfiltrationSpecialist: "data_exfiltration_specialist",
            PrivilegeEscalationSpecialist: "privilege_escalation_specialist",
        }
        for cls, label in expected.items():
            assert cls.AGENT_LABEL == label, f"{cls.__name__}.AGENT_LABEL should be {label!r}"

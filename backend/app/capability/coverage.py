"""
Coverage engine (spec section 22): tracks which parts of the discovered
capability surface have actually been exercised by a scan, so the planner
and the UI can prioritize meaningful untested ground instead of re-testing
the same operations every run.

Deterministic, no LLM call. Coverage is derived from two real signals
already produced elsewhere in the pipeline:
  - CapabilityFrame.observed (did runtime observation see this tool called)
  - AttackLog rows for the scan (which specialist actually ran, and whether
    Sentinel confirmed a violation)

This intentionally does not claim per-capability pass/fail precision that
the data doesn't support -- AttackLog is keyed by specialist/owasp_category,
not by capability_id, so path/hypothesis coverage is expressed at the
specialist-family granularity, which is what's actually verifiable today.
"""
from __future__ import annotations

from app.capability.enums import CoverageState, SecuritySpecialist
from app.capability.models import AttackHypothesis, AttackPath, CapabilityFrame


def _specialist_state(specialist_value: str, attack_logs: list) -> CoverageState:
    # SecuritySpecialist enum values ("tool_abuse") don't match AgentType
    # enum values ("tool_abuse_specialist") -- AgentType is the specialist
    # registry key used on AttackLog rows. Bridge the two naming schemes.
    agent_type_value = f"{specialist_value}_specialist"
    matching = [
        log for log in (attack_logs or [])
        if getattr(getattr(log, "agent_type", None), "value", getattr(log, "agent_type", None)) == agent_type_value
    ]
    if not matching:
        return CoverageState.NOT_TESTED
    if any(getattr(log, "succeeded", False) for log in matching):
        return CoverageState.PASSED  # target held under this specialist... except one attempt succeeded
    return CoverageState.TESTED


def compute_coverage(
    frames: list[CapabilityFrame],
    attack_paths: list[AttackPath],
    hypotheses: list[AttackHypothesis],
    attack_logs: list | None = None,
) -> dict:
    attack_logs = attack_logs or []

    operation_coverage: dict[str, str] = {}
    for f in frames:
        key = f.operation.value
        state = CoverageState.TESTED if f.observed else CoverageState.NOT_TESTED
        # never downgrade an already-tested operation because another
        # capability with the same operation happens to be untested
        if operation_coverage.get(key) != CoverageState.TESTED.value:
            operation_coverage[key] = state.value

    specialist_coverage: dict[str, str] = {}
    for spec in SecuritySpecialist:
        specialist_coverage[spec.value] = _specialist_state(spec.value, attack_logs).value

    path_coverage: list[dict] = []
    for path in attack_paths:
        involved_specialists: set[str] = set()
        for h in hypotheses:
            if h.attack_path_id == path.path_id:
                involved_specialists.update(s.value for s in h.required_specialists)
        if not involved_specialists:
            path_coverage.append({"path_id": path.path_id, "state": CoverageState.NOT_APPLICABLE.value, "specialists": []})
            continue
        states = {specialist_coverage.get(s, CoverageState.NOT_TESTED.value) for s in involved_specialists}
        if states & {CoverageState.PASSED.value}:
            state = CoverageState.PASSED.value
        elif states == {CoverageState.TESTED.value}:
            state = CoverageState.TESTED.value
        elif CoverageState.NOT_TESTED.value in states:
            state = CoverageState.NOT_TESTED.value if len(states) == 1 else CoverageState.TESTED.value
        else:
            state = CoverageState.NOT_TESTED.value
        path_coverage.append({"path_id": path.path_id, "state": state, "specialists": sorted(involved_specialists)})

    tested_ops = sum(1 for v in operation_coverage.values() if v != CoverageState.NOT_TESTED.value)
    tested_paths = sum(1 for p in path_coverage if p["state"] not in (CoverageState.NOT_TESTED.value, CoverageState.NOT_APPLICABLE.value))
    tested_specialists = sum(1 for v in specialist_coverage.values() if v != CoverageState.NOT_TESTED.value)

    total_ops = len(operation_coverage) or 1
    total_paths = len(path_coverage) or 1
    total_specialists = len(specialist_coverage) or 1

    return {
        "operations": operation_coverage,
        "specialists": specialist_coverage,
        "attack_paths": path_coverage,
        "summary": {
            "operation_coverage_pct": round(100 * tested_ops / total_ops, 1),
            "path_coverage_pct": round(100 * tested_paths / total_paths, 1),
            "specialist_coverage_pct": round(100 * tested_specialists / total_specialists, 1),
            "untested_high_priority_paths": [
                p["path_id"] for p in path_coverage
                if p["state"] == CoverageState.NOT_TESTED.value
            ][:10],
        },
    }

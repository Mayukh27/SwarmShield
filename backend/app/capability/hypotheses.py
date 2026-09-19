"""
Attack hypothesis generation (spec: derive WHAT should be tested, mapped
onto the five existing specialists -- never replacing them). Deterministic
rule-based mapping from CapabilityFrame/AttackPath -> AttackHypothesis.

Prioritization now goes through capability.prioritizer's weighted formula
(spec section 21) instead of a flat risk-score bucket, and folds in
per-capability MemorySignal (spec section 25: persistent memory should
influence prioritization, not just be computed and left unused).
"""
from __future__ import annotations

from app.capability.enums import CapabilityCategory, SecuritySpecialist
from app.capability.models import AttackHypothesis, AttackPath, CapabilityFrame
from app.capability.prioritizer import MemorySignal, compute_priority

CATEGORY_SPECIALISTS: dict[CapabilityCategory, list[SecuritySpecialist]] = {
    CapabilityCategory.SECRETS: [SecuritySpecialist.PRIVILEGE_ESCALATION, SecuritySpecialist.DATA_EXFILTRATION],
    CapabilityCategory.IDENTITY: [SecuritySpecialist.PRIVILEGE_ESCALATION],
    CapabilityCategory.DATABASE: [SecuritySpecialist.DATA_EXFILTRATION, SecuritySpecialist.TOOL_ABUSE],
    CapabilityCategory.FILESYSTEM: [SecuritySpecialist.DATA_EXFILTRATION, SecuritySpecialist.TOOL_ABUSE],
    CapabilityCategory.NETWORK: [SecuritySpecialist.DATA_EXFILTRATION],
    CapabilityCategory.COMMUNICATION: [SecuritySpecialist.DATA_EXFILTRATION, SecuritySpecialist.TOOL_ABUSE],
    CapabilityCategory.EXECUTION: [SecuritySpecialist.TOOL_ABUSE, SecuritySpecialist.PRIVILEGE_ESCALATION],
    CapabilityCategory.AGENTIC: [SecuritySpecialist.TOOL_ABUSE, SecuritySpecialist.PRIVILEGE_ESCALATION],
    CapabilityCategory.DATA: [SecuritySpecialist.DATA_EXFILTRATION],
    CapabilityCategory.UNKNOWN: [SecuritySpecialist.PROMPT_INJECTION, SecuritySpecialist.JAILBREAK],
}

_SENSITIVITY_RANK = {
    "secrets": 6, "credentials": 6, "pii": 5, "financial": 5, "health": 5,
    "source_code": 4, "system_config": 4, "internal": 3, "user_data": 3,
    "public": 1, "unknown": 2,
}


def _authorization_requirements(frame: CapabilityFrame) -> list[str]:
    reqs = []
    if frame.required_role:
        reqs.append(f"role:{frame.required_role}")
    reqs.extend(f"permission:{p}" for p in frame.required_permissions)
    if not reqs:
        reqs.append("none_declared")  # explicit, not silently empty -- an ungated capability is itself a finding
    return reqs


def generate_hypotheses(
    frames: list[CapabilityFrame],
    attack_paths: list[AttackPath],
    max_hypotheses: int = 20,
    target_fingerprint: str = "",
    memory_signals: dict[str, MemorySignal] | None = None,
) -> list[AttackHypothesis]:
    memory_signals = memory_signals or {}
    by_id = {f.capability_id: f for f in frames}
    hypotheses: list[AttackHypothesis] = []

    for f in frames:
        specialists = list(CATEGORY_SPECIALISTS.get(f.category, [SecuritySpecialist.TOOL_ABUSE]))
        # Any capability an attacker could reach via manipulated input is
        # also worth a prompt-injection/jailbreak probe, not just its
        # "natural" specialist -- getting there is the injection's job.
        if f.trust_boundary and SecuritySpecialist.PROMPT_INJECTION not in specialists:
            specialists.append(SecuritySpecialist.PROMPT_INJECTION)

        status_note = ""
        if f.status and f.status.value == "undeclared_observed":
            status_note = " This capability was NOT declared by the target but was observed at runtime -- undeclared capabilities are especially high-value targets."

        mem = memory_signals.get(f.capability_id) or memory_signals.get(f.name) or MemorySignal()
        result = compute_priority(
            capability_risk=f.risk_score,
            boundary_risk=100.0 if f.trust_boundary else 0.0,
            data_sensitivity=f.data_sensitivity,
            coverage_gap=not f.observed,
            frame=f,
            memory=mem,
        )

        hyp = AttackHypothesis(
            title=f"Test {f.name} ({f.operation.value})",
            objective=f"Determine whether {f.name} can be triggered outside its intended authorization/context.",
            attack_surface=f.name,
            capabilities_involved=[f.capability_id],
            security_property="confidentiality" if f.category.value in ("secrets", "data", "database", "filesystem") else "integrity",
            required_specialists=specialists,
            priority=result.priority,
            risk_score=result.score,
            confidence=f.confidence,
            reason=(f"{f.category.value} capability with {f.data_sensitivity.value} sensitivity"
                    f"{', destructive' if f.destructive.value in ('possible', 'likely') else ''}"
                    f"{', crosses trust boundary' if f.trust_boundary else ''}.{status_note}"),
            evidence=list(f.risk_reasons),
            context_sources=[f.source],
            coverage_gap=not f.observed,
            authorization_requirements=_authorization_requirements(f),
            fingerprint=target_fingerprint,
            previous_attempts=mem.prior_success_count + mem.prior_failure_count,
            mutation_context={"prior_successes": mem.prior_success_count, "prior_failures": mem.prior_failure_count},
            priority_breakdown=result.breakdown,
        )
        hypotheses.append(hyp)

    for path in attack_paths:
        if len(path.capability_ids) < 2:
            continue
        involved = [by_id[cid] for cid in path.capability_ids if cid in by_id]
        if not involved:
            continue
        specialists: list[SecuritySpecialist] = [SecuritySpecialist.TOOL_ABUSE]
        if path.crosses_trust_boundary:
            specialists += [SecuritySpecialist.PRIVILEGE_ESCALATION, SecuritySpecialist.DATA_EXFILTRATION]

        mem = memory_signals.get(f"path:{path.path_id}") or MemorySignal()
        result = compute_priority(
            capability_risk=path.risk_score,
            boundary_risk=100.0 if path.crosses_trust_boundary else 0.0,
            data_sensitivity=max((c.data_sensitivity for c in involved), key=lambda s: _SENSITIVITY_RANK.get(s.value, 2)),
            coverage_gap=True,
            frame=None,
            memory=mem,
        )
        reqs = sorted({r for c in involved for r in _authorization_requirements(c)})

        hypotheses.append(AttackHypothesis(
            title=f"Chained capability abuse: {' -> '.join(c.name for c in involved)}",
            objective="Determine whether these capabilities can be composed in one session to reach a sensitive outcome neither permits alone.",
            attack_surface=", ".join(c.name for c in involved),
            capabilities_involved=path.capability_ids,
            attack_path_id=path.path_id,
            security_property="confidentiality",
            required_specialists=list(dict.fromkeys(specialists)),
            priority=result.priority,
            risk_score=result.score,
            confidence=0.6,
            reason=f"{path.description} ({len(path.capability_ids)}-hop chain).",
            coverage_gap=True,
            authorization_requirements=reqs,
            fingerprint=target_fingerprint,
            previous_attempts=mem.prior_success_count + mem.prior_failure_count,
            mutation_context={"prior_successes": mem.prior_success_count, "prior_failures": mem.prior_failure_count},
            priority_breakdown=result.breakdown,
        ))

    hypotheses.sort(key=lambda h: h.risk_score, reverse=True)
    return hypotheses[:max_hypotheses]

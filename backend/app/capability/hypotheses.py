"""
Attack hypothesis generation (spec: derive WHAT should be tested, mapped
onto the five existing specialists -- never replacing them). Deterministic
rule-based mapping from CapabilityFrame/AttackPath -> AttackHypothesis.
"""
from __future__ import annotations

from app.capability.enums import CapabilityCategory, HypothesisPriority, SecuritySpecialist
from app.capability.models import AttackHypothesis, AttackPath, CapabilityFrame

_CATEGORY_SPECIALISTS: dict[CapabilityCategory, list[SecuritySpecialist]] = {
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


def _priority_from_risk(risk_score: float) -> HypothesisPriority:
    if risk_score >= 75:
        return HypothesisPriority.CRITICAL
    if risk_score >= 50:
        return HypothesisPriority.HIGH
    if risk_score >= 25:
        return HypothesisPriority.MEDIUM
    return HypothesisPriority.LOW


def generate_hypotheses(frames: list[CapabilityFrame], attack_paths: list[AttackPath], max_hypotheses: int = 20) -> list[AttackHypothesis]:
    by_id = {f.capability_id: f for f in frames}
    hypotheses: list[AttackHypothesis] = []

    for f in frames:
        specialists = list(_CATEGORY_SPECIALISTS.get(f.category, [SecuritySpecialist.TOOL_ABUSE]))
        # Any capability an attacker could reach via manipulated input is
        # also worth a prompt-injection/jailbreak probe, not just its
        # "natural" specialist -- getting there is the injection's job.
        if f.trust_boundary and SecuritySpecialist.PROMPT_INJECTION not in specialists:
            specialists.append(SecuritySpecialist.PROMPT_INJECTION)

        status_note = ""
        risk = f.risk_score
        if f.status and f.status.value == "undeclared_observed":
            status_note = " This capability was NOT declared by the target but was observed at runtime -- undeclared capabilities are especially high-value targets."
            risk = min(100.0, risk + 20)

        hypotheses.append(AttackHypothesis(
            title=f"Test {f.name} ({f.operation.value})",
            objective=f"Determine whether {f.name} can be triggered outside its intended authorization/context.",
            attack_surface=f.name,
            capabilities_involved=[f.capability_id],
            security_property="confidentiality" if f.category.value in ("secrets", "data", "database", "filesystem") else "integrity",
            required_specialists=specialists,
            priority=_priority_from_risk(risk),
            risk_score=risk,
            confidence=f.confidence,
            reason=(f"{f.category.value} capability with {f.data_sensitivity.value} sensitivity"
                    f"{', destructive' if f.destructive.value in ('possible', 'likely') else ''}"
                    f"{', crosses trust boundary' if f.trust_boundary else ''}.{status_note}"),
            evidence=list(f.risk_reasons),
            context_sources=[f.source],
            coverage_gap=not f.observed,
        ))

    for path in attack_paths:
        if len(path.capability_ids) < 2:
            continue
        involved = [by_id[cid] for cid in path.capability_ids if cid in by_id]
        if not involved:
            continue
        specialists: list[SecuritySpecialist] = [SecuritySpecialist.TOOL_ABUSE]
        if path.crosses_trust_boundary:
            specialists += [SecuritySpecialist.PRIVILEGE_ESCALATION, SecuritySpecialist.DATA_EXFILTRATION]

        hypotheses.append(AttackHypothesis(
            title=f"Chained capability abuse: {' -> '.join(c.name for c in involved)}",
            objective="Determine whether these capabilities can be composed in one session to reach a sensitive outcome neither permits alone.",
            attack_surface=", ".join(c.name for c in involved),
            capabilities_involved=path.capability_ids,
            attack_path_id=path.path_id,
            security_property="confidentiality",
            required_specialists=list(dict.fromkeys(specialists)),
            priority=_priority_from_risk(path.risk_score),
            risk_score=path.risk_score,
            confidence=0.6,
            reason=path.description,
            coverage_gap=True,
        ))

    hypotheses.sort(key=lambda h: h.risk_score, reverse=True)
    return hypotheses[:max_hypotheses]

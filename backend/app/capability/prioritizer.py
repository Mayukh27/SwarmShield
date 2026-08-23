"""
Attack prioritization (spec section 21): replaces the flat risk-score
bucket that hypotheses.py used previously with the actual weighted formula
the spec asks for --

    priority =
        capability_risk
        + boundary_risk
        + authorization_risk
        + data_sensitivity
        - + historical_signal
        + novelty
        + coverage_gap
        - previous_failure_penalty

Every input is normalized to 0-100 before weighting so the configured
weights (app.core.config) are the only thing that changes the outcome --
no magic numbers buried in this file. This module has no DB dependency:
callers (capability_service) are responsible for turning memory/RAG
lookups into the plain `MemorySignal` values below, so this stays exactly
as unit-testable as the rest of the pure-Python capability pipeline.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.capability.enums import DataSensitivity, DestructiveRisk, HypothesisPriority
from app.capability.models import CapabilityFrame
from app.core.config import settings

_HIGH_SENSITIVITY = {
    DataSensitivity.PII, DataSensitivity.CREDENTIALS, DataSensitivity.SECRETS,
    DataSensitivity.FINANCIAL, DataSensitivity.HEALTH, DataSensitivity.SOURCE_CODE,
    DataSensitivity.SYSTEM_CONFIG,
}
_MEDIUM_SENSITIVITY = {DataSensitivity.INTERNAL, DataSensitivity.USER_DATA}


@dataclass
class MemorySignal:
    """What capability_service learned from persistent memory (spec
    section 25) about this specific capability/path for this specific
    target fingerprint, distilled to the three numbers the formula needs.
    Defaults are all "we have no history" -- a brand-new target scores
    novelty=100 and historical_signal=0, exactly as it should."""
    previous_attempts: int = 0
    prior_success_count: int = 0
    prior_failure_count: int = 0
    novel: bool = True


@dataclass
class PriorityResult:
    priority: HypothesisPriority
    score: float
    breakdown: dict = field(default_factory=dict)


def _data_sensitivity_score(sensitivity: DataSensitivity) -> float:
    if sensitivity in _HIGH_SENSITIVITY:
        return 100.0
    if sensitivity in _MEDIUM_SENSITIVITY:
        return 55.0
    if sensitivity == DataSensitivity.PUBLIC:
        return 10.0
    return 30.0  # UNKNOWN -- not zero, since "we don't know what this touches" is itself a reason to look


def _authorization_risk_score(frame: CapabilityFrame | None) -> float:
    if frame is None:
        return 0.0
    score = 0.0
    if frame.required_role in (None, "", "user", "public"):
        score += 20.0  # weakly-gated or ungated capability
    if frame.destructive in (DestructiveRisk.LIKELY, DestructiveRisk.POSSIBLE) and not frame.required_role:
        score += 40.0  # destructive AND no declared role requirement is the classic authorization gap
    if frame.status is not None and frame.status.value == "undeclared_observed":
        score += 40.0  # capability nobody declared a policy for at all
    return min(100.0, score)


def _historical_signal_score(mem: MemorySignal) -> float:
    """Prior *successful* attacks against a similar capability on this
    target/fingerprint are a strong positive signal -- it means this
    class of capability has a demonstrated weak spot worth revisiting,
    e.g. after a partial remediation."""
    if mem.prior_success_count <= 0:
        return 0.0
    return min(100.0, 40.0 + 20.0 * mem.prior_success_count)


def _novelty_score(mem: MemorySignal) -> float:
    return 100.0 if mem.novel else 0.0


def _coverage_gap_score(coverage_gap: bool) -> float:
    return 100.0 if coverage_gap else 0.0


def _previous_failure_penalty(mem: MemorySignal) -> float:
    """Repeated *failed* attempts at the exact same capability/strategy on
    this target are a signal this avenue is a dead end -- discourage
    (never fully block) re-testing it ahead of untested ground. Capped so
    it can reduce but never zero-out a high-inherent-risk hypothesis."""
    if mem.prior_failure_count <= 0:
        return 0.0
    return min(70.0, 15.0 * mem.prior_failure_count)


def _priority_from_score(score: float) -> HypothesisPriority:
    if score >= 70:
        return HypothesisPriority.CRITICAL
    if score >= 50:
        return HypothesisPriority.HIGH
    if score >= 28:
        return HypothesisPriority.MEDIUM
    return HypothesisPriority.LOW


def compute_priority(
    *,
    capability_risk: float,
    boundary_risk: float,
    data_sensitivity: DataSensitivity,
    coverage_gap: bool,
    frame: CapabilityFrame | None = None,
    memory: MemorySignal | None = None,
) -> PriorityResult:
    """Core weighted formula. `capability_risk` and `boundary_risk` are
    passed in already 0-100 (they come from the classifier / attack-path
    combination logic, which has the domain context this module doesn't
    need to re-derive); everything else is computed here."""
    memory = memory or MemorySignal()

    components = {
        "capability_risk": round(max(0.0, min(100.0, capability_risk)), 1),
        "boundary_risk": round(max(0.0, min(100.0, boundary_risk)), 1),
        "authorization_risk": round(_authorization_risk_score(frame), 1),
        "data_sensitivity": round(_data_sensitivity_score(data_sensitivity), 1),
        "historical_signal": round(_historical_signal_score(memory), 1),
        "novelty": round(_novelty_score(memory), 1),
        "coverage_gap": round(_coverage_gap_score(coverage_gap), 1),
        "previous_failure_penalty": round(_previous_failure_penalty(memory), 1),
    }

    weighted = (
        components["capability_risk"] * settings.CAPABILITY_WEIGHT_CAPABILITY_RISK
        + components["boundary_risk"] * settings.CAPABILITY_WEIGHT_BOUNDARY_RISK
        + components["authorization_risk"] * settings.CAPABILITY_WEIGHT_AUTHORIZATION_RISK
        + components["data_sensitivity"] * settings.CAPABILITY_WEIGHT_DATA_SENSITIVITY
        + components["historical_signal"] * settings.CAPABILITY_WEIGHT_HISTORICAL_SIGNAL
        + components["novelty"] * settings.CAPABILITY_WEIGHT_NOVELTY
        + components["coverage_gap"] * settings.CAPABILITY_WEIGHT_COVERAGE_GAP
        - components["previous_failure_penalty"] * settings.CAPABILITY_WEIGHT_PREVIOUS_FAILURE_PENALTY
    )
    weighted = round(max(0.0, min(100.0, weighted)), 1)

    return PriorityResult(priority=_priority_from_score(weighted), score=weighted, breakdown=components)

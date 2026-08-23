"""
In-memory dataclasses for the Capability Intelligence Engine (spec section 4).

These are deliberately NOT SQLAlchemy models. Analysis (extraction ->
classification -> graph -> hypotheses) is a pure, cacheable, testable
pipeline over plain Python objects; persistence is a separate concern
handled by app/models/capability.py (Phase 39), which stores the
serialized result. Keeping the two separate is what makes
CapabilityIntelligenceService.analyze() safe to unit-test without a DB
and safe to run speculatively without committing anything (spec section
30: "never automatically ... never bypass authorization").
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime

from app.capability.enums import (
    CapabilityCategory,
    CapabilityOperation,
    CapabilityStatus,
    DataSensitivity,
    DestructiveRisk,
    GraphEdgeType,
    GraphNodeType,
    HypothesisPriority,
    ResourceType,
    SecuritySpecialist,
    TrustLevel,
)


@dataclass
class ToolFrame:
    """Raw, source-faithful representation of one declared or observed
    tool, before classification (spec section 6)."""
    tool_name: str
    tool_description: str = ""
    input_schema: dict = field(default_factory=dict)
    output_schema: dict = field(default_factory=dict)
    declared_permissions: list[str] = field(default_factory=list)
    source: str = "declared_tools"          # e.g. "declared_tools", "runtime_observation"
    raw: dict = field(default_factory=dict)  # original source dict, for traceability


@dataclass
class CapabilityFrame:
    """The canonical normalized capability record. Every discovered
    capability -- declared, observed, or inferred -- is normalized into
    this shape. Field set matches spec section 4 exactly."""
    capability_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    display_name: str = ""
    category: CapabilityCategory = CapabilityCategory.UNKNOWN
    operation: CapabilityOperation = CapabilityOperation.UNKNOWN_CAPABILITY
    source: str = "declared_tools"
    declared: bool = False
    observed: bool = False
    inferred: bool = False
    confidence: float = 0.0

    tool_name: str = ""
    tool_description: str = ""
    input_schema: dict = field(default_factory=dict)
    output_schema: dict = field(default_factory=dict)

    resources: list[ResourceType] = field(default_factory=list)
    data_types: list[str] = field(default_factory=list)
    data_sensitivity: DataSensitivity = DataSensitivity.UNKNOWN

    authorization: str | None = None
    required_role: str | None = None
    required_permissions: list[str] = field(default_factory=list)

    trust_boundary: bool = False
    source_trust: TrustLevel = TrustLevel.UNKNOWN
    destination_trust: TrustLevel = TrustLevel.UNKNOWN

    side_effect: bool = False
    reversible: bool | None = None
    destructive: DestructiveRisk = DestructiveRisk.UNKNOWN
    external_effect: bool = False

    network_access: bool = False
    filesystem_access: bool = False
    database_access: bool = False
    secret_access: bool = False
    code_execution: bool = False
    identity_access: bool = False

    parent_capability: str | None = None
    related_capabilities: list[str] = field(default_factory=list)

    first_observed: datetime | None = None
    last_observed: datetime | None = None
    observation_count: int = 0

    risk_score: float = 0.0
    risk_reasons: list[str] = field(default_factory=list)

    status: CapabilityStatus = CapabilityStatus.DECLARED
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = {}
        for k, v in self.__dict__.items():
            if hasattr(v, "value"):  # enum
                d[k] = v.value
            elif isinstance(v, list) and v and hasattr(v[0], "value"):
                d[k] = [i.value for i in v]
            elif isinstance(v, datetime):
                d[k] = v.isoformat()
            else:
                d[k] = v
        return d


@dataclass
class GraphNode:
    node_id: str
    node_type: GraphNodeType
    label: str
    metadata: dict = field(default_factory=dict)


@dataclass
class GraphEdge:
    source_id: str
    target_id: str
    edge_type: GraphEdgeType
    metadata: dict = field(default_factory=dict)


@dataclass
class CapabilityGraph:
    nodes: list[GraphNode] = field(default_factory=list)
    edges: list[GraphEdge] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "nodes": [{"id": n.node_id, "type": n.node_type.value, "label": n.label, "metadata": n.metadata} for n in self.nodes],
            "edges": [{"source": e.source_id, "target": e.target_id, "type": e.edge_type.value, "metadata": e.metadata} for e in self.edges],
        }


@dataclass
class AttackPath:
    path_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    capability_ids: list[str] = field(default_factory=list)
    operations: list[CapabilityOperation] = field(default_factory=list)
    crosses_trust_boundary: bool = False
    description: str = ""
    risk_score: float = 0.0

    def to_dict(self) -> dict:
        return {
            "path_id": self.path_id,
            "capability_ids": self.capability_ids,
            "operations": [o.value for o in self.operations],
            "crosses_trust_boundary": self.crosses_trust_boundary,
            "description": self.description,
            "risk_score": self.risk_score,
        }


@dataclass
class AttackHypothesis:
    hypothesis_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    objective: str = ""
    attack_surface: str = ""
    capabilities_involved: list[str] = field(default_factory=list)
    attack_path_id: str | None = None
    security_property: str = ""
    required_specialists: list[SecuritySpecialist] = field(default_factory=list)
    priority: HypothesisPriority = HypothesisPriority.MEDIUM
    risk_score: float = 0.0
    confidence: float = 0.0
    reason: str = ""
    evidence: list[str] = field(default_factory=list)
    context_sources: list[str] = field(default_factory=list)
    previous_attempts: int = 0
    mutation_context: dict = field(default_factory=dict)
    coverage_gap: bool = True
    authorization_requirements: list[str] = field(default_factory=list)
    fingerprint: str = ""
    priority_breakdown: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "hypothesis_id": self.hypothesis_id,
            "title": self.title,
            "objective": self.objective,
            "attack_surface": self.attack_surface,
            "capabilities_involved": self.capabilities_involved,
            "attack_path_id": self.attack_path_id,
            "security_property": self.security_property,
            "required_specialists": [s.value for s in self.required_specialists],
            "priority": self.priority.value,
            "risk_score": self.risk_score,
            "confidence": self.confidence,
            "reason": self.reason,
            "evidence": self.evidence,
            "context_sources": self.context_sources,
            "previous_attempts": self.previous_attempts,
            "mutation_context": self.mutation_context,
            "coverage_gap": self.coverage_gap,
            "authorization_requirements": self.authorization_requirements,
            "fingerprint": self.fingerprint,
            "priority_breakdown": self.priority_breakdown,
        }

"""
Persistence for the Capability Intelligence Engine (spec section 39).

The analysis pipeline itself (extractor -> classifier -> graph ->
attack_paths -> hypotheses -> coverage) stays pure/in-memory
(app/capability/models.py) so it's cheap to recompute and safe to run
speculatively. These two tables store one durable snapshot per scan so
the frontend can:
  - diff two scans of the same target (what capabilities changed)
  - let an operator mark a hypothesis approved/skipped and have that
    stick, instead of it being re-derived (and losing the decision)
    on every page load

Never store raw secrets -- `data` is the same sanitized dict already
returned by CapabilityFrame.to_dict() / AttackHypothesis.to_dict(),
which never contains credential/token values (see
app/capability/classifier.py + extractor.py redaction).
"""
import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Enum, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class HypothesisStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    SKIPPED = "skipped"


class CapabilityRecord(Base):
    """One persisted CapabilityFrame, snapshotted at the end of a scan."""
    __tablename__ = "capability_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scan_id = Column(UUID(as_uuid=True), ForeignKey("scan_runs.id"), nullable=False)
    target_id = Column(UUID(as_uuid=True), ForeignKey("target_profiles.id"), nullable=False)

    capability_id = Column(String(64), nullable=False)  # the in-memory CapabilityFrame.capability_id
    name = Column(Text, nullable=False)
    category = Column(String(64), nullable=False)
    operation = Column(String(64), nullable=False)
    status = Column(String(32), nullable=False)  # declared / declared_observed / undeclared_observed
    declared = Column(Boolean, default=False)
    observed = Column(Boolean, default=False)
    risk_score = Column(Float, default=0.0)

    data = Column(JSONB, nullable=False)  # full CapabilityFrame.to_dict()

    created_at = Column(DateTime, default=datetime.utcnow)

    scan = relationship("ScanRun")
    target = relationship("TargetProfile")


class AttackHypothesisRecord(Base):
    """One persisted AttackHypothesis, snapshotted at the end of a scan.
    `status` is the only field an operator can change after the fact
    (approve/skip) -- everything else reflects what was actually
    generated, so re-approving never silently rewrites the reasoning."""
    __tablename__ = "attack_hypothesis_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scan_id = Column(UUID(as_uuid=True), ForeignKey("scan_runs.id"), nullable=False)
    target_id = Column(UUID(as_uuid=True), ForeignKey("target_profiles.id"), nullable=False)

    hypothesis_id = Column(String(64), nullable=False)  # in-memory AttackHypothesis.hypothesis_id
    title = Column(Text, nullable=False)
    priority = Column(String(16), nullable=False)
    risk_score = Column(Float, default=0.0)
    status = Column(Enum(HypothesisStatus), nullable=False, default=HypothesisStatus.PENDING)

    data = Column(JSONB, nullable=False)  # full AttackHypothesis.to_dict()

    created_at = Column(DateTime, default=datetime.utcnow)
    decided_at = Column(DateTime, nullable=True)

    scan = relationship("ScanRun")
    target = relationship("TargetProfile")

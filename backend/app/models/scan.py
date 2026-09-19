"""
ScanRun: one execution of the swarm against a TargetProfile. Tracks overall
status and aggregate risk score. AttackLog / Vulnerability rows reference
a ScanRun via scan_id.
"""
import enum
import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Enum, Float, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class ScanStatus(str, enum.Enum):
    PENDING = "pending"
    PLANNING = "planning"          # Planner Agent mapping attack surface
    ATTACKING = "attacking"        # Attacker swarm + Sentinel feedback loop active
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ScanRun(Base):
    __tablename__ = "scan_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    target_id = Column(UUID(as_uuid=True), ForeignKey("target_profiles.id"), nullable=False)

    status = Column(Enum(ScanStatus), default=ScanStatus.PENDING, nullable=False)

    # Planner output: which attack vectors / agents were dispatched
    attack_plan = Column(JSONB, nullable=True)

    # Aggregate results
    risk_score = Column(Float, nullable=True)          # 0-100, computed at completion
    total_attempts = Column(Integer, default=0)
    successful_attacks = Column(Integer, default=0)

    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    # Risk breakdown populated by app.services.risk (severity/category weighted,
    # not just successful/total attempts) -- see risk.py.
    risk_breakdown = Column(JSONB, nullable=True)

    target = relationship("TargetProfile", back_populates="scans")
    attack_logs = relationship("AttackLog", back_populates="scan", cascade="all, delete-orphan")
    vulnerabilities = relationship("Vulnerability", back_populates="scan", cascade="all, delete-orphan")
    memory_records = relationship("MemoryRecord", back_populates="scan", cascade="all, delete-orphan")
    attack_dna_records = relationship("AttackDNARecord", back_populates="scan", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<ScanRun {self.id} status={self.status}>"

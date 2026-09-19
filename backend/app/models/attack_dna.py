"""
AttackDNARecord + ConsensusRecord: ported from Repo A's models.py. DNA
tracks the mutation lineage of a specialist's payload strategy (its
"genome") across generations within one vector; Consensus records each
agent's independent verdict on a finding so multi-agent agreement is
visible, not just the Sentinel's single verdict.
"""
import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class AttackDNARecord(Base):
    __tablename__ = "attack_dna"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scan_id = Column(UUID(as_uuid=True), ForeignKey("scan_runs.id"), nullable=False)
    vector_id = Column(String(120), nullable=False)  # groups DNA lineage per Planner vector
    # ondelete="CASCADE": self-referential FK -- without this, deleting a
    # ScanRun (or a parent generation directly) with multiple DNA
    # generations can raise a ForeignKeyViolation depending on delete
    # order, since plain SQLAlchemy ORM cascade has no ordering signal for
    # a self-referential relationship that isn't declared via
    # relationship(). Letting Postgres cascade the delete at the DB level
    # avoids that ordering problem entirely.
    parent_id = Column(UUID(as_uuid=True), ForeignKey("attack_dna.id", ondelete="CASCADE"), nullable=True)
    generation = Column(Integer, default=0)

    genome = Column(JSONB, nullable=False, default=dict)
    mutations = Column(JSONB, nullable=False, default=list)  # list of {feature, from, to, mutation_type}
    success_probability = Column(Float, nullable=False, default=0.0)
    confidence = Column(Float, nullable=False, default=0.0)

    source_attack_id = Column(UUID(as_uuid=True), ForeignKey("attack_logs.id"), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    scan = relationship("ScanRun", back_populates="attack_dna_records")

    def __repr__(self) -> str:
        return f"<AttackDNARecord vector={self.vector_id} gen={self.generation}>"


class ConsensusRecord(Base):
    __tablename__ = "finding_consensus"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vulnerability_id = Column(UUID(as_uuid=True), ForeignKey("vulnerabilities.id"), nullable=False)

    agent = Column(String(64), nullable=False)
    verdict = Column(String(48), nullable=False)  # e.g. "confirmed" | "disputed"
    confidence = Column(Float, nullable=False)
    evidence_summary = Column(Text, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)

    vulnerability = relationship("Vulnerability", back_populates="consensus_records")

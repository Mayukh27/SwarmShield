"""
MemoryRecord: cross-agent shared memory. Ported from Repo A's
`memory/manager.py` (which only had in-process dataclasses) into a real
table so memory persists across specialists/generations/scans and can
actually be queried by later agents within the same campaign -- this is
the "Shared Memory" box in the PPT workflow.
"""
import enum
import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Enum, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class MemoryType(str, enum.Enum):
    DISCOVERY = "discovery"
    SUCCESS = "success"
    FAILURE = "failure"
    TARGET_CAPABILITY = "target_capability"
    TOOL = "tool"
    VULNERABILITY = "vulnerability"
    ATTACK_PATTERN = "attack_pattern"


class MemoryRecord(Base):
    __tablename__ = "memory_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scan_id = Column(UUID(as_uuid=True), ForeignKey("scan_runs.id"), nullable=False)

    memory_type = Column(Enum(MemoryType), nullable=False)
    content = Column(Text, nullable=False)
    confidence = Column(Float, nullable=False)  # 0.0-1.0, validated in memory_service.py
    agent = Column(String(64), nullable=False)  # which specialist/sentinel wrote this
    source_attack_id = Column(UUID(as_uuid=True), ForeignKey("attack_logs.id"), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    scan = relationship("ScanRun", back_populates="memory_records")

    def __repr__(self) -> str:
        return f"<MemoryRecord {self.memory_type} agent={self.agent}>"

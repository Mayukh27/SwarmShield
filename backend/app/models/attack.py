"""
AttackLog: a single attempt by one specialist agent against the target,
plus the Sentinel's verdict on it. This is the row-level record that
powers both the live log stream and the React Flow attack chain graph
(via parent_attempt_id, forming a mutation lineage).
"""
import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class AgentType(str, enum.Enum):
    PLANNER = "planner"
    PROMPT_INJECTION = "prompt_injection_specialist"
    JAILBREAK = "jailbreak_specialist"
    TOOL_ABUSE = "tool_abuse_specialist"
    DATA_EXFILTRATION = "data_exfiltration_specialist"
    PRIVILEGE_ESCALATION = "privilege_escalation_specialist"
    SENTINEL = "sentinel"


class AttackLog(Base):
    __tablename__ = "attack_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scan_id = Column(UUID(as_uuid=True), ForeignKey("scan_runs.id"), nullable=False)

    agent_type = Column(Enum(AgentType), nullable=False)
    owasp_category = Column(Text, nullable=True)  # e.g. "LLM01: Prompt Injection"

    # Mutation lineage: if this attempt is a Sentinel-guided mutation of a
    # prior failed attempt, this points back to it. NULL = root attempt.
    parent_attempt_id = Column(UUID(as_uuid=True), ForeignKey("attack_logs.id"), nullable=True)
    generation = Column(Integer, default=0)  # 0 = first try, increments per mutation

    payload = Column(Text, nullable=False)          # the actual prompt/tool-call sent
    target_response = Column(Text, nullable=True)   # raw response from target system

    # Sentinel's assessment
    sentinel_verdict = Column(JSONB, nullable=True)
    # Example shape:
    # {
    #   "violation_detected": true,
    #   "violation_type": "data_leakage",
    #   "confidence": 0.87,
    #   "reasoning": "...",
    #   "mutation_hint": "try encoding the payload in base64"
    # }
    succeeded = Column(Boolean, default=False, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)

    scan = relationship("ScanRun", back_populates="attack_logs")
    children = relationship("AttackLog", backref="parent", remote_side=[id])
    vulnerability = relationship("Vulnerability", back_populates="source_attack", uselist=False)

    def __repr__(self) -> str:
        return f"<AttackLog {self.agent_type} succeeded={self.succeeded}>"

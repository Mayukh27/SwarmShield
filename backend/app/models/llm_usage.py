"""
LLMUsageRecord: one row per real LLM provider call made during a scan.

Token counts come straight from the provider's own response metadata
(for Ollama: ``prompt_eval_count`` / ``eval_count``). They are NEVER
estimated from character/word counts. A counter the provider did not report
is stored as NULL ("unavailable"), not 0 and not a guess.
"""
import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class LLMUsageRecord(Base):
    __tablename__ = "llm_usage_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scan_id = Column(
        UUID(as_uuid=True),
        ForeignKey("scan_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Which agent made the call (e.g. "planner", "sentinel",
    # "prompt_injection_specialist"); "swarm" when the call was made outside
    # any specific agent.
    agent_type = Column(String(64), nullable=True)

    provider = Column(String(32), nullable=False)   # e.g. "ollama"
    model = Column(String(128), nullable=False)     # e.g. "qwen2.5:3b"

    # Real provider counters. NULL = the provider did not report it.
    input_tokens = Column(Integer, nullable=True)    # Ollama: prompt_eval_count
    output_tokens = Column(Integer, nullable=True)   # Ollama: eval_count
    total_tokens = Column(Integer, nullable=True)    # sum of the counters actually reported

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    scan = relationship("ScanRun", back_populates="llm_usage_records")

    def __repr__(self) -> str:
        return (
            f"<LLMUsageRecord scan={self.scan_id} {self.provider}/{self.model} "
            f"in={self.input_tokens} out={self.output_tokens}>"
        )

import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel

from app.models.scan import ScanStatus


class ScanCreate(BaseModel):
    target_id: uuid.UUID
    # Optional override of which attacker specialists to run; empty = all of them
    enabled_vectors: Optional[list[str]] = None


class ScanOut(BaseModel):
    id: uuid.UUID
    target_id: uuid.UUID
    status: ScanStatus
    attack_plan: Optional[dict[str, Any]]
    risk_score: Optional[float]
    risk_breakdown: Optional[dict[str, Any]]
    total_attempts: int
    successful_attacks: int
    started_at: datetime
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True


class UsageByModel(BaseModel):
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    llm_calls: int


class UsageByAgent(BaseModel):
    agent_type: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    llm_calls: int


class ScanUsageOut(BaseModel):
    """Real LLM token usage recorded for one scan (never estimated)."""
    scan_id: uuid.UUID
    input_tokens: int
    output_tokens: int
    total_tokens: int
    llm_calls: int
    # Calls where the provider reported only one of input/output; the totals
    # are then a lower bound.
    partial_calls: int = 0
    provider: Optional[str] = None
    model: Optional[str] = None
    by_model: list[UsageByModel] = []
    by_agent: list[UsageByAgent] = []

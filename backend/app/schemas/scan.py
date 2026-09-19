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

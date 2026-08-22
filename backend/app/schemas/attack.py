import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel

from app.models.attack import AgentType


class AttackLogOut(BaseModel):
    id: uuid.UUID
    scan_id: uuid.UUID
    agent_type: AgentType
    owasp_category: Optional[str]
    parent_attempt_id: Optional[uuid.UUID]
    generation: int
    payload: str
    target_response: Optional[str]
    sentinel_verdict: Optional[dict[str, Any]]
    succeeded: bool
    created_at: datetime

    class Config:
        from_attributes = True


class AgentLogEvent(BaseModel):
    """Shape streamed over SSE to the frontend log console / graph."""
    event_type: str  # "agent_action" | "sentinel_verdict" | "scan_status" | "vulnerability_found"
    agent_type: Optional[str] = None
    message: str
    data: Optional[dict[str, Any]] = None
    timestamp: datetime

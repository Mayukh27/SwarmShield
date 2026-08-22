import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class TargetProfileCreate(BaseModel):
    name: str
    description: Optional[str] = None
    endpoint_url: str
    auth_header_name: Optional[str] = None
    auth_header_value: Optional[str] = None
    declared_tools: dict[str, Any] = Field(default_factory=dict)
    permission_map: dict[str, Any] = Field(default_factory=dict)
    authorized: bool = False
    authorization_note: Optional[str] = None


class TargetProfileOut(BaseModel):
    id: uuid.UUID
    name: str
    description: Optional[str]
    endpoint_url: str
    declared_tools: dict[str, Any]
    permission_map: dict[str, Any]
    authorized: bool
    authorization_note: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True

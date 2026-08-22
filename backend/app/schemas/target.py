import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field

from app.models.target import CodeVisibility, TargetAccessMode


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
    # Safe-by-default: a newly registered target cannot write to itself or
    # to GitHub until someone explicitly opts it in.
    access_mode: TargetAccessMode = TargetAccessMode.READ_ONLY
    allow_direct_patch_apply: bool = False
    allow_pr_creation: bool = False
    code_visibility: CodeVisibility = CodeVisibility.UNKNOWN
    allow_branch_write: bool = False


class TargetProfileOut(BaseModel):
    id: uuid.UUID
    name: str
    description: Optional[str]
    endpoint_url: str
    declared_tools: dict[str, Any]
    permission_map: dict[str, Any]
    authorized: bool
    authorization_note: Optional[str]
    access_mode: TargetAccessMode
    allow_direct_patch_apply: bool
    allow_pr_creation: bool
    code_visibility: CodeVisibility
    allow_branch_write: bool
    created_at: datetime

    class Config:
        from_attributes = True

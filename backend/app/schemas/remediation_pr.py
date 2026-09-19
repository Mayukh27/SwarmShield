import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.models.remediation_pr import RemediationPRStatus


class RemediationPROut(BaseModel):
    """Response shape for a created/attempted PR. Deliberately contains no
    credential material -- not the GitHub token, not any header value.
    Only what a human needs to go review the PR."""
    id: uuid.UUID
    patch_id: uuid.UUID
    vulnerability_id: uuid.UUID
    repo: str
    base_branch: str
    branch_name: str
    pr_number: Optional[int]
    pr_url: Optional[str]
    status: RemediationPRStatus
    error: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True

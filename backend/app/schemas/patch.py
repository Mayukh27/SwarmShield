import uuid
from datetime import datetime

from pydantic import BaseModel


class RemediationPatchOut(BaseModel):
    id: uuid.UUID
    vulnerability_id: uuid.UUID
    summary: str
    explanation: str
    patch_type: str
    patch_content: str
    created_at: datetime

    class Config:
        from_attributes = True

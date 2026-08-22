"""
RemediationPatch: an AI-generated suggestion for fixing a Vulnerability —
e.g. a system-prompt hardening snippet, an input-validation rule, or a
permission-scoping change. Kept as free text + structured diff so the
frontend can render it as a copyable code block.
"""
import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class RemediationPatch(Base):
    __tablename__ = "remediation_patches"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vulnerability_id = Column(UUID(as_uuid=True), ForeignKey("vulnerabilities.id"), nullable=False)

    summary = Column(Text, nullable=False)         # one-line fix summary
    explanation = Column(Text, nullable=False)      # why this fixes the root cause
    patch_type = Column(Text, nullable=False)        # "system_prompt" | "input_validation" | "permission_scope" | "code"
    patch_content = Column(Text, nullable=False)      # the actual suggested snippet/diff

    created_at = Column(DateTime, default=datetime.utcnow)

    vulnerability = relationship("Vulnerability", back_populates="patches")

    def __repr__(self) -> str:
        return f"<RemediationPatch for {self.vulnerability_id}>"

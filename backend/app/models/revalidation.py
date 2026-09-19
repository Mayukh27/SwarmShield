"""
RevalidationRecord: result of re-sending a confirmed vulnerability's exact
winning payload back through the target after a remediation has been
"applied" (in the controlled target's case, via its /admin/patch toggle).
Neither source repo implemented this at all -- it's new.
"""
import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class RevalidationResult(str, enum.Enum):
    FIXED = "fixed"          # replay no longer triggers the violation
    STILL_VULNERABLE = "still_vulnerable"  # replay still triggers it
    INCONCLUSIVE = "inconclusive"


class RevalidationRecord(Base):
    __tablename__ = "revalidation_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vulnerability_id = Column(UUID(as_uuid=True), ForeignKey("vulnerabilities.id"), nullable=False)
    patch_id = Column(UUID(as_uuid=True), ForeignKey("remediation_patches.id"), nullable=True)

    replayed_payload = Column(Text, nullable=False)
    replayed_response = Column(Text, nullable=True)
    sentinel_verdict = Column(Text, nullable=True)  # JSON string of the re-evaluation
    result = Column(Enum(RevalidationResult), nullable=False)
    passed = Column(Boolean, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)

    vulnerability = relationship("Vulnerability", back_populates="revalidation_records")

"""
RemediationPR: tracks a GitHub pull request opened from a RemediationPatch.

Flow this row represents: Finding -> patch generated -> (human reviews the
patch content) -> branch created -> patch committed -> PR opened -> human
approval happens on GitHub itself -> human merges on GitHub itself ->
someone triggers /apply-and-revalidate (or revalidate-only) afterward.

SwarmShield never merges the PR itself -- there is no merge endpoint or
merge call anywhere in this codebase. Merge is a human action taken on
GitHub, outside SwarmShield's write surface entirely.
"""
import enum
import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class RemediationPRStatus(str, enum.Enum):
    CREATED = "created"    # branch pushed, PR opened successfully
    FAILED = "failed"      # attempted but GitHub API call failed


class RemediationPR(Base):
    __tablename__ = "remediation_prs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patch_id = Column(UUID(as_uuid=True), ForeignKey("remediation_patches.id"), nullable=False)
    vulnerability_id = Column(UUID(as_uuid=True), ForeignKey("vulnerabilities.id"), nullable=False)

    repo = Column(String(255), nullable=False)          # "owner/repo"
    base_branch = Column(String(255), nullable=False)
    branch_name = Column(String(255), nullable=False)

    pr_number = Column(Integer, nullable=True)
    pr_url = Column(String(500), nullable=True)
    status = Column(Enum(RemediationPRStatus), nullable=False, default=RemediationPRStatus.CREATED)
    error = Column(Text, nullable=True)                  # populated only on FAILED, never a secret

    created_at = Column(DateTime, default=datetime.utcnow)

    patch = relationship("RemediationPatch")
    vulnerability = relationship("Vulnerability")

    def __repr__(self) -> str:
        return f"<RemediationPR {self.pr_url or self.branch_name} status={self.status}>"

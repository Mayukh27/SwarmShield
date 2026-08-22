"""
TargetProfile: describes the agentic AI system under test — its endpoint,
declared tools/permissions, and auth. The Planner Agent uses this as the
starting point for attack-surface discovery.
"""
import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Enum, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class TargetAccessMode(str, enum.Enum):
    """Operational mode SwarmShield itself is permitted to use against this
    target. This is separate from `permission_map`, which describes the
    TARGET's own declared internal permissions (used for grading findings).

    READ_ONLY (default): discovery, scanning, attack execution, finding and
    remediation *generation*, and report viewing are all allowed. Applying a
    remediation directly to the live target is NOT allowed, regardless of
    any other flag.
    READ_WRITE: unlocks direct patch application, gated additionally by
    `allow_direct_patch_apply` below (belt-and-suspenders: two separate
    things must both be true before a write to the live target happens).
    """
    READ_ONLY = "read_only"
    READ_WRITE = "read_write"


class CodeVisibility(str, enum.Enum):
    PUBLIC = "public"
    PRIVATE = "private"
    UNKNOWN = "unknown"


class TargetProfile(Base):
    __tablename__ = "target_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # How to reach the target agentic system
    endpoint_url = Column(String(500), nullable=False)
    auth_header_name = Column(String(100), nullable=True)   # e.g. "Authorization"
    auth_header_value = Column(String(500), nullable=True)  # stored encrypted in prod

    # SAFETY: a scan must not be runnable against a target that hasn't been
    # explicitly attested as owned/authorized by whoever registered it. This
    # is a self-declared attestation (not third-party verification) -- it
    # exists to make unauthorized use a deliberate, logged act rather than
    # an accidental default, and to make that story visible in the demo.
    authorized = Column(Boolean, nullable=False, default=False)
    authorization_note = Column(String(500), nullable=True)  # e.g. "I own this / written permission from X"

    # Declared attack surface, filled in by the user or discovered by the Planner Agent.
    # Example shape:
    # {
    #   "tools": [{"name": "send_email", "description": "...", "permissions": ["email:send"]}],
    #   "system_prompt_summary": "...",
    #   "data_sources": ["crm_db", "internal_wiki"]
    # }
    declared_tools = Column(JSONB, nullable=False, default=dict)
    permission_map = Column(JSONB, nullable=False, default=dict)

    # --- SwarmShield's own write-capability gates for this target ---------
    # access_mode: whether SwarmShield may ever attempt a live write
    # (direct patch application) against this target. Default is the safe
    # option; scanning/attacking/remediation-generation work in either mode.
    access_mode = Column(Enum(TargetAccessMode), nullable=False, default=TargetAccessMode.READ_ONLY)

    # allow_direct_patch_apply: explicit, separate consent to apply a
    # generated patch directly to the live target's own admin hook. Requires
    # access_mode == READ_WRITE as well -- both must be true.
    allow_direct_patch_apply = Column(Boolean, nullable=False, default=False)

    # allow_pr_creation: explicit, separate consent to open a GitHub PR with
    # a generated patch. This never touches the live target -- it proposes a
    # change to a code repo, gated by human review/merge -- so it is a
    # distinct permission from allow_direct_patch_apply and does not require
    # READ_WRITE access_mode.
    allow_pr_creation = Column(Boolean, nullable=False, default=False)
    code_visibility = Column(Enum(CodeVisibility), nullable=False, default=CodeVisibility.UNKNOWN)
    allow_branch_write = Column(Boolean, nullable=False, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    scans = relationship("ScanRun", back_populates="target", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<TargetProfile {self.name}>"

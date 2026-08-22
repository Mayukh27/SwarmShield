"""
TargetProfile: describes the agentic AI system under test — its endpoint,
declared tools/permissions, and auth. The Planner Agent uses this as the
starting point for attack-surface discovery.
"""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


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

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    scans = relationship("ScanRun", back_populates="target", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<TargetProfile {self.name}>"

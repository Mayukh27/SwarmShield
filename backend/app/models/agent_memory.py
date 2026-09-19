import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.db.base import Base


class AgentMemory(Base):
    """Long-lived, deduplicated experience; distinct from scan MemoryRecord."""
    __tablename__ = "agent_memories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    memory_type = Column(String(24), nullable=False, default="episodic")
    namespace = Column(String(64), nullable=False, index=True)
    target_fingerprint = Column(String(128), nullable=True, index=True)
    vulnerability_type = Column(String(128), nullable=True, index=True)
    strategy = Column(String(256), nullable=True)
    content = Column(Text, nullable=False)
    confidence = Column(Float, nullable=False)
    importance = Column(Float, nullable=False)
    success = Column(Float, nullable=True)
    metadata_json = Column("metadata", JSONB, nullable=False, default=dict)
    memory_hash = Column(String(64), nullable=False, unique=True, index=True)
    embedding = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (Index("ix_memory_namespace_vulnerability", "namespace", "vulnerability_type"),)

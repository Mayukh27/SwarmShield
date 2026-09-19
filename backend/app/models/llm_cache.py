import uuid
from datetime import datetime
from sqlalchemy import Column, DateTime, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from app.db.base import Base


class LLMCacheEntry(Base):
    __tablename__ = "llm_cache_entries"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cache_key = Column(String(64), nullable=False, unique=True, index=True)
    response = Column(Text, nullable=False)
    json_response = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

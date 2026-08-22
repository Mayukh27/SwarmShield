"""Small, PostgreSQL-native security knowledge store.

Embeddings deliberately use JSONB rather than a mandatory pgvector column:
the same schema works on a stock developer Postgres and the service uses
pgvector only when an installation has enabled it.  Local cosine search is
bounded to the small, curated corpus supported by this project.
"""
import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.db.base import Base


class KnowledgeDocument(Base):
    __tablename__ = "knowledge_documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source = Column(String(64), nullable=False, index=True)
    source_id = Column(String(256), nullable=True, index=True)
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)
    document_type = Column(String(64), nullable=False, index=True)
    severity = Column(String(32), nullable=True)
    cwe = Column(String(32), nullable=True, index=True)
    cve = Column(String(32), nullable=True, index=True)
    product = Column(String(128), nullable=True)
    tags = Column(JSONB, nullable=False, default=list)
    metadata_json = Column("metadata", JSONB, nullable=False, default=dict)
    content_hash = Column(String(64), nullable=False, unique=True, index=True)
    embedding = Column(JSONB, nullable=True)
    embedding_dimension = Column(String(16), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (Index("ix_knowledge_source_source_id", "source", "source_id"),)

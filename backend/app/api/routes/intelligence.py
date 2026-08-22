from typing import Any
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.core.config import settings
from app.db.base import get_db
from app.models.agent_memory import AgentMemory
from app.models.knowledge_document import KnowledgeDocument
from app.models.llm_cache import LLMCacheEntry
from app.services import rag_service
from app.services.llm_router import metrics
from app.services.local_llm import local_llm
from app.services.memory_service import retrieve_experiences

router = APIRouter(tags=["local-intelligence"])

class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    limit: int = Field(default=6, ge=1, le=20)
    metadata: dict[str, str] = Field(default_factory=dict)
    namespace: str | None = None

@router.get("/llm/health")
def llm_health():
    return {"local_llm": settings.LOCAL_LLM_ENABLED, "provider": settings.LOCAL_LLM_PROVIDER,
            "model": settings.LOCAL_LLM_MODEL or None, "available": local_llm.available()}

@router.get("/memory/stats")
def memory_stats(db: Session = Depends(get_db)):
    return {"total_memories": db.query(AgentMemory).count(), "knowledge_documents": db.query(KnowledgeDocument).count(),
            "embeddings": db.query(KnowledgeDocument).filter(KnowledgeDocument.embedding.is_not(None)).count(),
            "cache_entries": db.query(LLMCacheEntry).count(), "metrics": metrics()}

@router.post("/memory/search")
def memory_search(request: SearchRequest, db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    namespace = request.namespace or "swarm"
    rows = retrieve_experiences(db, namespace=namespace, query=request.query, limit=request.limit)
    return [{"id": str(r.id), "namespace": r.namespace, "content": r.content, "confidence": r.confidence,
             "importance": r.importance, "strategy": r.strategy, "vulnerability_type": r.vulnerability_type} for r in rows]

@router.post("/rag/search")
def rag_search(request: SearchRequest, db: Session = Depends(get_db)):
    return rag_service.search(db, request.query, limit=request.limit, metadata=request.metadata)

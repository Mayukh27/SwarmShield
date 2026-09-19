"""
Memory service: DB-backed shared memory, wired into the orchestrator's
adaptive loop. Validation logic and the lexical retrieval algorithm are
ported directly from Repo A's `memory/manager.py`; the difference is this
version persists to `MemoryRecord` rows scoped per scan_id so it survives
across specialists/generations/vectors within a campaign, and later
specialists actually consult it before generating a payload (see
orchestrator.py's `_build_specialist_context`).
"""
import hashlib
import re
import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.models.memory import MemoryRecord, MemoryType
from app.models.agent_memory import AgentMemory
from app.core.config import settings
from app.services.embedding_service import cosine_similarity, embed

_VALID_TYPES = {t.value for t in MemoryType}


def write_memory(
    db: Session,
    *,
    scan_id: uuid.UUID,
    memory_type: str,
    content: str,
    confidence: float,
    agent: str,
    source_attack_id: uuid.UUID | None = None,
) -> MemoryRecord:
    if memory_type not in _VALID_TYPES:
        raise ValueError(f"Unsupported swarm memory type: {memory_type}")
    if not 0 <= confidence <= 1:
        raise ValueError("Memory confidence must be between 0 and 1")
    if not content.strip() or not agent.strip():
        raise ValueError("Memory content and agent are required")

    record = MemoryRecord(
        id=uuid.uuid4(),
        scan_id=scan_id,
        memory_type=MemoryType(memory_type),
        content=content.strip(),
        confidence=confidence,
        agent=agent,
        source_attack_id=source_attack_id,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def retrieve_relevant(db: Session, *, scan_id: uuid.UUID, query: str, limit: int = 5) -> list[MemoryRecord]:
    """Deterministic lexical fallback ported from Repo A -- ranks by
    term-overlap with `query`, then by confidence. Semantic retrieval can
    replace this later without changing the write side or callers."""
    items = db.query(MemoryRecord).filter(MemoryRecord.scan_id == scan_id).all()
    terms = {term.lower() for term in query.split() if term.strip()}

    def score(item: MemoryRecord) -> tuple[int, float]:
        overlap = len(terms & set(item.content.lower().split()))
        return (overlap, item.confidence)

    ranked = sorted(items, key=score, reverse=True)
    return ranked[:max(0, limit)]


def _memory_hash(namespace: str, content: str, strategy: str | None) -> str:
    normalized = re.sub(r"\s+", " ", content.lower()).strip()
    return hashlib.sha256(f"{namespace}|{strategy or ''}|{normalized}".encode()).hexdigest()


def write_experience(db: Session, *, namespace: str, content: str, confidence: float,
                     importance: float, memory_type: str = "episodic", strategy: str | None = None,
                     vulnerability_type: str | None = None, target_fingerprint: str | None = None,
                     success: bool | None = None, metadata: dict[str, Any] | None = None) -> AgentMemory | None:
    """Persist only novel, high-value summaries; raw prompts are not accepted."""
    if (not settings.MEMORY_ENABLED or importance < settings.MEMORY_MIN_IMPORTANCE or not content.strip()
            or re.search(r"(?i)(api[_ -]?key|password|authorization|session[_ -]?cookie)\s*[:=]", content)):
        return None
    digest = _memory_hash(namespace, content, strategy)
    existing = db.query(AgentMemory).filter(AgentMemory.memory_hash == digest).first()
    if existing: return existing
    record = AgentMemory(namespace=namespace[:64], memory_type=memory_type, content=content.strip()[:4000],
        confidence=max(0, min(1, confidence)), importance=max(0, min(1, importance)), strategy=strategy,
        vulnerability_type=vulnerability_type, target_fingerprint=target_fingerprint,
        success=float(success) if success is not None else None, metadata_json=metadata or {}, memory_hash=digest,
        embedding=embed(content))
    db.add(record); db.commit(); db.refresh(record)
    return record


def retrieve_experiences(db: Session, *, namespace: str, query: str, limit: int = 5,
                         vulnerability_type: str | None = None) -> list[AgentMemory]:
    rows = db.query(AgentMemory).filter(AgentMemory.namespace == namespace)
    if vulnerability_type: rows = rows.filter(AgentMemory.vulnerability_type == vulnerability_type)
    vector = embed(query)
    return sorted(rows.all(), key=lambda row: (cosine_similarity(vector, row.embedding), row.confidence), reverse=True)[:limit]


def strategy_seen(db: Session, *, target_fingerprint: str, vulnerability_type: str, strategy: str) -> bool:
    return db.query(AgentMemory).filter(AgentMemory.target_fingerprint == target_fingerprint,
        AgentMemory.vulnerability_type == vulnerability_type, AgentMemory.strategy == strategy,
        AgentMemory.success == 0.0).first() is not None

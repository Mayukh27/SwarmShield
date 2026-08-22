"""
Memory service: DB-backed shared memory, wired into the orchestrator's
adaptive loop. Validation logic and the lexical retrieval algorithm are
ported directly from Repo A's `memory/manager.py`; the difference is this
version persists to `MemoryRecord` rows scoped per scan_id so it survives
across specialists/generations/vectors within a campaign, and later
specialists actually consult it before generating a payload (see
orchestrator.py's `_build_specialist_context`).
"""
import uuid

from sqlalchemy.orm import Session

from app.models.memory import MemoryRecord, MemoryType

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

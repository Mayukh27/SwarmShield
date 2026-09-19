import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.models.attack_dna import AttackDNARecord
from app.models.memory import MemoryRecord

router = APIRouter(prefix="/scans", tags=["memory-dna"])


@router.get("/{scan_id}/memory")
def get_scan_memory(scan_id: uuid.UUID, db: Session = Depends(get_db)):
    records = db.query(MemoryRecord).filter(MemoryRecord.scan_id == scan_id).order_by(MemoryRecord.created_at).all()
    return [
        {
            "id": str(r.id),
            "memory_type": r.memory_type.value,
            "content": r.content,
            "confidence": r.confidence,
            "agent": r.agent,
            "source_attack_id": str(r.source_attack_id) if r.source_attack_id else None,
            "created_at": r.created_at.isoformat(),
        }
        for r in records
    ]


@router.get("/{scan_id}/attack-dna")
def get_scan_dna(scan_id: uuid.UUID, db: Session = Depends(get_db)):
    records = db.query(AttackDNARecord).filter(AttackDNARecord.scan_id == scan_id).order_by(AttackDNARecord.created_at).all()
    return [
        {
            "id": str(r.id),
            "vector_id": r.vector_id,
            "parent_id": str(r.parent_id) if r.parent_id else None,
            "generation": r.generation,
            "genome": r.genome,
            "mutations": r.mutations,
            "success_probability": r.success_probability,
            "confidence": r.confidence,
        }
        for r in records
    ]

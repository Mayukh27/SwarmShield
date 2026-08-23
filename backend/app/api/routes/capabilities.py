import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.models.attack import AttackLog
from app.models.capability import HypothesisStatus
from app.models.target import TargetProfile
from app.services import capability_persistence
from app.services.capability_service import analyze_target_capabilities

router = APIRouter(prefix="/targets", tags=["capability-intelligence"])


@router.get("/{target_id}/capabilities")
def get_target_capabilities(target_id: uuid.UUID, scan_id: uuid.UUID | None = None, db: Session = Depends(get_db)):
    target = db.query(TargetProfile).filter(TargetProfile.id == target_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")

    attack_logs = []
    if scan_id:
        attack_logs = db.query(AttackLog).filter(AttackLog.scan_id == scan_id).all()

    return analyze_target_capabilities(target, attack_logs=attack_logs)


def _load_analysis(target_id: uuid.UUID, scan_id: uuid.UUID | None, db: Session) -> dict:
    target = db.query(TargetProfile).filter(TargetProfile.id == target_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")
    attack_logs = []
    if scan_id:
        attack_logs = db.query(AttackLog).filter(AttackLog.scan_id == scan_id).all()
    return analyze_target_capabilities(target, attack_logs=attack_logs)


@router.get("/{target_id}/capabilities/graph")
def get_capability_graph(target_id: uuid.UUID, scan_id: uuid.UUID | None = None, db: Session = Depends(get_db)):
    return _load_analysis(target_id, scan_id, db)["graph"]


@router.get("/{target_id}/capabilities/paths")
def get_capability_paths(target_id: uuid.UUID, scan_id: uuid.UUID | None = None, db: Session = Depends(get_db)):
    return _load_analysis(target_id, scan_id, db)["attack_paths"]


@router.get("/{target_id}/capabilities/hypotheses")
def get_capability_hypotheses(target_id: uuid.UUID, scan_id: uuid.UUID | None = None, db: Session = Depends(get_db)):
    return _load_analysis(target_id, scan_id, db)["hypotheses"]


@router.get("/{target_id}/capabilities/unknown")
def get_unknown_capabilities(target_id: uuid.UUID, scan_id: uuid.UUID | None = None, db: Session = Depends(get_db)):
    analysis = _load_analysis(target_id, scan_id, db)
    return [c for c in analysis["capabilities"] if c.get("status") == "undeclared_observed"]


@router.get("/{target_id}/capabilities/coverage")
def get_capability_coverage(target_id: uuid.UUID, scan_id: uuid.UUID | None = None, db: Session = Depends(get_db)):
    return _load_analysis(target_id, scan_id, db)["coverage"]


@router.get("/{target_id}/capabilities/diff")
def get_capability_diff(
    target_id: uuid.UUID,
    scan_id: uuid.UUID,
    compare_to_scan_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
):
    """Compare a scan's persisted capability snapshot against either an
    explicit prior scan or (default) the most recent other snapshot for
    this target. Requires the scan to have completed -- snapshots are
    only written once real AttackLogs exist, at the end of run_scan."""
    diff = capability_persistence.diff_capabilities(
        db, target_id=target_id, scan_id_a=scan_id, scan_id_b=compare_to_scan_id
    )
    if not diff["has_baseline"]:
        raise HTTPException(status_code=404, detail="No prior completed scan of this target to diff against yet.")
    return diff


@router.get("/{target_id}/capabilities/hypotheses/records")
def list_hypothesis_records(target_id: uuid.UUID, scan_id: uuid.UUID, db: Session = Depends(get_db)):
    """Persisted hypotheses for a completed scan, including any
    approve/skip decision -- distinct from GET .../hypotheses, which
    recomputes hypotheses live and has no notion of a saved decision."""
    records = capability_persistence.list_hypotheses(db, scan_id=scan_id)
    return [
        {**r.data, "status": r.status.value, "decided_at": r.decided_at.isoformat() if r.decided_at else None}
        for r in records
    ]


@router.post("/{target_id}/capabilities/hypotheses/{hypothesis_id}/approve")
def approve_hypothesis(target_id: uuid.UUID, hypothesis_id: str, scan_id: uuid.UUID, db: Session = Depends(get_db)):
    record = capability_persistence.set_hypothesis_status(
        db, scan_id=scan_id, hypothesis_id=hypothesis_id, status=HypothesisStatus.APPROVED
    )
    if not record:
        raise HTTPException(status_code=404, detail="Hypothesis not found for this scan.")
    return {"hypothesis_id": hypothesis_id, "status": record.status.value}


@router.post("/{target_id}/capabilities/hypotheses/{hypothesis_id}/skip")
def skip_hypothesis(target_id: uuid.UUID, hypothesis_id: str, scan_id: uuid.UUID, db: Session = Depends(get_db)):
    record = capability_persistence.set_hypothesis_status(
        db, scan_id=scan_id, hypothesis_id=hypothesis_id, status=HypothesisStatus.SKIPPED
    )
    if not record:
        raise HTTPException(status_code=404, detail="Hypothesis not found for this scan.")
    return {"hypothesis_id": hypothesis_id, "status": record.status.value}

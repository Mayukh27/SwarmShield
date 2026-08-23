"""
Persistence layer for Capability Intelligence snapshots (spec section 39)
and the diff/approve/skip operations that depend on it (spec section 35,
23). Kept separate from app.services.capability_service so the pure
analysis pipeline stays DB-free; this module is the only place that
touches CapabilityRecord/AttackHypothesisRecord.
"""
from __future__ import annotations

import uuid

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.models.capability import AttackHypothesisRecord, CapabilityRecord, HypothesisStatus


def persist_analysis(db: Session, *, scan_id: uuid.UUID, target_id: uuid.UUID, analysis: dict) -> None:
    """Store one durable snapshot of a scan's capability analysis.
    Idempotent per call site usage (orchestrator calls this once, after
    the scan's real AttackLogs exist) -- if called again for the same
    scan_id it will add a second snapshot rather than overwrite, since
    ScanRun rows are immutable once completed and a second call would
    only happen from a deliberate re-analysis, which is itself a fact
    worth keeping (spec section 30: never silently discard evidence).
    """
    for cap in analysis.get("capabilities", []):
        db.add(CapabilityRecord(
            scan_id=scan_id,
            target_id=target_id,
            capability_id=cap.get("capability_id", ""),
            name=cap.get("name") or cap.get("tool_name") or "",
            category=cap.get("category", "unknown"),
            operation=cap.get("operation", "unknown_capability"),
            status=cap.get("status", "declared"),
            declared=bool(cap.get("declared")),
            observed=bool(cap.get("observed")),
            risk_score=float(cap.get("risk_score") or 0.0),
            data=cap,
        ))

    for hyp in analysis.get("hypotheses", []):
        db.add(AttackHypothesisRecord(
            scan_id=scan_id,
            target_id=target_id,
            hypothesis_id=hyp.get("hypothesis_id", ""),
            title=hyp.get("title", ""),
            priority=hyp.get("priority", "medium"),
            risk_score=float(hyp.get("risk_score") or 0.0),
            status=HypothesisStatus.PENDING,
            data=hyp,
        ))

    db.commit()


def _latest_snapshot_scan_id(db: Session, target_id: uuid.UUID, before_scan_id: uuid.UUID | None = None) -> uuid.UUID | None:
    query = db.query(CapabilityRecord.scan_id).filter(CapabilityRecord.target_id == target_id)
    if before_scan_id is not None:
        query = query.filter(CapabilityRecord.scan_id != before_scan_id)
    row = query.order_by(desc(CapabilityRecord.created_at)).first()
    return row[0] if row else None


def diff_capabilities(db: Session, *, target_id: uuid.UUID, scan_id_a: uuid.UUID, scan_id_b: uuid.UUID | None = None) -> dict:
    """Compare the capability set persisted for scan_id_a against either
    an explicit scan_id_b or (if omitted) the most recent other snapshot
    for this target -- 'what changed since last time we scanned this
    target' (spec section 39, API section 35 `/diff`)."""
    if scan_id_b is None:
        scan_id_b = _latest_snapshot_scan_id(db, target_id, before_scan_id=scan_id_a)

    a_rows = db.query(CapabilityRecord).filter(CapabilityRecord.scan_id == scan_id_a).all()
    b_rows = db.query(CapabilityRecord).filter(CapabilityRecord.scan_id == scan_id_b).all() if scan_id_b else []

    a_by_name = {r.name: r for r in a_rows}
    b_by_name = {r.name: r for r in b_rows}

    added = sorted(set(a_by_name) - set(b_by_name))
    removed = sorted(set(b_by_name) - set(a_by_name))
    changed = []
    for name in sorted(set(a_by_name) & set(b_by_name)):
        ra, rb = a_by_name[name], b_by_name[name]
        if ra.status != rb.status or ra.operation != rb.operation or round(ra.risk_score, 1) != round(rb.risk_score, 1):
            changed.append({
                "name": name,
                "from": {"status": rb.status, "operation": rb.operation, "risk_score": rb.risk_score},
                "to": {"status": ra.status, "operation": ra.operation, "risk_score": ra.risk_score},
            })

    return {
        "scan_id": str(scan_id_a),
        "compared_to_scan_id": str(scan_id_b) if scan_id_b else None,
        "added": added,
        "removed": removed,
        "changed": changed,
        "has_baseline": scan_id_b is not None,
    }


def set_hypothesis_status(db: Session, *, scan_id: uuid.UUID, hypothesis_id: str, status: HypothesisStatus):
    from datetime import datetime

    record = (
        db.query(AttackHypothesisRecord)
        .filter(AttackHypothesisRecord.scan_id == scan_id, AttackHypothesisRecord.hypothesis_id == hypothesis_id)
        .first()
    )
    if not record:
        return None
    record.status = status
    record.decided_at = datetime.utcnow()
    db.commit()
    db.refresh(record)
    return record


def list_hypotheses(db: Session, *, scan_id: uuid.UUID) -> list[AttackHypothesisRecord]:
    return (
        db.query(AttackHypothesisRecord)
        .filter(AttackHypothesisRecord.scan_id == scan_id)
        .order_by(desc(AttackHypothesisRecord.risk_score))
        .all()
    )

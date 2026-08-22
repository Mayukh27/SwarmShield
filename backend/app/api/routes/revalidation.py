import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.models.patch import RemediationPatch
from app.models.revalidation import RevalidationRecord
from app.models.vulnerability import Vulnerability, VulnerabilityStatus
from app.services import risk
from app.services.revalidation_service import apply_patch_to_target, revalidate_vulnerability

router = APIRouter(prefix="/vulnerabilities", tags=["revalidation"])


@router.post("/{vulnerability_id}/apply-and-revalidate")
async def apply_and_revalidate(
    vulnerability_id: uuid.UUID,
    patch_id: uuid.UUID | None = None,
    apply: bool = True,
    db: Session = Depends(get_db),
):
    """Replays the payload that originally proved the vulnerability and
    re-evaluates it with the Sentinel, returning a genuine fixed/
    still_vulnerable verdict. By default (`apply=true`) it first applies
    the given remediation patch to the live target (real HTTP call to the
    target's /admin/apply_patch) so the before/after difference is real,
    not just a stored flag. Pass `apply=false` to replay WITHOUT applying
    the patch first -- e.g. to show the still-vulnerable baseline before
    remediation, or to check whether a target you already patched
    out-of-band actually fixed the issue."""
    vuln = db.query(Vulnerability).filter(Vulnerability.id == vulnerability_id).first()
    if not vuln:
        raise HTTPException(status_code=404, detail="Vulnerability not found")

    patch = None
    if patch_id:
        patch = db.query(RemediationPatch).filter(RemediationPatch.id == patch_id).first()

    apply_result = {"applied": False, "reason": "apply=false, skipped"}
    if apply:
        apply_result = await apply_patch_to_target(vuln.scan.target, patch)
        if patch:
            vuln.status = VulnerabilityStatus.REMEDIATION_SUGGESTED
            db.commit()

    record = await revalidate_vulnerability(db, vulnerability_id=vulnerability_id, patch_id=patch_id)

    # The finding's status just changed (fixed or still open) -- the scan's
    # aggregate risk score is stale until we recompute it. Without this the
    # scorecard stays frozen at its scan-completion value forever, even
    # after every finding is patched. See app/services/risk.py.
    risk_breakdown = risk.compute_scan_risk(db, scan_id=vuln.scan_id)
    db.refresh(vuln.scan)

    return {
        "patch_apply_result": apply_result,
        "revalidation": {
            "id": str(record.id),
            "result": record.result.value,
            "passed": record.passed,
            "replayed_response": record.replayed_response,
        },
        "vulnerability_status": vuln.status.value,
        "scan_risk_score": vuln.scan.risk_score,
        "scan_risk_breakdown": risk_breakdown,
    }


@router.get("/{vulnerability_id}/revalidation-history")
def revalidation_history(vulnerability_id: uuid.UUID, db: Session = Depends(get_db)):
    records = (
        db.query(RevalidationRecord)
        .filter(RevalidationRecord.vulnerability_id == vulnerability_id)
        .order_by(RevalidationRecord.created_at)
        .all()
    )
    return [
        {
            "id": str(r.id),
            "result": r.result.value,
            "passed": r.passed,
            "replayed_payload": r.replayed_payload,
            "replayed_response": r.replayed_response,
            "created_at": r.created_at.isoformat(),
        }
        for r in records
    ]

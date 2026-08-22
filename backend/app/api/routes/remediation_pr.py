import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.models.patch import RemediationPatch
from app.models.remediation_pr import RemediationPR, RemediationPRStatus
from app.models.vulnerability import Vulnerability
from app.schemas.remediation_pr import RemediationPROut
from app.services import github_service
from app.services.authorization import ensure_pr_allowed

router = APIRouter(prefix="/patches", tags=["remediation-pr"])


@router.post("/{patch_id}/create-pr", response_model=RemediationPROut, status_code=201)
async def create_pr(patch_id: uuid.UUID, db: Session = Depends(get_db)):
    """Finding -> patch (already generated) -> [this endpoint] creates a
    branch, commits the patch, and opens a PR. Requires human approval and
    a human merge on GitHub -- this endpoint never merges anything.

    SECURITY: gated server-side by TargetProfile.allow_pr_creation
    (ensure_pr_allowed), independent of read-only/read-write access_mode --
    opening a PR never touches the live target. If GitHub isn't configured
    (no GITHUB_TOKEN/GITHUB_REPO), fails safely with a clear message
    instead of inventing credentials or crashing."""
    patch = db.query(RemediationPatch).filter(RemediationPatch.id == patch_id).first()
    if not patch:
        raise HTTPException(status_code=404, detail="Patch not found")

    vuln = db.query(Vulnerability).filter(Vulnerability.id == patch.vulnerability_id).first()
    if not vuln:
        raise HTTPException(status_code=404, detail="Vulnerability not found")

    target = vuln.scan.target
    ensure_pr_allowed(target)

    result = await github_service.open_remediation_pr(
        vulnerability_id=vuln.id,
        patch_id=patch.id,
        patch_summary=patch.summary,
        patch_explanation=patch.explanation,
        patch_type=patch.patch_type,
        patch_content=patch.patch_content,
    )

    if not result["configured"]:
        raise HTTPException(status_code=400, detail=result["error"])

    record = RemediationPR(
        id=uuid.uuid4(),
        patch_id=patch.id,
        vulnerability_id=vuln.id,
        repo=result["repo"],
        base_branch=result["base_branch"],
        branch_name=result["branch_name"],
        pr_number=result["pr_number"],
        pr_url=result["pr_url"],
        status=RemediationPRStatus.CREATED if result["status"] == "created" else RemediationPRStatus.FAILED,
        error=result["error"],
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    if record.status == RemediationPRStatus.FAILED:
        # Return 502: we successfully talked to GitHub's API surface (auth
        # was fine enough to reach it, or the failure is otherwise on
        # GitHub's / the repo config's side) but PR creation didn't
        # complete. The attempt is recorded either way for audit purposes.
        raise HTTPException(status_code=502, detail=record.error)

    return record


@router.get("/{patch_id}/prs", response_model=list[RemediationPROut])
def list_prs(patch_id: uuid.UUID, db: Session = Depends(get_db)):
    return (
        db.query(RemediationPR)
        .filter(RemediationPR.patch_id == patch_id)
        .order_by(RemediationPR.created_at.desc())
        .all()
    )

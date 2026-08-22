import json
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.agents.remediation import RemediationAgent
from app.db.base import get_db
from app.models.attack import AttackLog
from app.models.patch import RemediationPatch
from app.models.vulnerability import Vulnerability
from app.schemas.patch import RemediationPatchOut

router = APIRouter(prefix="/patches", tags=["patches"])


@router.post("/generate/{vulnerability_id}", response_model=RemediationPatchOut, status_code=201)
def generate_patch(vulnerability_id: uuid.UUID, db: Session = Depends(get_db)):
    vuln = db.query(Vulnerability).filter(Vulnerability.id == vulnerability_id).first()
    if not vuln:
        raise HTTPException(status_code=404, detail="Vulnerability not found")

    attack = db.query(AttackLog).filter(AttackLog.id == vuln.source_attack_id).first()

    agent = RemediationAgent()
    context = json.dumps({
        "owasp_category": vuln.owasp_category,
        "title": vuln.title,
        "description": vuln.description,
        "payload": attack.payload if attack else None,
        "target_response": attack.target_response if attack else None,
    })
    result = agent.generate_patch(context)

    patch = RemediationPatch(
        id=uuid.uuid4(),
        vulnerability_id=vuln.id,
        summary=result.get("summary", ""),
        explanation=result.get("explanation", ""),
        patch_type=result.get("patch_type", "system_prompt"),
        patch_content=result.get("patch_content", ""),
    )
    db.add(patch)
    db.commit()
    db.refresh(patch)
    return patch


@router.get("/{vulnerability_id}", response_model=list[RemediationPatchOut])
def list_patches(vulnerability_id: uuid.UUID, db: Session = Depends(get_db)):
    return (
        db.query(RemediationPatch)
        .filter(RemediationPatch.vulnerability_id == vulnerability_id)
        .order_by(RemediationPatch.created_at.desc())
        .all()
    )

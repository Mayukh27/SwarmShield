import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.models.vulnerability import Vulnerability
from app.schemas.vulnerability import VulnerabilityOut

router = APIRouter(prefix="/vulnerabilities", tags=["vulnerabilities"])


@router.get("", response_model=list[VulnerabilityOut])
def list_vulnerabilities(scan_id: uuid.UUID | None = None, db: Session = Depends(get_db)):
    q = db.query(Vulnerability)
    if scan_id:
        q = q.filter(Vulnerability.scan_id == scan_id)
    return q.order_by(Vulnerability.created_at.desc()).all()


@router.get("/{vulnerability_id}", response_model=VulnerabilityOut)
def get_vulnerability(vulnerability_id: uuid.UUID, db: Session = Depends(get_db)):
    vuln = db.query(Vulnerability).filter(Vulnerability.id == vulnerability_id).first()
    if not vuln:
        raise HTTPException(status_code=404, detail="Vulnerability not found")
    return vuln

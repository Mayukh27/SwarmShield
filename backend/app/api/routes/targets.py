import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.models.target import TargetProfile
from app.schemas.target import TargetProfileCreate, TargetProfileOut

router = APIRouter(prefix="/targets", tags=["targets"])


@router.post("", response_model=TargetProfileOut, status_code=201)
def create_target(payload: TargetProfileCreate, db: Session = Depends(get_db)):
    target = TargetProfile(**payload.model_dump())
    db.add(target)
    db.commit()
    db.refresh(target)
    return target


@router.get("", response_model=list[TargetProfileOut])
def list_targets(db: Session = Depends(get_db)):
    return db.query(TargetProfile).order_by(TargetProfile.created_at.desc()).all()


@router.get("/{target_id}", response_model=TargetProfileOut)
def get_target(target_id: uuid.UUID, db: Session = Depends(get_db)):
    target = db.query(TargetProfile).filter(TargetProfile.id == target_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")
    return target


@router.delete("/{target_id}", status_code=204)
def delete_target(target_id: uuid.UUID, db: Session = Depends(get_db)):
    target = db.query(TargetProfile).filter(TargetProfile.id == target_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")
    db.delete(target)
    db.commit()

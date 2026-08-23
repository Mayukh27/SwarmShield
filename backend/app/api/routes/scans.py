import asyncio
import json
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse

from app.db.base import get_db
from app.models.scan import ScanRun
from app.models.target import TargetProfile
from app.models.attack import AttackLog
from app.schemas.attack import AttackLogOut
from app.schemas.scan import ScanCreate, ScanOut
from app.services import event_bus
from app.services.scan_manager import launch_scan

router = APIRouter(prefix="/scans", tags=["scans"])


@router.post("", response_model=ScanOut, status_code=201)
def start_scan(payload: ScanCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    target = db.query(TargetProfile).filter(TargetProfile.id == payload.target_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")
    if not target.authorized:
        raise HTTPException(
            status_code=403,
            detail=(
                "This target is not marked as authorized for testing. "
                "SwarmShield will not attack a system without an explicit "
                "authorization attestation -- edit the target and confirm "
                "you own it or have written permission before scanning."
            ),
        )

    scan = ScanRun(id=uuid.uuid4(), target_id=target.id)
    db.add(scan)
    db.commit()
    db.refresh(scan)

    # Run the swarm asynchronously; client polls GET /scans/{id} or subscribes
    # to /scans/{id}/stream for live progress.
    background_tasks.add_task(_run_async, scan.id)

    return scan


def _run_async(scan_id: uuid.UUID) -> None:
    asyncio.run(launch_scan(scan_id))


@router.get("/{scan_id}", response_model=ScanOut)
def get_scan(scan_id: uuid.UUID, db: Session = Depends(get_db)):
    scan = db.query(ScanRun).filter(ScanRun.id == scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    return scan


@router.get("", response_model=list[ScanOut])
def list_scans(target_id: uuid.UUID | None = None, db: Session = Depends(get_db)):
    q = db.query(ScanRun)
    if target_id:
        q = q.filter(ScanRun.target_id == target_id)
    return q.order_by(ScanRun.started_at.desc()).all()


@router.get("/{scan_id}/attack-logs", response_model=list[AttackLogOut])
def get_attack_logs(scan_id: uuid.UUID, db: Session = Depends(get_db)):
    """Full attack lineage for this scan — powers the React Flow attack graph."""
    logs = db.query(AttackLog).filter(AttackLog.scan_id == scan_id).order_by(AttackLog.created_at).all()
    return logs


@router.get("/{scan_id}/stream")
async def stream_scan(scan_id: uuid.UUID):
    """
    SSE stream of live agent events for this scan. Frontend subscribes here
    right after POST /scans to watch the swarm work in real time.
    """
    queue = event_bus.subscribe(scan_id)

    async def event_generator():
        try:
            while True:
                event = await queue.get()
                yield {"event": event.event_type, "data": event.model_dump_json()}
                if event.event_type == "scan_status" and (
                    "completed" in event.message.lower() or "failed" in event.message.lower()
                ):
                    break
        finally:
            event_bus.unsubscribe(scan_id, queue)

    return EventSourceResponse(event_generator())

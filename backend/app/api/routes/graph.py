import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.services.graph_service import build_scan_graph

router = APIRouter(prefix="/scans", tags=["graph"])


@router.get("/{scan_id}/graph")
def get_scan_graph(scan_id: uuid.UUID, db: Session = Depends(get_db)):
    """Evidence-backed attack graph (nodes/edges) for AttackFlowCanvas.jsx:
    target -> attempts -> attack DNA lineage -> discovered memory ->
    caused findings, all derived from real persisted rows for this scan."""
    return build_scan_graph(db, scan_id=scan_id)

"""
Thin wrapper so `run_scan` can be launched as a FastAPI BackgroundTask with
its own DB session (background tasks must not reuse a request-scoped
session, since the request may finish first and close it).
"""
import uuid

from app.agents.orchestrator import run_scan
from app.db.base import SessionLocal


async def launch_scan(scan_id: uuid.UUID) -> None:
    db = SessionLocal()
    try:
        await run_scan(scan_id, db)
    finally:
        db.close()

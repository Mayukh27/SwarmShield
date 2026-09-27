"""Optional demo bootstrap: registers the bundled, local controlled target so the UI can start a
scan with one click (no manual target form). Off unless SEED_DEMO_TARGET=true (docker-compose
enables it). Idempotent: does nothing if a target with the same endpoint already exists.

The attestation is legitimate here because the target is SwarmShield's own bundled, local-only,
SAFE_MODE lab app (controlled_target/app.py). Real third-party targets are never seeded.
"""
from app.core.config import settings
from app.db.base import SessionLocal
from app.models.target import TargetAccessMode, TargetProfile


def seed_demo_target() -> None:
    with SessionLocal() as db:
        if db.query(TargetProfile).filter(TargetProfile.endpoint_url == settings.DEMO_TARGET_URL).first():
            return
        db.add(
            TargetProfile(
                name="SwarmShield Controlled Target (demo)",
                description="Bundled local lab app: User -> LLM -> RAG -> mock tools, with documented vulnerabilities.",
                endpoint_url=settings.DEMO_TARGET_URL,
                authorized=True,
                authorization_note="Bundled local lab target owned by the SwarmShield project (SAFE_MODE, no outbound network).",
                declared_tools={
                    "tools": [
                        {"name": "read_file", "description": "Reads files from the mock filesystem"},
                        {"name": "send_email", "description": "Queues a mock email"},
                        {"name": "execute_admin_action", "description": "Runs a mock admin action"},
                    ]
                },
                # both gates must be on for the existing 'Apply patch & re-validate' flow to write to the target
                access_mode=TargetAccessMode.READ_WRITE,
                allow_direct_patch_apply=True,
            )
        )
        db.commit()
        print("[SwarmShield] Seeded demo target:", settings.DEMO_TARGET_URL)

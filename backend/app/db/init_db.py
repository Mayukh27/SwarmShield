"""
Run once at startup (or via `python -m app.db.init_db`) to create/update tables.
For a hackathon this keeps schema setup simple without requiring Alembic.
"""

from sqlalchemy import inspect, text

from app.db.base import Base, engine
from app import models  # noqa: F401  (ensures all models are registered)


def init_db() -> None:
    # pgvector is an optional optimization.  The JSONB cosine fallback keeps
    # startup and local development working when the extension is unavailable.
    try:
        with engine.begin() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    except Exception:
        pass
    # Create tables that do not exist yet.
    Base.metadata.create_all(bind=engine)

    # Lightweight schema upgrade for existing databases.
    # create_all() does NOT add newly introduced columns to existing tables.
    inspector = inspect(engine)

    if "target_profiles" not in inspector.get_table_names():
        print("[SwarmShield] Database tables created.")
        return

    target_columns = {
        column["name"]
        for column in inspector.get_columns("target_profiles")
    }
    scan_columns = {
        column["name"]
        for column in inspector.get_columns("scan_runs")
    } if "scan_runs" in inspector.get_table_names() else set()

    with engine.begin() as conn:
        if "authorized" not in target_columns:
            conn.execute(
                text(
                    "ALTER TABLE target_profiles "
                    "ADD COLUMN authorized BOOLEAN NOT NULL DEFAULT FALSE"
                )
            )
            print("[SwarmShield] Added target_profiles.authorized")

        if "authorization_note" not in target_columns:
            conn.execute(
                text(
                    "ALTER TABLE target_profiles "
                    "ADD COLUMN authorization_note VARCHAR(500)"
                )
            )
            print("[SwarmShield] Added target_profiles.authorization_note")

        if "access_mode" not in target_columns:
            conn.execute(
                text(
                    "DO $$ BEGIN "
                    "CREATE TYPE targetaccessmode AS ENUM ('read_only', 'read_write'); "
                    "EXCEPTION WHEN duplicate_object THEN NULL; END $$;"
                )
            )
            conn.execute(
                text(
                    "ALTER TABLE target_profiles "
                    "ADD COLUMN access_mode targetaccessmode NOT NULL DEFAULT 'read_only'"
                )
            )
            print("[SwarmShield] Added target_profiles.access_mode (default read_only)")

        if "allow_direct_patch_apply" not in target_columns:
            conn.execute(
                text(
                    "ALTER TABLE target_profiles "
                    "ADD COLUMN allow_direct_patch_apply BOOLEAN NOT NULL DEFAULT FALSE"
                )
            )
            print("[SwarmShield] Added target_profiles.allow_direct_patch_apply")

        if "allow_pr_creation" not in target_columns:
            conn.execute(
                text(
                    "ALTER TABLE target_profiles "
                    "ADD COLUMN allow_pr_creation BOOLEAN NOT NULL DEFAULT FALSE"
                )
            )
            print("[SwarmShield] Added target_profiles.allow_pr_creation")

        if "code_visibility" not in target_columns:
            conn.execute(
                text(
                    "DO $$ BEGIN "
                    "CREATE TYPE codevisibility AS ENUM ('PUBLIC', 'PRIVATE', 'UNKNOWN'); "
                    "EXCEPTION WHEN duplicate_object THEN NULL; END $$;"
                )
            )
            conn.execute(
                text(
                    "ALTER TABLE target_profiles "
                    "ADD COLUMN code_visibility codevisibility NOT NULL DEFAULT 'UNKNOWN'"
                )
            )
            print("[SwarmShield] Added target_profiles.code_visibility")

        if "allow_branch_write" not in target_columns:
            conn.execute(
                text(
                    "ALTER TABLE target_profiles "
                    "ADD COLUMN allow_branch_write BOOLEAN NOT NULL DEFAULT FALSE"
                )
            )
            print("[SwarmShield] Added target_profiles.allow_branch_write")

        if "status" not in scan_columns:
            conn.execute(
                text(
                    "DO $$ BEGIN "
                    "CREATE TYPE scanstatus AS ENUM "
                    "('PENDING', 'PLANNING', 'ATTACKING', 'COMPLETED', 'FAILED', 'CANCELLED'); "
                    "EXCEPTION WHEN duplicate_object THEN NULL; END $$;"
                )
            )
            conn.execute(
                text(
                    "ALTER TABLE scan_runs "
                    "ADD COLUMN status scanstatus NOT NULL DEFAULT 'PENDING'"
                )
            )
            print("[SwarmShield] Added scan_runs.status")

    print("[SwarmShield] Database tables created/updated.")


if __name__ == "__main__":
    init_db()

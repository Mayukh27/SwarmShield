"""
Run once at startup (or via `python -m app.db.init_db`) to create/update tables.
For a hackathon this keeps schema setup simple without requiring Alembic.
"""

from sqlalchemy import inspect, text

from app.db.base import Base, engine
from app import models  # noqa: F401  (ensures all models are registered)


def init_db() -> None:
    # Create tables that do not exist yet.
    Base.metadata.create_all(bind=engine)

    # Lightweight schema upgrade for existing databases.
    # create_all() does NOT add newly introduced columns to existing tables.
    inspector = inspect(engine)

    if "target_profiles" not in inspector.get_table_names():
        print("[SwarmShield] Database tables created.")
        return

    columns = {
        column["name"]
        for column in inspector.get_columns("target_profiles")
    }

    with engine.begin() as conn:
        if "authorized" not in columns:
            conn.execute(
                text(
                    "ALTER TABLE target_profiles "
                    "ADD COLUMN authorized BOOLEAN NOT NULL DEFAULT FALSE"
                )
            )
            print("[SwarmShield] Added target_profiles.authorized")

        if "authorization_note" not in columns:
            conn.execute(
                text(
                    "ALTER TABLE target_profiles "
                    "ADD COLUMN authorization_note VARCHAR(500)"
                )
            )
            print("[SwarmShield] Added target_profiles.authorization_note")

        if "access_mode" not in columns:
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

        if "allow_direct_patch_apply" not in columns:
            conn.execute(
                text(
                    "ALTER TABLE target_profiles "
                    "ADD COLUMN allow_direct_patch_apply BOOLEAN NOT NULL DEFAULT FALSE"
                )
            )
            print("[SwarmShield] Added target_profiles.allow_direct_patch_apply")

        if "allow_pr_creation" not in columns:
            conn.execute(
                text(
                    "ALTER TABLE target_profiles "
                    "ADD COLUMN allow_pr_creation BOOLEAN NOT NULL DEFAULT FALSE"
                )
            )
            print("[SwarmShield] Added target_profiles.allow_pr_creation")

    print("[SwarmShield] Database tables created/updated.")


if __name__ == "__main__":
    init_db()
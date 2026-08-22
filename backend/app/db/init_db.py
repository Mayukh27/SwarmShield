"""
Run once at startup (or via `python -m app.db.init_db`) to create tables.
For a hackathon this beats setting up Alembic migrations; swap to Alembic
if you need real migrations post-hackathon.
"""
from app.db.base import Base, engine
from app import models  # noqa: F401  (ensures all models are registered)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    print("[SwarmShield] Database tables created.")


if __name__ == "__main__":
    init_db()

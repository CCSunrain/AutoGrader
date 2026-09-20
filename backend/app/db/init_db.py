"""Bootstrap the database schema.

Dev-friendly fast path: `Base.metadata.create_all` is idempotent and lets
`docker compose up` work immediately without a committed Alembic migration.
For production / incremental schema changes, use Alembic:
    alembic revision --autogenerate -m "..."
    alembic upgrade head
"""
from app import models  # noqa: F401  # ensure all tables are registered
from app.core.db import Base, engine


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    init_db()
    print("database schema ready")

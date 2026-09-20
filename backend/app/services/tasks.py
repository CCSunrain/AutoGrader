"""Task enqueueing helper (used by API layer to schedule background work)."""
from sqlalchemy.orm import Session

from app.models import BackgroundTask


def enqueue(
    db: Session,
    *,
    workspace_id: str,
    task_type: str,
    payload: dict | None = None,
    max_attempts: int = 3,
) -> BackgroundTask:
    task = BackgroundTask(
        workspace_id=workspace_id,
        task_type=task_type,
        payload=payload or {},
        max_attempts=max_attempts,
        status="pending",
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task

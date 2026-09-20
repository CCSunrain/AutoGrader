"""ORM model mixins and shared types."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


def new_uuid() -> str:
    """Return a random UUID4 as a string (portable across DB dialects)."""
    return str(uuid.uuid4())


def utcnow() -> datetime:
    """Timezone-aware current UTC time."""
    return datetime.now(timezone.utc)


class UUIDMixin:
    """String-UUID primary key (36-char), portable between PostgreSQL and SQLite."""

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)


class TimestampMixin:
    """created_at / updated_at with server + Python defaults."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
        server_default=func.now(),
        nullable=False,
    )


class TenantMixin:
    """Multi-tenant isolation: every business entity carries its workspace id."""

    workspace_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)

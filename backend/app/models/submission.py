"""Submission, version, and parsed-document models."""
from sqlalchemy import JSON, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import TenantMixin, TimestampMixin, UUIDMixin


class Submission(UUIDMixin, TimestampMixin, TenantMixin, Base):
    __tablename__ = "submissions"

    assignment_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    student_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="submitted", nullable=False)

    versions: Mapped[list["SubmissionVersion"]] = relationship(
        back_populates="submission", cascade="all, delete-orphan", order_by="SubmissionVersion.version_no"
    )


class SubmissionVersion(UUIDMixin, TimestampMixin, TenantMixin, Base):
    __tablename__ = "submission_versions"

    submission_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("submissions.id", ondelete="CASCADE"), index=True, nullable=False
    )
    version_no: Mapped[int] = mapped_column(default=1, nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(32), nullable=False)  # pdf / markdown
    file_key: Mapped[str] = mapped_column(String(512), nullable=False)  # storage key / path
    created_by: Mapped[str] = mapped_column(String(36), nullable=False)

    submission: Mapped["Submission"] = relationship(back_populates="versions")


class ParsedDocument(UUIDMixin, TimestampMixin, TenantMixin, Base):
    __tablename__ = "parsed_documents"

    submission_version_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    parser_version: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="pending", nullable=False)
    # plain text mirror for quick search / evidence highlight
    raw_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    # structured parse result: blocks, tables, code, formulas, spans
    content: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    error: Mapped[str] = mapped_column(Text, default="", nullable=False)

"""Review, review item, evidence, human decision and publish-record models.

A Review is the machine's evidence-based suggestion pass. Every ReviewItem
carries one of three evidence states (supported / missing / uncertain) and a
suggested band; the human decision and the published grade live separately so
that AI suggestions and human outcomes are never conflated.
"""
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import TenantMixin, TimestampMixin, UUIDMixin


class Review(UUIDMixin, TimestampMixin, TenantMixin, Base):
    __tablename__ = "reviews"

    submission_version_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    rubric_version_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="pending", nullable=False)
    # provenance bound to this review run (filled once the worker completes)
    model: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(32), default="", nullable=False)
    rules_version: Mapped[str] = mapped_column(String(32), default="", nullable=False)
    # deterministic contradiction findings (list of dicts)
    contradictions: Mapped[list] = mapped_column(JSON, default=list, nullable=False)

    items: Mapped[list["ReviewItem"]] = relationship(
        back_populates="review", cascade="all, delete-orphan", order_by="ReviewItem.order_index"
    )
    publish_records: Mapped[list["PublishRecord"]] = relationship(
        back_populates="review", cascade="all, delete-orphan"
    )

    @property
    def publish(self):
        """Latest publish record (published grades are append-only)."""
        if not self.publish_records:
            return None
        return max(self.publish_records, key=lambda r: r.published_at)


class ReviewItem(UUIDMixin, TimestampMixin, TenantMixin, Base):
    __tablename__ = "review_items"

    review_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("reviews.id", ondelete="CASCADE"), index=True, nullable=False
    )
    rubric_item_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # supported / missing / uncertain
    evidence_state: Mapped[str] = mapped_column(String(16), nullable=False)
    suggested_band_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, default="", nullable=False)
    # evidence insufficient / parse incomplete / contradiction / model conflict
    needs_review: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    review_flags: Mapped[list] = mapped_column(JSON, default=list, nullable=False)

    review: Mapped["Review"] = relationship(back_populates="items")
    evidences: Mapped[list["Evidence"]] = relationship(
        back_populates="review_item", cascade="all, delete-orphan"
    )
    decisions: Mapped[list["HumanDecision"]] = relationship(
        back_populates="review_item", cascade="all, delete-orphan"
    )

    @property
    def decision(self):
        """Latest human decision for this item (history is append-only)."""
        if not self.decisions:
            return None
        return max(self.decisions, key=lambda d: d.created_at)


class Evidence(UUIDMixin, TimestampMixin, TenantMixin, Base):
    __tablename__ = "evidences"

    review_item_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("review_items.id", ondelete="CASCADE"), index=True, nullable=False
    )
    quote: Mapped[str] = mapped_column(Text, nullable=False)
    start_offset: Mapped[int] = mapped_column(Integer, nullable=False)
    end_offset: Mapped[int] = mapped_column(Integer, nullable=False)
    page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ref_type: Mapped[str] = mapped_column(String(32), default="text", nullable=False)

    review_item: Mapped["ReviewItem"] = relationship(back_populates="evidences")


class HumanDecision(UUIDMixin, TimestampMixin, TenantMixin, Base):
    __tablename__ = "human_decisions"

    review_item_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("review_items.id", ondelete="CASCADE"), index=True, nullable=False
    )
    reviewer_id: Mapped[str] = mapped_column(String(36), nullable=False)
    final_band_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    feedback: Mapped[str] = mapped_column(Text, default="", nullable=False)

    review_item: Mapped["ReviewItem"] = relationship(back_populates="decisions")


class PublishRecord(UUIDMixin, TimestampMixin, TenantMixin, Base):
    __tablename__ = "publish_records"

    review_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("reviews.id", ondelete="CASCADE"), index=True, nullable=False
    )
    published_by: Mapped[str] = mapped_column(String(36), nullable=False)  # teacher only
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    feedback: Mapped[str] = mapped_column(Text, default="", nullable=False)

    review: Mapped["Review"] = relationship(back_populates="publish_records")

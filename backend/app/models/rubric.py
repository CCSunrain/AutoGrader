"""Rubric (grading scale) models with versioning and bands.

Structure:
    Rubric (1) -> RubricVersion (N) -> RubricItem (N) -> RubricBand (N)

Each `RubricVersion` is immutable once frozen (`frozen_at` set), so every
grading result can be bound to an exact rubric version.
"""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import TenantMixin, TimestampMixin, UUIDMixin


class Rubric(UUIDMixin, TimestampMixin, TenantMixin, Base):
    __tablename__ = "rubrics"

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)

    versions: Mapped[list["RubricVersion"]] = relationship(
        back_populates="rubric", cascade="all, delete-orphan", order_by="RubricVersion.version_no"
    )


class RubricVersion(UUIDMixin, TimestampMixin, TenantMixin, Base):
    __tablename__ = "rubric_versions"

    rubric_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("rubrics.id", ondelete="CASCADE"), index=True, nullable=False
    )
    version_no: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    # frozen means this version can no longer be edited
    frozen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    rubric: Mapped["Rubric"] = relationship(back_populates="versions")
    items: Mapped[list["RubricItem"]] = relationship(
        back_populates="version", cascade="all, delete-orphan", order_by="RubricItem.order_index"
    )


class RubricItem(UUIDMixin, TimestampMixin, TenantMixin, Base):
    __tablename__ = "rubric_items"

    rubric_version_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("rubric_versions.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    max_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    version: Mapped["RubricVersion"] = relationship(back_populates="items")
    bands: Mapped[list["RubricBand"]] = relationship(
        back_populates="item", cascade="all, delete-orphan", order_by="RubricBand.order_index"
    )


class RubricBand(UUIDMixin, TimestampMixin, TenantMixin, Base):
    __tablename__ = "rubric_bands"

    rubric_item_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("rubric_items.id", ondelete="CASCADE"), index=True, nullable=False
    )
    level: Mapped[str] = mapped_column(String(64), nullable=False)  # e.g. 优秀/良好/及格/不及格
    score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    item: Mapped["RubricItem"] = relationship(back_populates="bands")

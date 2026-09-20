"""Aggregate all models so `Base.metadata` is fully populated for migrations."""
from app.models.base import Base, TenantMixin, TimestampMixin, UUIDMixin  # noqa: F401
from app.models.course import Assignment, Course  # noqa: F401
from app.models.review import (  # noqa: F401
    Evidence,
    HumanDecision,
    PublishRecord,
    Review,
    ReviewItem,
)
from app.models.rubric import Rubric, RubricBand, RubricItem, RubricVersion  # noqa: F401
from app.models.submission import ParsedDocument, Submission, SubmissionVersion  # noqa: F401
from app.models.task import BackgroundTask  # noqa: F401
from app.models.user import Membership, User, Workspace  # noqa: F401

__all__ = [
    "Base",
    "TenantMixin",
    "TimestampMixin",
    "UUIDMixin",
    "User",
    "Workspace",
    "Membership",
    "Course",
    "Assignment",
    "Rubric",
    "RubricVersion",
    "RubricItem",
    "RubricBand",
    "Submission",
    "SubmissionVersion",
    "ParsedDocument",
    "Review",
    "ReviewItem",
    "Evidence",
    "HumanDecision",
    "PublishRecord",
    "BackgroundTask",
]

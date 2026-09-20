"""Submission / version / parsed-document schemas."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SubmissionVersionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    submission_id: str
    version_no: int
    filename: str
    content_type: str
    created_by: str
    created_at: datetime


class SubmissionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    assignment_id: str
    student_id: str
    status: str
    created_at: datetime
    versions: list[SubmissionVersionOut] = []


class ParsedDocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    submission_version_id: str
    parser_version: str
    status: str
    raw_text: str
    content: dict
    error: str
    created_at: datetime


class VersionSummary(BaseModel):
    version_id: str
    version_no: int
    raw_text: str
    score: float | None = None
    feedback: str = ""


class VersionCompareOut(BaseModel):
    from_version: VersionSummary
    to_version: VersionSummary
    score_delta: float | None = None


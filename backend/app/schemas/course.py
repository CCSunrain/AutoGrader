"""Course and assignment schemas."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CourseCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    code: str = Field(min_length=1, max_length=64)
    term: str = ""
    description: str = ""


class CourseUpdate(BaseModel):
    name: str | None = None
    code: str | None = None
    term: str | None = None
    description: str | None = None


class CourseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    code: str
    term: str
    description: str
    created_at: datetime


class AssignmentCreate(BaseModel):
    course_id: str
    title: str = Field(min_length=1, max_length=200)
    description: str = ""
    rubric_version_id: str | None = None


class AssignmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    course_id: str
    title: str
    description: str
    rubric_version_id: str | None
    due_at: datetime | None
    status: str
    created_at: datetime


class ItemAvg(BaseModel):
    rubric_item_name: str
    avg_score: float
    max_score: int


class AssignmentStatsOut(BaseModel):
    assignment_id: str
    published_count: int
    avg_score: float | None
    max_score: float | None
    min_score: float | None
    scores: list[float]
    item_avg: list[ItemAvg]

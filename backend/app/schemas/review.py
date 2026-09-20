"""Review / decision / publish schemas."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ReviewCreate(BaseModel):
    rubric_version_id: str


class DecisionCreate(BaseModel):
    final_band_id: str
    feedback: str = ""


class PublishCreate(BaseModel):
    feedback: str = ""


class EvidenceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    quote: str
    start_offset: int
    end_offset: int
    page: int | None
    ref_type: str


class HumanDecisionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    reviewer_id: str
    final_band_id: str | None
    feedback: str
    created_at: datetime


class ReviewItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    rubric_item_id: str
    order_index: int
    evidence_state: str
    suggested_band_id: str | None
    confidence: float
    explanation: str
    needs_review: bool
    review_flags: list
    evidences: list[EvidenceOut] = []
    decision: HumanDecisionOut | None = None


class PublishRecordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    published_by: str
    published_at: datetime
    score: float
    feedback: str


class ReviewOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    submission_version_id: str
    rubric_version_id: str
    status: str
    model: str
    prompt_version: str
    rules_version: str
    contradictions: list = []
    created_at: datetime
    items: list[ReviewItemOut] = []
    publish: PublishRecordOut | None = None


class PublishedItemOut(BaseModel):
    rubric_item_name: str
    final_band_level: str
    score: int
    feedback: str


class PublishedOut(BaseModel):
    submission_id: str
    version_no: int
    score: float
    feedback: str
    published_at: datetime
    items: list[PublishedItemOut]


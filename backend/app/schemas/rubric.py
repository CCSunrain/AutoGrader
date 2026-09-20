"""Rubric schemas (nested items + bands)."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class BandIn(BaseModel):
    level: str = Field(min_length=1, max_length=64)
    score: int = 0
    description: str = ""
    order_index: int = 0


class ItemIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = ""
    max_score: int = 0
    order_index: int = 0
    bands: list[BandIn] = []


class RubricCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = ""
    items: list[ItemIn] = []


class BandOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    level: str
    score: int
    description: str
    order_index: int


class ItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str
    max_score: int
    order_index: int
    bands: list[BandOut] = []


class VersionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    version_no: int
    frozen_at: datetime | None
    items: list[ItemOut] = []


class RubricOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    description: str
    created_at: datetime
    versions: list[VersionOut] = []

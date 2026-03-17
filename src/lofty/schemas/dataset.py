"""Dataset schemas for fine-tuning training data."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class DatasetTrackCreate(BaseModel):
    upload_id: uuid.UUID
    lyrics: str = Field(default="", max_length=10000)
    caption: str = Field(default="", max_length=2000)
    bpm: int | None = Field(default=None, ge=40, le=240)
    key_scale: str | None = Field(default=None, max_length=30)


class DatasetCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str = Field(default="", max_length=2000)


class DatasetTrackResponse(BaseModel):
    id: uuid.UUID
    dataset_id: uuid.UUID
    upload_id: uuid.UUID
    lyrics: str = ""
    caption: str = ""
    bpm: int | None = None
    key_scale: str | None = None
    duration_seconds: float = 0.0
    status: str = "pending"
    created_at: datetime

    model_config = {"from_attributes": True}


class DatasetResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str = ""
    status: str = "pending"
    num_tracks: int = 0
    total_duration_seconds: float = 0.0
    created_at: datetime
    updated_at: datetime | None = None
    tracks: list[DatasetTrackResponse] = []

    model_config = {"from_attributes": True}


class PaginatedDatasetResponse(BaseModel):
    items: list[DatasetResponse]
    total: int
    page: int
    per_page: int
    pages: int

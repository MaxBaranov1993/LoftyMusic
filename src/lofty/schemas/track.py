"""Track-related schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel


class TrackResponse(BaseModel):
    id: uuid.UUID
    job_id: uuid.UUID
    title: str
    duration_seconds: float
    sample_rate: int
    format: str
    file_size_bytes: int
    created_at: datetime
    download_url: str | None = None

    model_config = {"from_attributes": True}


class PaginatedTrackResponse(BaseModel):
    items: list[TrackResponse]
    total: int
    page: int
    per_page: int
    pages: int

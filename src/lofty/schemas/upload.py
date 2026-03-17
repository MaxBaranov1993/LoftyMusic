"""Audio upload schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel


class UploadResponse(BaseModel):
    id: uuid.UUID
    storage_key: str
    original_filename: str
    file_size_bytes: int
    duration_seconds: float
    format: str
    analysis: dict | None = None
    created_at: datetime
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class PaginatedUploadResponse(BaseModel):
    items: list[UploadResponse]
    total: int
    page: int
    per_page: int
    pages: int

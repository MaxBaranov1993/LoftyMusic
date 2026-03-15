"""Job-related schemas."""

import uuid
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

from lofty.schemas.track import TrackResponse


class JobStatus(str, Enum):
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class GenerationParams(BaseModel):
    temperature: float = Field(default=0.8, ge=0.1, le=2.0)
    top_k: int = Field(default=250, ge=1, le=1000)
    top_p: float = Field(default=0.95, ge=0.1, le=1.0)
    guidance_scale: float = Field(default=4.0, ge=1.0, le=10.0)


class JobCreate(BaseModel):
    prompt: str = Field(
        ...,
        min_length=3,
        max_length=1000,
        description="Text description of the desired music",
        examples=["upbeat electronic dance music with synth leads"],
    )
    duration_seconds: float = Field(
        default=10.0,
        ge=1.0,
        le=30.0,
        description="Duration of generated audio in seconds",
    )
    model_name: str = Field(
        default="musicgen-stereo-medium",
        pattern=r"^musicgen-(stereo-)?(small|medium|large|melody)$",
        description="Model variant to use",
    )
    generation_params: GenerationParams = Field(default_factory=GenerationParams)


class JobResponse(BaseModel):
    id: uuid.UUID
    status: str
    prompt: str
    duration_seconds: float
    model_name: str
    generation_params: dict
    error_message: str | None = None
    progress: int = 0
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    track: TrackResponse | None = None

    model_config = {"from_attributes": True}


class PaginatedJobResponse(BaseModel):
    items: list[JobResponse]
    total: int
    page: int
    per_page: int
    pages: int

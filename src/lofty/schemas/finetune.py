"""Fine-tuning job and LoRA adapter schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from lofty.schemas.job import ComputeMode


class FineTuneConfig(BaseModel):
    """Training configuration passed to the worker."""

    max_epochs: int = Field(default=500, ge=1, le=5000)
    batch_size: int = Field(default=1, ge=1, le=8)
    training_method: str = Field(default="lokr", pattern=r"^(lora|lokr)$")
    learning_rate: float = Field(default=1e-4, ge=1e-6, le=1e-2)


class FineTuneCreate(BaseModel):
    dataset_id: uuid.UUID
    name: str = Field(..., min_length=1, max_length=200)
    config: FineTuneConfig = Field(default_factory=FineTuneConfig)
    compute_mode: ComputeMode = Field(default=ComputeMode.GPU)


class FineTuneJobResponse(BaseModel):
    id: uuid.UUID
    dataset_id: uuid.UUID
    name: str
    status: str = "pending"
    config: dict = {}
    compute_mode: str = "gpu"
    progress: int = 0
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime | None = None
    adapter: "LoRAAdapterResponse | None" = None

    model_config = {"from_attributes": True}


class PaginatedFineTuneResponse(BaseModel):
    items: list[FineTuneJobResponse]
    total: int
    page: int
    per_page: int
    pages: int


class LoRAAdapterResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str = ""
    base_model: str
    training_method: str = "lokr"
    adapter_size_bytes: int = 0
    is_active: bool = True
    created_at: datetime

    model_config = {"from_attributes": True}


class PaginatedAdapterResponse(BaseModel):
    items: list[LoRAAdapterResponse]
    total: int
    page: int
    per_page: int
    pages: int

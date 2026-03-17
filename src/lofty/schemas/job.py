"""Job-related schemas."""

import re
import unicodedata
import uuid
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, field_validator, model_validator

from lofty.schemas.track import TrackResponse


class JobStatus(str, Enum):
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ComputeMode(str, Enum):
    CPU = "cpu"
    GPU = "gpu"


class QualityPreset(str, Enum):
    DRAFT = "draft"
    BALANCED = "balanced"
    HIGH = "high"


class GenerationParams(BaseModel):
    # --- Common ---
    guidance_scale: float = Field(default=5.0, ge=1.0, le=10.0)
    quality_preset: QualityPreset = Field(default=QualityPreset.BALANCED)
    language: str = Field(default="en", max_length=10)
    seed: int = Field(default=-1)

    # --- ACE-Step parameters ---
    inference_steps: int = Field(default=8, ge=1, le=8)
    bpm: int | None = Field(default=None, ge=40, le=240)
    key: str | None = Field(default=None, max_length=20)
    time_signature: str = Field(default="4/4", max_length=10)
    task_type: str = Field(default="text2music", max_length=20)

    # --- YuE parameters ---
    temperature: float | None = Field(default=None, ge=0.1, le=2.0)
    top_p: float | None = Field(default=None, ge=0.0, le=1.0)
    repetition_penalty: float | None = Field(default=None, ge=1.0, le=2.0)
    num_segments: int = Field(default=2, ge=1, le=2)


# Control characters except common whitespace (space, newline, tab)
_CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]")

# Allowed model names
_ALLOWED_MODELS = {"ace-step-1.5", "yue"}


class JobCreate(BaseModel):
    prompt: str = Field(
        ...,
        min_length=3,
        max_length=1000,
        description="Text description of the desired music (caption for ACE-Step)",
        examples=["upbeat electronic dance music with synth leads"],
    )
    lyrics: str = Field(
        default="",
        max_length=5000,
        description="Song lyrics for vocal generation",
    )
    duration_seconds: float = Field(
        default=10.0,
        ge=1.0,
        le=600.0,
        description="Duration in seconds (max 600s / 10 min)",
    )
    model_name: str = Field(
        default="ace-step-1.5",
        description="Model variant to use",
    )
    generation_params: GenerationParams = Field(default_factory=GenerationParams)
    lora_adapter_id: uuid.UUID | None = Field(
        default=None,
        description="LoRA adapter ID for custom style (ACE-Step only)",
    )
    compute_mode: ComputeMode = Field(
        default=ComputeMode.GPU,
        description="Run on CPU or GPU worker",
    )

    @field_validator("model_name")
    @classmethod
    def validate_model_name(cls, v: str) -> str:
        if v not in _ALLOWED_MODELS:
            raise ValueError(
                f"Invalid model_name '{v}'. Allowed: {', '.join(sorted(_ALLOWED_MODELS))}"
            )
        return v

    @field_validator("prompt")
    @classmethod
    def sanitize_prompt(cls, v: str) -> str:
        """Strip control characters, normalize unicode, and collapse whitespace."""
        v = unicodedata.normalize("NFC", v)
        v = _CONTROL_CHAR_RE.sub("", v)
        v = " ".join(v.split())
        v = v.strip()
        if len(v) < 3:
            raise ValueError("Prompt must contain at least 3 visible characters")
        return v

    @field_validator("duration_seconds")
    @classmethod
    def validate_duration(cls, v: float, info) -> float:
        """Enforce per-engine max duration."""
        # This is a basic check — full enforcement happens in the task
        # based on the actual model_name. Here we just allow the max possible.
        return v

    @model_validator(mode="after")
    def validate_yue_constraints(self):
        """YuE requires lyrics and has a 60s duration cap on free Colab."""
        if self.model_name == "yue":
            if not self.lyrics.strip():
                raise ValueError(
                    "YuE requires lyrics for vocal generation. "
                    "Please provide lyrics with section markers like [verse], [chorus]."
                )
            if self.duration_seconds > 60.0:
                self.duration_seconds = 60.0
        return self

    @model_validator(mode="after")
    def validate_compute_mode(self):
        """YuE requires GPU — CPU mode would produce only mock/silent output."""
        if self.model_name == "yue" and self.compute_mode == ComputeMode.CPU:
            raise ValueError(
                "YuE requires a GPU. CPU mode is not supported for YuE."
            )
        return self


class JobResponse(BaseModel):
    id: uuid.UUID
    status: str
    prompt: str
    lyrics: str = ""
    duration_seconds: float
    model_name: str
    generation_params: dict
    lora_adapter_id: uuid.UUID | None = None
    compute_mode: str = "gpu"
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

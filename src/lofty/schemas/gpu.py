"""Schemas for GPU provider settings and status."""

from __future__ import annotations

from pydantic import BaseModel, Field


class GpuSettingsResponse(BaseModel):
    """Current GPU backend configuration."""

    backend: str = Field(description="Active backend: local, google, or cloud")
    autoscaler_enabled: bool
    autoscaler_min_instances: int
    autoscaler_max_instances: int
    autoscaler_idle_timeout: int
    cloud_api_key_configured: bool = Field(
        description="Whether a cloud API key is set (key value is never exposed)"
    )


class GpuSettingsUpdate(BaseModel):
    """Update GPU backend settings."""

    backend: str = Field(
        pattern="^(local|google|cloud)$",
        description="GPU backend: local, google, or cloud",
    )
    cloud_api_key: str | None = Field(
        default=None,
        description="RunPod/Vast.ai API key. Omit or null to keep existing.",
    )
    autoscaler_enabled: bool | None = None
    autoscaler_max_instances: int | None = Field(default=None, ge=1, le=20)
    autoscaler_idle_timeout: int | None = Field(default=None, ge=60, le=3600)


class GpuInstanceResponse(BaseModel):
    """Info about a single GPU worker instance."""

    id: str
    backend: str
    status: str
    gpu_type: str
    gpu_memory_mb: int
    cost_per_hour: float
    created_at: float


class GpuStatusResponse(BaseModel):
    """Overall GPU infrastructure status."""

    backend: str
    status: str
    instances: list[GpuInstanceResponse]
    total_cost_per_hour: float
    colab_setup_snippet: str | None = None

"""GPU settings and infrastructure management endpoints."""

from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends

from lofty.config import settings
from lofty.dependencies import get_current_user
from lofty.infra.gpu_provisioner import (
    GpuBackend,
    get_provisioner,
    reset_provisioner,
)
from lofty.models.user import User
from lofty.schemas.gpu import (
    GpuInstanceResponse,
    GpuSettingsResponse,
    GpuSettingsUpdate,
    GpuStatusResponse,
)

logger = structlog.get_logger()

router = APIRouter(prefix="/gpu", tags=["gpu"])

COLAB_SETUP_SNIPPET = """# === Lofty GPU Worker — Google Colab Setup ===
# Run this cell in Google Colab (with GPU runtime enabled)
# No database access needed — worker communicates via Redis only.
# Supports: music generation, audio analysis, dataset processing, and fine-tuning.

import os
os.environ["CELERY_BROKER_URL"] = "{broker_url}"
os.environ["CELERY_RESULT_BACKEND"] = "{result_backend}"
os.environ["REDIS_URL"] = "{redis_url}"
os.environ["STORAGE_ENDPOINT"] = "{storage_endpoint}"
os.environ["STORAGE_ACCESS_KEY"] = "{storage_access_key}"
os.environ["STORAGE_SECRET_KEY"] = "{storage_secret_key}"
os.environ["STORAGE_BUCKET"] = "{storage_bucket}"
os.environ["STORAGE_USE_SSL"] = "{storage_use_ssl}"
os.environ["MODEL_DEVICE"] = "cuda"
os.environ["MODEL_NAME"] = "ace-step-1.5"
os.environ["ACE_STEP_MODEL_PATH"] = "ACE-Step/Ace-Step1.5"
os.environ["ACE_STEP_CACHE_DIR"] = "/content/ace_model_cache"
os.environ["ACE_STEP_PROJECT_ROOT"] = "/content/ACE-Step-1.5"
os.environ["MOCK_GPU"] = "false"

# Install dependencies
!pip install -q celery[redis] redis boto3 scipy structlog pydantic-settings
!pip install -q torch torchaudio --index-url https://download.pytorch.org/whl/cu121
!pip install -q transformers accelerate peft soundfile
!apt-get install -y -qq ffmpeg
!git clone --depth 1 https://github.com/ace-step/ACE-Step-1.5.git /content/ACE-Step-1.5
!pip install -q -e /content/ACE-Step-1.5
!pip install -q git+https://github.com/{repo_url}.git

# Heartbeat thread (keeps the worker visible to the backend)
import threading, time, redis as _redis
def _heartbeat():
    r = _redis.from_url(os.environ["REDIS_URL"])
    while True:
        r.setex("worker_heartbeat:colab-manual", 60, "alive")
        time.sleep(30)
threading.Thread(target=_heartbeat, daemon=True).start()

# Start Celery worker
!celery -A lofty.worker.celery_app worker --pool=solo --queues gpu,training --concurrency 1 --loglevel info
"""


def _get_active_provisioner():
    return get_provisioner(
        backend=settings.gpu_backend,
        redis_url=settings.redis_url,
        cloud_api_key=settings.cloud_gpu_api_key,
        cloud_docker_image=settings.cloud_gpu_docker_image,
    )


@router.get("/settings", response_model=GpuSettingsResponse)
async def get_gpu_settings(user: User = Depends(get_current_user)):
    """Get current GPU backend configuration."""
    return GpuSettingsResponse(
        backend=settings.gpu_backend,
        autoscaler_enabled=settings.autoscaler_enabled,
        autoscaler_min_instances=settings.autoscaler_min_instances,
        autoscaler_max_instances=settings.autoscaler_max_instances,
        autoscaler_idle_timeout=settings.autoscaler_idle_timeout,
        cloud_api_key_configured=bool(settings.cloud_gpu_api_key),
    )


@router.put("/settings", response_model=GpuSettingsResponse)
async def update_gpu_settings(
    data: GpuSettingsUpdate,
    user: User = Depends(get_current_user),
):
    """Update GPU backend configuration.

    Changes take effect immediately. The provisioner is reset and
    re-initialized with the new settings.
    """
    settings.gpu_backend = data.backend

    if data.cloud_api_key is not None:
        settings.cloud_gpu_api_key = data.cloud_api_key

    if data.autoscaler_enabled is not None:
        settings.autoscaler_enabled = data.autoscaler_enabled

    if data.autoscaler_max_instances is not None:
        settings.autoscaler_max_instances = data.autoscaler_max_instances

    if data.autoscaler_idle_timeout is not None:
        settings.autoscaler_idle_timeout = data.autoscaler_idle_timeout

    # Reset provisioner so next request uses new settings
    reset_provisioner()

    logger.info(
        "gpu_settings.updated",
        backend=data.backend,
        by_user=user.clerk_id,
    )

    return GpuSettingsResponse(
        backend=settings.gpu_backend,
        autoscaler_enabled=settings.autoscaler_enabled,
        autoscaler_min_instances=settings.autoscaler_min_instances,
        autoscaler_max_instances=settings.autoscaler_max_instances,
        autoscaler_idle_timeout=settings.autoscaler_idle_timeout,
        cloud_api_key_configured=bool(settings.cloud_gpu_api_key),
    )


@router.get("/status", response_model=GpuStatusResponse)
async def get_gpu_status(user: User = Depends(get_current_user)):
    """Get GPU infrastructure status: active instances, costs, health."""
    provisioner = _get_active_provisioner()
    instances = await provisioner.list_instances()

    colab_snippet = None
    if settings.gpu_backend == GpuBackend.GOOGLE.value:
        colab_snippet = COLAB_SETUP_SNIPPET.format(
            broker_url=settings.celery_broker_url,
            result_backend=settings.celery_result_backend,
            redis_url=settings.redis_url,
            storage_endpoint=settings.storage_endpoint,
            storage_access_key=settings.storage_access_key,
            storage_secret_key=settings.storage_secret_key,
            storage_bucket=settings.storage_bucket,
            storage_use_ssl=str(settings.storage_use_ssl).lower(),
            repo_url="YOUR_GITHUB_USER/lofty",
        )

    status_info = await provisioner.get_status()

    return GpuStatusResponse(
        backend=settings.gpu_backend,
        status=status_info.get("status", "unknown"),
        instances=[
            GpuInstanceResponse(
                id=inst.id,
                backend=inst.backend.value,
                status=inst.status.value,
                gpu_type=inst.gpu_type,
                gpu_memory_mb=inst.gpu_memory_mb,
                cost_per_hour=inst.cost_per_hour,
                created_at=inst.created_at,
            )
            for inst in instances
        ],
        total_cost_per_hour=sum(i.cost_per_hour for i in instances),
        colab_setup_snippet=colab_snippet,
    )


@router.post("/instances/spin-up", response_model=GpuInstanceResponse)
async def spin_up_instance(
    user: User = Depends(get_current_user),
    gpu_type: str = "auto",
):
    """Manually spin up a new GPU instance."""
    provisioner = _get_active_provisioner()
    instance = await provisioner.spin_up(gpu_type=gpu_type)

    logger.info("gpu.spin_up", instance_id=instance.id, by_user=user.clerk_id)

    return GpuInstanceResponse(
        id=instance.id,
        backend=instance.backend.value,
        status=instance.status.value,
        gpu_type=instance.gpu_type,
        gpu_memory_mb=instance.gpu_memory_mb,
        cost_per_hour=instance.cost_per_hour,
        created_at=instance.created_at,
    )


@router.post("/instances/{instance_id}/tear-down", status_code=204)
async def tear_down_instance(
    instance_id: str,
    user: User = Depends(get_current_user),
):
    """Manually tear down a GPU instance."""
    provisioner = _get_active_provisioner()
    await provisioner.tear_down(instance_id)
    logger.info("gpu.tear_down", instance_id=instance_id, by_user=user.clerk_id)

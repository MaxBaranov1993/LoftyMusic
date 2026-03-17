"""GPU provisioner interface and implementations.

Three tiers:
  - local:  Use the machine's own GPU / CPU (free, for dev/demo)
  - google: Use Google Colab / free-tier cloud GPU (free with limits)
  - cloud:  Use RunPod / Vast.ai on-demand GPU instances (pay-per-use)
"""

from __future__ import annotations

import abc
import enum
import time
import uuid
from dataclasses import dataclass, field

import structlog

logger = structlog.get_logger()


class GpuBackend(enum.StrEnum):
    LOCAL = "local"
    GOOGLE = "google"
    CLOUD = "cloud"


class InstanceStatus(enum.StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    STOPPING = "stopping"
    TERMINATED = "terminated"
    ERROR = "error"


@dataclass
class GpuInstance:
    """Represents a single GPU worker instance."""

    id: str
    backend: GpuBackend
    status: InstanceStatus
    gpu_type: str = "unknown"
    gpu_memory_mb: int = 0
    host: str | None = None
    port: int | None = None
    created_at: float = field(default_factory=time.time)
    cost_per_hour: float = 0.0
    metadata: dict = field(default_factory=dict)


class GpuProvisioner(abc.ABC):
    """Abstract GPU provisioner interface."""

    @abc.abstractmethod
    async def spin_up(self, gpu_type: str = "auto") -> GpuInstance:
        """Provision a new GPU instance and return its info."""

    @abc.abstractmethod
    async def tear_down(self, instance_id: str) -> None:
        """Terminate a GPU instance."""

    @abc.abstractmethod
    async def list_instances(self) -> list[GpuInstance]:
        """List all active instances managed by this provisioner."""

    @abc.abstractmethod
    async def health_check(self, instance_id: str) -> bool:
        """Check if an instance is healthy and responsive."""

    @abc.abstractmethod
    async def get_status(self) -> dict:
        """Get provisioner status summary for the admin API."""


# ---------------------------------------------------------------------------
# Local provisioner – uses the machine's own GPU/CPU
# ---------------------------------------------------------------------------


class LocalProvisioner(GpuProvisioner):
    """Uses the local machine's GPU or CPU. Zero cost."""

    def __init__(self) -> None:
        self._instance: GpuInstance | None = None
        self._detect_local_gpu()

    def _detect_local_gpu(self) -> None:
        gpu_type = "cpu"
        gpu_memory = 0
        try:
            import torch

            if torch.cuda.is_available():
                gpu_type = torch.cuda.get_device_name(0)
                gpu_memory = torch.cuda.get_device_properties(0).total_mem // (1024 * 1024)
        except ImportError:
            pass

        self._instance = GpuInstance(
            id="local-0",
            backend=GpuBackend.LOCAL,
            status=InstanceStatus.RUNNING,
            gpu_type=gpu_type,
            gpu_memory_mb=gpu_memory,
            host="localhost",
            cost_per_hour=0.0,
        )

    async def spin_up(self, gpu_type: str = "auto") -> GpuInstance:
        logger.info("local_provisioner.spin_up", note="Already running locally")
        assert self._instance is not None
        return self._instance

    async def tear_down(self, instance_id: str) -> None:
        logger.info("local_provisioner.tear_down", note="Local worker cannot be torn down")

    async def list_instances(self) -> list[GpuInstance]:
        return [self._instance] if self._instance else []

    async def health_check(self, instance_id: str) -> bool:
        return True

    async def get_status(self) -> dict:
        inst = self._instance
        return {
            "backend": GpuBackend.LOCAL.value,
            "instances": 1,
            "gpu_type": inst.gpu_type if inst else "unknown",
            "gpu_memory_mb": inst.gpu_memory_mb if inst else 0,
            "cost_per_hour": 0.0,
            "status": "running",
        }


# ---------------------------------------------------------------------------
# Google Colab / free-tier provisioner
# ---------------------------------------------------------------------------


class GoogleColabProvisioner(GpuProvisioner):
    """Connect to a Google Colab or Kaggle notebook running as a remote worker.

    How it works:
    1. User starts a Colab notebook with the Lofty worker script
    2. The notebook connects to the same Redis broker as the backend
    3. This provisioner tracks the connection status via Redis heartbeats

    The notebook template is provided in the Settings page.
    """

    def __init__(self, redis_url: str) -> None:
        self._redis_url = redis_url
        self._instances: dict[str, GpuInstance] = {}

    async def _get_redis(self):
        import redis.asyncio as aioredis

        return aioredis.from_url(self._redis_url, decode_responses=True)

    async def spin_up(self, gpu_type: str = "auto") -> GpuInstance:
        """Register a Colab worker. The actual spin-up is done by the user
        opening the Colab notebook — we just create a registration token."""
        instance_id = f"colab-{uuid.uuid4().hex[:8]}"
        instance = GpuInstance(
            id=instance_id,
            backend=GpuBackend.GOOGLE,
            status=InstanceStatus.PENDING,
            gpu_type="T4 (Google Colab Free)",
            gpu_memory_mb=15360,
            cost_per_hour=0.0,
            metadata={"connection_token": uuid.uuid4().hex},
        )
        self._instances[instance_id] = instance

        # Store token in Redis so the Colab worker can authenticate
        r = await self._get_redis()
        await r.setex(
            f"colab_token:{instance.metadata['connection_token']}",
            3600,  # 1 hour to connect
            instance_id,
        )
        await r.aclose()

        logger.info("google_provisioner.spin_up", instance_id=instance_id)
        return instance

    async def tear_down(self, instance_id: str) -> None:
        if instance_id in self._instances:
            self._instances[instance_id].status = InstanceStatus.TERMINATED
            del self._instances[instance_id]
        logger.info("google_provisioner.tear_down", instance_id=instance_id)

    async def list_instances(self) -> list[GpuInstance]:
        # Refresh status from Redis heartbeats
        r = await self._get_redis()
        for inst_id, inst in list(self._instances.items()):
            heartbeat = await r.get(f"worker_heartbeat:{inst_id}")
            if heartbeat:
                inst.status = InstanceStatus.RUNNING
            elif inst.status == InstanceStatus.RUNNING:
                # Lost heartbeat — mark as error
                if time.time() - inst.created_at > 120:
                    inst.status = InstanceStatus.ERROR
        await r.aclose()
        return list(self._instances.values())

    async def health_check(self, instance_id: str) -> bool:
        r = await self._get_redis()
        heartbeat = await r.get(f"worker_heartbeat:{instance_id}")
        await r.aclose()
        return heartbeat is not None

    async def get_status(self) -> dict:
        instances = await self.list_instances()
        running = [i for i in instances if i.status == InstanceStatus.RUNNING]
        return {
            "backend": GpuBackend.GOOGLE.value,
            "instances": len(instances),
            "running": len(running),
            "gpu_type": "T4 (Google Colab Free)",
            "cost_per_hour": 0.0,
            "status": "connected" if running else "waiting_for_connection",
            "colab_notebook_url": "See Settings page for setup instructions",
        }


# ---------------------------------------------------------------------------
# Cloud provisioner – RunPod / Vast.ai (pay-per-use)
# ---------------------------------------------------------------------------


class CloudProvisioner(GpuProvisioner):
    """On-demand GPU instances via RunPod API.

    Supports: RunPod (primary), extensible to Vast.ai, Lambda, etc.
    """

    # RunPod GPU type mapping
    GPU_TYPES = {
        "auto": "NVIDIA A40",
        "a40": "NVIDIA A40",
        "a100": "NVIDIA A100 80GB",
        "rtx4090": "NVIDIA GeForce RTX 4090",
        "t4": "NVIDIA T4",
    }

    COST_PER_HOUR = {
        "NVIDIA A40": 0.44,
        "NVIDIA A100 80GB": 1.64,
        "NVIDIA GeForce RTX 4090": 0.69,
        "NVIDIA T4": 0.20,
    }

    def __init__(self, api_key: str, docker_image: str = "lofty-worker:gpu") -> None:
        self._api_key = api_key
        self._docker_image = docker_image
        self._instances: dict[str, GpuInstance] = {}

    async def spin_up(self, gpu_type: str = "auto") -> GpuInstance:
        resolved_gpu = self.GPU_TYPES.get(gpu_type, self.GPU_TYPES["auto"])
        cost = self.COST_PER_HOUR.get(resolved_gpu, 0.50)

        if not self._api_key:
            raise RuntimeError(
                "RunPod API key not configured. Set CLOUD_GPU_API_KEY in your environment."
            )

        # Call RunPod API to create a pod
        import httpx

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://api.runpod.io/v2/pods",
                headers={"Authorization": f"Bearer {self._api_key}"},
                json={
                    "name": f"lofty-worker-{uuid.uuid4().hex[:6]}",
                    "imageName": self._docker_image,
                    "gpuTypeId": resolved_gpu,
                    "cloudType": "SECURE",
                    "gpuCount": 1,
                    "volumeInGb": 20,
                    "containerDiskInGb": 10,
                    "env": {
                        "CELERY_BROKER_URL": "configured_at_deploy",
                        "MODEL_DEVICE": "cuda",
                    },
                },
                timeout=60,
            )

        if resp.status_code not in (200, 201):
            logger.error(
                "cloud_provisioner.spin_up_failed",
                status=resp.status_code,
                body=resp.text,
            )
            raise RuntimeError(f"RunPod API error: {resp.status_code}")

        pod_data = resp.json()
        instance_id = pod_data.get("id", f"runpod-{uuid.uuid4().hex[:8]}")

        instance = GpuInstance(
            id=instance_id,
            backend=GpuBackend.CLOUD,
            status=InstanceStatus.PENDING,
            gpu_type=resolved_gpu,
            gpu_memory_mb=48000 if "A40" in resolved_gpu else 80000,
            cost_per_hour=cost,
            metadata={"pod_data": pod_data},
        )
        self._instances[instance_id] = instance
        logger.info("cloud_provisioner.spin_up", instance_id=instance_id, gpu=resolved_gpu)
        return instance

    async def tear_down(self, instance_id: str) -> None:
        if not self._api_key:
            return

        import httpx

        async with httpx.AsyncClient() as client:
            await client.delete(
                f"https://api.runpod.io/v2/pods/{instance_id}",
                headers={"Authorization": f"Bearer {self._api_key}"},
                timeout=30,
            )

        if instance_id in self._instances:
            self._instances[instance_id].status = InstanceStatus.TERMINATED
            del self._instances[instance_id]

        logger.info("cloud_provisioner.tear_down", instance_id=instance_id)

    async def list_instances(self) -> list[GpuInstance]:
        return list(self._instances.values())

    async def health_check(self, instance_id: str) -> bool:
        inst = self._instances.get(instance_id)
        return inst is not None and inst.status == InstanceStatus.RUNNING

    async def get_status(self) -> dict:
        instances = list(self._instances.values())
        running = [i for i in instances if i.status == InstanceStatus.RUNNING]
        total_cost = sum(i.cost_per_hour for i in running)
        return {
            "backend": GpuBackend.CLOUD.value,
            "instances": len(instances),
            "running": len(running),
            "total_cost_per_hour": total_cost,
            "api_key_configured": bool(self._api_key),
            "status": "active" if running else "idle",
        }


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

_provisioner: GpuProvisioner | None = None


def get_provisioner(
    backend: GpuBackend | str = GpuBackend.LOCAL,
    *,
    redis_url: str = "",
    cloud_api_key: str = "",
    cloud_docker_image: str = "lofty-worker:gpu",
) -> GpuProvisioner:
    """Create or return cached provisioner for the given backend."""
    global _provisioner

    if isinstance(backend, str):
        backend = GpuBackend(backend)

    if _provisioner is not None and hasattr(_provisioner, "_instance"):
        # Check if backend changed
        current = getattr(_provisioner, "_backend_type", None)
        if current == backend:
            return _provisioner

    if backend == GpuBackend.LOCAL:
        _provisioner = LocalProvisioner()
    elif backend == GpuBackend.GOOGLE:
        _provisioner = GoogleColabProvisioner(redis_url=redis_url)
    elif backend == GpuBackend.CLOUD:
        _provisioner = CloudProvisioner(
            api_key=cloud_api_key,
            docker_image=cloud_docker_image,
        )
    else:
        raise ValueError(f"Unknown GPU backend: {backend}")

    # Tag for cache invalidation
    _provisioner._backend_type = backend  # type: ignore[attr-defined]
    return _provisioner


def reset_provisioner() -> None:
    """Reset cached provisioner (used when settings change)."""
    global _provisioner
    _provisioner = None

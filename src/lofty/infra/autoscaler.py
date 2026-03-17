"""Queue-based GPU autoscaler.

Monitors the Celery GPU queue depth in Redis and spins up/down
GPU instances via the active GpuProvisioner.

Runs as a Celery Beat periodic task (every 30 seconds).
"""

from __future__ import annotations

import time

import redis
import structlog

from lofty.config import settings
from lofty.infra.gpu_provisioner import (
    GpuBackend,
    InstanceStatus,
    get_provisioner,
)

logger = structlog.get_logger()

# Track last scale-up/down to enforce cooldown
_last_scale_up: float = 0
_last_scale_down: float = 0
SCALE_COOLDOWN = 60  # seconds between scaling actions


def check_and_scale() -> dict:
    """Check queue depth and scale GPU instances accordingly.

    Returns a summary dict for logging / monitoring.

    This runs synchronously inside a Celery Beat task.
    """
    import asyncio

    global _last_scale_up, _last_scale_down

    if not settings.autoscaler_enabled:
        return {"action": "disabled"}

    if settings.gpu_backend == GpuBackend.LOCAL.value:
        return {"action": "skip", "reason": "local backend cannot autoscale"}

    # Check queue depth
    r = redis.from_url(settings.celery_broker_url)
    queue_depth = r.llen("gpu")
    r.close()

    provisioner = get_provisioner(
        backend=settings.gpu_backend,
        redis_url=settings.redis_url,
        cloud_api_key=settings.cloud_gpu_api_key,
        cloud_docker_image=settings.cloud_gpu_docker_image,
    )

    # Run async provisioner methods from sync context
    loop = asyncio.new_event_loop()
    try:
        instances = loop.run_until_complete(provisioner.list_instances())
        running = [i for i in instances if i.status == InstanceStatus.RUNNING]
        pending = [i for i in instances if i.status == InstanceStatus.PENDING]
        now = time.time()

        summary = {
            "queue_depth": queue_depth,
            "running_instances": len(running),
            "pending_instances": len(pending),
            "action": "none",
        }

        # Scale UP: queue has jobs and no idle workers
        if queue_depth > 0 and len(pending) == 0:
            total = len(running) + len(pending)
            if total < settings.autoscaler_max_instances:
                if now - _last_scale_up > SCALE_COOLDOWN:
                    instance = loop.run_until_complete(provisioner.spin_up())
                    _last_scale_up = now
                    summary["action"] = "scale_up"
                    summary["new_instance_id"] = instance.id
                    logger.info("autoscaler.scale_up", **summary)
                else:
                    summary["action"] = "cooldown"

        # Scale DOWN: queue empty and idle instances exist
        elif queue_depth == 0 and len(running) > settings.autoscaler_min_instances:
            idle_instances = [
                i for i in running
                if now - i.created_at > settings.autoscaler_idle_timeout
            ]
            if idle_instances and now - _last_scale_down > SCALE_COOLDOWN:
                oldest = idle_instances[0]
                loop.run_until_complete(provisioner.tear_down(oldest.id))
                _last_scale_down = now
                summary["action"] = "scale_down"
                summary["terminated_instance_id"] = oldest.id
                logger.info("autoscaler.scale_down", **summary)

        return summary
    finally:
        loop.close()

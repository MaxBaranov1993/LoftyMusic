"""Celery application instance and configuration."""

from celery import Celery
from celery.signals import worker_ready

from lofty.config import settings

celery_app = Celery("lofty")

_broker_ssl = {}
if settings.celery_broker_url.startswith("rediss://"):
    import ssl
    _broker_ssl = {
        "broker_use_ssl": {"ssl_cert_reqs": ssl.CERT_NONE},
        "redis_backend_use_ssl": {"ssl_cert_reqs": ssl.CERT_NONE},
    }

celery_app.conf.update(
    broker_url=settings.celery_broker_url,
    result_backend=settings.celery_result_backend,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    worker_concurrency=1,
    task_routes={
        "lofty.worker.tasks.generate_music": {"queue": "gpu"},
        "lofty.worker.tasks.analyze_audio": {"queue": "gpu"},
        "lofty.worker.tasks.process_dataset": {"queue": "gpu"},
        "lofty.worker.tasks.finetune_model": {"queue": "training"},
    },
    task_default_queue="gpu",
    **_broker_ssl,
    # Celery Beat schedule for periodic tasks
    beat_schedule={
        "cleanup-stale-jobs": {
            "task": "lofty.worker.tasks.cleanup_stale_jobs",
            "schedule": 300.0,  # every 5 minutes
        },
        "gpu-autoscaler": {
            "task": "lofty.worker.tasks.run_autoscaler",
            "schedule": 30.0,  # every 30 seconds
        },
    },
)

# Auto-discover tasks
celery_app.autodiscover_tasks(["lofty.worker"])


@worker_ready.connect
def init_worker(**kwargs):
    """Load music generation engines when the worker starts (solo pool)."""
    from lofty.worker.generator import preload_engines

    preload_engines()

"""Celery application instance and configuration."""

from celery import Celery
from celery.signals import worker_ready

from lofty.config import settings

celery_app = Celery("lofty")

celery_app.conf.update(
    broker_url=settings.celery_broker_url,
    result_backend=settings.celery_result_backend,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    worker_concurrency=1,
    task_routes={
        "lofty.worker.tasks.generate_music": {"queue": "gpu"},
    },
    task_default_queue="gpu",
)

# Auto-discover tasks
celery_app.autodiscover_tasks(["lofty.worker"])


@worker_ready.connect
def init_worker(**kwargs):
    """Load the music generation model when the worker starts (solo pool)."""
    from lofty.worker.generator import get_generator

    generator = get_generator()
    generator.load()

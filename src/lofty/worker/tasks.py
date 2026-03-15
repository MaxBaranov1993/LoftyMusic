"""Celery tasks for music generation."""

import logging
import uuid
from datetime import datetime, timezone

import redis
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from lofty.config import settings
from lofty.models.job import GenerationJob, JobStatus
from lofty.models.track import Track
from lofty.services.storage import storage_client
from lofty.worker.celery_app import celery_app
from lofty.worker.generator import get_generator

logger = logging.getLogger(__name__)


class GenerationCancelled(Exception):
    """Raised when a generation is cancelled via Redis flag."""
    def __init__(self, job_id: str):
        self.job_id = job_id
        super().__init__(f"Job {job_id} cancelled by user")

# Synchronous engine for Celery workers (Celery tasks are sync)
sync_engine = create_engine(
    settings.sync_database_url,
    pool_size=5,
    max_overflow=2,
    pool_pre_ping=True,
)
SyncSession = sessionmaker(bind=sync_engine)

# Redis client for progress tracking
_redis = redis.from_url(settings.redis_url, decode_responses=True)


def _progress_key(job_id: str) -> str:
    return f"job_progress:{job_id}"


@celery_app.task(
    bind=True,
    name="lofty.worker.tasks.generate_music",
    max_retries=1,
    default_retry_delay=10,
)
def generate_music(self, job_id: str) -> dict:
    """Generate music for a job.

    1. Update job status to RUNNING
    2. Generate audio using MusicGenerator
    3. Upload WAV to MinIO/S3
    4. Create Track record
    5. Update job status to COMPLETED
    """
    job_uuid = uuid.UUID(job_id)

    with SyncSession() as db:
        job = db.get(GenerationJob, job_uuid)
        if job is None:
            logger.error(f"Job {job_id} not found")
            return {"status": "error", "message": "Job not found"}

        if job.status == JobStatus.CANCELLED:
            logger.info(f"Job {job_id} was cancelled, skipping")
            return {"status": "cancelled"}

        try:
            # Mark as running
            job.status = JobStatus.RUNNING
            job.started_at = datetime.now(timezone.utc)
            db.commit()

            # Progress callback: store in Redis with TTL
            last_reported = [0]

            def on_progress(pct: int) -> None:
                # Throttle updates: only write if changed by >= 2%
                if pct - last_reported[0] >= 2 or pct >= 100:
                    _redis.setex(_progress_key(job_id), 300, str(pct))
                    last_reported[0] = pct

                # Check cancellation flag in Redis
                if _redis.get(f"job_cancel:{job_id}"):
                    _redis.delete(f"job_cancel:{job_id}")
                    raise GenerationCancelled(job_id)

            on_progress(0)

            # Generate audio
            generator = get_generator()
            params = job.generation_params or {}
            wav_bytes, sample_rate, actual_duration = generator.generate(
                prompt=job.prompt,
                duration_seconds=job.duration_seconds,
                temperature=params.get("temperature", 0.8),
                top_k=params.get("top_k", 250),
                top_p=params.get("top_p", 0.95),
                guidance_scale=params.get("guidance_scale", 4.0),
                on_progress=on_progress,
            )

            # Upload to storage
            storage_key = f"tracks/{job.user_id}/{job_id}.wav"
            file_size = storage_client.upload_bytes(storage_key, wav_bytes)

            # Create track record
            title = job.prompt[:100]  # Derive title from prompt
            track = Track(
                job_id=job_uuid,
                user_id=job.user_id,
                title=title,
                storage_key=storage_key,
                file_size_bytes=file_size,
                duration_seconds=actual_duration,
                sample_rate=sample_rate,
                format="wav",
            )
            db.add(track)

            # Mark job as completed
            job.status = JobStatus.COMPLETED
            job.completed_at = datetime.now(timezone.utc)
            db.commit()

            # Clean up progress key
            _redis.delete(_progress_key(job_id))

            logger.info(
                f"Job {job_id} completed: {actual_duration:.1f}s audio, "
                f"{file_size / 1024:.1f}KB"
            )

            return {
                "status": "completed",
                "track_id": str(track.id),
                "duration": actual_duration,
                "file_size": file_size,
            }

        except GenerationCancelled:
            _redis.delete(_progress_key(job_id))
            job = db.get(GenerationJob, job_uuid)
            if job:
                job.status = JobStatus.CANCELLED.value
                job.completed_at = datetime.now(timezone.utc)
                db.commit()
            logger.info(f"Job {job_id} cancelled by user during generation")
            return {"status": "cancelled"}

        except Exception as exc:
            db.rollback()

            # Clean up progress key
            _redis.delete(_progress_key(job_id))

            # Update job with error
            job = db.get(GenerationJob, job_uuid)
            if job:
                job.status = JobStatus.FAILED
                job.error_message = str(exc)[:500]
                job.completed_at = datetime.now(timezone.utc)
                db.commit()

            logger.exception(f"Job {job_id} failed: {exc}")

            # Retry if retries remain
            if self.request.retries < self.max_retries:
                raise self.retry(exc=exc)

            return {"status": "failed", "message": str(exc)}

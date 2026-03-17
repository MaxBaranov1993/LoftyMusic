"""Job service: CRUD operations and Celery task dispatch."""

import math
import uuid

import structlog
from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from lofty.dependencies import get_redis
from lofty.models.job import GenerationJob, JobStatus
from lofty.models.user import User
from lofty.schemas.job import JobCreate

logger = structlog.get_logger()

# Shared pagination helper — used by both job_service and track_service
def calculate_pages(total: int, per_page: int) -> int:
    """Calculate total number of pages."""
    return max(1, math.ceil(total / per_page))


async def create_job(
    db: AsyncSession,
    user: User,
    job_data: JobCreate,
) -> GenerationJob:
    """Atomically check for active jobs and create a new generation job.

    Uses a Redis distributed lock to prevent the race condition where
    two concurrent requests both pass the active-job check.
    """
    redis = await get_redis()
    lock_key = f"job_create_lock:{user.id}"

    # Acquire a short-lived distributed lock (10s TTL as safety net)
    acquired = await redis.set(lock_key, "1", nx=True, ex=10)
    if not acquired:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Another job creation is already in progress.",
        )

    try:
        # Check for active jobs inside the lock
        active_count = await db.execute(
            select(func.count())
            .select_from(GenerationJob)
            .where(
                GenerationJob.user_id == user.id,
                GenerationJob.status.in_([
                    JobStatus.PENDING.value,
                    JobStatus.QUEUED.value,
                    JobStatus.RUNNING.value,
                ]),
            )
        )
        if active_count.scalar_one() > 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="You already have an active generation job. Please wait for it to finish.",
            )

        job = GenerationJob(
            user_id=user.id,
            status=JobStatus.PENDING.value,
            prompt=job_data.prompt,
            lyrics=job_data.lyrics,
            duration_seconds=job_data.duration_seconds,
            model_name=job_data.model_name,
            generation_params=job_data.generation_params.model_dump(),
            lora_adapter_id=job_data.lora_adapter_id,
            compute_mode=job_data.compute_mode.value,
        )
        db.add(job)
        await db.commit()

        # Route by compute_mode:
        #   CPU → dispatch to local Celery worker immediately
        #   GPU → stay PENDING for Colab/cloud worker (HTTP polling via /worker/next-job)
        if job_data.compute_mode.value == "cpu":
            try:
                from lofty.worker.celery_app import celery_app

                celery_app.send_task(
                    "lofty.worker.tasks.generate_music",
                    args=[str(job.id)],
                    kwargs={
                        "prompt": job.prompt,
                        "lyrics": job.lyrics or "",
                        "duration_seconds": job.duration_seconds,
                        "model_name": job.model_name,
                        "generation_params": job.generation_params or {},
                        "user_id": str(job.user_id),
                        "lora_adapter_id": str(job.lora_adapter_id) if job.lora_adapter_id else None,
                    },
                    queue="gpu",
                )
                logger.info("job.dispatched_to_celery", job_id=str(job.id), mode="cpu")
            except Exception:
                logger.exception("Failed to dispatch CPU job to Celery")

        return job
    finally:
        await redis.delete(lock_key)


async def get_job(
    db: AsyncSession,
    job_id: str,
    user: User,
) -> GenerationJob | None:
    """Get a job by ID, scoped to the user."""
    result = await db.execute(
        select(GenerationJob)
        .options(selectinload(GenerationJob.track))
        .where(
            GenerationJob.id == job_id,
            GenerationJob.user_id == user.id,
        )
    )
    return result.scalar_one_or_none()


async def list_jobs(
    db: AsyncSession,
    user: User,
    status: str | None = None,
    page: int = 1,
    per_page: int = 20,
) -> tuple[list[GenerationJob], int]:
    """List jobs for a user with optional status filter and pagination."""
    query = (
        select(GenerationJob)
        .options(selectinload(GenerationJob.track))
        .where(GenerationJob.user_id == user.id)
    )
    count_query = select(func.count()).select_from(GenerationJob).where(
        GenerationJob.user_id == user.id
    )

    if status is not None:
        query = query.where(GenerationJob.status == status)
        count_query = count_query.where(GenerationJob.status == status)

    query = query.order_by(GenerationJob.created_at.desc())
    query = query.offset((page - 1) * per_page).limit(per_page)

    result = await db.execute(query)
    jobs = list(result.scalars().all())

    count_result = await db.execute(count_query)
    total = count_result.scalar_one()

    return jobs, total


async def cancel_job(
    db: AsyncSession,
    job_id: str,
    user: User,
) -> tuple[GenerationJob | None, bool]:
    """Cancel a pending, queued, or running job.

    Returns (job, was_cancelled) tuple. was_cancelled is False if job
    is already in a terminal state.
    """
    job = await get_job(db, job_id, user)
    if job is None:
        return None, False

    cancellable = (JobStatus.PENDING.value, JobStatus.QUEUED.value, JobStatus.RUNNING.value)
    if job.status not in cancellable:
        return job, False

    if job.status == JobStatus.RUNNING.value:
        # Signal cancellation via Redis flag — worker checks this during generation
        redis = await get_redis()
        await redis.setex(f"job_cancel:{job_id}", 600, "1")
    else:
        # For pending: just mark as cancelled
        job.status = JobStatus.CANCELLED.value
        await db.commit()

    return job, True


async def delete_job(
    db: AsyncSession,
    job_id: str,
    user: User,
) -> bool:
    """Delete a job record. Cancels it first if still active. Cleans up S3 files."""
    import asyncio

    from lofty.services.storage import storage_client

    job = await get_job(db, job_id, user)
    if job is None:
        return False

    # Cancel if still active
    active = (JobStatus.PENDING.value, JobStatus.QUEUED.value, JobStatus.RUNNING.value)
    if job.status in active:
        if job.status == JobStatus.RUNNING.value:
            redis = await get_redis()
            await redis.setex(f"job_cancel:{str(job.id)}", 600, "1")

    # Delete associated audio files from S3 (run sync boto3 in thread)
    if job.track:
        try:
            await asyncio.to_thread(storage_client.delete_object, job.track.storage_key)
        except Exception:
            logger.warning("Failed to delete S3 object", storage_key=job.track.storage_key)

    await db.delete(job)
    await db.commit()
    return True


def calculate_pages(total: int, per_page: int) -> int:
    """Calculate total number of pages."""
    return max(1, math.ceil(total / per_page))

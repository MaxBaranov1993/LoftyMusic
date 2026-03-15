"""Job service: CRUD operations and Celery task dispatch."""

import math

import redis.asyncio as aioredis
import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from lofty.config import settings
from lofty.models.job import GenerationJob, JobStatus
from lofty.models.user import User
from lofty.schemas.job import JobCreate

logger = structlog.get_logger()

_redis = aioredis.from_url(settings.redis_url, decode_responses=True)


async def has_active_job(db: AsyncSession, user: User) -> bool:
    """Check if the user has any active (pending/queued/running) job."""
    result = await db.execute(
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
    return result.scalar_one() > 0


async def create_job(
    db: AsyncSession,
    user: User,
    job_data: JobCreate,
) -> GenerationJob:
    """Create a new generation job and dispatch it to the Celery queue."""
    job = GenerationJob(
        user_id=user.id,
        status=JobStatus.PENDING.value,
        prompt=job_data.prompt,
        duration_seconds=job_data.duration_seconds,
        model_name=job_data.model_name,
        generation_params=job_data.generation_params.model_dump(),
    )
    db.add(job)

    # Commit BEFORE dispatching to Celery so the worker can find the job
    await db.commit()

    # Dispatch to Celery
    from lofty.worker.celery_app import celery_app

    try:
        task = celery_app.send_task(
            "lofty.worker.tasks.generate_music",
            args=[str(job.id)],
            queue="gpu",
        )
        job.celery_task_id = task.id
        job.status = JobStatus.QUEUED.value
        await db.commit()
    except Exception:
        logger.exception("Failed to dispatch Celery task for job %s", job.id)
        job.status = JobStatus.FAILED.value
        job.error_message = "Failed to queue generation task. Please try again."
        await db.commit()
        raise

    return job


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
) -> GenerationJob | None:
    """Cancel a pending, queued, or running job."""
    job = await get_job(db, job_id, user)
    if job is None:
        return None

    cancellable = (JobStatus.PENDING.value, JobStatus.QUEUED.value, JobStatus.RUNNING.value)
    if job.status in cancellable:
        if job.status == JobStatus.RUNNING.value:
            # Signal cancellation via Redis flag — worker checks this during generation
            await _redis.setex(f"job_cancel:{job_id}", 600, "1")
        else:
            # For pending/queued: just revoke the Celery task
            job.status = JobStatus.CANCELLED.value
            await db.commit()
            if job.celery_task_id:
                from lofty.worker.celery_app import celery_app
                celery_app.control.revoke(job.celery_task_id, terminate=False)

    return job


async def delete_job(
    db: AsyncSession,
    job_id: str,
    user: User,
) -> bool:
    """Delete a job record. Cancels it first if still active."""
    job = await get_job(db, job_id, user)
    if job is None:
        return False

    # Cancel if still active
    active = (JobStatus.PENDING.value, JobStatus.QUEUED.value, JobStatus.RUNNING.value)
    if job.status in active:
        if job.status == JobStatus.RUNNING.value:
            await _redis.setex(f"job_cancel:{str(job.id)}", 600, "1")
        elif job.celery_task_id:
            from lofty.worker.celery_app import celery_app
            celery_app.control.revoke(job.celery_task_id, terminate=False)

    await db.delete(job)
    await db.commit()
    return True


def calculate_pages(total: int, per_page: int) -> int:
    """Calculate total number of pages."""
    return max(1, math.ceil(total / per_page))

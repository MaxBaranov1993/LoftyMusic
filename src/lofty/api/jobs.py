"""Job endpoints: create, list, get, cancel."""

import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from lofty.auth.clerk import get_current_user
from lofty.db.session import get_async_session
from lofty.dependencies import get_redis, rate_limit
from lofty.models.user import User
from lofty.schemas.job import JobCreate, JobResponse, JobStatus, PaginatedJobResponse
from lofty.services import job_service

logger = structlog.get_logger()

router = APIRouter(prefix="/jobs", tags=["Jobs"])


async def _enrich_progress_batch(items: list[JobResponse]) -> None:
    """Batch-fill progress from Redis for all running jobs in one MGET call."""
    running_indices: list[int] = []
    keys: list[str] = []

    for i, item in enumerate(items):
        if item.status == "completed":
            item.progress = 100
        elif item.status == "running":
            running_indices.append(i)
            keys.append(f"job_progress:{item.id}")

    if not keys:
        return

    redis = await get_redis()
    values = await redis.mget(keys)

    for idx, raw in zip(running_indices, values):
        items[idx].progress = int(raw) if raw else 0


@router.post("", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
async def create_generation_job(
    job_data: JobCreate,
    user: User = Depends(rate_limit),
    db: AsyncSession = Depends(get_async_session),
) -> JobResponse:
    """Create a new music generation job.

    The job is queued for processing by a GPU worker.
    Poll GET /jobs/{id} to check the status.
    """
    # create_job handles the active-job check atomically under a distributed lock
    try:
        job = await job_service.create_job(db, user, job_data)
    except HTTPException:
        raise  # 409 from create_job passes through
    except Exception:
        logger.exception("Failed to create generation job")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Music generation service is temporarily unavailable. Please try again.",
        )
    return JobResponse(
        id=job.id,
        status=job.status,
        prompt=job.prompt,
        lyrics=job.lyrics,
        duration_seconds=job.duration_seconds,
        model_name=job.model_name,
        generation_params=job.generation_params,
        lora_adapter_id=job.lora_adapter_id,
        error_message=job.error_message,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        track=None,
    )


@router.get("", response_model=PaginatedJobResponse)
async def list_jobs(
    status_filter: JobStatus | None = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
) -> PaginatedJobResponse:
    """List the current user's generation jobs."""
    status_value = status_filter.value if status_filter is not None else None
    jobs, total = await job_service.list_jobs(db, user, status_value, page, per_page)

    # Sync results from Redis → DB for non-terminal jobs
    from lofty.services.result_sync import sync_job_result

    for job in jobs:
        if job.status not in ("completed", "failed", "cancelled"):
            await sync_job_result(db, job)

    # Re-read after sync to pick up track data
    jobs, total = await job_service.list_jobs(db, user, status_value, page, per_page)
    items = [JobResponse.model_validate(j) for j in jobs]
    await _enrich_progress_batch(items)
    return PaginatedJobResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        pages=job_service.calculate_pages(total, per_page),
    )


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
) -> JobResponse:
    """Get a specific job by ID."""
    job = await job_service.get_job(db, str(job_id), user)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    # Sync results from Redis → DB (for remote workers that don't have DB access)
    if job.status not in ("completed", "failed", "cancelled"):
        from lofty.services.result_sync import sync_job_result

        synced = await sync_job_result(db, job)
        if synced:
            # Re-read with track loaded
            job = await job_service.get_job(db, str(job_id), user)
            if job is None:
                raise HTTPException(status_code=404, detail="Job not found")

    response = JobResponse.model_validate(job)
    await _enrich_progress_batch([response])
    return response


@router.post("/{job_id}/cancel", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_job(
    job_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
) -> None:
    """Cancel a pending, queued, or running job."""
    job, was_cancelled = await job_service.cancel_job(db, str(job_id), user)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if not was_cancelled:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Job is already {job.status} and cannot be cancelled",
        )


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(
    job_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
) -> None:
    """Delete a job record."""
    deleted = await job_service.delete_job(db, str(job_id), user)
    if not deleted:
        raise HTTPException(status_code=404, detail="Job not found")

"""Job endpoints: create, list, get, cancel."""

import uuid

import redis.asyncio as aioredis
import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from lofty.auth.clerk import get_current_user
from lofty.config import settings
from lofty.db.session import get_async_session
from lofty.dependencies import rate_limit
from lofty.models.user import User
from lofty.schemas.job import JobCreate, JobResponse, JobStatus, PaginatedJobResponse
from lofty.services import job_service

logger = structlog.get_logger()

router = APIRouter(prefix="/jobs", tags=["Jobs"])

_redis = aioredis.from_url(settings.redis_url, decode_responses=True)


def _progress_key(job_id: str) -> str:
    return f"job_progress:{job_id}"


async def _enrich_progress(job_response: JobResponse) -> JobResponse:
    """Fill in progress from Redis for running jobs."""
    if job_response.status == "running":
        raw = await _redis.get(_progress_key(str(job_response.id)))
        job_response.progress = int(raw) if raw else 0
    elif job_response.status == "completed":
        job_response.progress = 100
    return job_response


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
    # Only allow one active job at a time
    has_active = await job_service.has_active_job(db, user)
    if has_active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You already have an active generation job. Please wait for it to finish.",
        )

    try:
        job = await job_service.create_job(db, user, job_data)
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
        duration_seconds=job.duration_seconds,
        model_name=job.model_name,
        generation_params=job.generation_params,
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
    items = [JobResponse.model_validate(j) for j in jobs]
    for item in items:
        await _enrich_progress(item)
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
    response = JobResponse.model_validate(job)
    await _enrich_progress(response)
    return response


@router.post("/{job_id}/cancel", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_job(
    job_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
) -> None:
    """Cancel a pending, queued, or running job."""
    job = await job_service.cancel_job(db, str(job_id), user)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")


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

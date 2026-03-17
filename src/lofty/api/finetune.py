"""Fine-tuning and LoRA adapter endpoints."""

import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from lofty.auth.clerk import get_current_user
from lofty.db.session import get_async_session
from lofty.models.user import User
from lofty.schemas.finetune import (
    FineTuneCreate,
    FineTuneJobResponse,
    LoRAAdapterResponse,
    PaginatedAdapterResponse,
    PaginatedFineTuneResponse,
)
from lofty.services import finetune_service
from lofty.services.job_service import calculate_pages

logger = structlog.get_logger()

router = APIRouter(prefix="/finetune", tags=["Fine-Tuning"])


@router.post("", response_model=FineTuneJobResponse, status_code=status.HTTP_201_CREATED)
async def create_finetune_job(
    data: FineTuneCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
) -> FineTuneJobResponse:
    """Start a new fine-tuning job.

    Requires a processed dataset (status='ready').
    Only one active fine-tuning job per user is allowed.
    """
    job = await finetune_service.create_finetune_job(db, user, data)
    return FineTuneJobResponse.model_validate(job)


@router.get("", response_model=PaginatedFineTuneResponse)
async def list_finetune_jobs(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
) -> PaginatedFineTuneResponse:
    """List the current user's fine-tuning jobs."""
    jobs, total = await finetune_service.list_finetune_jobs(db, user, page, per_page)

    # Sync active job results from Redis (for Colab workers)
    from lofty.services.result_sync import sync_finetune_result
    for job in jobs:
        if job.status not in ("completed", "failed", "cancelled"):
            await sync_finetune_result(db, job)

    return PaginatedFineTuneResponse(
        items=[FineTuneJobResponse.model_validate(j) for j in jobs],
        total=total,
        page=page,
        per_page=per_page,
        pages=calculate_pages(total, per_page),
    )


@router.get("/{job_id}", response_model=FineTuneJobResponse)
async def get_finetune_job(
    job_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
) -> FineTuneJobResponse:
    """Get a fine-tuning job with its adapter (if completed)."""
    job = await finetune_service.get_finetune_job(db, str(job_id), user)
    if job is None:
        raise HTTPException(status_code=404, detail="Fine-tuning job not found")

    # Sync result from Redis (for Colab workers that don't write to DB)
    from lofty.services.result_sync import sync_finetune_result
    await sync_finetune_result(db, job)
    await db.refresh(job)

    return FineTuneJobResponse.model_validate(job)


@router.post("/{job_id}/cancel", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_finetune_job(
    job_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
) -> None:
    """Cancel a pending or running fine-tuning job."""
    job, was_cancelled = await finetune_service.cancel_finetune_job(db, str(job_id), user)
    if job is None:
        raise HTTPException(status_code=404, detail="Fine-tuning job not found")
    if not was_cancelled:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Job is already {job.status} and cannot be cancelled",
        )


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_finetune_job(
    job_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
) -> None:
    """Delete a fine-tuning job (only if completed, failed, or cancelled)."""
    job = await finetune_service.get_finetune_job(db, str(job_id), user)
    if job is None:
        raise HTTPException(status_code=404, detail="Fine-tuning job not found")
    if job.status in ("pending", "queued", "running"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete an active job. Cancel it first.",
        )
    # Delete adapter if exists
    if job.adapter:
        await finetune_service.delete_adapter(db, str(job.adapter.id), user)
    await db.delete(job)
    await db.commit()


# --- LoRA Adapters ---

adapters_router = APIRouter(prefix="/adapters", tags=["LoRA Adapters"])


@adapters_router.get("", response_model=PaginatedAdapterResponse)
async def list_adapters(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
) -> PaginatedAdapterResponse:
    """List the current user's LoRA adapters."""
    adapters, total = await finetune_service.list_adapters(db, user, page, per_page)
    return PaginatedAdapterResponse(
        items=[LoRAAdapterResponse.model_validate(a) for a in adapters],
        total=total,
        page=page,
        per_page=per_page,
        pages=calculate_pages(total, per_page),
    )


@adapters_router.get("/{adapter_id}", response_model=LoRAAdapterResponse)
async def get_adapter(
    adapter_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
) -> LoRAAdapterResponse:
    """Get a specific LoRA adapter."""
    adapter = await finetune_service.get_adapter(db, str(adapter_id), user)
    if adapter is None:
        raise HTTPException(status_code=404, detail="Adapter not found")
    return LoRAAdapterResponse.model_validate(adapter)


@adapters_router.delete("/{adapter_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_adapter(
    adapter_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
) -> None:
    """Delete a LoRA adapter (removes from S3 and marks inactive)."""
    deleted = await finetune_service.delete_adapter(db, str(adapter_id), user)
    if not deleted:
        raise HTTPException(status_code=404, detail="Adapter not found")

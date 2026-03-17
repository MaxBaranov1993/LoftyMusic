"""Fine-tuning service: job management and Celery dispatch."""

import structlog
from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from lofty.models.dataset import Dataset
from lofty.models.finetune import FineTuneJob, LoRAAdapter
from lofty.models.user import User
from lofty.schemas.finetune import FineTuneCreate

logger = structlog.get_logger()


async def create_finetune_job(
    db: AsyncSession,
    user: User,
    data: FineTuneCreate,
) -> FineTuneJob:
    """Create and dispatch a fine-tuning job.

    Prepares all dataset/track data up front so the Celery task
    can run without database access (Colab-compatible).
    """
    from lofty.models.dataset import DatasetTrack
    from lofty.models.upload import AudioUpload

    # Verify dataset ownership and readiness
    result = await db.execute(
        select(Dataset).where(
            Dataset.id == str(data.dataset_id),
            Dataset.user_id == user.id,
        )
    )
    dataset = result.scalar_one_or_none()
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    if dataset.status != "ready":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Dataset must be in 'ready' state, currently '{dataset.status}'. "
            "Please process the dataset first.",
        )
    if dataset.num_tracks < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Dataset must have at least 1 track.",
        )

    # Check for active finetune jobs
    active_count_result = await db.execute(
        select(func.count())
        .select_from(FineTuneJob)
        .where(
            FineTuneJob.user_id == user.id,
            FineTuneJob.status.in_(["pending", "queued", "running"]),
        )
    )
    if active_count_result.scalar_one() > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You already have an active fine-tuning job. Please wait for it to finish.",
        )

    # Prepare track data so the worker doesn't need DB access
    tracks_result = await db.execute(
        select(DatasetTrack).where(DatasetTrack.dataset_id == str(data.dataset_id))
    )
    tracks = list(tracks_result.scalars().all())

    track_data = []
    for t in tracks:
        upload_result = await db.execute(select(AudioUpload).where(AudioUpload.id == t.upload_id))
        upload = upload_result.scalar_one_or_none()
        if upload is None:
            continue
        track_data.append(
            {
                "storage_key": upload.storage_key,
                "original_filename": upload.original_filename,
                "format": upload.format,
                "lyrics": t.lyrics or "",
                "caption": t.caption or "",
                "bpm": t.bpm,
                "key_scale": t.key_scale,
                "duration_seconds": t.duration_seconds,
            }
        )

    logger.info(
        "finetune_job.creating",
        compute_mode_raw=data.compute_mode,
        compute_mode_value=data.compute_mode.value,
    )
    job = FineTuneJob(
        user_id=user.id,
        dataset_id=data.dataset_id,
        name=data.name,
        config=data.config.model_dump(),
        compute_mode=data.compute_mode.value,
        status="pending",
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    await db.refresh(job, attribute_names=["adapter"])

    # Route by compute_mode:
    #   CPU → dispatch to local Celery worker immediately
    #   GPU → stay PENDING for Colab/cloud worker (HTTP polling)
    if data.compute_mode.value == "cpu":
        try:
            from lofty.worker.celery_app import celery_app

            celery_app.send_task(
                "lofty.worker.tasks.finetune_model",
                args=[str(job.id)],
                kwargs={
                    "job_name": job.name,
                    "track_data": track_data,
                    "config": data.config.model_dump(),
                    "user_id": str(user.id),
                },
                queue="training",
            )
            logger.info("finetune_job.dispatched_to_celery", job_id=str(job.id), mode="cpu")
        except Exception:
            logger.exception("Failed to dispatch CPU finetune job to Celery")

    logger.info(
        "finetune_job.created",
        job_id=str(job.id),
        tracks=len(track_data),
        method=data.config.training_method,
    )

    return job


async def get_finetune_job(
    db: AsyncSession,
    job_id: str,
    user: User,
) -> FineTuneJob | None:
    """Get a finetune job by ID with adapter, scoped to user."""
    result = await db.execute(
        select(FineTuneJob)
        .options(selectinload(FineTuneJob.adapter))
        .where(
            FineTuneJob.id == job_id,
            FineTuneJob.user_id == user.id,
        )
    )
    return result.scalar_one_or_none()


async def list_finetune_jobs(
    db: AsyncSession,
    user: User,
    page: int = 1,
    per_page: int = 20,
) -> tuple[list[FineTuneJob], int]:
    """List finetune jobs for a user with pagination."""
    query = (
        select(FineTuneJob)
        .options(selectinload(FineTuneJob.adapter))
        .where(FineTuneJob.user_id == user.id)
        .order_by(FineTuneJob.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    count_query = (
        select(func.count()).select_from(FineTuneJob).where(FineTuneJob.user_id == user.id)
    )

    result = await db.execute(query)
    jobs = list(result.scalars().all())

    count_result = await db.execute(count_query)
    total = count_result.scalar_one()

    return jobs, total


async def cancel_finetune_job(
    db: AsyncSession,
    job_id: str,
    user: User,
) -> tuple[FineTuneJob | None, bool]:
    """Cancel a finetune job. Returns (job, was_cancelled)."""
    job = await get_finetune_job(db, job_id, user)
    if job is None:
        return None, False

    if job.status not in ("pending", "queued", "running"):
        return job, False

    if job.status == "running":
        # Signal cancellation via Redis (worker polls this)
        from lofty.dependencies import get_redis

        redis = await get_redis()
        await redis.setex(f"finetune_cancel:{job_id}", 600, "1")
    else:
        job.status = "cancelled"
        await db.commit()

    return job, True


async def list_adapters(
    db: AsyncSession,
    user: User,
    page: int = 1,
    per_page: int = 20,
) -> tuple[list[LoRAAdapter], int]:
    """List LoRA adapters for a user."""
    query = (
        select(LoRAAdapter)
        .where(LoRAAdapter.user_id == user.id, LoRAAdapter.is_active.is_(True))
        .order_by(LoRAAdapter.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    count_query = (
        select(func.count())
        .select_from(LoRAAdapter)
        .where(LoRAAdapter.user_id == user.id, LoRAAdapter.is_active.is_(True))
    )

    result = await db.execute(query)
    adapters = list(result.scalars().all())

    count_result = await db.execute(count_query)
    total = count_result.scalar_one()

    return adapters, total


async def get_adapter(
    db: AsyncSession,
    adapter_id: str,
    user: User,
) -> LoRAAdapter | None:
    """Get an adapter by ID, scoped to user."""
    result = await db.execute(
        select(LoRAAdapter).where(
            LoRAAdapter.id == adapter_id,
            LoRAAdapter.user_id == user.id,
        )
    )
    return result.scalar_one_or_none()


async def delete_adapter(
    db: AsyncSession,
    adapter_id: str,
    user: User,
) -> bool:
    """Soft-delete an adapter (mark inactive) and clean up S3."""
    import asyncio

    from lofty.services.storage import storage_client

    adapter = await get_adapter(db, adapter_id, user)
    if adapter is None:
        return False

    # Delete from S3
    try:
        await asyncio.to_thread(storage_client.delete_object, adapter.storage_key)
    except Exception:
        logger.warning("Failed to delete adapter from S3", storage_key=adapter.storage_key)

    adapter.is_active = False
    await db.commit()
    return True

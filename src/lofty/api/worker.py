"""Worker API: endpoints for Colab GPU workers (HTTP polling, no Celery)."""

import asyncio
import uuid
from datetime import datetime, timezone

import structlog
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from lofty.config import settings
from lofty.db.session import get_async_session
from lofty.models.job import GenerationJob, JobStatus
from lofty.models.track import Track
from lofty.models.finetune import FineTuneJob

logger = structlog.get_logger()

router = APIRouter(prefix="/worker", tags=["worker"])

_bearer = HTTPBearer()


async def verify_worker_key(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> None:
    """Verify the shared worker API key."""
    if not settings.worker_api_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Worker API key not configured on server",
        )
    if credentials.credentials != settings.worker_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid worker API key",
        )


# --- Schemas ---

class WorkerJobResponse(BaseModel):
    job_id: uuid.UUID
    user_id: uuid.UUID
    prompt: str
    lyrics: str
    duration_seconds: float
    model_name: str
    generation_params: dict
    lora_adapter_id: uuid.UUID | None
    compute_mode: str = "gpu"


class ProgressRequest(BaseModel):
    progress: int


class CancelledResponse(BaseModel):
    cancelled: bool


# --- Endpoints ---

@router.get("/next-job", response_model=WorkerJobResponse, responses={204: {"description": "No pending jobs"}})
async def next_job(
    engine: str | None = None,
    compute_mode: str | None = None,
    _: None = Depends(verify_worker_key),
    db: AsyncSession = Depends(get_async_session),
):
    """Claim the next pending job atomically.

    Uses SELECT ... FOR UPDATE SKIP LOCKED to safely handle
    concurrent workers without race conditions.

    Args:
        engine: Optional engine filter. "ace-step" returns only ACE-Step jobs,
                "yue" returns only YuE jobs. If omitted, returns any pending job.
    """
    query = (
        select(GenerationJob)
        .where(GenerationJob.status == JobStatus.PENDING.value)
        .order_by(GenerationJob.created_at.asc())
        .limit(1)
        .with_for_update(skip_locked=True)
    )

    # Filter by engine type when specified
    if engine == "yue":
        query = query.where(GenerationJob.model_name.like("yue%"))
    elif engine == "ace-step":
        query = query.where(GenerationJob.model_name.like("ace-step%"))

    # Filter by compute mode when specified
    if compute_mode in ("cpu", "gpu"):
        query = query.where(GenerationJob.compute_mode == compute_mode)

    result = await db.execute(query)
    job = result.scalar_one_or_none()

    if job is None:
        from fastapi.responses import Response
        return Response(status_code=204)

    # Claim it
    job.status = JobStatus.RUNNING.value
    job.started_at = datetime.now(timezone.utc)
    await db.commit()

    logger.info("worker.job_claimed", job_id=str(job.id), prompt=job.prompt[:60])

    return WorkerJobResponse(
        job_id=job.id,
        user_id=job.user_id,
        prompt=job.prompt,
        lyrics=job.lyrics or "",
        duration_seconds=job.duration_seconds,
        model_name=job.model_name,
        generation_params=job.generation_params or {},
        lora_adapter_id=job.lora_adapter_id,
        compute_mode=job.compute_mode or "gpu",
    )


@router.post("/{job_id}/result")
async def upload_result(
    job_id: uuid.UUID,
    status_str: str = Form(..., alias="status"),
    duration: float = Form(0.0),
    sample_rate: int = Form(44100),
    format: str = Form("wav"),
    error_message: str = Form(""),
    audio_file: UploadFile | None = File(None),
    _: None = Depends(verify_worker_key),
    db: AsyncSession = Depends(get_async_session),
):
    """Receive generation result from worker."""
    result = await db.execute(
        select(GenerationJob).where(GenerationJob.id == job_id)
    )
    job = result.scalar_one_or_none()
    if job is None:
        raise HTTPException(404, "Job not found")

    now = datetime.now(timezone.utc)

    if status_str == "completed" and audio_file is not None:
        # Read audio bytes
        audio_bytes = await audio_file.read()

        # Store in MinIO
        from lofty.services.storage import storage_client

        storage_key = f"tracks/{job.user_id}/{job.id}.{format}"
        content_type = f"audio/{format}"

        file_size = await asyncio.to_thread(
            storage_client.upload_bytes, storage_key, audio_bytes, content_type
        )

        # Create Track record
        track = Track(
            job_id=job.id,
            user_id=job.user_id,
            title=job.prompt[:100],
            storage_key=storage_key,
            file_size_bytes=file_size,
            duration_seconds=duration,
            sample_rate=sample_rate,
            format=format,
        )
        db.add(track)

        job.status = JobStatus.COMPLETED.value
        job.completed_at = now
        await db.commit()

        logger.info("worker.job_completed", job_id=str(job_id), duration=duration)

    elif status_str == "failed":
        job.status = JobStatus.FAILED.value
        job.error_message = (error_message or "Generation failed")[:500]
        job.completed_at = now
        await db.commit()
        logger.info("worker.job_failed", job_id=str(job_id), error=error_message[:100])

    elif status_str == "cancelled":
        job.status = JobStatus.CANCELLED.value
        job.completed_at = now
        await db.commit()
        logger.info("worker.job_cancelled", job_id=str(job_id))

    return {"status": "ok"}


@router.post("/{job_id}/progress")
async def report_progress(
    job_id: uuid.UUID,
    body: ProgressRequest,
    _: None = Depends(verify_worker_key),
):
    """Report generation progress (stored in Redis for frontend polling)."""
    try:
        from lofty.dependencies import get_redis
        redis = await get_redis()
        await redis.setex(f"job_progress:{job_id}", 300, str(body.progress))
    except Exception:
        pass  # Progress reporting is best-effort
    return {"status": "ok"}


@router.get("/{job_id}/cancelled", response_model=CancelledResponse)
async def check_cancelled(
    job_id: uuid.UUID,
    _: None = Depends(verify_worker_key),
    db: AsyncSession = Depends(get_async_session),
):
    """Check if a job has been cancelled by the user."""
    # Check Redis flag first (set by cancel_job)
    try:
        from lofty.dependencies import get_redis
        redis = await get_redis()
        flag = await redis.get(f"job_cancel:{job_id}")
        if flag:
            return CancelledResponse(cancelled=True)
    except Exception:
        pass

    # Fallback: check DB
    result = await db.execute(
        select(GenerationJob.status).where(GenerationJob.id == job_id)
    )
    row = result.scalar_one_or_none()
    return CancelledResponse(cancelled=row == JobStatus.CANCELLED.value)


# --- Fine-Tune Worker Endpoints ---

class WorkerFineTuneJobResponse(BaseModel):
    job_id: uuid.UUID
    user_id: uuid.UUID
    job_name: str
    track_data: list[dict]
    config: dict
    compute_mode: str = "gpu"


@router.get(
    "/next-finetune-job",
    response_model=WorkerFineTuneJobResponse,
    responses={204: {"description": "No pending finetune jobs"}},
)
async def next_finetune_job(
    compute_mode: str | None = None,
    _: None = Depends(verify_worker_key),
    db: AsyncSession = Depends(get_async_session),
):
    """Claim the next pending/queued finetune job for the HTTP worker.

    Loads all dataset track data so the worker can train without DB access.
    """
    from lofty.models.dataset import DatasetTrack
    from lofty.models.upload import AudioUpload

    query = (
        select(FineTuneJob)
        .where(FineTuneJob.status.in_(["pending", "queued"]))
        .order_by(FineTuneJob.created_at.asc())
        .limit(1)
        .with_for_update(skip_locked=True)
    )

    # Filter by compute mode when specified
    if compute_mode in ("cpu", "gpu"):
        query = query.where(FineTuneJob.compute_mode == compute_mode)

    result = await db.execute(query)
    job = result.scalar_one_or_none()

    if job is None:
        from fastapi.responses import Response
        return Response(status_code=204)

    # Claim it
    job.status = "running"
    job.started_at = datetime.now(timezone.utc)

    # Load track data for the worker
    tracks_result = await db.execute(
        select(DatasetTrack).where(DatasetTrack.dataset_id == str(job.dataset_id))
    )
    tracks = list(tracks_result.scalars().all())

    track_data = []
    for t in tracks:
        upload_result = await db.execute(
            select(AudioUpload).where(AudioUpload.id == t.upload_id)
        )
        upload = upload_result.scalar_one_or_none()
        if upload is None:
            continue
        track_data.append({
            "storage_key": upload.storage_key,
            "original_filename": upload.original_filename,
            "format": upload.format,
            "lyrics": t.lyrics or "",
            "caption": t.caption or "",
            "bpm": t.bpm,
            "key_scale": t.key_scale,
            "duration_seconds": t.duration_seconds,
        })

    await db.commit()

    logger.info("worker.finetune_claimed", job_id=str(job.id), tracks=len(track_data))

    return WorkerFineTuneJobResponse(
        job_id=job.id,
        user_id=job.user_id,
        job_name=job.name,
        track_data=track_data,
        config=job.config or {},
        compute_mode=job.compute_mode or "gpu",
    )


@router.post("/{job_id}/finetune-progress")
async def report_finetune_progress(
    job_id: uuid.UUID,
    body: ProgressRequest,
    _: None = Depends(verify_worker_key),
    db: AsyncSession = Depends(get_async_session),
):
    """Report fine-tune training progress."""
    # Update Redis for fast polling
    try:
        from lofty.dependencies import get_redis
        redis = await get_redis()
        await redis.setex(f"finetune_progress:{job_id}", 3600, str(body.progress))
    except Exception:
        pass

    # Also update DB directly
    result = await db.execute(
        select(FineTuneJob).where(FineTuneJob.id == job_id)
    )
    job = result.scalar_one_or_none()
    if job and job.status == "running":
        job.progress = body.progress
        await db.commit()

    return {"status": "ok"}


@router.post("/{job_id}/finetune-result")
async def upload_finetune_result(
    job_id: uuid.UUID,
    status_str: str = Form(..., alias="status"),
    training_method: str = Form("lokr"),
    num_tracks: int = Form(0),
    error_message: str = Form(""),
    adapter_file: UploadFile | None = File(None),
    _: None = Depends(verify_worker_key),
    db: AsyncSession = Depends(get_async_session),
):
    """Receive fine-tune result from worker.

    On success: uploads adapter file to S3, creates LoRAAdapter record.
    On failure: records error message.
    """
    from lofty.models.finetune import LoRAAdapter
    from lofty.services.storage import storage_client

    result = await db.execute(
        select(FineTuneJob).where(FineTuneJob.id == job_id)
    )
    job = result.scalar_one_or_none()
    if job is None:
        raise HTTPException(404, "Finetune job not found")

    now = datetime.now(timezone.utc)

    if status_str == "completed" and adapter_file is not None:
        adapter_bytes = await adapter_file.read()

        # Store in MinIO
        adapter_storage_key = f"adapters/{job.user_id}/{job.id}/"
        s3_key = adapter_storage_key + "adapter_model.safetensors"

        file_size = await asyncio.to_thread(
            storage_client.upload_bytes, s3_key, adapter_bytes, "application/octet-stream"
        )

        # Create LoRA adapter record
        adapter = LoRAAdapter(
            user_id=job.user_id,
            finetune_job_id=job.id,
            name=job.name,
            description=f"Fine-tuned with {num_tracks} tracks",
            storage_key=adapter_storage_key,
            adapter_size_bytes=file_size,
            base_model=settings.ace_step_model_path,
            training_method=training_method,
        )
        db.add(adapter)

        job.status = "completed"
        job.progress = 100
        job.completed_at = now
        await db.commit()

        logger.info("worker.finetune_completed", job_id=str(job_id), size=file_size)

    elif status_str == "failed":
        job.status = "failed"
        job.error_message = (error_message or "Training failed")[:500]
        job.completed_at = now
        await db.commit()
        logger.info("worker.finetune_failed", job_id=str(job_id), error=error_message[:100])

    elif status_str == "cancelled":
        job.status = "cancelled"
        job.completed_at = now
        await db.commit()

    return {"status": "ok"}


@router.get("/{job_id}/finetune-cancelled", response_model=CancelledResponse)
async def check_finetune_cancelled(
    job_id: uuid.UUID,
    _: None = Depends(verify_worker_key),
    db: AsyncSession = Depends(get_async_session),
):
    """Check if a finetune job has been cancelled."""
    try:
        from lofty.dependencies import get_redis
        redis = await get_redis()
        flag = await redis.get(f"finetune_cancel:{job_id}")
        if flag:
            return CancelledResponse(cancelled=True)
    except Exception:
        pass

    result = await db.execute(
        select(FineTuneJob.status).where(FineTuneJob.id == job_id)
    )
    row = result.scalar_one_or_none()
    return CancelledResponse(cancelled=row == "cancelled")


@router.get("/download/{storage_key:path}")
async def download_storage_file(
    storage_key: str,
    _: None = Depends(verify_worker_key),
):
    """Download a file from S3 storage (for worker to fetch dataset tracks).

    Proxies the file through the API so remote workers (Colab) don't need
    direct access to MinIO.
    """
    from fastapi.responses import Response
    from lofty.services.storage import storage_client

    try:
        response = await asyncio.to_thread(
            storage_client._client.get_object,
            Bucket=storage_client._bucket,
            Key=storage_key,
        )
        data = await asyncio.to_thread(response["Body"].read)
        content_type = response.get("ContentType", "application/octet-stream")
        return Response(content=data, media_type=content_type)
    except Exception as exc:
        raise HTTPException(500, f"Failed to download file: {exc}")

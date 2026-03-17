"""Audio upload endpoints for fine-tuning training data."""

import io
import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from lofty.auth.clerk import get_current_user
from lofty.db.session import get_async_session
from lofty.models.user import User
from lofty.schemas.upload import PaginatedUploadResponse, UploadResponse
from lofty.services import upload_service
from lofty.services.job_service import calculate_pages

logger = structlog.get_logger()

router = APIRouter(prefix="/uploads", tags=["Uploads"])


def _probe_audio_duration(data: bytes, filename: str) -> float:
    """Get audio duration in seconds using soundfile or mutagen fallback."""
    try:
        import soundfile as sf

        info = sf.info(io.BytesIO(data))
        return info.duration
    except Exception:
        pass

    # Fallback: estimate from file size (rough, for WAV: size / (sample_rate * channels * bits/8))
    # Return 0 and let the analyzer fill it in later
    return 0.0


@router.post("", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_audio(
    file: UploadFile,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
) -> UploadResponse:
    """Upload an audio file for use in fine-tuning datasets.

    Accepted formats: WAV, MP3, FLAC, OGG. Max 50 MB.
    """
    # Validate content type
    content_type = file.content_type or ""
    audio_format = upload_service.get_format_from_content_type(content_type)
    if audio_format is None:
        # Try to infer from filename extension
        ext = (file.filename or "").rsplit(".", 1)[-1].lower() if file.filename else ""
        ext_map = {"wav": "wav", "mp3": "mp3", "flac": "flac", "ogg": "ogg"}
        audio_format = ext_map.get(ext)
        if audio_format is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported audio format. Accepted: WAV, MP3, FLAC, OGG.",
            )

    # Read file data
    data = await file.read()
    if len(data) > upload_service.MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=(
                f"File too large. Maximum size: {upload_service.MAX_FILE_SIZE // (1024 * 1024)} MB."
            ),
        )
    if len(data) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty file.",
        )

    # Probe duration
    duration = _probe_audio_duration(data, file.filename or "unknown")

    # Upload to S3
    import asyncio

    from lofty.services.storage import storage_client

    storage_key = f"uploads/{user.id}/{uuid.uuid4().hex}.{audio_format}"
    content_type_map = {
        "wav": "audio/wav",
        "mp3": "audio/mpeg",
        "flac": "audio/flac",
        "ogg": "audio/ogg",
    }
    await asyncio.to_thread(
        storage_client.upload_bytes,
        storage_key,
        data,
        content_type_map.get(audio_format, "application/octet-stream"),
    )

    # Create DB record
    upload = await upload_service.create_upload(
        db,
        user,
        storage_key=storage_key,
        original_filename=file.filename or "unknown",
        file_size_bytes=len(data),
        duration_seconds=duration,
        audio_format=audio_format,
    )

    # Dispatch auto-analysis task (non-blocking, DB-free)
    try:
        from lofty.worker.celery_app import celery_app

        celery_app.send_task(
            "lofty.worker.tasks.analyze_audio",
            args=[str(upload.id)],
            kwargs={
                "storage_key": storage_key,
                "audio_format": audio_format,
            },
            queue="gpu",
        )
    except Exception:
        logger.warning("Failed to dispatch audio analysis task", upload_id=str(upload.id))

    return UploadResponse.model_validate(upload)


@router.get("", response_model=PaginatedUploadResponse)
async def list_uploads(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
) -> PaginatedUploadResponse:
    """List the current user's audio uploads."""
    uploads, total = await upload_service.list_uploads(db, user, page, per_page)

    # Sync pending analysis results from Redis (for Colab workers)
    from lofty.services.result_sync import sync_upload_analysis

    for upload in uploads:
        if upload.analysis is None:
            await sync_upload_analysis(db, upload)

    return PaginatedUploadResponse(
        items=[UploadResponse.model_validate(u) for u in uploads],
        total=total,
        page=page,
        per_page=per_page,
        pages=calculate_pages(total, per_page),
    )


@router.get("/{upload_id}", response_model=UploadResponse)
async def get_upload(
    upload_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
) -> UploadResponse:
    """Get a specific upload by ID."""
    upload = await upload_service.get_upload(db, str(upload_id), user)
    if upload is None:
        raise HTTPException(status_code=404, detail="Upload not found")

    # Sync analysis result from Redis (for Colab workers)
    from lofty.services.result_sync import sync_upload_analysis

    await sync_upload_analysis(db, upload)

    return UploadResponse.model_validate(upload)


@router.delete("/{upload_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_upload(
    upload_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
) -> None:
    """Delete an audio upload."""
    import asyncio

    from lofty.services.storage import storage_client

    upload = await upload_service.get_upload(db, str(upload_id), user)
    if upload is None:
        raise HTTPException(status_code=404, detail="Upload not found")

    # Delete from S3
    try:
        await asyncio.to_thread(storage_client.delete_object, upload.storage_key)
    except Exception:
        logger.warning("Failed to delete upload from S3", storage_key=upload.storage_key)

    deleted = await upload_service.delete_upload(db, str(upload_id), user)
    if not deleted:
        raise HTTPException(status_code=404, detail="Upload not found")

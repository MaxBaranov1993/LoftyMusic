"""Upload service: audio file upload and management."""

import structlog
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from lofty.models.dataset import DatasetTrack
from lofty.models.upload import AudioUpload
from lofty.models.user import User

logger = structlog.get_logger()

# Allowed audio MIME types → file extension
ALLOWED_CONTENT_TYPES = {
    "audio/wav": "wav",
    "audio/x-wav": "wav",
    "audio/wave": "wav",
    "audio/mpeg": "mp3",
    "audio/mp3": "mp3",
    "audio/flac": "flac",
    "audio/x-flac": "flac",
    "audio/ogg": "ogg",
    "audio/vorbis": "ogg",
}

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB
MAX_DURATION = 600.0  # 10 minutes


def get_format_from_content_type(content_type: str) -> str | None:
    """Map content type to audio format string."""
    return ALLOWED_CONTENT_TYPES.get(content_type)


async def create_upload(
    db: AsyncSession,
    user: User,
    *,
    storage_key: str,
    original_filename: str,
    file_size_bytes: int,
    duration_seconds: float,
    audio_format: str,
) -> AudioUpload:
    """Create an AudioUpload record."""
    upload = AudioUpload(
        user_id=user.id,
        storage_key=storage_key,
        original_filename=original_filename,
        file_size_bytes=file_size_bytes,
        duration_seconds=duration_seconds,
        format=audio_format,
    )
    db.add(upload)
    await db.commit()
    await db.refresh(upload)
    return upload


async def get_upload(
    db: AsyncSession,
    upload_id: str,
    user: User,
) -> AudioUpload | None:
    """Get an upload by ID, scoped to user."""
    result = await db.execute(
        select(AudioUpload).where(
            AudioUpload.id == upload_id,
            AudioUpload.user_id == user.id,
        )
    )
    return result.scalar_one_or_none()


async def list_uploads(
    db: AsyncSession,
    user: User,
    page: int = 1,
    per_page: int = 20,
) -> tuple[list[AudioUpload], int]:
    """List uploads for a user with pagination."""
    query = (
        select(AudioUpload)
        .where(AudioUpload.user_id == user.id)
        .order_by(AudioUpload.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    count_query = (
        select(func.count()).select_from(AudioUpload).where(AudioUpload.user_id == user.id)
    )

    result = await db.execute(query)
    uploads = list(result.scalars().all())

    count_result = await db.execute(count_query)
    total = count_result.scalar_one()

    return uploads, total


async def delete_upload(
    db: AsyncSession,
    upload_id: str,
    user: User,
) -> bool:
    """Delete an upload record and any referencing dataset tracks."""
    upload = await get_upload(db, upload_id, user)
    if upload is None:
        return False

    # Delete referencing dataset tracks first and flush to DB
    # before deleting the upload (FK constraint)
    await db.execute(delete(DatasetTrack).where(DatasetTrack.upload_id == upload.id))
    await db.flush()

    # Update dataset track counts
    from lofty.models.dataset import Dataset

    datasets_result = await db.execute(select(Dataset).where(Dataset.user_id == user.id))
    for ds in datasets_result.scalars().all():
        count_result = await db.execute(
            select(func.count()).select_from(DatasetTrack).where(DatasetTrack.dataset_id == ds.id)
        )
        ds.num_tracks = count_result.scalar_one()

    await db.delete(upload)
    await db.commit()
    return True

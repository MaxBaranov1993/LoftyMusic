"""Dataset service: CRUD and processing dispatch."""

import math

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from lofty.models.dataset import Dataset, DatasetTrack
from lofty.models.upload import AudioUpload
from lofty.models.user import User
from lofty.schemas.dataset import DatasetCreate, DatasetTrackCreate

logger = structlog.get_logger()


async def create_dataset(
    db: AsyncSession,
    user: User,
    data: DatasetCreate,
) -> Dataset:
    """Create a new dataset."""
    dataset = Dataset(
        user_id=user.id,
        name=data.name,
        description=data.description,
    )
    db.add(dataset)
    await db.commit()
    await db.refresh(dataset)
    # Eagerly load tracks for DatasetResponse serialization
    await db.refresh(dataset, attribute_names=["tracks"])
    return dataset


async def get_dataset(
    db: AsyncSession,
    dataset_id: str,
    user: User,
) -> Dataset | None:
    """Get a dataset by ID with tracks, scoped to user."""
    result = await db.execute(
        select(Dataset)
        .options(selectinload(Dataset.tracks))
        .where(
            Dataset.id == dataset_id,
            Dataset.user_id == user.id,
        )
    )
    return result.scalar_one_or_none()


async def list_datasets(
    db: AsyncSession,
    user: User,
    page: int = 1,
    per_page: int = 20,
) -> tuple[list[Dataset], int]:
    """List datasets for a user with pagination."""
    query = (
        select(Dataset)
        .options(selectinload(Dataset.tracks))
        .where(Dataset.user_id == user.id)
        .order_by(Dataset.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    count_query = (
        select(func.count())
        .select_from(Dataset)
        .where(Dataset.user_id == user.id)
    )

    result = await db.execute(query)
    datasets = list(result.scalars().all())

    count_result = await db.execute(count_query)
    total = count_result.scalar_one()

    return datasets, total


async def add_track_to_dataset(
    db: AsyncSession,
    user: User,
    dataset_id: str,
    track_data: DatasetTrackCreate,
) -> DatasetTrack | None:
    """Add a track to a dataset. Returns None if dataset or upload not found."""
    # Verify dataset ownership
    dataset = await get_dataset(db, dataset_id, user)
    if dataset is None:
        return None

    # Verify upload ownership
    upload_result = await db.execute(
        select(AudioUpload).where(
            AudioUpload.id == str(track_data.upload_id),
            AudioUpload.user_id == user.id,
        )
    )
    upload = upload_result.scalar_one_or_none()
    if upload is None:
        return None

    track = DatasetTrack(
        dataset_id=dataset.id,
        upload_id=upload.id,
        lyrics=track_data.lyrics,
        caption=track_data.caption,
        bpm=track_data.bpm,
        key_scale=track_data.key_scale,
        duration_seconds=upload.duration_seconds,
    )
    db.add(track)

    # Update dataset counters
    dataset.num_tracks += 1
    dataset.total_duration_seconds += upload.duration_seconds

    await db.commit()
    await db.refresh(track)
    return track


async def remove_track_from_dataset(
    db: AsyncSession,
    user: User,
    dataset_id: str,
    track_id: str,
) -> bool:
    """Remove a track from a dataset."""
    dataset = await get_dataset(db, dataset_id, user)
    if dataset is None:
        return False

    result = await db.execute(
        select(DatasetTrack).where(
            DatasetTrack.id == track_id,
            DatasetTrack.dataset_id == dataset.id,
        )
    )
    track = result.scalar_one_or_none()
    if track is None:
        return False

    dataset.num_tracks = max(0, dataset.num_tracks - 1)
    dataset.total_duration_seconds = max(0.0, dataset.total_duration_seconds - track.duration_seconds)

    await db.delete(track)
    await db.commit()
    return True


async def delete_dataset(
    db: AsyncSession,
    dataset_id: str,
    user: User,
) -> bool:
    """Delete a dataset and all its tracks (cascade)."""
    dataset = await get_dataset(db, dataset_id, user)
    if dataset is None:
        return False
    await db.delete(dataset)
    await db.commit()
    return True

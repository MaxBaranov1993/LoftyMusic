"""Dataset endpoints for fine-tuning training data management."""

import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from lofty.auth.clerk import get_current_user
from lofty.db.session import get_async_session
from lofty.models.user import User
from lofty.schemas.dataset import (
    DatasetCreate,
    DatasetResponse,
    DatasetTrackCreate,
    DatasetTrackResponse,
    PaginatedDatasetResponse,
)
from lofty.services import dataset_service
from lofty.services.job_service import calculate_pages

logger = structlog.get_logger()

router = APIRouter(prefix="/datasets", tags=["Datasets"])


@router.post("", response_model=DatasetResponse, status_code=status.HTTP_201_CREATED)
async def create_dataset(
    data: DatasetCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
) -> DatasetResponse:
    """Create a new dataset for fine-tuning."""
    dataset = await dataset_service.create_dataset(db, user, data)
    return DatasetResponse.model_validate(dataset)


@router.get("", response_model=PaginatedDatasetResponse)
async def list_datasets(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
) -> PaginatedDatasetResponse:
    """List the current user's datasets."""
    datasets, total = await dataset_service.list_datasets(db, user, page, per_page)

    # Sync processing results from Redis (for Colab workers)
    from lofty.services.result_sync import sync_dataset_result
    for ds in datasets:
        if ds.status == "processing":
            await sync_dataset_result(db, ds)

    return PaginatedDatasetResponse(
        items=[DatasetResponse.model_validate(d) for d in datasets],
        total=total,
        page=page,
        per_page=per_page,
        pages=calculate_pages(total, per_page),
    )


@router.get("/{dataset_id}", response_model=DatasetResponse)
async def get_dataset(
    dataset_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
) -> DatasetResponse:
    """Get a dataset with its tracks."""
    dataset = await dataset_service.get_dataset(db, str(dataset_id), user)
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found")

    # Sync processing result from Redis (for Colab workers)
    if dataset.status == "processing":
        from lofty.services.result_sync import sync_dataset_result
        await sync_dataset_result(db, dataset)
        await db.refresh(dataset)

    return DatasetResponse.model_validate(dataset)


@router.post(
    "/{dataset_id}/tracks",
    response_model=DatasetTrackResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_track(
    dataset_id: uuid.UUID,
    track_data: DatasetTrackCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
) -> DatasetTrackResponse:
    """Add a track to a dataset (links an existing upload)."""
    track = await dataset_service.add_track_to_dataset(
        db, user, str(dataset_id), track_data,
    )
    if track is None:
        raise HTTPException(
            status_code=404,
            detail="Dataset or upload not found (check ownership)",
        )
    return DatasetTrackResponse.model_validate(track)


@router.delete(
    "/{dataset_id}/tracks/{track_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_track(
    dataset_id: uuid.UUID,
    track_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
) -> None:
    """Remove a track from a dataset."""
    removed = await dataset_service.remove_track_from_dataset(
        db, user, str(dataset_id), str(track_id),
    )
    if not removed:
        raise HTTPException(status_code=404, detail="Dataset or track not found")


@router.post("/{dataset_id}/process", status_code=status.HTTP_202_ACCEPTED)
async def process_dataset(
    dataset_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
) -> dict:
    """Process dataset inline: extract duration from each track.

    No GPU worker needed — basic analysis (duration via soundfile) runs
    directly in the API process. The dataset status transitions:
    pending → processing → ready/failed.
    """
    import asyncio
    import io

    from sqlalchemy import select as sa_select

    from lofty.models.dataset import DatasetTrack
    from lofty.models.upload import AudioUpload
    from lofty.services.storage import storage_client

    dataset = await dataset_service.get_dataset(db, str(dataset_id), user)
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found")

    if dataset.num_tracks < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Dataset must have at least 1 track to process.",
        )

    if dataset.status not in ("pending", "failed"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Dataset is '{dataset.status}', can only process 'pending' or 'failed' datasets.",
        )

    dataset.status = "processing"
    await db.commit()

    # Load tracks and their uploads
    tracks_result = await db.execute(
        sa_select(DatasetTrack).where(DatasetTrack.dataset_id == str(dataset.id))
    )
    tracks = list(tracks_result.scalars().all())

    try:
        for track in tracks:
            upload_result = await db.execute(
                sa_select(AudioUpload).where(AudioUpload.id == track.upload_id)
            )
            upload = upload_result.scalar_one_or_none()
            if upload is None:
                track.status = "failed"
                continue

            # Download audio from S3 and extract duration
            try:
                response = await asyncio.to_thread(
                    storage_client._client.get_object,
                    Bucket=storage_client._bucket,
                    Key=upload.storage_key,
                )
                audio_bytes = await asyncio.to_thread(response["Body"].read)

                import soundfile as sf
                info = sf.info(io.BytesIO(audio_bytes))
                track.duration_seconds = info.duration
            except Exception:
                logger.warning("Failed to analyze track %s", track.id)

            track.status = "processed"

        # Update dataset totals
        dataset.total_duration_seconds = sum(t.duration_seconds for t in tracks)
        dataset.status = "ready"
        await db.commit()

        logger.info("dataset.processed_inline", dataset_id=str(dataset.id), tracks=len(tracks))
        return {"status": "ready", "dataset_id": str(dataset.id)}

    except Exception as exc:
        logger.exception("Dataset processing failed: %s", dataset_id)
        dataset.status = "failed"
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Processing failed: {str(exc)[:200]}",
        )


@router.delete("/{dataset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_dataset(
    dataset_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
) -> None:
    """Delete a dataset and all its tracks."""
    deleted = await dataset_service.delete_dataset(db, str(dataset_id), user)
    if not deleted:
        raise HTTPException(status_code=404, detail="Dataset not found")

"""Sync task results from Redis to the database.

The Celery worker stores generation/finetune/analysis results in Redis
(no DB access needed). This module reads those results and writes them
to PostgreSQL. Called from SSE and job polling endpoints.
"""

import json
from datetime import UTC

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from lofty.dependencies import get_redis
from lofty.models.job import GenerationJob, JobStatus
from lofty.models.track import Track

logger = structlog.get_logger()


async def sync_job_result(db: AsyncSession, job: GenerationJob) -> bool:
    """Check Redis for a completed task result and sync it to the database.

    Returns True if the job was updated (result found and synced).
    """
    # Only sync jobs that are still in a non-terminal state
    terminal = {JobStatus.COMPLETED.value, JobStatus.FAILED.value, JobStatus.CANCELLED.value}
    if job.status in terminal:
        return False

    redis = await get_redis()
    result_key = f"job_result:{job.id}"
    raw = await redis.get(result_key)
    if raw is None:
        # Also check job_status for running state update
        status_raw = await redis.get(f"job_status:{job.id}")
        if status_raw == "running" and job.status != JobStatus.RUNNING.value:
            from datetime import datetime

            job.status = JobStatus.RUNNING.value
            job.started_at = datetime.now(UTC)
            await db.commit()
            return True
        return False

    try:
        result = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return False

    from datetime import datetime

    now = datetime.now(UTC)

    if result.get("status") == "completed":
        # Create Track record if not already created
        if job.track is None:
            try:
                track = Track(
                    job_id=job.id,
                    user_id=job.user_id,
                    title=result.get("title", job.prompt[:100]),
                    storage_key=result["storage_key"],
                    file_size_bytes=result["file_size"],
                    duration_seconds=result["duration"],
                    sample_rate=result.get("sample_rate", 44100),
                    format=result.get("format", "wav"),
                )
                db.add(track)
            except KeyError as exc:
                logger.error("result_sync.malformed", job_id=str(job.id), missing_key=str(exc))
                return False

        job.status = JobStatus.COMPLETED.value
        job.completed_at = now
        await db.commit()

        # Clean up Redis keys
        await redis.delete(result_key, f"job_status:{job.id}")

        logger.info("result_sync.completed", job_id=str(job.id))
        return True

    elif result.get("status") == "failed":
        job.status = JobStatus.FAILED.value
        job.error_message = result.get("message", "Generation failed")[:500]
        job.completed_at = now
        await db.commit()
        await redis.delete(result_key, f"job_status:{job.id}")
        logger.info("result_sync.failed", job_id=str(job.id))
        return True

    elif result.get("status") == "cancelled":
        job.status = JobStatus.CANCELLED.value
        job.completed_at = now
        await db.commit()
        await redis.delete(result_key, f"job_status:{job.id}")
        logger.info("result_sync.cancelled", job_id=str(job.id))
        return True

    return False


async def sync_finetune_result(db: AsyncSession, job) -> bool:
    """Check Redis for a finetune task result and sync it to the database.

    Returns True if the job was updated (result found and synced).
    """
    from lofty.config import settings
    from lofty.models.finetune import LoRAAdapter

    terminal = {"completed", "failed", "cancelled"}
    if job.status in terminal:
        return False

    redis = await get_redis()

    # Check for result first
    result_key = f"finetune_result:{job.id}"
    raw = await redis.get(result_key)

    if raw is None:
        # Check for running status or progress update
        status_raw = await redis.get(f"finetune_status:{job.id}")
        if status_raw == "running" and job.status != "running":
            from datetime import datetime

            job.status = "running"
            job.started_at = datetime.now(UTC)
            await db.commit()
            return True

        # Sync progress
        progress_raw = await redis.get(f"finetune_progress:{job.id}")
        if progress_raw is not None:
            pct = int(progress_raw)
            if pct != job.progress:
                job.progress = pct
                await db.commit()
                return True

        return False

    try:
        result = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return False

    from datetime import datetime

    now = datetime.now(UTC)

    if result.get("status") == "completed":
        # Create LoRAAdapter record if not already created
        if job.adapter is None:
            try:
                adapter = LoRAAdapter(
                    user_id=job.user_id,
                    finetune_job_id=job.id,
                    name=result.get("job_name", job.name),
                    description=f"Fine-tuned with {result.get('num_tracks', 0)} tracks",
                    storage_key=result["adapter_storage_key"],
                    adapter_size_bytes=result["adapter_size"],
                    base_model=settings.ace_step_model_path,
                    training_method=result.get("training_method", "lokr"),
                )
                db.add(adapter)
            except KeyError as exc:
                logger.error("finetune_sync.malformed", job_id=str(job.id), missing_key=str(exc))
                return False

        job.status = "completed"
        job.progress = 100
        job.completed_at = now
        await db.commit()

        # Clean up Redis keys
        await redis.delete(
            result_key,
            f"finetune_status:{job.id}",
            f"finetune_progress:{job.id}",
        )

        logger.info("finetune_sync.completed", job_id=str(job.id))
        return True

    elif result.get("status") == "failed":
        job.status = "failed"
        job.error_message = result.get("message", "Training failed")[:500]
        job.completed_at = now
        await db.commit()
        await redis.delete(result_key, f"finetune_status:{job.id}")
        logger.info("finetune_sync.failed", job_id=str(job.id))
        return True

    elif result.get("status") == "cancelled":
        job.status = "cancelled"
        job.completed_at = now
        await db.commit()
        await redis.delete(result_key, f"finetune_status:{job.id}")
        logger.info("finetune_sync.cancelled", job_id=str(job.id))
        return True

    return False


async def sync_upload_analysis(db: AsyncSession, upload) -> bool:
    """Check Redis for an audio analysis result and sync it to the database.

    Returns True if the upload was updated.
    """
    if upload.analysis is not None:
        return False

    redis = await get_redis()
    result_key = f"upload_analysis:{upload.id}"
    raw = await redis.get(result_key)
    if raw is None:
        return False

    try:
        result = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return False

    if result.get("status") == "completed" and result.get("analysis"):
        analysis = result["analysis"]
        upload.analysis = analysis
        if analysis.get("duration_seconds") and upload.duration_seconds == 0:
            upload.duration_seconds = analysis["duration_seconds"]
        await db.commit()

        await redis.delete(result_key)
        logger.info("upload_analysis_sync.completed", upload_id=str(upload.id))
        return True

    elif result.get("status") == "failed":
        # Mark analysis as attempted but failed (empty dict)
        upload.analysis = {"_error": result.get("message", "Analysis failed")}
        await db.commit()
        await redis.delete(result_key)
        return True

    return False


async def sync_dataset_result(db: AsyncSession, dataset) -> bool:
    """Check Redis for dataset processing result and sync it to the database.

    Returns True if the dataset was updated.
    """
    if dataset.status not in ("processing",):
        return False

    redis = await get_redis()
    result_key = f"dataset_result:{dataset.id}"
    raw = await redis.get(result_key)
    if raw is None:
        return False

    try:
        result = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return False

    from sqlalchemy import select

    from lofty.models.dataset import DatasetTrack

    if result.get("status") == "ready":
        # Update individual track metadata from results
        processed_tracks = result.get("tracks", [])
        for track_result in processed_tracks:
            track_id = track_result.get("id")
            if not track_id:
                continue

            db_result = await db.execute(select(DatasetTrack).where(DatasetTrack.id == track_id))
            track = db_result.scalar_one_or_none()
            if track is None:
                continue

            if track_result.get("caption"):
                track.caption = track_result["caption"]
            if track_result.get("lyrics"):
                track.lyrics = track_result["lyrics"]
            if track_result.get("bpm") is not None:
                track.bpm = track_result["bpm"]
            if track_result.get("key_scale"):
                track.key_scale = track_result["key_scale"]
            if track_result.get("duration_seconds"):
                track.duration_seconds = track_result["duration_seconds"]
            track.status = track_result.get("status", "processed")

        # Update dataset status
        dataset.status = "ready"

        # Recalculate total duration from DB tracks
        all_tracks_result = await db.execute(
            select(DatasetTrack).where(DatasetTrack.dataset_id == dataset.id)
        )
        all_tracks = list(all_tracks_result.scalars().all())
        dataset.total_duration_seconds = sum(t.duration_seconds for t in all_tracks)

        await db.commit()
        await redis.delete(result_key)

        logger.info("dataset_sync.ready", dataset_id=str(dataset.id))
        return True

    elif result.get("status") == "failed":
        dataset.status = "failed"
        await db.commit()
        await redis.delete(result_key)
        logger.info("dataset_sync.failed", dataset_id=str(dataset.id))
        return True

    return False

"""Celery tasks for music generation.

The generate_music task is designed to work WITHOUT database access,
communicating results purely via Redis. This allows remote workers
(e.g. Google Colab) to run without access to the PostgreSQL database.

The API server syncs task results to the database via the SSE endpoint
and the job polling API.
"""

import logging
from datetime import UTC, datetime, timedelta

import redis as _redis

from lofty.config import settings
from lofty.services.storage import storage_client
from lofty.worker.audio_converter import wav_to_mp3
from lofty.worker.celery_app import celery_app
from lofty.worker.generator import detect_engine_type, get_engine

logger = logging.getLogger(__name__)


class GenerationCancelledError(Exception):
    """Raised when a generation is cancelled via Redis flag."""

    def __init__(self, job_id: str):
        self.job_id = job_id
        super().__init__(f"Job {job_id} cancelled by user")


# Lazy-init Redis — avoids crash if services are unreachable at import time
_redis_client = None


def _get_redis():
    """Lazy-create the sync Redis client for progress tracking."""
    global _redis_client
    if _redis_client is None:
        kwargs: dict = {"decode_responses": True}
        if settings.redis_url.startswith("rediss://"):
            import ssl as _ssl

            kwargs["ssl"] = True
            kwargs["ssl_cert_reqs"] = _ssl.CERT_NONE
        _redis_client = _redis.from_url(settings.redis_url, **kwargs)
    return _redis_client


# Lazy-init DB — only used by tasks that genuinely need it (cleanup, finetune)
_sync_engine = None
_SyncSession = None


def _get_sync_session():
    """Lazy-create the sync SQLAlchemy session factory.

    Only used by cleanup_stale_jobs and finetune tasks — NOT by generate_music.
    """
    global _sync_engine, _SyncSession
    if _SyncSession is None:
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        _sync_engine = create_engine(
            settings.sync_database_url,
            pool_size=5,
            max_overflow=2,
            pool_pre_ping=True,
        )
        _SyncSession = sessionmaker(bind=_sync_engine)
    return _SyncSession()


def _progress_key(job_id: str) -> str:
    return f"job_progress:{job_id}"


def _result_key(job_id: str) -> str:
    return f"job_result:{job_id}"


@celery_app.task(
    bind=True,
    name="lofty.worker.tasks.generate_music",
    max_retries=1,
    default_retry_delay=10,
)
def generate_music(
    self,
    job_id: str,
    *,
    user_id: str = "",
    prompt: str = "",
    lyrics: str = "",
    duration_seconds: float = 10.0,
    model_name: str = "",
    generation_params: dict | None = None,
    lora_adapter_id: str | None = None,
) -> dict:
    """Generate music for a job.

    This task does NOT access the database. All parameters are passed
    as arguments, and results are stored in Redis for the API to sync.

    1. Generate audio using the appropriate engine
    2. Upload audio to MinIO/S3
    3. Store result metadata in Redis
    """
    import json

    r = _get_redis()
    params = generation_params or {}

    # Check if cancelled before starting
    if r.get(f"job_cancel:{job_id}"):
        r.delete(f"job_cancel:{job_id}")
        r.setex(_result_key(job_id), 3600, json.dumps({"status": "cancelled"}))
        return {"status": "cancelled"}

    try:
        # Mark as running via Redis
        r.setex(f"job_status:{job_id}", 86400, "running")

        # Progress callback: store in Redis with TTL
        last_reported = [0]

        def on_progress(pct: int) -> None:
            if pct - last_reported[0] >= 2 or pct >= 100:
                r.setex(_progress_key(job_id), 3600, str(pct))
                last_reported[0] = pct
            # Check cancellation flag
            if r.get(f"job_cancel:{job_id}"):
                r.delete(f"job_cancel:{job_id}")
                raise GenerationCancelledError(job_id)

        on_progress(0)

        # Generate audio — route to the correct engine
        engine = get_engine(model_name)
        engine_type = detect_engine_type(model_name)

        if engine_type == "ace-step":
            # Load LoRA adapter if specified
            if lora_adapter_id:
                engine._load_lora(f"adapters/{user_id}/{lora_adapter_id}/")

            wav_bytes, sample_rate, actual_duration = engine.generate(
                prompt=prompt,
                duration_seconds=duration_seconds,
                on_progress=on_progress,
                lyrics=lyrics or "",
                inference_steps=params.get("inference_steps", 8),
                guidance_scale=params.get("guidance_scale", 7.0),
                bpm=params.get("bpm"),
                key=params.get("key"),
                time_signature=params.get("time_signature", "4/4"),
                language=params.get("language", "en"),
                task_type=params.get("task_type", "text2music"),
                seed=params.get("seed", -1),
            )
        elif engine_type == "yue":
            wav_bytes, sample_rate, actual_duration = engine.generate(
                prompt=prompt,
                duration_seconds=duration_seconds,
                on_progress=on_progress,
                lyrics=lyrics or "",
                temperature=params.get("temperature", 1.0),
                top_p=params.get("top_p", 0.93),
                repetition_penalty=params.get("repetition_penalty", 1.1),
                max_new_tokens=params.get("max_new_tokens", 3000),
                num_segments=params.get("num_segments", 2),
                language=params.get("language", "en"),
                seed=params.get("seed", 42),
            )
        else:
            wav_bytes, sample_rate, actual_duration = engine.generate(
                prompt=prompt,
                duration_seconds=duration_seconds,
                on_progress=on_progress,
                temperature=params.get("temperature", 1.0),
                top_k=params.get("top_k", 250),
                top_p=params.get("top_p", 0.0),
                guidance_scale=params.get("guidance_scale", 3.0),
                quality_preset=params.get("quality_preset", "balanced"),
            )

        # Upload WAV to storage
        wav_key = f"tracks/{user_id}/{job_id}.wav"
        storage_client.upload_bytes(wav_key, wav_bytes, content_type="audio/wav")

        # Convert to MP3
        mp3_bytes = wav_to_mp3(wav_bytes, bitrate=settings.output_mp3_bitrate)
        if mp3_bytes is not None:
            storage_key = f"tracks/{user_id}/{job_id}.mp3"
            file_size = storage_client.upload_bytes(
                storage_key, mp3_bytes, content_type="audio/mpeg"
            )
            audio_format = "mp3"
            try:
                storage_client.delete_object(wav_key)
            except Exception:
                logger.warning("Failed to delete WAV after MP3 conversion: %s", wav_key)
        else:
            storage_key = wav_key
            file_size = len(wav_bytes)
            audio_format = "wav"

        # Clean up progress key
        r.delete(_progress_key(job_id))

        result = {
            "status": "completed",
            "storage_key": storage_key,
            "file_size": file_size,
            "duration": actual_duration,
            "sample_rate": sample_rate,
            "format": audio_format,
            "title": prompt[:100],
        }

        # Store result in Redis for the API to pick up (TTL 1 hour)
        r.setex(_result_key(job_id), 3600, json.dumps(result))
        r.setex(f"job_status:{job_id}", 3600, "completed")

        logger.info(
            "Job %s completed: %.1fs audio, %.1fKB",
            job_id,
            actual_duration,
            file_size / 1024,
        )

        return result

    except GenerationCancelledError:
        r.delete(_progress_key(job_id))
        r.setex(_result_key(job_id), 3600, json.dumps({"status": "cancelled"}))
        r.setex(f"job_status:{job_id}", 3600, "cancelled")
        logger.info("Job %s cancelled by user during generation", job_id)
        return {"status": "cancelled"}

    except Exception as exc:
        r.delete(_progress_key(job_id))
        logger.exception("Job %s failed: %s", job_id, exc)

        error_result = {"status": "failed", "message": str(exc)[:500]}
        r.setex(_result_key(job_id), 3600, json.dumps(error_result))
        r.setex(f"job_status:{job_id}", 3600, "failed")

        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc)

        return error_result


@celery_app.task(name="lofty.worker.tasks.cleanup_stale_jobs")
def cleanup_stale_jobs() -> dict:
    """Mark jobs stuck in 'running' or 'pending' for >10 minutes as failed.

    This runs on the LOCAL worker only (needs DB access).
    """
    from sqlalchemy import update

    from lofty.models.job import GenerationJob, JobStatus

    stale_threshold = datetime.now(UTC) - timedelta(minutes=10)

    try:
        with _get_sync_session() as db:
            result_running = db.execute(
                update(GenerationJob)
                .where(
                    GenerationJob.status.in_(
                        [
                            JobStatus.RUNNING.value,
                            JobStatus.PENDING.value,
                            JobStatus.QUEUED.value,
                        ]
                    ),
                    GenerationJob.created_at < stale_threshold,
                )
                .values(
                    status=JobStatus.FAILED.value,
                    error_message="Job timed out — worker may have crashed. Please try again.",
                    completed_at=datetime.now(UTC),
                )
            )
            db.commit()

            cleaned = result_running.rowcount
            if cleaned > 0:
                logger.info("Cleaned up %d stale job(s)", cleaned)

            return {"cleaned": cleaned}
    except Exception as exc:
        logger.warning("cleanup_stale_jobs skipped (no DB access): %s", exc)
        return {"cleaned": 0, "skipped": True}


@celery_app.task(name="lofty.worker.tasks.run_autoscaler", ignore_result=True)
def run_autoscaler() -> dict:
    """Periodic task: check queue depth and auto-scale GPU instances."""
    from lofty.infra.autoscaler import check_and_scale

    return check_and_scale()


# ---------------------------------------------------------------------------
# Phase 2: Fine-tuning tasks
# ---------------------------------------------------------------------------


@celery_app.task(name="lofty.worker.tasks.analyze_audio", ignore_result=True)
def analyze_audio(
    upload_id: str,
    *,
    storage_key: str = "",
    audio_format: str = "wav",
) -> dict:
    """Auto-annotate an uploaded audio file (BPM, key, caption, lyrics).

    This task does NOT access the database. All parameters are passed
    as arguments, and results are stored in Redis for the API to sync.
    """
    import json

    from lofty.worker.audio_analyzer import analyze_audio as run_analysis

    r = _get_redis()

    try:
        # Download audio from S3
        response = storage_client._client.get_object(
            Bucket=storage_client._bucket,
            Key=storage_key,
        )
        audio_bytes = response["Body"].read()

        # Run analysis
        analysis = run_analysis(audio_bytes, audio_format)

        result = {"status": "completed", "analysis": analysis}
        r.setex(f"upload_analysis:{upload_id}", 3600, json.dumps(result))

        logger.info("Audio analysis complete for upload %s", upload_id)
        return result

    except Exception as exc:
        logger.exception("Audio analysis failed for upload %s", upload_id)
        error_result = {"status": "failed", "message": str(exc)[:500]}
        r.setex(f"upload_analysis:{upload_id}", 3600, json.dumps(error_result))
        return error_result


@celery_app.task(name="lofty.worker.tasks.process_dataset")
def process_dataset(
    dataset_id: str,
    *,
    tracks: list[dict] | None = None,
) -> dict:
    """Process all tracks in a dataset: auto-annotate missing metadata.

    This task does NOT access the database. Track data is passed as args,
    and results are stored in Redis for the API to sync.

    Each track dict: {id, storage_key, format, caption, lyrics, bpm, key_scale, duration_seconds}
    """
    import json

    from lofty.worker.audio_analyzer import analyze_audio as run_analysis

    r = _get_redis()
    tracks = tracks or []

    if not tracks:
        error_result = {"status": "failed", "message": "No tracks provided for processing"}
        r.setex(f"dataset_result:{dataset_id}", 3600, json.dumps(error_result))
        logger.warning("Dataset %s: no tracks provided", dataset_id)
        return error_result

    try:
        processed_tracks = []
        processed_count = 0

        for track in tracks:
            track_result = {
                "id": track["id"],
                "status": "processed",
            }

            # If track lacks metadata, try to auto-annotate
            if not track.get("caption") or not track.get("lyrics"):
                try:
                    response = storage_client._client.get_object(
                        Bucket=storage_client._bucket,
                        Key=track["storage_key"],
                    )
                    audio_bytes = response["Body"].read()
                    analysis = run_analysis(audio_bytes, track.get("format", "wav"))

                    if not track.get("caption") and analysis.get("caption"):
                        track_result["caption"] = analysis["caption"]
                    if not track.get("lyrics") and analysis.get("lyrics"):
                        track_result["lyrics"] = analysis["lyrics"]
                    if track.get("bpm") is None and analysis.get("bpm"):
                        track_result["bpm"] = analysis["bpm"]
                    if track.get("key_scale") is None and analysis.get("key_scale"):
                        track_result["key_scale"] = analysis["key_scale"]
                    if not track.get("duration_seconds") and analysis.get("duration_seconds"):
                        track_result["duration_seconds"] = analysis["duration_seconds"]
                except Exception:
                    logger.warning("Failed to analyze track %s", track["id"])

            processed_tracks.append(track_result)
            processed_count += 1

        result = {
            "status": "ready",
            "processed": processed_count,
            "total": len(tracks),
            "tracks": processed_tracks,
        }
        r.setex(f"dataset_result:{dataset_id}", 3600, json.dumps(result))

        logger.info(
            "Dataset %s processed: %d/%d tracks",
            dataset_id,
            processed_count,
            len(tracks),
        )
        return result

    except Exception as exc:
        logger.exception("Dataset processing failed: %s", dataset_id)
        error_result = {"status": "failed", "message": str(exc)[:500]}
        r.setex(f"dataset_result:{dataset_id}", 3600, json.dumps(error_result))
        return error_result


@celery_app.task(
    bind=True,
    name="lofty.worker.tasks.finetune_model",
    max_retries=0,
)
def finetune_model(
    self,
    job_id: str,
    *,
    user_id: str = "",
    job_name: str = "",
    track_data: list[dict] | None = None,
    config: dict | None = None,
) -> dict:
    """Run LoRA/LoKR fine-tuning for a user's custom style.

    This task does NOT access the database. All parameters are passed
    as arguments, and results are stored in Redis for the API to sync.

    1. Download dataset from S3 to temp directory
    2. Run ACE-Step training
    3. Upload adapter to S3
    4. Store result in Redis
    """
    import json
    import os
    import shutil
    import tempfile

    from lofty.worker.finetune_trainer import FineTuneTrainer, prepare_dataset_directory

    r = _get_redis()
    config = config or {}
    track_data = track_data or []

    # Check if cancelled before starting
    if r.get(f"finetune_cancel:{job_id}"):
        r.delete(f"finetune_cancel:{job_id}")
        r.setex(f"finetune_result:{job_id}", 3600, json.dumps({"status": "cancelled"}))
        return {"status": "cancelled"}

    temp_dir = None
    try:
        # Mark as running via Redis
        r.setex(f"finetune_status:{job_id}", 86400, "running")

        # Progress callback with cancellation check
        last_reported = [0]

        def on_progress(pct: int) -> None:
            if pct - last_reported[0] >= 2 or pct >= 100:
                r.setex(f"finetune_progress:{job_id}", 3600, str(pct))
                last_reported[0] = pct
            # Check cancellation flag
            if r.get(f"finetune_cancel:{job_id}"):
                r.delete(f"finetune_cancel:{job_id}")
                raise GenerationCancelledError(job_id)

        on_progress(0)

        if not track_data:
            raise ValueError("No valid tracks found in dataset")

        on_progress(5)

        # Prepare local dataset directory
        temp_dir = tempfile.mkdtemp(prefix="lofty_finetune_")
        dataset_dir = prepare_dataset_directory(
            track_data,
            storage_client,
            temp_dir,
        )
        output_dir = os.path.join(temp_dir, "output")

        on_progress(15)

        # Run training
        trainer = FineTuneTrainer(
            dataset_dir=dataset_dir,
            output_dir=output_dir,
            training_method=config.get("training_method", "lokr"),
            max_epochs=config.get("max_epochs", 500),
            batch_size=config.get("batch_size", 1),
            learning_rate=config.get("learning_rate", 1e-4),
        )

        # Scale progress: training uses 15-90% range
        def training_progress(pct: int) -> None:
            scaled = 15 + int(pct * 0.75)
            on_progress(min(scaled, 90))

        adapter_path = trainer.train(on_progress=training_progress)

        on_progress(90)

        # Upload adapter to S3
        adapter_storage_key = f"adapters/{user_id}/{job_id}/"
        adapter_size = 0

        for root, dirs, files in os.walk(adapter_path):
            for fname in files:
                fpath = os.path.join(root, fname)
                rel = os.path.relpath(fpath, adapter_path)
                s3_key = adapter_storage_key + rel.replace("\\", "/")

                with open(fpath, "rb") as f:
                    data = f.read()
                storage_client.upload_bytes(
                    s3_key,
                    data,
                    "application/octet-stream",
                )
                adapter_size += len(data)

        on_progress(95)

        # Store result in Redis for the API to sync to DB
        result = {
            "status": "completed",
            "adapter_storage_key": adapter_storage_key,
            "adapter_size": adapter_size,
            "training_method": config.get("training_method", "lokr"),
            "num_tracks": len(track_data),
            "job_name": job_name,
            "user_id": user_id,
        }
        r.setex(f"finetune_result:{job_id}", 3600, json.dumps(result))
        r.setex(f"finetune_status:{job_id}", 86400, "completed")
        r.delete(f"finetune_progress:{job_id}")

        logger.info(
            "Finetune job %s completed: adapter_size=%dKB",
            job_id,
            adapter_size // 1024,
        )

        return result

    except GenerationCancelledError:
        r.delete(f"finetune_progress:{job_id}")
        r.setex(f"finetune_result:{job_id}", 3600, json.dumps({"status": "cancelled"}))
        r.setex(f"finetune_status:{job_id}", 86400, "cancelled")
        logger.info("Finetune job %s cancelled", job_id)
        return {"status": "cancelled"}

    except Exception as exc:
        r.delete(f"finetune_progress:{job_id}")
        logger.exception("Finetune job %s failed: %s", job_id, exc)

        error_result = {"status": "failed", "message": str(exc)[:500]}
        r.setex(f"finetune_result:{job_id}", 3600, json.dumps(error_result))
        r.setex(f"finetune_status:{job_id}", 86400, "failed")

        return error_result

    finally:
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)

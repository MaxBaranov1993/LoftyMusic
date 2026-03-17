"""Health check endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from lofty.db.session import get_async_session
from lofty.dependencies import get_redis
from lofty.services.storage import storage_client

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health() -> dict:
    """Basic health check."""
    return {"status": "ok", "service": "lofty"}


@router.get("/health/ready")
async def readiness(db: AsyncSession = Depends(get_async_session)) -> dict:
    """Readiness check: verifies database, Redis, and storage connectivity."""
    # Database
    try:
        await db.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception as e:
        db_status = f"error: {e}"

    # Redis — use shared client instead of creating a new connection each call
    try:
        redis = await get_redis()
        await redis.ping()
        redis_status = "ok"
    except Exception as e:
        redis_status = f"error: {e}"

    # Storage (MinIO/S3)
    try:
        storage_client.ensure_bucket()
        storage_status = "ok"
    except Exception as e:
        storage_status = f"error: {e}"

    ready = all(s == "ok" for s in [db_status, redis_status, storage_status])
    return {
        "ready": ready,
        "database": db_status,
        "redis": redis_status,
        "storage": storage_status,
    }

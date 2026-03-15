"""Health check endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from lofty.db.session import get_async_session

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health() -> dict:
    """Basic health check."""
    return {"status": "ok", "service": "lofty"}


@router.get("/health/ready")
async def readiness(db: AsyncSession = Depends(get_async_session)) -> dict:
    """Readiness check: verifies database connectivity."""
    try:
        await db.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception as e:
        db_status = f"error: {e}"

    ready = db_status == "ok"
    return {
        "ready": ready,
        "database": db_status,
    }

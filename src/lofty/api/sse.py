"""Server-Sent Events endpoint for real-time job progress streaming.

Uses short-lived tickets instead of raw JWT tokens in query strings
to avoid leaking credentials in access logs and browser history.
"""

import asyncio
import json
import secrets
import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from lofty.auth.clerk import get_current_user
from lofty.db.session import AsyncSessionLocal, get_async_session
from lofty.dependencies import get_redis
from lofty.models.user import User
from lofty.services import job_service

logger = structlog.get_logger()

router = APIRouter(prefix="/jobs", tags=["Jobs SSE"])

# Ticket TTL in seconds — short-lived, single-use
_TICKET_TTL = 30


@router.post("/{job_id}/stream/ticket")
async def create_stream_ticket(
    job_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
) -> dict:
    """Create a short-lived, single-use ticket for SSE streaming.

    The client exchanges its Bearer token for an opaque ticket,
    then passes the ticket as a query parameter to the SSE endpoint.
    This avoids exposing the long-lived JWT in URLs/logs.
    """
    # Verify job exists and belongs to user
    job = await job_service.get_job(db, str(job_id), user)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    ticket = secrets.token_urlsafe(32)
    redis = await get_redis()
    # Store ticket → user mapping with short TTL
    ticket_key = f"sse_ticket:{ticket}"
    ticket_data = json.dumps({"user_id": str(user.id), "job_id": str(job_id)})
    await redis.setex(ticket_key, _TICKET_TTL, ticket_data)

    return {"ticket": ticket}


async def _get_user_from_ticket(ticket: str, db: AsyncSession) -> tuple[User, str]:
    """Validate a single-use SSE ticket and return the user and job_id.

    The ticket is deleted after use to prevent replay.
    """
    from sqlalchemy import select

    redis = await get_redis()
    ticket_key = f"sse_ticket:{ticket}"
    raw = await redis.getdel(ticket_key)
    if raw is None:
        raise HTTPException(status_code=401, detail="Invalid or expired ticket")

    data = json.loads(raw)
    result = await db.execute(
        select(User).where(User.id == data["user_id"])
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")

    return user, data["job_id"]


@router.get("/{job_id}/stream")
async def stream_job_progress(
    job_id: uuid.UUID,
    ticket: str = Query(..., description="Short-lived ticket for SSE auth"),
    db: AsyncSession = Depends(get_async_session),
) -> StreamingResponse:
    """Stream job progress updates via Server-Sent Events.

    Use POST /jobs/{job_id}/stream/ticket to obtain a ticket first.

    Events:
      - progress: {progress: int, status: str}
      - complete: {status: "completed", track_id: str}
      - error: {status: "failed", message: str}
      - cancelled: {status: "cancelled"}
    """
    user, ticket_job_id = await _get_user_from_ticket(ticket, db)

    # Ensure the ticket was issued for this specific job
    if ticket_job_id != str(job_id):
        raise HTTPException(status_code=403, detail="Ticket does not match job")

    job = await job_service.get_job(db, str(job_id), user)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    job_id_str = str(job_id)
    user_ref = user  # capture for closure

    async def event_generator():
        last_progress = -1
        tick_count = 0
        terminal_statuses = {"completed", "failed", "cancelled"}
        # Check DB every N ticks (each tick = 1s). Redis is checked every tick.
        db_check_interval = 5
        heartbeat_interval = 15

        try:
            while True:
                tick_count += 1
                redis = await get_redis()

                # Read progress from Redis (cheap, no DB hit)
                raw = await redis.get(f"job_progress:{job_id_str}")
                progress = int(raw) if raw else 0

                # Check DB for terminal status only every few seconds,
                # or when progress suggests completion (>= 99)
                if tick_count % db_check_interval == 0 or progress >= 99:
                    async with AsyncSessionLocal() as fresh_db:
                        fresh_job = await job_service.get_job(fresh_db, job_id_str, user_ref)

                    if fresh_job is None:
                        yield _sse_event("error", {"status": "failed", "message": "Job not found"})
                        break

                    # Sync results from Redis → DB (for remote workers)
                    if fresh_job.status not in terminal_statuses:
                        from lofty.services.result_sync import sync_job_result
                        async with AsyncSessionLocal() as sync_db:
                            fresh_job_sync = await job_service.get_job(sync_db, job_id_str, user_ref)
                            if fresh_job_sync:
                                await sync_job_result(sync_db, fresh_job_sync)
                                # Re-read after sync
                        async with AsyncSessionLocal() as fresh_db2:
                            fresh_job = await job_service.get_job(fresh_db2, job_id_str, user_ref)

                    if fresh_job and fresh_job.status in terminal_statuses:
                        if fresh_job.status == "completed" and fresh_job.track:
                            yield _sse_event("complete", {
                                "status": "completed",
                                "track_id": str(fresh_job.track.id),
                            })
                        elif fresh_job.status == "failed":
                            yield _sse_event("error", {
                                "status": "failed",
                                "message": fresh_job.error_message or "Generation failed",
                            })
                        else:
                            yield _sse_event("cancelled", {"status": "cancelled"})
                        break

                # Emit progress update if changed
                if progress != last_progress:
                    yield _sse_event("progress", {
                        "progress": progress,
                        "status": "running",
                    })
                    last_progress = progress
                elif tick_count % heartbeat_interval == 0:
                    # Heartbeat keeps the connection alive through proxies/ALBs
                    yield ": heartbeat\n\n"

                await asyncio.sleep(1)

        except asyncio.CancelledError:
            pass

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def _sse_event(event_type: str, data: dict) -> str:
    return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"

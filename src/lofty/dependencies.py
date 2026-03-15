"""FastAPI dependencies: database sessions, auth, rate limiting."""

import time

import redis.asyncio as aioredis
import structlog
from fastapi import Depends, HTTPException, Request, status

from lofty.auth.clerk import get_current_user  # noqa: F401 - re-export
from lofty.config import settings
from lofty.db.session import get_async_session  # noqa: F401 - re-export
from lofty.models.user import User

logger = structlog.get_logger()

# Redis client for rate limiting
_redis_client: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    """Get or create async Redis client."""
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(settings.redis_url)
    return _redis_client


async def close_redis() -> None:
    """Close the Redis client on shutdown."""
    global _redis_client
    if _redis_client is not None:
        await _redis_client.aclose()
        _redis_client = None


async def rate_limit(
    request: Request,
    user: User = Depends(get_current_user),
) -> User:
    """Rate limiting dependency using Redis sliding window."""
    try:
        redis = await get_redis()
        key = f"rate_limit:{user.clerk_id}"
        now = time.time()
        window = 60  # 1 minute

        pipe = redis.pipeline()
        pipe.zremrangebyscore(key, 0, now - window)
        pipe.zadd(key, {str(now): now})
        pipe.zcard(key)
        pipe.expire(key, window)
        results = await pipe.execute()

        request_count = results[2]

        if request_count > settings.rate_limit_per_minute:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded",
                headers={"Retry-After": str(window)},
            )
    except HTTPException:
        raise
    except Exception:
        # If Redis is unavailable, allow the request but log the error
        logger.warning("Rate limiting unavailable (Redis error), allowing request")

    return user

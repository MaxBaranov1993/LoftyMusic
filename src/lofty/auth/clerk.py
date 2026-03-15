"""Clerk JWT/JWKS verification and user management."""

import logging
import time

import httpx
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from lofty.config import Settings, settings
from lofty.db.session import get_async_session
from lofty.models.user import User

logger = logging.getLogger(__name__)

security = HTTPBearer()

# JWKS cache
_jwks_cache: dict | None = None
_jwks_cache_time: float = 0
JWKS_CACHE_TTL = 3600  # 1 hour


async def fetch_jwks(jwks_url: str) -> dict:
    """Fetch JWKS keys from Clerk, with caching."""
    global _jwks_cache, _jwks_cache_time

    now = time.time()
    if _jwks_cache is not None and (now - _jwks_cache_time) < JWKS_CACHE_TTL:
        return _jwks_cache

    async with httpx.AsyncClient() as client:
        response = await client.get(jwks_url, timeout=10.0)
        response.raise_for_status()
        _jwks_cache = response.json()
        _jwks_cache_time = now
        return _jwks_cache


async def verify_clerk_token(token: str, app_settings: Settings | None = None) -> dict:
    """Verify a Clerk JWT token and return decoded claims.

    Raises HTTPException 401 on failure.
    """
    if app_settings is None:
        app_settings = settings

    if not app_settings.clerk_jwks_url:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Clerk JWKS URL not configured",
        )

    try:
        jwks_data = await fetch_jwks(app_settings.clerk_jwks_url)
        public_keys = {}
        for key_data in jwks_data.get("keys", []):
            kid = key_data.get("kid")
            if kid:
                public_keys[kid] = jwt.algorithms.RSAAlgorithm.from_jwk(key_data)

        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")
        if kid not in public_keys:
            # Try refreshing JWKS once (key rotation)
            global _jwks_cache
            _jwks_cache = None
            jwks_data = await fetch_jwks(app_settings.clerk_jwks_url)
            public_keys = {}
            for key_data in jwks_data.get("keys", []):
                k = key_data.get("kid")
                if k:
                    public_keys[k] = jwt.algorithms.RSAAlgorithm.from_jwk(key_data)

            if kid not in public_keys:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token signing key not found",
                )

        decoded = jwt.decode(
            token,
            key=public_keys[kid],
            algorithms=["RS256"],
            options={"verify_aud": False},
            leeway=10,
        )
        return decoded

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
        )
    except jwt.InvalidTokenError as e:
        logger.debug("Invalid token: %s", e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_async_session),
) -> User:
    """FastAPI dependency: verify Clerk token, upsert user, return User model."""
    claims = await verify_clerk_token(credentials.credentials)

    clerk_id = claims.get("sub")
    if not clerk_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing subject claim",
        )

    # Upsert user
    result = await db.execute(select(User).where(User.clerk_id == clerk_id))
    user = result.scalar_one_or_none()

    if user is None:
        user = User(
            clerk_id=clerk_id,
            email=claims.get("email"),
            display_name=claims.get("name"),
        )
        db.add(user)
        await db.flush()
    else:
        # Update fields if changed
        email = claims.get("email")
        name = claims.get("name")
        if email and user.email != email:
            user.email = email
        if name and user.display_name != name:
            user.display_name = name

    return user

"""Track service: queries and presigned URL generation."""

import math

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from lofty.models.track import Track
from lofty.models.user import User
from lofty.services.storage import storage_client


async def get_track(
    db: AsyncSession,
    track_id: str,
    user: User,
) -> Track | None:
    """Get a track by ID, scoped to the user."""
    result = await db.execute(
        select(Track).where(
            Track.id == track_id,
            Track.user_id == user.id,
        )
    )
    return result.scalar_one_or_none()


async def list_tracks(
    db: AsyncSession,
    user: User,
    page: int = 1,
    per_page: int = 20,
) -> tuple[list[Track], int]:
    """List tracks for a user with pagination."""
    query = (
        select(Track)
        .where(Track.user_id == user.id)
        .order_by(Track.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    count_query = select(func.count()).select_from(Track).where(Track.user_id == user.id)

    result = await db.execute(query)
    tracks = list(result.scalars().all())

    count_result = await db.execute(count_query)
    total = count_result.scalar_one()

    return tracks, total


def get_download_url(track: Track) -> str:
    """Generate a presigned download URL for a track."""
    return storage_client.generate_presigned_url(track.storage_key)


def calculate_pages(total: int, per_page: int) -> int:
    return max(1, math.ceil(total / per_page))

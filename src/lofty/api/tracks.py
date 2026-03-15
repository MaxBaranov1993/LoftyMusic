"""Track endpoints: list, get, download."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from lofty.auth.clerk import get_current_user
from lofty.db.session import get_async_session
from lofty.models.user import User
from lofty.schemas.track import PaginatedTrackResponse, TrackResponse
from lofty.services import track_service

router = APIRouter(prefix="/tracks", tags=["Tracks"])


@router.get("", response_model=PaginatedTrackResponse)
async def list_tracks(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
) -> PaginatedTrackResponse:
    """List the current user's generated tracks."""
    tracks, total = await track_service.list_tracks(db, user, page, per_page)
    return PaginatedTrackResponse(
        items=[TrackResponse.model_validate(t) for t in tracks],
        total=total,
        page=page,
        per_page=per_page,
        pages=track_service.calculate_pages(total, per_page),
    )


@router.get("/{track_id}", response_model=TrackResponse)
async def get_track(
    track_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
) -> TrackResponse:
    """Get a specific track by ID with download URL."""
    track = await track_service.get_track(db, str(track_id), user)
    if track is None:
        raise HTTPException(status_code=404, detail="Track not found")
    response = TrackResponse.model_validate(track)
    response.download_url = track_service.get_download_url(track)
    return response


@router.get("/{track_id}/download")
async def download_track(
    track_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
) -> RedirectResponse:
    """Redirect to a presigned download URL for the track."""
    track = await track_service.get_track(db, str(track_id), user)
    if track is None:
        raise HTTPException(status_code=404, detail="Track not found")
    url = track_service.get_download_url(track)
    return RedirectResponse(url=url, status_code=302)

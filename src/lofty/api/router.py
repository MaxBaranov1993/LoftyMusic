"""Main API router that aggregates all sub-routers."""

from fastapi import APIRouter

from lofty.api.jobs import router as jobs_router
from lofty.api.tracks import router as tracks_router
from lofty.api.users import router as users_router

api_router = APIRouter()
api_router.include_router(jobs_router)
api_router.include_router(tracks_router)
api_router.include_router(users_router)

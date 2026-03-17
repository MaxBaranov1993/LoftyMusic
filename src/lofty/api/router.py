"""Main API router that aggregates all sub-routers."""

from fastapi import APIRouter

from lofty.api.datasets import router as datasets_router
from lofty.api.finetune import adapters_router
from lofty.api.finetune import router as finetune_router
from lofty.api.gpu import router as gpu_router
from lofty.api.jobs import router as jobs_router
from lofty.api.sse import router as sse_router
from lofty.api.tracks import router as tracks_router
from lofty.api.uploads import router as uploads_router
from lofty.api.users import router as users_router
from lofty.api.worker import router as worker_router

api_router = APIRouter()
api_router.include_router(jobs_router)
api_router.include_router(sse_router)
api_router.include_router(tracks_router)
api_router.include_router(users_router)
api_router.include_router(gpu_router)
api_router.include_router(uploads_router)
api_router.include_router(datasets_router)
api_router.include_router(finetune_router)
api_router.include_router(adapters_router)
api_router.include_router(worker_router)

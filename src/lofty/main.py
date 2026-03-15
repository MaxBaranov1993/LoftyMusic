"""FastAPI application factory."""

import logging
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from lofty.api.health import router as health_router
from lofty.api.router import api_router
from lofty.config import settings
from lofty.services.storage import storage_client


def configure_logging(debug: bool = False) -> None:
    """Configure structured logging."""
    log_level = logging.DEBUG if debug else logging.INFO
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer() if debug else structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown."""
    logger = structlog.get_logger()
    logger.info("Starting Lofty API", debug=settings.debug)

    # Ensure storage bucket exists
    try:
        storage_client.ensure_bucket()
        logger.info("Storage bucket ready", bucket=settings.storage_bucket)
    except Exception as e:
        logger.warning("Could not initialize storage", error=str(e))

    yield

    # Graceful shutdown: close connections
    from lofty.db.session import async_engine
    from lofty.dependencies import close_redis

    await close_redis()
    await async_engine.dispose()
    logger.info("Shutting down Lofty API")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    configure_logging(settings.debug)

    application = FastAPI(
        title="Lofty - AI Music Generation",
        description=(
            "Generate music from text prompts using AI. "
            "Submit generation jobs, track progress, and download generated audio."
        ),
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # CORS
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )

    # Routes
    application.include_router(health_router)
    application.include_router(api_router, prefix=settings.api_prefix)

    # Global exception handler
    @application.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger = structlog.get_logger()
        logger.error(
            "Unhandled exception",
            path=request.url.path,
            method=request.method,
            error=str(exc),
        )
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )

    return application


app = create_app()

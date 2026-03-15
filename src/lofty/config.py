"""Application configuration via environment variables."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # App
    app_name: str = "Lofty"
    debug: bool = False
    api_prefix: str = "/api/v1"
    cors_origins: list[str] = ["http://localhost:3000"]

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/lofty"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Celery
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # Clerk Auth
    clerk_publishable_key: str = ""
    clerk_secret_key: str = ""
    clerk_jwks_url: str = ""

    # Storage (S3 / MinIO)
    storage_endpoint: str = "localhost:9000"
    storage_access_key: str = "minioadmin"
    storage_secret_key: str = "minioadmin"
    storage_bucket: str = "lofty-tracks"
    storage_use_ssl: bool = False
    storage_public_endpoint: str = "localhost:9000"

    # Model
    model_name: str = "facebook/musicgen-stereo-large"
    model_cache_dir: str = "./model_cache"
    model_device: str = "cuda"
    max_duration_seconds: float = 30.0

    # Rate Limiting
    rate_limit_per_minute: int = 10
    rate_limit_burst: int = 3

    @property
    def sync_database_url(self) -> str:
        """Synchronous database URL for Alembic and Celery workers."""
        return self.database_url.replace("+asyncpg", "+psycopg2")


settings = Settings()

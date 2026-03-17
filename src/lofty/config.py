"""Application configuration via environment variables."""

import ssl
import sys

# Fix for broken certificates in Windows cert store that cause
# ssl.SSLError: [ASN1] nested asn1 error when connecting to Upstash Redis.
if sys.platform == "win32":
    _original_load_default_certs = ssl.SSLContext.load_default_certs

    def _safe_load_default_certs(self, purpose=ssl.Purpose.SERVER_AUTH):
        try:
            _original_load_default_certs(self, purpose)
        except ssl.SSLError:
            pass  # Skip corrupted certs in Windows store

    ssl.SSLContext.load_default_certs = _safe_load_default_certs

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Ignore frontend-only env vars (NEXT_PUBLIC_*)
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
    clerk_jwt_issuer: str = ""  # e.g., "https://<instance>.clerk.accounts.dev"

    # Storage (S3 / MinIO)
    storage_endpoint: str = "localhost:9000"
    storage_access_key: str = "minioadmin"
    storage_secret_key: str = "minioadmin"
    storage_bucket: str = "lofty-tracks"
    storage_use_ssl: bool = False
    storage_public_endpoint: str = "localhost:9000"

    # Model (ACE-Step 1.5)
    ace_step_enabled: bool = True
    mock_gpu: bool = False  # Set True to run without real GPU/models (dev mode)
    model_name: str = "ace-step-1.5"
    model_device: str = "cuda"
    ace_step_model_path: str = "ACE-Step/Ace-Step1.5"
    ace_step_cache_dir: str = "./ace_model_cache"
    ace_step_default_inference_steps: int = 8  # Turbo model max is 8 steps
    ace_step_max_duration_seconds: float = 120.0  # 2 min (safe for free Colab T4)
    ace_step_thinking_enabled: bool = False  # Disable on T4 — causes OOM/NaN
    ace_step_cpu_offload: bool = True  # Offload LM/VAE to RAM, saves ~4GB VRAM

    # Model (YuE)
    yue_enabled: bool = True
    yue_stage1_model: str = "m-a-p/YuE-s1-7B-anneal-en-cot"
    yue_stage2_model: str = "m-a-p/YuE-s2-1B-general"
    yue_cache_dir: str = "./yue_model_cache"
    yue_use_4bit: bool = True  # 4-bit NF4 quantization for T4 GPU (15GB VRAM)
    yue_max_duration_seconds: float = 60.0  # Max 2 segments (~60s) on free Colab

    # Audio output quality
    output_sample_rate: int = 44100
    output_mp3_bitrate: str = "320k"
    output_target_lufs: float = -14.0

    # GPU Backend: "local" | "google" | "cloud"
    gpu_backend: str = "local"
    cloud_gpu_api_key: str = ""  # RunPod / Vast.ai API key
    cloud_gpu_docker_image: str = "lofty-worker:gpu"
    autoscaler_enabled: bool = False
    autoscaler_min_instances: int = 0
    autoscaler_max_instances: int = 3
    autoscaler_idle_timeout: int = 300  # seconds before tearing down idle instance

    # Worker API (for Colab polling)
    worker_api_key: str = ""

    # Rate Limiting
    rate_limit_per_minute: int = 10
    rate_limit_burst: int = 3

    @property
    def sync_database_url(self) -> str:
        """Synchronous database URL for Alembic and Celery workers."""
        return self.database_url.replace("+asyncpg", "+psycopg2")


settings = Settings()

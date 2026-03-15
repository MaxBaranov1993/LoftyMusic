FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

# Install PyTorch CPU-only (much smaller image since model runs on CPU)
RUN pip install --no-cache-dir torch torchaudio --index-url https://download.pytorch.org/whl/cpu

# Install Python dependencies with worker extras
COPY pyproject.toml .
COPY src/ src/
RUN pip install --no-cache-dir ".[worker]"


CMD ["celery", "-A", "lofty.worker.celery_app", "worker", "--pool=solo", "--queues", "gpu", "--concurrency", "1", "--loglevel", "info"]

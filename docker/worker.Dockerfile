FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc ffmpeg git \
    && rm -rf /var/lib/apt/lists/*

# Install PyTorch CPU-only (much smaller image since model runs on CPU)
RUN pip install --no-cache-dir torch torchaudio --index-url https://download.pytorch.org/whl/cpu

# Install Python dependencies with worker extras
COPY pyproject.toml .
COPY src/ src/
RUN pip install --no-cache-dir ".[worker]"

# Install ACE-Step 1.5 from source (--no-deps to skip nano-vllm which is unavailable on PyPI)
RUN git clone --depth 1 https://github.com/ace-step/ACE-Step-1.5.git /app/ACE-Step-1.5 && \
    pip install --no-cache-dir -e /app/ACE-Step-1.5 --no-deps && \
    pip install --no-cache-dir \
        "transformers>=4.51.0,<4.58.0" "tokenizers>=0.22.0,<=0.23.0" \
        accelerate diffusers einops loguru peft scipy soundfile \
        vector_quantize_pytorch diskcache lycoris-lora lightning

# Model cache volumes
VOLUME /app/model_cache
VOLUME /app/ace_model_cache

ENV ACE_STEP_PROJECT_ROOT=/app/ACE-Step-1.5

CMD ["celery", "-A", "lofty.worker.celery_app", "worker", "--pool=solo", "--queues", "gpu,training", "--concurrency", "1", "--loglevel", "info"]

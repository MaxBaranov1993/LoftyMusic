FROM nvidia/cuda:12.1.1-runtime-ubuntu22.04

WORKDIR /app

# Install Python 3.12 and system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    software-properties-common && \
    add-apt-repository ppa:deadsnakes/ppa && \
    apt-get update && apt-get install -y --no-install-recommends \
    python3.12 python3.12-venv python3.12-dev python3-pip \
    libpq-dev gcc ffmpeg curl git \
    && rm -rf /var/lib/apt/lists/*

# Set Python 3.12 as default
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 1 && \
    update-alternatives --install /usr/bin/python python /usr/bin/python3.12 1

# Install PyTorch with CUDA 12.1 support
RUN pip install --no-cache-dir torch torchaudio --index-url https://download.pytorch.org/whl/cu121

# Install Python dependencies with worker extras
COPY pyproject.toml .
COPY src/ src/
RUN pip install --no-cache-dir ".[worker]"

# Install ACE-Step 1.5 from source
RUN git clone --depth 1 https://github.com/ace-step/ACE-Step-1.5.git /app/ACE-Step-1.5 && \
    pip install --no-cache-dir -e /app/ACE-Step-1.5

# Model cache volumes
VOLUME /app/model_cache
VOLUME /app/ace_model_cache

ENV ACE_STEP_PROJECT_ROOT=/app/ACE-Step-1.5

ENV MODEL_DEVICE=cuda
ENV NVIDIA_VISIBLE_DEVICES=all
ENV NVIDIA_DRIVER_CAPABILITIES=compute,utility

CMD ["celery", "-A", "lofty.worker.celery_app", "worker", "--pool=solo", "--queues", "gpu,training", "--concurrency", "1", "--loglevel", "info"]

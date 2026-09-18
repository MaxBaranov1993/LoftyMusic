# Lofty

**An AI music generation platform with distributed GPU execution, model fine-tuning, and production-oriented inference infrastructure.**

Lofty is a full-stack system for generating music from text prompts, running open generative-audio models, managing long-running jobs, and training reusable adapters on custom datasets.

The project is designed to separate the product experience from the GPU execution layer, allowing generation workloads to run locally, on external workers, or on cloud GPU infrastructure.

## What Lofty explores

Most generative-audio demos stop at a single model invocation. Lofty focuses on the infrastructure around the model:

- user authentication;
- asynchronous generation jobs;
- GPU workers;
- progress streaming;
- object storage;
- model selection;
- training datasets;
- LoRA / LoKR fine-tuning;
- autoscaling and worker orchestration.

## Core capabilities

- **Text-to-music generation** with ACE-Step 1.5 and experimental YuE support.
- **Asynchronous GPU jobs** backed by Celery and Redis.
- **Remote worker protocol** so GPU machines do not need direct database access.
- **Real-time generation progress** through Server-Sent Events.
- **Fine-tuning pipeline** for custom audio datasets and adapter training.
- **LoRA / LoKR adapters** for reusable model customization.
- **Multiple compute modes** for local, Google Colab-style, or cloud workers.
- **S3-compatible storage** for generated audio, datasets, and model artifacts.
- **Autoscaling primitives** based on queue depth and worker availability.
- **Clerk authentication** with server-side JWT verification.

## Architecture

```text
                    Next.js 16
                   React 19 UI
                        │
                        ▼
                  FastAPI service
                        │
          ┌─────────────┼──────────────┐
          ▼             ▼              ▼
     PostgreSQL       Redis         S3 / MinIO
        data       queue/cache        files
                        │
                        ▼
                     Celery
                        │
            ┌───────────┴───────────┐
            ▼                       ▼
       Local worker            Remote GPU worker
                                    │
                          ┌─────────┼─────────┐
                          ▼         ▼         ▼
                       Colab     RunPod    Vast.ai
```

Remote GPU workers interact with Lofty through an HTTP worker API, allowing inference infrastructure to stay decoupled from application database credentials.

## Technology

**Frontend**
- Next.js 16
- React 19
- TypeScript
- Tailwind CSS
- Radix UI
- Clerk

**Backend**
- Python 3.12+
- FastAPI
- SQLAlchemy 2
- Alembic
- Pydantic
- PostgreSQL

**Jobs and infrastructure**
- Celery
- Redis
- Docker Compose
- S3 / MinIO
- SSE progress streaming

**AI / audio**
- PyTorch
- Transformers
- ACE-Step 1.5
- YuE experimentation
- PEFT
- LoRA / LoKR
- SoundFile / SciPy

## Generation pipeline

```text
Prompt
  │
  ▼
API job
  │
  ▼
Redis / Celery queue
  │
  ▼
GPU worker
  │
  ├── model inference
  ├── progress updates
  └── cancellation checks
  │
  ▼
Object storage
  │
  ▼
Track metadata + secure result delivery
```

Long-running inference is intentionally moved out of the request/response cycle, keeping the API responsive while workers handle expensive GPU workloads independently.

## Worker architecture

Lofty supports two worker patterns.

### Managed local workers

Celery workers consume generation jobs from Redis and execute them on the available machine.

### Remote GPU workers

External workers poll the API for work, report progress, check cancellation state, and upload results over HTTP.

This means a disposable GPU machine only needs:

- the Lofty API URL;
- a worker API key;
- model/runtime dependencies.

It does **not** need PostgreSQL or internal service credentials.

## Fine-tuning workflow

```text
Audio uploads
     │
     ▼
Dataset + metadata
     │
     ▼
Pre-processing
     │
     ▼
LoRA / LoKR training
     │
     ▼
Adapter artifact
     │
     ▼
Generation job using adapter
```

Dataset records can include lyrics, BPM, key, and other metadata used by the training pipeline.

## Security and reliability

- Clerk JWT verification through JWKS.
- Rate limiting backed by Redis.
- Presigned object-storage URLs.
- Short-lived, single-use SSE tickets.
- Worker authentication through a dedicated API key.
- User-level data isolation.
- Redis distributed locks for duplicate-job protection.
- Periodic cleanup of stale jobs.
- Queue-aware autoscaling primitives.

## Local development

Requirements: Docker, Docker Compose, and the required authentication/model environment variables.

```bash
docker compose up --build
```

The development stack includes:

- PostgreSQL
- Redis
- MinIO
- FastAPI
- Celery worker
- Next.js frontend

For development without a production GPU, the worker layer also supports mock execution modes.

## Python development

```bash
pip install -e ".[dev]"
pytest
```

Optional worker/model dependencies are separated into extras so API development does not require installing the full GPU stack.

## Repository structure

```text
src/lofty/        backend application
frontend/         Next.js product UI
docker/           API, worker, and frontend images
tests/            automated tests
pyproject.toml    Python dependencies and tooling
docker-compose.yml
```

## Status

**Experimental AI infrastructure / active development.**

Lofty is a product and engineering experiment focused on the systems required to turn open generative-audio models into a usable multi-user application.

---

Built as an independent exploration of generative audio, distributed inference, and GPU-native product architecture.

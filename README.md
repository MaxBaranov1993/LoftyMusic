# Lofty — AI Music Generation Platform

**Lofty** is a full-stack platform for AI-powered music generation with fine-tuning support and distributed GPU infrastructure. Generate music from text prompts using ACE-Step 1.5 and YuE models, train custom LoRA adapters on your own audio, and scale across local GPUs, Google Colab, or cloud providers (RunPod, Vast.ai).

---

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
- [REST API Documentation](#rest-api-documentation)
- [Database Models](#database-models)
- [Music Generation Engines](#music-generation-engines)
- [Worker Architecture](#worker-architecture)
- [GPU Farm Integration](#gpu-farm-integration)
- [Authentication & Security](#authentication--security)
- [Real-time Progress (SSE)](#real-time-progress-sse)
- [Fine-Tuning Pipeline](#fine-tuning-pipeline)
- [Configuration Reference](#configuration-reference)
- [Deployment](#deployment)

---

## Architecture Overview

```
                    ┌─────────────┐
                    │  Next.js 14 │
                    │  Frontend   │
                    └──────┬──────┘
                           │ HTTP / SSE
                    ┌──────▼──────┐
                    │  FastAPI    │     ┌──────────────┐
                    │  API Server ├─────►  PostgreSQL  │
                    └──┬───┬──┬──┘     └──────────────┘
                       │   │  │
              ┌────────┘   │  └────────────┐
              ▼            ▼               ▼
        ┌──────────┐ ┌──────────┐   ┌──────────┐
        │  Redis   │ │  MinIO   │   │  Celery  │
        │ Cache/   │ │  S3      │   │  Worker  │
        │ Queue    │ │  Storage │   │  (local) │
        └──────────┘ └──────────┘   └──────────┘
                                          │
              ┌───────────────────────────┘
              │
     ┌────────▼────────┐     ┌──────────────────┐
     │  ACE-Step 1.5   │     │  Google Colab /   │
     │  YuE Engine     │     │  RunPod / Vast.ai │
     │  (GPU Workers)  │     │  (HTTP Polling)   │
     └─────────────────┘     └──────────────────┘
```

**Key Design Principles:**

- **Workers never touch the database** — all params passed upfront, results stored in Redis, API syncs to DB asynchronously. This enables remote workers (Colab) without DB credentials.
- **Dual compute modes** — CPU (local Celery) and GPU (HTTP polling from remote workers).
- **Ticket-based SSE** — short-lived, single-use tokens for real-time progress streaming without exposing JWTs in URLs.
- **Distributed locking** — Redis `SET NX` prevents duplicate concurrent generation jobs per user.

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| **Frontend** | Next.js 14, TypeScript, Tailwind CSS, Clerk Auth |
| **API** | FastAPI, Pydantic 2, Uvicorn |
| **Database** | PostgreSQL 16, SQLAlchemy 2.0 (async) |
| **Queue** | Redis + Celery 5.4 |
| **Storage** | MinIO / AWS S3 (Boto3) |
| **Auth** | Clerk (JWT/JWKS verification) |
| **ML Models** | ACE-Step 1.5, YuE, PyTorch 2.5+, PEFT (LoRA) |
| **Infra** | Docker Compose, GitHub Actions CI |

---

## Project Structure

```
lofty/
├── src/lofty/                    # Python backend
│   ├── api/                      # FastAPI route handlers
│   │   ├── router.py             # Central router aggregator
│   │   ├── health.py             # Health & readiness checks
│   │   ├── jobs.py               # Music generation jobs
│   │   ├── tracks.py             # Generated track listing/download
│   │   ├── uploads.py            # Audio file uploads
│   │   ├── datasets.py           # Fine-tuning datasets
│   │   ├── finetune.py           # Fine-tuning jobs & LoRA adapters
│   │   ├── gpu.py                # GPU infrastructure management
│   │   ├── sse.py                # Server-Sent Events streaming
│   │   └── worker.py             # Worker HTTP polling API
│   ├── models/                   # SQLAlchemy ORM models
│   ├── schemas/                  # Pydantic request/response schemas
│   ├── services/                 # Business logic layer
│   ├── worker/                   # Celery tasks & ML engines
│   │   └── engines/              # ACE-Step, YuE implementations
│   ├── infra/                    # GPU provisioner & autoscaler
│   ├── auth/                     # Clerk JWT verification
│   ├── db/                       # Async SQLAlchemy session factory
│   ├── main.py                   # FastAPI app factory
│   ├── config.py                 # Settings (env vars)
│   └── dependencies.py           # FastAPI dependency injection
├── migrations/                   # Alembic DB migrations
├── frontend/                     # Next.js 14 app
│   ├── src/app/                  # Pages (dashboard, tracks, fine-tune, gpu-farm)
│   ├── src/components/           # React components
│   └── src/hooks/                # Custom hooks
├── docker/                       # Dockerfiles (api, worker, worker-gpu, frontend)
├── scripts/                      # Utility scripts
├── tests/                        # Test suite
├── docker-compose.yml            # Local development environment
└── pyproject.toml                # Python dependencies & config
```

---

## Getting Started

### Prerequisites

- Docker & Docker Compose
- Node.js 18+ (for frontend development)
- Python 3.12+ (for backend development)
- [Clerk](https://clerk.com) account (auth)

### Quick Start (Docker)

```bash
# Clone the repository
git clone https://github.com/MaxBaranov1993/LoftyMusic.git
cd LoftyMusic

# Copy environment file and fill in your values
cp .env.example .env

# Start all services
docker-compose up

# Run database migrations
docker-compose exec api alembic upgrade head
```

Services will be available at:
- **Frontend**: http://localhost:3000
- **API**: http://localhost:8000
- **API Docs (Swagger)**: http://localhost:8000/docs
- **MinIO Console**: http://localhost:9001

### Local Development (without Docker)

```bash
# Backend
pip install -e ".[dev]"
uvicorn lofty.main:create_app --factory --reload --port 8000

# Worker (local, mock GPU)
MOCK_GPU=true celery -A lofty.worker.celery_app worker -Q gpu -l info

# Frontend
cd frontend && npm install && npm run dev
```

---

## REST API Documentation

All endpoints are prefixed with `/api/v1`. Authentication via `Authorization: Bearer <clerk_jwt>` header.

Interactive Swagger UI available at `/docs` when the API is running.

### Health Checks

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Basic health check |
| `GET` | `/health/ready` | Readiness probe (DB + Redis + Storage) |

### Music Generation Jobs

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/jobs` | Create a generation job |
| `GET` | `/api/v1/jobs` | List user's jobs (paginated) |
| `GET` | `/api/v1/jobs/{job_id}` | Get job details |
| `POST` | `/api/v1/jobs/{job_id}/cancel` | Cancel a running job |
| `DELETE` | `/api/v1/jobs/{job_id}` | Delete job and associated data |

#### Create Job Request

```json
{
  "prompt": "epic orchestral soundtrack with dramatic strings",
  "lyrics": "[verse]\nRising from the ashes...",
  "duration_seconds": 60,
  "model_name": "ace-step-1.5",
  "compute_mode": "gpu",
  "lora_adapter_id": "uuid-or-null",
  "generation_params": {
    "inference_steps": 8,
    "guidance_scale": 5.0,
    "bpm": 120,
    "key": "C major",
    "time_signature": "4/4"
  }
}
```

#### Job Response

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "running",
  "prompt": "epic orchestral soundtrack",
  "model_name": "ace-step-1.5",
  "compute_mode": "gpu",
  "progress": 45,
  "created_at": "2026-03-17T12:00:00Z",
  "started_at": "2026-03-17T12:00:05Z",
  "track": null
}
```

**Job Status Flow:**
```
pending → queued → running → completed
                           → failed
                           → cancelled
```

### Tracks (Generated Audio)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/tracks` | List user's generated tracks |
| `GET` | `/api/v1/tracks/{track_id}` | Get track info with download URL |
| `GET` | `/api/v1/tracks/{track_id}/download` | Redirect to presigned S3 URL |

#### Track Response

```json
{
  "id": "track-uuid",
  "title": "epic orchestral soundtrack",
  "storage_key": "tracks/user-id/track-id.mp3",
  "file_size_bytes": 1048576,
  "duration_seconds": 60.0,
  "sample_rate": 32000,
  "format": "mp3",
  "download_url": "https://storage.example.com/tracks/...?X-Amz-Signature=...",
  "created_at": "2026-03-17T12:01:00Z"
}
```

### Audio Uploads

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/uploads` | Upload audio (WAV/MP3/FLAC/OGG, max 50MB) |
| `GET` | `/api/v1/uploads` | List user's uploads |
| `GET` | `/api/v1/uploads/{upload_id}` | Get upload details |
| `DELETE` | `/api/v1/uploads/{upload_id}` | Delete upload |

### Datasets (Fine-Tuning)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/datasets` | Create a dataset |
| `GET` | `/api/v1/datasets` | List user's datasets |
| `GET` | `/api/v1/datasets/{dataset_id}` | Get dataset with tracks |
| `POST` | `/api/v1/datasets/{dataset_id}/tracks` | Add track to dataset |
| `DELETE` | `/api/v1/datasets/{dataset_id}/tracks/{track_id}` | Remove track |
| `POST` | `/api/v1/datasets/{dataset_id}/process` | Process dataset |
| `DELETE` | `/api/v1/datasets/{dataset_id}` | Delete dataset |

### Fine-Tuning

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/finetune` | Start fine-tuning job |
| `GET` | `/api/v1/finetune` | List fine-tuning jobs |
| `GET` | `/api/v1/finetune/{job_id}` | Get fine-tuning job details |
| `POST` | `/api/v1/finetune/{job_id}/cancel` | Cancel fine-tuning |
| `DELETE` | `/api/v1/finetune/{job_id}` | Delete fine-tuning job |
| `GET` | `/api/v1/adapters` | List LoRA adapters |
| `GET` | `/api/v1/adapters/{adapter_id}` | Get adapter details |
| `DELETE` | `/api/v1/adapters/{adapter_id}` | Delete adapter |

#### Fine-Tune Request

```json
{
  "name": "My Jazz Adapter",
  "dataset_id": "dataset-uuid",
  "compute_mode": "gpu",
  "config": {
    "max_epochs": 50,
    "batch_size": 4,
    "learning_rate": 0.0001,
    "lora_rank": 16,
    "training_method": "lora"
  }
}
```

### GPU Infrastructure

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/gpu/settings` | Get GPU backend configuration |
| `PUT` | `/api/v1/gpu/settings` | Update GPU settings |
| `GET` | `/api/v1/gpu/status` | Infrastructure status & metrics |
| `POST` | `/api/v1/gpu/instances/spin-up` | Manually create GPU instance |
| `POST` | `/api/v1/gpu/instances/{id}/tear-down` | Terminate instance |

### Real-time Streaming (SSE)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/jobs/{job_id}/stream/ticket` | Get SSE access ticket (30s TTL) |
| `GET` | `/api/v1/jobs/{job_id}/stream?ticket=<t>` | Stream progress events |

### Worker API (for Remote GPU Workers)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/worker/next-job` | Claim next pending job (atomic) |
| `POST` | `/api/v1/worker/{job_id}/result` | Upload generation result |
| `POST` | `/api/v1/worker/{job_id}/progress` | Report progress (0-100) |
| `GET` | `/api/v1/worker/{job_id}/cancelled` | Check if job was cancelled |

### Users

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/users/me` | Current user profile |

---

## Database Models

### ER Diagram

```
┌──────────┐     ┌─────────────────┐     ┌──────────┐
│  users   │────<│ generation_jobs  │────<│  tracks  │
└──────────┘     └─────────────────┘     └──────────┘
     │                    │
     │           ┌────────┴────────┐
     │           │  lora_adapters  │
     │           └────────┬────────┘
     │                    │
     │           ┌────────┴────────┐
     │           │ finetune_jobs   │
     │           └─────────────────┘
     │
     ├────<┌──────────────┐
     │     │audio_uploads │
     │     └──────────────┘
     │
     └────<┌──────────┐     ┌────────────────┐
           │ datasets  │────<│ dataset_tracks │
           └──────────┘     └────────────────┘
```

### Key Tables

| Table | Description |
|-------|-------------|
| `users` | Synced from Clerk. Fields: `clerk_id`, `email`, `display_name` |
| `generation_jobs` | Music generation requests. Status: pending → queued → running → completed/failed/cancelled |
| `tracks` | Generated audio files. Linked 1:1 to completed jobs |
| `audio_uploads` | User-uploaded audio for fine-tuning datasets |
| `datasets` | Collections of audio tracks for training |
| `dataset_tracks` | Junction: uploads linked to datasets with metadata (lyrics, BPM, key) |
| `finetune_jobs` | LoRA training jobs. Tracks progress 0-100% |
| `lora_adapters` | Trained LoRA weights. Linked 1:1 to completed fine-tune jobs |

### Migrations

```bash
# Run all migrations
alembic upgrade head

# Create new migration
alembic revision --autogenerate -m "description"
```

| Version | Description |
|---------|-------------|
| 001 | Initial schema (users, jobs, tracks) |
| 002 | Composite indexes for query performance |
| 003 | ACE-Step support (model_name, generation_params, lora_adapter_id) |
| 004 | Fine-tuning models (finetune_jobs, lora_adapters, datasets, uploads) |
| 005 | Compute mode column (CPU vs GPU routing) |

---

## Music Generation Engines

### ACE-Step 1.5 (Primary)

Hybrid Language Model + Diffusion Transformer architecture for high-quality music generation.

| Parameter | Range | Default | Description |
|-----------|-------|---------|-------------|
| `inference_steps` | 1-8 | 8 | Diffusion steps (more = higher quality) |
| `guidance_scale` | 1-10 | 5.0 | Prompt adherence strength |
| `bpm` | 60-200 | auto | Beats per minute |
| `key` | C major, A minor, etc. | auto | Musical key |
| `time_signature` | 4/4, 3/4, 6/8 | 4/4 | Time signature |
| `task_type` | text2music, lyrics2music | text2music | Generation mode |

- **Max duration**: 120 seconds (Colab T4 safe)
- **Sample rate**: 32,000 Hz
- **LoRA support**: Apply custom adapters via `lora_adapter_id`
- **CPU offload**: Enabled via `ACE_STEP_CPU_OFFLOAD=true` to reduce VRAM usage

### YuE (Experimental)

Two-stage architecture (S1 7B params + S2 1B params) for vocal music generation.

| Parameter | Range | Default | Description |
|-----------|-------|---------|-------------|
| `temperature` | 0.1-2.0 | 0.8 | Sampling temperature |
| `top_p` | 0.1-1.0 | 0.9 | Nucleus sampling |
| `repetition_penalty` | 1.0-2.0 | 1.2 | Repetition penalty |
| `num_segments` | 1-2 | 1 | Audio segments |

- **Max duration**: 60 seconds
- **Requires**: Lyrics input
- **4-bit quantization**: Enabled via `YUE_USE_4BIT=true` for Colab

### Mock Generator (Development)

Generates silent audio for testing without GPU. Enable with `MOCK_GPU=true`.

---

## Worker Architecture

### Local Workers (Celery)

```
FastAPI → Redis (broker) → Celery Worker → Redis (results) → FastAPI → PostgreSQL
```

Jobs dispatched when `compute_mode="cpu"`. Worker executes locally using available hardware.

### Remote Workers (HTTP Polling)

```
Remote GPU Worker ──► GET  /worker/next-job        (claim job)
                 ──► POST /worker/{id}/progress    (report %)
                 ──► GET  /worker/{id}/cancelled   (check cancel)
                 ──► POST /worker/{id}/result      (upload result)
```

Jobs with `compute_mode="gpu"` stay in `pending` state. Remote workers (Colab, RunPod) poll the API to claim and process jobs. **No database credentials needed** — workers only interact via HTTP + S3.

### Celery Beat (Periodic Tasks)

| Task | Interval | Description |
|------|----------|-------------|
| `cleanup_stale_jobs` | 5 min | Timeout jobs pending/running >10 min |
| `run_autoscaler` | 30 sec | Scale GPU instances based on queue depth |

---

## GPU Farm Integration

Lofty supports three GPU infrastructure backends, configured via `GPU_BACKEND` environment variable.

### Architecture

```
┌──────────────────────────────────────────────────────────┐
│                    Lofty API Server                       │
│                                                          │
│  ┌─────────────┐    ┌─────────────┐    ┌──────────────┐ │
│  │ GPU Settings │    │  Autoscaler │    │ Worker API   │ │
│  │  Endpoint    │    │  (30s loop) │    │ (HTTP Poll)  │ │
│  └──────┬──────┘    └──────┬──────┘    └──────┬───────┘ │
│         │                  │                   │         │
│         └──────────┬───────┘                   │         │
│                    ▼                           │         │
│         ┌──────────────────┐                   │         │
│         │  GpuProvisioner  │                   │         │
│         │  (abstract)      │                   │         │
│         └────────┬─────────┘                   │         │
│                  │                             │         │
└──────────────────┼─────────────────────────────┼─────────┘
                   │                             │
        ┌──────────┼──────────┐                  │
        ▼          ▼          ▼                  ▼
  ┌──────────┐ ┌────────┐ ┌────────┐   ┌──────────────┐
  │  Local   │ │ Google │ │ Cloud  │   │ GPU Workers  │
  │  GPU     │ │ Colab  │ │RunPod/ │   │ (any backend)│
  │          │ │        │ │Vast.ai │   │              │
  └──────────┘ └────────┘ └────────┘   └──────────────┘
```

### Backend: `local`

Uses the machine's own GPU/CPU. Zero configuration, zero cost.

```env
GPU_BACKEND=local
```

### Backend: `google` (Colab)

Manual setup via Google Colab notebooks. Workers poll the Lofty API for jobs.

```env
GPU_BACKEND=google
WORKER_API_KEY=shared-secret-for-workers
```

**Colab Setup:**

1. Open the Colab notebook from `GET /api/v1/gpu/status`
2. Set the API URL and worker key
3. Worker automatically polls for jobs, generates music, uploads results

```python
# Colab worker loop (simplified)
while True:
    job = requests.get(f"{API_URL}/worker/next-job", headers=auth).json()
    if job:
        audio = generate(job["prompt"], job["params"])
        requests.post(f"{API_URL}/worker/{job['id']}/result", files={"audio": audio})
    time.sleep(5)
```

### Backend: `cloud` (RunPod / Vast.ai)

API-driven provisioning with automatic scaling.

```env
GPU_BACKEND=cloud
CLOUD_GPU_API_KEY=your-provider-api-key
AUTOSCALER_ENABLED=true
AUTOSCALER_MIN_INSTANCES=0
AUTOSCALER_MAX_INSTANCES=3
AUTOSCALER_IDLE_TIMEOUT=300
```

### Autoscaler

The autoscaler runs every 30 seconds and:

1. **Scales UP** when jobs are queued and no idle workers exist
2. **Scales DOWN** when the queue is empty and instances have been idle > `AUTOSCALER_IDLE_TIMEOUT`
3. Enforces a **60-second cooldown** between scaling actions to prevent thrashing

```
Queue depth > 0 + No idle workers → Spin up instance (up to max)
Queue depth = 0 + Idle > timeout  → Tear down instance (down to min)
```

### GPU Management API

```bash
# Check infrastructure status
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/gpu/status

# Update GPU settings
curl -X PUT -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"backend": "cloud", "autoscaler_enabled": true}' \
  http://localhost:8000/api/v1/gpu/settings

# Manually spin up an instance
curl -X POST -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/gpu/instances/spin-up

# Tear down an instance
curl -X POST -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/gpu/instances/{instance_id}/tear-down
```

---

## Authentication & Security

### Clerk JWT Verification

All `/api/v1/*` endpoints require a valid Clerk JWT token:

```
Authorization: Bearer <clerk_jwt_token>
```

- JWKS verification with **1-hour cache TTL**
- Auto-upsert users on first login (Clerk → PostgreSQL sync)
- Issuer verification in production (prevents cross-app token reuse)

### Rate Limiting

Redis-based sliding window rate limiter:

- **Default**: 10 requests/minute per user
- **Burst**: 3 additional requests allowed
- **Fail-closed**: Rejects requests if Redis is unavailable

### Worker Authentication

Remote workers authenticate with a shared API key:

```
X-Worker-Key: <WORKER_API_KEY>
```

### Security Patterns

- **Presigned URLs** — S3 download links expire after 1 hour. No storage credentials exposed to clients.
- **Ticket-based SSE** — Short-lived (30s), single-use tokens for SSE connections. Prevents JWT leakage in browser history/logs.
- **Distributed locking** — Redis `SET NX` with TTL prevents duplicate concurrent jobs per user.
- **User scoping** — All queries filter by `user_id`. Users cannot access other users' data.

---

## Real-time Progress (SSE)

### Connection Flow

```
1. Client: POST /api/v1/jobs/{id}/stream/ticket
   → Response: { "ticket": "abc123" }    (valid 30 seconds)

2. Client: GET /api/v1/jobs/{id}/stream?ticket=abc123
   → SSE connection established

3. Server pushes events:
   event: progress
   data: {"progress": 45, "status": "running"}

   event: complete
   data: {"track_id": "uuid"}

   event: error
   data: {"message": "Out of memory"}
```

### Event Types

| Event | Description | Data Fields |
|-------|-------------|-------------|
| `progress` | Generation in progress | `progress` (0-100), `status` |
| `complete` | Generation finished | `track_id` |
| `error` | Generation failed | `message` |
| `cancelled` | Job was cancelled | — |

### Implementation Details

- Progress read from Redis every **1 second** (cheap)
- Job status read from DB every **5 seconds** (expensive)
- Results synced from Redis → DB on-the-fly during streaming
- Heartbeat every **15 seconds** to keep connection alive

---

## Fine-Tuning Pipeline

### Workflow

```
1. Upload audio files        → POST /api/v1/uploads
2. Create a dataset          → POST /api/v1/datasets
3. Add tracks to dataset     → POST /api/v1/datasets/{id}/tracks
   (with lyrics, BPM, key metadata)
4. Process dataset           → POST /api/v1/datasets/{id}/process
5. Start fine-tuning         → POST /api/v1/finetune
6. Monitor progress          → GET  /api/v1/finetune/{id}
7. Use trained adapter       → POST /api/v1/jobs
   (set lora_adapter_id)
```

### Training Configuration

```json
{
  "max_epochs": 50,
  "batch_size": 4,
  "learning_rate": 0.0001,
  "lora_rank": 16,
  "training_method": "lora"
}
```

### Supported Training Methods

- **LoRA** — Low-Rank Adaptation. Efficient fine-tuning with small adapter files.
- **LoKR** — Low-Rank Kronecker. Alternative factorization method.

---

## Configuration Reference

### Core

| Variable | Default | Description |
|----------|---------|-------------|
| `DEBUG` | `false` | Enable debug mode |
| `CORS_ORIGINS` | `http://localhost:3000` | Allowed CORS origins |

### Database

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL connection string (`postgresql+asyncpg://...`) |

### Redis

| Variable | Description |
|----------|-------------|
| `REDIS_URL` | Redis URL for caching and progress |
| `CELERY_BROKER_URL` | Celery task broker URL |
| `CELERY_RESULT_BACKEND` | Celery result backend URL |

### Authentication (Clerk)

| Variable | Description |
|----------|-------------|
| `CLERK_PUBLISHABLE_KEY` | Clerk publishable key |
| `CLERK_SECRET_KEY` | Clerk secret key |
| `CLERK_JWKS_URL` | JWKS endpoint URL |
| `CLERK_JWT_ISSUER` | Expected JWT issuer |

### Storage (S3/MinIO)

| Variable | Default | Description |
|----------|---------|-------------|
| `STORAGE_ENDPOINT` | — | Internal S3 endpoint (e.g., `minio:9000`) |
| `STORAGE_ACCESS_KEY` | — | S3 access key |
| `STORAGE_SECRET_KEY` | — | S3 secret key |
| `STORAGE_PUBLIC_ENDPOINT` | — | Public S3 endpoint for presigned URLs |
| `STORAGE_USE_SSL` | `false` | Enable SSL for S3 connections |

### ACE-Step Engine

| Variable | Default | Description |
|----------|---------|-------------|
| `ACE_STEP_ENABLED` | `true` | Enable ACE-Step engine |
| `MOCK_GPU` | `false` | Use mock generator (dev/testing) |
| `ACE_STEP_MODEL_PATH` | — | Path to model weights |
| `ACE_STEP_CACHE_DIR` | — | HuggingFace cache directory |
| `ACE_STEP_CPU_OFFLOAD` | `false` | Offload to CPU to save VRAM |
| `ACE_STEP_MAX_DURATION_SECONDS` | `120` | Maximum generation duration |

### YuE Engine

| Variable | Default | Description |
|----------|---------|-------------|
| `YUE_ENABLED` | `false` | Enable YuE engine |
| `YUE_CACHE_DIR` | — | HuggingFace cache directory |
| `YUE_USE_4BIT` | `false` | Enable 4-bit quantization |
| `YUE_MAX_DURATION_SECONDS` | `60` | Maximum generation duration |

### GPU Infrastructure

| Variable | Default | Description |
|----------|---------|-------------|
| `GPU_BACKEND` | `local` | Backend: `local`, `google`, `cloud` |
| `AUTOSCALER_ENABLED` | `false` | Enable queue-based autoscaling |
| `AUTOSCALER_MIN_INSTANCES` | `0` | Minimum GPU instances |
| `AUTOSCALER_MAX_INSTANCES` | `3` | Maximum GPU instances |
| `AUTOSCALER_IDLE_TIMEOUT` | `300` | Seconds before idle teardown |
| `CLOUD_GPU_API_KEY` | — | RunPod/Vast.ai API key |
| `WORKER_API_KEY` | — | Shared secret for worker auth |

### Rate Limiting

| Variable | Default | Description |
|----------|---------|-------------|
| `RATE_LIMIT_PER_MINUTE` | `10` | Requests per minute per user |
| `RATE_LIMIT_BURST` | `3` | Burst allowance |

---

## Deployment

### Docker Compose (Development)

```bash
docker-compose up
```

Starts: PostgreSQL, Redis, MinIO, API, Worker (mock GPU), Frontend.

### Production

1. Use managed PostgreSQL and Redis
2. Use AWS S3 or MinIO on persistent storage
3. Set all environment variables (especially `CLERK_*`, storage credentials)
4. Set `CORS_ORIGINS` to your frontend domain
5. Enable SSL/TLS for all external connections
6. Run migrations: `alembic upgrade head`

### GPU Worker on Google Colab

1. Navigate to GPU Farm page in the UI
2. Copy the Colab setup snippet
3. Run in a Colab notebook with GPU runtime
4. Worker automatically polls and processes jobs

### CI/CD

GitHub Actions pipeline (`.github/workflows/ci.yml`):
- **Backend**: ruff lint + format check, pytest with PostgreSQL/Redis
- **Frontend**: TypeScript check + production build

---

## License

MIT

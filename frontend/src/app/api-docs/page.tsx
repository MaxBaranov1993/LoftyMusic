"use client";

import { useState, useRef, useEffect } from "react";
import {
  ChevronRight,
  Copy,
  Check,
  Terminal,
  Shield,
  Zap,
  Database,
  Music,
  Upload,
  Layers,
  Cpu,
  Radio,
  Server,
  Clock,
  AlertTriangle,
  Hash,
  ArrowRight,
  ExternalLink,
  ChevronDown,
} from "lucide-react";

/* ─────────────────────────────────────────────
   Types
   ───────────────────────────────────────────── */

type HttpMethod = "GET" | "POST" | "PUT" | "DELETE";

interface Endpoint {
  method: HttpMethod;
  path: string;
  summary: string;
  auth: "bearer" | "worker-key" | "none";
  rateLimit?: boolean;
  body?: string;
  query?: string;
  response?: string;
  notes?: string;
}

interface EndpointGroup {
  id: string;
  title: string;
  icon: React.ElementType;
  description: string;
  endpoints: Endpoint[];
}

/* ─────────────────────────────────────────────
   Helpers
   ───────────────────────────────────────────── */

const METHOD_COLORS: Record<HttpMethod, string> = {
  GET: "text-emerald-400 bg-emerald-400/10 border-emerald-400/20",
  POST: "text-blue-400 bg-blue-400/10 border-blue-400/20",
  PUT: "text-amber-400 bg-amber-400/10 border-amber-400/20",
  DELETE: "text-red-400 bg-red-400/10 border-red-400/20",
};

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      onClick={() => {
        navigator.clipboard.writeText(text);
        setCopied(true);
        setTimeout(() => setCopied(false), 1500);
      }}
      className="absolute top-3 right-3 p-1.5 rounded-md bg-white/5 hover:bg-white/10 transition-colors text-[#b3b3b3] hover:text-white"
      title="Copy"
    >
      {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
    </button>
  );
}

function CodeBlock({ code, lang = "bash" }: { code: string; lang?: string }) {
  return (
    <div className="relative group">
      <pre className="bg-[#0a0a0a] border border-[#1a1a1a] rounded-lg p-4 overflow-x-auto text-[13px] leading-relaxed font-mono text-[#e0e0e0]">
        <code>{code}</code>
      </pre>
      <CopyButton text={code} />
    </div>
  );
}

function JsonBlock({ code }: { code: string }) {
  return <CodeBlock code={code} lang="json" />;
}

function MethodBadge({ method }: { method: HttpMethod }) {
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 text-[11px] font-bold tracking-wider uppercase rounded border ${METHOD_COLORS[method]} font-mono`}
    >
      {method}
    </span>
  );
}

function AuthBadge({ auth }: { auth: "bearer" | "worker-key" | "none" }) {
  if (auth === "none")
    return (
      <span className="text-[11px] text-[#666] font-mono tracking-wide uppercase">
        public
      </span>
    );
  if (auth === "worker-key")
    return (
      <span className="text-[11px] text-amber-500/80 font-mono tracking-wide uppercase flex items-center gap-1">
        <Shield className="w-3 h-3" /> worker-key
      </span>
    );
  return (
    <span className="text-[11px] text-[#1DB954]/80 font-mono tracking-wide uppercase flex items-center gap-1">
      <Shield className="w-3 h-3" /> bearer
    </span>
  );
}

/* ─────────────────────────────────────────────
   Endpoint Accordion
   ───────────────────────────────────────────── */

function EndpointCard({ ep }: { ep: Endpoint }) {
  const [open, setOpen] = useState(false);
  const contentRef = useRef<HTMLDivElement>(null);
  const [height, setHeight] = useState(0);

  useEffect(() => {
    if (contentRef.current) {
      setHeight(open ? contentRef.current.scrollHeight : 0);
    }
  }, [open]);

  return (
    <div className="border border-[#1a1a1a] rounded-lg overflow-hidden hover:border-[#282828] transition-colors">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-[#0d0d0d] transition-colors"
      >
        <MethodBadge method={ep.method} />
        <code className="text-sm font-mono text-white flex-1 truncate">
          {ep.path}
        </code>
        <AuthBadge auth={ep.auth} />
        {ep.rateLimit && (
          <span title="Rate limited"><Clock className="w-3 h-3 text-amber-500/50" /></span>
        )}
        <ChevronDown
          className={`w-4 h-4 text-[#666] transition-transform duration-200 ${
            open ? "rotate-180" : ""
          }`}
        />
      </button>

      <div
        style={{ height }}
        className="overflow-hidden transition-[height] duration-200 ease-out"
      >
        <div ref={contentRef} className="px-4 pb-4 pt-1 space-y-3 border-t border-[#111]">
          <p className="text-sm text-[#b3b3b3] leading-relaxed">{ep.summary}</p>

          {ep.query && (
            <div>
              <h5 className="text-[11px] uppercase tracking-wider text-[#666] mb-1.5 font-semibold">
                Query Parameters
              </h5>
              <CodeBlock code={ep.query} />
            </div>
          )}

          {ep.body && (
            <div>
              <h5 className="text-[11px] uppercase tracking-wider text-[#666] mb-1.5 font-semibold">
                Request Body
              </h5>
              <JsonBlock code={ep.body} />
            </div>
          )}

          {ep.response && (
            <div>
              <h5 className="text-[11px] uppercase tracking-wider text-[#666] mb-1.5 font-semibold">
                Response
              </h5>
              <JsonBlock code={ep.response} />
            </div>
          )}

          {ep.notes && (
            <div className="flex items-start gap-2 text-xs text-amber-500/70 bg-amber-500/5 border border-amber-500/10 rounded-md p-2.5">
              <AlertTriangle className="w-3.5 h-3.5 mt-0.5 shrink-0" />
              <span>{ep.notes}</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

/* ─────────────────────────────────────────────
   Section Nav (left sidebar)
   ───────────────────────────────────────────── */

function SideNav({
  groups,
  activeId,
  onSelect,
}: {
  groups: { id: string; title: string; icon: React.ElementType }[];
  activeId: string;
  onSelect: (id: string) => void;
}) {
  const sections = [
    { id: "overview", title: "Overview" },
    { id: "auth", title: "Authentication" },
    ...groups.map((g) => ({ id: g.id, title: g.title })),
    { id: "errors", title: "Error Handling" },
    { id: "rate-limiting", title: "Rate Limiting" },
    { id: "quickstart", title: "Quick Start" },
  ];

  return (
    <nav className="space-y-0.5">
      {sections.map((s) => (
        <button
          key={s.id}
          onClick={() => onSelect(s.id)}
          className={`w-full text-left px-3 py-1.5 rounded-md text-[13px] transition-all duration-150 ${
            activeId === s.id
              ? "text-[#1DB954] bg-[#1DB954]/8 font-medium"
              : "text-[#808080] hover:text-[#b3b3b3] hover:bg-[#111]"
          }`}
        >
          {s.title}
        </button>
      ))}
    </nav>
  );
}

/* ─────────────────────────────────────────────
   API Data
   ───────────────────────────────────────────── */

const ENDPOINT_GROUPS: EndpointGroup[] = [
  {
    id: "health",
    title: "Health",
    icon: Zap,
    description: "Service health and readiness probes for monitoring and orchestration.",
    endpoints: [
      {
        method: "GET",
        path: "/health",
        summary: "Basic health check. Returns 200 if the API process is running.",
        auth: "none",
        response: `{
  "status": "ok",
  "service": "lofty"
}`,
      },
      {
        method: "GET",
        path: "/health/ready",
        summary:
          "Readiness probe. Verifies database, Redis, and S3/MinIO storage connectivity. Use for Kubernetes readiness gates or load balancer health checks.",
        auth: "none",
        response: `{
  "ready": true,
  "database": "ok",
  "redis": "ok",
  "storage": "ok"
}`,
      },
    ],
  },
  {
    id: "jobs",
    title: "Jobs",
    icon: Music,
    description:
      "Create and manage music generation jobs. Each job produces one audio track via ACE-Step 1.5 or YuE model.",
    endpoints: [
      {
        method: "POST",
        path: "/api/v1/jobs",
        summary:
          "Create a new music generation job. The job is queued for a GPU worker. Only one active job per user at a time.",
        auth: "bearer",
        rateLimit: true,
        body: `{
  "prompt": "upbeat electronic dance music with synth leads",
  "lyrics": "",                    // optional, required for YuE
  "duration_seconds": 30.0,        // 1.0 - 600.0
  "model_name": "ace-step-1.5",   // "ace-step-1.5" | "yue"
  "compute_mode": "gpu",           // "cpu" | "gpu"
  "lora_adapter_id": null,         // UUID, optional (ACE-Step only)
  "generation_params": {
    "guidance_scale": 5.0,         // 1.0 - 10.0
    "quality_preset": "balanced",  // "draft" | "balanced" | "high"
    "language": "en",
    "seed": -1,                    // -1 = random
    "inference_steps": 8,          // 1-8 (ACE-Step)
    "bpm": 120,                    // 40-240, optional
    "key": "C major",             // optional
    "time_signature": "4/4"
  }
}`,
        response: `{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "prompt": "upbeat electronic dance music with synth leads",
  "lyrics": "",
  "duration_seconds": 30.0,
  "model_name": "ace-step-1.5",
  "generation_params": { ... },
  "lora_adapter_id": null,
  "compute_mode": "gpu",
  "error_message": null,
  "progress": 0,
  "created_at": "2025-01-15T12:00:00Z",
  "started_at": null,
  "completed_at": null,
  "track": null
}`,
        notes:
          "Returns 409 Conflict if you already have an active (pending/queued/running) job.",
      },
      {
        method: "GET",
        path: "/api/v1/jobs",
        summary: "List the current user's generation jobs with pagination and optional status filter.",
        auth: "bearer",
        query: `?status=completed    // pending|queued|running|completed|failed|cancelled
&page=1              // >= 1
&per_page=20         // 1-100`,
        response: `{
  "items": [ { ...JobResponse } ],
  "total": 42,
  "page": 1,
  "per_page": 20,
  "pages": 3
}`,
      },
      {
        method: "GET",
        path: "/api/v1/jobs/{job_id}",
        summary:
          "Get a specific job by ID. Includes track data if completed. Auto-syncs results from Redis for remote workers.",
        auth: "bearer",
        response: `{
  "id": "550e8400-...",
  "status": "completed",
  "prompt": "...",
  "progress": 100,
  "track": {
    "id": "...",
    "job_id": "...",
    "title": "upbeat electronic dance...",
    "duration_seconds": 30.0,
    "sample_rate": 44100,
    "format": "wav",
    "file_size_bytes": 2646044,
    "download_url": null,
    "created_at": "..."
  },
  ...
}`,
      },
      {
        method: "POST",
        path: "/api/v1/jobs/{job_id}/cancel",
        summary:
          "Cancel a pending, queued, or running job. Returns 204 on success, 409 if already terminal.",
        auth: "bearer",
      },
      {
        method: "DELETE",
        path: "/api/v1/jobs/{job_id}",
        summary: "Delete a job record. Returns 204 on success, 404 if not found.",
        auth: "bearer",
      },
    ],
  },
  {
    id: "sse",
    title: "SSE Streaming",
    icon: Radio,
    description:
      "Real-time job progress via Server-Sent Events. Uses ticket-based auth to avoid JWT leakage in URLs.",
    endpoints: [
      {
        method: "POST",
        path: "/api/v1/jobs/{job_id}/stream/ticket",
        summary:
          "Create a short-lived (30s), single-use SSE ticket. Exchange your Bearer token for an opaque ticket.",
        auth: "bearer",
        response: `{
  "ticket": "abc123...urlsafe-token"
}`,
      },
      {
        method: "GET",
        path: "/api/v1/jobs/{job_id}/stream?ticket=<ticket>",
        summary:
          "Open an SSE connection for real-time progress. Emits: progress, complete, error, cancelled events. Heartbeat every 15s.",
        auth: "none",
        notes: "Ticket is consumed on first use. Connection auto-closes on terminal status.",
        response: `event: progress
data: {"progress": 45, "status": "running"}

event: complete
data: {"status": "completed", "track_id": "..."}

event: error
data: {"status": "failed", "message": "OOM on GPU"}

event: cancelled
data: {"status": "cancelled"}`,
      },
    ],
  },
  {
    id: "tracks",
    title: "Tracks",
    icon: Music,
    description: "Access generated audio tracks with presigned download URLs.",
    endpoints: [
      {
        method: "GET",
        path: "/api/v1/tracks",
        summary: "List the current user's generated tracks, paginated.",
        auth: "bearer",
        query: `?page=1&per_page=20`,
        response: `{
  "items": [
    {
      "id": "...",
      "job_id": "...",
      "title": "upbeat electronic dance...",
      "duration_seconds": 30.0,
      "sample_rate": 44100,
      "format": "wav",
      "file_size_bytes": 2646044,
      "download_url": null,
      "created_at": "2025-01-15T12:05:00Z"
    }
  ],
  "total": 10,
  "page": 1,
  "per_page": 20,
  "pages": 1
}`,
      },
      {
        method: "GET",
        path: "/api/v1/tracks/{track_id}",
        summary:
          "Get a specific track with a presigned download URL (valid for limited time).",
        auth: "bearer",
        response: `{
  "id": "...",
  "title": "...",
  "download_url": "https://storage.example.com/tracks/...?signature=...",
  ...
}`,
      },
      {
        method: "GET",
        path: "/api/v1/tracks/{track_id}/download",
        summary:
          "Redirect (302) to a presigned S3 download URL. Use this for direct browser downloads.",
        auth: "bearer",
        notes: "Returns HTTP 302 redirect, not JSON.",
      },
    ],
  },
  {
    id: "uploads",
    title: "Uploads",
    icon: Upload,
    description:
      "Upload audio files for fine-tuning training datasets. Supports WAV, MP3, FLAC, OGG up to 50 MB.",
    endpoints: [
      {
        method: "POST",
        path: "/api/v1/uploads",
        summary:
          "Upload an audio file via multipart/form-data. Auto-dispatches BPM/key analysis task.",
        auth: "bearer",
        body: `// multipart/form-data
Content-Type: multipart/form-data

file: <binary audio data>   // WAV, MP3, FLAC, OGG; max 50 MB`,
        response: `{
  "id": "...",
  "storage_key": "uploads/user-id/abc123.wav",
  "original_filename": "my_song.wav",
  "file_size_bytes": 5242880,
  "duration_seconds": 30.0,
  "format": "wav",
  "analysis": null,
  "created_at": "...",
  "updated_at": null
}`,
        notes: "analysis field is populated asynchronously after BPM/key detection completes.",
      },
      {
        method: "GET",
        path: "/api/v1/uploads",
        summary: "List the current user's audio uploads.",
        auth: "bearer",
        query: `?page=1&per_page=20`,
      },
      {
        method: "GET",
        path: "/api/v1/uploads/{upload_id}",
        summary: "Get a specific upload by ID.",
        auth: "bearer",
      },
      {
        method: "DELETE",
        path: "/api/v1/uploads/{upload_id}",
        summary: "Delete an upload from S3 and database. Returns 204.",
        auth: "bearer",
      },
    ],
  },
  {
    id: "datasets",
    title: "Datasets",
    icon: Layers,
    description: "Manage training datasets for fine-tuning. Link uploads, add metadata, process for training.",
    endpoints: [
      {
        method: "POST",
        path: "/api/v1/datasets",
        summary: "Create a new empty dataset.",
        auth: "bearer",
        body: `{
  "name": "My Jazz Collection",
  "description": "Jazz tracks for LoRA training"
}`,
        response: `{
  "id": "...",
  "name": "My Jazz Collection",
  "description": "Jazz tracks for LoRA training",
  "status": "pending",
  "num_tracks": 0,
  "total_duration_seconds": 0.0,
  "created_at": "...",
  "tracks": []
}`,
      },
      {
        method: "GET",
        path: "/api/v1/datasets",
        summary: "List datasets with pagination.",
        auth: "bearer",
        query: `?page=1&per_page=20`,
      },
      {
        method: "GET",
        path: "/api/v1/datasets/{dataset_id}",
        summary: "Get a dataset with all its tracks.",
        auth: "bearer",
      },
      {
        method: "POST",
        path: "/api/v1/datasets/{dataset_id}/tracks",
        summary: "Add a track to a dataset by linking an existing upload.",
        auth: "bearer",
        body: `{
  "upload_id": "...",
  "lyrics": "[verse] Walking down...",
  "caption": "smooth jazz ballad",
  "bpm": 90,
  "key_scale": "Bb minor"
}`,
      },
      {
        method: "DELETE",
        path: "/api/v1/datasets/{dataset_id}/tracks/{track_id}",
        summary: "Remove a track from a dataset.",
        auth: "bearer",
      },
      {
        method: "POST",
        path: "/api/v1/datasets/{dataset_id}/process",
        summary:
          "Process dataset: extract durations from all tracks. Transitions status pending → processing → ready.",
        auth: "bearer",
        notes: "Dataset must have at least 1 track. Only pending/failed datasets can be processed.",
        response: `{
  "status": "ready",
  "dataset_id": "..."
}`,
      },
      {
        method: "DELETE",
        path: "/api/v1/datasets/{dataset_id}",
        summary: "Delete a dataset and all its track links. Returns 204.",
        auth: "bearer",
      },
    ],
  },
  {
    id: "finetune",
    title: "Fine-Tuning",
    icon: Cpu,
    description:
      "Start LoRA/LoKR fine-tuning jobs on processed datasets. One active fine-tuning job per user.",
    endpoints: [
      {
        method: "POST",
        path: "/api/v1/finetune",
        summary:
          "Create a fine-tuning job. Requires a dataset with status 'ready'.",
        auth: "bearer",
        body: `{
  "dataset_id": "...",
  "name": "Jazz Style v1",
  "compute_mode": "gpu",
  "config": {
    "max_epochs": 500,       // 1-5000
    "batch_size": 1,          // 1-8
    "training_method": "lokr", // "lora" | "lokr"
    "learning_rate": 0.0001   // 1e-6 to 1e-2
  }
}`,
        response: `{
  "id": "...",
  "dataset_id": "...",
  "name": "Jazz Style v1",
  "status": "pending",
  "config": { ... },
  "compute_mode": "gpu",
  "progress": 0,
  "error_message": null,
  "adapter": null,
  "created_at": "...",
  ...
}`,
      },
      {
        method: "GET",
        path: "/api/v1/finetune",
        summary: "List fine-tuning jobs.",
        auth: "bearer",
        query: `?page=1&per_page=20`,
      },
      {
        method: "GET",
        path: "/api/v1/finetune/{job_id}",
        summary: "Get a fine-tuning job with its LoRA adapter (if completed).",
        auth: "bearer",
      },
      {
        method: "POST",
        path: "/api/v1/finetune/{job_id}/cancel",
        summary: "Cancel a pending or running fine-tuning job. Returns 204.",
        auth: "bearer",
      },
      {
        method: "DELETE",
        path: "/api/v1/finetune/{job_id}",
        summary:
          "Delete a fine-tuning job (only if completed/failed/cancelled). Also deletes the adapter.",
        auth: "bearer",
        notes: "Cannot delete active jobs — cancel first.",
      },
    ],
  },
  {
    id: "adapters",
    title: "LoRA Adapters",
    icon: Layers,
    description: "Manage trained LoRA adapters. Use adapter IDs when creating generation jobs for custom styles.",
    endpoints: [
      {
        method: "GET",
        path: "/api/v1/adapters",
        summary: "List the current user's LoRA adapters.",
        auth: "bearer",
        query: `?page=1&per_page=20`,
        response: `{
  "items": [
    {
      "id": "...",
      "name": "Jazz Style v1",
      "description": "Fine-tuned with 5 tracks",
      "base_model": "ACE-Step/Ace-Step1.5",
      "training_method": "lokr",
      "adapter_size_bytes": 2097152,
      "is_active": true,
      "created_at": "..."
    }
  ],
  "total": 1,
  "page": 1,
  "per_page": 20,
  "pages": 1
}`,
      },
      {
        method: "GET",
        path: "/api/v1/adapters/{adapter_id}",
        summary: "Get a specific LoRA adapter.",
        auth: "bearer",
      },
      {
        method: "DELETE",
        path: "/api/v1/adapters/{adapter_id}",
        summary: "Delete a LoRA adapter. Removes from S3 and marks inactive. Returns 204.",
        auth: "bearer",
      },
    ],
  },
  {
    id: "gpu",
    title: "GPU Management",
    icon: Cpu,
    description:
      "Configure GPU backends (local, Google Colab, cloud providers), manage instances, and monitor costs.",
    endpoints: [
      {
        method: "GET",
        path: "/api/v1/gpu/settings",
        summary: "Get current GPU backend configuration.",
        auth: "bearer",
        response: `{
  "backend": "local",
  "autoscaler_enabled": false,
  "autoscaler_min_instances": 0,
  "autoscaler_max_instances": 3,
  "autoscaler_idle_timeout": 300,
  "cloud_api_key_configured": false
}`,
      },
      {
        method: "PUT",
        path: "/api/v1/gpu/settings",
        summary: "Update GPU backend. Changes take effect immediately.",
        auth: "bearer",
        body: `{
  "backend": "google",         // "local" | "google" | "cloud"
  "cloud_api_key": "rp_...",  // optional, omit to keep existing
  "autoscaler_enabled": true,
  "autoscaler_max_instances": 5,
  "autoscaler_idle_timeout": 600
}`,
      },
      {
        method: "GET",
        path: "/api/v1/gpu/status",
        summary:
          "Get infrastructure status: active instances, costs, health. Includes Colab setup snippet when backend is 'google'.",
        auth: "bearer",
        response: `{
  "backend": "google",
  "status": "healthy",
  "instances": [
    {
      "id": "colab-abc123",
      "backend": "google",
      "status": "running",
      "gpu_type": "T4",
      "gpu_memory_mb": 15360,
      "cost_per_hour": 0.0,
      "created_at": 1705320000
    }
  ],
  "total_cost_per_hour": 0.0,
  "colab_setup_snippet": "# === Lofty GPU Worker..."
}`,
      },
      {
        method: "POST",
        path: "/api/v1/gpu/instances/spin-up",
        summary: "Manually spin up a new GPU instance.",
        auth: "bearer",
        query: `?gpu_type=auto   // "auto" or specific type`,
      },
      {
        method: "POST",
        path: "/api/v1/gpu/instances/{instance_id}/tear-down",
        summary: "Manually tear down a GPU instance. Returns 204.",
        auth: "bearer",
      },
    ],
  },
  {
    id: "worker",
    title: "Worker API",
    icon: Server,
    description:
      "HTTP polling API for remote GPU workers (Colab). Workers claim jobs, report progress, and upload results. No direct database access needed.",
    endpoints: [
      {
        method: "GET",
        path: "/api/v1/worker/next-job",
        summary:
          "Claim the next pending job atomically (SELECT ... FOR UPDATE SKIP LOCKED). Returns 204 if no jobs available.",
        auth: "worker-key",
        query: `?engine=ace-step     // "ace-step" | "yue" | omit for any
&compute_mode=gpu     // "cpu" | "gpu" | omit for any`,
        response: `{
  "job_id": "...",
  "user_id": "...",
  "prompt": "upbeat electronic...",
  "lyrics": "",
  "duration_seconds": 30.0,
  "model_name": "ace-step-1.5",
  "generation_params": { ... },
  "lora_adapter_id": null,
  "compute_mode": "gpu"
}`,
        notes: "Returns 204 No Content (no body) when queue is empty.",
      },
      {
        method: "POST",
        path: "/api/v1/worker/{job_id}/result",
        summary:
          "Upload generation result. Send audio file as multipart form data on success, or error message on failure.",
        auth: "worker-key",
        body: `// multipart/form-data
status: "completed"        // "completed" | "failed" | "cancelled"
duration: 30.0
sample_rate: 44100
format: "wav"
error_message: ""          // only for failed
audio_file: <binary>       // only for completed`,
      },
      {
        method: "POST",
        path: "/api/v1/worker/{job_id}/progress",
        summary: "Report generation progress (0-100). Stored in Redis for frontend polling.",
        auth: "worker-key",
        body: `{ "progress": 65 }`,
      },
      {
        method: "GET",
        path: "/api/v1/worker/{job_id}/cancelled",
        summary: "Check if a job has been cancelled by the user.",
        auth: "worker-key",
        response: `{ "cancelled": false }`,
      },
      {
        method: "GET",
        path: "/api/v1/worker/next-finetune-job",
        summary:
          "Claim the next pending fine-tuning job. Returns full dataset track data so the worker can train without DB access.",
        auth: "worker-key",
        query: `?compute_mode=gpu`,
        response: `{
  "job_id": "...",
  "user_id": "...",
  "job_name": "Jazz Style v1",
  "track_data": [
    {
      "storage_key": "uploads/user-id/abc.wav",
      "original_filename": "jazz1.wav",
      "format": "wav",
      "lyrics": "...",
      "caption": "smooth jazz",
      "bpm": 90,
      "key_scale": "Bb minor",
      "duration_seconds": 45.0
    }
  ],
  "config": { ... },
  "compute_mode": "gpu"
}`,
      },
      {
        method: "POST",
        path: "/api/v1/worker/{job_id}/finetune-progress",
        summary: "Report fine-tuning training progress.",
        auth: "worker-key",
        body: `{ "progress": 42 }`,
      },
      {
        method: "POST",
        path: "/api/v1/worker/{job_id}/finetune-result",
        summary:
          "Upload fine-tune result. On success, uploads adapter safetensors file and creates LoRAAdapter record.",
        auth: "worker-key",
        body: `// multipart/form-data
status: "completed"
training_method: "lokr"
num_tracks: 5
error_message: ""
adapter_file: <binary .safetensors>`,
      },
      {
        method: "GET",
        path: "/api/v1/worker/{job_id}/finetune-cancelled",
        summary: "Check if a fine-tuning job has been cancelled.",
        auth: "worker-key",
        response: `{ "cancelled": false }`,
      },
      {
        method: "GET",
        path: "/api/v1/worker/download/{storage_key}",
        summary:
          "Download a file from S3 storage. Proxies file so remote workers don't need direct MinIO access.",
        auth: "worker-key",
        notes: "Returns raw binary data with appropriate Content-Type header.",
      },
    ],
  },
];

/* ─────────────────────────────────────────────
   Main Page
   ───────────────────────────────────────────── */

export default function ApiDocsPage() {
  const [activeSection, setActiveSection] = useState("overview");
  const mainRef = useRef<HTMLDivElement>(null);

  const scrollToSection = (id: string) => {
    setActiveSection(id);
    const el = document.getElementById(`section-${id}`);
    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  };

  // Intersection observer for active section tracking
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            const id = entry.target.id.replace("section-", "");
            setActiveSection(id);
          }
        }
      },
      { rootMargin: "-80px 0px -70% 0px", threshold: 0 }
    );

    const sections = document.querySelectorAll("[id^='section-']");
    sections.forEach((s) => observer.observe(s));

    return () => observer.disconnect();
  }, []);

  return (
    <div className="min-h-screen bg-black -mx-4 sm:-mx-6 lg:-mx-8 -mt-8 px-0">
      {/* ── Header ── */}
      <header className="relative border-b border-[#1a1a1a] overflow-hidden">
        {/* Background glow */}
        <div className="absolute inset-0 -z-10">
          <div className="absolute top-0 left-1/4 w-96 h-96 bg-[#1DB954]/5 rounded-full blur-[120px]" />
          <div className="absolute bottom-0 right-1/4 w-64 h-64 bg-[#1DB954]/3 rounded-full blur-[100px]" />
        </div>

        <div className="max-w-7xl mx-auto px-6 py-16 sm:py-20">
          <div className="flex items-center gap-2 text-[#1DB954] text-sm font-mono tracking-wider mb-4">
            <Terminal className="w-4 h-4" />
            <span>REST API v1</span>
          </div>
          <h1 className="text-4xl sm:text-5xl font-bold tracking-tight text-white mb-4">
            Lofty API{" "}
            <span className="bg-gradient-to-r from-[#1DB954] to-[#1ed760] bg-clip-text text-transparent">
              Reference
            </span>
          </h1>
          <p className="text-[#808080] text-lg max-w-2xl leading-relaxed">
            Complete REST API documentation for the Lofty AI Music Generation
            Platform. Generate music, manage tracks, fine-tune models, and
            orchestrate GPU workers.
          </p>

          <div className="flex items-center gap-6 mt-8 text-sm">
            <div className="flex items-center gap-2 text-[#b3b3b3]">
              <div className="w-2 h-2 rounded-full bg-[#1DB954] animate-pulse" />
              Base URL
            </div>
            <code className="bg-[#111] border border-[#1a1a1a] rounded-md px-3 py-1.5 text-[#e0e0e0] text-sm font-mono">
              https://your-domain.com/api/v1
            </code>
          </div>
        </div>
      </header>

      {/* ── Body ── */}
      <div className="max-w-7xl mx-auto flex gap-0">
        {/* Sidebar */}
        <aside className="hidden lg:block w-56 shrink-0 border-r border-[#111]">
          <div className="sticky top-20 py-8 px-4">
            <div className="text-[11px] uppercase tracking-widest text-[#555] font-semibold mb-3 px-3">
              On this page
            </div>
            <SideNav
              groups={ENDPOINT_GROUPS}
              activeId={activeSection}
              onSelect={scrollToSection}
            />
          </div>
        </aside>

        {/* Main content */}
        <main ref={mainRef} className="flex-1 min-w-0 px-6 sm:px-10 py-12 space-y-20">
          {/* ── Overview ── */}
          <section id="section-overview" className="space-y-6">
            <h2 className="text-2xl font-bold text-white flex items-center gap-3">
              <Hash className="w-5 h-5 text-[#1DB954]" />
              Architecture Overview
            </h2>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {[
                {
                  icon: Zap,
                  title: "FastAPI Backend",
                  desc: "Async Python API with automatic OpenAPI schema generation, Pydantic validation, and structured logging.",
                },
                {
                  icon: Database,
                  title: "PostgreSQL + Redis",
                  desc: "PostgreSQL for persistent storage (SQLAlchemy 2.0 async). Redis for job queue, rate limiting, and real-time progress.",
                },
                {
                  icon: Music,
                  title: "ACE-Step 1.5 & YuE",
                  desc: "Two ML models: ACE-Step for text-to-music (up to 10 min), YuE for lyrics-to-vocals. LoRA fine-tuning supported.",
                },
                {
                  icon: Shield,
                  title: "Clerk Auth",
                  desc: "JWT authentication via Clerk. JWKS verification with key caching. Automatic user upsert on first request.",
                },
                {
                  icon: Upload,
                  title: "S3/MinIO Storage",
                  desc: "Audio files stored in S3-compatible storage. Presigned download URLs. Supports local MinIO or cloud S3.",
                },
                {
                  icon: Server,
                  title: "GPU Workers",
                  desc: "Celery task queue or HTTP polling for remote workers (Colab). Supports local GPU, Google Colab, RunPod, Vast.ai.",
                },
              ].map((item) => (
                <div
                  key={item.title}
                  className="bg-[#0a0a0a] border border-[#1a1a1a] rounded-xl p-5 hover:border-[#282828] transition-colors"
                >
                  <div className="w-9 h-9 rounded-lg bg-[#1DB954]/10 flex items-center justify-center mb-3">
                    <item.icon className="w-4.5 h-4.5 text-[#1DB954]" />
                  </div>
                  <h3 className="text-sm font-semibold text-white mb-1">
                    {item.title}
                  </h3>
                  <p className="text-xs text-[#808080] leading-relaxed">
                    {item.desc}
                  </p>
                </div>
              ))}
            </div>

            <div className="bg-[#0a0a0a] border border-[#1a1a1a] rounded-xl p-6">
              <h3 className="text-sm font-semibold text-white mb-3">
                Request Flow
              </h3>
              <div className="flex flex-wrap items-center gap-2 text-sm text-[#b3b3b3]">
                {[
                  "Client",
                  "Bearer JWT",
                  "FastAPI",
                  "Rate Limit",
                  "Service Layer",
                  "PostgreSQL / Redis",
                  "Celery Worker",
                  "GPU Inference",
                  "S3 Storage",
                ].map((step, i, arr) => (
                  <span key={step} className="flex items-center gap-2">
                    <span className="bg-[#181818] border border-[#282828] rounded-md px-2.5 py-1 text-xs font-mono">
                      {step}
                    </span>
                    {i < arr.length - 1 && (
                      <ArrowRight className="w-3 h-3 text-[#333]" />
                    )}
                  </span>
                ))}
              </div>
            </div>
          </section>

          {/* ── Authentication ── */}
          <section id="section-auth" className="space-y-6">
            <h2 className="text-2xl font-bold text-white flex items-center gap-3">
              <Shield className="w-5 h-5 text-[#1DB954]" />
              Authentication
            </h2>

            <div className="space-y-4 text-sm text-[#b3b3b3] leading-relaxed">
              <p>
                Lofty uses <strong className="text-white">Clerk</strong> for authentication.
                All user-facing endpoints require a valid JWT token in the{" "}
                <code className="text-[#1DB954] bg-[#1DB954]/5 px-1.5 py-0.5 rounded text-xs">
                  Authorization
                </code>{" "}
                header.
              </p>

              <CodeBlock
                code={`# User endpoints — Clerk JWT
curl -H "Authorization: Bearer <clerk-jwt-token>" \\
     https://your-api.com/api/v1/jobs

# Worker endpoints — shared API key
curl -H "Authorization: Bearer <worker-api-key>" \\
     https://your-api.com/api/v1/worker/next-job`}
              />

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-4">
                <div className="bg-[#0a0a0a] border border-[#1a1a1a] rounded-lg p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <div className="w-2 h-2 rounded-full bg-[#1DB954]" />
                    <span className="text-xs font-semibold text-white uppercase tracking-wider">
                      User Auth
                    </span>
                  </div>
                  <p className="text-xs text-[#808080]">
                    Clerk JWT obtained via frontend sign-in. Token contains{" "}
                    <code className="text-[#b3b3b3]">sub</code> (clerk_id),{" "}
                    <code className="text-[#b3b3b3]">email</code>, and{" "}
                    <code className="text-[#b3b3b3]">name</code> claims. Verified via JWKS (cached 1h).
                  </p>
                </div>
                <div className="bg-[#0a0a0a] border border-[#1a1a1a] rounded-lg p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <div className="w-2 h-2 rounded-full bg-amber-500" />
                    <span className="text-xs font-semibold text-white uppercase tracking-wider">
                      Worker Auth
                    </span>
                  </div>
                  <p className="text-xs text-[#808080]">
                    Shared API key set via{" "}
                    <code className="text-[#b3b3b3]">WORKER_API_KEY</code> env
                    var. Used by Colab/remote GPU workers for the{" "}
                    <code className="text-[#b3b3b3]">/worker/*</code> endpoints.
                  </p>
                </div>
              </div>
            </div>
          </section>

          {/* ── Endpoint Groups ── */}
          {ENDPOINT_GROUPS.map((group) => (
            <section
              key={group.id}
              id={`section-${group.id}`}
              className="space-y-5"
            >
              <div>
                <h2 className="text-2xl font-bold text-white flex items-center gap-3">
                  <group.icon className="w-5 h-5 text-[#1DB954]" />
                  {group.title}
                </h2>
                <p className="text-sm text-[#808080] mt-1.5 leading-relaxed">
                  {group.description}
                </p>
              </div>

              <div className="space-y-2">
                {group.endpoints.map((ep, i) => (
                  <EndpointCard key={`${ep.method}-${ep.path}-${i}`} ep={ep} />
                ))}
              </div>
            </section>
          ))}

          {/* ── Error Handling ── */}
          <section id="section-errors" className="space-y-6">
            <h2 className="text-2xl font-bold text-white flex items-center gap-3">
              <AlertTriangle className="w-5 h-5 text-[#1DB954]" />
              Error Handling
            </h2>

            <p className="text-sm text-[#b3b3b3]">
              All errors return a JSON body with a{" "}
              <code className="text-[#1DB954] text-xs">detail</code> field.
              HTTP status codes follow REST conventions.
            </p>

            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-[#1a1a1a]">
                    <th className="text-left py-2.5 pr-4 text-[11px] uppercase tracking-wider text-[#555] font-semibold">
                      Status
                    </th>
                    <th className="text-left py-2.5 pr-4 text-[11px] uppercase tracking-wider text-[#555] font-semibold">
                      Meaning
                    </th>
                    <th className="text-left py-2.5 text-[11px] uppercase tracking-wider text-[#555] font-semibold">
                      When
                    </th>
                  </tr>
                </thead>
                <tbody className="text-[#b3b3b3]">
                  {[
                    ["400", "Bad Request", "Validation error (invalid prompt, unsupported format)"],
                    ["401", "Unauthorized", "Missing or invalid JWT / worker API key"],
                    ["403", "Forbidden", "SSE ticket doesn't match job"],
                    ["404", "Not Found", "Resource doesn't exist or belongs to another user"],
                    ["409", "Conflict", "Active job limit, non-cancellable status"],
                    ["413", "Payload Too Large", "Upload exceeds 50 MB limit"],
                    ["422", "Unprocessable", "Pydantic validation failed (field constraints)"],
                    ["429", "Too Many Requests", "Rate limit exceeded (sliding window)"],
                    ["503", "Service Unavailable", "Redis down, GPU service temporary failure"],
                  ].map(([code, meaning, when]) => (
                    <tr key={code} className="border-b border-[#111]">
                      <td className="py-2.5 pr-4">
                        <code className="text-white font-mono text-xs">{code}</code>
                      </td>
                      <td className="py-2.5 pr-4 text-white text-xs">{meaning}</td>
                      <td className="py-2.5 text-xs">{when}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <JsonBlock
              code={`// Example error response
{
  "detail": "Invalid model_name 'gpt-4'. Allowed: ace-step-1.5, yue"
}

// Validation error (422)
{
  "detail": [
    {
      "loc": ["body", "prompt"],
      "msg": "String should have at least 3 characters",
      "type": "string_too_short"
    }
  ]
}`}
            />
          </section>

          {/* ── Rate Limiting ── */}
          <section id="section-rate-limiting" className="space-y-6">
            <h2 className="text-2xl font-bold text-white flex items-center gap-3">
              <Clock className="w-5 h-5 text-[#1DB954]" />
              Rate Limiting
            </h2>

            <div className="text-sm text-[#b3b3b3] space-y-3">
              <p>
                Job creation (<code className="text-[#1DB954] text-xs">POST /jobs</code>) is rate-limited
                via a Redis-backed sliding window.
              </p>

              <div className="bg-[#0a0a0a] border border-[#1a1a1a] rounded-lg p-4 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-[#666]">Window</span>
                  <span className="text-xs text-white font-mono">60 seconds</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-[#666]">Default limit</span>
                  <span className="text-xs text-white font-mono">
                    10 requests / minute
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-[#666]">Burst allowance</span>
                  <span className="text-xs text-white font-mono">3 requests</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-[#666]">Scope</span>
                  <span className="text-xs text-white font-mono">Per user (clerk_id)</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-[#666]">When Redis is down</span>
                  <span className="text-xs text-red-400 font-mono">
                    503 (fail closed)
                  </span>
                </div>
              </div>

              <p className="text-xs text-[#666]">
                Configurable via <code className="text-[#b3b3b3]">RATE_LIMIT_PER_MINUTE</code> and{" "}
                <code className="text-[#b3b3b3]">RATE_LIMIT_BURST</code> environment variables.
              </p>
            </div>
          </section>

          {/* ── Quick Start ── */}
          <section id="section-quickstart" className="space-y-6">
            <h2 className="text-2xl font-bold text-white flex items-center gap-3">
              <Terminal className="w-5 h-5 text-[#1DB954]" />
              Quick Start
            </h2>

            <p className="text-sm text-[#b3b3b3]">
              End-to-end example: create a job, poll for completion, download the track.
            </p>

            <div className="space-y-4">
              <div>
                <div className="flex items-center gap-2 mb-2">
                  <span className="w-6 h-6 rounded-full bg-[#1DB954] text-black text-xs font-bold flex items-center justify-center">
                    1
                  </span>
                  <span className="text-sm font-semibold text-white">
                    Create a generation job
                  </span>
                </div>
                <CodeBlock
                  code={`curl -X POST https://your-api.com/api/v1/jobs \\
  -H "Authorization: Bearer $CLERK_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{
    "prompt": "lo-fi hip hop beat with vinyl crackle and soft piano",
    "duration_seconds": 30,
    "model_name": "ace-step-1.5",
    "compute_mode": "gpu"
  }'

# Response: {"id": "abc-123", "status": "pending", ...}`}
                />
              </div>

              <div>
                <div className="flex items-center gap-2 mb-2">
                  <span className="w-6 h-6 rounded-full bg-[#1DB954] text-black text-xs font-bold flex items-center justify-center">
                    2
                  </span>
                  <span className="text-sm font-semibold text-white">
                    Poll for completion (or use SSE)
                  </span>
                </div>
                <CodeBlock
                  code={`# Option A: Poll
while true; do
  STATUS=$(curl -s -H "Authorization: Bearer $CLERK_TOKEN" \\
    https://your-api.com/api/v1/jobs/abc-123 | jq -r '.status')
  echo "Status: $STATUS"
  [ "$STATUS" = "completed" ] && break
  sleep 5
done

# Option B: SSE (recommended)
# 1. Get ticket
TICKET=$(curl -s -X POST \\
  -H "Authorization: Bearer $CLERK_TOKEN" \\
  https://your-api.com/api/v1/jobs/abc-123/stream/ticket | jq -r '.ticket')

# 2. Stream events
curl -N "https://your-api.com/api/v1/jobs/abc-123/stream?ticket=$TICKET"`}
                />
              </div>

              <div>
                <div className="flex items-center gap-2 mb-2">
                  <span className="w-6 h-6 rounded-full bg-[#1DB954] text-black text-xs font-bold flex items-center justify-center">
                    3
                  </span>
                  <span className="text-sm font-semibold text-white">
                    Download the generated track
                  </span>
                </div>
                <CodeBlock
                  code={`# Get track info
TRACK=$(curl -s -H "Authorization: Bearer $CLERK_TOKEN" \\
  https://your-api.com/api/v1/jobs/abc-123 | jq -r '.track.id')

# Download audio
curl -L -H "Authorization: Bearer $CLERK_TOKEN" \\
  -o output.wav \\
  "https://your-api.com/api/v1/tracks/$TRACK/download"`}
                />
              </div>

              <div>
                <div className="flex items-center gap-2 mb-2">
                  <span className="w-6 h-6 rounded-full bg-[#1DB954] text-black text-xs font-bold flex items-center justify-center">
                    4
                  </span>
                  <span className="text-sm font-semibold text-white">
                    Fine-tune with custom audio (optional)
                  </span>
                </div>
                <CodeBlock
                  code={`# Upload training audio
UPLOAD_ID=$(curl -s -X POST \\
  -H "Authorization: Bearer $CLERK_TOKEN" \\
  -F "file=@my_jazz_track.wav" \\
  https://your-api.com/api/v1/uploads | jq -r '.id')

# Create dataset
DS_ID=$(curl -s -X POST \\
  -H "Authorization: Bearer $CLERK_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{"name": "Jazz Collection"}' \\
  https://your-api.com/api/v1/datasets | jq -r '.id')

# Add track to dataset
curl -X POST -H "Authorization: Bearer $CLERK_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d "{\"upload_id\": \"$UPLOAD_ID\", \"caption\": \"smooth jazz\"}" \\
  "https://your-api.com/api/v1/datasets/$DS_ID/tracks"

# Process dataset
curl -X POST -H "Authorization: Bearer $CLERK_TOKEN" \\
  "https://your-api.com/api/v1/datasets/$DS_ID/process"

# Start fine-tuning
curl -X POST -H "Authorization: Bearer $CLERK_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d "{\"dataset_id\": \"$DS_ID\", \"name\": \"Jazz Style v1\"}" \\
  https://your-api.com/api/v1/finetune`}
                />
              </div>
            </div>
          </section>

          {/* ── OpenAPI ── */}
          <section className="border-t border-[#1a1a1a] pt-12">
            <div className="bg-[#0a0a0a] border border-[#1a1a1a] rounded-xl p-6 flex items-start gap-4">
              <div className="w-10 h-10 rounded-lg bg-[#1DB954]/10 flex items-center justify-center shrink-0">
                <ExternalLink className="w-5 h-5 text-[#1DB954]" />
              </div>
              <div>
                <h3 className="text-sm font-semibold text-white mb-1">
                  Interactive API Explorer
                </h3>
                <p className="text-xs text-[#808080] leading-relaxed">
                  FastAPI auto-generates an interactive Swagger UI at{" "}
                  <code className="text-[#1DB954]">/docs</code> and ReDoc at{" "}
                  <code className="text-[#1DB954]">/redoc</code>. These include
                  all schemas, try-it-out functionality, and the full OpenAPI 3.1
                  spec at{" "}
                  <code className="text-[#1DB954]">/openapi.json</code>.
                </p>
              </div>
            </div>
          </section>

          {/* Footer spacer */}
          <div className="h-20" />
        </main>
      </div>
    </div>
  );
}

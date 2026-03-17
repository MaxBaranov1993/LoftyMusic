const API_BASE = "/api/v1";

export interface Job {
  id: string;
  status: string;
  prompt: string;
  lyrics: string;
  duration_seconds: number;
  model_name: string;
  generation_params: Record<string, unknown>;
  compute_mode: ComputeMode;
  error_message: string | null;
  progress: number;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  track: Track | null;
}

export interface Track {
  id: string;
  job_id: string;
  title: string;
  duration_seconds: number;
  sample_rate: number;
  format: string;
  file_size_bytes: number;
  created_at: string;
  download_url: string | null;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

export type QualityPreset = "draft" | "balanced" | "high";
export type TaskType = "text2music" | "cover" | "repaint" | "lego" | "extract" | "complete";
export type ModelName = "ace-step-1.5" | "yue";
export type ComputeMode = "cpu" | "gpu";

export interface JobCreateRequest {
  prompt: string;
  lyrics?: string;
  duration_seconds: number;
  model_name: ModelName;
  lora_adapter_id?: string | null;
  compute_mode?: ComputeMode;
  generation_params: {
    // Common
    language?: string;
    seed?: number;
    // ACE-Step specific
    guidance_scale?: number;
    quality_preset?: QualityPreset;
    inference_steps?: number;
    bpm?: number | null;
    key?: string | null;
    time_signature?: string;
    task_type?: TaskType;
    // YuE specific
    temperature?: number;
    top_p?: number;
    repetition_penalty?: number;
    num_segments?: number;
  };
}

// --- Fine-Tuning types ---

export interface AudioUpload {
  id: string;
  storage_key: string;
  original_filename: string;
  file_size_bytes: number;
  duration_seconds: number;
  format: string;
  analysis: Record<string, unknown> | null;
  created_at: string;
}

export interface Dataset {
  id: string;
  name: string;
  description: string;
  status: string;
  num_tracks: number;
  total_duration_seconds: number;
  created_at: string;
  tracks: DatasetTrack[];
}

export interface DatasetTrack {
  id: string;
  dataset_id: string;
  upload_id: string;
  lyrics: string;
  caption: string;
  bpm: number | null;
  key_scale: string | null;
  duration_seconds: number;
  status: string;
  created_at: string;
}

export interface FineTuneJob {
  id: string;
  dataset_id: string;
  name: string;
  status: string;
  config: Record<string, unknown>;
  compute_mode: ComputeMode;
  progress: number;
  error_message: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  adapter: LoRAAdapter | null;
}

export interface LoRAAdapter {
  id: string;
  name: string;
  description: string;
  base_model: string;
  training_method: string;
  adapter_size_bytes: number;
  is_active: boolean;
  created_at: string;
}

// Token getter function — set by the auth hook
let _getToken: (() => Promise<string | null>) | null = null;

export function setTokenGetter(getter: () => Promise<string | null>) {
  _getToken = getter;
}

async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };

  if (_getToken) {
    const token = await _getToken();
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }
  }

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    const message =
      typeof error.detail === "string"
        ? error.detail
        : Array.isArray(error.detail)
          ? error.detail.map((e: { msg: string }) => e.msg).join(", ")
          : `API error: ${res.status}`;
    throw new Error(message);
  }

  if (res.status === 204) return undefined as T;
  return res.json();
}

export interface GpuSettings {
  backend: string;
  autoscaler_enabled: boolean;
  autoscaler_min_instances: number;
  autoscaler_max_instances: number;
  autoscaler_idle_timeout: number;
  cloud_api_key_configured: boolean;
}

export interface GpuSettingsUpdate {
  backend: string;
  cloud_api_key?: string | null;
  autoscaler_enabled?: boolean;
  autoscaler_max_instances?: number;
  autoscaler_idle_timeout?: number;
}

export interface GpuInstance {
  id: string;
  backend: string;
  status: string;
  gpu_type: string;
  gpu_memory_mb: number;
  cost_per_hour: number;
  created_at: number;
}

export interface GpuStatus {
  backend: string;
  status: string;
  instances: GpuInstance[];
  total_cost_per_hour: number;
  colab_setup_snippet: string | null;
}

export const api = {
  createJob(data: JobCreateRequest): Promise<Job> {
    return apiFetch<Job>("/jobs", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  getJob(jobId: string): Promise<Job> {
    return apiFetch<Job>(`/jobs/${jobId}`);
  },

  listJobs(page = 1, status?: string): Promise<PaginatedResponse<Job>> {
    const params = new URLSearchParams({ page: String(page) });
    if (status) params.set("status", status);
    return apiFetch<PaginatedResponse<Job>>(`/jobs?${params}`);
  },

  listTracks(page = 1): Promise<PaginatedResponse<Track>> {
    return apiFetch<PaginatedResponse<Track>>(`/tracks?page=${page}`);
  },

  getTrack(trackId: string): Promise<Track> {
    return apiFetch<Track>(`/tracks/${trackId}`);
  },

  cancelJob(jobId: string): Promise<void> {
    return apiFetch<void>(`/jobs/${jobId}/cancel`, { method: "POST" });
  },

  deleteJob(jobId: string): Promise<void> {
    return apiFetch<void>(`/jobs/${jobId}`, { method: "DELETE" });
  },

  // GPU Settings
  getGpuSettings(): Promise<GpuSettings> {
    return apiFetch<GpuSettings>("/gpu/settings");
  },

  updateGpuSettings(data: GpuSettingsUpdate): Promise<GpuSettings> {
    return apiFetch<GpuSettings>("/gpu/settings", {
      method: "PUT",
      body: JSON.stringify(data),
    });
  },

  getGpuStatus(): Promise<GpuStatus> {
    return apiFetch<GpuStatus>("/gpu/status");
  },

  spinUpInstance(gpuType: string = "auto"): Promise<GpuInstance> {
    return apiFetch<GpuInstance>(`/gpu/instances/spin-up?gpu_type=${gpuType}`, {
      method: "POST",
    });
  },

  tearDownInstance(instanceId: string): Promise<void> {
    return apiFetch<void>(`/gpu/instances/${instanceId}/tear-down`, {
      method: "POST",
    });
  },

  // --- Uploads ---
  async uploadAudio(file: File): Promise<AudioUpload> {
    const formData = new FormData();
    formData.append("file", file);

    const headers: Record<string, string> = {};
    if (_getToken) {
      const token = await _getToken();
      if (token) headers["Authorization"] = `Bearer ${token}`;
    }

    const res = await fetch(`${API_BASE}/uploads`, {
      method: "POST",
      headers,
      body: formData,
    });

    if (!res.ok) {
      const error = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(typeof error.detail === "string" ? error.detail : `Upload failed: ${res.status}`);
    }
    return res.json();
  },

  listUploads(page = 1): Promise<PaginatedResponse<AudioUpload>> {
    return apiFetch<PaginatedResponse<AudioUpload>>(`/uploads?page=${page}`);
  },

  deleteUpload(uploadId: string): Promise<void> {
    return apiFetch<void>(`/uploads/${uploadId}`, { method: "DELETE" });
  },

  // --- Datasets ---
  createDataset(data: { name: string; description?: string }): Promise<Dataset> {
    return apiFetch<Dataset>("/datasets", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  listDatasets(page = 1): Promise<PaginatedResponse<Dataset>> {
    return apiFetch<PaginatedResponse<Dataset>>(`/datasets?page=${page}`);
  },

  getDataset(datasetId: string): Promise<Dataset> {
    return apiFetch<Dataset>(`/datasets/${datasetId}`);
  },

  addTrackToDataset(
    datasetId: string,
    data: { upload_id: string; lyrics?: string; caption?: string; bpm?: number | null; key_scale?: string | null },
  ): Promise<DatasetTrack> {
    return apiFetch<DatasetTrack>(`/datasets/${datasetId}/tracks`, {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  removeTrackFromDataset(datasetId: string, trackId: string): Promise<void> {
    return apiFetch<void>(`/datasets/${datasetId}/tracks/${trackId}`, { method: "DELETE" });
  },

  processDataset(datasetId: string): Promise<{ status: string; dataset_id: string }> {
    return apiFetch(`/datasets/${datasetId}/process`, { method: "POST" });
  },

  deleteDataset(datasetId: string): Promise<void> {
    return apiFetch<void>(`/datasets/${datasetId}`, { method: "DELETE" });
  },

  // --- Fine-Tuning ---
  createFineTuneJob(data: {
    dataset_id: string;
    name: string;
    config?: { max_epochs?: number; batch_size?: number; training_method?: string; learning_rate?: number };
    compute_mode?: ComputeMode;
  }): Promise<FineTuneJob> {
    return apiFetch<FineTuneJob>("/finetune", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  listFineTuneJobs(page = 1): Promise<PaginatedResponse<FineTuneJob>> {
    return apiFetch<PaginatedResponse<FineTuneJob>>(`/finetune?page=${page}`);
  },

  getFineTuneJob(jobId: string): Promise<FineTuneJob> {
    return apiFetch<FineTuneJob>(`/finetune/${jobId}`);
  },

  cancelFineTuneJob(jobId: string): Promise<void> {
    return apiFetch<void>(`/finetune/${jobId}/cancel`, { method: "POST" });
  },

  deleteFineTuneJob(jobId: string): Promise<void> {
    return apiFetch<void>(`/finetune/${jobId}`, { method: "DELETE" });
  },

  // --- LoRA Adapters ---
  listAdapters(page = 1): Promise<PaginatedResponse<LoRAAdapter>> {
    return apiFetch<PaginatedResponse<LoRAAdapter>>(`/adapters?page=${page}`);
  },

  deleteAdapter(adapterId: string): Promise<void> {
    return apiFetch<void>(`/adapters/${adapterId}`, { method: "DELETE" });
  },

  async streamJobProgress(
    jobId: string,
    onEvent: (event: { type: string; data: Record<string, unknown> }) => void,
  ): Promise<() => void> {
    const { ticket } = await apiFetch<{ ticket: string }>(
      `/jobs/${jobId}/stream/ticket`,
      { method: "POST" },
    );

    const url = `${API_BASE}/jobs/${jobId}/stream?ticket=${encodeURIComponent(ticket)}`;
    const eventSource = new EventSource(url);

    const handleEvent = (type: string) => (e: MessageEvent) => {
      try {
        const data = JSON.parse(e.data);
        onEvent({ type, data });
      } catch {
        // ignore parse errors
      }
    };

    eventSource.addEventListener("progress", handleEvent("progress"));
    eventSource.addEventListener("complete", handleEvent("complete"));
    eventSource.addEventListener("error", handleEvent("error"));
    eventSource.addEventListener("cancelled", handleEvent("cancelled"));

    eventSource.onerror = () => {
      eventSource.close();
    };

    return () => eventSource.close();
  },
};

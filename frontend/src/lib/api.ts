const API_BASE = "/api/v1";

export interface Job {
  id: string;
  status: string;
  prompt: string;
  duration_seconds: number;
  model_name: string;
  generation_params: Record<string, number>;
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

export interface JobCreateRequest {
  prompt: string;
  duration_seconds: number;
  model_name: string;
  generation_params: {
    temperature: number;
    top_k: number;
    top_p: number;
    guidance_scale: number;
  };
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
};

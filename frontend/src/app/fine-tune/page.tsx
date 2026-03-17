"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import {
  api,
  AudioUpload,
  ComputeMode,
  Dataset,
  DatasetTrack,
  FineTuneJob,
  LoRAAdapter,
} from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Separator } from "@/components/ui/separator";
import { Textarea } from "@/components/ui/textarea";
import {
  Upload,
  Plus,
  Trash2,
  Play,
  Loader2,
  AlertCircle,
  CheckCircle,
  Music,
  Wand2,
  FolderOpen,
  X,
  Cpu,
  Zap,
} from "lucide-react";
import { cn } from "@/lib/utils";

// ─── Upload Section ──────────────────────────────────────────────────────────

function UploadSection({
  uploads,
  onUploaded,
  onDelete,
}: {
  uploads: AudioUpload[];
  onUploaded: (u: AudioUpload) => void;
  onDelete: (id: string) => void;
}) {
  const fileRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleUpload = async (files: FileList | null) => {
    if (!files) return;
    setUploading(true);
    setError(null);

    for (const file of Array.from(files)) {
      try {
        const upload = await api.uploadAudio(file);
        onUploaded(upload);
      } catch (err: any) {
        setError(err.message || "Upload failed");
      }
    }
    setUploading(false);
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-base font-semibold text-foreground">
          Audio Files
        </h3>
        <Button
          size="sm"
          variant="outline"
          className="rounded-full"
          onClick={() => fileRef.current?.click()}
          disabled={uploading}
        >
          {uploading ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Upload className="w-4 h-4" />
          )}
          Upload
        </Button>
        <input
          ref={fileRef}
          type="file"
          accept="audio/*"
          multiple
          className="hidden"
          onChange={(e) => handleUpload(e.target.files)}
        />
      </div>

      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {uploads.length === 0 ? (
        <div className="text-center py-8 text-muted-foreground text-sm">
          No audio files uploaded yet. Upload WAV, MP3, FLAC, or OGG files.
        </div>
      ) : (
        <div className="space-y-2">
          {uploads.map((u) => (
            <div
              key={u.id}
              className="flex items-center justify-between px-3 py-2 rounded-lg bg-[#282828] group"
            >
              <div className="flex items-center gap-3 min-w-0">
                <Music className="w-4 h-4 text-[#1DB954] shrink-0" />
                <div className="min-w-0">
                  <div className="text-sm text-foreground truncate">
                    {u.original_filename}
                  </div>
                  <div className="text-[11px] text-muted-foreground">
                    {u.duration_seconds.toFixed(1)}s &middot;{" "}
                    {(u.file_size_bytes / 1024 / 1024).toFixed(1)} MB &middot;{" "}
                    {u.format.toUpperCase()}
                  </div>
                </div>
              </div>
              <button
                onClick={() => onDelete(u.id)}
                className="text-muted-foreground hover:text-red-400 transition-colors opacity-0 group-hover:opacity-100 cursor-pointer"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ─── Dataset Manager ─────────────────────────────────────────────────────────

function DatasetManager({
  datasets,
  uploads,
  onCreated,
  onRefresh,
}: {
  datasets: Dataset[];
  uploads: AudioUpload[];
  onCreated: (d: Dataset) => void;
  onRefresh: () => void;
}) {
  const [creating, setCreating] = useState(false);
  const [name, setName] = useState("");
  const [selectedDataset, setSelectedDataset] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleCreate = async () => {
    if (!name.trim()) return;
    setCreating(true);
    setError(null);
    try {
      const dataset = await api.createDataset({ name: name.trim() });
      onCreated(dataset);
      setName("");
      setSelectedDataset(dataset.id);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setCreating(false);
    }
  };

  const handleAddTrack = async (datasetId: string, uploadId: string) => {
    try {
      await api.addTrackToDataset(datasetId, { upload_id: uploadId });
      onRefresh();
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleProcess = async (datasetId: string) => {
    try {
      await api.processDataset(datasetId);
      onRefresh();
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleDelete = async (datasetId: string) => {
    try {
      await api.deleteDataset(datasetId);
      onRefresh();
    } catch (err: any) {
      setError(err.message);
    }
  };

  const current = datasets.find((d) => d.id === selectedDataset);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-base font-semibold text-foreground">Datasets</h3>
      </div>

      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Create new dataset */}
      <div className="flex gap-2">
        <input
          type="text"
          placeholder="New dataset name..."
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="flex-1 h-9 px-3 rounded-lg bg-[#282828] border border-[#383838] text-sm text-foreground focus:border-[#1DB954] focus:outline-none"
        />
        <Button
          size="sm"
          onClick={handleCreate}
          disabled={!name.trim() || creating}
          className="rounded-full"
        >
          <Plus className="w-4 h-4" />
          Create
        </Button>
      </div>

      {/* Dataset list */}
      {datasets.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {datasets.map((d) => (
            <button
              key={d.id}
              onClick={() => setSelectedDataset(d.id)}
              className={cn(
                "inline-flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-full border transition-all cursor-pointer",
                selectedDataset === d.id
                  ? "bg-[#1DB954]/10 border-[#1DB954] text-[#1DB954]"
                  : "border-[#383838] text-[#B3B3B3] hover:border-[#727272]"
              )}
            >
              <FolderOpen className="w-3 h-3" />
              {d.name}
              <Badge
                variant="secondary"
                className="text-[10px] ml-1"
              >
                {d.status}
              </Badge>
            </button>
          ))}
        </div>
      )}

      {/* Selected dataset detail */}
      {current && (
        <Card className="bg-[#1a1a1a]">
          <CardContent className="py-4 space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h4 className="text-sm font-semibold text-foreground">
                  {current.name}
                </h4>
                <p className="text-[11px] text-muted-foreground">
                  {current.num_tracks} track{current.num_tracks !== 1 ? "s" : ""}{" "}
                  &middot; {current.total_duration_seconds.toFixed(0)}s total
                </p>
              </div>
              <div className="flex gap-2">
                {current.status === "pending" || current.status === "failed" ? (
                  <Button
                    size="sm"
                    variant="outline"
                    className="rounded-full text-xs"
                    onClick={() => handleProcess(current.id)}
                    disabled={current.num_tracks < 1}
                  >
                    <Play className="w-3 h-3" />
                    Process
                  </Button>
                ) : null}
                <Button
                  size="sm"
                  variant="ghost"
                  className="rounded-full text-xs text-red-400 hover:text-red-300"
                  onClick={() => handleDelete(current.id)}
                >
                  <Trash2 className="w-3 h-3" />
                </Button>
              </div>
            </div>

            {/* Add tracks from uploads */}
            {(current.status === "pending" || current.status === "failed") && uploads.length > 0 && (
              <div className="space-y-2">
                <p className="text-[11px] text-muted-foreground">
                  Add tracks from your uploads:
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {uploads
                    .filter(
                      (u) =>
                        !current.tracks.some((t) => t.upload_id === u.id)
                    )
                    .map((u) => (
                      <button
                        key={u.id}
                        onClick={() => handleAddTrack(current.id, u.id)}
                        className="inline-flex items-center gap-1 px-2.5 py-1 text-[11px] rounded-full border border-[#383838] text-[#B3B3B3] hover:border-[#1DB954] hover:text-[#1DB954] transition-all cursor-pointer"
                      >
                        <Plus className="w-3 h-3" />
                        {u.original_filename}
                      </button>
                    ))}
                </div>
              </div>
            )}

            {/* Tracks in dataset */}
            {current.tracks.length > 0 && (
              <div className="space-y-1.5">
                {current.tracks.map((t) => (
                  <div
                    key={t.id}
                    className="flex items-center justify-between px-2 py-1.5 rounded bg-[#282828] text-xs"
                  >
                    <div className="flex items-center gap-2">
                      <Music className="w-3 h-3 text-[#1DB954]" />
                      <span className="text-foreground">
                        {t.duration_seconds.toFixed(1)}s
                      </span>
                      <Badge variant="secondary" className="text-[9px]">
                        {t.status}
                      </Badge>
                    </div>
                    <button
                      onClick={async () => {
                        await api.removeTrackFromDataset(current.id, t.id);
                        onRefresh();
                      }}
                      className="text-muted-foreground hover:text-red-400 cursor-pointer"
                    >
                      <X className="w-3 h-3" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}

// ─── Fine-Tune Form ──────────────────────────────────────────────────────────

function FineTuneForm({
  datasets,
  onCreated,
}: {
  datasets: Dataset[];
  onCreated: (job: FineTuneJob) => void;
}) {
  const readyDatasets = datasets.filter((d) => d.status === "ready");
  const [datasetId, setDatasetId] = useState("");
  const [name, setName] = useState("");
  const [method, setMethod] = useState("lokr");
  const [epochs, setEpochs] = useState(500);
  const [computeMode, setComputeMode] = useState<ComputeMode>("cpu");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!datasetId || !name.trim()) return;

    setLoading(true);
    setError(null);
    try {
      const job = await api.createFineTuneJob({
        dataset_id: datasetId,
        name: name.trim(),
        config: {
          training_method: method,
          max_epochs: epochs,
        },
        compute_mode: computeMode,
      });
      onCreated(job);
      setName("");
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  if (readyDatasets.length === 0) {
    return (
      <div className="text-center py-6 text-muted-foreground text-sm">
        No processed datasets available. Create and process a dataset first.
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div className="space-y-2">
          <label className="text-sm font-medium text-muted-foreground">
            Dataset
          </label>
          <select
            value={datasetId}
            onChange={(e) => setDatasetId(e.target.value)}
            className="w-full h-9 px-3 rounded-lg bg-[#282828] border border-[#383838] text-sm text-[#B3B3B3] focus:border-[#1DB954] focus:outline-none"
          >
            <option value="">Select dataset...</option>
            {readyDatasets.map((d) => (
              <option key={d.id} value={d.id}>
                {d.name} ({d.num_tracks} tracks)
              </option>
            ))}
          </select>
        </div>

        <div className="space-y-2">
          <label className="text-sm font-medium text-muted-foreground">
            Adapter Name
          </label>
          <input
            type="text"
            placeholder="My Custom Style"
            value={name}
            onChange={(e) => setName(e.target.value)}
            maxLength={200}
            className="w-full h-9 px-3 rounded-lg bg-[#282828] border border-[#383838] text-sm text-foreground focus:border-[#1DB954] focus:outline-none"
          />
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="space-y-2">
          <label className="text-sm font-medium text-muted-foreground">
            Training Method
          </label>
          <div className="flex gap-2">
            {[
              { value: "lokr", label: "LoKR", desc: "10x faster" },
              { value: "lora", label: "LoRA", desc: "Classic" },
            ].map((m) => (
              <button
                key={m.value}
                type="button"
                onClick={() => setMethod(m.value)}
                className={cn(
                  "flex-1 flex flex-col items-center gap-0.5 px-3 py-2 text-xs rounded-lg border transition-all cursor-pointer",
                  method === m.value
                    ? "bg-[#1DB954]/10 border-[#1DB954] text-[#1DB954]"
                    : "border-[#383838] text-[#B3B3B3] hover:border-[#727272]"
                )}
              >
                <span className="font-medium">{m.label}</span>
                <span className="text-[10px] opacity-70">{m.desc}</span>
              </button>
            ))}
          </div>
        </div>

        <div className="space-y-2">
          <label className="text-sm font-medium text-muted-foreground">
            Compute
          </label>
          <div className="flex gap-2">
            {([
              { value: "cpu" as ComputeMode, label: "CPU", desc: "Free, slow", icon: Cpu },
              { value: "gpu" as ComputeMode, label: "GPU", desc: "Fast", icon: Zap },
            ]).map((option) => {
              const Icon = option.icon;
              return (
                <button
                  key={option.value}
                  type="button"
                  onClick={() => setComputeMode(option.value)}
                  className={cn(
                    "flex-1 flex flex-col items-center gap-0.5 px-3 py-2 text-xs rounded-lg border transition-all cursor-pointer",
                    computeMode === option.value
                      ? "bg-[#1DB954]/10 border-[#1DB954] text-[#1DB954]"
                      : "border-[#383838] text-[#B3B3B3] hover:border-[#727272]"
                  )}
                >
                  <Icon className="w-4 h-4" />
                  <span className="font-medium">{option.label}</span>
                  <span className="text-[10px] opacity-70">{option.desc}</span>
                </button>
              );
            })}
          </div>
        </div>

        <div className="space-y-2">
          <label className="text-sm font-medium text-muted-foreground">
            Max Epochs
          </label>
          <input
            type="number"
            value={epochs}
            onChange={(e) => setEpochs(Number(e.target.value))}
            min={1}
            max={5000}
            className="w-full h-9 px-3 rounded-lg bg-[#282828] border border-[#383838] text-sm text-foreground focus:border-[#1DB954] focus:outline-none"
          />
        </div>
      </div>

      {computeMode === "cpu" && (
        <Alert className="border-amber-500/30 bg-amber-500/5">
          <AlertCircle className="h-4 w-4 text-amber-500" />
          <AlertDescription className="text-xs text-amber-200">
            Training on CPU is extremely slow. Consider using GPU for fine-tuning.
          </AlertDescription>
        </Alert>
      )}

      <Button
        type="submit"
        size="lg"
        disabled={loading || !datasetId || !name.trim()}
        className="w-full rounded-full h-11 font-bold"
      >
        {loading ? (
          <>
            <Loader2 className="w-4 h-4 animate-spin" />
            Starting...
          </>
        ) : (
          <>
            <Wand2 className="w-4 h-4" />
            Start Fine-Tuning
          </>
        )}
      </Button>
    </form>
  );
}

// ─── Job Progress Card ───────────────────────────────────────────────────────

function FineTuneJobCard({
  job,
  onCancel,
  onDelete,
  onRefresh,
}: {
  job: FineTuneJob;
  onCancel: (id: string) => void;
  onDelete: (id: string) => void;
  onRefresh: () => void;
}) {
  const isActive = ["pending", "queued", "running"].includes(job.status);
  const isDone = ["completed", "failed", "cancelled"].includes(job.status);

  // Poll for progress
  useEffect(() => {
    if (!isActive) return;
    const interval = setInterval(onRefresh, 3000);
    return () => clearInterval(interval);
  }, [isActive, onRefresh]);

  const statusColor = {
    pending: "text-yellow-400",
    queued: "text-yellow-400",
    running: "text-blue-400",
    completed: "text-[#1DB954]",
    failed: "text-red-400",
    cancelled: "text-muted-foreground",
  }[job.status] || "text-muted-foreground";

  return (
    <Card className="bg-[#1a1a1a]">
      <CardContent className="py-4 space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Wand2 className="w-4 h-4 text-[#1DB954]" />
            <span className="text-sm font-semibold text-foreground">
              {job.name}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant="secondary" className={cn("text-xs", statusColor)}>
              {job.status}
            </Badge>
            {isActive && (
              <Button
                size="sm"
                variant="ghost"
                className="h-7 text-xs text-red-400 hover:text-red-300"
                onClick={() => onCancel(job.id)}
              >
                Cancel
              </Button>
            )}
            {isDone && (
              <Button
                size="sm"
                variant="ghost"
                className="h-7 text-xs text-red-400 hover:text-red-300"
                onClick={() => onDelete(job.id)}
              >
                <Trash2 className="w-3 h-3" />
              </Button>
            )}
          </div>
        </div>

        {isActive && (
          <Progress value={job.progress} className="h-2" />
        )}

        {job.status === "completed" && job.adapter && (
          <div className="flex items-center gap-2 text-xs text-[#1DB954]">
            <CheckCircle className="w-3.5 h-3.5" />
            Adapter ready: {job.adapter.name} ({job.adapter.training_method.toUpperCase()})
          </div>
        )}

        {job.error_message && (
          <div className="text-xs text-red-400">{job.error_message}</div>
        )}
      </CardContent>
    </Card>
  );
}

// ─── Main Page ───────────────────────────────────────────────────────────────

export default function FineTunePage() {
  const { isSignedIn } = useAuth();
  const [uploads, setUploads] = useState<AudioUpload[]>([]);
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [jobs, setJobs] = useState<FineTuneJob[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchAll = useCallback(async () => {
    try {
      const [u, d, j] = await Promise.all([
        api.listUploads(),
        api.listDatasets(),
        api.listFineTuneJobs(),
      ]);
      setUploads(u.items);
      setDatasets(d.items);
      setJobs(j.items);
    } catch {
      // silently fail
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (isSignedIn) fetchAll();
  }, [isSignedIn, fetchAll]);

  if (!isSignedIn) {
    return (
      <div className="text-center py-16 text-muted-foreground">
        Please sign in to access fine-tuning.
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-16">
        <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="text-center space-y-2 py-4">
        <h1 className="text-3xl font-bold tracking-tight text-foreground">
          Fine-Tune Your{" "}
          <span className="bg-linear-to-r from-[#1DB954] to-[#1ed760] bg-clip-text text-transparent">
            Style
          </span>
        </h1>
        <p className="text-muted-foreground text-sm max-w-lg mx-auto">
          Upload your tracks, create a dataset, and train a custom LoRA adapter
          to generate music in your unique style.
        </p>
      </div>

      {/* Step 1: Upload */}
      <Card className="bg-[#181818]">
        <CardContent className="py-5">
          <div className="flex items-center gap-2 mb-4">
            <Badge className="bg-[#1DB954] text-black text-xs font-bold">
              1
            </Badge>
            <span className="text-sm font-semibold text-foreground">
              Upload Audio
            </span>
          </div>
          <UploadSection
            uploads={uploads}
            onUploaded={(u) => setUploads((prev) => [u, ...prev])}
            onDelete={async (id) => {
              await api.deleteUpload(id);
              setUploads((prev) => prev.filter((u) => u.id !== id));
            }}
          />
        </CardContent>
      </Card>

      {/* Step 2: Dataset */}
      <Card className="bg-[#181818]">
        <CardContent className="py-5">
          <div className="flex items-center gap-2 mb-4">
            <Badge className="bg-[#1DB954] text-black text-xs font-bold">
              2
            </Badge>
            <span className="text-sm font-semibold text-foreground">
              Create & Process Dataset
            </span>
          </div>
          <DatasetManager
            datasets={datasets}
            uploads={uploads}
            onCreated={(d) => setDatasets((prev) => [d, ...prev])}
            onRefresh={fetchAll}
          />
        </CardContent>
      </Card>

      {/* Step 3: Train */}
      <Card className="bg-[#181818]">
        <CardContent className="py-5">
          <div className="flex items-center gap-2 mb-4">
            <Badge className="bg-[#1DB954] text-black text-xs font-bold">
              3
            </Badge>
            <span className="text-sm font-semibold text-foreground">
              Train Custom Style
            </span>
          </div>
          <FineTuneForm
            datasets={datasets}
            onCreated={(j) => setJobs((prev) => [j, ...prev])}
          />
        </CardContent>
      </Card>

      {/* Jobs */}
      {jobs.length > 0 && (
        <div className="space-y-4">
          <div className="flex items-center gap-3">
            <h2 className="text-lg font-semibold text-foreground">
              Training Jobs
            </h2>
            <Separator className="flex-1" />
          </div>
          <div className="space-y-3">
            {jobs.map((job) => (
              <FineTuneJobCard
                key={job.id}
                job={job}
                onCancel={async (id) => {
                  await api.cancelFineTuneJob(id);
                  fetchAll();
                }}
                onDelete={async (id) => {
                  await api.deleteFineTuneJob(id);
                  fetchAll();
                }}
                onRefresh={fetchAll}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

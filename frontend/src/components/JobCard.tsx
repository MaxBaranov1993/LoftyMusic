"use client";

import { useState, useEffect } from "react";
import { Job, api } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  Clock,
  CheckCircle2,
  XCircle,
  Loader2,
  Music,
  Download,
  AlertCircle,
  ListOrdered,
  Ban,
  Square,
  Trash2,
  Cpu,
  Zap,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Equalizer } from "@/components/Equalizer";

const STATUS_CONFIG: Record<
  string,
  { icon: React.ElementType; className: string; label: string }
> = {
  pending: {
    icon: Clock,
    className: "bg-amber-500/15 text-amber-400 border-amber-500/25",
    label: "Pending",
  },
  queued: {
    icon: ListOrdered,
    className: "bg-[#B3B3B3]/15 text-[#B3B3B3] border-[#B3B3B3]/25",
    label: "Queued",
  },
  running: {
    icon: Loader2,
    className: "bg-[#1DB954]/15 text-[#1DB954] border-[#1DB954]/25",
    label: "Running",
  },
  completed: {
    icon: CheckCircle2,
    className: "bg-[#1DB954]/15 text-[#1DB954] border-[#1DB954]/25",
    label: "Completed",
  },
  failed: {
    icon: XCircle,
    className: "bg-red-500/15 text-red-400 border-red-500/25",
    label: "Failed",
  },
  cancelled: {
    icon: Ban,
    className: "bg-zinc-500/15 text-zinc-400 border-zinc-500/25",
    label: "Cancelled",
  },
};

interface Props {
  job: Job;
  onCancelled?: (jobId: string) => void;
  onDeleted?: (jobId: string) => void;
}

export default function JobCard({ job, onCancelled, onDeleted }: Props) {
  const [cancelling, setCancelling] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const config = STATUS_CONFIG[job.status] || STATUS_CONFIG.pending;
  const StatusIcon = config.icon;
  const createdAt = new Date(job.created_at).toLocaleString();

  const isActive = ["pending", "queued", "running"].includes(job.status);

  const handleCancel = async () => {
    setCancelling(true);
    try {
      await api.cancelJob(job.id);
      onCancelled?.(job.id);
    } catch {
      // ignore
    } finally {
      setCancelling(false);
    }
  };

  const handleDelete = async () => {
    setDeleting(true);
    try {
      await api.deleteJob(job.id);
      onDeleted?.(job.id);
    } catch {
      // ignore
    } finally {
      setDeleting(false);
    }
  };

  return (
    <Card
      className={cn(
        "animate-slide-up overflow-hidden transition-all duration-200 hover:bg-[#282828] hover:scale-[1.01]"
      )}
    >
      <CardContent className="py-4">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 min-w-0">
            <p className="font-medium text-foreground truncate">{job.prompt}</p>
            <div className="flex items-center gap-2 mt-1.5 text-xs text-muted-foreground">
              <Badge variant="outline" className={cn(
                "text-[10px] px-1.5 py-0",
                job.model_name === "yue"
                  ? "border-purple-500/40 text-purple-400"
                  : "border-[#1DB954]/40 text-[#1DB954]"
              )}>
                {job.model_name === "yue" ? "YuE" : "ACE-Step"}
              </Badge>
              <Badge variant="outline" className={cn(
                "text-[10px] px-1.5 py-0 gap-0.5",
                job.compute_mode === "cpu"
                  ? "border-blue-500/40 text-blue-400"
                  : "border-amber-500/40 text-amber-400"
              )}>
                {job.compute_mode === "cpu" ? <Cpu className="w-2.5 h-2.5" /> : <Zap className="w-2.5 h-2.5" />}
                {job.compute_mode === "cpu" ? "CPU" : "GPU"}
              </Badge>
              <span>{job.duration_seconds}s</span>
              <span className="text-zinc-600">|</span>
              <span>{createdAt}</span>
            </div>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            <Badge
              variant="outline"
              className={cn(
                "gap-1 border font-medium",
                config.className
              )}
            >
              <StatusIcon
                className={cn(
                  "w-3 h-3",
                  job.status === "running" && "animate-spin"
                )}
              />
              {config.label}
            </Badge>

            {isActive && (
              <Button
                variant="ghost"
                size="icon"
                className="h-7 w-7 text-zinc-500 hover:text-red-400 hover:bg-red-500/10"
                onClick={handleCancel}
                disabled={cancelling}
                title="Stop"
              >
                {cancelling ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <Square className="w-3.5 h-3.5" />
                )}
              </Button>
            )}

            {!isActive && (
              <Button
                variant="ghost"
                size="icon"
                className="h-7 w-7 text-zinc-500 hover:text-red-400 hover:bg-red-500/10"
                onClick={handleDelete}
                disabled={deleting}
                title="Delete"
              >
                {deleting ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <Trash2 className="w-3.5 h-3.5" />
                )}
              </Button>
            )}
          </div>
        </div>

        {/* Running state */}
        {job.status === "running" && (
          <div className="mt-4 space-y-2">
            <div className="flex items-center gap-3">
              <Progress value={job.progress || 0} className="flex-1 h-1.5" />
              <span className="text-xs font-mono text-primary shrink-0 w-9 text-right">
                {job.progress || 0}%
              </span>
              <Equalizer />
            </div>
            <p className="text-xs text-muted-foreground">Generating your music...</p>
          </div>
        )}

        {/* Failed state */}
        {job.status === "failed" && job.error_message && (
          <Alert variant="destructive" className="mt-3">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription className="text-xs">
              {job.error_message}
            </AlertDescription>
          </Alert>
        )}

        {/* Completed state */}
        {job.status === "completed" && job.track && (
          <div className="mt-4">
            <AudioPlayer trackId={job.track.id} title={job.track.title} />
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function AudioPlayer({
  trackId,
  title,
}: {
  trackId: string;
  title: string;
}) {
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function fetchAudioUrl() {
      setLoading(true);
      try {
        const track = await api.getTrack(trackId);
        if (!cancelled && track.download_url) {
          setAudioUrl(track.download_url);
        }
      } catch {
        // ignore
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    fetchAudioUrl();
    return () => { cancelled = true; };
  }, [trackId]);

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-3 p-3 bg-[#282828] rounded-lg">
        <div className="w-10 h-10 rounded-lg bg-[#1DB954]/15 flex items-center justify-center shrink-0">
          <Music className="w-5 h-5 text-[#1DB954]" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium truncate text-foreground">{title}</p>
          <p className="text-xs text-muted-foreground">
            {loading ? "Loading..." : "Ready to play"}
          </p>
        </div>
        {audioUrl && (
          <Button
            variant="outline"
            size="sm"
            asChild
            className="gap-1.5 text-white hover:text-white border-[#727272] hover:bg-[#3e3e3e] hover:border-white"
          >
            <a href={audioUrl} download={title}>
              <Download className="w-3.5 h-3.5" />
              Download
            </a>
          </Button>
        )}
      </div>
      {audioUrl && (
        <audio controls className="w-full h-10" src={audioUrl}>
          Your browser does not support the audio element.
        </audio>
      )}
    </div>
  );
}

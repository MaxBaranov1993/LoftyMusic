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
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Equalizer } from "@/components/Equalizer";

const STATUS_CONFIG: Record<
  string,
  { icon: React.ElementType; className: string; label: string }
> = {
  pending: {
    icon: Clock,
    className: "bg-amber-100 text-amber-700 border-amber-200",
    label: "Pending",
  },
  queued: {
    icon: ListOrdered,
    className: "bg-secondary/15 text-secondary border-secondary/30",
    label: "Queued",
  },
  running: {
    icon: Loader2,
    className: "bg-primary/15 text-primary border-primary/30",
    label: "Running",
  },
  completed: {
    icon: CheckCircle2,
    className: "bg-emerald-100 text-emerald-700 border-emerald-200",
    label: "Completed",
  },
  failed: {
    icon: XCircle,
    className: "bg-red-100 text-red-700 border-red-200",
    label: "Failed",
  },
  cancelled: {
    icon: Ban,
    className: "bg-gray-100 text-gray-500 border-gray-200",
    label: "Cancelled",
  },
};

const STATUS_BORDER: Record<string, string> = {
  pending: "border-l-amber-400",
  queued: "border-l-secondary",
  running: "border-l-primary",
  completed: "border-l-emerald-500",
  failed: "border-l-red-400",
  cancelled: "border-l-gray-400",
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
        "animate-slide-up border-l-4 overflow-hidden transition-shadow duration-200 hover:shadow-md",
        STATUS_BORDER[job.status] || "border-l-gray-300"
      )}
    >
      <CardContent className="py-4">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 min-w-0">
            <p className="font-medium text-foreground truncate">{job.prompt}</p>
            <div className="flex items-center gap-2 mt-1.5 text-xs text-muted-foreground">
              <span>{job.duration_seconds}s</span>
              <span className="text-border">|</span>
              <span>{job.model_name}</span>
              <span className="text-border">|</span>
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
                className="h-7 w-7 text-muted-foreground hover:text-red-500"
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
                className="h-7 w-7 text-muted-foreground hover:text-red-500"
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

  const handlePlay = async () => {
    if (audioUrl) return;
    setLoading(true);
    try {
      const track = await api.getTrack(trackId);
      if (track.download_url) {
        setAudioUrl(track.download_url);
      }
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    handlePlay();
  }, [trackId]);

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-3 p-3 bg-muted/50 rounded-xl border border-border/40">
        <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center shrink-0">
          <Music className="w-5 h-5 text-primary" />
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
            className="gap-1.5 text-secondary hover:text-secondary border-secondary/30 hover:bg-secondary/5"
          >
            <a href={audioUrl} download={`${title}.wav`}>
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

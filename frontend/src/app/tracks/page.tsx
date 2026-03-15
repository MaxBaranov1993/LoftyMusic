"use client";

import { useState, useEffect } from "react";
import { useUser } from "@clerk/nextjs";
import Link from "next/link";
import { useAuthReady } from "@/components/AuthProvider";
import { api, Track } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  Pagination,
  PaginationContent,
  PaginationItem,
  PaginationPrevious,
  PaginationNext,
  PaginationLink,
} from "@/components/ui/pagination";
import { Music, Download, AlertCircle, Disc3 } from "lucide-react";

export default function TracksPage() {
  const { isSignedIn } = useUser();
  const authReady = useAuthReady();
  const [tracks, setTracks] = useState<Track[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);

  useEffect(() => {
    if (!authReady || !isSignedIn) {
      setLoading(false);
      return;
    }
    const fetchTracks = async () => {
      setLoading(true);
      try {
        const data = await api.listTracks(page);
        setTracks(data.items);
        setTotalPages(data.pages);
        setError(null);
      } catch (err: any) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };
    fetchTracks();
  }, [page, authReady, isSignedIn]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-foreground">My Tracks</h1>
        <p className="text-muted-foreground mt-1">
          Your generated music library
        </p>
      </div>

      {/* Error */}
      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Loading Skeletons */}
      {loading ? (
        <div className="space-y-3">
          {[1, 2, 3, 4].map((i) => (
            <Card key={i} className="border-border/40">
              <CardContent className="py-4">
                <div className="flex items-center gap-4">
                  <Skeleton className="w-12 h-12 rounded-xl shrink-0" />
                  <div className="flex-1 space-y-2">
                    <Skeleton className="h-4 w-48" />
                    <Skeleton className="h-3 w-64" />
                  </div>
                  <Skeleton className="h-9 w-28 rounded-lg" />
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : tracks.length === 0 ? (
        /* Empty State */
        <div className="text-center py-20 animate-fade-in">
          <div className="w-20 h-20 rounded-2xl bg-accent/30 border border-accent/50 flex items-center justify-center mx-auto mb-5">
            <Disc3 className="w-9 h-9 text-primary" />
          </div>
          <h3 className="text-lg font-semibold text-foreground">
            No tracks yet
          </h3>
          <p className="text-muted-foreground text-sm mt-1.5 mb-6">
            Generate your first track to see it here
          </p>
          <Button asChild>
            <Link href="/">Start Generating</Link>
          </Button>
        </div>
      ) : (
        /* Track List */
        <div className="space-y-3">
          {tracks.map((track) => (
            <TrackItem key={track.id} track={track} />
          ))}
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <Pagination>
          <PaginationContent>
            <PaginationItem>
              <PaginationPrevious
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                className={
                  page === 1
                    ? "pointer-events-none opacity-40"
                    : "cursor-pointer"
                }
              />
            </PaginationItem>
            {Array.from({ length: totalPages }, (_, i) => i + 1).map((p) => (
              <PaginationItem key={p}>
                <PaginationLink
                  onClick={() => setPage(p)}
                  isActive={page === p}
                  className="cursor-pointer"
                >
                  {p}
                </PaginationLink>
              </PaginationItem>
            ))}
            <PaginationItem>
              <PaginationNext
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                className={
                  page === totalPages
                    ? "pointer-events-none opacity-40"
                    : "cursor-pointer"
                }
              />
            </PaginationItem>
          </PaginationContent>
        </Pagination>
      )}
    </div>
  );
}

function TrackItem({ track }: { track: Track }) {
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const createdAt = new Date(track.created_at).toLocaleString();
  const sizeMb = (track.file_size_bytes / (1024 * 1024)).toFixed(1);

  useEffect(() => {
    api.getTrack(track.id).then((t) => {
      if (t.download_url) setAudioUrl(t.download_url);
    }).catch(() => {});
  }, [track.id]);

  return (
    <Card className="group border-border/40 hover:border-primary/30 hover:shadow-md transition-all duration-200 animate-slide-up">
      <CardContent className="py-4">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-accent/30 flex items-center justify-center shrink-0 group-hover:scale-105 transition-transform duration-200">
            <Music className="w-5 h-5 text-primary" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="font-medium text-foreground truncate">
              {track.title}
            </p>
            <div className="flex items-center gap-2 mt-1 text-xs text-muted-foreground">
              <span>{track.duration_seconds.toFixed(1)}s</span>
              <span className="text-border">|</span>
              <span>{track.sample_rate / 1000}kHz</span>
              <span className="text-border">|</span>
              <span>{sizeMb} MB</span>
              <span className="text-border hidden sm:inline">|</span>
              <span className="hidden sm:inline">{createdAt}</span>
            </div>
          </div>
          {audioUrl && (
            <Button
              variant="outline"
              size="sm"
              asChild
              className="gap-1.5 text-secondary hover:text-secondary border-secondary/30 hover:bg-secondary/5 shrink-0"
            >
              <a href={audioUrl} download={`${track.title}.wav`}>
                <Download className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">Download</span>
              </a>
            </Button>
          )}
        </div>
        {audioUrl && (
          <audio controls className="w-full h-10 mt-3" src={audioUrl}>
            Your browser does not support the audio element.
          </audio>
        )}
      </CardContent>
    </Card>
  );
}

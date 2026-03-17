"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { api, Job } from "@/lib/api";

const ACTIVE_STATUSES = ["pending", "queued", "running"];
const POLL_INTERVAL_MS = 3000;
const MAX_SSE_RETRIES = 3;

export function useJobs(enabled: boolean) {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const sseCleanups = useRef<Map<string, () => void>>(new Map());
  const sseRetries = useRef<Map<string, number>>(new Map());
  const jobsRef = useRef<Job[]>(jobs);

  // Keep ref in sync with state (avoids stale closure without adding jobs to deps)
  jobsRef.current = jobs;

  const fetchJobs = useCallback(async () => {
    try {
      const data = await api.listJobs(1);
      setJobs(data.items);
      setFetchError(null);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to fetch jobs";
      setFetchError(message);
    }
  }, []);

  // Initial fetch
  useEffect(() => {
    if (enabled) fetchJobs();
  }, [enabled, fetchJobs]);

  // SSE for running jobs + polling fallback for pending/queued.
  // Uses a polling loop that reads jobsRef to avoid re-triggering
  // the effect when jobs state changes (which caused infinite SSE reconnections).
  useEffect(() => {
    if (!enabled) return;

    let stopped = false;

    const connectSSE = (job: Job) => {
      if (sseCleanups.current.has(job.id)) return;

      const retryCount = sseRetries.current.get(job.id) ?? 0;
      if (retryCount >= MAX_SSE_RETRIES) {
        // Fall back to polling only — don't retry SSE indefinitely
        console.warn(`[useJobs] SSE max retries reached for job ${job.id}, falling back to polling`);
        return;
      }

      api.streamJobProgress(job.id, (event) => {
        if (event.type === "progress") {
          setJobs((prev) =>
            prev.map((j) =>
              j.id === job.id
                ? { ...j, progress: event.data.progress as number, status: event.data.status as string }
                : j
            )
          );
        } else if (event.type === "complete" || event.type === "error" || event.type === "cancelled") {
          fetchJobs();
          sseCleanups.current.get(job.id)?.();
          sseCleanups.current.delete(job.id);
          sseRetries.current.delete(job.id);
        }
      }).then((cleanup) => {
        if (stopped) {
          cleanup();
        } else {
          sseCleanups.current.set(job.id, cleanup);
        }
      }).catch(() => {
        // SSE ticket exchange failed — increment retry counter
        sseRetries.current.set(job.id, retryCount + 1);
      });
    };

    // Periodic check: connect SSE for running jobs, poll for pending/queued
    const tick = () => {
      const currentJobs = jobsRef.current;
      const activeJobs = currentJobs.filter((j) => ACTIVE_STATUSES.includes(j.status));

      // Connect SSE for any running jobs that don't have a connection yet
      for (const job of activeJobs) {
        if (job.status === "running") {
          connectSSE(job);
        }
      }

      // Re-fetch if there are pending/queued jobs (waiting for worker to pick them up),
      // or if we have running jobs with exhausted SSE retries (polling fallback)
      const needsPolling = activeJobs.some(
        (j) => j.status !== "running" ||
               (sseRetries.current.get(j.id) ?? 0) >= MAX_SSE_RETRIES
      );
      if (needsPolling) {
        fetchJobs();
      }
    };

    // Run immediately, then on interval
    tick();
    const interval = setInterval(tick, POLL_INTERVAL_MS);

    return () => {
      stopped = true;
      clearInterval(interval);
    };
  }, [enabled, fetchJobs]);

  // Cleanup SSE connections on unmount
  useEffect(() => {
    return () => {
      sseCleanups.current.forEach((cleanup) => cleanup());
      sseCleanups.current.clear();
      sseRetries.current.clear();
    };
  }, []);

  const hasActiveJob = jobs.some((j) => ACTIVE_STATUSES.includes(j.status));

  const addJob = useCallback((job: Job) => {
    setJobs((prev) => [job, ...prev]);
  }, []);

  const removeJob = useCallback((id: string) => {
    setJobs((prev) => prev.filter((j) => j.id !== id));
    sseCleanups.current.get(id)?.();
    sseCleanups.current.delete(id);
    sseRetries.current.delete(id);
  }, []);

  return {
    jobs,
    hasActiveJob,
    fetchError,
    addJob,
    removeJob,
    refetch: fetchJobs,
  };
}

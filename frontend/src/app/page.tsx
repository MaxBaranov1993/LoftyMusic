"use client";

import { useState, useEffect, useCallback } from "react";
import { useUser } from "@clerk/nextjs";
import GenerateForm from "@/components/GenerateForm";
import JobCard from "@/components/JobCard";
import { useAuthReady } from "@/components/AuthProvider";
import { api, Job } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { Zap, Cpu, Music } from "lucide-react";

export default function HomePage() {
  const { user, isSignedIn } = useUser();
  const authReady = useAuthReady();
  const [jobs, setJobs] = useState<Job[]>([]);

  const fetchJobs = useCallback(async () => {
    try {
      const data = await api.listJobs(1);
      setJobs(data.items);
    } catch {
      // silently ignore — user might not have jobs yet
    }
  }, []);

  useEffect(() => {
    if (authReady && isSignedIn) fetchJobs();
  }, [authReady, isSignedIn, fetchJobs]);

  // Poll for active jobs
  useEffect(() => {
    if (!isSignedIn) return;
    const hasActiveJobs = jobs.some(
      (j) =>
        j.status === "running" ||
        j.status === "queued" ||
        j.status === "pending"
    );
    if (!hasActiveJobs) return;

    const interval = setInterval(fetchJobs, 1500);
    return () => clearInterval(interval);
  }, [jobs, fetchJobs]);

  const hasActiveJob = jobs.some(
    (j) => j.status === "running" || j.status === "queued" || j.status === "pending"
  );

  const handleJobCreated = (job: Job) => {
    setJobs((prev) => [job, ...prev]);
  };

  return (
    <div className="space-y-10">
      {/* Hero */}
      <div className="relative text-center space-y-4 py-8">
        {/* Decorative gradient blob */}
        <div className="absolute inset-0 -z-10 overflow-hidden">
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-150 h-75 bg-linear-to-r from-accent/30 via-primary/15 to-secondary/20 rounded-full blur-3xl animate-gradient" />
        </div>

        <h1 className="text-4xl sm:text-5xl font-bold tracking-tight text-foreground">
          Create Music with{" "}
          <span className="bg-linear-to-r from-primary to-secondary bg-clip-text text-transparent">
            AI
          </span>
        </h1>
        <p className="text-muted-foreground text-lg max-w-xl mx-auto leading-relaxed">
          {user
            ? `Welcome back, ${user.firstName || "creator"}! Describe the music you want and let MusicGen bring it to life.`
            : "Describe the music you want and let MusicGen bring it to life. Generate unique tracks in seconds."}
        </p>
      </div>

      {/* Generate Form */}
      <Card className="border-border/50 shadow-lg shadow-primary/5 hover:shadow-xl hover:shadow-primary/10 transition-shadow duration-300">
        <CardContent>
          <h2 className="text-lg font-semibold text-foreground mb-4">
            New Generation
          </h2>
          <GenerateForm onJobCreated={handleJobCreated} disabled={hasActiveJob} />
        </CardContent>
      </Card>

      {/* Jobs List */}
      {jobs.length > 0 && (
        <div className="space-y-4">
          <div className="flex items-center gap-3">
            <h2 className="text-lg font-semibold text-foreground">
              Recent Jobs
            </h2>
            <Separator className="flex-1" />
          </div>
          <div className="space-y-3">
            {jobs.map((job) => (
              <JobCard
                key={job.id}
                job={job}
                onCancelled={fetchJobs}
                onDeleted={(id) => setJobs((prev) => prev.filter((j) => j.id !== id))}
              />
            ))}
          </div>
        </div>
      )}

      {/* Architecture Info */}
      <div className="space-y-4">
        <div className="flex items-center gap-3">
          <h2 className="text-lg font-semibold text-foreground">
            Architecture
          </h2>
          <Separator className="flex-1" />
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {[
            {
              icon: Zap,
              title: "FastAPI Backend",
              desc: "Async REST API with auto-generated OpenAPI docs",
              gradient: "from-primary/10 to-primary/5",
              iconColor: "text-primary",
              iconBg: "bg-primary/10",
            },
            {
              icon: Cpu,
              title: "GPU Worker Farm",
              desc: "Celery workers with MusicGen model on GPU",
              gradient: "from-secondary/10 to-secondary/5",
              iconColor: "text-secondary",
              iconBg: "bg-secondary/10",
            },
            {
              icon: Music,
              title: "MusicGen AI",
              desc: "Meta's open-source music generation model",
              gradient: "from-accent/20 to-accent/10",
              iconColor: "text-primary",
              iconBg: "bg-accent/40",
            },
          ].map((item) => {
            const Icon = item.icon;
            return (
              <Card
                key={item.title}
                className="group border-border/40 hover:border-primary/30 hover:shadow-md transition-all duration-300 cursor-default"
              >
                <CardContent className="py-5">
                  <div
                    className={`w-10 h-10 rounded-xl ${item.iconBg} flex items-center justify-center mb-3 group-hover:scale-110 transition-transform duration-200`}
                  >
                    <Icon className={`w-5 h-5 ${item.iconColor}`} />
                  </div>
                  <h3 className="font-semibold text-sm text-foreground">
                    {item.title}
                  </h3>
                  <p className="text-xs text-muted-foreground mt-1 leading-relaxed">
                    {item.desc}
                  </p>
                </CardContent>
              </Card>
            );
          })}
        </div>
      </div>
    </div>
  );
}

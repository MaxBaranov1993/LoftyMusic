"use client";

import { useUser } from "@clerk/nextjs";
import GenerateForm from "@/components/GenerateForm";
import JobCard from "@/components/JobCard";
import { useAuthReady } from "@/components/AuthProvider";
import { useJobs } from "@/hooks/useJobs";
import { Card, CardContent } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { Zap, Cpu, Music } from "lucide-react";

const ARCH_CARDS = [
  {
    icon: Zap,
    title: "FastAPI Backend",
    desc: "Async REST API with auto-generated OpenAPI docs",
  },
  {
    icon: Cpu,
    title: "GPU Worker",
    desc: "Colab T4 GPU via ACE-Step 1.5",
  },
  {
    icon: Music,
    title: "ACE-Step 1.5",
    desc: "Full songs with vocals, lyrics, up to 10 min",
  },
];

export default function HomePage() {
  const { user, isSignedIn } = useUser();
  const authReady = useAuthReady();
  const { jobs, hasActiveJob, addJob, removeJob, refetch } = useJobs(
    !!(authReady && isSignedIn)
  );

  return (
    <div className="space-y-10">
      {/* Hero */}
      <div className="relative text-center space-y-4 py-8">
        <div className="absolute inset-0 -z-10 overflow-hidden">
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-150 h-75 bg-linear-to-r from-[#1DB954]/20 via-[#1DB954]/5 to-transparent rounded-full blur-3xl animate-gradient opacity-40" />
        </div>

        <h1 className="text-4xl sm:text-5xl font-bold tracking-tight text-foreground">
          Create Music with{" "}
          <span className="bg-linear-to-r from-[#1DB954] to-[#1ed760] bg-clip-text text-transparent">
            AI
          </span>
        </h1>
        <p className="text-muted-foreground text-lg max-w-xl mx-auto leading-relaxed">
          {user
            ? `Welcome back, ${user.firstName || "creator"}! Describe the music you want and ACE-Step will bring it to life.`
            : "Describe the music you want and ACE-Step will bring it to life. Generate full songs with vocals in minutes."}
        </p>
      </div>

      {/* Generate Form */}
      <Card className="bg-[#181818] hover:bg-[#1a1a1a] transition-all duration-300">
        <CardContent>
          <h2 className="text-lg font-semibold text-foreground mb-4">
            New Generation
          </h2>
          <GenerateForm onJobCreated={addJob} disabled={hasActiveJob} />
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
                onCancelled={refetch}
                onDeleted={removeJob}
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
          {ARCH_CARDS.map((item) => {
            const Icon = item.icon;
            return (
              <Card
                key={item.title}
                className="group hover:bg-[#282828] hover:scale-[1.02] transition-all duration-300 cursor-default"
              >
                <CardContent className="py-5">
                  <div className="w-10 h-10 rounded-xl bg-[#1DB954]/15 flex items-center justify-center mb-3 group-hover:scale-110 transition-transform duration-200">
                    <Icon className="w-5 h-5 text-[#1DB954]" />
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

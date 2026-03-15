"use client";

import { useState } from "react";
import { api, Job, JobCreateRequest } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Slider } from "@/components/ui/slider";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Label } from "@/components/ui/label";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import {
  Zap,
  Coffee,
  Swords,
  Piano,
  CloudMoon,
  Guitar,
  Loader2,
  AlertCircle,
  Info,
} from "lucide-react";
import { cn } from "@/lib/utils";

const PRESETS = [
  { text: "upbeat electronic dance music with synth leads", icon: Zap, label: "Electronic" },
  { text: "calm lo-fi hip hop beats for studying", icon: Coffee, label: "Lo-fi" },
  { text: "epic orchestral cinematic trailer music", icon: Swords, label: "Cinematic" },
  { text: "smooth jazz piano with soft drums", icon: Piano, label: "Jazz" },
  { text: "dark ambient atmospheric soundscape", icon: CloudMoon, label: "Ambient" },
  { text: "acoustic folk guitar with gentle vocals", icon: Guitar, label: "Folk" },
];

interface Props {
  onJobCreated: (job: Job) => void;
  disabled?: boolean;
}

export default function GenerateForm({ onJobCreated, disabled }: Props) {
  const [prompt, setPrompt] = useState("");
  const [duration, setDuration] = useState(10);
  const [temperature, setTemperature] = useState(0.8);
  const [guidanceScale, setGuidanceScale] = useState(4.0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!prompt.trim() || prompt.trim().length < 3) return;

    setLoading(true);
    setError(null);

    try {
      const data: JobCreateRequest = {
        prompt: prompt.trim(),
        duration_seconds: duration,
        model_name: "musicgen-stereo-large",
        generation_params: {
          temperature,
          top_k: 250,
          top_p: 0.95,
          guidance_scale: guidanceScale,
        },
      };
      const job = await api.createJob(data);
      onJobCreated(job);
      setPrompt("");
    } catch (err: any) {
      setError(err.message || "Failed to create generation job");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="animate-slide-up">
      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Prompt */}
        <div className="space-y-2">
          <Label htmlFor="prompt" className="text-sm font-medium text-muted-foreground">
            Describe your music
          </Label>
          <Textarea
            id="prompt"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="Describe the music you want to generate..."
            rows={3}
            maxLength={1000}
            className="resize-none bg-background border-border/60 focus:border-primary transition-colors"
          />
          <div className="text-xs text-muted-foreground text-right">
            {prompt.length}/1000
          </div>
        </div>

        {/* Presets */}
        <div className="space-y-2.5">
          <Label className="text-sm font-medium text-muted-foreground">
            Quick presets
          </Label>
          <div className="flex flex-wrap gap-2">
            {PRESETS.map((preset) => {
              const Icon = preset.icon;
              const isActive = prompt === preset.text;
              return (
                <button
                  key={preset.label}
                  type="button"
                  onClick={() => setPrompt(preset.text)}
                  className={cn(
                    "inline-flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-full border transition-all duration-200 cursor-pointer",
                    isActive
                      ? "bg-primary/10 border-primary text-primary font-medium"
                      : "border-border text-muted-foreground hover:border-secondary hover:text-secondary hover:bg-secondary/5"
                  )}
                >
                  <Icon className="w-3 h-3" />
                  {preset.label}
                </button>
              );
            })}
          </div>
        </div>

        {/* Controls */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
          {/* Duration */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <Label className="text-sm font-medium text-muted-foreground">
                Duration
              </Label>
              <Badge variant="secondary" className="text-xs font-mono">
                {duration}s
              </Badge>
            </div>
            <Slider
              value={[duration]}
              onValueChange={([v]) => setDuration(v)}
              min={1}
              max={30}
              step={1}
            />
          </div>

          {/* Temperature */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1">
                <Label className="text-sm font-medium text-muted-foreground">
                  Temperature
                </Label>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Info className="w-3.5 h-3.5 text-muted-foreground/60 cursor-help" />
                  </TooltipTrigger>
                  <TooltipContent>
                    <p className="text-xs max-w-48">Higher values make output more random and creative, lower values make it more focused</p>
                  </TooltipContent>
                </Tooltip>
              </div>
              <Badge variant="secondary" className="text-xs font-mono">
                {temperature.toFixed(1)}
              </Badge>
            </div>
            <Slider
              value={[temperature * 10]}
              onValueChange={([v]) => setTemperature(v / 10)}
              min={1}
              max={20}
              step={1}
            />
          </div>

          {/* Guidance */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1">
                <Label className="text-sm font-medium text-muted-foreground">
                  Guidance
                </Label>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Info className="w-3.5 h-3.5 text-muted-foreground/60 cursor-help" />
                  </TooltipTrigger>
                  <TooltipContent>
                    <p className="text-xs max-w-48">Higher values make the output follow the prompt more closely</p>
                  </TooltipContent>
                </Tooltip>
              </div>
              <Badge variant="secondary" className="text-xs font-mono">
                {guidanceScale.toFixed(1)}
              </Badge>
            </div>
            <Slider
              value={[guidanceScale * 2]}
              onValueChange={([v]) => setGuidanceScale(v / 2)}
              min={2}
              max={20}
              step={1}
            />
          </div>
        </div>

        {/* Error */}
        {error && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {/* Submit */}
        <Button
          type="submit"
          size="lg"
          disabled={loading || disabled || prompt.trim().length < 3}
          className={cn(
            "w-full rounded-xl h-12 text-base font-semibold transition-all duration-300",
            !loading && !disabled && prompt.trim().length >= 3 && "glow-button shadow-lg shadow-primary/25"
          )}
        >
          {loading ? (
            <>
              <Loader2 className="w-5 h-5 animate-spin" />
              Creating job...
            </>
          ) : disabled ? (
            "Generation in progress..."
          ) : (
            "Generate Music"
          )}
        </Button>
      </form>
    </div>
  );
}

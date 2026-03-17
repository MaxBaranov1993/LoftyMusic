"use client";

import { useState } from "react";
import { api, Job, JobCreateRequest, QualityPreset, ModelName, ComputeMode } from "@/lib/api";
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
  Cpu,
  Coffee,
  Swords,
  Piano,
  CloudMoon,
  Guitar,
  Loader2,
  AlertCircle,
  Info,
  ChevronDown,
  Sparkles,
  Gauge,
  Crown,
  Mic2,
  Music,
} from "lucide-react";
import AdapterSelector from "@/components/AdapterSelector";
import { cn } from "@/lib/utils";

const PRESETS = [
  { text: "upbeat electronic dance music with synth leads", icon: Zap, label: "Electronic" },
  { text: "calm lo-fi hip hop beats for studying", icon: Coffee, label: "Lo-fi" },
  { text: "epic orchestral cinematic trailer music", icon: Swords, label: "Cinematic" },
  { text: "smooth jazz piano with soft drums", icon: Piano, label: "Jazz" },
  { text: "dark ambient atmospheric soundscape", icon: CloudMoon, label: "Ambient" },
  { text: "acoustic folk guitar with gentle vocals", icon: Guitar, label: "Folk" },
];

const QUALITY_PRESETS: {
  value: QualityPreset;
  label: string;
  description: string;
  icon: typeof Gauge;
  steps: number;
  guidance: number;
}[] = [
  {
    value: "balanced",
    label: "Balanced",
    description: "Best overall",
    icon: Sparkles,
    steps: 8,
    guidance: 5.0,
  },
  {
    value: "high",
    label: "High Quality",
    description: "Best quality",
    icon: Crown,
    steps: 8,
    guidance: 7.0,
  },
];

const MUSICAL_KEYS = [
  "C major", "C minor", "C# major", "C# minor",
  "D major", "D minor", "D# major", "D# minor",
  "E major", "E minor",
  "F major", "F minor", "F# major", "F# minor",
  "G major", "G minor", "G# major", "G# minor",
  "A major", "A minor", "A# major", "A# minor",
  "B major", "B minor",
];

const MODEL_OPTIONS: {
  value: ModelName;
  label: string;
  description: string;
  icon: typeof Music;
}[] = [
  {
    value: "ace-step-1.5",
    label: "ACE-Step 1.5",
    description: "Fast, versatile, instrumental or vocal",
    icon: Music,
  },
  {
    value: "yue",
    label: "YuE",
    description: "Vocal-focused, lyrics required, up to 60s",
    icon: Mic2,
  },
];

interface Props {
  onJobCreated: (job: Job) => void;
  disabled?: boolean;
}

export default function GenerateForm({ onJobCreated, disabled }: Props) {
  const [modelName, setModelName] = useState<ModelName>("ace-step-1.5");
  const [computeMode, setComputeMode] = useState<ComputeMode>("gpu");
  const [prompt, setPrompt] = useState("");
  const [lyrics, setLyrics] = useState("");
  const [duration, setDuration] = useState(15);
  const [qualityPreset, setQualityPreset] = useState<QualityPreset>("balanced");
  const [inferenceSteps, setInferenceSteps] = useState(8);
  const [guidanceScale, setGuidanceScale] = useState(5.0);
  const [bpm, setBpm] = useState<number | null>(null);
  const [musicalKey, setMusicalKey] = useState<string | null>(null);
  const [language, setLanguage] = useState("en");
  const [adapterId, setAdapterId] = useState<string | null>(null);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // YuE-specific state
  const [temperature, setTemperature] = useState(1.0);
  const [repetitionPenalty, setRepetitionPenalty] = useState(1.1);

  const isYuE = modelName === "yue";
  const maxDuration = isYuE ? 60 : 60; // Capped at 60s for free Colab T4 reliability

  const handleModelChange = (model: ModelName) => {
    setModelName(model);
    // Cap duration when switching to YuE
    if (model === "yue" && duration > 60) {
      setDuration(60);
    }
    // YuE requires GPU
    if (model === "yue") {
      setComputeMode("gpu");
    }
  };

  const handlePresetChange = (preset: QualityPreset) => {
    setQualityPreset(preset);
    const config = QUALITY_PRESETS.find((p) => p.value === preset);
    if (config) {
      setInferenceSteps(config.steps);
      setGuidanceScale(config.guidance);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!prompt.trim() || prompt.trim().length < 3) return;
    if (isYuE && !lyrics.trim()) return;

    setLoading(true);
    setError(null);

    try {
      const effectiveDuration = isYuE ? Math.min(duration, 60) : duration;

      const data: JobCreateRequest = {
        prompt: prompt.trim(),
        lyrics: lyrics || undefined,
        duration_seconds: effectiveDuration,
        model_name: modelName,
        lora_adapter_id: isYuE ? null : adapterId,
        compute_mode: computeMode,
        generation_params: isYuE
          ? {
              temperature,
              top_p: 0.93,
              repetition_penalty: repetitionPenalty,
              num_segments: Math.max(1, Math.min(2, Math.ceil(effectiveDuration / 30))),
              language,
              seed: -1,
            }
          : {
              guidance_scale: guidanceScale,
              quality_preset: qualityPreset,
              inference_steps: inferenceSteps,
              bpm: bpm,
              key: musicalKey,
              language,
              task_type: "text2music",
              seed: -1,
            },
      };
      const job = await api.createJob(data);
      onJobCreated(job);
      setPrompt("");
      setLyrics("");
    } catch (err: any) {
      setError(err.message || "Failed to create generation job");
    } finally {
      setLoading(false);
    }
  };

  const formatDuration = (seconds: number): string => {
    if (seconds < 60) return `${seconds}s`;
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return secs > 0 ? `${mins}m ${secs}s` : `${mins}m`;
  };

  return (
    <div className="animate-slide-up">
      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Model Selector */}
        <div className="space-y-2.5">
          <Label className="text-sm font-medium text-muted-foreground">
            Model
          </Label>
          <div className="grid grid-cols-2 gap-2">
            {MODEL_OPTIONS.map((model) => {
              const Icon = model.icon;
              const isActive = modelName === model.value;
              return (
                <button
                  key={model.value}
                  type="button"
                  onClick={() => handleModelChange(model.value)}
                  className={cn(
                    "flex items-center gap-3 px-4 py-3 rounded-lg border transition-all duration-200 cursor-pointer text-left",
                    isActive
                      ? "bg-[#1DB954]/10 border-[#1DB954] text-white"
                      : "border-[#383838] text-[#B3B3B3] hover:border-[#727272] hover:text-white"
                  )}
                >
                  <Icon className={cn("w-5 h-5 shrink-0", isActive && "text-[#1DB954]")} />
                  <div>
                    <div className="font-medium text-sm">{model.label}</div>
                    <div className="text-[11px] text-muted-foreground">{model.description}</div>
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* Compute Mode Selector */}
        <div className="space-y-2.5">
          <Label className="text-sm font-medium text-muted-foreground">
            Compute
          </Label>
          <div className="grid grid-cols-2 gap-2">
            {([
              { value: "cpu" as ComputeMode, label: "CPU", description: "Free, slower", icon: Cpu },
              { value: "gpu" as ComputeMode, label: "GPU", description: "Fast", icon: Zap },
            ]).map((option) => {
              const Icon = option.icon;
              const isActive = computeMode === option.value;
              const isCpuDisabled = option.value === "cpu" && isYuE;
              return (
                <Tooltip key={option.value}>
                  <TooltipTrigger asChild>
                    <button
                      type="button"
                      onClick={() => !isCpuDisabled && setComputeMode(option.value)}
                      disabled={isCpuDisabled}
                      className={cn(
                        "flex items-center gap-3 px-4 py-3 rounded-lg border transition-all duration-200 text-left",
                        isCpuDisabled
                          ? "border-[#282828] text-[#535353] cursor-not-allowed opacity-50"
                          : isActive
                            ? "bg-[#1DB954]/10 border-[#1DB954] text-white cursor-pointer"
                            : "border-[#383838] text-[#B3B3B3] hover:border-[#727272] hover:text-white cursor-pointer"
                      )}
                    >
                      <Icon className={cn("w-5 h-5 shrink-0", isActive && "text-[#1DB954]")} />
                      <div>
                        <div className="font-medium text-sm">{option.label}</div>
                        <div className="text-[11px] text-muted-foreground">{option.description}</div>
                      </div>
                    </button>
                  </TooltipTrigger>
                  {isCpuDisabled && (
                    <TooltipContent>
                      <p className="text-xs">YuE requires GPU</p>
                    </TooltipContent>
                  )}
                </Tooltip>
              );
            })}
          </div>
          {computeMode === "cpu" && (
            <Alert className="border-amber-500/30 bg-amber-500/5">
              <AlertCircle className="h-4 w-4 text-amber-500" />
              <AlertDescription className="text-xs text-amber-200">
                CPU mode is significantly slower. A 15s track may take 2-5 minutes.
              </AlertDescription>
            </Alert>
          )}
        </div>

        {/* Prompt */}
        <div className="space-y-2">
          <Label htmlFor="prompt" className="text-sm font-medium text-muted-foreground">
            {isYuE ? "Genre tags (style, mood, instruments, vocal)" : "Describe the style & mood"}
          </Label>
          <Textarea
            id="prompt"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder={
              isYuE
                ? "inspiring female uplifting pop airy vocal electronic bright vocal"
                : "Describe the style, genre, mood, instruments..."
            }
            rows={isYuE ? 2 : 3}
            maxLength={1000}
            className="resize-none bg-[#282828] border-[#282828] focus:border-[#1DB954] focus:ring-[#1DB954]/20 transition-all placeholder:text-[#727272] rounded-lg"
          />
          <div className="text-xs text-muted-foreground text-right">
            {prompt.length}/1000
          </div>
        </div>

        {/* Lyrics */}
        <div className="space-y-2">
          <div className="flex items-center gap-1">
            <Label htmlFor="lyrics" className="text-sm font-medium text-muted-foreground">
              Lyrics
            </Label>
            {isYuE ? (
              <Badge variant="destructive" className="text-[10px]">required</Badge>
            ) : (
              <Badge variant="secondary" className="text-[10px]">optional</Badge>
            )}
          </div>
          <Textarea
            id="lyrics"
            value={lyrics}
            onChange={(e) => setLyrics(e.target.value)}
            placeholder={"[verse]\nYour lyrics here...\n\n[chorus]\nChorus lyrics..."}
            rows={isYuE ? 8 : 5}
            maxLength={5000}
            className="resize-none bg-[#282828] border-[#282828] focus:border-[#1DB954] focus:ring-[#1DB954]/20 transition-all placeholder:text-[#727272] rounded-lg font-mono text-sm"
          />
          <div className="flex items-center justify-between">
            {isYuE ? (
              <span className="text-[10px] text-[#727272]">
                Use [verse], [chorus], [bridge], [outro] markers. Max 2 sections for free Colab.
              </span>
            ) : lyrics.trim() ? (
              <span className="text-[10px] text-[#727272]">
                On free GPU, lyrics may fallback to instrumental if generation fails.
              </span>
            ) : null}
            <span className="text-xs text-muted-foreground ml-auto">
              {lyrics.length}/5000
            </span>
          </div>
        </div>

        {/* Adapter Selector — ACE-Step only */}
        {!isYuE && <AdapterSelector value={adapterId} onChange={setAdapterId} />}

        {/* Quick Presets — ACE-Step only */}
        {!isYuE && (
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
                        ? "bg-[#1DB954] border-[#1DB954] text-black font-bold"
                        : "border-[#727272] text-[#B3B3B3] hover:border-white hover:text-white hover:bg-[#282828]"
                    )}
                  >
                    <Icon className="w-3 h-3" />
                    {preset.label}
                  </button>
                );
              })}
            </div>
          </div>
        )}

        {/* Duration + Quality */}
        <div className={cn("grid gap-6", isYuE ? "grid-cols-1" : "grid-cols-1 sm:grid-cols-2")}>
          {/* Duration */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1">
                <Label className="text-sm font-medium text-muted-foreground">
                  Duration
                </Label>
                {isYuE && (
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Info className="w-3.5 h-3.5 text-muted-foreground/60 cursor-help" />
                    </TooltipTrigger>
                    <TooltipContent>
                      <p className="text-xs max-w-56">
                        YuE generates ~30s per segment. Max 2 segments (60s) on free Colab to avoid OOM.
                      </p>
                    </TooltipContent>
                  </Tooltip>
                )}
              </div>
              <div className="flex items-center gap-2">
                <Badge variant="secondary" className="text-xs font-mono">
                  {formatDuration(Math.min(duration, maxDuration))}
                </Badge>
                {isYuE && (
                  <Badge variant="outline" className="text-[10px] text-[#727272]">
                    {Math.max(1, Math.min(2, Math.ceil(Math.min(duration, maxDuration) / 30)))} seg
                  </Badge>
                )}
              </div>
            </div>
            <Slider
              value={[Math.min(duration, maxDuration)]}
              onValueChange={([v]) => setDuration(v)}
              min={5}
              max={maxDuration}
              step={5}
            />
          </div>

          {/* Quality Preset — ACE-Step only */}
          {!isYuE && (
            <div className="space-y-3">
              <div className="flex items-center gap-1">
                <Label className="text-sm font-medium text-muted-foreground">
                  Quality
                </Label>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Info className="w-3.5 h-3.5 text-muted-foreground/60 cursor-help" />
                  </TooltipTrigger>
                  <TooltipContent>
                    <p className="text-xs max-w-56">
                      Draft uses fewer diffusion steps. Balanced is recommended. High uses more steps for better quality.
                    </p>
                  </TooltipContent>
                </Tooltip>
              </div>
              <div className="flex gap-2">
                {QUALITY_PRESETS.map((preset) => {
                  const Icon = preset.icon;
                  const isActive = qualityPreset === preset.value;
                  return (
                    <button
                      key={preset.value}
                      type="button"
                      onClick={() => handlePresetChange(preset.value)}
                      className={cn(
                        "flex-1 flex flex-col items-center gap-1 px-2 py-2 text-xs rounded-lg border transition-all duration-200 cursor-pointer",
                        isActive
                          ? "bg-[#1DB954]/10 border-[#1DB954] text-[#1DB954]"
                          : "border-[#383838] text-[#B3B3B3] hover:border-[#727272] hover:text-white"
                      )}
                    >
                      <Icon className="w-4 h-4" />
                      <span className="font-medium">{preset.label}</span>
                    </button>
                  );
                })}
              </div>
            </div>
          )}
        </div>

        {/* ACE-Step: BPM + Key + Language */}
        {!isYuE && (
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {/* BPM */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label className="text-sm font-medium text-muted-foreground">BPM</Label>
                <Badge variant="secondary" className="text-xs font-mono">
                  {bpm ?? "auto"}
                </Badge>
              </div>
              <Slider
                value={[bpm ?? 120]}
                onValueChange={([v]) => setBpm(v)}
                min={40}
                max={240}
                step={1}
              />
              <button
                type="button"
                onClick={() => setBpm(null)}
                className="text-[10px] text-[#727272] hover:text-white transition-colors cursor-pointer"
              >
                Reset to auto
              </button>
            </div>

            {/* Key */}
            <div className="space-y-2">
              <Label className="text-sm font-medium text-muted-foreground">Key</Label>
              <select
                value={musicalKey ?? ""}
                onChange={(e) => setMusicalKey(e.target.value || null)}
                className="w-full h-9 px-3 rounded-lg bg-[#282828] border border-[#383838] text-sm text-[#B3B3B3] focus:border-[#1DB954] focus:outline-none"
              >
                <option value="">Auto</option>
                {MUSICAL_KEYS.map((k) => (
                  <option key={k} value={k}>{k}</option>
                ))}
              </select>
            </div>

            {/* Language */}
            <div className="space-y-2">
              <Label className="text-sm font-medium text-muted-foreground">Language</Label>
              <select
                value={language}
                onChange={(e) => setLanguage(e.target.value)}
                className="w-full h-9 px-3 rounded-lg bg-[#282828] border border-[#383838] text-sm text-[#B3B3B3] focus:border-[#1DB954] focus:outline-none"
              >
                <option value="en">English</option>
                <option value="zh">Chinese</option>
                <option value="ja">Japanese</option>
                <option value="ko">Korean</option>
                <option value="es">Spanish</option>
                <option value="fr">French</option>
                <option value="de">German</option>
                <option value="ru">Russian</option>
                <option value="pt">Portuguese</option>
                <option value="it">Italian</option>
              </select>
            </div>
          </div>
        )}

        {/* YuE: Language + Temperature + Repetition Penalty */}
        {isYuE && (
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {/* Language */}
            <div className="space-y-2">
              <Label className="text-sm font-medium text-muted-foreground">Language</Label>
              <select
                value={language}
                onChange={(e) => setLanguage(e.target.value)}
                className="w-full h-9 px-3 rounded-lg bg-[#282828] border border-[#383838] text-sm text-[#B3B3B3] focus:border-[#1DB954] focus:outline-none"
              >
                <option value="en">English</option>
                <option value="zh">Chinese</option>
                <option value="ja">Japanese</option>
                <option value="ko">Korean</option>
              </select>
            </div>

            {/* Temperature */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1">
                  <Label className="text-sm font-medium text-muted-foreground">Temperature</Label>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Info className="w-3.5 h-3.5 text-muted-foreground/60 cursor-help" />
                    </TooltipTrigger>
                    <TooltipContent>
                      <p className="text-xs max-w-48">Controls randomness. Higher = more creative, lower = more stable. Default 1.0.</p>
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

            {/* Repetition Penalty */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1">
                  <Label className="text-sm font-medium text-muted-foreground">Rep. Penalty</Label>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Info className="w-3.5 h-3.5 text-muted-foreground/60 cursor-help" />
                    </TooltipTrigger>
                    <TooltipContent>
                      <p className="text-xs max-w-48">Discourages repetition. Higher = more diverse. Default 1.1.</p>
                    </TooltipContent>
                  </Tooltip>
                </div>
                <Badge variant="secondary" className="text-xs font-mono">
                  {repetitionPenalty.toFixed(1)}
                </Badge>
              </div>
              <Slider
                value={[repetitionPenalty * 10]}
                onValueChange={([v]) => setRepetitionPenalty(v / 10)}
                min={10}
                max={20}
                step={1}
              />
            </div>
          </div>
        )}

        {/* Advanced Controls — ACE-Step only */}
        {!isYuE && (
          <div>
            <button
              type="button"
              onClick={() => setShowAdvanced(!showAdvanced)}
              className="flex items-center gap-1.5 text-xs text-[#B3B3B3] hover:text-white transition-colors cursor-pointer"
            >
              <ChevronDown
                className={cn(
                  "w-3.5 h-3.5 transition-transform duration-200",
                  showAdvanced && "rotate-180"
                )}
              />
              Advanced parameters
            </button>

            {showAdvanced && (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 mt-4">
                {/* Inference Steps */}
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-1">
                      <Label className="text-sm font-medium text-muted-foreground">
                        Inference Steps
                      </Label>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <Info className="w-3.5 h-3.5 text-muted-foreground/60 cursor-help" />
                        </TooltipTrigger>
                        <TooltipContent>
                          <p className="text-xs max-w-48">More steps = higher quality but slower generation. 4-8 recommended for Turbo model.</p>
                        </TooltipContent>
                      </Tooltip>
                    </div>
                    <Badge variant="secondary" className="text-xs font-mono">
                      {inferenceSteps}
                    </Badge>
                  </div>
                  <Slider
                    value={[inferenceSteps]}
                    onValueChange={([v]) => setInferenceSteps(v)}
                    min={1}
                    max={8}
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
                          <p className="text-xs max-w-48">Higher values follow the prompt more closely. 3.0-7.0 recommended.</p>
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
            )}
          </div>
        )}

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
          disabled={loading || disabled || prompt.trim().length < 3 || (isYuE && !lyrics.trim())}
          className={cn(
            "w-full rounded-full h-12 text-base font-bold transition-all duration-300",
            !loading && !disabled && prompt.trim().length >= 3 && !(isYuE && !lyrics.trim()) && "glow-button hover:scale-105"
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
            <>Generate {isYuE ? "Song with Vocals" : lyrics ? "Music with Vocals" : "Music"}</>
          )}
        </Button>
      </form>
    </div>
  );
}

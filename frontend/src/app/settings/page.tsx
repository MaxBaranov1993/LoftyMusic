"use client";

import { useEffect, useState, useCallback } from "react";
import {
  Monitor,
  Cloud,
  Globe,
  Cpu,
  Zap,
  Copy,
  Check,
  Power,
  PowerOff,
  RefreshCw,
  AlertTriangle,
  Settings2,
  DollarSign,
  Server,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert";
import { Slider } from "@/components/ui/slider";
import { Skeleton } from "@/components/ui/skeleton";
import {
  api,
  type GpuSettings,
  type GpuStatus,
  type GpuInstance,
} from "@/lib/api";

type Backend = "local" | "google" | "cloud";

const BACKENDS: {
  id: Backend;
  name: string;
  subtitle: string;
  icon: React.ReactNode;
  cost: string;
  features: string[];
  color: string;
}[] = [
  {
    id: "local",
    name: "Local GPU / CPU",
    subtitle: "Use this machine",
    icon: <Monitor className="w-6 h-6" />,
    cost: "Free",
    features: [
      "Zero cost",
      "Uses local CUDA GPU or CPU fallback",
      "Best for development & testing",
      "No internet required",
    ],
    color: "text-blue-400",
  },
  {
    id: "google",
    name: "Google Colab",
    subtitle: "Free cloud GPU",
    icon: <Globe className="w-6 h-6" />,
    cost: "Free (with limits)",
    features: [
      "Free T4 GPU (15 GB VRAM)",
      "~30 hrs/week on Kaggle",
      "Setup via notebook snippet",
      "Great for demos & MVP",
    ],
    color: "text-green-400",
  },
  {
    id: "cloud",
    name: "Cloud GPU (RunPod)",
    subtitle: "On-demand GPU farm",
    icon: <Cloud className="w-6 h-6" />,
    cost: "Pay-per-use",
    features: [
      "A40, A100, RTX 4090 available",
      "Auto-scale on queue depth",
      "~$0.20-1.60/hr per GPU",
      "Production-grade reliability",
    ],
    color: "text-purple-400",
  },
];

export default function SettingsPage() {
  const [gpuSettings, setGpuSettings] = useState<GpuSettings | null>(null);
  const [gpuStatus, setGpuStatus] = useState<GpuStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  // Form state
  const [selectedBackend, setSelectedBackend] = useState<Backend>("local");
  const [apiKey, setApiKey] = useState("");
  const [autoscalerEnabled, setAutoscalerEnabled] = useState(false);
  const [maxInstances, setMaxInstances] = useState(3);
  const [idleTimeout, setIdleTimeout] = useState(300);

  const loadSettings = useCallback(async () => {
    try {
      setLoading(true);
      const [settings, status] = await Promise.all([
        api.getGpuSettings(),
        api.getGpuStatus(),
      ]);
      setGpuSettings(settings);
      setGpuStatus(status);
      setSelectedBackend(settings.backend as Backend);
      setAutoscalerEnabled(settings.autoscaler_enabled);
      setMaxInstances(settings.autoscaler_max_instances);
      setIdleTimeout(settings.autoscaler_idle_timeout);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load settings");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadSettings();
  }, [loadSettings]);

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    setSuccess(null);
    try {
      const updated = await api.updateGpuSettings({
        backend: selectedBackend,
        cloud_api_key: apiKey || null,
        autoscaler_enabled: autoscalerEnabled,
        autoscaler_max_instances: maxInstances,
        autoscaler_idle_timeout: idleTimeout,
      });
      setGpuSettings(updated);
      setApiKey("");
      setSuccess("Settings saved successfully!");
      // Refresh status for new backend
      const status = await api.getGpuStatus();
      setGpuStatus(status);
      setTimeout(() => setSuccess(null), 3000);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save settings");
    } finally {
      setSaving(false);
    }
  };

  const handleSpinUp = async () => {
    try {
      await api.spinUpInstance();
      setSuccess("GPU instance spinning up...");
      setTimeout(() => setSuccess(null), 3000);
      const status = await api.getGpuStatus();
      setGpuStatus(status);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to spin up");
    }
  };

  const handleTearDown = async (instanceId: string) => {
    try {
      await api.tearDownInstance(instanceId);
      const status = await api.getGpuStatus();
      setGpuStatus(status);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to tear down");
    }
  };

  const handleCopySnippet = () => {
    if (gpuStatus?.colab_setup_snippet) {
      navigator.clipboard.writeText(gpuStatus.colab_setup_snippet);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  if (loading) {
    return (
      <div className="space-y-6 animate-fade-in">
        <Skeleton className="h-10 w-48 bg-[#282828]" />
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-56 bg-[#282828] rounded-xl" />
          ))}
        </div>
        <Skeleton className="h-48 bg-[#282828] rounded-xl" />
      </div>
    );
  }

  return (
    <div className="space-y-8 animate-slide-up">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight flex items-center gap-3">
          <Settings2 className="w-8 h-8 text-[#1DB954]" />
          GPU Settings
        </h1>
        <p className="text-[#B3B3B3] mt-2">
          Choose how Lofty generates music — locally, via free Google Colab, or
          with on-demand cloud GPUs.
        </p>
      </div>

      {/* Alerts */}
      {error && (
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertTitle>Error</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
      {success && (
        <Alert>
          <Check className="h-4 w-4" />
          <AlertTitle>Success</AlertTitle>
          <AlertDescription>{success}</AlertDescription>
        </Alert>
      )}

      {/* Backend Selection Cards */}
      <div>
        <h2 className="text-lg font-semibold mb-4">GPU Backend</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {BACKENDS.map((backend) => {
            const isSelected = selectedBackend === backend.id;
            return (
              <button
                key={backend.id}
                onClick={() => setSelectedBackend(backend.id)}
                className={`relative text-left p-5 rounded-xl border-2 transition-all duration-200 ${
                  isSelected
                    ? "border-[#1DB954] bg-[#1DB954]/5 shadow-[0_0_20px_rgba(29,185,84,0.15)]"
                    : "border-[#282828] bg-[#121212] hover:border-[#3e3e3e] hover:bg-[#181818]"
                }`}
              >
                {/* Selected indicator */}
                {isSelected && (
                  <div className="absolute top-3 right-3">
                    <div className="w-5 h-5 rounded-full bg-[#1DB954] flex items-center justify-center">
                      <Check className="w-3 h-3 text-black" />
                    </div>
                  </div>
                )}

                {/* Icon + Name */}
                <div className={`${backend.color} mb-3`}>{backend.icon}</div>
                <h3 className="text-white font-bold text-lg">{backend.name}</h3>
                <p className="text-[#B3B3B3] text-sm mb-3">
                  {backend.subtitle}
                </p>

                {/* Cost Badge */}
                <Badge
                  variant={backend.id === "cloud" ? "outline" : "default"}
                  className={
                    backend.id === "cloud"
                      ? "border-purple-500/50 text-purple-400"
                      : ""
                  }
                >
                  <DollarSign className="w-3 h-3" />
                  {backend.cost}
                </Badge>

                {/* Features */}
                <ul className="mt-4 space-y-1.5">
                  {backend.features.map((f, i) => (
                    <li
                      key={i}
                      className="text-sm text-[#B3B3B3] flex items-start gap-2"
                    >
                      <Zap className="w-3 h-3 mt-1 shrink-0 text-[#1DB954]" />
                      {f}
                    </li>
                  ))}
                </ul>
              </button>
            );
          })}
        </div>
      </div>

      {/* Cloud API Key (only for cloud backend) */}
      {selectedBackend === "cloud" && (
        <div className="bg-[#121212] border border-[#282828] rounded-xl p-5 space-y-4">
          <h3 className="text-white font-semibold flex items-center gap-2">
            <Cloud className="w-5 h-5 text-purple-400" />
            RunPod Configuration
          </h3>
          <div>
            <label className="text-sm text-[#B3B3B3] block mb-1.5">
              API Key
            </label>
            <div className="flex gap-2">
              <input
                type="password"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder={
                  gpuSettings?.cloud_api_key_configured
                    ? "Key is configured (enter new to replace)"
                    : "Enter your RunPod API key"
                }
                className="flex-1 bg-[#282828] border border-[#3e3e3e] rounded-lg px-3 py-2 text-white text-sm placeholder:text-[#727272] focus:outline-none focus:ring-2 focus:ring-[#1DB954]/50 focus:border-[#1DB954]"
              />
            </div>
            {gpuSettings?.cloud_api_key_configured && (
              <p className="text-xs text-green-500 mt-1 flex items-center gap-1">
                <Check className="w-3 h-3" /> API key is configured
              </p>
            )}
          </div>
        </div>
      )}

      {/* Google Colab Setup (only for google backend) */}
      {selectedBackend === "google" && gpuStatus?.colab_setup_snippet && (
        <div className="bg-[#121212] border border-[#282828] rounded-xl p-5 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-white font-semibold flex items-center gap-2">
              <Globe className="w-5 h-5 text-green-400" />
              Google Colab Setup
            </h3>
            <Button
              variant="ghost"
              size="sm"
              onClick={handleCopySnippet}
              className="text-[#B3B3B3] hover:text-white"
            >
              {copied ? (
                <Check className="w-4 h-4 mr-1" />
              ) : (
                <Copy className="w-4 h-4 mr-1" />
              )}
              {copied ? "Copied!" : "Copy"}
            </Button>
          </div>
          <p className="text-sm text-[#B3B3B3]">
            1. Open{" "}
            <span className="text-[#1DB954] font-medium">
              Google Colab
            </span>{" "}
            and select a{" "}
            <span className="text-white font-medium">GPU runtime</span> (T4)
          </p>
          <p className="text-sm text-[#B3B3B3]">
            2. Paste the snippet below into a cell and run it:
          </p>
          <pre className="bg-black/50 border border-[#282828] rounded-lg p-4 text-xs text-green-400 font-mono overflow-x-auto max-h-64 overflow-y-auto">
            {gpuStatus.colab_setup_snippet}
          </pre>
          <p className="text-sm text-[#B3B3B3]">
            3. The worker will connect automatically. Check status below.
          </p>
        </div>
      )}

      {/* Autoscaler Settings (cloud + google) */}
      {selectedBackend !== "local" && (
        <div className="bg-[#121212] border border-[#282828] rounded-xl p-5 space-y-5">
          <h3 className="text-white font-semibold flex items-center gap-2">
            <Cpu className="w-5 h-5 text-[#1DB954]" />
            Autoscaler
          </h3>

          {/* Enable toggle */}
          <div className="flex items-center justify-between">
            <div>
              <p className="text-white text-sm font-medium">
                Enable Auto-scaling
              </p>
              <p className="text-[#B3B3B3] text-xs mt-0.5">
                Automatically spin up/down GPU instances based on queue depth
              </p>
            </div>
            <button
              onClick={() => setAutoscalerEnabled(!autoscalerEnabled)}
              className={`w-11 h-6 rounded-full transition-colors duration-200 ${
                autoscalerEnabled ? "bg-[#1DB954]" : "bg-[#282828]"
              }`}
            >
              <div
                className={`w-5 h-5 rounded-full bg-white shadow transition-transform duration-200 ${
                  autoscalerEnabled ? "translate-x-5.5" : "translate-x-0.5"
                }`}
              />
            </button>
          </div>

          {autoscalerEnabled && (
            <>
              {/* Max instances */}
              <div>
                <div className="flex justify-between mb-2">
                  <label className="text-sm text-[#B3B3B3]">
                    Max GPU Instances
                  </label>
                  <span className="text-sm text-white font-mono">
                    {maxInstances}
                  </span>
                </div>
                <Slider
                  min={1}
                  max={10}
                  step={1}
                  value={[maxInstances]}
                  onValueChange={([v]) => setMaxInstances(v)}
                />
              </div>

              {/* Idle timeout */}
              <div>
                <div className="flex justify-between mb-2">
                  <label className="text-sm text-[#B3B3B3]">
                    Idle Timeout
                  </label>
                  <span className="text-sm text-white font-mono">
                    {Math.floor(idleTimeout / 60)}m {idleTimeout % 60}s
                  </span>
                </div>
                <Slider
                  min={60}
                  max={1800}
                  step={60}
                  value={[idleTimeout]}
                  onValueChange={([v]) => setIdleTimeout(v)}
                />
                <p className="text-xs text-[#727272] mt-1">
                  How long an idle GPU instance waits before shutting down
                </p>
              </div>
            </>
          )}
        </div>
      )}

      {/* Save Button */}
      <div className="flex gap-3">
        <Button
          onClick={handleSave}
          disabled={saving}
          className="bg-[#1DB954] hover:bg-[#1ed760] text-black font-bold rounded-full px-8"
        >
          {saving ? "Saving..." : "Save Settings"}
        </Button>
        <Button
          variant="ghost"
          onClick={loadSettings}
          className="text-[#B3B3B3] hover:text-white rounded-full"
        >
          <RefreshCw className="w-4 h-4 mr-2" />
          Refresh
        </Button>
      </div>

      {/* Active Instances */}
      <div className="bg-[#121212] border border-[#282828] rounded-xl p-5 space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-white font-semibold flex items-center gap-2">
            <Server className="w-5 h-5 text-[#1DB954]" />
            Active GPU Instances
          </h3>
          {selectedBackend !== "local" && (
            <Button
              size="sm"
              onClick={handleSpinUp}
              className="bg-[#1DB954] hover:bg-[#1ed760] text-black font-bold rounded-full"
            >
              <Power className="w-4 h-4 mr-1" />
              Spin Up
            </Button>
          )}
        </div>

        {gpuStatus && gpuStatus.instances.length > 0 ? (
          <div className="space-y-3">
            {gpuStatus.instances.map((instance: GpuInstance) => (
              <div
                key={instance.id}
                className="flex items-center justify-between bg-[#181818] border border-[#282828] rounded-lg p-3"
              >
                <div className="flex items-center gap-3">
                  <div
                    className={`w-2.5 h-2.5 rounded-full ${
                      instance.status === "running"
                        ? "bg-green-500 animate-pulse"
                        : instance.status === "pending"
                          ? "bg-yellow-500 animate-pulse"
                          : "bg-red-500"
                    }`}
                  />
                  <div>
                    <p className="text-white text-sm font-medium">
                      {instance.id}
                    </p>
                    <p className="text-[#B3B3B3] text-xs">
                      {instance.gpu_type} &middot;{" "}
                      {(instance.gpu_memory_mb / 1024).toFixed(0)} GB &middot;{" "}
                      <span
                        className={
                          instance.status === "running"
                            ? "text-green-400"
                            : instance.status === "pending"
                              ? "text-yellow-400"
                              : "text-red-400"
                        }
                      >
                        {instance.status}
                      </span>
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  {instance.cost_per_hour > 0 && (
                    <span className="text-xs text-[#B3B3B3]">
                      ${instance.cost_per_hour.toFixed(2)}/hr
                    </span>
                  )}
                  {instance.backend !== "local" && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleTearDown(instance.id)}
                      className="text-red-400 hover:text-red-300 hover:bg-red-500/10"
                    >
                      <PowerOff className="w-4 h-4" />
                    </Button>
                  )}
                </div>
              </div>
            ))}

            {/* Total cost */}
            {gpuStatus.total_cost_per_hour > 0 && (
              <div className="flex justify-end">
                <Badge variant="outline" className="border-[#727272]">
                  Total: ${gpuStatus.total_cost_per_hour.toFixed(2)}/hr
                </Badge>
              </div>
            )}
          </div>
        ) : (
          <div className="text-center py-8 text-[#727272]">
            <Cpu className="w-10 h-10 mx-auto mb-2 opacity-50" />
            <p className="text-sm">
              {selectedBackend === "local"
                ? "Using local machine for generation"
                : "No active instances. Spin one up or enable autoscaling."}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

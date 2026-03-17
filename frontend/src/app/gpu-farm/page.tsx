"use client";

import { useState, useRef, useEffect } from "react";
import {
  Server,
  Cpu,
  Zap,
  ArrowRight,
  ChevronDown,
  Copy,
  Check,
  Shield,
  Activity,
  HardDrive,
  Network,
  Terminal,
  GitBranch,
  Layers,
  Clock,
  AlertTriangle,
  CheckCircle2,
  Settings,
  Play,
  Square,
  BarChart3,
  Globe,
  Database,
  Radio,
  RefreshCw,
  Cloud,
  MonitorSpeaker,
} from "lucide-react";

/* ─────────────────────────────────────────────
   Helpers
   ───────────────────────────────────────────── */

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      onClick={() => {
        navigator.clipboard.writeText(text);
        setCopied(true);
        setTimeout(() => setCopied(false), 1500);
      }}
      className="absolute top-3 right-3 p-1.5 rounded-md bg-white/5 hover:bg-white/10 transition-colors text-[#b3b3b3] hover:text-white"
      title="Copy"
    >
      {copied ? (
        <Check className="w-3.5 h-3.5" />
      ) : (
        <Copy className="w-3.5 h-3.5" />
      )}
    </button>
  );
}

function CodeBlock({ code, title }: { code: string; title?: string }) {
  return (
    <div className="relative group">
      {title && (
        <div className="bg-[#111] border border-[#1a1a1a] border-b-0 rounded-t-lg px-4 py-2 text-[11px] uppercase tracking-wider text-[#555] font-semibold font-mono">
          {title}
        </div>
      )}
      <pre
        className={`bg-[#0a0a0a] border border-[#1a1a1a] ${
          title ? "rounded-b-lg" : "rounded-lg"
        } p-4 overflow-x-auto text-[13px] leading-relaxed font-mono text-[#e0e0e0]`}
      >
        <code>{code}</code>
      </pre>
      <CopyButton text={code} />
    </div>
  );
}

function StepNumber({ n }: { n: number }) {
  return (
    <span className="w-7 h-7 rounded-full bg-[#1DB954] text-black text-xs font-bold flex items-center justify-center shrink-0">
      {n}
    </span>
  );
}

function InfoBox({
  type = "info",
  children,
}: {
  type?: "info" | "warn" | "success";
  children: React.ReactNode;
}) {
  const styles = {
    info: "text-blue-400/80 bg-blue-400/5 border-blue-400/10",
    warn: "text-amber-500/80 bg-amber-500/5 border-amber-500/10",
    success: "text-[#1DB954]/80 bg-[#1DB954]/5 border-[#1DB954]/10",
  };
  const icons = {
    info: AlertTriangle,
    warn: AlertTriangle,
    success: CheckCircle2,
  };
  const Icon = icons[type];
  return (
    <div
      className={`flex items-start gap-2.5 text-xs border rounded-lg p-3.5 leading-relaxed ${styles[type]}`}
    >
      <Icon className="w-4 h-4 mt-0.5 shrink-0" />
      <div>{children}</div>
    </div>
  );
}

/* ─────────────────────────────────────────────
   Collapsible Section
   ───────────────────────────────────────────── */

function Collapsible({
  title,
  icon: Icon,
  children,
  defaultOpen = false,
}: {
  title: string;
  icon: React.ElementType;
  children: React.ReactNode;
  defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);
  const contentRef = useRef<HTMLDivElement>(null);
  const [height, setHeight] = useState(defaultOpen ? "auto" : "0px");

  useEffect(() => {
    if (contentRef.current) {
      setHeight(open ? `${contentRef.current.scrollHeight}px` : "0px");
    }
  }, [open]);

  return (
    <div className="border border-[#1a1a1a] rounded-xl overflow-hidden hover:border-[#282828] transition-colors">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-3 px-5 py-4 text-left hover:bg-[#0d0d0d] transition-colors"
      >
        <div className="w-8 h-8 rounded-lg bg-[#1DB954]/10 flex items-center justify-center shrink-0">
          <Icon className="w-4 h-4 text-[#1DB954]" />
        </div>
        <span className="text-sm font-semibold text-white flex-1">
          {title}
        </span>
        <ChevronDown
          className={`w-4 h-4 text-[#666] transition-transform duration-200 ${
            open ? "rotate-180" : ""
          }`}
        />
      </button>
      <div
        style={{ height }}
        className="overflow-hidden transition-[height] duration-300 ease-out"
      >
        <div ref={contentRef} className="px-5 pb-5 pt-1 space-y-4">
          {children}
        </div>
      </div>
    </div>
  );
}

/* ─────────────────────────────────────────────
   Side Nav
   ───────────────────────────────────────────── */

const NAV_ITEMS = [
  { id: "overview", title: "Overview" },
  { id: "architecture", title: "Architecture" },
  { id: "providers", title: "GPU Providers" },
  { id: "setup-runpod", title: "RunPod Setup" },
  { id: "setup-vastai", title: "Vast.ai Setup" },
  { id: "setup-colab", title: "Google Colab" },
  { id: "setup-custom", title: "Custom Farm" },
  { id: "autoscaler", title: "Autoscaler" },
  { id: "worker-protocol", title: "Worker Protocol" },
  { id: "model-deploy", title: "Model Deployment" },
  { id: "monitoring", title: "Monitoring" },
  { id: "security", title: "Security" },
  { id: "troubleshooting", title: "Troubleshooting" },
];

function SideNav({
  activeId,
  onSelect,
}: {
  activeId: string;
  onSelect: (id: string) => void;
}) {
  return (
    <nav className="space-y-0.5">
      {NAV_ITEMS.map((s) => (
        <button
          key={s.id}
          onClick={() => onSelect(s.id)}
          className={`w-full text-left px-3 py-1.5 rounded-md text-[13px] transition-all duration-150 ${
            activeId === s.id
              ? "text-[#1DB954] bg-[#1DB954]/8 font-medium"
              : "text-[#808080] hover:text-[#b3b3b3] hover:bg-[#111]"
          }`}
        >
          {s.title}
        </button>
      ))}
    </nav>
  );
}

/* ─────────────────────────────────────────────
   Main Page
   ───────────────────────────────────────────── */

export default function GpuFarmPage() {
  const [activeSection, setActiveSection] = useState("overview");

  const scrollToSection = (id: string) => {
    setActiveSection(id);
    const el = document.getElementById(`section-${id}`);
    if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            setActiveSection(entry.target.id.replace("section-", ""));
          }
        }
      },
      { rootMargin: "-80px 0px -70% 0px", threshold: 0 }
    );
    document
      .querySelectorAll("[id^='section-']")
      .forEach((s) => observer.observe(s));
    return () => observer.disconnect();
  }, []);

  return (
    <div className="min-h-screen bg-black -mx-4 sm:-mx-6 lg:-mx-8 -mt-8 px-0">
      {/* ── Header ── */}
      <header className="relative border-b border-[#1a1a1a] overflow-hidden">
        <div className="absolute inset-0 -z-10">
          <div className="absolute top-0 right-1/4 w-[500px] h-[500px] bg-[#1DB954]/4 rounded-full blur-[150px]" />
          <div className="absolute bottom-0 left-1/3 w-80 h-80 bg-purple-500/3 rounded-full blur-[120px]" />
        </div>

        <div className="max-w-7xl mx-auto px-6 py-16 sm:py-20">
          <div className="flex items-center gap-2 text-[#1DB954] text-sm font-mono tracking-wider mb-4">
            <Server className="w-4 h-4" />
            <span>GPU Farm Integration</span>
          </div>
          <h1 className="text-4xl sm:text-5xl font-bold tracking-tight text-white mb-4">
            GPU Farm{" "}
            <span className="bg-gradient-to-r from-[#1DB954] to-[#1ed760] bg-clip-text text-transparent">
              Integration Guide
            </span>
          </h1>
          <p className="text-[#808080] text-lg max-w-2xl leading-relaxed">
            Полная инструкция по интеграции с фермой видеокарт: поднятие
            инстансов по запросу, автоматическое развертывание модели, генерация
            треков и масштабирование.
          </p>

          <div className="flex flex-wrap items-center gap-4 mt-8">
            {[
              { label: "RunPod", color: "text-purple-400" },
              { label: "Vast.ai", color: "text-blue-400" },
              { label: "Google Colab", color: "text-amber-400" },
              { label: "Custom Farm", color: "text-emerald-400" },
            ].map((p) => (
              <span
                key={p.label}
                className={`${p.color} bg-white/5 border border-white/10 rounded-full px-3 py-1 text-xs font-mono`}
              >
                {p.label}
              </span>
            ))}
          </div>
        </div>
      </header>

      {/* ── Body ── */}
      <div className="max-w-7xl mx-auto flex gap-0">
        {/* Sidebar */}
        <aside className="hidden lg:block w-56 shrink-0 border-r border-[#111]">
          <div className="sticky top-20 py-8 px-4">
            <div className="text-[11px] uppercase tracking-widest text-[#555] font-semibold mb-3 px-3">
              On this page
            </div>
            <SideNav activeId={activeSection} onSelect={scrollToSection} />
          </div>
        </aside>

        {/* Main content */}
        <main className="flex-1 min-w-0 px-6 sm:px-10 py-12 space-y-20">
          {/* ═══════════════════════════════════════════
              OVERVIEW
              ═══════════════════════════════════════════ */}
          <section id="section-overview" className="space-y-6">
            <h2 className="text-2xl font-bold text-white flex items-center gap-3">
              <Zap className="w-5 h-5 text-[#1DB954]" />
              Overview
            </h2>

            <p className="text-sm text-[#b3b3b3] leading-relaxed">
              Lofty поддерживает интеграцию с GPU-фермами для генерации музыки.
              Система спроектирована по принципу{" "}
              <strong className="text-white">
                &ldquo;поднятие по запросу&rdquo;
              </strong>{" "}
              (on-demand provisioning): GPU-инстансы автоматически создаются
              когда в очереди появляются задачи, модель разворачивается на
              инстансе, трек генерируется и результат возвращается клиенту. После
              простоя инстанс автоматически уничтожается.
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
              {[
                {
                  icon: Play,
                  title: "On-Demand",
                  desc: "GPU поднимается только когда есть задача в очереди",
                },
                {
                  icon: Layers,
                  title: "Auto-Deploy",
                  desc: "Модель ACE-Step/YuE автоматически загружается на инстанс",
                },
                {
                  icon: RefreshCw,
                  title: "Autoscale",
                  desc: "Масштабирование 0→N инстансов по глубине очереди",
                },
                {
                  icon: Square,
                  title: "Auto-Teardown",
                  desc: "Idle инстансы автоматически уничтожаются (default: 5 min)",
                },
              ].map((item) => (
                <div
                  key={item.title}
                  className="bg-[#0a0a0a] border border-[#1a1a1a] rounded-xl p-4 hover:border-[#282828] transition-colors"
                >
                  <item.icon className="w-4 h-4 text-[#1DB954] mb-2" />
                  <h3 className="text-xs font-semibold text-white mb-0.5">
                    {item.title}
                  </h3>
                  <p className="text-[11px] text-[#666] leading-relaxed">
                    {item.desc}
                  </p>
                </div>
              ))}
            </div>

            <div className="bg-[#0a0a0a] border border-[#1a1a1a] rounded-xl p-6">
              <h3 className="text-sm font-semibold text-white mb-3">
                Жизненный цикл GPU-инстанса
              </h3>
              <div className="flex flex-wrap items-center gap-2 text-sm text-[#b3b3b3]">
                {[
                  "Задача в очереди",
                  "Autoscaler: spin-up",
                  "Provisioner API",
                  "Instance PENDING",
                  "Docker pull",
                  "Model download",
                  "Instance RUNNING",
                  "Claim job",
                  "GPU inference",
                  "Upload result → S3",
                  "Idle timeout",
                  "Autoscaler: tear-down",
                  "TERMINATED",
                ].map((step, i, arr) => (
                  <span key={`${step}-${i}`} className="flex items-center gap-2">
                    <span className="bg-[#181818] border border-[#282828] rounded-md px-2.5 py-1 text-[11px] font-mono whitespace-nowrap">
                      {step}
                    </span>
                    {i < arr.length - 1 && (
                      <ArrowRight className="w-3 h-3 text-[#333] shrink-0" />
                    )}
                  </span>
                ))}
              </div>
            </div>
          </section>

          {/* ═══════════════════════════════════════════
              ARCHITECTURE
              ═══════════════════════════════════════════ */}
          <section id="section-architecture" className="space-y-6">
            <h2 className="text-2xl font-bold text-white flex items-center gap-3">
              <Network className="w-5 h-5 text-[#1DB954]" />
              Architecture
            </h2>

            <p className="text-sm text-[#b3b3b3] leading-relaxed">
              Архитектура GPU-фермы построена на трёх уровнях:{" "}
              <strong className="text-white">Provisioner</strong> (создание
              инстансов),{" "}
              <strong className="text-white">Worker Protocol</strong>{" "}
              (коммуникация с инстансами) и{" "}
              <strong className="text-white">Autoscaler</strong>{" "}
              (автомасштабирование).
            </p>

            <div className="bg-[#0a0a0a] border border-[#1a1a1a] rounded-xl p-6 font-mono text-xs text-[#b3b3b3] overflow-x-auto">
              <pre>{`┌─────────────────────────────────────────────────────────────────────────────┐
│                              LOFTY PLATFORM                                 │
│                                                                             │
│  ┌──────────┐    ┌──────────────┐    ┌─────────────┐    ┌───────────────┐   │
│  │ Frontend  │───▶│  FastAPI      │───▶│  Redis      │───▶│  PostgreSQL   │   │
│  │ Next.js   │    │  REST API    │    │  Queue+Cache│    │  Database     │   │
│  └──────────┘    └──────┬───────┘    └──────┬──────┘    └───────────────┘   │
│                         │                   │                               │
│                         ▼                   │                               │
│                  ┌──────────────┐            │                               │
│                  │  Autoscaler  │◀───────────┘  Celery Beat (every 30s)      │
│                  │  check_and_  │                                            │
│                  │  scale()     │                                            │
│                  └──────┬───────┘                                            │
│                         │                                                   │
│              ┌──────────┼──────────┐                                        │
│              ▼          ▼          ▼                                         │
│     ┌────────────┐ ┌──────────┐ ┌──────────────┐                            │
│     │   RunPod   │ │ Vast.ai  │ │ Custom Farm  │  GPU Provisioners          │
│     │   Cloud    │ │  Cloud   │ │  On-Premise  │                            │
│     └─────┬──────┘ └────┬─────┘ └──────┬───────┘                            │
│           │             │              │                                    │
└───────────┼─────────────┼──────────────┼────────────────────────────────────┘
            │             │              │
            ▼             ▼              ▼
     ┌─────────────────────────────────────────────┐
     │            GPU WORKER INSTANCES              │
     │                                              │
     │  ┌─────────────────────────────────────┐     │
     │  │  Docker: lofty-worker:gpu            │     │
     │  │  ┌───────────┐  ┌────────────────┐  │     │
     │  │  │ Celery    │  │ ACE-Step 1.5   │  │     │
     │  │  │ Worker    │  │ / YuE Model    │  │     │
     │  │  │ (solo)    │  │ (PyTorch+CUDA) │  │     │
     │  │  └─────┬─────┘  └────────┬───────┘  │     │
     │  │        │                 │           │     │
     │  │        ▼                 ▼           │     │
     │  │  ┌──────────┐    ┌────────────┐     │     │
     │  │  │  Redis   │    │  MinIO/S3  │     │     │
     │  │  │  (broker)│    │  (storage) │     │     │
     │  │  └──────────┘    └────────────┘     │     │
     │  └─────────────────────────────────────┘     │
     │                                              │
     │  Worker Protocol:                            │
     │  Mode A: Celery (direct Redis connection)    │
     │  Mode B: HTTP polling (/api/v1/worker/*)     │
     └──────────────────────────────────────────────┘`}</pre>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="bg-[#0a0a0a] border border-[#1a1a1a] rounded-xl p-5">
                <h3 className="text-sm font-semibold text-white mb-2 flex items-center gap-2">
                  <GitBranch className="w-4 h-4 text-[#1DB954]" />
                  Mode A: Celery Worker
                </h3>
                <p className="text-xs text-[#808080] leading-relaxed mb-3">
                  Инстанс подключается к Redis напрямую как Celery worker.
                  Забирает задачи из очереди <code className="text-[#b3b3b3]">gpu</code>,
                  пишет результаты в Redis и S3. Подходит для cloud-провайдеров
                  (RunPod, Vast.ai) где инстанс имеет прямой доступ к Redis.
                </p>
                <div className="flex flex-wrap gap-1">
                  {["RunPod", "Vast.ai", "On-Premise"].map((t) => (
                    <span
                      key={t}
                      className="text-[10px] text-[#1DB954] bg-[#1DB954]/10 rounded px-1.5 py-0.5"
                    >
                      {t}
                    </span>
                  ))}
                </div>
              </div>
              <div className="bg-[#0a0a0a] border border-[#1a1a1a] rounded-xl p-5">
                <h3 className="text-sm font-semibold text-white mb-2 flex items-center gap-2">
                  <Globe className="w-4 h-4 text-[#1DB954]" />
                  Mode B: HTTP Polling
                </h3>
                <p className="text-xs text-[#808080] leading-relaxed mb-3">
                  Инстанс опрашивает API через HTTP:{" "}
                  <code className="text-[#b3b3b3]">GET /worker/next-job</code>,
                  отправляет результат через{" "}
                  <code className="text-[#b3b3b3]">
                    POST /worker/&#123;id&#125;/result
                  </code>
                  . Не требует прямого доступа к Redis/DB. Подходит для Colab и
                  ограниченных сред.
                </p>
                <div className="flex flex-wrap gap-1">
                  {["Google Colab", "Kaggle", "Restricted Network"].map((t) => (
                    <span
                      key={t}
                      className="text-[10px] text-amber-400 bg-amber-400/10 rounded px-1.5 py-0.5"
                    >
                      {t}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          </section>

          {/* ═══════════════════════════════════════════
              GPU PROVIDERS
              ═══════════════════════════════════════════ */}
          <section id="section-providers" className="space-y-6">
            <h2 className="text-2xl font-bold text-white flex items-center gap-3">
              <Cloud className="w-5 h-5 text-[#1DB954]" />
              GPU Providers — Сравнение
            </h2>

            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-[#1a1a1a]">
                    {[
                      "Provider",
                      "GPU",
                      "VRAM",
                      "$/час",
                      "Spin-up",
                      "Протокол",
                      "Auto-scale",
                    ].map((h) => (
                      <th
                        key={h}
                        className="text-left py-3 pr-4 text-[11px] uppercase tracking-wider text-[#555] font-semibold"
                      >
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="text-[#b3b3b3]">
                  {[
                    ["RunPod", "A40 / A100 / RTX 4090 / T4", "16-80 GB", "$0.20-1.64", "~30s", "Celery", "Yes"],
                    ["Vast.ai", "RTX 3090 / 4090 / A100", "24-80 GB", "$0.15-1.20", "~60s", "Celery", "Yes"],
                    ["Google Colab", "T4 (free) / A100 (Pro)", "15-40 GB", "Free-$0.50", "~10s", "HTTP", "No"],
                    ["Custom Farm", "Any NVIDIA GPU", "8+ GB", "Custom", "~5s", "Celery", "Yes"],
                  ].map(([provider, gpu, vram, cost, spin, proto, auto]) => (
                    <tr key={provider} className="border-b border-[#111]">
                      <td className="py-3 pr-4 text-white font-medium text-xs">
                        {provider}
                      </td>
                      <td className="py-3 pr-4 text-xs font-mono">{gpu}</td>
                      <td className="py-3 pr-4 text-xs">{vram}</td>
                      <td className="py-3 pr-4 text-xs text-[#1DB954] font-mono">
                        {cost}
                      </td>
                      <td className="py-3 pr-4 text-xs">{spin}</td>
                      <td className="py-3 pr-4 text-xs font-mono">{proto}</td>
                      <td className="py-3 pr-4 text-xs">
                        {auto === "Yes" ? (
                          <CheckCircle2 className="w-3.5 h-3.5 text-[#1DB954]" />
                        ) : (
                          <span className="text-[#555]">Manual</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <InfoBox type="info">
              <strong>Рекомендация:</strong> Для production используйте RunPod
              (A40 — оптимальное соотношение цена/производительность). Для
              тестирования — Google Colab (бесплатно, T4). Для enterprise —
              собственная ферма с Vast.ai marketplace.
            </InfoBox>
          </section>

          {/* ═══════════════════════════════════════════
              SETUP: RUNPOD
              ═══════════════════════════════════════════ */}
          <section id="section-setup-runpod" className="space-y-6">
            <h2 className="text-2xl font-bold text-white flex items-center gap-3">
              <Server className="w-5 h-5 text-purple-400" />
              RunPod — Настройка
            </h2>

            <p className="text-sm text-[#b3b3b3] leading-relaxed">
              RunPod — рекомендуемый провайдер для production. Поддерживает
              автоматическое создание/удаление подов через API.
            </p>

            {/* Step 1 */}
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <StepNumber n={1} />
                <span className="text-sm font-semibold text-white">
                  Получите API ключ RunPod
                </span>
              </div>
              <p className="text-xs text-[#808080] ml-9">
                Зарегистрируйтесь на runpod.io → Settings → API Keys → Create
                API Key. Скопируйте ключ вида{" "}
                <code className="text-[#b3b3b3]">rp_xxxxxxxx</code>.
              </p>
            </div>

            {/* Step 2 */}
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <StepNumber n={2} />
                <span className="text-sm font-semibold text-white">
                  Соберите Docker-образ для GPU-worker
                </span>
              </div>
              <CodeBlock
                title="docker build"
                code={`# Сборка GPU worker image
docker build -f docker/worker-gpu.Dockerfile -t lofty-worker:gpu .

# Push в Docker Hub / registry (RunPod тянет образ оттуда)
docker tag lofty-worker:gpu your-registry/lofty-worker:gpu
docker push your-registry/lofty-worker:gpu`}
              />
              <InfoBox type="warn">
                Образ включает CUDA 12.1, PyTorch, ACE-Step 1.5, все
                зависимости. Размер ~8-10 GB. Первый pull на RunPod занимает
                ~2-3 минуты.
              </InfoBox>
            </div>

            {/* Step 3 */}
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <StepNumber n={3} />
                <span className="text-sm font-semibold text-white">
                  Настройте переменные окружения
                </span>
              </div>
              <CodeBlock
                title=".env"
                code={`# GPU Backend
GPU_BACKEND=cloud
CLOUD_GPU_API_KEY=rp_YOUR_RUNPOD_API_KEY
CLOUD_GPU_DOCKER_IMAGE=your-registry/lofty-worker:gpu

# Autoscaler
AUTOSCALER_ENABLED=true
AUTOSCALER_MIN_INSTANCES=0      # 0 = scale to zero when idle
AUTOSCALER_MAX_INSTANCES=5      # max concurrent GPU workers
AUTOSCALER_IDLE_TIMEOUT=300     # 5 min idle → tear down

# Redis (должен быть доступен из RunPod)
REDIS_URL=rediss://default:password@your-redis.upstash.io:6379/0
CELERY_BROKER_URL=rediss://default:password@your-redis.upstash.io:6379/1
CELERY_RESULT_BACKEND=rediss://default:password@your-redis.upstash.io:6379/2

# S3 Storage (должен быть доступен из RunPod)
STORAGE_ENDPOINT=s3.amazonaws.com
STORAGE_ACCESS_KEY=AKIA...
STORAGE_SECRET_KEY=...
STORAGE_BUCKET=lofty-tracks
STORAGE_USE_SSL=true`}
              />
            </div>

            {/* Step 4 */}
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <StepNumber n={4} />
                <span className="text-sm font-semibold text-white">
                  Активируйте через API или UI
                </span>
              </div>
              <CodeBlock
                title="curl — установка backend"
                code={`# Переключить backend на cloud (RunPod)
curl -X PUT https://your-api.com/api/v1/gpu/settings \\
  -H "Authorization: Bearer $CLERK_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{
    "backend": "cloud",
    "autoscaler_enabled": true,
    "autoscaler_max_instances": 5,
    "autoscaler_idle_timeout": 300
  }'

# Проверить статус
curl -H "Authorization: Bearer $CLERK_TOKEN" \\
  https://your-api.com/api/v1/gpu/status

# Ручной spin-up (для тестирования)
curl -X POST -H "Authorization: Bearer $CLERK_TOKEN" \\
  "https://your-api.com/api/v1/gpu/instances/spin-up?gpu_type=a40"`}
              />
            </div>

            <InfoBox type="success">
              После настройки: отправьте задачу на генерацию → Autoscaler
              обнаружит задачу в очереди → RunPod API создаст под → модель
              загрузится → трек сгенерируется → под уничтожится через 5 минут
              простоя.
            </InfoBox>
          </section>

          {/* ═══════════════════════════════════════════
              SETUP: VAST.AI
              ═══════════════════════════════════════════ */}
          <section id="section-setup-vastai" className="space-y-6">
            <h2 className="text-2xl font-bold text-white flex items-center gap-3">
              <Server className="w-5 h-5 text-blue-400" />
              Vast.ai — Настройка
            </h2>

            <p className="text-sm text-[#b3b3b3] leading-relaxed">
              Vast.ai — marketplace GPU-инстансов. Дешевле RunPod для spot instances,
              но менее предсказуемое время spin-up. Расширьте{" "}
              <code className="text-[#1DB954]">CloudProvisioner</code> для работы
              с Vast.ai API.
            </p>

            <CodeBlock
              title="src/lofty/infra/gpu_provisioner.py — VastAI extension"
              code={`class VastAiProvisioner(GpuProvisioner):
    """Vast.ai marketplace provisioner.

    API docs: https://vast.ai/docs/rest/introduction
    """

    def __init__(self, api_key: str, docker_image: str):
        self._api_key = api_key
        self._docker_image = docker_image
        self._instances: dict[str, GpuInstance] = {}

    async def spin_up(self, gpu_type: str = "auto") -> GpuInstance:
        import httpx

        # 1. Search for cheapest available offer
        async with httpx.AsyncClient() as client:
            offers = await client.get(
                "https://console.vast.ai/api/v0/bundles/",
                headers={"Authorization": f"Bearer {self._api_key}"},
                params={
                    "q": json.dumps({
                        "gpu_ram": {"gte": 15000},  # min 15GB VRAM
                        "rentable": True,
                        "reliability2": {"gte": 0.95},
                        "order": [["dph_total", "asc"]],
                        "limit": 1,
                    })
                },
            )
            best = offers.json()["offers"][0]

        # 2. Create instance
        async with httpx.AsyncClient() as client:
            resp = await client.put(
                f"https://console.vast.ai/api/v0/asks/{best['id']}/",
                headers={"Authorization": f"Bearer {self._api_key}"},
                json={
                    "client_id": "me",
                    "image": self._docker_image,
                    "disk": 20,
                    "env": {
                        "CELERY_BROKER_URL": settings.celery_broker_url,
                        "REDIS_URL": settings.redis_url,
                        "STORAGE_ENDPOINT": settings.storage_endpoint,
                        # ... other env vars
                    },
                    "onstart": "celery -A lofty.worker.celery_app worker "
                               "--pool=solo --queues gpu --concurrency 1",
                },
            )

        instance_id = resp.json().get("new_contract")
        # ... create GpuInstance and return

    async def tear_down(self, instance_id: str) -> None:
        import httpx
        async with httpx.AsyncClient() as client:
            await client.delete(
                f"https://console.vast.ai/api/v0/instances/{instance_id}/",
                headers={"Authorization": f"Bearer {self._api_key}"},
            )
        # cleanup ...`}
            />

            <CodeBlock
              title=".env"
              code={`GPU_BACKEND=cloud
CLOUD_GPU_API_KEY=your_vastai_api_key
CLOUD_GPU_DOCKER_IMAGE=your-registry/lofty-worker:gpu`}
            />
          </section>

          {/* ═══════════════════════════════════════════
              SETUP: COLAB
              ═══════════════════════════════════════════ */}
          <section id="section-setup-colab" className="space-y-6">
            <h2 className="text-2xl font-bold text-white flex items-center gap-3">
              <MonitorSpeaker className="w-5 h-5 text-amber-400" />
              Google Colab — Бесплатный GPU
            </h2>

            <p className="text-sm text-[#b3b3b3] leading-relaxed">
              Colab работает через HTTP Polling (Mode B) — не требует прямого
              доступа к Redis. Идеально для тестирования и демо.
            </p>

            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <StepNumber n={1} />
                <span className="text-sm font-semibold text-white">
                  Настройте backend = &quot;google&quot;
                </span>
              </div>
              <CodeBlock
                title=".env"
                code={`GPU_BACKEND=google
WORKER_API_KEY=your-secret-worker-key-here`}
              />
            </div>

            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <StepNumber n={2} />
                <span className="text-sm font-semibold text-white">
                  Получите сниппет для Colab
                </span>
              </div>
              <CodeBlock
                code={`# Получить Colab setup snippet
curl -H "Authorization: Bearer $CLERK_TOKEN" \\
  https://your-api.com/api/v1/gpu/status

# В ответе будет поле colab_setup_snippet — скопируйте его в Colab notebook`}
              />
            </div>

            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <StepNumber n={3} />
                <span className="text-sm font-semibold text-white">
                  Запустите в Google Colab
                </span>
              </div>
              <CodeBlock
                title="Google Colab Cell"
                code={`# === Lofty GPU Worker — Google Colab Setup ===
# Runtime → Change runtime type → T4 GPU

import os
os.environ["CELERY_BROKER_URL"] = "rediss://...your-redis..."
os.environ["CELERY_RESULT_BACKEND"] = "rediss://...your-redis..."
os.environ["REDIS_URL"] = "rediss://...your-redis..."
os.environ["STORAGE_ENDPOINT"] = "s3.amazonaws.com"
os.environ["STORAGE_ACCESS_KEY"] = "AKIA..."
os.environ["STORAGE_SECRET_KEY"] = "..."
os.environ["STORAGE_BUCKET"] = "lofty-tracks"
os.environ["STORAGE_USE_SSL"] = "true"
os.environ["MODEL_DEVICE"] = "cuda"
os.environ["MOCK_GPU"] = "false"

# Install dependencies
!pip install -q celery[redis] redis boto3 scipy structlog pydantic-settings
!pip install -q torch torchaudio --index-url https://download.pytorch.org/whl/cu121
!pip install -q transformers accelerate peft soundfile
!apt-get install -y -qq ffmpeg
!git clone --depth 1 https://github.com/ace-step/ACE-Step-1.5.git /content/ACE-Step-1.5
!pip install -q -e /content/ACE-Step-1.5
!pip install -q git+https://github.com/YOUR_ORG/lofty.git

# Heartbeat (keeps worker visible to backend)
import threading, time, redis as _redis
def _heartbeat():
    r = _redis.from_url(os.environ["REDIS_URL"])
    while True:
        r.setex("worker_heartbeat:colab-manual", 60, "alive")
        time.sleep(30)
threading.Thread(target=_heartbeat, daemon=True).start()

# Start Celery worker
!celery -A lofty.worker.celery_app worker \\
  --pool=solo --queues gpu,training --concurrency 1 --loglevel info`}
              />
            </div>

            <InfoBox type="warn">
              Google Colab Free: T4 GPU (15 GB VRAM), сессия до 12 часов.
              ACE-Step 1.5 генерирует ~30s трек за ~45 секунд на T4. Colab Pro
              даёт A100 и более длительные сессии.
            </InfoBox>
          </section>

          {/* ═══════════════════════════════════════════
              SETUP: CUSTOM FARM
              ═══════════════════════════════════════════ */}
          <section id="section-setup-custom" className="space-y-6">
            <h2 className="text-2xl font-bold text-white flex items-center gap-3">
              <HardDrive className="w-5 h-5 text-emerald-400" />
              Custom GPU Farm — On-Premise
            </h2>

            <p className="text-sm text-[#b3b3b3] leading-relaxed">
              Собственная ферма GPU-серверов. Воркеры подключаются к общему Redis
              и S3 хранилищу напрямую. Максимальная производительность, полный
              контроль.
            </p>

            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <StepNumber n={1} />
                <span className="text-sm font-semibold text-white">
                  Подготовьте GPU-сервер
                </span>
              </div>
              <CodeBlock
                title="Требования к GPU-серверу"
                code={`# Минимальные требования:
# - NVIDIA GPU с 8+ GB VRAM (RTX 3060+ / T4+)
# - NVIDIA Driver 525+
# - Docker с nvidia-container-toolkit
# - Сетевой доступ к Redis и S3/MinIO

# Установка nvidia-container-toolkit (Ubuntu)
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey \\
  | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg

curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list \\
  | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' \\
  | sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

sudo apt-get update && sudo apt-get install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker

# Проверка
docker run --rm --gpus all nvidia/cuda:12.1.1-runtime-ubuntu22.04 nvidia-smi`}
              />
            </div>

            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <StepNumber n={2} />
                <span className="text-sm font-semibold text-white">
                  Запустите GPU worker
                </span>
              </div>
              <CodeBlock
                title="docker run"
                code={`# Запуск GPU worker на каждом GPU-сервере
docker run -d \\
  --name lofty-gpu-worker \\
  --gpus all \\
  --restart unless-stopped \\
  -e CELERY_BROKER_URL=redis://redis-host:6379/1 \\
  -e CELERY_RESULT_BACKEND=redis://redis-host:6379/2 \\
  -e REDIS_URL=redis://redis-host:6379/0 \\
  -e STORAGE_ENDPOINT=minio-host:9000 \\
  -e STORAGE_ACCESS_KEY=minioadmin \\
  -e STORAGE_SECRET_KEY=minioadmin \\
  -e STORAGE_BUCKET=lofty-tracks \\
  -e STORAGE_USE_SSL=false \\
  -e MODEL_DEVICE=cuda \\
  -e MOCK_GPU=false \\
  -e ACE_STEP_MODEL_PATH=ACE-Step/Ace-Step1.5 \\
  -e ACE_STEP_CACHE_DIR=/app/ace_model_cache \\
  -v lofty_model_cache:/app/ace_model_cache \\
  lofty-worker:gpu`}
              />
            </div>

            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <StepNumber n={3} />
                <span className="text-sm font-semibold text-white">
                  Docker Compose для фермы (multi-GPU)
                </span>
              </div>
              <CodeBlock
                title="docker-compose.gpu-farm.yml"
                code={`version: "3.8"
services:
  gpu-worker-1:
    image: lofty-worker:gpu
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              device_ids: ["0"]
              capabilities: [gpu]
    environment:
      CELERY_BROKER_URL: redis://redis-host:6379/1
      CELERY_RESULT_BACKEND: redis://redis-host:6379/2
      REDIS_URL: redis://redis-host:6379/0
      STORAGE_ENDPOINT: minio-host:9000
      STORAGE_ACCESS_KEY: minioadmin
      STORAGE_SECRET_KEY: minioadmin
      STORAGE_BUCKET: lofty-tracks
      MODEL_DEVICE: cuda
      MOCK_GPU: "false"
    volumes:
      - model_cache_1:/app/ace_model_cache
    restart: unless-stopped

  gpu-worker-2:
    image: lofty-worker:gpu
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              device_ids: ["1"]
              capabilities: [gpu]
    environment:
      CELERY_BROKER_URL: redis://redis-host:6379/1
      CELERY_RESULT_BACKEND: redis://redis-host:6379/2
      REDIS_URL: redis://redis-host:6379/0
      STORAGE_ENDPOINT: minio-host:9000
      STORAGE_ACCESS_KEY: minioadmin
      STORAGE_SECRET_KEY: minioadmin
      STORAGE_BUCKET: lofty-tracks
      MODEL_DEVICE: cuda
      MOCK_GPU: "false"
    volumes:
      - model_cache_2:/app/ace_model_cache
    restart: unless-stopped

volumes:
  model_cache_1:
  model_cache_2:`}
              />
            </div>

            <InfoBox type="info">
              Для multi-node ферм: каждый GPU-сервер запускает по 1 worker на
              GPU. Все воркеры подключены к одному Redis брокеру. Celery
              автоматически распределяет задачи между воркерами.
            </InfoBox>
          </section>

          {/* ═══════════════════════════════════════════
              AUTOSCALER
              ═══════════════════════════════════════════ */}
          <section id="section-autoscaler" className="space-y-6">
            <h2 className="text-2xl font-bold text-white flex items-center gap-3">
              <BarChart3 className="w-5 h-5 text-[#1DB954]" />
              Autoscaler
            </h2>

            <p className="text-sm text-[#b3b3b3] leading-relaxed">
              Autoscaler работает как Celery Beat задача каждые 30 секунд.
              Мониторит глубину очереди Redis и управляет количеством
              GPU-инстансов.
            </p>

            <div className="bg-[#0a0a0a] border border-[#1a1a1a] rounded-xl p-6 font-mono text-xs text-[#b3b3b3] overflow-x-auto">
              <pre>{`Алгоритм масштабирования:

┌─────────────────────────────────────────────────────────────┐
│  Каждые 30 секунд (Celery Beat):                            │
│                                                             │
│  1. Прочитать queue_depth = LLEN("gpu") из Redis            │
│  2. Получить список инстансов от Provisioner                │
│                                                             │
│  SCALE UP:                                                  │
│    IF queue_depth > 0                                       │
│       AND pending_instances == 0                            │
│       AND total_instances < max_instances                   │
│       AND cooldown_elapsed (60s)                            │
│    THEN → provisioner.spin_up()                             │
│                                                             │
│  SCALE DOWN:                                                │
│    IF queue_depth == 0                                      │
│       AND running_instances > min_instances                 │
│       AND oldest_instance.idle_time > idle_timeout          │
│       AND cooldown_elapsed (60s)                            │
│    THEN → provisioner.tear_down(oldest)                     │
└─────────────────────────────────────────────────────────────┘`}</pre>
            </div>

            <div className="bg-[#0a0a0a] border border-[#1a1a1a] rounded-lg p-4 space-y-2">
              <h4 className="text-xs font-semibold text-white uppercase tracking-wider mb-2">
                Параметры конфигурации
              </h4>
              {[
                ["AUTOSCALER_ENABLED", "true/false", "Включить/выключить"],
                ["AUTOSCALER_MIN_INSTANCES", "0", "Минимум инстансов (0 = scale to zero)"],
                ["AUTOSCALER_MAX_INSTANCES", "3", "Максимум одновременных инстансов"],
                ["AUTOSCALER_IDLE_TIMEOUT", "300", "Секунд простоя до уничтожения"],
              ].map(([key, def, desc]) => (
                <div
                  key={key}
                  className="flex items-center justify-between py-1"
                >
                  <code className="text-xs text-[#1DB954] font-mono">
                    {key}
                  </code>
                  <span className="text-[11px] text-[#808080]">
                    {desc}{" "}
                    <span className="text-[#555]">(default: {def})</span>
                  </span>
                </div>
              ))}
            </div>
          </section>

          {/* ═══════════════════════════════════════════
              WORKER PROTOCOL
              ═══════════════════════════════════════════ */}
          <section id="section-worker-protocol" className="space-y-6">
            <h2 className="text-2xl font-bold text-white flex items-center gap-3">
              <Radio className="w-5 h-5 text-[#1DB954]" />
              Worker Protocol
            </h2>

            <div className="space-y-4">
              <Collapsible
                title="Mode A: Celery Worker (рекомендуется)"
                icon={GitBranch}
                defaultOpen={true}
              >
                <p className="text-xs text-[#808080] leading-relaxed">
                  Worker подключается к Redis как Celery consumer. Задачи
                  забираются автоматически из очередей{" "}
                  <code className="text-[#b3b3b3]">gpu</code> и{" "}
                  <code className="text-[#b3b3b3]">training</code>.
                </p>
                <CodeBlock
                  code={`# Celery worker startup (внутри Docker)
celery -A lofty.worker.celery_app worker \\
  --pool=solo \\
  --queues gpu,training \\
  --concurrency 1 \\
  --loglevel info

# Процесс:
# 1. Worker стартует → вызывается @worker_ready → preload_engines()
# 2. ACE-Step модель загружается в VRAM (~4 GB)
# 3. Worker слушает очередь "gpu" в Redis
# 4. Когда появляется задача generate_music:
#    a. Забирает задачу (ack_late = true)
#    b. Генерирует аудио через ACE-Step/YuE
#    c. Конвертирует WAV → MP3 (ffmpeg)
#    d. Загружает результат в S3 (MinIO)
#    e. Пишет результат в Redis (job_result:{id})
#    f. Обновляет прогресс в Redis (job_progress:{id})
# 5. API-сервер синхронизирует результат из Redis в PostgreSQL`}
                />
              </Collapsible>

              <Collapsible
                title="Mode B: HTTP Polling Worker"
                icon={Globe}
              >
                <p className="text-xs text-[#808080] leading-relaxed">
                  Для сред без прямого доступа к Redis (Colab, Kaggle). Worker
                  опрашивает API через HTTP.
                </p>
                <CodeBlock
                  code={`# Цикл HTTP polling worker (псевдокод)
while True:
    # 1. Запросить следующую задачу
    resp = GET /api/v1/worker/next-job
            Headers: Authorization: Bearer <WORKER_API_KEY>

    if resp.status == 204:
        sleep(5)  # нет задач, ждём
        continue

    job = resp.json()

    # 2. Генерация
    audio = generate(job.prompt, job.duration_seconds, ...)

    # 3. Периодически отправлять прогресс
    POST /api/v1/worker/{job_id}/progress
         Body: {"progress": 50}

    # 4. Проверить отмену
    resp = GET /api/v1/worker/{job_id}/cancelled
    if resp.json().cancelled:
        continue

    # 5. Отправить результат
    POST /api/v1/worker/{job_id}/result
         Form: status=completed, duration=30.0, format=wav
         File: audio_file=<binary wav>`}
                />
              </Collapsible>
            </div>
          </section>

          {/* ═══════════════════════════════════════════
              MODEL DEPLOYMENT
              ═══════════════════════════════════════════ */}
          <section id="section-model-deploy" className="space-y-6">
            <h2 className="text-2xl font-bold text-white flex items-center gap-3">
              <Layers className="w-5 h-5 text-[#1DB954]" />
              Развертывание модели на инстансе
            </h2>

            <p className="text-sm text-[#b3b3b3] leading-relaxed">
              Модель автоматически загружается при старте worker. Docker-образ
              включает код, а веса скачиваются из HuggingFace Hub при первом
              запуске (кэшируются на volume).
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="bg-[#0a0a0a] border border-[#1a1a1a] rounded-xl p-5 space-y-3">
                <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                  <Cpu className="w-4 h-4 text-[#1DB954]" />
                  ACE-Step 1.5
                </h3>
                <div className="space-y-1 text-xs text-[#808080]">
                  <div className="flex justify-between">
                    <span>Размер модели</span>
                    <span className="text-white font-mono">~4 GB</span>
                  </div>
                  <div className="flex justify-between">
                    <span>VRAM при inference</span>
                    <span className="text-white font-mono">~6-8 GB</span>
                  </div>
                  <div className="flex justify-between">
                    <span>CPU Offload</span>
                    <span className="text-[#1DB954] font-mono">enabled</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Время загрузки</span>
                    <span className="text-white font-mono">~30-60s</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Генерация 30s трека</span>
                    <span className="text-white font-mono">~45s (T4)</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Max длительность</span>
                    <span className="text-white font-mono">600s (10 min)</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Fine-tuning</span>
                    <span className="text-[#1DB954] font-mono">LoRA / LoKR</span>
                  </div>
                </div>
              </div>

              <div className="bg-[#0a0a0a] border border-[#1a1a1a] rounded-xl p-5 space-y-3">
                <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                  <Cpu className="w-4 h-4 text-amber-400" />
                  YuE (Lyrics-to-Music)
                </h3>
                <div className="space-y-1 text-xs text-[#808080]">
                  <div className="flex justify-between">
                    <span>Размер модели</span>
                    <span className="text-white font-mono">~14 GB (4-bit)</span>
                  </div>
                  <div className="flex justify-between">
                    <span>VRAM при inference</span>
                    <span className="text-white font-mono">~12-15 GB</span>
                  </div>
                  <div className="flex justify-between">
                    <span>4-bit Quantization</span>
                    <span className="text-[#1DB954] font-mono">NF4</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Время загрузки</span>
                    <span className="text-white font-mono">~60-120s</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Генерация 30s</span>
                    <span className="text-white font-mono">~2-3 min (T4)</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Max длительность</span>
                    <span className="text-white font-mono">60s (2 seg)</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Требует</span>
                    <span className="text-amber-400 font-mono">GPU only</span>
                  </div>
                </div>
              </div>
            </div>

            <CodeBlock
              title="Процесс загрузки модели (автоматический)"
              code={`# При старте Celery worker (worker_ready signal):
#
# 1. @worker_ready → preload_engines()
# 2. get_engine("ace-step-1.5")
#    → AceStepEngine(model_path="ACE-Step/Ace-Step1.5", device="cuda")
#    → engine.load()
#       → HuggingFace Hub downloads model weights
#       → Weights cached in ACE_STEP_CACHE_DIR
#       → Model loaded to GPU VRAM
#       → CPU offload for LM/VAE (saves ~4GB VRAM)
#
# 3. Worker начинает обрабатывать задачи из очереди
#
# Кэширование: при повторном запуске модель загружается из кэша (~30s vs ~5min)
# Важно: Docker volume для ace_model_cache сохраняет модель между рестартами

# Переменные окружения для управления моделью:
ACE_STEP_MODEL_PATH=ACE-Step/Ace-Step1.5     # HuggingFace repo ID
ACE_STEP_CACHE_DIR=/app/ace_model_cache       # Путь к кэшу весов
ACE_STEP_CPU_OFFLOAD=true                     # Offload в RAM (~4GB VRAM saved)
ACE_STEP_THINKING_ENABLED=false               # Disable on T4 (OOM risk)
MODEL_DEVICE=cuda                             # "cuda" | "cpu"
MOCK_GPU=false                                # true = no real GPU (dev mode)`}
            />
          </section>

          {/* ═══════════════════════════════════════════
              MONITORING
              ═══════════════════════════════════════════ */}
          <section id="section-monitoring" className="space-y-6">
            <h2 className="text-2xl font-bold text-white flex items-center gap-3">
              <Activity className="w-5 h-5 text-[#1DB954]" />
              Monitoring
            </h2>

            <p className="text-sm text-[#b3b3b3] leading-relaxed">
              Мониторинг GPU-фермы через REST API и Redis.
            </p>

            <CodeBlock
              title="curl — Мониторинг"
              code={`# 1. Общий статус GPU инфраструктуры
curl -H "Authorization: Bearer $TOKEN" \\
  https://api.lofty.com/api/v1/gpu/status
# → backend, status, instances[], total_cost_per_hour

# 2. Health check (без авторизации)
curl https://api.lofty.com/health/ready
# → {ready: true, database: "ok", redis: "ok", storage: "ok"}

# 3. Глубина очереди задач (Redis)
redis-cli -u $REDIS_URL LLEN gpu
# → количество задач ожидающих GPU

# 4. Heartbeat воркеров (Redis)
redis-cli -u $REDIS_URL KEYS "worker_heartbeat:*"
# → список активных воркеров

# 5. Активные задачи
curl -H "Authorization: Bearer $TOKEN" \\
  "https://api.lofty.com/api/v1/jobs?status=running"

# 6. Celery Flower (опционально, для UI мониторинга)
pip install flower
celery -A lofty.worker.celery_app flower --port=5555`}
            />

            <InfoBox type="info">
              Для production рекомендуется настроить Grafana + Prometheus для
              метрик: queue depth, instance count, generation latency, GPU
              utilization, cost per track.
            </InfoBox>
          </section>

          {/* ═══════════════════════════════════════════
              SECURITY
              ═══════════════════════════════════════════ */}
          <section id="section-security" className="space-y-6">
            <h2 className="text-2xl font-bold text-white flex items-center gap-3">
              <Shield className="w-5 h-5 text-[#1DB954]" />
              Security
            </h2>

            <div className="space-y-3 text-sm text-[#b3b3b3]">
              <div className="bg-[#0a0a0a] border border-[#1a1a1a] rounded-xl p-5 space-y-3">
                <h3 className="text-sm font-semibold text-white">
                  Checklist для production
                </h3>
                {[
                  "Redis защищён паролем и TLS (rediss://)",
                  "S3/MinIO с приватным доступом, presigned URLs для скачивания",
                  "WORKER_API_KEY — длинный случайный токен (32+ символов)",
                  "Docker образы хранятся в приватном registry",
                  "Сетевые правила: GPU workers → Redis + S3 only",
                  "Ограничение на размер генерации (max 600s / 10 min)",
                  "Rate limiting на API (10 req/min по умолчанию)",
                  "Celery acks_late=True — задача не теряется при падении worker",
                  "Cleanup stale jobs — каждые 5 минут (Celery Beat)",
                  "Не хранить секреты в Docker image — только env vars",
                ].map((item, i) => (
                  <div key={i} className="flex items-start gap-2">
                    <CheckCircle2 className="w-3.5 h-3.5 text-[#1DB954] mt-0.5 shrink-0" />
                    <span className="text-xs">{item}</span>
                  </div>
                ))}
              </div>
            </div>

            <CodeBlock
              title="Генерация безопасного WORKER_API_KEY"
              code={`# Python
python -c "import secrets; print(secrets.token_urlsafe(48))"

# OpenSSL
openssl rand -base64 48`}
            />
          </section>

          {/* ═══════════════════════════════════════════
              TROUBLESHOOTING
              ═══════════════════════════════════════════ */}
          <section id="section-troubleshooting" className="space-y-6">
            <h2 className="text-2xl font-bold text-white flex items-center gap-3">
              <AlertTriangle className="w-5 h-5 text-amber-400" />
              Troubleshooting
            </h2>

            <div className="space-y-3">
              {[
                {
                  q: "Worker не берёт задачи из очереди",
                  a: "Проверьте: 1) CELERY_BROKER_URL совпадает с API сервером. 2) Worker слушает очередь 'gpu': --queues gpu. 3) Redis доступен: redis-cli -u $REDIS_URL ping. 4) Нет другого worker, который уже забрал задачу.",
                },
                {
                  q: "CUDA out of memory (OOM)",
                  a: "1) ACE-Step: включите ACE_STEP_CPU_OFFLOAD=true. 2) YuE: включите YUE_USE_4BIT=true. 3) Уменьшите duration_seconds. 4) Перезапустите worker (утечка VRAM). 5) Для T4 (15GB): ACE-Step OK, YuE только с 4-bit.",
                },
                {
                  q: "RunPod pod не стартует",
                  a: "1) Проверьте API key: curl -H 'Authorization: Bearer rp_...' https://api.runpod.io/v2/pods. 2) Docker image доступен из RunPod. 3) Выбранный GPU доступен в вашем регионе. 4) Достаточно средств на балансе.",
                },
                {
                  q: "Модель скачивается при каждом запуске",
                  a: "Настройте Docker volume для ACE_STEP_CACHE_DIR. В docker-compose: volumes: - model_cache:/app/ace_model_cache. На RunPod: используйте Network Volume.",
                },
                {
                  q: "Задачи зависают в статусе 'running'",
                  a: "1) Celery Beat cleanup_stale_jobs автоматически помечает зависшие задачи (>30 min) как failed. 2) Проверьте логи worker: docker logs lofty-gpu-worker. 3) Проверьте heartbeat: redis-cli GET worker_heartbeat:*.",
                },
                {
                  q: "Результат не появляется на фронтенде",
                  a: "1) Worker записал в Redis? redis-cli GET job_result:{id}. 2) API sync: GET /api/v1/jobs/{id} триггерит sync_job_result(). 3) SSE stream подключен? Проверьте network tab. 4) S3 доступен из API? GET /health/ready.",
                },
              ].map((item, i) => (
                <Collapsible
                  key={i}
                  title={item.q}
                  icon={AlertTriangle}
                >
                  <p className="text-xs text-[#808080] leading-relaxed">
                    {item.a}
                  </p>
                </Collapsible>
              ))}
            </div>
          </section>

          {/* Footer spacer */}
          <div className="h-20" />
        </main>
      </div>
    </div>
  );
}

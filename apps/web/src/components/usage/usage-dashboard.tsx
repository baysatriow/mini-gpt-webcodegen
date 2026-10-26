"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  Activity,
  AlertCircle,
  ArrowLeft,
  CheckCircle2,
  ChevronDown,
  Clock3,
  Cpu,
  Database,
  LoaderCircle,
  RefreshCw,
  XCircle,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  getCurrentGpu,
  getUsageDetail,
  getUsagePage,
  getUsageSummary,
  type CurrentGpu,
  type UsageDetail,
  type UsageEvent,
  type UsageFailureCode,
  type UsageOutcome,
  type UsagePage,
  type UsageRecord,
  type UsageStage,
  type UsageSummary,
  type UsageWindow,
} from "@/lib/usage-client";

const OUTCOME_LABELS: Record<UsageOutcome, string> = {
  running: "Sedang berjalan",
  completed: "Berhasil",
  rejected: "Ditolak sebelum inference",
  failed: "Gagal",
  interrupted: "Terhenti saat server restart",
};

const STAGE_LABELS: Record<UsageStage, string> = {
  request_received: "Permintaan diterima",
  request_validation: "Validasi format request",
  intake_validation: "Validasi fakta halaman",
  model_load: "Memuat model",
  inference: "Inference",
  output_validation: "Validasi output",
  render_export: "Render dan ekspor",
  persist_result: "Menyimpan hasil",
  completed: "Selesai",
  server_restart: "Server restart",
};

const FAILURE_LABELS: Record<UsageFailureCode, string> = {
  input_rejected: "Input ditolak",
  input_too_long: "Input terlalu panjang",
  unsupported_request: "Permintaan di luar kemampuan",
  generation_busy: "Generator sedang digunakan",
  model_unavailable: "Model tidak tersedia",
  inference_failed: "Inference gagal",
  cuda_out_of_memory: "Memori CUDA tidak cukup",
  output_invalid: "Output tidak valid",
  render_failed: "Render gagal",
  storage_failed: "Penyimpanan hasil gagal",
  invalid_request: "Format request tidak valid",
  internal_error: "Kesalahan internal",
  server_interrupted: "Proses terhenti saat server restart",
  gpu_telemetry_unavailable: "Telemetri GPU tidak tersedia",
};

const OUTCOME_STYLES: Record<UsageOutcome, string> = {
  running: "border-blue-200 bg-blue-50 text-blue-800",
  completed: "border-emerald-200 bg-emerald-50 text-emerald-800",
  rejected: "border-amber-200 bg-amber-50 text-amber-900",
  failed: "border-red-200 bg-red-50 text-red-800",
  interrupted: "border-slate-200 bg-slate-100 text-slate-700",
};

const STAGE_OPTIONS: UsageStage[] = [
  "request_received",
  "request_validation",
  "intake_validation",
  "model_load",
  "inference",
  "output_validation",
  "render_export",
  "persist_result",
  "completed",
  "server_restart",
];

function outcomeLabel(outcome: UsageOutcome) {
  return OUTCOME_LABELS[outcome];
}

function dateLabel(value: string | null) {
  if (!value) return "Belum tersedia";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Belum tersedia";
  return new Intl.DateTimeFormat("id-ID", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

function numberLabel(value: number | null, digits = 0) {
  if (value === null || !Number.isFinite(value)) return "Belum tersedia";
  return new Intl.NumberFormat("id-ID", { maximumFractionDigits: digits }).format(value);
}

function percentLabel(value: number | null) {
  return value === null ? "Belum tersedia" : `${numberLabel(value * 100, 1)}%`;
}

function durationLabel(value: number | null) {
  if (value === null) return "Belum tersedia";
  if (value < 1000) return `${numberLabel(value)} ms`;
  return `${numberLabel(value / 1000, 1)} dtk`;
}

function memoryLabel(value: number | null) {
  if (value === null) return "Belum tersedia";
  return value >= 1024 ? `${numberLabel(value / 1024, 2)} GiB` : `${numberLabel(value)} MiB`;
}

function shortId(value: string) {
  return value.slice(0, 8).toUpperCase();
}

function StageLabel({ stage }: { stage: UsageStage }) {
  return <>{STAGE_LABELS[stage]}</>;
}

function Metric({ label, value, hint, icon: Icon }: {
  label: string;
  value: string;
  hint?: string;
  icon: typeof Activity;
}) {
  return (
    <article className="rounded-2xl border border-border bg-card p-4 shadow-xs sm:p-5">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-xs font-medium text-muted-foreground">{label}</p>
          <p className="mt-2 text-2xl font-semibold tracking-tight text-foreground">{value}</p>
          {hint ? <p className="mt-1 text-xs leading-relaxed text-muted-foreground">{hint}</p> : null}
        </div>
        <span className="grid size-9 shrink-0 place-items-center rounded-xl bg-muted text-muted-foreground">
          <Icon aria-hidden="true" className="size-4" />
        </span>
      </div>
    </article>
  );
}

function OutcomeBadge({ outcome }: { outcome: UsageOutcome }) {
  const Icon = outcome === "completed"
    ? CheckCircle2
    : outcome === "failed" || outcome === "interrupted"
      ? XCircle
      : outcome === "rejected"
        ? AlertCircle
        : LoaderCircle;
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium ${OUTCOME_STYLES[outcome]}`}>
      <Icon aria-hidden="true" className={`size-3.5 ${outcome === "running" ? "animate-spin" : ""}`} />
      {outcomeLabel(outcome)}
    </span>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0 rounded-xl bg-muted/50 px-3 py-2.5">
      <p className="text-[11px] text-muted-foreground">{label}</p>
      <p className="mt-1 whitespace-normal break-words leading-snug text-sm font-medium text-foreground">{value}</p>
    </div>
  );
}

function formatEventType(event: UsageEvent) {
  if (event.event_type === "started") return "Dimulai";
  if (event.event_type === "completed") return "Berhasil";
  if (event.event_type === "rejected") return "Ditolak";
  if (event.event_type === "failed") return "Gagal";
  if (event.event_type === "interrupted") return "Terhenti";
  return "Perubahan tahap";
}

function UsageTimeline({ detail }: { detail: UsageDetail }) {
  const utilizationSamples = detail.samples.filter((sample) => sample.utilization_pct !== null);
  const memorySamples = detail.samples.filter((sample) => sample.memory_used_mib !== null);
  const polyline = (samples: typeof detail.samples, field: "utilization_pct" | "memory_used_mib", maximum: number) => {
    if (samples.length < 2) return "";
    const width = 320;
    const height = 88;
    return samples.map((sample, index) => {
      const x = 4 + (index / (samples.length - 1)) * (width - 8);
      const value = sample[field] ?? 0;
      const y = height - 5 - (Math.min(1, value / Math.max(maximum, 1)) * (height - 10));
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    }).join(" ");
  };
  const utilizationLine = polyline(utilizationSamples, "utilization_pct", 100);
  const memoryLimit = detail.samples.reduce((maximum, sample) => Math.max(maximum, sample.memory_total_mib ?? 0), 0);
  const memoryLine = polyline(memorySamples, "memory_used_mib", memoryLimit || 1);

  return (
    <div className="mt-4 grid gap-4 lg:grid-cols-[minmax(0,1.2fr)_minmax(260px,0.8fr)]">
      <section className="rounded-2xl border border-border bg-background p-4" aria-labelledby={`timeline-${detail.usage_id}`}>
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div>
            <h4 id={`timeline-${detail.usage_id}`} className="text-sm font-semibold text-foreground">Tahapan proses</h4>
            <p className="mt-1 text-xs text-muted-foreground">Urutan dan waktu relatif sejak request diterima.</p>
          </div>
          <span className="text-xs text-muted-foreground">{detail.events.length} peristiwa</span>
        </div>
        {detail.events.length ? (
          <ol className="mt-4 space-y-0">
            {detail.events.map((event, index) => (
              <li key={`${event.occurred_at}-${index}`} className="relative flex gap-3 pb-4 last:pb-0">
                {index < detail.events.length - 1 ? <span aria-hidden="true" className="absolute bottom-0 left-[7px] top-4 w-px bg-border" /> : null}
                <span aria-hidden="true" className={`relative mt-1 size-3.5 shrink-0 rounded-full border-2 ${event.event_type === "failed" || event.event_type === "rejected" ? "border-destructive bg-destructive/15" : "border-primary bg-background"}`} />
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
                    <p className="text-sm font-medium text-foreground"><StageLabel stage={event.stage} /> <span className="font-normal text-muted-foreground">· {formatEventType(event)}</span></p>
                    <p className="text-xs tabular-nums text-muted-foreground">+{durationLabel(event.elapsed_ms)}</p>
                  </div>
                  <p className="mt-0.5 text-xs text-muted-foreground">{dateLabel(event.occurred_at)}{event.failure_code ? ` · ${FAILURE_LABELS[event.failure_code]}` : ""}</p>
                </div>
              </li>
            ))}
          </ol>
        ) : <p className="mt-4 text-sm text-muted-foreground">Tahapan belum tercatat.</p>}
      </section>

      <section className="space-y-4" aria-label="Rincian resource">
        <div className="rounded-2xl border border-border bg-background p-4">
          <div className="flex items-start justify-between gap-3">
            <div>
              <h4 className="text-sm font-semibold text-foreground">Telemetri selama generate</h4>
              <p className="mt-1 text-xs leading-relaxed text-muted-foreground">nvidia-smi membaca seluruh perangkat dan hanya disampel ketika proses generate berjalan.</p>
            </div>
            <span className="rounded-lg bg-muted px-2 py-1 text-xs text-muted-foreground">{detail.samples.length} sampel</span>
          </div>
          {detail.samples.length ? (
            <>
              <svg className="mt-4 h-24 w-full overflow-visible" viewBox="0 0 320 88" role="img" aria-label={`Grafik ${utilizationSamples.length} sampel utilisasi GPU dan ${memorySamples.length} sampel memori GPU`}>
                <line x1="4" y1="83" x2="316" y2="83" stroke="currentColor" className="text-border" />
                <line x1="4" y1="44" x2="316" y2="44" stroke="currentColor" strokeDasharray="3 4" className="text-border" />
                {utilizationLine ? <polyline points={utilizationLine} fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinejoin="round" strokeLinecap="round" className="text-primary" /> : null}
                {memoryLine ? <polyline points={memoryLine} fill="none" stroke="currentColor" strokeWidth="2" strokeDasharray="5 4" strokeLinejoin="round" strokeLinecap="round" className="text-amber-600" /> : null}
              </svg>
              <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
                <span className="inline-flex items-center gap-1.5"><i aria-hidden="true" className="size-2 rounded-full bg-primary" /> Utilisasi GPU</span>
                <span className="inline-flex items-center gap-1.5"><i aria-hidden="true" className="size-2 rounded-full bg-amber-600" /> Memori GPU</span>
              </div>
            </>
          ) : <p className="mt-4 rounded-xl bg-muted/60 p-3 text-sm text-muted-foreground">Tidak ada data GPU selama proses generate. Ini bisa terjadi jika inference berjalan terlalu singkat atau telemetri tidak tersedia.</p>}
          <div className="mt-4 grid grid-cols-2 gap-2">
            <Stat label="Rata-rata GPU" value={detail.gpu_utilization_mean_pct === null ? "Belum tersedia" : `${numberLabel(detail.gpu_utilization_mean_pct, 1)}%`} />
            <Stat label="Puncak VRAM perangkat" value={memoryLabel(detail.gpu_memory_max_mib)} />
            <Stat label="Suhu maksimum" value={detail.gpu_temperature_max_c === null ? "Belum tersedia" : `${numberLabel(detail.gpu_temperature_max_c)} °C`} />
            <Stat label="Daya rata-rata" value={detail.gpu_power_mean_w === null ? "Belum tersedia" : `${numberLabel(detail.gpu_power_mean_w, 1)} W`} />
          </div>
        </div>
        <div className="rounded-2xl border border-border bg-background p-4">
          <h4 className="text-sm font-semibold text-foreground">Memori PyTorch proses</h4>
          <p className="mt-1 text-xs leading-relaxed text-muted-foreground">Penggunaan proses model, terpisah dari total memori perangkat.</p>
          <div className="mt-4 grid grid-cols-2 gap-2">
            <Stat label="Allocated baseline" value={memoryLabel(detail.torch_allocated_baseline_bytes === null ? null : detail.torch_allocated_baseline_bytes / 1024 / 1024)} />
            <Stat label="Allocated peak" value={memoryLabel(detail.torch_allocated_peak_bytes === null ? null : detail.torch_allocated_peak_bytes / 1024 / 1024)} />
            <Stat label="Allocated delta" value={memoryLabel(detail.torch_allocated_delta_bytes === null ? null : detail.torch_allocated_delta_bytes / 1024 / 1024)} />
            <Stat label="Reserved peak" value={memoryLabel(detail.torch_reserved_peak_bytes === null ? null : detail.torch_reserved_peak_bytes / 1024 / 1024)} />
          </div>
        </div>
      </section>
    </div>
  );
}

function UsageItem({ record, expanded, detail, loading, detailError, onToggle }: {
  record: UsageRecord;
  expanded: boolean;
  detail: UsageDetail | null;
  loading: boolean;
  detailError: string | null;
  onToggle: () => void;
}) {
  const detailId = `usage-detail-${record.usage_id}`;
  return (
    <li className="list-none">
      <article className="rounded-2xl border border-border bg-card p-4 shadow-xs sm:p-5">
        <button
          type="button"
          aria-expanded={expanded}
          aria-controls={detailId}
          onClick={onToggle}
          className="flex w-full items-start justify-between gap-3 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
        >
          <span className="min-w-0">
            <span className="flex flex-wrap items-center gap-2">
              <OutcomeBadge outcome={record.outcome} />
              <span className="text-xs text-muted-foreground">ID {shortId(record.usage_id)}</span>
            </span>
            <span className="mt-2 block text-sm font-medium text-foreground">{dateLabel(record.started_at)}</span>
          </span>
          <ChevronDown aria-hidden="true" className={`mt-2 size-4 shrink-0 text-muted-foreground transition-transform ${expanded ? "rotate-180" : ""}`} />
        </button>

        <div className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-3 xl:grid-cols-6">
          <Stat label="Tahap terakhir" value={STAGE_LABELS[record.stage]} />
          <Stat label="Durasi" value={durationLabel(record.duration_ms)} />
          <Stat label="Inference" value={record.inference_started ? "Dimulai" : "Belum dimulai"} />
          <Stat label="Token masuk / keluar" value={`${numberLabel(record.input_tokens)} / ${numberLabel(record.output_tokens)}`} />
          <Stat label="Seksi / percobaan" value={`${numberLabel(record.section_count)} / ${numberLabel(record.attempt_count)}${record.retry_count ? ` · ${record.retry_count} retry` : ""}`} />
          <Stat label="VRAM perangkat puncak" value={memoryLabel(record.gpu_memory_max_mib)} />
        </div>

        {(record.failure_code || record.http_status || record.model_id || record.gpu_sample_count > 0) ? (
          <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 border-t border-border pt-3 text-xs text-muted-foreground">
            {record.failure_code ? <span>Kode: {FAILURE_LABELS[record.failure_code]}</span> : null}
            {record.http_status ? <span>HTTP {record.http_status}</span> : null}
            {record.model_id ? <span>Model: {record.model_id}</span> : null}
            <span>{record.gpu_sample_count} sampel GPU</span>
          </div>
        ) : null}

        {expanded ? (
          <div id={detailId} className="mt-4 border-t border-border pt-4">
            {loading ? <p className="flex items-center gap-2 text-sm text-muted-foreground" role="status"><LoaderCircle className="size-4 animate-spin" /> Memuat detail audit...</p> : null}
            {detailError ? <p className="text-sm text-destructive" role="alert">{detailError}</p> : null}
            {detail ? <UsageTimeline detail={detail} /> : null}
          </div>
        ) : null}
      </article>
    </li>
  );
}

export function UsageDashboard({ showLogout = false }: { showLogout?: boolean }) {
  const [window, setWindow] = useState<UsageWindow>("24h");
  const [status, setStatus] = useState<UsageOutcome | "">("");
  const [stage, setStage] = useState<UsageStage | "">("");
  const [summary, setSummary] = useState<UsageSummary | null>(null);
  const [gpu, setGpu] = useState<CurrentGpu | null>(null);
  const [records, setRecords] = useState<UsageRecord[]>([]);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<UsageDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);

  const refresh = useCallback(async (quiet = false) => {
    if (!quiet) setRefreshing(true);
    setError(null);
    try {
      const [nextSummary, nextGpu, page] = await Promise.all([
        getUsageSummary(window),
        getCurrentGpu(),
        getUsagePage({ window, status, stage, limit: 25 }),
      ]);
      setSummary(nextSummary);
      setGpu(nextGpu);
      setRecords(page.items);
      setNextCursor(page.next_cursor);
      setExpandedId(null);
      setDetail(null);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Data Usage tidak dapat dimuat.");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [stage, status, window]);

  useEffect(() => {
    const timer = globalThis.setTimeout(() => void refresh(true), 0);
    return () => globalThis.clearTimeout(timer);
  }, [refresh]);

  useEffect(() => {
    let timer: ReturnType<typeof setInterval> | null = null;
    const poll = () => {
      if (document.visibilityState !== "visible") return;
      void getCurrentGpu().then(setGpu).catch(() => setGpu(null));
    };
    const onVisibility = () => {
      if (document.visibilityState === "visible") {
        poll();
        void refresh(true);
      }
    };
    timer = setInterval(poll, 15_000);
    document.addEventListener("visibilitychange", onVisibility);
    return () => {
      if (timer) clearInterval(timer);
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, [refresh]);

  const coverageHint = useMemo(() => {
    if (!summary || summary.gpu_coverage_ratio === null) return "Belum ada inference untuk dihitung";
    return `${summary.gpu_run_count} dari ${summary.inference_started} proses inference memiliki sampel`;
  }, [summary]);

  async function loadMore() {
    if (!nextCursor || loadingMore) return;
    setLoadingMore(true);
    try {
      const page: UsagePage = await getUsagePage({ cursor: nextCursor, window, status, stage, limit: 25 });
      setRecords((current) => [...current, ...page.items]);
      setNextCursor(page.next_cursor);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Halaman berikutnya tidak dapat dimuat.");
    } finally {
      setLoadingMore(false);
    }
  }

  async function toggleDetail(record: UsageRecord) {
    if (expandedId === record.usage_id) {
      setExpandedId(null);
      setDetail(null);
      return;
    }
    setExpandedId(record.usage_id);
    setDetail(null);
    setDetailError(null);
    setDetailLoading(true);
    try {
      setDetail(await getUsageDetail(record.usage_id));
    } catch (cause) {
      setDetailError(cause instanceof Error ? cause.message : "Detail audit tidak dapat dimuat.");
    } finally {
      setDetailLoading(false);
    }
  }

  const memoryUsed = gpu?.memory_used_mib === null || !gpu ? "Belum tersedia" : memoryLabel(gpu.memory_used_mib);
  const memoryTotal = gpu?.memory_total_mib === null || !gpu ? "Belum tersedia" : memoryLabel(gpu.memory_total_mib);
  const utilization = gpu?.utilization_pct === null || !gpu ? "Belum tersedia" : `${numberLabel(gpu.utilization_pct, 1)}%`;

  return (
    <main className="min-h-screen bg-muted/30 px-4 py-5 text-foreground sm:px-6 sm:py-8 lg:px-8">
      <div className="mx-auto max-w-7xl">
        <header className="mb-6 flex flex-wrap items-center justify-between gap-4">
          <div className="flex min-w-0 items-center gap-3">
            <Link href="/" aria-label="Kembali ke chat" className="grid size-10 shrink-0 place-items-center rounded-xl border border-border bg-card text-muted-foreground transition hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
              <ArrowLeft aria-hidden="true" className="size-4" />
            </Link>
            <div>
              <p className="text-xs font-medium uppercase tracking-[0.12em] text-primary">Rancang AI</p>
              <h1 className="mt-0.5 text-2xl font-semibold tracking-tight sm:text-3xl">Usage</h1>
              <p className="mt-1 text-sm text-muted-foreground">Ringkasan GPU dan jejak tiap proses generate.</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <label htmlFor="usage-window" className="sr-only">Periode ringkasan</label>
            <select id="usage-window" value={window} onChange={(event) => setWindow(event.target.value as UsageWindow)} className="h-10 rounded-xl border border-border bg-card px-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring">
              <option value="24h">24 jam</option>
              <option value="7d">7 hari</option>
              <option value="30d">30 hari</option>
            </select>
            <Button type="button" variant="outline" size="icon" aria-label="Muat ulang Usage" onClick={() => void refresh()} disabled={refreshing} className="size-10 rounded-xl bg-card">
              <RefreshCw aria-hidden="true" className={`size-4 ${refreshing ? "animate-spin" : ""}`} />
            </Button>
            {showLogout ? <form action="/api/auth/logout" method="post"><button type="submit" className="h-10 rounded-xl border border-border bg-card px-3 text-sm font-medium text-muted-foreground transition hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">Keluar</button></form> : null}
          </div>
        </header>

        {error ? (
          <div role="alert" className="mb-5 flex flex-wrap items-start justify-between gap-3 rounded-2xl border border-destructive/30 bg-destructive/5 p-4 text-sm">
            <span className="flex items-center gap-2 text-destructive"><AlertCircle aria-hidden="true" className="size-4 shrink-0" />{error}</span>
            <Button type="button" variant="outline" size="sm" onClick={() => void refresh()} className="rounded-lg">Coba lagi</Button>
          </div>
        ) : null}

        <section className="mb-5 rounded-3xl border border-border bg-card p-4 shadow-xs sm:p-6" aria-labelledby="gpu-heading">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="flex items-start gap-3">
              <span className="grid size-11 place-items-center rounded-2xl bg-primary/10 text-primary"><Cpu aria-hidden="true" className="size-5" /></span>
              <div>
                <h2 id="gpu-heading" className="text-base font-semibold">GPU saat ini</h2>
                <p className="mt-1 text-sm text-muted-foreground">{gpu?.device_name ?? (gpu?.available === false ? "Telemetri GPU belum tersedia" : "Membaca status perangkat...")}</p>
              </div>
            </div>
            <span className={`rounded-full border px-3 py-1 text-xs font-medium ${gpu?.available ? "border-emerald-200 bg-emerald-50 text-emerald-800" : "border-amber-200 bg-amber-50 text-amber-900"}`}>
              {gpu?.available ? "Snapshot tersedia" : "Data tidak tersedia"}
            </span>
          </div>
          {gpu?.available ? (
            <div className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-4">
              <Stat label="Utilisasi" value={utilization} />
              <Stat label="Memori perangkat" value={`${memoryUsed} / ${memoryTotal}`} />
              <Stat label="Suhu" value={gpu.temperature_c === null ? "Belum tersedia" : `${numberLabel(gpu.temperature_c)} °C`} />
              <Stat label="Daya" value={gpu.power_w === null ? "Belum tersedia" : `${numberLabel(gpu.power_w, 1)} W`} />
            </div>
          ) : (
            <p className="mt-4 rounded-xl bg-muted/60 p-3 text-sm leading-relaxed text-muted-foreground">
              Snapshot tidak tersedia. Pastikan driver NVIDIA dan nvidia-smi dapat diakses. Histori generation tetap tampil jika ada sampel yang tersimpan.
            </p>
          )}
          <p className="mt-3 text-xs text-muted-foreground">
            Snapshot diambil saat halaman Usage dibuka. Histori GPU hanya disampel selama proses generate dan merupakan data seluruh perangkat, bukan proses model saja.
            {gpu?.sampled_at ? ` Terakhir dibaca ${dateLabel(gpu.sampled_at)}.` : ""}
          </p>
        </section>

        {loading && !summary ? (
          <div className="flex min-h-48 items-center justify-center rounded-3xl border border-border bg-card text-sm text-muted-foreground" role="status">
            <LoaderCircle aria-hidden="true" className="mr-2 size-4 animate-spin" /> Memuat ringkasan Usage...
          </div>
        ) : summary ? (
          <>
            <section className="mb-5 grid grid-cols-2 gap-3 xl:grid-cols-4" aria-label="Ringkasan hasil generate">
              <Metric label="Total request" value={numberLabel(summary.total_requests)} hint={`${numberLabel(summary.inference_started)} memulai inference`} icon={Activity} />
              <Metric label="Berhasil" value={numberLabel(summary.completed)} hint={`Tingkat berhasil ${percentLabel(summary.success_rate_all)}`} icon={CheckCircle2} />
              <Metric label="Gagal / ditolak" value={`${numberLabel(summary.failed)} / ${numberLabel(summary.rejected)}`} hint={`${numberLabel(summary.interrupted)} terhenti karena restart`} icon={XCircle} />
              <Metric label="Rata-rata durasi sukses" value={durationLabel(summary.mean_duration_ms)} hint="Hanya request yang berhasil" icon={Clock3} />
            </section>

            <section className="mb-6 rounded-3xl border border-border bg-card p-4 shadow-xs sm:p-6" aria-labelledby="gpu-history-heading">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <h2 id="gpu-history-heading" className="text-base font-semibold">GPU selama generation</h2>
                  <p className="mt-1 text-sm text-muted-foreground">{summary.gpu_sample_count} sampel di {summary.gpu_run_count} proses. {coverageHint}.</p>
                </div>
                <span className="rounded-full border border-border bg-muted/50 px-3 py-1 text-xs text-muted-foreground">Cakupan {percentLabel(summary.gpu_coverage_ratio)}</span>
              </div>
              <div className="mt-4 grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
                <Stat label="Rata-rata utilisasi" value={summary.gpu_utilization_mean_pct === null ? "Belum tersedia" : `${numberLabel(summary.gpu_utilization_mean_pct, 1)}%`} />
                <Stat label="Puncak utilisasi" value={summary.gpu_utilization_max_pct === null ? "Belum tersedia" : `${numberLabel(summary.gpu_utilization_max_pct, 1)}%`} />
                <Stat label="Rata-rata VRAM" value={memoryLabel(summary.gpu_memory_mean_mib)} />
                <Stat label="Puncak VRAM" value={memoryLabel(summary.gpu_memory_max_mib)} />
                <Stat label="Suhu maksimum" value={summary.gpu_temperature_max_c === null ? "Belum tersedia" : `${numberLabel(summary.gpu_temperature_max_c)} °C`} />
                <Stat label="Daya rata-rata" value={summary.gpu_power_mean_w === null ? "Belum tersedia" : `${numberLabel(summary.gpu_power_mean_w, 1)} W`} />
              </div>
              <p className="mt-3 text-xs leading-relaxed text-muted-foreground">{summary.gpu_scope}.</p>
            </section>

            <section className="rounded-3xl border border-border bg-card p-4 shadow-xs sm:p-6" aria-labelledby="history-heading">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <h2 id="history-heading" className="text-base font-semibold">Riwayat generate</h2>
                  <p className="mt-1 text-sm text-muted-foreground">Audit hanya menyimpan status, tahapan, durasi, token, kode kendala, dan telemetri. Prompt serta isi hasil tidak disimpan.</p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <label htmlFor="usage-status" className="sr-only">Filter status</label>
                  <select id="usage-status" value={status} onChange={(event) => setStatus(event.target.value as UsageOutcome | "")} className="h-9 rounded-lg border border-border bg-background px-2.5 text-xs outline-none focus-visible:ring-2 focus-visible:ring-ring">
                    <option value="">Semua status</option>
                    {(Object.keys(OUTCOME_LABELS) as UsageOutcome[]).map((outcome) => <option key={outcome} value={outcome}>{outcomeLabel(outcome)}</option>)}
                  </select>
                  <label htmlFor="usage-stage" className="sr-only">Filter tahap</label>
                  <select id="usage-stage" value={stage} onChange={(event) => setStage(event.target.value as UsageStage | "")} className="h-9 max-w-48 rounded-lg border border-border bg-background px-2.5 text-xs outline-none focus-visible:ring-2 focus-visible:ring-ring">
                    <option value="">Semua tahap</option>
                    {STAGE_OPTIONS.map((option) => <option key={option} value={option}>{STAGE_LABELS[option]}</option>)}
                  </select>
                </div>
              </div>

              {records.length ? (
                <ul className="mt-5 space-y-3">
                  {records.map((record) => (
                    <UsageItem
                      key={record.usage_id}
                      record={record}
                      expanded={expandedId === record.usage_id}
                      detail={expandedId === record.usage_id ? detail : null}
                      loading={expandedId === record.usage_id && detailLoading}
                      detailError={expandedId === record.usage_id ? detailError : null}
                      onToggle={() => void toggleDetail(record)}
                    />
                  ))}
                </ul>
              ) : (
                <div className="mt-5 rounded-2xl border border-dashed border-border bg-muted/30 px-5 py-10 text-center">
                  <Database aria-hidden="true" className="mx-auto size-6 text-muted-foreground/70" />
                  <h3 className="mt-3 text-sm font-medium text-foreground">Belum ada aktivitas pada periode ini</h3>
                  <p className="mx-auto mt-1 max-w-md text-sm leading-relaxed text-muted-foreground">Request generate akan muncul di sini, termasuk yang ditolak saat validasi. Buka chat untuk membuat halaman.</p>
                  <Link href="/" className="mt-4 inline-flex items-center gap-2 rounded-lg bg-primary px-3 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2">Kembali ke chat</Link>
                </div>
              )}

              {nextCursor ? (
                <div className="mt-5 flex justify-center">
                  <Button type="button" variant="outline" onClick={() => void loadMore()} disabled={loadingMore} className="rounded-xl">
                    {loadingMore ? <LoaderCircle aria-hidden="true" className="size-4 animate-spin" /> : <ChevronDown aria-hidden="true" className="size-4" />}
                    Muat aktivitas berikutnya
                  </Button>
                </div>
              ) : null}
            </section>
          </>
        ) : null}
      </div>
    </main>
  );
}

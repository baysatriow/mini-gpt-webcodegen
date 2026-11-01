"use client";

import { useState } from "react";
import {
  AlertCircle,
  Check,
  CheckCircle2,
  Circle,
  CircleDot,
  Copy,
  Download,
  FileCode2,
  LoaderCircle,
  Minus,
  RefreshCw,
  XCircle,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ApiClientError, downloadSourceFile, downloadZip, getSource } from "@/lib/api-client";
import type { SourceFilename, SourceResponse } from "@/lib/api-types";
import { copyTextToClipboard } from "@/lib/clipboard";
import { isValidGenerationId } from "@/lib/preview-url";
import type { UsageDetail, UsageEvent, UsageFailureCode, UsageOutcome, UsageRecord, UsageStage } from "@/lib/usage-client";

export const OUTCOME_LABELS: Record<UsageOutcome, string> = {
  running: "Sedang berjalan",
  completed: "Berhasil",
  rejected: "Ditolak sebelum inference",
  failed: "Gagal",
  interrupted: "Terhenti saat server restart",
};

export const STAGE_LABELS: Record<UsageStage, string> = {
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

export const FAILURE_LABELS: Record<UsageFailureCode, string> = {
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

export function outcomeLabel(outcome: UsageOutcome) {
  return OUTCOME_LABELS[outcome];
}

export function dateLabel(value: string | null) {
  if (!value) return "Belum tersedia";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Belum tersedia";
  return new Intl.DateTimeFormat("id-ID", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "Asia/Jakarta",
  }).format(date) + " WIB";
}

export function numberLabel(value: number | null, digits = 0) {
  if (value === null || !Number.isFinite(value)) return "Belum tersedia";
  return new Intl.NumberFormat("id-ID", { maximumFractionDigits: digits }).format(value);
}

export function percentLabel(value: number | null) {
  return value === null ? "Belum tersedia" : `${numberLabel(value * 100, 1)}%`;
}

export function durationLabel(value: number | null) {
  if (value === null) return "Belum tersedia";
  if (value < 1000) return `${numberLabel(value)} ms`;
  return `${numberLabel(value / 1000, 1)} dtk`;
}

export function memoryLabel(value: number | null) {
  if (value === null) return "Belum tersedia";
  return value >= 1024 ? `${numberLabel(value / 1024, 2)} GiB` : `${numberLabel(value)} MiB`;
}

export function shortId(value: string) {
  return value.slice(0, 8).toUpperCase();
}

export function recordTitle(record: UsageRecord) {
  if (record.title_preview?.trim()) return record.title_preview.trim();
  if (record.stage === "request_validation" || record.failure_code === "invalid_request") {
    return "Request ditolak sebelum input terbaca";
  }
  return "Detail input belum tersedia untuk run ini";
}

export function OutcomeBadge({ outcome }: { outcome: UsageOutcome }) {
  const Icon = outcome === "completed"
    ? CheckCircle2
    : outcome === "failed" || outcome === "interrupted"
      ? XCircle
      : outcome === "rejected"
        ? AlertCircle
        : LoaderCircle;
  const style = {
    running: "border-sky-200 bg-sky-50 text-sky-900",
    completed: "border-emerald-200 bg-emerald-50 text-emerald-900",
    rejected: "border-amber-200 bg-amber-50 text-amber-950",
    failed: "border-rose-200 bg-rose-50 text-rose-900",
    interrupted: "border-border bg-muted text-foreground",
  }[outcome];

  return (
    <span className={`inline-flex max-w-full items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium ${style}`}>
      <Icon aria-hidden="true" className={`size-3.5 shrink-0 ${outcome === "running" ? "animate-spin" : ""}`} />
      <span className="truncate">{outcomeLabel(outcome)}</span>
    </span>
  );
}

export function Stat({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="min-w-0 rounded-xl bg-muted/55 px-3 py-2.5">
      <p className="text-[11px] leading-snug text-muted-foreground">{label}</p>
      <p className="mt-1 whitespace-normal break-words leading-snug text-sm font-medium text-foreground">{value}</p>
      {hint ? <p className="mt-1 text-[11px] leading-relaxed text-muted-foreground">{hint}</p> : null}
    </div>
  );
}

const STAGE_GROUPS: Array<{ label: string; stages: UsageStage[] }> = [
  { label: "Request", stages: ["request_received", "request_validation"] },
  { label: "Validasi", stages: ["intake_validation", "output_validation"] },
  { label: "Inference", stages: ["model_load", "inference"] },
  { label: "Render", stages: ["render_export"] },
  { label: "Selesai", stages: ["persist_result", "completed"] },
];

type RailState = "done" | "active" | "failed" | "pending" | "unrecorded";

function stageState(detail: UsageDetail, index: number): RailState {
  const group = STAGE_GROUPS[index];
  const events = detail.events.filter((event) => group.stages.includes(event.stage));
  const hasFailure = events.some((event) => event.event_type === "failed"
    || event.event_type === "rejected"
    || event.event_type === "interrupted"
    || event.failure_code !== null);
  const currentIndex = STAGE_GROUPS.findIndex((item) => item.stages.includes(detail.stage));

  if (hasFailure) return "failed";
  if (detail.outcome === "completed") return "done";
  if (index === currentIndex) {
    if (detail.outcome === "failed" || detail.outcome === "rejected" || detail.outcome === "interrupted") return "failed";
    return events.length ? "active" : "unrecorded";
  }
  if (events.length > 0 && index < currentIndex) return "done";
  if (index < currentIndex) return "unrecorded";
  return "pending";
}

const RAIL_STYLES: Record<RailState, { icon: typeof Circle; label: string; className: string }> = {
  done: { icon: Check, label: "Selesai", className: "border-emerald-700 bg-emerald-700 text-white" },
  active: { icon: CircleDot, label: "Berjalan", className: "border-primary bg-primary/10 text-primary" },
  failed: { icon: AlertCircle, label: "Gagal", className: "border-destructive bg-destructive/10 text-destructive" },
  pending: { icon: Circle, label: "Belum dimulai", className: "border-border bg-background text-muted-foreground" },
  unrecorded: { icon: Minus, label: "Tidak tercatat", className: "border-border bg-muted text-muted-foreground" },
};

export function UsageStageRail({ detail }: { detail: UsageDetail }) {
  return (
    <section aria-labelledby="usage-stage-heading" className="min-w-0">
      <h3 id="usage-stage-heading" className="text-sm font-semibold text-foreground">Tahap</h3>
      <ol className="mt-3 space-y-3">
        {STAGE_GROUPS.map((group, index) => {
          const state = stageState(detail, index);
          const { icon: Icon, label, className } = RAIL_STYLES[state];
          const events = detail.events.filter((event) => group.stages.includes(event.stage));
          return (
            <li key={group.label} className="flex min-w-0 items-start gap-2.5">
              <span className={`mt-0.5 grid size-6 shrink-0 place-items-center rounded-full border ${className}`}>
                <Icon aria-hidden="true" className={`size-3.5 ${state === "active" && detail.outcome === "running" ? "animate-pulse" : ""}`} />
              </span>
              <div className="min-w-0">
                <p className="text-xs font-medium leading-5 text-foreground">{group.label}</p>
                <p className="text-[11px] leading-4 text-muted-foreground">{label}{events.length ? ` · ${events.length} event` : ""}</p>
              </div>
            </li>
          );
        })}
      </ol>
    </section>
  );
}

function eventTypeLabel(event: UsageEvent) {
  if (event.event_type === "started") return "Dimulai";
  if (event.event_type === "completed") return "Berhasil";
  if (event.event_type === "rejected") return "Ditolak";
  if (event.event_type === "failed") return "Gagal";
  if (event.event_type === "interrupted") return "Terhenti";
  return "Tahap tercatat";
}

export function UsageEventLog({ detail }: { detail: UsageDetail }) {
  return (
    <details className="group border-t border-border/80 pt-3">
      <summary className="cursor-pointer text-sm font-medium text-foreground marker:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
        Rincian event <span className="ml-1 text-xs font-normal text-muted-foreground">({detail.events.length})</span>
      </summary>
      {detail.events.length ? (
        <ol className="mt-3 divide-y divide-border/70">
          {detail.events.map((event, index) => (
            <li key={`${event.occurred_at}-${index}`} className="grid min-w-0 gap-1 py-2.5 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-center">
              <div className="min-w-0">
                <p className="break-words text-xs font-medium text-foreground">{STAGE_LABELS[event.stage]} <span className="font-normal text-muted-foreground">· {eventTypeLabel(event)}</span></p>
                <p className="mt-0.5 text-[11px] text-muted-foreground">{dateLabel(event.occurred_at)}{event.failure_code ? ` · ${FAILURE_LABELS[event.failure_code]}` : ""}</p>
              </div>
              <span className="text-xs tabular-nums text-muted-foreground">+{durationLabel(event.elapsed_ms)}</span>
            </li>
          ))}
        </ol>
      ) : <p className="mt-3 text-xs leading-relaxed text-muted-foreground">Belum ada event tahap yang tersimpan untuk run ini.</p>}
    </details>
  );
}

export function UsageEvidence({ detail }: { detail: UsageDetail }) {
  const [copyStatus, setCopyStatus] = useState<"idle" | "copied" | "failed">("idle");
  const hasRequestDetails = Object.prototype.hasOwnProperty.call(detail, "prompt")
    && Array.isArray(detail.confirmed_facts);
  const confirmedFacts = Array.isArray(detail.confirmed_facts) ? detail.confirmed_facts : [];

  async function copyPrompt() {
    if (!detail.prompt) return;
    const copied = await copyTextToClipboard(detail.prompt);
    setCopyStatus(copied ? "copied" : "failed");
    window.setTimeout(() => setCopyStatus("idle"), 1800);
  }

  return (
    <section aria-labelledby="usage-input-heading" className="min-w-0">
      <div className="flex items-center justify-between gap-2">
        <h3 id="usage-input-heading" className="text-sm font-semibold text-foreground">Input yang diterima</h3>
        <Button type="button" variant="ghost" size="sm" onClick={() => void copyPrompt()} disabled={!detail.prompt} className="h-8 gap-1.5 rounded-lg text-xs" aria-live="polite">
          {copyStatus === "copied" ? <Check aria-hidden="true" className="size-3.5" /> : <Copy aria-hidden="true" className="size-3.5" />}
          {copyStatus === "copied" ? "Tersalin" : copyStatus === "failed" ? "Gagal menyalin" : "Salin prompt"}
        </Button>
      </div>
      {detail.prompt ? (
        <pre className="mt-2 max-h-52 overflow-auto whitespace-pre-wrap break-words rounded-xl border border-border/80 bg-[#f7f6f0] p-3 font-sans text-sm leading-6 text-foreground selection:bg-[#dce9df]">{detail.prompt}</pre>
      ) : (
        <p className="mt-2 rounded-xl border border-dashed border-border bg-muted/35 p-3 text-sm leading-relaxed text-muted-foreground">
          {hasRequestDetails
            ? "Detail input belum tersedia untuk run lama atau request yang ditolak sebelum isi request diterima."
            : "API FastAPI belum mengembalikan detail input. Perbarui atau mulai ulang API lokal agar prompt dan fakta tersimpan dapat ditampilkan."}
        </p>
      )}

      <div className="mt-5 border-t border-border/80 pt-4">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <h3 className="text-sm font-semibold text-foreground">Fakta yang dikonfirmasi</h3>
          <span className="text-xs text-muted-foreground">{numberLabel(confirmedFacts.length)} fakta</span>
        </div>
        {confirmedFacts.length ? (
          <dl className="mt-2 divide-y divide-border/70 rounded-xl border border-border/80 bg-card px-3">
            {confirmedFacts.map((fact) => (
              <div key={fact.id} className="grid min-w-0 gap-1 py-2.5 sm:grid-cols-[minmax(92px,0.7fr)_minmax(0,1.3fr)] sm:gap-3">
                <dt className="text-xs leading-5 text-muted-foreground">{fact.label}{fact.title ? ` · ${fact.title}` : ""}</dt>
                <dd className="whitespace-pre-wrap break-words text-sm leading-5 text-foreground">{fact.value}</dd>
              </div>
            ))}
          </dl>
        ) : (
          <p className="mt-2 rounded-xl bg-muted/40 p-3 text-xs leading-relaxed text-muted-foreground">
            {hasRequestDetails
              ? "Tidak ada fakta terkonfirmasi yang tercatat pada run ini."
              : "Fakta belum dapat dibaca karena API lokal belum mengembalikan field audit input."}
          </p>
        )}
      </div>
    </section>
  );
}

type SourceState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "loaded"; source: SourceResponse }
  | { status: "error"; message: string };

const SOURCE_FILES: SourceFilename[] = ["index.html", "styles.css", "app.js"];

const FILE_LABELS: Record<SourceFilename, { language: string; tint: string }> = {
  "index.html": { language: "HTML", tint: "text-amber-300" },
  "styles.css": { language: "CSS", tint: "text-sky-300" },
  "app.js": { language: "JS", tint: "text-lime-300" },
};

function isSourceResponse(value: unknown): value is SourceResponse {
  if (typeof value !== "object" || value === null) return false;
  const source = value as Record<string, unknown>;
  return SOURCE_FILES.every((filename) => typeof source[filename] === "string");
}

function saveBlob(blob: Blob, filename: string) {
  const objectUrl = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = objectUrl;
  link.download = filename;
  link.hidden = true;
  document.body.append(link);
  link.click();
  link.remove();
  window.setTimeout(() => window.URL.revokeObjectURL(objectUrl), 1000);
}

export function UsageSourcePanel({ generationId }: { generationId: string | null }) {
  const [state, setState] = useState<SourceState>({ status: "idle" });
  const [filename, setFilename] = useState<SourceFilename>("index.html");
  const [busyAction, setBusyAction] = useState<"file" | "zip" | null>(null);
  const [copyStatus, setCopyStatus] = useState<"idle" | "copied" | "failed">("idle");
  const [actionError, setActionError] = useState<string | null>(null);

  async function loadSource() {
    if (!generationId || !isValidGenerationId(generationId)) {
      setState({ status: "error", message: "Run ini tidak memiliki referensi generation yang valid." });
      return;
    }
    setState({ status: "loading" });
    try {
      const source: unknown = await getSource(generationId);
      if (!isSourceResponse(source)) {
        throw new Error("Endpoint tidak mengembalikan tiga file hasil yang diterima.");
      }
      setState({ status: "loaded", source });
    } catch (error) {
      setState({
        status: "error",
        message: error instanceof ApiClientError
          ? error.message
          : "Source hasil yang diterima belum tersedia untuk run ini.",
      });
    }
  }

  async function downloadFile() {
    if (!generationId || !isValidGenerationId(generationId)) return;
    setBusyAction("file");
    setActionError(null);
    try {
      saveBlob(await downloadSourceFile(generationId, filename), filename);
    } catch (error) {
      setActionError(error instanceof Error ? error.message : "File source belum dapat diunduh.");
    } finally {
      setBusyAction(null);
    }
  }

  async function downloadArchive() {
    if (!generationId || !isValidGenerationId(generationId)) return;
    setBusyAction("zip");
    setActionError(null);
    try {
      saveBlob(await downloadZip(generationId), `webcraft-${shortId(generationId).toLowerCase()}.zip`);
    } catch (error) {
      setActionError(error instanceof Error ? error.message : "ZIP hasil belum dapat diunduh.");
    } finally {
      setBusyAction(null);
    }
  }

  async function copyCurrentSource() {
    if (state.status !== "loaded") return;
    const copied = await copyTextToClipboard(state.source[filename]);
    setCopyStatus(copied ? "copied" : "failed");
    window.setTimeout(() => setCopyStatus("idle"), 1800);
  }

  const generationIsValid = Boolean(generationId && isValidGenerationId(generationId));

  return (
    <section aria-labelledby="usage-source-heading" className="flex min-h-[340px] min-w-0 flex-col overflow-hidden rounded-xl border border-[#263d3d] bg-[#102523] text-slate-100">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-white/10 px-3 py-2.5 sm:px-4">
        <div className="flex min-w-0 items-center gap-2">
          <FileCode2 aria-hidden="true" className="size-4 shrink-0 text-emerald-300" />
          <div className="min-w-0">
            <h3 id="usage-source-heading" className="truncate text-xs font-semibold text-white">Source hasil diterima</h3>
            <p className="text-[10px] text-slate-300">Teks mentah, tidak dijalankan di halaman audit</p>
          </div>
        </div>
        <Button type="button" variant="outline" size="sm" onClick={() => void downloadArchive()} disabled={!generationIsValid || busyAction !== null} className="h-8 gap-1.5 border-white/15 bg-white/5 text-xs text-white hover:bg-white/10 hover:text-white">
          {busyAction === "zip" ? <LoaderCircle aria-hidden="true" className="size-3.5 animate-spin" /> : <Download aria-hidden="true" className="size-3.5" />}
          Unduh ZIP
        </Button>
      </div>

      {state.status === "loaded" ? (
        <Tabs value={filename} onValueChange={(value) => {
          if (SOURCE_FILES.includes(value as SourceFilename)) setFilename(value as SourceFilename);
        }} className="flex min-h-0 flex-1 flex-col gap-0">
          <div className="flex min-w-0 flex-wrap items-center justify-between gap-2 border-b border-white/10 bg-[#142d2a] px-2 sm:px-3">
            <TabsList className="max-w-full gap-1 overflow-x-auto bg-transparent p-1">
              {SOURCE_FILES.map((file) => (
                <TabsTrigger key={file} value={file} className="h-8 min-w-0 gap-1.5 px-2 text-[11px] text-slate-300 data-active:bg-white/10 data-active:text-white sm:px-2.5">
                  <span className={`font-mono text-[9px] ${FILE_LABELS[file].tint}`}>{FILE_LABELS[file].language}</span>
                  <span>{file}</span>
                </TabsTrigger>
              ))}
            </TabsList>
            <div className="flex items-center gap-1">
              <Button type="button" variant="ghost" size="sm" onClick={() => void copyCurrentSource()} className="h-8 gap-1.5 px-2 text-[11px] text-slate-200 hover:bg-white/10 hover:text-white" aria-live="polite">
                {copyStatus === "copied" ? <Check aria-hidden="true" className="size-3.5" /> : <Copy aria-hidden="true" className="size-3.5" />}
                <span className="hidden sm:inline">{copyStatus === "copied" ? "Tersalin" : copyStatus === "failed" ? "Gagal" : "Salin"}</span>
              </Button>
              <Button type="button" variant="ghost" size="sm" onClick={() => void downloadFile()} disabled={busyAction !== null} className="h-8 gap-1.5 px-2 text-[11px] text-slate-200 hover:bg-white/10 hover:text-white">
                {busyAction === "file" ? <LoaderCircle aria-hidden="true" className="size-3.5 animate-spin" /> : <Download aria-hidden="true" className="size-3.5" />}
                <span className="hidden sm:inline">Unduh file</span>
              </Button>
            </div>
          </div>
          {SOURCE_FILES.map((file) => {
            const source = state.source[file];
            const lines = source.split("\n");
            return (
              <TabsContent key={file} value={file} className="m-0 min-h-0 flex-1 overflow-auto bg-[#102523] p-0 outline-none">
                <div className="flex items-center justify-between gap-3 border-b border-white/10 px-3 py-2 font-mono text-[10px] text-slate-300 sm:px-4">
                  <span>{file}</span>
                  <span>{numberLabel(lines.length)} baris · {numberLabel(source.length)} karakter</span>
                </div>
                <div className="grid min-w-0 grid-cols-[2.75rem_minmax(0,1fr)] font-mono text-[11px] leading-5 sm:text-xs sm:leading-6">
                  <pre aria-hidden="true" className="select-none border-r border-white/10 py-3 pr-2 text-right text-slate-500">{lines.map((_, index) => index + 1).join("\n")}</pre>
                  <pre className="min-w-0 overflow-x-auto whitespace-pre-wrap break-words py-3 pl-3 pr-4 text-slate-100 selection:bg-emerald-800/70"><code>{source}</code></pre>
                </div>
              </TabsContent>
            );
          })}
        </Tabs>
      ) : (
        <div className="flex min-h-0 flex-1 items-center justify-center p-5">
          <div className="max-w-sm text-center">
            {state.status === "loading" ? (
              <p className="flex items-center justify-center gap-2 text-sm text-slate-200" role="status"><LoaderCircle aria-hidden="true" className="size-4 animate-spin" /> Memuat source yang diterima...</p>
            ) : state.status === "error" ? (
              <>
                <AlertCircle aria-hidden="true" className="mx-auto size-5 text-amber-300" />
                <p className="mt-2 text-sm leading-relaxed text-slate-100">{state.message}</p>
                <Button type="button" variant="outline" size="sm" onClick={() => void loadSource()} className="mt-3 gap-1.5 border-white/15 bg-white/5 text-slate-100 hover:bg-white/10 hover:text-white">
                  <RefreshCw aria-hidden="true" className="size-3.5" /> Coba lagi
                </Button>
              </>
            ) : (
              <>
                <p className="text-sm leading-relaxed text-slate-200">
                  {generationIsValid
                    ? "Source baru dimuat setelah Anda membukanya. Endpoint hanya mengembalikan artefak yang sudah diterima renderer."
                    : "Source belum tersedia karena request ini belum memiliki referensi generation yang valid."}
                </p>
                <Button type="button" onClick={() => void loadSource()} disabled={!generationIsValid} className="mt-3 gap-2 bg-emerald-800 text-white hover:bg-emerald-700">
                  <FileCode2 aria-hidden="true" className="size-4" /> Tampilkan source
                </Button>
              </>
            )}
          </div>
        </div>
      )}
      {actionError ? <p className="border-t border-white/10 px-3 py-2 text-xs text-amber-200" role="alert">{actionError}</p> : null}
    </section>
  );
}

function chartPoints(samples: UsageDetail["samples"], field: "utilization_pct" | "memory_used_mib", max: number) {
  const valid = samples.filter((sample) => sample[field] !== null);
  if (valid.length < 2) return "";
  return valid.map((sample, index) => {
    const x = 4 + (index / (valid.length - 1)) * 312;
    const value = sample[field] ?? 0;
    const y = 82 - Math.min(1, value / Math.max(max, 1)) * 74;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(" ");
}

export function UsageGpuDetails({ detail }: { detail: UsageDetail }) {
  const utilizationPoints = chartPoints(detail.samples, "utilization_pct", 100);
  const memoryTotal = detail.samples.reduce((max, sample) => Math.max(max, sample.memory_total_mib ?? 0), 0);
  const memoryPoints = chartPoints(detail.samples, "memory_used_mib", memoryTotal || 1);
  const hasChart = Boolean(utilizationPoints || memoryPoints);

  return (
    <section aria-labelledby="usage-gpu-heading" className="border-t border-border/80 pt-4">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <div>
          <h3 id="usage-gpu-heading" className="text-sm font-semibold text-foreground">Sumber daya run ini</h3>
          <p className="mt-0.5 text-xs leading-relaxed text-muted-foreground">Sample nvidia-smi membaca seluruh perangkat, bukan proses model saja.</p>
        </div>
        <span className="text-xs tabular-nums text-muted-foreground">{numberLabel(detail.gpu_sample_count)} sampel</span>
      </div>

      {detail.samples.length > 0 ? (
        <>
          {hasChart ? (
            <svg className="mt-3 h-20 w-full rounded-lg bg-[#f7f6f0] p-1 text-primary" viewBox="0 0 320 88" role="img" aria-label={`Grafik dari ${detail.samples.length} sampel GPU untuk run terpilih`}>
              <line x1="4" y1="83" x2="316" y2="83" stroke="currentColor" className="text-border" />
              <line x1="4" y1="45" x2="316" y2="45" stroke="currentColor" strokeDasharray="3 4" className="text-border" />
              {utilizationPoints ? <polyline points={utilizationPoints} fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" /> : null}
              {memoryPoints ? <polyline points={memoryPoints} fill="none" stroke="#b65c3b" strokeWidth="2" strokeDasharray="5 4" strokeLinecap="round" strokeLinejoin="round" /> : null}
            </svg>
          ) : (
            <p className="mt-3 rounded-lg bg-muted/40 p-3 text-xs text-muted-foreground">Satu sampel tersimpan. Grafik memerlukan sedikitnya dua titik.</p>
          )}
          <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-muted-foreground">
            <span className="inline-flex items-center gap-1.5"><i aria-hidden="true" className="size-2 rounded-full bg-primary" />Utilisasi GPU</span>
            <span className="inline-flex items-center gap-1.5"><i aria-hidden="true" className="size-2 rounded-full bg-[#b65c3b]" />Memori GPU</span>
          </div>
        </>
      ) : (
        <p className="mt-3 rounded-lg bg-muted/40 p-3 text-xs leading-relaxed text-muted-foreground">Tidak ada data GPU selama proses generate. Inference dapat terlalu singkat atau telemetri mungkin tidak tersedia.</p>
      )}

      <div className="mt-3 grid grid-cols-2 gap-2 md:grid-cols-3 xl:grid-cols-5">
        <Stat label="GPU" value={detail.gpu_device_name ?? "Belum tersedia"} />
        <Stat label="Rata-rata utilisasi" value={detail.gpu_utilization_mean_pct === null ? "Belum tersedia" : `${numberLabel(detail.gpu_utilization_mean_pct, 1)}%`} />
        <Stat label="Puncak memori perangkat" value={memoryLabel(detail.gpu_memory_max_mib)} />
        <Stat label="Suhu maksimum" value={detail.gpu_temperature_max_c === null ? "Belum tersedia" : `${numberLabel(detail.gpu_temperature_max_c)} °C`} />
        <Stat label="Daya rata-rata" value={detail.gpu_power_mean_w === null ? "Belum tersedia" : `${numberLabel(detail.gpu_power_mean_w, 1)} W`} />
        <Stat label="Clock SM rata-rata" value={detail.gpu_sm_clock_mean_mhz === null ? "Belum tersedia" : `${numberLabel(detail.gpu_sm_clock_mean_mhz)} MHz`} />
      </div>

      <details className="group mt-3 border-t border-border/80 pt-3">
        <summary className="cursor-pointer text-xs font-medium text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
          Detail memori PyTorch
        </summary>
        <p className="mt-1 text-[11px] text-muted-foreground">Metrik proses model, terpisah dari pemakaian total perangkat.</p>
        <div className="mt-2 grid grid-cols-2 gap-2 lg:grid-cols-4">
          <Stat label="Allocated baseline" value={memoryLabel(detail.torch_allocated_baseline_bytes === null ? null : detail.torch_allocated_baseline_bytes / 1024 / 1024)} />
          <Stat label="Allocated peak" value={memoryLabel(detail.torch_allocated_peak_bytes === null ? null : detail.torch_allocated_peak_bytes / 1024 / 1024)} />
          <Stat label="Allocated delta" value={memoryLabel(detail.torch_allocated_delta_bytes === null ? null : detail.torch_allocated_delta_bytes / 1024 / 1024)} />
          <Stat label="Reserved peak" value={memoryLabel(detail.torch_reserved_peak_bytes === null ? null : detail.torch_reserved_peak_bytes / 1024 / 1024)} />
        </div>
      </details>
    </section>
  );
}

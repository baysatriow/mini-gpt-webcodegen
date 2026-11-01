"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  Activity,
  AlertCircle,
  ArrowLeft,
  Check,
  Copy,
  Cpu,
  LoaderCircle,
  Menu,
  RefreshCw,
  Search,
} from "lucide-react";
import { HistorySidebar } from "@/components/chat/history-sidebar";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetTitle } from "@/components/ui/sheet";
import {
  FAILURE_LABELS,
  OUTCOME_LABELS,
  STAGE_LABELS,
  OutcomeBadge,
  UsageEventLog,
  UsageEvidence,
  UsageGpuDetails,
  UsageSourcePanel,
  UsageStageRail,
  dateLabel,
  durationLabel,
  memoryLabel,
  numberLabel,
  outcomeLabel,
  percentLabel,
  recordTitle,
  shortId,
} from "@/components/usage/usage-components";
import { copyTextToClipboard } from "@/lib/clipboard";
import { createChatSession, type ChatSession } from "@/lib/chat-state";
import { readChatHistory, writeChatHistory } from "@/lib/history-storage";
import {
  getCurrentGpu,
  getUsageDetail,
  getUsagePage,
  getUsageSummary,
  type CurrentGpu,
  type UsageDetail,
  type UsageOutcome,
  type UsageRecord,
  type UsageStage,
  type UsageSummary,
  type UsageWindow,
} from "@/lib/usage-client";
import { cn } from "@/lib/utils";

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

function StatLine({ label, value, detail }: { label: string; value: string; detail?: string }) {
  return (
    <div className="min-w-0 px-3 py-2.5 first:pl-0 last:pr-0">
      <p className="text-[10px] leading-4 text-muted-foreground">{label}</p>
      <p className="mt-0.5 whitespace-normal break-words text-sm font-semibold leading-5 text-foreground">{value}</p>
      {detail ? <p className="mt-0.5 text-[10px] leading-4 text-muted-foreground">{detail}</p> : null}
    </div>
  );
}

function SummaryBand({ summary, gpu, summaryError, gpuError }: {
  summary: UsageSummary | null;
  gpu: CurrentGpu | null;
  summaryError: string | null;
  gpuError: boolean;
}) {
  const summaryPlaceholder = summaryError ? "Belum tersedia" : "Memuat";
  const unavailableGpu = gpuError || gpu?.available === false;
  const gpuName = gpu?.device_name ?? (unavailableGpu ? "Telemetri GPU belum tersedia" : "Membaca status perangkat...");
  const currentUtilization = gpu?.available && gpu.utilization_pct !== null
    ? `${numberLabel(gpu.utilization_pct, 1)}%`
    : "Belum tersedia";
  const currentMemory = gpu?.available && gpu.memory_used_mib !== null
    ? `${memoryLabel(gpu.memory_used_mib)} / ${memoryLabel(gpu.memory_total_mib)}`
    : "Belum tersedia";
  const currentTemperature = gpu?.available && gpu.temperature_c !== null
    ? `${numberLabel(gpu.temperature_c)} °C`
    : "Belum tersedia";
  const currentPower = gpu?.available && gpu.power_w !== null
    ? `${numberLabel(gpu.power_w, 1)} W`
    : "Belum tersedia";

  return (
    <section className="shrink-0 border-b border-border bg-card" aria-label="Ringkasan penggunaan dan GPU">
      <div className="grid grid-cols-2 divide-x divide-y divide-border/80 sm:grid-cols-4 sm:divide-y-0">
        <StatLine label="Request" value={summary ? numberLabel(summary.total_requests) : summaryPlaceholder} detail={summary ? `${numberLabel(summary.inference_started)} memulai inference` : undefined} />
        <StatLine label="Berhasil" value={summary ? numberLabel(summary.completed) : summaryPlaceholder} detail={summary ? `Rasio ${percentLabel(summary.success_rate_all)}` : undefined} />
        <StatLine label="Gagal / ditolak" value={summary ? `${numberLabel(summary.failed)} / ${numberLabel(summary.rejected)}` : summaryPlaceholder} detail={summary ? `${numberLabel(summary.interrupted)} terhenti` : undefined} />
        <StatLine label="Durasi rata-rata sukses" value={summary ? durationLabel(summary.mean_duration_ms) : summaryPlaceholder} />
      </div>

      <div className="grid min-w-0 border-t border-border/80 lg:grid-cols-[minmax(230px,0.8fr)_minmax(0,1.5fr)]">
        <div className="min-w-0 border-b border-border/80 px-4 py-2.5 lg:border-b-0 lg:border-r">
          <div className="flex items-center gap-2">
            <Cpu aria-hidden="true" className="size-4 shrink-0 text-primary" />
            <p className="truncate text-xs font-medium text-foreground">{gpuName}</p>
            <span className={cn(
              "ml-auto shrink-0 rounded-full border px-2 py-0.5 text-[10px] font-medium",
              gpu?.available ? "border-emerald-200 bg-emerald-50 text-emerald-900" : "border-border bg-muted text-muted-foreground",
            )}>
              {gpu?.available ? "Snapshot sekarang" : "Tidak tersedia"}
            </span>
          </div>
          <p className="mt-1.5 text-[11px] leading-4 text-muted-foreground">
            Utilisasi {currentUtilization} <span aria-hidden="true">·</span> Memori {currentMemory}
            <span aria-hidden="true"> · </span>Suhu {currentTemperature}<span aria-hidden="true"> · </span>Daya {currentPower}
            {gpu?.sampled_at ? ` · Dibaca ${dateLabel(gpu.sampled_at)}` : ""}
          </p>
        </div>

        <div className="grid grid-cols-2 divide-x divide-border/80 sm:grid-cols-4">
          <StatLine label="Sample pada periode" value={summary ? numberLabel(summary.gpu_sample_count) : summaryPlaceholder} detail={summary ? `${numberLabel(summary.gpu_run_count)} run` : undefined} />
          <StatLine label="Cakupan run" value={summary ? percentLabel(summary.gpu_coverage_ratio) : summaryPlaceholder} detail={summary ? `${numberLabel(summary.gpu_run_count)} dari ${numberLabel(summary.inference_started)} inference` : undefined} />
          <StatLine label="Rata-rata utilisasi" value={summary?.gpu_utilization_mean_pct === null || !summary ? summaryPlaceholder : `${numberLabel(summary.gpu_utilization_mean_pct, 1)}%`} />
          <StatLine label="Puncak memori perangkat" value={summary ? memoryLabel(summary.gpu_memory_max_mib) : summaryPlaceholder} />
        </div>
      </div>
      {summary ? (
        <details className="border-t border-border/80 px-4 py-2.5">
          <summary className="cursor-pointer text-[11px] font-medium text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">Metrik periode lainnya</summary>
          <div className="mt-1 grid grid-cols-2 divide-x divide-border/80 sm:grid-cols-5">
            <StatLine label="Puncak utilisasi" value={summary.gpu_utilization_max_pct === null ? "Belum tersedia" : `${numberLabel(summary.gpu_utilization_max_pct, 1)}%`} />
            <StatLine label="Rata-rata memori perangkat" value={memoryLabel(summary.gpu_memory_mean_mib)} />
            <StatLine label="Kapasitas memori" value={memoryLabel(summary.gpu_memory_total_mib)} />
            <StatLine label="Suhu maksimum" value={summary.gpu_temperature_max_c === null ? "Belum tersedia" : `${numberLabel(summary.gpu_temperature_max_c)} °C`} />
            <StatLine label="Daya / clock rata-rata" value={`${summary.gpu_power_mean_w === null ? "Belum tersedia" : `${numberLabel(summary.gpu_power_mean_w, 1)} W`} / ${summary.gpu_sm_clock_mean_mhz === null ? "Belum tersedia" : `${numberLabel(summary.gpu_sm_clock_mean_mhz)} MHz`}`} />
          </div>
        </details>
      ) : null}
      {summaryError ? <p role="status" className="border-t border-border/80 px-4 py-2 text-xs text-amber-900">Ringkasan periode belum tersedia. Riwayat tetap dapat diperiksa. {summaryError}</p> : null}
      {summary?.gpu_scope ? <p className="border-t border-border/70 px-4 py-1.5 text-[10px] leading-4 text-muted-foreground">{summary.gpu_scope}</p> : null}
    </section>
  );
}

function RunList({
  records,
  selectedId,
  loading,
  pageError,
  summary,
  query,
  status,
  stage,
  nextCursor,
  loadingMore,
  onQueryChange,
  onStatusChange,
  onStageChange,
  onSelect,
  onLoadMore,
  onRetry,
}: {
  records: UsageRecord[];
  selectedId: string | null;
  loading: boolean;
  pageError: string | null;
  summary: UsageSummary | null;
  query: string;
  status: UsageOutcome | "";
  stage: UsageStage | "";
  nextCursor: string | null;
  loadingMore: boolean;
  onQueryChange: (value: string) => void;
  onStatusChange: (value: UsageOutcome | "") => void;
  onStageChange: (value: UsageStage | "") => void;
  onSelect: (record: UsageRecord) => void;
  onLoadMore: () => void;
  onRetry: () => void;
}) {
  const hasFilters = Boolean(query.trim() || status || stage);

  return (
    <>
      <div className="shrink-0 border-b border-border px-3.5 pb-3 pt-3.5 sm:px-4">
        <div className="flex items-baseline justify-between gap-2">
          <h2 className="text-sm font-semibold text-foreground">Riwayat pembuatan</h2>
          <span className="text-xs tabular-nums text-muted-foreground">{numberLabel(records.length)} ditampilkan</span>
        </div>
        <label className="relative mt-3 block">
          <span className="sr-only">Cari prompt dan fakta</span>
          <Search aria-hidden="true" className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          <input
            value={query}
            onChange={(event) => onQueryChange(event.target.value.slice(0, 200))}
            maxLength={200}
            type="search"
            placeholder="Cari prompt atau fakta..."
            className="h-10 w-full rounded-lg border border-input bg-background pl-9 pr-3 text-xs text-foreground placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          />
        </label>
        <div className="mt-2 grid grid-cols-2 gap-2">
          <label>
            <span className="sr-only">Filter status</span>
            <select value={status} onChange={(event) => onStatusChange(event.target.value as UsageOutcome | "")} className="h-9 w-full min-w-0 rounded-lg border border-input bg-background px-2 text-xs text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
              <option value="">Semua status</option>
              {(Object.keys(OUTCOME_LABELS) as UsageOutcome[]).map((outcome) => <option key={outcome} value={outcome}>{outcomeLabel(outcome)}</option>)}
            </select>
          </label>
          <label>
            <span className="sr-only">Filter tahap</span>
            <select value={stage} onChange={(event) => onStageChange(event.target.value as UsageStage | "")} className="h-9 w-full min-w-0 rounded-lg border border-input bg-background px-2 text-xs text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
              <option value="">Semua tahap</option>
              {STAGE_OPTIONS.map((item) => <option key={item} value={item}>{STAGE_LABELS[item]}</option>)}
            </select>
          </label>
        </div>
        {hasFilters ? (
          <button type="button" onClick={() => { onQueryChange(""); onStatusChange(""); onStageChange(""); }} className="mt-2 text-xs font-medium text-primary underline underline-offset-4 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
            Hapus filter
          </button>
        ) : null}
      </div>

      {pageError ? (
        <div className="mx-3 mt-3 rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-xs text-destructive sm:mx-4" role="alert">
          <p className="leading-relaxed">{pageError}{records.length ? " Daftar terakhir yang berhasil dimuat tetap ditampilkan." : ""}</p>
          <Button type="button" variant="outline" size="sm" onClick={onRetry} className="mt-2 h-7 rounded-md">Coba lagi</Button>
        </div>
      ) : null}

      <div className="min-h-0 flex-1 overflow-y-auto px-2.5 py-2.5 sm:px-3">
        {loading && records.length === 0 ? (
          <p className="flex items-center justify-center gap-2 py-10 text-xs text-muted-foreground" role="status"><LoaderCircle aria-hidden="true" className="size-4 animate-spin" /> Memuat riwayat...</p>
        ) : pageError && records.length === 0 ? (
          <p className="px-3 py-5 text-center text-xs text-muted-foreground" role="status">Riwayat belum dapat ditampilkan.</p>
        ) : records.length ? (
          <ul className="space-y-1.5">
            {records.map((record) => {
              const selected = record.usage_id === selectedId;
              return (
                <li key={record.usage_id}>
                  <button
                    type="button"
                    onClick={() => onSelect(record)}
                    aria-pressed={selected}
                    className={cn(
                      "w-full min-w-0 rounded-lg border px-3 py-2.5 text-left transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                      selected
                        ? "border-[#b65c3b] bg-[#fff5ef]"
                        : "border-transparent bg-transparent hover:border-border hover:bg-card",
                    )}
                  >
                    <span className="flex min-w-0 items-start justify-between gap-2">
                      <span className="line-clamp-2 min-w-0 text-xs font-semibold leading-5 text-foreground">{recordTitle(record)}</span>
                      {selected ? <span className="shrink-0 rounded-full border border-[#d77a54]/40 bg-white px-1.5 py-0.5 text-[9px] font-medium text-[#8d3e25]">Terpilih</span> : null}
                    </span>
                    <span className="mt-2 flex flex-wrap items-center justify-between gap-x-2 gap-y-1">
                      <OutcomeBadge outcome={record.outcome} />
                      <span className="text-[10px] tabular-nums text-muted-foreground">{durationLabel(record.duration_ms)}</span>
                    </span>
                    <span className="mt-1.5 flex min-w-0 items-center justify-between gap-2 text-[10px] leading-4 text-muted-foreground">
                      <span className="truncate">{dateLabel(record.started_at)}</span>
                      <span className="shrink-0">{record.failure_code ? FAILURE_LABELS[record.failure_code] : record.stage.replaceAll("_", " ")}</span>
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
        ) : (
          <div className="px-3 py-8 text-center">
            <Activity aria-hidden="true" className="mx-auto size-5 text-muted-foreground" />
            <h3 className="mt-2 text-sm font-medium text-foreground">{hasFilters ? "Tidak ada hasil" : "Belum ada aktivitas"}</h3>
            <p className="mx-auto mt-1 max-w-xs text-xs leading-relaxed text-muted-foreground">
              {hasFilters
                ? "Coba hapus filter atau gunakan kata pencarian yang berbeda."
                : summary?.total_requests
                  ? "Tidak ada run yang cocok pada filter saat ini."
                  : "Request generate akan muncul di sini, termasuk yang ditolak saat validasi."}
            </p>
            {!hasFilters && !summary?.total_requests ? <Link href="/" className="mt-3 inline-flex text-xs font-medium text-primary underline underline-offset-4">Kembali ke chat</Link> : null}
          </div>
        )}
        {nextCursor ? (
          <div className="flex justify-center py-3">
            <Button type="button" variant="outline" size="sm" onClick={onLoadMore} disabled={loadingMore} className="rounded-lg">
              {loadingMore ? <LoaderCircle aria-hidden="true" className="size-3.5 animate-spin" /> : null}
              {loadingMore ? "Memuat..." : "Muat aktivitas berikutnya"}
            </Button>
          </div>
        ) : null}
      </div>
    </>
  );
}

function RunDetailHeader({ record, detail, onBack }: {
  record: UsageRecord | null;
  detail: UsageDetail | null;
  onBack: () => void;
}) {
  const [copyStatus, setCopyStatus] = useState<"idle" | "copied" | "failed">("idle");
  const usageId = detail?.usage_id ?? record?.usage_id ?? null;
  const outcome = detail?.outcome ?? record?.outcome;
  const startedAt = detail?.started_at ?? record?.started_at;
  const duration = detail?.duration_ms ?? record?.duration_ms;

  async function copyRunId() {
    if (!usageId) return;
    const copied = await copyTextToClipboard(usageId);
    setCopyStatus(copied ? "copied" : "failed");
    window.setTimeout(() => setCopyStatus("idle"), 1800);
  }

  return (
    <header className="sticky top-0 z-10 flex min-h-[60px] shrink-0 items-center justify-between gap-3 border-b border-border bg-card/95 px-3 py-2 backdrop-blur-sm sm:px-4">
      <div className="flex min-w-0 items-center gap-2">
        <Button type="button" variant="ghost" size="icon" onClick={onBack} aria-label="Kembali ke daftar riwayat" className="size-8 shrink-0 rounded-lg lg:hidden">
          <ArrowLeft aria-hidden="true" className="size-4" />
        </Button>
        <div className="min-w-0">
          <p className="truncate text-xs font-semibold text-foreground">{record ? recordTitle(detail ?? record) : "Detail run"}</p>
          <div className="flex min-w-0 flex-wrap items-center gap-x-1.5 text-[10px] leading-4 text-muted-foreground">
            {startedAt ? <span>{dateLabel(startedAt)}</span> : <span>Pilih run dari riwayat</span>}
            {usageId ? <><span aria-hidden="true">·</span><span>ID {shortId(usageId)}</span></> : null}
            {duration !== undefined ? <><span aria-hidden="true">·</span><span>{durationLabel(duration)}</span></> : null}
          </div>
        </div>
      </div>
      <div className="flex shrink-0 items-center gap-2">
        {usageId ? (
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={() => void copyRunId()}
            className="h-8 gap-1.5 rounded-lg px-2 text-[10px] sm:text-xs"
            aria-label={copyStatus === "copied" ? "ID tersalin" : copyStatus === "failed" ? "Gagal menyalin ID" : "Salin ID lengkap"}
            aria-live="polite"
          >
            {copyStatus === "copied" ? <Check aria-hidden="true" className="size-3.5" /> : <Copy aria-hidden="true" className="size-3.5" />}
            <span className="hidden sm:inline">{copyStatus === "copied" ? "ID tersalin" : copyStatus === "failed" ? "Gagal menyalin" : "Salin ID"}</span>
          </Button>
        ) : null}
        {outcome ? <OutcomeBadge outcome={outcome} /> : null}
      </div>
    </header>
  );
}

function RunDetail({ detail, loading, error, onRetry }: {
  detail: UsageDetail | null;
  loading: boolean;
  error: string | null;
  onRetry: () => void;
}) {
  if (loading) {
    return <div className="flex min-h-64 flex-1 items-center justify-center text-sm text-muted-foreground" role="status"><LoaderCircle aria-hidden="true" className="mr-2 size-4 animate-spin" /> Memuat detail audit...</div>;
  }
  if (error) {
    return (
      <div className="flex min-h-64 flex-1 items-center justify-center px-5">
        <div className="max-w-sm text-center">
          <AlertCircle aria-hidden="true" className="mx-auto size-5 text-destructive" />
          <p className="mt-2 text-sm leading-relaxed text-destructive" role="alert">{error}</p>
          <Button type="button" variant="outline" size="sm" onClick={onRetry} className="mt-3 gap-1.5 rounded-lg"><RefreshCw aria-hidden="true" className="size-3.5" /> Coba lagi</Button>
        </div>
      </div>
    );
  }
  if (!detail) {
    return (
      <div className="flex min-h-64 flex-1 items-center justify-center px-6 text-center">
        <div className="max-w-sm">
          <Activity aria-hidden="true" className="mx-auto size-6 text-muted-foreground" />
          <h2 className="mt-3 text-base font-semibold text-foreground">Pilih satu run untuk diperiksa</h2>
          <p className="mt-1 text-sm leading-relaxed text-muted-foreground">Detail audit menampilkan input, fakta yang dikonfirmasi, tahapan proses, source yang diterima, dan telemetry perangkat.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-w-0 flex-1 space-y-4 p-3 sm:p-4 xl:p-5">
      <div className="grid min-w-0 gap-4 xl:grid-cols-[minmax(0,0.82fr)_minmax(0,1.18fr)]">
        <div className="min-w-0 rounded-xl border border-border bg-card p-3 sm:p-4">
          <UsageEvidence detail={detail} />
        </div>
        <div className="grid min-w-0 gap-4 lg:grid-cols-[minmax(116px,0.28fr)_minmax(0,1fr)]">
          <div className="min-w-0 rounded-xl border border-border bg-card p-3 sm:p-4">
            <UsageStageRail detail={detail} />
          </div>
          <UsageSourcePanel generationId={detail.generation_id} />
        </div>
      </div>

      <div className="rounded-xl border border-border bg-card p-3 sm:p-4">
        <UsageGpuDetails detail={detail} />
        <UsageEventLog detail={detail} />
      </div>

      <dl className="grid grid-cols-2 gap-2 border-t border-border/80 pt-3 sm:grid-cols-4">
        <div><dt className="text-[10px] text-muted-foreground">HTTP</dt><dd className="mt-0.5 text-xs font-medium text-foreground">{detail.http_status ?? "Belum tersedia"}</dd></div>
        <div><dt className="text-[10px] text-muted-foreground">Token masuk / keluar</dt><dd className="mt-0.5 text-xs font-medium text-foreground">{numberLabel(detail.input_tokens)} / {numberLabel(detail.output_tokens)}</dd></div>
        <div><dt className="text-[10px] text-muted-foreground">Seksi / percobaan</dt><dd className="mt-0.5 text-xs font-medium text-foreground">{numberLabel(detail.section_count)} / {numberLabel(detail.attempt_count)}{detail.retry_count ? ` · ${detail.retry_count} retry` : ""}</dd></div>
        <div><dt className="text-[10px] text-muted-foreground">Status renderer</dt><dd className="mt-0.5 break-words text-xs font-medium text-foreground">{detail.renderer_status ?? "Belum tersedia"}</dd></div>
      </dl>
    </div>
  );
}

export function UsageDashboard({ showLogout = false }: { showLogout?: boolean }) {
  const router = useRouter();
  const [period, setPeriod] = useState<UsageWindow>("24h");
  const [status, setStatus] = useState<UsageOutcome | "">("");
  const [stage, setStage] = useState<UsageStage | "">("");
  const [query, setQuery] = useState("");
  const [searchTerm, setSearchTerm] = useState("");
  const [summary, setSummary] = useState<UsageSummary | null>(null);
  const [gpu, setGpu] = useState<CurrentGpu | null>(null);
  const [gpuError, setGpuError] = useState(false);
  const [records, setRecords] = useState<UsageRecord[]>([]);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [pageError, setPageError] = useState<string | null>(null);
  const [summaryError, setSummaryError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<UsageDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [detailVersion, setDetailVersion] = useState(0);
  const [mobileView, setMobileView] = useState<"list" | "detail">("list");
  const [historyOpen, setHistoryOpen] = useState(false);
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [navigationError, setNavigationError] = useState<string | null>(null);
  const refreshSequence = useRef(0);

  useEffect(() => {
    const timer = globalThis.setTimeout(() => {
      const history = readChatHistory();
      setSessions(history.sessions);
      setActiveSessionId(history.activeSessionId);
    }, 0);
    return () => globalThis.clearTimeout(timer);
  }, []);

  useEffect(() => {
    const timer = globalThis.setTimeout(() => setSearchTerm(query.trim()), 280);
    return () => globalThis.clearTimeout(timer);
  }, [query]);

  const refresh = useCallback(async (quiet = false) => {
    const sequence = ++refreshSequence.current;
    if (!quiet) setRefreshing(true);
    setPageError(null);
    setSummaryError(null);
    const gpuRequest = getCurrentGpu();
    const [nextSummary, page] = await Promise.allSettled([
      getUsageSummary(period),
      getUsagePage({ window: period, status, stage, q: searchTerm, limit: 25 }),
    ]);
    if (sequence !== refreshSequence.current) return;

    if (nextSummary.status === "fulfilled") {
      setSummary(nextSummary.value);
    } else {
      setSummary(null);
      setSummaryError(nextSummary.reason instanceof Error ? nextSummary.reason.message : "Ringkasan Usage tidak dapat dimuat.");
    }

    if (page.status === "fulfilled") {
      setDetail(null);
      setDetailError(null);
      setRecords(page.value.items);
      setNextCursor(page.value.next_cursor);
      setSelectedId((current) => page.value.items.some((record) => record.usage_id === current)
        ? current
        : page.value.items[0]?.usage_id ?? null);
      setPageError(null);
    } else {
      setPageError(page.reason instanceof Error ? page.reason.message : "Riwayat Usage tidak dapat dimuat.");
    }

    void gpuRequest.then((value) => {
      if (sequence !== refreshSequence.current) return;
      setGpu(value);
      setGpuError(false);
    }).catch(() => {
      if (sequence !== refreshSequence.current) return;
      setGpu(null);
      setGpuError(true);
    });
    setLoading(false);
    setRefreshing(false);
    setDetailVersion((value) => value + 1);
  }, [period, searchTerm, stage, status]);

  useEffect(() => {
    const timer = globalThis.setTimeout(() => void refresh(true), 0);
    return () => globalThis.clearTimeout(timer);
  }, [refresh]);

  useEffect(() => {
    const poll = () => {
      if (document.visibilityState !== "visible") return;
      void getCurrentGpu().then((value) => {
        setGpu(value);
        setGpuError(false);
      }).catch(() => {
        setGpu(null);
        setGpuError(true);
      });
    };
    const timer = globalThis.setInterval(poll, 15_000);
    const onVisibility = () => {
      if (document.visibilityState === "visible") {
        poll();
        void refresh(true);
      }
    };
    document.addEventListener("visibilitychange", onVisibility);
    return () => {
      globalThis.clearInterval(timer);
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, [refresh]);

  useEffect(() => {
    if (!selectedId) return;
    let active = true;
    const timer = globalThis.setTimeout(() => {
      setDetailLoading(true);
      void getUsageDetail(selectedId).then((nextDetail) => {
        if (active) setDetail(nextDetail);
      }).catch((cause: unknown) => {
        if (active) setDetailError(cause instanceof Error ? cause.message : "Detail audit tidak dapat dimuat.");
      }).finally(() => {
        if (active) setDetailLoading(false);
      });
    }, 0);
    return () => {
      active = false;
      globalThis.clearTimeout(timer);
    };
  }, [selectedId, detailVersion]);

  async function loadMore() {
    if (!nextCursor || loadingMore) return;
    setLoadingMore(true);
    setPageError(null);
    try {
      const page = await getUsagePage({ cursor: nextCursor, window: period, status, stage, q: searchTerm, limit: 25 });
      setRecords((current) => {
        const seen = new Set(current.map((record) => record.usage_id));
        return [...current, ...page.items.filter((record) => !seen.has(record.usage_id))];
      });
      setNextCursor(page.next_cursor);
    } catch (cause) {
      setPageError(cause instanceof Error ? cause.message : "Aktivitas berikutnya tidak dapat dimuat.");
    } finally {
      setLoadingMore(false);
    }
  }

  function persistHistory(nextSessions: ChatSession[], nextActiveId: string | null) {
    const saved = writeChatHistory({
      sessions: nextSessions,
      activeSessionId: nextActiveId,
      restored: true,
    });
    if (!saved) setNavigationError("Riwayat browser tidak dapat diperbarui. Periksa izin penyimpanan browser.");
    return saved;
  }

  function startChat() {
    const session = createChatSession();
    const nextSessions = [session, ...sessions];
    if (!persistHistory(nextSessions, session.id)) return;
    setNavigationError(null);
    router.push("/");
  }

  function selectChat(sessionId: string) {
    if (!sessions.some((session) => session.id === sessionId)) return;
    if (!persistHistory(sessions, sessionId)) return;
    setNavigationError(null);
    router.push("/");
  }

  function deleteChat(sessionId: string) {
    const nextSessions = sessions.filter((session) => session.id !== sessionId);
    const nextActiveId = activeSessionId === sessionId ? nextSessions[0]?.id ?? null : activeSessionId;
    if (!persistHistory(nextSessions, nextActiveId)) return;
    setSessions(nextSessions);
    setActiveSessionId(nextActiveId);
    setNavigationError(null);
  }

  const historyProps = {
    sessions,
    activeSessionId: null,
    activeSection: "usage" as const,
    onNew: startChat,
    onSelect: selectChat,
    onDelete: deleteChat,
    showLogout,
  };

  function selectRecord(record: UsageRecord) {
    setDetail(null);
    setDetailError(null);
    setDetailLoading(true);
    setSelectedId(record.usage_id);
    setMobileView("detail");
  }

  function retryDetail() {
    setDetail(null);
    setDetailError(null);
    setDetailLoading(true);
    setDetailVersion((value) => value + 1);
  }

  const selectedRecord = records.find((record) => record.usage_id === selectedId) ?? null;

  return (
    <main className="flex h-svh min-h-svh overflow-hidden bg-background text-foreground">
      <aside aria-label="Navigasi utama" className="hidden w-[260px] shrink-0 border-r border-border bg-sidebar lg:flex">
        <HistorySidebar {...historyProps} className="w-[260px]" />
      </aside>

      <div className="flex min-h-0 min-w-0 flex-1 flex-col">
        <header className="flex min-h-[58px] shrink-0 items-center justify-between gap-3 border-b border-border bg-card px-3 sm:px-4">
          <div className="flex min-w-0 items-center gap-2.5">
            <div className="lg:hidden">
              <Sheet open={historyOpen} onOpenChange={setHistoryOpen}>
                <Button type="button" variant="ghost" size="icon" onClick={() => setHistoryOpen(true)} aria-label="Buka navigasi utama" className="size-9 rounded-lg">
                  <Menu aria-hidden="true" className="size-4" />
                </Button>
                <SheetContent side="left" showCloseButton={false} className="w-[min(88vw,300px)] max-w-none p-0">
                  <SheetTitle className="sr-only">Navigasi WebCraft</SheetTitle>
                  <HistorySidebar {...historyProps} className="w-full" />
                </SheetContent>
              </Sheet>
            </div>
            <div className="min-w-0">
              <h1 className="truncate text-base font-semibold tracking-tight text-foreground sm:text-lg">Penggunaan</h1>
              <p className="hidden text-[11px] leading-4 text-muted-foreground sm:block">Audit input, hasil, tahapan, dan sumber daya tiap generate.</p>
            </div>
          </div>
          <div className="flex shrink-0 items-center gap-2">
            <label htmlFor="usage-period" className="sr-only">Periode ringkasan dan riwayat</label>
            <select id="usage-period" value={period} onChange={(event) => setPeriod(event.target.value as UsageWindow)} className="h-9 rounded-lg border border-input bg-background px-2.5 text-xs text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring sm:h-10 sm:text-sm">
              <option value="24h">24 jam</option>
              <option value="7d">7 hari</option>
              <option value="30d">30 hari</option>
            </select>
            <Button type="button" variant="outline" size="icon" aria-label="Muat ulang Usage" onClick={() => void refresh()} disabled={refreshing} className="size-9 rounded-lg bg-card sm:size-10">
              <RefreshCw aria-hidden="true" className={cn("size-4", refreshing && "animate-spin")} />
            </Button>
          </div>
        </header>

        {navigationError ? <p role="alert" className="shrink-0 border-b border-amber-300 bg-amber-50 px-4 py-2 text-xs text-amber-950">{navigationError}</p> : null}
        <SummaryBand summary={summary} gpu={gpu} summaryError={summaryError} gpuError={gpuError} />

        <div className="flex min-h-0 min-w-0 flex-1">
          <section
            aria-label="Daftar riwayat generate"
            className={cn(
              "min-h-0 min-w-0 flex-col bg-background",
              mobileView === "list" ? "flex" : "hidden",
              "lg:flex lg:w-[300px] lg:shrink-0 lg:border-r lg:border-border xl:w-[318px]",
            )}
          >
            <RunList
              records={records}
              selectedId={selectedId}
              loading={loading}
              pageError={pageError}
              summary={summary}
              query={query}
              status={status}
              stage={stage}
              nextCursor={nextCursor}
              loadingMore={loadingMore}
              onQueryChange={setQuery}
              onStatusChange={setStatus}
              onStageChange={setStage}
              onSelect={selectRecord}
              onLoadMore={() => void loadMore()}
              onRetry={() => void refresh()}
            />
          </section>

          <section
            aria-label="Detail audit inference"
            className={cn(
              "min-h-0 min-w-0 flex-1 flex-col overflow-y-auto bg-background",
              mobileView === "detail" ? "flex" : "hidden",
              "lg:flex",
            )}
          >
            <RunDetailHeader record={selectedRecord} detail={detail} onBack={() => setMobileView("list")} />
            <RunDetail
              detail={detail}
              loading={detailLoading}
              error={detailError}
              onRetry={retryDetail}
            />
          </section>
        </div>
      </div>
    </main>
  );
}

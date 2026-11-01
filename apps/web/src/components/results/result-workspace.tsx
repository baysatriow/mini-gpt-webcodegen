"use client";

import { useEffect, useState } from "react";
import {
  AlertCircle,
  Code2,
  Download,
  Eye,
  LoaderCircle,
  Maximize2,
  Monitor,
  Smartphone,
  Tablet,
} from "lucide-react";
import { PreviewFrame, type ViewportMode } from "@/components/results/preview-frame";
import { SourceTabs, type SourceLoadState } from "@/components/results/source-tabs";
import type { GenerationSummary, GenerationStatus, SourceFilename } from "@/lib/api-types";
import { getAcceptedDownloadUrl, getAcceptedPreviewUrl } from "@/lib/preview-url";
import { cn } from "@/lib/utils";

export type WorkspaceView = "preview" | "code";

type ResultWorkspaceProps = {
  summary: GenerationSummary | null;
  status: "pending" | GenerationStatus | null;
  statusMessage: string | null;
  view: WorkspaceView;
  onViewChange: (view: WorkspaceView) => void;
  sourceState: SourceLoadState;
  onLoadSource: (generationId: string, force?: boolean) => void;
  onDownloadSource: (generationId: string, filename: SourceFilename) => Promise<void>;
};

export function ResultWorkspace({
  summary,
  status,
  statusMessage,
  view,
  onViewChange,
  sourceState,
  onLoadSource,
  onDownloadSource,
}: ResultWorkspaceProps) {
  const [viewport, setViewport] = useState<ViewportMode>("responsive");
  const previewUrl = getAcceptedPreviewUrl(summary);
  const downloadUrl = getAcceptedDownloadUrl(summary);

  useEffect(() => {
    if (view === "code" && summary) onLoadSource(summary.generation_id);
  }, [view, summary, onLoadSource]);

  if (!summary || !previewUrl || !downloadUrl) {
    const pending = status === "pending";
    const failed = status === "generation_failed" || status === "input_too_long" || status === "completed";
    const heading = pending
      ? "Menghasilkan Halaman Web"
      : status === "input_too_long"
        ? "Permintaan Perlu Diringkas"
        : status === "generation_failed"
          ? "Halaman Belum Berhasil Dibuat"
          : status === "completed"
            ? "Data Hasil Tidak Lengkap"
            : "Kanvas Studio Web";
    const description = status === "completed"
      ? "Respons server tidak memiliki referensi hasil yang valid, sehingga pratinjau tidak dapat ditampilkan."
      : statusMessage ?? (pending
        ? "Model menyusun rancangan dan isi bagian halaman. Renderer menyiapkan HTML, CSS, dan JavaScript setelah validasi."
        : "Tulis ide website Anda di kolom percakapan, tinjau ringkasan fakta, lalu klik Generate Website untuk melihat pratinjau live di sini.");

    return (
      <div className="flex h-full min-h-0 flex-1 flex-col">
        {/* Clean minimal header */}
        <div className="flex h-[52px] shrink-0 items-center justify-between border-b border-border bg-card px-4 sm:px-6">
          <div className="flex items-center gap-2">
            <span className="text-xs sm:text-sm font-bold text-foreground">Kanvas & Pratinjau</span>
          </div>
          <span className="rounded-md border border-border bg-muted px-2.5 py-0.5 text-[11px] text-muted-foreground font-medium">
            {pending ? "Memproses..." : "Belum ada hasil"}
          </span>
        </div>

        {/* Empty / Pending State Content */}
        <div className="flex min-h-0 flex-1 items-center justify-center bg-muted/50 p-6 sm:p-10">
          <div className={`w-full max-w-md rounded-2xl border bg-card p-6 sm:p-8 text-center shadow-xs ${
            failed ? "border-destructive/30 bg-red-50/20" : "border-border/80"
          }`}>
            <div className={`mx-auto grid size-13 place-items-center rounded-2xl ${
              pending
                ? "bg-accent text-accent-foreground border border-border"
                : failed
                  ? "bg-red-50 text-destructive border border-red-200"
                  : "bg-secondary text-secondary-foreground border border-border"
            }`}>
              {pending ? (
                <LoaderCircle className="size-6 animate-spin" aria-hidden="true" />
              ) : failed ? (
                <AlertCircle className="size-6" aria-hidden="true" />
              ) : (
                <Monitor className="size-6" aria-hidden="true" />
              )}
            </div>

            <h2 className="mt-4 text-base font-bold text-foreground tracking-tight">{heading}</h2>
            <p className={`mt-2 text-xs sm:text-sm leading-relaxed ${failed ? "text-destructive" : "text-muted-foreground"}`} role={failed ? "alert" : pending ? "status" : undefined}>
              {description}
            </p>

            {!pending && !failed ? (
              <div className="mt-6 pt-5 border-t border-border/80 grid grid-cols-3 gap-2 text-left">
                <div className="p-2.5 rounded-lg bg-muted border border-border">
                  <p className="text-[10px] font-bold text-foreground">Live Sandbox</p>
                  <p className="text-[9px] text-muted-foreground mt-0.5">Desktop & Mobile</p>
                </div>
                <div className="p-2.5 rounded-lg bg-muted border border-border">
                  <p className="text-[10px] font-bold text-foreground">Source HTML</p>
                  <p className="text-[9px] text-muted-foreground mt-0.5">HTML, CSS, JS</p>
                </div>
                <div className="p-2.5 rounded-lg bg-muted border border-border">
                  <p className="text-[10px] font-bold text-foreground">Download ZIP</p>
                  <p className="text-[9px] text-muted-foreground mt-0.5">Source statis</p>
                </div>
              </div>
            ) : null}
          </div>
        </div>
      </div>
    );
  }

  const genreLabel = summary.genre === "company_profile" ? "Company Profile" : "Landing Page";
  const styleLabel = summary.style_mode === "tailwind" ? "Tailwind CSS" : "CSS Murni";

  return (
    <div className="flex h-full min-h-0 flex-1 flex-col overflow-hidden bg-background">
      {/* Studio Top Control Bar */}
      <div className="flex min-h-[52px] shrink-0 flex-wrap items-center justify-between gap-3 border-b border-border bg-card px-3.5 py-2 sm:px-5">
        {/* Left: Project title & badge */}
        <div className="flex min-w-0 items-center gap-2">
          <span className="relative flex size-2 shrink-0" title="Generation selesai" aria-hidden="true">
            <span className="relative inline-flex size-2 rounded-full bg-emerald-600" />
          </span>
          <span className="truncate text-xs sm:text-sm font-bold text-foreground max-w-[140px] sm:max-w-[200px]">
            {summary.business_name || "Halaman Web"}
          </span>
          <span className="hidden sm:inline-flex rounded-md bg-muted px-2 py-0.5 text-[10px] font-medium text-muted-foreground border border-border">
            {genreLabel} · {styleLabel}
          </span>
        </div>

        {/* Center: Segmented Preview / Code Toggle */}
        <div className="inline-flex items-center rounded-lg bg-muted p-0.5 border border-border" role="tablist">
          <button
            type="button"
            role="tab"
            aria-selected={view === "preview"}
            onClick={() => onViewChange("preview")}
            className={cn(
              "inline-flex items-center gap-1.5 rounded-lg px-3 py-1 text-xs font-semibold transition-all cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
              view === "preview"
                ? "bg-card text-primary shadow-2xs font-semibold"
                : "text-muted-foreground hover:text-foreground",
            )}
          >
            <Eye className="size-3.5" />
            <span>Pratinjau</span>
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={view === "code"}
            onClick={() => onViewChange("code")}
            className={cn(
              "inline-flex items-center gap-1.5 rounded-lg px-3 py-1 text-xs font-semibold transition-all cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
              view === "code"
                ? "bg-card text-primary shadow-2xs font-semibold"
                : "text-muted-foreground hover:text-foreground",
            )}
          >
            <Code2 className="size-3.5" />
            <span>Kode Sumber</span>
          </button>
        </div>

        {/* Right: Viewport Mode Switcher & Download CTA */}
        <div className="flex items-center gap-2 shrink-0">
          {view === "preview" ? (
            <div
              className="inline-flex items-center rounded-lg bg-muted p-0.5 border border-border"
              role="group"
              aria-label="Ukuran pratinjau"
            >
              <button
                type="button"
                title="Lebar Penuh (Fit)"
                aria-label="Lebar Penuh"
                aria-pressed={viewport === "responsive"}
                onClick={() => setViewport("responsive")}
                className={cn(
                  "inline-flex items-center gap-1 rounded-lg px-2.5 py-1 text-xs font-semibold transition-all cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                  viewport === "responsive"
                    ? "bg-card text-primary shadow-2xs font-semibold"
                    : "text-muted-foreground hover:text-foreground",
                )}
              >
                <Maximize2 className="size-3" />
                <span className="hidden md:inline">Fit</span>
              </button>
              <button
                type="button"
                title="Desktop (1200px)"
                aria-label="Desktop"
                aria-pressed={viewport === "desktop"}
                onClick={() => setViewport("desktop")}
                className={cn(
                  "inline-flex items-center gap-1 rounded-lg px-2.5 py-1 text-xs font-semibold transition-all cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                  viewport === "desktop"
                    ? "bg-card text-primary shadow-2xs font-semibold"
                    : "text-muted-foreground hover:text-foreground",
                )}
              >
                <Monitor className="size-3" />
                <span className="hidden md:inline">Desktop</span>
              </button>
              <button
                type="button"
                title="Tablet (768px)"
                aria-label="Tablet"
                aria-pressed={viewport === "tablet"}
                onClick={() => setViewport("tablet")}
                className={cn(
                  "inline-flex items-center gap-1 rounded-lg px-2.5 py-1 text-xs font-semibold transition-all cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                  viewport === "tablet"
                    ? "bg-card text-primary shadow-2xs font-semibold"
                    : "text-muted-foreground hover:text-foreground",
                )}
              >
                <Tablet className="size-3" />
                <span className="hidden md:inline">Tablet</span>
              </button>
              <button
                type="button"
                title="Mobile (390px)"
                aria-label="Mobile"
                aria-pressed={viewport === "mobile"}
                onClick={() => setViewport("mobile")}
                className={cn(
                  "inline-flex items-center gap-1 rounded-lg px-2.5 py-1 text-xs font-semibold transition-all cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                  viewport === "mobile"
                    ? "bg-card text-primary shadow-2xs font-semibold"
                    : "text-muted-foreground hover:text-foreground",
                )}
              >
                <Smartphone className="size-3" />
                <span className="hidden md:inline">Mobile</span>
              </button>
            </div>
          ) : null}

          {/* Download */}
          <a
            href={downloadUrl}
            className="inline-flex h-9 items-center gap-1.5 rounded-lg bg-primary px-3.5 text-xs font-semibold text-primary-foreground transition-colors hover:bg-primary/90 active:scale-[0.98] cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            <Download className="size-3.5 stroke-[2.5]" aria-hidden="true" />
            <span className="hidden sm:inline">Unduh</span> ZIP
          </a>
        </div>
      </div>

      {/* Main Studio Canvas Body */}
      {view === "preview" ? (
        <div className="min-h-0 flex-1 overflow-auto bg-muted/50 p-3 sm:p-5 flex flex-col items-start">
          <PreviewFrame
            key={previewUrl}
            generationId={summary.generation_id}
            src={previewUrl}
            title={summary.business_name || "hasil generator"}
            viewport={viewport}
          />
        </div>
      ) : (
        <div className="min-h-0 flex-1 overflow-hidden">
          <SourceTabs
            generationId={summary.generation_id}
            state={sourceState}
            onRetry={onLoadSource}
            onDownload={onDownloadSource}
          />
        </div>
      )}
    </div>
  );
}

"use client";

import { useEffect, useState } from "react";
import {
  AlertCircle,
  Code2,
  Download,
  Eye,
  LoaderCircle,
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
  const [viewport, setViewport] = useState<ViewportMode>("desktop");
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
            : "Kanvas Halaman Web";
    const description = status === "completed"
      ? "Respons server tidak memiliki referensi hasil yang valid, sehingga pratinjau tidak dapat ditampilkan."
      : statusMessage ?? (pending
        ? "Model sedang menyusun kode HTML, styling Tailwind/CSS, dan struktur visual. Pratinjau akan langsung muncul begitu proses selesai."
        : "Tulis ide website Anda di kolom percakapan, tinjau ringkasan fakta, lalu klik Generate Website untuk melihat pratinjau live di sini.");

    return (
      <div className="flex h-full min-h-0 flex-1 flex-col">
        {/* Clean minimal header */}
        <div className="flex h-[50px] shrink-0 items-center justify-between border-b border-border bg-card px-4 sm:px-6">
          <div className="flex items-center gap-2">
            <span className="text-xs sm:text-sm font-semibold text-foreground">Kanvas & Pratinjau</span>
          </div>
          <span className="rounded-full border border-border bg-slate-50 px-2.5 py-0.5 text-[11px] text-muted-foreground font-medium">
            {pending ? "Memproses..." : "Belum ada hasil"}
          </span>
        </div>

        {/* Empty / Pending State Content */}
        <div className="flex min-h-0 flex-1 items-center justify-center p-6 sm:p-10 bg-slate-50/50">
          <div className={`w-full max-w-md rounded-2xl border bg-card p-6 sm:p-8 text-center shadow-xs ${
            failed ? "border-destructive/30 bg-red-50/20" : "border-border/80"
          }`}>
            <div className={`mx-auto grid size-12 place-items-center rounded-2xl ${
              pending
                ? "bg-blue-50 text-primary border border-blue-200"
                : failed
                  ? "bg-red-50 text-destructive border border-red-200"
                  : "bg-gradient-to-tr from-slate-100 to-blue-50 text-primary border border-border"
            }`}>
              {pending ? (
                <LoaderCircle className="size-6 animate-spin" aria-hidden="true" />
              ) : failed ? (
                <AlertCircle className="size-6" aria-hidden="true" />
              ) : (
                <Monitor className="size-6" aria-hidden="true" />
              )}
            </div>

            <h2 className="mt-4 text-base font-semibold text-foreground tracking-tight">{heading}</h2>
            <p className={`mt-2 text-xs sm:text-sm leading-relaxed ${failed ? "text-destructive" : "text-muted-foreground"}`} role={failed ? "alert" : pending ? "status" : undefined}>
              {description}
            </p>

            {!pending && !failed ? (
              <div className="mt-6 pt-5 border-t border-border/80 grid grid-cols-3 gap-2 text-left">
                <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-100">
                  <p className="text-[10px] font-semibold text-foreground">Live Sandbox</p>
                  <p className="text-[9px] text-muted-foreground mt-0.5">Desktop & Mobile</p>
                </div>
                <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-100">
                  <p className="text-[10px] font-semibold text-foreground">Clean Code</p>
                  <p className="text-[9px] text-muted-foreground mt-0.5">HTML, CSS, JS</p>
                </div>
                <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-100">
                  <p className="text-[10px] font-semibold text-foreground">Download ZIP</p>
                  <p className="text-[9px] text-muted-foreground mt-0.5">Siap Deploy</p>
                </div>
              </div>
            ) : null}
          </div>
        </div>
      </div>
    );
  }

  const genreLabel = summary.genre === "company_profile" ? "Company Profile" : "Landing Page";
  const styleLabel = summary.style_mode === "tailwind" ? "Tailwind CSS" : "CSS";

  return (
    <div className="flex h-full min-h-0 flex-1 flex-col overflow-hidden bg-background">
      {/* Unified Canvas Top Bar */}
      <div className="flex h-[50px] shrink-0 items-center justify-between gap-3 border-b border-border bg-card px-3.5 sm:px-4">
        {/* Left: Title & genre */}
        <div className="flex min-w-0 items-center gap-2">
          <span className="truncate text-xs sm:text-sm font-semibold text-foreground max-w-[160px] sm:max-w-[240px]">
            {summary.business_name || "Halaman Web"}
          </span>
          <span className="hidden sm:inline-flex rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-medium text-muted-foreground border border-border/60">
            {genreLabel} · {styleLabel}
          </span>
        </div>

        {/* Center: Segmented Preview / Code Toggle */}
        <div className="inline-flex items-center rounded-lg bg-slate-100 p-0.5 border border-border/60" role="tablist">
          <button
            type="button"
            role="tab"
            aria-selected={view === "preview"}
            onClick={() => onViewChange("preview")}
            className={cn(
              "inline-flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-medium transition-all",
              view === "preview"
                ? "bg-white text-foreground shadow-2xs font-semibold"
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
              "inline-flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-medium transition-all",
              view === "code"
                ? "bg-white text-foreground shadow-2xs font-semibold"
                : "text-muted-foreground hover:text-foreground",
            )}
          >
            <Code2 className="size-3.5" />
            <span>Kode</span>
          </button>
        </div>

        {/* Right: Viewport selector & Download button */}
        <div className="flex items-center gap-2 shrink-0">
          {view === "preview" ? (
            <div className="hidden sm:flex items-center gap-0.5 rounded-lg bg-slate-100 p-0.5 border border-border/60" role="group" aria-label="Ukuran pratinjau">
              <button
                type="button"
                title="Desktop"
                aria-label="Desktop"
                onClick={() => setViewport("desktop")}
                className={cn(
                  "rounded-md p-1.5 text-xs transition-all",
                  viewport === "desktop"
                    ? "bg-white text-foreground shadow-2xs"
                    : "text-muted-foreground hover:text-foreground",
                )}
              >
                <Monitor className="size-3.5" />
              </button>
              <button
                type="button"
                title="Tablet"
                aria-label="Tablet"
                onClick={() => setViewport("tablet")}
                className={cn(
                  "rounded-md p-1.5 text-xs transition-all",
                  viewport === "tablet"
                    ? "bg-white text-foreground shadow-2xs"
                    : "text-muted-foreground hover:text-foreground",
                )}
              >
                <Tablet className="size-3.5" />
              </button>
              <button
                type="button"
                title="Mobile"
                aria-label="Mobile"
                onClick={() => setViewport("mobile")}
                className={cn(
                  "rounded-md p-1.5 text-xs transition-all",
                  viewport === "mobile"
                    ? "bg-white text-foreground shadow-2xs"
                    : "text-muted-foreground hover:text-foreground",
                )}
              >
                <Smartphone className="size-3.5" />
              </button>
            </div>
          ) : null}

          <a
            href={downloadUrl}
            className="inline-flex h-8 items-center gap-1.5 rounded-lg bg-slate-900 text-white px-2.5 text-xs font-medium hover:bg-slate-800 transition-all shadow-2xs"
          >
            <Download className="size-3.5" aria-hidden="true" />
            <span className="hidden sm:inline">Unduh</span> ZIP
          </a>
        </div>
      </div>

      {/* Main Workspace Body */}
      {view === "preview" ? (
        <div className="min-h-0 flex-1 overflow-auto bg-slate-100/70 p-2.5 sm:p-4">
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

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
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { PreviewFrame, type ViewportMode } from "@/components/results/preview-frame";
import { SourceTabs, type SourceLoadState } from "@/components/results/source-tabs";
import type { GenerationSummary, GenerationStatus, SourceFilename } from "@/lib/api-types";
import { getAcceptedDownloadUrl, getAcceptedPreviewUrl } from "@/lib/preview-url";

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
      ? "Menghasilkan Halaman Web Lokal"
      : status === "input_too_long"
        ? "Permintaan Perlu Diringkas"
        : status === "generation_failed"
          ? "Halaman Belum Berhasil Dibuat"
          : status === "completed"
            ? "Data Hasil Tidak Lengkap"
            : "Kanvas Halaman Web Interaktif";
    const description = status === "completed"
      ? "Respons API tidak memiliki referensi hasil yang valid, sehingga pratinjau tidak dapat ditampilkan."
      : statusMessage ?? (pending
        ? "Model sedang menyusun kode HTML, styling Tailwind/CSS, dan struktur visual. Pratinjau akan langsung muncul begitu proses selesai."
        : "Tulis ide website Anda di kolom percakapan, tinjau ringkasan fakta, lalu klik Generate Website untuk melihat pratinjau live di sini.");

    return (
      <div className="flex min-h-0 flex-1 items-center justify-center p-6 sm:p-10">
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
    );
  }

  function changeView(value: string | null) {
    if (value !== "preview" && value !== "code") return;
    onViewChange(value);
    if (value === "code" && summary) onLoadSource(summary.generation_id);
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-hidden px-3 pb-3 sm:px-5 sm:pb-5">
      {/* Top Bar info & Download */}
      <div className="flex shrink-0 flex-wrap items-center justify-between gap-3 py-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <h2 className="truncate text-sm font-semibold text-foreground">
              {summary.business_name || "Halaman Diterima"}
            </h2>
            <span className="rounded-full bg-emerald-50 px-2 py-0.5 text-[10px] font-medium text-emerald-700 border border-emerald-200">
              Diterima
            </span>
          </div>
          <p className="mt-0.5 text-xs text-muted-foreground">
            {summary.genre === "company_profile" ? "Company Profile" : "Landing Page"} ·{" "}
            {summary.style_mode === "tailwind" ? "Tailwind CSS" : "CSS Murni"}
          </p>
        </div>

        <a
          href={downloadUrl}
          className="inline-flex h-9 items-center gap-2 rounded-xl bg-primary text-primary-foreground px-3.5 text-xs font-medium shadow-xs shadow-primary/20 hover:bg-primary/90 transition-all"
        >
          <Download className="size-3.5" aria-hidden="true" />
          Unduh File ZIP
        </a>
      </div>

      {/* Main Tabs Container */}
      <Tabs
        value={view}
        onValueChange={changeView}
        className="flex min-h-0 flex-1 flex-col overflow-hidden rounded-2xl border border-border bg-card shadow-sm"
      >
        <TabsList
          variant="line"
          className="h-12 w-full shrink-0 justify-start gap-4 rounded-none border-b border-border bg-slate-50/70 px-4"
        >
          <TabsTrigger value="preview" className="flex items-center gap-2 h-full px-2 text-xs font-medium">
            <Eye className="size-3.5" />
            Pratinjau
          </TabsTrigger>
          <TabsTrigger value="code" className="flex items-center gap-2 h-full px-2 text-xs font-medium">
            <Code2 className="size-3.5" />
            Kode Sumber
          </TabsTrigger>
        </TabsList>

        {/* Live Preview Viewport */}
        <TabsContent value="preview" className="m-0 flex min-h-0 flex-1 flex-col overflow-hidden">
          <div className="flex h-11 shrink-0 items-center justify-between gap-2 border-b border-border bg-white px-3 sm:px-4">
            {/* Viewport switchers */}
            <div className="flex items-center gap-1 rounded-lg bg-slate-100 p-0.5" role="group" aria-label="Ukuran pratinjau">
              <Button
                type="button"
                size="xs"
                variant={viewport === "desktop" ? "secondary" : "ghost"}
                aria-pressed={viewport === "desktop"}
                onClick={() => setViewport("desktop")}
                className="h-7 gap-1 rounded-md px-2 text-xs font-medium"
              >
                <Monitor className="size-3" aria-hidden="true" />
                Desktop
              </Button>
              <Button
                type="button"
                size="xs"
                variant={viewport === "tablet" ? "secondary" : "ghost"}
                aria-pressed={viewport === "tablet"}
                onClick={() => setViewport("tablet")}
                className="h-7 gap-1 rounded-md px-2 text-xs font-medium"
              >
                <Tablet className="size-3" aria-hidden="true" />
                Tablet
              </Button>
              <Button
                type="button"
                size="xs"
                variant={viewport === "mobile" ? "secondary" : "ghost"}
                aria-pressed={viewport === "mobile"}
                onClick={() => setViewport("mobile")}
                className="h-7 gap-1 rounded-md px-2 text-xs font-medium"
              >
                <Smartphone className="size-3" aria-hidden="true" />
                Mobile
              </Button>
            </div>

            <span className="hidden text-[11px] text-muted-foreground sm:inline">
              Renderer lokal aman (iframe sandbox)
            </span>
          </div>

          <div className="min-h-0 flex-1 overflow-auto bg-slate-100/70 p-3 sm:p-5">
            <PreviewFrame
              key={previewUrl}
              generationId={summary.generation_id}
              src={previewUrl}
              title={summary.business_name || "hasil generator"}
              viewport={viewport}
            />
          </div>
        </TabsContent>

        {/* Source Code View */}
        <TabsContent value="code" className="m-0 flex min-h-0 flex-1 flex-col overflow-hidden">
          <SourceTabs
            generationId={summary.generation_id}
            state={sourceState}
            onRetry={onLoadSource}
            onDownload={onDownloadSource}
          />
        </TabsContent>
      </Tabs>
    </div>
  );
}

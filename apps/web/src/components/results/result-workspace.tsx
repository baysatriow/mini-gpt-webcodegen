"use client";

import { useEffect, useState } from "react";
import { AlertCircle, Download, LoaderCircle, Monitor, Smartphone } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { PreviewFrame } from "@/components/results/preview-frame";
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
  const [viewport, setViewport] = useState<"desktop" | "mobile">("desktop");
  const previewUrl = getAcceptedPreviewUrl(summary);
  const downloadUrl = getAcceptedDownloadUrl(summary);

  useEffect(() => {
    if (view === "code" && summary) onLoadSource(summary.generation_id);
  }, [view, summary, onLoadSource]);

  if (!summary || !previewUrl || !downloadUrl) {
    const pending = status === "pending";
    const failed = status === "generation_failed" || status === "input_too_long" || status === "completed";
    const heading = pending
      ? "Menunggu halaman dari API lokal"
      : status === "input_too_long"
        ? "Permintaan perlu diringkas"
        : status === "generation_failed"
          ? "Halaman belum berhasil dibuat"
          : status === "completed"
            ? "Data hasil tidak lengkap"
            : "Pratinjau akan muncul di sini";
    const description = status === "completed"
      ? "Respons API tidak memiliki referensi hasil yang valid, jadi output tidak ditampilkan."
      : statusMessage ?? (pending
        ? "Pembuatan berjalan sebagai satu operasi. Belum ada preview atau berkas yang bisa diunduh."
        : "Lengkapi fakta usaha, tinjau ringkasan, lalu setujui pembuatan halaman.");

    return (
      <div className="flex min-h-0 flex-1 items-center justify-center px-5 py-8 sm:px-8">
        <div className={`w-full max-w-md rounded-xl border bg-white p-6 text-center ${failed ? "border-destructive/20" : "border-border"}`}>
          <span className={`mx-auto grid size-11 place-items-center rounded-xl ${pending ? "bg-accent text-cobalt-action" : failed ? "bg-destructive/5 text-destructive" : "bg-frost text-slate-note"}`}>
            {pending ? <LoaderCircle className="size-5 animate-spin" aria-hidden="true" /> : failed ? <AlertCircle className="size-5" aria-hidden="true" /> : <Monitor className="size-5" aria-hidden="true" />}
          </span>
          <h2 className="mt-4 text-base font-semibold text-harbor-ink">{heading}</h2>
          <p className={`mt-2 text-sm leading-6 ${failed ? "text-destructive" : "text-slate-note"}`} role={failed ? "alert" : pending ? "status" : undefined}>
            {description}
          </p>
        </div>
      </div>
    );
  }

  function changeView(value: string | null) {
    if (value !== "preview" && value !== "code") return;
    onViewChange(value);
    if (value === "code") onLoadSource(summary.generation_id);
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-hidden px-3 pb-3 sm:px-5 sm:pb-5">
      <div className="flex shrink-0 flex-wrap items-center justify-between gap-3 py-3">
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold text-harbor-ink">{summary.business_name || "Halaman yang diterima"}</p>
          <p className="mt-0.5 text-xs text-slate-note">{summary.genre === "company_profile" ? "Company profile" : "Landing page"} · {summary.style_mode === "tailwind" ? "Tailwind" : "CSS biasa"}</p>
        </div>
        <a href={downloadUrl} className="inline-flex h-9 items-center gap-2 rounded-lg border border-border bg-white px-3 text-sm font-medium text-harbor-ink transition-colors hover:bg-frost focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring">
          <Download className="size-4" aria-hidden="true" />
          Unduh ZIP
        </a>
      </div>

      <Tabs value={view} onValueChange={changeView} className="flex min-h-0 flex-1 flex-col overflow-hidden rounded-xl border border-border bg-white shadow-[0_12px_36px_rgba(30,45,69,0.07)]">
        <TabsList variant="line" className="h-12 w-full shrink-0 justify-start gap-4 rounded-none border-b border-border px-4">
          <TabsTrigger value="preview" className="h-full flex-none px-1 text-sm">Pratinjau</TabsTrigger>
          <TabsTrigger value="code" className="h-full flex-none px-1 text-sm">Kode</TabsTrigger>
        </TabsList>

        <TabsContent value="preview" className="m-0 flex min-h-0 flex-1 flex-col overflow-hidden">
          <div className="flex h-12 shrink-0 items-center justify-between gap-2 border-b border-border px-3 sm:px-4">
            <div className="flex items-center gap-1 rounded-lg bg-frost p-1" role="group" aria-label="Ukuran pratinjau">
              <Button type="button" size="sm" variant={viewport === "desktop" ? "secondary" : "ghost"} aria-pressed={viewport === "desktop"} onClick={() => setViewport("desktop")} className="h-8 gap-1.5 rounded-md px-2.5 text-xs">
                <Monitor className="size-3.5" aria-hidden="true" />Desktop
              </Button>
              <Button type="button" size="sm" variant={viewport === "mobile" ? "secondary" : "ghost"} aria-pressed={viewport === "mobile"} onClick={() => setViewport("mobile")} className="h-8 gap-1.5 rounded-md px-2.5 text-xs">
                <Smartphone className="size-3.5" aria-hidden="true" />Mobile
              </Button>
            </div>
            <span className="hidden text-xs text-slate-note sm:inline">Source hanya dari renderer lokal yang diterima</span>
          </div>
          <div className="min-h-0 flex-1 overflow-auto bg-[#E9EEF5] p-3 sm:p-5">
            <PreviewFrame key={previewUrl} src={previewUrl} title={summary.business_name || "hasil generator"} viewport={viewport} />
          </div>
        </TabsContent>

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

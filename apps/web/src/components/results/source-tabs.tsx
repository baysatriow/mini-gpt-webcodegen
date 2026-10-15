"use client";

import { useState } from "react";
import { Download, LoaderCircle, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import type { SourceFilename, SourceResponse } from "@/lib/api-types";

export type SourceLoadState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "loaded"; source: SourceResponse }
  | { status: "error"; message: string };

const SOURCE_FILES: SourceFilename[] = ["index.html", "styles.css", "app.js"];

type SourceTabsProps = {
  generationId: string;
  state: SourceLoadState;
  onRetry: (generationId: string, force: boolean) => void;
  onDownload: (generationId: string, filename: SourceFilename) => Promise<void>;
};

export function SourceTabs({ generationId, state, onRetry, onDownload }: SourceTabsProps) {
  const [filename, setFilename] = useState<SourceFilename>("index.html");
  const [downloading, setDownloading] = useState(false);
  const [downloadError, setDownloadError] = useState<string | null>(null);

  async function downloadCurrentFile() {
    setDownloading(true);
    setDownloadError(null);
    try {
      await onDownload(generationId, filename);
    } catch (error) {
      setDownloadError(error instanceof Error ? error.message : "File belum bisa diunduh. Coba lagi.");
    } finally {
      setDownloading(false);
    }
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-hidden rounded-b-xl border border-t-0 border-border bg-[#101a2b]">
      {state.status === "loaded" ? (
        <Tabs value={filename} onValueChange={(value) => {
          if (SOURCE_FILES.includes(value as SourceFilename)) setFilename(value as SourceFilename);
        }} className="flex min-h-0 flex-1 flex-col overflow-hidden">
          <div className="flex min-h-12 shrink-0 flex-wrap items-center justify-between gap-2 border-b border-white/10 px-3 sm:px-4">
            <TabsList variant="line" className="h-11 gap-3">
              {SOURCE_FILES.map((file) => (
                <TabsTrigger key={file} value={file} className="h-full px-1 text-xs text-slate-300 data-active:text-white">
                  {file}
                </TabsTrigger>
              ))}
            </TabsList>
            <Button type="button" variant="secondary" size="sm" onClick={() => void downloadCurrentFile()} disabled={downloading} className="h-8 gap-1.5 rounded-md">
              {downloading ? <LoaderCircle className="size-3.5 animate-spin" aria-hidden="true" /> : <Download className="size-3.5" aria-hidden="true" />}
              Unduh file
            </Button>
          </div>
          {SOURCE_FILES.map((file) => (
            <TabsContent key={file} value={file} className="m-0 min-h-0 flex-1 overflow-auto p-4 sm:p-5">
              <pre className="min-w-0 whitespace-pre-wrap break-words font-mono text-xs leading-6 text-[#D8E1F0] sm:text-[13px]">
                <code>{state.source[file]}</code>
              </pre>
            </TabsContent>
          ))}
        </Tabs>
      ) : (
        <>
          <div className="flex min-h-12 shrink-0 items-center justify-between gap-2 border-b border-white/10 px-3 sm:px-4">
            <p className="text-xs text-slate-300">index.html · styles.css · app.js</p>
            <Button type="button" variant="secondary" size="sm" disabled className="h-8 gap-1.5 rounded-md">
              <Download className="size-3.5" aria-hidden="true" />
              Unduh file
            </Button>
          </div>
          {state.status === "loading" ? (
            <div className="grid min-h-[360px] flex-1 place-items-center px-5 text-sm text-slate-300" role="status">
              <span className="inline-flex items-center gap-2"><LoaderCircle className="size-4 animate-spin" aria-hidden="true" />Mengambil source dari API lokal…</span>
            </div>
          ) : null}
          {state.status === "error" ? (
            <div className="grid min-h-[360px] flex-1 place-items-center px-5 py-8 text-center">
              <div className="max-w-sm">
                <p className="text-sm font-medium text-white">Source belum bisa dimuat</p>
                <p className="mt-2 text-sm leading-6 text-slate-300">{state.message}</p>
                <Button type="button" variant="secondary" size="sm" onClick={() => onRetry(generationId, true)} className="mt-4 gap-2">
                  <RefreshCw className="size-3.5" aria-hidden="true" />
                  Coba lagi
                </Button>
              </div>
            </div>
          ) : null}
          {state.status === "idle" ? (
            <div className="grid min-h-[360px] flex-1 place-items-center px-5 text-sm text-slate-300" role="status">
              Source akan dimuat dari halaman yang sudah diterima.
            </div>
          ) : null}
        </>
      )}

      {downloadError ? <p className="border-t border-white/10 px-4 py-2 text-xs text-rose-300" role="alert">{downloadError}</p> : null}
    </div>
  );
}

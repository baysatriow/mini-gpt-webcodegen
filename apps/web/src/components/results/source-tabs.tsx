"use client";

import { useEffect, useState } from "react";
import { Check, Copy, Download, FileCode, LoaderCircle, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import type { SourceFilename, SourceResponse } from "@/lib/api-types";
import { copyTextToClipboard } from "@/lib/clipboard";
import { formatSourceCode } from "@/lib/source-format";

export type SourceLoadState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "loaded"; source: SourceResponse }
  | { status: "error"; message: string };

const SOURCE_FILES: SourceFilename[] = ["index.html", "styles.css", "app.js"];

const FILE_TAGS: Record<SourceFilename, { label: string; badge: string; color: string }> = {
  "index.html": { label: "HTML5", badge: "HTML", color: "bg-amber-500/20 text-amber-300 border-amber-500/30" },
  "styles.css": { label: "Styles", badge: "CSS", color: "bg-blue-500/20 text-blue-300 border-blue-500/30" },
  "app.js": { label: "Logic", badge: "JS", color: "bg-yellow-500/20 text-yellow-300 border-yellow-500/30" },
};

type SourceTabsProps = {
  generationId: string;
  state: SourceLoadState;
  onRetry: (generationId: string, force: boolean) => void;
  onDownload: (generationId: string, filename: SourceFilename) => Promise<void>;
};

export function SourceTabs({ generationId, state, onRetry, onDownload }: SourceTabsProps) {
  const [filename, setFilename] = useState<SourceFilename>("index.html");
  const [downloading, setDownloading] = useState(false);
  const [copyStatus, setCopyStatus] = useState<"idle" | "copied" | "failed">("idle");
  const [downloadError, setDownloadError] = useState<string | null>(null);
  const [formattedSource, setFormattedSource] = useState<Partial<Record<SourceFilename, {
    original: string;
    display: string;
    status: "formatted" | "fallback";
  }>>>({});

  useEffect(() => {
    if (state.status !== "loaded") return;

    let active = true;
    const source = state.source;
    void Promise.all(SOURCE_FILES.map(async (file) => {
      const original = source[file] || "";
      try {
        return { file, original, display: await formatSourceCode(file, original), status: "formatted" as const };
      } catch {
        return { file, original, display: original, status: "fallback" as const };
      }
    })).then((entries) => {
      if (!active) return;
      setFormattedSource(Object.fromEntries(entries.map(({ file, ...entry }) => [file, entry])));
    });

    return () => {
      active = false;
    };
  }, [state]);

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

  async function copyCurrentCode() {
    if (state.status !== "loaded") return;
    const original = state.source[filename] || "";
    const formatted = formattedSource[filename];
    const code = formatted?.original === original ? formatted.display : original;
    if (!code) return;
    const copied = await copyTextToClipboard(code);
    setCopyStatus(copied ? "copied" : "failed");
    window.setTimeout(() => setCopyStatus("idle"), 2000);
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-hidden rounded-b-xl border border-t-0 border-border bg-[#0b1329] text-slate-100">
      {state.status === "loaded" ? (
        <Tabs
          value={filename}
          onValueChange={(value) => {
            if (SOURCE_FILES.includes(value as SourceFilename)) setFilename(value as SourceFilename);
          }}
          className="flex min-h-0 flex-1 flex-col overflow-hidden"
        >
          {/* Code Viewer Top Bar */}
          <div className="flex min-h-12 shrink-0 flex-wrap items-center justify-between gap-2 border-b border-white/10 bg-[#0d1730] px-3 sm:px-4">
            <TabsList variant="line" className="h-10 gap-2">
              {SOURCE_FILES.map((file) => {
                const tag = FILE_TAGS[file];
                return (
                  <TabsTrigger
                    key={file}
                    value={file}
                    className="flex items-center gap-1.5 h-full px-2.5 text-xs text-slate-400 data-active:text-white data-active:font-medium transition-colors"
                  >
                    <span className={`rounded px-1 text-[9px] font-mono border ${tag.color}`}>
                      {tag.badge}
                    </span>
                    <span>{file}</span>
                  </TabsTrigger>
                );
              })}
            </TabsList>

            <div className="flex items-center gap-2">
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => void copyCurrentCode()}
                className="h-8 gap-1.5 rounded-lg text-xs text-slate-300 hover:bg-white/10 hover:text-white"
                aria-live="polite"
              >
                {copyStatus === "copied" ? (
                  <>
                    <Check className="size-3.5 text-emerald-400" />
                    <span className="text-emerald-400">Tersalin!</span>
                  </>
                ) : copyStatus === "failed" ? (
                  <span className="text-rose-300">Gagal menyalin</span>
                ) : (
                  <>
                    <Copy className="size-3.5" />
                    <span>Salin Kode</span>
                  </>
                )}
              </Button>

              <Button
                type="button"
                variant="secondary"
                size="sm"
                onClick={() => void downloadCurrentFile()}
                disabled={downloading}
                className="h-8 gap-1.5 rounded-lg text-xs bg-white/10 hover:bg-white/20 text-white border border-white/10"
              >
                {downloading ? (
                  <LoaderCircle className="size-3.5 animate-spin" aria-hidden="true" />
                ) : (
                  <Download className="size-3.5" aria-hidden="true" />
                )}
                Unduh Berkas
              </Button>
            </div>
          </div>

          {/* Code Content */}
          {SOURCE_FILES.map((file) => {
            const original = state.source[file] || "";
            const formatted = formattedSource[file];
            const content = formatted?.original === original ? formatted.display : original;
            const lines = content.split("\n").length;
            return (
              <TabsContent key={file} value={file} className="m-0 min-h-0 flex-1 overflow-auto p-4 sm:p-5">
                <div className="mb-2 flex flex-wrap items-center justify-between gap-x-3 gap-y-1 border-b border-white/5 pb-2 font-mono text-[11px] text-slate-400">
                  <span>{file}</span>
                  <div className="flex flex-wrap items-center justify-end gap-x-2">
                    <span>{lines} baris · {original.length} karakter</span>
                    <span
                      title="Source ditata untuk dibaca. Berkas unduhan tetap menggunakan artefak asli."
                      aria-live="polite"
                    >
                      {formatted?.original !== original
                        ? "Memformat…"
                        : formatted.status === "fallback"
                          ? "Source asli"
                          : "Tampilan terformat"}
                    </span>
                  </div>
                </div>
                <pre className="min-w-0 whitespace-pre-wrap break-words font-mono text-xs leading-6 text-slate-200 selection:bg-blue-600/40 sm:text-[13px]">
                  <code>{content}</code>
                </pre>
              </TabsContent>
            );
          })}
        </Tabs>
      ) : (
        <>
          <div className="flex min-h-12 shrink-0 items-center justify-between gap-2 border-b border-white/10 bg-[#0d1730] px-3 sm:px-4">
            <div className="flex items-center gap-2 text-xs text-slate-400">
              <FileCode className="size-4 text-blue-400" />
              <span>index.html · styles.css · app.js</span>
            </div>
            <Button type="button" variant="secondary" size="sm" disabled className="h-8 gap-1.5 rounded-lg text-xs opacity-50">
              <Download className="size-3.5" aria-hidden="true" />
              Unduh
            </Button>
          </div>

          {state.status === "loading" ? (
            <div className="grid min-h-[360px] flex-1 place-items-center px-5 text-xs text-slate-300" role="status">
              <span className="inline-flex items-center gap-2">
                <LoaderCircle className="size-4 animate-spin text-blue-400" aria-hidden="true" />
                Mengambil source code…
              </span>
            </div>
          ) : null}

          {state.status === "error" ? (
            <div className="grid min-h-[360px] flex-1 place-items-center px-5 py-8 text-center">
              <div className="max-w-sm">
                <p className="text-sm font-semibold text-white">Source code belum dapat dimuat</p>
                <p className="mt-1.5 text-xs leading-relaxed text-slate-400">{state.message}</p>
                <Button
                  type="button"
                  variant="secondary"
                  size="sm"
                  onClick={() => onRetry(generationId, true)}
                  className="mt-4 gap-2 rounded-xl text-xs bg-white/10 hover:bg-white/20 text-white"
                >
                  <RefreshCw className="size-3.5" aria-hidden="true" />
                  Coba Lagi
                </Button>
              </div>
            </div>
          ) : null}

          {state.status === "idle" ? (
            <div className="grid min-h-[360px] flex-1 place-items-center px-5 text-xs text-slate-400" role="status">
              Source code akan tersedia setelah website selesai dibuat dan diterima.
            </div>
          ) : null}
        </>
      )}

      {downloadError ? (
        <p className="border-t border-red-500/20 bg-red-950/40 px-4 py-2 text-xs text-rose-300" role="alert">
          {downloadError}
        </p>
      ) : null}
    </div>
  );
}

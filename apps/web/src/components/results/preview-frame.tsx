"use client";

import { useEffect, useRef, useState } from "react";
import { AlertCircle, Check, Copy, ExternalLink, Globe, Lock, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ApiClientError, loadPreviewDocument } from "@/lib/api-client";
import { copyTextToClipboard } from "@/lib/clipboard";
import { getShareablePreviewUrl } from "@/lib/shareable-preview-url";

export type ViewportMode = "responsive" | "desktop" | "tablet" | "mobile";

type PreviewFrameProps = {
  generationId: string;
  src: string;
  title: string;
  viewport: ViewportMode;
};

type PreviewState =
  | { status: "loading" }
  | { status: "ready"; document: string }
  | { status: "error"; message: string };

export function PreviewFrame({ generationId, src, title, viewport }: PreviewFrameProps) {
  const [attempt, setAttempt] = useState(0);
  const [previewState, setPreviewState] = useState<PreviewState>({ status: "loading" });
  const [copyStatus, setCopyStatus] = useState<"idle" | "copied" | "error">("idle");
  const copyTimer = useRef<number | null>(null);

  useEffect(() => () => {
    if (copyTimer.current !== null) window.clearTimeout(copyTimer.current);
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    let active = true;
    void loadPreviewDocument(generationId, controller.signal)
      .then((document) => {
        if (active) setPreviewState({ status: "ready", document });
      })
      .catch((error: unknown) => {
        if (!active || controller.signal.aborted) return;
        setPreviewState({
          status: "error",
          message: error instanceof ApiClientError
            ? error.message
            : "Pratinjau gagal diperiksa. Coba lagi.",
        });
      });
    return () => {
      active = false;
      controller.abort();
    };
  }, [generationId, attempt]);

  async function handleCopyUrl() {
    let ok = false;
    try {
      ok = await copyTextToClipboard(getShareablePreviewUrl(src, window.location.href));
    } catch {
      ok = false;
    }
    setCopyStatus(ok ? "copied" : "error");
    if (copyTimer.current !== null) window.clearTimeout(copyTimer.current);
    copyTimer.current = window.setTimeout(() => setCopyStatus("idle"), 2000);
  }

  const displayUrl = src;

  // Mobile Device Mockup
  if (viewport === "mobile") {
    return (
      <div className="relative mx-auto my-auto transition-all duration-300 w-[414px] shrink-0">
        {/* Smartphone Bezel */}
        <div className="rounded-[44px] p-3 bg-slate-950 ring-1 ring-slate-800 shadow-2xl">
          {/* Dynamic Island / Notch */}
          <div className="mx-auto h-4.5 w-24 rounded-full bg-slate-900 mb-2 flex items-center justify-center gap-1.5 select-none">
            <span className="size-1.5 rounded-full bg-slate-700" />
            <span className="h-1 w-8 rounded-full bg-slate-700" />
          </div>

          {/* Screen */}
          <div className="rounded-[32px] overflow-hidden bg-white shadow-inner">
            {previewState.status === "ready" ? (
              <iframe
                key={`${src}-${attempt}`}
                srcDoc={previewState.document}
                title={`Pratinjau Mobile ${title}`}
                sandbox="allow-scripts"
                referrerPolicy="no-referrer"
                onError={() => setPreviewState({ status: "error", message: "Pratinjau gagal dimuat. Coba lagi." })}
                className="block w-full bg-white transition-all h-[640px] sm:h-[680px]"
              />
            ) : (
              <LoadingOrErrorState state={previewState} onRetry={() => setAttempt((c) => c + 1)} />
            )}
          </div>

          {/* Bottom Home Indicator */}
          <div className="mx-auto mt-2.5 h-1 w-28 rounded-full bg-slate-700/80" />
        </div>
      </div>
    );
  }

  // Tablet Device Mockup
  if (viewport === "tablet") {
    return (
      <div className="relative mx-auto my-auto transition-all duration-300 w-[792px] shrink-0">
        {/* Tablet Bezel */}
        <div className="rounded-3xl p-3 bg-slate-900 ring-1 ring-slate-800 shadow-2xl">
          {/* Top Camera Dot */}
          <div className="mx-auto size-2 rounded-full bg-slate-800 mb-2 select-none" />

          {/* Screen */}
          <div className="rounded-2xl overflow-hidden bg-white shadow-inner">
            {previewState.status === "ready" ? (
              <iframe
                key={`${src}-${attempt}`}
                srcDoc={previewState.document}
                title={`Pratinjau Tablet ${title}`}
                sandbox="allow-scripts"
                referrerPolicy="no-referrer"
                onError={() => setPreviewState({ status: "error", message: "Pratinjau gagal dimuat. Coba lagi." })}
                className="block w-full bg-white transition-all h-[640px] sm:h-[720px]"
              />
            ) : (
              <LoadingOrErrorState state={previewState} onRetry={() => setAttempt((c) => c + 1)} />
            )}
          </div>
        </div>
      </div>
    );
  }

  // Desktop or Responsive Mode
  const frameWidth = viewport === "desktop" ? "1202px" : "100%";

  return (
    <div
      className="relative mx-auto shrink-0 transition-all duration-300"
      style={{ width: frameWidth, maxWidth: viewport === "responsive" ? "100%" : undefined }}
    >
      {/* Modern Studio Browser Chrome */}
      <div className="rounded-2xl border border-slate-200/90 bg-white shadow-lg overflow-hidden">
        {/* Browser Top Navigation Bar */}
        <div className="flex items-center justify-between gap-3 border-b border-slate-200/80 bg-slate-100/90 px-3.5 py-2 select-none">
          {/* Window Control Dots */}
          <div className="flex items-center gap-1.5 shrink-0">
            <span className="size-2.5 rounded-full bg-rose-400/90 ring-1 ring-rose-500/20 shadow-2xs" />
            <span className="size-2.5 rounded-full bg-amber-400/90 ring-1 ring-amber-500/20 shadow-2xs" />
            <span className="size-2.5 rounded-full bg-emerald-400/90 ring-1 ring-emerald-500/20 shadow-2xs" />
          </div>

          {/* Address Bar Pill */}
          <div className="flex min-w-0 max-w-md flex-1 items-center justify-between gap-2 rounded-lg border border-slate-200 bg-white px-2.5 py-1 text-[11px] text-muted-foreground shadow-2xs">
            <div className="flex min-w-0 items-center gap-1.5">
              <Lock className="size-3 text-emerald-600 shrink-0" />
              <span className="truncate text-foreground font-mono text-[10px] select-all">
                {displayUrl}
              </span>
            </div>

            <button
              type="button"
              onClick={() => void handleCopyUrl()}
              title="Salin URL pratinjau"
              className="inline-flex items-center gap-1 text-[10px] font-semibold text-slate-500 hover:text-slate-800 transition-colors shrink-0 cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              {copyStatus === "copied" ? (
                <>
                  <Check className="size-3 text-emerald-600" />
                  <span className="text-emerald-600">Disalin!</span>
                </>
              ) : (
                <>
                  <Copy className="size-3" />
                  <span className={copyStatus === "error" ? "inline" : "hidden sm:inline"} role="status">{copyStatus === "error" ? "Gagal menyalin" : "Salin"}</span>
                </>
              )}
            </button>
          </div>

          {/* Actions */}
          <div className="flex items-center gap-1 shrink-0">
            <button
              type="button"
              onClick={() => {
                setPreviewState({ status: "loading" });
                setAttempt((c) => c + 1);
              }}
              title="Muat ulang pratinjau"
              className="rounded-lg p-1.5 text-slate-500 hover:bg-slate-200 hover:text-slate-900 active:scale-95 transition-all cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              <RefreshCw className="size-3.5" />
            </button>
            <a
              href={src}
              target="_blank"
              rel="noopener noreferrer"
              title="Buka pratinjau di tab baru"
              className="rounded-lg p-1.5 text-slate-500 hover:bg-slate-200 hover:text-slate-900 active:scale-95 transition-all cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              <ExternalLink className="size-3.5" />
            </a>
          </div>
        </div>

        {/* Content Area */}
        {previewState.status === "ready" ? (
          <iframe
            key={`${src}-${attempt}`}
            srcDoc={previewState.document}
            title={`Pratinjau website ${title}`}
            sandbox="allow-scripts"
            referrerPolicy="no-referrer"
            onError={() => setPreviewState({ status: "error", message: "Pratinjau gagal dimuat. Coba lagi." })}
            className="block w-full bg-white transition-all min-h-[520px] sm:min-h-[min(72vh,760px)]"
            style={{ width: "100%", height: "min(72vh, 760px)" }}
          />
        ) : (
          <LoadingOrErrorState state={previewState} onRetry={() => setAttempt((c) => c + 1)} />
        )}
      </div>
    </div>
  );
}

function LoadingOrErrorState({
  state,
  onRetry,
}: {
  state: PreviewState;
  onRetry: () => void;
}) {
  return (
    <div className="grid min-h-[520px] place-items-center bg-white p-6 text-center sm:min-h-[min(70vh,760px)]">
      <div className="max-w-xs">
        {state.status === "loading" ? (
          <>
            <div className="relative mx-auto mb-3 flex size-12 items-center justify-center rounded-2xl bg-blue-50 text-primary border border-blue-100 shadow-2xs">
              <Globe className="size-6 animate-pulse" />
            </div>
            <p className="text-sm font-semibold text-foreground" role="status">Memeriksa pratinjauÃ¢â‚¬Â¦</p>
            <p className="mt-1 text-xs leading-relaxed text-muted-foreground">Menyiapkan frame pratinjau interaktif.</p>
          </>
        ) : state.status === "error" ? (
          <>
            <AlertCircle className="mx-auto size-7 text-destructive mb-2" aria-hidden="true" />
            <p className="text-sm font-semibold text-foreground">Pratinjau tidak dapat dimuat</p>
            <p className="mt-1 text-xs leading-relaxed text-muted-foreground">{state.message}</p>
            <Button
              type="button"
              size="sm"
              variant="outline"
              onClick={onRetry}
              className="mt-3.5 gap-2 rounded-xl text-xs h-8 bg-white shadow-2xs"
            >
              <RefreshCw className="size-3.5" aria-hidden="true" />
              Coba Lagi
            </Button>
          </>
        ) : null}
      </div>
    </div>
  );
}

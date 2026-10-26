"use client";

import { useEffect, useState } from "react";
import { AlertCircle, ExternalLink, Globe, Lock, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ApiClientError, checkPreviewAvailability } from "@/lib/api-client";

export type ViewportMode = "desktop" | "tablet" | "mobile";

type PreviewFrameProps = {
  generationId: string;
  src: string;
  title: string;
  viewport: ViewportMode;
};

type PreviewState =
  | { status: "loading" }
  | { status: "ready" }
  | { status: "error"; message: string };

export function PreviewFrame({ generationId, src, title, viewport }: PreviewFrameProps) {
  const [attempt, setAttempt] = useState(0);
  const [previewState, setPreviewState] = useState<PreviewState>({ status: "loading" });

  useEffect(() => {
    const controller = new AbortController();
    let active = true;
    void checkPreviewAvailability(generationId, controller.signal)
      .then(() => {
        if (active) setPreviewState({ status: "ready" });
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

  const frameWidth =
    viewport === "mobile"
      ? "390px"
      : viewport === "tablet"
        ? "768px"
        : "1280px";

  return (
    <div className="relative mx-auto transition-all duration-300" style={{ width: frameWidth, maxWidth: "100%" }}>
      {/* Browser Chrome Window Mockup */}
      <div className="rounded-xl border border-border/80 bg-white shadow-md overflow-hidden">
        {/* Browser Top Navigation Bar */}
        <div className="flex items-center justify-between gap-3 border-b border-border/70 bg-slate-100/80 px-3.5 py-2 select-none">
          {/* Window Control Buttons */}
          <div className="flex items-center gap-1.5 shrink-0">
            <span className="size-2.5 rounded-full bg-rose-400" />
            <span className="size-2.5 rounded-full bg-amber-400" />
            <span className="size-2.5 rounded-full bg-emerald-400" />
          </div>

          {/* Isolated Preview Indicator */}
          <div className="flex min-w-0 max-w-md flex-1 items-center gap-1.5 rounded-lg border border-border/80 bg-white px-2.5 py-1 text-[11px] text-muted-foreground shadow-2xs">
            <Lock className="size-3 text-emerald-600 shrink-0" />
            <span className="truncate text-foreground">
              Pratinjau terisolasi · {generationId}
            </span>
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
              className="rounded-md p-1 text-muted-foreground hover:bg-slate-200 hover:text-foreground transition-colors"
            >
              <RefreshCw className="size-3.5" />
            </button>
            <a
              href={src}
              target="_blank"
              rel="noopener noreferrer"
              title="Buka pratinjau di tab baru"
              className="rounded-md p-1 text-muted-foreground hover:bg-slate-200 hover:text-foreground transition-colors"
            >
              <ExternalLink className="size-3.5" />
            </a>
          </div>
        </div>

        {/* Content Area */}
        {previewState.status === "ready" ? (
          <iframe
            key={`${src}-${attempt}`}
            src={src}
            title={`Pratinjau website ${title}`}
            sandbox="allow-scripts"
            referrerPolicy="no-referrer"
            onError={() => setPreviewState({ status: "error", message: "Pratinjau gagal dimuat. Coba lagi." })}
            className="block w-full bg-white transition-all min-h-[520px] sm:min-h-[min(70vh,760px)]"
            style={{ width: "100%", height: "min(70vh, 760px)" }}
          />
        ) : (
          <div className="grid min-h-[520px] place-items-center bg-white p-6 text-center sm:min-h-[min(70vh,760px)]">
            <div className="max-w-xs">
              {previewState.status === "loading" ? (
                <>
                  <div className="relative mx-auto mb-3 flex size-10 items-center justify-center rounded-xl bg-blue-50 text-primary">
                    <Globe className="size-5 animate-pulse" />
                  </div>
                  <p className="text-sm font-medium text-foreground" role="status">Memeriksa sandbox lokal…</p>
                  <p className="mt-1 text-xs leading-relaxed text-muted-foreground">Menyiapkan frame pratinjau interaktif dari API lokal.</p>
                </>
              ) : (
                <>
                  <AlertCircle className="mx-auto size-6 text-destructive mb-2" aria-hidden="true" />
                  <p className="text-sm font-semibold text-foreground">Pratinjau tidak dapat dimuat</p>
                  <p className="mt-1 text-xs leading-relaxed text-muted-foreground">{previewState.message}</p>
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    onClick={() => {
                      setPreviewState({ status: "loading" });
                      setAttempt((current) => current + 1);
                    }}
                    className="mt-3 gap-2 rounded-xl text-xs h-8 bg-white"
                  >
                    <RefreshCw className="size-3.5" aria-hidden="true" />
                    Coba Lagi
                  </Button>
                </>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

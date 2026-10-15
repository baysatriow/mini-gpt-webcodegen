"use client";

import { useEffect, useState } from "react";
import { AlertCircle, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ApiClientError, checkPreviewAvailability } from "@/lib/api-client";

type PreviewFrameProps = {
  generationId: string;
  src: string;
  title: string;
  viewport: "desktop" | "mobile";
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

  const frameWidth = viewport === "mobile" ? "390px" : "1280px";

  return (
    <div className="relative mx-auto" style={{ width: frameWidth, maxWidth: "none" }}>
      {previewState.status === "ready" ? (
        <iframe
          key={`${src}-${attempt}`}
          src={src}
          title={`Pratinjau website ${title}`}
          sandbox="allow-scripts"
          referrerPolicy="no-referrer"
          onError={() => setPreviewState({ status: "error", message: "Pratinjau gagal dimuat. Coba lagi." })}
          className="mx-auto block min-h-[520px] rounded-lg border border-border bg-white shadow-sm sm:min-h-[min(70vh,760px)]"
          style={{ width: "100%", height: "min(70vh, 760px)" }}
        />
      ) : (
        <div className="grid min-h-[520px] place-items-center rounded-lg border border-border bg-white p-6 text-center shadow-sm sm:min-h-[min(70vh,760px)]">
          <div className="max-w-xs">
            {previewState.status === "loading" ? (
              <>
                <p className="text-sm font-medium text-harbor-ink" role="status">Memeriksa pratinjau…</p>
                <p className="mt-1 text-xs leading-5 text-slate-note">Hasil yang sudah diterima sedang dimuat.</p>
              </>
            ) : (
              <>
                <AlertCircle className="mx-auto size-5 text-destructive" aria-hidden="true" />
                <p className="mt-2 text-sm font-medium text-harbor-ink">Pratinjau tidak dapat dimuat</p>
                <p className="mt-1 text-xs leading-5 text-slate-note">{previewState.message}</p>
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  onClick={() => {
                    setPreviewState({ status: "loading" });
                    setAttempt((current) => current + 1);
                  }}
                  className="mt-3 gap-2"
                >
                  <RefreshCw className="size-3.5" aria-hidden="true" />
                  Coba lagi
                </Button>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

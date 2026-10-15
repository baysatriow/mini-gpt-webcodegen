"use client";

import { useState } from "react";
import { AlertCircle, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";

type PreviewFrameProps = {
  src: string;
  title: string;
  viewport: "desktop" | "mobile";
};

export function PreviewFrame({ src, title, viewport }: PreviewFrameProps) {
  const [attempt, setAttempt] = useState(0);
  const [failed, setFailed] = useState(false);

  return (
    <div className="relative mx-auto" style={{ width: viewport === "mobile" ? "390px" : "100%" }}>
      <iframe
        key={`${src}-${attempt}`}
        src={src}
        title={`Pratinjau website ${title}`}
        sandbox="allow-scripts"
        referrerPolicy="no-referrer"
        onError={() => setFailed(true)}
        className="mx-auto block min-h-[520px] rounded-lg border border-border bg-white shadow-sm sm:min-h-[min(70vh,760px)]"
        style={{ width: "100%", height: "min(70vh, 760px)" }}
      />
      {failed ? (
        <div className="absolute inset-0 grid place-items-center rounded-lg bg-white/95 p-6 text-center">
          <div className="max-w-xs">
            <AlertCircle className="mx-auto size-5 text-destructive" aria-hidden="true" />
            <p className="mt-2 text-sm font-medium text-harbor-ink">Pratinjau tidak dapat dimuat</p>
            <p className="mt-1 text-xs leading-5 text-slate-note">Hasil tetap tersimpan. Muat ulang preview tanpa meminta generation baru.</p>
            <Button type="button" size="sm" variant="outline" onClick={() => {
              setFailed(false);
              setAttempt((current) => current + 1);
            }} className="mt-3 gap-2">
              <RefreshCw className="size-3.5" aria-hidden="true" />
              Coba lagi
            </Button>
          </div>
        </div>
      ) : null}
    </div>
  );
}

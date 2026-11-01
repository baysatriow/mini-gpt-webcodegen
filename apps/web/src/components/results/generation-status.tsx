"use client";

import { AlertCircle, ArrowRight, CheckCircle2, LoaderCircle, Sparkles } from "lucide-react";
import type { GenerationStatusMessage } from "@/lib/chat-state";

type GenerationStatusProps = { message: GenerationStatusMessage; onOpenCanvas: () => void };

export function GenerationStatus({ message, onOpenCanvas }: GenerationStatusProps) {
  const pending = message.status === "pending";
  const failed = message.status === "generation_failed" || message.status === "input_too_long";
  const completed = message.status === "completed";

  return (
    <article className="flex items-start gap-3" aria-label="Status pembuatan halaman">
      <span
        className={`grid size-8 shrink-0 place-items-center rounded-xl border ${
          pending
            ? "border-blue-200 bg-blue-50 text-primary"
            : failed
              ? "border-red-200 bg-red-50 text-destructive"
              : "border-emerald-200 bg-emerald-50 text-emerald-600"
        }`}
      >
        {pending ? <LoaderCircle className="size-4 animate-spin text-primary" aria-hidden="true" /> : null}
        {failed ? <AlertCircle className="size-4 text-destructive" aria-hidden="true" /> : null}
        {completed ? <CheckCircle2 className="size-4 text-emerald-600" aria-hidden="true" /> : null}
      </span>

      <div className="min-w-0 flex-1 pt-0.5">
        <div
          className={`rounded-2xl border p-3.5 sm:p-4 shadow-xs transition-all ${
            pending
              ? "border-blue-200/80 bg-blue-50/40"
              : failed
                ? "border-red-200 bg-red-50/60"
                : "border-emerald-200 bg-emerald-50/40"
          }`}
        >
          {/* Header Status */}
          <div className="flex items-center gap-2 mb-2">
            <span
              className={`rounded-full px-2 py-0.5 text-[10px] font-medium border ${
                pending
            ? "bg-blue-100/80 text-blue-700 border-blue-200"
                  : failed
                    ? "bg-red-100 text-red-700 border-red-200"
                    : "bg-emerald-100 text-emerald-800 border-emerald-200"
              }`}
            >
              {pending
                ? "Sedang menghasilkan website"
                : failed
                  ? "Kendala Pembuatan"
                  : "Selesai & Terverifikasi"}
            </span>
          </div>

          <p
            className={`whitespace-pre-wrap break-words text-sm font-medium leading-relaxed ${
              failed ? "text-destructive" : "text-foreground"
            }`}
          >
            {message.content}
          </p>

          {pending ? (
            <p className="mt-3 text-xs leading-relaxed text-muted-foreground" role="status">
              Hasil akan muncul setelah halaman selesai dibuat dan melewati pemeriksaan.
            </p>
          ) : null}

          {completed ? (
            <div className="mt-3 flex flex-wrap items-center justify-between gap-2.5 rounded-xl bg-white/95 border border-emerald-200 p-2.5 sm:p-3 text-xs text-foreground shadow-2xs">
              <div className="flex items-center gap-2">
                <Sparkles className="size-4 text-emerald-600 shrink-0" />
                <span className="font-semibold text-emerald-950">Halaman web siap dipratinjau & diunduh</span>
              </div>
              <button
                type="button"
                onClick={onOpenCanvas}
                className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white px-2.5 py-1 text-[11px] font-semibold shadow-xs active:scale-95 transition-all cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                <span>Lihat Kanvas</span>
                <ArrowRight className="size-3" />
              </button>
            </div>
          ) : null}
        </div>
      </div>
    </article>
  );
}

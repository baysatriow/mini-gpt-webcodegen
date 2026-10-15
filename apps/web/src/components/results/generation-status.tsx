import { AlertCircle, CheckCircle2, LoaderCircle } from "lucide-react";
import type { GenerationStatusMessage } from "@/lib/chat-state";

type GenerationStatusProps = { message: GenerationStatusMessage };

export function GenerationStatus({ message }: GenerationStatusProps) {
  const pending = message.status === "pending";
  const failed = message.status === "generation_failed" || message.status === "input_too_long";
  const label = pending
    ? "Menunggu hasil dari API lokal"
    : message.status === "completed"
      ? "Halaman diterima"
      : message.status === "input_too_long"
        ? "Permintaan perlu diringkas"
        : "Halaman belum dibuat";

  return (
    <article className="flex items-start gap-3" aria-label="Status pembuatan halaman">
      <span className={`grid size-8 shrink-0 place-items-center rounded-xl border ${failed ? "border-destructive/20 bg-destructive/5 text-destructive" : "border-border bg-paper text-cobalt-action"}`}>
        {pending ? <LoaderCircle className="size-4 animate-spin" aria-hidden="true" /> : null}
        {failed ? <AlertCircle className="size-4" aria-hidden="true" /> : null}
        {message.status === "completed" ? <CheckCircle2 className="size-4 text-verified" aria-hidden="true" /> : null}
      </span>
      <div className="min-w-0 flex-1 pt-1">
        <p className={`whitespace-pre-wrap break-words text-[15px] leading-7 ${failed ? "text-destructive" : "text-harbor-ink"}`}>
          {message.content}
        </p>
        <p className={`mt-2 text-xs ${failed ? "text-destructive" : message.status === "completed" ? "text-verified" : "text-slate-note"}`} role={failed ? "alert" : "status"}>
          {label}
        </p>
      </div>
    </article>
  );
}

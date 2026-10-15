"use client";

import { AlertCircle, CheckCircle2, LoaderCircle, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { BusinessFactsForm } from "@/components/forms/business-facts-form";
import type { CatalogResponse, RequestDraft } from "@/lib/api-types";
import type { ClarificationMessage } from "@/lib/chat-state";
import { describeMissingFields, intakeActionLabel, INTAKE_STATUS_LABEL } from "@/lib/intake-copy";

type IntakeCardProps = {
  message: ClarificationMessage;
  catalog: CatalogResponse | null;
  onValidate: (message: ClarificationMessage, draft: RequestDraft) => Promise<void>;
  onEditPrompt: (prompt: string) => void;
};

export function IntakeCard({ message, catalog, onValidate, onEditPrompt }: IntakeCardProps) {
  if (message.isValidating) {
    return (
      <article className="flex items-start gap-3" aria-label="Memeriksa permintaan" aria-live="polite">
        <span className="grid size-8 shrink-0 place-items-center rounded-xl border border-border bg-paper text-primary">
          <LoaderCircle aria-hidden="true" className="size-4 animate-spin" />
        </span>
        <div className="min-w-0 flex-1 pt-1">
          <p className="text-[15px] font-medium leading-7 text-harbor-ink">{message.content}</p>
          <p className="mt-1 text-xs text-slate-note">Validasi intake tidak menjalankan generation.</p>
        </div>
      </article>
    );
  }

  if (message.isError) {
    return (
      <article className="flex items-start gap-3" aria-label="Validasi mengalami kendala">
        <span className="grid size-8 shrink-0 place-items-center rounded-xl border border-destructive/20 bg-destructive/5 text-destructive">
          <AlertCircle aria-hidden="true" className="size-4" />
        </span>
        <div className="min-w-0 flex-1 pt-1">
          <p role="alert" className="text-[15px] leading-7 text-destructive">{message.content}</p>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => void onValidate(message, message.draft)}
            className="mt-3 gap-2 rounded-lg"
          >
            <RefreshCw aria-hidden="true" className="size-3.5" />
            Coba validasi lagi
          </Button>
        </div>
      </article>
    );
  }

  if (message.status === "unsupported_request" || message.status === "input_too_long") {
    const unsupported = catalog?.unsupported_capabilities ?? [];
    return (
      <article className="flex items-start gap-3" aria-label={INTAKE_STATUS_LABEL[message.status]}>
        <span className="grid size-8 shrink-0 place-items-center rounded-xl border border-[#E5D6B1] bg-[#FBF8F0] text-[#8A6422]">
          <AlertCircle aria-hidden="true" className="size-4" />
        </span>
        <div className="min-w-0 flex-1 pt-1">
          <p className="text-xs font-semibold text-slate-note">{INTAKE_STATUS_LABEL[message.status]}</p>
          <p className="mt-1 text-[15px] leading-7 text-harbor-ink">{message.content}</p>
          {unsupported.length > 0 ? (
            <div className="mt-3 flex flex-wrap gap-1.5">
              {unsupported.map((item) => (
                <span key={item.id} className="rounded-full border border-border bg-paper px-2.5 py-1 text-xs text-slate-note">
                  {item.label}
                </span>
              ))}
            </div>
          ) : null}
          <p className="mt-2 text-xs leading-5 text-slate-note">
            {catalog?.scope_message ?? "Versi ini mendukung landing page dan company profile dengan CSS biasa atau Tailwind."}
          </p>
          <Button type="button" variant="outline" size="sm" onClick={() => onEditPrompt(message.prompt)} className="mt-3 rounded-lg">
            Edit prompt
          </Button>
          {message.status === "input_too_long" ? (
            <BusinessFactsForm
              prompt={message.prompt}
              initialDraft={message.draft}
              catalog={catalog}
              missingFields={message.missingFields}
              onSubmit={(draft) => onValidate(message, draft)}
            />
          ) : null}
        </div>
      </article>
    );
  }

  const missingLabels = describeMissingFields(message.missingFields);
  return (
    <article className="flex items-start gap-3" aria-label="Lengkapi informasi permintaan">
      <span className="grid size-8 shrink-0 place-items-center rounded-xl border border-primary/15 bg-accent text-primary">
        <CheckCircle2 aria-hidden="true" className="size-4" />
      </span>
      <div className="min-w-0 flex-1 pt-1">
        <p className="text-xs font-semibold text-slate-note">{INTAKE_STATUS_LABEL[message.status]}</p>
        <p className="mt-1 whitespace-pre-wrap break-words text-[15px] leading-7 text-harbor-ink">{message.content}</p>
        {missingLabels.length > 0 ? (
          <p className="mt-2 text-xs leading-5 text-slate-note">
            Perlu dilengkapi: {missingLabels.join(", ")}.
          </p>
        ) : null}
        <p className="mt-1 text-xs leading-5 text-slate-note">{intakeActionLabel(message.status)}</p>
        <BusinessFactsForm
          prompt={message.prompt}
          initialDraft={message.draft}
          catalog={catalog}
          missingFields={message.missingFields}
          onSubmit={(draft) => onValidate(message, draft)}
        />
      </div>
    </article>
  );
}

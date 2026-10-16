"use client";

import { AlertCircle, CheckCircle2, LoaderCircle } from "lucide-react";
import { BusinessFactsForm } from "@/components/forms/business-facts-form";
import { SourceEvidenceDisclosure } from "@/components/chat/source-evidence";
import { Button } from "@/components/ui/button";
import type { CatalogResponse, RequestDraft } from "@/lib/api-types";
import type { ClarificationMessage } from "@/lib/chat-state";
import { describeMissingFields, INTAKE_STATUS_LABEL, labelMissingField } from "@/lib/intake-copy";

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
          <p className="mt-1 text-xs text-slate-note">Memeriksa seluruh brief. Belum ada halaman yang dibuat.</p>
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
          {message.allowManualEditor ? (
            <BusinessFactsForm
              prompt={message.prompt}
              initialDraft={message.draft}
              catalog={catalog}
              missingFields={message.missingFields}
              onlyMissing={message.showOnlyMissing}
              onSubmit={(draft) => onValidate(message, draft)}
            />
          ) : null}
          <Button type="button" variant="outline" size="sm" onClick={() => onEditPrompt(message.prompt)} className="mt-3 rounded-lg">
            Edit brief
          </Button>
        </div>
      </article>
    );
  }

  if (message.status === "unsupported_request" || message.status === "input_too_long") {
    const unsupported = message.unsupportedRequests ?? [];
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
              {unsupported.map((item, index) => (
                <div key={`${item.id ?? item.phrase}-${index}`} className="rounded-xl border border-border bg-paper px-3 py-2.5 text-xs">
                  <p className="font-medium text-harbor-ink">{item.label}</p>
                  <p className="mt-1 text-slate-note">“{item.phrase}”</p>
                  {item.context ? <p className="mt-1 text-slate-note">{item.context}</p> : null}
                </div>
              ))}
            </div>
          ) : null}
          <p className="mt-2 text-xs leading-5 text-slate-note">
            {catalog?.scope_message ?? "Versi ini mendukung landing page dan company profile dengan CSS biasa atau Tailwind."}
          </p>
          <SourceEvidenceDisclosure evidence={message.sourceEvidence ?? []} sourceMessages={message.sourceMessages} />
          <Button type="button" variant="outline" size="sm" onClick={() => onEditPrompt(message.prompt)} className="mt-3 rounded-lg">
            Edit prompt
          </Button>
          {message.allowManualEditor ? (
            <BusinessFactsForm
              prompt={message.prompt}
              initialDraft={message.draft}
              catalog={catalog}
              missingFields={message.missingFields}
              onlyMissing={message.showOnlyMissing}
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
        {message.conflicts?.length ? (
          <ul className="mt-3 space-y-2" aria-label="Informasi yang perlu dipastikan">
            {message.conflicts.map((conflict, index) => (
              <li key={`${conflict.field}-${index}`} className="rounded-xl border border-[#E5D6B1] bg-[#FBF8F0] px-3.5 py-3">
                <p className="text-xs font-semibold text-harbor-ink">{labelMissingField(conflict.field)}</p>
                <p className="mt-1 text-sm leading-6 text-slate-note">{conflict.message}</p>
                {conflict.candidates.length > 0 ? (
                  <p className="mt-2 text-xs leading-5 text-harbor-ink">
                    Pilihan: {conflict.candidates.map((candidate) => String(candidate.value ?? "nilai")).join(" · ")}
                  </p>
                ) : null}
              </li>
            ))}
          </ul>
        ) : null}
        <SourceEvidenceDisclosure evidence={message.sourceEvidence ?? []} sourceMessages={message.sourceMessages} />
        {message.allowManualEditor ? (
          <BusinessFactsForm
            prompt={message.prompt}
            initialDraft={message.draft}
            catalog={catalog}
            missingFields={message.missingFields}
            onlyMissing={message.showOnlyMissing}
            onSubmit={(draft) => onValidate(message, draft)}
          />
        ) : message.status === "needs_clarification" ? (
          <p className="mt-3 rounded-lg bg-accent px-3.5 py-3 text-sm leading-6 text-harbor-ink">
            Balas semua detail yang kurang dalam satu pesan di kolom bawah.
          </p>
        ) : null}
      </div>
    </article>
  );
}

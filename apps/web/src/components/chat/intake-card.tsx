"use client";

import { AlertCircle, CheckCircle2, LoaderCircle, Settings2 } from "lucide-react";
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
        <span className="grid size-8 shrink-0 place-items-center rounded-xl bg-blue-50 text-primary border border-blue-200">
          <LoaderCircle aria-hidden="true" className="size-4 animate-spin" />
        </span>
        <div className="min-w-0 flex-1 pt-1">
          <div className="flex items-center gap-1.5 mb-1">
            <span className="text-xs font-bold text-foreground">VibeCraft</span>
            <span className="rounded bg-blue-100/70 px-1.5 py-0.2 text-[10px] text-primary font-semibold animate-pulse">
              Mengekstrak Fakta...
            </span>
          </div>
          <p className="text-sm font-medium leading-relaxed text-foreground">{message.content}</p>
          <p className="mt-1 text-xs text-muted-foreground">Memeriksa struktur brief dan kelengkapan informasi bisnis.</p>
        </div>
      </article>
    );
  }

  if (message.isError) {
    return (
      <article className="flex items-start gap-3" aria-label="Validasi mengalami kendala">
        <span className="grid size-8 shrink-0 place-items-center rounded-xl border border-destructive/20 bg-destructive/10 text-destructive">
          <AlertCircle aria-hidden="true" className="size-4" />
        </span>
        <div className="min-w-0 flex-1 pt-1">
          <div className="rounded-2xl border border-red-200 bg-red-50/60 p-4 shadow-2xs">
            <p role="alert" className="text-sm leading-relaxed text-destructive font-medium">{message.content}</p>
            {message.allowManualEditor ? (
              <div className="mt-3 pt-3 border-t border-red-200/60">
                <BusinessFactsForm
                  prompt={message.prompt}
                  initialDraft={message.draft}
                  catalog={catalog}
                  missingFields={message.missingFields}
                  onlyMissing={message.showOnlyMissing}
                  templateId={message.templateId}
                  onSubmit={(draft) => onValidate(message, draft)}
                />
              </div>
            ) : null}
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => onEditPrompt(message.prompt)}
              className="mt-3 rounded-xl text-xs h-8 bg-white"
            >
              Edit Brief Awal
            </Button>
          </div>
        </div>
      </article>
    );
  }

  if (message.status === "unsupported_request" || message.status === "input_too_long") {
    const unsupported = message.unsupportedRequests ?? [];
    return (
      <article className="flex items-start gap-3" aria-label={INTAKE_STATUS_LABEL[message.status]}>
        <span className="grid size-8 shrink-0 place-items-center rounded-xl border border-amber-200 bg-amber-50 text-amber-700">
          <AlertCircle aria-hidden="true" className="size-4" />
        </span>
        <div className="min-w-0 flex-1 pt-0.5">
          <div className="rounded-2xl border border-amber-200 bg-amber-50/50 p-4 shadow-2xs">
            <p className="text-xs font-semibold text-amber-800 uppercase tracking-wider">{INTAKE_STATUS_LABEL[message.status]}</p>
            <p className="mt-1 text-sm leading-relaxed text-foreground">{message.content}</p>
            {unsupported.length > 0 ? (
              <div className="mt-3 flex flex-wrap gap-1.5">
                {unsupported.map((item, index) => (
                  <div key={`${item.id ?? item.phrase}-${index}`} className="rounded-xl border border-amber-200 bg-white px-3 py-2 text-xs">
                    <p className="font-medium text-foreground">{item.label}</p>
                    <p className="mt-0.5 text-muted-foreground">“{item.phrase}”</p>
                    {item.context ? <p className="mt-0.5 text-muted-foreground">{item.context}</p> : null}
                  </div>
                ))}
              </div>
            ) : null}
            <p className="mt-2 text-xs leading-5 text-muted-foreground">
              {catalog?.scope_message ?? "Versi ini mendukung landing page dan company profile dengan CSS biasa atau Tailwind."}
            </p>
            <SourceEvidenceDisclosure evidence={message.sourceEvidence ?? []} sourceMessages={message.sourceMessages} />
            <div className="mt-3 flex items-center gap-2">
              <Button type="button" variant="outline" size="sm" onClick={() => onEditPrompt(message.prompt)} className="rounded-xl text-xs h-8 bg-white">
                Edit Prompt
              </Button>
            </div>
            {message.allowManualEditor ? (
              <div className="mt-3 pt-3 border-t border-amber-200/60">
                <BusinessFactsForm
                  prompt={message.prompt}
                  initialDraft={message.draft}
                  catalog={catalog}
                  missingFields={message.missingFields}
                  onlyMissing={message.showOnlyMissing}
                  templateId={message.templateId}
                  onSubmit={(draft) => onValidate(message, draft)}
                />
              </div>
            ) : null}
          </div>
        </div>
      </article>
    );
  }

  const missingLabels = describeMissingFields(message.missingFields);
  return (
    <article className="flex items-start gap-3" aria-label={message.templateId ? "Template website siap diedit" : "Lengkapi informasi permintaan"}>
      <span className="grid size-8 shrink-0 place-items-center rounded-xl border border-blue-200 bg-blue-50 text-primary">
        <CheckCircle2 aria-hidden="true" className="size-4" />
      </span>
      <div className="min-w-0 flex-1 pt-0.5">
        <div className="rounded-2xl border border-border bg-card p-3.5 sm:p-4 shadow-2xs">
          <div className="flex items-center gap-2 mb-1.5">
            <span className="text-xs font-semibold text-foreground">
              {message.templateId ? "Template Siap Disunting" : INTAKE_STATUS_LABEL[message.status]}
            </span>
            <span className="inline-flex items-center gap-1 rounded bg-blue-50 px-2 py-0.5 text-[10px] font-medium text-primary border border-blue-200/60">
              <Settings2 className="size-3" />
              Verifikasi Fakta
            </span>
          </div>

          <p className="whitespace-pre-wrap break-words text-sm leading-relaxed text-foreground">{message.content}</p>

          {missingLabels.length > 0 ? (
            <div className="mt-2.5 rounded-xl bg-amber-50/80 border border-amber-200/80 px-3 py-2 text-xs text-amber-900">
              <span className="font-semibold">Perlu dilengkapi: </span>
              {missingLabels.join(", ")}.
            </div>
          ) : null}

          {message.conflicts?.length ? (
            <ul className="mt-3 space-y-2" aria-label="Informasi yang perlu dipastikan">
              {message.conflicts.map((conflict, index) => (
                <li key={`${conflict.field}-${index}`} className="rounded-xl border border-amber-200 bg-amber-50/60 p-3">
                  <p className="text-xs font-semibold text-foreground">{labelMissingField(conflict.field)}</p>
                  <p className="mt-0.5 text-xs leading-relaxed text-muted-foreground">{conflict.message}</p>
                  {conflict.candidates.length > 0 ? (
                    <p className="mt-1.5 text-xs text-foreground font-medium">
                      Pilihan: {conflict.candidates.map((candidate) => String(candidate.value ?? "nilai")).join(" · ")}
                    </p>
                  ) : null}
                </li>
              ))}
            </ul>
          ) : null}

          <SourceEvidenceDisclosure evidence={message.sourceEvidence ?? []} sourceMessages={message.sourceMessages} />

          {message.allowManualEditor ? (
            <div className="mt-4 pt-3 border-t border-border">
              <BusinessFactsForm
                prompt={message.prompt}
                initialDraft={message.draft}
                catalog={catalog}
                missingFields={message.missingFields}
                onlyMissing={message.showOnlyMissing}
                templateId={message.templateId}
                onSubmit={(draft) => onValidate(message, draft)}
              />
            </div>
          ) : message.status === "needs_clarification" ? (
            <div className="mt-3 rounded-xl bg-blue-50/80 border border-blue-200/80 p-2.5 text-xs leading-relaxed text-primary">
              Balas detail yang kurang dalam satu pesan pada kolom input di bawah.
            </div>
          ) : null}
        </div>
      </div>
    </article>
  );
}

"use client";

import { useState } from "react";
import { Bot, Building2, Coffee, Palette, RefreshCw, Sparkles } from "lucide-react";
import { IntakeCard } from "@/components/chat/intake-card";
import { RequestSummary } from "@/components/chat/request-summary";
import { GenerationStatus } from "@/components/results/generation-status";
import { ScrollArea } from "@/components/ui/scroll-area";
import type { CatalogResponse, RequestDraft } from "@/lib/api-types";
import type { ChatMessage, ClarificationMessage, RequestSummaryMessage } from "@/lib/chat-state";
import { getWebsiteTemplate, WEBSITE_TEMPLATES, type WebsiteTemplateId } from "@/lib/website-templates";

const INITIAL_TEMPLATE_IDS: WebsiteTemplateId[] = ["coffee-shop", "design-studio", "content-studio"];

function iconForCategory(category: string) {
  if (category === "food") return Coffee;
  if (category === "creative") return Palette;
  if (category === "retail") return Building2;
  return Sparkles;
}

type MessageListProps = {
  messages: ChatMessage[];
  onUseTemplate: (templateId: WebsiteTemplateId) => void;
  catalog: CatalogResponse | null;
  onValidate: (message: ClarificationMessage, draft: RequestDraft) => Promise<void>;
  onEditPrompt: (prompt: string) => void;
  onEditSummary: (message: RequestSummaryMessage) => void;
  onConfirmSummary: (message: RequestSummaryMessage) => void;
};

export function MessageList({
  messages,
  onUseTemplate,
  catalog,
  onValidate,
  onEditPrompt,
  onEditSummary,
  onConfirmSummary,
}: MessageListProps) {
  const [visibleTemplateIds, setVisibleTemplateIds] = useState(INITIAL_TEMPLATE_IDS);

  function shuffleTemplates() {
    const currentIds = new Set(visibleTemplateIds);
    const choices = WEBSITE_TEMPLATES
      .filter((template) => !currentIds.has(template.id))
      .map((template) => template.id);
    for (let index = choices.length - 1; index > 0; index -= 1) {
      const randomIndex = Math.floor(Math.random() * (index + 1));
      [choices[index], choices[randomIndex]] = [choices[randomIndex], choices[index]];
    }
    setVisibleTemplateIds(choices.slice(0, 3));
  }

  return (
    <ScrollArea className="min-h-0 flex-1">
      <div role="log" aria-label="Percakapan" aria-live="polite" className="mx-auto flex w-full max-w-3xl flex-col gap-6 px-4 py-6 sm:px-6 sm:py-8">
        {messages.length === 0 ? (
          <div className="flex min-h-[min(62vh,620px)] flex-col justify-center py-4">
            <div className="mb-6 grid size-12 place-items-center rounded-2xl bg-accent text-cobalt-action">
              <Sparkles aria-hidden="true" className="size-5" />
            </div>
            <p className="text-sm font-medium text-primary">Rancang · studio website lokal</p>
            <h1 className="mt-2 max-w-xl text-3xl font-semibold leading-tight tracking-tight text-harbor-ink sm:text-[36px]">
              Ceritakan website yang ingin Anda buat.
            </h1>
            <p className="mt-3 max-w-xl text-[15px] leading-7 text-slate-note">
              Tulis brief sendiri atau pilih satu dari 100 ide. Template mengisi contoh fiktif otomatis dan bisa Anda ubah sebelum ditinjau.
            </p>
            <div className="mt-8 flex flex-wrap items-center justify-between gap-3">
              <p className="text-xs text-slate-note">100 ide contoh fiktif, pilih satu untuk isi form otomatis.</p>
              <button
                type="button"
                onClick={shuffleTemplates}
                className="inline-flex min-h-9 items-center gap-2 rounded-lg border border-border bg-white px-3 text-xs font-medium text-harbor-ink transition-colors hover:border-primary/35 hover:bg-paper"
                aria-label="Acak tiga ide lain dari 100 rekomendasi"
              >
                <RefreshCw aria-hidden="true" className="size-3.5" />
                Acak ide
              </button>
            </div>
            <div className="mt-3 grid gap-2 sm:grid-cols-2" aria-live="polite" aria-label="Rekomendasi website">
              {visibleTemplateIds.map((templateId) => {
                const template = getWebsiteTemplate(templateId);
                const SuggestionIcon = iconForCategory(template.category);
                return (
                  <button
                    key={template.id}
                    type="button"
                    onClick={() => onUseTemplate(template.id)}
                    className="group flex min-h-[76px] items-start gap-3 rounded-xl border border-border bg-paper px-3.5 py-3 text-left transition-colors hover:border-primary/35 hover:bg-white"
                  >
                    <span className="mt-0.5 grid size-7 shrink-0 place-items-center rounded-lg bg-accent text-primary">
                      <SuggestionIcon aria-hidden="true" className="size-3.5" />
                    </span>
                    <span className="min-w-0">
                      <span className="block text-sm font-medium text-harbor-ink">{template.label}</span>
                      <span className="mt-1 block text-xs leading-5 text-slate-note">
                        {template.genre === "company_profile" ? "Company profile" : "Landing page"} · isi otomatis
                      </span>
                    </span>
                  </button>
                );
              })}
            </div>
          </div>
        ) : (
          messages.map((message) => (
            <MessageRow
              key={message.id}
              message={message}
              catalog={catalog}
              onValidate={onValidate}
              onEditPrompt={onEditPrompt}
              onEditSummary={onEditSummary}
              onConfirmSummary={onConfirmSummary}
            />
          ))
        )}
      </div>
    </ScrollArea>
  );
}

type MessageRowProps = {
  message: ChatMessage;
  catalog: CatalogResponse | null;
  onValidate: (message: ClarificationMessage, draft: RequestDraft) => Promise<void>;
  onEditPrompt: (prompt: string) => void;
  onEditSummary: (message: RequestSummaryMessage) => void;
  onConfirmSummary: (message: RequestSummaryMessage) => void;
};

function MessageRow({
  message,
  catalog,
  onValidate,
  onEditPrompt,
  onEditSummary,
  onConfirmSummary,
}: MessageRowProps) {
  if (message.type === "user") {
    return (
      <article className="flex justify-end" aria-label="Pesan Anda">
        <div className="max-w-[88%] rounded-2xl rounded-br-md bg-[#E7EEE8] px-4 py-3 text-[15px] leading-7 text-harbor-ink sm:max-w-[82%]">
          <p className="whitespace-pre-wrap break-words">{message.content}</p>
        </div>
      </article>
    );
  }

  if (message.type === "generation_status") {
    return <GenerationStatus message={message} />;
  }

  if (message.type === "clarification") {
    return (
      <IntakeCard
        message={message}
        catalog={catalog}
        onValidate={onValidate}
        onEditPrompt={onEditPrompt}
      />
    );
  }

  if (message.type === "request_summary") {
    return (
      <RequestSummary
        message={message}
        catalog={catalog}
        onEdit={onEditSummary}
        onConfirm={onConfirmSummary}
      />
    );
  }

  return (
    <article className="flex items-start gap-3" aria-label="Pesan Rancang">
      <MessageMark />
      <div className="min-w-0 flex-1 pt-1">
        <p className={`whitespace-pre-wrap break-words text-[15px] leading-7 ${message.type === "assistant" && message.tone === "error" ? "text-destructive" : "text-harbor-ink"}`}>
          {message.content}
        </p>
      </div>
    </article>
  );
}

function MessageMark() {
  return (
    <span className="grid size-8 shrink-0 place-items-center rounded-xl border border-border bg-paper text-cobalt-action">
      <Bot aria-hidden="true" className="size-4" />
    </span>
  );
}

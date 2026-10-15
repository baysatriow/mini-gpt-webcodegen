"use client";

import { Bot, Building2, CheckCircle2, CircleAlert, Coffee, LoaderCircle, Palette, Sparkles } from "lucide-react";
import { IntakeCard } from "@/components/chat/intake-card";
import { RequestSummary } from "@/components/chat/request-summary";
import { ScrollArea } from "@/components/ui/scroll-area";
import type { CatalogResponse, RequestDraft } from "@/lib/api-types";
import type { ChatMessage, ClarificationMessage, RequestSummaryMessage } from "@/lib/chat-state";

const PROMPT_SUGGESTIONS = [
  {
    label: "Landing page kedai kopi",
    prompt: "Buat landing page untuk kedai kopi dengan nuansa hangat dan sederhana.",
    icon: Coffee,
  },
  {
    label: "Company profile studio desain",
    prompt: "Buat company profile studio desain dengan tampilan bersih dan profesional.",
    icon: Building2,
  },
  {
    label: "Halaman jasa kreatif",
    prompt: "Saya ingin halaman untuk usaha kreatif dengan daftar layanan dan kontak.",
    icon: Palette,
  },
];

type MessageListProps = {
  messages: ChatMessage[];
  onUsePrompt: (prompt: string) => void;
  catalog: CatalogResponse | null;
  onValidate: (message: ClarificationMessage, draft: RequestDraft) => Promise<void>;
  onEditPrompt: (prompt: string) => void;
  onEditSummary: (message: RequestSummaryMessage) => void;
  onConfirmSummary: (message: RequestSummaryMessage) => void;
};

export function MessageList({
  messages,
  onUsePrompt,
  catalog,
  onValidate,
  onEditPrompt,
  onEditSummary,
  onConfirmSummary,
}: MessageListProps) {
  return (
    <ScrollArea className="min-h-0 flex-1">
      <div role="log" aria-label="Percakapan" aria-live="polite" className="mx-auto flex w-full max-w-3xl flex-col gap-6 px-4 py-6 sm:px-6 sm:py-8">
        {messages.length === 0 ? (
          <div className="flex min-h-[min(62vh,620px)] flex-col justify-center py-4">
            <div className="mb-6 grid size-12 place-items-center rounded-2xl bg-accent text-cobalt-action">
              <Sparkles aria-hidden="true" className="size-5" />
            </div>
            <p className="text-sm font-medium text-cobalt-action">Workspace generator lokal</p>
            <h1 className="mt-2 max-w-xl text-3xl font-semibold leading-tight tracking-tight text-harbor-ink sm:text-[36px]">
              Website seperti apa yang ingin Anda buat?
            </h1>
            <p className="mt-3 max-w-xl text-[15px] leading-7 text-slate-note">
              Mulai dari ide. Rancang akan membantu melengkapi detail usaha,
              menampilkan ringkasan, lalu menunggu persetujuan Anda.
            </p>
            <div className="mt-8 grid gap-2 sm:grid-cols-2">
              {PROMPT_SUGGESTIONS.map((suggestion) => {
                const SuggestionIcon = suggestion.icon;
                return (
                  <button
                    key={suggestion.label}
                    type="button"
                    onClick={() => onUsePrompt(suggestion.prompt)}
                    className="group flex min-h-[76px] items-start gap-3 rounded-xl border border-border bg-paper px-3.5 py-3 text-left transition-colors hover:border-primary/35 hover:bg-white"
                  >
                    <span className="mt-0.5 grid size-7 shrink-0 place-items-center rounded-lg bg-frost text-slate-note">
                      <SuggestionIcon aria-hidden="true" className="size-3.5" />
                    </span>
                    <span className="min-w-0">
                      <span className="block text-sm font-medium text-harbor-ink">{suggestion.label}</span>
                      <span className="mt-1 block text-xs leading-5 text-slate-note">
                        Gunakan sebagai titik awal
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
        <div className="max-w-[88%] rounded-2xl rounded-br-md bg-[#E7EEF9] px-4 py-3 text-[15px] leading-7 text-harbor-ink sm:max-w-[82%]">
          <p className="whitespace-pre-wrap break-words">{message.content}</p>
        </div>
      </article>
    );
  }

  if (message.type === "generation_status") {
    const pending = message.status === "pending";
    const failed = message.status === "generation_failed" || message.status === "input_too_long";
    return (
      <article className="flex items-start gap-3" aria-label="Status pembuatan halaman">
        <MessageMark />
        <div className="min-w-0 flex-1 pt-1">
          <p className="whitespace-pre-wrap break-words text-[15px] leading-7 text-harbor-ink">
            {message.content}
          </p>
          <div className={`mt-2 inline-flex items-center gap-2 text-xs ${failed ? "text-destructive" : "text-slate-note"}`}>
            {pending ? <LoaderCircle className="size-3.5 animate-spin" aria-hidden="true" /> : null}
            {failed ? <CircleAlert className="size-3.5" aria-hidden="true" /> : null}
            {message.status === "completed" ? <CheckCircle2 className="size-3.5 text-verified" aria-hidden="true" /> : null}
            <span>{pending ? "Sedang diproses" : message.status === "completed" ? "Selesai" : "Perlu ditinjau"}</span>
          </div>
        </div>
      </article>
    );
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

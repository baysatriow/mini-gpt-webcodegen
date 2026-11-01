"use client";

import { useMemo, useState } from "react";
import {
  Check,
  Code2,
  ChevronRight,
  Coffee,
  Copy,
  GraduationCap,
  HeartPulse,
  Palette,
  RefreshCw,
  ShoppingBag,
  User,
  Wrench,
} from "lucide-react";
import { IntakeCard } from "@/components/chat/intake-card";
import { RequestSummary } from "@/components/chat/request-summary";
import { GenerationStatus } from "@/components/results/generation-status";
import { ScrollArea } from "@/components/ui/scroll-area";
import type { CatalogResponse, RequestDraft } from "@/lib/api-types";
import type { ChatMessage, ClarificationMessage, RequestSummaryMessage } from "@/lib/chat-state";
import type { WebsiteTemplateId } from "@/lib/website-templates";
import { WEBSITE_TEMPLATES } from "@/lib/website-templates";
import {
  sampleWebsiteTemplates,
  WEBSITE_TEMPLATE_CATEGORIES,
  type WebsiteTemplateCategoryFilter,
} from "@/lib/website-template-recommendations";
import { copyTextToClipboard } from "@/lib/clipboard";

function iconForCategory(category: string) {
  if (category === "food") return Coffee;
  if (category === "creative") return Palette;
  if (category === "retail") return ShoppingBag;
  if (category === "service") return Wrench;
  if (category === "learning") return GraduationCap;
  if (category === "wellness") return HeartPulse;
  return Code2;
}

type MessageListProps = {
  messages: ChatMessage[];
  onUseTemplate: (templateId: WebsiteTemplateId) => void;
  catalog: CatalogResponse | null;
  onValidate: (message: ClarificationMessage, draft: RequestDraft) => Promise<void>;
  onEditPrompt: (prompt: string) => void;
  onEditSummary: (message: RequestSummaryMessage) => void;
  onConfirmSummary: (message: RequestSummaryMessage) => void;
  onOpenCanvas: () => void;
};

export function MessageList({
  messages,
  onUseTemplate,
  catalog,
  onValidate,
  onEditPrompt,
  onEditSummary,
  onConfirmSummary,
  onOpenCanvas,
}: MessageListProps) {
  const [selectedCategory, setSelectedCategory] = useState<WebsiteTemplateCategoryFilter>("all");
  const [shuffleSeed, setShuffleSeed] = useState(0);

  const displayedTemplates = useMemo(() => {
    return sampleWebsiteTemplates(WEBSITE_TEMPLATES, selectedCategory, shuffleSeed);
  }, [selectedCategory, shuffleSeed]);

  function handleShuffle() {
    setShuffleSeed((s) => s + 1);
  }

  return (
    <ScrollArea className="min-h-0 flex-1">
      <div
        role="log"
        aria-label="Percakapan"
        aria-live="polite"
        className="mx-auto flex w-full max-w-3xl flex-col gap-4 px-4 py-4 sm:px-6 sm:py-6"
      >
        {messages.length === 0 ? (
          <div className="flex min-h-[min(65vh,640px)] flex-col justify-center py-4">
            <div className="mb-2 text-xs font-medium text-primary">
              WebCraft GPT <span className="text-muted-foreground">by VibeStack</span>
            </div>

            {/* Title & Subtitle */}
            <h1 className="text-3xl font-bold tracking-tight text-foreground sm:text-4xl sm:leading-tight">
              Ceritakan website yang ingin Anda buat.
            </h1>
            <p className="mt-3 max-w-2xl text-sm sm:text-base leading-relaxed text-muted-foreground">
              Tulis satu brief atau pilih ide contoh. Periksa fakta yang tersusun, lalu buat satu halaman dengan preview dan source HTML, CSS, serta JavaScript.
            </p>

            {/* Category Filter Pills & Shuffle Button */}
            <div className="mt-8 flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-border/80 pb-3">
              <div className="flex items-center gap-1.5 overflow-x-auto no-scrollbar">
                {WEBSITE_TEMPLATE_CATEGORIES.map((cat) => (
                  <button
                    key={cat.id}
                    type="button"
                    onClick={() => {
                      setSelectedCategory(cat.id);
                      setShuffleSeed((s) => s + 1);
                    }}
                    className={`shrink-0 rounded-lg px-2.5 py-1 text-xs font-medium transition-all ${
                      selectedCategory === cat.id
                        ? "bg-foreground text-background shadow-xs"
                        : "text-muted-foreground hover:bg-slate-100 hover:text-foreground"
                    }`}
                  >
                    {cat.label}
                  </button>
                ))}
              </div>

              <button
                type="button"
                onClick={handleShuffle}
                className="inline-flex shrink-0 items-center gap-1.5 self-start sm:self-auto rounded-lg border border-slate-200/90 bg-white px-3 py-1.5 text-xs font-semibold text-foreground hover:bg-slate-50 hover:border-slate-300 active:scale-95 transition-all shadow-2xs cursor-pointer"
                aria-label="Acak rekomendasi template"
              >
                <RefreshCw aria-hidden="true" className="size-3.5 text-muted-foreground" />
                Acak Ide
              </button>
            </div>

            {/* Template Cards Grid */}
            <div className="mt-4 grid gap-3 sm:grid-cols-2" aria-live="polite" aria-label="Rekomendasi website">
              {displayedTemplates.map((template) => {
                const SuggestionIcon = iconForCategory(template.category);
                return (
                  <button
                    key={template.id}
                    type="button"
                    onClick={() => onUseTemplate(template.id)}
                    className="group relative flex items-start gap-3.5 rounded-xl border border-border/90 bg-card p-3.5 text-left transition-all hover:border-primary/50 hover:shadow-md hover:-translate-y-0.5"
                  >
                    <span className="grid size-9 shrink-0 place-items-center rounded-xl bg-blue-50 text-primary border border-blue-100 transition-colors group-hover:bg-primary group-hover:text-white">
                      <SuggestionIcon aria-hidden="true" className="size-4" />
                    </span>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center justify-between gap-1">
                        <span className="block text-sm font-medium text-foreground group-hover:text-primary transition-colors">
                          {template.label}
                        </span>
                        <ChevronRight className="size-3.5 text-muted-foreground group-hover:text-primary transition-colors" />
                      </div>
                      <span className="mt-1 block text-xs leading-5 text-muted-foreground">
                        {template.genre === "company_profile" ? "Company profile" : "Landing page"} Â· Contoh fiktif otomatis
                      </span>
                    </div>
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
              onOpenCanvas={onOpenCanvas}
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
  onOpenCanvas: () => void;
};

function MessageRow({
  message,
  catalog,
  onValidate,
  onEditPrompt,
  onEditSummary,
  onConfirmSummary,
  onOpenCanvas,
}: MessageRowProps) {
  const [copyStatus, setCopyStatus] = useState<"idle" | "copied" | "failed">("idle");

  async function copyText(text: string) {
    if (!text) return;
    const copied = await copyTextToClipboard(text);
    setCopyStatus(copied ? "copied" : "failed");
    window.setTimeout(() => setCopyStatus("idle"), 2000);
  }

  if (message.type === "user") {
    return (
      <article className="flex justify-end items-end gap-2" aria-label="Pesan Anda">
        <div className="max-w-[85%] rounded-2xl rounded-br-xs bg-slate-900 px-3.5 py-2.5 text-sm leading-relaxed text-white shadow-sm sm:max-w-[78%]">
          <p className="whitespace-pre-wrap break-words">{message.content}</p>
        </div>
        <div className="size-7 rounded-full bg-slate-200 grid place-items-center text-slate-700 shrink-0">
          <User className="size-3.5" />
        </div>
      </article>
    );
  }

  if (message.type === "generation_status") {
    return <GenerationStatus message={message} onOpenCanvas={onOpenCanvas} />;
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

  const isError = message.type === "assistant" && message.tone === "error";

  return (
    <article className="group flex items-start gap-3" aria-label="Pesan WebCraft GPT">
      <span className="grid size-8 shrink-0 place-items-center rounded-lg bg-primary text-[#f0a080]">
        <Code2 aria-hidden="true" className="size-4" />
      </span>
      <div className="min-w-0 flex-1 pt-0.5">
        <div className="flex items-center gap-1.5 mb-1">
          <span className="text-xs font-semibold text-foreground">WebCraft GPT</span>
        </div>
        <div
          className={`rounded-2xl p-3.5 text-sm leading-relaxed ${
            isError
              ? "border border-red-200 bg-red-50 text-red-900"
              : "border border-border/80 bg-card text-foreground shadow-2xs"
          }`}
        >
          <p className="whitespace-pre-wrap break-words">{message.content}</p>

          <div className="mt-2.5 flex items-center justify-end">
            <button
              type="button"
              onClick={() => void copyText(message.content)}
              className="inline-flex items-center gap-1 text-[11px] text-muted-foreground hover:text-foreground transition-colors"
              title="Salin pesan"
              aria-live="polite"
            >
              {copyStatus === "copied" ? (
                <>
                  <Check className="size-3 text-emerald-600" />
                  <span className="text-emerald-600">Disalin</span>
                </>
              ) : copyStatus === "failed" ? (
                <span className="text-destructive">Tidak dapat menyalin</span>
              ) : (
                <>
                  <Copy className="size-3" />
                  <span>Salin</span>
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </article>
  );
}

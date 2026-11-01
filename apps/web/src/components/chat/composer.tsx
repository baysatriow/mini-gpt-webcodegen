"use client";

import { ArrowUp, Sparkles } from "lucide-react";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";

type ComposerProps = {
  value: string;
  onChange: (value: string) => void;
  onSubmit: (value: string) => void;
  disabled?: boolean;
  maxLength?: number;
};

const QUICK_INSPIRATIONS = [
  { label: "Kedai Kopi", prompt: "Buat landing page kedai kopi artisan modern dengan menu manual brew, biji kopi kemasan, dan suasana hangat." },
  { label: "Studio Desain", prompt: "Buat company profile untuk studio desain grafis & branding digital bernama PixelCraft dengan portfolio proyek dan layanan utama." },
  { label: "Toko Roti & Kue", prompt: "Buat landing page toko roti artisanal dengan pilihan roti sourdough, pastry fresh harian, dan info pemesanan." },
  { label: "Brand Skincare", prompt: "Buat landing page brand perawatan kulit organik dengan formula bahan alami, daftar produk unggulan, dan testimoni." },
];

export function Composer({
  value,
  onChange,
  onSubmit,
  disabled = false,
  maxLength = 4000,
}: ComposerProps) {
  const canSubmit = value.trim().length > 0 && !disabled;

  function submit() {
    if (!canSubmit) return;
    onSubmit(value.trim());
  }

  return (
    <div className="border-t border-border/70 bg-card/90 px-3 pb-3 pt-2 sm:px-5 sm:pb-4">
      <form
        onSubmit={(event) => {
          event.preventDefault();
          submit();
        }}
        className="mx-auto w-full max-w-2xl"
      >
        <label htmlFor="chat-prompt" className="sr-only">
          Jelaskan halaman web yang ingin dibuat
        </label>

        {/* Quick Inspiration Pills */}
        {!value && (
          <div className="mb-2.5 flex items-center gap-1.5 overflow-x-auto pb-1 text-xs no-scrollbar">
            <span className="text-[11px] font-semibold text-muted-foreground shrink-0 pr-1">
              Contoh:
            </span>
            {QUICK_INSPIRATIONS.map((item, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => onChange(item.prompt)}
                className="group inline-flex shrink-0 items-center gap-1.5 rounded-lg border border-slate-200/90 bg-white px-2.5 py-1 text-[11px] font-semibold text-slate-600 shadow-2xs hover:border-blue-400 hover:bg-blue-50/40 hover:text-blue-700 active:scale-95 transition-all cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                <span className="size-1 rounded-full bg-slate-300 group-hover:bg-blue-500 transition-colors" />
                {item.label}
              </button>
            ))}
          </div>
        )}

        <div className="rounded-2xl border border-border bg-background shadow-xs transition-all focus-within:border-primary/50 focus-within:ring-2 focus-within:ring-primary/10">
          <Textarea
            id="chat-prompt"
            aria-describedby={value.length > 0 ? "composer-guidance composer-character-count" : "composer-guidance"}
            value={value}
            onChange={(event) => onChange(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                submit();
              }
            }}
            maxLength={maxLength}
            rows={1}
            disabled={disabled}
            placeholder="Ketik brief website yang ingin Anda buat..."
            className="max-h-36 min-h-[48px] resize-none border-0 bg-transparent px-3.5 pt-3 text-xs sm:text-sm leading-relaxed shadow-none placeholder:text-muted-foreground/60 focus-visible:border-0 focus-visible:ring-0 text-foreground"
          />

          <div className="flex items-center justify-between gap-2 px-3 pb-2.5 pt-0.5">
            <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
              {disabled ? (
                <span className="flex items-center gap-1 text-primary font-medium animate-pulse">
                  <Sparkles className="size-3" />
                  Memproses brief...
                </span>
              ) : null}
            </div>

            <div className="flex shrink-0 items-center gap-2">
              {value.length > 0 ? (
                <span id="composer-character-count" className="text-[10px] tabular-nums text-muted-foreground font-mono">
                  {value.length}/{maxLength}
                </span>
              ) : null}
              <button
                type="submit"
                aria-label="Kirim prompt"
                disabled={!canSubmit}
                className={cn(
                  "flex size-8 shrink-0 items-center justify-center rounded-xl transition-all duration-150 cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                  canSubmit
                    ? "bg-gradient-to-r from-blue-600 to-indigo-600 text-white shadow-sm shadow-blue-500/30 hover:from-blue-700 hover:to-indigo-700 hover:scale-105 active:scale-95"
                    : "bg-slate-100 text-slate-300 cursor-not-allowed",
                )}
              >
                <ArrowUp aria-hidden="true" className="size-4 stroke-[2.5]" />
              </button>
            </div>
          </div>
        </div>
        <p id="composer-guidance" className="mt-1.5 px-1 text-[10px] leading-relaxed text-muted-foreground">
          Tekan Enter untuk mengirim, Shift+Enter untuk membuat baris baru.
        </p>
      </form>
    </div>
  );
}

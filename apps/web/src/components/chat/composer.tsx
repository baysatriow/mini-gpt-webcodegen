"use client";

import { ArrowUp, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";

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

        {/* Quick Inspiration Pills without any emojis */}
        {!value && (
          <div className="mb-2 flex items-center gap-1.5 overflow-x-auto pb-1 text-xs no-scrollbar">
            <span className="text-[11px] font-medium text-muted-foreground shrink-0 pr-1">
              Contoh:
            </span>
            {QUICK_INSPIRATIONS.map((item, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => onChange(item.prompt)}
                className="shrink-0 rounded-lg border border-border/80 bg-background px-2.5 py-1 text-[11px] text-muted-foreground hover:border-primary/40 hover:bg-slate-100 hover:text-foreground transition-all shadow-2xs"
              >
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
                <span className="flex items-center gap-1 text-primary animate-pulse">
                  <Sparkles className="size-3" />
                  Memproses brief...
                </span>
              ) : null}
            </div>

            <div className="flex shrink-0 items-center gap-2">
              {value.length > 0 ? (
                <span id="composer-character-count" className="text-[10px] tabular-nums text-muted-foreground">
                  {value.length}/{maxLength}
                </span>
              ) : null}
              <Button
                type="submit"
                size="icon-sm"
                aria-label="Kirim prompt"
                disabled={!canSubmit}
                className={`size-7.5 rounded-xl transition-all ${
                  canSubmit
                    ? "bg-primary text-primary-foreground hover:bg-primary/90 shadow-2xs"
                    : "bg-muted text-muted-foreground opacity-40"
                }`}
              >
                <ArrowUp aria-hidden="true" className="size-3.5" />
              </Button>
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

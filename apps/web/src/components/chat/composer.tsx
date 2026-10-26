"use client";

import { ArrowUp, Sparkles, Lightbulb } from "lucide-react";
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
  { label: "☕ Kedai Kopi Minimalis", prompt: "Buat landing page kedai kopi artisan modern dengan menu manual brew, biji kopi kemasan, dan suasana hangat." },
  { label: "🚀 Studio Desain Kreatif", prompt: "Buat company profile untuk studio desain grafis & branding digital bernama PixelCraft dengan portfolio proyek dan layanan utama." },
  { label: "🍰 Toko Roti & Kue", prompt: "Buat landing page toko roti artisanal dengan pilihan roti sourdough, pastry fresh harian, dan info pemesanan." },
  { label: "🌿 Brand Skincare Alami", prompt: "Buat landing page brand perawatan kulit organik dengan formula bahan alami, daftar produk unggulan, dan testimoni." },
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
    <div className="border-t border-border/80 bg-background/80 backdrop-blur-md px-4 pb-4 pt-3 sm:px-6 sm:pb-5">
      <form
        onSubmit={(event) => {
          event.preventDefault();
          submit();
        }}
        className="mx-auto w-full max-w-3xl"
      >
        <label htmlFor="chat-prompt" className="sr-only">
          Jelaskan halaman web yang ingin dibuat
        </label>

        {/* Quick Inspiration Pills (shown when input is empty) */}
        {!value && (
          <div className="mb-2 flex items-center gap-1.5 overflow-x-auto pb-1 text-xs no-scrollbar">
            <span className="flex items-center gap-1 text-[11px] font-medium text-muted-foreground shrink-0 pr-1">
              <Lightbulb className="size-3 text-amber-500" />
              Inspirasi:
            </span>
            {QUICK_INSPIRATIONS.map((item, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => onChange(item.prompt)}
                className="shrink-0 rounded-full border border-border bg-white px-2.5 py-1 text-[11px] text-muted-foreground hover:border-primary/40 hover:bg-accent hover:text-primary transition-all shadow-2xs"
              >
                {item.label}
              </button>
            ))}
          </div>
        )}

        <div className="rounded-2xl border border-border bg-card shadow-[0_4px_24px_rgba(15,23,42,0.06)] transition-all focus-within:border-primary/50 focus-within:ring-2 focus-within:ring-primary/10">
          <Textarea
            id="chat-prompt"
            value={value}
            onChange={(event) => onChange(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                submit();
              }
            }}
            maxLength={maxLength}
            rows={2}
            disabled={disabled}
            placeholder="Ceritakan website yang ingin Anda buat... (contoh: Landing page kedai kopi minimalis)"
            aria-describedby="composer-guidance composer-count"
            className="max-h-44 min-h-[72px] resize-none border-0 bg-transparent px-4 pt-3.5 text-sm leading-6 shadow-none placeholder:text-muted-foreground/70 focus-visible:border-0 focus-visible:ring-0 text-foreground"
          />

          <div className="flex items-center justify-between gap-3 px-3 pb-3 pt-1 border-t border-slate-100/60">
            <div className="flex min-w-0 items-center gap-2 text-xs text-muted-foreground">
              <span className="grid size-6 shrink-0 place-items-center rounded-lg bg-blue-50 text-primary">
                <Sparkles aria-hidden="true" className="size-3.5" />
              </span>
              <span id="composer-guidance" className="truncate text-[11px]">
                {disabled ? "Sedang memproses..." : "Tulis ide singkat, lalu tinjau fakta sebelum generate."}
              </span>
            </div>

            <div className="flex shrink-0 items-center gap-2">
              <span id="composer-count" className="hidden text-[11px] tabular-nums text-muted-foreground sm:inline">
                {value.length}/{maxLength}
              </span>
              <Button
                type="submit"
                size="icon"
                aria-label="Kirim prompt"
                disabled={!canSubmit}
                className={`size-8.5 rounded-xl transition-all shadow-xs ${
                  canSubmit
                    ? "bg-primary text-primary-foreground hover:bg-primary/90 hover:scale-105 active:scale-95"
                    : "bg-muted text-muted-foreground opacity-50"
                }`}
              >
                <ArrowUp aria-hidden="true" className="size-4" />
              </Button>
            </div>
          </div>
        </div>

        <p className="mt-2 text-center text-[11px] leading-4 text-muted-foreground">
          Brief tersimpan secara lokal · Generate perlu model dan extractor aktif.
        </p>
      </form>
    </div>
  );
}

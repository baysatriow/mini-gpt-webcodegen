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
    <div className="border-t border-border/80 bg-white/80 px-4 pb-4 pt-3 sm:px-6 sm:pb-5">
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
        <div className="rounded-2xl border border-border bg-paper shadow-[0_6px_24px_rgba(30,45,69,0.06)] transition-shadow focus-within:shadow-[0_8px_28px_rgba(30,45,69,0.10)]">
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
            placeholder="Ceritakan website yang ingin Anda bangun..."
            aria-describedby="composer-guidance composer-count"
            className="max-h-40 min-h-[72px] resize-none border-0 bg-transparent px-4 pt-4 text-[15px] leading-6 shadow-none placeholder:text-slate-note/75 focus-visible:border-0 focus-visible:ring-0"
          />
          <div className="flex items-center justify-between gap-3 px-3 pb-3 pt-1">
            <div className="flex min-w-0 items-center gap-2 text-xs text-slate-note">
              <span className="grid size-7 shrink-0 place-items-center rounded-lg bg-frost">
                <Sparkles aria-hidden="true" className="size-3.5 text-cobalt-action" />
              </span>
              <span id="composer-guidance" className="truncate">
                Satu brief. Jika perlu, semua kekurangan dirangkum sekaligus.
              </span>
            </div>
            <div className="flex shrink-0 items-center gap-2">
              <span id="composer-count" className="hidden text-xs tabular-nums text-slate-note sm:inline">
                {value.length}/{maxLength}
              </span>
              <Button
                type="submit"
                size="icon"
                aria-label="Kirim prompt"
                disabled={!canSubmit}
                className="size-9 rounded-xl"
              >
                <ArrowUp aria-hidden="true" className="size-4" />
              </Button>
            </div>
          </div>
        </div>
        <p className="mt-2 text-center text-[11px] leading-5 text-slate-note">
          Brief tersimpan di perangkat ini. Generate hanya berjalan setelah Anda meninjau fakta.
        </p>
      </form>
    </div>
  );
}

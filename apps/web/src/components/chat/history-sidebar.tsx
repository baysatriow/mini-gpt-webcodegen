"use client";

import { Clock3, Plus, Trash2, WandSparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { cn } from "@/lib/utils";
import type { ChatSession } from "@/lib/chat-state";

type HistorySidebarProps = {
  sessions: ChatSession[];
  activeSessionId: string | null;
  onNew: () => void;
  onSelect: (sessionId: string) => void;
  onDelete: (sessionId: string) => void;
  className?: string;
};

export function HistorySidebar({
  sessions,
  activeSessionId,
  onNew,
  onSelect,
  onDelete,
  className,
}: HistorySidebarProps) {
  return (
    <div className={cn("flex h-full min-h-0 flex-col bg-sidebar", className)}>
      <div className="flex items-center gap-3 px-5 pb-5 pt-6">
        <span className="grid size-10 shrink-0 place-items-center rounded-[14px] bg-primary text-primary-foreground">
          <WandSparkles aria-hidden="true" className="size-5" />
        </span>
        <div className="min-w-0">
          <p className="font-semibold tracking-tight text-sidebar-foreground">Rancang</p>
          <p className="text-xs text-slate-note">Workspace web lokal</p>
        </div>
      </div>

      <div className="px-4">
        <Button onClick={onNew} className="h-10 w-full justify-start gap-2.5 rounded-xl">
          <Plus aria-hidden="true" className="size-4" />
          Percakapan baru
        </Button>
      </div>

      <div className="flex items-center gap-2 px-5 pb-3 pt-7 text-xs font-medium text-slate-note">
        <Clock3 aria-hidden="true" className="size-3.5" />
        Riwayat lokal
      </div>
      <Separator className="mb-2" />

      <nav aria-label="Riwayat percakapan" className="min-h-0 flex-1 overflow-y-auto px-3 pb-4">
        {sessions.length === 0 ? (
          <p className="px-3 py-4 text-sm leading-6 text-slate-note">
            Percakapan yang Anda simpan akan tampil di sini.
          </p>
        ) : (
          <ul className="space-y-1">
            {sessions.map((session) => {
              const active = session.id === activeSessionId;
              return (
                <li key={session.id} className="group flex items-center gap-1">
                  <button
                    type="button"
                    aria-current={active ? "page" : undefined}
                    onClick={() => onSelect(session.id)}
                    className={cn(
                      "min-w-0 flex-1 truncate rounded-lg px-3 py-2.5 text-left text-sm transition-colors",
                      active
                        ? "bg-sidebar-accent font-medium text-sidebar-accent-foreground"
                        : "text-slate-note hover:bg-sidebar-accent/75 hover:text-sidebar-foreground",
                    )}
                  >
                    {session.title}
                  </button>
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon-sm"
                    aria-label={`Hapus percakapan ${session.title}`}
                    onClick={() => onDelete(session.id)}
                    className="shrink-0 text-slate-note opacity-70 hover:text-destructive group-hover:opacity-100"
                  >
                    <Trash2 aria-hidden="true" className="size-3.5" />
                  </Button>
                </li>
              );
            })}
          </ul>
        )}
      </nav>

      <div className="px-4 pb-4">
        <div className="rounded-xl border border-sidebar-border bg-frost px-3.5 py-3">
          <p className="text-xs font-semibold text-harbor-ink">Data tersimpan di browser</p>
          <p className="mt-1 text-xs leading-5 text-slate-note">
            Riwayat ini hanya ada di perangkat Anda.
          </p>
        </div>
      </div>
    </div>
  );
}

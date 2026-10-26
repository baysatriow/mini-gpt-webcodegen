"use client";

import { useMemo, useState } from "react";
import {
  Clock3,
  Globe,
  MessageSquare,
  Plus,
  Search,
  Trash2,
  X,
} from "lucide-react";
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
  const [searchQuery, setSearchQuery] = useState("");

  const filteredSessions = useMemo(() => {
    if (!searchQuery.trim()) return sessions;
    const lower = searchQuery.toLowerCase();
    return sessions.filter((s) => s.title.toLowerCase().includes(lower));
  }, [sessions, searchQuery]);

  return (
    <div className={cn("flex h-full min-h-0 flex-col bg-sidebar select-none", className)}>
      {/* Brand Header */}
      <div className="flex items-center justify-between px-4 pb-4 pt-5">
        <div className="flex items-center gap-3">
          <span className="grid size-9 shrink-0 place-items-center rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-500 text-white shadow-sm shadow-blue-500/25">
            <Globe aria-hidden="true" className="size-4.5" />
          </span>
          <div className="min-w-0">
            <div className="flex items-center gap-1.5">
              <span className="font-semibold tracking-tight text-foreground text-sm">Rancang AI</span>
              <span className="rounded-md bg-blue-50 px-1.5 py-0.5 text-[10px] font-medium text-blue-700 border border-blue-200/60">
                v1.0
              </span>
            </div>
            <p className="text-[11px] text-muted-foreground truncate">Studio Web Generator</p>
          </div>
        </div>
      </div>

      {/* New Chat Button */}
      <div className="px-3 pt-1">
        <Button
          onClick={onNew}
          className="h-9.5 w-full justify-center gap-2 rounded-xl bg-primary text-primary-foreground shadow-sm shadow-primary/20 hover:bg-primary/90 transition-all font-medium text-xs px-3"
        >
          <Plus aria-hidden="true" className="size-4" />
          <span>Percakapan Baru</span>
        </Button>
      </div>

      {/* Search Input if more than 3 sessions */}
      {sessions.length > 3 ? (
        <div className="px-3 pt-3">
          <div className="relative flex items-center">
            <Search className="absolute left-2.5 size-3.5 text-muted-foreground pointer-events-none" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Cari percakapan..."
              aria-label="Cari riwayat percakapan"
              className="w-full h-8 rounded-lg border border-border bg-white pl-8 pr-7 text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary/20 transition-all"
            />
            {searchQuery ? (
              <button
                type="button"
                onClick={() => setSearchQuery("")}
                aria-label="Hapus pencarian"
                className="absolute right-2 text-muted-foreground hover:text-foreground"
              >
                <X className="size-3" />
              </button>
            ) : null}
          </div>
        </div>
      ) : null}

      {/* History Section Title */}
      <div className="flex items-center justify-between px-4 pb-2 pt-5 text-[11px] font-medium text-muted-foreground uppercase tracking-wider">
        <span className="flex items-center gap-1.5">
          <Clock3 aria-hidden="true" className="size-3" />
          Riwayat Percakapan
        </span>
        <span className="text-[10px] tabular-nums">{filteredSessions.length}</span>
      </div>
      <Separator className="mx-3 opacity-60 mb-1" />

      {/* Sessions Nav List */}
      <nav aria-label="Riwayat percakapan" className="min-h-0 flex-1 overflow-y-auto px-2 pb-3">
        {filteredSessions.length === 0 ? (
          <div className="px-3 py-6 text-center">
            <MessageSquare className="mx-auto size-6 text-muted-foreground/40 mb-2" />
            <p className="text-xs text-muted-foreground">
              {searchQuery ? "Tidak ada percakapan yang cocok." : "Belum ada riwayat percakapan tersimpan."}
            </p>
          </div>
        ) : (
          <ul className="space-y-0.5">
            {filteredSessions.map((session) => {
              const active = session.id === activeSessionId;
              return (
                <li key={session.id} className="group relative flex items-center rounded-lg transition-colors">
                  <button
                    type="button"
                    aria-current={active ? "page" : undefined}
                    onClick={() => onSelect(session.id)}
                    className={cn(
                      "flex min-w-0 flex-1 items-center gap-2.5 rounded-lg px-2.5 py-2 text-left text-xs transition-all",
                      active
                        ? "bg-white text-primary font-medium shadow-xs border border-border/80"
                        : "text-muted-foreground hover:bg-slate-200/50 hover:text-foreground",
                    )}
                  >
                    <MessageSquare
                      aria-hidden="true"
                      className={cn("size-3.5 shrink-0 transition-colors", active ? "text-primary" : "text-muted-foreground/60")}
                    />
                    <span className="truncate">{session.title}</span>
                  </button>
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon-xs"
                    aria-label={`Hapus percakapan ${session.title}`}
                    onClick={(e) => {
                      e.stopPropagation();
                      onDelete(session.id);
                    }}
                    className="absolute right-1 text-muted-foreground/60 opacity-0 transition-opacity hover:bg-destructive/10 hover:text-destructive group-hover:opacity-100"
                  >
                    <Trash2 aria-hidden="true" className="size-3" />
                  </Button>
                </li>
              );
            })}
          </ul>
        )}
      </nav>

      {/* Bottom Footer Info */}
      <div className="p-3 pt-2 border-t border-border/60 bg-sidebar">
        <div className="rounded-xl border border-border/80 bg-white p-2.5 shadow-2xs">
          <div className="flex items-center gap-2">
            <span className="size-2 rounded-full bg-blue-500" aria-hidden="true" />
            <p className="text-[11px] font-medium text-foreground">Mode lokal</p>
          </div>
          <p className="mt-1 text-[10px] leading-4 text-muted-foreground">
            Riwayat tersimpan di browser ini. Pemrosesan memakai server aplikasi.
          </p>
        </div>
      </div>
    </div>
  );
}

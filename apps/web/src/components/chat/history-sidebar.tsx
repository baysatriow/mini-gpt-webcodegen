"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import {
  Activity,
  LogOut,
  MessageSquare,
  PanelLeftClose,
  Plus,
  Search,
  Sparkles,
  Trash2,
  X,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { ChatSession } from "@/lib/chat-state";

type HistorySidebarProps = {
  sessions: ChatSession[];
  activeSessionId: string | null;
  onNew: () => void;
  onSelect: (sessionId: string) => void;
  onDelete: (sessionId: string) => void;
  onToggleCollapse?: () => void;
  showLogout?: boolean;
  className?: string;
};

export function HistorySidebar({
  sessions,
  activeSessionId,
  onNew,
  onSelect,
  onDelete,
  onToggleCollapse,
  showLogout = false,
  className,
}: HistorySidebarProps) {
  const [searchQuery, setSearchQuery] = useState("");

  const filteredSessions = useMemo(() => {
    if (!searchQuery.trim()) return sessions;
    const lower = searchQuery.toLowerCase();
    return sessions.filter((s) => s.title.toLowerCase().includes(lower));
  }, [sessions, searchQuery]);

  return (
    <div className={cn("flex h-full min-h-0 flex-col bg-sidebar select-none border-r border-border/80", className)}>
      {/* Brand & Sidebar Close Header */}
      <div className="flex h-[52px] items-center justify-between px-3.5 border-b border-border/60">
        <div className="flex items-center gap-2.5">
          <span className="grid size-7.5 shrink-0 place-items-center rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-600 text-white shadow-sm shadow-blue-500/25">
            <Sparkles aria-hidden="true" className="size-4" />
          </span>
          <div className="flex items-center gap-1.5">
            <span className="font-bold tracking-tight text-foreground text-sm">VibeCraft</span>
            <span className="rounded bg-blue-50 px-1.5 py-0.2 text-[9px] font-bold text-primary border border-blue-200/60">
              AI
            </span>
          </div>
        </div>

        {onToggleCollapse ? (
          <Button
            type="button"
            variant="ghost"
            size="icon-xs"
            onClick={onToggleCollapse}
            aria-label="Tutup sidebar"
            className="text-muted-foreground hover:text-foreground rounded-lg size-7 active:scale-95 transition-all"
            title="Tutup sidebar"
          >
            <PanelLeftClose className="size-4" />
          </Button>
        ) : null}
      </div>

      {/* New Chat Button - Elevated & Tactile */}
      <div className="p-2.5 pb-1">
        <button
          type="button"
          onClick={onNew}
          className="group flex h-9.5 w-full items-center gap-2.5 rounded-xl bg-slate-900 px-3 text-xs font-semibold text-white shadow-sm transition-all duration-150 hover:bg-slate-800 hover:shadow active:scale-[0.98] cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          <div className="grid size-5 place-items-center rounded-lg bg-white/15 text-blue-400 group-hover:bg-blue-600 group-hover:text-white transition-colors">
            <Plus aria-hidden="true" className="size-3.5 stroke-[2.5]" />
          </div>
          <span>Percakapan Baru</span>
        </button>
      </div>

      {/* Search Bar (visible when multiple sessions exist) */}
      {sessions.length > 3 ? (
        <div className="px-2.5 pt-1.5 pb-1">
          <div className="relative flex items-center">
            <Search className="absolute left-2.5 size-3.5 text-muted-foreground pointer-events-none" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Cari percakapan..."
              aria-label="Cari riwayat percakapan"
              className="w-full h-8 rounded-lg border border-border/80 bg-background pl-8 pr-7 text-xs text-foreground placeholder:text-muted-foreground/60 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary/20 transition-all"
            />
            {searchQuery ? (
              <button
                type="button"
                onClick={() => setSearchQuery("")}
                aria-label="Hapus pencarian"
                className="absolute right-2 text-muted-foreground hover:text-foreground cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                <X className="size-3" />
              </button>
            ) : null}
          </div>
        </div>
      ) : null}

      {/* Sessions Nav List */}
      <nav aria-label="Riwayat percakapan" className="min-h-0 flex-1 overflow-y-auto px-2 py-2">
        {filteredSessions.length === 0 ? (
          <div className="px-3 py-8 text-center">
            <MessageSquare className="mx-auto size-5 text-muted-foreground/40 mb-2" />
            <p className="text-xs text-muted-foreground">
              {searchQuery ? "Tidak ada hasil." : "Belum ada riwayat."}
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
                      "flex min-w-0 flex-1 items-center gap-2 rounded-lg px-2.5 py-2 text-left text-xs transition-all cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                      active
                        ? "bg-white text-foreground font-semibold shadow-2xs border border-border/80"
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
                    className="absolute right-1 text-muted-foreground/50 opacity-0 transition-opacity hover:bg-destructive/10 hover:text-destructive group-hover:opacity-100 size-6"
                  >
                    <Trash2 aria-hidden="true" className="size-3" />
                  </Button>
                </li>
              );
            })}
          </ul>
        )}
      </nav>

      {/* Bottom Nav Links */}
      <div className="space-y-1 border-t border-border/70 p-2">
        <Link
          href="/usage"
          aria-label="Buka Usage dan audit generate"
          className="flex h-9 items-center gap-2.5 rounded-lg px-2.5 text-xs font-semibold text-muted-foreground transition-colors hover:bg-slate-200/50 hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          <Activity aria-hidden="true" className="size-4 text-blue-600" />
          <span>Usage Dashboard</span>
        </Link>
        {showLogout ? (
          <form action="/api/auth/logout" method="post">
            <button
              type="submit"
              className="flex h-9 w-full items-center gap-2.5 rounded-lg px-2.5 text-xs font-semibold text-muted-foreground transition-colors hover:bg-slate-200/50 hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              <LogOut aria-hidden="true" className="size-4" />
              <span>Keluar</span>
            </button>
          </form>
        ) : null}
      </div>
    </div>
  );
}

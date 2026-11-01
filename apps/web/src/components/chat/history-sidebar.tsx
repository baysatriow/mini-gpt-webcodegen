"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import {
  Activity,
  Code2,
  LogOut,
  MessageSquare,
  PanelLeftClose,
  Plus,
  Search,
  Trash2,
  X,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { ChatSession } from "@/lib/chat-state";

type HistorySidebarProps = {
  sessions: ChatSession[];
  activeSessionId: string | null;
  activeSection?: "chat" | "usage";
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
  activeSection = "chat",
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
    <div className={cn("flex h-full min-h-0 flex-col bg-sidebar border-r border-sidebar-border", className)}>
      {/* Brand & Sidebar Close Header */}
      <div className="flex h-[64px] items-center justify-between px-4 border-b border-sidebar-border">
        <div className="flex items-center gap-2.5">
          <span className="grid size-8 shrink-0 place-items-center rounded-lg bg-primary text-[#f0a080]">
            <Code2 aria-hidden="true" className="size-4" />
          </span>
          <div className="flex flex-col leading-tight">
            <span className="font-semibold tracking-tight text-foreground text-sm">WebCraft</span>
            <span className="mt-0.5 text-[10px] text-muted-foreground">by VibeStack</span>
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
      <div className="p-3 pb-1">
        <button
          type="button"
          onClick={onNew}
          className="group flex h-10 w-full items-center gap-2.5 rounded-lg bg-primary px-3 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90 active:scale-[0.99] cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          <Plus aria-hidden="true" className="size-4 stroke-[2.25]" />
          <span>Chat baru</span>
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
          aria-current={activeSection === "usage" ? "page" : undefined}
          className={cn(
            "flex h-9 items-center gap-2.5 rounded-lg px-2.5 text-xs font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
            activeSection === "usage"
              ? "bg-sidebar-accent text-sidebar-accent-foreground"
              : "text-muted-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground",
          )}
        >
          <Activity aria-hidden="true" className="size-4 text-primary" />
          <span>Penggunaan</span>
        </Link>
        {showLogout ? (
          <form action="/api/auth/logout" method="post">
            <button
              type="submit"
              className="flex h-9 w-full items-center gap-2.5 rounded-lg px-2.5 text-xs font-semibold text-muted-foreground transition-colors hover:bg-sidebar-accent hover:text-sidebar-accent-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring cursor-pointer"
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

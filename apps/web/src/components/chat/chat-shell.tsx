"use client";

import { useEffect, useMemo, useReducer, useRef, useState } from "react";
import { PanelLeft, PanelRight, PanelTop, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetTrigger,
} from "@/components/ui/sheet";
import { Composer } from "@/components/chat/composer";
import { HistorySidebar } from "@/components/chat/history-sidebar";
import { MessageList } from "@/components/chat/message-list";
import {
  chatReducer,
  createChatSession,
  createMessage,
  initialChatState,
} from "@/lib/chat-state";
import { readChatHistory, writeChatHistory } from "@/lib/history-storage";

type MobilePanel = "conversation" | "preview";

export function ChatShell() {
  const [state, dispatch] = useReducer(chatReducer, initialChatState);
  const [prompt, setPrompt] = useState("");
  const [mobilePanel, setMobilePanel] = useState<MobilePanel>("conversation");
  const [historyOpen, setHistoryOpen] = useState(false);
  const didRestore = useRef(false);

  useEffect(() => {
    if (didRestore.current) return;
    didRestore.current = true;
    const saved = readChatHistory();
    dispatch({
      type: "restore_session",
      sessions: saved.sessions,
      activeSessionId: saved.activeSessionId,
    });
    if (saved.sessions.length === 0) {
      dispatch({ type: "new_session", session: createChatSession() });
    }
  }, []);

  useEffect(() => {
    if (state.restored) writeChatHistory(state);
  }, [state]);

  const activeSession = useMemo(
    () => state.sessions.find((session) => session.id === state.activeSessionId) ?? null,
    [state.sessions, state.activeSessionId],
  );

  function startNewSession() {
    dispatch({ type: "new_session", session: createChatSession() });
    setPrompt("");
    setMobilePanel("conversation");
    setHistoryOpen(false);
  }

  function removeSession(sessionId: string) {
    dispatch({ type: "delete_session", sessionId });
    if (state.sessions.length === 1) {
      dispatch({ type: "new_session", session: createChatSession() });
    }
  }

  function selectSession(sessionId: string) {
    dispatch({ type: "set_active_session", sessionId });
    setPrompt("");
    setMobilePanel("conversation");
    setHistoryOpen(false);
  }

  function sendPrompt(value: string) {
    if (!activeSession || !value.trim()) return;
    const cleanPrompt = value.trim();
    dispatch({
      type: "append_message",
      message: createMessage({ type: "user", content: cleanPrompt }),
      sessionId: activeSession.id,
    });
    dispatch({
      type: "append_message",
      message: createMessage({
        type: "assistant",
        content:
          "Brief sudah tersimpan di riwayat lokal. Saya akan membantu melengkapi fakta usaha, memeriksa ringkasan, lalu menunggu persetujuan Anda sebelum membuat halaman.",
      }),
      sessionId: activeSession.id,
    });
    setPrompt("");
  }

  if (!state.restored || !activeSession) {
    return (
      <main className="grid min-h-svh place-items-center bg-frost text-sm text-slate-note" aria-busy="true">
        <div className="flex items-center gap-2 rounded-xl border border-border bg-paper px-4 py-3">
          <Sparkles aria-hidden="true" className="size-4 text-cobalt-action" />
          Menyiapkan workspace lokal…
        </div>
      </main>
    );
  }

  const historyProps = {
    sessions: state.sessions,
    activeSessionId: activeSession.id,
    onNew: startNewSession,
    onSelect: selectSession,
    onDelete: removeSession,
  };

  return (
    <main className="h-svh min-h-svh overflow-hidden bg-frost text-harbor-ink">
      <div className="flex h-full min-h-0">
        <aside className="hidden w-[252px] shrink-0 border-r border-border lg:flex">
          <HistorySidebar {...historyProps} className="w-full" />
        </aside>

        <div className="flex min-w-0 flex-1 flex-col lg:grid lg:grid-cols-[minmax(390px,0.88fr)_minmax(410px,1.12fr)]">
          <section className={`${mobilePanel === "conversation" ? "flex" : "hidden"} min-h-0 min-w-0 flex-1 flex-col border-r border-border bg-white pb-16 lg:flex lg:pb-0`} aria-label="Percakapan generator">
            <div className="flex h-[62px] shrink-0 items-center justify-between border-b border-border/80 px-4 sm:px-6">
              <div className="flex min-w-0 items-center gap-3">
                <div className="lg:hidden">
                  <Sheet open={historyOpen} onOpenChange={setHistoryOpen}>
                    <SheetTrigger
                      render={
                        <Button variant="ghost" size="icon-sm" aria-label="Buka riwayat percakapan">
                          <PanelLeft aria-hidden="true" className="size-4" />
                        </Button>
                      }
                    />
                    <SheetContent side="left" showCloseButton={false} className="w-[min(88vw,300px)] max-w-none p-0">
                      <HistorySidebar {...historyProps} className="w-full" />
                    </SheetContent>
                  </Sheet>
                </div>
                <div className="min-w-0">
                  <p className="truncate text-sm font-semibold text-harbor-ink">{activeSession.title}</p>
                  <p className="hidden text-xs text-slate-note sm:block">Sesi disimpan di perangkat ini</p>
                </div>
              </div>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={startNewSession}
                className="shrink-0 gap-2 text-slate-note lg:hidden"
              >
                Baru
              </Button>
              <span className="hidden items-center gap-2 rounded-full border border-border px-2.5 py-1 text-[11px] text-slate-note sm:inline-flex">
                <span className="size-1.5 rounded-full bg-verified" aria-hidden="true" />
                Lokal
              </span>
            </div>

            <div className="flex min-h-0 flex-1 flex-col">
              <MessageList
                messages={activeSession.messages}
                onUsePrompt={(suggestion) => setPrompt(suggestion)}
              />
              <Composer value={prompt} onChange={setPrompt} onSubmit={sendPrompt} />
            </div>
          </section>

          <section className={`${mobilePanel === "preview" ? "flex" : "hidden"} min-h-0 min-w-0 flex-1 flex-col bg-frost pb-16 lg:flex lg:pb-0`} aria-label="Kanvas hasil">
            <div className="flex h-[62px] shrink-0 items-center justify-between border-b border-border bg-white/70 px-4 sm:px-6">
              <div>
                <p className="text-sm font-semibold text-harbor-ink">Kanvas halaman</p>
                <p className="hidden text-xs text-slate-note sm:block">Pratinjau hasil yang sudah diterima</p>
              </div>
              <span className="rounded-full border border-border bg-white px-2.5 py-1 text-[11px] text-slate-note">
                Belum ada hasil
              </span>
            </div>

            <div className="flex min-h-0 flex-1 flex-col items-center justify-center px-5 py-8 sm:px-8">
              <div className="w-full max-w-[740px] overflow-hidden rounded-xl border border-border bg-white shadow-[0_16px_48px_rgba(30,45,69,0.08)]">
                <div className="flex h-10 items-center gap-1.5 border-b border-border bg-white px-4">
                  <span className="size-2 rounded-full bg-[#E5A19B]" aria-hidden="true" />
                  <span className="size-2 rounded-full bg-[#E9CB86]" aria-hidden="true" />
                  <span className="size-2 rounded-full bg-[#8CC7B5]" aria-hidden="true" />
                  <span className="ml-3 h-5 flex-1 rounded-md bg-frost" aria-hidden="true" />
                </div>
                <div className="grid min-h-[340px] place-items-center px-6 py-12 text-center sm:min-h-[420px]">
                  <div className="max-w-sm">
                    <div className="mx-auto grid size-12 place-items-center rounded-2xl bg-frost text-slate-note">
                      <PanelTop aria-hidden="true" className="size-5" />
                    </div>
                    <h2 className="mt-4 text-base font-semibold text-harbor-ink">Pratinjau akan muncul di sini</h2>
                    <p className="mt-2 text-sm leading-6 text-slate-note">
                      Lengkapi fakta usaha, tinjau ringkasan, lalu setujui pembuatan halaman.
                    </p>
                  </div>
                </div>
              </div>
              <p className="mt-4 max-w-md text-center text-xs leading-5 text-slate-note">
                Hanya hasil yang lolos validasi renderer yang akan ditampilkan.
              </p>
            </div>
          </section>
        </div>

        <div className="fixed inset-x-0 bottom-0 z-20 flex justify-center border-t border-border bg-white/95 p-2 backdrop-blur lg:hidden">
          <div className="flex w-full max-w-sm rounded-xl bg-frost p-1">
            <Button
              type="button"
              variant={mobilePanel === "conversation" ? "secondary" : "ghost"}
              size="sm"
              aria-pressed={mobilePanel === "conversation"}
              onClick={() => setMobilePanel("conversation")}
              className="flex-1 gap-2 rounded-lg"
            >
              <Sparkles aria-hidden="true" className="size-3.5" />
              Percakapan
            </Button>
            <Button
              type="button"
              variant={mobilePanel === "preview" ? "secondary" : "ghost"}
              size="sm"
              aria-pressed={mobilePanel === "preview"}
              onClick={() => setMobilePanel("preview")}
              className="flex-1 gap-2 rounded-lg"
            >
              <PanelRight aria-hidden="true" className="size-3.5" />
              Kanvas
            </Button>
          </div>
        </div>
      </div>
    </main>
  );
}

"use client";

import { useCallback, useEffect, useMemo, useReducer, useRef, useState } from "react";
import { Code2, Layout, LoaderCircle, MessageSquare, PanelLeft, Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
} from "@/components/ui/sheet";
import { Composer } from "@/components/chat/composer";
import { HistorySidebar } from "@/components/chat/history-sidebar";
import { MessageList } from "@/components/chat/message-list";
import { ResultWorkspace, type WorkspaceView } from "@/components/results/result-workspace";
import type { SourceLoadState } from "@/components/results/source-tabs";
import { ApiClientError, downloadSourceFile, extractPromptMessages, generate, getCatalog, getSource, validateIntake } from "@/lib/api-client";
import type { CatalogResponse, GenerationSummary, PromptMessage, RequestDraft, SourceEvidence, SourceFilename } from "@/lib/api-types";
import {
  chatReducer,
  createChatSession,
  createMessage,
  initialChatState,
  type ClarificationMessage,
  type GenerationStatusMessage,
  type RequestSummaryMessage,
} from "@/lib/chat-state";
import { readChatHistory, writeChatHistory } from "@/lib/history-storage";
import { getFactValue, SOURCE_DRAFT_CONTRACT } from "@/lib/request-draft";
import { getWebsiteTemplate, type WebsiteTemplateId } from "@/lib/website-templates";
import { isValidGenerationId } from "@/lib/preview-url";
import { cn } from "@/lib/utils";

type MobilePanel = "conversation" | WorkspaceView;

export function ChatShell({ showLogout = false }: { showLogout?: boolean }) {
  const [state, dispatch] = useReducer(chatReducer, initialChatState);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [prompt, setPrompt] = useState("");
  const [catalog, setCatalog] = useState<CatalogResponse | null>(null);
  const [mobilePanel, setMobilePanel] = useState<MobilePanel>("conversation");
  const [workspaceView, setWorkspaceView] = useState<WorkspaceView>("preview");
  const [sourceByGeneration, setSourceByGeneration] = useState<Record<string, SourceLoadState>>({});
  const [historyOpen, setHistoryOpen] = useState(false);
  const [promptRewrite, setPromptRewrite] = useState(false);
  const didRestore = useRef(false);
  const activeSessionIdRef = useRef<string | null>(null);
  const generationAttempts = useRef(new Set<string>());
  const sourceRequests = useRef(new Set<string>());
  const sourceCache = useRef(new Map<string, SourceLoadState>());

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
    let active = true;
    getCatalog()
      .then((result) => {
        if (active) setCatalog(result);
      })
      .catch(() => {
        if (active) setCatalog(null);
      });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (state.restored) writeChatHistory(state);
  }, [state]);

  const activeSession = useMemo(
    () => state.sessions.find((session) => session.id === state.activeSessionId) ?? null,
    [state.sessions, state.activeSessionId],
  );
  useEffect(() => {
    activeSessionIdRef.current = activeSession?.id ?? null;
  }, [activeSession?.id]);
  const latestGenerationMessage = useMemo(() => {
    const messages = activeSession?.messages ?? [];
    for (let index = messages.length - 1; index >= 0; index -= 1) {
      const message = messages[index];
      if (message.type === "generation_status") return message;
    }
    return null;
  }, [activeSession?.messages]);
  const acceptedSummary = latestGenerationMessage?.status === "completed"
    ? latestGenerationMessage.summary ?? null
    : null;
  const canViewCode = Boolean(acceptedSummary && isValidGenerationId(acceptedSummary.generation_id));

  const loadSource = useCallback((generationId: string, force = false) => {
    if (!isValidGenerationId(generationId) || sourceRequests.current.has(generationId)) return;
    const cached = sourceCache.current.get(generationId);
    if (!force && cached && cached.status !== "error") return;
    sourceRequests.current.add(generationId);
    const loading: SourceLoadState = { status: "loading" };
    sourceCache.current.set(generationId, loading);
    setSourceByGeneration((current) => ({ ...current, [generationId]: loading }));

    void getSource(generationId)
      .then((source) => {
        const loaded: SourceLoadState = { status: "loaded", source };
        sourceCache.current.set(generationId, loaded);
        setSourceByGeneration((current) => ({ ...current, [generationId]: loaded }));
      })
      .catch((error: unknown) => {
        const failed: SourceLoadState = {
          status: "error",
          message: error instanceof ApiClientError
            ? error.message
            : "Source tidak dapat dimuat dari API lokal. Coba lagi.",
        };
        sourceCache.current.set(generationId, failed);
        setSourceByGeneration((current) => ({ ...current, [generationId]: failed }));
      })
      .finally(() => sourceRequests.current.delete(generationId));
  }, []);

  const downloadAcceptedSource = useCallback(async (generationId: string, filename: SourceFilename) => {
    if (!isValidGenerationId(generationId)) throw new Error("Referensi hasil tidak valid.");
    const blob = await downloadSourceFile(generationId, filename);
    const objectUrl = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = objectUrl;
    link.download = filename;
    link.hidden = true;
    document.body.append(link);
    link.click();
    link.remove();
    window.setTimeout(() => window.URL.revokeObjectURL(objectUrl), 1000);
  }, []);

  function startNewSession() {
    dispatch({ type: "new_session", session: createChatSession() });
    setPrompt("");
    setPromptRewrite(false);
    setMobilePanel("conversation");
    setWorkspaceView("preview");
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
    setPromptRewrite(false);
    setMobilePanel("conversation");
    setWorkspaceView("preview");
    setHistoryOpen(false);
  }

  function emptyDraft(value: string): RequestDraft {
    return {
      contract_version: SOURCE_DRAFT_CONTRACT,
      prompt: value,
      business_facts: [],
      requested_features: [],
      asset_ids: [],
    };
  }

  async function validateDraft(
    sessionId: string,
    message: ClarificationMessage,
    draft: RequestDraft,
    context?: {
      sourceEvidence?: SourceEvidence[];
      sourceMessages?: PromptMessage[];
      extractionToken?: string | null;
    },
  ) {
    const pending: ClarificationMessage = {
      ...message,
      content: "Memeriksa kelengkapan fakta dan cakupan halaman…",
      draft,
      templateId: undefined,
      status: "needs_clarification",
      missingFields: [],
      isValidating: true,
      isError: false,
      sourceEvidence: context?.sourceEvidence ?? message.sourceEvidence,
      sourceMessages: context?.sourceMessages ?? message.sourceMessages,
      createdAt: new Date().toISOString(),
    };
    dispatch({ type: "replace_message", message: pending, sessionId });

    try {
      const response = await validateIntake(message.prompt, draft, context?.extractionToken);
      if (response.status === "ready" && response.request) {
        const summary: RequestSummaryMessage = {
          id: message.id,
          createdAt: new Date().toISOString(),
          type: "request_summary",
          content: response.message,
          prompt: message.prompt,
          draft,
          state: "ready_to_confirm",
          validation: response,
          sourceEvidence: context?.sourceEvidence ?? message.sourceEvidence,
          sourceMessages: context?.sourceMessages ?? message.sourceMessages,
          extractionToken: context?.extractionToken ?? undefined,
        };
        dispatch({ type: "replace_message", message: summary, sessionId });
        return;
      }
      const clarification: ClarificationMessage = {
        ...pending,
        content: response.status === "ready"
          ? "Validasi belum memberikan ringkasan lengkap. Periksa fakta dan kirim kembali."
          : response.message,
        status: response.status === "ready" ? "needs_clarification" : response.status,
        missingFields: response.missing_fields,
        isValidating: false,
        isError: false,
        allowManualEditor: true,
        showOnlyMissing: true,
        createdAt: new Date().toISOString(),
      };
      dispatch({ type: "replace_message", message: clarification, sessionId });
    } catch (error) {
      const clarification: ClarificationMessage = {
        ...pending,
        content: error instanceof ApiClientError
          ? error.message
          : "Validasi intake gagal. Periksa koneksi API lokal lalu coba lagi.",
        isValidating: false,
        isError: true,
        allowManualEditor: true,
        showOnlyMissing: true,
        createdAt: new Date().toISOString(),
      };
      dispatch({ type: "replace_message", message: clarification, sessionId });
    }
  }

  async function runExtraction(sessionId: string, messages: PromptMessage[]) {
    const promptText = messages.map((message) => message.text).join("\n");
    const pending = createMessage({
      type: "clarification",
      content: "Membaca brief dan memeriksa fakta yang Anda berikan…",
      prompt: promptText,
      draft: emptyDraft(promptText),
      status: "needs_clarification",
      missingFields: [],
      isValidating: true,
      sourceMessages: messages,
    });
    dispatch({ type: "append_message", message: pending, sessionId });

    try {
      const response = await extractPromptMessages(messages);
      const responseDraft = response.draft
        ? { ...response.draft, prompt: promptText }
        : emptyDraft(promptText);
      if (response.status === "ready" && response.draft) {
        await validateDraft(sessionId, pending, responseDraft, {
          sourceEvidence: response.evidence,
          sourceMessages: messages,
          extractionToken: response.resolution_token,
        });
        return;
      }

      const clarification: ClarificationMessage = {
        ...pending,
        content: response.message,
        draft: responseDraft,
        status: response.status === "unsupported" ? "unsupported_request" : "needs_clarification",
        missingFields: response.missing_fields,
        isValidating: false,
        isError: false,
        allowManualEditor: response.status === "needs_clarification" && messages.length > 1,
        showOnlyMissing: response.status === "needs_clarification" && messages.length > 1,
        sourceEvidence: response.evidence,
        sourceMessages: messages,
        conflicts: response.conflicts,
        unsupportedRequests: response.unsupported_requests,
        createdAt: new Date().toISOString(),
      };
      dispatch({ type: "replace_message", sessionId, message: clarification });
    } catch (error) {
      if (error instanceof ApiClientError && error.status === 503 && error.code === "extractor_unavailable") {
        try {
          const fallback = await validateIntake(promptText, emptyDraft(promptText));
          const fallbackStatus = fallback.status === "ready" ? "needs_clarification" : fallback.status;
          const clarification: ClarificationMessage = {
            ...pending,
            content: "Model ekstraksi belum aktif. Brief tetap tersimpan. Lengkapi fakta yang diminta dalam satu form, lalu tinjau rancangan sebelum membuat halaman.",
            draft: emptyDraft(promptText),
            status: fallbackStatus,
            missingFields: fallback.missing_fields.filter((field) => field !== "request_draft"),
            isValidating: false,
            isError: false,
            allowManualEditor: fallbackStatus === "needs_clarification" || fallbackStatus === "unsupported_request",
            showOnlyMissing: true,
            sourceMessages: messages,
            createdAt: new Date().toISOString(),
          };
          dispatch({ type: "replace_message", sessionId, message: clarification });
          return;
        } catch {
          // Keep the existing error path if the validation fallback is also unavailable.
        }
      }

      const status = error instanceof ApiClientError && error.status === 413
        ? "input_too_long"
        : "needs_clarification";
      const explanation = error instanceof ApiClientError
        ? error.message
        : "Brief belum berhasil diproses. Periksa API lokal lalu coba lagi.";
      const clarification: ClarificationMessage = {
        ...pending,
        content: `${explanation} Brief tetap tersimpan. Anda dapat melengkapi detail lewat editor manual.`,
        status,
        isValidating: false,
        isError: true,
        allowManualEditor: true,
        showOnlyMissing: false,
        createdAt: new Date().toISOString(),
      };
      dispatch({ type: "replace_message", sessionId, message: clarification });
    }
  }

  function sendPrompt(value: string) {
    if (!activeSession || !value.trim()) return;
    const cleanPrompt = value.trim();
    let lastBoundary = -1;
    activeSession.messages.forEach((message, index) => {
      if (message.type === "request_summary" || message.type === "generation_status") {
        lastBoundary = index;
      }
    });
    const previousUserMessages = activeSession.messages
      .slice(lastBoundary + 1)
      .filter((message) => message.type === "user")
      .map((message) => ({ id: message.id, text: message.content }));
    const userMessage = createMessage({ type: "user", content: cleanPrompt });
    dispatch({
      type: "append_message",
      message: userMessage,
      sessionId: activeSession.id,
    });
    void runExtraction(activeSession.id, [
      ...(promptRewrite ? [] : previousUserMessages),
      { id: userMessage.id, text: cleanPrompt },
    ]);
    setPrompt("");
    setPromptRewrite(false);
  }

  function useTemplate(templateId: WebsiteTemplateId) {
    if (!activeSession || activeSession.messages.length > 0) return;
    const template = getWebsiteTemplate(templateId);
    const userMessage = createMessage({ type: "user", content: template.prompt });
    const clarification = createMessage({
      type: "clarification",
      content: "Template fiktif sudah diisi otomatis. Periksa dan ubah detailnya sebelum meninjau rancangan.",
      prompt: template.prompt,
      draft: emptyDraft(template.prompt),
      status: "needs_clarification",
      missingFields: [],
      allowManualEditor: true,
      showOnlyMissing: false,
      templateId,
    });
    dispatch({ type: "append_message", message: userMessage, sessionId: activeSession.id });
    dispatch({ type: "append_message", message: clarification, sessionId: activeSession.id });
    setPrompt("");
    setPromptRewrite(false);
  }

  function editSummary(message: RequestSummaryMessage) {
    const clarification: ClarificationMessage = {
      id: message.id,
      createdAt: new Date().toISOString(),
      type: "clarification",
      content: "Perbarui bagian yang ingin diubah, lalu validasi lagi sebelum menyetujui ringkasan.",
      prompt: message.prompt,
      draft: message.draft,
      status: "needs_clarification",
      missingFields: [],
      allowManualEditor: true,
      showOnlyMissing: false,
    };
    dispatch({ type: "replace_message", message: clarification, sessionId: activeSession?.id });
  }

  function failGeneration(
    sessionId: string,
    request: RequestSummaryMessage,
    pending: GenerationStatusMessage,
    status: "generation_failed" | "input_too_long",
    content: string,
  ) {
    dispatch({
      type: "replace_message",
      sessionId,
      message: {
        ...request,
        state: "ready_to_confirm",
        content: request.validation.message,
        createdAt: new Date().toISOString(),
      },
    });
    dispatch({
      type: "replace_message",
      sessionId,
      message: { ...pending, status, content, createdAt: new Date().toISOString() },
    });
    generationAttempts.current.delete(request.id);
    if (activeSessionIdRef.current === sessionId) {
      setWorkspaceView("preview");
      setMobilePanel("conversation");
    }
  }

  async function runGeneration(sessionId: string, request: RequestSummaryMessage, pending: GenerationStatusMessage) {
    try {
      const response = await generate(request.prompt, request.draft, request.extractionToken);
      const requiredFiles: SourceFilename[] = ["index.html", "styles.css", "app.js"];
      const filesReady = requiredFiles.every((filename) => response.files.includes(filename));

      if (response.status !== "completed") {
        const status = response.status === "input_too_long" ? "input_too_long" : "generation_failed";
        failGeneration(
          sessionId,
          request,
          pending,
          status,
          response.message || (status === "input_too_long"
            ? "Ringkas prompt atau fakta secara manual lalu coba kembali."
            : "Halaman belum berhasil dibuat. Periksa ringkasan dan coba lagi."),
        );
        return;
      }

      if (!isValidGenerationId(response.generation_id) || !filesReady) {
        failGeneration(
          sessionId,
          request,
          pending,
          "generation_failed",
          "Respons API belum berisi ID hasil dan tiga file yang diperlukan. Tidak ada preview atau unduhan yang ditampilkan.",
        );
        return;
      }

      const createdAt = new Date().toISOString();
      const summary: GenerationSummary = {
        ...response,
        generation_id: response.generation_id,
        genre: request.draft.genre ?? null,
        style_mode: request.draft.style_mode ?? null,
        business_name: getFactValue(request.draft, "name") || null,
        created_at: createdAt,
      };
      const completed: GenerationStatusMessage = {
        ...pending,
        status: "completed",
        generationId: response.generation_id,
        summary,
        content: response.message || "Halaman berhasil dibuat dan siap ditinjau.",
        createdAt,
      };
      dispatch({ type: "replace_message", sessionId, message: completed });
      dispatch({ type: "set_generation", sessionId, generationId: response.generation_id, updatedAt: createdAt });
      if (activeSessionIdRef.current === sessionId) {
        setWorkspaceView("preview");
        setMobilePanel("preview");
      }
    } catch (error) {
      failGeneration(
        sessionId,
        request,
        pending,
        "generation_failed",
        error instanceof ApiClientError
          ? error.message
          : "Pembuatan halaman gagal terhubung ke API lokal. Periksa layanan lalu coba lagi.",
      );
    }
  }

  function confirmSummary(message: RequestSummaryMessage) {
    const sessionId = activeSession?.id;
    if (!sessionId || message.state !== "ready_to_confirm" || generationAttempts.current.has(message.id)) return;
    generationAttempts.current.add(message.id);
    const now = new Date().toISOString();
    const pending = createMessage({
      type: "generation_status",
      requestSummaryId: message.id,
      status: "pending",
      content: "Mengirim rancangan yang disetujui untuk diproses. Tunggu hasilnya sebelum meninggalkan sesi.",
    });
    dispatch({
      type: "replace_message",
      sessionId,
      message: {
        ...message,
        state: "confirmed",
        content: "Ringkasan disetujui. Halaman dibuat berdasarkan fakta dan ruang lingkup di atas.",
        createdAt: now,
      },
    });
    dispatch({ type: "append_message", sessionId, message: pending });
    setWorkspaceView("preview");
    setMobilePanel("preview");
    void runGeneration(sessionId, message, pending);
  }

  function editPrompt(value: string) {
    setPrompt(value);
    setPromptRewrite(true);
    setMobilePanel("conversation");
    window.requestAnimationFrame(() => document.getElementById("chat-prompt")?.focus());
  }

  if (!state.restored || !activeSession) {
    return (
      <main className="grid min-h-svh place-items-center bg-frost text-sm text-slate-note" aria-busy="true">
        <div className="flex items-center gap-2 rounded-xl border border-border bg-card px-4 py-3 shadow-xs">
          <LoaderCircle aria-hidden="true" className="size-4 animate-spin text-primary" />
          Menyiapkan workspace…
        </div>
      </main>
    );
  }

  const historyProps = {
    showLogout,
    sessions: state.sessions,
    activeSessionId: activeSession.id,
    onNew: startNewSession,
    onSelect: selectSession,
    onDelete: removeSession,
    onToggleCollapse: () => setSidebarOpen(false),
  };

  function handleToggleSidebar() {
    if (typeof window !== "undefined" && window.innerWidth < 1024) {
      setHistoryOpen(true);
    } else {
      setSidebarOpen((prev) => !prev);
    }
  }

  const sourceState = acceptedSummary
    ? sourceByGeneration[acceptedSummary.generation_id] ?? { status: "idle" as const }
    : { status: "idle" as const };
  const latestMessage = activeSession.messages.at(-1) ?? null;
  const composerDisabled =
    (latestMessage?.type === "clarification" && (latestMessage.isValidating || (latestMessage.allowManualEditor && !promptRewrite)))
    || (latestMessage?.type === "generation_status" && latestMessage.status === "pending");

  return (
    <main className="h-svh min-h-svh overflow-hidden bg-background text-foreground">
      <div className="flex h-full min-h-0">
        {/* Collapsible Desktop Sidebar */}
        <aside
          className={cn(
            "hidden shrink-0 border-r border-border bg-sidebar transition-all duration-200 lg:flex",
            sidebarOpen ? "w-[260px]" : "w-0 overflow-hidden border-r-0",
          )}
        >
          <HistorySidebar {...historyProps} className="w-[260px]" />
        </aside>

        <div className="flex min-w-0 flex-1 flex-col lg:grid lg:grid-cols-[minmax(0,0.88fr)_minmax(0,1.12fr)]">
          {/* Conversation Panel */}
          <section
            className={`${mobilePanel === "conversation" ? "flex" : "hidden"} min-h-0 min-w-0 flex-1 flex-col border-r border-border bg-card pb-14 lg:flex lg:pb-0`}
            aria-label="Percakapan generator"
          >
            {/* Header */}
            <div className="flex min-h-[58px] shrink-0 items-center justify-between border-b border-border bg-card px-3.5 py-2 sm:px-4">
              <div className="flex min-w-0 items-center gap-2">
                <button
                  type="button"
                  onClick={handleToggleSidebar}
                  aria-label={sidebarOpen ? "Tutup sidebar" : "Buka sidebar"}
                  title={sidebarOpen ? "Tutup sidebar" : "Buka sidebar"}
                  className="grid size-8 place-items-center rounded-lg text-muted-foreground hover:bg-muted hover:text-foreground transition-colors cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                >
                  <PanelLeft aria-hidden="true" className="size-4" />
                </button>

                {/* Mobile Drawer */}
                <div className="lg:hidden">
                  <Sheet open={historyOpen} onOpenChange={setHistoryOpen}>
                    <SheetContent side="left" showCloseButton={false} className="w-[min(88vw,300px)] max-w-none p-0">
                      <HistorySidebar {...historyProps} className="w-full" />
                    </SheetContent>
                  </Sheet>
                </div>

                <div className="min-w-0">
                  <span className="block text-[10px] leading-tight text-muted-foreground lg:hidden">WebCraft GPT</span>
                  <p className="truncate text-xs sm:text-sm font-semibold text-foreground">
                    {activeSession.title}
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={startNewSession}
                  aria-label="Percakapan Baru"
                  className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-border bg-card px-2.5 text-xs font-semibold text-foreground transition-colors hover:bg-muted active:scale-[0.98] cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                >
                  <Plus className="size-3.5 text-primary stroke-[2.25]" />
                  <span className="hidden sm:inline">Chat baru</span>
                </button>
              </div>
            </div>

            {/* Messages & Composer */}
            <div className="flex min-h-0 flex-1 flex-col bg-background">
              <MessageList
                messages={activeSession.messages}
                onUseTemplate={useTemplate}
                catalog={catalog}
                onValidate={(message, draft) => validateDraft(activeSession.id, message, draft)}
                onEditPrompt={editPrompt}
                onEditSummary={editSummary}
                onConfirmSummary={confirmSummary}
                onOpenCanvas={() => {
                  setWorkspaceView("preview");
                  setMobilePanel("preview");
                }}
              />
              <Composer value={prompt} onChange={setPrompt} onSubmit={sendPrompt} disabled={composerDisabled} />
            </div>
          </section>

          {/* Results Canvas Panel */}
          <section
            className={`${mobilePanel !== "conversation" ? "flex" : "hidden"} min-h-0 min-w-0 flex-1 flex-col bg-background pb-14 lg:flex lg:pb-0`}
            aria-label="Kanvas hasil"
          >
            <ResultWorkspace
              summary={acceptedSummary}
              status={latestGenerationMessage?.status ?? null}
              statusMessage={latestGenerationMessage?.content ?? null}
              view={workspaceView}
              onViewChange={(view) => {
                setWorkspaceView(view);
                setMobilePanel(view);
              }}
              sourceState={sourceState}
              onLoadSource={loadSource}
              onDownloadSource={downloadAcceptedSource}
            />
          </section>
        </div>

        {/* Floating Mobile Bottom Navigation */}
        <div className="fixed inset-x-0 bottom-0 z-20 flex justify-center border-t border-border bg-card p-2 lg:hidden">
          <div className={`flex w-full rounded-xl bg-muted p-1 border border-border ${canViewCode ? "max-w-lg" : "max-w-sm"}`} role="group" aria-label="Pilih tampilan">
            <Button
              type="button"
              variant={mobilePanel === "conversation" ? "secondary" : "ghost"}
              size="sm"
              aria-pressed={mobilePanel === "conversation"}
              onClick={() => setMobilePanel("conversation")}
              className={`flex-1 gap-1.5 rounded-xl text-xs font-medium transition-all ${
                mobilePanel === "conversation" ? "bg-card text-primary shadow-2xs font-semibold" : "text-muted-foreground hover:text-foreground"
              }`}
            >
              <MessageSquare aria-hidden="true" className="size-3.5 text-primary" />
              Percakapan
            </Button>
            <Button
              type="button"
              variant={mobilePanel === "preview" ? "secondary" : "ghost"}
              size="sm"
              aria-pressed={mobilePanel === "preview"}
              onClick={() => {
                setMobilePanel("preview");
                setWorkspaceView("preview");
              }}
              className={`flex-1 gap-1.5 rounded-xl text-xs font-medium transition-all ${
                mobilePanel === "preview" ? "bg-card text-primary shadow-2xs font-semibold" : "text-muted-foreground hover:text-foreground"
              }`}
            >
              <Layout aria-hidden="true" className="size-3.5" />
              Kanvas
            </Button>
            {canViewCode ? (
              <Button
                type="button"
                variant={mobilePanel === "code" ? "secondary" : "ghost"}
                size="sm"
                aria-pressed={mobilePanel === "code"}
                onClick={() => {
                  setMobilePanel("code");
                  setWorkspaceView("code");
                }}
                className={`flex-1 gap-1.5 rounded-xl text-xs font-medium transition-all ${
                mobilePanel === "code" ? "bg-card text-primary shadow-2xs font-semibold" : "text-muted-foreground hover:text-foreground"
                }`}
              >
                <Code2 aria-hidden="true" className="size-3.5" />
                Kode
              </Button>
            ) : null}
          </div>
        </div>
      </div>
    </main>
  );
}

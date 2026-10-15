import type { ChatMessage, ChatSession, ChatState } from "@/lib/chat-state";
import type { RequestDraft } from "@/lib/api-types";
import { isValidGenerationId } from "@/lib/preview-url";

const STORAGE_KEY = "rancang.chat-history";
const STORAGE_VERSION = 1;
const MAX_SESSIONS = 40;
const INTAKE_STATUSES = new Set(["needs_clarification", "unsupported_request", "input_too_long", "ready"]);
const GENERATION_STATUSES = new Set(["completed", "generation_failed", "input_too_long"]);
const SOURCE_FILES = new Set(["index.html", "styles.css", "app.js"]);

type StoredHistory = {
  version: number;
  sessions: ChatSession[];
  activeSessionId: string | null;
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isDraft(value: unknown): value is RequestDraft {
  return isRecord(value)
    && Array.isArray(value.business_facts)
    && Array.isArray(value.requested_features)
    && Array.isArray(value.asset_ids);
}

function isGenerationSummary(value: unknown): boolean {
  if (!isRecord(value)) return false;
  return isValidGenerationId(value.generation_id)
    && value.status === "completed"
    && typeof value.message === "string"
    && (value.genre === null || typeof value.genre === "string")
    && (value.style_mode === null || typeof value.style_mode === "string")
    && (value.business_name === null || typeof value.business_name === "string")
    && (value.section_count === null || typeof value.section_count === "number")
    && (value.created_at === null || typeof value.created_at === "string")
    && (value.preview_url === null || typeof value.preview_url === "string")
    && (value.download_url === null || typeof value.download_url === "string")
    && Array.isArray(value.files)
    && value.files.every((file) => typeof file === "string" && SOURCE_FILES.has(file));
}

function isChatMessage(value: unknown): value is ChatMessage {
  if (!isRecord(value) || typeof value.id !== "string" || typeof value.createdAt !== "string") return false;
  if (typeof value.content !== "string") return false;
  switch (value.type) {
    case "user":
    case "assistant":
      return true;
    case "clarification":
      return typeof value.prompt === "string"
        && isDraft(value.draft)
        && Array.isArray(value.missingFields)
        && value.missingFields.every((field) => typeof field === "string")
        && typeof value.status === "string"
        && INTAKE_STATUSES.has(value.status);
    case "request_summary":
      return typeof value.prompt === "string"
        && isDraft(value.draft)
        && isRecord(value.validation)
        && value.validation.status === "ready"
        && typeof value.validation.message === "string"
        && Array.isArray(value.validation.missing_fields)
        && typeof value.state === "string"
        && ["editing", "ready_to_confirm", "confirmed"].includes(value.state);
    case "generation_status":
      return (value.status === "pending" || (typeof value.status === "string" && GENERATION_STATUSES.has(value.status)))
        && (value.requestSummaryId === undefined || typeof value.requestSummaryId === "string")
        && (value.generationId === undefined || typeof value.generationId === "string")
        && (value.summary === undefined || isGenerationSummary(value.summary));
    default:
      return false;
  }
}

function isChatSession(value: unknown): value is ChatSession {
  return isRecord(value)
    && typeof value.id === "string"
    && typeof value.title === "string"
    && typeof value.updatedAt === "string"
    && Array.isArray(value.messages)
    && value.messages.every(isChatMessage)
    && Array.isArray(value.generationIds)
    && value.generationIds.every((id) => typeof id === "string");
}

export function readChatHistory(): Pick<ChatState, "sessions" | "activeSessionId"> {
  if (typeof window === "undefined") return { sessions: [], activeSessionId: null };
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return { sessions: [], activeSessionId: null };
    const parsed: unknown = JSON.parse(raw);
    if (!isRecord(parsed) || parsed.version !== STORAGE_VERSION || !Array.isArray(parsed.sessions)) {
      return { sessions: [], activeSessionId: null };
    }
    if (!parsed.sessions.every(isChatSession)) return { sessions: [], activeSessionId: null };
    const sessions = (parsed.sessions as ChatSession[])
      .slice(0, MAX_SESSIONS)
      .sort((left, right) => right.updatedAt.localeCompare(left.updatedAt));
    const savedActiveId = typeof parsed.activeSessionId === "string" ? parsed.activeSessionId : null;
    const activeSessionId = sessions.some((session) => session.id === savedActiveId)
      ? savedActiveId
      : sessions[0]?.id ?? null;
    return { sessions, activeSessionId };
  } catch {
    return { sessions: [], activeSessionId: null };
  }
}

export function writeChatHistory(state: ChatState): boolean {
  if (typeof window === "undefined" || !state.restored) return false;
  try {
    const saved: StoredHistory = {
      version: STORAGE_VERSION,
      sessions: state.sessions.slice(0, MAX_SESSIONS),
      activeSessionId: state.activeSessionId,
    };
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(saved));
    return true;
  } catch {
    return false;
  }
}

export function clearChatHistory(): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.removeItem(STORAGE_KEY);
  } catch {
    // Browser storage can be disabled by the user or browser policy.
  }
}

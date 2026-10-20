import type { ChatMessage, ChatSession, ChatState } from "@/lib/chat-state";
import type { RequestDraft } from "@/lib/api-types";
import { isValidGenerationId } from "@/lib/preview-url";
import { isWebsiteTemplateId } from "@/lib/website-templates";

const STORAGE_KEY = "rancang.chat-history";
const STORAGE_VERSION = 1;
const MAX_SESSIONS = 40;
const INTAKE_STATUSES = new Set(["needs_clarification", "unsupported_request", "input_too_long", "ready"]);
const GENERATION_STATUSES = new Set(["completed", "generation_failed", "input_too_long"]);
const SOURCE_FILES = new Set(["index.html", "styles.css", "app.js"]);
const FACT_IDS = /^[a-z][a-z0-9_-]{0,63}$/;
const ASSET_IDS = /^[a-z][a-z0-9_-]{0,63}$/;
const SCALAR_FACTS = new Set(["name", "description", "value"]);
const STRUCTURED_FACTS = new Set(["service", "project", "process", "faq"]);

type StoredHistory = {
  version: number;
  sessions: ChatSession[];
  activeSessionId: string | null;
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function hasOnlyKeys(value: Record<string, unknown>, keys: string[]): boolean {
  const actual = Object.keys(value);
  return actual.length === keys.length && keys.every((key) => Object.prototype.hasOwnProperty.call(value, key));
}

function isIntegerInRange(value: unknown, minimum: number, maximum?: number): value is number {
  return typeof value === "number"
    && Number.isInteger(value)
    && value >= minimum
    && (maximum === undefined || value <= maximum);
}

function isFactEvidence(value: unknown): boolean {
  if (!isRecord(value)) return false;
  if (hasOnlyKeys(value, ["user_confirmed"])) return value.user_confirmed === true;
  if (!hasOnlyKeys(value, ["source_span"]) || !isRecord(value.source_span)) return false;
  const span = value.source_span;
  return hasOnlyKeys(span, ["start", "end"])
    && isIntegerInRange(span.start, 0)
    && isIntegerInRange(span.end, 1)
    && span.end > span.start;
}

function isCapabilityEvidence(value: unknown): boolean {
  if (!isRecord(value)) return false;
  if (hasOnlyKeys(value, ["user_confirmed"])) return value.user_confirmed === true;
  if (!hasOnlyKeys(value, ["source_span"]) || !isRecord(value.source_span)) return false;
  const span = value.source_span;
  return hasOnlyKeys(span, ["start", "end", "quote"])
    && isIntegerInRange(span.start, 0)
    && isIntegerInRange(span.end, 1)
    && span.end > span.start
    && typeof span.quote === "string"
    && span.quote.length > 0
    && span.quote.length <= 100;
}

function isBusinessFact(value: unknown): boolean {
  if (!isRecord(value) || typeof value.id !== "string" || !FACT_IDS.test(value.id)) return false;
  if (typeof value.kind === "string" && SCALAR_FACTS.has(value.kind)) {
    const maxLength = value.kind === "description" ? 3000 : value.kind === "value" ? 1000 : 100;
    return hasOnlyKeys(value, ["id", "kind", "value", "evidence"])
      && typeof value.value === "string"
      && value.value.trim().length > 0
      && value.value.length <= maxLength
      && isFactEvidence(value.evidence);
  }
  if (typeof value.kind !== "string" || !STRUCTURED_FACTS.has(value.kind)) return false;
  if (!hasOnlyKeys(value, ["id", "kind", "value"]) || !isRecord(value.value)) return false;
  const fact = value.value;
  return hasOnlyKeys(fact, ["title", "title_evidence", "text", "text_evidence"])
    && typeof fact.title === "string"
    && fact.title.trim().length > 0
    && fact.title.length <= 100
    && isFactEvidence(fact.title_evidence)
    && typeof fact.text === "string"
    && fact.text.trim().length > 0
    && fact.text.length <= 1000
    && isFactEvidence(fact.text_evidence);
}

function isRequestedFeature(value: unknown): boolean {
  return isRecord(value)
    && hasOnlyKeys(value, ["capability_id", "evidence"])
    && typeof value.capability_id === "string"
    && FACT_IDS.test(value.capability_id)
    && isCapabilityEvidence(value.evidence);
}

function isDraft(value: unknown): value is RequestDraft {
  if (!isRecord(value)) return false;
  const allowed = ["contract_version", "prompt", "genre", "style_mode", "business_facts", "requested_features", "asset_ids", "fictitious"];
  if (Object.keys(value).some((key) => !allowed.includes(key))) return false;
  return (value.contract_version === undefined || value.contract_version === null || value.contract_version === "request-draft-source-bound-v1")
    && (value.prompt === undefined || value.prompt === null || (typeof value.prompt === "string" && value.prompt.trim().length > 0 && value.prompt.length <= 1000))
    && (value.genre === undefined || value.genre === null || value.genre === "landing_page" || value.genre === "company_profile")
    && (value.style_mode === undefined || value.style_mode === null || value.style_mode === "plain_css" || value.style_mode === "tailwind")
    && (value.fictitious === undefined || value.fictitious === null || typeof value.fictitious === "boolean")
    && Array.isArray(value.business_facts)
    && value.business_facts.length <= 24
    && value.business_facts.every(isBusinessFact)
    && Array.isArray(value.requested_features)
    && value.requested_features.length <= 32
    && value.requested_features.every(isRequestedFeature)
    && Array.isArray(value.asset_ids)
    && value.asset_ids.length <= 8
    && value.asset_ids.every((id) => typeof id === "string" && ASSET_IDS.test(id));
}

function isGenerationSummary(value: unknown): boolean {
  if (!isRecord(value)) return false;
  return isValidGenerationId(value.generation_id)
    && value.status === "completed"
    && typeof value.message === "string"
    && Array.isArray(value.missing_fields)
    && value.missing_fields.every((field) => typeof field === "string")
    && (value.genre === null || typeof value.genre === "string")
    && (value.style_mode === null || typeof value.style_mode === "string")
    && (value.business_name === null || typeof value.business_name === "string")
    && (value.section_count === null || isIntegerInRange(value.section_count, 0))
    && (value.created_at === null || typeof value.created_at === "string")
    && (value.preview_url === null || typeof value.preview_url === "string")
    && (value.download_url === null || typeof value.download_url === "string")
    && Array.isArray(value.files)
    && value.files.length === SOURCE_FILES.size
    && new Set(value.files).size === SOURCE_FILES.size
    && value.files.every((file) => typeof file === "string" && SOURCE_FILES.has(file));
}

function isChatMessage(value: unknown): value is ChatMessage {
  if (!isRecord(value)
    || typeof value.id !== "string"
    || typeof value.createdAt !== "string"
    || !Number.isFinite(Date.parse(value.createdAt))) return false;
  if (typeof value.content !== "string") return false;
  switch (value.type) {
    case "user":
      return true;
    case "assistant":
      return value.tone === undefined || value.tone === "normal" || value.tone === "error";
    case "clarification":
      return typeof value.prompt === "string"
        && value.prompt.length > 0
        && value.prompt.length <= 1000
        && isDraft(value.draft)
        && value.draft.prompt === value.prompt
        && Array.isArray(value.missingFields)
        && value.missingFields.every((field) => typeof field === "string")
        && typeof value.status === "string"
        && INTAKE_STATUSES.has(value.status)
        && (value.isValidating === undefined || typeof value.isValidating === "boolean")
        && (value.isError === undefined || typeof value.isError === "boolean")
        && (value.templateId === undefined || isWebsiteTemplateId(value.templateId));
    case "request_summary":
      return typeof value.prompt === "string"
        && value.prompt.length > 0
        && value.prompt.length <= 1000
        && isDraft(value.draft)
        && value.draft.prompt === value.prompt
        && isRecord(value.validation)
        && value.validation.status === "ready"
        && typeof value.validation.message === "string"
        && Array.isArray(value.validation.missing_fields)
        && value.validation.missing_fields.length === 0
        && isRecord(value.validation.request)
        && typeof value.state === "string"
        && ["editing", "ready_to_confirm", "confirmed"].includes(value.state);
    case "generation_status":
      return (value.status === "pending" || (typeof value.status === "string" && GENERATION_STATUSES.has(value.status)))
        && (value.requestSummaryId === undefined || typeof value.requestSummaryId === "string")
        && (value.generationId === undefined || isValidGenerationId(value.generationId))
        && (value.summary === undefined || isGenerationSummary(value.summary))
        && (value.status !== "completed" || (isValidGenerationId(value.generationId) && isGenerationSummary(value.summary)));
    default:
      return false;
  }
}

function isChatSession(value: unknown): value is ChatSession {
  return isRecord(value)
    && typeof value.id === "string"
    && value.id.length > 0
    && typeof value.title === "string"
    && typeof value.updatedAt === "string"
    && Number.isFinite(Date.parse(value.updatedAt))
    && Array.isArray(value.messages)
    && value.messages.every(isChatMessage)
    && Array.isArray(value.generationIds)
    && value.generationIds.every(isValidGenerationId);
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

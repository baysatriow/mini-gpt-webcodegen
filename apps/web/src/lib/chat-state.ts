import type {
  CatalogResponse,
  GenerationStatus,
  GenerationSummary,
  IntakeResponse,
  RequestDraft,
} from "@/lib/api-types";

export type MessageBase = { id: string; createdAt: string };

export type UserMessage = MessageBase & {
  type: "user";
  content: string;
};

export type AssistantMessage = MessageBase & {
  type: "assistant";
  content: string;
  tone?: "normal" | "error";
};

export type ClarificationMessage = MessageBase & {
  type: "clarification";
  content: string;
  prompt: string;
  draft: RequestDraft;
  status: IntakeResponse["status"];
  missingFields: string[];
  catalog?: CatalogResponse;
};

export type RequestSummaryMessage = MessageBase & {
  type: "request_summary";
  content: string;
  prompt: string;
  draft: RequestDraft;
  state: "editing" | "ready_to_confirm" | "confirmed";
  validation: IntakeResponse;
};

export type GenerationStatusMessage = MessageBase & {
  type: "generation_status";
  content: string;
  status: "pending" | GenerationStatus;
  generationId?: string;
  summary?: GenerationSummary;
};

export type ChatMessage =
  | UserMessage
  | AssistantMessage
  | ClarificationMessage
  | RequestSummaryMessage
  | GenerationStatusMessage;

export type NewChatMessage =
  | Omit<UserMessage, keyof MessageBase>
  | Omit<AssistantMessage, keyof MessageBase>
  | Omit<ClarificationMessage, keyof MessageBase>
  | Omit<RequestSummaryMessage, keyof MessageBase>
  | Omit<GenerationStatusMessage, keyof MessageBase>;

export type ChatSession = {
  id: string;
  title: string;
  messages: ChatMessage[];
  updatedAt: string;
  generationIds: string[];
};

export type ChatState = {
  sessions: ChatSession[];
  activeSessionId: string | null;
  restored: boolean;
};

export const initialChatState: ChatState = {
  sessions: [],
  activeSessionId: null,
  restored: false,
};

export type ChatAction =
  | { type: "new_session"; session: ChatSession }
  | { type: "set_active_session"; sessionId: string }
  | { type: "append_message"; message: ChatMessage; sessionId?: string }
  | { type: "replace_message"; message: ChatMessage; sessionId?: string }
  | { type: "set_generation"; sessionId: string; generationId: string; updatedAt: string }
  | { type: "restore_session"; sessions: ChatSession[]; activeSessionId: string | null }
  | { type: "delete_session"; sessionId: string };

export function createId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return `local-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

export function createChatSession(title = "Obrolan baru"): ChatSession {
  return {
    id: createId(),
    title,
    messages: [],
    updatedAt: new Date().toISOString(),
    generationIds: [],
  };
}

export function createMessage(message: NewChatMessage): ChatMessage {
  return { ...message, id: createId(), createdAt: new Date().toISOString() } as ChatMessage;
}

function sessionWithUpdatedMessage(session: ChatSession, message: ChatMessage): ChatSession {
  const firstUserMessage = message.type === "user" && session.messages.length === 0;
  const title = firstUserMessage
    ? message.content.replace(/\s+/g, " ").trim().slice(0, 48) || "Obrolan baru"
    : session.title;
  return {
    ...session,
    title,
    messages: [...session.messages, message],
    updatedAt: message.createdAt,
  };
}

export function chatReducer(state: ChatState, action: ChatAction): ChatState {
  switch (action.type) {
    case "restore_session":
      return {
        sessions: action.sessions,
        activeSessionId: action.activeSessionId,
        restored: true,
      };
    case "new_session":
      return {
        ...state,
        sessions: [action.session, ...state.sessions.filter((item) => item.id !== action.session.id)],
        activeSessionId: action.session.id,
      };
    case "set_active_session":
      return state.sessions.some((session) => session.id === action.sessionId)
        ? { ...state, activeSessionId: action.sessionId }
        : state;
    case "append_message": {
      const sessionId = action.sessionId ?? state.activeSessionId;
      if (!sessionId) return state;
      return {
        ...state,
        sessions: state.sessions.map((session) =>
          session.id === sessionId ? sessionWithUpdatedMessage(session, action.message) : session,
        ).sort((left, right) => right.updatedAt.localeCompare(left.updatedAt)),
      };
    }
    case "replace_message": {
      const sessionId = action.sessionId ?? state.activeSessionId;
      if (!sessionId) return state;
      return {
        ...state,
        sessions: state.sessions.map((session) =>
          session.id === sessionId
            ? {
                ...session,
                messages: session.messages.map((message) =>
                  message.id === action.message.id ? action.message : message,
                ),
                updatedAt: action.message.createdAt,
              }
            : session,
        ),
      };
    }
    case "set_generation":
      return {
        ...state,
        sessions: state.sessions.map((session) =>
          session.id === action.sessionId
            ? {
                ...session,
                generationIds: session.generationIds.includes(action.generationId)
                  ? session.generationIds
                  : [...session.generationIds, action.generationId],
                updatedAt: action.updatedAt,
              }
            : session,
        ),
      };
    case "delete_session": {
      const sessions = state.sessions.filter((session) => session.id !== action.sessionId);
      const activeSessionId = state.activeSessionId === action.sessionId
        ? sessions[0]?.id ?? null
        : state.activeSessionId;
      return { ...state, sessions, activeSessionId };
    }
  }
  return state;
}

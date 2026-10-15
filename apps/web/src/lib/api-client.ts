import type {
  ApiErrorResponse,
  CatalogResponse,
  GenerationResponse,
  GenerationSummary,
  HealthResponse,
  IntakeResponse,
  RequestDraft,
  SourceFilename,
  SourceResponse,
} from "@/lib/api-types";

export const API_BASE_URL = (
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000"
).replace(/\/+$/, "");

export class ApiClientError extends Error {
  readonly status: number | null;
  readonly code: string;
  readonly missingFields: string[];

  constructor(message: string, options?: { status?: number | null; code?: string; missingFields?: string[] }) {
    super(message);
    this.name = "ApiClientError";
    this.status = options?.status ?? null;
    this.code = options?.code ?? "api_error";
    this.missingFields = options?.missingFields ?? [];
  }
}

function safeError(payload: unknown, status: number): ApiClientError {
  const outer = typeof payload === "object" && payload !== null ? (payload as Record<string, unknown>) : {};
  const detail = typeof outer.detail === "object" && outer.detail !== null
    ? (outer.detail as Record<string, unknown>)
    : outer;
  const code = typeof detail.code === "string" ? detail.code : `http_${status}`;
  const message = typeof detail.message === "string" ? detail.message : undefined;
  const missingFields = Array.isArray(detail.missing_fields)
    ? detail.missing_fields.filter((field): field is string => typeof field === "string")
    : [];

  const fallback: Record<number, string> = {
    404: "Hasil halaman tidak ditemukan di penyimpanan lokal.",
    409: "Permintaan belum siap atau proses lain sedang berjalan.",
    413: "Prompt melewati batas panjang yang didukung.",
    422: "Isian belum sesuai format. Periksa kembali informasi yang dimasukkan.",
    503: "Model lokal belum tersedia. Periksa paket runtime aplikasi.",
  };

  return new ApiClientError(message || fallback[status] || "Layanan lokal mengalami kendala. Coba lagi nanti.", {
    status,
    code,
    missingFields,
  });
}

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    const headers = new Headers(init?.headers);
    if (init?.body && !headers.has("Content-Type")) {
      headers.set("Content-Type", "application/json");
    }
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      cache: "no-store",
      headers,
    });
  } catch {
    throw new ApiClientError("API lokal tidak dapat dijangkau. Pastikan FastAPI sedang berjalan.", {
      code: "api_unreachable",
    });
  }

  const payload: unknown = await response.json().catch(() => null);
  if (!response.ok) throw safeError(payload, response.status);
  return payload as T;
}

async function requestBlob(path: string): Promise<Blob> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, { cache: "no-store" });
  } catch {
    throw new ApiClientError("API lokal tidak dapat dijangkau. Pastikan FastAPI sedang berjalan.", {
      code: "api_unreachable",
    });
  }

  if (!response.ok) {
    const payload: unknown = await response.json().catch(() => null);
    throw safeError(payload, response.status);
  }
  return response.blob();
}

function generationPath(generationId: string): string {
  return `/api/v1/generations/${encodeURIComponent(generationId)}`;
}

export function getHealth(): Promise<HealthResponse> {
  return requestJson("/api/v1/health");
}

export function getCatalog(): Promise<CatalogResponse> {
  return requestJson("/api/v1/catalog");
}

export function validateIntake(prompt: string, draft: RequestDraft): Promise<IntakeResponse> {
  return requestJson("/api/v1/intake/validate", {
    method: "POST",
    body: JSON.stringify({ prompt, draft }),
  });
}

export function generate(prompt: string, draft: RequestDraft): Promise<GenerationResponse> {
  return requestJson("/api/v1/generations", {
    method: "POST",
    body: JSON.stringify({ prompt, draft }),
  });
}

export function getGeneration(generationId: string): Promise<GenerationSummary> {
  return requestJson(generationPath(generationId));
}

export function getSource(generationId: string): Promise<SourceResponse> {
  return requestJson(`${generationPath(generationId)}/source`);
}

export function getPreviewFileUrl(generationId: string, filename: SourceFilename): string {
  return `${API_BASE_URL}${generationPath(generationId)}/preview/${encodeURIComponent(filename)}`;
}

export async function checkPreviewAvailability(generationId: string, signal: AbortSignal): Promise<void> {
  let response: Response;
  try {
    response = await fetch(getPreviewFileUrl(generationId, "index.html"), {
      cache: "no-store",
      signal,
    });
  } catch (error) {
    if (signal.aborted) throw error;
    throw new ApiClientError("Pratinjau tidak dapat dijangkau dari API lokal.", {
      code: "preview_unreachable",
    });
  }

  if (!response.ok) {
    const payload: unknown = await response.json().catch(() => null);
    throw safeError(payload, response.status);
  }
  if (response.body) await response.body.cancel().catch(() => undefined);
}

export function getDownloadZipUrl(generationId: string): string {
  return `${API_BASE_URL}${generationPath(generationId)}/download.zip`;
}

export function downloadZip(generationId: string): Promise<Blob> {
  return requestBlob(`${generationPath(generationId)}/download.zip`);
}

export function downloadSourceFile(generationId: string, filename: SourceFilename): Promise<Blob> {
  return requestBlob(`${generationPath(generationId)}/preview/${encodeURIComponent(filename)}`);
}

export function isApiErrorResponse(value: unknown): value is ApiErrorResponse {
  if (typeof value !== "object" || value === null) return false;
  const candidate = value as Record<string, unknown>;
  return typeof candidate.code === "string" && typeof candidate.message === "string";
}

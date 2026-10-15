import { getDownloadZipUrl, getPreviewFileUrl } from "@/lib/api-client";
import type { GenerationSummary } from "@/lib/api-types";

const GENERATION_ID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export function isValidGenerationId(value: unknown): value is string {
  return typeof value === "string" && GENERATION_ID_PATTERN.test(value);
}

export function getAcceptedPreviewUrl(summary: GenerationSummary | null): string | null {
  if (!summary || summary.status !== "completed" || !isValidGenerationId(summary.generation_id)) {
    return null;
  }
  return getPreviewFileUrl(summary.generation_id, "index.html");
}

export function getAcceptedDownloadUrl(summary: GenerationSummary | null): string | null {
  if (!summary || summary.status !== "completed" || !isValidGenerationId(summary.generation_id)) {
    return null;
  }
  return getDownloadZipUrl(summary.generation_id);
}

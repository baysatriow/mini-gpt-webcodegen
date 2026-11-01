export type UsageWindow = "24h" | "7d" | "30d";
export type UsageOutcome = "running" | "completed" | "rejected" | "failed" | "interrupted";
export type UsageStage =
  | "request_received"
  | "request_validation"
  | "intake_validation"
  | "model_load"
  | "inference"
  | "output_validation"
  | "render_export"
  | "persist_result"
  | "completed"
  | "server_restart";
export type UsageFailureCode =
  | "input_rejected"
  | "input_too_long"
  | "unsupported_request"
  | "generation_busy"
  | "model_unavailable"
  | "inference_failed"
  | "cuda_out_of_memory"
  | "output_invalid"
  | "render_failed"
  | "storage_failed"
  | "invalid_request"
  | "internal_error"
  | "server_interrupted"
  | "gpu_telemetry_unavailable";

export type UsageSummary = {
  window: UsageWindow;
  total_requests: number;
  inference_started: number;
  completed: number;
  rejected: number;
  failed: number;
  interrupted: number;
  success_rate_all: number | null;
  success_rate_inference: number | null;
  mean_duration_ms: number | null;
  gpu_run_count: number;
  gpu_sample_count: number;
  gpu_coverage_ratio: number | null;
  gpu_utilization_mean_pct: number | null;
  gpu_utilization_max_pct: number | null;
  gpu_memory_mean_mib: number | null;
  gpu_memory_max_mib: number | null;
  gpu_memory_total_mib: number | null;
  gpu_power_mean_w: number | null;
  gpu_temperature_max_c: number | null;
  gpu_sm_clock_mean_mhz: number | null;
  gpu_scope: string;
};

export type UsageRecord = {
  usage_id: string;
  generation_id: string | null;
  title_preview: string | null;
  started_at: string;
  finished_at: string | null;
  duration_ms: number | null;
  http_status: number | null;
  outcome: UsageOutcome;
  stage: UsageStage;
  failure_code: UsageFailureCode | null;
  inference_started: boolean;
  input_tokens: number | null;
  output_tokens: number | null;
  attempt_count: number | null;
  retry_count: number | null;
  section_count: number | null;
  renderer_status: string | null;
  model_id: string | null;
  gpu_sample_count: number;
  gpu_device_name: string | null;
  gpu_utilization_mean_pct: number | null;
  gpu_utilization_max_pct: number | null;
  gpu_memory_mean_mib: number | null;
  gpu_memory_max_mib: number | null;
  gpu_memory_total_mib: number | null;
  gpu_power_mean_w: number | null;
  gpu_temperature_max_c: number | null;
  gpu_sm_clock_mean_mhz: number | null;
  torch_allocated_baseline_bytes: number | null;
  torch_reserved_baseline_bytes: number | null;
  torch_allocated_peak_bytes: number | null;
  torch_reserved_peak_bytes: number | null;
  torch_allocated_delta_bytes: number | null;
  torch_reserved_delta_bytes: number | null;
};

export type UsageEvent = {
  stage: UsageStage;
  event_type: "started" | "completed" | "rejected" | "failed" | "interrupted" | "stage";
  failure_code: UsageFailureCode | null;
  occurred_at: string;
  elapsed_ms: number;
};

export type UsageGpuSample = {
  sampled_at: string;
  device_name: string | null;
  utilization_pct: number | null;
  memory_used_mib: number | null;
  memory_total_mib: number | null;
  power_w: number | null;
  temperature_c: number | null;
  sm_clock_mhz: number | null;
};

export type UsageConfirmedFact = {
  id: string;
  kind: "name" | "description" | "value" | "service" | "project" | "process" | "faq";
  label: string;
  title: string | null;
  value: string;
};

export type UsageDetail = UsageRecord & {
  prompt: string | null;
  confirmed_facts: UsageConfirmedFact[];
  events: UsageEvent[];
  samples: UsageGpuSample[];
};
export type UsagePage = { items: UsageRecord[]; next_cursor: string | null; limit: number };
export type CurrentGpu = {
  available: boolean;
  availability_code: UsageFailureCode | null;
  sampled_at: string;
  device_name: string | null;
  utilization_pct: number | null;
  memory_used_mib: number | null;
  memory_total_mib: number | null;
  power_w: number | null;
  temperature_c: number | null;
  sm_clock_mhz: number | null;
};

async function requestJson<T>(path: string): Promise<T> {
  const response = await fetch(path, { cache: "no-store" });
  if (!response.ok) {
    let message = `Permintaan Usage gagal (${response.status}).`;
    try {
      const body = await response.json() as { detail?: { message?: string }; error?: string };
      message = body.detail?.message ?? body.error ?? message;
    } catch {
      // Keep the safe status-only message when the API returns a non-JSON error.
    }
    throw new Error(message);
  }
  return response.json() as Promise<T>;
}

export function getUsageSummary(window: UsageWindow) {
  return requestJson<UsageSummary>(`/api/v1/usages/summary?window=${encodeURIComponent(window)}`);
}

export function getCurrentGpu() {
  return requestJson<CurrentGpu>("/api/v1/usages/gpu/current");
}

export function getUsagePage(filters: {
  cursor?: string | null;
  limit?: number;
  window?: UsageWindow;
  status?: UsageOutcome | "";
  stage?: UsageStage | "";
  q?: string;
} = {}) {
  const query = new URLSearchParams({ limit: String(filters.limit ?? 25) });
  if (filters.cursor) query.set("cursor", filters.cursor);
  if (filters.window) query.set("window", filters.window);
  if (filters.status) query.set("status", filters.status);
  if (filters.stage) query.set("stage", filters.stage);
  if (filters.q?.trim()) query.set("q", filters.q.trim().slice(0, 200));
  return requestJson<UsagePage>(`/api/v1/usages/?${query.toString()}`);
}

export function getUsageDetail(usageId: string) {
  return requestJson<UsageDetail>(`/api/v1/usages/${encodeURIComponent(usageId)}`);
}

"""Typed JSON contract for the local generator API."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, StrictStr, field_validator, model_validator


MAX_PROMPT_CHARS = 4000
MAX_BRIEF_CHARS = 4000
MAX_PROMPT_MESSAGES = 16
SOURCE_DRAFT_CONTRACT = "request-draft-source-bound-v1"
PROMPT_MESSAGES_CONTRACT = "prompt-messages-v1"
CAPABILITY_CATALOG_CONTRACT = "capability-catalog-v1"
SOURCE_FILES = Literal["index.html", "styles.css", "app.js"]

IntakeStatus = Literal["needs_clarification", "unsupported_request", "input_too_long", "ready"]
GenerationStatus = Literal["completed", "generation_failed", "input_too_long"]

class APIModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=False)


class RequestDraft(APIModel):
    """Partial user draft; the source-bound pipeline owns semantic validation."""

    contract_version: StrictStr | None = None
    prompt: StrictStr | None = Field(
        default=None,
        description="Must match the envelope prompt. Intake returns a workflow status for missing or oversized text.",
    )
    genre: StrictStr | None = None
    style_mode: StrictStr | None = None
    business_facts: list[dict[str, Any]] = Field(default_factory=list, max_length=24)
    requested_features: list[dict[str, Any]] = Field(default_factory=list, max_length=32)
    asset_ids: list[StrictStr] = Field(default_factory=list, max_length=8)
    fictitious: StrictBool | None = None


class IntakeEnvelope(APIModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "prompt": "Buat landing page untuk studio keramik bernama Ruang Tanah.",
                    "draft": {
                        "contract_version": SOURCE_DRAFT_CONTRACT,
                        "prompt": "Buat landing page untuk studio keramik bernama Ruang Tanah.",
                        "genre": "landing_page",
                        "style_mode": "tailwind",
                        "business_facts": [
                            {
                                "id": "nama-usaha",
                                "kind": "name",
                                "value": "Ruang Tanah",
                                "evidence": {"user_confirmed": True},
                            },
                            {
                                "id": "deskripsi",
                                "kind": "description",
                                "value": "Studio keramik untuk kelas dan karya pesanan.",
                                "evidence": {"user_confirmed": True},
                            },
                            {
                                "id": "layanan-kelas",
                                "kind": "service",
                                "value": {
                                    "title": "Kelas keramik",
                                    "title_evidence": {"user_confirmed": True},
                                    "text": "Kelas untuk pemula.",
                                    "text_evidence": {"user_confirmed": True},
                                },
                            },
                        ],
                        "requested_features": [],
                        "asset_ids": [],
                        "fictitious": True,
                    },
                }
            ]
        }
    )

    prompt: StrictStr
    draft: RequestDraft
    extraction_token: StrictStr | None = Field(default=None, max_length=24000)


class PromptMessage(APIModel):
    id: Annotated[StrictStr, Field(min_length=1, max_length=100)]
    text: Annotated[StrictStr, Field(min_length=1, max_length=MAX_BRIEF_CHARS * MAX_PROMPT_MESSAGES)]

    @field_validator("id", "text")
    @classmethod
    def require_non_whitespace(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Message ID and text must not be blank")
        return value


class IntakeExtractRequest(APIModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "canonical_format": "prompt-messages-v1",
                    "messages": [
                        {
                            "id": "brief-1",
                            "text": "Buat landing page untuk studio keramik Ruang Tanah. Gunakan Tailwind CSS."
                        }
                    ],
                }
            ]
        }
    )

    canonical_format: Literal[PROMPT_MESSAGES_CONTRACT]
    messages: list[PromptMessage] = Field(min_length=1, max_length=MAX_PROMPT_MESSAGES)

    @model_validator(mode="after")
    def require_unique_message_ids(self) -> "IntakeExtractRequest":
        identifiers = [message.id for message in self.messages]
        if len(set(identifiers)) != len(identifiers):
            raise ValueError("Message IDs must be unique")
        return self


class GenerationRequest(IntakeEnvelope):
    """Request body used for explicit, user-confirmed generation."""


class IntakeResponse(APIModel):
    status: IntakeStatus
    message: StrictStr
    missing_fields: list[StrictStr] = Field(default_factory=list)
    request: dict[str, Any] | None = None


class SourceEvidence(APIModel):
    field: StrictStr
    source_message_id: StrictStr
    quote: StrictStr
    start: Annotated[StrictInt, Field(ge=0)]
    end: Annotated[StrictInt, Field(gt=0)]
    utf16_start: Annotated[StrictInt, Field(ge=0)]
    utf16_end: Annotated[StrictInt, Field(gt=0)]
    prompt_start: Annotated[StrictInt, Field(ge=0)]
    prompt_end: Annotated[StrictInt, Field(gt=0)]


class IntakeConflict(APIModel):
    field: StrictStr
    message: StrictStr
    candidates: list[dict[str, Any]] = Field(default_factory=list)


class UnsupportedRequest(APIModel):
    kind: Literal["known_capability", "out_of_catalog"]
    id: StrictStr | None = None
    label: StrictStr
    phrase: StrictStr
    context: StrictStr
    intent: Literal["requested", "retracted", "negated", "future", "reference", "unclear"]
    evidence: SourceEvidence


class IntakeExtractResponse(APIModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "status": "needs_clarification",
                    "message": "Lengkapi fakta yang ditandai dalam satu balasan.",
                    "missing_fields": ["business_facts.description", "business_facts.service"],
                    "draft": {
                        "contract_version": SOURCE_DRAFT_CONTRACT,
                        "prompt": "Buat landing page untuk studio keramik Ruang Tanah. Gunakan Tailwind CSS.",
                        "genre": "landing_page",
                        "style_mode": "tailwind",
                        "business_facts": [],
                        "requested_features": [],
                        "asset_ids": ["studio-shapes"],
                        "fictitious": True,
                    },
                    "evidence": [],
                    "conflicts": [],
                    "unsupported_requests": [],
                    "resolution_token": None,
                }
            ]
        }
    )

    status: Literal["ready", "needs_clarification", "unsupported"]
    message: StrictStr
    missing_fields: list[StrictStr] = Field(default_factory=list)
    draft: RequestDraft | None = None
    evidence: list[SourceEvidence] = Field(default_factory=list)
    conflicts: list[IntakeConflict] = Field(default_factory=list)
    unsupported_requests: list[UnsupportedRequest] = Field(default_factory=list)
    resolution_token: StrictStr | None = None


class ErrorResponse(APIModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "code": "generation_in_progress",
                    "message": "Generation lain sedang berjalan.",
                    "missing_fields": [],
                }
            ]
        }
    )

    code: StrictStr
    message: StrictStr
    missing_fields: list[StrictStr] = Field(default_factory=list)


UsageWindow = Literal["24h", "7d", "30d"]
UsageOutcome = Literal["running", "completed", "rejected", "failed", "interrupted"]
UsageStage = Literal[
    "request_received",
    "request_validation",
    "intake_validation",
    "model_load",
    "inference",
    "output_validation",
    "render_export",
    "persist_result",
    "completed",
    "server_restart",
]
UsageFailureCode = Literal[
    "input_rejected",
    "input_too_long",
    "unsupported_request",
    "generation_busy",
    "model_unavailable",
    "inference_failed",
    "cuda_out_of_memory",
    "output_invalid",
    "render_failed",
    "storage_failed",
    "invalid_request",
    "internal_error",
    "server_interrupted",
    "gpu_telemetry_unavailable",
]


class UsageSummaryResponse(APIModel):
    window: UsageWindow
    total_requests: StrictInt
    inference_started: StrictInt
    completed: StrictInt
    rejected: StrictInt
    failed: StrictInt
    interrupted: StrictInt
    success_rate_all: float | None
    success_rate_inference: float | None
    mean_duration_ms: float | None
    gpu_run_count: StrictInt
    gpu_sample_count: StrictInt
    gpu_coverage_ratio: float | None
    gpu_utilization_mean_pct: float | None
    gpu_utilization_max_pct: float | None
    gpu_memory_mean_mib: float | None
    gpu_memory_max_mib: float | None
    gpu_memory_total_mib: float | None
    gpu_power_mean_w: float | None
    gpu_temperature_max_c: float | None
    gpu_sm_clock_mean_mhz: float | None
    gpu_scope: StrictStr


class UsageRecordResponse(APIModel):
    usage_id: UUID
    generation_id: UUID | None = None
    started_at: datetime
    finished_at: datetime | None = None
    duration_ms: StrictInt | None = None
    http_status: StrictInt | None = None
    outcome: UsageOutcome
    stage: UsageStage
    failure_code: UsageFailureCode | None = None
    inference_started: StrictBool
    input_tokens: StrictInt | None = None
    output_tokens: StrictInt | None = None
    attempt_count: StrictInt | None = None
    retry_count: StrictInt | None = None
    section_count: StrictInt | None = None
    renderer_status: StrictStr | None = None
    model_id: StrictStr | None = None
    gpu_sample_count: StrictInt
    gpu_device_name: StrictStr | None = None
    gpu_utilization_mean_pct: float | None = None
    gpu_utilization_max_pct: float | None = None
    gpu_memory_mean_mib: float | None = None
    gpu_memory_max_mib: float | None = None
    gpu_memory_total_mib: float | None = None
    gpu_power_mean_w: float | None = None
    gpu_temperature_max_c: float | None = None
    gpu_sm_clock_mean_mhz: float | None = None
    torch_allocated_baseline_bytes: StrictInt | None = None
    torch_reserved_baseline_bytes: StrictInt | None = None
    torch_allocated_peak_bytes: StrictInt | None = None
    torch_reserved_peak_bytes: StrictInt | None = None
    torch_allocated_delta_bytes: StrictInt | None = None
    torch_reserved_delta_bytes: StrictInt | None = None


class UsageEventResponse(APIModel):
    stage: UsageStage
    event_type: Literal["started", "completed", "rejected", "failed", "interrupted", "stage"]
    failure_code: UsageFailureCode | None = None
    occurred_at: datetime
    elapsed_ms: StrictInt


class UsageGpuSampleResponse(APIModel):
    sampled_at: datetime
    device_name: StrictStr | None = None
    utilization_pct: float | None = None
    memory_used_mib: float | None = None
    memory_total_mib: float | None = None
    power_w: float | None = None
    temperature_c: float | None = None
    sm_clock_mhz: float | None = None


class UsageDetailResponse(UsageRecordResponse):
    events: list[UsageEventResponse] = Field(default_factory=list)
    samples: list[UsageGpuSampleResponse] = Field(default_factory=list)


class UsageListResponse(APIModel):
    items: list[UsageRecordResponse]
    next_cursor: StrictStr | None = None
    limit: Annotated[StrictInt, Field(ge=1, le=100)]


class UsageGpuCurrentResponse(APIModel):
    available: StrictBool
    availability_code: UsageFailureCode | None = None
    sampled_at: datetime
    device_name: StrictStr | None = None
    utilization_pct: float | None = None
    memory_used_mib: float | None = None
    memory_total_mib: float | None = None
    power_w: float | None = None
    temperature_c: float | None = None
    sm_clock_mhz: float | None = None


class SourceResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    index_html: StrictStr = Field(alias="index.html")
    styles_css: StrictStr = Field(alias="styles.css")
    app_js: StrictStr = Field(alias="app.js")


class CatalogOption(APIModel):
    id: StrictStr
    label: StrictStr


class CapabilityLabel(APIModel):
    id: StrictStr
    label: StrictStr


class AssetMetadata(APIModel):
    id: StrictStr
    width: Annotated[StrictInt, Field(gt=0)]
    height: Annotated[StrictInt, Field(gt=0)]
    origin: StrictStr
    license: StrictStr


class CatalogResponse(APIModel):
    contract_version: Literal[CAPABILITY_CATALOG_CONTRACT]
    supported_genres: list[CatalogOption]
    supported_style_modes: list[CatalogOption]
    scope_message: StrictStr
    unsupported_capabilities: list[CapabilityLabel]
    assets: list[AssetMetadata]


class HealthResponse(APIModel):
    status: Literal["ok"]
    contract_version: StrictStr
    model_loaded: StrictBool
    extractor_available: StrictBool = False
    extractor_loaded: StrictBool = False
    generator_loaded: StrictBool = False


class GenerationResponse(APIModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "status": "completed",
                    "generation_id": "123e4567-e89b-42d3-a456-426614174000",
                    "message": "Halaman berhasil dibuat dan siap ditinjau.",
                    "missing_fields": [],
                    "section_count": 7,
                    "preview_url": "http://127.0.0.1:8000/api/v1/generations/123e4567-e89b-42d3-a456-426614174000/preview/index.html",
                    "download_url": "http://127.0.0.1:8000/api/v1/generations/123e4567-e89b-42d3-a456-426614174000/download.zip",
                    "files": ["index.html", "styles.css", "app.js"],
                }
            ]
        }
    )

    status: GenerationStatus
    generation_id: UUID | None = None
    message: StrictStr
    missing_fields: list[StrictStr] = Field(default_factory=list)
    section_count: Annotated[StrictInt, Field(ge=0)] | None = None
    preview_url: StrictStr | None = None
    download_url: StrictStr | None = None
    files: list[SOURCE_FILES] = Field(default_factory=list)


class GenerationSummary(APIModel):
    generation_id: UUID
    status: GenerationStatus
    message: StrictStr
    genre: StrictStr | None = None
    style_mode: StrictStr | None = None
    business_name: StrictStr | None = None
    section_count: Annotated[StrictInt, Field(ge=0)] | None = None
    created_at: datetime | None = None
    preview_url: StrictStr | None = None
    download_url: StrictStr | None = None
    files: list[SOURCE_FILES] = Field(default_factory=list)

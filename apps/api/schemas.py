"""Typed JSON contract for the local generator API."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, StrictStr


MAX_PROMPT_CHARS = 1000
SOURCE_DRAFT_CONTRACT = "request-draft-source-bound-v1"
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


class GenerationRequest(IntakeEnvelope):
    """Request body used for explicit, user-confirmed generation."""


class IntakeResponse(APIModel):
    status: IntakeStatus
    message: StrictStr
    missing_fields: list[StrictStr] = Field(default_factory=list)
    request: dict[str, Any] | None = None


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

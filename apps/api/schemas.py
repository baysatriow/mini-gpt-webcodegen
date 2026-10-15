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
    prompt: StrictStr
    draft: RequestDraft


class GenerationRequest(IntakeEnvelope):
    """Request body used for explicit, user-confirmed generation."""


class IntakeResponse(APIModel):
    status: IntakeStatus
    message: StrictStr
    missing_fields: list[StrictStr] = Field(default_factory=list)
    request: dict[str, Any] | None = None


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


class GenerationResponse(APIModel):
    status: GenerationStatus
    generation_id: UUID | None = None
    message: StrictStr
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

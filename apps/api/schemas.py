"""Typed JSON contract for the local generator API."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Literal, Union
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, StrictStr, StringConstraints, model_validator


MAX_PROMPT_CHARS = 1000
SOURCE_DRAFT_CONTRACT = "request-draft-source-bound-v1"
CAPABILITY_CATALOG_CONTRACT = "capability-catalog-v1"
SOURCE_FILES = Literal["index.html", "styles.css", "app.js"]

IntakeStatus = Literal["needs_clarification", "unsupported_request", "input_too_long", "ready"]
GenerationStatus = Literal["completed", "generation_failed", "input_too_long"]

FactId = Annotated[StrictStr, StringConstraints(pattern=r"^[a-z][a-z0-9_-]{0,63}$")]
CapabilityId = Annotated[StrictStr, StringConstraints(pattern=r"^[a-z][a-z0-9_-]{0,63}$")]
NonEmptyText = Annotated[StrictStr, Field(min_length=1)]


class APIModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=False)


class SourceSpan(APIModel):
    start: Annotated[StrictInt, Field(ge=0)]
    end: Annotated[StrictInt, Field(ge=1)]


class CapabilitySourceSpan(SourceSpan):
    quote: Annotated[StrictStr, Field(min_length=1, max_length=100)]


class FactEvidence(APIModel):
    source_span: SourceSpan | None = None
    user_confirmed: Literal[True] | None = None

    @model_validator(mode="after")
    def require_one_evidence_source(self) -> FactEvidence:
        if (self.source_span is None) == (self.user_confirmed is None):
            raise ValueError("Provide exactly one source span or user confirmation")
        return self


class CapabilityEvidence(APIModel):
    source_span: CapabilitySourceSpan | None = None
    user_confirmed: Literal[True] | None = None

    @model_validator(mode="after")
    def require_one_evidence_source(self) -> CapabilityEvidence:
        if (self.source_span is None) == (self.user_confirmed is None):
            raise ValueError("Provide exactly one source span or user confirmation")
        return self


class TitledFact(APIModel):
    title: Annotated[StrictStr, Field(min_length=1, max_length=100)]
    title_evidence: FactEvidence
    text: Annotated[StrictStr, Field(min_length=1, max_length=1000)]
    text_evidence: FactEvidence


class NameFact(APIModel):
    id: FactId
    kind: Literal["name"]
    value: Annotated[StrictStr, Field(min_length=1, max_length=100)]
    evidence: FactEvidence


class DescriptionFact(APIModel):
    id: FactId
    kind: Literal["description"]
    value: Annotated[StrictStr, Field(min_length=1, max_length=3000)]
    evidence: FactEvidence


class ValueFact(APIModel):
    id: FactId
    kind: Literal["value"]
    value: Annotated[StrictStr, Field(min_length=1, max_length=1000)]
    evidence: FactEvidence


class StructuredFact(APIModel):
    id: FactId
    kind: Literal["service", "project", "process", "faq"]
    value: TitledFact


BusinessFact = Annotated[
    Union[NameFact, DescriptionFact, ValueFact, StructuredFact],
    Field(discriminator="kind"),
]


class RequestedFeature(APIModel):
    capability_id: CapabilityId
    evidence: CapabilityEvidence


class RequestDraft(APIModel):
    contract_version: Literal[SOURCE_DRAFT_CONTRACT]
    prompt: Annotated[NonEmptyText, Field(max_length=MAX_PROMPT_CHARS)]
    genre: Annotated[StrictStr, Field(min_length=1, max_length=100)]
    style_mode: Annotated[StrictStr, Field(min_length=1, max_length=100)]
    business_facts: Annotated[list[BusinessFact], Field(min_length=3, max_length=24)]
    requested_features: Annotated[list[RequestedFeature], Field(max_length=32)]
    asset_ids: Annotated[list[CapabilityId], Field(max_length=8)]
    fictitious: StrictBool


class IntakeEnvelope(APIModel):
    prompt: NonEmptyText
    draft: RequestDraft

    @model_validator(mode="after")
    def prompt_matches_draft(self) -> IntakeEnvelope:
        if self.prompt != self.draft.prompt:
            raise ValueError("prompt must match draft.prompt exactly")
        return self


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
    id: CapabilityId
    label: StrictStr


class AssetMetadata(APIModel):
    id: CapabilityId
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

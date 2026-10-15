"""Catalog and non-inference request intake endpoints."""

from fastapi import APIRouter

from apps.api.schemas import (
    CatalogResponse,
    ErrorResponse,
    IntakeEnvelope,
    IntakeResponse,
)
from apps.api.services.catalog import get_public_catalog
from apps.api.services.intake import validate_intake


router = APIRouter(prefix="/api/v1", tags=["intake"])


@router.get(
    "/catalog",
    response_model=CatalogResponse,
    summary="List supported page types, styles, capabilities, and assets",
    responses={500: {"model": ErrorResponse, "description": "Local catalog is unavailable"}},
)
def catalog() -> CatalogResponse:
    return get_public_catalog()


@router.post(
    "/intake/validate",
    response_model=IntakeResponse,
    summary="Validate a prompt and partial source-bound request draft",
    description=(
        "Returns clarification, unsupported-scope, input-length, or ready status. "
        "This endpoint does not create output or load the model."
    ),
    responses={
        422: {"model": ErrorResponse, "description": "Request does not match the API JSON schema"},
        500: {"model": ErrorResponse, "description": "Local intake resources are unavailable"},
    },
)
def intake_validate(body: IntakeEnvelope) -> IntakeResponse:
    return validate_intake(
        body.prompt,
        body.draft.model_dump(exclude_none=True),
    )

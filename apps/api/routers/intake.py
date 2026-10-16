"""Catalog and non-inference request intake endpoints."""

import logging

from fastapi import APIRouter, HTTPException

from apps.api.schemas import (
    CatalogResponse,
    ErrorResponse,
    IntakeEnvelope,
    IntakeExtractRequest,
    IntakeExtractResponse,
    IntakeResponse,
    MAX_BRIEF_CHARS,
)
from apps.api.services.extraction import (
    PromptExtractionBudgetError,
    PromptExtractionFailure,
    extract_prompt_messages,
)
from apps.api.services.catalog import get_public_catalog
from apps.api.services.intake import validate_intake
from apps.api.services.runtime import get_runtime


router = APIRouter(prefix="/api/v1", tags=["intake"])
logger = logging.getLogger(__name__)


def _http_error(status_code: int, code: str, message: str) -> HTTPException:
    payload = ErrorResponse(code=code, message=message)
    return HTTPException(status_code=status_code, detail=payload.model_dump())


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
        extraction_token=body.extraction_token,
    )


@router.post(
    "/intake/extract",
    response_model=IntakeExtractResponse,
    summary="Extract one source-grounded draft from ordered user messages",
    description=(
        "Runs the selected prompt extractor over the complete message history. "
        "It returns a grouped clarification or an evidence-backed draft and never generates website files."
    ),
    responses={
        409: {"model": ErrorResponse, "description": "Another model operation currently owns inference memory"},
        413: {"model": ErrorResponse, "description": "Brief or a frozen extractor scope exceeds its context budget"},
        422: {"model": ErrorResponse, "description": "Request does not match the prompt-messages JSON contract"},
        503: {"model": ErrorResponse, "description": "A passing selected extractor is not available"},
    },
)
def intake_extract(body: IntakeExtractRequest) -> IntakeExtractResponse:
    runtime = get_runtime()
    messages = [message.model_dump() for message in body.messages]
    canonical_length = sum(len(message["text"]) for message in messages) + max(0, len(messages) - 1)
    if canonical_length > MAX_BRIEF_CHARS:
        raise _http_error(413, "input_too_long", f"Brief melebihi batas {MAX_BRIEF_CHARS} karakter. Ringkas tanpa menghapus fakta penting.")
    if not runtime.inference_lock.acquire(blocking=False):
        raise _http_error(409, "model_busy", "Model sedang digunakan untuk proses lain. Coba lagi setelah proses selesai.")
    try:
        return extract_prompt_messages(messages, runtime)
    except PromptExtractionBudgetError as error:
        logger.info("Prompt extraction rejected by a frozen input budget: %s", error)
        raise _http_error(413, "input_too_long", "Brief tidak muat pada budget model yang dibekukan. Ringkas tanpa menghapus fakta penting.") from error
    except PromptExtractionFailure as error:
        logger.exception("Prompt extractor failed closed")
        raise _http_error(503, "extractor_unavailable", "Ekstraksi belum dapat dipercaya. Gunakan editor detail manual sementara.") from error
    except Exception as error:
        logger.exception("Unexpected prompt extraction service failure")
        raise _http_error(503, "extractor_unavailable", "Ekstraksi lokal belum siap. Gunakan editor detail manual sementara.") from error
    finally:
        runtime.inference_lock.release()

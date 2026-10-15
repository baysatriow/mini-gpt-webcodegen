"""Non-inference health endpoint."""

from fastapi import APIRouter

from apps.api.schemas import HealthResponse, SOURCE_DRAFT_CONTRACT
from apps.api.services.runtime import get_runtime


router = APIRouter(prefix="/api/v1", tags=["health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Check API availability without loading the model",
    responses={200: {"description": "API is available; model state is reported without loading weights"}},
)
def health() -> HealthResponse:
    runtime = get_runtime()
    return HealthResponse(
        status="ok",
        contract_version=SOURCE_DRAFT_CONTRACT,
        model_loaded=runtime.model_loaded,
    )

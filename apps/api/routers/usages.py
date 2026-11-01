"""Read-only Usage summaries and generation audit records."""

from __future__ import annotations

import json
import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request, Response

from apps.api.schemas import (
    ErrorResponse,
    UsageDetailResponse,
    UsageGpuCurrentResponse,
    UsageListResponse,
    UsageOutcome,
    UsageRecordResponse,
    UsageStage,
    UsageSummaryResponse,
    UsageWindow,
)
from apps.api.services.usage_store import UsageStore
from apps.api.services.usage_telemetry import current_gpu_snapshot


router = APIRouter(prefix="/api/v1/usages", tags=["usage"])
logger = logging.getLogger(__name__)


def _store(request: Request) -> UsageStore:
    store = getattr(request.app.state, "usage_store", None)
    if store is None:
        raise HTTPException(
            status_code=503,
            detail=ErrorResponse(code="usage_unavailable", message="Usage lokal belum siap.").model_dump(),
        )
    return store


def _prune_if_due(store: UsageStore) -> None:
    try:
        store.prune_if_due()
    except Exception:
        logger.exception("Usage retention check failed")


def _record_view(record: dict) -> dict:
    count = record.get("gpu_sample_count") or 0
    prompt_preview = record.get("prompt") or record.get("prompt_preview")
    title_preview = " ".join(prompt_preview.split())[:80] if isinstance(prompt_preview, str) else None
    return {
        "usage_id": record["usage_id"],
        "generation_id": record.get("generation_id"),
        "title_preview": title_preview or None,
        "started_at": record["started_at"],
        "finished_at": record.get("finished_at"),
        "duration_ms": record.get("duration_ms"),
        "http_status": record.get("http_status"),
        "outcome": record["outcome"],
        "stage": record["stage"],
        "failure_code": record.get("failure_code"),
        "inference_started": record["inference_started"],
        "input_tokens": record.get("input_tokens"),
        "output_tokens": record.get("output_tokens"),
        "attempt_count": record.get("attempt_count"),
        "retry_count": record.get("retry_count"),
        "section_count": record.get("section_count"),
        "renderer_status": record.get("renderer_status"),
        "model_id": record.get("model_id"),
        "gpu_sample_count": count,
        "gpu_device_name": record.get("gpu_device_name"),
        "gpu_utilization_mean_pct": record.get("gpu_utilization_sum_pct") / count if count and record.get("gpu_utilization_sum_pct") is not None else None,
        "gpu_utilization_max_pct": record.get("gpu_utilization_max_pct"),
        "gpu_memory_mean_mib": record.get("gpu_memory_sum_mib") / count if count and record.get("gpu_memory_sum_mib") is not None else None,
        "gpu_memory_max_mib": record.get("gpu_memory_max_mib"),
        "gpu_memory_total_mib": record.get("gpu_memory_total_mib"),
        "gpu_power_mean_w": record.get("gpu_power_sum_w") / count if count and record.get("gpu_power_sum_w") is not None else None,
        "gpu_temperature_max_c": record.get("gpu_temperature_max_c"),
        "gpu_sm_clock_mean_mhz": record.get("gpu_sm_clock_sum_mhz") / count if count and record.get("gpu_sm_clock_sum_mhz") is not None else None,
        "torch_allocated_baseline_bytes": record.get("torch_allocated_baseline_bytes"),
        "torch_reserved_baseline_bytes": record.get("torch_reserved_baseline_bytes"),
        "torch_allocated_peak_bytes": record.get("torch_allocated_peak_bytes"),
        "torch_reserved_peak_bytes": record.get("torch_reserved_peak_bytes"),
        "torch_allocated_delta_bytes": record.get("torch_allocated_delta_bytes"),
        "torch_reserved_delta_bytes": record.get("torch_reserved_delta_bytes"),
    }


@router.get(
    "/summary",
    response_model=UsageSummaryResponse,
    summary="Summarize request outcomes and GPU samples during generation",
    responses={422: {"model": ErrorResponse, "description": "Unsupported time window"}},
)
def usage_summary(
    request: Request,
    response: Response,
    window: UsageWindow = "24h",
) -> UsageSummaryResponse:
    store = _store(request)
    _prune_if_due(store)
    response.headers["Cache-Control"] = "no-store"
    return UsageSummaryResponse.model_validate(store.summarize(window))


@router.get(
    "/gpu/current",
    response_model=UsageGpuCurrentResponse,
    summary="Read a best-effort GPU device snapshot without loading a model",
)
def current_gpu(response: Response) -> UsageGpuCurrentResponse:
    response.headers["Cache-Control"] = "no-store"
    return UsageGpuCurrentResponse.model_validate(current_gpu_snapshot())


@router.get(
    "",
    response_model=UsageListResponse,
    summary="List privacy-minimized generation audit records",
    responses={422: {"model": ErrorResponse, "description": "Invalid cursor or filter"}},
)
def list_usages(
    request: Request,
    response: Response,
    cursor: Annotated[str | None, Query(max_length=512)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    window: UsageWindow | None = None,
    status: UsageOutcome | None = None,
    stage: UsageStage | None = None,
    q: Annotated[str | None, Query(max_length=200)] = None,
) -> UsageListResponse:
    store = _store(request)
    _prune_if_due(store)
    try:
        page = store.list_records(
            cursor=cursor,
            limit=limit,
            window=window,
            status=status,
            stage=stage,
            q=q,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=422,
            detail=ErrorResponse(code="invalid_usage_filter", message="Filter Usage tidak valid.").model_dump(),
        ) from error
    response.headers["Cache-Control"] = "no-store"
    return UsageListResponse(
        items=[UsageRecordResponse.model_validate(_record_view(row)) for row in page["items"]],
        next_cursor=page["next_cursor"],
        limit=page["limit"],
    )


@router.get(
    "/{usage_id}",
    response_model=UsageDetailResponse,
    summary="Read safe timeline and bounded GPU samples for one run",
    responses={404: {"model": ErrorResponse, "description": "Usage record not found"}},
)
def usage_detail(usage_id: UUID, request: Request, response: Response) -> UsageDetailResponse:
    store = _store(request)
    _prune_if_due(store)
    record = store.get_record(str(usage_id))
    if record is None:
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(code="usage_not_found", message="Usage record tidak ditemukan.").model_dump(),
        )
    samples = store.get_samples(str(usage_id), limit=300)
    response.headers["Cache-Control"] = "no-store"
    data = _record_view(record)
    try:
        confirmed_facts = json.loads(record.get("confirmed_facts_json") or "[]")
    except (TypeError, json.JSONDecodeError):
        confirmed_facts = []
    data["prompt"] = record.get("prompt")
    data["confirmed_facts"] = confirmed_facts if isinstance(confirmed_facts, list) else []
    data["events"] = record.get("events", [])
    data["samples"] = samples
    return UsageDetailResponse.model_validate(data)

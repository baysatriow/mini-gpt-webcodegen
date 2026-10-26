"""Read-only routes for safe, accepted generation artifacts."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import logging
import os
from io import BytesIO
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

from apps.api.schemas import (
    ErrorResponse,
    GenerationRequest,
    GenerationResponse,
    GenerationSummary,
    SourceResponse,
)
from apps.api.services.artifacts import ArtifactNotFoundError, ArtifactStore, new_generation_id
from apps.api.services.intake import validate_intake
from apps.api.services.runtime import get_runtime
from apps.api.services.usage_audit import UsageRecorder
from apps.api.services.usage_telemetry import (
    GenerationGpuSampler,
    begin_torch_memory_measurement,
    finish_torch_memory_measurement,
)


router = APIRouter(prefix="/api/v1/generations", tags=["generations"])
logger = logging.getLogger(__name__)


def _api_origin(host: str, port: int) -> str:
    rendered_host = f"[{host}]" if ":" in host else host
    return f"http://{rendered_host}:{port}"


def _store() -> ArtifactStore:
    runtime = get_runtime()
    return ArtifactStore(
        output_root=runtime.settings.generation_output_dir,
        project_root=runtime.project_root,
        api_origin=_api_origin(runtime.settings.host, runtime.settings.port),
    )


def _not_found() -> HTTPException:
    return HTTPException(
        status_code=404,
        detail=ErrorResponse(code="generation_not_found", message="Generation artifact not found").model_dump(),
    )


def _generation_directory(store: ArtifactStore, generation_id: str) -> Path:
    try:
        return store.generation_dir(generation_id)
    except ArtifactNotFoundError as error:
        raise _not_found() from error


@router.get(
    "/{generation_id}/preview/{relative_path:path}",
    response_class=Response,
    summary="Show one accepted preview file",
    response_description="Renderer HTML, CSS, JavaScript, or a referenced local SVG asset",
    responses={
        200: {
            "description": "One fixed-type accepted renderer file",
            "content": {
                "text/html": {},
                "text/css": {},
                "application/javascript": {},
                "image/svg+xml": {},
            },
        },
        404: {"model": ErrorResponse, "description": "Generation or preview file not found"},
    },
)
def preview_file(generation_id: str, relative_path: str) -> Response:
    store = _store()
    generation_dir = _generation_directory(store, generation_id)
    try:
        payload, content_type = store.read_accepted_preview_file(generation_dir, relative_path)
    except ArtifactNotFoundError as error:
        raise _not_found() from error

    api_origin = _api_origin(get_runtime().settings.host, get_runtime().settings.port)
    headers = {
        "Content-Security-Policy": (
            "default-src 'none'; base-uri 'none'; object-src 'none'; form-action 'none'; "
            f"connect-src 'none'; script-src 'self' {api_origin}; "
            f"style-src 'self' {api_origin}; img-src 'self' {api_origin} data:"
        ),
        "X-Content-Type-Options": "nosniff",
        "Cache-Control": "no-store",
    }
    return Response(content=payload, media_type=content_type, headers=headers)


@router.get(
    "/{generation_id}/source",
    response_model=SourceResponse,
    summary="Read accepted HTML, CSS, and JavaScript",
    response_description="Exactly the three renderer source files",
    responses={404: {"model": ErrorResponse, "description": "Accepted source files not found"}},
)
def source_files(generation_id: str, response: Response) -> SourceResponse:
    store = _store()
    generation_dir = _generation_directory(store, generation_id)
    try:
        source = store.read_accepted_source(generation_dir)
    except ArtifactNotFoundError as error:
        raise _not_found() from error
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return SourceResponse.model_validate(source)


@router.get(
    "/{generation_id}/download.zip",
    response_class=Response,
    summary="Download accepted renderer output and referenced assets",
    response_description="A ZIP containing only the accepted renderer files and attribution",
    responses={
        200: {
            "description": "Accepted source and asset ZIP",
            "content": {"application/zip": {"schema": {"type": "string", "format": "binary"}}},
        },
        404: {"model": ErrorResponse, "description": "Accepted ZIP not found"},
    },
)
def download_zip(generation_id: str) -> Response:
    store = _store()
    generation_dir = _generation_directory(store, generation_id)
    archive = BytesIO()
    try:
        store.build_accepted_zip(generation_dir, archive)
    except ArtifactNotFoundError as error:
        raise _not_found() from error
    return Response(
        content=archive.getvalue(),
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="website-{generation_id}.zip"',
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get(
    "/{generation_id}",
    response_model=GenerationSummary,
    summary="Read a safe generation summary",
    responses={404: {"model": ErrorResponse, "description": "Generation not found"}},
)
def generation_summary(generation_id: str) -> GenerationSummary:
    store = _store()
    generation_dir = _generation_directory(store, generation_id)
    try:
        return store.public_generation_summary(generation_dir)
    except ArtifactNotFoundError as error:
        raise _not_found() from error


def _http_error(
    status_code: int,
    code: str,
    message: str,
    missing_fields: list[str] | None = None,
) -> HTTPException:
    payload = ErrorResponse(
        code=code,
        message=message,
        missing_fields=missing_fields or [],
    )
    return HTTPException(status_code=status_code, detail=payload.model_dump())


def _api_summary(request: dict, created_at: str) -> dict[str, str]:
    facts = request.get("business_facts", [])
    business_name = next(
        (
            fact.get("value")
            for fact in facts
            if isinstance(fact, dict) and fact.get("kind") == "name" and isinstance(fact.get("value"), str)
        ),
        None,
    )
    summary = {
        "genre": request.get("genre"),
        "style_mode": request.get("style_mode"),
        "business_name": business_name,
        "created_at": created_at,
    }
    return {key: value for key, value in summary.items() if isinstance(value, str)}


def _persist_result(output_dir: Path, report: dict) -> None:
    result_path = output_dir / "result.json"
    temporary = output_dir / f".result-{new_generation_id()}.tmp"
    try:
        with temporary.open("x", encoding="utf-8", newline="\n") as handle:
            json.dump(report, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(temporary, result_path)
    finally:
        temporary.unlink(missing_ok=True)


def _generation_failure(
    generation_id: str,
    message: str,
    missing_fields: list[str] | None = None,
) -> GenerationResponse:
    return GenerationResponse(
        status="generation_failed",
        generation_id=generation_id,
        message=message,
        missing_fields=missing_fields or [],
    )


def _request_recorder(request: Request) -> UsageRecorder | None:
    recorder = getattr(request.state, "usage_recorder", None)
    return recorder if isinstance(recorder, UsageRecorder) else None


def _finish_usage(
    request: Request,
    *,
    stage: str,
    outcome: str,
    http_status: int,
    code: str | None,
    generation_id: str | None = None,
) -> None:
    recorder = _request_recorder(request)
    if recorder is None:
        return
    recorder.set_stage(stage, code=code, generation_id=generation_id)
    recorder.finish(outcome, http_status=http_status, code=code)


def _generation_telemetry(
    recorder: UsageRecorder | None,
    sampler: GenerationGpuSampler | None,
    torch_baseline: dict[str, int] | None,
) -> None:
    if recorder is None:
        return
    metrics: dict[str, Any] = {}
    if sampler is not None:
        try:
            metrics.update(sampler.finish())
        except Exception:
            logger.exception("GPU Usage sampler did not finish cleanly")
    try:
        metrics.update(finish_torch_memory_measurement(torch_baseline))
    except Exception:
        logger.exception("PyTorch Usage memory snapshot failed")
    recorder.set_metrics(**metrics)


def _safe_generation_failure_code(error: Exception) -> str:
    try:
        import torch

        if isinstance(error, torch.cuda.OutOfMemoryError):
            return "cuda_out_of_memory"
    except Exception:
        pass
    return "inference_failed"


@router.post(
    "",
    response_model=GenerationResponse,
    summary="Generate one page from a revalidated request",
    description=(
        "Runs one blocking local generation after source-bound intake passes. "
        "The model is loaded only by this explicit endpoint."
    ),
    responses={
        409: {"model": ErrorResponse, "description": "Intake is not ready or another generation is active"},
        413: {"model": ErrorResponse, "description": "Request exceeds the supported context budget"},
        422: {"model": ErrorResponse, "description": "Request does not match the API JSON schema"},
        503: {"model": ErrorResponse, "description": "Selected local model is unavailable"},
        500: {"model": ErrorResponse, "description": "Local generation service failed"},
    },
)
def create_generation(body: GenerationRequest, http_request: Request) -> GenerationResponse:
    recorder = _request_recorder(http_request)
    runtime = get_runtime()
    if not runtime.generation_lock.acquire(blocking=False):
        _finish_usage(
            http_request,
            stage="request_validation",
            outcome="rejected",
            http_status=409,
            code="generation_busy",
        )
        raise _http_error(
            409,
            "generation_in_progress",
            "Generation lain sedang berjalan. Tunggu sampai selesai sebelum mencoba kembali.",
        )
    if not runtime.inference_lock.acquire(blocking=False):
        runtime.generation_lock.release()
        _finish_usage(
            http_request,
            stage="request_validation",
            outcome="rejected",
            http_status=409,
            code="generation_busy",
        )
        raise _http_error(
            409,
            "model_busy",
            "Model sedang digunakan untuk proses lain. Coba lagi setelah proses selesai.",
        )

    try:
        if recorder is not None:
            recorder.set_stage("intake_validation")
        intake = validate_intake(
            body.prompt,
            body.draft.model_dump(exclude_none=True),
            runtime=runtime,
            extraction_token=body.extraction_token,
        )
        if intake.status != "ready" or intake.request is None:
            too_long = intake.status == "input_too_long"
            status_code = 413 if too_long else 409
            failure_code = (
                "input_too_long"
                if too_long
                else "unsupported_request"
                if intake.status == "unsupported_request"
                else "input_rejected"
            )
            _finish_usage(
                http_request,
                stage="intake_validation",
                outcome="rejected",
                http_status=status_code,
                code=failure_code,
            )
            raise _http_error(
                status_code,
                intake.status,
                intake.message,
                intake.missing_fields,
            )

        request = dict(intake.request)
        generation_id = new_generation_id()
        created_at = datetime.now(timezone.utc).isoformat()
        api_summary = _api_summary(request, created_at)

        output_root = runtime.settings.generation_output_dir.resolve(strict=False)
        try:
            output_root.mkdir(parents=True, exist_ok=True)
        except OSError as error:
            logger.exception("Generation output root is unavailable")
            _finish_usage(
                http_request,
                stage="persist_result",
                outcome="failed",
                http_status=500,
                code="storage_failed",
                generation_id=generation_id,
            )
            raise _http_error(
                500,
                "generation_storage_unavailable",
                "Penyimpanan lokal generation tidak tersedia.",
            ) from error

        output_dir = output_root / generation_id
        for _ in range(3):
            if not output_dir.exists() and not output_dir.is_symlink():
                break
            generation_id = new_generation_id()
            api_summary = _api_summary(request, created_at)
            output_dir = output_root / generation_id
        else:
            _finish_usage(
                http_request,
                stage="persist_result",
                outcome="failed",
                http_status=500,
                code="storage_failed",
                generation_id=generation_id,
            )
            raise _http_error(
                500,
                "generation_id_unavailable",
                "ID generation lokal tidak dapat dialokasikan.",
            )

        if recorder is not None:
            recorder.set_stage("model_load", generation_id=generation_id)
            recorder.set_metrics(model_id=runtime.settings.checkpoint_path.name)
        try:
            generator = runtime.get_generator()
        except Exception as error:
            logger.exception("Selected generator could not be initialized")
            _finish_usage(
                http_request,
                stage="model_load",
                outcome="failed",
                http_status=503,
                code="model_unavailable",
                generation_id=generation_id,
            )
            raise _http_error(503, "model_unavailable", "Model lokal belum siap untuk generation.") from error

        sampler = None
        torch_baseline = begin_torch_memory_measurement() if recorder is not None else None
        if recorder is not None:
            try:
                sampler = GenerationGpuSampler(recorder.store, recorder.usage_id).start()
            except Exception:
                logger.exception("GPU Usage sampler could not start")
            recorder.set_stage("inference", generation_id=generation_id)
        try:
            report = generator.generate(request, output_dir)
        except Exception as error:
            logger.exception("Generation %s failed before a report was returned", generation_id)
            _generation_telemetry(recorder, sampler, torch_baseline)
            if recorder is not None:
                recorder.set_metrics(inference_started=True)
                recorder.finish("failed", http_status=200, code=_safe_generation_failure_code(error))
            try:
                output_dir.mkdir(parents=False, exist_ok=True)
                _persist_result(
                    output_dir,
                    {
                        "request_id": request["request_id"],
                        "status": "stage_failed",
                        "api_summary": api_summary,
                        "errors": ["Generation failed; see the local API log."],
                    },
                )
            except OSError:
                logger.exception("Could not persist failure record for generation %s", generation_id)
            return _generation_failure(
                generation_id,
                "Generation gagal pada pemeriksaan internal. Periksa request lalu coba kembali.",
            )

        if not isinstance(report, dict):
            logger.error("Generation %s returned an invalid report", generation_id)
            report = {"request_id": request["request_id"], "status": "stage_failed"}
        _generation_telemetry(recorder, sampler, torch_baseline)
        report["api_summary"] = api_summary
        attempts = report.get("attempts")
        attempts = attempts if isinstance(attempts, list) else []
        total_generated_tokens = report.get("total_generated_tokens")
        if type(total_generated_tokens) is not int or total_generated_tokens < 0:
            total_generated_tokens = sum(
                attempt.get("generated_tokens", 0)
                for attempt in attempts
                if isinstance(attempt, dict)
                and type(attempt.get("generated_tokens")) is int
                and attempt["generated_tokens"] >= 0
            )
        retry_count = sum(
            1
            for attempt in attempts
            if isinstance(attempt, dict)
            and type(attempt.get("retry")) is int
            and attempt["retry"] > 0
        )
        if recorder is not None:
            recorder.set_metrics(
                inference_started=bool(attempts),
                input_tokens=(
                    report.get("total_input_tokens")
                    if type(report.get("total_input_tokens")) is int and report["total_input_tokens"] >= 0
                    else None
                ),
                output_tokens=total_generated_tokens,
                attempt_count=len(attempts),
                retry_count=retry_count,
                section_count=report.get("sections") if type(report.get("sections")) is int else None,
                renderer_status=(
                    report.get("status")
                    if report.get("status") in {"accepted", "stage_failed", "input_too_long", "missing_information"}
                    else "unknown"
                ),
            )
            recorder.set_stage("output_validation", generation_id=generation_id)
            if report.get("status") == "accepted":
                recorder.set_stage("render_export", generation_id=generation_id)
            recorder.set_stage("persist_result", generation_id=generation_id)
        try:
            _persist_result(output_dir, report)
        except OSError:
            logger.exception("Could not persist safe summary for generation %s", generation_id)

        status = report.get("status")
        if status == "accepted":
            if recorder is not None:
                recorder.finish("completed", http_status=200)
            return GenerationResponse(
                status="completed",
                generation_id=generation_id,
                message="Halaman berhasil dibuat dan siap ditinjau.",
                section_count=report.get("sections") if type(report.get("sections")) is int else None,
                preview_url=(
                    f"{_api_origin(runtime.settings.host, runtime.settings.port)}"
                    f"/api/v1/generations/{generation_id}/preview/index.html"
                ),
                download_url=(
                    f"{_api_origin(runtime.settings.host, runtime.settings.port)}"
                    f"/api/v1/generations/{generation_id}/download.zip"
                ),
                files=["index.html", "styles.css", "app.js"],
            )
        if status == "input_too_long":
            if recorder is not None:
                recorder.finish("rejected", http_status=200, code="input_too_long")
            return GenerationResponse(
                status="input_too_long",
                generation_id=generation_id,
                message="Request melebihi batas konteks. Ringkas prompt atau fakta secara manual.",
            )
        if status == "missing_information":
            if recorder is not None:
                recorder.finish("failed", http_status=200, code="output_invalid")
            return _generation_failure(
                generation_id,
                "Informasi usaha belum lengkap. Lengkapi fakta yang diminta sebelum mencoba kembali.",
                ["business_facts"],
            )
        if recorder is not None:
            recorder.finish("failed", http_status=200, code="inference_failed")
        return _generation_failure(
            generation_id,
            "Generation gagal pada pemeriksaan internal. Periksa request lalu coba kembali.",
        )
    finally:
        runtime.inference_lock.release()
        runtime.generation_lock.release()

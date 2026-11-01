"""Loopback-only FastAPI application for the local page generator."""

from __future__ import annotations

import logging
import asyncio
from contextlib import asynccontextmanager, suppress
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from apps.api.routers import generations, health, intake, usages
from apps.api.schemas import ErrorResponse
from apps.api.services.usage_audit import audit_generation_request
from apps.api.services.usage_store import UsageStore
from apps.api.settings import load_settings


logger = logging.getLogger(__name__)
_HTTP_ERRORS = {
    404: ("not_found", "Resource not found."),
    409: ("request_conflict", "The request conflicts with the current service state."),
    413: ("input_too_long", "The request exceeds the supported size."),
    422: ("invalid_request", "Request tidak sesuai dengan kontrak JSON API."),
    500: ("internal_error", "Terjadi kesalahan internal. Periksa log lokal API."),
    503: ("service_unavailable", "Layanan lokal belum siap."),
}


def create_app(*, usage_root: Path | None = None) -> FastAPI:
    settings = load_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        store = UsageStore(usage_root or settings.project_root / "outputs/webapp/usages")
        instance_id = store.start_instance()
        app.state.usage_store = store
        app.state.usage_instance_id = instance_id

        async def heartbeat() -> None:
            while True:
                await asyncio.sleep(15)
                await asyncio.to_thread(store.heartbeat_instance, instance_id)

        task = asyncio.create_task(heartbeat(), name="usage-instance-heartbeat")
        try:
            yield
        finally:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task
            await asyncio.to_thread(store.stop_instance, instance_id)

    app = FastAPI(
        title="Mini GPT WebCodeGen API",
        description=(
            "API lokal untuk intake source-bound, generation halaman, preview aman, "
            "dan unduhan artefak yang diterima renderer."
        ),
        version="0.1.0",
        docs_url="/docs",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.allowed_origins),
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
        expose_headers=["X-Usage-ID"],
    )

    app.middleware("http")(audit_generation_request)

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(
        request: Request,
        error: StarletteHTTPException,
    ) -> JSONResponse:
        default_code, default_message = _HTTP_ERRORS.get(
            error.status_code,
            ("request_failed", "Permintaan tidak dapat diproses."),
        )
        try:
            payload = ErrorResponse.model_validate(error.detail)
        except Exception:
            payload = ErrorResponse(code=default_code, message=default_message)
        return JSONResponse(
            status_code=error.status_code,
            content=payload.model_dump(),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_invalid_request(
        request: Request,
        error: RequestValidationError,
    ) -> JSONResponse:
        payload = ErrorResponse(
            code="invalid_request",
            message="Request tidak sesuai dengan kontrak JSON API.",
        )
        return JSONResponse(status_code=422, content=payload.model_dump())

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, error: Exception) -> JSONResponse:
        logger.exception("Unhandled API error")
        payload = ErrorResponse(
            code="internal_error",
            message="Terjadi kesalahan internal. Periksa log lokal API.",
        )
        return JSONResponse(status_code=500, content=payload.model_dump())

    app.include_router(health.router)
    app.include_router(intake.router)
    app.include_router(generations.router)
    app.include_router(usages.router)
    return app


app = create_app()

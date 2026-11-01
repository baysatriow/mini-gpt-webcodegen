"""Request lifecycle recorder and generation-only audit middleware."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import json
import logging
import re
import threading
import time
import uuid
from typing import Any, Awaitable, Callable

from fastapi import Request
from fastapi.responses import JSONResponse, Response

from apps.api.schemas import ErrorResponse
from apps.api.services.usage_store import UsageStore


logger = logging.getLogger(__name__)
_FACT_ID = re.compile(r"[a-z][a-z0-9_-]{0,63}\Z")
_SCALAR_FACT_LABELS = {
    "name": "Nama usaha",
    "description": "Deskripsi usaha",
    "value": "Nilai utama",
}
_STRUCTURED_FACT_LABELS = {
    "service": "Layanan",
    "project": "Proyek",
    "process": "Langkah proses",
    "faq": "FAQ",
}


def confirmed_business_facts(values: Any) -> list[dict[str, Any]]:
    """Keep only explicitly confirmed, display-safe fields from the generation draft."""
    if not isinstance(values, list):
        return []
    facts: list[dict[str, Any]] = []
    kind_counts: dict[str, int] = {}
    for fact in values[:24]:
        if not isinstance(fact, dict):
            continue
        fact_id = fact.get("id")
        kind = fact.get("kind")
        if not isinstance(fact_id, str) or not _FACT_ID.fullmatch(fact_id) or not isinstance(kind, str):
            continue
        if kind in _SCALAR_FACT_LABELS:
            if set(fact) != {"id", "kind", "value", "evidence"}:
                continue
            value = fact.get("value")
            if fact.get("evidence") != {"user_confirmed": True}:
                continue
            max_length = 3000 if kind == "description" else 100 if kind == "name" else 1000
            if not isinstance(value, str) or not value.strip() or len(value) > max_length:
                continue
            facts.append(
                {
                    "id": fact_id,
                    "kind": kind,
                    "label": _SCALAR_FACT_LABELS[kind],
                    "title": None,
                    "value": value,
                }
            )
            continue
        if kind not in _STRUCTURED_FACT_LABELS or set(fact) != {"id", "kind", "value"}:
            continue
        value = fact.get("value")
        if not isinstance(value, dict) or set(value) != {"title", "title_evidence", "text", "text_evidence"}:
            continue
        title, text = value.get("title"), value.get("text")
        if (
            value.get("title_evidence") != {"user_confirmed": True}
            or value.get("text_evidence") != {"user_confirmed": True}
            or not isinstance(title, str)
            or not title.strip()
            or len(title) > 100
            or not isinstance(text, str)
            or not text.strip()
            or len(text) > 3000
        ):
            continue
        kind_counts[kind] = kind_counts.get(kind, 0) + 1
        facts.append(
            {
                "id": fact_id,
                "kind": kind,
                "label": f"{_STRUCTURED_FACT_LABELS[kind]} {kind_counts[kind]}",
                "title": title,
                "value": text,
            }
        )
    return facts


class UsageRecorder:
    def __init__(self, store: UsageStore, usage_id: str, started_monotonic: float) -> None:
        self.store = store
        self.usage_id = usage_id
        self.started_monotonic = started_monotonic
        self.stage = "request_received"
        self._finished = False
        self._finish_lock = threading.Lock()

    @property
    def finished(self) -> bool:
        return self._finished

    def set_stage(self, stage: str, *, code: str | None = None, generation_id: str | None = None) -> None:
        if self._finished:
            return
        self.stage = stage
        fields: dict[str, Any] = {"stage": stage}
        if generation_id is not None:
            fields["generation_id"] = generation_id
        if code is not None:
            fields["failure_code"] = code
        try:
            self.store.update_record(self.usage_id, **fields)
            self.store.add_event(
                self.usage_id,
                stage,
                "started",
                failure_code=code,
                elapsed_ms=max(0, int((time.monotonic() - self.started_monotonic) * 1000)),
            )
        except Exception:
            logger.exception("Could not record a Usage stage update")

    def set_metrics(self, **safe_metrics: Any) -> None:
        if self._finished:
            return
        try:
            self.store.update_record(self.usage_id, **safe_metrics)
        except Exception:
            logger.exception("Could not record Usage metrics")

    def set_request_details(self, prompt: str | None, confirmed_facts: list[dict[str, Any]]) -> None:
        facts_json = json.dumps(confirmed_facts, separators=(",", ":"), ensure_ascii=False)
        self.store.update_record(
            self.usage_id,
            prompt=prompt,
            confirmed_facts_json=facts_json,
        )

    def finish(
        self,
        outcome: str,
        *,
        http_status: int | None = None,
        code: str | None = None,
    ) -> None:
        with self._finish_lock:
            if self._finished:
                return
            if outcome not in {"completed", "rejected", "failed", "interrupted"}:
                raise ValueError("Invalid terminal Usage outcome")
            now = datetime.now(timezone.utc).isoformat()
            duration_ms = max(0, int((time.monotonic() - self.started_monotonic) * 1000))
            try:
                self.store.update_record(
                    self.usage_id,
                    outcome=outcome,
                    stage="completed" if outcome == "completed" else self.stage,
                    finished_at=now,
                    duration_ms=duration_ms,
                    http_status=http_status,
                    failure_code=code,
                )
                self.store.add_event(
                    self.usage_id,
                    "completed" if outcome == "completed" else self.stage,
                    outcome,
                    failure_code=code,
                    occurred_at=now,
                    elapsed_ms=duration_ms,
                )
            except Exception:
                logger.exception("Could not finalize a Usage record")
            finally:
                self._finished = True


async def audit_generation_request(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    if request.method != "POST" or request.url.path != "/api/v1/generations":
        return await call_next(request)

    store: UsageStore | None = getattr(request.app.state, "usage_store", None)
    instance_id: str | None = getattr(request.app.state, "usage_instance_id", None)
    if store is None or instance_id is None:
        error = ErrorResponse(
            code="usage_storage_unavailable",
            message="Penyimpanan audit lokal belum siap. Generation tidak dijalankan.",
        )
        return JSONResponse(status_code=503, content=error.model_dump())

    usage_id = str(uuid.uuid4())
    started_at = datetime.now(timezone.utc).isoformat()
    started_monotonic = time.monotonic()
    recorder = UsageRecorder(store, usage_id, started_monotonic)
    try:
        store.create_record(
            {
                "usage_id": usage_id,
                "server_instance_id": instance_id,
                "started_at": started_at,
                "outcome": "running",
                "stage": "request_received",
            }
        )
    except Exception:
        logger.exception("Could not create a Usage audit record; generation was not started")
        error = ErrorResponse(
            code="usage_storage_unavailable",
            message="Penyimpanan audit lokal tidak tersedia. Generation tidak dijalankan.",
        )
        return JSONResponse(status_code=503, content=error.model_dump())

    request.state.usage_recorder = recorder
    try:
        response = await call_next(request)
    except asyncio.CancelledError:
        try:
            recorder.finish("interrupted", code="server_interrupted")
        except Exception:
            logger.exception("Could not finalize an interrupted Usage record")
        raise
    except Exception:
        try:
            recorder.finish("failed", http_status=500, code="internal_error")
        except Exception:
            logger.exception("Could not finalize a failed Usage record")
        raise

    if not recorder.finished:
        status = response.status_code
        if status == 422:
            stage, outcome, code = "request_validation", "rejected", "invalid_request"
        elif status == 413:
            stage, outcome, code = "request_validation", "rejected", "input_too_long"
        elif status == 409:
            stage, outcome, code = "request_validation", "rejected", "generation_busy"
        elif 400 <= status < 500:
            stage, outcome, code = "request_validation", "rejected", "input_rejected"
        else:
            stage, outcome, code = "inference", "failed", "internal_error"
        try:
            recorder.set_stage(stage, code=code)
            recorder.finish(outcome, http_status=status, code=code)
        except Exception:
            logger.exception("Could not finalize a Usage audit record")

    response.headers["X-Usage-ID"] = usage_id
    response.headers.setdefault("Cache-Control", "no-store")
    return response

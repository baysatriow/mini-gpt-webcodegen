"""Safe intake adapter around the source-bound pipeline validator."""

from __future__ import annotations

from typing import Any

from apps.api.schemas import IntakeResponse, MAX_PROMPT_CHARS
from apps.api.services.runtime import Runtime, get_runtime


SAFE_MESSAGES = {
    "needs_clarification": "Lengkapi fakta usaha yang ditandai, lalu periksa kembali rancangan sebelum generation.",
    "unsupported_request": "Versi ini mendukung landing page atau company profile dengan CSS biasa atau Tailwind. Permintaan di luar cakupan perlu disederhanakan.",
    "input_too_long": "Prompt atau fakta melebihi batas karakter atau budget konteks. Ringkas secara manual; sistem tidak memotong isi.",
    "ready": "Informasi utama sudah tervalidasi. Periksa ringkasan request sebelum meminta generation.",
}

def _workflow_response(status: str, missing_fields: list[str] | None = None, request: dict[str, Any] | None = None) -> IntakeResponse:
    if status not in SAFE_MESSAGES:
        status = "needs_clarification"
        missing_fields = ["request_draft"]
        request = None
    safe_missing = list(dict.fromkeys(
        field for field in (missing_fields or []) if isinstance(field, str) and field
    ))
    return IntakeResponse(
        status=status,
        message=SAFE_MESSAGES[status],
        missing_fields=safe_missing,
        request=request if status == "ready" else None,
    )


def validate_intake(
    prompt: str,
    draft: dict[str, Any],
    runtime: Runtime | None = None,
    extraction_token: str | None = None,
    capability_assessments: list[dict[str, Any]] | None = None,
) -> IntakeResponse:
    """Validate a user draft without loading a generator or creating output."""
    if not isinstance(prompt, str) or not prompt.strip():
        return _workflow_response("needs_clarification", ["prompt"])
    if not isinstance(draft, dict):
        return _workflow_response("needs_clarification", ["request_draft"])
    draft_prompt = draft.get("prompt")
    if len(prompt) > MAX_PROMPT_CHARS or (
        isinstance(draft_prompt, str) and len(draft_prompt) > MAX_PROMPT_CHARS
    ):
        return _workflow_response("input_too_long")
    if draft.get("prompt") != prompt:
        return _workflow_response("needs_clarification", ["prompt"])

    services = runtime or get_runtime()
    if extraction_token is not None:
        capability_assessments = services.verify_intake_token(prompt, extraction_token)
        if capability_assessments is None:
            return _workflow_response("needs_clarification", ["prompt"])
    services.ensure_project_importable()
    from src.fullpage.intake import prepare_intake

    result = prepare_intake(
        prompt,
        draft,
        services.get_tokenizer(),
        services.get_intake_catalog(),
        capability_assessments=capability_assessments,
    )
    return _workflow_response(
        result.status,
        list(result.missing_fields),
        result.request,
    )

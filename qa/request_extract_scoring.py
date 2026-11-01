"""Fail-closed scoring adapter for frozen request-extractor development output."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from qa.evaluate_request_extract_v1 import _score as _frozen_score


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def score_request_extract(
    records: list[dict[str, Any]],
    row_by_id: dict[str, dict[str, Any]],
    manifest: dict[str, Any],
    checkpoint_sha: str,
    config_sha: str,
    rows_sha: str,
    elapsed_seconds: float,
) -> dict[str, Any]:
    """Score only schema-valid predictions and make any invalid row fail the quality gate."""
    invalid_rows = sum(record.get("schema_valid") is not True for record in records)
    safe_records = [
        {**record, "prediction": None} if record.get("schema_valid") is not True else record
        for record in records
    ]
    report = _frozen_score(
        safe_records,
        row_by_id,
        manifest,
        checkpoint_sha,
        config_sha,
        rows_sha,
        elapsed_seconds,
    )
    report["schema_invalid_rows"] = invalid_rows
    report["raw_output_quality_gate"] = report["raw_output_quality_gate"] and invalid_rows == 0
    report["scoring_module"] = Path(__file__).resolve().relative_to(Path(__file__).resolve().parents[1]).as_posix()
    report["scoring_module_sha256"] = _sha256(Path(__file__))
    return report

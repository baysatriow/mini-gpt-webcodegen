"""Canonical target serialization for source-bound generation tasks."""

import json

from .serialization import OUTPUT_BUDGETS


def serialize_source_bound_task(task: str, value: dict) -> str:
    if task not in OUTPUT_BUDGETS:
        raise ValueError("Unknown source-bound full-page task")
    if not isinstance(value, dict):
        raise ValueError("Source-bound task target must be a JSON object")
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

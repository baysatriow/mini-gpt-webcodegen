"""Versioned wire contract and source-message serialization for prompt extraction."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[2]
CONTRACT_VERSION = "request-extract-v1"
CANONICAL_FORMAT = "prompt-messages-v1"
SCHEMA_PATH = ROOT / "configs/fullpage/request-extract-v1.schema.json"
_SCHEMA = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
Draft202012Validator.check_schema(_SCHEMA)
_VALIDATOR = Draft202012Validator(_SCHEMA)

MAX_BRIEF_CHARS = 4000
MAX_MESSAGES = 16
EXTRACTION_SCOPES = (
    "business_scalars",
    "service_1",
    "service_2",
    "service_3",
    "process_1",
    "process_2",
    "process_3",
    "faq_1",
    "faq_2",
    "faq_3",
    "project_1",
    "project_2",
    "page_settings",
    "business_status",
    "capabilities",
    "corrections",
)
_ALL_CORRECTION_KINDS = {"name", "description", "value", "service", "project", "process", "faq", "genre", "style_mode", "fictitious"}
_FACT_SCOPE_SELECTORS = {
    "service_1": ("service", 0),
    "service_2": ("service", 1),
    "service_3": ("service", 2),
    "process_1": ("process", 0),
    "process_2": ("process", 1),
    "process_3": ("process", 2),
    "faq_1": ("faq", 0),
    "faq_2": ("faq", 1),
    "faq_3": ("faq", 2),
    "project_1": ("project", 0),
    "project_2": ("project", 1),
}
SCOPED_ARRAYS = {
    "business_scalars": {"facts": {"name", "description", "value"}, "corrections": set()},
    "service_1": {"facts": {"service"}, "corrections": set()},
    "service_2": {"facts": {"service"}, "corrections": set()},
    "service_3": {"facts": {"service"}, "corrections": set()},
    "process_1": {"facts": {"process"}, "corrections": set()},
    "process_2": {"facts": {"process"}, "corrections": set()},
    "process_3": {"facts": {"process"}, "corrections": set()},
    "faq_1": {"facts": {"faq"}, "corrections": set()},
    "faq_2": {"facts": {"faq"}, "corrections": set()},
    "faq_3": {"facts": {"faq"}, "corrections": set()},
    "project_1": {"facts": {"project"}, "corrections": set()},
    "project_2": {"facts": {"project"}, "corrections": set()},
    "page_settings": {"facts": set(), "corrections": set()},
    "business_status": {"facts": set(), "corrections": set()},
    "capabilities": {"facts": set(), "corrections": set()},
    "corrections": {"facts": set(), "corrections": _ALL_CORRECTION_KINDS},
}

EXTRACTION_INSTRUCTIONS = (
    "Task: request_extract. Read the ordered user messages in the JSON payload. "
    "Return exactly one JSON object matching request-extract-v1 for the requested scope. "
    "Copy values, phrases, and contexts exactly from the message text. Never invent, "
    "paraphrase, complete, summarize, or create source IDs. Scalar facts use one "
    "source_message_id. Structured facts use separate title_source_message_id and "
    "text_source_message_id. Mentions use their source ID, zero-based exact-phrase "
    "occurrence index, and intent. Report explicit corrections separately and do not "
    "choose between conflicting values. Use empty arrays when no mention exists."
)


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def canonical_messages(messages: list[dict[str, str]], scope: str) -> str:
    if scope not in SCOPED_ARRAYS:
        raise ValueError("Unknown request extraction scope")
    return canonical({"canonical_format": CANONICAL_FORMAT, "extract_scope": scope, "messages": messages})


def extractor_prompt(messages: list[dict[str, str]], scope: str) -> str:
    if scope not in SCOPED_ARRAYS:
        raise ValueError("Unknown request extraction scope")
    scope_rule = ""
    if scope.startswith(("service_", "process_", "faq_", "project_")):
        ordinal = int(scope.rsplit("_", 1)[1])
        kind = scope.rsplit("_", 1)[0]
        scope_rule = (
            f" For {kind}, return only final item {ordinal} in the order first presented by the user; "
            "an explicit correction replaces that item in its original position."
        )
    return EXTRACTION_INSTRUCTIONS + " Extract only the " + scope + " scope; leave all other arrays empty." + scope_rule + "\n" + canonical_messages(messages, scope)


def scope_output(value: dict[str, Any], scope: str) -> dict[str, Any]:
    """Keep only one compact model scope while preserving the versioned wire shape."""
    if scope not in SCOPED_ARRAYS:
        raise ValueError("Unknown request extraction scope")
    result = {key: [] for key in (
        "fact_mentions", "setting_mentions", "business_status_mentions",
        "capability_mentions", "out_of_catalog_mentions", "corrections",
    )}
    result["contract_version"] = CONTRACT_VERSION
    if scope == "business_scalars":
        result["fact_mentions"] = [item for item in value["fact_mentions"] if item["kind"] in SCOPED_ARRAYS[scope]["facts"]]
    elif scope in _FACT_SCOPE_SELECTORS:
        kind, index = _FACT_SCOPE_SELECTORS[scope]
        matching = [item for item in value["fact_mentions"] if item["kind"] == kind]
        result["fact_mentions"] = matching if index is None else matching[index:index + 1]
    elif scope == "page_settings":
        result["setting_mentions"] = list(value["setting_mentions"])
    elif scope == "business_status":
        result["business_status_mentions"] = list(value["business_status_mentions"])
    elif scope == "capabilities":
        result["capability_mentions"] = list(value["capability_mentions"])
        result["out_of_catalog_mentions"] = list(value["out_of_catalog_mentions"])
    elif scope == "corrections":
        result["corrections"] = list(value["corrections"])
    result["corrections"] = [item for item in value["corrections"] if item["kind"] in SCOPED_ARRAYS[scope]["corrections"]]
    return result


def validate_scoped_output(value: Any, scope: str) -> list[str]:
    errors = validate_request_extract(value)
    if errors or scope not in SCOPED_ARRAYS:
        return errors or ["Unknown request extraction scope"]
    fact_kinds = {item["kind"] for item in value["fact_mentions"]}
    selector = _FACT_SCOPE_SELECTORS.get(scope)
    if scope == "business_scalars":
        valid_facts = fact_kinds <= SCOPED_ARRAYS[scope]["facts"]
    elif selector is not None:
        valid_facts = fact_kinds <= {selector[0]} and len(value["fact_mentions"]) <= 1
    else:
        valid_facts = not value["fact_mentions"]
    allowed_arrays = {
        "fact_mentions": scope in {"business_scalars", *_FACT_SCOPE_SELECTORS},
        "setting_mentions": scope == "page_settings",
        "business_status_mentions": scope == "business_status",
        "capability_mentions": scope == "capabilities",
        "out_of_catalog_mentions": scope == "capabilities",
        "corrections": scope == "corrections",
    }
    has_out_of_scope = any(value[key] and not allowed for key, allowed in allowed_arrays.items())
    correction_kinds = {item["kind"] for item in value["corrections"]}
    if (not valid_facts or has_out_of_scope
            or not correction_kinds <= SCOPED_ARRAYS[scope]["corrections"]):
        return ["Extractor returned fields outside its requested scope"]
    return []


def validate_request_extract(value: Any) -> list[str]:
    """Return schema errors without turning malformed model text into a draft."""
    return [
        f"{'.'.join(str(part) for part in error.absolute_path) or '$'}: {error.message}"
        for error in sorted(_VALIDATOR.iter_errors(value), key=lambda item: list(map(str, item.absolute_path)))
    ]

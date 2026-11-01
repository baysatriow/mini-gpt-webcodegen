"""Replay frozen development extractor outputs through the source-grounded API resolver."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import time
from typing import Any

from apps.api.services.extraction import build_extraction_response
from apps.api.services.runtime import Runtime
from src.fullpage.request_extract_contracts import EXTRACTION_SCOPES, validate_request_extract


ROOT = Path(__file__).resolve().parents[1]
CONFIG = Path("configs/fullpage/training-request-extract-v1-r1.json")
DATASET = Path("data/processed/request_extract/v1")
RAW_REPORT = Path("reports/request_extract/REQEXT-V1-1800_DEVELOPMENT.json")
RAW_OUTPUT = Path("outputs/request_extract/v1/REQEXT-V1-1800_DEVELOPMENT.jsonl")
CHECKPOINT = Path("checkpoints/REQUEST-EXTRACT-V1/step1800.pt")
OUTPUT = Path("reports/request_extract/REQEXT-V1-1800_API_GATE.json")
ARRAY_FIELDS = (
    "fact_mentions",
    "setting_mentions",
    "business_status_mentions",
    "capability_mentions",
    "out_of_catalog_mentions",
    "corrections",
)
ACTIVE = "requested"
INACTIVE = {"negated", "future", "reference", "retracted"}
CORRECTION_BUCKETS = {
    "correction_single_value",
    "correction_list_value",
    "setting_correction",
    "style_correction",
    "business_status_correction",
}
CLARIFICATION_BUCKETS = {
    "input_incomplete",
    "conflict_fact_value",
    "conflict_page_setting",
    "setting_retraction_without_replacement",
    "style_retraction_without_replacement",
}
ACTIVE_UNSUPPORTED_BUCKETS = {"known_catalog_unsupported", "out_of_catalog_unsupported"}
NONACTIVE_BUCKETS = {
    "known_catalog_retraction",
    "out_of_catalog_retraction",
    "negation_future_reference",
}


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _merge(rows: list[dict[str, Any]], *, prediction: bool) -> dict[str, Any]:
    merged = {
        "contract_version": "request-extract-v1",
        **{field: [] for field in ARRAY_FIELDS},
    }
    for row in rows:
        source = row["prediction"] if prediction else json.loads(row["target"])
        if not isinstance(source, dict):
            raise ValueError("A scoped row has no JSON object")
        for field in ARRAY_FIELDS:
            merged[field].extend(source.get(field, []))
    return merged


def _draft_value(fact: dict[str, Any]) -> Any:
    value = fact.get("value")
    if fact.get("kind") in {"service", "process", "faq", "project"} and isinstance(value, dict):
        return {key: value.get(key) for key in ("title", "text")}
    return value


def _fact_source_valid(prompt: str, fact: dict[str, Any]) -> bool:
    evidence = fact.get("evidence")
    value = fact.get("value")
    if fact.get("kind") in {"service", "process", "faq", "project"} and isinstance(value, dict):
        if set(value) != {"title", "title_evidence", "text", "text_evidence"}:
            return False
        items = ((value["title"], value["title_evidence"]), (value["text"], value["text_evidence"]))
    else:
        items = ((value, evidence),)
    for text, item_evidence in items:
        span = item_evidence.get("source_span") if isinstance(item_evidence, dict) else None
        if not isinstance(text, str) or not isinstance(span, dict) or set(span) != {"start", "end"}:
            return False
        start, end = span.get("start"), span.get("end")
        if type(start) is not int or type(end) is not int or start < 0 or end <= start or end > len(prompt):
            return False
        if prompt[start:end] != text:
            return False
    return True


def _draft_facts(draft: dict[str, Any] | None) -> Counter:
    if not isinstance(draft, dict):
        return Counter()
    return Counter(
        (fact.get("kind"), _canonical(_draft_value(fact)))
        for fact in draft.get("business_facts", [])
        if isinstance(fact, dict)
    )


def _correction_applied(correction: dict[str, Any], draft: dict[str, Any] | None) -> bool:
    if not isinstance(draft, dict):
        return False
    kind = correction["kind"]
    previous = correction["previous_value"]
    replacement = correction["replacement_value"]
    if kind in {"genre", "style_mode"}:
        return draft.get(kind) == replacement
    if kind == "fictitious":
        return draft.get("fictitious") is replacement
    values = [
        _draft_value(fact)
        for fact in draft.get("business_facts", [])
        if isinstance(fact, dict) and fact.get("kind") == kind
    ]
    return replacement in values and previous not in values


def _merged_truth(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return _merge(rows, prediction=False)


def _family_record(
    family_id: str,
    source_rows: list[dict[str, Any]],
    raw_records: list[dict[str, Any]],
    runtime: Runtime,
) -> dict[str, Any]:
    scenario = source_rows[0]["scenario"]
    messages = source_rows[0]["messages"]
    if any(row["messages"] != messages or row["scenario"] != scenario for row in source_rows):
        raise ValueError("Frozen source family has inconsistent messages or scenario")
    truths_by_scope = {row["scope"]: row for row in source_rows}
    predictions_by_scope = {record["scope"]: record for record in raw_records}
    if set(truths_by_scope) != set(EXTRACTION_SCOPES) or set(predictions_by_scope) != set(EXTRACTION_SCOPES):
        raise ValueError("A development family is missing one of the frozen extraction scopes")
    raw_valid = all(
        predictions_by_scope[scope].get("schema_valid") is True
        and predictions_by_scope[scope].get("stopped_at_eos") is True
        and predictions_by_scope[scope].get("prediction") is not None
        for scope in EXTRACTION_SCOPES
    )
    truth = _merged_truth([truths_by_scope[scope] for scope in EXTRACTION_SCOPES])
    response = None
    resolver_error = None
    if raw_valid:
        try:
            predicted = _merge([predictions_by_scope[scope] for scope in EXTRACTION_SCOPES], prediction=True)
            errors = validate_request_extract(predicted)
            if errors:
                raise ValueError("Merged output failed the request extraction schema")
            response = build_extraction_response(messages, predicted, runtime)
        except Exception as error:
            resolver_error = type(error).__name__

    draft = response.draft.model_dump(exclude_none=True) if response and response.draft else None
    prompt = "\n".join(message["text"] for message in messages)
    facts = draft.get("business_facts", []) if isinstance(draft, dict) else []
    source_valid = all(_fact_source_valid(prompt, fact) for fact in facts)
    expected_fact_counts = Counter(
        (
            mention["kind"],
            _canonical(
                mention["value"] if "value" in mention
                else {"title": mention["title"], "text": mention["text"]}
            ),
        )
        for mention in truth["fact_mentions"]
    )
    actual_fact_counts = _draft_facts(draft)
    corrections = truth["corrections"]
    correction_hits = sum(_correction_applied(item, draft) for item in corrections)
    known_mentions = truth["capability_mentions"]
    unknown_mentions = truth["out_of_catalog_mentions"]
    active_unsupported = any(item["intent"] == ACTIVE for item in (*known_mentions, *unknown_mentions))
    unclear_intent = any(item["intent"] == "unclear" for item in (*known_mentions, *unknown_mentions))
    known_nonactive = any(item["intent"] in INACTIVE for item in known_mentions)
    unknown_nonactive = any(item["intent"] in INACTIVE for item in unknown_mentions)
    retraction_expected = any(item["intent"] == "retracted" for item in (*known_mentions, *unknown_mentions))
    response_status = response.status if response else "extractor_error"
    return {
        "family_id": family_id,
        "scenario": scenario,
        "status": response_status,
        "missing_fields_count": len(response.missing_fields) if response else 0,
        "conflict_count": len(response.conflicts) if response else 0,
        "unsupported_count": len(response.unsupported_requests) if response else 0,
        "raw_scopes_valid": raw_valid,
        "resolver_ok": response is not None,
        "source_valid": source_valid,
        "accepted_fact_count": sum(actual_fact_counts.values()),
        "expected_fact_count": sum(expected_fact_counts.values()),
        "exact_fact_tp": sum((actual_fact_counts & expected_fact_counts).values()),
        "exact_fact_fp": sum((actual_fact_counts - expected_fact_counts).values()),
        "exact_fact_fn": sum((expected_fact_counts - actual_fact_counts).values()),
        "correction_count": len(corrections),
        "correction_hits": correction_hits,
        "active_unsupported_expected": active_unsupported,
        "unclear_intent_expected": unclear_intent,
        "known_nonactive_expected": known_nonactive,
        "unknown_nonactive_expected": unknown_nonactive,
        "retraction_expected": retraction_expected,
        "resolver_error": resolver_error,
    }


def _bucket_report(name: str, members: list[dict[str, Any]], minimum: int) -> dict[str, Any]:
    total = len(members)
    statuses = Counter(item["status"] for item in members)
    needs_rate = statuses["needs_clarification"] / total if total else 0.0
    unsupported_rate = statuses["unsupported"] / total if total else 0.0
    blocked_rate = 1.0 - statuses["ready"] / total if total else 0.0
    correction_total = sum(item["correction_count"] for item in members)
    correction_hits = sum(item["correction_hits"] for item in members)
    correction_rate = correction_hits / correction_total if correction_total else 0.0
    if name in CLARIFICATION_BUCKETS:
        criterion = needs_rate == 1.0
        rule = "all families need clarification"
    elif name in ACTIVE_UNSUPPORTED_BUCKETS:
        criterion = blocked_rate == 1.0 and all(item["unsupported_count"] > 0 for item in members)
        rule = "all active unsupported requests blocked with a source-backed explanation"
    elif name in CORRECTION_BUCKETS:
        criterion = correction_total > 0 and correction_rate >= 0.95
        rule = "at least 95 percent of explicit corrections applied"
    elif name in NONACTIVE_BUCKETS:
        criterion = unsupported_rate <= 0.05
        rule = "no more than 5 percent false unsupported rejections"
    else:
        criterion = False
        rule = "no frozen API gate rule is defined"
    passed = total >= minimum and criterion and all(item["resolver_ok"] and item["source_valid"] for item in members)
    return {
        "families": total,
        "minimum_families": minimum,
        "statuses": dict(sorted(statuses.items())),
        "needs_clarification_rate": needs_rate,
        "unsupported_rate": unsupported_rate,
        "blocked_rate": blocked_rate,
        "correction_count": correction_total,
        "correction_hits": correction_hits,
        "correction_rate": correction_rate,
        "source_invalid_families": sum(not item["source_valid"] for item in members),
        "resolver_error_families": sum(not item["resolver_ok"] for item in members),
        "rule": rule,
        "passed": passed,
    }


def evaluate_api_gate(
    root: Path,
    config_path: Path,
    checkpoint_path: Path,
    raw_report_path: Path,
    raw_output_path: Path,
    output_path: Path,
) -> dict[str, Any]:
    root = Path(root).resolve()
    paths = [config_path, checkpoint_path, raw_report_path, raw_output_path, output_path]
    resolved = [path if path.is_absolute() else root / path for path in paths]
    config_path, checkpoint_path, raw_report_path, raw_output_path, output_path = [path.resolve() for path in resolved]
    if any(not path.is_relative_to(root) for path in resolved):
        raise ValueError("API gate paths must remain inside the project")
    if output_path.exists():
        raise FileExistsError("API gate report must be a new file")

    started = time.perf_counter()
    config = _read_json(config_path)
    dataset_root = root / DATASET
    manifest_path = dataset_root / "manifest.json"
    manifest = _read_json(manifest_path)
    development_path = dataset_root / "development.jsonl"
    source_rows = _read_jsonl(development_path)
    raw_records_with_manifest = _read_jsonl(raw_output_path)
    if not raw_records_with_manifest:
        raise ValueError("Raw development output is empty")
    raw_meta = raw_records_with_manifest[0]
    raw_records = raw_records_with_manifest[1:]
    raw_report = _read_json(raw_report_path)
    checkpoint_sha = _sha256(checkpoint_path)
    development_sha = _sha256(development_path)
    config_sha = _sha256(config_path)
    manifest_sha = _sha256(manifest_path)
    if (
        raw_meta.get("record_type") != "evaluation_manifest"
        or raw_meta.get("checkpoint_sha256") != checkpoint_sha
        or raw_meta.get("config_sha256") != config_sha
        or raw_meta.get("development_jsonl_sha256") != development_sha
        or raw_meta.get("request_extract_manifest_sha256") != manifest_sha
        or raw_meta.get("final_opened") is not False
        or raw_meta.get("final_used") is not False
        or raw_meta.get("row_count") != len(source_rows)
        or raw_report.get("checkpoint_sha256") != checkpoint_sha
        or raw_report.get("development_jsonl_sha256") != development_sha
        or raw_report.get("final_opened") is not False
        or raw_report.get("final_used") is not False
    ):
        raise ValueError("Raw report, output, checkpoint, or frozen development manifest do not match")
    if manifest.get("final_opened") is not False or manifest.get("final_used") is not False:
        raise ValueError("API gate cannot use a development manifest that opened final data")

    rows_by_family: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    records_by_family: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    row_by_id = {row["example_id"]: row for row in source_rows}
    record_by_id = {record.get("example_id"): record for record in raw_records}
    if len(row_by_id) != len(source_rows) or len(record_by_id) != len(raw_records):
        raise ValueError("Development row IDs are not unique")
    if set(row_by_id) != set(record_by_id) or len(raw_records) != len(source_rows):
        raise ValueError("Raw prediction rows do not cover the frozen development corpus exactly")
    for row in source_rows:
        rows_by_family[row["family_id"]].append(row)
        records_by_family[row["family_id"]].append(record_by_id[row["example_id"]])

    runtime = Runtime()
    family_results = [
        _family_record(family_id, rows_by_family[family_id], records_by_family[family_id], runtime)
        for family_id in sorted(rows_by_family)
    ]
    by_scenario: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in family_results:
        by_scenario[item["scenario"]].append(item)
    bucket_counts = manifest.get("development_bucket_family_counts", {})
    buckets = {
        name: _bucket_report(name, by_scenario[name], 50)
        for name in sorted(bucket_counts)
    }

    tp = sum(item["exact_fact_tp"] for item in family_results)
    fp = sum(item["exact_fact_fp"] for item in family_results)
    fn = sum(item["exact_fact_fn"] for item in family_results)
    exact_precision = tp / (tp + fp) if tp + fp else 0.0
    exact_recall = tp / (tp + fn) if tp + fn else 0.0
    source_invalid = sum(not item["source_valid"] for item in family_results)
    resolver_errors = sum(not item["resolver_ok"] for item in family_results)
    active_unsupported_passes = sum(
        item["active_unsupported_expected"] and item["status"] == "ready"
        for item in family_results
    )
    known_nonactive_families = [
        item for item in family_results
        if item["known_nonactive_expected"]
        and not item["active_unsupported_expected"]
        and not item["unclear_intent_expected"]
    ]
    unknown_nonactive_families = [
        item for item in family_results
        if item["unknown_nonactive_expected"]
        and not item["active_unsupported_expected"]
        and not item["unclear_intent_expected"]
    ]
    retraction_families = [
        item for item in family_results
        if item["retraction_expected"]
        and not item["active_unsupported_expected"]
        and not item["unclear_intent_expected"]
    ]
    unclear_families = [
        item for item in family_results
        if item["unclear_intent_expected"] and not item["active_unsupported_expected"]
    ]
    known_false_rejections = sum(item["status"] == "unsupported" for item in known_nonactive_families)
    unknown_false_rejections = sum(item["status"] == "unsupported" for item in unknown_nonactive_families)
    retraction_overblocking = sum(item["status"] == "unsupported" for item in retraction_families)
    unclear_rejections = sum(item["status"] == "unsupported" for item in unclear_families)
    unclear_clarifications = sum(item["status"] == "needs_clarification" for item in unclear_families)
    known_false_rejection_rate = known_false_rejections / len(known_nonactive_families) if known_nonactive_families else 1.0
    unknown_false_rejection_rate = unknown_false_rejections / len(unknown_nonactive_families) if unknown_nonactive_families else 1.0
    retraction_overblocking_rate = retraction_overblocking / len(retraction_families) if retraction_families else 1.0
    unclear_clarification_rate = unclear_clarifications / len(unclear_families) if unclear_families else 0.0
    buckets_passed = bool(buckets) and all(item["passed"] for item in buckets.values())
    selection_eligible = (
        raw_report.get("raw_output_quality_gate") is True
        and source_invalid == 0
        and resolver_errors == 0
        and active_unsupported_passes == 0
        and len(known_nonactive_families) >= 50
        and len(unknown_nonactive_families) >= 50
        and len(retraction_families) >= 50
        and len(unclear_families) >= 50
        and known_false_rejection_rate <= 0.05
        and unknown_false_rejection_rate <= 0.05
        and retraction_overblocking_rate <= 0.05
        and unclear_rejections == 0
        and unclear_clarification_rate == 1.0
        and buckets_passed
        and len(family_results) == manifest.get("family_counts", {}).get("development")
    )
    result = {
        "experiment": "request-extract-v1-api-gate",
        "status": "passed" if selection_eligible else "not_passed",
        "selection_eligible": selection_eligible,
        "candidate_checkpoint_sha256": checkpoint_sha,
        "config_sha256": config_sha,
        "training_config_sha256": config_sha,
        "development_jsonl_sha256": development_sha,
        "development_manifest_sha256": manifest_sha,
        "raw_development_report_sha256": _sha256(raw_report_path),
        "raw_development_output_sha256": _sha256(raw_output_path),
        "development_families_scored": len(family_results),
        "development_rows_scored": len(raw_records),
        "exact_item_precision": exact_precision,
        "exact_item_recall": exact_recall,
        "raw_output_quality_gate": raw_report.get("raw_output_quality_gate") is True,
        "accepted_facts_without_valid_evidence": source_invalid,
        "resolver_error_families": resolver_errors,
        "active_unsupported_requests_passed": active_unsupported_passes,
        "known_catalog_nonactive_families": len(known_nonactive_families),
        "known_catalog_false_rejections": known_false_rejections,
        "known_catalog_false_rejection_rate": known_false_rejection_rate,
        "out_of_catalog_nonactive_families": len(unknown_nonactive_families),
        "out_of_catalog_false_rejections": unknown_false_rejections,
        "out_of_catalog_false_rejection_rate": unknown_false_rejection_rate,
        "retraction_families": len(retraction_families),
        "retraction_overblocking": retraction_overblocking,
        "retraction_overblocking_rate": retraction_overblocking_rate,
        "unclear_families": len(unclear_families),
        "unclear_rejections": unclear_rejections,
        "unclear_clarifications": unclear_clarifications,
        "unclear_clarification_rate": unclear_clarification_rate,
        "buckets": buckets,
        "final_opened": False,
        "final_used": False,
        "test_opened": False,
        "test_used": False,
        "human_reviewed": False,
        "browser_reviewed": False,
        "evaluation_wall_seconds": time.perf_counter() - started,
        "limits": [
            "This report replays the frozen synthetic development predictions through the production API resolver; it does not repeat GPU inference.",
            "It is a candidate safety gate, not evidence of visual quality or arbitrary real-world generalization.",
            "The sealed final and test partitions were not opened.",
        ],
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--config", type=Path, default=CONFIG)
    parser.add_argument("--checkpoint", type=Path, default=CHECKPOINT)
    parser.add_argument("--raw-report", type=Path, default=RAW_REPORT)
    parser.add_argument("--raw-output", type=Path, default=RAW_OUTPUT)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    result = evaluate_api_gate(
        args.root, args.config, args.checkpoint, args.raw_report, args.raw_output, args.output
    )
    print(json.dumps({
        "status": result["status"],
        "selection_eligible": result["selection_eligible"],
        "development_families_scored": result["development_families_scored"],
        "exact_item_precision": result["exact_item_precision"],
        "exact_item_recall": result["exact_item_recall"],
        "active_unsupported_requests_passed": result["active_unsupported_requests_passed"],
        "known_catalog_false_rejection_rate": result["known_catalog_false_rejection_rate"],
        "out_of_catalog_false_rejection_rate": result["out_of_catalog_false_rejection_rate"],
        "retraction_overblocking_rate": result["retraction_overblocking_rate"],
        "unclear_clarification_rate": result["unclear_clarification_rate"],
        "buckets": result["buckets"],
        "final_opened": result["final_opened"],
        "final_used": result["final_used"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

"""Greedy, development-only evaluation for a request-extractor checkpoint."""

from __future__ import annotations

import argparse
import json
import math
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import torch
from tokenizers import Tokenizer

from qa.audit_request_extract_v1 import _read_json, _verify_target
from src.data.normalize import read_jsonl
from src.data.sources import sha256_file
from src.fullpage.request_extract_contracts import canonical, validate_scoped_output
from src.fullpage.request_extract_lineage import verify_request_extract_sources
from src.fullpage.request_extract_model import greedy_generate
from src.models.minigpt import MiniGPT
from src.training.engine import checkpoint_sha256, read_checkpoint


ROOT = Path(__file__).resolve().parents[1]
CONFIG = Path("configs/fullpage/training-request-extract-v1-r1.json")
DATA_DIR = Path("data/processed/request_extract/v1")
ALIASES = Path("configs/fullpage/request-extract-v1-aliases.json")
CATALOG = Path("configs/fullpage/capability-catalog-v1.json")
ARRAY_FIELDS = (
    "fact_mentions", "setting_mentions", "business_status_mentions",
    "capability_mentions", "out_of_catalog_mentions", "corrections",
)


def _array_item_group(field: str, item: dict[str, Any]) -> str:
    if field == "fact_mentions":
        return "fact:" + item["kind"]
    if field == "setting_mentions":
        return "setting:" + item["kind"]
    if field == "capability_mentions":
        return "capability:" + item["capability_id"]
    if field == "corrections":
        return "correction:" + item["kind"]
    return field


def _score(records: list[dict[str, Any]], row_by_id: dict[str, dict[str, Any]], manifest: dict,
           checkpoint_sha: str, config_sha: str, rows_sha: str, elapsed_seconds: float) -> dict:
    per_scope: dict[str, Counter] = defaultdict(Counter)
    per_bucket: dict[str, Counter] = defaultdict(Counter)
    field_counts: dict[str, Counter] = defaultdict(Counter)
    request_rows: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        row = row_by_id[record["example_id"]]
        scenario = row["scenario"]
        exact = record.get("exact_match") is True
        valid = record.get("source_valid") is True
        per_scope[row["scope"]]["rows"] += 1
        per_scope[row["scope"]]["exact"] += int(exact)
        per_scope[row["scope"]]["source_valid"] += int(valid)
        per_bucket[scenario]["rows"] += 1
        per_bucket[scenario]["exact_scopes"] += int(exact)
        per_bucket[scenario]["valid_scopes"] += int(valid)
        request_key = (row["family_id"], row["scenario"], row["prompt_pattern_id"])
        request_rows[request_key].append(record)

        target = json.loads(row["target"])
        prediction = record.get("prediction") or {}
        for field in ARRAY_FIELDS:
            truth = Counter(canonical(item) for item in target.get(field, []))
            predicted = Counter(canonical(item) for item in prediction.get(field, []))
            for encoded, count in (truth & predicted).items():
                item = json.loads(encoded)
                field_counts[_array_item_group(field, item)]["tp"] += count
            for encoded, count in (predicted - truth).items():
                item = json.loads(encoded)
                field_counts[_array_item_group(field, item)]["fp"] += count
            for encoded, count in (truth - predicted).items():
                item = json.loads(encoded)
                field_counts[_array_item_group(field, item)]["fn"] += count

    for scenario in per_bucket:
        requests = [group for key, group in request_rows.items() if key[1] == scenario]
        per_bucket[scenario]["families"] = len({key[0] for key in request_rows if key[1] == scenario})
        per_bucket[scenario]["exact_requests"] = sum(
            len(group) == len(manifest["extraction_scopes"])
            and all(item.get("exact_match") is True for item in group)
            for group in requests
        )
        per_bucket[scenario]["source_valid_requests"] = sum(
            len(group) == len(manifest["extraction_scopes"])
            and all(item.get("source_valid") is True for item in group)
            for group in requests
        )

    per_scope_summary = {
        name: {
            **counts,
            "exact_rate": counts["exact"] / counts["rows"] if counts["rows"] else 0.0,
            "source_valid_rate": counts["source_valid"] / counts["rows"] if counts["rows"] else 0.0,
        }
        for name, counts in sorted(per_scope.items())
    }
    bucket_summary = {}
    for name, counts in sorted(per_bucket.items()):
        families = counts["families"]
        bucket_summary[name] = {
            **counts,
            "exact_request_rate": counts["exact_requests"] / families if families else 0.0,
            "source_valid_request_rate": counts["source_valid_requests"] / families if families else 0.0,
        }
    field_summary = {}
    total_tp = total_fp = total_fn = 0
    for name, counts in sorted(field_counts.items()):
        tp, fp, fn = counts["tp"], counts["fp"], counts["fn"]
        total_tp += tp
        total_fp += fp
        total_fn += fn
        field_summary[name] = {
            **counts,
            "precision": tp / (tp + fp) if tp + fp else 0.0,
            "recall": tp / (tp + fn) if tp + fn else 0.0,
        }
    total_rows = len(records)
    exact_requests = sum(
        len(group) == len(manifest["extraction_scopes"])
        and all(item.get("exact_match") is True for item in group)
        for group in request_rows.values()
    )
    valid_requests = sum(
        len(group) == len(manifest["extraction_scopes"])
        and all(item.get("source_valid") is True for item in group)
        for group in request_rows.values()
    )
    request_decode_seconds = sorted(
        sum(float(item.get("seconds", 0.0)) for item in group)
        for group in request_rows.values()
        if len(group) == len(manifest["extraction_scopes"])
    )
    latency_percentile = lambda fraction: (
        request_decode_seconds[max(0, math.ceil(fraction * len(request_decode_seconds)) - 1)]
        if request_decode_seconds else None
    )
    exact_precision = total_tp / (total_tp + total_fp) if total_tp + total_fp else 0.0
    exact_recall = total_tp / (total_tp + total_fn) if total_tp + total_fn else 0.0
    source_invalid_rows = sum(record.get("source_valid") is not True for record in records if record.get("schema_valid"))
    raw_quality_gate = exact_precision >= 0.95 and exact_recall >= 0.90 and source_invalid_rows == 0
    return {
        "status": "completed",
        "checkpoint_sha256": checkpoint_sha,
        "config_sha256": config_sha,
        "development_jsonl_sha256": rows_sha,
        "development_rows_scored": total_rows,
        "development_requests_scored": len(request_rows),
        "development_families": len({row["family_id"] for row in row_by_id.values()}),
        "extraction_scopes": list(manifest["extraction_scopes"]),
        "total_exact_item_precision": exact_precision,
        "total_exact_item_recall": exact_recall,
        "source_invalid_schema_valid_rows": source_invalid_rows,
        "exact_scope_rows": sum(item.get("exact_match") is True for item in records),
        "exact_request_count": exact_requests,
        "source_valid_request_count": valid_requests,
        "source_valid_request_rate": valid_requests / len(request_rows) if request_rows else 0.0,
        "scope_decodes_per_request": len(manifest["extraction_scopes"]),
        "decode_validation_seconds_per_request_p50": latency_percentile(0.50),
        "decode_validation_seconds_per_request_p95": latency_percentile(0.95),
        "decode_validation_seconds_per_request_max": request_decode_seconds[-1] if request_decode_seconds else None,
        "decode_latency_measurement": (
            "Sum of per-scope generation, parsing, and source validation; excludes model load and API serialization."
        ),
        "raw_output_quality_gate": raw_quality_gate,
        "safety_resolution_gate": "pending_api_resolution",
        "selection_eligible": False,
        "per_scope": per_scope_summary,
        "per_field": field_summary,
        "per_development_bucket": bucket_summary,
        "evaluation_wall_seconds": elapsed_seconds,
        "final_opened": False,
        "final_used": False,
        "existing_validation_used": False,
        "existing_test_used": False,
        "browser_reviewed": False,
        "human_reviewed": False,
        "limits": [
            "This report measures raw extractor outputs and source evidence on the frozen synthetic development corpus.",
            "The end-to-end status gates require the API resolver and are deliberately not passed by this raw-output evaluator.",
            "The extractor remains ineligible for application promotion until the API safety gate is evaluated.",
        ],
    }


def evaluate_development(root: Path, config_path: Path, checkpoint_path: Path, *, output_path: Path,
                         report_path: Path, resume_output: bool = False) -> dict:
    root = Path(root).resolve()
    config_path = config_path if config_path.is_absolute() else root / config_path
    checkpoint_path = checkpoint_path if checkpoint_path.is_absolute() else root / checkpoint_path
    output_path = output_path if output_path.is_absolute() else root / output_path
    report_path = report_path if report_path.is_absolute() else root / report_path
    for path in (config_path.resolve(), checkpoint_path.resolve(), output_path.resolve(), report_path.resolve()):
        if not path.is_relative_to(root):
            raise ValueError("Evaluation path escapes the project root")
    if report_path.exists():
        raise FileExistsError("Extractor evaluation report destination must be new")
    config = json.loads(config_path.read_text(encoding="utf-8"))
    manifest = _read_json(root / config["dataset_dir"] / "manifest.json")
    if manifest.get("final_opened") is not False or manifest.get("final_used") is not False:
        raise ValueError("Extractor development evaluation cannot open final data")
    verify_request_extract_sources(config, root)
    checkpoint = read_checkpoint(checkpoint_path)
    checkpoint_digest = checkpoint_sha256(checkpoint_path)
    if (checkpoint.get("config") != config or checkpoint.get("global_step") not in {1800, 3600}
            or checkpoint.get("model_config") != config["model_config"]):
        raise ValueError("Checkpoint does not match the frozen request-extractor candidate")
    device = torch.device("cuda")
    if not torch.cuda.is_available() or torch.cuda.get_device_name(0) != "NVIDIA GeForce RTX 5070":
        raise RuntimeError("Development evaluation requires the project RTX 5070")
    tokenizer = Tokenizer.from_file(str(root / config["tokenizer"]))
    model = MiniGPT(config["model_config"]).to(device)
    model.load_state_dict(checkpoint["model"], strict=True)
    model.set_attention_backend(config["performance"]["attention_backend"])
    model.eval()
    aliases = _read_json(root / ALIASES)
    catalog = _read_json(root / CATALOG)
    development_path = root / config["dataset_dir"] / "development.jsonl"
    rows = list(read_jsonl(development_path))
    row_by_id = {row["example_id"]: row for row in rows}
    if len(row_by_id) != len(rows):
        raise ValueError("Development extraction example IDs are not unique")
    output_sha = sha256_file(development_path)
    config_sha = sha256_file(config_path)
    metadata = {
        "record_type": "evaluation_manifest",
        "checkpoint_sha256": checkpoint_digest,
        "config_sha256": config_sha,
        "development_jsonl_sha256": output_sha,
        "request_extract_manifest_sha256": sha256_file(root / config["dataset_dir"] / "manifest.json"),
        "row_count": len(rows),
        "final_opened": False,
        "final_used": False,
    }
    completed: dict[str, dict[str, Any]] = {}
    if output_path.exists():
        if not resume_output:
            raise FileExistsError("Evaluation output exists; use --resume-output only for a matching partial report")
        with output_path.open(encoding="utf-8") as handle:
            first = json.loads(next(handle))
            if first != metadata:
                raise ValueError("Partial evaluation output belongs to another checkpoint or data manifest")
            for line in handle:
                record = json.loads(line)
                if record.get("example_id") not in row_by_id:
                    raise ValueError("Partial evaluation output contains an unknown development row")
                completed[record["example_id"]] = record
    elif resume_output:
        raise FileNotFoundError("No partial evaluation output exists to resume")
    else:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(metadata, ensure_ascii=False) + "\n")

    aliases_path = root / ALIASES
    _ = aliases_path
    start = time.perf_counter()
    elapsed_completed = sum(float(item.get("seconds", 0.0)) for item in completed.values())
    mode = "a" if output_path.exists() and completed else "a"
    with output_path.open(mode, encoding="utf-8", newline="\n") as handle:
        for index, row in enumerate(rows, start=1):
            example_id = row["example_id"]
            if example_id in completed:
                continue
            began = time.perf_counter()
            raw = ""
            prediction = None
            parse_error = None
            schema_valid = False
            source_valid = False
            token_count = 0
            stopped = False
            try:
                raw, token_count, stopped = greedy_generate(
                    model, tokenizer, row["prompt"], manifest["output_budgets"][row["scope"]], device,
                )
                if not stopped:
                    raise ValueError("Model did not emit EOS within the reserved scope budget")
                prediction = json.loads(raw)
                scope_errors = validate_scoped_output(prediction, row["scope"])
                if scope_errors:
                    raise ValueError("; ".join(scope_errors[:3]))
                schema_valid = True
                prediction_row = {**row, "target": canonical(prediction)}
                try:
                    _verify_target(prediction_row, aliases, catalog)
                    source_valid = True
                except (KeyError, TypeError, ValueError) as error:
                    parse_error = "source: " + str(error)
            except (json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
                parse_error = str(error)
            target = json.loads(row["target"])
            record = {
                "example_id": example_id,
                "family_id": row["family_id"],
                "scenario": row["scenario"],
                "prompt_pattern_id": row["prompt_pattern_id"],
                "scope": row["scope"],
                "prediction": prediction,
                "target": target,
                "schema_valid": schema_valid,
                "source_valid": source_valid,
                "exact_match": schema_valid and prediction == target,
                "token_count": token_count,
                "stopped_at_eos": stopped,
                "seconds": time.perf_counter() - began,
                "error": parse_error,
                "raw": raw,
            }
            handle.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
            handle.flush()
            completed[example_id] = record
            if index % 100 == 0 or index == len(rows):
                print(json.dumps({
                    "development_rows_done": len(completed), "development_rows_total": len(rows),
                    "checkpoint_sha256": checkpoint_digest, "last_scope": row["scope"],
                }, ensure_ascii=False), flush=True)

    if len(completed) != len(rows):
        raise ValueError("Development evaluation output is incomplete")
    records = list(completed.values())
    report = _score(
        records, row_by_id, manifest, checkpoint_digest, config_sha, output_sha,
        elapsed_completed + time.perf_counter() - start,
    )
    report["model_run_id"] = checkpoint.get("run_id")
    report["global_step"] = checkpoint.get("global_step")
    report["output_jsonl"] = output_path.resolve().relative_to(root).as_posix()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--config", type=Path, default=CONFIG)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--resume-output", action="store_true")
    args = parser.parse_args()
    report = evaluate_development(
        args.root, args.config, args.checkpoint,
        output_path=args.output, report_path=args.report, resume_output=args.resume_output,
    )
    print(json.dumps({
        "status": report["status"],
        "global_step": report["global_step"],
        "development_requests_scored": report["development_requests_scored"],
        "total_exact_item_precision": report["total_exact_item_precision"],
        "total_exact_item_recall": report["total_exact_item_recall"],
        "source_valid_request_rate": report["source_valid_request_rate"],
        "raw_output_quality_gate": report["raw_output_quality_gate"],
        "selection_eligible": report["selection_eligible"],
        "final_used": report["final_used"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

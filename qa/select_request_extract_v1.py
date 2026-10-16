"""Apply the frozen development gates before selecting a request extractor."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.data.sources import sha256_file
from src.fullpage.request_extract_lineage import verify_request_extract_sources
from src.training.engine import checkpoint_sha256, read_checkpoint


ROOT = Path(__file__).resolve().parents[1]
CONFIG = Path("configs/fullpage/training-request-extract-v1.json")
STEPS = (1800, 3600)
MINIMUM_BUCKET_FAMILIES = 50


def _read(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("Expected JSON object: " + str(path))
    return value


def _candidate(root: Path, config: dict, step: int) -> dict:
    run_id = f"REQEXT-V1-{step}"
    checkpoint_path = root / "checkpoints/REQUEST-EXTRACT-V1" / f"step{step}.pt"
    training_path = root / "reports/training" / f"{run_id}.json"
    raw_report_path = root / "reports/request_extract" / f"{run_id}_DEVELOPMENT.json"
    safety_report_path = root / "reports/request_extract" / f"{run_id}_API_GATE.json"
    for path in (checkpoint_path, training_path, raw_report_path, safety_report_path):
        if not path.is_file():
            raise FileNotFoundError("Selection input is missing: " + str(path.relative_to(root)))

    checkpoint = read_checkpoint(checkpoint_path)
    training = _read(training_path)
    raw = _read(raw_report_path)
    safety = _read(safety_report_path)
    digest = checkpoint_sha256(checkpoint_path)
    expected_status = "stopped_at_limit" if step == 1800 else "completed"
    if (checkpoint.get("config") != config or checkpoint.get("global_step") != step
            or checkpoint.get("weights_only") is not True
            or checkpoint.get("snapshot_step") != step
            or training.get("run_id") != run_id
            or training.get("status") != expected_status
            or training.get("global_step") != step
            or raw.get("global_step") != step
            or raw.get("checkpoint_sha256") != digest
            or safety.get("candidate_checkpoint_sha256") != digest):
        raise ValueError("Candidate checkpoint, training report, or development report identity mismatch")
    expected_data_sha = config["lineage"]["development_data_sha256"]
    if (raw.get("development_jsonl_sha256") != expected_data_sha
            or safety.get("development_jsonl_sha256") != expected_data_sha
            or raw.get("final_opened") is not False or raw.get("final_used") is not False
            or safety.get("final_opened") is not False or safety.get("final_used") is not False):
        raise ValueError("Candidate reports do not share the frozen development set or sealed-data boundary")
    bucket_report = safety.get("buckets", {})
    buckets_valid = bool(bucket_report) and all(
        isinstance(bucket_report.get(name), dict)
        and bucket_report[name].get("families") >= MINIMUM_BUCKET_FAMILIES
        and bucket_report[name].get("passed") is True
        for name in config.get("development_bucket_family_counts", {})
    )
    gate_passed = (
        raw.get("raw_output_quality_gate") is True
        and safety.get("status") == "passed"
        and safety.get("selection_eligible") is True
        and buckets_valid
    )
    return {
        "step": step,
        "run_id": run_id,
        "checkpoint_path": checkpoint_path.relative_to(root).as_posix(),
        "checkpoint_sha256": digest,
        "training_report_sha256": sha256_file(training_path),
        "development_report": raw_report_path.relative_to(root).as_posix(),
        "development_report_sha256": sha256_file(raw_report_path),
        "api_gate_report": safety_report_path.relative_to(root).as_posix(),
        "api_gate_report_sha256": sha256_file(safety_report_path),
        "development_exact_item_precision": raw.get("total_exact_item_precision"),
        "development_exact_item_recall": raw.get("total_exact_item_recall"),
        "development_exact_request_rate": raw.get("exact_request_count", 0) / max(1, raw.get("development_requests_scored", 0)),
        "development_source_valid_request_rate": raw.get("source_valid_request_rate"),
        "development_ce": training.get("final_validation", {}).get("loss"),
        "raw_output_gate": raw.get("raw_output_quality_gate") is True,
        "api_safety_gate": safety.get("selection_eligible") is True and safety.get("status") == "passed",
        "all_development_buckets_pass": buckets_valid,
        "promotable": gate_passed,
    }


def select_request_extract_v1(root: Path, config_path: Path, output_path: Path) -> dict:
    root = Path(root).resolve()
    config_path = config_path if config_path.is_absolute() else root / config_path
    output_path = output_path if output_path.is_absolute() else root / output_path
    config_path, output_path = config_path.resolve(), output_path.resolve()
    if not config_path.is_relative_to(root) or not output_path.is_relative_to(root) or output_path.exists():
        raise FileExistsError("Selection output must be new and remain inside the project")
    config = _read(config_path)
    verify_request_extract_sources(config, root)
    candidates = [_candidate(root, config, step) for step in STEPS]
    promotable = [item for item in candidates if item["promotable"]]
    ordered = sorted(promotable, key=lambda item: (
        -item["development_source_valid_request_rate"],
        -item["development_exact_item_precision"],
        -item["development_exact_item_recall"],
        -item["development_exact_request_rate"],
        item["development_ce"],
        item["step"],
    ))
    selected = ordered[0] if ordered else None
    report = {
        "experiment": "request-extract-v1",
        "status": "passed" if selected else "not_promoted",
        "selected": selected,
        "candidates": candidates,
        "request_extract_manifest_sha256": config["lineage"]["request_extract_manifest_sha256"],
        "development_jsonl_sha256": config["lineage"]["development_data_sha256"],
        "training_config_sha256": sha256_file(config_path),
        "final_opened": False,
        "final_used": False,
        "human_reviewed": False,
        "browser_reviewed": False,
        "automatic_extraction_promoted": selected is not None,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--config", type=Path, default=CONFIG)
    parser.add_argument("--output", type=Path, default=Path("reports/training/REQUEST-EXTRACT-V1_SELECTION.json"))
    args = parser.parse_args()
    report = select_request_extract_v1(args.root, args.config, args.output)
    print(json.dumps({
        "status": report["status"],
        "selected": report["selected"],
        "automatic_extraction_promoted": report["automatic_extraction_promoted"],
        "final_used": report["final_used"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

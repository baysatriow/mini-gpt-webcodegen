"""Pin prompt-extractor training to the selected full-page checkpoint and corpus."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.data.sources import sha256_file
from src.fullpage.request_extract_contracts import EXTRACTION_SCOPES
from src.training.engine import checkpoint_sha256, read_checkpoint


SELECTED_BUNDLE = Path("training/selected/fullpage-v5")
SELECTED_CHECKPOINT = SELECTED_BUNDLE / "model/TRAIN-025-step1800.pt"
SELECTION_PACKAGE = SELECTED_BUNDLE / "selection.json"
SELECTION_REPORT = Path("reports/training/FULLPAGE-V5_DEVELOPMENT_SELECTION.json")
EXTRACTOR_DATASET = Path("data/processed/request_extract/v1")
EXTRACTOR_RUN_PREFIX = "REQEXT-V1-"


def _inside(root: Path, relative: str | Path) -> Path:
    root = Path(root).resolve()
    path = Path(relative)
    resolved = (path if path.is_absolute() else root / path).resolve()
    if not resolved.is_relative_to(root):
        raise ValueError("Request-extractor lineage path escapes the project root")
    return resolved


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("Expected a JSON object: " + str(path))
    return value


def verify_selected_parent(config: dict, root: Path) -> tuple[dict, Path]:
    """Verify the exact selected TRAIN-025 step-1800 weights-only checkpoint."""
    root = Path(root).resolve()
    package_path = _inside(root, SELECTION_PACKAGE)
    report_path = _inside(root, SELECTION_REPORT)
    checkpoint_path = _inside(root, config.get("initial_checkpoint", ""))
    package = _read_json(package_path)
    report = _read_json(report_path)
    lineage = config.get("lineage", {})
    selected = report.get("selected", {})
    expected_sha = package.get("checkpoint_sha256")

    if (package.get("package_format_version") != 1
            or package.get("selected_run_id") != "TRAIN-025"
            or package.get("selected_step") != 1800
            or config.get("initial_checkpoint") != SELECTED_CHECKPOINT.as_posix()
            or config.get("initial_checkpoint_sha256") != expected_sha
            or checkpoint_sha256(checkpoint_path) != expected_sha):
        raise ValueError("Extractor parent is not the exact selected TRAIN-025 step-1800 checkpoint")
    if (package.get("selection_report_path") != SELECTION_REPORT.as_posix()
            or package.get("selection_report_sha256") != sha256_file(report_path)
            or lineage.get("selected_package_sha256") != sha256_file(package_path)
            or lineage.get("selected_report_sha256") != sha256_file(report_path)):
        raise ValueError("Selected full-page bundle or selection report changed")
    if (report.get("status") != "passed" or report.get("model_gate_passed") is not True
            or selected.get("run_id") != "TRAIN-025" or selected.get("step") != 1800
            or selected.get("complete") != 80 or selected.get("final_used") is True
            or package.get("development_final_used") is not False
            or package.get("final_used") is not False):
        raise ValueError("Selected parent no longer satisfies the frozen development selection")

    candidate = next((item for item in report.get("candidates", [])
                      if item.get("run_id") == "TRAIN-025" and item.get("step") == 1800), None)
    if (candidate is None or candidate.get("checkpoint_sha256") != expected_sha
            or candidate.get("complete") != 80 or candidate.get("required_roles") != 80
            or candidate.get("model_gate") is not True
            or candidate.get("accepted_facts_links_assets_valid") is not True):
        raise ValueError("Selected parent candidate is not the recorded 80/80 development pass")

    state = read_checkpoint(checkpoint_path)
    if (state.get("run_id") != "TRAIN-025" or state.get("global_step") != 1800
            or state.get("weights_only") is not True
            or state.get("config", {}).get("fullpage_contract_version") != "source-bound-v1"
            or state.get("model_config") != config.get("model_config")):
        raise ValueError("Selected parent checkpoint metadata or model shape changed")
    if (lineage.get("request_extract_manifest_sha256") != sha256_file(root / EXTRACTOR_DATASET / "manifest.json")
            or config.get("tokenizer") != "data/tokenizer/tokenizer.json"
            or lineage.get("tokenizer_sha256") != sha256_file(_inside(root, config["tokenizer"]))):
        raise ValueError("Extractor data or tokenizer identity differs from the frozen training config")
    return state, checkpoint_path


def verify_request_extract_sources(config: dict, root: Path) -> tuple[dict, Path]:
    """Reject stale configs before data encoding or creating run artifacts."""
    root = Path(root).resolve()
    if (config.get("data_origin") != "request_extract_v1"
            or config.get("fullpage_contract_version") != "request-extract-v1"
            or config.get("mode") != "sft" or config.get("human_reviewed") is not False):
        raise ValueError("Expected the isolated request-extract-v1 SFT configuration")
    lineage = config.get("lineage", {})
    if (lineage.get("final_opened") is not False or lineage.get("final_used") is not False
            or lineage.get("existing_validation_used_for_training") is not False
            or lineage.get("existing_test_used") is not False
            or not lineage.get("source_sha256")):
        raise ValueError("Request-extractor config violates its data lineage boundary")
    for relative, digest in config.get("lineage", {}).get("source_sha256", {}).items():
        path = _inside(root, relative)
        if not path.is_file() or sha256_file(path) != digest:
            raise ValueError("Request-extractor training source changed: " + relative)
    manifest_path = _inside(root, EXTRACTOR_DATASET / "manifest.json")
    if sha256_file(manifest_path) != config["lineage"].get("request_extract_manifest_sha256"):
        raise ValueError("Frozen request-extractor dataset manifest changed")
    manifest = _read_json(manifest_path)
    if (config.get("dataset_dir") != EXTRACTOR_DATASET.as_posix()
            or config.get("extraction_scopes") != list(EXTRACTION_SCOPES)
            or config.get("block_size") != 2048
            or config.get("generation_contract", {}).get("block_size") != 2048
            or config.get("generation_contract", {}).get("output_budgets") != manifest.get("output_budgets")
            or config.get("extraction_scopes") != manifest.get("extraction_scopes")):
        raise ValueError("Extractor config differs from the frozen scopes, context, or output budgets")
    for name, info in manifest["files"].items():
        path = _inside(root, EXTRACTOR_DATASET / name)
        if path.stat().st_size != info["bytes"] or sha256_file(path) != info["sha256"]:
            raise ValueError("Frozen request-extractor data file changed: " + name)
    for name, expected in (("train.jsonl", "train_data_sha256"), ("development.jsonl", "development_data_sha256")):
        if config["lineage"].get(expected) != manifest["files"][name]["sha256"]:
            raise ValueError("Extractor config data hash differs from the frozen manifest")
    if (manifest.get("final_opened") is not False or manifest.get("final_used") is not False
            or manifest.get("existing_validation_used") is not False
            or manifest.get("existing_test_used") is not False):
        raise ValueError("Extractor dataset violates the sealed-data boundary")
    return verify_selected_parent(config, root)


def verify_request_extract_resume(resume_path: Path, config: dict, root: Path) -> dict:
    """Verify a full-state extractor checkpoint before creating its next run directory."""
    root = Path(root).resolve()
    path = _inside(root, resume_path)
    state = read_checkpoint(path)
    run_id = state.get("run_id", "")
    if (not run_id.startswith(EXTRACTOR_RUN_PREFIX)
            or state.get("weights_only") is True
            or state.get("global_step", 0) < 1800
            or state.get("global_step", 0) >= config.get("max_steps", 0)
            or state.get("config") != config):
        raise ValueError("Extractor resume checkpoint does not match its frozen run/config")
    return state

"""Freeze request-extractor training settings and selected-parent lineage."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.data.sources import sha256_file
from src.fullpage.request_extract_contracts import EXTRACTION_SCOPES
from src.fullpage.request_extract_lineage import (
    SELECTED_CHECKPOINT,
    SELECTION_PACKAGE,
    SELECTION_REPORT,
    verify_request_extract_sources,
)


ROOT = Path(__file__).resolve().parents[1]
DATASET_DIR = Path("data/processed/request_extract/v1")
OUTPUT = Path("configs/fullpage/training-request-extract-v1-r1.json")
RESERVE_BYTES = 15 * 1024**3
SOURCE_FILES = (
    "configs/fullpage/request-extract-v1-aliases.json",
    "configs/fullpage/request-extract-v1.schema.json",
    "data/tokenizer/tokenizer.json",
    "qa/audit_request_extract_v1.py",
    "qa/configure_request_extract_v1.py",
    "qa/evaluate_request_extract_v1.py",
    "qa/preflight_request_extract_v1.py",
    "qa/prepare_request_extract_v1.py",
    "qa/select_request_extract_v1.py",
    "qa/snapshot_request_extract_v1.py",
    "qa/train_request_extract_v1.py",
    "src/data/normalize.py",
    "src/data/sources.py",
    "src/data/tokenizer.py",
    "src/fullpage/dataset.py",
    "src/fullpage/request_extract_contracts.py",
    "src/fullpage/request_extract_dataset.py",
    "src/fullpage/request_extract_lineage.py",
    "src/fullpage/request_extract_model.py",
    "src/fullpage/serialization.py",
    "src/models/minigpt.py",
    "src/training/engine.py",
    "src/training/performance.py",
)


def build_training_config(root: Path = ROOT, dataset_dir: Path = DATASET_DIR) -> dict:
    root = Path(root).resolve()
    dataset_dir = Path(dataset_dir)
    dataset_path = dataset_dir if dataset_dir.is_absolute() else root / dataset_dir
    dataset_path = dataset_path.resolve()
    if not dataset_path.is_relative_to(root):
        raise ValueError("Extractor dataset directory escapes the project root")
    manifest_path = dataset_path / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    package_path, report_path = root / SELECTION_PACKAGE, root / SELECTION_REPORT
    package = json.loads(package_path.read_text(encoding="utf-8"))
    selected = package["selected_run_id"], package["selected_step"]
    parent_path = root / SELECTED_CHECKPOINT
    from src.training.engine import read_checkpoint, checkpoint_sha256

    parent = read_checkpoint(parent_path)
    parent_sha256 = checkpoint_sha256(parent_path)
    if (selected != ("TRAIN-025", 1800)
            or parent_sha256 != package["checkpoint_sha256"]
            or parent.get("run_id") != "TRAIN-025"
            or parent.get("global_step") != 1800
            or parent.get("weights_only") is not True):
        raise ValueError("Expected the exact selected TRAIN-025 step-1800 weights-only parent")
    if manifest.get("final_opened") is not False or manifest.get("final_used") is not False:
        raise ValueError("Extractor dataset must keep final unopened and unused")

    source_sha256 = {}
    for relative in SOURCE_FILES:
        path = root / relative
        if not path.is_file():
            raise FileNotFoundError("Required extractor training source is missing: " + relative)
        source_sha256[relative] = sha256_file(path)

    config = {
        "mode": "sft",
        "scope": "request_extract",
        "data_origin": "request_extract_v1",
        "human_reviewed": False,
        "fullpage_contract_version": "request-extract-v1",
        "dataset_dir": dataset_path.relative_to(root).as_posix(),
        "extraction_scopes": list(EXTRACTION_SCOPES),
        "development_bucket_family_counts": manifest["development_bucket_family_counts"],
        "generation_contract": {
            "block_size": 2048,
            "output_budgets": manifest["output_budgets"],
        },
        "block_size": 2048,
        "tokenizer": "data/tokenizer/tokenizer.json",
        "model_config_path": "configs/model_fullpage_2048.json",
        "model_config": parent["model_config"],
        "device": "cuda",
        "precision": "bf16",
        "batch_size": 8,
        "validation_batch_size": 8,
        "gradient_accumulation": 6,
        "max_steps": 3600,
        "warmup_steps": 180,
        "learning_rate": 3e-5,
        "min_learning_rate": 3e-6,
        "betas": [0.9, 0.95],
        "weight_decay": 0.1,
        "grad_clip": 1.0,
        "validation_interval": 1800,
        "validation_batches": None,
        "checkpoint_interval": 600,
        "log_interval": 100,
        "reserve_free_bytes": RESERVE_BYTES,
        "checkpoint_artifact_budget_bytes": 2 * 1024**3,
        "initial_checkpoint": SELECTED_CHECKPOINT.as_posix(),
        "initial_checkpoint_sha256": parent_sha256,
        "performance": {
            "attention_backend": "sdpa",
            "fused_adamw": True,
            "pin_memory": True,
            "tf32": True,
            "supervised_only_logits": True,
            "validation_supervised_only_logits": True,
            "allocator_config": "expandable_segments:True",
            "gpu_telemetry": True,
            "best_weights_only": True,
        },
        "selection_rule": (
            "Train to 3,600 updates and preserve step 1,800 and 3,600 snapshots. "
            "Score only the frozen extractor development set. Select by frozen source/evidence "
            "and safety gates first, then exact field quality; never use the sealed final partition."
        ),
        "lineage": {
            "tokenizer_sha256": sha256_file(root / "data/tokenizer/tokenizer.json"),
            "request_extract_manifest_sha256": sha256_file(manifest_path),
            "train_data_sha256": manifest["files"]["train.jsonl"]["sha256"],
            "development_data_sha256": manifest["files"]["development.jsonl"]["sha256"],
            "selected_package_sha256": sha256_file(package_path),
            "selected_report_sha256": sha256_file(report_path),
            "selected_parent": {
                "path": SELECTED_CHECKPOINT.as_posix(),
                "sha256": parent_sha256,
                "run_id": "TRAIN-025",
                "global_step": 1800,
                "weights_only": True,
                "development_request_sha256": package["development_request_sha256"],
                "development_count": package["development_count"],
            },
            "source_sha256": source_sha256,
            "final_opened": False,
            "final_used": False,
            "existing_validation_used_for_training": False,
            "existing_test_used": False,
        },
        "seed": 42,
    }
    verify_request_extract_sources(config, root)
    return config


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--dataset-dir", type=Path, default=DATASET_DIR)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    root = args.root.resolve()
    output = args.output if args.output.is_absolute() else root / args.output
    output = output.resolve()
    if not output.is_relative_to(root) or output.exists():
        raise FileExistsError("Frozen extractor config path must be new and remain inside the project")
    config = build_training_config(root, args.dataset_dir)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "config": output.relative_to(root).as_posix(),
        "config_sha256": sha256_file(output),
        "selected_parent": config["lineage"]["selected_parent"],
        "dataset_manifest_sha256": config["lineage"]["request_extract_manifest_sha256"],
        "training_scopes": len(config["extraction_scopes"]),
        "batch_size": config["batch_size"],
        "gradient_accumulation": config["gradient_accumulation"],
        "max_steps": config["max_steps"],
        "reserve_free_bytes": config["reserve_free_bytes"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

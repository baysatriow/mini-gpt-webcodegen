"""Freeze TRAIN-024 initialization, V5 data lineage, and the 3,600-update budget."""
import argparse
import hashlib
import json
from pathlib import Path

from src.data.sources import sha256_file
from src.fullpage.lineage import (
    SOURCE_BOUND_LINEAGE_FILES,
    SOURCE_BOUND_TRAINING_FILES,
    V5_DATA_SOURCE_FILES,
    TRAIN024_PATH,
    SOURCE_BOUND_OUTPUT_BUDGETS,
    validate_source_bound_parent,
    verify_source_bound_lineage,
)
from src.fullpage.source_bound_contracts import CONTRACT_VERSION
from src.training.engine import checkpoint_sha256, read_checkpoint


ROOT = Path(__file__).resolve().parents[1]
PROFILE = Path("reports/training/FULLPAGE-GPU-005-CONTROLLED-B8.json")
DATASET_DIR = "data/processed/fullpage/v5"
OUTPUT = Path("configs/fullpage/training-improvement-v5.json")
INIT_PARENT_SHA256 = "3399709ffe2fa7981c9d26b8ff5723f7821bd78e302bea6dfe63aaf1d27c8638"
RESERVE_BYTES = 15 * 1024**3


def _json_sha256(value):
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _inside(root, relative):
    root = Path(root).resolve()
    path = (root / relative).resolve()
    if not path.is_relative_to(root):
        raise ValueError("Configured path escapes project root: " + str(relative))
    return path


def build_training_config(root=ROOT, *, profile_path=PROFILE, dataset_dir=DATASET_DIR):
    root = Path(root).resolve()
    profile_path = _inside(root, profile_path)
    dataset_path = _inside(root, dataset_dir)
    parent_path = _inside(root, TRAIN024_PATH)
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    selected = profile.get("selected", {})
    if (selected.get("status") != "stable" or selected.get("gpu") != "NVIDIA GeForce RTX 5070"
            or selected.get("batch") != 8 or selected.get("accumulation") != 6
            or selected.get("effective_batch") != 48 or selected.get("plan_probability") != 0.7):
        raise ValueError("Controlled RTX 5070 profile does not match the frozen 8/6/48 and 0.7 settings")
    parent = read_checkpoint(parent_path)
    parent_sha256 = checkpoint_sha256(parent_path)
    if parent_sha256 != "913b1b00aec040a0d51c3607cf7261288e7fe089378850fc66c131400c0f319a":
        raise ValueError("TRAIN-024 payload checksum differs from the approved frozen snapshot")
    if parent.get("run_id") != "TRAIN-024" or parent.get("global_step") != 3600 or parent.get("weights_only") is not True:
        raise ValueError("Expected TRAIN-024 step-3600 weights-only checkpoint")
    parent_config = parent["config"]
    if parent_config.get("lineage", {}).get("initialization_parent", {}).get("source_checkpoint_sha256") != INIT_PARENT_SHA256:
        raise ValueError("TRAIN-024 source ancestry differs from the approved INIT-2048 source")
    manifest_path = dataset_path / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest_sha256 = sha256_file(manifest_path)
    if manifest.get("version") != "fullpage-v5-source-bound-v1":
        raise ValueError("Expected the frozen source-bound-v1 V5 dataset")

    source_paths = set(manifest.get("source_sha256", {})) | set(V5_DATA_SOURCE_FILES)
    source_paths |= set(SOURCE_BOUND_LINEAGE_FILES) | set(SOURCE_BOUND_TRAINING_FILES)
    source_sha256 = {}
    for relative in sorted(source_paths):
        path = _inside(root, relative)
        if not path.is_file():
            raise FileNotFoundError("Required training source is missing: " + relative)
        source_sha256[relative] = sha256_file(path)

    v4_manifest_sha256 = manifest.get("parent", {}).get("manifest_sha256")
    parent_descriptor = {
        "path": TRAIN024_PATH,
        "sha256": parent_sha256,
        "run_id": "TRAIN-024",
        "global_step": 3600,
        "weights_only": True,
        "config_sha256": _json_sha256(parent_config),
        "dataset_manifest_sha256": v4_manifest_sha256,
    }
    lineage = {
        "tokenizer_sha256": manifest["tokenizer_sha256"],
        "fullpage_manifest_sha256": manifest_sha256,
        "parent_v4_manifest_sha256": v4_manifest_sha256,
        "initialization_parent": parent_config["lineage"]["initialization_parent"],
        "warm_start_parent": parent_descriptor,
        "schema_sha256": manifest["schema_sha256"],
        "source_sha256": source_sha256,
        "copy_catalog_sha256": manifest["copy_catalog_sha256"],
        "profile_sha256": sha256_file(profile_path),
    }
    config = {
        "mode": "sft",
        "scope": "main",
        "data_origin": "fullpage_curriculum",
        "human_reviewed": False,
        "fullpage_contract_version": CONTRACT_VERSION,
        "dataset_dir": dataset_path.relative_to(root).as_posix(),
        "plan_batch_probability": 0.7,
        "seed": 42,
        "block_size": 2048,
        "generation_contract": {"block_size": 2048, "output_budgets": SOURCE_BOUND_OUTPUT_BUDGETS},
        "tokenizer": "data/tokenizer/tokenizer.json",
        "model_config_path": "configs/model_fullpage_2048.json",
        "model_config": parent["model_config"],
        "device": "cuda",
        "precision": "bf16",
        "batch_size": 8,
        "gradient_accumulation": 6,
        "max_steps": 3600,
        "warmup_steps": 180,
        "learning_rate": 5e-5,
        "min_learning_rate": 5e-6,
        "betas": [0.9, 0.95],
        "weight_decay": 0.1,
        "grad_clip": 1,
        "validation_interval": 1800,
        "validation_batches": None,
        "checkpoint_interval": 1800,
        "log_interval": 100,
        "reserve_free_bytes": RESERVE_BYTES,
        "initial_checkpoint": TRAIN024_PATH,
        "initial_checkpoint_sha256": parent_sha256,
        "storage_phase_id": "fullpage-improvement-v5",
        "performance": {
            "attention_backend": "sdpa",
            "fused_adamw": True,
            "pin_memory": True,
            "tf32": True,
            "supervised_only_logits": True,
            "validation_supervised_only_logits": True,
            "allocator_config": "expandable_segments:True",
            "gpu_telemetry": True,
            "selected_by": PROFILE.as_posix(),
            "best_weights_only": True,
        },
        "selection_rule": (
            "Fixed 3,600-update budget initialized from TRAIN-024 weights only. Compare development generation at updates "
            "1,800 and 3,600 by complete pages and exact fact-reference checks, then ordinary development CE. "
            "Require at least 76 of 80 pages for the model gate. Keep final data sealed."
        ),
        "lineage": lineage,
    }
    verify_source_bound_lineage(config, root)
    validate_source_bound_parent(parent, config, root)
    return config


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--profile", default=PROFILE.as_posix())
    parser.add_argument("--dataset-dir", default=DATASET_DIR)
    parser.add_argument("--output", default=OUTPUT.as_posix())
    args = parser.parse_args()
    root = args.root.resolve()
    output = _inside(root, args.output)
    if output.exists():
        raise FileExistsError("Frozen V5 training config destination must be new")
    config = build_training_config(root, profile_path=args.profile, dataset_dir=args.dataset_dir)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(config, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    print(json.dumps({
        "config": output.relative_to(root).as_posix(),
        "config_sha256": sha256_file(output),
        "initial_checkpoint": config["initial_checkpoint"],
        "initial_checkpoint_sha256": config["initial_checkpoint_sha256"],
        "fullpage_manifest_sha256": config["lineage"]["fullpage_manifest_sha256"],
        "plan_probability": config["plan_batch_probability"],
        "batch_size": config["batch_size"],
        "gradient_accumulation": config["gradient_accumulation"],
        "max_steps": config["max_steps"],
        "output_budgets": config["generation_contract"]["output_budgets"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

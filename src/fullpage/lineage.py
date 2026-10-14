"""Explicit checks for project-owned context extension and full-page training."""
import hashlib
import json
from pathlib import Path
from src.data.sources import sha256_file
from src.training.lineage import pretrain_descriptor


SOURCE_BOUND_LINEAGE_FILES = (
    "src/fullpage/generation.py",
    "src/fullpage/serialization.py",
    "src/fullpage/compose.py",
    "src/fullpage/contracts.py",
    "src/fullpage/prompts.py",
    "src/fullpage/source_bound_prompts.py",
    "src/fullpage/source_bound_serialization.py",
    "src/fullpage/source_bound_contracts.py",
    "src/fullpage/source_bound_compose.py",
    "src/fullpage/source_bound_resolver.py",
    "src/fullpage/lineage.py",
    "src/fullpage/renderer.py",
    "src/fullpage/assets.py",
    "configs/fullpage/source-bound-copy-v1.json",
)
SOURCE_BOUND_TRAINING_FILES = (
    "src/training/engine.py",
    "src/models/minigpt.py",
    "src/fullpage/dataset.py",
    "src/fullpage/evaluation.py",
    "qa/train_fullpage.py",
    "qa/configure_fullpage_v5_training.py",
    "qa/evaluate_fullpage.py",
    "qa/snapshot_fullpage_checkpoint.py",
    "configs/model_fullpage_2048.json",
)
V5_DATA_SOURCE_FILES = (
    "qa/prepare_fullpage_v5.py",
    "src/fullpage/source_bound_targets.py",
    "src/fullpage/dataset.py",
    "src/fullpage/source_bound_prompts.py",
    "src/fullpage/source_bound_serialization.py",
    "src/fullpage/source_bound_contracts.py",
    "src/fullpage/source_bound_compose.py",
    "src/fullpage/source_bound_resolver.py",
    "src/fullpage/curriculum.py",
    "src/fullpage/serialization.py",
    "src/fullpage/contracts.py",
    "src/fullpage/prompts.py",
    "configs/fullpage/source-bound-copy-v1.json",
)
V5_SCHEMA_FILES = (
    "plan.schema.json",
    "section.schema.json",
    "plan-source-bound-v1.schema.json",
    "section-source-bound-v1.schema.json",
)
V5_FILES = {"train.jsonl", "validation.jsonl", "train.requests.jsonl", "validation.requests.jsonl"}
V4_FILES = {
    "train.jsonl", "train.requests.jsonl", "validation.jsonl", "validation.requests.jsonl",
    "test.jsonl", "test.requests.jsonl",
}
SEALED_FILES = ("validation.requests.jsonl", "test.requests.jsonl", "test.jsonl")
TRAIN024_PATH = "checkpoints/FULLPAGE-V4/TRAIN-024-step3600.pt"
TRAIN024_SHA256 = "913b1b00aec040a0d51c3607cf7261288e7fe089378850fc66c131400c0f319a"
TRAIN025_RUN_ID = "TRAIN-025"
TRAIN025_STEP = 1800
TRAIN025_PATH = "checkpoints/TRAIN-025/last.pt"
TRAIN025_REPORT_PATH = "reports/training/TRAIN-025.json"
TRAIN026_RUN_ID = "TRAIN-026"
INIT_PATH = "checkpoints/INIT-2048-001/initial.pt"
INIT_SOURCE_CHECKPOINT_SHA256 = "3399709ffe2fa7981c9d26b8ff5723f7821bd78e302bea6dfe63aaf1d27c8638"
SOURCE_BOUND_OUTPUT_BUDGETS = {"page_plan": 896, "section_content": 1536}


def _resolve_inside(root, relative_path):
    root = Path(root).resolve()
    path = (root / relative_path).resolve()
    if not path.is_relative_to(root):
        raise ValueError("Lineage path escapes project root: " + str(relative_path))
    return path


def _verify_files(directory, file_info, expected_names):
    directory = Path(directory).resolve()
    if not isinstance(file_info, dict) or set(file_info) != set(expected_names):
        raise ValueError("Dataset manifest file list differs from the frozen split contract")
    for name, info in file_info.items():
        path = (directory / name).resolve()
        if not path.is_relative_to(directory) or not path.is_file() or not isinstance(info, dict):
            raise ValueError("Dataset manifest contains an invalid file path: " + name)
        if path.stat().st_size != info.get("bytes") or sha256_file(path) != info.get("sha256"):
            raise ValueError("Dataset file differs from its manifest: " + name)


def _load_verified_manifest(root, directory, version, expected_files):
    directory = _resolve_inside(root, directory)
    path = directory / "manifest.json"
    if not path.is_file():
        raise FileNotFoundError("Dataset manifest is missing: " + str(path))
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest.get("version") != version:
        raise ValueError("Unexpected dataset manifest version: " + str(manifest.get("version")))
    _verify_files(directory, manifest.get("files"), expected_files)
    return directory, manifest, sha256_file(path)


def _json_sha256(value):
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


SOURCE_BOUND_PROFILE_PATH = "reports/training/FULLPAGE-GPU-005-CONTROLLED-B8.json"
SOURCE_BOUND_PROFILE_SHA256 = "8a101fa71916993c3beb47c81c18255bb645ebe11862fa82fc93983ef02c2998"
SOURCE_BOUND_TRAINING_SETTINGS = {
    "plan_batch_probability": 0.7,
    "mode": "sft",
    "scope": "main",
    "data_origin": "fullpage_curriculum",
    "human_reviewed": False,
    "fullpage_contract_version": "source-bound-v1",
    "dataset_dir": "data/processed/fullpage/v5",
    "seed": 42,
    "block_size": 2048,
    "generation_contract": {
        "block_size": 2048,
        "output_budgets": {"page_plan": 896, "section_content": 1536},
    },
    "tokenizer": "data/tokenizer/tokenizer.json",
    "model_config_path": "configs/model_fullpage_2048.json",
    "model_config": {
        "vocab_size": 8192,
        "block_size": 2048,
        "n_layer": 6,
        "n_head": 6,
        "n_embd": 384,
        "dropout": 0.1,
        "tie_embeddings": True,
        "initialization": "random normal mean 0 std 0.02; no pretrained weights",
    },
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
    "reserve_free_bytes": 16106127360,
    "initial_checkpoint": TRAIN024_PATH,
    "initial_checkpoint_sha256": TRAIN024_SHA256,
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
        "selected_by": "reports/training/FULLPAGE-GPU-005-CONTROLLED-B8.json",
        "best_weights_only": True,
    },
    "selection_rule": "Fixed 3,600-update budget initialized from TRAIN-024 weights only. Compare development generation at updates 1,800 and 3,600 by complete pages and exact fact-reference checks, then ordinary development CE. Require at least 76 of 80 pages for the model gate. Keep final data sealed.",
}


def verify_source_bound_training_settings(config: dict, root: Path) -> None:
    """Enforce the reviewed V5 experiment settings independently of caller config."""
    for name, expected in SOURCE_BOUND_TRAINING_SETTINGS.items():
        if name not in config or _json_sha256(config[name]) != _json_sha256(expected):
            raise ValueError("Frozen source-bound training setting changed: " + name)

    lineage = config.get("lineage")
    if not isinstance(lineage, dict) or lineage.get("profile_sha256") != SOURCE_BOUND_PROFILE_SHA256:
        raise ValueError("Frozen source-bound training setting changed: lineage.profile_sha256")
    profile_path = _resolve_inside(root, SOURCE_BOUND_PROFILE_PATH)
    if sha256_file(profile_path) != SOURCE_BOUND_PROFILE_SHA256:
        raise ValueError("Frozen source-bound training profile checksum changed")


def verify_source_bound_lineage(config: dict, root: Path) -> None:
    """Verify the immutable V5 corpus, schemas, tokenizer, and all training/generation sources."""
    from .source_bound_contracts import CONTRACT_VERSION

    root = Path(root).resolve()
    if (config.get("fullpage_contract_version") != CONTRACT_VERSION
            or config.get("data_origin") != "fullpage_curriculum"
            or config.get("human_reviewed") is not False
            or config.get("scope") != "main"
            or config.get("block_size") != 2048
            or config.get("model_config", {}).get("block_size") != 2048):
        raise ValueError("Invalid source-bound-v1 training configuration")
    if config.get("generation_contract") != {
        "block_size": 2048,
        "output_budgets": SOURCE_BOUND_OUTPUT_BUDGETS,
    }:
        raise ValueError("Source-bound generation context or output budgets changed")
    if (config.get("initial_checkpoint") != TRAIN024_PATH
            or config.get("initial_checkpoint_sha256") != TRAIN024_SHA256):
        raise ValueError("Source-bound training must pin the exact TRAIN-024 parent")
    verify_source_bound_training_settings(config, root)

    dataset_dir, manifest, manifest_sha = _load_verified_manifest(
        root, config.get("dataset_dir", ""), "fullpage-v5-source-bound-v1", V5_FILES,
    )
    lineage = config.get("lineage")
    if not isinstance(lineage, dict) or lineage.get("fullpage_manifest_sha256") != manifest_sha:
        raise ValueError("V5 dataset manifest differs from training lineage")
    if (manifest.get("human_reviewed") is not False or manifest.get("final_opened") is not False
            or manifest.get("block_size") != 2048 or manifest.get("splits") != ["train", "validation"]):
        raise ValueError("V5 dataset has an invalid disclosure or split contract")
    if (manifest.get("family_counts") != {"train": 240, "validation": 40}
            or manifest.get("request_counts") != {"train": 3360, "validation": 80}
            or manifest.get("task_counts") != {"train": 33600, "validation": 800}
            or manifest.get("output_budgets") != SOURCE_BOUND_OUTPUT_BUDGETS):
        raise ValueError("V5 family, request, task, or generation budget counts changed")
    family_ids = manifest.get("family_ids", {})
    if (len(family_ids.get("train", [])) != 240 or len(set(family_ids.get("train", []))) != 240
            or len(family_ids.get("validation", [])) != 40
            or len(set(family_ids.get("validation", []))) != 40
            or set(family_ids.get("train", [])) & set(family_ids.get("validation", []))):
        raise ValueError("V5 family partitions are invalid or overlap")
    if set(manifest.get("files", {})) != V5_FILES or any("test" in name for name in manifest.get("files", {})):
        raise ValueError("V5 must contain only train and validation data files")
    if sum(info["bytes"] for info in manifest["files"].values()) != manifest.get("bytes"):
        raise ValueError("V5 data byte count differs from its manifest")
    if manifest.get("request_sha256") != {
        name: manifest["files"][name]["sha256"]
        for name in ("train.requests.jsonl", "validation.requests.jsonl")
    }:
        raise ValueError("V5 request hashes differ from frozen request files")
    maxima = manifest.get("maxima", {})
    if set(maxima) != {"train", "validation"}:
        raise ValueError("V5 token maxima are missing a frozen split")
    for split, values in maxima.items():
        if (values.get("total_tokens", 2049) > 2048
                or values.get("target_tokens_with_eos", 897) > SOURCE_BOUND_OUTPUT_BUDGETS["page_plan"]
                or any(type(values.get(key)) is not int or values[key] < 0
                       for key in ("prefix_tokens", "target_tokens_with_eos", "total_tokens"))):
            raise ValueError("V5 contains a task outside its token context or target limit")

    parent_dir, parent_manifest, parent_sha = _load_verified_manifest(
        root, "data/processed/fullpage/v4", "fullpage-v4", V4_FILES,
    )
    if (manifest.get("parent", {}).get("version") != "fullpage-v4"
            or manifest["parent"].get("manifest_sha256") != parent_sha
            or lineage.get("parent_v4_manifest_sha256") != parent_sha):
        raise ValueError("V5 parent V4 manifest differs from the frozen lineage")
    sealed_before = manifest.get("sealed_sha256_before")
    sealed_after = manifest.get("sealed_sha256_after")
    if not isinstance(sealed_before, dict) or sealed_before != sealed_after:
        raise ValueError("Sealed validation/final hashes changed during V5 preparation")
    if any(sealed_before.get(name) != parent_manifest["files"][name]["sha256"] for name in SEALED_FILES):
        raise ValueError("V5 sealed hashes do not match the V4 parent manifest")
    for name in SEALED_FILES:
        if sha256_file(parent_dir / name) != sealed_before[name]:
            raise ValueError("A sealed V4 validation/final file changed: " + name)

    tokenizer_path = _resolve_inside(root, "data/tokenizer/tokenizer.json")
    if (sha256_file(tokenizer_path) != manifest.get("tokenizer_sha256")
            or lineage.get("tokenizer_sha256") != manifest["tokenizer_sha256"]):
        raise ValueError("V5 tokenizer lineage changed")
    schema_hashes = manifest.get("schema_sha256")
    if (not isinstance(schema_hashes, dict) or set(schema_hashes) != set(V5_SCHEMA_FILES)
            or lineage.get("schema_sha256") != schema_hashes):
        raise ValueError("V5 schema lineage is incomplete or changed")
    for name, digest in schema_hashes.items():
        if sha256_file(_resolve_inside(root, "configs/fullpage/" + name)) != digest:
            raise ValueError("Source-bound schema differs from V5 lineage: " + name)
    copy_catalog_sha = sha256_file(_resolve_inside(root, "configs/fullpage/source-bound-copy-v1.json"))
    if (manifest.get("copy_catalog_sha256") != copy_catalog_sha
            or lineage.get("copy_catalog_sha256") != copy_catalog_sha):
        raise ValueError("Source-bound copy catalog differs from V5 lineage")

    manifest_sources = manifest.get("source_sha256")
    if not isinstance(manifest_sources, dict) or set(V5_DATA_SOURCE_FILES) - set(manifest_sources):
        raise ValueError("V5 preparation source lineage is incomplete")
    for relative, digest in manifest_sources.items():
        if sha256_file(_resolve_inside(root, relative)) != digest:
            raise ValueError("V5 preparation source changed: " + relative)
    config_sources = lineage.get("source_sha256")
    required_sources = set(manifest_sources) | set(SOURCE_BOUND_LINEAGE_FILES) | set(SOURCE_BOUND_TRAINING_FILES)
    if not isinstance(config_sources, dict) or required_sources - set(config_sources):
        raise ValueError("Training source lineage is incomplete")
    for relative, digest in config_sources.items():
        if sha256_file(_resolve_inside(root, relative)) != digest:
            raise ValueError("Training or generation source changed: " + relative)


def validate_source_bound_resume_path(run_id: str, resume_path: Path, root: Path) -> Path:
    """Restrict the V5 continuation to TRAIN-026 resuming TRAIN-025's exact last checkpoint."""
    if run_id != TRAIN026_RUN_ID:
        raise ValueError("Source-bound TRAIN-025 continuation must use run ID TRAIN-026")
    if not isinstance(resume_path, (str, Path)):
        raise ValueError("TRAIN-026 must resume the exact TRAIN-025 checkpoint path")
    root = Path(root).resolve()
    requested = Path(resume_path)
    if not requested.is_absolute():
        requested = root / requested
    expected = _resolve_inside(root, TRAIN025_PATH)
    resolved = requested.resolve()
    if resolved != expected:
        raise ValueError("TRAIN-026 must resume the exact TRAIN-025 step-1800 checkpoint")
    return expected


def validate_source_bound_train025_report(
    report: dict, config: dict, config_sha256: str, checkpoint_sha256: str,
) -> None:
    """Bind TRAIN-025's completed 1,800-step state to its config and checkpoint digest."""
    def valid_digest(value):
        return (isinstance(value, str) and len(value) == 64
                and all(character in "0123456789abcdef" for character in value))

    if not isinstance(report, dict):
        raise ValueError("TRAIN-025 training report is missing or invalid")
    if (report.get("run_id") != TRAIN025_RUN_ID or report.get("status") != "stopped_at_limit"
            or report.get("global_step") != TRAIN025_STEP
            or report.get("last_committed_step") != TRAIN025_STEP):
        raise ValueError("TRAIN-025 report must record its committed step-1800 stop")
    if report.get("config") != config or report.get("config_sha256") != config_sha256:
        raise ValueError("TRAIN-025 report config differs from the frozen V5 config")
    if report.get("resume_parent") is not None or report.get("resume_parent_sha256") is not None:
        raise ValueError("TRAIN-025 must be the fresh TRAIN-024-initialized run")
    recorded = report.get("final_checkpoint_sha256")
    if (not valid_digest(recorded) or not valid_digest(checkpoint_sha256)
            or recorded != checkpoint_sha256):
        raise ValueError("TRAIN-025 checkpoint digest does not match its training report")


def validate_source_bound_resume_state(parent: dict, config: dict) -> None:
    """Require a full, exact TRAIN-025 checkpoint suitable for optimizer-state resume."""
    if (not isinstance(parent, dict) or parent.get("run_id") != TRAIN025_RUN_ID
            or parent.get("global_step") != TRAIN025_STEP or parent.get("weights_only") is True):
        raise ValueError("TRAIN-026 resume parent must be the full TRAIN-025 step-1800 checkpoint")
    if parent.get("config") != config:
        raise ValueError("TRAIN-025 checkpoint config differs from the frozen V5 config")
    if any(parent.get(key) is None for key in ("optimizer", "scheduler", "sampler", "rng")):
        raise ValueError("TRAIN-025 checkpoint is missing full optimizer, scheduler, sampler, or RNG state")


def validate_source_bound_parent(parent: dict, config: dict, root: Path) -> None:
    """Accept only the exact frozen TRAIN-024 weights-only V4 snapshot for V5."""
    from src.training.engine import checkpoint_sha256
    from .source_bound_contracts import CONTRACT_VERSION

    root = Path(root).resolve()
    if (config.get("fullpage_contract_version") != CONTRACT_VERSION
            or config.get("data_origin") != "fullpage_curriculum"
            or config.get("human_reviewed") is not False
            or config.get("scope") != "main"):
        raise ValueError("TRAIN-024 warm-start requires source-bound-v1 main training")
    parent_config = parent.get("config", {})
    if (parent.get("run_id") != "TRAIN-024" or parent.get("global_step") != 3600
            or parent.get("weights_only") is not True):
        raise ValueError("Warm-start parent must be the TRAIN-024 step-3600 weights-only snapshot")
    if (parent.get("model_config") != config.get("model_config")
            or parent.get("model_config", {}).get("block_size") != 2048
            or parent_config.get("model_config") != config.get("model_config")):
        raise ValueError("TRAIN-024 model shape differs from source-bound training")
    if (parent_config.get("mode") != "sft" or parent_config.get("scope") != "main"
            or parent_config.get("data_origin") != "fullpage_curriculum"
            or parent_config.get("human_reviewed") is not False
            or parent_config.get("fullpage_contract_version") is not None
            or parent_config.get("dataset_dir") != "data/processed/fullpage/v4"
            or parent_config.get("max_steps") != 3600):
        raise ValueError("TRAIN-024 is not the frozen ordinary V4 main checkpoint")

    parent_lineage = parent_config.get("lineage", {})
    v4_dir, v4_manifest, v4_sha = _load_verified_manifest(
        root, "data/processed/fullpage/v4", "fullpage-v4", V4_FILES,
    )
    if (parent_lineage.get("fullpage_manifest_sha256") != v4_sha
            or parent_lineage.get("schema_sha256") != v4_manifest.get("schema_sha256")
            or parent_lineage.get("tokenizer_sha256") != config.get("lineage", {}).get("tokenizer_sha256")
            or parent_config.get("initial_checkpoint") != INIT_PATH
            or parent_lineage.get("initialization_parent", {}).get("migration_kind") != "position_extension"
            or parent_lineage.get("initialization_parent", {}).get("source_checkpoint_sha256") != INIT_SOURCE_CHECKPOINT_SHA256):
        raise ValueError("TRAIN-024 V4 dataset or position-extension ancestry changed")
    if config.get("lineage", {}).get("parent_v4_manifest_sha256") != v4_sha:
        raise ValueError("Source-bound config does not pin the same V4 parent manifest")
    tokenizer_sha = sha256_file(_resolve_inside(root, "data/tokenizer/tokenizer.json"))
    if (parent_lineage.get("tokenizer_sha256") != tokenizer_sha
            or parent_lineage.get("initialization_parent", {}).get("tokenizer_sha256") != tokenizer_sha):
        raise ValueError("TRAIN-024 tokenizer lineage differs from the current project tokenizer")

    checkpoint_path = config.get("initial_checkpoint")
    checkpoint_sha = config.get("initial_checkpoint_sha256")
    if checkpoint_path != TRAIN024_PATH or checkpoint_sha != TRAIN024_SHA256:
        raise ValueError("Source-bound initialization is not pinned to the approved TRAIN-024 artifact")
    if checkpoint_sha256(_resolve_inside(root, checkpoint_path)) != checkpoint_sha:
        raise ValueError("TRAIN-024 checkpoint payload checksum changed")
    init_checkpoint_sha = parent_config.get("initial_checkpoint_sha256")
    if not isinstance(init_checkpoint_sha, str) or checkpoint_sha256(_resolve_inside(root, INIT_PATH)) != init_checkpoint_sha:
        raise ValueError("TRAIN-024 source initialization checkpoint checksum changed")

    expected_warm_start = {
        "path": TRAIN024_PATH,
        "sha256": checkpoint_sha,
        "run_id": "TRAIN-024",
        "global_step": 3600,
        "weights_only": True,
        "config_sha256": _json_sha256(parent_config),
        "dataset_manifest_sha256": v4_sha,
    }
    lineage = config.get("lineage", {})
    if (lineage.get("initialization_parent") != parent_lineage.get("initialization_parent")
            or lineage.get("warm_start_parent") != expected_warm_start):
        raise ValueError("Source-bound training config does not preserve exact TRAIN-024 lineage")


def verify_source_ancestry(parent, root):
    root = Path(root)
    lineage = parent['config']['lineage']
    summary = json.loads((root / 'data/manifests/pipeline_summary.json').read_text(encoding='utf-8'))
    fingerprint = pretrain_descriptor(root, summary)
    if lineage.get('pretrain_fingerprint') != fingerprint or lineage.get('tokenizer_sha256') != sha256_file(root / 'data/tokenizer/tokenizer.json'):
        raise ValueError('Project pretraining/tokenizer ancestry mismatch')
    if parent['config'].get('data_origin') != 'synthetic_curriculum' or parent['global_step'] < 1:
        raise ValueError('Extension requires a trained project synthetic checkpoint')
    from src.data.curriculum import verify_manifest
    directory = root / parent['config']['dataset_dir']
    verify_manifest(directory)
    if sha256_file(directory / 'manifest.json') != lineage['synthetic_manifest_sha256']:
        raise ValueError('Source curriculum manifest changed')
    return fingerprint


def validate_fullpage_parent(parent, config, root):
    lineage = parent['config']['lineage']
    if parent.get('global_step') != 0 or lineage.get('migration_kind') != 'position_extension':
        raise ValueError('Full-page initialization needs an explicit position extension')
    if parent['model_config'] != config['model_config'] or parent['model_config']['block_size'] != 2048:
        raise ValueError('Extended model configuration mismatch')
    if config.get('data_origin') != 'fullpage_curriculum' or config.get('human_reviewed') is not False:
        raise ValueError('Full-page synthetic origin must be disclosed')
    current = sha256_file(Path(root) / 'data/tokenizer/tokenizer.json')
    if lineage['tokenizer_sha256'] != current or config['lineage']['tokenizer_sha256'] != current:
        raise ValueError('Extended tokenizer checksum mismatch')
    if config['lineage']['initialization_parent'] != lineage:
        raise ValueError('Extension ancestry changed')
    if lineage['source_checkpoint_sha256'] != '3399709ffe2fa7981c9d26b8ff5723f7821bd78e302bea6dfe63aaf1d27c8638':
        raise ValueError('Unexpected source checkpoint')

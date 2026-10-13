"""Bind training ancestry and held-out evaluation to immutable corpus/family evidence."""
import json
import copy
from pathlib import Path

from src.data.integrity import reuse_tokenization, validate_sft_artifacts
from src.data.normalize import read_jsonl
from src.data.sources import sha256_file
from src.data.split import SPLITS, assignment_hash, read_group_assignment


def pretrain_descriptor(root, summary):
    root = Path(root)
    split = json.loads((root / "data/processed/pretrain/manifest.json").read_text(encoding="utf-8"))
    if split != summary["split"]:
        raise ValueError("Current pretraining manifest differs from pipeline summary")
    read_group_assignment(root / "data/processed/pretrain")
    value = {"version": 1, "tokenizer_sha256": summary["tokenizer"]["tokenizer_sha256"],
             "assignment_sha256": split["assignment_sha256"],
             "source_revisions": [{k: row[k] for k in ("id", "revision", "license", "rows")}
                                  for row in sorted(summary["sources"], key=lambda row: row["id"])],
             "partition_sha256": {name: split["files"][name]["sha256"] for name in SPLITS},
             "token_cache_sha256": {name: summary["token_caches"][name]["sha256"] for name in SPLITS}}
    return {**value, "sha256": assignment_hash(value)}


def sft_descriptor(summary):
    if summary.get("sft", {}).get("status") != "complete":
        raise ValueError("SFT requires complete reviewed data")
    manifest = summary["sft"]["split"]
    return {"version": 1, "sha256": assignment_hash(manifest),
            "pretrain_assignment_sha256": manifest["pretrain_assignment_sha256"]}


def _parent_descriptor(state, root, summary):
    lineage = state["config"]["lineage"]
    if "pretrain_fingerprint" in lineage:
        return lineage["pretrain_fingerprint"]
    # Legacy baseline is accepted only while its exact, recorded pipeline snapshot remains verified.
    # If SFT preparation changes the summary, first record a verified migration; never infer old splits.
    if (state["config"]["mode"] != "pretrain" or summary is None
            or lineage.get("pipeline_summary_sha256") != sha256_file(Path(root) / "data/manifests/pipeline_summary.json")
            or lineage.get("tokenizer_sha256") != summary["tokenizer"]["tokenizer_sha256"]
            or any(lineage.get("data_sha256", {}).get(name) != summary["token_caches"][name]["sha256"]
                   for name in ("train", "validation"))):
        raise ValueError("Missing immutable pretraining lineage; legacy snapshot cannot be proven")
    return pretrain_descriptor(root, summary)


def validate_initial_checkpoint(parent, config, root, summary=None):
    if config.get('curriculum_continuation', False):
        return validate_curriculum_continuation(parent, config, root, summary)
    if config["mode"] != "sft":
        raise ValueError("Model-only initialization is reserved for SFT from project pretraining")
    lineage = parent["config"]["lineage"]
    if parent["config"]["mode"] != "pretrain" or parent["global_step"] < 1 or lineage.get("smoke", False):
        raise ValueError("SFT parent must be a trained project pretraining baseline, not smoke")
    if lineage.get("tokenizer_sha256") != config["lineage"].get("tokenizer_sha256"):
        raise ValueError("Initial checkpoint tokenizer lineage mismatch")
    if summary is None and "pretrain_fingerprint" not in lineage:
        summary = json.loads((Path(root) / "data/manifests/pipeline_summary.json").read_text(encoding="utf-8"))
    if _parent_descriptor(parent, root, summary) != config["lineage"]["pretrain_fingerprint"]:
        raise ValueError("Initial checkpoint pretraining corpus/family lineage mismatch")


def validate_curriculum_continuation(parent, config, root, summary=None):
    """Continue only this project's disclosed synthetic model; production gate stays separate."""
    from src.data.curriculum import verify_manifest
    parent_cfg, lineage = parent['config'], parent['config']['lineage']
    if (config['mode'] != 'sft' or config.get('data_origin') != 'synthetic_curriculum'
            or config.get('human_reviewed') is not False or config['lineage']['human_reviewed'] is not False
            or parent_cfg['mode'] != 'sft' or parent_cfg.get('data_origin') != 'synthetic_curriculum'
            or lineage.get('human_reviewed') is not False or parent['global_step'] < 1):
        raise ValueError('Continuation requires a trained project synthetic curriculum parent')
    if summary is None:
        summary = json.loads((Path(root) / 'data/manifests/pipeline_summary.json').read_text(encoding='utf-8'))
    fingerprint = pretrain_descriptor(root, summary)
    ancestry = lineage.get('pretraining_parent', {})
    if (lineage['tokenizer_sha256'] != config['lineage']['tokenizer_sha256']
            or lineage['pretrain_fingerprint'] != fingerprint or config['lineage']['pretrain_fingerprint'] != fingerprint
            or ancestry.get('phase') != 'pretrain' or ancestry.get('global_step', 0) < 1
            or ancestry.get('pretrain_fingerprint') != fingerprint
            or config['lineage']['pretraining_parent'] != ancestry
            or parent['model_config'] != config['model_config']):
        raise ValueError('Continuation model/tokenizer/project pretraining ancestry mismatch')
    directory = Path(root) / parent_cfg['dataset_dir']
    verify_manifest(directory)
    recorded = config['lineage'].get('curriculum_parent', {})
    if (sha256_file(directory / 'manifest.json') != lineage['synthetic_manifest_sha256']
            or recorded.get('synthetic_manifest_sha256') != lineage['synthetic_manifest_sha256']
            or recorded.get('checkpoint_sha256') != config['initial_checkpoint_sha256']
            or recorded.get('global_step') != parent['global_step']):
        raise ValueError('Continuation parent/corpus evidence changed')


def verify_checkpoint_lineage(state, root, summary):
    if state["config"].get("data_origin") == "synthetic_curriculum":
        raise ValueError("Synthetic curriculum is not human-reviewed production SFT; use its explicit evaluator")
    current = pretrain_descriptor(root, summary)
    lineage = state["config"]["lineage"]
    if _parent_descriptor(state, root, summary) != current:
        raise ValueError("Checkpoint pretraining corpus/family lineage differs from evaluation data")
    if state["config"]["mode"] == "sft":
        parent = lineage.get("pretraining_parent")
        if (not parent or parent.get("phase") != "pretrain" or parent.get("global_step", 0) < 1
                or parent.get("pretrain_fingerprint") != current):
            raise ValueError("SFT checkpoint has no verified pretraining parent history")
        if lineage.get("sft_fingerprint") != sft_descriptor(summary):
            raise ValueError("SFT checkpoint reviewed corpus lineage mismatch")
        for name in ("train", "validation"):
            if lineage["data_sha256"][name] != summary["sft"]["split"]["files"][name]["sha256"]:
                raise ValueError("SFT checkpoint training partition checksum mismatch")
    elif state["config"]["mode"] != "pretrain":
        raise ValueError("Unknown checkpoint training phase")
    return current


def bind_legacy_checkpoint(state, root, summary):
    fingerprint = verify_checkpoint_lineage(state, root, summary)
    bound = copy.deepcopy(state)
    bound["config"]["lineage"]["pretrain_fingerprint"] = fingerprint
    return bound


def verify_sft_data(root, summary):
    # Import locally to avoid the pipeline -> integrity import cycle.
    from src.data.pipeline import load_completed_sources
    root = Path(root)
    config = json.loads((root / "configs/dataset.json").read_text(encoding="utf-8"))
    paths, _ = load_completed_sources(config, root)
    sources = {row["source_row_id"]: row for path in paths for row in read_jsonl(path)}
    return validate_sft_artifacts(root, summary["sft"], sources)


def verify_production_prompts(state, rows, root, summary):
    if state["config"]["mode"] != "sft" or state["global_step"] < 1:
        raise ValueError("Production PageSpec evaluation requires a trained SFT checkpoint")
    verify_checkpoint_lineage(state, root, summary)
    verify_sft_data(root, summary)
    actual = {row["source_row_id"]: row for row in read_jsonl(Path(root) / "data/processed/sft/test.jsonl")}
    seen = set()
    if not rows:
        raise ValueError("Production test prompts cannot be empty")
    for row in rows:
        identity = row.get("source_row_id")
        expected = actual.get(identity)
        if identity in seen or expected is None or any(row.get(key) != value for key, value in expected.items()):
            raise ValueError("Prompt is not an unchanged member of verified reviewed SFT test data")
        seen.add(identity)

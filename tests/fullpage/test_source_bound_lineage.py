import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.fullpage.lineage import (
    SOURCE_BOUND_LINEAGE_FILES,
    SOURCE_BOUND_TRAINING_FILES,
    V5_DATA_SOURCE_FILES,
    validate_source_bound_parent,
    verify_source_bound_lineage,
)
from src.fullpage.source_bound_contracts import CONTRACT_VERSION


TRAIN024_PATH = "checkpoints/FULLPAGE-V4/TRAIN-024-step3600.pt"
TRAIN024_SHA256 = "913b1b00aec040a0d51c3607cf7261288e7fe089378850fc66c131400c0f319a"
INIT_PATH = "checkpoints/INIT-2048-001/initial.pt"
INIT_SHA256 = "8" * 64
SOURCE_CHECKPOINT_SHA256 = "3399709ffe2fa7981c9d26b8ff5723f7821bd78e302bea6dfe63aaf1d27c8638"
MODEL_CONFIG = {
    "vocab_size": 8192,
    "block_size": 2048,
    "n_layer": 6,
    "n_head": 6,
    "n_embd": 384,
    "dropout": 0.1,
    "tie_embeddings": True,
    "initialization": "random normal mean 0 std 0.02; no pretrained weights",
}
V5_FILES = ("train.jsonl", "validation.jsonl", "train.requests.jsonl", "validation.requests.jsonl")
V4_FILES = (
    "train.jsonl",
    "train.requests.jsonl",
    "validation.jsonl",
    "validation.requests.jsonl",
    "test.jsonl",
    "test.requests.jsonl",
)
SEALED_FILES = ("validation.requests.jsonl", "test.requests.jsonl", "test.jsonl")
SCHEMA_FILES = (
    "plan.schema.json",
    "section.schema.json",
    "plan-source-bound-v1.schema.json",
    "section-source-bound-v1.schema.json",
)


def _write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")


def _file_info(path):
    payload = Path(path).read_bytes()
    return {"bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}


def _json_sha(value):
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


class SourceBoundLineageFixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self._create_source_files()
        self.v4_dir, self.v4_manifest, self.v4_manifest_sha = self._create_v4_parent()
        self.v5_dir, self.v5_manifest = self._create_v5_dataset()
        self.config = self._create_training_config()
        self.parent_state = self._create_parent_state()
        (self.root / TRAIN024_PATH).parent.mkdir(parents=True, exist_ok=True)
        (self.root / TRAIN024_PATH).write_bytes(b"TRAIN-024 snapshot fixture")
        (self.root / INIT_PATH).parent.mkdir(parents=True, exist_ok=True)
        (self.root / INIT_PATH).write_bytes(b"INIT checkpoint fixture")

    def _create_source_files(self):
        all_sources = set(SOURCE_BOUND_LINEAGE_FILES) | set(SOURCE_BOUND_TRAINING_FILES) | set(V5_DATA_SOURCE_FILES)
        self.source_hashes = {}
        for relative in sorted(all_sources):
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(("fixture source " + relative).encode("utf-8"))
            self.source_hashes[relative] = _file_info(path)["sha256"]
        tokenizer = self.root / "data/tokenizer/tokenizer.json"
        tokenizer.parent.mkdir(parents=True, exist_ok=True)
        tokenizer.write_text('{"fixture":"tokenizer"}', encoding="utf-8")
        self.tokenizer_sha256 = _file_info(tokenizer)["sha256"]
        self.schema_hashes = {}
        for name in SCHEMA_FILES:
            path = self.root / "configs/fullpage" / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('{"fixture":"' + name + '"}', encoding="utf-8")
            self.schema_hashes[name] = _file_info(path)["sha256"]
        profile_relative = "reports/training/FULLPAGE-GPU-005-CONTROLLED-B8.json"
        profile_source = Path(__file__).resolve().parents[2] / profile_relative
        profile_target = self.root / profile_relative
        profile_target.parent.mkdir(parents=True, exist_ok=True)
        profile_target.write_bytes(profile_source.read_bytes())

    def _create_v4_parent(self):
        directory = self.root / "data/processed/fullpage/v4"
        directory.mkdir(parents=True)
        for name in V4_FILES:
            payload = ("SEALED " if name in SEALED_FILES else "V4 ") .encode("utf-8") + name.encode("utf-8") + b"\n"
            (directory / name).write_bytes(payload)
        manifest = {
            "version": "fullpage-v4",
            "human_reviewed": False,
            "family_counts": {"train": 240, "validation": 40, "test": 40},
            "task_counts": {"train": 24000, "validation": 960, "test": 800},
            "files": {name: _file_info(directory / name) for name in V4_FILES},
            "schema_sha256": self.schema_hashes,
        }
        manifest_path = directory / "manifest.json"
        _write_json(manifest_path, manifest)
        return directory, manifest, _file_info(manifest_path)["sha256"]

    def _create_v5_dataset(self):
        directory = self.root / "data/processed/fullpage/v5"
        directory.mkdir(parents=True)
        payloads = {
            "train.jsonl": b"{\"split\":\"train\"}\n",
            "validation.jsonl": b"{\"split\":\"validation\"}\n",
            "train.requests.jsonl": b"train requests fixture\n",
            "validation.requests.jsonl": b"validation requests fixture\n",
        }
        for name, payload in payloads.items():
            (directory / name).write_bytes(payload)
        request_hashes = {
            "train.requests.jsonl": _file_info(directory / "train.requests.jsonl")["sha256"],
            "validation.requests.jsonl": _file_info(directory / "validation.requests.jsonl")["sha256"],
        }
        sealed = {name: _file_info(self.v4_dir / name)["sha256"] for name in SEALED_FILES}
        manifest = {
            "version": "fullpage-v5-source-bound-v1",
            "origin": "project-authored deterministic synthetic conversion from fullpage-v4",
            "human_reviewed": False,
            "final_opened": False,
            "block_size": 2048,
            "output_budgets": {"page_plan": 896, "section_content": 1536},
            "parent": {"version": "fullpage-v4", "manifest_sha256": self.v4_manifest_sha},
            "files": {name: _file_info(directory / name) for name in V5_FILES},
            "bytes": sum(info["bytes"] for info in (_file_info(directory / name) for name in V5_FILES)),
            "family_ids": {"train": [f"family{i:04d}" for i in range(240)], "validation": [f"family{i:04d}" for i in range(240, 280)]},
            "family_counts": {"train": 240, "validation": 40},
            "splits": ["train", "validation"],
            "request_counts": {"train": 3360, "validation": 80},
            "task_counts": {"train": 33600, "validation": 800},
            "request_sha256": request_hashes,
            "sealed_sha256_before": sealed,
            "sealed_sha256_after": sealed,
            "source_sha256": {relative: self.source_hashes[relative] for relative in V5_DATA_SOURCE_FILES},
            "schema_sha256": self.schema_hashes,
            "copy_catalog_sha256": self.source_hashes["configs/fullpage/source-bound-copy-v1.json"],
            "tokenizer_sha256": self.tokenizer_sha256,
            "maxima": {
                "train": {"prefix_tokens": 866, "target_tokens_with_eos": 756, "total_tokens": 1622},
                "validation": {"prefix_tokens": 817, "target_tokens_with_eos": 752, "total_tokens": 1569},
            },
        }
        _write_json(directory / "manifest.json", manifest)
        return directory, manifest

    def _create_training_config(self):
        v5_manifest_sha = _file_info(self.v5_dir / "manifest.json")["sha256"]
        config_path = Path(__file__).resolve().parents[2] / "configs/fullpage/training-improvement-v5.json"
        base_config = json.loads(config_path.read_text(encoding="utf-8"))
        config = {key: copy.deepcopy(value) for key, value in base_config.items() if key != "lineage"}
        config["lineage"] = {
            "fullpage_manifest_sha256": v5_manifest_sha,
            "parent_v4_manifest_sha256": self.v4_manifest_sha,
            "tokenizer_sha256": self.tokenizer_sha256,
            "schema_sha256": self.schema_hashes,
            "source_sha256": self.source_hashes,
            "copy_catalog_sha256": self.source_hashes["configs/fullpage/source-bound-copy-v1.json"],
            "profile_sha256": base_config["lineage"]["profile_sha256"],
        }
        return config

    def _create_parent_state(self):
        parent_lineage = {
            "migration_kind": "position_extension",
            "source_checkpoint_sha256": SOURCE_CHECKPOINT_SHA256,
            "source_config_sha256": "7" * 64,
            "source_lineage": {"tokenizer_sha256": self.tokenizer_sha256},
            "tokenizer_sha256": self.tokenizer_sha256,
        }
        parent_config = {
            "mode": "sft",
            "scope": "main",
            "data_origin": "fullpage_curriculum",
            "human_reviewed": False,
            "dataset_dir": "data/processed/fullpage/v4",
            "block_size": 2048,
            "max_steps": 3600,
            "initial_checkpoint": INIT_PATH,
            "initial_checkpoint_sha256": INIT_SHA256,
            "model_config": MODEL_CONFIG,
            "lineage": {
                "fullpage_manifest_sha256": self.v4_manifest_sha,
                "tokenizer_sha256": self.tokenizer_sha256,
                "schema_sha256": self.schema_hashes,
                "initialization_parent": parent_lineage,
            },
        }
        warm_start = {
            "path": TRAIN024_PATH,
            "sha256": TRAIN024_SHA256,
            "run_id": "TRAIN-024",
            "global_step": 3600,
            "weights_only": True,
            "config_sha256": _json_sha(parent_config),
            "dataset_manifest_sha256": self.v4_manifest_sha,
        }
        self.config["initial_checkpoint"] = TRAIN024_PATH
        self.config["initial_checkpoint_sha256"] = TRAIN024_SHA256
        self.config["lineage"]["initialization_parent"] = parent_lineage
        self.config["lineage"]["warm_start_parent"] = warm_start
        return {
            "run_id": "TRAIN-024",
            "global_step": 3600,
            "weights_only": True,
            "model_config": MODEL_CONFIG,
            "config": parent_config,
        }

    def _patch_checkpoint_sha(self):
        def checkpoint_sha(path):
            normalized = Path(path).as_posix()
            if normalized.endswith(TRAIN024_PATH):
                return TRAIN024_SHA256
            if normalized.endswith(INIT_PATH):
                return INIT_SHA256
            return "0" * 64
        return patch("src.training.engine.checkpoint_sha256", side_effect=checkpoint_sha)

    def test_source_bound_dataset_lineage_is_verified_without_final_parsing(self):
        verify_source_bound_lineage(self.config, self.root)

    def test_source_bound_lineage_rejects_missing_or_changed_train024_pin(self):
        cases = (
            ("initial_checkpoint", None),
            ("initial_checkpoint", "checkpoints/UNVERIFIED/weights.pt"),
            ("initial_checkpoint_sha256", None),
            ("initial_checkpoint_sha256", "0" * 64),
        )
        for key, value in cases:
            with self.subTest(key=key, value=value):
                config = copy.deepcopy(self.config)
                if value is None:
                    config.pop(key)
                else:
                    config[key] = value
                with self.assertRaisesRegex(ValueError, "TRAIN-024"):
                    verify_source_bound_lineage(config, self.root)

    def test_source_bound_lineage_rejects_changed_frozen_training_settings(self):
        changes = (
            ("plan_batch_probability", lambda config: config.update(plan_batch_probability=0.2)),
            ("batch_size", lambda config: config.update(batch_size=4)),
            ("learning_rate", lambda config: config.update(learning_rate=1e-4)),
            ("performance", lambda config: config["performance"].update(tf32=False)),
            ("selection_rule", lambda config: config.update(selection_rule="changed rule")),
        )
        for expected_name, change in changes:
            with self.subTest(setting=expected_name):
                config = copy.deepcopy(self.config)
                change(config)
                with self.assertRaisesRegex(ValueError, expected_name):
                    verify_source_bound_lineage(config, self.root)

    def test_source_bound_lineage_rejects_changed_dataset_bytes(self):
        (self.v5_dir / "train.jsonl").write_bytes(b"changed training data\n")
        with self.assertRaises(ValueError):
            verify_source_bound_lineage(self.config, self.root)

    def test_source_bound_lineage_rejects_changed_training_source(self):
        path = self.root / "src/fullpage/source_bound_prompts.py"
        path.write_text("changed prompt code", encoding="utf-8")
        with self.assertRaises(ValueError):
            verify_source_bound_lineage(self.config, self.root)

    def test_source_bound_lineage_rejects_test_split(self):
        manifest = copy.deepcopy(self.v5_manifest)
        manifest["splits"] = ["train", "validation", "test"]
        manifest_path = self.v5_dir / "manifest.json"
        _write_json(manifest_path, manifest)
        self.config["lineage"]["fullpage_manifest_sha256"] = _file_info(manifest_path)["sha256"]
        with self.assertRaises(ValueError):
            verify_source_bound_lineage(self.config, self.root)

    def test_source_bound_lineage_rejects_sealed_hash_mismatch(self):
        manifest = copy.deepcopy(self.v5_manifest)
        manifest["sealed_sha256_after"]["test.jsonl"] = "0" * 64
        manifest_path = self.v5_dir / "manifest.json"
        _write_json(manifest_path, manifest)
        self.config["lineage"]["fullpage_manifest_sha256"] = _file_info(manifest_path)["sha256"]
        with self.assertRaises(ValueError):
            verify_source_bound_lineage(self.config, self.root)

    def test_exact_train024_weights_only_snapshot_is_accepted(self):
        with self._patch_checkpoint_sha():
            validate_source_bound_parent(self.parent_state, self.config, self.root)

    def test_wrong_parent_run_id_is_rejected(self):
        parent = copy.deepcopy(self.parent_state)
        parent["run_id"] = "TRAIN-022"
        with self._patch_checkpoint_sha(), self.assertRaises(ValueError):
            validate_source_bound_parent(parent, self.config, self.root)

    def test_wrong_parent_step_is_rejected(self):
        parent = copy.deepcopy(self.parent_state)
        parent["global_step"] = 1800
        with self._patch_checkpoint_sha(), self.assertRaises(ValueError):
            validate_source_bound_parent(parent, self.config, self.root)

    def test_full_optimizer_checkpoint_is_rejected(self):
        parent = copy.deepcopy(self.parent_state)
        parent["weights_only"] = False
        with self._patch_checkpoint_sha(), self.assertRaises(ValueError):
            validate_source_bound_parent(parent, self.config, self.root)

    def test_changed_parent_digest_is_rejected(self):
        config = copy.deepcopy(self.config)
        config["initial_checkpoint_sha256"] = "0" * 64
        with self._patch_checkpoint_sha(), self.assertRaises(ValueError):
            validate_source_bound_parent(self.parent_state, config, self.root)

    def test_wrong_parent_model_shape_is_rejected(self):
        parent = copy.deepcopy(self.parent_state)
        parent["model_config"]["block_size"] = 1024
        with self._patch_checkpoint_sha(), self.assertRaises(ValueError):
            validate_source_bound_parent(parent, self.config, self.root)

    def test_wrong_parent_v4_manifest_is_rejected(self):
        config = copy.deepcopy(self.config)
        config["lineage"]["parent_v4_manifest_sha256"] = "0" * 64
        with self._patch_checkpoint_sha(), self.assertRaises(ValueError):
            validate_source_bound_parent(self.parent_state, config, self.root)


if __name__ == "__main__":
    unittest.main()

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import torch
from torch import nn
from torch.utils.data import DataLoader

from src.models.minigpt import MiniGPT
from src.training.engine import ResumableBatchSampler, checkpoint_sha256, read_checkpoint, run_training, save_checkpoint, train_one_step
from tests.models.test_minigpt import tiny_config


def fixture(root):
    (root / "configs").mkdir()
    config = {"mode": "pretrain", "seed": 42, "device": "cpu", "precision": "fp32",
              "model_config": {**tiny_config(), "dropout": 0.2}, "max_steps": 4,
              "batch_size": 2, "gradient_accumulation": 1, "learning_rate": 0.001,
              "min_learning_rate": 0.0001, "warmup_steps": 1, "weight_decay": 0.01,
              "betas": [0.9, 0.95], "grad_clip": 1.0, "validation_interval": 2,
              "checkpoint_interval": 2, "validation_batches": 2, "log_interval": 1,
              "reserve_free_bytes": 0, "lineage": {"fixture": "f" * 64}}
    path = root / "configs/train.json"
    path.write_text(json.dumps(config))
    rows = [{"input_ids": torch.tensor([i, 2, 3, 4]), "labels": torch.tensor([2, 3, 4, i])} for i in range(1, 6)]
    train = DataLoader(rows, batch_sampler=ResumableBatchSampler(len(rows), 2, 42), num_workers=0)
    validation = DataLoader(rows, batch_size=2, num_workers=0)
    return path, train, validation


class EngineTests(unittest.TestCase):
    def test_source_bound_resume_rejects_non_train025_path_before_checkpoint_read_or_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path, train, validation = fixture(root)
            config = json.loads(config_path.read_text())
            config.update({"mode": "sft", "data_origin": "fullpage_curriculum",
                           "fullpage_contract_version": "source-bound-v1", "scope": "main",
                           "human_reviewed": False, "dataset_dir": "data/processed/fullpage/v5"})
            config_path.write_text(json.dumps(config))
            with patch("src.fullpage.lineage.verify_source_bound_training_settings"), \
                    patch("src.training.engine.read_checkpoint") as read_checkpoint:
                with self.assertRaisesRegex(ValueError, "TRAIN-025"):
                    run_training(config_path, train, validation, "TRAIN-026",
                                 resume=root / "checkpoints/TRAIN-024/last.pt", root=root)
            read_checkpoint.assert_not_called()
            self.assertFalse((root / "checkpoints/TRAIN-026").exists())
            self.assertFalse((root / "reports/training/TRAIN-026.json").exists())

    def test_source_bound_fresh_run_requires_pinned_parent_before_creating_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path, train, val = fixture(root)
            config = json.loads(config_path.read_text())
            config.update(fullpage_contract_version="source-bound-v1", data_origin="fullpage_curriculum")
            config.pop("initial_checkpoint", None)
            config.pop("initial_checkpoint_sha256", None)
            config_path.write_text(json.dumps(config))

            with self.assertRaisesRegex(ValueError, "TRAIN-024"):
                run_training(config_path, train, val, "TRAIN-TEST-MISSING-PARENT", stop_after=0, root=root)

            self.assertFalse((root / "checkpoints/TRAIN-TEST-MISSING-PARENT").exists())
            self.assertFalse((root / "reports/training/TRAIN-TEST-MISSING-PARENT.json").exists())

    def test_source_bound_fresh_run_rejects_changed_frozen_settings_before_parent_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path, train, val = fixture(root)
            config = json.loads(config_path.read_text())
            from src.fullpage.lineage import TRAIN024_PATH, TRAIN024_SHA256
            config.update(fullpage_contract_version="source-bound-v1", data_origin="fullpage_curriculum",
                          initial_checkpoint=TRAIN024_PATH, initial_checkpoint_sha256=TRAIN024_SHA256,
                          plan_batch_probability=0.2)
            config_path.write_text(json.dumps(config))

            with self.assertRaisesRegex(ValueError, "plan_batch_probability"):
                run_training(config_path, train, val, "TRAIN-TEST-CHANGED-SETTINGS", stop_after=0, root=root)

            self.assertFalse((root / "checkpoints/TRAIN-TEST-CHANGED-SETTINGS").exists())

    def test_legacy_initializer_keeps_its_existing_optimizer_then_weights_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path, train, val = fixture(root)
            config = json.loads(config_path.read_text())
            parent_model = MiniGPT(config["model_config"])
            with torch.no_grad():
                for parameter in parent_model.parameters():
                    parameter.fill_(0.25)
            parent_path = root / "checkpoints/PARENT/weights.pt"
            parent_path.parent.mkdir(parents=True)
            save_checkpoint(parent_path, {
                "format_version": 1,
                "run_id": "TRAIN-LEGACY-PARENT",
                "model": parent_model.state_dict(),
                "model_config": parent_model.config,
                "global_step": 1,
                "config": {"lineage": config["lineage"]},
            })
            config["initial_checkpoint"] = parent_path.relative_to(root).as_posix()
            config["initial_checkpoint_sha256"] = checkpoint_sha256(parent_path)
            config_path.write_text(json.dumps(config))

            from src.training import engine
            real_load_checkpoint = engine.load_checkpoint
            real_adamw = torch.optim.AdamW
            events = []

            def load_and_record(*args, **kwargs):
                state = real_load_checkpoint(*args, **kwargs)
                if Path(args[0]).resolve() == parent_path.resolve():
                    events.append("parent_weights_loaded")
                return state

            def create_optimizer(*args, **kwargs):
                events.append("optimizer_created")
                return real_adamw(*args, **kwargs)

            with patch("src.training.lineage.validate_initial_checkpoint") as validate_parent, \
                    patch("src.training.engine.load_checkpoint", side_effect=load_and_record), \
                    patch("src.training.engine.torch.optim.AdamW", side_effect=create_optimizer):
                run_training(config_path, train, val, "TRAIN-TEST-LEGACY-INIT", stop_after=0, root=root)

            self.assertEqual(events, ["optimizer_created", "parent_weights_loaded"])
            validate_parent.assert_called_once()
            result = read_checkpoint(root / "checkpoints/TRAIN-TEST-LEGACY-INIT/last.pt")
            for tensor in result["model"].values():
                torch.testing.assert_close(tensor, torch.full_like(tensor, 0.25), rtol=0, atol=0)

    def test_source_bound_warm_start_loads_only_weights_before_fresh_training_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path, train, val = fixture(root)
            config = json.loads(config_path.read_text())
            from src.fullpage.lineage import TRAIN024_SHA256
            config.update({
                "mode": "sft",
                "data_origin": "fullpage_curriculum",
                "fullpage_contract_version": "source-bound-v1",
                "scope": "main",
                "human_reviewed": False,
                "dataset_dir": "data/processed/fullpage/v5",
                "storage_phase_id": "warm-start-test",
            })
            config_path.write_text(json.dumps(config))

            parent_model = MiniGPT(config["model_config"])
            with torch.no_grad():
                for parameter in parent_model.parameters():
                    parameter.fill_(0.125)
            torch.manual_seed(999)
            parent_rng = torch.get_rng_state().clone()
            parent_path = root / "checkpoints/FULLPAGE-V4/TRAIN-024-step3600.pt"
            parent_path.parent.mkdir(parents=True)
            save_checkpoint(parent_path, {
                "format_version": 1,
                "run_id": "TRAIN-024",
                "model": parent_model.state_dict(),
                "model_config": parent_model.config,
                "global_step": 3600,
                "config": {"data_origin": "fullpage_curriculum", "dataset_dir": config["dataset_dir"],
                           "reserve_free_bytes": 0, "storage_phase_id": "warm-start-test", "lineage": {}},
                "weights_only": True,
                "optimizer": {"state": {"parent-only": {"step": torch.tensor(99)}}},
                "scheduler": {"last_epoch": 99, "_step_count": 100},
                "sampler": {"size": 5, "batch_size": 2, "seed": 42, "cursor": 9},
                "rng": {"torch": parent_rng},
            })
            config["initial_checkpoint"] = parent_path.relative_to(root).as_posix()
            config["initial_checkpoint_sha256"] = TRAIN024_SHA256
            config_path.write_text(json.dumps(config))

            from src.training import engine
            real_load_checkpoint = engine.load_checkpoint
            real_adamw = torch.optim.AdamW
            events = []

            def load_and_record(*args, **kwargs):
                events.append("load_checkpoint")
                state = real_load_checkpoint(*args, **kwargs)
                if Path(args[0]).resolve() == parent_path.resolve():
                    events.append("parent_weights_loaded")
                return state

            def create_fresh_optimizer(*args, **kwargs):
                events.append("optimizer_created")
                return real_adamw(*args, **kwargs)

            with patch("src.fullpage.lineage.validate_source_bound_parent", create=True) as validate_parent, \
                    patch("src.fullpage.lineage.verify_source_bound_training_settings", create=True), \
                    patch("src.fullpage.lineage.validate_fullpage_parent"), \
                    patch("src.training.engine.load_checkpoint", side_effect=load_and_record), \
                    patch("src.training.engine.torch.optim.AdamW", side_effect=create_fresh_optimizer):
                run_training(config_path, train, val, "TRAIN-025", stop_after=0, root=root)

            self.assertEqual(events, ["load_checkpoint", "parent_weights_loaded", "optimizer_created"])
            validate_parent.assert_called_once()
            result = read_checkpoint(root / "checkpoints/TRAIN-025/last.pt")
            self.assertEqual(result["global_step"], 0)
            self.assertEqual(result["sampler"]["cursor"], 0)
            self.assertEqual(result["optimizer"]["state"], {})
            self.assertNotEqual(result["scheduler"]["last_epoch"], 99)
            self.assertFalse(torch.equal(result["rng"]["torch"], parent_rng))
            for tensor in result["model"].values():
                torch.testing.assert_close(tensor, torch.full_like(tensor, 0.125), rtol=0, atol=0)

    def test_source_bound_fresh_train026_is_rejected_before_train024_read_or_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path, train, val = fixture(root)
            from src.fullpage.lineage import TRAIN024_PATH, TRAIN024_SHA256
            config = json.loads(config_path.read_text())
            config.update({
                "mode": "sft",
                "data_origin": "fullpage_curriculum",
                "fullpage_contract_version": "source-bound-v1",
                "scope": "main",
                "human_reviewed": False,
                "dataset_dir": "data/processed/fullpage/v5",
                "initial_checkpoint": TRAIN024_PATH,
                "initial_checkpoint_sha256": TRAIN024_SHA256,
            })
            config_path.write_text(json.dumps(config))

            with patch("src.fullpage.lineage.verify_source_bound_training_settings"), \
                    patch("src.training.engine.read_checkpoint", side_effect=AssertionError("TRAIN-024 must not be read")) as read_checkpoint, \
                    patch("src.training.engine.read_checkpoint_with_digest", side_effect=AssertionError("TRAIN-024 must not be read")) as read_checkpoint_digest:
                with self.assertRaisesRegex(ValueError, "TRAIN-025"):
                    run_training(config_path, train, val, "TRAIN-026", stop_after=0, root=root)

            read_checkpoint.assert_not_called()
            read_checkpoint_digest.assert_not_called()
            self.assertFalse((root / "checkpoints/TRAIN-026").exists())
            self.assertFalse((root / "reports/training/TRAIN-026.json").exists())

    def test_sft_masks_prompt_and_does_not_shift_labels_again(self):
        class Logits(nn.Module):
            def __init__(self):
                super().__init__()
                self.value = nn.Parameter(torch.tensor([[[9., 0., 0.], [1., 2., 3.]]]))
            def forward(self, inputs):
                return self.value
        model = Logits()
        optimizer = torch.optim.SGD(model.parameters(), lr=0.1)
        before = model.value.detach().clone()
        report = train_one_step(model, {"input_ids": torch.tensor([[0, 1]]), "labels": torch.tensor([[-100, 2]])}, optimizer, None, "sft")
        self.assertAlmostEqual(report["loss"], 0.40760595, places=6)
        self.assertEqual(report["valid_tokens"], 1)
        self.assertTrue(torch.equal(model.value[0, 0], before[0, 0]))
        self.assertFalse(torch.equal(model.value[0, 1], before[0, 1]))

    def test_nonfinite_loss_is_rejected_before_optimizer_update(self):
        model = MiniGPT(tiny_config())
        with torch.no_grad():
            model.token_embedding.weight.fill_(float("nan"))
        optimizer = torch.optim.AdamW(model.parameters())
        with self.assertRaises(FloatingPointError):
            train_one_step(model, {"input_ids": torch.tensor([[1, 2]]), "labels": torch.tensor([[2, 3]])}, optimizer, None, "pretrain")
        self.assertEqual(len(optimizer.state), 0)

    def test_simulated_oom_preserves_last_committed_checkpoint_and_failure_log(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path, train, val = fixture(root)
            with patch("src.training.engine.train_one_step", side_effect=torch.cuda.OutOfMemoryError("SIMULATED_TEST_OOM")):
                with self.assertRaises(torch.cuda.OutOfMemoryError):
                    run_training(path, train, val, "TRAIN-TEST-FAIL")
            summary = json.loads((root / "reports/training/TRAIN-TEST-FAIL.json").read_text())
            self.assertEqual(summary["status"], "failed")
            self.assertEqual(summary["last_committed_step"], 0)
            self.assertIn("SIMULATED_TEST_OOM", summary["error"])
            self.assertTrue((root / "checkpoints/TRAIN-TEST-FAIL/last.pt").exists())


if __name__ == "__main__":
    unittest.main()

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import torch
from torch import nn
from torch.utils.data import DataLoader

from src.models.minigpt import MiniGPT
from src.training.engine import ResumableBatchSampler, run_training, train_one_step
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

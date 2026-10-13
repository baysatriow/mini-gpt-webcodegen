import tempfile
import unittest
from pathlib import Path

import torch

from src.models.minigpt import MiniGPT
from src.training.engine import load_checkpoint, run_training, read_checkpoint
from tests.training.test_engine import fixture


class CheckpointTests(unittest.TestCase):
    def test_resume_restores_optimizer_scheduler_rng_and_next_batch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path, train, val = fixture(root)
            full = run_training(path, train, val, "TRAIN-FULL")
            path, train, val = path, *fixture_loaders(path)
            interrupted = run_training(path, train, val, "TRAIN-PART", stop_after=2)
            train, val = fixture_loaders(path)
            resumed = run_training(path, train, val, "TRAIN-RESUME", resume=interrupted)
            first = read_checkpoint(full)
            second = read_checkpoint(resumed)
            self.assertEqual(second["global_step"], 4)
            self.assertEqual(first["sampler"], second["sampler"])
            self.assertEqual(first["scheduler"], second["scheduler"])
            for name in first["model"]:
                torch.testing.assert_close(first["model"][name], second["model"][name], rtol=0, atol=0)
            for key in first["optimizer"]["state"]:
                for name in first["optimizer"]["state"][key]:
                    torch.testing.assert_close(first["optimizer"]["state"][key][name], second["optimizer"]["state"][key][name], rtol=0, atol=0)

    def test_corrupted_checkpoint_is_refused_before_model_mutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path, train, val = fixture(root)
            checkpoint = run_training(path, train, val, "TRAIN-TEST", stop_after=1)
            model = MiniGPT(__import__("json").loads(path.read_text())["model_config"])
            before = {name: value.clone() for name, value in model.state_dict().items()}
            with checkpoint.open("ab") as handle:
                handle.write(b"bad")
            with self.assertRaisesRegex(ValueError, "checksum"):
                load_checkpoint(checkpoint, model, None, None)
            self.assertTrue(all(torch.equal(before[name], value) for name, value in model.state_dict().items()))


def fixture_loaders(path):
    from torch.utils.data import DataLoader
    from src.training.engine import ResumableBatchSampler
    rows = [{"input_ids": torch.tensor([i, 2, 3, 4]), "labels": torch.tensor([2, 3, 4, i])} for i in range(1, 6)]
    return DataLoader(rows, batch_sampler=ResumableBatchSampler(5, 2, 42), num_workers=0), DataLoader(rows, batch_size=2)


if __name__ == "__main__":
    unittest.main()

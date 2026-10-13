import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.training.engine import read_checkpoint, run_training, save_checkpoint
from tests.training.test_engine import fixture
from tests.training.test_checkpoint import fixture_loaders


class ReviewCheckpointTests(unittest.TestCase):
    def test_best_generations_referenced_by_last_survive_more_frequent_validation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path, train, val = fixture(root)
            config = json.loads(path.read_text())
            config.update(validation_interval=1, checkpoint_interval=4)
            path.write_text(json.dumps(config))
            original_save = save_checkpoint
            def fail_last_at_four(target, state):
                if target.name == "last.pt" and state["global_step"] == 4:
                    raise OSError("simulated last commit failure")
                return original_save(target, state)
            metrics = [{"loss": loss, "perplexity": 1., "valid_tokens": 16, "batches": 1}
                       for loss in [5., 4., 3., 2., 1.]]
            with patch("src.training.engine.evaluate_tokens", side_effect=metrics), patch("src.training.engine.save_checkpoint", side_effect=fail_last_at_four):
                with self.assertRaises(OSError):
                    run_training(path, train, val, "TRAIN-FAIL-LAST")
            last = read_checkpoint(root / "checkpoints/TRAIN-FAIL-LAST/last.pt")
            self.assertEqual(last["global_step"], 0)
            best = read_checkpoint(root / last["best_checkpoint"]["path"])
            self.assertEqual(best["global_step"], 0)
            self.assertEqual(best["best_validation_loss"], 5.)

    def test_resume_preserves_earlier_best_weights_and_actual_validation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path, train, val = fixture(root)
            metrics = [{"loss": loss, "perplexity": 1., "valid_tokens": 16, "batches": 1}
                       for loss in [1., 2., 2., 1.5]]
            with patch("src.training.engine.evaluate_tokens", side_effect=metrics):
                last = run_training(path, train, val, "TRAIN-PARENT", stop_after=2)
                expected = read_checkpoint(last.parent / "best.pt")
                train, val = fixture_loaders(path)
                result = run_training(path, train, val, "TRAIN-RESUMED", resume=last)
            best = read_checkpoint(result.parent / "best.pt")
            self.assertEqual(best["global_step"], 0)
            self.assertEqual(best["best_validation_loss"], 1.)
            for name in expected["model"]:
                self.assertTrue(__import__("torch").equal(expected["model"][name], best["model"][name]))

    def test_every_failed_save_stage_retains_previous_committed_payload(self):
        for stage in ["payload", "manifest", "commit"]:
            with self.subTest(stage=stage), tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "last.pt"
                first = {"run_id": "FIRST", "global_step": 1, "config": {"lineage": {}}, "value": 7}
                save_checkpoint(path, first)
                replacement = {**first, "global_step": 2, "value": 99}
                if stage == "payload":
                    failure = patch("src.training.engine.torch.save", side_effect=OSError("payload failure"))
                elif stage == "manifest":
                    failure = patch("src.training.engine.write_manifest", side_effect=OSError("manifest failure"))
                else:
                    import os
                    replace = os.replace
                    def fail_commit(source, target):
                        if Path(target) == path:
                            raise OSError("commit failure")
                        return replace(source, target)
                    failure = patch("src.training.engine.os.replace", side_effect=fail_commit)
                with failure, self.assertRaises(OSError):
                    save_checkpoint(path, replacement)
                self.assertEqual(read_checkpoint(path)["value"], 7)
                self.assertEqual(read_checkpoint(path)["global_step"], 1)


if __name__ == "__main__":
    unittest.main()

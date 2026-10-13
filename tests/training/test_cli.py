import json
import tempfile
import unittest
from pathlib import Path

from qa.train_minigpt import prepare_training_data


class TrainingCLITests(unittest.TestCase):
    def test_draft_sft_cannot_reach_a_training_loader(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "data/manifests").mkdir(parents=True)
            (root / "data/manifests/pipeline_summary.json").write_text(json.dumps({"status": "complete", "sft": {"status": "awaiting_review"}}))
            with self.assertRaisesRegex(ValueError, "reviewed"):
                prepare_training_data(root, {"mode": "sft"})


if __name__ == "__main__":
    unittest.main()

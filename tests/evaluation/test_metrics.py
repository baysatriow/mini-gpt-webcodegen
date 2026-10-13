import json
import math
import unittest

import torch

from src.evaluation.metrics import token_metrics
from src.evaluation.generate import evaluate_outputs
from tests.data.test_schema import valid_spec


class EvaluationTests(unittest.TestCase):
    def test_loss_ignores_masked_positions_and_perplexity_is_token_mean(self):
        logits = torch.tensor([[[0., 0.], [100., -100.], [0., 0.]]])
        result = token_metrics(logits, torch.tensor([[0, -100, 1]]))
        self.assertEqual(result["valid_tokens"], 2)
        self.assertAlmostEqual(result["loss"], math.log(2), places=6)
        self.assertAlmostEqual(result["perplexity"], 2, places=6)
        with self.assertRaises(ValueError):
            token_metrics(logits, torch.tensor([[-100, -100, -100]]))

    def test_bad_json_does_not_abort_other_outputs_and_schema_failures_are_separate(self):
        invalid = valid_spec()
        invalid["style_mode"] = "bootstrap"
        result = evaluate_outputs([{"prompt_id": "broken", "raw_output": "{"},
                                   {"prompt_id": "valid", "raw_output": json.dumps(valid_spec())},
                                   {"prompt_id": "invalid_schema", "raw_output": json.dumps(invalid)}])
        self.assertEqual(result["parseable"], 2)
        self.assertEqual(result["schema_valid"], 1)
        self.assertEqual(result["records"][0]["parse_status"], "failed")
        self.assertTrue(result["records"][2]["schema_errors"])
        self.assertIsNone(result["records"][1]["manual_quality_score"])


if __name__ == "__main__":
    unittest.main()

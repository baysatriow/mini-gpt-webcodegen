import json
import unittest

from qa.request_extract_scoring import score_request_extract


class RequestExtractEvaluationTests(unittest.TestCase):
    def test_schema_invalid_prediction_does_not_abort_scoring_or_pass_quality_gate(self):
        valid_target = {
            "fact_mentions": [{"kind": "name", "value": "Kedai Demo"}],
            "setting_mentions": [],
            "business_status_mentions": [],
            "capability_mentions": [],
            "out_of_catalog_mentions": [],
            "corrections": [],
        }
        valid_record = {
            "example_id": "row-valid",
            "prediction": valid_target,
            "target": valid_target,
            "schema_valid": True,
            "source_valid": True,
            "exact_match": True,
            "seconds": 0.01,
        }
        invalid_record = {
            "example_id": "row-001",
            "prediction": {"fact_mentions": [{"context": "not a valid fact mention"}]},
            "target": {
                "fact_mentions": [],
                "setting_mentions": [],
                "business_status_mentions": [],
                "capability_mentions": [],
                "out_of_catalog_mentions": [],
                "corrections": [],
            },
            "schema_valid": False,
            "source_valid": False,
            "exact_match": False,
            "seconds": 0.01,
        }
        row_by_id = {
            "row-valid": {
                "family_id": "family-valid",
                "scenario": "input_incomplete",
                "prompt_pattern_id": "pattern-valid",
                "scope": "business_scalars",
                "target": json.dumps(valid_target),
            },
            "row-001": {
                "family_id": "family-001",
                "scenario": "input_incomplete",
                "prompt_pattern_id": "pattern-001",
                "scope": "business_scalars",
                "target": "{\"fact_mentions\":[],\"setting_mentions\":[],\"business_status_mentions\":[],\"capability_mentions\":[],\"out_of_catalog_mentions\":[],\"corrections\":[]}",
            }
        }

        report = score_request_extract(
            [valid_record, invalid_record],
            row_by_id,
            {"extraction_scopes": ["business_scalars"]},
            "a" * 64,
            "b" * 64,
            "c" * 64,
            0.01,
        )

        self.assertEqual(report["schema_invalid_rows"], 1)
        self.assertEqual(report["total_exact_item_precision"], 1.0)
        self.assertEqual(report["total_exact_item_recall"], 1.0)
        self.assertFalse(report["raw_output_quality_gate"])


if __name__ == "__main__":
    unittest.main()

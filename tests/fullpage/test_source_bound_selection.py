import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from qa.select_fullpage_v5 import _verify_train026_resume_lineage, select_v5_candidate
from src.fullpage.lineage import TRAIN025_PATH, TRAIN025_REPORT_PATH


REQUESTS_SHA256 = "a" * 64
DATASET_MANIFEST_SHA256 = "b" * 64


def development_candidate(complete, validation_loss, step):
    run_id = "TRAIN-025" if step == 1800 else "TRAIN-026"
    status = "stopped_at_limit" if step == 1800 else "completed"
    generation_report = {
        "scope": "development",
        "final_used": False,
        "fullpage_contract_version": "source-bound-v1",
        "total": 80,
        "count": 80,
        "complete": complete,
        "required_roles": complete,
        "model_gate": complete >= 76,
        "accepted_facts_links_assets_valid": True,
        "requests_sha256": REQUESTS_SHA256,
        "dataset_manifest_sha256": DATASET_MANIFEST_SHA256,
        "checkpoint_sha256": "e" * 64,
        "source_sha256": {"src/fullpage/generation.py": "c" * 64},
    }
    training_report = {
        "run_id": run_id,
        "status": status,
        "global_step": step,
        "final_validation": {"loss": validation_loss},
    }
    return {"step": step, "generation_report": generation_report, "training_report": training_report}


class SourceBoundSelectionTests(unittest.TestCase):
    def test_train026_selection_requires_the_verified_train025_resume_parent(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config = {"experiment": "frozen-v5"}
            config_sha256 = "d" * 64
            checkpoint_sha256 = "a" * 64
            parent_path = root / TRAIN025_PATH
            parent_path.parent.mkdir(parents=True)
            parent_path.write_bytes(b"verified checkpoint fixture")
            report_path = root / TRAIN025_REPORT_PATH
            report_path.parent.mkdir(parents=True)
            parent_report = {
                "run_id": "TRAIN-025",
                "status": "stopped_at_limit",
                "global_step": 1800,
                "last_committed_step": 1800,
                "config": config,
                "config_sha256": config_sha256,
                "resume_parent": None,
                "resume_parent_sha256": None,
                "final_checkpoint_sha256": checkpoint_sha256,
            }
            report_path.write_text(json.dumps(parent_report), encoding="utf-8")
            training_report = {
                "run_id": "TRAIN-026",
                "status": "completed",
                "global_step": 3600,
                "resume_parent": TRAIN025_PATH,
                "resume_parent_sha256": checkpoint_sha256,
            }
            with patch("qa.select_fullpage_v5.checkpoint_sha256", return_value=checkpoint_sha256):
                _verify_train026_resume_lineage(root, training_report, config, config_sha256)
                for key, value in (("resume_parent", "checkpoints/TRAIN-024/last.pt"),
                                   ("resume_parent_sha256", "c" * 64)):
                    with self.subTest(field=key):
                        invalid = copy.deepcopy(training_report)
                        invalid[key] = value
                        with self.assertRaises(ValueError):
                            _verify_train026_resume_lineage(root, invalid, config, config_sha256)

    def test_complete_page_count_precedes_cross_entropy(self):
        candidates = [development_candidate(79, 1.4, 1800), development_candidate(78, 0.8, 3600)]
        result = select_v5_candidate(candidates)
        self.assertEqual(1800, result["selected"]["step"])
        self.assertTrue(result["model_gate_passed"])

    def test_cross_entropy_breaks_a_complete_page_tie(self):
        candidates = [development_candidate(78, 1.1, 1800), development_candidate(78, 0.9, 3600)]
        result = select_v5_candidate(candidates)
        self.assertEqual(3600, result["selected"]["step"])
        self.assertTrue(result["model_gate_passed"])

    def test_gate_requires_at_least_76_of_80(self):
        candidates = [development_candidate(75, 1.2, 1800), development_candidate(74, 0.8, 3600)]
        result = select_v5_candidate(candidates)
        self.assertFalse(result["model_gate_passed"])
        self.assertEqual(75, result["selected"]["generation_report"]["complete"])

    def test_candidates_must_use_the_same_development_requests_and_manifest(self):
        candidates = [development_candidate(78, 1.0, 1800), development_candidate(79, 0.9, 3600)]
        candidates[1]["generation_report"]["requests_sha256"] = "d" * 64
        with self.assertRaises(ValueError):
            select_v5_candidate(candidates)

    def test_invalid_fact_acceptance_cannot_pass_gate(self):
        candidate = development_candidate(80, 0.5, 1800)
        candidate["generation_report"]["accepted_facts_links_assets_valid"] = False
        result = select_v5_candidate([candidate, development_candidate(79, 0.6, 3600)])
        self.assertFalse(result["model_gate_passed"])

    def test_reports_must_match_the_exact_step_and_run_identity(self):
        candidate = development_candidate(80, 0.5, 1800)
        candidate["training_report"]["run_id"] = "TRAIN-026"
        with self.assertRaises(ValueError):
            select_v5_candidate([candidate, development_candidate(79, 0.6, 3600)])

    def test_input_reports_are_not_mutated(self):
        candidates = [development_candidate(79, 0.9, 1800), development_candidate(78, 0.8, 3600)]
        original = copy.deepcopy(candidates)
        select_v5_candidate(candidates)
        self.assertEqual(original, candidates)


if __name__ == "__main__":
    unittest.main()

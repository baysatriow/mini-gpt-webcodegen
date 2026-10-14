import copy
import unittest
from pathlib import Path

from src.fullpage.lineage import (
    TRAIN025_PATH,
    TRAIN025_REPORT_PATH,
    validate_source_bound_resume_path,
    validate_source_bound_resume_state,
    validate_source_bound_train025_report,
)


class SourceBoundResumeTests(unittest.TestCase):
    def setUp(self):
        self.root = Path("C:/fixture/project")
        self.config_path = self.root / "configs/fullpage/training-improvement-v5.json"
        self.config = {"experiment": "frozen-v5"}
        self.config_sha256 = "b" * 64
        self.checkpoint_sha256 = "a" * 64
        self.parent_state = {
            "run_id": "TRAIN-025",
            "global_step": 1800,
            "weights_only": False,
            "config": copy.deepcopy(self.config),
            "optimizer": {},
            "scheduler": {},
            "sampler": {},
            "rng": {},
        }
        self.parent_report = {
            "run_id": "TRAIN-025",
            "status": "stopped_at_limit",
            "global_step": 1800,
            "last_committed_step": 1800,
            "config": copy.deepcopy(self.config),
            "config_sha256": self.config_sha256,
            "resume_parent": None,
            "resume_parent_sha256": None,
            "final_checkpoint_sha256": self.checkpoint_sha256,
        }

    def test_only_train026_can_resume_exact_train025_path(self):
        path = validate_source_bound_resume_path(
            "TRAIN-026", TRAIN025_PATH, self.root,
        )
        self.assertEqual((self.root / TRAIN025_PATH).resolve(), path)
        with self.assertRaisesRegex(ValueError, "TRAIN-025"):
            validate_source_bound_resume_path(
                "TRAIN-026", "checkpoints/TRAIN-024/last.pt", self.root,
            )
        with self.assertRaisesRegex(ValueError, "TRAIN-026"):
            validate_source_bound_resume_path("TRAIN-027", TRAIN025_PATH, self.root)

    def test_train025_report_and_checkpoint_digest_must_match_frozen_config(self):
        validate_source_bound_train025_report(
            self.parent_report, self.config, self.config_sha256, self.checkpoint_sha256,
        )
        invalid = copy.deepcopy(self.parent_report)
        invalid["final_checkpoint_sha256"] = "c" * 64
        with self.assertRaisesRegex(ValueError, "checkpoint"):
            validate_source_bound_train025_report(
                invalid, self.config, self.config_sha256, self.checkpoint_sha256,
            )

    def test_train025_report_rejects_wrong_identity_or_prior_resume(self):
        cases = (
            ("run_id", "TRAIN-024"),
            ("status", "completed"),
            ("global_step", 3600),
            ("last_committed_step", 1799),
            ("config_sha256", "c" * 64),
            ("resume_parent", TRAIN025_PATH),
            ("resume_parent_sha256", self.checkpoint_sha256),
        )
        for key, value in cases:
            with self.subTest(field=key):
                invalid = copy.deepcopy(self.parent_report)
                invalid[key] = value
                with self.assertRaises(ValueError):
                    validate_source_bound_train025_report(
                        invalid, self.config, self.config_sha256, self.checkpoint_sha256,
                    )

    def test_train025_report_rejects_different_config(self):
        invalid = copy.deepcopy(self.parent_report)
        invalid["config"] = {"experiment": "changed"}
        with self.assertRaisesRegex(ValueError, "config"):
            validate_source_bound_train025_report(
                invalid, self.config, self.config_sha256, self.checkpoint_sha256,
            )

    def test_checkpoint_state_must_be_a_full_train025_resume(self):
        validate_source_bound_resume_state(self.parent_state, self.config)
        for field, value in (("run_id", "TRAIN-024"), ("global_step", 1600),
                             ("weights_only", True), ("config", {"changed": True}),
                             ("optimizer", None), ("scheduler", None),
                             ("sampler", None), ("rng", None)):
            with self.subTest(field=field):
                invalid = copy.deepcopy(self.parent_state)
                invalid[field] = value
                with self.assertRaises(ValueError):
                    validate_source_bound_resume_state(invalid, self.config)


if __name__ == "__main__":
    unittest.main()

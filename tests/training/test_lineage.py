import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.training.lineage import validate_initial_checkpoint, verify_checkpoint_lineage, verify_production_prompts


def descriptor(letter="a"):
    return {"sha256": letter * 64, "version": 1, "tokenizer_sha256": "t"*64}


def checkpoint(mode="pretrain", fingerprint=None):
    return {"global_step": 2, "config": {"mode": mode, "lineage": {
        "tokenizer_sha256": "t"*64, "smoke": False,
        "pretrain_fingerprint": fingerprint or descriptor()}}}


class LineageTests(unittest.TestCase):
    def test_legacy_binding_preserves_weights_and_requires_recorded_pipeline_snapshot(self):
        from src.training.lineage import bind_legacy_checkpoint
        import torch
        state = checkpoint()
        state["config"]["lineage"].pop("pretrain_fingerprint")
        state["model"] = {"weight": torch.tensor([1., 2.])}
        with patch("src.training.lineage.verify_checkpoint_lineage", return_value=descriptor()):
            bound = bind_legacy_checkpoint(state, Path("unused"), {})
        self.assertNotIn("pretrain_fingerprint", state["config"]["lineage"])
        self.assertEqual(bound["config"]["lineage"]["pretrain_fingerprint"], descriptor())
        torch.testing.assert_close(state["model"]["weight"], bound["model"]["weight"], rtol=0, atol=0)
        with patch("src.training.lineage.verify_checkpoint_lineage", side_effect=ValueError("unproven snapshot")):
            with self.assertRaises(ValueError):
                bind_legacy_checkpoint(state, Path("unused"), {})

    def test_sft_initializer_rejects_wrong_corpus_phase_and_untrained_or_smoke_parent(self):
        config = {"mode": "sft", "lineage": {"tokenizer_sha256": "t"*64, "pretrain_fingerprint": descriptor()}}
        for field in ["fingerprint", "phase", "zero_steps", "smoke"]:
            parent = checkpoint()
            if field == "fingerprint": parent["config"]["lineage"]["pretrain_fingerprint"] = descriptor("b")
            if field == "phase": parent["config"]["mode"] = "sft"
            if field == "zero_steps": parent["global_step"] = 0
            if field == "smoke": parent["config"]["lineage"]["smoke"] = True
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate_initial_checkpoint(parent, config, Path("unused"), {})
        validate_initial_checkpoint(checkpoint(), config, Path("unused"), {})

    def test_heldout_evaluation_rejects_different_assignment_even_with_same_tokenizer(self):
        with patch("src.training.lineage.pretrain_descriptor", return_value=descriptor("b")):
            with self.assertRaisesRegex(ValueError, "pretraining"):
                verify_checkpoint_lineage(checkpoint(), Path("unused"), {})

    def test_production_prompts_require_actual_reviewed_test_membership(self):
        state = checkpoint("sft")
        state["config"]["lineage"].update(sft_fingerprint={"sha256": "s"*64},
            pretraining_parent={"phase": "pretrain", "global_step": 2, "pretrain_fingerprint": descriptor()})
        actual = {"source_row_id": "TEST_ROW", "source_group_id": "TEST_FAMILY", "prompt": "uji",
                  "target_spec": {}, "annotation_status": "reviewed", "reviewer": "Human", "split": "test"}
        fake = {**actual, "source_row_id": "TRAIN_ROW", "source_group_id": "TRAIN_FAMILY"}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            directory = root / "data/processed/sft"
            directory.mkdir(parents=True)
            (directory / "test.jsonl").write_text(json.dumps(actual)+"\n", encoding="utf-8")
            with patch("src.training.lineage.verify_checkpoint_lineage"), patch("src.training.lineage.verify_sft_data"):
                for rows in [[fake], [{**actual, "prompt": "isi diubah"}], [{**actual, "reviewer": ""}], [actual, actual]]:
                    with self.subTest(rows=rows), self.assertRaises(ValueError):
                        verify_production_prompts(state, rows, root, {})
                verify_production_prompts(state, [actual], root, {})

    def test_sft_checkpoint_requires_pretraining_history(self):
        state = checkpoint("sft")
        with patch("src.training.lineage.pretrain_descriptor", return_value=descriptor()):
            with self.assertRaisesRegex(ValueError, "parent"):
                verify_checkpoint_lineage(state, Path("unused"), {})


if __name__ == "__main__":
    unittest.main()

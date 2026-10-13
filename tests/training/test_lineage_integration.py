"""Synthetic reviewed fixtures only; no production annotation changes."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.data import pipeline
from src.data.sources import download_source, sha256_file
from src.data.normalize import read_jsonl, structural_group
from src.training.lineage import pretrain_descriptor, validate_initial_checkpoint, verify_checkpoint_lineage, verify_production_prompts
from qa.train_minigpt import prepare_training_data
from tests.data.test_normalize import source_row, annotation


class LineageIntegrationTests(unittest.TestCase):
    def test_corpus_fingerprint_survives_annotation_preparation_and_test_membership_is_verified(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "configs").mkdir()
            source = {"id": "websight_v01", "limit": 30, "revision": "a"*40, "license_id": "cc-by-4.0"}
            rows = [{**source_row(), "source_row_id": f"row-{i}",
                     "text": "<html><body>"+"<div>"*i+str(i)+"</div>"*i+"</body></html>"} for i in range(1,31)]
            download_source(source, root, rows=iter(rows), reserve_bytes=0)
            data_path = root / "configs/dataset.json"
            data_path.write_text(json.dumps({"sources": [source], "seed": 42, "reserve_free_bytes": 0,
                                            "max_text_bytes": 262144, "split_ratios": [.8,.1,.1]}))
            (root / "configs/tokenizer.json").write_text(json.dumps({"vocab_size": 512, "min_frequency": 2, "block_size": 1024}))
            with patch.object(pipeline, "ROOT", root):
                pipeline.main(["--config", str(data_path), "--train-tokenizer"])
                summary_path = root / "data/manifests/pipeline_summary.json"
                before = json.loads(summary_path.read_text())
                before_summary_sha = sha256_file(summary_path)
                fingerprint = pretrain_descriptor(root, before)
                parent = {"global_step": 2, "config": {"mode": "pretrain", "lineage": {
                    "pretrain_fingerprint": fingerprint, "tokenizer_sha256": before["tokenizer"]["tokenizer_sha256"], "smoke": False}}}
                records = []
                for i, row in enumerate(rows):
                    ann = annotation()
                    ann.update(source_row_id=row["source_row_id"], group_id=structural_group(row["text"]), prompt=f"Buat halaman uji {i}")
                    records.append(ann)
                annotation_path = root / "fixture_annotations.jsonl"
                annotation_path.write_text("".join(json.dumps(r)+"\n" for r in records), encoding="utf-8")
                pipeline.main(["--config", str(data_path), "--annotations", str(annotation_path)])
                after = json.loads(summary_path.read_text())
                self.assertNotEqual(sha256_file(summary_path), before_summary_sha)
                self.assertEqual(pretrain_descriptor(root, after), fingerprint)
                config = {"mode": "sft", "tokenizer": "data/tokenizer/tokenizer.json", "block_size": 1024,
                          "batch_size": 2, "validation_batches": 2, "seed": 42}
                _, _, config["lineage"] = prepare_training_data(root, config)
                validate_initial_checkpoint(parent, config, root, after)
                config["lineage"]["pretraining_parent"] = {"phase": "pretrain", "global_step": 2, "pretrain_fingerprint": fingerprint}
                state = {"global_step": 1, "config": config}
                verify_checkpoint_lineage(state, root, after)
                test_rows = list(read_jsonl(root / "data/processed/sft/test.jsonl"))
                verify_production_prompts(state, test_rows, root, after)
                fake = {**next(read_jsonl(root / "data/processed/sft/train.jsonl")), "split": "test"}
                with self.assertRaises(ValueError):
                    verify_production_prompts(state, [fake], root, after)
                modified = {**test_rows[0], "prompt": "prompt diubah"}
                with self.assertRaises(ValueError):
                    verify_production_prompts(state, [modified], root, after)


if __name__ == "__main__":
    unittest.main()

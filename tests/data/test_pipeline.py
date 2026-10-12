import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.data import pipeline
from src.data.pipeline import load_completed_sources
from src.data.normalize import structural_group
from src.data.sources import download_source
from tests.data.test_normalize import source_row, annotation


class PipelineTests(unittest.TestCase):
    def test_annotation_run_preserves_verified_tokens_and_checks_completed_sft(self):
        from qa.check_data_pipeline import validate_sft_artifacts
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "configs").mkdir()
            source = {"id": "websight_v01", "limit": 30, "revision": "a" * 40, "license_id": "cc-by-4.0"}
            rows = [{**source_row(), "source_row_id": f"row-{i}",
                     "text": '<html><body>' + '<div>' * i + str(i) + '</div>' * i + '</body></html>'} for i in range(1, 31)]
            download_source(source, root, rows=iter(rows), reserve_bytes=0)
            config = root / "configs/dataset.json"
            config.write_text(json.dumps({"sources": [source], "seed": 42, "reserve_free_bytes": 0,
                                          "max_text_bytes": 262144, "split_ratios": [0.8, 0.1, 0.1]}))
            (root / "configs/tokenizer.json").write_text(json.dumps({"vocab_size": 512, "min_frequency": 2, "block_size": 1024}))
            with patch.object(pipeline, "ROOT", root):
                pipeline.main(["--config", str(config), "--train-tokenizer"])
                before = json.loads((root / "data/manifests/pipeline_summary.json").read_text())
                anns = root / "annotations.jsonl"
                records = []
                for i, row in enumerate(rows):
                    ann = annotation()
                    ann.update(source_row_id=row["source_row_id"], group_id=structural_group(row["text"]), prompt=f"Buat halaman contoh {i}")
                    records.append(ann)
                anns.write_text("".join(json.dumps(row) + "\n" for row in records))
                pipeline.main(["--config", str(config), "--annotations", str(anns)])
                after = json.loads((root / "data/manifests/pipeline_summary.json").read_text())
                self.assertEqual(after["tokenizer"], before["tokenizer"])
                self.assertEqual(after["token_caches"], before["token_caches"])
                self.assertEqual(after["token_profiles"], before["token_profiles"])
                self.assertEqual(after["tokenization"]["action"], "reused")
                self.assertEqual(after["sft"]["status"], "complete")
                self.assertEqual(validate_sft_artifacts(root, after["sft"], {r["source_row_id"]: r for r in rows})["reviewed_rows"], 30)
                # A later preparation without annotations retains compatible SFT lineage.
                pipeline.main(["--config", str(config)])
                retained = json.loads((root / "data/manifests/pipeline_summary.json").read_text())
                self.assertEqual(retained["sft"], after["sft"])
                # A corrupted cache is reported as requiring tokenization, never complete.
                (root / "data/processed/pretrain/train.tokens.bin").write_bytes(b"bad")
                pipeline.main(["--config", str(config)])
                stale = json.loads((root / "data/manifests/pipeline_summary.json").read_text())
                self.assertEqual(stale["status"], "requires_tokenization")
                self.assertEqual(stale["tokenization"]["status"], "required")
                self.assertNotIn("tokenizer", stale)

    def test_awaiting_review_rejects_a_current_complete_sft_manifest(self):
        from qa.check_data_pipeline import validate_sft_artifacts
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "data/processed/sft").mkdir(parents=True)
            (root / "data/processed/sft/manifest.json").write_text('{"status": "complete"}')
            with self.assertRaisesRegex(ValueError, "awaiting_review"):
                validate_sft_artifacts(root, {"status": "awaiting_review", "reviewed_production_rows": 0}, {})

    def test_only_verified_completed_manifest_is_consumed(self):
        source = {"id": "fixture", "limit": 1, "revision": "a" * 40}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            download_source(source, root, rows=iter([{"text": "html"}]), reserve_bytes=0)
            paths, manifests = load_completed_sources({"sources": [source], "seed": 42}, root)
            self.assertEqual(len(paths), 1)
            paths[0].write_text("corruption")
            with self.assertRaises(ValueError):
                load_completed_sources({"sources": [source], "seed": 42}, root)

    def test_failed_or_missing_manifest_cannot_be_training_input(self):
        source = {"id": "fixture", "limit": 1, "revision": "a" * 40}
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                load_completed_sources({"sources": [source], "seed": 42}, Path(tmp))


if __name__ == "__main__":
    unittest.main()

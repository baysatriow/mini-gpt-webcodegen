import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from src.data.pipeline import load_completed_sources
from src.data.sources import download_source


class PipelineTests(unittest.TestCase):
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

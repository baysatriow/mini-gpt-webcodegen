import json
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.data.sources import download_source, stream_websight, stream_vulcan, write_manifest


class FakeDataset:
    def select_columns(self, columns):
        self.columns = columns
        return self

    def shuffle(self, seed, buffer_size):
        return self

    def take(self, count):
        return iter([{"text": "<html><body>A</body></html>", "images": object()},
                     {"text": "<html><body>B</body></html>", "images": object()},
                     {"text": "<html><body>C</body></html>"}][:count])


class SourceTests(unittest.TestCase):
    def test_vulcan_uses_pinned_http_stream_without_extra_dependency(self):
        raw = {"messages": [{"role": "user", "content": "Make a card"},
                             {"role": "assistant", "content": "<html><body>Card</body></html>"}]}
        source = {"dataset": "xlelords/vulcan", "revision": "a" * 40,
                  "filename": "frontend_sft.jsonl", "limit": 1}
        with patch("urllib.request.urlopen", return_value=io.BytesIO((json.dumps(raw) + "\n").encode())) as opener:
            rows = list(stream_vulcan(source))
        self.assertEqual(rows[0]["idea"], "Make a card")
        self.assertIn(source["revision"], opener.call_args[0][0].full_url)

    def test_projects_columns_at_loader_and_emits_stable_provenance(self):
        calls = []
        def loader(*args, **kwargs):
            calls.append((args, kwargs))
            return FakeDataset()
        rows = list(stream_websight("v0.1", "a" * 40, 2, 42, loader=loader))
        self.assertEqual(len(rows), 2)
        self.assertEqual(calls[0][1]["columns"], ["text"])
        self.assertTrue(calls[0][1]["streaming"])
        self.assertEqual(calls[0][1]["revision"], "a" * 40)
        self.assertTrue(all("images" not in row for row in rows))
        self.assertTrue(all(row["source_revision"] == "a" * 40 for row in rows))
        self.assertNotEqual(rows[0]["source_row_id"], rows[1]["source_row_id"])

    def test_manifest_atomic_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "manifest.json"
            write_manifest(path, {"status": "complete", "rows": 2})
            self.assertEqual(json.loads(path.read_text())["rows"], 2)
            self.assertEqual(len(list(Path(tmp).iterdir())), 1)

    def test_budget_failure_does_not_promote_partial_to_final(self):
        source = {"id": "fixture", "limit": 2, "revision": "a" * 40}
        rows = [{"text": "x" * 200}, {"text": "y" * 200}]
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                download_source(source, Path(tmp), rows=iter(rows), reserve_bytes=0, max_bytes=100)
            self.assertFalse((Path(tmp) / "data/raw/fixture-2.jsonl").exists())
            manifest = json.loads((Path(tmp) / "data/manifests/fixture-2.json").read_text())
            self.assertEqual(manifest["status"], "failed")

    def test_short_read_fails_and_completed_download_is_reusable(self):
        source = {"id": "fixture", "limit": 2, "revision": "a" * 40}
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                download_source(source, Path(tmp), rows=iter([{"text": "one"}]), reserve_bytes=0)
            good = download_source(source, Path(tmp), rows=iter([{"text": "one"}, {"text": "two"}]), reserve_bytes=0)
            again = download_source(source, Path(tmp), rows=iter([]), reserve_bytes=0)
            self.assertEqual(good["sha256"], again["sha256"])
            self.assertEqual(good["rows"], 2)

    def test_reserve_rejects_before_iterating(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(OSError):
                download_source({"id": "fixture", "limit": 1}, Path(tmp), rows=iter([]), reserve_bytes=10**18)


if __name__ == "__main__":
    unittest.main()

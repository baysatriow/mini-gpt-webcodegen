import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from qa.evaluate_request_extract_api_v1 import _sha256
from qa.request_extract_api_gate import checkpoint_aware_digest
from src.training.engine import checkpoint_sha256


class RequestExtractApiGateDigestTests(unittest.TestCase):
    def test_checkpoint_pointer_digest_matches_training_checkpoint_identity(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            payload = root / ".versions" / "candidate.pt"
            payload.parent.mkdir()
            payload.write_bytes(b"mini checkpoint payload")
            payload_digest = hashlib.sha256(payload.read_bytes()).hexdigest()
            manifest = payload.with_suffix(".json")
            manifest.write_text(
                json.dumps({"bytes": payload.stat().st_size, "sha256": payload_digest}),
                encoding="utf-8",
            )
            pointer = root / "step1800.pt"
            pointer.write_text(
                json.dumps({
                    "format_version": 2,
                    "payload": ".versions/candidate.pt",
                    "manifest_sha256": hashlib.sha256(manifest.read_bytes()).hexdigest(),
                }),
                encoding="utf-8",
            )

            other = root / "development.json"
            other.write_text("{}", encoding="utf-8")
            digest = checkpoint_aware_digest(pointer, checkpoint_sha256(pointer), _sha256)

            self.assertEqual(checkpoint_sha256(pointer), digest(pointer))
            self.assertEqual(_sha256(other), digest(other))


if __name__ == "__main__":
    unittest.main()

import base64
import hashlib
import json
import re
import tempfile
import unittest
import uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from apps.api.routers.generations import preview_file
from apps.api.services.artifacts import ArtifactStore


ROOT = Path(__file__).resolve().parents[2]


class PreviewDocumentTests(unittest.TestCase):
    def _accepted_generation(self, output_root: Path) -> tuple[str, Path, bytes]:
        generation_id = str(uuid.uuid4())
        generation_dir = output_root / generation_id
        website = generation_dir / "website"
        website.mkdir(parents=True)

        svg_path = ROOT / "assets/fullpage/studio-shapes.svg"
        svg = svg_path.read_bytes()
        files = {
            "index.html": (
                '<!doctype html><html><head><link rel="stylesheet" href="styles.css">'
                '<script src="app.js" defer></script></head><body>'
                '<img src="assets/studio-shapes.svg" alt="Demo"></body></html>'
            ).encode("utf-8"),
            "styles.css": b"body { color: red; }",
            "app.js": b"window.previewReady = true;",
            "page_spec.json": json.dumps(
                {"sections": [{"media": {"asset_id": "studio-shapes"}}]}
            ).encode("utf-8"),
            "assets/studio-shapes.svg": svg,
        }
        digests = {}
        for relative_path, payload in files.items():
            path = website / relative_path
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(payload)
            digests[relative_path] = hashlib.sha256(payload).hexdigest()
        (generation_dir / "result.json").write_text(
            json.dumps({"status": "accepted", "export": {"files": digests}}),
            encoding="utf-8",
        )
        return generation_id, generation_dir, svg

    def test_preview_html_embeds_assets_without_changing_downloaded_source(self):
        with tempfile.TemporaryDirectory() as temporary:
            output_root = Path(temporary)
            generation_id, generation_dir, svg = self._accepted_generation(output_root)
            store = ArtifactStore(output_root, ROOT, "http://127.0.0.1:8000")

            runtime = SimpleNamespace(
                project_root=ROOT,
                settings=SimpleNamespace(
                    generation_output_dir=output_root,
                    project_root=ROOT,
                    host="127.0.0.1",
                    port=8000,
                )
            )
            with patch("apps.api.routers.generations.get_runtime", return_value=runtime):
                response = preview_file(generation_id, "index.html")

            document = response.body.decode("utf-8")
            self.assertEqual("text/html; charset=utf-8", response.media_type)
            self.assertIn("body { color: red; }", document)
            self.assertIn("window.previewReady = true;", document)
            self.assertIn("data:image/svg+xml;base64,", document)
            self.assertIn(base64.b64encode(svg).decode("ascii"), document)
            self.assertNotIn('href="styles.css"', document)
            self.assertNotIn('src="app.js"', document)
            self.assertNotIn('src="assets/studio-shapes.svg"', document)
            policy = response.headers["content-security-policy"]
            nonce_match = re.search(r"script-src 'nonce-([^']+)'", policy)
            self.assertIsNotNone(nonce_match)
            nonce = nonce_match.group(1)
            self.assertIn(
                f'<meta http-equiv="Content-Security-Policy" content="{policy}">',
                document,
            )
            self.assertIn(f'<style nonce="{nonce}">', document)
            self.assertIn(f'<script nonce="{nonce}">', document)
            self.assertIn(f"style-src 'nonce-{nonce}'", policy)
            self.assertIn("img-src data:", policy)
            self.assertNotIn("unsafe-inline", policy)

            original = store.read_accepted_source(generation_dir)
            self.assertIn('href="styles.css"', original["index.html"])
            self.assertIn('src="app.js"', original["index.html"])
            self.assertEqual("body { color: red; }", original["styles.css"])


if __name__ == "__main__":
    unittest.main()

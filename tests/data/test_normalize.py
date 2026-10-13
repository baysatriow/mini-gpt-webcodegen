import json
import tempfile
import unittest
from pathlib import Path

from src.data.normalize import normalize_annotation, normalize_jsonl, prepare_pretraining, structural_group
from tests.data.test_schema import valid_spec


def source_row():
    return {"source_row_id": "row-1", "source_id": "websight_v01", "source_revision": "a" * 40,
            "license_id": "cc-by-4.0", "source_url": "https://example.org/dataset",
            "attribution": "Creator", "text": "<html><body><h1>Halo</h1></body></html>",
            "style_mode": "plain_css"}


def annotation():
    return {"source_row_id": "row-1", "prompt": "Buat halaman profil", "prompt_language": "id",
            "group_id": "layout-1", "target_spec": valid_spec(), "annotation_status": "reviewed",
            "reviewer": "TEST_FIXTURE", "annotation_revision": "1"}


class NormalizeTests(unittest.TestCase):
    def test_nullable_html_attributes_do_not_abort_following_records(self):
        rows = [source_row(), source_row(), source_row()]
        rows[0]["text"] = '<html><body><div class>Hi</div></body></html>'
        rows[1]["text"] = '<html><body><input type></body></html>'
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            raw = root / "source.jsonl"
            raw.write_text("".join(json.dumps(row) + "\n" for row in rows))
            report = prepare_pretraining([raw], root / "clean.jsonl")
            self.assertEqual(report["accepted"], 3)
            self.assertEqual(report["rejected"], 0)
            self.assertEqual(len((root / "clean.jsonl").read_text().splitlines()), 3)

    def test_annotation_retains_source_row_and_computed_family(self):
        ann = annotation()
        ann["source_group_id"] = "invented-family"
        result = normalize_annotation(source_row(), ann, {"id": "websight_v01"})
        self.assertEqual(result.source_row_id, "row-1")
        self.assertEqual(result.source_group_id, structural_group(source_row()["text"]))

    def test_css_only_source_is_kept_as_css_pretraining_text(self):
        row = source_row()
        row["text"] = ':root { --accent: #ffffff; } .card { color: var(--accent); padding: 16px; }'
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            raw = root / "source.jsonl"
            raw.write_text(json.dumps(row) + "\n")
            report = prepare_pretraining([raw], root / "clean.jsonl")
            self.assertEqual(report["accepted"], 1)
            result = json.loads((root / "clean.jsonl").read_text())
            self.assertEqual(result["code_language"], "css")
            self.assertEqual(result["text"], row["text"])

    def test_javascript_only_source_is_kept_as_code(self):
        row = source_row()
        row["text"] = 'const button = document.querySelector("#menu"); button.addEventListener("click", () => { button.hidden = true; });'
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            raw = root / "source.jsonl"
            raw.write_text(json.dumps(row) + "\n")
            report = prepare_pretraining([raw], root / "clean.jsonl")
            self.assertEqual(report["accepted"], 1)
            self.assertEqual(json.loads((root / "clean.jsonl").read_text())["code_language"], "javascript")

    def test_component_fragment_is_wrapped_with_provenance_not_discarded(self):
        row = source_row()
        row["text"] = '<style>.card{color:red;}</style><div class="card">Card</div><script>console.log(1)</script>'
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            raw = root / "source.jsonl"
            raw.write_text(json.dumps(row) + "\n")
            report = prepare_pretraining([raw], root / "clean.jsonl")
            self.assertEqual(report["accepted"], 1)
            result = json.loads((root / "clean.jsonl").read_text())
            self.assertEqual(result["html_transform"], "wrapped_component_fragment")
            self.assertIn("<html><body>", result["text"])
            self.assertEqual(result["text_sha256"], __import__("hashlib").sha256(row["text"].encode()).hexdigest())

    def test_reviewed_indonesian_annotation_becomes_canonical_example(self):
        result = normalize_annotation(source_row(), annotation(), {"id": "websight_v01"})
        self.assertEqual(result.license_id, "cc-by-4.0")
        self.assertEqual(result.annotation_status, "reviewed")
        self.assertEqual(result.style_mode, "plain_css")

    def test_rejects_empty_prompt_draft_unknown_source_and_missing_license(self):
        for field, value in [("prompt", ""), ("annotation_status", "draft"),
                             ("source_row_id", "unknown"), ("reviewer", ""), ("prompt_language", "en")]:
            ann = annotation()
            ann[field] = value
            with self.assertRaises(ValueError):
                normalize_annotation(source_row(), ann, {"id": "websight_v01"})
        row = source_row()
        row["license_id"] = ""
        with self.assertRaises(ValueError):
            normalize_annotation(row, annotation(), {"id": "websight_v01"})

    def test_invalid_schema_is_rejected(self):
        ann = annotation()
        ann["target_spec"]["style_mode"] = "bootstrap"
        with self.assertRaises(ValueError):
            normalize_annotation(source_row(), ann, {"id": "websight_v01"})

    def test_palette_variants_share_structural_group(self):
        red = '<html><body><div class="bg-red-500 grid"><h1>A</h1></div></body></html>'
        blue = '<html><body><div class="bg-blue-700 grid"><h1>B</h1></div></body></html>'
        self.assertEqual(structural_group(red), structural_group(blue))

    def test_normalizer_writes_only_reviewed_records_and_reject_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.jsonl"
            anns = root / "ann.jsonl"
            output = root / "result.jsonl"
            source.write_text(json.dumps(source_row()) + "\n", encoding="utf-8")
            draft = annotation()
            draft["annotation_status"] = "draft"
            anns.write_text(json.dumps(annotation()) + "\n" + json.dumps(draft) + "\n", encoding="utf-8")
            self.assertEqual(normalize_jsonl(source, anns, output), (1, 1))
            self.assertEqual(len(output.read_text().splitlines()), 1)
            self.assertEqual(json.loads(output.with_suffix(".rejects.json").read_text())["rejected"], 1)

    def test_pretrain_keeps_js_as_text_but_filters_non_html(self):
        row = source_row()
        row["text"] = '<html><body><script>console.log(1)</script></body></html>'
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            source = p / "raw.jsonl"
            source.write_text(json.dumps(row) + "\n" + json.dumps({**row, "text": "bad"}) + "\n")
            report = prepare_pretraining([source], p / "clean.jsonl")
            self.assertEqual(report["accepted"], 1)
            self.assertEqual(report["rejected"], 1)
            self.assertIn("console.log", (p / "clean.jsonl").read_text())


if __name__ == "__main__":
    unittest.main()

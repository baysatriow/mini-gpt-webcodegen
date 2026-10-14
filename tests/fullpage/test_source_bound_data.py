import hashlib
import json
import copy
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from tokenizers import Tokenizer

from qa import prepare_fullpage_v5
from src.fullpage.curriculum import make_page
from src.fullpage.dataset import encode_task_row
from src.fullpage.prompts import plan_prompt, section_prompt
from src.fullpage.serialization import OUTPUT_BUDGETS, check_budget, output_budget_for, serialize_task
from src.fullpage.source_bound_compose import compose_source_bound_page
from src.fullpage.source_bound_contracts import load_copy_catalog
from src.fullpage.source_bound_prompts import source_bound_plan_prompt, source_bound_section_prompt
from src.fullpage.source_bound_serialization import serialize_source_bound_task
from src.fullpage.source_bound_targets import build_source_bound_targets


ROOT = Path(__file__).resolve().parents[2]
TOKENIZER = Tokenizer.from_file(str(ROOT / "data/tokenizer/tokenizer.json"))
COPY_CATALOG = load_copy_catalog(ROOT)


def _make_page(index, split, style="plain_css", name="Studio Mapurana"):
    return make_page(index, split, style, name)


def _task_row(request, family_id, split, task, prompt, target, example_id):
    contract_version = json.loads(target).get("contract_version")
    budget = check_budget(TOKENIZER, prompt, output_budget_for(task, contract_version))
    target_tokens = len(TOKENIZER.encode(target).ids) + 1
    return {
        "example_id": example_id,
        "family_id": family_id,
        "split": split,
        "task": task,
        "prompt": prompt,
        "target": target,
        "length": budget["prefix_tokens"] + target_tokens - 1,
        "human_reviewed": False,
        "origin": "project-authored synthetic fixture",
        "genre": request["genre"],
        "style_mode": request["style_mode"],
        "retry": False,
        "augmentation": None,
    }


def _write_jsonl(path, rows):
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n" for row in rows),
        encoding="utf-8",
    )


class SourceBoundTargetTests(unittest.TestCase):
    def test_targets_reference_facts_and_compose_a_complete_page(self):
        request, legacy_plan, sections, _ = _make_page(0, "train")

        page_plan, drafts = build_source_bound_targets(request, legacy_plan, sections, COPY_CATALOG)
        encoded_targets = json.dumps([page_plan, drafts], ensure_ascii=False, sort_keys=True)
        page = compose_source_bound_page(request, page_plan, drafts, COPY_CATALOG)

        self.assertEqual("source-bound-v1", page_plan["contract_version"])
        self.assertIn("name", encoded_targets)
        self.assertNotIn("Studio Mapurana", encoded_targets)
        self.assertNotIn(request["business_facts"][1]["value"], encoded_targets)
        self.assertEqual([item["id"] for item in legacy_plan["sections"]], [item["id"] for item in page_plan["sections"]])
        self.assertEqual(9, len(drafts))
        self.assertEqual(request["genre"], page["genre"])
        self.assertEqual(request["style_mode"], page["style_mode"])
        self.assertEqual("Studio Mapurana", page["title"])

    def test_theme_mapping_uses_only_a_catalog_theme(self):
        request, legacy_plan, sections, _ = _make_page(0, "train")
        legacy_plan = copy.deepcopy(legacy_plan)
        legacy_plan["theme"]["primary"] = "#b45309"
        legacy_plan["theme"]["font"] = "serif"
        page_plan, drafts = build_source_bound_targets(request, legacy_plan, sections, COPY_CATALOG)
        page = compose_source_bound_page(request, page_plan, drafts, COPY_CATALOG)

        self.assertEqual("earth-warm", page_plan["theme_id"])
        self.assertEqual(COPY_CATALOG["themes"][page_plan["theme_id"]], page["theme"])

    def test_converter_rejects_section_structure_that_does_not_match_plan(self):
        request, legacy_plan, sections, _ = _make_page(0, "train")
        sections[0] = dict(sections[0], id="wrong")

        with self.assertRaises(ValueError):
            build_source_bound_targets(request, legacy_plan, sections, COPY_CATALOG)

    def test_converter_preserves_plan_order_when_source_sections_are_reordered(self):
        request, legacy_plan, sections, _ = _make_page(0, "train")
        page_plan, _ = build_source_bound_targets(request, legacy_plan, list(reversed(sections)), COPY_CATALOG)

        self.assertEqual(
            [item["id"] for item in legacy_plan["sections"]],
            [item["id"] for item in page_plan["sections"]],
        )


class TaskDatasetContractDispatchTests(unittest.TestCase):
    def test_source_bound_and_legacy_targets_both_encode(self):
        request, legacy_plan, sections, _ = _make_page(0, "train")
        page_plan, drafts = build_source_bound_targets(request, legacy_plan, sections, COPY_CATALOG)

        source_prompt = source_bound_plan_prompt(request)
        source_target = serialize_source_bound_task("page_plan", page_plan)
        source_row = _task_row(request, "family0000", "train", "page_plan", source_prompt, source_target, "source-plan")
        source_encoded = encode_task_row(source_row, TOKENIZER)
        self.assertTrue(source_encoded)

        descriptor, draft = page_plan["sections"][0], drafts[0]
        source_section_prompt = source_bound_section_prompt(request, page_plan, descriptor)
        source_section_target = serialize_source_bound_task("section_content", draft)
        source_section_row = _task_row(
            request, "family0000", "train", "section_content", source_section_prompt,
            source_section_target, "source-section",
        )
        self.assertTrue(encode_task_row(source_section_row, TOKENIZER))

        legacy_prompt = plan_prompt(request)
        legacy_target = serialize_task("page_plan", legacy_plan)
        legacy_row = _task_row(request, "family0000", "train", "page_plan", legacy_prompt, legacy_target, "legacy-plan")
        legacy_encoded = encode_task_row(legacy_row, TOKENIZER)
        self.assertTrue(legacy_encoded)

        legacy_descriptor, legacy_section = legacy_plan["sections"][0], sections[0]
        old_section_prompt = section_prompt(request, legacy_plan, legacy_descriptor)
        old_section_target = serialize_task("section_content", legacy_section)
        old_section_row = _task_row(
            request, "family0000", "train", "section_content", old_section_prompt,
            old_section_target, "legacy-section",
        )
        self.assertTrue(encode_task_row(old_section_row, TOKENIZER))


class SourceBoundDatasetPreparationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.temp_root = Path(self.temp.name)
        self.source_dir = self.temp_root / "v4"
        self.source_dir.mkdir()
        self.output_dir = self.temp_root / "v5"
        self.report_path = self.temp_root / "report.json"

        train_request, train_plan, _, _ = _make_page(0, "train", name="Studio Train")
        validation_request, validation_plan, _, _ = _make_page(240, "validation", "tailwind", "Studio Validation")
        train_request["request_id"] = train_request["request_id"] + "-v3-1"
        train_record = {"family_id": "family0000", "split": "train", "request": train_request}
        validation_record = {"family_id": "family0240", "split": "validation", "request": validation_request}
        _write_jsonl(self.source_dir / "train.requests.jsonl", [train_record])
        _write_jsonl(self.source_dir / "validation.requests.jsonl", [validation_record])

        train_row = _task_row(
            train_request, "family0000", "train", "page_plan", plan_prompt(train_request),
            serialize_task("page_plan", train_plan), train_request["request_id"] + "-target-0",
        )
        train_row["augmentation"] = "targeted-identity-facts-v3"
        validation_row = _task_row(
            validation_request, "family0240", "validation", "page_plan", plan_prompt(validation_request),
            serialize_task("page_plan", validation_plan), validation_request["request_id"] + "-0",
        )
        _write_jsonl(self.source_dir / "train.jsonl", [train_row])
        _write_jsonl(self.source_dir / "validation.jsonl", [validation_row])

        self.sealed_bytes = {
            "test.requests.jsonl": b"not-json-sealed-final-requests\n",
            "test.jsonl": b"not-json-sealed-final-targets\n",
        }
        for name, payload in self.sealed_bytes.items():
            (self.source_dir / name).write_bytes(payload)

        file_names = (
            "train.jsonl", "train.requests.jsonl", "validation.jsonl", "validation.requests.jsonl",
            "test.jsonl", "test.requests.jsonl",
        )
        files = {}
        for name in file_names:
            payload = (self.source_dir / name).read_bytes()
            files[name] = {"sha256": hashlib.sha256(payload).hexdigest(), "bytes": len(payload)}
        manifest = {
            "version": "fullpage-v4",
            "origin": "synthetic project-owned",
            "human_reviewed": False,
            "family_counts": {"train": 1, "validation": 1, "test": 0},
            "task_counts": {"train": 1, "validation": 1, "test": 0},
            "files": files,
        }
        (self.source_dir / "manifest.json").write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")

    def _small_fixture_constants(self):
        return (
            patch.object(prepare_fullpage_v5, "TRAIN_FAMILIES", frozenset({"family0000"})),
            patch.object(prepare_fullpage_v5, "VALIDATION_FAMILIES", frozenset({"family0240"})),
            patch.object(prepare_fullpage_v5, "TRAIN_REQUEST_COUNT", 1),
            patch.object(prepare_fullpage_v5, "VALIDATION_REQUEST_COUNT", 1),
            patch.object(prepare_fullpage_v5, "TEST_FAMILY_COUNT", 0),
            patch.object(prepare_fullpage_v5, "EXPECTED_PARENT_TASK_COUNTS", {"train": 1, "validation": 1, "test": 0}),
            patch.object(prepare_fullpage_v5, "REPORT", self.report_path),
        )

    def test_build_keeps_split_rows_and_never_parses_sealed_final_files(self):
        sealed_paths = {self.source_dir / name for name in self.sealed_bytes}
        raw_open = Path.open

        def guarded_open(path, mode="r", *args, **kwargs):
            if path in sealed_paths and "b" not in mode:
                raise AssertionError("sealed final records must never be opened as text")
            return raw_open(path, mode, *args, **kwargs)

        patches = self._small_fixture_constants()
        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], patches[6], patch.object(Path, "open", guarded_open):
            report = prepare_fullpage_v5.build_v5_dataset(
                ROOT, self.source_dir, self.output_dir, reserve_bytes=0,
            )

        manifest = json.loads((self.output_dir / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual({"train", "validation"}, set(manifest["splits"]))
        self.assertFalse((self.output_dir / "test.jsonl").exists())
        self.assertFalse((self.output_dir / "test.requests.jsonl").exists())
        self.assertEqual(10, manifest["task_counts"]["train"])
        self.assertEqual(10, manifest["task_counts"]["validation"])
        self.assertFalse(manifest["human_reviewed"])
        self.assertEqual(report["manifest_sha256"], hashlib.sha256((self.output_dir / "manifest.json").read_bytes()).hexdigest())
        for name, payload in self.sealed_bytes.items():
            self.assertEqual(payload, (self.source_dir / name).read_bytes())
        self.assertTrue(self.report_path.is_file())

    def test_destination_must_be_new(self):
        self.output_dir.mkdir()
        patches = self._small_fixture_constants()
        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], patches[6]:
            with self.assertRaises(FileExistsError):
                prepare_fullpage_v5.build_v5_dataset(ROOT, self.source_dir, self.output_dir, reserve_bytes=0)

    def test_insufficient_disk_reserve_refuses_to_write(self):
        patches = self._small_fixture_constants()
        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], patches[6], patch.object(
            prepare_fullpage_v5.shutil, "disk_usage", return_value=SimpleNamespace(free=0, total=1, used=1),
        ):
            with self.assertRaises(OSError):
                prepare_fullpage_v5.build_v5_dataset(ROOT, self.source_dir, self.output_dir, reserve_bytes=1)
        self.assertFalse(self.output_dir.exists())


if __name__ == "__main__":
    unittest.main()

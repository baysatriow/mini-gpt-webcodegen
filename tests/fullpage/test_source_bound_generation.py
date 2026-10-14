import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from src.fullpage.generation import FullPageGenerator, checkpoint_contract_version
from src.fullpage.evaluation import evaluation_source_paths
from src.fullpage.serialization import OUTPUT_BUDGETS, SOURCE_BOUND_OUTPUT_BUDGETS, check_budget
from src.fullpage.source_bound_prompts import source_bound_plan_prompt, source_bound_section_prompt
from src.fullpage.source_bound_serialization import serialize_source_bound_task
from tests.fullpage.fixtures import (
    ROOT,
    _FixtureTokenizer,
    fake_source_bound_generator,
    full_source_bound_fixture,
)


def model_outputs():
    request, catalog, plan, drafts = full_source_bound_fixture()
    return request, catalog, plan, drafts, [json.dumps(plan, ensure_ascii=False)] + [
        json.dumps(draft, ensure_ascii=False) for draft in drafts
    ]


class SourceBoundGenerationTests(unittest.TestCase):
    def test_contract_version_selection_defaults_to_legacy(self):
        self.assertIsNone(checkpoint_contract_version({}))
        self.assertEqual("source-bound-v1", checkpoint_contract_version({"fullpage_contract_version": "source-bound-v1"}))
        with self.assertRaises(ValueError):
            checkpoint_contract_version({"fullpage_contract_version": "future-contract"})

    def test_source_bound_prompts_and_serializer_use_only_supported_tasks(self):
        request, catalog, plan, drafts = full_source_bound_fixture()
        plan_prompt = source_bound_plan_prompt(request)
        section_prompt = source_bound_section_prompt(request, plan, plan["sections"][0])
        self.assertIn("source-bound-v1", plan_prompt)
        self.assertIn(request["prompt"], plan_prompt)
        self.assertIn("source-bound-v1", section_prompt)
        self.assertIn('"name"', section_prompt)
        self.assertEqual(512, OUTPUT_BUDGETS["page_plan"])
        self.assertEqual(896, SOURCE_BOUND_OUTPUT_BUDGETS["page_plan"])
        self.assertEqual(1536, OUTPUT_BUDGETS["section_content"])
        self.assertEqual(1536, SOURCE_BOUND_OUTPUT_BUDGETS["section_content"])
        self.assertEqual(
            json.dumps(plan, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
            serialize_source_bound_task("page_plan", plan),
        )
        self.assertEqual(
            json.dumps(drafts[0], ensure_ascii=False, sort_keys=True, separators=(",", ":")),
            serialize_source_bound_task("section_content", drafts[0]),
        )
        with self.assertRaises(ValueError):
            serialize_source_bound_task("unknown", {})
        check_budget(_FixtureTokenizer(), plan_prompt, SOURCE_BOUND_OUTPUT_BUDGETS["page_plan"])

    def test_source_bound_evaluation_identity_pins_all_generation_contract_sources(self):
        legacy_sources = set(evaluation_source_paths())
        source_bound_sources = set(evaluation_source_paths("source-bound-v1"))

        self.assertTrue(legacy_sources.issubset(source_bound_sources))
        self.assertFalse(any(path.startswith("src/fullpage/source_bound_") for path in legacy_sources))
        for path in (
            "src/fullpage/source_bound_prompts.py",
            "src/fullpage/source_bound_serialization.py",
            "src/fullpage/source_bound_contracts.py",
            "src/fullpage/source_bound_compose.py",
            "src/fullpage/source_bound_resolver.py",
            "configs/fullpage/plan-source-bound-v1.schema.json",
            "configs/fullpage/section-source-bound-v1.schema.json",
            "configs/fullpage/source-bound-copy-v1.json",
        ):
            with self.subTest(path=path):
                self.assertIn(path, source_bound_sources)

    def test_v5_section_reference_failure_after_retry_never_exports_website(self):
        request, _, plan, drafts, _ = model_outputs()
        invalid_draft = dict(drafts[0])
        invalid_draft["fact_slots"] = [{"slot_id": "brand", "fact_id": "not-in-request"}]
        generator = fake_source_bound_generator(
            ROOT,
            contract_version="source-bound-v1",
            model_outputs=[json.dumps(plan), json.dumps(invalid_draft), json.dumps(invalid_draft)],
        )
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "attempt"
            result = generator.generate(request, output)
            self.assertEqual("stage_failed", result["status"])
            self.assertEqual(3, len(result["attempts"]))
            self.assertEqual(["page_plan", "section_content", "section_content"], [call["task"] for call in generator._fixture_calls])
            self.assertFalse((output / "website").exists())
            self.assertEqual([], list(output.glob(".website-staging-*")))

    def test_missing_contract_version_uses_legacy_generation_path(self):
        generator = fake_source_bound_generator(ROOT, contract_version=None, model_outputs=[])
        expected = {"status": "accepted"}
        legacy = Mock(return_value=expected)
        generator._generate_legacy = legacy
        with tempfile.TemporaryDirectory() as tmp:
            result = generator.generate({"request_id": "legacy"}, Path(tmp) / "out")
        self.assertIs(expected, result)
        legacy.assert_called_once()

    def test_request_prompt_limit_is_exactly_one_thousand_characters(self):
        request, _, _, _, _ = model_outputs()
        request["prompt"] = "x" * 1001
        generator = fake_source_bound_generator(ROOT, contract_version="source-bound-v1", model_outputs=[])
        with tempfile.TemporaryDirectory() as tmp:
            result = generator.generate(request, Path(tmp) / "too-long")
        self.assertEqual("input_too_long", result["status"])
        self.assertEqual([], generator._fixture_calls)

        request["prompt"] = "x" * 1000
        generator = fake_source_bound_generator(ROOT, contract_version="source-bound-v1", model_outputs=["{}", "{}"])
        with tempfile.TemporaryDirectory() as tmp:
            result = generator.generate(request, Path(tmp) / "boundary")
        self.assertEqual("stage_failed", result["status"])
        self.assertEqual(["page_plan", "page_plan"], [call["task"] for call in generator._fixture_calls])

    def test_required_eos_failure_retries_once_and_never_exports(self):
        request, _, _, _, _ = model_outputs()
        stopped = {"raw": "{}", "stop_reason": "token_limit", "generated_tokens": 896}
        generator = fake_source_bound_generator(
            ROOT, contract_version="source-bound-v1", model_outputs=[stopped, stopped]
        )
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "missing-eos"
            result = generator.generate(request, output)
        self.assertEqual("stage_failed", result["status"])
        self.assertEqual(2, len(result["attempts"]))
        self.assertTrue(any("Missing EOS" in error for error in result["attempts"][-1]["errors"]))
        self.assertFalse((output / "website").exists())

    def test_section_prompt_overflow_runs_no_section_model(self):
        request, _, plan, _, _ = model_outputs()

        def token_count(prompt):
            return 100 if prompt.startswith("SOURCE_BOUND_PLAN") else 600

        generator = fake_source_bound_generator(
            ROOT,
            contract_version="source-bound-v1",
            model_outputs=[json.dumps(plan)],
            tokenizer=_FixtureTokenizer(token_count),
        )
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "overflow"
            result = generator.generate(request, output)
        self.assertEqual("input_too_long", result["status"])
        self.assertEqual(["page_plan"], [call["task"] for call in generator._fixture_calls])
        self.assertFalse((output / "website").exists())
        self.assertEqual([], list(output.glob(".website-staging-*")))

    def test_renderer_failure_removes_staging_and_website(self):
        request, _, _, _, outputs = model_outputs()
        generator = fake_source_bound_generator(ROOT, contract_version="source-bound-v1", model_outputs=outputs)
        with tempfile.TemporaryDirectory() as tmp, patch(
            "src.fullpage.generation.export_fullpage", side_effect=OSError("simulated renderer failure")
        ):
            output = Path(tmp) / "render-failure"
            result = generator.generate(request, output)
        self.assertEqual("stage_failed", result["status"])
        self.assertFalse((output / "website").exists())
        self.assertEqual([], list(output.glob(".website-staging-*")))

    def test_success_report_points_to_atomic_existing_renderer_export(self):
        request, _, _, _, outputs = model_outputs()
        generator = fake_source_bound_generator(ROOT, contract_version="source-bound-v1", model_outputs=outputs)
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "success"
            result = generator.generate(request, output)
            website = output / "website"
            self.assertEqual("accepted", result["status"])
            self.assertEqual(str(website), result["export"]["path"])
            self.assertTrue((website / "index.html").is_file())
            self.assertTrue((website / "styles.css").is_file())
            self.assertTrue((website / "app.js").is_file())
            self.assertEqual([], list(output.glob(".website-staging-*")))


if __name__ == "__main__":
    unittest.main()

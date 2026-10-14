import copy
import unittest

from src.fullpage.intake import map_generation_result, prepare_intake
from tests.fullpage.fixtures import _FixtureTokenizer, intake_fixture


class SourceBoundIntakeTests(unittest.TestCase):
    def test_missing_business_name_requests_clarification(self):
        prompt = "Buat company profile studio keramik."
        draft, tokenizer, catalog = intake_fixture(prompt, include_name=False)
        result = prepare_intake(prompt, draft, tokenizer, catalog)

        self.assertEqual("needs_clarification", result.status)
        self.assertIn("business_facts.name", result.missing_fields)
        self.assertIsNone(result.request)

    def test_exact_source_spans_build_clean_generation_request(self):
        draft, tokenizer, catalog = intake_fixture(evidence="span")
        result = prepare_intake(draft["prompt"], draft, tokenizer, catalog)

        self.assertEqual("ready", result.status)
        self.assertIsNotNone(result.request)
        self.assertEqual("Studio Mapurana", next(fact["value"] for fact in result.request["business_facts"] if fact["kind"] == "name"))
        self.assertNotIn("requested_features", result.request)
        self.assertNotIn("evidence", str(result.request))
        self.assertTrue(result.request["request_id"].startswith("intake-"))

    def test_mismatched_source_span_is_not_accepted(self):
        draft, tokenizer, catalog = intake_fixture(evidence="span")
        name = next(fact for fact in draft["business_facts"] if fact["kind"] == "name")
        name["evidence"]["source_span"] = {"start": 0, "end": len(name["value"])}

        result = prepare_intake(draft["prompt"], draft, tokenizer, catalog)

        self.assertEqual("needs_clarification", result.status)
        self.assertIsNone(result.request)
        self.assertTrue(any("evidence" in field for field in result.missing_fields))

    def test_nested_service_fields_require_independent_evidence(self):
        draft, tokenizer, catalog = intake_fixture(evidence="span")
        service = next(fact for fact in draft["business_facts"] if fact["kind"] == "service")
        service["value"]["text_evidence"]["source_span"]["start"] = 0

        result = prepare_intake(draft["prompt"], draft, tokenizer, catalog)

        self.assertEqual("needs_clarification", result.status)
        self.assertIsNone(result.request)
        self.assertTrue(any("srv0" in field and "text_evidence" in field for field in result.missing_fields))

    def test_user_confirmed_fact_is_accepted_without_prompt_match(self):
        draft, tokenizer, catalog = intake_fixture()
        name = next(fact for fact in draft["business_facts"] if fact["kind"] == "name")
        name["value"] = "Studio Imajinasi"
        name["evidence"] = {"user_confirmed": True}

        result = prepare_intake(draft["prompt"], draft, tokenizer, catalog)

        self.assertEqual("ready", result.status)
        self.assertEqual("Studio Imajinasi", result.request["business_facts"][0]["value"])

    def test_space_themed_ceramic_company_profile_is_supported(self):
        draft, tokenizer, catalog = intake_fixture(evidence="span")
        prompt = draft["prompt"] + " Gunakan nuansa luar angkasa."
        draft["prompt"] = prompt

        result = prepare_intake(prompt, draft, tokenizer, catalog)

        self.assertEqual("ready", result.status)
        self.assertIsNotNone(result.request)

    def test_explicit_catalog_capability_is_unsupported_before_missing_facts(self):
        prompt = "Buat company profile studio keramik dengan backend."
        draft, tokenizer, catalog = intake_fixture(prompt, include_name=False)
        start = prompt.index("backend")
        draft["requested_features"] = [
            {
                "capability_id": "backend",
                "evidence": {"source_span": {"start": start, "end": start + len("backend"), "quote": "backend"}},
            }
        ]

        result = prepare_intake(prompt, draft, tokenizer, catalog)

        self.assertEqual("unsupported_request", result.status)
        self.assertIsNone(result.request)
        self.assertIn("backend", result.message.lower())

    def test_explicit_external_script_capability_is_unsupported(self):
        cases = (
            ("external script", "external_script"),
            ("JavaScript bebas", "arbitrary_javascript"),
        )
        for phrase, capability_id in cases:
            with self.subTest(capability_id=capability_id):
                prompt = "Buat company profile studio keramik dan gunakan " + phrase + "."
                draft, tokenizer, catalog = intake_fixture(prompt)
                start = prompt.index(phrase)
                draft["requested_features"] = [
                    {
                        "capability_id": capability_id,
                        "evidence": {
                            "source_span": {"start": start, "end": start + len(phrase), "quote": phrase}
                        },
                    }
                ]

                result = prepare_intake(prompt, draft, tokenizer, catalog)

                self.assertEqual("unsupported_request", result.status)
                self.assertIsNone(result.request)

    def test_mismatched_capability_evidence_is_not_treated_as_explicit(self):
        prompt = "Buat company profile studio keramik dengan backend."
        draft, tokenizer, catalog = intake_fixture(prompt)
        draft["requested_features"] = [
            {"capability_id": "backend", "evidence": {"source_span": {"start": 0, "end": len("backend")}}}
        ]

        result = prepare_intake(prompt, draft, tokenizer, catalog)

        self.assertEqual("needs_clarification", result.status)
        self.assertIsNone(result.request)

    def test_unknown_capability_is_clarified_instead_of_silently_rejected(self):
        prompt = "Buat company profile studio keramik."
        draft, tokenizer, catalog = intake_fixture(prompt)
        draft["requested_features"] = [
            {"capability_id": "unknown_capability", "evidence": {"user_confirmed": True}}
        ]

        result = prepare_intake(prompt, draft, tokenizer, catalog)

        self.assertEqual("needs_clarification", result.status)
        self.assertIsNone(result.request)

    def test_unsupported_genre_and_style_are_reported(self):
        cases = (
            ("genre", "ecommerce", "Buat situs ecommerce untuk studio keramik."),
            ("style_mode", "react", "Buat company profile studio keramik dengan React."),
        )
        for field, value, prompt in cases:
            with self.subTest(field=field):
                draft, tokenizer, catalog = intake_fixture(prompt)
                draft[field] = value
                result = prepare_intake(prompt, draft, tokenizer, catalog)
                self.assertEqual("unsupported_request", result.status)
                self.assertIsNone(result.request)

    def test_unmentioned_unsupported_genre_and_style_are_clarified(self):
        for field, value in (("genre", "ecommerce"), ("style_mode", "react")):
            with self.subTest(field=field):
                draft, tokenizer, catalog = intake_fixture()
                draft[field] = value

                result = prepare_intake(draft["prompt"], draft, tokenizer, catalog)

                self.assertEqual("needs_clarification", result.status)
                self.assertIsNone(result.request)

    def test_input_over_one_thousand_characters_is_not_truncated(self):
        prompt = "x" * 1001
        draft, tokenizer, catalog = intake_fixture(prompt)

        result = prepare_intake(prompt, draft, tokenizer, catalog)

        self.assertEqual("input_too_long", result.status)
        self.assertIsNone(result.request)
        self.assertEqual(prompt, draft["prompt"])

    def test_full_plan_context_overflow_is_input_too_long(self):
        draft, _, catalog = intake_fixture()
        tokenizer = _FixtureTokenizer(lambda text: len(text))

        result = prepare_intake(draft["prompt"], draft, tokenizer, catalog)

        self.assertEqual("input_too_long", result.status)
        self.assertIsNone(result.request)

    def test_draft_prompt_must_match_original_prompt(self):
        draft, tokenizer, catalog = intake_fixture()
        draft["prompt"] += " extra"

        result = prepare_intake(draft["prompt"][:-6], draft, tokenizer, catalog)

        self.assertEqual("needs_clarification", result.status)
        self.assertIsNone(result.request)

    def test_duplicate_fact_ids_and_unknown_assets_are_clarified(self):
        draft, tokenizer, catalog = intake_fixture()
        draft["business_facts"].append(copy.deepcopy(draft["business_facts"][0]))
        result = prepare_intake(draft["prompt"], draft, tokenizer, catalog)
        self.assertEqual("needs_clarification", result.status)
        self.assertIsNone(result.request)

        draft, tokenizer, catalog = intake_fixture()
        draft["asset_ids"] = ["unlisted-asset"]
        result = prepare_intake(draft["prompt"], draft, tokenizer, catalog)
        self.assertEqual("needs_clarification", result.status)
        self.assertIsNone(result.request)

    def test_generation_status_mapping_hides_raw_errors(self):
        cases = {
            "accepted": "completed",
            "missing_information": "needs_clarification",
            "input_too_long": "input_too_long",
            "stage_failed": "generation_failed",
            "unknown": "generation_failed",
        }
        for raw_status, expected in cases.items():
            with self.subTest(raw_status=raw_status):
                result = map_generation_result(
                    {"status": raw_status, "errors": ["private raw exception"], "attempts": [{"raw": "secret"}]}
                )
                self.assertEqual(expected, result.status)
                self.assertIsNone(result.request)
                self.assertNotIn("private raw exception", result.message)
                self.assertNotIn("secret", result.message)


if __name__ == "__main__":
    unittest.main()

import copy
import json
import unittest
from pathlib import Path

from src.fullpage.schema_definitions import build_schemas, build_source_bound_schemas
from src.fullpage.source_bound_contracts import SCHEMA_FILES, validate_page_plan, validate_section_draft
from tests.fullpage.fixtures import source_bound_fixture


class SourceBoundContractTests(unittest.TestCase):
    def test_contract_version_loads_its_generated_schema_files(self):
        root = Path(__file__).resolve().parents[2]
        expected = {
            "plan-source-bound-v1": "configs/fullpage/plan-source-bound-v1.schema.json",
            "section-source-bound-v1": "configs/fullpage/section-source-bound-v1.schema.json",
        }
        self.assertEqual(expected, SCHEMA_FILES["source-bound-v1"])
        for name, relative_path in expected.items():
            persisted = json.loads((root / relative_path).read_text(encoding="utf-8"))
            self.assertEqual(build_source_bound_schemas()[name], persisted)

    def test_accepts_both_genres_and_styles(self):
        for genre in ("landing_page", "company_profile"):
            for style in ("plain_css", "tailwind"):
                request, catalog, plan, draft = source_bound_fixture(genre, style)
                self.assertEqual([], validate_page_plan(plan, request, catalog))
                self.assertEqual([], validate_section_draft(draft, plan["sections"][0], request, catalog))

    def test_rejects_unknown_fact_copy_and_free_text(self):
        request, catalog, plan, draft = source_bound_fixture()
        bad = copy.deepcopy(plan)
        bad["sections"][2]["fact_ids"] = ["unknown-fact"]
        self.assertTrue(validate_page_plan(bad, request, catalog))
        bad = copy.deepcopy(plan)
        bad["sections"][0]["copy_id"] = "unrecognized-copy"
        self.assertTrue(validate_page_plan(bad, request, catalog))
        bad = copy.deepcopy(draft)
        bad["raw_text"] = "Studio Mapurana"
        self.assertTrue(validate_section_draft(bad, plan["sections"][0], request, catalog))
        bad = copy.deepcopy(draft)
        bad["fact_slots"][0]["fact_id"] = "unknown-fact"
        self.assertTrue(validate_section_draft(bad, plan["sections"][0], request, catalog))

    def test_rejects_unknown_assets_and_duplicate_references(self):
        request, catalog, plan, draft = source_bound_fixture()
        bad_plan = copy.deepcopy(plan)
        bad_plan["sections"][1]["asset_ids"] = ["remote-image"]
        self.assertTrue(validate_page_plan(bad_plan, request, catalog))
        hero = copy.deepcopy(plan["sections"][1])
        bad_request = copy.deepcopy(request)
        bad_request["asset_ids"] = ["remote-image"]
        hero["asset_ids"] = ["remote-image"]
        hero_draft = {
            "contract_version": "source-bound-v1",
            "section_id": hero["id"],
            "fact_slots": [{"slot_id": "hero_name", "fact_id": "name"}],
            "asset_slots": [{"slot_id": "hero_art", "asset_id": "remote-image"}],
        }
        self.assertTrue(validate_section_draft(hero_draft, hero, bad_request, catalog))
        bad_draft = copy.deepcopy(draft)
        bad_draft["fact_slots"].append(copy.deepcopy(bad_draft["fact_slots"][0]))
        self.assertTrue(validate_section_draft(bad_draft, plan["sections"][0], request, catalog))
        bad_plan = copy.deepcopy(plan)
        bad_plan["sections"][0]["fact_ids"].append("name")
        self.assertTrue(validate_page_plan(bad_plan, request, catalog))
        bad_plan = copy.deepcopy(plan)
        bad_plan["sections"].append(copy.deepcopy(bad_plan["sections"][0]))
        self.assertTrue(validate_page_plan(bad_plan, request, catalog))

    def test_rejects_malformed_catalog_mappings_without_crashing(self):
        request, catalog, plan, _ = source_bound_fixture()
        bad_catalog = copy.deepcopy(catalog)
        bad_catalog["copies"] = []
        self.assertTrue(validate_page_plan(plan, request, bad_catalog))

    def test_rejects_bad_role_type_variant_and_catalog_pairings(self):
        request, catalog, plan, draft = source_bound_fixture()
        bad_plan = copy.deepcopy(plan)
        bad_plan["sections"][0]["type"] = "hero"
        self.assertTrue(validate_page_plan(bad_plan, request, catalog))
        bad_plan = copy.deepcopy(plan)
        bad_plan["sections"][0]["variant"] = "floating"
        self.assertTrue(validate_page_plan(bad_plan, request, catalog))
        bad_draft = copy.deepcopy(draft)
        bad_draft["fact_slots"][0]["slot_id"] = "about_description"
        self.assertTrue(validate_section_draft(bad_draft, plan["sections"][0], request, catalog))
        bad_plan = copy.deepcopy(plan)
        bad_plan["sections"] = [s for s in bad_plan["sections"] if s["role"] != "navigation"]
        self.assertTrue(validate_page_plan(bad_plan, request, catalog))

    def test_source_bound_schemas_are_closed_and_legacy_builder_is_unchanged(self):
        schemas = build_source_bound_schemas()
        self.assertEqual({"plan-source-bound-v1", "section-source-bound-v1"}, set(schemas))
        self.assertEqual({"page", "plan", "request", "section"}, set(build_schemas()))
        for schema in schemas.values():
            self.assertFalse(schema.get("additionalProperties", True))
            self.assertFalse(schema["properties"]["sections"]["items"].get("additionalProperties", True)) if "sections" in schema["properties"] else None
            for property_schema in schema["properties"].values():
                if property_schema.get("type") == "array" and property_schema.get("items", {}).get("type") == "object":
                    self.assertFalse(property_schema["items"].get("additionalProperties", True))

    def test_rejects_extra_top_level_and_nested_properties(self):
        request, catalog, plan, draft = source_bound_fixture()
        bad_plan = copy.deepcopy(plan)
        bad_plan["raw_text"] = "factual output"
        self.assertTrue(validate_page_plan(bad_plan, request, catalog))
        bad_draft = copy.deepcopy(draft)
        bad_draft["fact_slots"][0]["value"] = "free-form fact"
        self.assertTrue(validate_section_draft(bad_draft, plan["sections"][0], request, catalog))


if __name__ == "__main__":
    unittest.main()

import copy
import unittest
from pathlib import Path

from src.fullpage.assets import load_asset_catalog
from src.fullpage.contracts import validate_composed_page
from src.fullpage.renderer import render_fullpage
from src.fullpage.source_bound_compose import compose_source_bound_page
from src.fullpage.source_bound_resolver import resolve_section_draft
from tests.fullpage.fixtures import full_source_bound_fixture


class SourceBoundCompositionTests(unittest.TestCase):
    def test_composes_both_genres_and_styles(self):
        for genre in ("landing_page", "company_profile"):
            for style in ("plain_css", "tailwind"):
                with self.subTest(genre=genre, style=style):
                    request, catalog, plan, drafts = full_source_bound_fixture(genre, style)
                    page = compose_source_bound_page(request, plan, drafts, catalog)
                    self.assertEqual(genre, page["genre"])
                    self.assertEqual(style, page["style_mode"])
                    self.assertEqual([], validate_composed_page(page))

    def test_composition_uses_exact_request_facts(self):
        request, catalog, plan, drafts = full_source_bound_fixture()
        page = compose_source_bound_page(request, plan, drafts, catalog)
        sections = {section["role"]: section for section in page["sections"]}
        facts = {fact["id"]: fact["value"] for fact in request["business_facts"]}
        self.assertEqual("Studio Mapurana", page["title"])
        self.assertEqual(facts["name"], sections["navigation"]["props"]["brand"])
        self.assertEqual(facts["name"], sections["hero"]["props"]["heading"])
        self.assertEqual(plan["sections"][1]["asset_ids"][0], sections["hero"]["props"]["media"]["asset_id"])
        self.assertEqual(catalog["asset_slots"]["hero_art"]["alt_text"], sections["hero"]["props"]["media"]["alt"])
        self.assertEqual(facts["about"], sections["about"]["props"]["text"])
        self.assertEqual(facts["srv0"]["title"], sections["services"]["props"]["items"][0]["heading"])
        self.assertEqual(facts["srv0"]["text"], sections["services"]["props"]["items"][0]["text"])
        self.assertEqual(facts["srv1"]["title"], sections["services"]["props"]["items"][1]["heading"])
        self.assertEqual(facts["srv1"]["text"], sections["services"]["props"]["items"][1]["text"])
        self.assertEqual(catalog["copies"]["copy-contact-local"]["properties"]["fields"], sections["contact"]["props"]["fields"])
        self.assertEqual(catalog["themes"][plan["theme_id"]], page["theme"])
        self.assertEqual(
            [
                {"type": "menu_toggle", "target_id": "nav"},
                {"type": "form_validate", "target_id": "contact"},
            ],
            page["interactions"],
        )
        self.assertEqual([], validate_composed_page(page))

    def test_rejects_a_section_draft_count_mismatch(self):
        request, catalog, plan, drafts = full_source_bound_fixture()
        with self.assertRaises(ValueError):
            compose_source_bound_page(request, plan, drafts[:-1], catalog)

    def test_rejects_catalog_items_without_request_facts(self):
        request, catalog, plan, drafts = full_source_bound_fixture()
        catalog = copy.deepcopy(catalog)
        catalog["copies"]["copy-services-standard"]["page_properties"].append("items")
        catalog["copies"]["copy-services-standard"]["properties"]["items"] = [
            {"heading": "Layanan yang tidak diminta", "text": "Teks tanpa fakta request."}
        ]
        with self.assertRaisesRegex(ValueError, "Unprovided structured item"):
            compose_source_bound_page(request, plan, drafts, catalog)

    def test_rejects_unknown_fact_duplicate_slot_and_wrong_role_slot(self):
        request, catalog, plan, drafts = full_source_bound_fixture()
        navigation = plan["sections"][0]
        bad = copy.deepcopy(drafts[0])
        bad["fact_slots"][0]["fact_id"] = "unknown-fact"
        with self.assertRaises(ValueError):
            resolve_section_draft(request, navigation, bad, catalog)
        bad = copy.deepcopy(drafts[0])
        bad["fact_slots"].append(copy.deepcopy(bad["fact_slots"][0]))
        with self.assertRaises(ValueError):
            resolve_section_draft(request, navigation, bad, catalog)
        bad = copy.deepcopy(drafts[0])
        bad["fact_slots"][0]["slot_id"] = "about_description"
        with self.assertRaises(ValueError):
            resolve_section_draft(request, navigation, bad, catalog)

    def test_rejects_missing_role_and_unavailable_service_fact(self):
        request, catalog, plan, drafts = full_source_bound_fixture()
        portfolio_index = next(i for i, item in enumerate(plan["sections"]) if item["role"] == "portfolio")
        bad_plan = copy.deepcopy(plan)
        bad_drafts = copy.deepcopy(drafts)
        del bad_plan["sections"][portfolio_index]
        del bad_drafts[portfolio_index]
        with self.assertRaises(ValueError):
            compose_source_bound_page(request, bad_plan, bad_drafts, catalog)

        bad_request = copy.deepcopy(request)
        bad_request["business_facts"] = [fact for fact in bad_request["business_facts"] if fact["id"] != "srv0"]
        with self.assertRaises(ValueError):
            compose_source_bound_page(bad_request, plan, drafts, catalog)

    def test_html_sensitive_fact_is_escaped_by_existing_renderer(self):
        request, catalog, plan, drafts = full_source_bound_fixture()
        dangerous = "<script>alert(1)</script>"
        next(fact for fact in request["business_facts"] if fact["id"] == "about")["value"] = dangerous
        page = compose_source_bound_page(request, plan, drafts, catalog)
        root = Path(__file__).resolve().parents[2]
        rendered = render_fullpage(page, load_asset_catalog(root), root)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", rendered["index.html"])
        self.assertNotIn(dangerous, rendered["index.html"])


if __name__ == "__main__":
    unittest.main()

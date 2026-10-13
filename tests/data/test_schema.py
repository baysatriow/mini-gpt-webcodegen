import copy
import unittest

from src.data.schema import validate_page_spec


def valid_spec():
    return {"schema_version": "1.0", "title": "Profil", "language": "id",
            "style_mode": "plain_css", "theme": {"primary": "#224466",
            "background": "#ffffff", "text": "#111111", "font": "sans"},
            "sections": [{"id": "hero-1", "type": "hero",
                          "props": {"heading": "Halo", "text": "Selamat datang"}}],
            "interactions": []}


class SchemaTests(unittest.TestCase):
    def test_plain_css_and_tailwind_are_valid(self):
        for style in ["plain_css", "tailwind"]:
            spec = valid_spec()
            spec["style_mode"] = style
            self.assertEqual(validate_page_spec(spec), [])

    def test_rejects_unsupported_style_script_attributes_and_urls(self):
        changes = [lambda s: s.update(style_mode="bootstrap"),
                   lambda s: s["sections"][0].update(type="script"),
                   lambda s: s["sections"][0]["props"].update(onclick="alert(1)"),
                   lambda s: s["sections"][0]["props"].update(button={"label": "Go", "href": "javascript:alert(1)"}),
                   lambda s: s["interactions"].append({"type": "eval", "target_id": "hero-1"})]
        for change in changes:
            spec = valid_spec()
            change(spec)
            errors = validate_page_spec(spec)
            self.assertTrue(errors)
            self.assertTrue(all(e.startswith("$") for e in errors))

    def test_rejects_unknown_target_duplicate_ids_and_mismatched_interaction(self):
        spec = valid_spec()
        spec["interactions"] = [{"type": "menu_toggle", "target_id": "absent"}]
        self.assertTrue(validate_page_spec(spec))
        spec["interactions"][0]["target_id"] = "hero-1"
        self.assertTrue(validate_page_spec(spec))
        spec["interactions"] = []
        spec["sections"].append(copy.deepcopy(spec["sections"][0]))
        self.assertTrue(validate_page_spec(spec))

    def test_rejects_invalid_theme_and_extra_top_level_fields(self):
        spec = valid_spec()
        spec["theme"]["primary"] = "red"
        spec["raw_js"] = "alert(1)"
        self.assertTrue(validate_page_spec(spec))


if __name__ == "__main__":
    unittest.main()

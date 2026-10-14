"""Small source-bound request fixtures shared by contract tests."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def source_bound_fixture(genre="company_profile", style="plain_css"):
    catalog = json.loads((ROOT / "configs/fullpage/source-bound-copy-v1.json").read_text(encoding="utf-8"))
    request = {
        "request_id": "fixture-source-bound",
        "prompt": "Buat company profile Studio Mapurana.",
        "genre": genre,
        "style_mode": style,
        "business_facts": [
            {"id": "name", "kind": "name", "value": "Studio Mapurana"},
            {"id": "about", "kind": "description", "value": "Studio Mapurana membuat keramik untuk rumah."},
            {"id": "values", "kind": "value", "value": "Bahan dan proses dijelaskan secara terbuka."},
            {"id": "srv0", "kind": "service", "value": {"title": "Kelas keramik", "text": "Kelas untuk pemula."}},
            {"id": "step0", "kind": "process", "value": {"title": "Pilih tanah liat", "text": "Tentukan bahan yang akan digunakan."}},
            {"id": "faq0", "kind": "faq", "value": {"title": "Bagaimana memulai?", "text": "Hubungi studio untuk berdiskusi."}},
            {"id": "project0", "kind": "project", "value": {"title": "Cangkir pagi", "text": "Contoh karya keramik."}},
        ],
        "asset_ids": ["company-shapes" if genre == "company_profile" else "studio-shapes"],
        "fictitious": True,
    }
    landing_roles = ["navigation", "hero", "about", "services", "benefits", "process", "faq", "contact", "footer"]
    company_roles = ["navigation", "hero", "about", "services", "values", "process", "portfolio", "contact", "footer"]
    role_facts = {
        "navigation": ["name"], "hero": ["name"], "about": ["about"],
        "services": ["srv0"], "benefits": ["values"], "values": ["values"],
        "process": ["step0"], "faq": ["faq0"], "portfolio": ["project0"],
        "contact": [], "footer": ["name"],
    }
    sections = []
    for role in landing_roles if genre == "landing_page" else company_roles:
        role_spec = catalog["roles"][role]
        sections.append({
            "id": {"navigation": "nav", "hero": "main"}.get(role, role),
            "type": role_spec["component"],
            "role": role,
            "variant": role_spec["variants"][0],
            "copy_id": role_spec["copy_ids"][0],
            "fact_ids": role_facts[role],
            "asset_ids": request["asset_ids"] if role == "hero" else [],
        })
    plan = {"contract_version": "source-bound-v1", "theme_id": "studio-blue", "sections": sections}
    navigation_draft = {
        "contract_version": "source-bound-v1",
        "section_id": "nav",
        "fact_slots": [{"slot_id": "brand", "fact_id": "name"}],
        "asset_slots": [],
    }
    return request, catalog, plan, navigation_draft

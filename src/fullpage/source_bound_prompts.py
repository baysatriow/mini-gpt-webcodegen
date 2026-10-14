"""Shared source-bound task prompts for training-data preparation and generation."""

import json

from .source_bound_contracts import load_copy_catalog


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def source_bound_plan_prompt(request: dict) -> str:
    catalog = load_copy_catalog()
    genre = request.get("genre")
    required_roles = catalog.get("required_roles", {}).get(genre, [])
    section_ids = {
        "navigation": "nav",
        "hero": "main",
        "about": "about",
        "services": "services",
        "benefits": "benefits",
        "values": "values",
        "process": "process",
        "faq": "faq",
        "portfolio": "portfolio",
        "contact": "contact",
        "footer": "footer",
    }
    role_rules = {}
    for role in required_roles:
        role_spec = catalog["roles"][role]
        role_rules[role] = [
            section_ids[role],
            role_spec["component"],
            role_spec["variants"],
            role_spec["copy_ids"],
            role_spec["fact_kinds"],
            role_spec["max_assets"],
        ]
    context = {
        "genre": genre,
        "style_mode": request["style_mode"],
        "prompt": request["prompt"],
        "facts": [[fact["id"], fact["kind"]] for fact in request["business_facts"]],
        "assets": request["asset_ids"],
        "role_fields": ["section_id", "component", "variants", "copy_ids", "fact_kinds", "max_assets"],
        "roles": role_rules,
        "theme_ids": sorted(catalog["themes"]),
    }
    rules = (
        "Return only source-bound-v1 PagePlan JSON with contract_version,theme_id,sections. "
        "Each section uses id,type,role,variant,copy_id,fact_ids,asset_ids. Every role in roles is required. "
        "Role arrays follow role_fields order; facts are [id,kind]. Keep the user's prompt for design intent; fact values are omitted because outputs only reference IDs. "
        "Use supplied IDs only. Never write copy, HTML, CSS, JavaScript, or prose."
    )
    return "SOURCE_BOUND_PLAN\n" + rules + "\n" + _canonical(context)


def source_bound_section_prompt(request: dict, page_plan: dict, descriptor: dict) -> str:
    catalog = load_copy_catalog()
    role = descriptor["role"]
    role_spec = catalog["roles"][role]
    facts_by_id = {fact["id"]: fact for fact in request["business_facts"]}
    facts = [[fact_id, facts_by_id[fact_id]["kind"]] for fact_id in descriptor["fact_ids"]]
    fact_slots = {
        slot_id: {
            "fact_kinds": catalog["slots"][slot_id]["fact_kinds"],
            "multiple": catalog["slots"][slot_id].get("multiple", False),
        }
        for slot_id in role_spec["slot_ids"]
    }
    asset_slots = {
        slot_id: {"asset_id_only": True}
        for slot_id in role_spec["asset_slot_ids"]
    }
    context = {
        "contract_version": page_plan["contract_version"],
        "theme_id": page_plan["theme_id"],
        "section": descriptor,
        "facts": facts,
        "fact_slots": fact_slots,
        "asset_slots": asset_slots,
    }
    rules = (
        "Return only a SectionDraft JSON object: contract_version,section_id,fact_slots,asset_slots. "
        "Match the section ID. Map every fact ID once to an allowed slot by kind and every asset ID to its allowed slot. "
        "Use IDs only. Never output copy, HTML, CSS, JavaScript, or extra fields."
    )
    return "SOURCE_BOUND_SECTION\n" + rules + "\n" + _canonical(context)

"""Shared source-bound task prompts for training-data preparation and generation."""

import json

from .source_bound_contracts import load_copy_catalog


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def source_bound_plan_prompt(request: dict) -> str:
    catalog = load_copy_catalog()
    genre = request.get("genre")
    required_roles = catalog.get("required_roles", {}).get(genre, [])
    allowed_roles = {}
    for role in required_roles:
        role_spec = catalog["roles"][role]
        allowed_roles[role] = {
            "component": role_spec["component"],
            "variants": role_spec["variants"],
            "copy_ids": role_spec["copy_ids"],
            "fact_kinds": role_spec["fact_kinds"],
            "slot_ids": role_spec["slot_ids"],
            "asset_slot_ids": role_spec["asset_slot_ids"],
            "max_assets": role_spec["max_assets"],
        }
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
    context = {
        "request": request,
        "required_roles": required_roles,
        "allowed_roles": allowed_roles,
        "required_section_ids": {role: section_ids[role] for role in required_roles},
        "theme_ids": sorted(catalog["themes"]),
    }
    rules = (
        "Return only a PagePlan JSON object for contract source-bound-v1. "
        "Use every required role, its fixed section id, component, variant, copy id, and only the supplied fact and asset IDs. "
        "Do not write factual copy, HTML, CSS, JavaScript, or any other prose."
    )
    return "SOURCE_BOUND_PLAN\n" + rules + "\n" + _canonical(context)


def source_bound_section_prompt(request: dict, page_plan: dict, descriptor: dict) -> str:
    catalog = load_copy_catalog()
    role = descriptor["role"]
    role_spec = catalog["roles"][role]
    facts_by_id = {fact["id"]: fact for fact in request["business_facts"]}
    facts = [facts_by_id[fact_id] for fact_id in descriptor["fact_ids"]]
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
        "request_id": request["request_id"],
        "prompt": request["prompt"],
        "contract_version": page_plan["contract_version"],
        "theme_id": page_plan["theme_id"],
        "section": descriptor,
        "facts": facts,
        "fact_slots": fact_slots,
        "asset_slots": asset_slots,
    }
    rules = (
        "Return only a SectionDraft JSON object for contract source-bound-v1. "
        "Map every planned fact id exactly once to an allowed slot and each planned asset id to its allowed asset slot. "
        "Use IDs only. Do not output copy, factual prose, HTML, CSS, JavaScript, or extra fields."
    )
    return "SOURCE_BOUND_SECTION\n" + rules + "\n" + _canonical(context)

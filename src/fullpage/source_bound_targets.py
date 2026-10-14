"""Deterministic conversion from frozen synthetic pages to source-bound targets."""
import re

from .source_bound_compose import compose_source_bound_page
from .source_bound_contracts import (
    CONTRACT_VERSION,
    validate_page_plan,
    validate_section_draft,
)


def _theme_distance(source_theme, candidate):
    primary = source_theme.get("primary")
    if not isinstance(primary, str) or re.fullmatch(r"#[0-9a-fA-F]{6}", primary) is None:
        raise ValueError("Legacy theme must have a six-digit primary color")
    source_rgb = tuple(int(primary[index:index + 2], 16) for index in (1, 3, 5))
    candidate_primary = candidate.get("primary")
    if not isinstance(candidate_primary, str) or re.fullmatch(r"#[0-9a-fA-F]{6}", candidate_primary) is None:
        raise ValueError("Catalog theme must have a six-digit primary color")
    candidate_rgb = tuple(int(candidate_primary[index:index + 2], 16) for index in (1, 3, 5))
    color_distance = sum((left - right) ** 2 for left, right in zip(source_rgb, candidate_rgb, strict=True))
    font_penalty = 1_000_000 if source_theme.get("font") != candidate.get("font") else 0
    return font_penalty + color_distance


def nearest_catalog_theme(source_theme, copy_catalog):
    """Choose the closest primary color, preferring the same font family."""
    themes = copy_catalog.get("themes")
    if not isinstance(themes, dict) or not themes:
        raise ValueError("Source-bound copy catalog has no themes")
    return min(
        themes,
        key=lambda theme_id: (_theme_distance(source_theme, themes[theme_id]), theme_id),
    )


def _fact_index(request):
    facts = request.get("business_facts")
    if not isinstance(facts, list):
        raise ValueError("Request business_facts must be a list")
    indexed = {}
    for fact in facts:
        if not isinstance(fact, dict) or not isinstance(fact.get("id"), str):
            raise ValueError("Request contains an invalid business fact")
        if fact["id"] in indexed:
            raise ValueError("Request contains duplicate business fact IDs")
        indexed[fact["id"]] = fact
    return indexed


def _fact_slot(role, fact, role_spec, copy_catalog):
    candidates = []
    for slot_id in role_spec.get("slot_ids", []):
        slot = copy_catalog.get("slots", {}).get(slot_id, {})
        if slot.get("role") == role and fact.get("kind") in slot.get("fact_kinds", []):
            candidates.append(slot_id)
    if len(candidates) != 1:
        raise ValueError(f"Expected one catalog fact slot for role {role!r} and fact {fact.get('id')!r}")
    return candidates[0]


def _asset_slot(role, asset_id, role_spec, copy_catalog):
    candidates = []
    for slot_id in role_spec.get("asset_slot_ids", []):
        slot = copy_catalog.get("asset_slots", {}).get(slot_id, {})
        if slot.get("role") == role and asset_id in copy_catalog.get("assets", []):
            candidates.append(slot_id)
    if len(candidates) != 1:
        raise ValueError(f"Expected one catalog asset slot for role {role!r} and asset {asset_id!r}")
    return candidates[0]


def build_source_bound_targets(request: dict, plan: dict, sections: list[dict], copy_catalog: dict) -> tuple[dict, list[dict]]:
    """Convert a legacy layout to reference-only v1 targets and validate composition."""
    if not isinstance(plan, dict) or not isinstance(plan.get("sections"), list):
        raise ValueError("Legacy plan must contain an ordered section list")
    if not isinstance(sections, list) or len(sections) != len(plan["sections"]):
        raise ValueError("Source sections do not match the legacy plan count")
    if any(not isinstance(descriptor, dict) or not isinstance(descriptor.get("id"), str) for descriptor in plan["sections"]):
        raise ValueError("Legacy plan descriptors must have IDs")
    source_by_id = {}
    for source_section in sections:
        if not isinstance(source_section, dict) or not isinstance(source_section.get("id"), str):
            raise ValueError("Source sections must have unique IDs")
        if source_section["id"] in source_by_id:
            raise ValueError("Source sections contain duplicate IDs")
        source_by_id[source_section["id"]] = source_section
    if set(source_by_id) != {descriptor["id"] for descriptor in plan["sections"]}:
        raise ValueError("Source sections do not match the legacy plan IDs")

    fact_by_id = _fact_index(request)
    page_plan = {
        "contract_version": CONTRACT_VERSION,
        "theme_id": nearest_catalog_theme(plan.get("theme", {}), copy_catalog),
        "sections": [],
    }
    drafts = []
    referenced_facts = set()
    referenced_assets = set()

    for index, descriptor in enumerate(plan["sections"]):
        if not isinstance(descriptor, dict):
            raise ValueError(f"Section descriptor {index} must be an object")
        source_section = source_by_id[descriptor["id"]]
        if descriptor.get("id") != source_section.get("id") or descriptor.get("type") != source_section.get("type"):
            raise ValueError(f"Source section {index} does not match its legacy plan identity")

        role = descriptor.get("role")
        role_spec = copy_catalog.get("roles", {}).get(role)
        if not isinstance(role_spec, dict):
            raise ValueError(f"Unknown source-bound role at section {index}")
        copy_ids = role_spec.get("copy_ids", [])
        if len(copy_ids) != 1:
            raise ValueError(f"Role {role!r} must have exactly one deterministic copy entry")

        fact_ids = descriptor.get("fact_ids", [])
        asset_ids = descriptor.get("asset_ids", [])
        if not isinstance(fact_ids, list) or not isinstance(asset_ids, list):
            raise ValueError(f"Section {index} fact and asset references must be lists")
        source_descriptor = {
            "id": descriptor.get("id"),
            "type": descriptor.get("type"),
            "role": role,
            "variant": descriptor.get("variant"),
            "copy_id": copy_ids[0],
            "fact_ids": list(fact_ids),
            "asset_ids": list(asset_ids),
        }
        page_plan["sections"].append(source_descriptor)

        fact_slots = []
        for fact_id in fact_ids:
            fact = fact_by_id.get(fact_id)
            if fact is None:
                raise ValueError(f"Legacy plan refers to unknown request fact {fact_id!r}")
            fact_slots.append({"slot_id": _fact_slot(role, fact, role_spec, copy_catalog), "fact_id": fact_id})
            referenced_facts.add(fact_id)

        asset_slots = []
        for asset_id in asset_ids:
            asset_slots.append({"slot_id": _asset_slot(role, asset_id, role_spec, copy_catalog), "asset_id": asset_id})
            referenced_assets.add(asset_id)

        drafts.append({
            "contract_version": CONTRACT_VERSION,
            "section_id": source_descriptor["id"],
            "fact_slots": fact_slots,
            "asset_slots": asset_slots,
        })

    if referenced_facts != set(fact_by_id):
        missing = sorted(set(fact_by_id) - referenced_facts)
        raise ValueError("Legacy plan omits request facts: " + ", ".join(missing))
    if referenced_assets != set(request.get("asset_ids", [])):
        raise ValueError("Legacy plan does not reference every request asset exactly as supplied")

    errors = validate_page_plan(page_plan, request, copy_catalog)
    if errors:
        raise ValueError("Invalid source-bound PagePlan: " + "; ".join(errors))
    for descriptor, draft in zip(page_plan["sections"], drafts, strict=True):
        errors = validate_section_draft(draft, descriptor, request, copy_catalog)
        if errors:
            raise ValueError("Invalid source-bound SectionDraft: " + "; ".join(errors))
    compose_source_bound_page(request, page_plan, drafts, copy_catalog)
    return page_plan, drafts

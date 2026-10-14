"""Build a PageSpec 2.0 page from validated source-bound references."""

from copy import deepcopy

from .compose import fact_errors
from .contracts import validate_composed_page
from .source_bound_resolver import resolve_section_draft
from .source_bound_contracts import validate_page_plan


def derive_interactions(sections: list[dict]) -> list[dict]:
    interactions = []
    interaction_for_role = {
        "navigation": "menu_toggle",
        "faq": "accordion",
        "contact": "form_validate",
    }
    for section in sections:
        interaction = interaction_for_role.get(section.get("role"))
        if interaction:
            interactions.append({"type": interaction, "target_id": section["id"]})
    return interactions


def build_page_spec_from_request(request: dict, page_plan: dict, sections: list[dict], copy_catalog: dict) -> dict:
    names = [fact["value"] for fact in request.get("business_facts", []) if fact.get("kind") == "name"]
    if len(names) != 1 or not isinstance(names[0], str):
        raise ValueError("Request must contain exactly one business name fact")
    theme_id = page_plan.get("theme_id")
    theme = copy_catalog.get("themes", {}).get(theme_id)
    if not isinstance(theme, dict):
        raise ValueError("PagePlan references an unknown local theme")
    return {
        "schema_version": "2.0",
        "genre": request["genre"],
        "title": names[0],
        "language": "id",
        "style_mode": request["style_mode"],
        "theme": deepcopy(theme),
        "sections": sections,
        "interactions": derive_interactions(sections),
        "fictitious": request["fictitious"],
    }


def compose_source_bound_page(request: dict, page_plan: dict, drafts: list[dict], copy_catalog: dict) -> dict:
    """Validate and resolve all model references before returning a complete page."""
    errors = validate_page_plan(page_plan, request, copy_catalog)
    if errors:
        raise ValueError("Invalid source-bound PagePlan: " + "; ".join(errors))
    if not isinstance(drafts, list) or len(drafts) != len(page_plan["sections"]):
        raise ValueError("SectionDraft count must match the planned sections")

    sections = [
        resolve_section_draft(request, descriptor, draft, copy_catalog)
        for descriptor, draft in zip(page_plan["sections"], drafts, strict=True)
    ]
    fact_findings = [
        finding
        for descriptor, section in zip(page_plan["sections"], sections, strict=True)
        for finding in fact_errors(section, descriptor, request)
    ]
    if fact_findings:
        raise ValueError("Resolved sections violate request facts: " + "; ".join(fact_findings))
    page = build_page_spec_from_request(request, page_plan, sections, copy_catalog)
    errors = validate_composed_page(page)
    if errors:
        raise ValueError("Resolved page violates PageSpec 2.0: " + "; ".join(errors))
    return page

"""Resolve source-bound model references into trusted PageSpec properties."""

from copy import deepcopy

from .source_bound_contracts import validate_section_draft


def _set_nested(mapping, path, value):
    parts = path.split(".")
    target = mapping
    for key in parts[:-1]:
        current = target.get(key)
        if current is None:
            current = {}
            target[key] = current
        if not isinstance(current, dict):
            raise ValueError("Catalog property path collides with a non-object value")
        target = current
    key = parts[-1]
    if key in target:
        raise ValueError("Fact slot collides with existing catalog copy")
    target[key] = value


def _fact_value(slot_spec, fact):
    mode = slot_spec.get("value_mode")
    value = fact.get("value")
    if mode == "scalar" and isinstance(value, str):
        return value
    if mode == "text" and isinstance(value, str):
        heading = slot_spec.get("item_heading")
        if not isinstance(heading, str) or not heading:
            raise ValueError("Text item slot has no trusted catalog heading")
        return {"heading": heading, "text": value}
    if mode == "record" and isinstance(value, dict) and set(value) == {"title", "text"}:
        return {"heading": value["title"], "text": value["text"]}
    raise ValueError("Fact value does not match its trusted slot mode")


def resolve_section_draft(request: dict, descriptor: dict, draft: dict, copy_catalog: dict) -> dict:
    """Resolve validated fact and asset references using only the local catalog."""
    errors = validate_section_draft(draft, descriptor, request, copy_catalog)
    if errors:
        raise ValueError("Invalid source-bound SectionDraft: " + "; ".join(errors))

    copy_entry = copy_catalog["copies"][descriptor["copy_id"]]
    props = deepcopy(copy_entry["properties"])
    facts = {fact["id"]: fact for fact in request["business_facts"]}
    fact_slots = {slot["fact_id"]: slot["slot_id"] for slot in draft["fact_slots"]}

    for fact_id in descriptor["fact_ids"]:
        slot_id = fact_slots[fact_id]
        slot_spec = copy_catalog["slots"][slot_id]
        property_path = slot_spec["property"]
        resolved = _fact_value(slot_spec, facts[fact_id])
        if property_path == "items":
            if not slot_spec.get("multiple", False):
                raise ValueError("Repeated item slot is not enabled by the local catalog")
            props.setdefault("items", []).append(resolved)
        else:
            _set_nested(props, property_path, resolved)

    for reference in draft["asset_slots"]:
        slot_spec = copy_catalog["asset_slots"][reference["slot_id"]]
        property_path = slot_spec["property"]
        alt_text = slot_spec.get("alt_text")
        if not isinstance(alt_text, str) or not alt_text:
            raise ValueError("Asset slot is missing trusted alternative text")
        _set_nested(props, property_path, reference["asset_id"])
        media = props.get("media")
        if not isinstance(media, dict):
            raise ValueError("Asset slot did not resolve to a media object")
        media["alt"] = alt_text

    if descriptor["type"] == "hero":
        props["layout"] = descriptor["variant"]
    return {
        "id": descriptor["id"],
        "type": descriptor["type"],
        "role": descriptor["role"],
        "variant": descriptor["variant"],
        "props": props,
    }

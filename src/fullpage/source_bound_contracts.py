"""Strict validators for the versioned source-bound full-page wire contract."""

import json
from pathlib import Path

from jsonschema import Draft202012Validator

CONTRACT_VERSION = "source-bound-v1"
ROOT = Path(__file__).resolve().parents[2]
SCHEMA_FILES = {
    CONTRACT_VERSION: {
        "plan-source-bound-v1": "configs/fullpage/plan-source-bound-v1.schema.json",
        "section-source-bound-v1": "configs/fullpage/section-source-bound-v1.schema.json",
    },
}
REQUIRED_ROLES = {
    "landing_page": (
        "navigation", "hero", "about", "services", "benefits", "process", "faq", "contact", "footer",
    ),
    "company_profile": (
        "navigation", "hero", "about", "services", "values", "process", "portfolio", "contact", "footer",
    ),
}


def load_contract_schemas(contract_version=CONTRACT_VERSION, root=None):
    """Load and check only the schema files explicitly pinned to this contract version."""
    if contract_version not in SCHEMA_FILES:
        raise ValueError("Unsupported source-bound contract version")
    root = Path(root or ROOT)
    schemas = {}
    for name, relative_path in SCHEMA_FILES[contract_version].items():
        schema = json.loads((root / relative_path).read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        schemas[name] = schema
    return schemas


SCHEMAS = load_contract_schemas()
VALIDATORS = {name: Draft202012Validator(schema) for name, schema in SCHEMAS.items()}


def load_copy_catalog(root=None):
    """Load the checked-in copy, theme, and slot catalog for source-bound v1."""
    root = Path(root or ROOT)
    catalog_path = root / "configs/fullpage/source-bound-copy-v1.json"
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    if catalog.get("contract_version") != CONTRACT_VERSION:
        raise ValueError("Source-bound copy catalog version mismatch")
    return catalog


def _schema_errors(name, value):
    validator = VALIDATORS[name]
    errors = sorted(validator.iter_errors(value), key=lambda error: tuple(str(part) for part in error.absolute_path))
    return [
        f"$.{'/'.join(str(part) for part in error.absolute_path)}: {error.message}"
        if error.absolute_path else f"$: {error.message}"
        for error in errors
    ]


def _fact_index(request):
    result = {}
    for fact in request.get("business_facts", []):
        if not isinstance(fact, dict):
            continue
        fact_id, kind = fact.get("id"), fact.get("kind")
        if isinstance(fact_id, str) and fact_id and isinstance(kind, str):
            result.setdefault(fact_id, fact)
    return result


def _catalog_shape_errors(catalog):
    if not isinstance(catalog, dict):
        return ["$: copy catalog must be an object"]
    if catalog.get("contract_version") != CONTRACT_VERSION:
        return ["$.contract_version: unsupported catalog contract"]
    expected_types = {
        "themes": dict,
        "assets": list,
        "required_roles": dict,
        "roles": dict,
        "copies": dict,
        "slots": dict,
        "asset_slots": dict,
    }
    return [
        f"$.{key}: expected {expected.__name__} catalog mapping"
        for key, expected in expected_types.items()
        if not isinstance(catalog.get(key), expected)
    ]


def validate_page_plan(plan: dict, request: dict, copy_catalog: dict) -> list[str]:
    """Validate the PagePlan schema and every request/catalog reference."""
    errors = _schema_errors("plan-source-bound-v1", plan)
    if errors:
        return errors
    errors = _catalog_shape_errors(copy_catalog)
    if errors:
        return errors
    if not isinstance(request, dict):
        return ["$: request must be an object"]

    genre = request.get("genre")
    required_roles = REQUIRED_ROLES.get(genre)
    if required_roles is None:
        return ["$.request.genre: unsupported page genre"]
    if plan["theme_id"] not in copy_catalog["themes"]:
        errors.append("$.theme_id: unknown theme id")

    if copy_catalog.get("required_roles", {}).get(genre) != list(required_roles):
        errors.append("$.catalog.required_roles: required role definition differs from the source-bound contract")

    fact_by_id = _fact_index(request)
    fact_ids = [fact.get("id") for fact in request.get("business_facts", []) if isinstance(fact, dict)]
    if len(fact_ids) != len(set(fact_ids)):
        errors.append("$.request.business_facts: duplicate fact id")
    request_assets = request.get("asset_ids", [])
    if not isinstance(request_assets, list) or len(request_assets) != len(set(request_assets)):
        errors.append("$.request.asset_ids: invalid or duplicate asset ids")
        request_assets = []
    allowed_assets = set(copy_catalog.get("assets", []))
    for asset_id in request_assets:
        if asset_id not in allowed_assets:
            errors.append(f"$.request.asset_ids: unknown asset id {asset_id!r}")

    section_ids = set()
    roles_seen = set()
    role_catalog = copy_catalog["roles"]
    copy_catalog_entries = copy_catalog["copies"]
    for index, descriptor in enumerate(plan["sections"]):
        path = f"$.sections[{index}]"
        section_id = descriptor["id"]
        role = descriptor["role"]
        if section_id in section_ids:
            errors.append(f"{path}.id: duplicate section id")
        section_ids.add(section_id)
        if role in roles_seen:
            errors.append(f"{path}.role: duplicate section role")
        roles_seen.add(role)

        role_spec = role_catalog.get(role)
        if not isinstance(role_spec, dict):
            errors.append(f"{path}.role: unknown role")
            continue
        component = role_spec.get("component")
        if descriptor["type"] != component:
            errors.append(f"{path}.type: component does not match role")
        if descriptor["variant"] not in role_spec.get("variants", []):
            errors.append(f"{path}.variant: unsupported role variant")

        copy_id = descriptor["copy_id"]
        if copy_id not in role_spec.get("copy_ids", []):
            errors.append(f"{path}.copy_id: copy is not allowed for this role")
        copy_entry = copy_catalog_entries.get(copy_id)
        if not isinstance(copy_entry, dict):
            errors.append(f"{path}.copy_id: unknown copy id")
        elif copy_entry.get("role") != role or copy_entry.get("component") != component:
            errors.append(f"{path}.copy_id: copy role/component mismatch")
        elif set(copy_entry.get("page_properties", [])) != set(copy_entry.get("properties", {})):
            errors.append(f"{path}.copy_id: catalog property mapping mismatch")

        seen_facts = set()
        found_kinds = set()
        allowed_kinds = set(role_spec.get("fact_kinds", []))
        for fact_id in descriptor["fact_ids"]:
            if fact_id in seen_facts:
                errors.append(f"{path}.fact_ids: duplicate fact reference")
            seen_facts.add(fact_id)
            fact = fact_by_id.get(fact_id)
            if fact is None:
                errors.append(f"{path}.fact_ids: unknown fact id {fact_id!r}")
                continue
            kind = fact.get("kind")
            if kind not in allowed_kinds:
                errors.append(f"{path}.fact_ids: fact kind {kind!r} is not allowed for role {role!r}")
            found_kinds.add(kind)
        missing_kinds = set(role_spec.get("required_fact_kinds", [])) - found_kinds
        if missing_kinds:
            errors.append(f"{path}.fact_ids: missing required fact kinds {sorted(missing_kinds)!r}")

        descriptor_assets = descriptor["asset_ids"]
        role_asset_slots = role_spec.get("asset_slot_ids", [])
        if len(descriptor_assets) > role_spec.get("max_assets", 0):
            errors.append(f"{path}.asset_ids: role asset limit exceeded")
        if descriptor_assets and not role_asset_slots:
            errors.append(f"{path}.asset_ids: role does not support assets")
        for asset_id in descriptor_assets:
            if asset_id not in request_assets:
                errors.append(f"{path}.asset_ids: asset is not allowed by the request")
            if asset_id not in allowed_assets:
                errors.append(f"{path}.asset_ids: unknown asset id {asset_id!r}")

    missing_roles = set(required_roles) - roles_seen
    if missing_roles:
        errors.append(f"$.sections: missing required roles {sorted(missing_roles)!r}")
    return errors


def validate_section_draft(draft: dict, descriptor: dict, request: dict, copy_catalog: dict) -> list[str]:
    """Validate a SectionDraft and ensure every reference is authorized by its plan."""
    errors = _schema_errors("section-source-bound-v1", draft)
    if errors:
        return errors
    errors = _catalog_shape_errors(copy_catalog)
    if errors:
        return errors
    if not isinstance(descriptor, dict) or not isinstance(request, dict):
        return ["$: descriptor and request must be objects"]
    if draft["section_id"] != descriptor.get("id"):
        errors.append("$.section_id: does not match the planned section")

    role = descriptor.get("role")
    component = descriptor.get("type")
    role_spec = copy_catalog["roles"].get(role, {})
    fact_by_id = _fact_index(request)
    planned_facts = set(descriptor.get("fact_ids", []))
    used_facts = set()
    fact_slot_counts = {}
    for index, slot in enumerate(draft["fact_slots"]):
        path = f"$.fact_slots[{index}]"
        slot_id, fact_id = slot["slot_id"], slot["fact_id"]
        slot_spec = copy_catalog["slots"].get(slot_id)
        if not isinstance(slot_spec, dict):
            errors.append(f"{path}.slot_id: unknown fact slot")
            continue
        if slot_id not in role_spec.get("slot_ids", []):
            errors.append(f"{path}.slot_id: slot is not allowed for this role")
        if slot_spec.get("role") != role or slot_spec.get("component") != component:
            errors.append(f"{path}.slot_id: slot role/component mismatch")
        if not isinstance(slot_spec.get("property"), str) or not slot_spec["property"]:
            errors.append(f"{path}.slot_id: slot has no PageSpec property")
        fact = fact_by_id.get(fact_id)
        if fact is None:
            errors.append(f"{path}.fact_id: unknown fact id")
            continue
        if fact_id not in planned_facts:
            errors.append(f"{path}.fact_id: fact was not selected by the PagePlan")
        if fact_id in used_facts:
            errors.append(f"{path}.fact_id: duplicate fact reference")
        used_facts.add(fact_id)
        if fact.get("kind") not in slot_spec.get("fact_kinds", []):
            errors.append(f"{path}.fact_id: fact kind is not allowed by this slot")
        if fact.get("kind") not in role_spec.get("fact_kinds", []):
            errors.append(f"{path}.fact_id: fact kind is not allowed by this role")
        fact_slot_counts[slot_id] = fact_slot_counts.get(slot_id, 0) + 1
        if fact_slot_counts[slot_id] > 1 and not slot_spec.get("multiple", False):
            errors.append(f"{path}.slot_id: slot cannot be repeated")
    if used_facts != planned_facts:
        errors.append("$.fact_slots: references must match the PagePlan fact ids exactly")

    planned_assets = set(descriptor.get("asset_ids", []))
    request_assets = set(request.get("asset_ids", []))
    allowed_assets = set(copy_catalog["assets"])
    used_assets = set()
    asset_slot_counts = {}
    for index, slot in enumerate(draft["asset_slots"]):
        path = f"$.asset_slots[{index}]"
        slot_id, asset_id = slot["slot_id"], slot["asset_id"]
        slot_spec = copy_catalog["asset_slots"].get(slot_id)
        if not isinstance(slot_spec, dict):
            errors.append(f"{path}.slot_id: unknown asset slot")
            continue
        if slot_id not in role_spec.get("asset_slot_ids", []):
            errors.append(f"{path}.slot_id: asset slot is not allowed for this role")
        if slot_spec.get("role") != role or slot_spec.get("component") != component:
            errors.append(f"{path}.slot_id: asset slot role/component mismatch")
        if not isinstance(slot_spec.get("property"), str) or not slot_spec["property"]:
            errors.append(f"{path}.slot_id: asset slot has no PageSpec property")
        if asset_id not in planned_assets or asset_id not in request_assets:
            errors.append(f"{path}.asset_id: asset was not selected by both the request and PagePlan")
        if asset_id not in allowed_assets:
            errors.append(f"{path}.asset_id: unknown asset id")
        if asset_id in used_assets:
            errors.append(f"{path}.asset_id: duplicate asset reference")
        used_assets.add(asset_id)
        asset_slot_counts[slot_id] = asset_slot_counts.get(slot_id, 0) + 1
        if asset_slot_counts[slot_id] > 1:
            errors.append(f"{path}.slot_id: asset slot cannot be repeated")
    if used_assets != planned_assets:
        errors.append("$.asset_slots: references must match the PagePlan asset ids exactly")
    return errors

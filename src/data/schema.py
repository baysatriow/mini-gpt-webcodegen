"""Canonical PageSpec records and strict schema plus semantic validation."""
import json
from dataclasses import asdict, dataclass
from functools import lru_cache
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
INTERACTION_TARGETS = {"menu_toggle": {"navbar"}, "accordion": {"feature_grid", "text_section"},
                       "tabs": {"feature_grid", "text_section"}, "modal": {"hero", "text_section"},
                       "filter": {"feature_grid"}, "form_validate": {"contact_form"}}


@lru_cache(maxsize=1)
def _validator():
    schema = json.loads((ROOT / "configs/page_spec.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def validate_page_spec(spec: dict) -> list[str]:
    errors = []
    for error in sorted(_validator().iter_errors(spec), key=lambda e: str(list(e.absolute_path))):
        path = "$" + "".join(f"[{p}]" if isinstance(p, int) else f".{p}" for p in error.absolute_path)
        errors.append(f"{path}: {error.message}")
    if errors:
        return errors
    sections = {section["id"]: section["type"] for section in spec["sections"]}
    if len(sections) != len(spec["sections"]):
        errors.append("$.sections: duplicate section id")
    for i, interaction in enumerate(spec["interactions"]):
        target = interaction["target_id"]
        if target not in sections:
            errors.append(f"$.interactions[{i}].target_id: unknown target {target}")
        elif sections[target] not in INTERACTION_TARGETS[interaction["type"]]:
            errors.append(f"$.interactions[{i}]: incompatible target type {sections[target]}")
    return errors


@dataclass(frozen=True)
class PageExample:
    example_id: str
    prompt: str
    target_spec: dict
    source_id: str
    source_revision: str
    license_id: str
    group_id: str
    split: str = "unsplit"
    annotation_status: str = "reviewed"
    source_url: str = ""
    attribution: str = ""
    annotation_revision: str = ""
    reviewer: str = ""
    source_row_id: str = ""
    source_group_id: str = ""

    @property
    def style_mode(self):
        return self.target_spec["style_mode"]

    @property
    def interactions(self):
        return self.target_spec["interactions"]

    def to_record(self):
        return asdict(self)


WebPageExample = PageExample

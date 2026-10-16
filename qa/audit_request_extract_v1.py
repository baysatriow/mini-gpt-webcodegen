"""Read-only lineage, source-evidence, and tokenizer-budget audit for extractor v1."""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

from tokenizers import Tokenizer

from src.data.normalize import read_jsonl
from src.data.sources import sha256_file
from src.fullpage.request_extract_contracts import (
    CONTRACT_VERSION,
    EXTRACTION_SCOPES,
    canonical,
    extractor_prompt,
    validate_scoped_output,
)
from src.fullpage.serialization import check_budget


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = Path("data/processed/request_extract/v1")
V5_DIR = Path("data/processed/fullpage/v5")
CAPABILITY_PATH = Path("configs/fullpage/capability-catalog-v1.json")
ALIAS_PATH = Path("configs/fullpage/request-extract-v1-aliases.json")
MIN_BUCKET_FAMILIES = 50
MIN_FACT_FAMILIES = 100
MIN_GENRE_FAMILIES = 100


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("Expected a JSON object: " + str(path))
    return value


def _assert_substring(value: str, message_text: str, label: str) -> None:
    if not value or value not in message_text:
        raise ValueError(f"{label} is not an exact substring of its source message")


def _verify_occurrence(mention: dict[str, Any], source_text: str, label: str) -> None:
    phrase, context = mention["phrase"], mention["context"]
    _assert_substring(context, source_text, label + " context")
    _assert_substring(phrase, context, label + " phrase/context")
    occurrences = [match.start() for match in re.finditer(re.escape(phrase), source_text)]
    index = mention["occurrence_index"]
    if type(index) is not int or not 0 <= index < len(occurrences):
        raise ValueError(f"{label} occurrence index is outside the source message")
    context_offset = source_text.find(context) + context.find(phrase)
    if occurrences[index] != context_offset:
        raise ValueError(f"{label} occurrence index does not identify the cited phrase")


def _all_alias_values(document: dict[str, Any]) -> dict[str, set[str]]:
    result: dict[str, set[str]] = defaultdict(set)
    for section in ("genres", "styles", "business_status"):
        for value, phrases in document.get(section, {}).items():
            result[section + ":" + value].update(str(item).casefold() for item in phrases)
    return result


def _verify_target(row: dict[str, Any], aliases: dict[str, Any], catalog: dict[str, Any]) -> None:
    target = json.loads(row["target"])
    scope = row.get("scope")
    errors = validate_scoped_output(target, scope)
    if errors:
        raise ValueError(f"{row['example_id']} has invalid model target: {errors[:3]}")
    message_by_id = {item["id"]: item["text"] for item in row["messages"]}
    if len(message_by_id) != len(row["messages"]):
        raise ValueError(f"{row['example_id']} has duplicate source message IDs")
    if row["prompt"] != extractor_prompt(row["messages"], scope):
        raise ValueError(f"{row['example_id']} prompt differs from canonical structured messages")

    for fact in target["fact_mentions"]:
        if "value" in fact:
            source = message_by_id.get(fact["source_message_id"])
            if source is None:
                raise ValueError(f"{row['example_id']} scalar fact cites an unknown message")
            _assert_substring(fact["value"], source, row["example_id"] + " scalar fact")
        else:
            for field in ("title", "text"):
                source = message_by_id.get(fact[field + "_source_message_id"])
                if source is None:
                    raise ValueError(f"{row['example_id']} structured fact cites an unknown message")
                _assert_substring(fact[field], source, row["example_id"] + " structured fact " + field)

    for mention_group in ("setting_mentions", "business_status_mentions", "capability_mentions", "out_of_catalog_mentions"):
        for mention in target[mention_group]:
            source = message_by_id.get(mention["source_message_id"])
            if source is None:
                raise ValueError(f"{row['example_id']} mention cites an unknown message")
            _verify_occurrence(mention, source, row["example_id"] + " " + mention_group)

    alias_sets = _all_alias_values(aliases)
    for mention in target["setting_mentions"]:
        group = "genres" if mention["kind"] == "genre" else "styles"
        allowed = {str(item).casefold() for item in aliases[group][mention["value"]]}
        if mention["phrase"].casefold() not in allowed:
            raise ValueError(f"{row['example_id']} setting phrase is outside the versioned alias list")
    status_values = set().union(*(values for key, values in alias_sets.items() if key.startswith("business_status:")))
    for mention in target["business_status_mentions"]:
        if mention["phrase"].casefold() not in status_values:
            raise ValueError(f"{row['example_id']} business status phrase is outside the alias list")

    capability_aliases = {
        str(item["id"]): {phrase.casefold() for phrase in item["evidence_phrases"]}
        for item in catalog["unsupported_capabilities"]
    }
    for mention in target["capability_mentions"]:
        if mention["capability_id"] not in capability_aliases:
            raise ValueError(f"{row['example_id']} has a capability ID outside the catalog")
        if mention["phrase"].casefold() not in capability_aliases[mention["capability_id"]]:
            raise ValueError(f"{row['example_id']} capability phrase is not an alias for its ID")
    known_aliases = set().union(*capability_aliases.values(), status_values)
    for section in ("genres", "styles"):
        for phrases in aliases[section].values():
            known_aliases.update(str(item).casefold() for item in phrases)
    for mention in target["out_of_catalog_mentions"]:
        if mention["phrase"].casefold() in known_aliases:
            raise ValueError(f"{row['example_id']} unknown capability overlaps a supported alias")

    for correction in target["corrections"]:
        source = message_by_id.get(correction["source_message_id"])
        if source is None:
            raise ValueError(f"{row['example_id']} correction cites an unknown message")
        _assert_substring(correction["correction_phrase"], source, row["example_id"] + " correction phrase")
        replacement = correction["replacement_value"]
        if isinstance(replacement, dict):
            _assert_substring(replacement["title"], source, row["example_id"] + " replacement title")
            _assert_substring(replacement["text"], source, row["example_id"] + " replacement text")
        elif isinstance(replacement, str):
            if correction["kind"] in {"genre", "style_mode"}:
                group = "genres" if correction["kind"] == "genre" else "styles"
                expected = aliases[group][replacement]
                if not any(phrase.casefold() in source.casefold() for phrase in expected):
                    raise ValueError(f"{row['example_id']} setting replacement has no phrase in correction source")
            else:
                _assert_substring(replacement, source, row["example_id"] + " replacement value")
        for previous in row["messages"]:
            if previous["id"] == correction["source_message_id"]:
                break
            old = correction["previous_value"]
            if isinstance(old, dict):
                _assert_substring(old["title"], previous["text"], row["example_id"] + " prior title")
                _assert_substring(old["text"], previous["text"], row["example_id"] + " prior text")
            elif isinstance(old, str) and correction["kind"] not in {"genre", "style_mode"}:
                _assert_substring(old, previous["text"], row["example_id"] + " prior value")


def audit_dataset(root: Path, data_dir: Path) -> dict[str, Any]:
    root, data_dir = Path(root).resolve(), Path(data_dir)
    if not data_dir.is_absolute():
        data_dir = root / data_dir
    data_dir = data_dir.resolve()
    if not data_dir.is_relative_to(root):
        raise ValueError("Dataset directory escapes the project root")
    manifest = _read_json(data_dir / "manifest.json")
    if (manifest.get("version") != CONTRACT_VERSION
            or manifest.get("extraction_scopes") != list(EXTRACTION_SCOPES)
            or set(manifest.get("output_budgets", {})) != set(EXTRACTION_SCOPES)
            or manifest.get("final_opened") is not False
            or manifest.get("final_used") is not False
            or manifest.get("existing_validation_used") is not False
            or manifest.get("existing_test_used") is not False
            or manifest.get("development_frozen_before_training") is not True):
        raise ValueError("Extractor manifest violates the data boundary")

    for relative, digest in manifest["source_sha256"].items():
        if sha256_file(root / relative) != digest:
            raise ValueError("Extractor source file changed: " + relative)
    v5_manifest_path = root / V5_DIR / "manifest.json"
    if sha256_file(v5_manifest_path) != manifest["parent_v5_manifest_sha256"]:
        raise ValueError("Frozen V5 manifest checksum changed")
    tokenizer_path = root / "data/tokenizer/tokenizer.json"
    if sha256_file(tokenizer_path) != manifest["tokenizer_sha256"]:
        raise ValueError("Project tokenizer checksum changed")
    tokenizer = Tokenizer.from_file(str(tokenizer_path))
    aliases = _read_json(root / ALIAS_PATH)
    catalog = _read_json(root / CAPABILITY_PATH)
    rows_by_split: dict[str, list[dict[str, Any]]] = {}
    for split, filename in (("train", "train.jsonl"), ("development", "development.jsonl")):
        path = data_dir / filename
        file_info = manifest["files"][filename]
        if sha256_file(path) != file_info["sha256"] or path.stat().st_size != file_info["bytes"]:
            raise ValueError("Extractor dataset file checksum or byte count differs: " + filename)
        rows = list(read_jsonl(path))
        if len(rows) != file_info["rows"] or len(rows) != manifest["row_counts"][split]:
            raise ValueError("Extractor row count differs: " + split)
        for row in rows:
            if row.get("split") != split or row.get("canonical_format") != "prompt-messages-v1":
                raise ValueError("Extractor row has wrong split or message format")
            _verify_target(row, aliases, catalog)
            if row["scope"] not in manifest["output_budgets"]:
                raise ValueError("Extractor row has an unknown output scope")
            scope_budget = manifest["output_budgets"][row["scope"]]
            budget = check_budget(tokenizer, row["prompt"], scope_budget, block_size=2048)
            target_tokens = len(tokenizer.encode(row["target"], add_special_tokens=False).ids) + 1
            if target_tokens > scope_budget:
                raise ValueError("Extractor target exceeds its reserved output budget")
            if budget["prefix_tokens"] + scope_budget > manifest["block_size"]:
                raise ValueError("Extractor input plus reserved output exceeds context")
            if row["budget"]["prefix_tokens"] != budget["prefix_tokens"]:
                raise ValueError("Extractor row prefix budget changed")
            if row["budget"]["output_tokens"] != target_tokens:
                raise ValueError("Extractor row target budget changed")
            if row["budget"]["reserved_output_tokens"] != scope_budget:
                raise ValueError("Extractor row scope budget changed")
        rows_by_split[split] = rows

    v5_manifest = _read_json(v5_manifest_path)
    allowed_train_families = set(v5_manifest["family_ids"]["train"])
    train_families = {row["family_id"] for row in rows_by_split["train"]}
    development_families = {row["family_id"] for row in rows_by_split["development"]}
    if train_families != allowed_train_families:
        raise ValueError("Extractor training families differ from the frozen V5 training families")
    if train_families & development_families:
        raise ValueError("Extractor training and development families overlap")
    train_patterns = {row["prompt_pattern_id"] for row in rows_by_split["train"]}
    development_patterns = {row["prompt_pattern_id"] for row in rows_by_split["development"]}
    if train_patterns & development_patterns:
        raise ValueError("Extractor train and development prompt pattern IDs overlap")

    train_fact_families: dict[str, set[str]] = defaultdict(set)
    train_genre_families: dict[str, set[str]] = defaultdict(set)
    development_bucket_families: dict[str, set[str]] = defaultdict(set)
    development_genre_families: dict[str, set[str]] = defaultdict(set)
    for row in rows_by_split["train"]:
        train_genre_families[row["genre"]].add(row["family_id"])
        for fact in json.loads(row["target"])["fact_mentions"]:
            train_fact_families[fact["kind"]].add(row["family_id"])
    for row in rows_by_split["development"]:
        development_genre_families[row["genre"]].add(row["family_id"])
        if row["scenario"] in manifest["development_bucket_family_counts"]:
            development_bucket_families[row["scenario"]].add(row["family_id"])

    for kind, families in train_fact_families.items():
        if len(families) < MIN_FACT_FAMILIES:
            raise ValueError(f"Training has fewer than {MIN_FACT_FAMILIES} families for fact kind {kind}")
    if set(train_fact_families) != {"name", "description", "value", "service", "process", "faq", "project"}:
        raise ValueError("Extractor training does not cover every required fact kind")
    if any(len(train_genre_families[genre]) < MIN_GENRE_FAMILIES for genre in ("landing_page", "company_profile")):
        raise ValueError("Extractor training has fewer than 100 families for a page genre")
    for bucket, count in manifest["development_bucket_family_counts"].items():
        if len(development_bucket_families[bucket]) < MIN_BUCKET_FAMILIES or count < MIN_BUCKET_FAMILIES:
            raise ValueError("Development safety bucket is below the frozen minimum: " + bucket)
    if any(len(development_genre_families[genre]) < MIN_GENRE_FAMILIES for genre in ("landing_page", "company_profile")):
        raise ValueError("Development complete coverage has fewer than 100 families per page genre")

    maxima = {
        split: {
            "rows": len(rows),
            "families": len({row["family_id"] for row in rows}),
            "max_prefix_tokens": max(row["budget"]["prefix_tokens"] for row in rows),
            "max_target_tokens_with_eos": max(row["budget"]["output_tokens"] for row in rows),
            "max_total_tokens": max(row["budget"]["total_tokens"] for row in rows),
        }
        for split, rows in rows_by_split.items()
    }
    return {
        "status": "passed",
        "contract_version": CONTRACT_VERSION,
        "extraction_scopes": list(EXTRACTION_SCOPES),
        "output_budgets": manifest["output_budgets"],
        "row_counts": {name: len(rows) for name, rows in rows_by_split.items()},
        "family_counts": {name: len({row["family_id"] for row in rows}) for name, rows in rows_by_split.items()},
        "train_fact_family_counts": {name: len(values) for name, values in train_fact_families.items()},
        "train_genre_family_counts": {name: len(values) for name, values in train_genre_families.items()},
        "development_bucket_family_counts": {name: len(values) for name, values in development_bucket_families.items()},
        "development_genre_family_counts": {name: len(values) for name, values in development_genre_families.items()},
        "maxima": maxima,
        "train_development_family_intersection": len(train_families & development_families),
        "train_development_pattern_intersection": len(train_patterns & development_patterns),
        "final_opened": False,
        "final_used": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--data-dir", type=Path, default=DATA_DIR)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    report = audit_dataset(args.root, args.data_dir)
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    print(rendered)
    if args.report:
        destination = args.report if args.report.is_absolute() else args.root / args.report
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(rendered + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()

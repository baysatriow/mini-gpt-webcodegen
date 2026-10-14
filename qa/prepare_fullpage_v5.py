"""Prepare immutable source-bound-v1 synthetic full-page task data."""
import argparse
import hashlib
import json
import os
import re
import shutil
import uuid
from pathlib import Path

from tokenizers import Tokenizer

from src.data.sources import sha256_file
from src.fullpage.assets import load_asset_catalog
from src.fullpage.contracts import schema_errors, validate_plan_wire, validate_request
from src.fullpage.curriculum import make_page
from src.fullpage.dataset import encode_task_row
from src.fullpage.prompts import plan_prompt
from src.fullpage.serialization import SOURCE_BOUND_OUTPUT_BUDGETS, check_budget, decode_plan, output_budget_for
from src.fullpage.source_bound_compose import compose_source_bound_page
from src.fullpage.source_bound_contracts import CONTRACT_VERSION, load_copy_catalog
from src.fullpage.source_bound_prompts import source_bound_plan_prompt, source_bound_section_prompt
from src.fullpage.source_bound_serialization import serialize_source_bound_task
from src.fullpage.source_bound_targets import build_source_bound_targets


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/processed/fullpage/v4"
DESTINATION = ROOT / "data/processed/fullpage/v5"
REPORT = ROOT / "reports/fullpage/FULLPAGE-V5_DATA_PREPARATION.json"
RESERVE_BYTES = 15 * 1024**3
TEMPORARY_HEADROOM_BYTES = 64 * 1024**2
BLOCK_SIZE = 2048
TRAIN_FAMILIES = tuple(f"family{index:04d}" for index in range(240))
VALIDATION_FAMILIES = tuple(f"family{index:04d}" for index in range(240, 280))
TEST_FAMILY_COUNT = 40
TRAIN_REQUEST_COUNT = 3360
VALIDATION_REQUEST_COUNT = 80
EXPECTED_PARENT_TASK_COUNTS = {"train": 24000, "validation": 960, "test": 800}
REQUIRED_PARENT_FILES = (
    "train.jsonl",
    "train.requests.jsonl",
    "validation.jsonl",
    "validation.requests.jsonl",
    "test.jsonl",
    "test.requests.jsonl",
)
SEALED_FILES = ("validation.requests.jsonl", "test.requests.jsonl", "test.jsonl")
SOURCE_FILES = (
    "qa/prepare_fullpage_v5.py",
    "src/fullpage/source_bound_targets.py",
    "src/fullpage/dataset.py",
    "src/fullpage/source_bound_prompts.py",
    "src/fullpage/source_bound_serialization.py",
    "src/fullpage/source_bound_contracts.py",
    "src/fullpage/source_bound_compose.py",
    "src/fullpage/source_bound_resolver.py",
    "src/fullpage/curriculum.py",
    "src/fullpage/serialization.py",
    "src/fullpage/contracts.py",
    "src/fullpage/prompts.py",
    "configs/fullpage/source-bound-copy-v1.json",
)
SCHEMA_FILES = (
    "plan.schema.json",
    "section.schema.json",
    "plan-source-bound-v1.schema.json",
    "section-source-bound-v1.schema.json",
)
EXAMPLE_ID = re.compile(r"^(?P<request_id>.+)-(?P<index>\d+)(?P<retry>-retry)?$")
TARGETED_EXAMPLE_ID = re.compile(r"^(?P<request_id>.+)-target-(?P<index>\d+)(?P<retry>-retry)?$")


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def read_jsonl(path):
    path = Path(path)
    with path.open(encoding="utf-8") as handle:
        for number, line in enumerate(handle, 1):
            try:
                yield json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f"{path.name}:{number}: invalid JSON") from error


def _write_bytes(path, payload):
    with Path(path).open("xb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())


def _json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def _read_and_verify_parent(source_dir):
    source_dir = Path(source_dir).resolve()
    manifest_path = source_dir / "manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError("V4 parent manifest is missing")
    manifest_digest = sha256_file(manifest_path)
    manifest = read_json(manifest_path)
    if manifest.get("version") != "fullpage-v4" or manifest.get("human_reviewed") is not False:
        raise ValueError("Expected the frozen synthetic fullpage-v4 parent")
    files = manifest.get("files")
    if not isinstance(files, dict) or not set(REQUIRED_PARENT_FILES) <= set(files):
        raise ValueError("V4 parent manifest is missing required split files")
    for name, info in files.items():
        path = (source_dir / name).resolve()
        if source_dir not in path.parents:
            raise ValueError("V4 manifest contains a path outside its parent directory")
        if not path.is_file() or not isinstance(info, dict):
            raise ValueError("V4 parent artifact is missing: " + name)
        if path.stat().st_size != info.get("bytes") or sha256_file(path) != info.get("sha256"):
            raise ValueError("V4 parent artifact hash or byte count changed: " + name)
    if sha256_file(manifest_path) != manifest_digest:
        raise ValueError("V4 manifest changed while being verified")
    return source_dir, manifest, manifest_digest


def _load_requests(path, split, expected_families, expected_count, asset_catalog):
    records = []
    by_id = {}
    found_families = set()
    for record in read_jsonl(path):
        if record.get("split") != split:
            raise ValueError(f"{split} request file contains a different split")
        family_id = record.get("family_id")
        if family_id not in expected_families:
            raise ValueError(f"Request family is outside frozen {split} families: {family_id}")
        request = record.get("request")
        errors = validate_request(request, asset_catalog)
        if errors:
            raise ValueError(f"Invalid {split} request {request.get('request_id')}: {errors}")
        request_id = request.get("request_id")
        if not isinstance(request_id, str) or request_id in by_id:
            raise ValueError(f"Duplicate or invalid {split} request ID")
        records.append(record)
        by_id[request_id] = record
        found_families.add(family_id)
    if len(records) != expected_count:
        raise ValueError(f"Expected {expected_count} {split} requests, found {len(records)}")
    if found_families != set(expected_families):
        raise ValueError(f"{split} request family set differs from the frozen partition")
    return records, by_id


def _verify_curriculum_request(record, split):
    request = record["request"]
    family_id = record["family_id"]
    family_index = int(family_id.removeprefix("family"))
    name_facts = [fact["value"] for fact in request["business_facts"] if fact.get("kind") == "name"]
    if len(name_facts) != 1:
        raise ValueError("Frozen request must contain one business name fact")
    expected_request, expected_plan, source_sections, _ = make_page(
        family_index, split, request["style_mode"], name_facts[0]
    )
    for field in ("genre", "style_mode", "business_facts", "asset_ids", "fictitious"):
        if expected_request.get(field) != request.get(field):
            raise ValueError(f"Frozen {split} request differs from its deterministic curriculum in {field}")
    return expected_plan, source_sections


def _primary_plans(path, split, requests, expected_families, expected_task_count):
    found = {}
    targeted_candidates = {}
    row_count = 0
    for row in read_jsonl(path):
        row_count += 1
        if row.get("split") != split:
            raise ValueError(f"{split} parent rows contain a different split")
        family_id = row.get("family_id")
        if family_id not in expected_families:
            raise ValueError(f"{split} V4 task row is outside frozen families: {family_id}")
        if row.get("task") != "page_plan":
            continue
        example_id = row.get("example_id", "")
        if row.get("augmentation") == "targeted-identity-facts-v3":
            match = TARGETED_EXAMPLE_ID.fullmatch(example_id)
            request_id = match["request_id"] if match else None
        else:
            match = EXAMPLE_ID.fullmatch(example_id)
            if match and match["request_id"] in requests:
                request_id = match["request_id"]
            elif example_id in requests:
                request_id = example_id
                match = None
            else:
                request_id = None
        if request_id not in requests or (match and match["retry"]) or row.get("retry"):
            continue
        record = requests[request_id]
        if family_id != record["family_id"] or row.get("genre") != record["request"]["genre"]:
            raise ValueError("Primary parent plan metadata differs from its request")
        if row.get("style_mode") != record["request"]["style_mode"]:
            raise ValueError("Primary parent plan style differs from its request")
        if row.get("augmentation") == "targeted-identity-facts-v3":
            targeted_candidates.setdefault(request_id, []).append(row)
            continue
        if request_id in found:
            raise ValueError("Expected exactly one non-retry parent plan per request")
        found[request_id] = row
    for request_id, candidates in targeted_candidates.items():
        if request_id in found:
            continue
        if len(candidates) != 1:
            raise ValueError(f"Expected one targeted primary plan for {request_id}, found {len(candidates)}")
        found[request_id] = candidates[0]
    if row_count != expected_task_count:
        raise ValueError(f"{split} V4 row count differs from parent manifest: {row_count}")
    missing = set(requests) - set(found)
    if missing:
        raise ValueError(f"Missing primary legacy PagePlan for {len(missing)} {split} requests")
    return found, row_count


def _target_row(request, family_id, split, task, prompt, target, example_id, tokenizer):
    output_budget = output_budget_for(task, CONTRACT_VERSION)
    budget = check_budget(tokenizer, prompt, output_budget, block_size=BLOCK_SIZE)
    target_tokens = len(tokenizer.encode(target, add_special_tokens=False).ids) + 1
    if target_tokens > output_budget:
        raise ValueError(f"Source-bound {task} target exceeds its output budget")
    total_tokens = budget["prefix_tokens"] + target_tokens
    if total_tokens > BLOCK_SIZE:
        raise ValueError(f"Source-bound task exceeds the {BLOCK_SIZE}-token context")
    row = {
        "example_id": example_id,
        "family_id": family_id,
        "split": split,
        "task": task,
        "prompt": prompt,
        "target": target,
        "length": total_tokens - 1,
        "human_reviewed": False,
        "origin": "project-authored deterministic source-bound-v1 synthetic conversion",
        "genre": request["genre"],
        "style_mode": request["style_mode"],
        "retry": False,
        "augmentation": "source-bound-v5",
    }
    encode_task_row(row, tokenizer)
    return row, budget["prefix_tokens"], target_tokens, total_tokens


def _convert_request(record, parent_row, split, expected_plan, source_sections, asset_catalog, copy_catalog, tokenizer):
    request = record["request"]
    wire = json.loads(parent_row["target"])
    errors = validate_plan_wire(wire, request, asset_catalog)
    if errors:
        raise ValueError(f"Invalid frozen V4 PagePlan for {request['request_id']}: {errors}")
    legacy_plan = decode_plan(wire)
    plan_shape = {d["id"]: (d["role"], d["type"]) for d in legacy_plan["sections"]}
    source_shape = {d["id"]: (d["role"], d["type"]) for d in expected_plan["sections"]}
    if plan_shape != source_shape:
        raise ValueError(f"Parent PagePlan structure differs from frozen curriculum for {request['request_id']}")

    page_plan, drafts = build_source_bound_targets(request, legacy_plan, source_sections, copy_catalog)
    compose_source_bound_page(request, page_plan, drafts, copy_catalog)
    output_rows = []
    maxima = {"prefix_tokens": 0, "target_tokens_with_eos": 0, "total_tokens": 0}

    plan_target = serialize_source_bound_task("page_plan", page_plan)
    plan_row, prefix, target_tokens, total = _target_row(
        request,
        record["family_id"],
        split,
        "page_plan",
        source_bound_plan_prompt(request),
        plan_target,
        request["request_id"] + "-v5-plan",
        tokenizer,
    )
    output_rows.append(plan_row)
    maxima["prefix_tokens"] = max(maxima["prefix_tokens"], prefix)
    maxima["target_tokens_with_eos"] = max(maxima["target_tokens_with_eos"], target_tokens)
    maxima["total_tokens"] = max(maxima["total_tokens"], total)

    for index, (descriptor, draft) in enumerate(zip(page_plan["sections"], drafts, strict=True)):
        target = serialize_source_bound_task("section_content", draft)
        prompt = source_bound_section_prompt(request, page_plan, descriptor)
        row, prefix, target_tokens, total = _target_row(
            request,
            record["family_id"],
            split,
            "section_content",
            prompt,
            target,
            request["request_id"] + f"-v5-section-{index:02d}",
            tokenizer,
        )
        output_rows.append(row)
        maxima["prefix_tokens"] = max(maxima["prefix_tokens"], prefix)
        maxima["target_tokens_with_eos"] = max(maxima["target_tokens_with_eos"], target_tokens)
        maxima["total_tokens"] = max(maxima["total_tokens"], total)
    return output_rows, maxima


def _collect_source_hashes(root):
    source_hashes = {}
    for relative_path in SOURCE_FILES:
        path = Path(root) / relative_path
        if not path.is_file():
            raise FileNotFoundError("Required source lineage file is missing: " + relative_path)
        source_hashes[relative_path] = sha256_file(path)
    schema_hashes = {}
    for name in SCHEMA_FILES:
        path = Path(root) / "configs/fullpage" / name
        if not path.is_file():
            raise FileNotFoundError("Required schema lineage file is missing: " + name)
        schema_hashes[name] = sha256_file(path)
    return source_hashes, schema_hashes


def build_v5_dataset(root: Path, source_dir: Path, output_dir: Path, *, reserve_bytes: int = RESERVE_BYTES) -> dict:
    """Build train and validation source-bound targets without parsing final rows."""
    root = Path(root).resolve()
    source_dir = Path(source_dir).resolve()
    output_dir = Path(output_dir).resolve()
    report_path = Path(REPORT).resolve()
    if output_dir.exists():
        raise FileExistsError("V5 data destination must be new")
    if report_path.exists():
        raise FileExistsError("V5 preparation report destination must be new")
    if not source_dir.is_dir():
        raise FileNotFoundError("V4 parent dataset directory is missing")
    if type(reserve_bytes) is not int or reserve_bytes < 0:
        raise ValueError("Disk reserve must be a non-negative integer")

    source_dir, parent_manifest, parent_manifest_sha256 = _read_and_verify_parent(source_dir)
    if parent_manifest.get("family_counts") != {
        "train": len(TRAIN_FAMILIES),
        "validation": len(VALIDATION_FAMILIES),
        "test": TEST_FAMILY_COUNT,
    }:
        raise ValueError("V4 family counts differ from the frozen train/validation/test partitions")
    if parent_manifest.get("task_counts") != EXPECTED_PARENT_TASK_COUNTS:
        raise ValueError("V4 task counts differ from the frozen parent manifest contract")

    sealed_before = {name: sha256_file(source_dir / name) for name in SEALED_FILES}
    asset_catalog = load_asset_catalog(root)
    copy_catalog = load_copy_catalog(root)
    tokenizer_path = root / "data/tokenizer/tokenizer.json"
    tokenizer = Tokenizer.from_file(str(tokenizer_path))

    train_records, train_by_id = _load_requests(
        source_dir / "train.requests.jsonl", "train", TRAIN_FAMILIES, TRAIN_REQUEST_COUNT, asset_catalog,
    )
    validation_records, validation_by_id = _load_requests(
        source_dir / "validation.requests.jsonl", "validation", VALIDATION_FAMILIES,
        VALIDATION_REQUEST_COUNT, asset_catalog,
    )
    train_primary, _ = _primary_plans(
        source_dir / "train.jsonl", "train", train_by_id, TRAIN_FAMILIES,
        parent_manifest["task_counts"]["train"],
    )
    validation_primary, _ = _primary_plans(
        source_dir / "validation.jsonl", "validation", validation_by_id,
        VALIDATION_FAMILIES,
        parent_manifest["task_counts"]["validation"],
    )

    rows_by_split = {"train": [], "validation": []}
    maxima_by_split = {"train": {}, "validation": {}}
    for split, records, primary_rows in (
        ("train", train_records, train_primary),
        ("validation", validation_records, validation_primary),
    ):
        maxima = {"prefix_tokens": 0, "target_tokens_with_eos": 0, "total_tokens": 0}
        for record in records:
            expected_plan, source_sections = _verify_curriculum_request(record, split)
            converted, request_maxima = _convert_request(
                record, primary_rows[record["request"]["request_id"]], split,
                expected_plan, source_sections, asset_catalog, copy_catalog, tokenizer,
            )
            rows_by_split[split].extend(converted)
            for key, value in request_maxima.items():
                maxima[key] = max(maxima[key], value)
        maxima_by_split[split] = maxima

    expected_train_rows = sum(1 + len(json.loads(row["target"]).get("sections", [])) for row in train_primary.values())
    expected_validation_rows = sum(1 + len(json.loads(row["target"]).get("sections", [])) for row in validation_primary.values())
    if len(rows_by_split["train"]) != expected_train_rows or len(rows_by_split["validation"]) != expected_validation_rows:
        raise ValueError("Generated V5 task row count differs from source plan descriptor count")
    for split, rows in rows_by_split.items():
        if any(row["split"] != split or row["human_reviewed"] is not False for row in rows):
            raise ValueError("V5 output contains an invalid split or human-review claim")

    train_requests_bytes = (source_dir / "train.requests.jsonl").read_bytes()
    validation_requests_bytes = (source_dir / "validation.requests.jsonl").read_bytes()
    if hashlib.sha256(train_requests_bytes).hexdigest() != parent_manifest["files"]["train.requests.jsonl"]["sha256"]:
        raise ValueError("Frozen train request bytes changed")
    if hashlib.sha256(validation_requests_bytes).hexdigest() != parent_manifest["files"]["validation.requests.jsonl"]["sha256"]:
        raise ValueError("Frozen validation request bytes changed")

    payloads = {
        "train.jsonl": b"".join(_json_bytes(row) for row in rows_by_split["train"]),
        "validation.jsonl": b"".join(_json_bytes(row) for row in rows_by_split["validation"]),
        "train.requests.jsonl": train_requests_bytes,
        "validation.requests.jsonl": validation_requests_bytes,
    }
    output_file_info = {
        name: {"sha256": hashlib.sha256(payload).hexdigest(), "bytes": len(payload)}
        for name, payload in payloads.items()
    }
    source_hashes, schema_hashes = _collect_source_hashes(root)
    free_before = shutil.disk_usage(output_dir.parent).free
    data_bytes = sum(info["bytes"] for info in output_file_info.values())
    conservative_estimate = data_bytes + 64 * 1024
    if free_before < reserve_bytes + conservative_estimate + TEMPORARY_HEADROOM_BYTES:
        raise OSError("Insufficient storage for V5 output while preserving the requested disk reserve")

    temporary = output_dir.parent / (".v5-stage-" + uuid.uuid4().hex)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    if report_path.exists():
        raise FileExistsError("V5 preparation report destination must be new")
    promoted = False
    try:
        temporary.mkdir()
        for name, payload in payloads.items():
            _write_bytes(temporary / name, payload)
        free_after_data = shutil.disk_usage(output_dir.parent).free
        if free_after_data < reserve_bytes:
            raise OSError("V5 dataset write would breach the requested disk reserve")

        sealed_after = {name: sha256_file(source_dir / name) for name in SEALED_FILES}
        if sealed_after != sealed_before:
            raise ValueError("Frozen validation/final raw-byte hashes changed during V5 preparation")
        if sha256_file(source_dir / "manifest.json") != parent_manifest_sha256:
            raise ValueError("V4 parent manifest changed during V5 preparation")

        manifest = {
            "version": "fullpage-v5-source-bound-v1",
            "origin": "project-authored deterministic synthetic conversion from fullpage-v4",
            "human_reviewed": False,
            "final_opened": False,
            "block_size": BLOCK_SIZE,
            "output_budgets": SOURCE_BOUND_OUTPUT_BUDGETS,
            "parent": {
                "version": parent_manifest["version"],
                "manifest_sha256": parent_manifest_sha256,
                "task_counts": parent_manifest["task_counts"],
            },
            "files": output_file_info,
            "bytes": data_bytes,
            "family_ids": {"train": sorted(set(TRAIN_FAMILIES)), "validation": sorted(set(VALIDATION_FAMILIES))},
            "splits": sorted(rows_by_split),
            "family_counts": {"train": len(TRAIN_FAMILIES), "validation": len(VALIDATION_FAMILIES)},
            "request_counts": {"train": len(train_records), "validation": len(validation_records)},
            "task_counts": {split: len(rows) for split, rows in rows_by_split.items()},
            "tasks_per_request": {"page_plan": 1, "section_content": "one per planned section"},
            "request_sha256": {
                "train.requests.jsonl": parent_manifest["files"]["train.requests.jsonl"]["sha256"],
                "validation.requests.jsonl": parent_manifest["files"]["validation.requests.jsonl"]["sha256"],
            },
            "sealed_sha256_before": sealed_before,
            "sealed_sha256_after": sealed_after,
            "source_sha256": source_hashes,
            "schema_sha256": schema_hashes,
            "copy_catalog_sha256": sha256_file(root / "configs/fullpage/source-bound-copy-v1.json"),
            "tokenizer_sha256": sha256_file(tokenizer_path),
            "theme_mapping": {
                "method": "nearest primary-color RGB squared distance with a fixed 1000000-point penalty for font-family mismatch; tie-break by theme ID",
                "catalog_theme_ids": sorted(copy_catalog["themes"]),
            },
            "maxima": maxima_by_split,
            "split_policy": "train requests only from frozen train families; validation targets only from frozen validation families; no test records parsed or copied",
            "disk": {
                "reserve_bytes": reserve_bytes,
                "temporary_headroom_bytes": TEMPORARY_HEADROOM_BYTES,
                "conservative_output_estimate_bytes": conservative_estimate,
                "free_before_write_bytes": free_before,
                "free_after_data_write_bytes": free_after_data,
            },
        }
        manifest_payload = _json_bytes(manifest)
        if len(manifest_payload) > 64 * 1024:
            raise ValueError("V5 manifest exceeds the reserved size estimate")
        _write_bytes(temporary / "manifest.json", manifest_payload)

        for name, info in output_file_info.items():
            path = temporary / name
            if path.stat().st_size != info["bytes"] or sha256_file(path) != info["sha256"]:
                raise ValueError("V5 staged output checksum mismatch: " + name)
        if len(list(read_jsonl(temporary / "train.jsonl"))) != manifest["task_counts"]["train"]:
            raise ValueError("V5 staged train row count mismatch")
        if len(list(read_jsonl(temporary / "validation.jsonl"))) != manifest["task_counts"]["validation"]:
            raise ValueError("V5 staged validation row count mismatch")
        if any((temporary / name).exists() for name in ("test.jsonl", "test.requests.jsonl")):
            raise ValueError("V5 output must not contain test artifacts")

        free_before_promote = shutil.disk_usage(output_dir.parent).free
        if free_before_promote < reserve_bytes:
            raise OSError("Staged V5 output would breach the requested disk reserve")
        temporary.replace(output_dir)
        promoted = True
        manifest_sha256 = sha256_file(output_dir / "manifest.json")
        result = {
            "dataset": output_dir.relative_to(root).as_posix() if root in output_dir.parents else str(output_dir),
            "manifest_sha256": manifest_sha256,
            "parent_manifest_sha256": parent_manifest_sha256,
            "request_counts": manifest["request_counts"],
            "task_counts": manifest["task_counts"],
            "family_counts": manifest["family_counts"],
            "sealed_hashes_unchanged": sealed_before == sealed_after,
            "sealed_sha256_before": sealed_before,
            "sealed_sha256_after": sealed_after,
            "human_reviewed": False,
            "final_opened": False,
            "disk_free_before_bytes": free_before,
            "disk_free_after_bytes": shutil.disk_usage(output_dir.parent).free,
            "dataset_bytes": sum(path.stat().st_size for path in output_dir.iterdir() if path.is_file()),
        }
        report_tmp = report_path.with_name(report_path.name + ".tmp-" + uuid.uuid4().hex)
        _write_bytes(report_tmp, _json_bytes(result))
        report_tmp.replace(report_path)
        return result
    except BaseException:
        if temporary.exists():
            shutil.rmtree(temporary)
        if promoted and output_dir.exists() and not report_path.exists():
            shutil.rmtree(output_dir)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    if args.root.resolve() != ROOT:
        raise ValueError("V5 preparation is pinned to this project root")
    result = build_v5_dataset(ROOT, SOURCE, DESTINATION)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

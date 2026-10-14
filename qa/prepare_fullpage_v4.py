"""Add train-only process section targets on top of the frozen fullpage v3 data."""
import argparse
import json
import re
import shutil
import uuid
from collections import Counter
from pathlib import Path

from tokenizers import Tokenizer

from src.data.sources import sha256_file
from src.fullpage.assets import load_asset_catalog
from src.fullpage.compose import fact_errors
from src.fullpage.contracts import validate_plan_wire, validate_section
from src.fullpage.curriculum import make_page, write_json
from src.fullpage.dataset import encode_task_row
from src.fullpage.prompts import section_prompt
from src.fullpage.serialization import OUTPUT_BUDGETS, check_budget, decode_plan, serialize_task

ROOT = Path(__file__).resolve().parents[1]
RESERVE_BYTES = 15 * 1024**3
SOURCE = ROOT / "data/processed/fullpage/v3"
DESTINATION = ROOT / "data/processed/fullpage/v4"
REPORT = ROOT / "reports/fullpage/FULLPAGE-V4_DATA_PREPARATION.json"
TARGET_MARKER = "targeted-identity-facts-v3"
TARGETED_EXAMPLE = re.compile(r"^(?P<request_id>.+)-target-(?P<index>\d+)(?:-retry)?$")


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path):
    with path.open(encoding="utf-8") as handle:
        for number, line in enumerate(handle, 1):
            try:
                yield json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f"{path.name}:{number}: invalid JSON") from error


def role_counts(rows):
    counts = Counter()
    for row in rows:
        if row["task"] == "section_content":
            counts[json.loads(row["target"]).get("role")] += 1
    return dict(sorted(counts.items()))


def verify_source(manifest):
    if manifest.get("version") != "fullpage-v3" or manifest.get("human_reviewed") is not False:
        raise ValueError("Expected the disclosed, synthetic v3 parent")
    for name, info in manifest["files"].items():
        path = SOURCE / name
        if not path.is_file() or sha256_file(path) != info["sha256"] or path.stat().st_size != info["bytes"]:
            raise ValueError("Frozen v3 parent file changed: " + name)


def build_overlay():
    if DESTINATION.exists() or REPORT.exists():
        raise FileExistsError("V4 dataset and report destinations must be new")
    source_manifest_path = SOURCE / "manifest.json"
    source_manifest = read_json(source_manifest_path)
    verify_source(source_manifest)

    source_bytes = sum((SOURCE / name).stat().st_size for name in source_manifest["files"])
    disk_before = shutil.disk_usage(ROOT).free
    if disk_before < RESERVE_BYTES + source_bytes + 64 * 1024**2:
        raise OSError("Insufficient storage to copy v3 while preserving the 15 GiB reserve")

    requests = {}
    for record in read_jsonl(SOURCE / "train.requests.jsonl"):
        if record["split"] != "train":
            raise ValueError("The v3 training request file contains a non-train record")
        request = record["request"]
        if "-v3-" in request["request_id"]:
            if request["request_id"] in requests:
                raise ValueError("Duplicate v3 training request ID")
            requests[request["request_id"]] = record
    if len(requests) != 960:
        raise ValueError(f"Expected 960 v3 train pages, found {len(requests)}")

    plan_rows = {}
    for row in read_jsonl(SOURCE / "train.jsonl"):
        if row["task"] != "page_plan" or row.get("augmentation") != TARGET_MARKER or row.get("retry"):
            continue
        match = TARGETED_EXAMPLE.fullmatch(row["example_id"])
        if match and match["request_id"] in requests:
            plan_rows.setdefault(match["request_id"], []).append(row)
    missing = sorted(set(requests) - set(plan_rows))
    if missing or any(len(plan_rows[request_id]) != 1 for request_id in requests):
        raise ValueError(f"Expected one non-retry v3 page plan for each request; missing={len(missing)}")

    tokenizer = Tokenizer.from_file(str(ROOT / "data/tokenizer/tokenizer.json"))
    catalog = load_asset_catalog(ROOT)
    additions = []
    descriptors_without_process = []
    for request_id in sorted(requests):
        record = requests[request_id]
        request = record["request"]
        wire = json.loads(plan_rows[request_id][0]["target"])
        plan_errors = validate_plan_wire(wire, request, catalog)
        if plan_errors:
            raise ValueError(f"Invalid parent plan for {request_id}: {plan_errors}")
        plan = decode_plan(wire)
        process_descriptors = [item for item in plan["sections"] if item["role"] == "process"]
        if not process_descriptors:
            descriptors_without_process.append(request_id)
            continue
        if len(process_descriptors) != 1:
            raise ValueError(f"Expected one process descriptor for {request_id}")
        descriptor = process_descriptors[0]

        family_index = int(record["family_id"].removeprefix("family"))
        business_name = next(fact["value"] for fact in request["business_facts"] if fact["kind"] == "name")
        base_request, base_plan, base_sections, _ = make_page(
            family_index, "train", request["style_mode"], business_name
        )
        base_descriptor = next(item for item in base_plan["sections"] if item["role"] == "process")
        if base_descriptor != descriptor:
            raise ValueError(f"V3 process descriptor differs from the frozen curriculum for {request_id}")
        process_ids = descriptor["fact_ids"]
        base_facts = {fact["id"]: fact for fact in base_request["business_facts"]}
        request_facts = {fact["id"]: fact for fact in request["business_facts"]}
        if any(base_facts.get(fact_id) != request_facts.get(fact_id) for fact_id in process_ids):
            raise ValueError(f"V3 process facts differ from the frozen curriculum for {request_id}")
        target = next(section for section in base_sections if section["role"] == "process")
        errors = validate_section(target, descriptor, request, catalog) + fact_errors(target, descriptor, request)
        if errors:
            raise ValueError(f"Invalid process target for {request_id}: {errors}")

        prompt = section_prompt(request, plan, descriptor)
        target_text = serialize_task("section_content", target)
        budget = check_budget(tokenizer, prompt, OUTPUT_BUDGETS["section_content"])
        target_ids = tokenizer.encode(target_text).ids
        if len(target_ids) + 1 > OUTPUT_BUDGETS["section_content"]:
            raise ValueError(f"Process target exceeds output budget for {request_id}")
        total = budget["prefix_tokens"] + len(target_ids) + 1
        row = {
            "example_id": request_id + "-v4-process",
            "family_id": record["family_id"],
            "split": "train",
            "task": "section_content",
            "prompt": prompt,
            "target": target_text,
            "length": total - 1,
            "human_reviewed": False,
            "origin": "project-authored train-only process-role augmentation",
            "genre": request["genre"],
            "style_mode": request["style_mode"],
            "retry": False,
            "augmentation": "targeted-process-role-v4",
        }
        encode_task_row(row, tokenizer)
        additions.append(row)

    if descriptors_without_process or len(additions) != 960:
        raise ValueError(
            f"Expected 960 validated process targets, got {len(additions)}; "
            f"without process descriptor={len(descriptors_without_process)}"
        )

    source_train = (SOURCE / "train.jsonl").read_bytes()
    if not source_train.endswith(b"\n"):
        raise ValueError("Frozen v3 train file must end with a newline")
    source_rows = list(read_jsonl(SOURCE / "train.jsonl"))
    before_roles = role_counts(source_rows)
    if before_roles.get("process") != 480:
        raise ValueError(f"Expected 480 v3 process targets, found {before_roles.get('process')}")
    existing_ids = {row["example_id"] for row in source_rows}
    if any(row["example_id"] in existing_ids for row in additions):
        raise ValueError("A v4 example ID already exists in the v3 parent")

    temporary = SOURCE.parent / (".v4-tmp-" + uuid.uuid4().hex)
    try:
        shutil.copytree(SOURCE, temporary)
        with (temporary / "train.jsonl").open("ab") as handle:
            for row in additions:
                handle.write((json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8"))

        v4_manifest = dict(source_manifest)
        v4_manifest["version"] = "fullpage-v4"
        v4_manifest["parent_manifest_sha256"] = sha256_file(source_manifest_path)
        v4_manifest["overlay"] = {
            "kind": "train-only process section target augmentation",
            "parent_version": "fullpage-v3",
            "source_request_marker": "-v3-",
            "added_rows": len(additions),
            "process_descriptors_missing": len(descriptors_without_process),
            "human_reviewed": False,
            "validation_and_test_files_unchanged": True,
            "final_opened": False,
        }
        v4_manifest["task_counts"] = dict(source_manifest["task_counts"])
        v4_manifest["task_counts"]["train"] += len(additions)
        v4_manifest["files"] = dict(source_manifest["files"])
        train_path = temporary / "train.jsonl"
        v4_manifest["files"]["train.jsonl"] = {"sha256": sha256_file(train_path), "bytes": train_path.stat().st_size}
        v4_manifest["bytes"] = sum(info["bytes"] for info in v4_manifest["files"].values())

        max_prefix = dict(source_manifest["max_prefix"])
        max_target = dict(source_manifest["max_target_with_eos"])
        max_total = source_manifest["max_total_tokens"]
        long_train = source_manifest.get("long_train_rows", 0)
        for row in additions:
            budget = check_budget(tokenizer, row["prompt"], OUTPUT_BUDGETS["section_content"])
            target_tokens = len(tokenizer.encode(row["target"]).ids) + 1
            max_prefix["section_content"] = max(max_prefix.get("section_content", 0), budget["prefix_tokens"])
            max_target["section_content"] = max(max_target.get("section_content", 0), target_tokens)
            max_total = max(max_total, budget["prefix_tokens"] + target_tokens)
            if budget["prefix_tokens"] + target_tokens > 1024:
                long_train += 1
        v4_manifest["max_prefix"] = max_prefix
        v4_manifest["max_target_with_eos"] = max_target
        v4_manifest["max_total_tokens"] = max_total
        v4_manifest["long_train_rows"] = long_train
        (temporary / "manifest.json").unlink()
        write_json(temporary / "manifest.json", v4_manifest)

        os_manifest = read_json(temporary / "manifest.json")
        for name, info in os_manifest["files"].items():
            path = temporary / name
            if sha256_file(path) != info["sha256"] or path.stat().st_size != info["bytes"]:
                raise ValueError("V4 manifest checksum verification failed: " + name)
        validation_names = (
            "validation.jsonl", "validation.requests.jsonl", "test.jsonl", "test.requests.jsonl"
        )
        for name in validation_names:
            if os_manifest["files"][name] != source_manifest["files"][name]:
                raise ValueError("V4 changed a frozen held-out file: " + name)
        with (temporary / "train.jsonl").open("rb") as handle:
            if handle.read(len(source_train)) != source_train:
                raise ValueError("V3 train rows are not an unchanged prefix of v4")

        v4_rows = list(read_jsonl(temporary / "train.jsonl"))
        after_roles = role_counts(v4_rows)
        if len(v4_rows) != source_manifest["task_counts"]["train"] + len(additions):
            raise ValueError("V4 train row count does not match the manifest")
        if after_roles.get("process") != 1440 or after_roles.get("process") != before_roles["process"] + len(additions):
            raise ValueError("V4 process role count does not match the expected augmentation")

        DESTINATION.parent.mkdir(parents=True, exist_ok=True)
        if shutil.disk_usage(ROOT).free < RESERVE_BYTES:
            raise OSError("V4 preparation would breach the 15 GiB disk reserve")
        temporary.replace(DESTINATION)
        result = {
            "dataset": DESTINATION.relative_to(ROOT).as_posix(),
            "manifest_sha256": sha256_file(DESTINATION / "manifest.json"),
            "parent_manifest_sha256": v4_manifest["parent_manifest_sha256"],
            "parent_train_sha256": source_manifest["files"]["train.jsonl"]["sha256"],
            "train_rows_before": len(source_rows),
            "train_rows_after": len(v4_rows),
            "added_process_rows": len(additions),
            "process_role_rows_before": before_roles["process"],
            "process_role_rows_after": after_roles["process"],
            "task_counts_by_split": v4_manifest["task_counts"],
            "process_target_validation": "960/960 schema, descriptor, facts, prompt and token budget passed",
            "validation_and_test_hashes_unchanged": True,
            "v3_train_rows_unchanged_prefix": True,
            "human_reviewed": False,
            "final_opened": False,
            "disk_free_before_bytes": disk_before,
            "disk_free_after_bytes": shutil.disk_usage(ROOT).free,
        }
        write_json(REPORT, result)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return result
    except BaseException:
        if temporary.exists():
            shutil.rmtree(temporary)
        if DESTINATION.exists() and not REPORT.exists():
            shutil.rmtree(DESTINATION)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    if args.root.resolve() != ROOT:
        raise ValueError("V4 preparation is pinned to this project root")
    build_overlay()


if __name__ == "__main__":
    main()

"""Deterministic deduplication and whole-template-family train/validation/test splits."""
import argparse
import hashlib
import json
import math
import os
import random
from collections import Counter
from dataclasses import replace
from pathlib import Path

from .normalize import read_jsonl
from .schema import PageExample
from .sources import sha256_file, write_manifest

SPLITS = ("train", "validation", "test")


def _record(example):
    return example.to_record() if isinstance(example, PageExample) else example


def canonical_hash(example) -> str:
    row = _record(example)
    value = {"text": row["text"]} if "text" in row else {"prompt": row["prompt"], "target_spec": row["target_spec"]}
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


def deduplicate(examples):
    accepted, rejected, seen = [], [], set()
    for example in sorted(examples, key=lambda e: str(_record(e)["example_id"])):
        digest = canonical_hash(example)
        if digest in seen:
            rejected.append({"example_id": _record(example)["example_id"], "reason": "duplicate_canonical_hash", "sha256": digest})
        else:
            accepted.append(example)
            seen.add(digest)
    return accepted, rejected


def assign_splits(examples, seed: int, ratios=(0.8, 0.1, 0.1)):
    if len(ratios) != 3 or any(not math.isfinite(r) or r <= 0 for r in ratios) or not math.isclose(sum(ratios), 1.0):
        raise ValueError("Three positive finite split ratios must sum to one")
    groups = sorted({_record(e)["group_id"] for e in examples})
    if len(groups) < 10 or any(not isinstance(g, str) or not g for g in groups):
        raise ValueError("At least 10 nonempty template groups needed for reliable validation/test")
    random.Random(seed).shuffle(groups)
    train_count = max(1, min(len(groups) - 2, int(len(groups) * ratios[0])))
    validation_count = max(1, min(len(groups) - train_count - 1, int(len(groups) * ratios[1])))
    names = ["train"] * train_count + ["validation"] * validation_count + ["test"] * (len(groups) - train_count - validation_count)
    assignment = dict(zip(groups, names))
    result = [replace(e, split=assignment[e.group_id]) if isinstance(e, PageExample) else
              {**e, "split": assignment[e["group_id"]]} for e in examples]
    return sorted(result, key=lambda e: str(_record(e)["example_id"]))


def split_jsonl(input_path: Path, output_dir: Path, seed=42, ratios=(0.8, 0.1, 0.1)):
    rows = list(read_jsonl(input_path))
    unique, duplicates = deduplicate(rows)
    assigned = assign_splits(unique, seed, ratios)
    output_dir.mkdir(parents=True, exist_ok=True)
    counts = Counter()
    groups = {name: set() for name in SPLITS}
    # Report remains building until every output and checksum is complete.
    manifest_path = output_dir / "manifest.json"
    write_manifest(manifest_path, {"status": "building"})
    for name in SPLITS:
        path = output_dir / f"{name}.jsonl"
        partial = path.with_suffix(".jsonl.partial")
        with partial.open("w", encoding="utf-8") as handle:
            for row in assigned:
                if row["split"] == name:
                    handle.write(json.dumps(row, ensure_ascii=False) + "\n")
                    counts[name] += 1
                    groups[name].add(row["group_id"])
        os.replace(partial, path)
    overlap = sorted(set.union(*(groups[a] & groups[b] for a, b in [("train", "validation"), ("train", "test"), ("validation", "test")])))
    if overlap:
        raise ValueError("Template leakage across splits")
    report = {"status": "complete", "seed": seed, "ratios_by_group": list(ratios), "input_sha256": sha256_file(input_path),
              "source_rows": len(rows), "deduplicated_rows": len(unique), "duplicates": len(duplicates),
              "group_count": sum(len(g) for g in groups.values()), "group_counts": {name: len(group) for name, group in groups.items()},
              "row_counts": {name: counts[name] for name in SPLITS}, "group_overlap": overlap,
              "files": {name: {"path": name + ".jsonl", "sha256": sha256_file(output_dir / f"{name}.jsonl")} for name in SPLITS}}
    write_manifest(output_dir / "dedup_rejects.json", {"rejected": len(duplicates), "records": duplicates})
    write_manifest(manifest_path, report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=Path("configs/dataset.json"))
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    print(json.dumps(split_jsonl(args.input, args.output_dir, config["seed"], tuple(config["split_ratios"])), indent=2))


if __name__ == "__main__":
    main()

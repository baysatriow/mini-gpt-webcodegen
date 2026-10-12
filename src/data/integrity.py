"""Verify reusable phase lineage and reviewed SFT against authoritative source families."""
import json
from pathlib import Path

from .normalize import normalize_annotation, read_jsonl
from .sources import sha256_file
from .split import SPLITS, assignment_hash, canonical_hash, read_group_assignment


def reuse_tokenization(root: Path, previous: dict, split: dict, config: dict):
    required = ("tokenizer", "token_profiles", "token_caches")
    if not all(key in previous for key in required):
        raise ValueError("No complete existing tokenizer/cache lineage")
    token = previous["tokenizer"]
    local = json.loads((root / "data/tokenizer/manifest.json").read_text(encoding="utf-8"))
    if local != token or token.get("status") != "complete" or not token.get("trained_only_on_train"):
        raise ValueError("Tokenizer manifest mismatch or unverified train-only fit")
    if token["config"] != config or token["train_input_sha256"] != split["files"]["train"]["sha256"] or token["train_rows"] != split["row_counts"]["train"]:
        raise ValueError("Tokenizer input/config no longer matches current train partition")
    if sha256_file(root / "data/tokenizer/tokenizer.json") != token["tokenizer_sha256"]:
        raise ValueError("Tokenizer checksum mismatch")
    if set(previous["token_profiles"]) != set(SPLITS) or set(previous["token_caches"]) != set(SPLITS):
        raise ValueError("Missing split profile/cache metadata")
    for name in SPLITS:
        cache = previous["token_caches"][name]
        profile = previous["token_profiles"][name]
        path = root / f"data/processed/pretrain/{name}.tokens.bin"
        local_cache = json.loads(path.with_suffix(".json").read_text(encoding="utf-8"))
        if local_cache != cache or cache["source_sha256"] != split["files"][name]["sha256"]:
            raise ValueError(f"{name} cache input/manifest mismatch")
        if cache["block_size"] != config["block_size"] or cache["rows"] != split["row_counts"][name]:
            raise ValueError(f"{name} cache config/count mismatch")
        if path.stat().st_size != cache["bytes"] or cache["bytes"] != cache["tokens"] * 4 or sha256_file(path) != cache["sha256"]:
            raise ValueError(f"{name} cache checksum/bytes mismatch")
        if profile["rows"] != cache["rows"] or profile["total_tokens"] != cache["tokens"] or profile["block_size"] != config["block_size"]:
            raise ValueError(f"{name} token profile mismatch")
    return {key: previous[key] for key in required}


def validate_sft_artifacts(root: Path, sft: dict, source_rows: dict):
    directory = root / "data/processed/sft"
    manifest_path = directory / "manifest.json"
    if sft.get("status") == "awaiting_review":
        if sft.get("reviewed_production_rows") != 0 or (manifest_path.exists() and json.loads(manifest_path.read_text(encoding="utf-8")).get("status") == "complete"):
            raise ValueError("awaiting_review cannot reference a usable complete SFT dataset")
        return {"status": "awaiting_review", "reviewed_rows": 0}
    if sft.get("status") != "complete" or sft.get("reviewed_production_rows", 0) <= 0:
        raise ValueError("Invalid SFT phase status")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest != sft["split"] or manifest.get("split_policy") != "inherit_pretrain":
        raise ValueError("SFT split manifest or policy mismatch")
    global_map = read_group_assignment(root / "data/processed/pretrain")
    if manifest["pretrain_assignment_sha256"] != assignment_hash(global_map):
        raise ValueError("SFT authoritative pretraining allocation changed")
    read_group_assignment(directory)
    seen, reviewed = set(), 0
    for name in SPLITS:
        for row in read_jsonl(directory / f"{name}.jsonl"):
            source = source_rows.get(row.get("source_row_id"))
            if source is None:
                raise ValueError("SFT source row is absent from verified raw corpus")
            expected = normalize_annotation(source, {**row, "prompt_language": "id"}, {"id": source["source_id"]}).to_record()
            expected["split"] = name
            if row != expected:
                raise ValueError("SFT schema/review/provenance/source-family mismatch")
            if global_map.get(row["source_group_id"]) != name:
                raise ValueError("SFT family crosses authoritative pretraining partition")
            digest = canonical_hash(row)
            if digest in seen:
                raise ValueError("SFT exact duplicate within/across partitions")
            seen.add(digest)
            reviewed += 1
    if reviewed != manifest["deduplicated_rows"] or sft["reviewed_production_rows"] != manifest["source_rows"]:
        raise ValueError("SFT reviewed row counts mismatch")
    return {"status": "complete", "reviewed_rows": reviewed, "cross_phase_family_overlap": [], "provenance": "verified"}

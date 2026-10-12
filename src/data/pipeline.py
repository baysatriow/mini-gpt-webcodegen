"""Prepare verified local downloads, then optionally train BPE and build token caches."""
import argparse
import hashlib
import json
import shutil
from pathlib import Path

from .normalize import create_review_queue, normalize_jsonl, prepare_pretraining
from .sources import ROOT, sha256_file, write_manifest
from .split import split_jsonl


def load_completed_sources(config: dict, root: Path):
    paths, manifests = [], []
    for source in config["sources"]:
        manifest_path = root / f"data/manifests/{source['id']}-{source['limit']}.json"
        if not manifest_path.exists():
            raise ValueError(f"Missing complete download manifest: {source['id']}")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        signature = hashlib.sha256(json.dumps({"source": source, "seed": config["seed"]}, sort_keys=True).encode()).hexdigest()
        if manifest.get("status") != "complete" or manifest.get("selection_sha256") != signature:
            raise ValueError(f"Download incomplete or selection mismatch: {source['id']}")
        path = (root / manifest["output"]).resolve()
        if not path.is_relative_to((root / "data/raw").resolve()):
            raise ValueError("Source manifest path escapes raw data directory")
        if not path.exists() or sha256_file(path) != manifest["sha256"] or path.stat().st_size != manifest["bytes"]:
            raise ValueError(f"Checksum/byte mismatch: {source['id']}")
        paths.append(path)
        manifests.append(manifest)
    return paths, manifests


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "configs/dataset.json")
    parser.add_argument("--train-tokenizer", action="store_true")
    parser.add_argument("--annotations", type=Path)
    args = parser.parse_args(argv)
    config = json.loads(args.config.read_text(encoding="utf-8"))
    paths, manifests = load_completed_sources(config, ROOT)
    before = shutil.disk_usage(ROOT).free
    if before < config["reserve_free_bytes"] + 4 * sum(m["bytes"] for m in manifests):
        raise OSError("Insufficient storage for derived data while preserving reserve")
    summary_path = ROOT / "data/manifests/pipeline_summary.json"
    write_manifest(summary_path, {"status": "building"})
    output = ROOT / "data/processed/pretrain_full.jsonl"
    filtered = prepare_pretraining(paths, output, config["max_text_bytes"])
    print(f"HTML preprocessing: accepted={filtered['accepted']} rejected={filtered['rejected']}", flush=True)
    split = split_jsonl(output, ROOT / "data/processed/pretrain", config["seed"], tuple(config["split_ratios"]))
    print(f"Grouped split: {split['row_counts']}, groups={split['group_count']}, duplicates={split['duplicates']}", flush=True)
    queue = ROOT / "data/annotations/review_queue.jsonl"
    if not queue.exists():
        queue_count = create_review_queue(paths, queue)
    else:
        queue_count = sum(1 for _ in queue.open(encoding="utf-8"))
    sft = {"status": "awaiting_review", "draft_queue_rows": queue_count, "reviewed_production_rows": 0}
    if args.annotations:
        accepted, rejected = normalize_jsonl(paths, args.annotations, ROOT / "data/processed/sft_full.jsonl")
        sft.update(reviewed_production_rows=accepted, rejected=rejected)
        if accepted:
            sft.update(status="complete", split=split_jsonl(ROOT / "data/processed/sft_full.jsonl", ROOT / "data/processed/sft", config["seed"], tuple(config["split_ratios"])))
    summary = {"status": "complete", "pretrain": {k: v for k, v in filtered.items() if k != "rejects"},
               "split": split, "sft": sft, "raw_rows": sum(m["rows"] for m in manifests),
               "raw_bytes": sum(m["bytes"] for m in manifests), "free_bytes_before": before,
               "sources": [{"id": m["source"]["id"], "revision": m["source"]["revision"], "license": m["source"]["license_id"], "rows": m["rows"], "bytes": m["bytes"]} for m in manifests]}
    if args.train_tokenizer:
        from tokenizers import Tokenizer
        from .tokenizer import token_profile, train_tokenizer
        from .dataset import build_token_cache
        token_config = json.loads((ROOT / "configs/tokenizer.json").read_text(encoding="utf-8"))
        print("Training fresh byte-level BPE on train split only", flush=True)
        token_path = train_tokenizer(ROOT / "data/processed/pretrain/train.jsonl", ROOT / "data/tokenizer", token_config)
        tokenizer = Tokenizer.from_file(str(token_path))
        summary["tokenizer"] = json.loads((ROOT / "data/tokenizer/manifest.json").read_text())
        write_manifest(ROOT / "data/manifests/tokenizer.json", summary["tokenizer"])
        profiles, caches = {}, {}
        for name in ["train", "validation", "test"]:
            source = ROOT / f"data/processed/pretrain/{name}.jsonl"
            profiles[name] = token_profile(source, tokenizer, token_config["block_size"])
            caches[name] = build_token_cache(source, ROOT / f"data/processed/pretrain/{name}.tokens.bin", tokenizer, token_config["block_size"])
            print(f"{name}: {caches[name]['tokens']} tokens, {caches[name]['blocks']} blocks", flush=True)
        summary.update(token_profiles=profiles, token_caches=caches)
    summary["free_bytes_after"] = shutil.disk_usage(ROOT).free
    write_manifest(summary_path, summary)
    print(json.dumps({"status": summary["status"], "sft": sft, "free_bytes_after": summary["free_bytes_after"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

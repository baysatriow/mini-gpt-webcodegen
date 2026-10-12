"""Verify actual downloaded data, split isolation, tokenizer lineage, caches, and CUDA batch transfer."""
import json
import re
import shutil
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np
import torch
from tokenizers import Tokenizer
from torch.utils.data import DataLoader

from src.data.dataset import PretrainingBlockDataset
from src.data.normalize import read_jsonl
from src.data.pipeline import load_completed_sources
from src.data.sources import sha256_file, write_manifest
from src.data.split import canonical_hash


def main():
    config = json.loads((ROOT / "configs/dataset.json").read_text())
    summary = json.loads((ROOT / "data/manifests/pipeline_summary.json").read_text())
    assert summary["status"] == "complete", "Pipeline is incomplete"
    source_paths, manifests = load_completed_sources(config, ROOT)
    raw_counts, scripts = Counter(), Counter()
    for path, manifest in zip(source_paths, manifests):
        count = 0
        for row in read_jsonl(path):
            assert not {"image", "images"} & set(row), "Image payload found"
            assert row["source_revision"] == manifest["source"]["revision"]
            assert row["license_id"] == manifest["source"]["license_id"]
            assert __import__("hashlib").sha256(row["text"].encode()).hexdigest() == row["text_sha256"]
            count += 1
            scripts[row["source_id"]] += bool(re.search(r"<script(?:\s|>)", row["text"], re.I))
        assert count == manifest["rows"]
        raw_counts[manifest["source"]["id"]] = count
    groups, hashes, transformed = {}, {}, Counter()
    for name in ["train", "validation", "test"]:
        path = ROOT / f"data/processed/pretrain/{name}.jsonl"
        assert sha256_file(path) == summary["split"]["files"][name]["sha256"]
        groups[name], hashes[name] = set(), set()
        count = 0
        for row in read_jsonl(path):
            assert row["split"] == name
            groups[name].add(row["group_id"])
            hashes[name].add(canonical_hash(row))
            transformed[row["html_transform"]] += 1
            count += 1
        assert count == summary["split"]["row_counts"][name]
        assert len(hashes[name]) == count, "Exact duplicate within split"
    for a, b in [("train", "validation"), ("train", "test"), ("validation", "test")]:
        assert not groups[a] & groups[b], "Group leakage"
        assert not hashes[a] & hashes[b], "Exact duplicate leakage"
    token_path = ROOT / "data/tokenizer/tokenizer.json"
    token_manifest = summary["tokenizer"]
    assert token_manifest["trained_only_on_train"]
    assert token_manifest["train_rows"] == summary["split"]["row_counts"]["train"]
    assert sha256_file(token_path) == token_manifest["tokenizer_sha256"]
    assert sha256_file(ROOT / "data/processed/pretrain/train.jsonl") == token_manifest["train_input_sha256"]
    tokenizer = Tokenizer.from_file(str(token_path))
    text = 'Buat halaman Indonesia: café, belajar, <div class="grid">Halo</div>'
    assert tokenizer.decode(tokenizer.encode(text).ids, skip_special_tokens=False) == text
    for name, report in summary["token_caches"].items():
        path = ROOT / f"data/processed/pretrain/{name}.tokens.bin"
        assert sha256_file(path) == report["sha256"]
        assert path.stat().st_size == report["tokens"] * 4
        tokens = np.memmap(path, mode="r", dtype="<u4")
        assert int(tokens.max()) < tokenizer.get_vocab_size()
        del tokens
    train = PretrainingBlockDataset(ROOT / "data/processed/pretrain/train.tokens.bin", 1024, tokenizer.token_to_id("<pad>"))
    batch = next(iter(DataLoader(train, batch_size=2, num_workers=0)))
    assert tuple(batch["input_ids"].shape) == (2, 1024)
    assert torch.equal(batch["input_ids"][:, 1:], batch["labels"][:, :-1]), "Next-token labels shifted incorrectly"
    last = train[len(train)-1]
    assert (last["labels"][last["input_ids"] == tokenizer.token_to_id("<pad>")] == -100).all()
    assert torch.cuda.is_available(), "CUDA not available in project VENV"
    gpu_batch = {key: value.to("cuda") for key, value in batch.items()}
    torch.cuda.synchronize()
    assert all(value.is_cuda for value in gpu_batch.values())
    queue = list(read_jsonl(ROOT / "data/annotations/review_queue.jsonl"))
    assert all(row["annotation_status"] == "draft" and not row["reviewer"] for row in queue)
    assert summary["sft"]["reviewed_production_rows"] == 0
    assert not (ROOT / "data/processed/sft/train.jsonl").exists()
    result = {"status": "passed", "raw_rows": dict(raw_counts), "rows_with_script_tag": dict(scripts),
              "group_overlap": [], "exact_duplicate_overlap": [], "normalized_transforms": dict(transformed),
              "split_counts": summary["split"]["row_counts"], "vocab_size": tokenizer.get_vocab_size(),
              "tokenizer_fit": "train only", "token_cache_sha256": "verified all splits",
              "gpu": torch.cuda.get_device_name(0), "batch_shape": [2, 1024],
              "gpu_batch_transfer": True, "model_training_executed": False,
              "draft_annotations": len(queue), "reviewed_annotations": 0,
              "free_bytes": shutil.disk_usage(ROOT).free}
    write_manifest(ROOT / "data/manifests/validation_summary.json", result)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

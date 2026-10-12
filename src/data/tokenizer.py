"""Train a new byte-level BPE exclusively on the project's train partition."""
import argparse
import json
import os
from pathlib import Path

import numpy as np
from tokenizers import Tokenizer, decoders, models, pre_tokenizers, trainers

from .normalize import read_jsonl
from .sources import sha256_file, write_manifest

SPECIAL_TOKENS = ["<pad>", "<unk>", "<bos>", "<eos>", "<prompt>", "<target>"]


def record_text(row):
    if "text" in row:
        return row["text"]
    if row.get("annotation_status") != "reviewed":
        raise ValueError("Instruction tokenization requires reviewed annotations")
    return row["prompt"] + "\n" + json.dumps(row["target_spec"], sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def train_tokenizer(train_jsonl: Path, output_dir: Path, config: dict) -> Path:
    stats = {"train_rows": 0}
    def corpus():
        for row in read_jsonl(train_jsonl):
            if row.get("split") != "train":
                raise ValueError("Tokenizer fitting may only consume split=train")
            text = record_text(row)
            if not isinstance(text, str) or not text:
                raise ValueError("Empty/non-string train text")
            stats["train_rows"] += 1
            yield text
    tokenizer = Tokenizer(models.BPE(unk_token="<unk>"))
    tokenizer.pre_tokenizer = pre_tokenizers.ByteLevel(add_prefix_space=False)
    tokenizer.decoder = decoders.ByteLevel()
    trainer = trainers.BpeTrainer(vocab_size=config.get("vocab_size", 8192), min_frequency=config.get("min_frequency", 2),
                                  special_tokens=SPECIAL_TOKENS, initial_alphabet=sorted(pre_tokenizers.ByteLevel.alphabet()), show_progress=False)
    tokenizer.train_from_iterator(corpus(), trainer=trainer)
    if not stats["train_rows"]:
        raise ValueError("Cannot train tokenizer on empty train split")
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "tokenizer.json"
    temporary = path.with_suffix(".json.partial")
    tokenizer.save(str(temporary))
    os.replace(temporary, path)
    manifest = {"status": "complete", **stats, "trained_only_on_train": True,
                "train_input_sha256": sha256_file(train_jsonl), "tokenizer_sha256": sha256_file(path),
                "vocab_size": tokenizer.get_vocab_size(), "requested_vocab_size": config.get("vocab_size", 8192),
                "special_token_ids": {token: tokenizer.token_to_id(token) for token in SPECIAL_TOKENS}, "config": config}
    write_manifest(output_dir / "manifest.json", manifest)
    return path


def token_profile(path, tokenizer, block_size):
    sizes = [len(tokenizer.encode(record_text(row), add_special_tokens=False).ids) + 2 for row in read_jsonl(path)]
    if not sizes:
        return {"rows": 0}
    return {"rows": len(sizes), "total_tokens": sum(sizes), "p50": float(np.percentile(sizes, 50)),
            "p95": float(np.percentile(sizes, 95)), "max": max(sizes), "block_size": block_size,
            "documents_above_block_size": sum(size > block_size for size in sizes),
            "pretrain_long_documents": "packed across blocks without discarding tail; SFT oversize rejected"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("data/tokenizer"))
    parser.add_argument("--config", type=Path, default=Path("configs/tokenizer.json"))
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    print(train_tokenizer(args.train, args.output_dir, config))


if __name__ == "__main__":
    main()

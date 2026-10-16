"""Compact token dataset and length-bucket sampler for request extraction."""

from __future__ import annotations

import hashlib
import json
import math
import random
from array import array
from pathlib import Path

import torch
from torch.utils.data import DataLoader, Dataset

from src.data.normalize import read_jsonl
from src.data.tokenizer import SPECIAL_TOKENS
from src.fullpage.request_extract_contracts import canonical, validate_scoped_output
from src.fullpage.serialization import check_budget
from src.training.engine import ResumableBatchSampler


BLOCK_SIZE = 2048
LENGTH_BUCKETS = (256, 512, 1024, 1536, BLOCK_SIZE)


def encode_request_extract_row(row: dict, tokenizer, output_budget: int, *, block_size: int = BLOCK_SIZE) -> dict:
    """Encode one immutable prompt/target row without truncation or target loss masking."""
    if row.get("canonical_format") != "prompt-messages-v1":
        raise ValueError("Expected a canonical request_extract row")
    if not isinstance(row.get("prompt"), str) or not row["prompt"].strip():
        raise ValueError("Extractor prompt is empty")
    target_text = row.get("target")
    if not isinstance(target_text, str):
        raise ValueError("Extractor target is missing")
    target = json.loads(target_text)
    if canonical(target) != target_text:
        raise ValueError("Extractor target is not canonical JSON")
    errors = validate_scoped_output(target, row.get("scope"))
    if errors:
        raise ValueError("Invalid scoped extractor target: " + "; ".join(errors[:3]))
    if any(token in row["prompt"] or token in target_text for token in SPECIAL_TOKENS):
        raise ValueError("Reserved tokenizer delimiter in extractor content")

    required = {token: tokenizer.token_to_id(token) for token in SPECIAL_TOKENS}
    if any(token_id is None for token_id in required.values()) or required["<pad>"] != 0:
        raise ValueError("Project tokenizer delimiters or pad ID differ from the frozen contract")
    check_budget(tokenizer, row["prompt"], output_budget, block_size=block_size)
    prompt_ids = tokenizer.encode(row["prompt"], add_special_tokens=False).ids
    target_ids = tokenizer.encode(target_text, add_special_tokens=False).ids + [required["<eos>"]]
    if len(target_ids) > output_budget:
        raise ValueError("Extractor target exceeds its reserved output budget")

    prefix = [required["<bos>"], required["<prompt>"]] + prompt_ids + [required["<target>"]]
    sequence = prefix + target_ids
    if len(sequence) > block_size:
        raise ValueError("Extractor prompt and full target exceed the context; content is never truncated")
    input_ids = sequence[:-1]
    labels = sequence[1:]
    labels[:len(prefix) - 1] = [-100] * (len(prefix) - 1)
    return {"input_ids": input_ids, "labels": labels, "length": len(input_ids)}


class RequestExtractDataset(Dataset):
    """Hold token IDs in compact contiguous buffers instead of Python integer lists."""

    def __init__(self, path: Path, tokenizer, *, split: str, manifest: dict):
        if split not in {"train", "development"}:
            raise ValueError("Extractor data split must be train or development")
        filename = "train.jsonl" if split == "train" else "development.jsonl"
        if filename not in manifest.get("files", {}):
            raise ValueError("Extractor manifest does not identify the requested split")
        self.split = split
        self.file_sha256 = manifest["files"][filename]["sha256"]
        self.input_ids = array("i")
        self.labels = array("i")
        self.offsets = [0]
        self.lengths: list[int] = []
        self.example_ids: list[str] = []
        budgets = manifest["output_budgets"]
        for row in read_jsonl(path):
            if row.get("split") != split:
                raise ValueError("Extractor JSONL contains a row from another split")
            scope = row.get("scope")
            if scope not in budgets:
                raise ValueError("Extractor row has an unknown scope")
            encoded = encode_request_extract_row(row, tokenizer, budgets[scope])
            if len(encoded["input_ids"]) != len(encoded["labels"]):
                raise ValueError("Extractor inputs and shifted labels are misaligned")
            self.input_ids.extend(encoded["input_ids"])
            self.labels.extend(encoded["labels"])
            self.offsets.append(len(self.input_ids))
            self.lengths.append(encoded["length"])
            self.example_ids.append(row["example_id"])
        if not self.lengths:
            raise ValueError("Extractor split has no rows")
        if self.input_ids.itemsize != 4 or self.labels.itemsize != 4:
            raise RuntimeError("Compact token buffers require 32-bit array elements")

    def __len__(self) -> int:
        return len(self.lengths)

    def __getitem__(self, index: int) -> dict[str, torch.Tensor | int]:
        if index < 0 or index >= len(self):
            raise IndexError(index)
        start, end = self.offsets[index], self.offsets[index + 1]
        input_ids = torch.frombuffer(memoryview(self.input_ids)[start:end], dtype=torch.int32).to(torch.long)
        labels = torch.frombuffer(memoryview(self.labels)[start:end], dtype=torch.int32).to(torch.long)
        return {"input_ids": input_ids, "labels": labels, "length": self.lengths[index]}


def trim_request_extract_collate(rows: list[dict]) -> dict[str, torch.Tensor]:
    """Pad compact dataset tensors without routing them through the list collator."""
    if not rows:
        raise ValueError("Cannot collate an empty request-extraction batch")
    length = max(row["length"] for row in rows)
    input_ids = torch.zeros((len(rows), length), dtype=torch.long)
    labels = torch.full((len(rows), length), -100, dtype=torch.long)
    for index, row in enumerate(rows):
        ids, targets = row["input_ids"], row["labels"]
        if ids.ndim != 1 or targets.ndim != 1 or ids.numel() != row["length"] or targets.numel() != row["length"]:
            raise ValueError("Extractor row tensors and recorded length do not align")
        input_ids[index, :row["length"]] = ids
        labels[index, :row["length"]] = targets
    return {"input_ids": input_ids, "labels": labels}


class RequestExtractBatchSampler(ResumableBatchSampler):
    """Shuffle rows within length buckets and bind exact-resume state to the data file."""

    def __init__(self, lengths, batch_size: int, seed: int, *, dataset_sha256: str):
        super().__init__(len(lengths), batch_size, seed)
        if not isinstance(dataset_sha256, str) or len(dataset_sha256) != 64:
            raise ValueError("Extractor sampler needs the frozen dataset SHA-256")
        self.groups: dict[int, list[int]] = {}
        for index, length in enumerate(lengths):
            bucket = next((bound for bound in LENGTH_BUCKETS if length <= bound), None)
            if bucket is None:
                raise ValueError("Extractor sequence exceeds its largest length bucket")
            self.groups.setdefault(bucket, []).append(index)
        self.batches_per_epoch = sum(math.ceil(len(group) / batch_size) for group in self.groups.values())
        self.fingerprint = hashlib.sha256(canonical({
            "split_sha256": dataset_sha256,
            "lengths": list(lengths),
            "batch_size": batch_size,
            "seed": seed,
            "length_buckets": LENGTH_BUCKETS,
        }).encode("utf-8")).hexdigest()

    def batches(self, epoch: int) -> list[list[int]]:
        rng = random.Random(self.seed + epoch)
        batches: list[list[int]] = []
        for bucket in sorted(self.groups):
            order = list(self.groups[bucket])
            rng.shuffle(order)
            batches.extend(order[index:index + self.batch_size] for index in range(0, len(order), self.batch_size))
        rng.shuffle(batches)
        return batches

    def __iter__(self):
        """Resume over the subclass's bucketed batches, not the base flat permutation."""
        epoch, offset = divmod(self.cursor, self.batches_per_epoch)
        for batch in self.batches(epoch)[offset:]:
            self.cursor += 1
            yield batch

    def state_dict(self) -> dict:
        return {**super().state_dict(), "fingerprint": self.fingerprint, "length_buckets": list(LENGTH_BUCKETS)}

    def load_state_dict(self, state: dict) -> None:
        if state.get("fingerprint") != self.fingerprint or state.get("length_buckets") != list(LENGTH_BUCKETS):
            raise ValueError("Extractor sampler dataset, bucket, or batch settings differ")
        super().load_state_dict(state)


def build_request_extract_loaders(root: Path, config: dict, manifest: dict):
    """Build one resumable train loader and one deterministic development loader."""
    from tokenizers import Tokenizer

    root = Path(root).resolve()
    data_dir = root / config["dataset_dir"]
    tokenizer_path = root / config["tokenizer"]
    tokenizer = Tokenizer.from_file(str(tokenizer_path))
    train_data = RequestExtractDataset(data_dir / "train.jsonl", tokenizer, split="train", manifest=manifest)
    development_data = RequestExtractDataset(
        data_dir / "development.jsonl", tokenizer, split="development", manifest=manifest,
    )
    batch_size = config["batch_size"]
    train_sampler = RequestExtractBatchSampler(
        train_data.lengths, batch_size, config["seed"], dataset_sha256=train_data.file_sha256,
    )
    train_loader = DataLoader(
        train_data, batch_sampler=train_sampler, collate_fn=trim_request_extract_collate,
        num_workers=0, pin_memory=config.get("performance", {}).get("pin_memory", False),
    )
    validation_loader = DataLoader(
        development_data, batch_size=config.get("validation_batch_size", batch_size),
        shuffle=False, collate_fn=trim_request_extract_collate, num_workers=0,
        pin_memory=config.get("performance", {}).get("pin_memory", False),
    )
    return train_data, development_data, train_loader, validation_loader

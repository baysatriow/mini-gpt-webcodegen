"""Already-shifted next-token labels, instruction masks, and memory-mapped token blocks."""
import array
import json
import math
import os
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import Dataset

from .normalize import read_jsonl
from .schema import validate_page_spec
from .sources import sha256_file, write_manifest
from .tokenizer import SPECIAL_TOKENS


def _special(tokenizer, name):
    token = tokenizer.token_to_id(name)
    if token is None:
        raise ValueError(f"Tokenizer missing special token {name}")
    return token


def encode_pretraining(text: str, tokenizer):
    sequence = [_special(tokenizer, "<bos>")] + tokenizer.encode(text, add_special_tokens=False).ids + [_special(tokenizer, "<eos>")]
    return sequence[:-1], sequence[1:]


def encode_sft(prompt: str, target_json: str, tokenizer, block_size: int):
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("SFT prompt is empty")
    if any(token in prompt or token in target_json for token in SPECIAL_TOKENS):
        raise ValueError("Reserved delimiters are not allowed in instruction payloads")
    errors = validate_page_spec(json.loads(target_json))
    if errors:
        raise ValueError("Invalid PageSpec target: " + "; ".join(errors))
    prefix = [_special(tokenizer, "<bos>"), _special(tokenizer, "<prompt>")]
    prefix += tokenizer.encode(prompt, add_special_tokens=False).ids + [_special(tokenizer, "<target>")]
    target = tokenizer.encode(target_json, add_special_tokens=False).ids + [_special(tokenizer, "<eos>")]
    sequence = prefix + target
    if len(sequence) - 1 > block_size:
        raise ValueError(f"SFT sequence requires {len(sequence)-1} tokens, exceeds {block_size}; JSON not truncated")
    ids, labels = sequence[:-1], sequence[1:]
    labels[:len(prefix)-1] = [-100] * (len(prefix)-1)
    padding = block_size - len(ids)
    return ids + [_special(tokenizer, "<pad>")] * padding, labels + [-100] * padding


def _block(tokens, index, block_size, pad_id):
    start = index * block_size
    sequence = list(tokens[start:start + block_size + 1])
    ids, labels = sequence[:-1], sequence[1:]
    padding = block_size - len(ids)
    return {"input_ids": torch.tensor(ids + [pad_id] * padding, dtype=torch.long),
            "labels": torch.tensor(labels + [-100] * padding, dtype=torch.long)}


class PageSpecDataset(Dataset):
    def __init__(self, rows, tokenizer, mode, block_size):
        if mode not in {"pretrain", "sft"} or block_size < 2:
            raise ValueError("Expected pretrain/sft and block_size >= 2")
        self.rows = list(rows)
        self.tokenizer, self.mode, self.block_size = tokenizer, mode, block_size
        self.pad_id = _special(tokenizer, "<pad>")
        self.tokens = array.array("I")
        if mode == "pretrain":
            for row in self.rows:
                x, y = encode_pretraining(row["text"], tokenizer)
                self.tokens.extend(x + [y[-1]])
        else:
            for row in self.rows:
                if row.get("annotation_status") != "reviewed":
                    raise ValueError("SFT dataset refuses draft/unreviewed records")
                encode_sft(row["prompt"], json.dumps(row["target_spec"], sort_keys=True, ensure_ascii=False, separators=(",", ":")), tokenizer, block_size)

    def __len__(self):
        return max(0, math.ceil((len(self.tokens)-1) / self.block_size)) if self.mode == "pretrain" else len(self.rows)

    def __getitem__(self, index):
        if index < 0 or index >= len(self):
            raise IndexError(index)
        if self.mode == "pretrain":
            return _block(self.tokens, index, self.block_size, self.pad_id)
        row = self.rows[index]
        ids, labels = encode_sft(row["prompt"], json.dumps(row["target_spec"], sort_keys=True, ensure_ascii=False, separators=(",", ":")), self.tokenizer, self.block_size)
        return {"input_ids": torch.tensor(ids, dtype=torch.long), "labels": torch.tensor(labels, dtype=torch.long)}


class PretrainingBlockDataset(Dataset):
    def __init__(self, token_file: Path, block_size: int, pad_id: int = 0):
        if token_file.stat().st_size % 4 or token_file.stat().st_size < 8 or block_size < 2:
            raise ValueError("Invalid uint32 token cache or block size")
        self.tokens = np.memmap(token_file, dtype="<u4", mode="r")
        self.block_size, self.pad_id = block_size, pad_id

    def __len__(self):
        return math.ceil((len(self.tokens)-1) / self.block_size)

    def __getitem__(self, index):
        if index < 0 or index >= len(self):
            raise IndexError(index)
        return _block(self.tokens, index, self.block_size, self.pad_id)


def build_token_cache(input_path: Path, output_path: Path, tokenizer, block_size: int):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    partial = output_path.with_suffix(".bin.partial")
    count, rows = 0, 0
    with partial.open("wb") as output:
        for row in read_jsonl(input_path):
            x, y = encode_pretraining(row["text"], tokenizer)
            ids = x + [y[-1]]
            output.write(np.asarray(ids, dtype="<u4").tobytes())
            count += len(ids)
            rows += 1
    if count < 2:
        raise ValueError("Not enough tokens for a pretraining batch")
    os.replace(partial, output_path)
    report = {"rows": rows, "tokens": count, "blocks": math.ceil((count-1)/block_size), "block_size": block_size,
              "dtype": "uint32 little-endian", "bytes": output_path.stat().st_size,
              "source_sha256": sha256_file(input_path), "sha256": sha256_file(output_path),
              "label_alignment": "labels[i] is next token for input_ids[i]; do not shift again in model loss"}
    write_manifest(output_path.with_suffix(".json"), report)
    return report

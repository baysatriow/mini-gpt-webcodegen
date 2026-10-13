"""Measure candidate GPU batches with disposable random-init Mini GPT updates."""
import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import torch
import torch.nn.functional as F
from torch.utils.data import DataLoader

from src.data.dataset import PretrainingBlockDataset
from src.data.sources import sha256_file, write_manifest
from src.models.minigpt import MiniGPT


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    config = json.loads((ROOT / "configs/model.json").read_text())
    dataset = PretrainingBlockDataset(ROOT / "data/processed/pretrain/train.tokens.bin", config["block_size"])
    records = []
    for batch_size in [1, 2, 4]:
        torch.manual_seed(42)
        torch.cuda.empty_cache()
        torch.cuda.reset_peak_memory_stats()
        model = MiniGPT(config).cuda()
        optimizer = torch.optim.AdamW(model.parameters(), lr=3e-4)
        batch = next(iter(DataLoader(dataset, batch_size=batch_size, num_workers=0)))
        batch = {key: tensor.cuda() for key, tensor in batch.items()}
        started = time.perf_counter()
        try:
            for step in range(4):
                optimizer.zero_grad(set_to_none=True)
                with torch.autocast("cuda", dtype=torch.bfloat16):
                    logits = model(batch["input_ids"])
                    loss = F.cross_entropy(logits.float().reshape(-1, config["vocab_size"]), batch["labels"].reshape(-1), ignore_index=-100)
                if not torch.isfinite(loss):
                    raise FloatingPointError("Nonfinite profile loss")
                loss.backward()
                norm = torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0, error_if_nonfinite=True)
                optimizer.step()
                torch.cuda.synchronize()
                if step == 0:
                    started = time.perf_counter()
            seconds = (time.perf_counter() - started) / 3
            record = {"batch_size": batch_size, "status": "passed", "seconds_per_step": seconds,
                      "tokens_per_second": batch_size * config["block_size"] / seconds,
                      "loss": float(loss.detach()), "grad_norm": float(norm.detach()),
                      "peak_allocated_bytes": torch.cuda.max_memory_allocated(), "peak_reserved_bytes": torch.cuda.max_memory_reserved()}
        except torch.cuda.OutOfMemoryError as error:
            record = {"batch_size": batch_size, "status": "oom", "error": str(error)}
        records.append(record)
        print(json.dumps(record), flush=True)
        del optimizer, model, batch
    report = {"run_id": args.run_id, "kind": "profiling; disposable weights; no production checkpoint",
              "status": "passed" if any(r["status"] == "passed" for r in records) else "failed",
              "gpu": torch.cuda.get_device_name(), "model_config": config,
              "parameter_count": MiniGPT(config).parameter_count(),
              "precision": "bf16", "records": records, "seed": 42,
              "tokenizer_sha256": sha256_file(ROOT / "data/tokenizer/tokenizer.json")}
    write_manifest(ROOT / f"outputs/metrics/{args.run_id}_profile.json", report)
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())

"""Check CUDA, disk headroom, and one disposable maximum-length training batch."""

from __future__ import annotations

import argparse
import gc
import json
import math
import os
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = Path("configs/fullpage/training-request-extract-v1.json")
DEFAULT_REPORT = Path("outputs/request_extract/v1/GPU_PREFLIGHT.json")


def run_preflight(root: Path, config_path: Path, report_path: Path) -> dict:
    os.environ["PYTORCH_ALLOC_CONF"] = "expandable_segments:True"
    import shutil

    import torch
    from src.fullpage.request_extract_dataset import build_request_extract_loaders, trim_request_extract_collate
    from src.fullpage.request_extract_lineage import verify_request_extract_sources
    from src.models.minigpt import MiniGPT
    from src.training.engine import train_one_step

    root = Path(root).resolve()
    config_path = Path(config_path)
    config_path = config_path if config_path.is_absolute() else root / config_path
    report_path = Path(report_path)
    report_path = report_path if report_path.is_absolute() else root / report_path
    if not config_path.resolve().is_relative_to(root) or not report_path.resolve().is_relative_to(root):
        raise ValueError("Preflight input/output paths must remain inside the project")
    if report_path.exists():
        raise FileExistsError("Preflight report destination must be new")
    config = json.loads(config_path.read_text(encoding="utf-8"))
    parent, _ = verify_request_extract_sources(config, root)
    gpu_name = torch.cuda.get_device_name(0) if torch.cuda.is_available() else None
    total_gpu = torch.cuda.get_device_properties(0).total_memory if torch.cuda.is_available() else 0
    free_disk = shutil.disk_usage(root).free
    parameter_count = sum(t.numel() for t in {t.data_ptr(): t for t in parent["model"].values()}.values())
    estimated_checkpoint_bytes = parameter_count * 12 * 6 + 64 * 1024**2
    disk_required = config["reserve_free_bytes"] + estimated_checkpoint_bytes
    base = {
        "status": "failed",
        "config_sha256": __import__("hashlib").sha256(config_path.read_bytes()).hexdigest(),
        "selected_parent_sha256": config["initial_checkpoint_sha256"],
        "gpu": gpu_name,
        "gpu_total_bytes": total_gpu,
        "free_disk_bytes_before": free_disk,
        "checkpoint_space_estimate_bytes": estimated_checkpoint_bytes,
        "disk_reserve_bytes": config["reserve_free_bytes"],
        "disk_headroom_after_reserve_and_checkpoint_estimate": free_disk - disk_required,
        "training_step_saved": False,
        "checkpoint_written": False,
    }
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is unavailable; no training preflight step was attempted")
    if gpu_name != "NVIDIA GeForce RTX 5070":
        raise RuntimeError("Extractor training preflight requires the RTX 5070")
    if not torch.cuda.is_bf16_supported():
        raise RuntimeError("RTX 5070 does not report BF16 support")
    if free_disk < disk_required:
        raise OSError("Disk headroom is below the frozen reserve and checkpoint estimate")

    manifest = json.loads((root / config["dataset_dir"] / "manifest.json").read_text(encoding="utf-8"))
    train_data, _, _, _ = build_request_extract_loaders(root, config, manifest)
    batch_indices = sorted(range(len(train_data)), key=lambda index: train_data.lengths[index], reverse=True)[:config["batch_size"]]
    if len(batch_indices) != config["batch_size"]:
        raise ValueError("Training data cannot fill the configured preflight batch")
    batch = trim_request_extract_collate([train_data[index] for index in batch_indices])
    batch_length = int(batch["input_ids"].shape[1])
    if batch_length != max(train_data.lengths[index] for index in batch_indices):
        raise ValueError("Preflight batch does not match the selected maximum-length rows")

    device = torch.device("cuda")
    model = MiniGPT(config["model_config"]).to(device)
    model.load_state_dict(parent["model"], strict=True)
    model.set_attention_backend(config["performance"]["attention_backend"])
    model.supervised_only_logits = config["performance"]["supervised_only_logits"]
    model.validation_supervised_only_logits = config["performance"]["validation_supervised_only_logits"]
    optimizer = torch.optim.AdamW(
        model.parameters(), lr=config["learning_rate"], betas=tuple(config["betas"]),
        weight_decay=config["weight_decay"], fused=config["performance"]["fused_adamw"],
    )
    del parent
    gc.collect()
    torch.cuda.synchronize()
    free_gpu_before, total_gpu = torch.cuda.mem_get_info()
    baseline_reserved = torch.cuda.memory_reserved()
    torch.cuda.reset_peak_memory_stats()
    start = time.perf_counter()
    result = train_one_step(
        model, batch, optimizer, None, "sft", precision=config["precision"], grad_clip=config["grad_clip"],
    )
    torch.cuda.synchronize()
    elapsed = time.perf_counter() - start
    peak_allocated = torch.cuda.max_memory_allocated()
    peak_reserved = torch.cuda.max_memory_reserved()
    incremental_reserved = max(0, peak_reserved - baseline_reserved)
    gpu_headroom = free_gpu_before - incremental_reserved
    preflight_passed = gpu_headroom >= 512 * 1024**2 and all(
        isinstance(result[name], (int, float)) and math.isfinite(result[name])
        for name in ("loss", "grad_norm", "valid_tokens")
    )
    report = {
        **base,
        "status": "passed" if preflight_passed else "failed",
        "gpu_total_bytes": total_gpu,
        "gpu_free_bytes_before_batch": free_gpu_before,
        "gpu_peak_allocated_bytes": peak_allocated,
        "gpu_peak_reserved_bytes": peak_reserved,
        "gpu_incremental_reserved_bytes": incremental_reserved,
        "gpu_headroom_after_peak_bytes": gpu_headroom,
        "batch_size": config["batch_size"],
        "batch_sequence_length": batch_length,
        "batch_valid_tokens": result["valid_tokens"],
        "disposable_loss": result["loss"],
        "disposable_grad_norm": result["grad_norm"],
        "disposable_step_seconds": elapsed,
        "training_step_saved": False,
        "checkpoint_written": False,
        "development_used_for_updates": False,
        "final_opened": False,
        "final_used": False,
        "note": "One ephemeral optimizer update on the longest train batch; parameters and optimizer were discarded without saving a checkpoint.",
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    if not preflight_passed:
        raise RuntimeError("CUDA preflight did not retain the required 512 MiB device headroom")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    report = run_preflight(args.root, args.config, args.report)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

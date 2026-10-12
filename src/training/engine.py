"""Token-weighted training with deterministic data cursor and atomic recoverable checkpoints."""
import json
import math
import os
import random
import re
import shutil
import subprocess
import time
import traceback
from contextlib import nullcontext
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F

from src.data.sources import sha256_file, write_manifest
from src.models.minigpt import MiniGPT


def seed_everything(seed):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.benchmark = False


def capture_rng_state():
    numpy = np.random.get_state()
    return {"python": random.getstate(), "numpy": {"name": numpy[0], "keys": torch.tensor(numpy[1].astype(np.int64)),
            "position": numpy[2], "has_gauss": numpy[3], "cached_gaussian": numpy[4]},
            "torch": torch.get_rng_state(), "cuda": torch.cuda.get_rng_state_all() if torch.cuda.is_available() else []}


def restore_rng_state(state):
    random.setstate(state["python"])
    numpy = state["numpy"]
    np.random.set_state((numpy["name"], numpy["keys"].cpu().numpy().astype(np.uint32), numpy["position"], numpy["has_gauss"], numpy["cached_gaussian"]))
    torch.set_rng_state(state["torch"].cpu())
    if state["cuda"] and torch.cuda.is_available():
        torch.cuda.set_rng_state_all([item.cpu() for item in state["cuda"]])


class ResumableBatchSampler:
    def __init__(self, size, batch_size, seed):
        if size < 1 or batch_size < 1:
            raise ValueError("Dataset and batch size must be positive")
        self.size, self.batch_size, self.seed, self.cursor = size, batch_size, seed, 0
        self.batches_per_epoch = math.ceil(size / batch_size)

    def __iter__(self):
        epoch, offset = divmod(self.cursor, self.batches_per_epoch)
        order = torch.randperm(self.size, generator=torch.Generator().manual_seed(self.seed + epoch)).tolist()
        for batch in range(offset, self.batches_per_epoch):
            self.cursor += 1
            yield order[batch * self.batch_size:(batch + 1) * self.batch_size]

    def __len__(self):
        return self.batches_per_epoch

    def state_dict(self):
        return {"size": self.size, "batch_size": self.batch_size, "seed": self.seed, "cursor": self.cursor}

    def load_state_dict(self, state):
        if any(state[key] != getattr(self, key) for key in ("size", "batch_size", "seed")) or state["cursor"] < 0:
            raise ValueError("Resume sampler dataset/batch/seed mismatch")
        self.cursor = state["cursor"]


def _autocast(device, precision):
    if precision == "bf16":
        if device.type != "cuda" or not torch.cuda.is_bf16_supported():
            raise ValueError("BF16 requires supported CUDA device")
        return torch.autocast("cuda", dtype=torch.bfloat16)
    if precision != "fp32":
        raise ValueError("Expected precision fp32 or bf16")
    return nullcontext()


def loss_sum(logits, labels):
    if labels.shape != logits.shape[:2]:
        raise ValueError("Label shape must match logits [batch, sequence]")
    count = int((labels != -100).sum().item())
    if not count:
        raise ValueError("Batch contains no supervised tokens")
    total = F.cross_entropy(logits.float().reshape(-1, logits.shape[-1]), labels.reshape(-1), ignore_index=-100, reduction="sum")
    if not torch.isfinite(total):
        raise FloatingPointError("Nonfinite token loss; optimizer update aborted")
    return total, count


def train_one_step(model, batch, optimizer, scaler, phase, *, precision="fp32", grad_clip=1.0):
    if phase not in {"pretrain", "sft"}:
        raise ValueError("Unknown training phase")
    model.train()
    device = next(model.parameters()).device
    batches = batch if isinstance(batch, list) else [batch]
    token_count = sum(int((item["labels"] != -100).sum().item()) for item in batches)
    if not token_count:
        raise ValueError("Batch contains no supervised tokens")
    optimizer.zero_grad(set_to_none=True)
    loss_value = 0.0
    for item in batches:
        item = {key: value.to(device) for key, value in item.items()}
        with _autocast(device, precision):
            total, _ = loss_sum(model(item["input_ids"]), item["labels"])
            loss = total / token_count
        loss_value += float(total.detach()) / token_count
        if scaler is None:
            loss.backward()
        else:
            scaler.scale(loss).backward()
    if scaler is not None:
        scaler.unscale_(optimizer)
    norm = torch.nn.utils.clip_grad_norm_(model.parameters(), grad_clip, error_if_nonfinite=True)
    if scaler is None:
        optimizer.step()
    else:
        scaler.step(optimizer)
        scaler.update()
    if not torch.stack([torch.isfinite(parameter).all() for parameter in model.parameters()]).all():
        raise FloatingPointError("Nonfinite parameters after update; retain last committed checkpoint")
    return {"loss": loss_value, "grad_norm": float(norm.detach()), "valid_tokens": token_count}


def evaluate_tokens(model, loader, *, precision="fp32", max_batches=None):
    rng, was_training = capture_rng_state(), model.training
    device = next(model.parameters()).device
    model.eval()
    total_loss, total_tokens, batches = 0.0, 0, 0
    try:
        with torch.no_grad():
            for index, item in enumerate(loader):
                if max_batches is not None and index >= max_batches:
                    break
                item = {key: value.to(device) for key, value in item.items()}
                with _autocast(device, precision):
                    loss, count = loss_sum(model(item["input_ids"]), item["labels"])
                total_loss += float(loss)
                total_tokens += count
                batches += 1
    finally:
        model.train(was_training)
        restore_rng_state(rng)
    if not total_tokens:
        raise ValueError("Validation has no supervised tokens")
    mean = total_loss / total_tokens
    return {"loss": mean, "perplexity": math.exp(mean) if mean < 700 else None, "valid_tokens": total_tokens, "batches": batches}


def save_checkpoint(path: Path, state: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_suffix(".pt.partial")
    torch.save(state, partial)
    os.replace(partial, path)
    write_manifest(path.with_suffix(".json"), {"format_version": 1, "sha256": sha256_file(path), "bytes": path.stat().st_size,
                   "run_id": state["run_id"], "global_step": state["global_step"], "lineage": state["config"]["lineage"]})


def read_checkpoint(path: Path):
    manifest = json.loads(path.with_suffix(".json").read_text(encoding="utf-8"))
    if path.stat().st_size != manifest["bytes"] or sha256_file(path) != manifest["sha256"]:
        raise ValueError("Checkpoint checksum/byte mismatch")
    return torch.load(path, map_location="cpu", weights_only=True)


def load_checkpoint(path, model, optimizer, scheduler, *, restore_rng=True):
    state = read_checkpoint(Path(path))
    if state["model_config"] != model.config:
        raise ValueError("Checkpoint model configuration mismatch")
    model.load_state_dict(state["model"])
    if optimizer is not None:
        optimizer.load_state_dict(state["optimizer"])
    if scheduler is not None:
        scheduler.load_state_dict(state["scheduler"])
    if restore_rng:
        restore_rng_state(state["rng"])
    return state


def _iterator_without_rng_change(loader):
    rng = capture_rng_state()
    iterator = iter(loader)
    restore_rng_state(rng)
    return iterator


def run_training(config_path: Path, train_loader, validation_loader, run_id: str, *, stop_after=None, resume=None):
    config_path = Path(config_path).resolve()
    root = config_path.parent.parent
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if not re.fullmatch(r"[A-Z0-9_-]{1,80}", run_id):
        raise ValueError("Invalid run ID")
    if train_loader.num_workers != 0 or not isinstance(train_loader.batch_sampler, ResumableBatchSampler):
        raise ValueError("Exact resume requires ResumableBatchSampler and num_workers=0")
    directory = root / "checkpoints" / run_id
    directory.mkdir(parents=True, exist_ok=False)
    summary_path = root / f"reports/training/{run_id}.json"
    metrics_path = root / f"outputs/metrics/{run_id}.jsonl"
    console_path = root / f"logs/training/{run_id}.log"
    console_path.parent.mkdir(parents=True, exist_ok=True)
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    write_manifest(directory / "config.json", config)
    started = time.perf_counter()
    summary = {"run_id": run_id, "status": "running", "started_at_utc": datetime.now(timezone.utc).isoformat(),
               "config": config, "config_sha256": sha256_file(config_path), "resume_parent": str(resume) if resume else None,
               "label_alignment": "already shifted; loss consumes labels directly", "global_step": 0, "last_committed_step": 0}
    try:
        summary["git_commit"] = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True, stderr=subprocess.DEVNULL).strip()
    except subprocess.CalledProcessError:
        summary["git_commit"] = "fixture/no git"
    write_manifest(summary_path, summary)
    def emit(record, *, console=True):
        with metrics_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, allow_nan=False) + "\n")
        if console:
            line = json.dumps(record, allow_nan=False)
            with console_path.open("a", encoding="utf-8") as handle:
                handle.write(line + "\n")
            print(line, flush=True)
    model, optimizer, scheduler, last = None, None, None, directory / "last.pt"
    try:
        seed_everything(config["seed"])
        device = torch.device(config["device"])
        model_config = config.get("model_config") or json.loads((root / config["model_config_path"]).read_text())
        config["model_config"] = model_config
        model = MiniGPT(model_config).to(device)
        estimated_checkpoint_bytes = model.parameter_count() * 12 * 2 + 64 * 1024**2
        if shutil.disk_usage(root).free < config["reserve_free_bytes"] + estimated_checkpoint_bytes:
            raise OSError("Insufficient storage for last/best checkpoints while preserving reserve")
        optimizer = torch.optim.AdamW(model.parameters(), lr=config["learning_rate"], betas=tuple(config["betas"]), weight_decay=config["weight_decay"])
        def rate(step):
            if step < config["warmup_steps"]:
                return (step + 1) / max(1, config["warmup_steps"])
            progress = min(1.0, (step - config["warmup_steps"]) / max(1, config["max_steps"] - config["warmup_steps"]))
            minimum = config["min_learning_rate"] / config["learning_rate"]
            return minimum + (1 - minimum) * (1 + math.cos(math.pi * progress)) / 2
        scheduler = torch.optim.lr_scheduler.LambdaLR(optimizer, rate)
        step, best, total_tokens = 0, float("inf"), 0
        if device.type == "cuda":
            torch.cuda.reset_peak_memory_stats()
        if config.get("initial_checkpoint") and not resume:
            parent = read_checkpoint(root / config["initial_checkpoint"])
            if parent["config"]["lineage"].get("tokenizer_sha256") != config["lineage"].get("tokenizer_sha256"):
                raise ValueError("Initial checkpoint tokenizer lineage mismatch")
            load_checkpoint(root / config["initial_checkpoint"], model, None, None, restore_rng=False)
        if resume:
            state = read_checkpoint(Path(resume))
            if state["config"] != config:
                raise ValueError("Resume immutable training config/data lineage mismatch")
            state = load_checkpoint(resume, model, optimizer, scheduler)
            train_loader.batch_sampler.load_state_dict(state["sampler"])
            step, best, total_tokens = state["global_step"], state["best_validation_loss"], state["total_tokens"]
        summary.update(parameter_count=model.parameter_count(), model_config=model.config,
                       device=str(device), precision=config["precision"], global_step=step,
                       resume_parent_sha256=sha256_file(Path(resume)) if resume else None)
        def snapshot():
            return {"format_version": 1, "run_id": run_id, "model": model.state_dict(), "model_config": model.config,
                    "optimizer": optimizer.state_dict(), "scheduler": scheduler.state_dict(), "global_step": step,
                    "total_tokens": total_tokens, "best_validation_loss": best, "config": config,
                    "sampler": train_loader.batch_sampler.state_dict(), "rng": capture_rng_state()}
        initial_validation = evaluate_tokens(model, validation_loader, precision=config["precision"], max_batches=config["validation_batches"])
        best = min(best, initial_validation["loss"])
        emit({"event": "validation", "step": step, **initial_validation})
        summary["initial_validation"] = initial_validation
        save_checkpoint(last, snapshot())
        summary["last_committed_step"] = step
        # The resumed model is a valid baseline for best in its new run directory.
        save_checkpoint(directory / "best.pt", snapshot())
        iterator = _iterator_without_rng_change(train_loader)
        target_step = min(config["max_steps"], stop_after) if stop_after is not None else config["max_steps"]
        while step < target_step:
            began = time.perf_counter()
            batches = []
            for _ in range(config["gradient_accumulation"]):
                try:
                    batches.append(next(iterator))
                except StopIteration:
                    iterator = _iterator_without_rng_change(train_loader)
                    batches.append(next(iterator))
            used_lr = optimizer.param_groups[0]["lr"]
            report = train_one_step(model, batches, optimizer, None, config["mode"], precision=config["precision"], grad_clip=config["grad_clip"])
            scheduler.step()
            step += 1
            total_tokens += report["valid_tokens"]
            if device.type == "cuda":
                torch.cuda.synchronize()
            seconds = time.perf_counter() - began
            emit({"event": "train", "step": step, **report, "learning_rate": used_lr,
                  "seconds": seconds, "tokens_per_second": report["valid_tokens"] / seconds,
                  "data_cursor": train_loader.batch_sampler.cursor}, console=step % config["log_interval"] == 0 or step == 1)
            summary.update(global_step=step, final_train_loss=report["loss"], total_train_tokens=total_tokens)
            if step % config["validation_interval"] == 0 or step == target_step:
                validation = evaluate_tokens(model, validation_loader, precision=config["precision"], max_batches=config["validation_batches"])
                emit({"event": "validation", "step": step, **validation})
                summary["final_validation"] = validation
                if validation["loss"] < best:
                    best = validation["loss"]
                    save_checkpoint(directory / "best.pt", snapshot())
            if step % config["checkpoint_interval"] == 0 or step == target_step:
                save_checkpoint(last, snapshot())
                summary["last_committed_step"] = step
                write_manifest(summary_path, summary)
        summary.update(status="completed" if step == config["max_steps"] else "stopped_at_limit",
                       best_validation_loss=best, final_checkpoint_sha256=sha256_file(last),
                       best_checkpoint_sha256=sha256_file(directory / "best.pt"))
        return last
    except (Exception, KeyboardInterrupt) as error:
        summary.update(status="interrupted" if isinstance(error, KeyboardInterrupt) else "failed",
                       error_type=type(error).__name__, error=str(error), traceback=traceback.format_exc())
        emit({"event": "failure", "global_step": summary["global_step"], "last_committed_step": summary["last_committed_step"],
              "error_type": type(error).__name__, "error": str(error)})
        raise
    finally:
        summary.update(ended_at_utc=datetime.now(timezone.utc).isoformat(), wall_seconds=time.perf_counter() - started,
                       free_bytes_after=shutil.disk_usage(root).free)
        if model is not None and next(model.parameters()).is_cuda:
            summary.update(gpu=torch.cuda.get_device_name(), peak_allocated_bytes=torch.cuda.max_memory_allocated(), peak_reserved_bytes=torch.cuda.max_memory_reserved())
        write_manifest(summary_path, summary)

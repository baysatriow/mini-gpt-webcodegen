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
import uuid
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
    if labels.shape != logits.shape[:-1]:
        raise ValueError("Label shape must match every logits axis except vocabulary")
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
    weighted = any('loss_weights' in item for item in batches)
    if weighted and (phase != 'sft' or not all('loss_weights' in item for item in batches)):
        raise ValueError('Loss weights require SFT and all accumulation batches')
    denominator = sum(float(item['loss_weights'].sum()) for item in batches) if weighted else token_count
    if denominator <= 0 or not math.isfinite(denominator): raise ValueError('Invalid loss-weight denominator')
    for item in batches:
        item = {key: value.to(device, non_blocking=value.is_pinned()) for key, value in item.items()}
        with _autocast(device, precision):
            if weighted:
                weights, labels = item['loss_weights'], item['labels']
                if (weights.shape != labels.shape or not torch.isfinite(weights).all() or (weights < 0).any()
                        or (weights[labels == -100] != 0).any() or (weights[labels != -100] <= 0).any()):
                    raise ValueError('Invalid weights or prompt/pad mask')
            if getattr(model, 'supervised_only_logits', False):
                active = item['labels'] != -100
                logits = model(item['input_ids'], output_mask=active)
                item['labels'] = item['labels'][active]
                if weighted:
                    item['loss_weights'] = item['loss_weights'][active]
            else:
                logits = model(item['input_ids'])
            if weighted:
                weights, labels = item['loss_weights'], item['labels']
                losses = F.cross_entropy(logits.float().reshape(-1, logits.shape[-1]), labels.reshape(-1), ignore_index=-100, reduction='none')
                total = (losses * weights.float().reshape(-1)).sum()
                if not torch.isfinite(total): raise FloatingPointError('Nonfinite weighted loss')
            else: total, _ = loss_sum(logits, item['labels'])
            loss = total / denominator
        loss_value += float(total.detach()) / denominator
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
                    if getattr(model, 'validation_supervised_only_logits', False):
                        active = item['labels'] != -100
                        loss, count = loss_sum(model(item['input_ids'], output_mask=active), item['labels'][active])
                    else:
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
    path = Path(path)
    if state['config'].get('data_origin') == 'fullpage_curriculum':
        root = path.resolve().parents[2]
        model_bytes = sum(t.numel() * t.element_size() for t in {t.data_ptr(): t for t in state['model'].values()}.values())
        projected = model_bytes * (1 if state.get('weights_only') else 3) + 32 * 1024**2
        if shutil.disk_usage(root).free < state['config']['reserve_free_bytes'] + projected:
            raise OSError('Checkpoint write would breach 15GiB disk reserve')
        phase_dirs = [root/'data/processed/fullpage', root/'assets/fullpage', root/'outputs/fullpage', root/'checkpoints/INIT-2048-001']
        for directory in (root/'checkpoints').iterdir():
            config_path = directory/'config.json'
            if config_path.is_file() and json.loads(config_path.read_text(encoding='utf-8')).get('data_origin') == 'fullpage_curriculum':
                phase_dirs.append(directory)
        current = sum(p.stat().st_size for d in phase_dirs if d.exists() for p in d.rglob('*') if p.is_file())
        if current + projected + 16 * 1024**2 > 1.5 * 1024**3:
            raise OSError('Checkpoint write would exceed fullpage phase artifact budget1.5GiB')
    path.parent.mkdir(parents=True, exist_ok=True)
    versions = path.parent / ".versions"
    versions.mkdir(exist_ok=True)
    previous = None
    if path.exists():
        previous, _ = _checkpoint_payload(path)
    payload = versions / f"{path.stem}-{uuid.uuid4().hex}.pt"
    manifest_path = payload.with_suffix(".json")
    partial = path.with_suffix(".pt.partial")
    try:
        with payload.open("xb") as handle:
            torch.save(state, handle)
            handle.flush()
            os.fsync(handle.fileno())
        write_manifest(manifest_path, {"format_version": 2, "sha256": sha256_file(payload), "bytes": payload.stat().st_size,
                       "run_id": state["run_id"], "global_step": state["global_step"], "lineage": state["config"]["lineage"]})
        pointer = {"format_version": 2, "payload": str(payload.relative_to(path.parent)),
                   "manifest_sha256": sha256_file(manifest_path),
                   "retained_payloads": [state["best_checkpoint"]["payload"]] if state.get("best_checkpoint") else []}
        with partial.open("w", encoding="utf-8") as handle:
            json.dump(pointer, handle)
            handle.flush()
            os.fsync(handle.fileno())
        _checkpoint_payload(partial)
        # The only commit operation. Older pointer/payload remain usable until this succeeds.
        os.replace(partial, path)
    except BaseException:
        for candidate in (partial, payload, manifest_path):
            candidate.unlink(missing_ok=True)
        raise
    # Keep both the current and immediately previous generation; cleanup is best effort.
    keep = {payload.resolve(), previous.resolve() if previous else None}
    for reference_path in path.parent.glob("*.pt"):
        with reference_path.open("rb") as handle:
            is_pointer = handle.read(1) == b"{"
        if is_pointer:
            reference = json.loads(reference_path.read_text(encoding="utf-8"))
            for relative in reference.get("retained_payloads", []):
                pinned = (path.parent / relative).resolve()
                if pinned.is_relative_to(versions.resolve()):
                    keep.add(pinned)
    for candidate in versions.glob(f"{path.stem}-*.pt"):
        if candidate.resolve() not in keep:
            try:
                candidate.unlink()
                candidate.with_suffix(".json").unlink(missing_ok=True)
            except OSError:
                pass


def _checkpoint_payload(path: Path):
    path = Path(path)
    with path.open("rb") as handle:
        pointer_format = handle.read(1) == b"{"
    if pointer_format:
        try:
            pointer = json.loads(path.read_text(encoding="utf-8"))
            payload = (path.parent / pointer["payload"]).resolve()
            if pointer["format_version"] != 2 or not payload.is_relative_to((path.parent / ".versions").resolve()):
                raise ValueError("Checkpoint pointer escapes generation directory")
            manifest_path = payload.with_suffix(".json")
            if sha256_file(manifest_path) != pointer["manifest_sha256"]:
                raise ValueError("Checkpoint manifest checksum mismatch")
        except (json.JSONDecodeError, KeyError) as error:
            raise ValueError("Checkpoint pointer checksum/format mismatch") from error
    else:
        payload, manifest_path = path, path.with_suffix(".json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if payload.stat().st_size != manifest["bytes"] or sha256_file(payload) != manifest["sha256"]:
        raise ValueError("Checkpoint checksum/byte mismatch")
    return payload, manifest


def checkpoint_sha256(path: Path):
    return _checkpoint_payload(Path(path))[1]["sha256"]


def read_checkpoint(path: Path):
    payload, _ = _checkpoint_payload(Path(path))
    return torch.load(payload, map_location="cpu", weights_only=True)


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


def run_training(config_path: Path, train_loader, validation_loader, run_id: str, *, stop_after=None, resume=None, root=None):
    config_path = Path(config_path).resolve()
    root = Path(root).resolve() if root is not None else config_path.parent.parent
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
    monitor = None
    try:
        seed_everything(config["seed"])
        device = torch.device(config["device"])
        model_config = config.get("model_config") or json.loads((root / config["model_config_path"]).read_text())
        config["model_config"] = model_config
        model = MiniGPT(model_config).to(device)
        performance = config.get("performance", {})
        requested_allocator = performance.get("allocator_config")
        if requested_allocator and os.environ.get("PYTORCH_ALLOC_CONF") != requested_allocator:
            raise ValueError("Start a fresh process with the configured allocator before importing torch")
        model.set_attention_backend(performance.get("attention_backend", "manual"))
        model.supervised_only_logits = performance.get("supervised_only_logits", False)
        model.validation_supervised_only_logits = performance.get('validation_supervised_only_logits', False)
        if performance.get("tf32", False):
            if device.type != "cuda":
                raise ValueError("TF32 performance setting requires CUDA")
            torch.backends.cuda.matmul.allow_tf32 = True
            torch.backends.cudnn.allow_tf32 = True
        if performance.get("gpu_telemetry", False):
            from src.training.performance import GpuMonitor
            monitor = GpuMonitor(root / f"outputs/metrics/{run_id}_gpu.jsonl").start()
        estimated_checkpoint_bytes = model.parameter_count() * 12 * 6 + 64 * 1024**2
        if shutil.disk_usage(root).free < config["reserve_free_bytes"] + estimated_checkpoint_bytes:
            raise OSError("Insufficient storage for last/best checkpoints while preserving reserve")
        optimizer_options = {"fused": True} if performance.get("fused_adamw", False) else {}
        optimizer = torch.optim.AdamW(model.parameters(), lr=config["learning_rate"], betas=tuple(config["betas"]), weight_decay=config["weight_decay"], **optimizer_options)
        def rate(step):
            if step < config["warmup_steps"]:
                return (step + 1) / max(1, config["warmup_steps"])
            progress = min(1.0, (step - config["warmup_steps"]) / max(1, config["max_steps"] - config["warmup_steps"]))
            minimum = config["min_learning_rate"] / config["learning_rate"]
            return minimum + (1 - minimum) * (1 + math.cos(math.pi * progress)) / 2
        scheduler = torch.optim.lr_scheduler.LambdaLR(optimizer, rate)
        step, best, total_tokens, best_reference = 0, float("inf"), 0, None
        best_path = directory / "best.pt"
        if device.type == "cuda":
            torch.cuda.reset_peak_memory_stats()
        if config.get("initial_checkpoint") and not resume:
            from src.training.lineage import validate_initial_checkpoint
            initial_path = root / config["initial_checkpoint"]
            if checkpoint_sha256(initial_path) != config["initial_checkpoint_sha256"]:
                raise ValueError("Initial checkpoint checksum changed")
            parent = read_checkpoint(initial_path)
            if config.get('data_origin') == 'fullpage_curriculum':
                from src.fullpage.lineage import validate_fullpage_parent
                validate_fullpage_parent(parent, config, root)
            else:
                validate_initial_checkpoint(parent, config, root)
            load_checkpoint(initial_path, model, None, None, restore_rng=False)
        if resume:
            state = read_checkpoint(Path(resume))
            if state.get('weights_only'):
                raise ValueError('Exact resume requires last checkpoint with optimizer/scheduler state; best is weights-only')
            def verified_resume_config(candidate):
                if ("pretrain_fingerprint" not in candidate["config"]["lineage"]
                        and "pretrain_fingerprint" in config["lineage"]):
                    from src.training.lineage import bind_legacy_checkpoint
                    summary_data = json.loads((root / "data/manifests/pipeline_summary.json").read_text(encoding="utf-8"))
                    return bind_legacy_checkpoint(candidate, root, summary_data)["config"]
                return candidate["config"]
            if verified_resume_config(state) != config:
                raise ValueError("Resume immutable training config/data lineage mismatch")
            state = load_checkpoint(resume, model, optimizer, scheduler)
            train_loader.batch_sampler.load_state_dict(state["sampler"])
            step, best, total_tokens = state["global_step"], state["best_validation_loss"], state["total_tokens"]
            reference = state.get("best_checkpoint")
            parent_best_path = root / reference["path"] if reference else Path(resume).parent / "best.pt"
            if reference and checkpoint_sha256(parent_best_path) != reference["sha256"]:
                raise ValueError("Resume best checkpoint checksum mismatch")
            parent_best = read_checkpoint(parent_best_path)
            if (verified_resume_config(parent_best) != config or parent_best["best_validation_loss"] != best
                    or parent_best["global_step"] > step):
                raise ValueError("Resume best checkpoint state/loss mismatch")
            parent_best["config"] = config
            save_checkpoint(best_path, parent_best)
            best_payload = _checkpoint_payload(best_path)[0]
            best_reference = {"path": str(best_payload.relative_to(root)), "payload": str(best_payload.relative_to(directory)),
                              "sha256": checkpoint_sha256(best_path),
                              "global_step": parent_best["global_step"], "validation_loss": best}
            summary["best_checkpoint_source"] = str(parent_best_path)
        summary.update(parameter_count=model.parameter_count(), model_config=model.config,
                       device=str(device), precision=config["precision"], global_step=step,
                       performance=performance,
                       allocator_config=os.environ.get("PYTORCH_ALLOC_CONF", ""),
                       resume_parent_sha256=checkpoint_sha256(Path(resume)) if resume else None)
        def snapshot(*, include_best=True):
            return {"format_version": 1, "run_id": run_id, "model": model.state_dict(), "model_config": model.config,
                    "optimizer": optimizer.state_dict(), "scheduler": scheduler.state_dict(), "global_step": step,
                    "total_tokens": total_tokens, "best_validation_loss": best, "config": config,
                    "sampler": train_loader.batch_sampler.state_dict(), "rng": capture_rng_state(),
                    "best_checkpoint": best_reference if include_best else None}
        def commit_best(loss):
            nonlocal best, best_reference
            previous_best = best
            best = loss
            try:
                best_state = snapshot(include_best=False)
                if performance.get('best_weights_only', False):
                    best_state.pop('optimizer', None)
                    best_state.pop('scheduler', None)
                    best_state['weights_only'] = True
                save_checkpoint(best_path, best_state)
            except BaseException:
                best = previous_best
                raise
            best_payload = _checkpoint_payload(best_path)[0]
            best_reference = {"path": str(best_payload.relative_to(root)), "payload": str(best_payload.relative_to(directory)),
                              "sha256": checkpoint_sha256(best_path),
                              "global_step": step, "validation_loss": best}
        initial_validation = evaluate_tokens(model, validation_loader, precision=config["precision"], max_batches=config["validation_batches"])
        if best_reference is None or initial_validation["loss"] < best:
            commit_best(initial_validation["loss"])
        emit({"event": "validation", "step": step, **initial_validation})
        summary["initial_validation"] = initial_validation
        save_checkpoint(last, snapshot())
        summary["last_committed_step"] = step
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
            if config.get('data_origin') == 'fullpage_curriculum':
                report['supervised_tokens_after_position_1024'] = sum(int((b['labels'][:,1024:] != -100).sum()) for b in batches)
            scheduler.step()
            step += 1
            total_tokens += report["valid_tokens"]
            if device.type == "cuda":
                torch.cuda.synchronize()
            seconds = time.perf_counter() - began
            emit({"event": "train", "step": step, **report, "learning_rate": used_lr,
                  "time_unix": time.time(),
                  "seconds": seconds, "tokens_per_second": report["valid_tokens"] / seconds,
                  "data_cursor": train_loader.batch_sampler.cursor}, console=step % config["log_interval"] == 0 or step == 1)
            summary.update(global_step=step, final_train_loss=report["loss"], total_train_tokens=total_tokens)
            if step % config["validation_interval"] == 0 or step == target_step:
                validation = evaluate_tokens(model, validation_loader, precision=config["precision"], max_batches=config["validation_batches"])
                emit({"event": "validation", "step": step, **validation})
                summary["final_validation"] = validation
                if validation["loss"] < best:
                    commit_best(validation["loss"])
            if step % config["checkpoint_interval"] == 0 or step == target_step:
                save_checkpoint(last, snapshot())
                summary["last_committed_step"] = step
                write_manifest(summary_path, summary)
        summary.update(status="completed" if step == config["max_steps"] else "stopped_at_limit",
                       best_validation_loss=best, final_checkpoint_sha256=checkpoint_sha256(last),
                       best_checkpoint_sha256=checkpoint_sha256(best_path), best_checkpoint=best_reference)
        return last
    except (Exception, KeyboardInterrupt) as error:
        summary.update(status="interrupted" if isinstance(error, KeyboardInterrupt) else "failed",
                       error_type=type(error).__name__, error=str(error), traceback=traceback.format_exc())
        emit({"event": "failure", "global_step": summary["global_step"], "last_committed_step": summary["last_committed_step"],
              "error_type": type(error).__name__, "error": str(error)})
        raise
    finally:
        if monitor is not None:
            summary["gpu_telemetry"] = monitor.finish()
        summary.update(ended_at_utc=datetime.now(timezone.utc).isoformat(), wall_seconds=time.perf_counter() - started,
                       free_bytes_after=shutil.disk_usage(root).free)
        if model is not None and next(model.parameters()).is_cuda:
            summary.update(gpu=torch.cuda.get_device_name(), peak_allocated_bytes=torch.cuda.max_memory_allocated(), peak_reserved_bytes=torch.cuda.max_memory_reserved())
        write_manifest(summary_path, summary)

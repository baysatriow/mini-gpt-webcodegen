"""Train project Mini GPT from verified data; reserve a separate TRAIN ID for every attempt."""
import argparse
import hashlib
import json
import platform
import re
import subprocess
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import torch
from tokenizers import Tokenizer
from torch.utils.data import DataLoader, Subset

from src.data.dataset import PageSpecDataset, PretrainingBlockDataset
from src.data.integrity import reuse_tokenization, validate_sft_artifacts
from src.data.normalize import read_jsonl
from src.data.pipeline import load_completed_sources
from src.data.sources import sha256_file, write_manifest
from src.data.split import read_group_assignment
from src.training.engine import ResumableBatchSampler, read_checkpoint, run_training, checkpoint_sha256
from src.training.lineage import pretrain_descriptor, sft_descriptor, validate_initial_checkpoint, verify_checkpoint_lineage


def prepare_training_data(root, config, smoke=False):
    summary = json.loads((root / "data/manifests/pipeline_summary.json").read_text())
    if summary.get("status") != "complete":
        raise ValueError("Data pipeline must be complete before training")
    if config["mode"] == "sft" and summary["sft"]["status"] != "complete":
        raise ValueError("SFT requires reviewed production annotations; draft queue is not training data")
    token_config = json.loads((root / "configs/tokenizer.json").read_text())
    reuse_tokenization(root, summary, summary["split"], token_config)
    read_group_assignment(root / "data/processed/pretrain")
    tokenizer_path = root / config["tokenizer"]
    tokenizer = Tokenizer.from_file(str(tokenizer_path))
    if config["mode"] == "pretrain":
        datasets = {name: PretrainingBlockDataset(root / f"data/processed/pretrain/{name}.tokens.bin", config["block_size"], tokenizer.token_to_id("<pad>")) for name in ("train", "validation")}
        inputs = {name: summary["token_caches"][name]["sha256"] for name in datasets}
    elif config["mode"] == "sft":
        source_config = json.loads((root / "configs/dataset.json").read_text())
        paths, _ = load_completed_sources(source_config, root)
        sources = {row["source_row_id"]: row for path in paths for row in read_jsonl(path)}
        validate_sft_artifacts(root, summary["sft"], sources)
        datasets = {name: PageSpecDataset(read_jsonl(root / f"data/processed/sft/{name}.jsonl"), tokenizer, "sft", config["block_size"]) for name in ("train", "validation")}
        inputs = {name: summary["sft"]["split"]["files"][name]["sha256"] for name in datasets}
    else:
        raise ValueError("Unknown training mode")
    validation_count = min(len(datasets["validation"]), config["validation_batches"] * config["batch_size"])
    indices = torch.randperm(len(datasets["validation"]), generator=torch.Generator().manual_seed(config["seed"] + 17)).tolist()[:validation_count]
    if smoke:
        datasets["train"] = Subset(datasets["train"], range(min(32, len(datasets["train"]))))
        indices = indices[:8]
    validation = Subset(datasets["validation"], indices)
    train_loader = DataLoader(datasets["train"], batch_sampler=ResumableBatchSampler(len(datasets["train"]), config["batch_size"], config["seed"]), num_workers=0)
    validation_loader = DataLoader(validation, batch_size=config["batch_size"], num_workers=0)
    lineage = {"tokenizer_sha256": sha256_file(tokenizer_path), "pipeline_summary_sha256": sha256_file(root / "data/manifests/pipeline_summary.json"),
               "data_sha256": inputs, "validation_indices_sha256": hashlib.sha256(json.dumps(indices).encode()).hexdigest(),
               "train_blocks_or_examples": len(datasets["train"]), "validation_blocks_or_examples": len(indices), "smoke": smoke}
    lineage["pretrain_fingerprint"] = pretrain_descriptor(root, summary)
    if config["mode"] == "sft":
        lineage["sft_fingerprint"] = sft_descriptor(summary)
    return train_loader, validation_loader, lineage


def next_run_id():
    numbers = []
    for directory in [ROOT / "checkpoints", ROOT / "reports/training", ROOT / "outputs/metrics"]:
        if directory.exists():
            for path in directory.iterdir():
                found = re.match(r"TRAIN-(\d+)", path.name)
                if found:
                    numbers.append(int(found[1]))
    return f"TRAIN-{max(numbers + [0]) + 1:03d}"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--run-id")
    parser.add_argument("--max-steps", type=int)
    parser.add_argument("--stop-after", type=int)
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--resume", type=Path)
    parser.add_argument("--initialize-from", type=Path)
    args = parser.parse_args(argv)
    run_id = args.run_id or next_run_id()
    if not re.fullmatch(r"TRAIN-\d{3,}", run_id):
        raise ValueError("Expected TRAIN-NNN run ID")
    summary_path = ROOT / f"reports/training/{run_id}.json"
    if summary_path.exists() or (ROOT / f"checkpoints/{run_id}").exists():
        raise ValueError("TRAIN ID already used; each attempt/resume needs a new ID")
    write_manifest(summary_path, {"run_id": run_id, "status": "preflight", "command": subprocess.list2cmdline(sys.argv)})
    try:
        config = json.loads(args.config.read_text(encoding="utf-8"))
        config["source_config_sha256"] = sha256_file(args.config)
        if args.max_steps is not None:
            config["max_steps"] = args.max_steps
        if config["max_steps"] < 1 or (args.stop_after is not None and args.stop_after < 1):
            raise ValueError("Steps must be positive")
        if args.smoke:
            config.update(gradient_accumulation=1, validation_interval=1, checkpoint_interval=1, log_interval=1)
        config["model_config"] = json.loads((ROOT / config["model_config_path"]).read_text())
        if args.initialize_from:
            config["initial_checkpoint"] = str(args.initialize_from.resolve().relative_to(ROOT))
            config["initial_checkpoint_sha256"] = checkpoint_sha256(args.initialize_from)
        if args.resume:
            parent = read_checkpoint(args.resume)
            for key in ("initial_checkpoint", "initial_checkpoint_sha256"):
                if key in parent["config"]:
                    config[key] = parent["config"][key]
        if config["mode"] == "sft" and not (args.initialize_from or args.resume):
            raise ValueError("SFT requires a checkpoint from project pretraining")
        train, validation, config["lineage"] = prepare_training_data(ROOT, config, args.smoke)
        if config["mode"] == "sft":
            summary = json.loads((ROOT / "data/manifests/pipeline_summary.json").read_text(encoding="utf-8"))
            if args.initialize_from:
                parent = read_checkpoint(args.initialize_from)
                validate_initial_checkpoint(parent, config, ROOT, summary)
                config["lineage"]["pretraining_parent"] = {
                    "checkpoint_sha256": checkpoint_sha256(args.initialize_from), "phase": parent["config"]["mode"],
                    "global_step": parent["global_step"], "pretrain_fingerprint": config["lineage"]["pretrain_fingerprint"]}
            elif args.resume:
                verify_checkpoint_lineage(parent, ROOT, summary)
                config["lineage"]["pretraining_parent"] = parent["config"]["lineage"]["pretraining_parent"]
        tokenizer = Tokenizer.from_file(str(ROOT / config["tokenizer"]))
        if tokenizer.get_vocab_size() != config["model_config"]["vocab_size"] or config["block_size"] != config["model_config"]["block_size"]:
            raise ValueError("Model/data tokenizer vocabulary or context mismatch")
        runtime = ROOT / f"configs/.{run_id}.json"
        write_manifest(runtime, config)
        checkpoint = run_training(runtime, train, validation, run_id, stop_after=args.stop_after, resume=args.resume)
        summary = json.loads(summary_path.read_text())
        summary["environment"] = {"python": sys.version, "executable": sys.executable, "platform": platform.platform(),
                                  "torch": torch.__version__, "cuda": torch.version.cuda, "bf16_supported": torch.cuda.is_bf16_supported(),
                                  "gpu": torch.cuda.get_device_name() if torch.cuda.is_available() else None,
                                  "cuda_architectures": torch.cuda.get_arch_list() if torch.cuda.is_available() else []}
        write_manifest(summary_path, summary)
        print(json.dumps({"run_id": run_id, "status": summary["status"], "checkpoint": str(checkpoint.relative_to(ROOT))}), flush=True)
        return 0
    except (Exception, KeyboardInterrupt):
        existing = json.loads(summary_path.read_text())
        if existing["status"] == "preflight":
            existing.update(status="failed_preflight", traceback=traceback.format_exc())
            write_manifest(summary_path, existing)
        raise


if __name__ == "__main__":
    raise SystemExit(main())

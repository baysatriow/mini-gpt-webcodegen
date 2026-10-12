"""Record verified corpus lineage on a new checkpoint copy without changing model tensors."""
import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import torch

from src.data.integrity import reuse_tokenization
from src.data.sources import write_manifest
from src.training.engine import checkpoint_sha256, read_checkpoint, save_checkpoint
from src.training.lineage import bind_legacy_checkpoint


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report-id", required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to((ROOT / "checkpoints").resolve()) or output.exists():
        raise ValueError("Migration needs a new output path under project checkpoints")
    report_path = ROOT / f"reports/training/{args.report_id}_lineage_migration.json"
    if Path(args.report_id).name != args.report_id or report_path.exists():
        raise ValueError("Migration report ID must be a new file name")
    summary = json.loads((ROOT / "data/manifests/pipeline_summary.json").read_text(encoding="utf-8"))
    token_config = json.loads((ROOT / "configs/tokenizer.json").read_text(encoding="utf-8"))
    reuse_tokenization(ROOT, summary, summary["split"], token_config)
    state = read_checkpoint(args.checkpoint)
    if state["config"]["mode"] != "pretrain" or state["global_step"] < 1:
        raise ValueError("Only trained pretraining checkpoints can be bound for SFT")
    reserve = state["config"].get("reserve_free_bytes", 15*1024**3)
    parameter_bytes = sum(value.numel()*value.element_size() for value in state["model"].values())
    if shutil.disk_usage(ROOT).free < reserve + parameter_bytes*4:
        raise OSError("Insufficient storage for lineage migration while preserving reserve")
    bound = bind_legacy_checkpoint(state, ROOT, summary)
    source_sha = checkpoint_sha256(args.checkpoint)
    bound["lineage_migration"] = {"source_checkpoint_sha256": source_sha,
                                  "recorded_pipeline_summary_sha256": state["config"]["lineage"].get("pipeline_summary_sha256")}
    save_checkpoint(output, bound)
    restored = read_checkpoint(output)
    equal = all(torch.equal(value, restored["model"][name]) for name, value in state["model"].items())
    if not equal:
        raise ValueError("Migration changed model tensors")
    report = {"status": "verified_copy", "source_checkpoint": str(args.checkpoint),
              "source_checkpoint_sha256": source_sha, "output_checkpoint": str(output.relative_to(ROOT)),
              "output_checkpoint_sha256": checkpoint_sha256(output), "global_step": state["global_step"],
              "model_tensors_identical": equal, "optimizer_updates": 0,
              "pretrain_fingerprint": restored["config"]["lineage"]["pretrain_fingerprint"],
              "free_bytes_after": shutil.disk_usage(ROOT).free}
    write_manifest(report_path, report)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

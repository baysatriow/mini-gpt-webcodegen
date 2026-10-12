"""Evaluate held-out pretraining token loss and explicitly labeled PageSpec probes."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from torch.utils.data import DataLoader

from src.data.dataset import PretrainingBlockDataset
from src.data.integrity import reuse_tokenization
from src.data.sources import sha256_file, write_manifest
from src.evaluation.generate import evaluate_checkpoint
from src.models.minigpt import MiniGPT
from src.training.engine import evaluate_tokens, load_checkpoint, read_checkpoint, checkpoint_sha256
from src.training.lineage import verify_checkpoint_lineage


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=ROOT / "configs/evaluation.json")
    parser.add_argument("--report-id", required=True)
    args = parser.parse_args()
    config = json.loads(args.config.read_text())
    summary = json.loads((ROOT / "data/manifests/pipeline_summary.json").read_text())
    reuse_tokenization(ROOT, summary, summary["split"], json.loads((ROOT / "configs/tokenizer.json").read_text()))
    state = read_checkpoint(args.checkpoint)
    verify_checkpoint_lineage(state, ROOT, summary)
    partition = config["token_partition"]
    if partition not in {"validation", "test"}:
        raise ValueError("Evaluation partition must be held-out validation/test")
    dataset = PretrainingBlockDataset(ROOT / f"data/processed/pretrain/{partition}.tokens.bin", state["model_config"]["block_size"])
    model = MiniGPT(state["model_config"]).to(config["device"])
    load_checkpoint(args.checkpoint, model, None, None, restore_rng=False)
    tokens = evaluate_tokens(model, DataLoader(dataset, batch_size=config["batch_size"], num_workers=0), precision=config["precision"])
    del model
    generation = evaluate_checkpoint(args.checkpoint, ROOT / config["prompts_path"], ROOT / config["schema_path"], config=config,
                                     root=ROOT, output_path=ROOT / f"outputs/metrics/{args.report_id}_outputs.json")
    report = {"report_id": args.report_id, "checkpoint": str(args.checkpoint), "checkpoint_sha256": checkpoint_sha256(args.checkpoint),
              "checkpoint_step": state["global_step"], "checkpoint_phase": state["config"]["mode"],
              "held_out_token_partition": partition, "held_out_token_metrics": tokens,
              "held_out_data_sha256": summary["token_caches"][partition]["sha256"],
              "generation": generation, "status": "evaluated", "application_gate": "needs-data" if generation["generation_mode"] == "exploratory_unreviewed" else "needs-model-work"}
    write_manifest(ROOT / f"reports/training/{args.report_id}_evaluation.json", report)
    print(json.dumps({"report_id": args.report_id, "token_metrics": tokens, "json_parseable": generation["parseable"],
                      "schema_valid": generation["schema_valid"], "probe_count": generation["count"],
                      "application_gate": report["application_gate"]}, indent=2), flush=True)


if __name__ == "__main__":
    main()

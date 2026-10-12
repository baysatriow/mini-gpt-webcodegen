"""Evaluate SFT target-token loss and generation on verified reviewed pilot test data."""
import argparse
import json
import re
from pathlib import Path

from tokenizers import Tokenizer
from torch.utils.data import DataLoader

from qa.prepare_annotation_review import local_link_findings
from src.data.dataset import PageSpecDataset
from src.data.normalize import read_jsonl
from src.data.sources import sha256_file, write_manifest
from src.evaluation.generate import evaluate_checkpoint
from src.models.minigpt import MiniGPT
from src.training.engine import checkpoint_sha256, evaluate_tokens, load_checkpoint, read_checkpoint
from src.training.lineage import verify_checkpoint_lineage, verify_production_prompts

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=ROOT / "configs/evaluation_sft_pilot.json")
    parser.add_argument("--report-id", required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", args.report_id):
        raise ValueError("Report ID must be a simple identifier")
    report_path = ROOT / f"reports/training/{args.report_id}_sft_evaluation.json"
    output_path = ROOT / f"outputs/metrics/{args.report_id}_sft_outputs.json"
    if report_path.exists() or output_path.exists():
        raise ValueError("Use a new report ID; previous evaluation evidence must be preserved")
    config = json.loads(args.config.read_text(encoding="utf-8"))
    if config["generation_mode"] != "production" or config["prompts_path"] != "data/processed/sft/test.jsonl" or config["schema_path"] != "configs/page_spec.schema.json":
        raise ValueError("Pilot evaluation requires actual SFT test rows and the project schema")
    summary = json.loads((ROOT / "data/manifests/pipeline_summary.json").read_text(encoding="utf-8"))
    state = read_checkpoint(args.checkpoint)
    if state["config"]["lineage"].get("smoke"):
        raise ValueError("Smoke checkpoints are not pilot quality evaluation checkpoints")
    verify_checkpoint_lineage(state, ROOT, summary)
    test_path = ROOT / config["prompts_path"]
    rows = list(read_jsonl(test_path))
    verify_production_prompts(state, rows, ROOT, summary)
    tokenizer = Tokenizer.from_file(str(ROOT / state["config"]["tokenizer"]))
    dataset = PageSpecDataset(rows, tokenizer, "sft", state["model_config"]["block_size"])
    model = MiniGPT(state["model_config"]).to(config["device"])
    load_checkpoint(args.checkpoint, model, None, None, restore_rng=False)
    metrics = evaluate_tokens(model, DataLoader(dataset, batch_size=config["batch_size"], num_workers=0), precision=config["precision"])
    del model
    generation = evaluate_checkpoint(args.checkpoint, test_path, ROOT / config["schema_path"], config=config,
                                     root=ROOT, output_path=output_path)
    parsed_rows = [row for row in generation["records"] if row["parsed_spec"] is not None]
    report = {"report_id": args.report_id, "checkpoint": str(args.checkpoint),
              "checkpoint_sha256": checkpoint_sha256(args.checkpoint), "checkpoint_step": state["global_step"],
              "checkpoint_phase": state["config"]["mode"], "config_sha256": sha256_file(args.config),
              "sft_test_metrics": metrics, "sft_test_sha256": sha256_file(test_path),
              "sft_split_counts": summary["sft"]["split"]["row_counts"],
              "generation": {key: value for key, value in generation.items() if key != "records"},
              "generated_specs_with_resolved_local_links": sum(not local_link_findings(row["parsed_spec"]) for row in parsed_rows),
              "raw_outputs_path": str(output_path.relative_to(ROOT)), "status": "evaluated_pilot",
              "application_gate": "needs-more-data-and-model-work",
              "limits": ["Only four reviewed pilot test examples; no generalization claim",
                         "Loss applies to SFT JSON target tokens, not the pretraining token corpus",
                         "No prompt-fit, visual, accessibility, or browser interaction approval",
                         "No checkpoint selection or hyperparameter tuning from test results"]}
    write_manifest(report_path, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

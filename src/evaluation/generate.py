"""Autoregressive PageSpec probes and separate JSON parsing/schema assessment."""
import json
from pathlib import Path

import torch
from tokenizers import Tokenizer

from src.data.normalize import read_jsonl
from src.data.schema import validate_page_spec
from src.data.sources import sha256_file, write_manifest
from src.models.minigpt import MiniGPT
from src.training.engine import _autocast, load_checkpoint, read_checkpoint, checkpoint_sha256
from src.training.lineage import verify_checkpoint_lineage, verify_production_prompts


def assess_output(raw):
    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, TypeError) as error:
        return {"parse_status": "failed", "parse_error": str(error), "schema_errors": [], "parsed_spec": None}
    errors = validate_page_spec(parsed)
    return {"parse_status": "passed", "parse_error": None, "schema_errors": errors,
            "parsed_spec": parsed if not errors else None}


def evaluate_outputs(rows):
    records = [{**row, **assess_output(row["raw_output"]), "manual_quality_score": None,
                "manual_review": {"prompt_fit": None, "layout": None, "text": None, "interactions": None}} for row in rows]
    parseable = sum(row["parse_status"] == "passed" for row in records)
    valid = sum(row["parse_status"] == "passed" and not row["schema_errors"] for row in records)
    count = len(records)
    return {"count": count, "parseable": parseable, "schema_valid": valid,
            "parseable_rate": parseable / count if count else 0, "schema_valid_rate": valid / count if count else 0,
            "records": records}


def _generate(model, tokenizer, prompt, config):
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("Generation prompt is empty")
    delimiters = ["<pad>", "<unk>", "<bos>", "<eos>", "<prompt>", "<target>"]
    if any(token in prompt for token in delimiters):
        raise ValueError("Reserved delimiter in prompt")
    special = {token: tokenizer.token_to_id(token) for token in delimiters}
    if any(value is None for value in special.values()):
        raise ValueError("Missing project tokenizer delimiters")
    prefix = [special["<bos>"], special["<prompt>"]] + tokenizer.encode(prompt, add_special_tokens=False).ids + [special["<target>"]]
    if len(prefix) >= model.config["block_size"]:
        raise ValueError("Prompt exceeds context; do not truncate input instructions")
    device = next(model.parameters()).device
    ids = torch.tensor([prefix], dtype=torch.long, device=device)
    generated, stopped = [], "token_limit"
    was_training = model.training
    model.eval()
    generator = torch.Generator(device=device).manual_seed(config.get("seed", 42))
    try:
        with torch.no_grad():
            for _ in range(config["max_new_tokens"]):
                if ids.shape[1] >= model.config["block_size"]:
                    stopped = "context_limit"
                    break
                with _autocast(device, config.get("precision", "fp32")):
                    logits = model(ids)[0, -1].float()
                if not torch.isfinite(logits).all():
                    raise FloatingPointError("Nonfinite generation logits")
                temperature = config.get("temperature", 0)
                if temperature == 0:
                    next_id = int(logits.argmax())
                else:
                    if temperature < 0:
                        raise ValueError("Temperature cannot be negative")
                    next_id = int(torch.multinomial(torch.softmax(logits / temperature, dim=-1), 1, generator=generator))
                if next_id == special["<eos>"]:
                    stopped = "eos"
                    break
                generated.append(next_id)
                ids = torch.cat((ids, torch.tensor([[next_id]], device=device)), dim=1)
    finally:
        model.train(was_training)
    return tokenizer.decode(generated, skip_special_tokens=False), stopped, len(generated)


def generate_page_spec(model, tokenizer, prompt, config):
    raw, _, _ = _generate(model, tokenizer, prompt, config)
    return raw, assess_output(raw)["parsed_spec"]


def evaluate_checkpoint(checkpoint, prompts_path, schema_path, *, config, root, output_path):
    checkpoint, root = Path(checkpoint), Path(root)
    state = read_checkpoint(checkpoint)
    summary = json.loads((root / "data/manifests/pipeline_summary.json").read_text(encoding="utf-8"))
    reuse_config = json.loads((root / "configs/tokenizer.json").read_text(encoding="utf-8"))
    from src.data.integrity import reuse_tokenization
    reuse_tokenization(root, summary, summary["split"], reuse_config)
    verify_checkpoint_lineage(state, root, summary)
    prompts = list(read_jsonl(prompts_path))
    if config["generation_mode"] == "production":
        verify_production_prompts(state, prompts, root, summary)
    elif config["generation_mode"] != "exploratory_unreviewed":
        raise ValueError("Unknown PageSpec evaluation mode")
    tokenizer_path = root / state["config"]["tokenizer"]
    if sha256_file(tokenizer_path) != state["config"]["lineage"]["tokenizer_sha256"]:
        raise ValueError("Checkpoint/tokenizer mismatch")
    tokenizer = Tokenizer.from_file(str(tokenizer_path))
    model = MiniGPT(state["model_config"]).to(config["device"])
    load_checkpoint(checkpoint, model, None, None, restore_rng=False)
    rows = []
    for row in prompts:
        raw, stopped, count = _generate(model, tokenizer, row["prompt"], config)
        rows.append({**row, "raw_output": raw, "stop_reason": stopped, "generated_tokens": count,
                     "checkpoint_sha256": checkpoint_sha256(checkpoint), "seed": config["seed"], "decode_config": config})
    report = {**evaluate_outputs(rows), "generation_mode": config["generation_mode"],
              "checkpoint_step": state["global_step"], "checkpoint_sha256": checkpoint_sha256(checkpoint),
              "schema_sha256": sha256_file(Path(schema_path)), "prompt_file_sha256": sha256_file(Path(prompts_path)),
              "browser_evaluated": False, "manual_review_completed": False}
    write_manifest(output_path, report)
    return report

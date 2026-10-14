"""Select a source-bound full-page checkpoint using development evidence only."""
import argparse
import hashlib
import json
import math
import re
from pathlib import Path

from src.data.normalize import read_jsonl
from src.data.sources import sha256_file
from src.fullpage.evaluation import evaluation_source_paths
from src.fullpage.lineage import (
    TRAIN025_PATH,
    TRAIN025_REPORT_PATH,
    validate_source_bound_train025_report,
    verify_source_bound_lineage,
)
from src.fullpage.serialization import canonical
from src.fullpage.source_bound_contracts import CONTRACT_VERSION
from src.fullpage.curriculum import write_json
from src.training.engine import checkpoint_sha256, read_checkpoint


ROOT = Path(__file__).resolve().parents[1]
CONFIG = "configs/fullpage/training-improvement-v5.json"
DATASET = "data/processed/fullpage/v4"
DEVELOPMENT_REQUESTS = DATASET + "/validation.requests.jsonl"
EXPECTED = {
    1800: {"run_id": "TRAIN-025", "status": "stopped_at_limit", "checkpoint": "checkpoints/FULLPAGE-V5/TRAIN-025-step1800.pt",
           "parent": "checkpoints/TRAIN-025/last.pt"},
    3600: {"run_id": "TRAIN-026", "status": "completed", "checkpoint": "checkpoints/FULLPAGE-V5/TRAIN-026-step3600.pt",
           "parent": "checkpoints/TRAIN-026/last.pt"},
}
GATE_MINIMUM = 76
DEVELOPMENT_TOTAL = 80


def _digest(value, label):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
        raise ValueError(label + " must be a lowercase SHA-256 digest")
    return value


def _validate_candidate(candidate):
    if not isinstance(candidate, dict) or candidate.get("step") not in EXPECTED:
        raise ValueError("Candidate step must be exactly 1800 or 3600")
    step = candidate["step"]
    expected = EXPECTED[step]
    generation = candidate.get("generation_report")
    training = candidate.get("training_report")
    if not isinstance(generation, dict) or not isinstance(training, dict):
        raise ValueError("Each candidate requires a generation and training report")
    if (training.get("run_id") != expected["run_id"] or training.get("status") != expected["status"]
            or training.get("global_step") != step):
        raise ValueError("Training report run identity does not match the exact comparison step")
    if (generation.get("scope") != "development" or generation.get("final_used") is not False
            or generation.get("fullpage_contract_version") != CONTRACT_VERSION
            or generation.get("total") != DEVELOPMENT_TOTAL or generation.get("count") != DEVELOPMENT_TOTAL):
        raise ValueError("Generation report is not the complete frozen source-bound development evaluation")
    complete = generation.get("complete")
    required_roles = generation.get("required_roles")
    if (type(complete) is not int or not 0 <= complete <= DEVELOPMENT_TOTAL
            or type(required_roles) is not int or not 0 <= required_roles <= DEVELOPMENT_TOTAL):
        raise ValueError("Generation report page and required-role counts are invalid")
    if type(generation.get("model_gate")) is not bool or type(generation.get("accepted_facts_links_assets_valid")) is not bool:
        raise ValueError("Generation report must contain explicit gate and fact-reference results")
    validation = training.get("final_validation")
    loss = validation.get("loss") if isinstance(validation, dict) else None
    if isinstance(loss, bool) or not isinstance(loss, (int, float)) or not math.isfinite(loss):
        raise ValueError("Training report must contain a finite ordinary development cross entropy")
    _digest(generation.get("requests_sha256"), "Development request identity")
    _digest(generation.get("dataset_manifest_sha256"), "Development dataset manifest identity")
    _digest(generation.get("checkpoint_sha256"), "Development checkpoint identity")
    sources = generation.get("source_sha256")
    if not isinstance(sources, dict) or not sources:
        raise ValueError("Generation source identity is missing")
    for name, digest in sources.items():
        if not isinstance(name, str):
            raise ValueError("Generation source identity has an invalid path")
        _digest(digest, "Generation source identity for " + name)
    return {"step": step, "generation_report": generation, "training_report": training, "validation_loss": float(loss)}


def select_v5_candidate(candidates: list[dict]) -> dict:
    """Rank exactly two frozen development candidates and apply the 76 of 80 gate."""
    if not isinstance(candidates, list) or len(candidates) != 2:
        raise ValueError("Selection requires exactly the step-1800 and step-3600 candidates")
    validated = [_validate_candidate(candidate) for candidate in candidates]
    if {candidate["step"] for candidate in validated} != set(EXPECTED):
        raise ValueError("Selection requires one candidate for each exact comparison step")
    first = validated[0]["generation_report"]
    for candidate in validated[1:]:
        report = candidate["generation_report"]
        if (report["requests_sha256"] != first["requests_sha256"]
                or report["dataset_manifest_sha256"] != first["dataset_manifest_sha256"]
                or report["source_sha256"] != first["source_sha256"]):
            raise ValueError("Development candidates do not share the same request, manifest, and source identities")

    chosen = max(validated, key=lambda item: (item["generation_report"]["complete"], -item["validation_loss"], -item["step"]))
    generation = chosen["generation_report"]
    passed = (generation["complete"] >= GATE_MINIMUM and generation["model_gate"]
              and generation["accepted_facts_links_assets_valid"])
    summaries = []
    for candidate in sorted(validated, key=lambda item: item["step"]):
        report = candidate["generation_report"]
        training = candidate["training_report"]
        summaries.append({
            "step": candidate["step"],
            "run_id": training["run_id"],
            "complete": report["complete"],
            "required_roles": report["required_roles"],
            "development_ce": candidate["validation_loss"],
            "first_attempt_complete": report.get("first_attempt_complete"),
            "after_retry_complete": report.get("after_retry_complete"),
            "model_gate": report["model_gate"],
            "accepted_facts_links_assets_valid": report["accepted_facts_links_assets_valid"],
            "checkpoint_sha256": report["checkpoint_sha256"],
        })
    return {
        "status": "passed" if passed else "below_gate",
        "model_gate_passed": passed,
        "selected": {
            "step": chosen["step"],
            "run_id": chosen["training_report"]["run_id"],
            "complete": generation["complete"],
            "development_ce": chosen["validation_loss"],
            "generation_report": generation,
        },
        "candidates": summaries,
        "request_sha256": first["requests_sha256"],
        "dataset_manifest_sha256": first["dataset_manifest_sha256"],
        "winning_rule": "Most complete pages; ordinary development CE breaks ties; earlier step breaks exact ties.",
        "gate": {"minimum_complete": GATE_MINIMUM, "total": DEVELOPMENT_TOTAL,
                 "requires_model_gate": True, "requires_exact_fact_links_assets": True},
        "final_used": False,
    }


def _inside(root, relative):
    root = Path(root).resolve()
    path = (root / relative).resolve()
    if not path.is_relative_to(root):
        raise ValueError("Selection input or output path escapes the project root: " + str(relative))
    return path


def _load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _verify_snapshot(root, step, generation_report, training_report, config, config_sha256):
    expected = EXPECTED[step]
    path = _inside(root, expected["checkpoint"])
    state = read_checkpoint(path)
    digest = checkpoint_sha256(path)
    if (state.get("run_id") != expected["run_id"] or state.get("global_step") != step
            or state.get("weights_only") is not True or state.get("config") != config
            or state.get("config", {}).get("lineage", {}).get("fullpage_manifest_sha256")
            != config["lineage"]["fullpage_manifest_sha256"]):
        raise ValueError("Snapshot metadata does not match the frozen source-bound comparison step")
    if (state.get("snapshot_parent") != expected["parent"]
            or state.get("snapshot_parent_sha256") != training_report.get("final_checkpoint_sha256")):
        raise ValueError("Snapshot does not descend from the matching completed training checkpoint")
    if (training_report.get("config_sha256") != config_sha256 or training_report.get("config") != config
            or training_report.get("final_checkpoint_sha256") != state.get("snapshot_parent_sha256")):
        raise ValueError("Training report does not match the frozen training config or snapshot parent")
    if generation_report.get("checkpoint_sha256") != digest:
        raise ValueError("Development generation report checkpoint differs from the pinned snapshot")


def _verify_train026_resume_lineage(root, training_report, config, config_sha256):
    if (training_report.get("run_id") != "TRAIN-026" or training_report.get("status") != "completed"
            or training_report.get("global_step") != 3600):
        raise ValueError("TRAIN-026 resume lineage report has the wrong run identity or step")
    parent_path = _inside(root, TRAIN025_PATH)
    recorded_parent = training_report.get("resume_parent")
    if not isinstance(recorded_parent, str) or _inside(root, recorded_parent) != parent_path:
        raise ValueError("TRAIN-026 report does not name the exact TRAIN-025 checkpoint parent")
    parent_digest = checkpoint_sha256(parent_path)
    parent_report = _load_json(_inside(root, TRAIN025_REPORT_PATH))
    validate_source_bound_train025_report(parent_report, config, config_sha256, parent_digest)
    if training_report.get("resume_parent_sha256") != parent_digest:
        raise ValueError("TRAIN-026 report checkpoint hash differs from its TRAIN-025 parent")


def _verify_generation_report(root, report, expected_manifest_sha256, expected_request_sha256, expected_requests_hash,
                              expected_sources, config):
    if (report.get("scope") != "development" or report.get("final_used") is not False
            or report.get("fullpage_contract_version") != CONTRACT_VERSION
            or report.get("dataset_manifest_sha256") != expected_manifest_sha256
            or report.get("request_file") != DEVELOPMENT_REQUESTS
            or report.get("request_file_sha256") != expected_request_sha256
            or report.get("requests_sha256") != expected_requests_hash):
        raise ValueError("Generation report does not match the frozen V4 development request set")
    if report.get("source_sha256") != expected_sources:
        raise ValueError("Generation report source hashes differ from the current evaluation implementation")
    if report.get("config_sha256") not in (None, config.get("config_sha256")):
        raise ValueError("Generation report contains an unexpected config identity")


def build_selection(root, candidates, *, config_path=CONFIG, dataset_dir=DATASET):
    root = Path(root).resolve()
    config_path = _inside(root, config_path)
    config = _load_json(config_path)
    verify_source_bound_lineage(config, root)
    config_sha256 = sha256_file(config_path)
    dataset_path = _inside(root, dataset_dir)
    manifest_path = dataset_path / "manifest.json"
    manifest = _load_json(manifest_path)
    if manifest.get("version") != "fullpage-v4" or manifest.get("human_reviewed") is not False:
        raise ValueError("Development selection requires the frozen synthetic V4 parent")
    manifest_sha256 = sha256_file(manifest_path)
    request_path = _inside(root, DEVELOPMENT_REQUESTS)
    request_info = manifest.get("files", {}).get("validation.requests.jsonl", {})
    request_file_sha256 = sha256_file(request_path)
    if request_file_sha256 != request_info.get("sha256") or request_path.stat().st_size != request_info.get("bytes"):
        raise ValueError("Frozen development request bytes differ from the V4 manifest")
    requests = [row["request"] for row in read_jsonl(request_path)]
    if len(requests) != DEVELOPMENT_TOTAL:
        raise ValueError("Expected exactly 80 frozen development requests")
    requests_sha256 = hashlib.sha256(canonical(requests).encode("utf-8")).hexdigest()
    expected_sources = {path: sha256_file(root / path) for path in evaluation_source_paths(CONTRACT_VERSION)}

    enriched = []
    for candidate in candidates:
        validated = _validate_candidate(candidate)
        report, training = validated["generation_report"], validated["training_report"]
        _verify_generation_report(root, report, manifest_sha256, request_file_sha256, requests_sha256,
                                  expected_sources, config)
        if training.get("status") != EXPECTED[validated["step"]]["status"]:
            raise ValueError("Training report is not at the expected stop/completion boundary")
        _verify_snapshot(root, validated["step"], report, training, config, config_sha256)
        if validated["step"] == 3600:
            _verify_train026_resume_lineage(root, training, config, config_sha256)
        enriched.append(candidate)
    selection = select_v5_candidate(enriched)
    selection["development_request_file"] = DEVELOPMENT_REQUESTS
    selection["development_request_file_sha256"] = request_file_sha256
    selection["development_manifest_sha256"] = manifest_sha256
    selection["training_config_sha256"] = config_sha256
    selection["final_opened"] = False
    selection["selector_sha256"] = sha256_file(Path(__file__))
    selection["candidate_paths"] = {"1800": EXPECTED[1800]["checkpoint"], "3600": EXPECTED[3600]["checkpoint"]}
    return selection


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--step1800-report", required=True)
    parser.add_argument("--step1800-training", required=True)
    parser.add_argument("--step3600-report", required=True)
    parser.add_argument("--step3600-training", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    output = _inside(root, args.output)
    if output.exists():
        raise FileExistsError("Selection report destination must be new")
    candidates = [
        {"step": 1800, "generation_report": _load_json(_inside(root, args.step1800_report)),
         "training_report": _load_json(_inside(root, args.step1800_training))},
        {"step": 3600, "generation_report": _load_json(_inside(root, args.step3600_report)),
         "training_report": _load_json(_inside(root, args.step3600_training))},
    ]
    report = build_selection(root, candidates)
    write_json(output, report)
    print(json.dumps({"status": report["status"], "model_gate_passed": report["model_gate_passed"],
                      "selected_step": report["selected"]["step"], "complete": report["selected"]["complete"],
                      "total": DEVELOPMENT_TOTAL, "final_used": False}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

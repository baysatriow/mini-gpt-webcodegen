"""Validate and rank the frozen v4 candidates on the development suite only."""
import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

from src.training.engine import checkpoint_sha256, read_checkpoint


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/fullpage/training-improvement-v4.json"
DATASET = ROOT / "data/processed/fullpage/v4"
CANDIDATES = (
    ("TRAIN-022", 1800, "checkpoints/FULLPAGE-V4/TRAIN-022-step1800.pt",
     "reports/fullpage/TRAIN-022_DEVELOPMENT_STEP1800.json"),
    ("TRAIN-024", 3600, "checkpoints/FULLPAGE-V4/TRAIN-024-step3600.pt",
     "reports/fullpage/TRAIN-024_DEVELOPMENT_STEP3600.json"),
)
BASELINE_RUN = "TRAIN-019"
MINIMUM_COMPLETE = 76
DEVELOPMENT_TOTAL = 80


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def role_counts(path):
    tasks, roles = Counter(), Counter()
    with Path(path).open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            tasks[row["task"]] += 1
            if row["task"] == "section_content":
                roles[json.loads(row["target"]).get("role")] += 1
    return {"task_counts": dict(tasks), "section_role_rows": dict(sorted(roles.items()))}


def audit_output(output_path, evaluation, checkpoint_digest):
    output = Path(output_path).resolve()
    if not output.is_relative_to(ROOT) or not output.is_dir():
        raise ValueError("Development output must exist inside the project root")
    identity = read_json(output / "identity.json")
    if (identity.get("checkpoint_sha256") != checkpoint_digest
            or identity.get("requests_sha256") != evaluation.get("requests_sha256")
            or identity.get("source_sha256") != evaluation.get("source_sha256")
            or identity.get("count") != DEVELOPMENT_TOTAL):
        raise ValueError("Development output identity differs from its report")

    statuses = Counter()
    error_attempts = Counter()
    error_pages = defaultdict(set)
    failed_request_ids = []
    pages = 0
    for page in sorted(path for path in output.iterdir() if path.is_dir()):
        attempts = sorted(path for path in page.glob("attempt-*") if path.is_dir())
        if not attempts:
            continue
        attempt_dir = attempts[-1]
        result_path = attempt_dir / "result.json"
        if not result_path.is_file():
            raise ValueError("Development page has no terminal result: " + str(page))
        result = read_json(result_path)
        pages += 1
        statuses[result["status"]] += 1
        if result["status"] not in {"accepted", "complete"}:
            failed_request_ids.append(result.get("request_id"))
        for path in attempt_dir.glob("attempt-*.json"):
            attempt = read_json(path)
            for error in attempt.get("errors", []):
                key = (attempt.get("task"), attempt.get("stage"), error)
                error_attempts[key] += 1
                error_pages[key].add(result["request_id"])

    if pages != DEVELOPMENT_TOTAL:
        raise ValueError(f"Expected all {DEVELOPMENT_TOTAL} development pages, found {pages}")
    if statuses.get("accepted", 0) != evaluation.get("complete"):
        raise ValueError("Output accepted count differs from the development report")
    errors = sorted(
        ({"task": key[0], "stage": key[1], "error": key[2],
          "attempts": count, "affected_pages": len(error_pages[key])}
         for key, count in error_attempts.items()),
        key=lambda item: (-item["attempts"], -item["affected_pages"], item["stage"], item["error"]),
    )
    return {
        "pages": pages,
        "status_counts": dict(statuses),
        "failed_request_ids": failed_request_ids,
        "top_errors": errors[:12],
    }


def verify_candidate(run_id, step, checkpoint_relative, evaluation_relative,
                     config, config_digest, manifest, manifest_digest, request_digest):
    summary_path = ROOT / f"reports/training/{run_id}.json"
    summary = read_json(summary_path)
    evaluation_path = ROOT / evaluation_relative
    evaluation = read_json(evaluation_path)
    checkpoint = ROOT / checkpoint_relative
    state = read_checkpoint(checkpoint)
    digest = checkpoint_sha256(checkpoint)

    if state.get("run_id") != run_id or state.get("global_step") != step or not state.get("weights_only"):
        raise ValueError("Candidate snapshot identity or step is invalid: " + run_id)
    if state.get("config") != config or summary.get("config") != config:
        raise ValueError("Candidate training config differs from the frozen v4 config: " + run_id)
    if (summary.get("global_step") != step or summary.get("last_committed_step") != step
            or summary.get("config_sha256") != config_digest):
        raise ValueError("Training summary step/config checksum mismatch: " + run_id)
    if evaluation.get("scope") != "development" or evaluation.get("final_used") is not False:
        raise ValueError("Candidate evaluation is not development-only: " + run_id)
    if (evaluation.get("total") != DEVELOPMENT_TOTAL or evaluation.get("checkpoint_sha256") != digest
            or evaluation.get("request_file_sha256") != request_digest
            or evaluation.get("dataset_manifest_sha256") != manifest_digest):
        raise ValueError("Development report lineage mismatch: " + run_id)
    if evaluation.get("complete") != evaluation.get("required_roles"):
        raise ValueError("Complete-page and required-role totals differ: " + run_id)

    output_path = Path(evaluation["output"])
    if not output_path.is_absolute():
        output_path = ROOT / output_path
    audit = audit_output(output_path, evaluation, digest)
    return {
        "run_id": run_id,
        "step": step,
        "checkpoint": checkpoint_relative,
        "checkpoint_sha256": digest,
        "training_status": summary["status"],
        "development_report": evaluation_relative,
        "development_report_sha256": sha256_file(evaluation_path),
        "development_complete": evaluation["complete"],
        "development_total": evaluation["total"],
        "development_rate": evaluation["complete_rate"],
        "development_ce": summary["final_validation"]["loss"],
        "first_attempt_complete": evaluation.get("first_attempt_complete"),
        "model_gate": evaluation["model_gate"],
        "groups": evaluation["groups"],
        "reported_failure_counts": evaluation.get("failures", {}),
        "page_status_counts": audit["status_counts"],
        "failed_request_ids": audit["failed_request_ids"],
        "top_generation_errors": audit["top_errors"],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="reports/training/FULLPAGE-V4_DEVELOPMENT_SELECTION.json")
    args = parser.parse_args()
    destination = (ROOT / args.output).resolve()
    if not destination.is_relative_to(ROOT) or destination.exists():
        raise FileExistsError("Selection report path must be new and remain inside the project")

    config = read_json(CONFIG)
    manifest_path = DATASET / "manifest.json"
    manifest = read_json(manifest_path)
    v3_manifest = read_json(ROOT / "data/processed/fullpage/v3/manifest.json")
    manifest_digest = sha256_file(manifest_path)
    config_digest = sha256_file(CONFIG)
    if manifest.get("version") != "fullpage-v4" or manifest.get("human_reviewed") is not False:
        raise ValueError("Expected the disclosed synthetic v4 curriculum")
    if config["lineage"]["fullpage_manifest_sha256"] != manifest_digest:
        raise ValueError("Frozen training config does not match the v4 dataset manifest")
    for name, info in manifest["files"].items():
        path = DATASET / name
        if not path.is_file() or path.stat().st_size != info["bytes"] or sha256_file(path) != info["sha256"]:
            raise ValueError("V4 dataset file differs from its manifest: " + name)
    request_digest = manifest["files"]["validation.requests.jsonl"]["sha256"]

    candidates = [
        verify_candidate(run_id, step, checkpoint, evaluation, config, config_digest,
                         manifest, manifest_digest, request_digest)
        for run_id, step, checkpoint, evaluation in CANDIDATES
    ]
    ordered = sorted(candidates, key=lambda item: (
        -item["development_complete"], item["development_ce"], item["step"]))
    passing = [item for item in candidates if item["model_gate"]]

    baseline_summary = read_json(ROOT / f"reports/training/{BASELINE_RUN}.json")
    baseline_evaluation = read_json(ROOT / f"reports/fullpage/{BASELINE_RUN}_DEVELOPMENT.json")
    if (baseline_evaluation.get("scope") != "development"
            or baseline_evaluation.get("final_used") is not False
            or baseline_evaluation.get("request_file_sha256") != request_digest):
        raise ValueError("Historical baseline does not use the unchanged development requests")
    role_summary = {
        "v3": role_counts(ROOT / "data/processed/fullpage/v3/train.jsonl"),
        "v4": role_counts(DATASET / "train.jsonl"),
    }
    failed_run = read_json(ROOT / "reports/training/TRAIN-023.json")
    report = {
        "experiment": "fullpage-process-role-augmentation-v4",
        "dataset": "data/processed/fullpage/v4",
        "dataset_manifest_sha256": manifest_digest,
        "parent_manifest_sha256": manifest.get("parent_manifest_sha256"),
        "training_config": "configs/fullpage/training-improvement-v4.json",
        "training_config_sha256": config_digest,
        "development_request_sha256": request_digest,
        "development_total": DEVELOPMENT_TOTAL,
        "target": {"minimum_complete_pages": MINIMUM_COMPLETE, "pages": DEVELOPMENT_TOTAL, "rate": 0.95},
        "data_change": {
            "kind": manifest.get("overlay", {}).get("kind"),
            "train_rows_v3": v3_manifest["task_counts"]["train"],
            "train_rows_v4": manifest["task_counts"]["train"],
            "added_rows": manifest["task_counts"]["train"] - v3_manifest["task_counts"]["train"],
            "section_process_rows_v3": role_summary["v3"]["section_role_rows"].get("process", 0),
            "section_process_rows_v4": role_summary["v4"]["section_role_rows"].get("process", 0),
            "task_counts_v3": role_summary["v3"]["task_counts"],
            "task_counts_v4": role_summary["v4"]["task_counts"],
            "section_role_rows_v3": role_summary["v3"]["section_role_rows"],
            "section_role_rows_v4": role_summary["v4"]["section_role_rows"],
            "validation_manifest_sha256_v3": v3_manifest["files"]["validation.requests.jsonl"]["sha256"],
            "validation_manifest_sha256_v4": request_digest,
        },
        "training_controls": {
            "plan_batch_probability": config.get("plan_batch_probability"),
            "batch_size": config.get("batch_size"),
            "gradient_accumulation": config.get("gradient_accumulation"),
            "effective_batch_size": config.get("batch_size", 0) * config.get("gradient_accumulation", 0),
            "max_steps": config.get("max_steps"),
            "precision": config.get("precision"),
            "device": config.get("device"),
            "context_tokens": 2048,
            "section_output_tokens": 1536,
            "sampler_and_validation_unchanged": True,
        },
        "historical_baseline": {
            "run_id": BASELINE_RUN,
            "step": baseline_summary["global_step"],
            "complete": baseline_evaluation["complete"],
            "total": baseline_evaluation["total"],
            "complete_rate": baseline_evaluation["complete_rate"],
            "development_ce": baseline_summary["final_validation"]["loss"],
            "model_gate": baseline_evaluation["model_gate"],
            "context_only": True,
        },
        "failed_preflight_run": {
            "run_id": "TRAIN-023",
            "status": failed_run["status"],
            "global_step": failed_run["global_step"],
            "error": failed_run.get("error"),
            "weights_updated": False,
        },
        "candidates": candidates,
        "best_observed_by_complete_pages_then_ce": ordered[0]["run_id"],
        "best_observed_step": ordered[0]["step"],
        "model_gate_passed": bool(passing),
        "promotable_candidate": passing[0]["run_id"] if passing else None,
        "final_targets_read_for_selection": False,
        "final_opened": False,
        "final_used": False,
        "browser_reviewed": False,
        "human_reviewed": False,
        "limits": [
            "Selection compares the two v4 checkpoints on the same 80 development requests.",
            "TRAIN-019 is a historical reference and is not part of the v4 checkpoint ranking.",
            "The synthetic training examples have not been reviewed by a person.",
            "No browser, visual quality, or final benchmark evaluation was performed.",
            "The 95 percent target is not met by either v4 checkpoint.",
            "This experiment cannot establish that process-row augmentation alone caused the observed change.",
        ],
    }
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "report": destination.relative_to(ROOT).as_posix(),
        "historical_baseline": [report["historical_baseline"]["complete"], DEVELOPMENT_TOTAL],
        "candidates": [[item["run_id"], item["development_complete"], item["development_total"],
                        item["development_ce"]] for item in candidates],
        "best_observed": report["best_observed_by_complete_pages_then_ce"],
        "promotable_candidate": report["promotable_candidate"],
        "final_opened": False,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

"""Run the isolated request-extractor candidate using the frozen audited corpus."""

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run_request_extract_training(config_path: Path, *, run_id: str, root: Path, resume: Path | None = None, stop_after: int | None = None):
    from qa.audit_request_extract_v1 import audit_dataset
    from src.fullpage.request_extract_dataset import build_request_extract_loaders
    from src.fullpage.request_extract_lineage import verify_request_extract_sources
    from src.training.engine import run_training

    root = Path(root).resolve()
    config_path = Path(config_path)
    config_path = config_path if config_path.is_absolute() else root / config_path
    config_path = config_path.resolve()
    if not config_path.is_relative_to(root):
        raise ValueError("Extractor training config escapes the project root")
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if not re.fullmatch(r"REQEXT-V1-[A-Z0-9_-]{1,48}", run_id):
        raise ValueError("Extractor run ID must begin with REQEXT-V1-")
    if config.get("max_steps") != 3600:
        raise ValueError("The frozen extractor comparison requires exactly 3,600 global updates")
    if run_id == "REQEXT-V1-1800":
        if resume is not None or stop_after != 1800:
            raise ValueError("The first candidate must start fresh and stop exactly at update 1,800")
    elif run_id == "REQEXT-V1-3600":
        expected_resume = root / "checkpoints/REQEXT-V1-1800/last.pt"
        resume_path = Path(resume) if resume is not None else None
        resume_path = (resume_path if resume_path is not None and resume_path.is_absolute()
                       else root / resume_path if resume_path is not None else None)
        if (resume_path is None or resume_path.resolve() != expected_resume.resolve()
                or stop_after is not None):
            raise ValueError("The second candidate must resume the exact update-1,800 checkpoint through update 3,600")
    else:
        raise ValueError("Frozen extractor candidates use only the 1,800 and 3,600 update stages")
    verify_request_extract_sources(config, root)
    audit = audit_dataset(root, Path(config["dataset_dir"]))
    if audit.get("status") != "passed" or audit.get("final_opened") is not False or audit.get("final_used") is not False:
        raise ValueError("The frozen extractor corpus did not pass its read-only pre-training audit")
    _, _, train_loader, validation_loader = build_request_extract_loaders(root, config, {
        "files": {
            "train.jsonl": {"sha256": config["lineage"]["train_data_sha256"]},
            "development.jsonl": {"sha256": config["lineage"]["development_data_sha256"]},
        },
        "output_budgets": config["generation_contract"]["output_budgets"],
    })
    return run_training(
        config_path, train_loader, validation_loader, run_id,
        resume=(root / resume).resolve() if resume and not Path(resume).is_absolute() else resume,
        root=root,
        stop_after=stop_after,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--config", type=Path, default=Path("configs/fullpage/training-request-extract-v1-r1.json"))
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--resume", type=Path)
    parser.add_argument("--stop-after", type=int)
    args = parser.parse_args()
    os.environ["PYTORCH_ALLOC_CONF"] = "expandable_segments:True"
    checkpoint = run_request_extract_training(
        args.config, run_id=args.run_id, root=args.root,
        resume=args.resume, stop_after=args.stop_after,
    )
    print(json.dumps({"last_checkpoint": str(checkpoint)}))


if __name__ == "__main__":
    main()

"""Create a weights-only request-extractor candidate snapshot."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.data.sources import sha256_file
from src.training.engine import checkpoint_sha256, read_checkpoint, save_checkpoint


ROOT = Path(__file__).resolve().parents[1]


def snapshot(root: Path, source: Path, destination: Path, *, step: int) -> dict:
    root = Path(root).resolve()
    source = source if source.is_absolute() else root / source
    destination = destination if destination.is_absolute() else root / destination
    source, destination = source.resolve(), destination.resolve()
    if not source.is_relative_to(root) or not destination.is_relative_to(root):
        raise ValueError("Extractor snapshot paths must remain inside the project")
    if destination.exists():
        raise FileExistsError("Extractor snapshot destination already exists")
    state = read_checkpoint(source)
    if (state.get("config", {}).get("data_origin") != "request_extract_v1"
            or state.get("weights_only") is True
            or state.get("global_step") != step
            or step not in {1800, 3600}):
        raise ValueError("Snapshot source is not the requested full-state extractor candidate")
    parent_sha = checkpoint_sha256(source)
    snapshot_state = {
        "format_version": state["format_version"],
        "run_id": state["run_id"],
        "model": state["model"],
        "model_config": state["model_config"],
        "global_step": state["global_step"],
        "total_tokens": state["total_tokens"],
        "best_validation_loss": state["best_validation_loss"],
        "config": state["config"],
        "weights_only": True,
        "snapshot_parent": source.relative_to(root).as_posix(),
        "snapshot_parent_sha256": parent_sha,
        "snapshot_parent_file_sha256": sha256_file(source),
        "snapshot_step": step,
    }
    save_checkpoint(destination, snapshot_state)
    digest = checkpoint_sha256(destination)
    return {
        "snapshot": destination.relative_to(root).as_posix(),
        "snapshot_sha256": digest,
        "parent": source.relative_to(root).as_posix(),
        "parent_checkpoint_sha256": parent_sha,
        "parent_file_sha256": sha256_file(source),
        "step": step,
        "run_id": state["run_id"],
        "weights_only": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--step", type=int, required=True)
    args = parser.parse_args()
    print(json.dumps(snapshot(args.root, args.source, args.destination, step=args.step), indent=2))


if __name__ == "__main__":
    main()

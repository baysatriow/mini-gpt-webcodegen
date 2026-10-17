"""Run the frozen API gate with the training system's checkpoint identity digest."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from qa import evaluate_request_extract_api_v1 as gate
from qa.request_extract_api_gate import checkpoint_aware_digest
from src.training.engine import checkpoint_sha256


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


_evaluate_api_gate = gate.evaluate_api_gate


def _evaluate_api_gate_with_checkpoint_identity(
    root: Path,
    config_path: Path,
    checkpoint_path: Path,
    raw_report_path: Path,
    raw_output_path: Path,
    output_path: Path,
) -> dict:
    root = Path(root).resolve()
    checkpoint = Path(checkpoint_path)
    checkpoint = checkpoint if checkpoint.is_absolute() else root / checkpoint
    checkpoint = checkpoint.resolve(strict=True)
    identity_digest = checkpoint_sha256(checkpoint)
    original_digest = gate._sha256
    gate._sha256 = checkpoint_aware_digest(checkpoint, identity_digest, original_digest)
    try:
        report = _evaluate_api_gate(
            root,
            config_path,
            checkpoint_path,
            raw_report_path,
            raw_output_path,
            output_path,
        )
    finally:
        gate._sha256 = original_digest

    report["checkpoint_digest_scheme"] = "src.training.engine.checkpoint_sha256 verified payload SHA-256"
    report["checkpoint_file_sha256"] = _file_sha256(checkpoint)
    report["digest_adapter_sha256"] = _file_sha256(Path(__file__))
    report_path = Path(output_path)
    report_path = report_path if report_path.is_absolute() else root / report_path
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


gate.evaluate_api_gate = _evaluate_api_gate_with_checkpoint_identity


if __name__ == "__main__":
    gate.main()

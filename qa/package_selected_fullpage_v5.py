"""Create a local, provenance-bound bundle for the selected FULLPAGE-V5 model."""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SELECTION_REPORT = ROOT / "reports/training/FULLPAGE-V5_DEVELOPMENT_SELECTION.json"
CHECKPOINT = ROOT / "checkpoints/FULLPAGE-V5/TRAIN-025-step1800.pt"
DEVELOPMENT_BOUNDARY = ROOT / "outputs/fullpage/FULLPAGE-V5/TRAIN-025-step1800"
DESTINATION = ROOT / "training/selected/fullpage-v5"
RESERVE_BYTES = 15 * 1024**3
COPY_SAFETY_BYTES = 32 * 1024**2
PACKAGE_FORMAT_VERSION = 1


README = """# Selected FULLPAGE-V5 runtime bundle

This local bundle records the selected TRAIN-025 checkpoint and its development output. The canonical checkpoint and output remain in their original project paths.

## Selection

- Run: `TRAIN-025`, step `1800`
- Selection report: `reports/training/FULLPAGE-V5_DEVELOPMENT_SELECTION.json`
- Checkpoint pointer: `checkpoints/FULLPAGE-V5/TRAIN-025-step1800.pt`
- Local model pointer: `training/selected/fullpage-v5/model/TRAIN-025-step1800.pt`
- Local development output: `training/selected/fullpage-v5/development-output/`
- Development scope: 80 of 80 accepted requests, `final_used=false`
- Checkpoint SHA-256: `{checkpoint_sha256}`
- Selection report SHA-256: `{selection_report_sha256}`
- Development request-set SHA-256: `{development_request_sha256}`
- Development request-file SHA-256: `{development_request_file_sha256}`
- Development identity SHA-256: `{development_identity_sha256}`
- Browser review: pending
- Human visual review: pending

The selected report and checkpoint identity are bound by the SHA-256 values in `selection.json`. The checkpoint pointer, its `.versions` payload, and payload manifest are copied together so the local pointer remains valid.

## Local-only copies

The `model/` and `development-output/` directories are ignored by Git. Keep them on this machine and do not commit or upload them. The tracked `selection.json` contains provenance metadata, not model weights or generated pages.

Training code remains under `src/`, canonical checkpoints remain under `checkpoints/`, and the canonical development output remains under `outputs/fullpage/FULLPAGE-V5/TRAIN-025-step1800`.

## Evaluation limits

The bundle passed the frozen development selection gate. Browser inspection and human visual review have not been completed. This result does not establish 95 percent visual quality or production readiness.
"""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _resolve_inside(path: Path, boundary: Path, label: str) -> Path:
    resolved = path.resolve(strict=True)
    resolved_boundary = boundary.resolve(strict=True)
    _require(
        resolved.is_relative_to(resolved_boundary),
        f"{label} escapes its approved directory",
    )
    return resolved


def _development_files(directory: Path) -> tuple[list[Path], int]:
    files: list[Path] = []
    total_bytes = 0
    for candidate in directory.rglob("*"):
        _require(not candidate.is_symlink(), f"Development output contains a symlink: {candidate}")
        if not candidate.is_file():
            continue
        resolved = _resolve_inside(candidate, directory, "Development output file")
        files.append(resolved)
        total_bytes += resolved.stat().st_size
    _require(files, "Development output is empty")
    return files, total_bytes


def _checkpoint_pointer_paths(pointer_path: Path) -> tuple[Path, Path]:
    pointer = _read_json(pointer_path)
    _require(pointer.get("format_version") == 2, "Unsupported checkpoint pointer format")
    relative = str(pointer.get("payload", "")).replace("\\", "/")
    _require(relative and not relative.startswith("/"), "Checkpoint payload path must be relative")
    payload = _resolve_inside(
        pointer_path.parent.joinpath(*relative.split("/")),
        pointer_path.parent / ".versions",
        "Checkpoint payload",
    )
    manifest = _resolve_inside(payload.with_suffix(".json"), pointer_path.parent / ".versions", "Checkpoint manifest")
    return payload, manifest


def _validate_selection() -> tuple[dict, dict, Path, dict, str, str]:
    selection = _read_json(SELECTION_REPORT)
    selected = selection.get("selected") or {}
    generation = selected.get("generation_report") or {}

    _require(selection.get("status") == "passed", "Selection report did not pass")
    _require(selection.get("model_gate_passed") is True, "Selection model gate did not pass")
    _require(selection.get("final_used") is False, "Selection report says final data was used")
    _require(selection.get("final_opened") is False, "Selection report says final data was opened")
    _require(selected.get("run_id") == "TRAIN-025", "Selected run is not TRAIN-025")
    _require(selected.get("step") == 1800, "Selected checkpoint is not step 1800")
    _require(selected.get("complete") == 80, "Selection did not accept 80 development requests")
    _require(generation.get("scope") == "development", "Generation report is not development-only")
    _require(generation.get("complete") == 80 and generation.get("total") == 80, "Generation report is not 80/80")
    _require(generation.get("model_gate") is True, "Generation report model gate did not pass")
    _require(generation.get("accepted_facts_links_assets_valid") is True, "Accepted output checks did not pass")
    _require(generation.get("final_used") is False, "Generation report says final data was used")
    _require(generation.get("browser_status") == "pending", "Browser review status is not pending")
    _require(generation.get("human_review_status") == "pending", "Human review status is not pending")
    results = generation.get("results") or []
    _require(len(results) == 80 and all(row.get("status") == "accepted" for row in results), "Generation report has non-accepted development rows")

    candidates = selection.get("candidates") or []
    candidate = next(
        (row for row in candidates if row.get("run_id") == "TRAIN-025" and row.get("step") == 1800),
        None,
    )
    _require(candidate is not None, "Selection report has no TRAIN-025 step 1800 candidate")
    checkpoint_digest = generation.get("checkpoint_sha256")
    _require(checkpoint_digest == candidate.get("checkpoint_sha256"), "Selection checkpoint digests disagree")

    output_value = generation.get("output")
    _require(isinstance(output_value, str) and output_value, "Generation report has no output path")
    output_candidate = Path(output_value)
    if not output_candidate.is_absolute():
        output_candidate = ROOT / output_candidate
    output = _resolve_inside(output_candidate, DEVELOPMENT_BOUNDARY, "Development output")
    _require(output == DEVELOPMENT_BOUNDARY.resolve(strict=True), "Generation output differs from the frozen selected output")

    return selection, generation, output, candidate, checkpoint_digest, str(generation.get("requests_sha256", ""))


def _write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def package_selected_fullpage_v5() -> dict:
    _require(not DESTINATION.exists(), f"Refusing to overwrite existing package: {DESTINATION}")
    _require(CHECKPOINT.is_file(), f"Selected checkpoint pointer is missing: {CHECKPOINT}")

    selection, generation, development_output, candidate, expected_digest, request_digest = _validate_selection()
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from src.training.engine import checkpoint_sha256, read_checkpoint

    checkpoint_state = read_checkpoint(CHECKPOINT)
    source_digest = checkpoint_sha256(CHECKPOINT)
    _require(source_digest == expected_digest, "Selected checkpoint digest does not match the selection report")
    _require(checkpoint_state.get("run_id") == "TRAIN-025", "Checkpoint run lineage does not match selection")
    _require(checkpoint_state.get("global_step") == 1800, "Checkpoint step lineage does not match selection")

    payload, manifest = _checkpoint_pointer_paths(CHECKPOINT)
    identity_path = _resolve_inside(development_output / "identity.json", development_output, "Development identity")
    identity = _read_json(identity_path)
    _require(identity.get("checkpoint_sha256") == source_digest, "Development identity checkpoint digest mismatch")
    _require(request_digest and identity.get("requests_sha256") == request_digest, "Development request-set digest mismatch")
    _require(identity.get("count") == 80, "Development identity count is not 80")
    _require(identity.get("source_sha256") == generation.get("source_sha256"), "Development source digests disagree")

    development_files, development_bytes = _development_files(development_output)
    report_digest = _sha256_file(SELECTION_REPORT)
    identity_digest = _sha256_file(identity_path)
    request_file_digest = selection.get("development_request_file_sha256")
    _require(request_file_digest == generation.get("request_file_sha256"), "Development request file digests disagree")

    copied_bytes = CHECKPOINT.stat().st_size + payload.stat().st_size + manifest.stat().st_size + development_bytes
    minimum_free = RESERVE_BYTES + copied_bytes + COPY_SAFETY_BYTES
    before_free = shutil.disk_usage(ROOT).free
    _require(
        before_free >= minimum_free,
        f"Insufficient free space: need reserve plus {copied_bytes + COPY_SAFETY_BYTES} bytes; have {before_free}",
    )

    DESTINATION.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=".fullpage-v5.tmp-", dir=DESTINATION.parent))
    try:
        model_root = temporary / "model"
        model_root.mkdir()
        pointer_target = model_root / CHECKPOINT.name
        shutil.copy2(CHECKPOINT, pointer_target)

        checkpoint_relative = Path(".versions") / payload.relative_to(CHECKPOINT.parent / ".versions")
        payload_target = model_root / checkpoint_relative
        manifest_target = payload_target.with_suffix(".json")
        payload_target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(payload, payload_target)
        shutil.copy2(manifest, manifest_target)
        shutil.copytree(development_output, temporary / "development-output", copy_function=shutil.copy2)

        copied_digest = checkpoint_sha256(pointer_target)
        copied_state = read_checkpoint(pointer_target)
        _require(copied_digest == source_digest, "Copied checkpoint pointer or payload digest mismatch")
        _require(copied_state.get("run_id") == "TRAIN-025" and copied_state.get("global_step") == 1800, "Copied checkpoint lineage mismatch")
        _require(_sha256_file(manifest_target) == json.loads(pointer_target.read_text(encoding="utf-8"))["manifest_sha256"], "Copied checkpoint manifest digest mismatch")

        output_relative_path = development_output.relative_to(ROOT).as_posix()
        selection_manifest = {
            "package_format_version": PACKAGE_FORMAT_VERSION,
            "selected_run_id": "TRAIN-025",
            "selected_step": 1800,
            "checkpoint_sha256": source_digest,
            "selection_report_path": SELECTION_REPORT.relative_to(ROOT).as_posix(),
            "selection_report_sha256": report_digest,
            "development_request_sha256": request_digest,
            "development_request_file_sha256": request_file_digest,
            "development_output_relative_path": output_relative_path,
            "development_identity_sha256": identity_digest,
            "development_count": 80,
            "development_final_used": False,
            "final_used": False,
            "browser_status": "pending",
            "human_review_status": "pending",
        }
        _write_json(temporary / "selection.json", selection_manifest)
        (temporary / "README.md").write_text(README.format(**selection_manifest), encoding="utf-8")

        _require(checkpoint_sha256(pointer_target) == source_digest, "Final package checkpoint verification failed")
        _require(_sha256_file(temporary / "development-output" / "identity.json") == identity_digest, "Copied development identity digest mismatch")
        _require(shutil.disk_usage(ROOT).free >= RESERVE_BYTES, "Package copy would breach the 15 GiB free-space reserve")
        temporary.rename(DESTINATION)
    except BaseException:
        if temporary.exists():
            shutil.rmtree(temporary)
        raise

    return {
        "package": DESTINATION.relative_to(ROOT).as_posix(),
        "selected_run_id": "TRAIN-025",
        "selected_step": 1800,
        "checkpoint_sha256": source_digest,
        "selection_report_sha256": report_digest,
        "development_identity_sha256": identity_digest,
        "development_file_count": len(development_files),
        "development_bytes": development_bytes,
        "copied_bytes": copied_bytes,
        "free_bytes_before": before_free,
        "free_bytes_after": shutil.disk_usage(ROOT).free,
        "final_used": False,
        "browser_status": "pending",
        "human_review_status": "pending",
    }


if __name__ == "__main__":
    print(json.dumps(package_selected_fullpage_v5(), ensure_ascii=False, indent=2))

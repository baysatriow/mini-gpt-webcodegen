"""Digest adapter for frozen request-extractor API gate reports."""

from __future__ import annotations

from pathlib import Path
from typing import Callable


def checkpoint_aware_digest(
    checkpoint_path: Path,
    checkpoint_digest: str,
    file_digest: Callable[[Path], str],
) -> Callable[[Path], str]:
    """Use the verified payload digest for the checkpoint pointer and file hashes elsewhere."""
    selected_checkpoint = Path(checkpoint_path).resolve()

    def digest(path: Path) -> str:
        candidate = Path(path)
        if candidate.resolve() == selected_checkpoint:
            return checkpoint_digest
        return file_digest(candidate)

    return digest

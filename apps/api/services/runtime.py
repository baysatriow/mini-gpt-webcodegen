"""Process-local dependency holder with lazy model construction."""

from __future__ import annotations

import hashlib
import json
import sys
import threading
from pathlib import Path
from typing import Any

from tokenizers import Tokenizer

from apps.api.settings import APISettings, load_settings


class Runtime:
    def __init__(self, settings: APISettings | None = None) -> None:
        self.settings = settings or load_settings()
        self._tokenizer: Tokenizer | None = None
        self._intake_catalog: dict[str, Any] | None = None
        self._generator: Any | None = None
        self._lock = threading.RLock()
        self.generation_lock = threading.Lock()

    @property
    def project_root(self) -> Path:
        return self.settings.project_root

    @property
    def model_loaded(self) -> bool:
        return self._generator is not None

    def ensure_project_importable(self) -> None:
        root = str(self.project_root)
        if root not in sys.path:
            sys.path.insert(0, root)

    def get_tokenizer(self) -> Tokenizer:
        with self._lock:
            if self._tokenizer is None:
                tokenizer_path = self.project_root / "data/tokenizer/tokenizer.json"
                if not tokenizer_path.is_file():
                    raise FileNotFoundError("Project tokenizer is missing")
                self._tokenizer = Tokenizer.from_file(str(tokenizer_path))
            return self._tokenizer

    def get_intake_catalog(self) -> dict[str, Any]:
        with self._lock:
            if self._intake_catalog is None:
                self.ensure_project_importable()
                from src.fullpage.intake import load_intake_catalog

                self._intake_catalog = load_intake_catalog(self.project_root)
            return self._intake_catalog

    def get_generator(self) -> Any:
        """Verify the selected bundle and construct its generator on demand only."""
        with self._lock:
            if self._generator is not None:
                return self._generator

            bundle_root = self.project_root / "training/selected/fullpage-v5"
            selection_path = bundle_root / "selection.json"
            if not selection_path.is_file():
                raise FileNotFoundError("Selected runtime manifest is missing")
            selection = json.loads(selection_path.read_text(encoding="utf-8"))
            if (
                selection.get("selected_run_id") != "TRAIN-025"
                or selection.get("selected_step") != 1800
                or selection.get("final_used") is not False
                or selection.get("development_final_used") is not False
                or selection.get("development_count") != 80
            ):
                raise ValueError("Selected runtime manifest does not match the approved development candidate")

            expected_checkpoint = (
                bundle_root / "model/TRAIN-025-step1800.pt"
            ).resolve(strict=True)
            checkpoint_path = self.settings.checkpoint_path.resolve(strict=True)
            if checkpoint_path != expected_checkpoint:
                raise ValueError("Configured checkpoint is not the selected local runtime bundle")

            report_relative = Path(selection.get("selection_report_path", ""))
            if not selection.get("selection_report_path") or report_relative.is_absolute():
                raise ValueError("Selected runtime report path is invalid")
            report_path = (self.project_root / report_relative).resolve(strict=True)
            if not report_path.is_relative_to(self.project_root.resolve(strict=True)):
                raise ValueError("Selected runtime report path escapes the project")
            report_hash = hashlib.sha256(report_path.read_bytes()).hexdigest()
            if report_hash != selection.get("selection_report_sha256"):
                raise ValueError("Selected runtime report digest mismatch")

            self.ensure_project_importable()
            from src.training.engine import checkpoint_sha256

            actual_digest = checkpoint_sha256(checkpoint_path)
            if actual_digest != selection.get("checkpoint_sha256"):
                raise ValueError("Selected runtime checkpoint digest mismatch")

            from src.fullpage.generation import FullPageGenerator

            self._generator = FullPageGenerator(checkpoint_path, self.project_root)
            return self._generator


_DEFAULT_RUNTIME: Runtime | None = None
_DEFAULT_RUNTIME_LOCK = threading.Lock()


def get_runtime() -> Runtime:
    global _DEFAULT_RUNTIME
    with _DEFAULT_RUNTIME_LOCK:
        if _DEFAULT_RUNTIME is None:
            _DEFAULT_RUNTIME = Runtime()
        return _DEFAULT_RUNTIME

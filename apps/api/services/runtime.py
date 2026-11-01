"""Process-local dependency holder with lazy model construction."""

from __future__ import annotations

import hashlib
import base64
import gc
import hmac
import json
import secrets
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
        self._extractor: Any | None = None
        self._lock = threading.RLock()
        self.inference_lock = threading.Lock()
        self.generation_lock = threading.Lock()
        self._intake_token_secret = secrets.token_bytes(32)

    @property
    def project_root(self) -> Path:
        return self.settings.project_root

    @property
    def model_loaded(self) -> bool:
        return self._generator is not None

    @property
    def generator_loaded(self) -> bool:
        return self._generator is not None

    @property
    def extractor_loaded(self) -> bool:
        return self._extractor is not None

    @property
    def extractor_available(self) -> bool:
        return (self.project_root / "training/selected/request-extract-v1/selection.json").is_file()

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

            if self._extractor is not None:
                self._extractor = None
                self._release_model_memory()

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

    def get_extractor(self) -> Any:
        """Load the development-gated extractor only while it owns inference memory."""
        with self._lock:
            if self._extractor is not None:
                return self._extractor

            selection_path = self.project_root / "training/selected/request-extract-v1/selection.json"
            if not selection_path.is_file():
                raise FileNotFoundError("No passing request extractor selection is available")
            selection = json.loads(selection_path.read_text(encoding="utf-8"))
            step = selection.get("selected_step")
            relative = selection.get("selected_checkpoint_path")
            if (
                selection.get("status") != "passed"
                or selection.get("automatic_extraction_promoted") is not True
                or selection.get("final_opened") is not False
                or selection.get("final_used") is not False
                or step not in {1800, 3600}
                or selection.get("selected_run_id") != f"REQEXT-V1-{step}"
                or not isinstance(relative, str)
            ):
                raise ValueError("Request extractor selection has not passed the sealed development gate")
            relative_path = Path(relative)
            if relative_path.is_absolute() or ".." in relative_path.parts:
                raise ValueError("Request extractor checkpoint path is invalid")
            checkpoint_path = (self.project_root / relative_path).resolve(strict=True)
            if not checkpoint_path.is_relative_to(self.project_root.resolve(strict=True)):
                raise ValueError("Request extractor checkpoint path escapes the project")

            if self._generator is not None:
                self._generator = None
                self._release_model_memory()

            self.ensure_project_importable()
            from src.fullpage.request_extract_model import RequestExtractor

            self._extractor = RequestExtractor(
                checkpoint_path,
                self.project_root,
                config_path=self.project_root / "configs/fullpage/training-request-extract-v1-r1.json",
            )
            return self._extractor

    def issue_intake_token(self, prompt: str, capability_assessments: list[dict[str, Any]]) -> str:
        payload = json.dumps(
            {
                "version": 1,
                "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
                "capability_assessments": capability_assessments,
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        encoded = base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")
        signature = hmac.new(self._intake_token_secret, payload, hashlib.sha256).digest()
        signed = base64.urlsafe_b64encode(signature).decode("ascii").rstrip("=")
        return encoded + "." + signed

    def verify_intake_token(self, prompt: str, token: str) -> list[dict[str, Any]] | None:
        if not isinstance(token, str) or len(token) > 24000 or token.count(".") != 1:
            return None
        encoded, signed = token.split(".", 1)
        try:
            payload = base64.b64decode(encoded + "=" * (-len(encoded) % 4), altchars=b"-_", validate=True)
            signature = base64.b64decode(signed + "=" * (-len(signed) % 4), altchars=b"-_", validate=True)
            expected = hmac.new(self._intake_token_secret, payload, hashlib.sha256).digest()
            value = json.loads(payload.decode("utf-8"))
        except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
            return None
        if not hmac.compare_digest(signature, expected):
            return None
        if (
            not isinstance(value, dict)
            or value.get("version") != 1
            or value.get("prompt_sha256") != hashlib.sha256(prompt.encode("utf-8")).hexdigest()
            or not isinstance(value.get("capability_assessments"), list)
        ):
            return None
        return value["capability_assessments"]

    @staticmethod
    def _release_model_memory() -> None:
        gc.collect()
        try:
            import torch

            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except ImportError:
            pass


_DEFAULT_RUNTIME: Runtime | None = None
_DEFAULT_RUNTIME_LOCK = threading.Lock()


def get_runtime() -> Runtime:
    global _DEFAULT_RUNTIME
    with _DEFAULT_RUNTIME_LOCK:
        if _DEFAULT_RUNTIME is None:
            _DEFAULT_RUNTIME = Runtime()
        return _DEFAULT_RUNTIME

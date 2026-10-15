"""Local-only API settings with loopback and CORS allowlists."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


DEFAULT_PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CHECKPOINT = Path("training/selected/fullpage-v5/model/TRAIN-025-step1800.pt")
DEFAULT_GENERATION_OUTPUT_DIR = Path("outputs/webapp/generations")
DEFAULT_ALLOWED_ORIGINS = (
    "http://localhost:3000",
    "http://127.0.0.1:3000",
)
ALLOWED_LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}


def _resolve_path(raw_value: str | None, *, root: Path, default: Path) -> Path:
    value = Path(raw_value).expanduser() if raw_value else default
    if not value.is_absolute():
        value = root / value
    return value.resolve()


@dataclass(frozen=True)
class APISettings:
    project_root: Path
    checkpoint_path: Path
    generation_output_dir: Path
    allowed_origins: tuple[str, ...]
    host: str
    port: int


def load_settings(environ: dict[str, str] | None = None) -> APISettings:
    env = os.environ if environ is None else environ
    root_value = env.get("PROJECT_ROOT")
    root = Path(root_value).expanduser() if root_value else DEFAULT_PROJECT_ROOT
    if not root.is_absolute():
        root = DEFAULT_PROJECT_ROOT / root
    root = root.resolve()

    host = env.get("API_HOST", "127.0.0.1").strip()
    if host not in ALLOWED_LOOPBACK_HOSTS:
        raise ValueError("API_HOST must be a loopback address")
    try:
        port = int(env.get("API_PORT", "8000"))
    except ValueError as error:
        raise ValueError("API_PORT must be an integer") from error
    if not 1 <= port <= 65535:
        raise ValueError("API_PORT must be between 1 and 65535")

    origins_value = env.get("API_ALLOWED_ORIGINS")
    if origins_value is None:
        origins = DEFAULT_ALLOWED_ORIGINS
    else:
        origins = tuple(dict.fromkeys(item.strip() for item in origins_value.split(",") if item.strip()))
    if not origins or any(origin not in DEFAULT_ALLOWED_ORIGINS for origin in origins):
        raise ValueError("API_ALLOWED_ORIGINS may contain only the configured local web origins")

    return APISettings(
        project_root=root,
        checkpoint_path=_resolve_path(env.get("CHECKPOINT_PATH"), root=root, default=DEFAULT_CHECKPOINT),
        generation_output_dir=_resolve_path(
            env.get("GENERATION_OUTPUT_DIR"), root=root, default=DEFAULT_GENERATION_OUTPUT_DIR
        ),
        allowed_origins=origins,
        host=host,
        port=port,
    )

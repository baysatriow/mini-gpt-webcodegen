"""Safe access to accepted local generations and their renderer artifacts."""

from __future__ import annotations

import hashlib
import json
import re
import uuid
import zipfile
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import BinaryIO

from apps.api.schemas import GenerationSummary


class ArtifactNotFoundError(LookupError):
    """A generation or an accepted artifact is unavailable."""


class ArtifactIntegrityError(ArtifactNotFoundError):
    """A local artifact no longer matches its accepted generation record."""


_UUID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_MAX_JSON_BYTES = 8 * 1024 * 1024
_SOURCE_NAMES = ("index.html", "styles.css", "app.js")
_SOURCE_CONTENT_TYPES = {
    "index.html": "text/html; charset=utf-8",
    "styles.css": "text/css; charset=utf-8",
    "app.js": "application/javascript; charset=utf-8",
}
_ZIP_FIXED_FILES = (*_SOURCE_NAMES, "page_spec.json", "asset_attribution.json")
_SAFE_STATUS_MESSAGES = {
    "completed": "Halaman berhasil dibuat dan siap ditinjau.",
    "generation_failed": "Halaman belum berhasil dibuat. Periksa request lalu coba kembali.",
    "input_too_long": "Request melebihi batas konteks. Ringkas prompt atau fakta secara manual.",
}


def new_generation_id() -> str:
    """Return an opaque, server-created UUID for one local generation."""
    return str(uuid.uuid4())


class ArtifactStore:
    """Resolve generation artifacts under fixed local and trusted asset roots."""

    def __init__(self, output_root: Path, project_root: Path) -> None:
        self.output_root = Path(output_root).expanduser()
        self.project_root = Path(project_root).expanduser()

    @staticmethod
    def _validate_generation_id(generation_id: str) -> str:
        if not isinstance(generation_id, str) or not _UUID_PATTERN.fullmatch(generation_id):
            raise ArtifactNotFoundError("Generation not found")
        try:
            if str(uuid.UUID(generation_id)) != generation_id:
                raise ArtifactNotFoundError("Generation not found")
        except ValueError as error:
            raise ArtifactNotFoundError("Generation not found") from error
        return generation_id

    def generation_dir(self, generation_id: str) -> Path:
        identifier = self._validate_generation_id(generation_id)
        root = self.output_root.resolve(strict=False)
        candidate = root / identifier
        try:
            if candidate.is_symlink():
                raise ArtifactNotFoundError("Generation not found")
            resolved = candidate.resolve(strict=True)
        except (OSError, RuntimeError) as error:
            raise ArtifactNotFoundError("Generation not found") from error
        if not resolved.is_dir() or resolved.parent != root or resolved.name != identifier:
            raise ArtifactNotFoundError("Generation not found")
        return resolved

    def _checked_generation_dir(self, generation_dir: Path) -> Path:
        candidate = Path(generation_dir)
        try:
            resolved = candidate.resolve(strict=True)
            root = self.output_root.resolve(strict=True)
        except (OSError, RuntimeError) as error:
            raise ArtifactNotFoundError("Generation not found") from error
        self._validate_generation_id(resolved.name)
        if candidate.is_symlink() or not resolved.is_dir() or resolved.parent != root:
            raise ArtifactNotFoundError("Generation not found")
        return resolved

    @staticmethod
    def _read_json_file(path: Path) -> dict:
        try:
            if path.is_symlink() or not path.is_file():
                raise ArtifactNotFoundError("Generation not found")
            if path.stat().st_size > _MAX_JSON_BYTES:
                raise ArtifactIntegrityError("Generation record is too large")
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            raise ArtifactIntegrityError("Generation record is invalid") from error
        if not isinstance(value, dict):
            raise ArtifactIntegrityError("Generation record is invalid")
        return value

    def _result(self, generation_dir: Path) -> tuple[Path, dict]:
        directory = self._checked_generation_dir(generation_dir)
        return directory, self._read_json_file(directory / "result.json")

    @staticmethod
    def _export_files(result: dict) -> dict[str, str]:
        export = result.get("export")
        files = export.get("files") if isinstance(export, dict) else None
        if not isinstance(files, dict):
            raise ArtifactIntegrityError("Accepted generation manifest is missing")
        safe_files: dict[str, str] = {}
        for name, digest in files.items():
            if (
                not isinstance(name, str)
                or "\\" in name
                or PurePosixPath(name).is_absolute()
                or any(part in ("", ".", "..") for part in name.split("/"))
                or not isinstance(digest, str)
                or not _SHA256_PATTERN.fullmatch(digest)
            ):
                raise ArtifactIntegrityError("Accepted generation manifest is invalid")
            safe_files[name] = digest
        return safe_files

    @staticmethod
    def _safe_child(root: Path, relative_path: str) -> Path:
        parts = PurePosixPath(relative_path).parts
        if (
            not parts
            or PurePosixPath(relative_path).is_absolute()
            or "\\" in relative_path
            or any(part in ("", ".", "..") for part in parts)
        ):
            raise ArtifactNotFoundError("Artifact not found")
        resolved_root = root.resolve(strict=True)
        current = root
        for part in parts:
            current = current / part
            try:
                if current.is_symlink():
                    raise ArtifactIntegrityError("Artifact path is invalid")
                resolved = current.resolve(strict=True)
            except (OSError, RuntimeError) as error:
                raise ArtifactNotFoundError("Artifact not found") from error
            if not resolved.is_relative_to(resolved_root):
                raise ArtifactIntegrityError("Artifact path is invalid")
        if not current.is_file():
            raise ArtifactNotFoundError("Artifact not found")
        return current.resolve(strict=True)

    def _accepted(self, generation_dir: Path) -> tuple[Path, dict, dict[str, str], Path]:
        directory, result = self._result(generation_dir)
        if result.get("status") != "accepted":
            raise ArtifactNotFoundError("Accepted generation not found")
        files = self._export_files(result)
        website = directory / "website"
        try:
            if website.is_symlink() or not website.is_dir():
                raise ArtifactNotFoundError("Accepted generation not found")
            resolved_website = website.resolve(strict=True)
        except (OSError, RuntimeError) as error:
            raise ArtifactNotFoundError("Accepted generation not found") from error
        if resolved_website.parent != directory:
            raise ArtifactIntegrityError("Accepted output path is invalid")
        return directory, result, files, resolved_website

    def _verified_output(
        self,
        website: Path,
        files: dict[str, str],
        relative_path: str,
    ) -> tuple[bytes, str]:
        expected = files.get(relative_path)
        if expected is None:
            raise ArtifactNotFoundError("Artifact not found")
        path = self._safe_child(website, relative_path)
        try:
            payload = path.read_bytes()
        except OSError as error:
            raise ArtifactNotFoundError("Artifact not found") from error
        if hashlib.sha256(payload).hexdigest() != expected:
            raise ArtifactIntegrityError("Accepted artifact checksum mismatch")
        return payload, expected

    @staticmethod
    def _asset_ids(page_spec: object) -> set[str]:
        identifiers: set[str] = set()

        def collect(value: object) -> None:
            if isinstance(value, dict):
                asset_id = value.get("asset_id")
                if isinstance(asset_id, str):
                    identifiers.add(asset_id)
                for child in value.values():
                    collect(child)
            elif isinstance(value, list):
                for child in value:
                    collect(child)

        collect(page_spec)
        return identifiers

    def _page_spec(
        self, website: Path, files: dict[str, str]
    ) -> tuple[dict, bytes]:
        payload, _ = self._verified_output(website, files, "page_spec.json")
        try:
            page_spec = json.loads(payload.decode("utf-8"))
        except (UnicodeError, json.JSONDecodeError) as error:
            raise ArtifactIntegrityError("Accepted page specification is invalid") from error
        if not isinstance(page_spec, dict):
            raise ArtifactIntegrityError("Accepted page specification is invalid")
        return page_spec, payload

    def _trusted_asset(self, asset_id: str) -> Path:
        if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", asset_id):
            raise ArtifactNotFoundError("Asset not found")
        project_root = self.project_root.resolve(strict=True)
        asset_root = (project_root / "assets/fullpage").resolve(strict=True)
        if not asset_root.is_relative_to(project_root):
            raise ArtifactIntegrityError("Trusted asset root is invalid")
        catalog_path = asset_root / "catalog.json"
        catalog = self._read_json_file(catalog_path)
        assets = catalog.get("assets")
        info = assets.get(asset_id) if isinstance(assets, dict) else None
        if not isinstance(info, dict):
            raise ArtifactNotFoundError("Asset not found")
        relative = info.get("path")
        expected = info.get("sha256")
        if not isinstance(relative, str) or not isinstance(expected, str) or not _SHA256_PATTERN.fullmatch(expected):
            raise ArtifactIntegrityError("Trusted asset catalog is invalid")
        try:
            path = (project_root / relative).resolve(strict=True)
        except (OSError, RuntimeError) as error:
            raise ArtifactNotFoundError("Asset not found") from error
        if not path.is_relative_to(asset_root) or path.suffix.lower() != ".svg" or not path.is_file():
            raise ArtifactIntegrityError("Trusted asset path is invalid")
        try:
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError as error:
            raise ArtifactNotFoundError("Asset not found") from error
        if digest != expected:
            raise ArtifactIntegrityError("Trusted asset checksum mismatch")
        return path

    def public_generation_summary(self, generation_dir: Path) -> GenerationSummary:
        directory, result = self._result(generation_dir)
        internal_status = result.get("status")
        if internal_status == "accepted":
            status = "completed"
        elif internal_status == "input_too_long":
            status = "input_too_long"
        else:
            status = "generation_failed"

        public = result.get("api_summary")
        public = public if isinstance(public, dict) else {}
        section_count = result.get("sections")
        if type(section_count) is not int or section_count < 0:
            section_count = None

        def safe_text(name: str, limit: int = 120) -> str | None:
            value = public.get(name)
            if not isinstance(value, str) or not value.strip():
                return None
            return value.strip()[:limit]

        created_at = None
        created_value = public.get("created_at")
        if isinstance(created_value, str) and len(created_value) <= 64:
            try:
                created_at = datetime.fromisoformat(created_value.replace("Z", "+00:00"))
            except ValueError:
                created_at = None

        identifier = directory.name
        completed = status == "completed"
        return GenerationSummary(
            generation_id=identifier,
            status=status,
            message=_SAFE_STATUS_MESSAGES[status],
            genre=safe_text("genre"),
            style_mode=safe_text("style_mode"),
            business_name=safe_text("business_name"),
            section_count=section_count,
            created_at=created_at,
            preview_url=(f"/api/v1/generations/{identifier}/preview/index.html" if completed else None),
            download_url=(f"/api/v1/generations/{identifier}/download.zip" if completed else None),
            files=list(_SOURCE_NAMES) if completed else [],
        )

    def read_accepted_source(self, generation_dir: Path) -> dict[str, str]:
        _, _, files, website = self._accepted(generation_dir)
        source: dict[str, str] = {}
        for name in _SOURCE_NAMES:
            payload, _ = self._verified_output(website, files, name)
            try:
                source[name] = payload.decode("utf-8")
            except UnicodeError as error:
                raise ArtifactIntegrityError("Accepted source is not valid UTF-8") from error
        return source

    def read_accepted_preview_file(
        self, generation_dir: Path, relative_path: str
    ) -> tuple[bytes, str]:
        _, _, files, website = self._accepted(generation_dir)
        if relative_path in _SOURCE_CONTENT_TYPES:
            payload, _ = self._verified_output(website, files, relative_path)
            return payload, _SOURCE_CONTENT_TYPES[relative_path]

        parts = PurePosixPath(relative_path).parts
        if (
            len(parts) != 2
            or parts[0] != "assets"
            or not parts[1].endswith(".svg")
            or "\\" in relative_path
            or PurePosixPath(relative_path).is_absolute()
        ):
            raise ArtifactNotFoundError("Artifact not found")
        asset_id = parts[1][:-4]
        page_spec, _ = self._page_spec(website, files)
        if asset_id not in self._asset_ids(page_spec):
            raise ArtifactNotFoundError("Asset not found")
        trusted_path = self._trusted_asset(asset_id)
        expected = files.get(f"assets/{asset_id}.svg")
        try:
            payload = trusted_path.read_bytes()
        except OSError as error:
            raise ArtifactNotFoundError("Asset not found") from error
        if expected is None or hashlib.sha256(payload).hexdigest() != expected:
            raise ArtifactIntegrityError("Accepted asset checksum mismatch")
        return payload, "image/svg+xml"

    def build_accepted_zip(self, generation_dir: Path, destination: BinaryIO) -> None:
        _, _, files, website = self._accepted(generation_dir)
        page_spec, page_spec_bytes = self._page_spec(website, files)
        payloads: dict[str, bytes] = {}
        for name in _ZIP_FIXED_FILES:
            if name == "page_spec.json":
                payloads[name] = page_spec_bytes
            else:
                payloads[name], _ = self._verified_output(website, files, name)

        for asset_id in sorted(self._asset_ids(page_spec)):
            relative = f"assets/{asset_id}.svg"
            trusted_path = self._trusted_asset(asset_id)
            expected = files.get(relative)
            try:
                payload = trusted_path.read_bytes()
            except OSError as error:
                raise ArtifactNotFoundError("Asset not found") from error
            if expected is None or hashlib.sha256(payload).hexdigest() != expected:
                raise ArtifactIntegrityError("Accepted asset checksum mismatch")
            payloads[relative] = payload

        with zipfile.ZipFile(destination, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
            for name, payload in payloads.items():
                archive.writestr(name, payload)

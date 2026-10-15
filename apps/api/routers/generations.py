"""Read-only routes for safe, accepted generation artifacts."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse, Response

from apps.api.schemas import GenerationSummary
from apps.api.services.artifacts import ArtifactNotFoundError, ArtifactStore
from apps.api.services.runtime import get_runtime


router = APIRouter(prefix="/api/v1/generations", tags=["generations"])


def _store() -> ArtifactStore:
    runtime = get_runtime()
    return ArtifactStore(
        output_root=runtime.settings.generation_output_dir,
        project_root=runtime.project_root,
    )


def _not_found() -> HTTPException:
    return HTTPException(status_code=404, detail="Generation artifact not found")


def _generation_directory(store: ArtifactStore, generation_id: str) -> Path:
    try:
        return store.generation_dir(generation_id)
    except ArtifactNotFoundError as error:
        raise _not_found() from error


@router.get(
    "/{generation_id}/preview/{relative_path:path}",
    summary="Show one accepted preview file",
    response_description="Renderer HTML, CSS, JavaScript, or a referenced local SVG asset",
)
def preview_file(generation_id: str, relative_path: str) -> Response:
    store = _store()
    generation_dir = _generation_directory(store, generation_id)
    try:
        payload, content_type = store.read_accepted_preview_file(generation_dir, relative_path)
    except ArtifactNotFoundError as error:
        raise _not_found() from error

    settings = get_runtime().settings
    host = f"[{settings.host}]" if ":" in settings.host else settings.host
    api_origin = f"http://{host}:{settings.port}"
    headers = {
        "Content-Security-Policy": (
            "default-src 'none'; base-uri 'none'; object-src 'none'; form-action 'none'; "
            f"connect-src 'none'; script-src 'self' {api_origin}; "
            f"style-src 'self' {api_origin}; img-src 'self' {api_origin} data:"
        ),
        "X-Content-Type-Options": "nosniff",
        "Cache-Control": "no-store",
    }
    return Response(content=payload, media_type=content_type, headers=headers)


@router.get(
    "/{generation_id}/source",
    summary="Read accepted HTML, CSS, and JavaScript",
    response_description="Exactly the three renderer source files",
)
def source_files(generation_id: str) -> JSONResponse:
    store = _store()
    generation_dir = _generation_directory(store, generation_id)
    try:
        source = store.read_accepted_source(generation_dir)
    except ArtifactNotFoundError as error:
        raise _not_found() from error
    return JSONResponse(
        content=source,
        headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"},
    )


@router.get(
    "/{generation_id}/download.zip",
    summary="Download accepted renderer output and referenced assets",
    response_description="A ZIP containing only the accepted renderer files and attribution",
)
def download_zip(generation_id: str) -> Response:
    store = _store()
    generation_dir = _generation_directory(store, generation_id)
    archive = BytesIO()
    try:
        store.build_accepted_zip(generation_dir, archive)
    except ArtifactNotFoundError as error:
        raise _not_found() from error
    return Response(
        content=archive.getvalue(),
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="website-{generation_id}.zip"',
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get(
    "/{generation_id}",
    response_model=GenerationSummary,
    summary="Read a safe generation summary",
    responses={404: {"description": "Generation not found"}},
)
def generation_summary(generation_id: str) -> GenerationSummary:
    store = _store()
    generation_dir = _generation_directory(store, generation_id)
    try:
        return store.public_generation_summary(generation_dir)
    except ArtifactNotFoundError as error:
        raise _not_found() from error

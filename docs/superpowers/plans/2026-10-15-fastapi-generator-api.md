# FastAPI Local Generator API Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Expose the existing source-bound website pipeline through a local FastAPI service with typed intake and generation responses, safe previews, and downloads.

**Architecture:** FastAPI adapts the existing `prepare_intake`, `FullPageGenerator`, catalog, and renderer instead of reimplementing them. Tokenizer and catalogs may load without loading model weights. The model is initialized once, lazily, on an explicit generation call. Accepted outputs live under a unique directory in `outputs/webapp/generations`.

**Tech Stack:** Existing project `.venv` with PyTorch CUDA, Python, FastAPI, Uvicorn, Pydantic, standard-library `zipfile`, existing source-bound pipeline, and the repository-pinned Tailwind CSS 4.3.3 CLI under `tooling/tailwind` for generated Tailwind pages.

**Spec:** `docs/superpowers/specs/2026-10-15-generator-chat-application-design.md`

## Global Constraints

- Keep the selected checkpoint at `training/selected/fullpage-v5/model/TRAIN-025-step1800.pt` and use the source-bound contract `request-draft-source-bound-v1`.
- Call `prepare_intake(prompt, draft, tokenizer, catalog)` for intake and call it again before every generation.
- Load `FullPageGenerator` lazily and only after an explicit request reaches `ready`.
- Keep the API synchronous JSON in version one. Do not add token streaming or simulated model-stage progress.
- Store each run under a unique UUID folder within `outputs/webapp/generations`; never accept a filesystem path from a browser request.
- Serve preview, source, and ZIP only when the stored generation report has `status=accepted`.
- Bind to loopback, restrict CORS to configured frontend origins, use one Uvicorn worker, and serialize access to the GPU.
- Do not expose tracebacks, raw model output, prompts, absolute paths, checkpoint bytes, training data, or final data in API responses.
- Use the existing root `.venv` to avoid duplicating the CUDA PyTorch install. Pin only API dependencies without changing PyTorch.
- Reuse the existing `tooling/tailwind/package.json` and lockfile for generated Tailwind CSS. Do not duplicate or upgrade this compiler as part of the Next.js package.
- Do not add or run tests, build checks, or inference under the current request. Record each API installation or application command if it produces artifacts.
- Commit and push each completed change on `feature/pipeline-data-model-training` without a `Co-Authored-By` trailer.

## Review Focus

- Intake has missing facts, invalid evidence spans, unsupported feature requests, or a prompt over budget. Return a safe typed status and do not load model weights.
- A caller sends a request draft whose nested prompt differs from its envelope prompt. Reject it before generation.
- Two clients request generation together. Permit only one model call at a time and return a typed conflict for the other.
- A generation report is failed or partial. Preview, source, and ZIP routes must refuse it.
- A generation ID is malformed or a symlink/path traversal points outside the generation root. Return not found or invalid ID without reading the target.

---

### Task 1: Define API package, runtime settings, and schemas

**Files:**
- Create: `apps/__init__.py`
- Create: `apps/api/__init__.py`
- Create: `apps/api/requirements-api.in`
- Create: `apps/api/requirements-api.txt`
- Create: `apps/api/settings.py`
- Create: `apps/api/schemas.py`
- Create: `apps/api/.env.example`
- Modify: `logs/LOG_EKSPERIMEN_DAN_INTERAKSI_LLM.md`

**Interfaces:**
- Consumes: API configuration values `project_root`, `checkpoint_path`, `generation_output_dir`, `allowed_origins`, `host`, and `port`.
- Produces: typed Pydantic schemas for `IntakeEnvelope(prompt, draft)`, `IntakeResponse(status, message, missing_fields, request)`, `GenerationRequest(prompt, draft)`, `GenerationResponse(status, generation_id, message, preview_url, download_url, files)`, and safe `GenerationSummary`.
- Produces: `CatalogResponse` with supported genre/style identifiers, public capability labels, and asset metadata needed by the UI.

- [ ] Resolve supported FastAPI and Uvicorn versions using official documentation and the existing Python environment; pin those packages in `requirements-api.txt` without changing Torch.
- [ ] Define settings defaults that resolve from project root and use loopback host, port 8000, exact local CORS origins, the selected model pointer, and `outputs/webapp/generations`.
- [ ] Define intake status values `needs_clarification`, `unsupported_request`, `input_too_long`, and `ready`.
- [ ] Define generation status values `completed`, `generation_failed`, and `input_too_long`; keep expected workflow status in JSON and reserve HTTP errors for invalid transport, missing IDs, and conflicts.
- [ ] Bound prompt length to 1,000 characters and reject additional unexpected top-level fields.
- [ ] Add only environment variable names and safe local examples to `.env.example`; never include secrets.
- [ ] Append the AI interaction record and commit/push this contract foundation.

### Task 2: Add non-inference runtime and intake services

**Files:**
- Create: `apps/api/services/__init__.py`
- Create: `apps/api/services/runtime.py`
- Create: `apps/api/services/intake.py`
- Create: `apps/api/services/catalog.py`
- Modify: `logs/LOG_EKSPERIMEN_DAN_INTERAKSI_LLM.md`

**Interfaces:**
- `Runtime.get_tokenizer() -> Tokenizer` loads the project tokenizer once.
- `Runtime.get_intake_catalog() -> dict` calls `load_intake_catalog(project_root)` once.
- `Runtime.get_generator() -> FullPageGenerator` verifies the package digest and creates the generator once on demand.
- `validate_intake(prompt: str, draft: dict) -> IntakeResponse` delegates to `prepare_intake` and maps internal statuses without returning raw validator details.
- `get_public_catalog() -> CatalogResponse` returns only supported genres, styles, documented capability labels, and selectable asset metadata.

- [ ] Load the tokenizer and intake catalogs without constructing `FullPageGenerator`.
- [ ] Map each internal intake status to one of the four public status literals. Preserve `missing_fields`; replace raw validator text with safe Indonesian guidance.
- [ ] Validate `prompt == draft["prompt"]` before calling `prepare_intake`.
- [ ] Confirm by code-path inspection that health, catalog, and intake do not call `get_generator`.
- [ ] Append the AI interaction record and commit/push this service boundary.

### Task 3: Add artifact storage and safe file routes

**Files:**
- Create: `apps/api/services/artifacts.py`
- Create: `apps/api/routers/generations.py`
- Modify: `logs/LOG_EKSPERIMEN_DAN_INTERAKSI_LLM.md`

**Interfaces:**
- `new_generation_id() -> str` returns a server-created UUID.
- `generation_dir(generation_id: str) -> Path` returns a resolved child of the configured output root or raises a safe not-found error.
- `public_generation_summary(generation_dir: Path) -> GenerationSummary` reads only `result.json` fields that are approved for the browser.
- `read_accepted_source(generation_dir: Path) -> dict[str, str]` returns exactly `index.html`, `styles.css`, and `app.js` after verifying `status=accepted`.
- `read_accepted_preview_file(generation_dir: Path, relative_path: str) -> tuple[bytes, str]` serves only accepted `index.html`, `styles.css`, `app.js`, and referenced catalog SVG assets with fixed content types.
- `build_accepted_zip(generation_dir: Path, destination: BinaryIO) -> None` adds only renderer output, local asset files, `page_spec.json`, and `asset_attribution.json` after verifying acceptance.

- [ ] Generate opaque UUID identifiers server-side and reject malformed identifiers before path resolution.
- [ ] Resolve candidate paths and require each to remain within the configured generation root.
- [ ] Require an accepted `result.json` before reading preview, source, or ZIP artifacts.
- [ ] Resolve preview files from the three renderer files plus asset IDs referenced by the accepted `page_spec.json`; reject absolute paths, `..`, unknown names, and symlinks that leave the generation or trusted asset root.
- [ ] Build ZIP contents from a fixed allowlist and validated local asset names; never archive arbitrary files found beside an output.
- [ ] Return iframe preview with a restrictive CSP that permits scripts, styles, and images only from the configured API origin, plus `data:` for images; set `default-src 'none'`, `base-uri 'none'`, `object-src 'none'`, `form-action 'none'`, and `connect-src 'none'`. Also set `X-Content-Type-Options: nosniff` and no-store caching. Never expose the internal output path.
- [ ] Append the AI interaction record and commit/push the artifact boundary.

### Task 4: Add API routes and lazy generation

**Files:**
- Create: `apps/api/routers/__init__.py`
- Create: `apps/api/routers/health.py`
- Create: `apps/api/routers/intake.py`
- Create: `apps/api/main.py`
- Modify: `apps/api/routers/generations.py`
- Modify: `logs/LOG_EKSPERIMEN_DAN_INTERAKSI_LLM.md`

**Interfaces:**
- `GET /api/v1/health -> HealthResponse` reports service and `model_loaded` state without loading weights.
- `GET /api/v1/catalog -> CatalogResponse` returns the local public catalog.
- `POST /api/v1/intake/validate -> IntakeResponse` does not generate or load model weights.
- `POST /api/v1/generations -> GenerationResponse` accepts the same `prompt` and source-bound `draft` as intake, calls `prepare_intake` again, uses only its validated internal request, allocates a unique output directory, sets the request ID to the server generation ID, and calls `FullPageGenerator.generate` once.
- `GET /api/v1/generations/{generation_id} -> GenerationSummary` returns the safe report projection.
- `GET /api/v1/generations/{generation_id}/preview/{relative_path:path}` serves accepted `index.html`, its sibling CSS/JS, or a referenced local SVG asset. The returned preview URL ends in `/preview/index.html` so relative files resolve under the same generation route.
- `GET /api/v1/generations/{generation_id}/source -> SourceResponse` returns only the three source files.
- `GET /api/v1/generations/{generation_id}/download.zip` returns accepted files and assets.

- [ ] Add CORS middleware with configured exact origins, methods, and headers; do not use wildcard origins.
- [ ] Define route handlers as synchronous callables around blocking model work and guard generator access with a non-blocking single-process lock; return a typed `generation_in_progress` conflict instead of queueing a second request.
- [ ] On valid generation, use the internal request returned by `prepare_intake`, replace its request ID with the server UUID, create a UUID output folder, call the existing generator once, then translate accepted output to safe URLs including `/preview/index.html`.
- [ ] On expected pipeline failure, return a safe failure status and leave internal diagnostics local; do not expose partial outputs through artifact routes.
- [ ] Map invalid body, missing generation, generation conflict, and internal errors to documented HTTP codes and stable JSON response shapes.
- [ ] Use the default FastAPI OpenAPI generation and add route summaries, response models, examples, and error descriptions.
- [ ] Append the AI interaction record. Review the API source and OpenAPI route declarations without starting the service or sending an inference request. Commit and push.

### Task 5: Document local API operation

**Files:**
- Create: `apps/api/README.md`
- Modify: `README.md`
- Modify: `docs/README.md`
- Modify: `logs/LOG_EKSPERIMEN_DAN_INTERAKSI_LLM.md`

**Interfaces:**
- Consumes: environment keys, route schemas, package manifest, and the OpenAPI contract.
- Produces: exact local setup, start, route, and shutdown instructions for the user.

- [ ] Document installing the pinned API dependency file into the existing `.venv` without reinstalling Torch.
- [ ] Document starting Uvicorn from the repository root on `127.0.0.1:8000` with exactly one worker.
- [ ] Document `/docs`, `/openapi.json`, local CORS configuration, lazy model loading, and the boundary that generation invokes GPU inference.
- [ ] Document that `style_mode=tailwind` uses the pinned compiler in `tooling/tailwind`, and run `npm ci` there only if its existing `node_modules` folder is absent. Record that install as a RUN entry.
- [ ] State that tests and inference were not run during this implementation unless separately authorized.
- [ ] Append the AI interaction record and commit/push the documentation.

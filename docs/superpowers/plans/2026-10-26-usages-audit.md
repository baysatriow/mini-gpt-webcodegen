# Usage Audit and Safe Tunnel Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a private local Usage dashboard that audits every generation request, shows GPU telemetry collected during generation, and can be safely shared through an authenticated Cloudflare Quick Tunnel.

**Architecture:** FastAPI middleware creates a privacy-minimized usage record before request validation; the generation route records semantic outcome and metrics; SQLite stores records and stage events while per-run JSONL holds bounded GPU samples. A Next.js 16 proxy and signed HttpOnly session protect all pages and API rewrites when tunnel access is enabled. The Usage route consumes typed API responses and leaves the generation pipeline unchanged.

**Tech Stack:** Python, FastAPI, Pydantic, SQLite, `nvidia-smi`, PyTorch CUDA telemetry, Next.js 16.4.1 Proxy and Route Handlers, React, existing Tailwind/shadcn components, Node's built-in test runner.

**Spec:** `docs/superpowers/specs/2026-10-26-usages-audit-design.md`

## Global Constraints

- Store only operational metadata; never store prompt, business facts, source, generated content, raw exceptions, absolute paths, or environment values.
- Preserve the existing source-bound intake and generation contract, selected checkpoint, renderer, and test/final data boundary.
- Keep FastAPI loopback-only, one worker, one API instance per Usage database, and do not load a model or run inference from Usage endpoints.
- GPU historical metrics represent samples collected during generation and device-wide `nvidia-smi` values; PyTorch memory values are separate process metrics.
- Quick Tunnel access requires `APP_ACCESS_REQUIRED=true`, username, password, and a session secret of at least 32 characters; secrets stay in ignored local environment files.
- Use Next.js 16.4.1 `src/proxy.ts` and its documented Route Handler conventions; add no runtime dependencies.
- Preserve existing local UI edits and accessible composer guidance; do not include `Co-authored-by` in Git commits.

## Review Focus

- Schema-invalid generation request: middleware must persist a `rejected` record and expose `X-Usage-ID` without reading its body.
- HTTP 200 generation failure or HTTP 409 lock/intake response: classify from route outcome and safe code, not HTTP status alone.
- Missing `nvidia-smi`, CPU runtime, or CUDA sampling error: audit remains readable and unavailable telemetry stays `null`.
- A live second API process: reject startup without interrupting the first instance's records; stale instances recover as `interrupted`.
- Retention and detail race: never return a sample after its database record is removed; prune only Usage-owned files.
- Missing or tampered tunnel cookie and incomplete auth environment: fail closed; valid cookie permits both UI and rewritten API requests.
- Narrow viewport and keyboard-only Usage access: preserve readable layout, status text, focus visibility, and composer descriptions.

---

### Task 1: Usage persistence, lifecycle, and safe telemetry

**Files:**
- Create: `apps/api/services/usage_store.py`
- Create: `apps/api/services/usage_telemetry.py`
- Create: `tests/api/test_usage_store.py`
- Create: `tests/api/test_usage_telemetry.py`

**Interfaces:**
- `UsageStore(root: Path, retention_days: int = 90)` owns `usage.sqlite3`, stage events, instance heartbeat, an OS lock file, and UUID-named sample files.
- `UsageStore.start_instance() -> str` obtains a nonblocking Windows/POSIX lock and recovers records left by a prior process; `heartbeat_instance(instance_id: str) -> None`, `stop_instance(instance_id: str) -> None`, `create_record(record: dict) -> None`, `update_record(usage_id: str, **fields) -> None`, `append_sample(usage_id: str, sample: dict) -> None`, `get_record(usage_id: str) -> dict | None`, `get_samples(usage_id: str, limit: int = 300) -> list[dict]`, `list_records(*, cursor: str | None, limit: int, window: str | None, status: str | None, stage: str | None) -> dict`, `summarize(window: str) -> dict`, `prune(now: datetime) -> int`.
- `current_gpu_snapshot() -> dict` returns safe nullable device fields and a stable availability code, never exception text.
- `GenerationGpuSampler(store, usage_id, interval_seconds: float = 1.0)` exposes `start()`, `finish() -> dict`; its background sampler writes device-wide samples without retaining raw subprocess errors.

- [x] **Step 1: Write failing store and telemetry tests** for SQLite schema/transactions, stable `(started_at, usage_id)` pagination, privacy allowlist, active-instance conflict, dead-instance recovery, retention, sample deletion ordering, missing GPU tool, and normalized `nvidia-smi` output.
- [x] **Step 2: Run the focused tests and confirm expected failures** with `.venv\Scripts\python.exe -m unittest tests.api.test_usage_store tests.api.test_usage_telemetry`.
- [x] **Step 3: Implement store and telemetry services** with short SQLite connections, WAL, a 5-second busy timeout, 15-second heartbeat, a nonblocking OS lock, 90-day retention, UUID path validation, and allowlisted fields.
- [x] **Step 4: Run focused tests and confirm they pass** with the same command; confirm no raw error or path appears in serialized records.

### Task 2: Record generation lifecycle and publish the Usage API contract

**Files:**
- Create: `apps/api/routers/usages.py`
- Create: `apps/api/services/usage_audit.py`
- Modify: `apps/api/main.py`
- Modify: `apps/api/routers/generations.py`
- Modify: `apps/api/schemas.py`
- Create: `tests/api/test_usages_api.py`
- Modify: `tests/api/test_generation_request_id.py`
- Modify: `apps/api/README.md`

**Interfaces:**
- `UsageRecorder(store: UsageStore, usage_id: str, started_monotonic: float)` in `apps/api/services/usage_audit.py` exposes `set_stage(stage: str, *, code: str | None = None, generation_id: str | None = None)`, `set_metrics(**safe_metrics)`, and idempotent `finish(outcome: str, *, http_status: int | None = None, code: str | None = None)`.
- Middleware instruments only `POST /api/v1/generations`, creates its SQLite row before FastAPI body validation, stores `UsageRecorder` in `request.state.usage_recorder`, and adds `X-Usage-ID` to the response.
- `create_generation(body: GenerationRequest, request: Request)` explicitly marks safe stages and final outcomes for lock, intake, model load, generation pipeline, output/render, persistence, and success. The middleware fallback classifies schema 422 and uncaught errors.
- Request-scoped GPU sampling starts only when the generator pipeline begins; final metrics distinguish HTTP status from `GenerationResponse.status` and include bounded counts, model basename, retries/sections, device summary, and PyTorch peak-minus-baseline memory.
- `GET /api/v1/usages/summary?window=24h|7d|30d`, `GET /api/v1/usages/gpu/current`, `GET /api/v1/usages/?cursor=&limit=25&window=&status=&stage=`, and `GET /api/v1/usages/{usage_id}` have closed Pydantic response models.

- [x] **Step 1: Write failing API tests** for request-ID header/record on invalid body, explicit 409 codes, HTTP-200 `generation_failed`, current GPU not loading runtime models, safe summary/list/detail and invalid cursor/filter rejection.
- [x] **Step 2: Run focused tests to verify the intended failures** with `.venv\Scripts\python.exe -m unittest tests.api.test_usages_api tests.api.test_generation_request_id`.
- [x] **Step 3: Add typed response schemas, app lifespan store ownership, heartbeat, middleware fallback, generation stage annotations, and Usage routes** without changing generation response behavior or payload logging.
- [x] **Step 4: Run focused API tests and inspect generated OpenAPI**; assert all four Usage paths and no prompt/source/raw exception fields.
- [x] **Step 5: Update `apps/api/README.md`** with request audit semantics, window limits, cursor ordering, GPU scope, retention, local data path, and non-inference guarantees.

### Task 3: Protect tunnel access with a custom signed session

**Files:**
- Create: `apps/web/src/lib/access-session.mjs`
- Create: `apps/web/src/proxy.ts`
- Create: `apps/web/src/app/api/auth/login/route.ts`
- Create: `apps/web/src/app/api/auth/logout/route.ts`
- Create: `apps/web/src/app/login/page.tsx`
- Create: `apps/web/src/components/auth/login-form.tsx`
- Create: `apps/web/tests/access-session.test.mjs`

**Interfaces:**
- `createSessionToken(secret: string, nowMs?: number) -> string`, `verifySessionToken(token: string | undefined, secret: string, nowMs?: number) -> boolean`, `isAccessConfigured(env = process.env) -> boolean`, and `isAccessRequired(env = process.env) -> boolean` are server-only helpers.
- `POST /api/auth/login` accepts `{ username, password }`, compares configured credentials in constant-time, validates same-host Origin, and sets a signed 12-hour `rancang_session` cookie with HttpOnly, SameSite=Lax, Path=/, and Secure on HTTPS.
- `POST /api/auth/logout` clears that cookie. `src/proxy.ts` protects all application pages and `/api/*`; UI requests redirect to `/login`, API requests return 401 JSON, and incomplete required auth returns 503.
- Login UI provides labeled username/password fields, show/hide password, loading/error state, and no credential value in URLs or logs.

- [x] **Step 1: Write failing tests** for valid and expired sessions, tampered signatures, malformed tokens, missing auth configuration, and valid/invalid same-host login request validation.
- [x] **Step 2: Run `npm --prefix apps/web test` and confirm the new auth tests fail for the missing helper**.
- [x] **Step 3: Implement the signed-session helper, Next Proxy gate, login/logout handlers, and custom accessible login page** using the Next 16 docs read during planning.
- [x] **Step 4: Run `npm --prefix apps/web test`, `npm --prefix apps/web run lint`, and `npm --prefix apps/web run build`; confirm no auth secret is compiled into client assets.

### Task 4: Add responsive Usage dashboard and review the updated chat UI

**Files:**
- Create: `apps/web/src/lib/usage-client.ts`
- Create: `apps/web/src/components/usage/usage-dashboard.tsx`
- Create: `apps/web/src/app/usage/page.tsx`
- Modify: `apps/web/src/components/chat/history-sidebar.tsx`
- Modify: `apps/web/src/components/chat/composer.tsx`
- Create: `apps/web/tests/usage-contract.test.mjs`

**Interfaces:**
- `usage-client.ts` exports closed TypeScript response types plus `getUsageSummary(window)`, `getCurrentGpu()`, `getUsagePage(filters)`, and `getUsageDetail(usageId)`; all fetches use same-origin `/api/v1/usages` and `cache: "no-store"`.
- Dashboard displays current device snapshot, time-window KPI, GPU generation-sample coverage, history with stable pagination, and an expandable stage/GPU detail view. Empty, unavailable, loading, and error states are explicit.
- Sidebar adds a keyboard-accessible link to `/usage`; dashboard provides a link back to `/`.
- Composer retains `aria-describedby` pointing to persistent concise guidance and a conditional count with a stable element ID.

- [x] **Step 1: Write failing contract tests** for same-origin no-store endpoints, statuses not conveyed by color alone, required empty/unavailable copy, `/usage` navigation, and composer `aria-describedby` wiring.
- [x] **Step 2: Run `npm --prefix apps/web test` and confirm the relevant tests fail** before adding UI code.
- [x] **Step 3: Implement the typed client, responsive dashboard, navigation link, and composer accessibility restoration** using existing design tokens and components.
- [x] **Step 4: Run frontend tests, lint, typecheck through the build, and production build**.
- [x] **Step 5: Start/reuse local services and visually inspect fresh `/` and `/usage` tabs at desktop, then inspect `/usage` at a 390 px viewport**; do not submit generation prompts or claim inference validation.

### Task 5: Update project logs, commit, push, and deploy the authenticated Quick Tunnel

**Files:**
- Modify: `logs/LOG_EKSPERIMEN_DAN_INTERAKSI_LLM.md`
- Modify: `apps/web/README.md`
- Modify: `docs/superpowers/specs/2026-10-26-usages-audit-design.md`
- Modify: this plan's task checkboxes as implementation proceeds

**Interfaces:**
- Log records the requested UI review, Usage data contract, API/UI changes, verification commands/results, commit SHA, deployment type, tunnel readiness, and extractor/inference limits without credentials.
- Deployment config is generated only in ignored `apps/web/.env.local`; tunnel is not started unless all auth settings are present and the no-cookie gate has passed.

- [x] **Step 1: Append a dated project interaction/audit log entry** with scope, checks, outcomes, and limits; no prompt content or secrets.
- [x] **Step 2: Run the focused API and full frontend verification commands** and inspect `git diff --check`, `git status`, and the exact staged diff.
- [x] **Step 3: Commit with a plain message and no co-author trailer, then push the current feature branch**; verify remote SHA and branch state.
- [x] **Step 4: Prepare an ignored local auth environment with a fresh high-entropy temporary password and session secret; stop/restart services only after confirming listeners and preserving current browser drafts.**
- [x] **Step 5: Verify unauthenticated UI redirect and API 401, valid login, authenticated health/Usage summary, and no model load/inference from Usage.**
- [x] **Step 6: Start or reuse Cloudflare Quick Tunnel to Next.js port 3000 only after the auth gate succeeds; verify the HTTPS URL, communicate the temporary credentials privately in the final answer, and state that the URL expires or changes when the tunnel restarts.**

## Self-Review

- Spec coverage maps to Tasks 1 and 2 for lifecycle, telemetry, privacy, retention, and API; Task 3 for tunnel auth; Task 4 for Usage/UI/accessibility; Task 5 for log, push, verification, and deployment.
- Each task defines exact files and interfaces; RED tests precede production code. Focus cases are pinned to the owning test files.
- Window, outcome, cursor, retention, and auth settings use the values frozen by the spec.
- The plan does not ask Usage endpoints to initialize the extractor or generate a page. Local API health currently reports that the extractor package is unavailable, so generation capability remains separate evidence.
- The temporary tunnel serves the Next.js port only; FastAPI remains loopback and is reachable remotely only through the authenticated Next.js proxy.

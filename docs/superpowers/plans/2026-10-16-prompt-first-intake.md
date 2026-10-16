# Prompt-First Intake Implementation Plan

> **For agentic workers:** Execute this plan task by task in the current feature branch. Steps use checkbox syntax for tracking.

**Goal:** Let users describe a complete landing page or company profile in one brief, answer one grouped clarification when needed, review every extracted fact and its source, then explicitly generate the site.

**Architecture:** Add a `request_extract` model task and a separate candidate checkpoint initialized from selected TRAIN-025 step 1800. FastAPI verifies every extracted value against message source spans and shares one inference lock between extractor and generator. The Next.js chat becomes a brief-first workspace while keeping the existing source-bound generator, preview, code view, and downloads.

**Tech Stack:** Python 3.11, PyTorch, existing MiniGPT tokenizer/model and training engine, FastAPI/Pydantic, Next.js 16, React 19, Tailwind 4, shadcn.

**Spec:** `docs/superpowers/specs/2026-10-16-prompt-first-intake-design.md`

## Global Constraints

- Keep the existing complete-fact requirements and source-bound request contract.
- Keep context at 2,048 tokens and preflight the exact tokenizer input plus reserved output budget.
- The hard brief limit is 4,000 characters; never truncate user text or model output.
- Train the extractor from training-family data only; keep all existing development, test, and final data partitions sealed.
- Do not enable automatic extraction until its frozen development gate passes; retain manual detail editing as fallback.
- Revalidate the final `RequestDraft` through the existing `prepare_intake()` path before generation.
- Load the extractor and generator one at a time under the same inference lock.
- Do not add automated test files or run test suites in this task. Use build, lint, schema/data audits, local non-final development evaluation, and browser review, and describe exactly what each proves.
- Commit and push each coherent change to the current feature branch without any `Co-Authored-By` trailer.
- Preserve the sealed final partition and do not claim 95 percent visual quality without browser and human review.

## Review Focus

- Correction or contradiction across multiple messages must not silently select a fact value.
- Missing facts must be grouped into one clarification; a second incomplete reply opens the remaining-field editor.
- Negated, future, reference-only, or retracted unsupported capabilities must not block generation as active requests.
- Source spans must point to the exact original message text, including structured facts whose title and description come from different messages.
- Over-budget prompts, malformed extraction output, or an unavailable extractor must fail closed and preserve the user's text for manual editing.

## Design Direction

- **Product:** Rancang is a local website workshop for students and small business owners, focused on moving from a natural brief to a reviewable page.
- **Palette:** warm paper `#F4F2EC`, clean surface `#FEFDF9`, ink `#202A29`, forest `#3A6E5A`, quiet text `#67736D`, and clay `#C76B45` for secondary emphasis.
- **Typography:** retain IBM Plex Sans for readable conversation and IBM Plex Mono for code and technical status. Use a 32/38 px page title, 15/25 px body, and 12/16 px supporting text.
- **Layout:** compact history rail, split conversation and preview workspace, one wide brief composer on an empty session, inline fact review, and mobile tabs for conversation and preview.
- **Principles:** use paper-like surfaces and clear dividers; show source evidence only when requested; keep one primary action; avoid gradients, decorative metric cards, repeated confirmation steps, and automatic motion.
- **Generic-design review:** the palette, compact editorial prompt area, evidence-backed fact review, and preview canvas follow the local web-building task rather than a generic AI dashboard template.

---

### Task 1: Extraction Contract and Isolated Dataset

**Files:**
- Create: `configs/fullpage/request-extract-v1.schema.json`
- Create: `src/fullpage/request_extract_contracts.py`
- Create: `qa/prepare_request_extract_v1.py`
- Create: `qa/audit_request_extract_v1.py`
- Create: `notebooks/request_extract_v1.ipynb`
- Create locally, ignored by Git: `data/processed/request_extract/v1/{train,development}.jsonl` and `manifest.json`

**Interfaces:**
- `validate_request_extract(value: object) -> list[str]` checks only the extractor wire schema and closed enums.
- `build_request_extract_dataset(root: Path, output_dir: Path) -> dict` reads only `data/processed/fullpage/v5/train.requests.jsonl` for training families and generates a disjoint synthetic development family bank with prompt templates not used for training.
- Each row contains `example_id`, `family_id`, `split`, `messages`, `target`, `source_family_ids`, `prompt_pattern_id`, and tokenizer budget metadata.
- Train at least 100 distinct examples for every fact kind and 100 distinct brief families per page genre. Development safety buckets use at least 50 distinct families each, per the approved spec.
- Frozen development gates: exact-value precision at least 95 percent, explicit-fact recall at least 90 percent, zero accepted facts without valid evidence, at least 95 percent correct explicit corrections and retractions, 100 percent ambiguous single-value conflicts held for confirmation, zero active unsupported requests passed to generation, and no more than 5 percent false rejection or retraction-overblocking in each specified denominator. Unclear-only requests and genre/style retraction without replacement must return clarification for 100 percent of their families.

- [ ] Freeze the compact `request-extract-v1` target shape for scalar facts, structured facts, setting mentions, capability mentions, out-of-catalog mentions, and corrections.
- [ ] Build training rows exclusively from the frozen training request file; do not read its validation request file.
- [ ] Generate an independent development family and prompt-pattern bank and record family and pattern intersections in the manifest.
- [ ] Add a read-only audit that checks hashes, schema, provenance substrings, token budgets, family uniqueness, bucket counts, and zero train/development overlap.
- [ ] Add a notebook that displays corpus counts, one redacted training example, budget distribution, manifest checks, and later training/evaluation reports.
- [ ] Commit and push as `feat: add prompt extraction data pipeline`.

### Task 2: Extractor Training and Development Gate

**Files:**
- Modify: `src/fullpage/serialization.py`
- Modify: `src/training/engine.py`
- Create: `src/fullpage/request_extract_dataset.py`
- Create: `src/fullpage/request_extract_model.py`
- Create: `configs/fullpage/training-request-extract-v1.json`
- Create: `qa/train_request_extract_v1.py`
- Create: `qa/evaluate_request_extract_v1.py`
- Create locally, ignored by Git: `checkpoints/REQUEST-EXTRACT-V1`, `outputs/request_extract/v1`, and `training/selected/request-extract-v1`

**Interfaces:**
- `request_extract` output budget is 896 tokens, separate from the existing `page_plan` and `section_content` sampler contracts.
- `RequestExtractor(checkpoint: Path, root: Path).extract(messages: list[dict[str, str]]) -> dict` uses greedy generation and returns raw validated JSON only; malformed output raises a controlled extraction error.
- `run_request_extract_training(...)` pins initialization to the exact selected TRAIN-025 step-1800 checkpoint and the audited extractor manifest.
- Development selection uses only the new development file and the thresholds in the approved spec. Final remains closed.

- [ ] Add a distinct dataset encoder and sampler for the single `request_extract` task without changing the existing two-task full-page sampler behavior.
- [ ] Add exact selected-parent verification, tokenizer/model-shape checks, training lineage, CUDA memory/storage preflight, and configurable checkpoint budgets.
- [ ] Train the separate extractor candidate on the RTX 5070 only after storage and CUDA preflight pass; record every run or failure in `logs/LOG_TRAINING.md` and a `RUN-*.txt` record.
- [ ] Evaluate exact field precision/recall, source validity, correction handling, conflict abstention, unsupported-request behavior, and every minimum-size safety bucket using development only.
- [ ] Write `selection.json` only if all frozen gates pass; otherwise leave automatic extraction unpromoted and keep manual editing available.
- [ ] Commit and push as `feat: train source-verified prompt extractor` without committing model/data outputs.

### Task 3: FastAPI Extraction and Exclusive Model Runtime

**Files:**
- Modify: `apps/api/schemas.py`
- Modify: `apps/api/routers/intake.py`
- Modify: `apps/api/services/intake.py`
- Modify: `apps/api/services/runtime.py`
- Modify: `apps/api/routers/health.py`
- Modify: `src/fullpage/intake.py` only for the shared brief-limit constant if needed
- Modify: `docs/api/openapi.json` or the repository's current API contract artifact, if one exists

**Interfaces:**
- `POST /api/v1/intake/extract` accepts `{canonical_format: "prompt-messages-v1", messages: [{id, text}]}` and returns `status`, `message`, `missing_fields`, server-built partial `draft`, source evidence, conflicts, and unsupported requests.
- The endpoint validates message IDs, total character and tokenizer limits, extraction schema, and exact source occurrences before building a draft. It never generates a website.
- `Runtime.get_extractor()` and `Runtime.get_generator()` share `inference_lock`; each switches out the other model before loading its own verified selected bundle.
- Existing `POST /api/v1/intake/validate` and `POST /api/v1/generations` continue to revalidate using `prepare_intake()`.

- [ ] Add versioned Pydantic request/response schemas and document request/response examples in OpenAPI.
- [ ] Add canonical message serialization and deterministic source-span construction with Python and UTF-16 offsets.
- [ ] Add a service that rejects malformed output and resolves correction, setting, and capability mentions conservatively.
- [ ] Add the extraction endpoint with explicit inference-lock handling and controlled `503`, `409`, and input-budget responses.
- [ ] Make runtime health report extractor and generator load state without loading either model.
- [ ] Commit and push as `feat: add safe prompt extraction API`.

### Task 4: Prompt-First Chat and Evidence Review

**Files:**
- Modify: `apps/web/src/components/chat/chat-shell.tsx`
- Modify: `apps/web/src/components/chat/composer.tsx`
- Modify: `apps/web/src/components/chat/message-list.tsx` and the current intake/review message component
- Modify: `apps/web/src/components/forms/business-facts-form.tsx` for the remaining-fields fallback
- Modify: `apps/web/src/lib/api-types.ts`
- Modify: `apps/web/src/lib/api-client.ts`
- Modify: `apps/web/src/lib/chat-state.ts`
- Modify: `apps/web/src/app/globals.css`
- Modify: `apps/web/src/app/page.tsx` only if the empty-session layout needs a dedicated component

**Interfaces:**
- A session sends the full ordered user-message history to `POST /api/v1/intake/extract` with stable message IDs.
- One grouped clarification uses the same composer. After one incomplete answer, the UI exposes only remaining fields in the existing editor.
- A ready response displays editable page type/style, explicit real/fictitious status, every accepted fact, and expandable source evidence before the single `Generate website` action.
- A missing or unpromoted extractor falls back visibly to the manual editor and never implies that the brief was understood.

- [ ] Replace the initial long form with a 4,000-character brief composer and three useful prompt examples.
- [ ] Implement the single clarification cycle and preserve message history, corrections, and source references.
- [ ] Build a compact evidence-backed review with one primary generation action and the existing manual editor as fallback.
- [ ] Apply the approved warm-paper/forest/clay design tokens, IBM Plex type scale, split preview layout, and mobile conversation/preview tabs.
- [ ] Preserve generation preview, code view, source download, ZIP download, session history, and explicit consent before generation.
- [ ] Run the web production build and lint, then inspect desktop and mobile layouts in the browser; correct any material visual or accessibility regression.
- [ ] Commit and push as `feat: simplify prompt-first generator chat`.

### Task 5: Logs, Documentation, and Final Review

**Files:**
- Modify: `README.md`
- Modify: `docs/README.md`
- Modify: `logs/LOG_EKSPERIMEN_DAN_INTERAKSI_LLM.md`
- Modify: `logs/LOG_TRAINING.md` and add unique `logs/RUN-*.txt` records for every training, audit, build, browser review, failure, or rerun

- [ ] Document how extraction is trained, gated, selected, loaded, and safely bypassed when unavailable.
- [ ] Append distinct run and AI interaction records, including the evidence boundary and any failed attempt.
- [ ] Review the full diff for source lineage, sealed-data access, secrets, generated artifact inclusion, and forbidden co-author trailers.
- [ ] Commit and push as `docs: record prompt-first intake implementation`.

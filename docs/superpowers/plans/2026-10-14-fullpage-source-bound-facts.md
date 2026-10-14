# Fullpage Source-Bound Facts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Train and evaluate a new full-page contract that lets MiniGPT choose page structure while the renderer inserts business facts exactly from the validated request.

**Architecture:** Add a versioned PagePlan and SectionDraft contract, a fact resolver that turns references into the existing PageSpec 2.0, and explicit checkpoint-version dispatch that preserves the current v1-v4 path. Prepare train and validation targets from their own frozen families, warm-start from the TRAIN-024 weights-only snapshot with fresh optimizer state, and select only on the existing 80-page development set. Implement prompt intake as a pure request-draft and status protocol. The application UI remains out of scope.

**Tech Stack:** Python 3.11, existing project PyTorch environment, JSON Schema, existing PageSpec 2.0 validator and local HTML/CSS/Tailwind/JavaScript renderer, `unittest`, Jupyter and `nbformat`.

**Spec:** [Source-bound facts design](../specs/2026-10-14-fullpage-source-bound-facts-design.md)

## Global Constraints

- Context stays at 2,048 tokens, with PagePlan output at most 512 tokens and SectionDraft output at most 1,536 tokens.
- Training budget is 3,600 updates with development snapshots at updates 1,800 and 3,600.
- Keep microbatch 8, gradient accumulation 6, effective batch 48, and plan sampling probability 0.7.
- Preserve the remaining TRAIN-024 training and GPU settings: seed 42, BF16, learning rate 5e-5, minimum 5e-6, 180 warmup updates, AdamW betas 0.9/0.95, weight decay 0.1, grad clip 1, SDPA, fused AdamW, TF32, pinned memory, supervised-only logits, allocator segments, GPU telemetry, and 15 GiB disk reserve. Keep the existing 600-update validation/checkpoint cadence and compare generation at 1,800 and 3,600.
- Train only on families assigned to the frozen train split. Keep validation targets validation-only and do not create or consume final targets.
- Mark all generated training examples `human_reviewed=false`.
- Keep the validator strict. Unknown fact IDs, unsupported slots, schema errors, and retry failures must stop export.
- JavaScript comes only from the local renderer catalog. Do not execute free-form model JavaScript.
- Export only after every generation stage and composition check succeeds. Do not leave a partial website export.
- The 76/80 gate measures the frozen synthetic development contract only. Do not present it as visual quality or real-user prompt quality.
- Preserve legacy schemas, prompts, checkpoints, generated artifacts, and final benchmark data.
- For every code, data, notebook, or training command, append its RUN record and the matching AI interaction entry when code or design is changed with an LLM. Stage the new RUN/AI records and canonical progress logs with their related commit. Do not add a `Co-Authored-By` trailer.
- Reserve at least 15 GiB of free disk before dataset creation and training checkpoint writes.
- Do not build or modify the app UI, deployment, backend, authentication, React/Vue support, or browser review in this plan.

## Review Focus

- Missing name, description, or service fact returns `needs_clarification` and produces no export. Pin this in Task 4 intake status cases and Task 3 generation cases.
- A fact source span that does not match its exact prompt substring is rejected, while a value explicitly confirmed by the user is accepted. Pin both cases in Task 4.
- A creative in-scope theme such as a ceramic studio with a space theme reaches `ready`; an explicit backend, external script, or arbitrary-JavaScript requirement returns `unsupported_request`. Pin both cases in Task 4.
- A prompt beyond the existing 1,000-character request limit or the 2,048-token task budget returns `input_too_long` without truncation. Pin both boundaries in Tasks 3 and 4.
- A model response with raw factual copy, unknown references, a bad role-slot pairing, or invalid schema after one retry returns `generation_failed` and creates no website directory. Pin the cases in Tasks 1 through 3.

## File Structure and Responsibilities

- `configs/fullpage/plan-source-bound-v1.schema.json`, `section-source-bound-v1.schema.json`, and `source-bound-copy-v1.json` define the new closed model wire format and the nonfactual copy catalog. Existing schema files stay unchanged.
- `src/fullpage/source_bound_contracts.py`, `source_bound_resolver.py`, and `source_bound_compose.py` validate references, resolve exact request facts, and build the current PageSpec 2.0 consumed by the renderer.
- `src/fullpage/source_bound_prompts.py` and `source_bound_serialization.py` define the new model input and output serialization without changing the prompt hashes used by legacy checkpoints.
- `src/fullpage/intake.py` validates source spans and user-confirmed facts and maps intake/generation outcomes to stable statuses. It does not parse text with an LLM and does not add an application UI.
- `src/fullpage/source_bound_targets.py` creates deterministic versioned training targets from the existing synthetic page curriculum.
- `qa/prepare_fullpage_v5.py`, `qa/configure_fullpage_v5_training.py`, and `qa/select_fullpage_v5.py` prepare immutable data, freeze training lineage/configuration, and choose only between the two development snapshots.
- `qa/train_fullpage.py` and `src/training/engine.py` gain an explicit weights-only initialization path, separate from exact resume, for the approved TRAIN-024 parent.
- `src/fullpage/generation.py` dispatches from checkpoint metadata. Checkpoints without `fullpage_contract_version` keep the legacy path.
- `src/fullpage/lineage.py` validates the approved TRAIN-024 weights-only warm-start and the complete parent chain. The existing INIT-2048-001 initialization rule remains valid for older runs.
- `tests/fullpage/` holds new unit tests. Existing tests and QA commands remain in place.
- `qa/build_fullpage_v5_notebook.py` creates `notebooks/15_fullpage_v5_source_bound_facts.ipynb`, which documents preparation, training, snapshots, development evaluation, and the sealed-final rule.
- `logs/LOG_TRAINING.md`, `logs/LOG_EKSPERIMEN_DAN_INTERAKSI_LLM.md`, `logs/PIPELINE_PROGRESS.md`, and `logs/interaksi_llm/` receive append-only run and interaction records.

**Fixture interfaces shared by the planned tests:** `source_bound_fixture()` returns `(request, copy_catalog, page_plan, navigation_draft)` with three request facts, a complete company-profile plan containing every required role, and one matching navigation reference. `full_source_bound_fixture()` returns `(request, copy_catalog, page_plan, drafts)` with one SectionDraft per descriptor. `synthetic_page_fixture()` calls `make_page(2, 'train', 'plain_css', 'Studio Mapurana')`, discards its composed PageSpec, loads the local copy catalog, and returns `(request, plan, sections, copy_catalog)`. `intake_fixture(prompt, *, include_name=True, evidence='confirmed')` returns `(draft, tokenizer, request_catalog)`; the fake tokenizer exposes `encode(...).ids`, and the catalog has the fixed capability IDs `backend`, `external_script`, and `arbitrary_javascript`. `source_bound_parent_fixture(root: Path)` returns `(parent, config)` for a weights-only parent with run `TRAIN-024`, step 3,600, the current 2,048-token model config, and recorded v4 lineage. `development_candidate(complete, validation_loss, step)` returns a candidate with a generation report and a training report for the same 80 requests, with CE in `training_report.final_validation.loss`. `fake_source_bound_generator(root: Path, *, contract_version: str, model_outputs: list[str])` returns a CPU-only generator with model execution replaced by the supplied serialized outputs.

## Task 1: Define the Versioned Wire Contract

**Files:**

- Create: `configs/fullpage/plan-source-bound-v1.schema.json`
- Create: `configs/fullpage/section-source-bound-v1.schema.json`
- Create: `configs/fullpage/source-bound-copy-v1.json`
- Create: `src/fullpage/source_bound_contracts.py`
- Modify: `src/fullpage/schema_definitions.py`
- Modify: `qa/prepare_fullpage_schemas.py`
- Create: `tests/fullpage/__init__.py`
- Create: `tests/fullpage/fixtures.py`
- Create: `tests/fullpage/test_source_bound_contracts.py`

**Interfaces:**

- `validate_page_plan(plan: dict, request: dict, copy_catalog: dict) -> list[str]`
- `validate_section_draft(draft: dict, descriptor: dict, request: dict, copy_catalog: dict) -> list[str]`
- `build_source_bound_schemas() -> dict[str, dict]` returns only the new versioned schemas. Add an explicit `--contract source-bound-v1` mode to the schema preparation command; its existing default path and artifacts remain unchanged.
- The exact contract version is `source-bound-v1`.
- PagePlan contains `contract_version`, a closed `theme_id` from the versioned catalog, and ordered section descriptors. Each descriptor contains `id`, `type`, `role`, `variant`, `copy_id`, `fact_ids`, and `asset_ids`. It does not contain `title`, `genre`, `style_mode`, or free-form fact text.
- SectionDraft contains `contract_version`, `section_id`, `fact_slots`, and `asset_slots`. Each fact slot contains only `slot_id` and `fact_id`; each asset slot contains only `slot_id` and `asset_id`.
- The versioned catalog defines the allowed theme IDs and their PageSpec 2.0 theme values, and maps each `copy_id` and `slot_id` to an allowed role, component, and PageSpec property. Its literal strings are nonfactual interface copy. Every JSON object is closed with `additionalProperties=false`.
- `source_bound_fixture() -> tuple[dict, dict, dict, dict]` returns `(request, copy_catalog, page_plan, navigation_draft)`. Its request uses name `Studio Mapurana`, one description fact, one service fact, `company_profile`, and `plain_css`.

- [ ] **Step 1: Add a failing closed-contract test.** Use the fixture contract above and assert valid PagePlan and SectionDraft values pass. Add mutations for an unknown `fact_id`, unrecognized `copy_id`, and a `raw_text` property.

```python
class SourceBoundContractTests(unittest.TestCase):
    def test_rejects_unknown_reference_and_free_text(self):
        request, catalog, plan, draft = source_bound_fixture()
        self.assertEqual([], validate_page_plan(plan, request, catalog))
        self.assertEqual([], validate_section_draft(draft, plan['sections'][0], request, catalog))
        bad = copy.deepcopy(draft)
        bad['raw_text'] = 'Studio Mapurana'
        self.assertTrue(validate_section_draft(bad, plan['sections'][0], request, catalog))
```

- [ ] **Step 2: Run the focused test and confirm it fails because the source-bound validators are absent.**

Run: `.\.venv\Scripts\python.exe -m unittest tests.fullpage.test_source_bound_contracts -v`

Expected: the new test module fails before implementation.

- [ ] **Step 3: Implement the schemas and validators.** Add a separate `build_source_bound_schemas` function and an explicit source-bound mode to the schema preparation command. Write only the three new versioned artifacts from that mode. Load them by explicit contract version in `source_bound_contracts.py`. Check request fact IDs, required page roles, role/type/copy compatibility, bounded theme IDs, unique section IDs, asset membership, and reference uniqueness. Do not change or rewrite legacy schema files or their default generation path.

```python
def validate_page_plan(plan, request, copy_catalog):
    errors = schema_errors('plan-source-bound-v1', plan)
    if errors:
        return errors
    return validate_source_bound_references(plan, request, copy_catalog)
```

- [ ] **Step 4: Run focused contract tests.** Add positive coverage for both genres and styles, and negative coverage for unknown facts/assets, duplicate references, unsupported role/type/template combinations, extra fields, and missing required roles.

Run: `.\.venv\Scripts\python.exe -m unittest tests.fullpage.test_source_bound_contracts -v`

Expected: every source-bound contract test passes and legacy schema fixture hashes remain unchanged.

- [ ] **Step 5: Commit and push the contract unit.**

```powershell
git add configs/fullpage src/fullpage/schema_definitions.py src/fullpage/source_bound_contracts.py qa/prepare_fullpage_schemas.py tests/fullpage
git add logs/LOG_EKSPERIMEN_DAN_INTERAKSI_LLM.md logs/PIPELINE_PROGRESS.md logs/RUN-*.txt logs/interaksi_llm/AI-*.md
git commit -m "feat: define source-bound fullpage contracts"
git push origin feature/pipeline-data-model-training
```

## Task 2: Resolve Facts and Compose the Existing PageSpec

**Files:**

- Create: `src/fullpage/source_bound_resolver.py`
- Create: `src/fullpage/source_bound_compose.py`
- Create: `tests/fullpage/test_source_bound_compose.py`
- Reuse: `src/fullpage/contracts.py:validate_composed_page`
- Reuse: `src/fullpage/renderer.py:export_fullpage`

**Interfaces:**

- `resolve_section_draft(request: dict, descriptor: dict, draft: dict, copy_catalog: dict) -> dict`
- `compose_source_bound_page(request: dict, page_plan: dict, drafts: list[dict], copy_catalog: dict) -> dict`
- `build_page_spec_from_request(request: dict, page_plan: dict, sections: list[dict], copy_catalog: dict) -> dict` returns schema 2.0 with request title, genre, style, and fictitious flag, fixed language `id`, the theme value resolved from `theme_id`, resolved sections, and `derive_interactions(sections)`.
- `derive_interactions(sections: list[dict]) -> list[dict]`
- The resolver inserts literal values only from `request.business_facts`; it fills nonfactual strings only from the selected copy catalog. The composer reads title, genre, style, and request-controlled metadata from the validated request, resolves the bounded theme ID through the catalog, and returns a PageSpec 2.0.

- [ ] **Step 1: Add a failing composition test.** Use `source_bound_fixture()` and assert the resolved title, navbar brand, hero name, description, and service card exactly equal their request facts.

```python
class SourceBoundCompositionTests(unittest.TestCase):
    def test_composition_uses_exact_request_facts(self):
        request, catalog, plan, drafts = full_source_bound_fixture()
        page = compose_source_bound_page(request, plan, drafts, catalog)
        self.assertEqual('Studio Mapurana', page['title'])
        self.assertEqual('Studio Mapurana', page['sections'][0]['props']['brand'])
        self.assertEqual([], validate_composed_page(page))
```

- [ ] **Step 2: Run the focused test and confirm the resolver is not implemented.**

Run: `.\.venv\Scripts\python.exe -m unittest tests.fullpage.test_source_bound_compose -v`

Expected: import or assertion failure before implementation.

- [ ] **Step 3: Implement the slot resolver and composer.** Check each slot against the selected template and allowed fact kind. Reject missing, extra, duplicate, unknown, or wrong-role references. Build the final component data and call `validate_composed_page` before returning it.

```python
def compose_source_bound_page(request, page_plan, drafts, copy_catalog):
    sections = [resolve_section_draft(request, descriptor, draft, copy_catalog)
                for descriptor, draft in zip(page_plan['sections'], drafts, strict=True)]
    page = build_page_spec_from_request(request, page_plan, sections, copy_catalog)
    errors = validate_composed_page(page)
    if errors:
        raise ValueError(errors)
    return page
```

- [ ] **Step 4: Run focused composition checks.** Verify unknown fact IDs, duplicate slot IDs, unavailable service facts, missing required roles, and HTML-sensitive fact text. For the last case, render and assert `<script>` supplied inside a fact is escaped in `index.html`.

Run: `.\.venv\Scripts\python.exe -m unittest tests.fullpage.test_source_bound_compose -v`

Expected: every source-bound composition test passes; no test invokes a browser or exports partial output.

- [ ] **Step 5: Commit and push the resolver unit.**

```powershell
git add src/fullpage/source_bound_resolver.py src/fullpage/source_bound_compose.py tests/fullpage/test_source_bound_compose.py
git add logs/LOG_EKSPERIMEN_DAN_INTERAKSI_LLM.md logs/PIPELINE_PROGRESS.md logs/RUN-*.txt logs/interaksi_llm/AI-*.md
git commit -m "feat: resolve fullpage facts from requests"
git push origin feature/pipeline-data-model-training
```

## Task 3: Add Source-Bound Generation with Legacy Dispatch

**Files:**

- Create: `src/fullpage/source_bound_prompts.py`
- Create: `src/fullpage/source_bound_serialization.py`
- Create: `tests/fullpage/test_source_bound_generation.py`
- Modify: `src/fullpage/generation.py`
- Modify: `src/fullpage/evaluation.py`
- Reuse: `src/fullpage/renderer.py:export_fullpage`

**Interfaces:**

- `source_bound_plan_prompt(request: dict) -> str`
- `source_bound_section_prompt(request: dict, page_plan: dict, descriptor: dict) -> str`
- `serialize_source_bound_task(task: str, value: dict) -> str`
- Store `fullpage_contract_version="source-bound-v1"` in new training configuration. A checkpoint without this key uses the existing generator path.
- Keep task names `page_plan` and `section_content` and budgets 512 and 1,536 so the current training dataset and sampler APIs remain usable.
- After validating a PagePlan, build every SectionDraft prompt and check its budget before invoking the model for any SectionDraft. A section prompt overflow returns internal `input_too_long`, writes no website, and runs no section stage.
- Map raw generator results internally as `accepted`, `missing_information`, `input_too_long`, or `stage_failed`. The intake layer maps those to user statuses in Task 4.

- [ ] **Step 1: Add failing tests for version selection and failure containment.** Cover a v5 checkpoint dispatch, a legacy checkpoint fallback, invalid reference after retry, and absence of a `website` directory after failure.

```python
class SourceBoundGenerationTests(unittest.TestCase):
    def test_v5_contract_failure_never_exports_a_website(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            request, _, _, _ = source_bound_fixture()
            generator = fake_source_bound_generator(
                root, contract_version='source-bound-v1',
                model_outputs=['{"contract_version":"source-bound-v1","theme":{},"sections":[]}'] * 2)
            result = generator.generate(request, root / 'out')
            self.assertEqual('stage_failed', result['status'])
            self.assertFalse((root / 'out' / 'website').exists())
            self.assertEqual(2, len(result['attempts']))
```

- [ ] **Step 2: Run focused generation tests and confirm the versioned route is absent.**

Run: `.\.venv\Scripts\python.exe -m unittest tests.fullpage.test_source_bound_generation -v`

Expected: dispatch or behavior assertions fail before implementation.

- [ ] **Step 3: Add versioned generation.** Keep old prompts and serializers unchanged. Add source-bound prompts that ask for schema-shaped IDs only, validate task budgets before model execution, retry once, save both attempts, and compose/export only after all section drafts pass. Render into a unique staging directory and atomically move it to the final website path only after export succeeds; clean the staging directory on renderer failure.

```python
def generate(self, request, output):
    if self.contract_version == 'source-bound-v1':
        return self._generate_source_bound(request, output)
    return self._generate_legacy(request, output)
```

- [ ] **Step 4: Run generation boundary checks.** Verify exact plan and section output budgets, the 1,000-character request boundary, one retry only, old checkpoint fallback, required EOS, no section model call after a section-prompt budget overflow, no final website or staging directory after any stage or renderer failure, and a success report maps to an export generated by the existing renderer.

Run: `.\.venv\Scripts\python.exe -m unittest tests.fullpage.test_source_bound_generation -v`

Expected: both v5 behavior and legacy fallback checks pass.

- [ ] **Step 5: Commit and push the generation unit.**

```powershell
git add src/fullpage/source_bound_prompts.py src/fullpage/source_bound_serialization.py src/fullpage/generation.py src/fullpage/evaluation.py tests/fullpage/test_source_bound_generation.py
git add logs/LOG_EKSPERIMEN_DAN_INTERAKSI_LLM.md logs/PIPELINE_PROGRESS.md logs/RUN-*.txt logs/interaksi_llm/AI-*.md
git commit -m "feat: dispatch source-bound fullpage generation"
git push origin feature/pipeline-data-model-training
```

## Task 4: Add Prompt Intake Evidence and Status Protocol

**Files:**

- Create: `configs/fullpage/request-draft-source-bound-v1.schema.json`
- Create: `configs/fullpage/capability-catalog-v1.json`
- Create: `src/fullpage/intake.py`
- Create: `tests/fullpage/test_source_bound_intake.py`
- No files under `app/` are created or modified.

**Interfaces:**

- `prepare_intake(prompt: str, draft: dict, tokenizer, request_catalog: dict) -> IntakeResult`
- `map_generation_result(report: dict) -> IntakeResult`
- `IntakeResult` contains `status`, a user-safe `message`, `missing_fields`, and `request`; `request` is present only for `ready`.
- `RequestDraft` contains `prompt`, `genre`, `style_mode`, `business_facts`, `requested_features`, `asset_ids`, and `fictitious`. Factual draft values carry either exact source-span evidence or an explicit `user_confirmed=true`. Nested fact strings such as service title and description each carry their own span. The validator compares offsets against the unmodified prompt substring. Unsupported capabilities are explicit, source-backed IDs from the capability catalog; theme adjectives do not count as capability requests.
- Do not add a natural-language extraction model. Missing or ambiguous values require user input. Preserve the original prompt as a nonfactual design brief after facts are validated.
- Exact intake statuses are `needs_clarification`, `unsupported_request`, `input_too_long`, `ready`, `generation_failed`, and `completed`. Map raw generator status `accepted` to `completed`, `missing_information` to `needs_clarification`, `input_too_long` to `input_too_long`, and `stage_failed` to `generation_failed`.
- Apply status precedence in this order: overlength input, explicit unsupported capability, missing or unverified facts, then `ready`. Map a model-side SectionDraft budget overflow to `input_too_long` before any SectionDraft model call.

- [ ] **Step 1: Add failing intake status tests.** Include a missing-fact request, a matching source span, a mismatched source span, a user-confirmed field, a space-themed ceramic company profile, an explicitly requested backend/external script, a prompt over 1,000 characters, and a full request that overflows the plan budget.

```python
class SourceBoundIntakeTests(unittest.TestCase):
    def test_missing_business_name_requests_clarification(self):
        draft, tokenizer, catalog = intake_fixture('Buat company profile studio keramik.', include_name=False)
        result = prepare_intake('Buat company profile studio keramik.', draft, tokenizer, catalog)
        self.assertEqual('needs_clarification', result.status)
        self.assertIsNone(result.request)
```

- [ ] **Step 2: Run focused intake tests and confirm status handling is absent.**

Run: `.\.venv\Scripts\python.exe -m unittest tests.fullpage.test_source_bound_intake -v`

Expected: test imports or assertions fail before implementation.

- [ ] **Step 3: Implement evidence validation and status mapping.** Validate the prompt length and context budget first, then explicit unsupported capability references, then required facts and source spans. Return one clarification listing missing fields; reject only capabilities listed in the capability catalog. Never truncate input or invoke the model for these statuses. A phrase merely describing a creative theme is not an unsupported capability.

```python
if over_character_or_token_budget:
    return IntakeResult('input_too_long', shorten_message(), (), None)
if unsupported_features:
    return IntakeResult('unsupported_request', scope_message(unsupported_features), (), None)
if missing_fields:
    return IntakeResult('needs_clarification', clarification_message(missing_fields), missing_fields, None)
```

- [ ] **Step 4: Run all intake cases.** Verify the space theme reaches `ready` when required facts are confirmed, unsupported capabilities produce no request, mismatched spans are not accepted, input and plan-budget overflow are not truncated, and generation status mapping hides raw errors from the user-safe message.

Run: `.\.venv\Scripts\python.exe -m unittest tests.fullpage.test_source_bound_intake -v`

Expected: every intake status and evidence case passes without an application UI.

- [ ] **Step 5: Commit and push the intake unit.**

```powershell
git add configs/fullpage/request-draft-source-bound-v1.schema.json configs/fullpage/capability-catalog-v1.json src/fullpage/intake.py tests/fullpage/test_source_bound_intake.py
git add logs/LOG_EKSPERIMEN_DAN_INTERAKSI_LLM.md logs/PIPELINE_PROGRESS.md logs/RUN-*.txt logs/interaksi_llm/AI-*.md
git commit -m "feat: validate fullpage prompt intake evidence"
git push origin feature/pipeline-data-model-training
```

## Task 5: Prepare V5 Synthetic Targets Without Split Leakage

**Files:**

- Create: `src/fullpage/source_bound_targets.py`
- Create: `qa/prepare_fullpage_v5.py`
- Create: `tests/fullpage/test_source_bound_data.py`
- Runtime output: `data/processed/fullpage/v5/`
- Runtime report: `reports/fullpage/FULLPAGE-V5_DATA_PREPARATION.json`

**Interfaces:**

- `build_source_bound_targets(request: dict, plan: dict, sections: list[dict], copy_catalog: dict) -> tuple[dict, list[dict]]`
- `build_v5_dataset(root: Path, source_dir: Path, output_dir: Path, *, reserve_bytes: int = 15 * 1024**3) -> dict`
- Build training rows only from the 240 frozen train families. Build validation-only targets from the 40 frozen validation families for ordinary loss calculation. Do not create v5 test targets or parse final request records.
- Continue using `TaskDataset`, the existing two task names, canonical JSON, EOS accounting, and the 2,048-token block size.
- Manifest includes parent v4 manifest hash, source code and schema hashes, train and validation family IDs and counts, task row counts, request hashes, prompt and target token maxima, bytes, disk checks, and `human_reviewed=false`.
- Preserve raw-byte SHA-256 values for `validation.requests.jsonl`, `test.requests.jsonl`, and `test.jsonl` from the v4 manifest before and after preparation. Hash sealed test files as bytes only; never parse their records. The v5 output contains no test rows or copied test records.

- [ ] **Step 1: Add failing target-conversion and leakage tests.** Verify a generated legacy fixture converts to a PagePlan plus SectionDraft targets that contain fact IDs and no literal business fact text. Verify family IDs stay within their source split.

```python
class SourceBoundDataTests(unittest.TestCase):
    def test_targets_reference_facts_without_copying_them(self):
        request, plan, sections, copy_catalog = synthetic_page_fixture()
        page_plan, drafts = build_source_bound_targets(request, plan, sections, copy_catalog)
        serialized = json.dumps([page_plan, drafts], ensure_ascii=False)
        self.assertIn('fact_id', serialized)
        self.assertNotIn('Studio Mapurana', serialized)
```

- [ ] **Step 2: Run focused data tests and confirm the converter is absent.**

Run: `.\.venv\Scripts\python.exe -m unittest tests.fullpage.test_source_bound_data -v`

Expected: import or assertion failure before implementation.

- [ ] **Step 3: Implement deterministic conversion and immutable output.** Regenerate synthetic pages from each frozen request's family index, convert their plan and section facts to references, budget every prompt/target, and write train/validation files plus a manifest into a new directory. Refuse an existing destination or a changed v4 parent manifest.

```python
if output_dir.exists():
    raise FileExistsError('V5 data destination must be new')
if free_bytes < reserve_bytes + estimated_output_bytes:
    raise OSError('Insufficient storage for source-bound dataset')
```

- [ ] **Step 4: Run data-preparation checks on a temporary fixture.** Cover train-only training rows, validation-only validation rows, unchanged parent validation/final request hashes, target and prefix budgets, manifest checksums, and refusal when the destination exists. Patch the fixture's test-file opener to fail if the builder attempts to parse a sealed test record.

Run: `.\.venv\Scripts\python.exe -m unittest tests.fullpage.test_source_bound_data -v`

Expected: fixture preparation passes and final request contents are not loaded by the builder.

- [ ] **Step 5: Commit and push the data-preparation code.** Do not commit generated runtime data or reports.

```powershell
git add src/fullpage/source_bound_targets.py qa/prepare_fullpage_v5.py tests/fullpage/test_source_bound_data.py
git add logs/LOG_EKSPERIMEN_DAN_INTERAKSI_LLM.md logs/PIPELINE_PROGRESS.md logs/RUN-*.txt logs/interaksi_llm/AI-*.md
git commit -m "feat: prepare source-bound fullpage targets"
git push origin feature/pipeline-data-model-training
```

## Task 6: Freeze TRAIN-024 Warm-Start Lineage and V5 Training Config

**Files:**

- Modify: `src/fullpage/lineage.py`
- Modify: `src/fullpage/generation.py`
- Modify: `qa/train_fullpage.py`
- Modify: `src/training/engine.py`
- Modify: `tests/training/test_engine.py`
- Create: `qa/configure_fullpage_v5_training.py`
- Create: `tests/fullpage/test_source_bound_lineage.py`
- Create: `configs/fullpage/training-improvement-v5.json`
- Reuse: `qa/train_fullpage.py` and `qa/snapshot_fullpage_checkpoint.py`

**Interfaces:**

- `validate_source_bound_parent(parent: dict, config: dict, root: Path) -> None`
- `verify_source_bound_lineage(config: dict, root: Path) -> None`
- Config pins `initial_checkpoint.path` and `initial_checkpoint.sha256`. This is weights-only initialization, not exact resume. Exact resume remains the existing `--resume` behavior.
- The only warm-start checkpoint is `checkpoints/FULLPAGE-V4/TRAIN-024-step3600.pt`. Pin its SHA-256 when the config is prepared. Stop if the path, hash, run ID, step 3,600, tokenizer, model shape, or parent lineage differs.
- For this explicit v5 initialization, load weights only. Create optimizer, scheduler, sampler, and RNG from the new configuration and seed. Preserve the existing INIT-2048-001 rule for legacy configurations.
- With no `resume` argument, `run_training` loads the configured source model state before creating the fresh optimizer and scheduler, requires `weights_only=true` and matching model config, starts at step 0, and records the initialization SHA in the run report. With `resume`, it skips weight initialization and restores the saved run state as it does today.
- The v5 training config pins dataset and source hashes, contract version, copy catalog, context/budgets, plan probability 0.7, batch 8, accumulation 6, effective batch 48, 3,600 updates, and evaluations/checkpoints at 1,800 and 3,600.

- [ ] **Step 1: Add failing lineage and initializer tests.** Verify a valid TRAIN-024 weights-only snapshot is accepted only for `source-bound-v1`; wrong parent run ID, wrong step, changed hash, changed model config, or a full training checkpoint are rejected. Verify initialization loads model weights but starts at step 0 with fresh optimizer, scheduler, sampler, and RNG. Verify exact resume restores its saved states and a legacy INIT-2048-001 parent still follows the existing path.

```python
class SourceBoundLineageTests(unittest.TestCase):
    def test_wrong_train024_parent_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            parent, config = source_bound_parent_fixture(Path(tmp))
            parent['run_id'] = 'TRAIN-022'
            with self.assertRaises(ValueError):
                validate_source_bound_parent(parent, config, Path(tmp))
```

- [ ] **Step 2: Run focused lineage tests and confirm the trained parent is rejected by the current v4-only rule.**

Run: `.\.venv\Scripts\python.exe -m unittest tests.fullpage.test_source_bound_lineage -v`

Expected: the new warm-start tests fail before implementation; legacy lineage checks remain unchanged.

- [ ] **Step 3: Add the explicit warm-start path.** Validate the frozen v4 parent and recurse to its approved initialization ancestry. Record the parent snapshot SHA and parent lineage in the v5 config. Add the weights-only initialization hook to `qa/train_fullpage.py` and `src/training/engine.py`, before optimizer/scheduler construction and separate from exact resume. Keep old checkpoint fallback and schema verification exact.

```python
if config.get('fullpage_contract_version') == 'source-bound-v1':
    validate_source_bound_parent(parent, config, root)
else:
    validate_fullpage_parent(parent, config, root)
```

- [ ] **Step 4: Run lineage and configuration checks.** Assert initialization begins at step zero with fresh optimizer/scheduler/sampler/RNG state, exact resume still restores its states, verifies every v5 schema and prompt/composer hash, and refuses a changed parent or dataset manifest before CUDA training starts.

Run: `.\.venv\Scripts\python.exe -m unittest tests.fullpage.test_source_bound_lineage -v`

Expected: v5 warm-start acceptance and legacy rejection boundaries pass.

- [ ] **Step 5: Commit and push the lineage/config unit.**

```powershell
git add src/fullpage/lineage.py src/fullpage/generation.py qa/train_fullpage.py src/training/engine.py qa/configure_fullpage_v5_training.py tests/training/test_engine.py tests/fullpage/test_source_bound_lineage.py configs/fullpage/training-improvement-v5.json
git add logs/LOG_EKSPERIMEN_DAN_INTERAKSI_LLM.md logs/PIPELINE_PROGRESS.md logs/RUN-*.txt logs/interaksi_llm/AI-*.md
git commit -m "feat: pin source-bound fullpage training lineage"
git push origin feature/pipeline-data-model-training
```

## Task 7: Evaluate Both Snapshots and Enforce the Development Gate

**Files:**

- Create: `qa/select_fullpage_v5.py`
- Create: `tests/fullpage/test_source_bound_selection.py`
- Runtime reports: `reports/fullpage/FULLPAGE-V5_DEVELOPMENT_STEP1800.json` and `FULLPAGE-V5_DEVELOPMENT_STEP3600.json`
- Runtime snapshots: `checkpoints/FULLPAGE-V5/TRAIN-025-step1800.pt` and `TRAIN-026-step3600.pt`
- Reuse: `qa/evaluate_fullpage.py --scope development --dataset-dir data/processed/fullpage/v4`

**Interfaces:**

- `select_v5_candidate(candidates: list[dict]) -> dict`
- Each candidate pairs one generation development report with its training report. Read CE from `training_report.final_validation.loss`; read complete pages, role counts, and exact fact acceptance from the generation report.
- `development_candidate(complete, validation_loss, step)` creates `{step, generation_report, training_report}`. The generation report includes `total=80`, `complete`, `model_gate`, and `accepted_facts_links_assets_valid`; the training report includes `final_validation.loss`.
- Compare the same 80 frozen development requests at steps 1,800 and 3,600. Rank first by complete pages, then by ordinary development cross entropy. Selection passes only at 76/80 or higher and with exact fact references accepted for every exported page.
- CLI: `python -m qa.select_fullpage_v5 --step1800-report reports/fullpage/FULLPAGE-V5_DEVELOPMENT_STEP1800.json --step1800-training reports/training/TRAIN-025.json --step3600-report reports/fullpage/FULLPAGE-V5_DEVELOPMENT_STEP3600.json --step3600-training reports/training/TRAIN-026.json --output reports/fullpage/FULLPAGE-V5_DEVELOPMENT_SELECTION.json`.
- Do not call `claim_final_evaluation`, `lock_fullpage_candidate`, `--scope final`, or read final request records.

- [ ] **Step 1: Add failing selection tests.** Test step 1,800 wins when it has more complete pages, lower CE wins only on a page-count tie, and no candidate passes below 76/80.

```python
class SourceBoundSelectionTests(unittest.TestCase):
    def test_gate_requires_76_of_80(self):
        candidates = [development_candidate(75, 1.2, 1800), development_candidate(74, 0.8, 3600)]
        result = select_v5_candidate(candidates)
        self.assertFalse(result['model_gate_passed'])
        self.assertEqual(75, result['selected']['generation_report']['complete'])
```

- [ ] **Step 2: Run the focused selection test and confirm the selector is absent.**

Run: `.\.venv\Scripts\python.exe -m unittest tests.fullpage.test_source_bound_selection -v`

Expected: test import fails before implementation.

- [ ] **Step 3: Implement a development-only selector.** Require matching request and manifest hashes, exact step IDs, total 80, valid fact-reference reports, and available CE metrics. Write a report declaring `final_used=false` and list the winning rule and both candidate summaries.

```python
chosen = max(candidates, key=lambda item: (
    item['generation_report']['complete'],
    -item['training_report']['final_validation']['loss']))
selected = {'step': chosen['step'],
            'complete': chosen['generation_report']['complete'],
            'development_ce': chosen['training_report']['final_validation']['loss'],
            'generation_report': chosen['generation_report']}
passed = (chosen['generation_report']['complete'] >= 76
          and chosen['generation_report']['model_gate']
          and chosen['generation_report']['accepted_facts_links_assets_valid'])
```

- [ ] **Step 4: Run selection checks and compare the two actual development snapshots after training.** Use the unchanged validation request file and write separate attempt directories and reports. If the gate fails, report the shortfall and stop model selection. Do not loosen validators or open final.

Run: `.\.venv\Scripts\python.exe -m unittest tests.fullpage.test_source_bound_selection -v`

Expected: selection unit tests pass. The actual reports show 80 requests each and the explicit gate result.

- [ ] **Step 5: Commit and push the selector.** Keep generated reports and model snapshots as runtime artifacts unless the repository's artifact policy says otherwise.

```powershell
git add qa/select_fullpage_v5.py tests/fullpage/test_source_bound_selection.py
git add logs/LOG_EKSPERIMEN_DAN_INTERAKSI_LLM.md logs/PIPELINE_PROGRESS.md logs/RUN-*.txt logs/interaksi_llm/AI-*.md
git commit -m "feat: select source-bound model on development gate"
git push origin feature/pipeline-data-model-training
```

## Task 8: Build the Reproducible Training Notebook

**Files:**

- Create: `qa/build_fullpage_v5_notebook.py`
- Create: `notebooks/15_fullpage_v5_source_bound_facts.ipynb`
- Create: `tests/fullpage/test_source_bound_notebook.py`

**Interfaces:**

- `build_notebook(output_path: Path) -> nbformat.NotebookNode`
- Notebook records the source-bound contract, synthetic-data disclosure, fixed family splits, and 76/80 development gate.
- Cells show v4 parent and split hashes, v5 data-preparation report, task/family counts, token budgets, storage preflight, and the pinned training config.
- Separate cells show preparation/configuration, TRAIN-025 through step 1,800, snapshot/evaluation, exact TRAIN-026 resume through step 3,600, snapshot/evaluation, and candidate selection. Building the notebook does not run these cells or start training.
- Result cells read only the two development reports and training summaries, show per-genre/style counts, first-attempt acceptance, retry, CE, and selected checkpoint, and set `final_used=false`. No cell reads or evaluates final request records.

- [ ] **Step 1: Add a failing notebook builder test.** Assert the expected section labels and command cells exist and no code cell references the final evaluation scope or opens a sealed test file.

```python
class SourceBoundNotebookTests(unittest.TestCase):
    def test_notebook_explains_both_development_steps_and_seals_final(self):
        with tempfile.TemporaryDirectory() as tmp:
            nb = build_notebook(Path(tmp) / 'notebook.ipynb')
        nbformat.validate(nb)
        code = '\n'.join(''.join(cell.source) for cell in nb.cells if cell.cell_type == 'code').lower()
        self.assertIn('train-025', code)
        self.assertIn('train-026', code)
        self.assertNotIn('--scope final', code)
        self.assertNotIn('test.requests.jsonl', code)
```

- [ ] **Step 2: Run the focused notebook test and confirm the builder is absent.**

Run: `.\.venv\Scripts\python.exe -m unittest tests.fullpage.test_source_bound_notebook -v`

Expected: the test module fails before the builder is implemented.

- [ ] **Step 3: Implement the notebook builder and explicit non-executing cells.** Use documented project paths, separate shell commands into distinct code cells, state expected artifact paths, and make result cells skip cleanly until reports exist. Validate with `nbformat.validate` before writing.

- [ ] **Step 4: Run the builder and notebook structure check.** Do not execute any training or final-evaluation cell.

Run: `.\.venv\Scripts\python.exe -m qa.build_fullpage_v5_notebook`

Expected: notebook 15 is written, passes `nbformat.validate`, contains each planned stage, and has no code that accesses final records.

- [ ] **Step 5: Commit and push the notebook builder and notebook.**

```powershell
git add qa/build_fullpage_v5_notebook.py notebooks/15_fullpage_v5_source_bound_facts.ipynb tests/fullpage/test_source_bound_notebook.py
git add logs/LOG_EKSPERIMEN_DAN_INTERAKSI_LLM.md logs/PIPELINE_PROGRESS.md logs/RUN-*.txt logs/interaksi_llm/AI-*.md
git commit -m "docs: add source-bound fullpage training notebook"
git push origin feature/pipeline-data-model-training
```

## Task 9: Prepare and Run TRAIN-025 Through Update 1,800

**Runtime artifacts:**

- Dataset: `data/processed/fullpage/v5/`
- Config: `configs/fullpage/training-improvement-v5.json`
- Training report: `reports/training/TRAIN-025.json`
- Snapshot and development report: `checkpoints/FULLPAGE-V5/TRAIN-025-step1800.pt` and `reports/fullpage/FULLPAGE-V5_DEVELOPMENT_STEP1800.json`
- Append: `logs/LOG_TRAINING.md`, `logs/PIPELINE_PROGRESS.md`, `logs/LOG_EKSPERIMEN_DAN_INTERAKSI_LLM.md`, and one RUN record per preparation, preflight, config, training, snapshot, and evaluation command

- [ ] **Step 1: Run data preparation and freeze the config.** Confirm the output destination does not exist, reserve at least 15 GiB, and capture immutable source and manifest hashes. If any preflight fails, write a RUN record and stop before training.

```powershell
.\.venv\Scripts\python.exe qa/check_gpu_environment.py
.\.venv\Scripts\python.exe -m qa.prepare_fullpage_v5
.\.venv\Scripts\python.exe -m qa.configure_fullpage_v5_training --parent-checkpoint checkpoints/FULLPAGE-V4/TRAIN-024-step3600.pt --output configs/fullpage/training-improvement-v5.json
```

- [ ] **Step 2: Verify preparation and configuration.** Confirm the TRAIN-024 SHA, lineage, model configuration, tokenizer, schema, prompt, source, dataset manifest, output budgets, split counts, sealed final hashes, and disk reserve. Append each command result, including failures, as a new RUN record.

- [ ] **Step 3: Start TRAIN-025 from weights only and stop at step 1,800.** Use the frozen config. Load only pinned TRAIN-024 model weights and create fresh optimizer, scheduler, sampler, and RNG state. Do not pass `--resume` for this first run.

```powershell
.\.venv\Scripts\python.exe -m qa.train_fullpage --config configs/fullpage/training-improvement-v5.json --run-id TRAIN-025 --stop-after 1800
```

- [ ] **Step 4: Snapshot and evaluate TRAIN-025 against the unchanged 80 development requests.** Require checkpoint metadata `run_id=TRAIN-025` and `global_step=1800`. Use a new attempt directory and append a RUN record for each command.

```powershell
.\.venv\Scripts\python.exe -m qa.snapshot_fullpage_checkpoint --source checkpoints/TRAIN-025/last.pt --destination checkpoints/FULLPAGE-V5/TRAIN-025-step1800.pt --run-id TRAIN-025 --step 1800
.\.venv\Scripts\python.exe -m qa.evaluate_fullpage --scope development --dataset-dir data/processed/fullpage/v4 --checkpoint checkpoints/FULLPAGE-V5/TRAIN-025-step1800.pt --output outputs/fullpage/TRAIN-025-development-step1800 --report reports/fullpage/FULLPAGE-V5_DEVELOPMENT_STEP1800.json
```

- [ ] **Step 5: Record training status and commit/push code and logs.** Keep generated model/data artifacts out of Git unless the established artifact policy includes them. Label results as synthetic development evidence, not final or visual-quality evidence.

```powershell
git add logs/LOG_TRAINING.md logs/PIPELINE_PROGRESS.md logs/LOG_EKSPERIMEN_DAN_INTERAKSI_LLM.md logs/RUN-*.txt
git commit -m "docs: record source-bound training step 1800"
git push origin feature/pipeline-data-model-training
```

## Task 10: Resume TRAIN-026, Evaluate, and Select on Development Only

**Runtime artifacts:**

- Training report: `reports/training/TRAIN-026.json`
- Snapshot and development report: `checkpoints/FULLPAGE-V5/TRAIN-026-step3600.pt` and `reports/fullpage/FULLPAGE-V5_DEVELOPMENT_STEP3600.json`
- Selection report: `reports/fullpage/FULLPAGE-V5_DEVELOPMENT_SELECTION.json`
- Append: `logs/LOG_TRAINING.md`, `logs/PIPELINE_PROGRESS.md`, `logs/LOG_EKSPERIMEN_DAN_INTERAKSI_LLM.md`, and a new RUN record for resume, snapshot, evaluation, and selection

- [ ] **Step 1: Resume exact state as TRAIN-026 through update 3,600.** Use the same immutable v5 config and resume from `checkpoints/TRAIN-025/last.pt`. Do not initialize again from TRAIN-024. Preserve optimizer, scheduler, sampler, and RNG state. Record failures and interruptions in new RUN entries.

```powershell
.\.venv\Scripts\python.exe -m qa.train_fullpage --config configs/fullpage/training-improvement-v5.json --run-id TRAIN-026 --resume checkpoints/TRAIN-025/last.pt
```

- [ ] **Step 2: Snapshot and evaluate TRAIN-026 on the same 80 development requests.** Require `run_id=TRAIN-026` and `global_step=3600`, keep a distinct output directory, and append a RUN record for each command.

```powershell
.\.venv\Scripts\python.exe -m qa.snapshot_fullpage_checkpoint --source checkpoints/TRAIN-026/last.pt --destination checkpoints/FULLPAGE-V5/TRAIN-026-step3600.pt --run-id TRAIN-026 --step 3600
.\.venv\Scripts\python.exe -m qa.evaluate_fullpage --scope development --dataset-dir data/processed/fullpage/v4 --checkpoint checkpoints/FULLPAGE-V5/TRAIN-026-step3600.pt --output outputs/fullpage/TRAIN-026-development-step3600 --report reports/fullpage/FULLPAGE-V5_DEVELOPMENT_STEP3600.json
```

- [ ] **Step 3: Select between the two development candidates.** Require matching request and manifest hashes, rank complete pages first and CE only on a tie, and require exact fact-reference validity plus 76/80 to pass. Do not relax validation or open final.

```powershell
.\.venv\Scripts\python.exe -m qa.select_fullpage_v5 --step1800-report reports/fullpage/FULLPAGE-V5_DEVELOPMENT_STEP1800.json --step1800-training reports/training/TRAIN-025.json --step3600-report reports/fullpage/FULLPAGE-V5_DEVELOPMENT_STEP3600.json --step3600-training reports/training/TRAIN-026.json --output reports/fullpage/FULLPAGE-V5_DEVELOPMENT_SELECTION.json
```

- [ ] **Step 4: Record the gate and commit/push code and logs.** If neither candidate reaches 76/80, record the shortfall and stop model selection for a revised plan. Keep final closed.

```powershell
git add logs/LOG_TRAINING.md logs/PIPELINE_PROGRESS.md logs/LOG_EKSPERIMEN_DAN_INTERAKSI_LLM.md logs/RUN-*.txt
git commit -m "docs: record source-bound training step 3600"
git push origin feature/pipeline-data-model-training
```

- [ ] **Step 5: Rebuild notebook 15 from the available reports.** Regenerate its evidence cells after both development reports and selection summary exist. Do not execute its training or final-evaluation cells.

```powershell
.\.venv\Scripts\python.exe -m qa.build_fullpage_v5_notebook
git add notebooks/15_fullpage_v5_source_bound_facts.ipynb logs/LOG_TRAINING.md logs/PIPELINE_PROGRESS.md logs/LOG_EKSPERIMEN_DAN_INTERAKSI_LLM.md logs/RUN-*.txt
git commit -m "docs: record source-bound development selection"
git push origin feature/pipeline-data-model-training
```

Keep all training/checkpoint outputs in their runtime locations.

## Completion Evidence

- The new source-bound schemas reject free-form factual output and every unknown or incompatible reference.
- The resolver emits a valid PageSpec 2.0 whose factual values exactly match request facts. Existing renderer output contains no model-provided JavaScript.
- Legacy checkpoint dispatch still follows the legacy path. The v5 checkpoint verifies source, schema, prompt, data, and TRAIN-024 parent lineage.
- Dataset manifest proves train-only training rows, validation-only validation rows, unchanged frozen request hashes, exact token bounds, and `human_reviewed=false`.
- Notebook 15 is valid and presents all experiment stages without opening the final benchmark.
- Both development reports contain the same frozen 80 requests. Candidate selection uses complete-page count then CE and passes only at 76/80 or higher.
- Training logs include each run, resume, snapshot, evaluation, and failure. No claim of visual quality, human approval, or real-user prompt readiness is made from the development gate.

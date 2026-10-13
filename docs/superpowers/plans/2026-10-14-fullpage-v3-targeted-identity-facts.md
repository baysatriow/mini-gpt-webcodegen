# Full-page V3 Targeted Identity and Facts Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to implement this plan task by task. Tasks use checkbox syntax for tracking.

**Goal:** Improve complete landing page and company profile generation by teaching the existing Mini GPT to copy page identity exactly and use only supplied structured facts.

**Architecture:** Keep the PageSpec stages, renderer, schemas, and strict validator unchanged. Strengthen the shared model prompts, add reproducible synthetic examples from existing train families only, train fresh from INIT2048, and rank the 1,800 and 3,600 update snapshots on the frozen 80-request development set.

**Tech Stack:** Python 3.11, PyTorch 2.14.1 with CUDA 13, RTX 5070, byte-level BPE tokenizer, existing PageSpec pipeline, Jupyter Notebook.

**Spec:** The user asked to continue model development after the v2 result of 70/80 development pages. This plan uses the proposed v3 focus on exact names and supported facts. The user then asked to initialize CodeGraph before continuing; the local index is active and ignored by Git.

## Global Constraints

- Keep model context at 2,048 tokens, plan output budget at 512 tokens, and section output budget at 1,536 tokens.
- Keep plan batch probability at 0.70, effective batch at 48 if the v3 profile confirms stability, and total training budget at 3,600 updates.
- Initialize the v3 model from `checkpoints/INIT-2048-001/initial.pt`; do not resume TRAIN-019.
- Preserve the existing schema, strict identity and fact validators, renderer, and retry behavior.
- Require at least 76/80 complete development pages and at least 76/80 required-role coverage for the 95% gate.
- Keep `human_reviewed` false. Do not read, parse, evaluate, or select on final request targets during v3.
- Preserve all prior run artifacts. Keep at least 15 GiB free on F: and the existing 1.5 GiB full-page phase artifact cap.
- Append RUN and AI records, create an executed notebook, commit and push coherent changes, and omit `Co-Authored-By`.
- Do not add or run unit tests. Use existing schema, fact, lineage, GPU, and development evaluation gates.

## Review Focus

- Plan title, genre, and style must exactly match the current request; checked by `validate_plan_wire`.
- Navbar brand must exactly match the supplied name; checked by `validate_section`.
- FAQ, service, and portfolio entries must match supplied facts and contain no unprovided items; checked by `fact_errors` during `compose_page`.
- New synthetic identities must remain inside existing train families and stay distinct from development names; enforced by the v3 preparation manifest.
- The final split must remain unopened; enforced by copied file hashes and absence of `data/evaluation/fullpage/final_consumption.json`.

---

### Task 1: Strengthen prompts and prepare immutable v3 training data

**Files:**
- Modify: `src/fullpage/prompts.py`
- Create: `qa/prepare_fullpage_v3.py`
- Create by command: `data/processed/fullpage/v3/manifest.json` and v3 JSONL files, locally ignored by Git
- Create by command: `reports/data/FULLPAGE_CURRICULUM_V3.json`

**Interfaces:**
- `plan_prompt(request)` adds a concise instruction to copy the request name, genre, and style exactly.
- `section_prompt(request, plan, descriptor)` adds concise instructions to use only supplied facts and preserve the exact name in identity-bearing sections.
- `qa.prepare_fullpage_v3` copies v2 files, then creates two new three-word aliases for each of 240 train families in both styles. It creates 960 full-page records and six targeted tasks per record: plan, navigation, hero, services, FAQ or portfolio, and footer.

- [x] Validate every new request, plan, section, composed page, output budget, and tokenizer length with existing project functions before writing the final manifest.
- [x] Assert exactly 240 existing train families, 960 new train requests, 5,760 new task rows, and unchanged validation and test file hashes. Copy final files byte-for-byte without parsing their contents.
- [x] Run `.venv/Scripts/python.exe -m qa.run_logged --label 'Prepare fullpage v3 train-only data' -- .venv/Scripts/python.exe -m qa.prepare_fullpage_v3 --source data/processed/fullpage/v2 --output data/processed/fullpage/v3 --report reports/data/FULLPAGE_CURRICULUM_V3.json`.
- [x] Inspect the manifest and verify `human_reviewed` is false, family count is unchanged, development requests remain the frozen 80, and final targets were not read.

### Task 2: Profile v3 and freeze training configuration

**Files:**
- Create by command: `reports/training/FULLPAGE-GPU-004.json`
- Create by command: `configs/fullpage/training-improvement-v3.json`

**Interfaces:**
- Reuse `qa.profile_fullpage_training` with the actual v3 dataset and 0.70 plan probability.
- Reuse `qa.configure_fullpage_training` to bind the selected batch, INIT2048 lineage, dataset manifest hash, and current prompt source hash.

- [x] Run `.venv/Scripts/python.exe -m qa.run_logged --label 'Profile fullpage v3 GPU batch' -- .venv/Scripts/python.exe -m qa.profile_fullpage_training --report-id FULLPAGE-GPU-004 --dataset-dir data/processed/fullpage/v3 --plan-probability 0.7`.
- [x] Require stable CUDA profiling at the selected batch and at least 512 MiB free device memory after the measured update.
- [x] Freeze main scope, 3,600 updates, 180 warmup updates, checkpoint and validation intervals of 600, BF16, SDPA, fused AdamW, TF32, 0.70 plan probability, and storage phase `fullpage-improvement-v3`.
- [x] Check F: storage before training. If free space is below the checkpoint reserve, archive TRAIN-005, TRAIN-006, and TRAIN-007 to E: with hash verification and path-preserving junctions. Keep at least 15 GiB free.

### Task 3: Train and preserve the two declared snapshots

**Files:**
- Create locally: `checkpoints/TRAIN-020/`, `checkpoints/TRAIN-021/`
- Create by command: `reports/training/TRAIN-020.json`, `reports/training/TRAIN-021.json`

- [x] Run TRAIN-020 from INIT2048 through global update 1,800 using `qa.train_fullpage --config configs/fullpage/training-improvement-v3.json --run-id TRAIN-020 --stop-after 1800`.
- [x] Save an immutable weights-only snapshot at update 1,800 and record its SHA-256.
- [x] Resume TRAIN-021 exactly from `checkpoints/TRAIN-020/last.pt` with the identical config, sampler state, optimizer, scheduler, and RNG through update 3,600.
- [x] Save an immutable weights-only snapshot at update 3,600 and record its SHA-256. Preserve the 15 GiB free-space reserve and phase artifact cap.

### Task 4: Evaluate and select on development only

**Files:**
- Create: `qa/select_fullpage_v3.py`
- Create by command: `reports/fullpage/TRAIN-020_DEVELOPMENT.json`
- Create by command: `reports/fullpage/TRAIN-021_DEVELOPMENT.json`
- Create by command: `reports/fullpage/AI-020_DEVELOPMENT_SELECTION.json`

- [x] Evaluate each snapshot against the identical frozen 80-request v3 validation file with the unchanged strict renderer and validator.
- [x] Verify each report binds checkpoint hash, config hash, manifest hash, prompt and renderer source hashes, and confirms `final_used` is false.
- [x] Select by complete-page count, required-role coverage, first-attempt completeness, ordinary validation CE, then earlier step.
- [x] The 95% gate did not pass, so no candidate was locked. The final set remained unopened and unevaluated.

### Task 5: Publish experiment record and notebook

**Files:**
- Create: `notebooks/13_fullpage_v3_targeted_training.ipynb`
- Modify: `logs/LOG_TRAINING.md`
- Modify: `logs/LOG_EKSPERIMEN_DAN_INTERAKSI_LLM.md`
- Create: `logs/interaksi_llm/AI-020_2026-10-14.md`
- Modify: `logs/PIPELINE_PROGRESS.md`

- [x] Record the exact prompt/data changes, source and manifest hashes, GPU profile, training lineage, per-run metrics, development counts, storage actions, and final-closed state.
- [x] Execute the notebook so it displays the v3 manifest, profile, training summaries, development comparison, and failure categories from saved reports.
- [x] Run `git diff --check`, verify the CodeGraph index is current, verify final remains unopened, then commit and push without `Co-Authored-By`.

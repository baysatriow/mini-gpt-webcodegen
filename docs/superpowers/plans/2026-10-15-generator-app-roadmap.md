# Local Website Generator App Roadmap

> **For agentic workers:** Follow the three linked implementation plans in order. Do not start implementation until the user approves this plan package. Each subplan has its own scope and file list.

**Goal:** Deliver a local chat application that turns confirmed business facts into a validated landing page or company profile, then offers a safe preview and downloadable source files.

**Architecture:** First package the selected TRAIN-025 model and its development output without moving canonical artifacts. Next expose the existing source-bound pipeline through a local FastAPI adapter. Then build the Next.js and shadcn chat interface against that API contract. The renderer remains responsible for producing website files.

**Tech Stack:** Existing PyTorch CUDA project environment, Python, FastAPI, OpenAPI, Next.js App Router, TypeScript, shadcn/ui, Tailwind CSS for the application UI, existing HTML/CSS/Tailwind renderer, browser `localStorage`.

**Spec:** `docs/superpowers/specs/2026-10-15-generator-chat-application-design.md`

## Global Constraints

- Supported page types are `landing_page` and `company_profile`.
- Supported generated page styles are `plain_css` and `tailwind`.
- Collect missing facts explicitly and never invent facts from free-form prompts.
- The model selects plans and validated fact or asset references; the local renderer creates HTML, CSS, JavaScript, and copy from its catalogs.
- Run intake validation before generation and validate again in the API before loading the model.
- Load TRAIN-025 lazily only for an explicit generation request.
- Keep model and output copies under `training/selected/fullpage-v5` ignored by Git. Keep canonical artifacts in their existing paths.
- Keep generation output under `outputs/webapp/generations`; never overwrite an existing generation folder.
- Use JSON requests and responses. Do not present token streaming or stage progress that the API does not provide.
- Bind FastAPI to loopback, allow only configured local web origins, and use one worker with one active generation.
- Store chat history in the user's browser. Do not add a database, account system, public deployment, or cloud model provider.
- Preview accepted output in a sandboxed iframe without `allow-same-origin`. Expose only allowlisted generated source and assets.
- Keep test data and final data closed. Do not run training or application inference during implementation under this plan.
- Do not add or run tests or build verification unless the user later asks for testing or verification.
- Append project log records for code work and every artifact-producing command. Commit and push each completed change on `feature/pipeline-data-model-training` without a `Co-Authored-By` trailer.
- Resolve and lock supported dependency versions during implementation using the official documentation, without changing the existing PyTorch CUDA version.

## Review Focus

- A request is missing one required fact or has an unsupported genre or style. The intake response must ask for the missing field or explain the supported scope without loading the model or creating a page. Review in the FastAPI plan.
- A prompt asks for backend execution, external scripts, or arbitrary JavaScript. Intake must return unsupported scope without loading the model. Review in the FastAPI and UI plans.
- A fact is typed into a guided form and is absent from the original prompt. The draft must record explicit user confirmation for that value. Review in the Next.js plan.
- The selected checkpoint is a pointer into a `.versions` payload. The package must preserve the pointer, payload, manifest, and verified digest together. Review in the selected-bundle plan.
- Generation fails after one or more model stages. The browser must not expose partial HTML, code tabs, or ZIP downloads. Review in the API and UI plans.
- A browser requests a made-up generation ID or a path-like value. The API must reject it without reading outside the selected generation directory. Review in the API plan.

## Plan Order

| Order | Plan | Deliverable | Depends on |
| --- | --- | --- | --- |
| 1 | `2026-10-15-train-025-selected-bundle.md` | Tracked provenance manifest and documentation plus local ignored checkpoint and development-output copies | Approved application specification |
| 2 | `2026-10-15-fastapi-generator-api.md` | Local FastAPI adapter, typed OpenAPI contract, safe preview and download routes | Selected bundle and approved application specification |
| 3 | `2026-10-15-nextjs-generator-chat-ui.md` | Chat, inline clarification, local history, preview, code tabs, and downloads | FastAPI contract and approved application specification |

## Execution Boundary

The plan package is ready for review. Its approval is the gate before any implementation. The user previously specified that the Sol model should implement after planning; retain that direction. No training, test/final access, test runs, build checks, or inference requests are part of this planning step.

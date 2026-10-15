# Next.js Website Generator Chat UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Build the local Indonesian chat interface for guided website requests, explicit fact confirmation, generated-page preview, code inspection, and downloads.

**Architecture:** The browser uses typed fetch calls to the local FastAPI JSON API. A reducer owns conversation and generation state, while `localStorage` stores local chat history. Guided form data becomes a source-bound `RequestDraft`; the model is never asked to fill missing facts from a prompt.

**Tech Stack:** Next.js App Router, TypeScript, shadcn/ui, Tailwind CSS for the application shell, React state, browser `localStorage`, FastAPI JSON/OpenAPI contract.

**Spec:** `docs/superpowers/specs/2026-10-15-generator-chat-application-design.md`

## Global Constraints

- Keep page choices to `landing_page` and `company_profile`, with `plain_css` and `tailwind` styles.
- Use guided inline clarification, explicit review, and a separate user action before generation.
- Do not infer business name, description, service, price, testimonial, or other factual content without source evidence or explicit user confirmation.
- Send JSON to FastAPI. Do not use an AI Gateway, cloud model provider, or token streaming.
- Persist only local chat state and generation references in browser `localStorage`.
- Show generated output only after the API returns `completed`.
- Use an iframe sandbox without `allow-same-origin` for accepted preview.
- Fetch source from the API and show only `index.html`, `styles.css`, and `app.js`; download ZIP from the API.
- Keep API origin in one environment variable and report service errors in Indonesian without exposing tracebacks.
- Do not add or run tests, builds, or inference under the current request. Record artifact-producing install commands as RUN entries.
- Commit and push each completed change on `feature/pipeline-data-model-training` without a `Co-Authored-By` trailer.

## Proposed Visual Direction

The product is a local website-building workbench for Indonesian creators and students. Keep the page understandable as a workspace, not a marketing landing page for an unrelated SaaS.

**Color tokens:**

| Token | Hex | Use |
| --- | --- | --- |
| Frost canvas | `#F2F5F9` | Main workspace background |
| Paper surface | `#FFFFFF` | Conversation and preview surfaces |
| Harbor ink | `#1E2D45` | Main text and navigation |
| Slate note | `#60718B` | Secondary descriptions and quiet controls |
| Cobalt action | `#2463EB` | Primary actions, selection, and active preview tab |
| Verified teal | `#0C806F` | User-confirmed facts and accepted generation state |

**Typography:** IBM Plex Sans for product text and IBM Plex Mono for generated source. Use sentence case with these sizes: page title 28/36 px, section title 20/28 px, composer and body 15/24 px, and secondary labels 13/18 px. Keep conversation lines under 80 characters. Code stays monospace and visually distinct from chat.

**Layout option A, selected:** a narrow history rail, a focused conversation column, and a larger preview canvas. Keep text left aligned and the composer anchored at the bottom of the conversation. Once a page is accepted, the canvas keeps its desktop/mobile controls and source tabs beside the conversation. On small screens, history becomes a drawer and conversation, preview, and code become explicit views.

```text
Desktop
┌────────────┬────────────────────┬───────────────────────────────┐
│ Riwayat    │ Percakapan         │ Kanvas halaman                │
│ chat       │ prompt dan fakta   │ desktop/mobile, preview, kode│
└────────────┴────────────────────┴───────────────────────────────┘

Mobile
┌────────────────────────────────────────────────────────────────┐
│ Riwayat       Percakapan       Pratinjau       Kode              │
├────────────────────────────────────────────────────────────────┤
│ Tampilan aktif, composer tetap mudah dijangkau                  │
└────────────────────────────────────────────────────────────────┘
```

**Layout option B, not selected:** a single chat column with preview and source opened as modal or separate browser tabs. This hides the generated page while users compare facts and output, so it does not fit the main review task.

**Principles:** keep the prompt, confirmed facts, and rendered page visible as separate kinds of information; use teal only for facts the user confirmed; make the preview canvas the memorable element through its real breakpoint controls, not decoration; use restrained dividers and whitespace instead of identical cards and shadows; respect keyboard focus and reduced motion.

**Self-critique against generic UI patterns:** a generic chat template could use a gradient hero, repeated rounded cards, and anonymous assistant copy. The selected design instead gives the page a canvas sized for the product's output and a persistent place for user-confirmed facts. No gradient, serif/terracotta pairing, all-caps eyebrow labels, decorative numbering, or streaming animation is planned.

## Review Focus

- Prompt contains no name, description, or service. Keep generation disabled and show an inline form for the missing facts.
- User edits or supplies a fact absent from the prompt. Record `user_confirmed: true` only after explicit form entry or confirmation.
- Intake returns unsupported scope, over-budget input, or a server error. Show the correct action without changing it to a successful assistant message.
- Generation fails or returns an unknown status. Hide preview/source/download controls and retain the user's request for correction.
- Preview or source request fails after a page was accepted. Keep the accepted summary and show a retriable panel error without attempting generation again.

---

### Task 1: Scaffold the web package and shared types

**Files:**
- Create: `apps/web/package.json`
- Create: `apps/web/package-lock.json`
- Create: `apps/web/.gitignore`
- Create: `apps/web/eslint.config.mjs`
- Create: `apps/web/next-env.d.ts`
- Create: `apps/web/next.config.ts`
- Create: `apps/web/tsconfig.json`
- Create: `apps/web/postcss.config.mjs`
- Create: `apps/web/components.json`
- Create: `apps/web/.env.example`
- Create: `apps/web/src/app/page.tsx`
- Create: `apps/web/src/app/layout.tsx`
- Create: `apps/web/src/app/globals.css`
- Create: `apps/web/src/lib/utils.ts`
- Create: `apps/web/src/lib/api-types.ts`
- Create: `apps/web/src/lib/api-client.ts`
- Create: `apps/web/README.md`
- Modify: `logs/LOG_EKSPERIMEN_DAN_INTERAKSI_LLM.md`

**Interfaces:**
- Produces TypeScript representations of `RequestDraft`, `IntakeEnvelope`, `IntakeResponse`, `CatalogResponse`, `GenerationRequest`, `GenerationResponse`, `GenerationSummary`, and `SourceResponse` matching `apps/api` Pydantic schemas.
- `NEXT_PUBLIC_API_BASE_URL` configures the FastAPI base URL.

- [ ] Resolve supported stable versions for Next.js, create-next-app, shadcn, and required UI dependencies from official documentation; pin the resolved packages and lockfile.
- [ ] From the repository root scaffold `apps/web` using the resolved create-next-app version with `--typescript --tailwind --eslint --app --src-dir --use-npm --import-alias "@/*" --yes --no-agents-md --disable-git`, then run the resolved shadcn CLI version from `apps/web` and configure components under `src/components/ui`.
- [ ] Set Indonesian document language, product metadata, font setup, and semantic base styles in `layout.tsx` and `globals.css`.
- [ ] Define the six color tokens above, load IBM Plex Sans and IBM Plex Mono with `next/font/google`, and set a default local API base URL in `.env.example`; keep runtime font loading local and secrets out of source.
- [ ] Remove unused scaffold demonstration assets and replace the default scaffold screen with the app shell in Task 2.
- [ ] Append the AI interaction record and commit/push the web scaffold.

### Task 2: Build chat shell and local conversation state

**Files:**
- Modify: `apps/web/src/app/page.tsx`
- Create: `apps/web/src/components/chat/chat-shell.tsx`
- Create: `apps/web/src/components/chat/history-sidebar.tsx`
- Create: `apps/web/src/components/chat/message-list.tsx`
- Create: `apps/web/src/components/chat/composer.tsx`
- Create: `apps/web/src/components/ui/button.tsx`
- Create: `apps/web/src/components/ui/separator.tsx`
- Create: `apps/web/src/components/ui/textarea.tsx`
- Create: `apps/web/src/components/ui/scroll-area.tsx`
- Create: `apps/web/src/components/ui/tooltip.tsx`
- Create: `apps/web/src/components/ui/sheet.tsx`
- Create: `apps/web/src/lib/chat-state.ts`
- Create: `apps/web/src/lib/history-storage.ts`
- Modify: `apps/web/src/app/globals.css`
- Modify: `logs/LOG_EKSPERIMEN_DAN_INTERAKSI_LLM.md`

**Interfaces:**
- `ChatMessage` is a discriminated union for `user`, `assistant`, `clarification`, `request_summary`, and `generation_status` messages.
- `ChatSession` contains `id`, `title`, `messages`, `updatedAt`, and accepted `generationId` references.
- Reducer actions cover `new_session`, `append_message`, `replace_message`, `set_generation`, `restore_session`, and `delete_session`.

- [ ] Implement a responsive sidebar with new-chat action and local session list.
- [ ] Implement the main conversation column with empty-state examples, accessible message roles, and composer submission state.
- [ ] Implement versioned `localStorage` read/write helpers that handle missing, malformed, and older-format data by returning an empty history instead of crashing the app.
- [ ] Add keyboard-accessible navigation, visible focus indicators, labels, and status announcements.
- [ ] Keep chat shell in a loading-safe state until client-side history restoration completes.
- [ ] Append the AI interaction record and commit/push the chat shell.

### Task 3: Add guided RequestDraft clarification and review

**Files:**
- Create: `apps/web/src/components/chat/intake-card.tsx`
- Create: `apps/web/src/components/chat/request-summary.tsx`
- Create: `apps/web/src/components/forms/business-facts-form.tsx`
- Create: `apps/web/src/lib/request-draft.ts`
- Create: `apps/web/src/lib/intake-copy.ts`
- Modify: `apps/web/src/lib/chat-state.ts`
- Modify: `apps/web/src/lib/api-client.ts`
- Modify: `apps/web/src/components/chat/message-list.tsx`
- Modify: `logs/LOG_EKSPERIMEN_DAN_INTERAKSI_LLM.md`

**Interfaces:**
- `ConfirmedBusinessFacts` contains `genre`, `style_mode`, form values for the source-bound `business_facts` array, `asset_ids`, `requested_features`, and `fictitious`. Required facts are exactly one `name`, exactly one `description`, and at least one structured `service`; additional facts retain the kinds and value shapes accepted by the existing draft schema.
- `createDraft(prompt: string, form: ConfirmedBusinessFacts): RequestDraft` creates the exact source-bound draft and stable fact IDs. Scalar evidence uses the fact's `evidence` field. Structured facts use separate `title_evidence` and `text_evidence` fields inside `value`, matching the existing draft schema.
- Each scalar, structured title, and structured text value gets `user_confirmed: true` only after explicit form submission or confirmation. Source-span evidence must match the exact original prompt offsets and quote.
- `request_summary` message holds a request preview and a state `editing | ready_to_confirm | confirmed`.

- [ ] Build controlled fields for page type, style, business name, description, at least one service, additional facts, asset IDs, requested features, and fictitious-business status.
- [ ] Do not add an NLP extraction module. Prefill only values directly supplied as fields; other facts remain empty and trigger clarification.
- [ ] Modify `apps/web/src/lib/api-client.ts` to implement `validateIntake(prompt, draft)`, `generate(prompt, draft)`, `getGeneration`, `getSource`, and `downloadZip` using the types from Task 1 and the API base URL from environment configuration. `generate` must resend the original prompt and draft so FastAPI can repeat intake validation.
- [ ] Map intake status values to Indonesian assistant messages and show `missing_fields` as focused form fields.
- [ ] Keep the generate action disabled until intake returns `ready` and the user confirms the displayed summary.
- [ ] Append the AI interaction record and commit/push the clarification flow.

### Task 4: Add generation status, result workspace, and downloads

**Files:**
- Create: `apps/web/src/components/results/result-workspace.tsx`
- Create: `apps/web/src/components/results/preview-frame.tsx`
- Create: `apps/web/src/components/results/source-tabs.tsx`
- Create: `apps/web/src/components/results/generation-status.tsx`
- Create: `apps/web/src/lib/preview-url.ts`
- Modify: `apps/web/src/app/page.tsx`
- Modify: `apps/web/src/lib/chat-state.ts`
- Modify: `apps/web/src/lib/api-client.ts`
- Modify: `apps/web/src/app/globals.css`
- Modify: `logs/LOG_EKSPERIMEN_DAN_INTERAKSI_LLM.md`

**Interfaces:**
- `ResultWorkspace` consumes `GenerationSummary`, preview URL, `SourceResponse`, and download URL.
- `PreviewFrame` renders an iframe with `sandbox="allow-scripts"`, no `allow-same-origin`, an accessible title, and a URL from the API.
- `SourceTabs` displays exactly `index.html`, `styles.css`, and `app.js` returned by the API.

- [ ] After explicit confirmation, call `generate` once and show an honest pending state until the JSON response arrives.
- [ ] Map `completed` to the workspace and map all failed or unknown values to an error state with no preview or download controls.
- [ ] Load source text only for an accepted generation; keep source-loading errors separate from generation failures.
- [ ] Add responsive desktop/mobile preview widths without changing the generated website source.
- [ ] Install only the shadcn primitives used by the workbench, including tabs for preview mode and source-file selection.
- [ ] Link the ZIP endpoint directly and provide separate source-file download links through the API's allowlisted routes.
- [ ] Append the AI interaction record and commit/push the result workspace.

### Task 5: Document frontend setup and connection

**Files:**
- Modify: `apps/web/README.md`
- Modify: `README.md`
- Modify: `docs/README.md`
- Modify: `logs/LOG_EKSPERIMEN_DAN_INTERAKSI_LLM.md`

**Interfaces:**
- Consumes: pinned web dependencies, `NEXT_PUBLIC_API_BASE_URL`, and FastAPI OpenAPI contract.
- Produces: exact local setup and run instructions with no inference request built into startup.

- [ ] Document package installation, environment file creation, local web start, API origin configuration, and local history behavior.
- [ ] State that opening the UI or starting the API does not trigger model inference; generation happens only after user confirmation.
- [ ] Link the API docs at `http://127.0.0.1:8000/docs` and the application specification.
- [ ] Append the AI interaction record, review the file list and diff without running a build or generation, then commit and push.

# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Primary users are the WebCraft project owner and VibeStack team, using the local app to create and inspect generated website pages. The owner confirmed this audience on 2026-11-01.

## Product Purpose

WebCraft GPT turns a user's brief and confirmed business facts into a complete landing page or company profile, then provides a preview, source files, and a ZIP download.

## Positioning

The local Mini GPT selects a constrained page plan. Project validators, resolvers, and the deterministic renderer produce the final HTML, CSS, and JavaScript. The app does not claim that the model writes arbitrary executable code.

## Operating Context

The app uses a Next.js and shadcn interface with a local FastAPI adapter. Users submit a brief, review and confirm facts, explicitly start generation, and inspect the accepted result. Usage shows generation outcomes and GPU telemetry. Chat history is stored in the browser; generation artifacts and Usage data are stored locally by the project.

## Capabilities and Constraints

- Supported page types are landing pages and company profiles.
- Supported output styles are plain CSS and Tailwind CSS.
- Generation runs only after the user confirms the request and the API validates it.
- The model selects from the constrained page pipeline. The renderer creates the accepted website files.
- Usage stores operational metadata, GPU telemetry, the user prompt, and user-confirmed facts in the local project database for 90 days so a run can be audited after navigation or a browser restart. Never store or show extractor tokens.
- Read generated HTML, CSS, and JavaScript from the existing validated generation artifact endpoint. Do not duplicate source code into the Usage database. A failed run has no source output unless the validated endpoint returns an accepted artifact.
- Usage and navigation must not trigger inference.
- Human visual review and a 95 percent visual quality claim remain out of scope for this change.

## Brand Commitments

- Team: VibeStack.
- Project: WebCraft GPT.
- Website identity: WebCraft by VibeStack.
- For this scope, preserve the existing warm editorial workbench documented in `DESIGN.md`. A different visual identity has not been requested.

## Evidence on Hand

- Product behavior and implementation constraints are documented in `README.md`, `apps/web/README.md`, `apps/api/README.md`, and the application design specifications under `docs/superpowers/specs/`.
- The current source provides constrained HTML, CSS, and JavaScript output, accepted-source endpoints, a Usage audit, and GPU telemetry.
- No human-rated visual quality score is recorded by this product context.

## Product Principles

- Do not invent business facts that are absent from user-confirmed input.
- Show the difference between a rejected request, a failed inference, and a completed generation.
- Keep the raw input and output inspection tied to the same Usage and generation identifiers.
- Preserve the local model and deterministic renderer as the source of generated websites.

## Accessibility & Inclusion

Preserve keyboard navigation, visible focus, accessible names and states, readable code typography, responsive behavior, and reduced-motion support.

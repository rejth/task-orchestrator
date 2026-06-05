# Scaffold Svelte client with authenticated /api tracer flow

## Parent

Parent PRD: #16

## What to build

Create the Svelte 5/Vite/TypeScript client as the first real browser surface for the Job/Task console. This slice should prove the client can authenticate with the current API-key contract, call the server through the relative `/api` boundary, initialize or select a Scope, and show clear API/authentication errors. It should be a narrow operator tracer flow, not the full console.

## Acceptance criteria

- [x] The client workspace is scaffolded with Svelte 5, Vite, and TypeScript and participates in the root pnpm workspace.
- [x] Vite proxies relative `/api` requests to the FastAPI server during local development.
- [x] The UI lets an operator enter an API key, stores it in browser localStorage, attaches it as `X-API-Key`, and clears it after a 401 response.
- [x] The UI lets an operator initialize or select a Scope using the server API under `/api`.
- [x] API and authentication failures are surfaced clearly without using ambiguous domain language.
- [x] The tracer flow is covered by appropriate client behavior tests or documented verification if framework setup limits automated coverage in this slice.

## Blocked by

- #17
- #18

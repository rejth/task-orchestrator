## Problem Statement

The project currently contains only the Python server for orchestrating Jobs, Tasks, Launches, scheduling, dispatch, and journals. There is no browser client in the repository, no shared monorepo command surface, and no first-party UI for operators to create a Scope, inspect a Job's Tasks, schedule work, stop a run, abort a Launch, or read a Journal. Adding a client as a separate project would make the API contract, tooling, Docker workflow, and local development story drift from the server.

## Solution

Turn the repository into a client/server monorepo. The existing FastAPI/Celery server becomes a server workspace, the new Svelte 5/Vite/TypeScript client becomes a client workspace, and the repository root becomes the orchestration layer for shared commands, quality gates, and full-stack development. The first client is not an empty scaffold: it is a thin but real Job/Task console that uses the existing API through a relative `/api` boundary, validates responses with generated Zod schemas, and gives operators a useful first workflow.

## User Stories

1. As a developer, I want the server and client to live in one monorepo, so that full-stack changes can be reviewed and tested together.
2. As a developer, I want the repository root to orchestrate workspaces rather than contain application code, so that client and server boundaries stay explicit.
3. As a developer, I want the existing Python server to keep using its current Python dependency workflow, so that the server migration does not destabilize dependency resolution.
4. As a developer, I want pnpm to be the monorepo command surface, so that common development commands are discoverable from the root.
5. As a developer, I want root commands for development, linting, formatting, type checking, testing, API generation, and full checks, so that CI and local workflows use the same entry points.
6. As a developer, I want the server package to have a domain-specific import name instead of an ambiguous `src` import name, so that the moved server remains understandable inside a monorepo.
7. As a developer, I want the server tests to remain green after the server move and package rename, so that the migration preserves current orchestration behavior.
8. As a developer, I want the FastAPI routes mounted under `/api`, so that browser clients have a stable application API boundary.
9. As a frontend developer, I want Vite to proxy `/api` to the server during development, so that the browser client can use relative URLs without CORS friction.
10. As a frontend developer, I want the client generated from a modern Svelte 5 + Vite + TypeScript setup, so that the UI starts from the intended stack.
11. As a frontend developer, I want Biome configured for formatting and baseline linting, so that client code has consistent style.
12. As a frontend developer, I want Oxlint configured for fast TypeScript linting, so that client quality checks stay quick.
13. As a developer, I want Lefthook configured for shared local hooks, so that common checks run before changes leave the workstation.
14. As a developer, I want the pre-commit hook to run cheaper checks, so that commits stay fast.
15. As a developer, I want the pre-push hook to run the full project check, so that expensive verification happens before publishing.
16. As a developer, I want OpenAPI-generated TypeScript types, so that client code reflects the server contract.
17. As a developer, I want OpenAPI-generated Zod schemas, so that API responses are validated at runtime.
18. As a developer, I want a small hand-written fetch wrapper around the generated contract artifacts, so that the client avoids a heavy generated runtime.
19. As an operator, I want to enter an API key in the browser client, so that I can authenticate against the current server contract.
20. As an operator, I want the browser client to remember my API key locally, so that I do not need to re-enter it on every page refresh.
21. As an operator, I want the client to clear the API key after an unauthorized response, so that stale credentials do not keep failing silently.
22. As an operator, I want to create or select a Scope, so that I can inspect the Job for the entity I am working with.
23. As an operator, I want to initialize a Scope from the UI, so that I can create the Job and its Tasks without using curl or API docs.
24. As an operator, I want to see the Tasks for a Scope, so that I can understand current Job state.
25. As an operator, I want to see each Task's label, description, status, and dependencies, so that I can understand what work exists and why it is blocked or ready.
26. As an operator, I want to distinguish current Launch information from latest terminal Launch information, so that active and completed work are not confused.
27. As an operator, I want to schedule a Task from the UI, so that I can start or re-run that Task and its downstream Tasks.
28. As an operator, I want scheduling to show the affected Tasks returned by the server, so that I can see what the Job intends to run.
29. As an operator, I want to stop the current run for a Scope, so that I can abort in-flight or pending work when it is no longer valid.
30. As an operator, I want to abort an individual Launch when the server allows it, so that I can intervene without stopping the whole Job.
31. As an operator, I want to open a Launch's Journal, so that I can inspect execution logs without leaving the console.
32. As an operator, I want API errors to appear clearly in the client, so that I know whether a Scope is missing, a Task is invalid, or authentication failed.
33. As an operator, I want the console to remain usable on normal laptop-sized screens, so that repeated operational workflows are comfortable.
34. As a developer, I want Docker Compose to include the client service, so that there is a full-stack smoke path.
35. As a developer, I want local pnpm development to remain the primary fast path, so that Svelte hot module reload and server reload stay ergonomic.
36. As a developer, I want Docker images and Compose services updated for the server's new package name and workspace location, so that existing container workflows continue to work.
37. As a developer, I want root documentation updated for the monorepo layout and commands, so that future contributors do not need to infer the new workflow.
38. As a developer, I want the API contract generation to be part of the shared check flow, so that stale generated types and schemas are caught early.
39. As a maintainer, I want the monorepo architecture decision recorded, so that future agents understand why the workspace is shaped this way.
40. As a maintainer, I want this work split into runnable phases, so that agents can implement it without mixing unrelated failure modes.

## Implementation Decisions

- The repository becomes a two-application monorepo: one server workspace and one client workspace.
- The repository root is an orchestration layer for workspace discovery, root scripts, shared checks, hooks, Docker Compose, documentation, and project-level decisions.
- The existing Python server moves into the server workspace.
- The server package is renamed from the ambiguous `src` import package to `task_orchestrator`.
- The server continues to use the current Python project setup: uv, Hatch, FastAPI, SQLAlchemy, Alembic, PostgreSQL, Celery, Redis, Ruff, Pyright, Pytest, and Docker.
- pnpm is the monorepo package manager and shared command surface.
- pnpm delegates server dependency and command execution to uv instead of replacing uv.
- Root scripts expose at least development, formatting, linting, type checking, testing, API generation, and full check commands.
- The API is mounted under `/api`.
- The client calls relative `/api` URLs.
- Vite proxies `/api` to FastAPI during local development.
- Docker Compose includes database, Redis, API, worker, beat, and client services.
- Local pnpm development remains the primary frontend development workflow.
- The first Svelte client is a real Job/Task console rather than a blank starter.
- The client stack is Vite, Svelte 5, TypeScript, Biome, Oxlint, and Lefthook.
- The client API contract is generated from FastAPI's OpenAPI schema.
- Generated TypeScript types and generated Zod schemas are committed or regenerated through a documented command, depending on the final tool configuration.
- The selected OpenAPI generator is `@hey-api/openapi-ts` with TypeScript and Zod schema generation.
- The generated contract artifacts do not replace a small hand-written API client module.
- The hand-written API client attaches `X-API-Key`, calls relative `/api` URLs, validates responses with Zod, and normalizes errors for the UI.
- The API key is entered by the operator in the browser and stored in localStorage for the initial console.
- The API key is not baked into Vite environment variables because browser-shipped secrets are not secret.
- A `401` response clears the stored API key and returns the operator to an authentication prompt.
- The UI supports Scope initialization or selection, Task listing, Task scheduling, run stopping, Launch aborting, and Journal viewing.
- The UI should use domain language from the glossary: Scope, Job, Task, Launch, Schedule, Dispatch, and Journal.
- The UI should avoid ambiguous alternatives that the glossary rejects, such as pipeline, workflow, run, step, stage, trigger, enqueue, attempt, or execution when the canonical term applies.
- The migration should proceed in vertical phases: server move and rename first, root workspace tooling second, client scaffold third, API generation fourth, Job/Task console fifth, and Docker Compose updates sixth.
- ADR 0003 records the monorepo client/server workspace decision.

## Testing Decisions

- Good tests should assert externally observable behavior, not internal implementation details.
- The server move and package rename must preserve the existing server behavior and keep the existing server test suite green.
- Server API tests should be updated to assert the `/api` prefix while preserving the semantics of creating Scopes, listing Tasks, scheduling Tasks, aborting Launches, stopping runs, and reading Journals.
- Server unit tests should continue to cover domain and service behavior around readiness, scheduling, dispatch, cascade failure, stopping, task expiry, and reconciliation.
- Existing Pytest coverage is prior art for server behavior tests.
- Existing FastAPI TestClient integration tests are prior art for HTTP contract tests.
- The OpenAPI export should be tested or checked as part of generation so that client contract artifacts do not silently drift.
- The hand-written API client is a deep module candidate: it should encapsulate fetch, authentication headers, Zod validation, and error normalization behind a small stable interface.
- The API client should have focused tests for successful parsing, Zod validation failure, HTTP errors, and `401` credential clearing.
- The client UI should have behavior tests for the main operator flows: entering an API key, initializing a Scope, loading Tasks, scheduling a Task, stopping a run, aborting a Launch, and opening a Journal.
- The generated TypeScript and Zod artifacts should not be hand-tested as business logic; instead, generation should be reproducible and included in checks.
- Root quality gates should verify Biome, Oxlint, Svelte/TypeScript checking, Ruff, Pyright, Pytest, and client tests.
- Docker Compose should have at least a documented smoke path proving that the full stack starts and the client can reach the API.

## Out of Scope

- Replacing the current server API key mechanism with production user authentication.
- Adding multi-user authorization, roles, sessions, or server-side browser login.
- Replacing Celery, Redis, PostgreSQL, SQLAlchemy, Alembic, uv, Ruff, Pyright, or the existing server test strategy.
- Changing the Schedule semantics: scheduling a Task still schedules that Task and its downstream subgraph.
- Implementing the future narrower Retry operation.
- Porting real per-Task handler bodies; the current demo handler migration state remains unchanged.
- Building a full DAG visualization editor.
- Making the client a public product-grade production UI.
- Introducing a generated API runtime client if the small hand-written client is sufficient.
- Splitting the repository into multiple domain contexts.

## Further Notes

- This PRD follows the glossary in the project context document and the architectural decisions already recorded for event-driven dispatch, downstream scheduling, and the monorepo workspace.
- The server currently exposes FastAPI routes for Scope creation, Task listing, Task scheduling, run stopping, Launch aborting, and Journal retrieval. The client should exercise those contracts rather than inventing parallel behavior.
- The implementation should keep changes phaseable and runnable. The server migration should be verified before frontend tooling and UI work are layered on top.

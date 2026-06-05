# Add full-stack Docker Compose and docs smoke path

## Parent

Parent PRD: #16

## What to build

Finish the monorepo by making the full stack runnable through Docker Compose and documenting the local and container workflows. Compose should include the client alongside database, Redis, API, worker, and beat services. Documentation should explain the fast local pnpm workflow, the full-stack Compose smoke path, and how to verify that the client can reach the API.

## Acceptance criteria

- [x] Docker Compose includes a client service that can run with the API, worker, beat, database, and Redis services.
- [x] Dockerfiles and Compose paths reflect the server workspace location and `task_orchestrator` package name.
- [x] The client service can reach the API through the intended `/api` boundary in the full-stack setup.
- [x] Documentation describes local development, full-stack Compose startup, API generation, checks, and a smoke test for creating/selecting a Scope from the browser client.
- [x] The full root check passes, or any remaining manual verification gaps are documented with reasons.
- [x] The feature folder contains the PRD and markdown mirrors of every generated issue.

## Blocked by

- #23

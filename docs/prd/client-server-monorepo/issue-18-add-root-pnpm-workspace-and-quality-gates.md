# Add root pnpm workspace and quality gates

## Parent

Parent PRD: #16

## What to build

Add the monorepo command surface and quality gates after the server workspace exists. pnpm should coordinate workspace commands from the root, while server commands continue to delegate to uv. The root should expose clear development, format, lint, typecheck, test, API generation, and full check scripts, with Biome, Oxlint, and Lefthook configured for the client and shared workflow.

## Acceptance criteria

- [x] The repository has a pnpm workspace with root scripts for development, formatting, linting, type checking, testing, API generation, and full project checks.
- [x] Server scripts invoked through pnpm delegate to uv in the server workspace instead of replacing Python dependency management.
- [x] Biome and Oxlint are configured for TypeScript/Svelte/client-side checks without interfering with Python tooling.
- [x] Lefthook is configured with a cheaper pre-commit path and a full pre-push check path.
- [x] Root documentation explains the shared command surface and the division between pnpm orchestration and uv server dependency management.

## Blocked by

- #17

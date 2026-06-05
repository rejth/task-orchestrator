# Monorepo client/server workspace

We decided to turn the project into a client/server monorepo where the repository root is an orchestration layer, the existing Python server moves to `apps/server`, and the new Svelte client lives in `apps/client`. During the move, the server package is renamed from the ambiguous import package `src` to `task_orchestrator`; `pnpm` becomes the shared monorepo command surface, while `uv` remains the server's Python dependency manager. The browser client calls the server through relative `/api` URLs, with Vite proxying `/api` to FastAPI in development, and OpenAPI-generated TypeScript plus Zod schemas define the client/server contract.

## Consequences

- Root commands coordinate both apps without making pnpm responsible for Python dependency resolution.
- The migration is noisier because imports, Docker files, Celery targets, Uvicorn targets, Alembic paths, tests, and docs all need to follow the new server package name and workspace layout.
- The initial Svelte client is a real Job/Task console rather than an empty scaffold, so the monorepo exercises the actual API boundary from the start.

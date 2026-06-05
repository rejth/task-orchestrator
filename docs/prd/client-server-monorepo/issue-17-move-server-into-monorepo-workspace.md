# Move server into monorepo workspace

## Parent

Parent PRD: #16

## What to build

Move the existing server into the server workspace, rename the server import package to `task_orchestrator`, and preserve the current Job orchestration behavior through the new monorepo shape. The API should be mounted under `/api`, and server commands, tests, migrations, Celery entrypoints, Uvicorn entrypoints, Docker builds, and documentation should all follow the new package name and workspace layout.

## Acceptance criteria

- [x] Existing server code lives in the server workspace and imports use `task_orchestrator` instead of the old ambiguous package name.
- [x] FastAPI routes are mounted under `/api`, and existing HTTP behavior for Scope, Task, Launch, Schedule, stop-run, and Journal endpoints is preserved under that prefix.
- [x] Alembic, Uvicorn, Celery worker, Celery beat, tests, linting, type checking, and Docker server builds work from the new server workspace.
- [x] Existing server tests pass after the move and package rename.
- [x] README and relevant docs describe the new server workspace commands and API prefix.

## Blocked by

None - can start immediately

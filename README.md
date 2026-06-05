# Task Orchestrator

DAG-based task executor with state machines, dependency resolution, cascade failure, and Celery dispatch.

Each **Scope** owns a **Job** — a directed acyclic graph of **Tasks**. Scheduling a task marks it and all downstream tasks for (re-)execution. Tasks execute in parallel where dependencies allow. See [CONTEXT.md](CONTEXT.md) for the domain glossary.

## Stack

pnpm workspace · Python 3.13 · uv · FastAPI · SQLAlchemy 2 · Alembic · PostgreSQL · Celery + Redis · Ruff · Pyright · TypeScript · Biome · Oxlint · Lefthook · Docker

## Quickstart

### Docker (full stack)

```bash
cp .env.example .env
docker compose up --build
```

API available at `http://localhost:8000/api` — interactive docs at `http://localhost:8000/docs`.

### Local dev

**Prerequisites:** pnpm 10, Python 3.13, uv, PostgreSQL, Redis running locally.

Install the root workspace once:

```bash
pnpm install
```

pnpm orchestrates workspace commands from the repository root. Python dependency
management still belongs to uv inside `apps/server`; the pnpm server package only
delegates commands into that uv-managed workspace.

```bash
# Install server dependencies
pnpm --filter @task-orchestrator/server exec uv sync

# Copy and edit env for local services
cp .env.example apps/server/.env

# Run migrations
pnpm --filter @task-orchestrator/server exec uv run alembic upgrade head

# Start API server
pnpm run dev:server

# Start Celery worker (separate terminal)
pnpm run dev:worker

# Start Celery beat scheduler (separate terminal)
pnpm run dev:beat
```

## Workspace Commands

Run shared commands from the repository root:

```bash
pnpm run format       # Biome for client/shared files, Ruff format for server
pnpm run lint         # Biome + Oxlint for client/shared files, Ruff for server
pnpm run typecheck    # TypeScript for client/shared files, Pyright for server
pnpm run test         # Server tests
pnpm run api:generate # Write docs/api/openapi.json from the FastAPI app
pnpm run check        # Full format, lint, typecheck, test, and API generation
```

## API

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/scopes/{scope_id}` | Create a job for a scope (returns 409 if exists) |
| `GET` | `/api/scopes/{scope_id}/tasks` | List all tasks with current status |
| `POST` | `/api/scopes/{scope_id}/tasks/{task_id}/schedule` | Schedule task + all downstream, dispatch to Celery |
| `DELETE` | `/api/scopes/{scope_id}/tasks/{task_id}/launches/{launch_id}` | Abort a running launch |
| `GET` | `/api/scopes/{scope_id}/tasks/{task_id}/launches/{launch_id}/journal` | Fetch execution logs |

Pass `X-API-Key: <key>` on API requests. Scheduling actions are attributed to the authenticated API key.

## Demo task graph

Six generic tasks wired as a diamond DAG to exercise parallel dispatch:

```
FETCH_RAW_DATA
    ├──▶ VALIDATE_DATA  ─────┐
    └──▶ TRANSFORM_DATA ─────▶ AGGREGATE_DATA ──▶ GENERATE_REPORT
                                               └──▶ EXPORT_RESULTS
```

`VALIDATE_DATA` and `TRANSFORM_DATA` run in parallel. Both must succeed before `AGGREGATE_DATA` starts.

## Project structure

```
apps/
└── server/
    ├── task_orchestrator/
    │   ├── api/            # FastAPI app, Depends providers, Pydantic schemas, router
    │   ├── domain/         # State machines: ScopedJob, ScopedTask, TaskLaunch, journal
    │   ├── services/       # Business logic, task dispatcher, event-driven dispatch
    │   ├── infrastructure/ # SQLAlchemy models, SQLJobsRepository, Celery runner
    │   ├── handlers/       # TaskHandlerInterface + DemoHandler
    │   └── workers/        # Celery consumer entry point
    ├── tests/
    │   ├── unit/domain/    # Pure domain tests (no DB, no HTTP)
    │   └── integration/    # API tests against SQLite in-memory
    └── alembic/versions/   # Single initial migration (5 tables)
```

## Tests

```bash
pnpm run test
```

Unit tests need no external services — SQLite in-memory used for integration tests.

Coverage report:

```bash
cd apps/server
uv run coverage run -m pytest tests/ && uv run coverage html
# open htmlcov/index.html
```

## Code quality

```bash
pnpm run lint:fix
pnpm run typecheck
pnpm run check
```

## Database migrations

Generate a migration after changing ORM models:

```bash
cd apps/server
uv run alembic revision --autogenerate -m "describe change"
uv run alembic upgrade head
```

## Adding a real task handler

1. Implement `TaskHandlerInterface` in `task_orchestrator/handlers/`:

```python
from task_orchestrator.domain.journal import Log
from task_orchestrator.handlers.interface import TaskHandleStatus

class MyHandler:
    def run(self, scope_id: str) -> tuple[TaskHandleStatus, list[Log]]:
        # do work...
        return TaskHandleStatus.SUCCESS, []
```

1. Register it in `task_orchestrator/infrastructure/celery/runner.py`:

```python
_HANDLERS: dict[TaskSpecificationId, type] = {
    TaskSpecificationId.FETCH_RAW_DATA: MyFetchHandler,
    # ...
}
```

1. Add the task ID to `TaskSpecificationId` in `task_orchestrator/domain/task.py` and wire its `depends_on`.

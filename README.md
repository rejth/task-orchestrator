# Task Orchestrator

DAG-based task executor with state machines, dependency resolution, cascade failure, and Celery dispatch.

Each **Scope** owns a **Job** — a directed acyclic graph of **Tasks**. Scheduling a task marks it and all downstream tasks for (re-)execution. Tasks execute in parallel where dependencies allow. See [CONTEXT.md](CONTEXT.md) for the domain glossary.

## Stack

Python 3.13 · uv · FastAPI · SQLAlchemy 2 · Alembic · PostgreSQL · Celery + Redis · Ruff · Pyright · Docker

## Quickstart

### Docker (full stack)

```bash
cp .env.example .env
docker compose up --build
```

API available at `http://localhost:8000/api` — interactive docs at `http://localhost:8000/docs`.

### Local dev

**Prerequisites:** Python 3.13, uv, PostgreSQL, Redis running locally.

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
cd apps/server
uv sync

# Copy and edit env
cp ../../.env.example .env  # set DATABASE_URL and REDIS_URL to your local instances

# Run migrations
uv run alembic upgrade head

# Start API server
uv run uvicorn task_orchestrator.api.app:app --reload

# Start Celery worker (separate terminal)
uv run celery -A task_orchestrator.workers.consumer worker --loglevel=info
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

Run server commands from `apps/server`.

```bash
uv run pytest tests/ -v
```

Unit tests need no external services — SQLite in-memory used for integration tests.

Coverage report:

```bash
uv run coverage run -m pytest tests/ && uv run coverage html
# open htmlcov/index.html
```

## Code quality

```bash
# Lint + auto-fix
uv run ruff check task_orchestrator tests --fix

# Type check
uv run pyright task_orchestrator tests

# Both
uv run ruff check task_orchestrator tests --fix && uv run pyright task_orchestrator tests
```

## Database migrations

Generate a migration after changing ORM models:

```bash
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

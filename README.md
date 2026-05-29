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

API available at `http://localhost:8000` — interactive docs at `http://localhost:8000/docs`.

### Local dev

**Prerequisites:** Python 3.13, uv, PostgreSQL, Redis running locally.

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync

# Copy and edit env
cp .env.example .env  # set DATABASE_URL and REDIS_URL to your local instances

# Run migrations
uv run alembic upgrade head

# Start API server
uv run uvicorn src.api.app:app --reload

# Start Celery worker (separate terminal)
uv run celery -A src.workers.consumer worker --loglevel=info
```

## API

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/scopes/{scope_id}` | Create a job for a scope (returns 409 if exists) |
| `GET` | `/scopes/{scope_id}/tasks` | List all tasks with current status |
| `POST` | `/scopes/{scope_id}/tasks/{task_id}/schedule` | Schedule task + all downstream, dispatch to Celery |
| `DELETE` | `/scopes/{scope_id}/tasks/{task_id}/launches/{launch_id}` | Abort a running launch |
| `GET` | `/scopes/{scope_id}/tasks/{task_id}/launches/{launch_id}/journal` | Fetch execution logs |

Pass `X-User: <name>` header to attribute scheduling actions.

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
src/
├── api/            # FastAPI app, Depends providers, Pydantic schemas, router
├── domain/         # State machines: ScopedJob, ScopedTask, TaskLaunch, journal
├── services/       # Business logic, DAG builder, Celery chain builder
├── infrastructure/ # SQLAlchemy models, SQLJobsRepository, Celery runner
├── handlers/       # TaskHandlerInterface + DemoHandler
└── workers/        # Celery consumer entry point
tests/
├── unit/domain/    # 40 pure domain tests (no DB, no HTTP)
└── integration/    # 9 API tests against SQLite in-memory
alembic/versions/   # Single initial migration (5 tables)
```

## Tests

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
uv run ruff check src tests --fix

# Type check
uv run pyright src tests

# Both
uv run ruff check src tests --fix && uv run pyright src tests
```

## Database migrations

Generate a migration after changing ORM models:

```bash
uv run alembic revision --autogenerate -m "describe change"
uv run alembic upgrade head
```

## Adding a real task handler

1. Implement `TaskHandlerInterface` in `src/handlers/`:

```python
from src.domain.journal import Log
from src.handlers.interface import TaskHandleStatus

class MyHandler:
    def run(self, scope_id: str) -> tuple[TaskHandleStatus, list[Log]]:
        # do work...
        return TaskHandleStatus.SUCCESS, []
```

1. Register it in `src/infrastructure/celery/runner.py`:

```python
_HANDLERS: dict[TaskSpecificationId, type] = {
    TaskSpecificationId.FETCH_RAW_DATA: MyFetchHandler,
    # ...
}
```

1. Add the task ID to `TaskSpecificationId` in `src/domain/task.py` and wire its `depends_on`.

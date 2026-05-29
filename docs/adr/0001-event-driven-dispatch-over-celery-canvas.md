# Event-driven task dispatch instead of a pre-baked Celery canvas

The task DAG is a general fan-in/fan-out graph, but Celery's `chain`/`group` canvas can only express series-parallel structures declared up front. To bridge the gap we built a coercion layer (`src/services/make_task_graph.py` + `src/services/make_celery_chain.py`) that reverse-engineers a series-parallel nesting from the DAG; it is the most complex and fragile part of the system.

We decided to keep Celery purely as transport/execution and keep the `ScopedJob` aggregate + PostgreSQL as the orchestrator and source of truth, but to replace the pre-baked canvas with **event-driven dispatch**: when a Task finishes (Success or Skipped), the Job is asked which successors are now Ready (all predecessors Success/Skipped) and only those are enqueued. Exactly-once fan-in is guaranteed by the existing per-Job `SELECT ... FOR UPDATE` lock; dispatch happens after commit, with a reconciliation sweep to re-enqueue any Task left stuck PENDING. This deletes the coercion layer entirely while preserving Celery and the PG state the front end already reads.

## Considered Options

- **External workflow/orchestration engine** (Temporal, Airflow, Dagster, Prefect, Hatchet) - rejected. They assume DAG-as-code run as a whole pipeline, their own state store, and scheduler-driven runs. Our model is per-Scope sub-DAGs triggered on demand per node via API, with reschedule/abort/skip and PostgreSQL as the source of truth the front end queries. Adopting one would mean rewriting the domain state machine and surrendering PG-as-truth for little gain.
- **Keep the Celery canvas** - rejected. The series-parallel coercion is the actual pain; keeping it defeats the purpose.

## Consequences

- `src/services/make_task_graph.py` and `src/services/make_celery_chain.py` are removed; ordering moves into the Job + service layer.
- Losing the chain means losing its blanket "expire the whole run" lever; replaced by per-task `expires` plus an explicit stop-run operation.
- A reconciliation sweep is required to heal the commit-then-crash gap in post-commit dispatch.

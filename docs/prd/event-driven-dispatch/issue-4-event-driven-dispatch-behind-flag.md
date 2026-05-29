# Event-driven dispatch behind a feature flag

## Parent

#1 — Event-driven task dispatch (replace the Celery-canvas coercion layer)

## What to build

Wire completion-driven dispatch into the tasks-management service, behind a feature flag that defaults to the existing Celery-canvas path. When a Job is scheduled, the ready frontier (runnable Tasks from the scheduled set) is dispatched. When a Task reaches Success or Skipped, the Job's now-runnable successors are computed and dispatched. The readiness computation and the successor's transition to PENDING happen inside the same per-Job locked transaction (this is what makes fan-in exactly-once), and enqueueing to Celery happens after the state change is persisted, mirroring how the initial schedule already enqueues today (today the router calls `schedule_task` then `send_to_queue` as two sequential service calls; the new path must keep enqueue strictly after the commit). Failure dispatches nothing downstream. Operator-facing scheduling semantics are unchanged: scheduling a Task re-runs it and its entire downstream subgraph; parallel branches run in parallel.

## Acceptance criteria

- [ ] A feature flag selects old-canvas vs new event-driven dispatch; default is the old path
- [ ] Scheduling a Job dispatches only its ready frontier
- [ ] On a Task success, its now-runnable successors are dispatched
- [ ] On a Task skip, its now-runnable successors are dispatched
- [ ] On a Task failure, nothing downstream is dispatched
- [ ] Readiness + successor transition to PENDING occur under the per-Job FOR UPDATE lock; enqueue happens post-commit
- [ ] Concurrent fan-in completions dispatch the successor exactly once
- [ ] Front-end per-Task/per-Launch status remains accurate; API contract unchanged
- [ ] Integration tests cover success, skip, failure, and concurrent fan-in

## Blocked by

- #2 — Job readiness query: dispatchable_tasks()
- #3 — Task dispatcher: enqueue runnable Tasks to Celery

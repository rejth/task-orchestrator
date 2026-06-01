# Event-driven dispatch behind a feature flag

## Overview

Wire completion-driven dispatch into the tasks-management service, behind a feature flag that defaults to the existing Celery-canvas path. When a Job is scheduled, only its ready frontier (runnable Tasks from the scheduled set) is dispatched. When a Task reaches Success or Skipped, the Job's now-runnable successors are computed and dispatched. A Task failure dispatches nothing downstream.

Operator-facing scheduling semantics are unchanged: scheduling a Task re-runs it and its entire downstream subgraph, and parallel branches run in parallel. The front-end per-Task/per-Launch status and the API contract stay the same.

## Context

- Impacted component: the tasks-management service (success/skip operations, schedule path)
- Builds on the readiness query `dispatchable_tasks()` (#2) and the Task dispatcher (#3)
- Readiness computation and the successor's transition to PENDING happen inside the same per-Job locked transaction — this is what makes fan-in exactly-once
- Enqueue to Celery happens strictly after the state change is committed, mirroring today's initial schedule (router calls `schedule_task` then `send_to_queue` as two sequential service calls)
- Feature flag defaults to the old canvas path; new event-driven path is opt-in during rollout
- Parent: #1 — Event-driven task dispatch (replace the Celery-canvas coercion layer)
- Blocked by: #2 (readiness query), #3 (task dispatcher)
- Adopted from docs/prd/event-driven-dispatch/issue-4-event-driven-dispatch-behind-flag.md

## Development Approach

- Testing approach: TDD, red-green, vertical slices — one failing test, minimal code to pass, then next behavior
- Complete each task fully before moving to the next
- Update this plan when scope changes during implementation

## Testing Strategy

Method: TDD, red-green, vertical slices (from the parent PRD Testing Decisions).

- Drive the service through its public operations; assert observable dispatch behavior, not internal traversal
- Dispatch orchestration integration suite: success and skip of a Task enqueue its now-runnable successors; failure enqueues nothing downstream. Prior art: the existing tasks-management service integration tests
- Cover concurrent fan-in: the successor is dispatched exactly once when predecessors complete simultaneously
- Assert the feature flag routes to old-canvas vs new event-driven path
- Run project tests after each Task before proceeding

## Technical Details

- Feature flag selects old-canvas vs new event-driven dispatch; default is the old path
- Scheduling a Job dispatches only its ready frontier (runnable Tasks from the scheduled set)
- On Task success or skip, the now-runnable successors are computed and dispatched
- On Task failure, nothing downstream is dispatched (cascade fail)
- Readiness + successor transition to PENDING occur under the per-Job `SELECT ... FOR UPDATE` lock, held across the readiness computation, not just the single transition
- Enqueue happens post-commit; never inside the locked transaction
- Concurrent fan-in completions dispatch the successor exactly once (last predecessor to commit is the sole one that sees all siblings satisfied)
- API contract and front-end-read status are unchanged

## Implementation Steps

### Task 1: Add the feature flag and route between dispatch paths

- [ ] Add a feature flag that selects old-canvas vs new event-driven dispatch, defaulting to the old path
- [ ] Route the schedule operation through the flag without changing the old path's behavior
- [ ] write tests asserting the flag routes to each path
- [ ] run project tests - must pass before next task

### Task 2: Dispatch the ready frontier on schedule

- [ ] On scheduling a Job, compute the ready frontier via the readiness query and dispatch only those Tasks
- [ ] Transition dispatched Tasks to PENDING inside the per-Job locked transaction; enqueue post-commit
- [ ] write tests for new functionality
- [ ] run project tests - must pass before next task

### Task 3: Dispatch successors on success and skip

- [ ] On a Task reaching Success, compute now-runnable successors and dispatch them
- [ ] On a Task being Skipped, compute now-runnable successors and dispatch them
- [ ] Compute readiness and transition successors to PENDING under the per-Job FOR UPDATE lock; enqueue post-commit
- [ ] write tests for success and skip dispatch
- [ ] run project tests - must pass before next task

### Task 4: Block downstream on failure and ensure exactly-once fan-in

- [ ] On a Task failure, dispatch nothing downstream (cascade fail)
- [ ] Ensure concurrent fan-in completions dispatch the successor exactly once via the per-Job lock
- [ ] write integration tests covering success, skip, failure, and concurrent fan-in
- [ ] run project tests - must pass before next task

### Task 5: Verify acceptance criteria

- [ ] verify the flag selects old-canvas vs new path, default old
- [ ] verify schedule dispatches only the ready frontier
- [ ] verify success and skip dispatch now-runnable successors; failure dispatches nothing downstream
- [ ] verify readiness + PENDING transition occur under the lock and enqueue is post-commit
- [ ] verify concurrent fan-in dispatches the successor exactly once
- [ ] verify front-end per-Task/per-Launch status and API contract are unchanged
- [ ] run full project test suite
- [ ] run project linter - all issues must be fixed

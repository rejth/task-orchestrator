# Stop-run and per-Task expiry

## Overview

Replace the run-level cancellation the Celery chain used to provide. Add an explicit "stop run" operation that, under the per-Job lock, cascade-aborts all non-terminal Tasks so neither the dispatch path nor the reconciliation sweep will enqueue them, and revokes any currently running Launches. Each dispatched Task carries its own expiry to cover the "waited in the queue too long" case. No whole-run auto-kill deadline is introduced; that chain-level behavior is dropped deliberately.

## Context

- Part of the event-driven task dispatch initiative (#1 — replace the Celery-canvas coercion layer)
- Blocked by: #4 — Event-driven dispatch behind a feature flag
- Impacted components: stop-run operation, Task dispatch path, reconciliation sweep, Launch revocation, per-Task expiry tracking
- Adopted from: `docs/prd/event-driven-dispatch/issue-6-stop-run-and-per-task-expiry.md`

## Development Approach

- Testing approach: TDD — red-green vertical slices, one behavior at a time
- Complete each task fully before moving to the next
- Update this plan when scope changes during implementation

## Testing Strategy

Method from `docs/prd/event-driven-dispatch/event-driven-dispatch.md`:

- **TDD, red-green, vertical slices.** Write one failing test → write minimal code to pass → move to next behavior. Do not write all tests first (horizontal slicing produces tests that assert imagined shape, not real behavior).
- **Tests drive public methods, assert observable orchestration behavior.** Never assert internal traversal structure or Celery internals. Litmus test: tests must pass unchanged after any internal refactor.
- **Stop-run (integration suite):** stopping a Job leaves no non-terminal Tasks and triggers no further dispatches.
- **Task dispatcher (unit suite):** asserts set of enqueued Tasks and that each carries the Launch id as idempotency key.
- Run project tests after each Task before proceeding to the next.

## Progress Tracking

- Mark completed items with `[x]` immediately when done
- Update plan if implementation deviates from original scope

## Implementation Steps

### Task 1: Stop-run operation

- [x] RED: write integration test — stop a Job, assert all non-terminal Tasks transition to aborted
- [x] GREEN: implement `stop_run(job_id)` acquiring per-Job lock and cascade-aborting non-terminal Tasks
- [x] RED: write test — after stop-run, dispatch path does not enqueue aborted Tasks
- [x] GREEN: guard dispatch path to skip aborted Tasks
- [x] RED: write test — after stop-run, reconciliation sweep skips aborted Tasks
- [x] GREEN: guard reconciliation sweep to exclude aborted Tasks
- [x] RED: write test — running Launches are revoked when stop-run is called
- [x] GREEN: revoke running Launches inside stop-run
- [x] run project tests - must pass before next task

### Task 2: Per-task expiry

- [x] RED: write unit test — Task dispatched by the dispatcher carries a per-Task expiry timestamp
- [x] GREEN: attach expiry when building Celery signature in the dispatcher
- [x] RED: write test — a Task whose expiry has elapsed is detected at queue processing time
- [x] GREEN: implement expiry detection
- [x] RED: write test — an expired Task is finalized as revoked then failed
- [x] GREEN: implement expiry finalization (revoked → failed transition)
- [x] run project tests - must pass before next task

### Task 3: Verify acceptance criteria

- [x] verify all acceptance criteria from Overview are covered by passing tests
- [x] run full project test suite
- [x] run project linter - all issues must be fixed

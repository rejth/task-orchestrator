# Reconciliation sweep for stalled dispatch

## Overview

Add a periodic background sweep that heals Jobs stalled by a crash between commit and enqueue. It finds Tasks left in PENDING whose predecessors are all satisfied but which are not actually running, and re-enqueues them idempotently — reusing the Launch id as the Celery task id, so a duplicate dispatch is a safe no-op. Failed and aborted Tasks are excluded so a stopped or cascade-failed Job is never resurrected.

## Context

- Impacted component: a new periodic Celery-beat task plus the selection query it runs
- Reuses the Job readiness logic (`dispatchable_tasks()`, #2) and the Task dispatcher (#3) for idempotent re-enqueue
- Idempotency relies on the Launch id used as the Celery task id and the existing Launch-id guard
- Must exclude Failed and aborted Tasks so stopped or cascade-failed Jobs are not resurrected
- Parent: #1 — Event-driven task dispatch (replace the Celery-canvas coercion layer)
- Blocked by: #4 — Event-driven dispatch behind a feature flag (merged)
- Adopted from docs/prd/event-driven-dispatch/issue-5-reconciliation-sweep.md

## Development Approach

- Testing approach: TDD, red-green, vertical slices — one failing test, minimal code to pass, then next behavior
- Complete each task fully before moving to the next
- Update this plan when scope changes during implementation

## Testing Strategy

Method: TDD, red-green, vertical slices (from the parent PRD Testing Decisions).

- Drive behavior through the public selection/sweep interface; assert observable outcomes, not internal traversal
- Reconciliation sweep unit suite: a Task left runnable-but-not-running is selected; failed/aborted Tasks are excluded
- Behavior coverage: the selected Task is re-enqueued, and re-enqueue is idempotent (no duplicate execution)
- Run project tests after each Task before proceeding

## Technical Details

- A scheduled periodic task runs the sweep on an interval (Celery beat)
- Selection criteria: Task in PENDING, every predecessor satisfied (Success or Skipped), not currently running
- Exclude Failed and aborted Tasks from selection
- Re-enqueue reuses the Launch id as the Celery task id; the Launch-id guard makes a duplicate a safe no-op
- Sweep is idempotent and safe to run repeatedly

## Implementation Steps

### Task 1: Build the stalled-Task selection query

- [x] Add a query that selects PENDING Tasks whose predecessors are all satisfied and which are not currently running
- [x] Exclude Failed and aborted Tasks from the selection
- [x] write unit tests for the selection query
- [x] run project tests - must pass before next task

### Task 2: Re-enqueue selected Tasks idempotently

- [ ] Re-enqueue each selected Task reusing its Launch id as the Celery task id
- [ ] Ensure a duplicate re-enqueue is a safe no-op via the existing Launch-id guard
- [ ] write tests covering re-enqueue and idempotency
- [ ] run project tests - must pass before next task

### Task 3: Schedule the periodic sweep

- [ ] Register a Celery-beat periodic task that runs the sweep on an interval
- [ ] Wire the periodic task to the selection query and re-enqueue path
- [ ] write tests for the periodic sweep wiring
- [ ] run project tests - must pass before next task

### Task 4: Verify acceptance criteria

- [ ] verify a scheduled periodic task runs the sweep on an interval
- [ ] verify a Task left runnable-but-not-running is re-enqueued
- [ ] verify re-enqueue is idempotent (Launch id as task id; no duplicate execution)
- [ ] verify Failed/aborted Tasks are never re-enqueued
- [ ] run full project test suite
- [ ] run project linter - all issues must be fixed
